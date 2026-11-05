"""CI Quality Gate for Cite RAG platform.

Ultra-fast, LLM-free evaluation that executes retrieval across the golden QA dataset,
calculates Recall@k, HitRate@k, and MRR, and asserts that metrics do not degrade
by more than the allowed regression threshold (default: 3% / 0.03) against eval/baseline.json.

Exits with code 0 on PASS, and non-zero code (1) on regression failure.
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from apps.api.src.db.session import async_session_maker
from apps.api.src.logging import get_logger, setup_logging
from eval.metrics import RetrievalMetrics, compute_retrieval_metrics
from packages.rag.src.rag.embeddings import get_embedder
from packages.rag.src.rag.search import HybridRetriever, RetrievalMode

setup_logging(log_level="INFO", environment="development")
logger = get_logger("cite.eval.ci_gate")

DEFAULT_GOLDEN_SET = Path("eval/golden_set/qa_golden_set.jsonl")
DEFAULT_BASELINE = Path("eval/baseline.json")
DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
REGRESSION_THRESHOLD = 0.03  # Max allowable 3% drop


def load_golden_set(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


async def evaluate_retrieval(
    items: list[dict[str, Any]],
    org_id: uuid.UUID = DEFAULT_ORG_ID,
    retriever: HybridRetriever | None = None,
    mode: RetrievalMode = RetrievalMode.HYBRID,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, list[list[dict[str, Any]]]]:
    """Runs retrieval for each query in the dataset and computes metrics."""
    if retriever is None:
        retriever = HybridRetriever(embedder=get_embedder())

    predictions: list[list[dict[str, Any]]] = []

    async with async_session_maker() as session:
        for item in items:
            if item.get("should_refuse"):
                predictions.append([])
                continue

            query = item["query"]
            results = await retriever.search(
                session=session,
                query=query,
                org_id=org_id,
                mode=mode,
                top_k=top_k,
            )
            predictions.append(
                [
                    {
                        "chunk_id": str(r.chunk_id),
                        "document_id": str(r.document_id),
                        "document_title": r.document_title,
                        "section_title": r.section_title,
                        "score": r.score,
                        "content": r.content,
                    }
                    for r in results
                ]
            )

    metrics = compute_retrieval_metrics(items, predictions)
    return metrics, predictions


def check_gate(
    current: RetrievalMetrics, baseline: dict[str, float], threshold: float = REGRESSION_THRESHOLD
) -> tuple[bool, list[str]]:
    """Checks whether current metrics violate the regression threshold against baseline."""
    failures: list[str] = []
    checks = [
        ("mrr", current.mrr, baseline.get("mrr", 0.0)),
        ("recall_at_5", current.recall_at_5, baseline.get("recall_at_5", 0.0)),
        ("hit_rate_at_5", current.hit_rate_at_5, baseline.get("hit_rate_at_5", 0.0)),
        ("recall_at_3", current.recall_at_3, baseline.get("recall_at_3", 0.0)),
        ("hit_rate_at_3", current.hit_rate_at_3, baseline.get("hit_rate_at_3", 0.0)),
    ]

    for name, curr_val, base_val in checks:
        diff = curr_val - base_val
        if diff < -threshold:
            failures.append(
                f"REGRESSION in {name}: current={curr_val:.4f}, baseline={base_val:.4f}, delta={diff:+.4f} (exceeds tolerance -{threshold:.4f})"
            )

    is_pass = len(failures) == 0
    return is_pass, failures


async def run_ci_gate(
    golden_set_path: Path = DEFAULT_GOLDEN_SET,
    baseline_path: Path = DEFAULT_BASELINE,
    init_baseline: bool = False,
    threshold: float = REGRESSION_THRESHOLD,
    retriever: HybridRetriever | None = None,
) -> int:
    """Executes the CI quality gate."""
    if not golden_set_path.exists():
        logger.error("Golden dataset not found", path=str(golden_set_path))
        return 1

    items = load_golden_set(golden_set_path)
    logger.info("Loaded golden dataset", items_count=len(items))

    metrics, _ = await evaluate_retrieval(items, retriever=retriever)
    logger.info(
        "Retrieval evaluation complete",
        hit_rate_5=metrics.hit_rate_at_5,
        recall_5=metrics.recall_at_5,
        mrr=metrics.mrr,
        total_eval=metrics.total_evaluated,
    )

    current_dict = {
        "mrr": metrics.mrr,
        "recall_at_5": metrics.recall_at_5,
        "hit_rate_at_5": metrics.hit_rate_at_5,
        "recall_at_3": metrics.recall_at_3,
        "hit_rate_at_3": metrics.hit_rate_at_3,
        "total_evaluated": metrics.total_evaluated,
    }

    if init_baseline or not baseline_path.exists():
        logger.info("Initializing baseline metrics file", path=str(baseline_path))
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(current_dict, f, indent=2)
        print("\n✅ Baseline successfully initialized at:", baseline_path)
        print(json.dumps(current_dict, indent=2))
        return 0

    with open(baseline_path, encoding="utf-8") as f:
        baseline_dict = json.load(f)

    is_pass, failures = check_gate(metrics, baseline_dict, threshold=threshold)

    print("\n" + "=" * 60)
    print(" CITE CI QUALITY GATE RESULTS")
    print("=" * 60)
    print(f"Total Evaluated Queries: {metrics.total_evaluated}")
    print(f"{'Metric':<18} | {'Current':<10} | {'Baseline':<10} | {'Delta':<10}")
    print("-" * 60)
    for key in ["mrr", "recall_at_5", "hit_rate_at_5", "recall_at_3", "hit_rate_at_3"]:
        curr = current_dict[key]
        base = baseline_dict.get(key, 0.0)
        delta = curr - base
        status = "✅" if delta >= -threshold else "❌"
        print(f"{status} {key:<16} | {curr:<10.4f} | {base:<10.4f} | {delta:+.4f}")
    print("=" * 60)

    if not is_pass:
        print("\n❌ CI QUALITY GATE FAILED! Regression detected:")
        for fail in failures:
            print(f"  • {fail}")
        return 1

    print("\n✅ CI QUALITY GATE PASSED: All retrieval metrics meet or exceed baseline tolerance.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Cite CI Quality Gate")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--init-baseline", action="store_true", help="Save current run as baseline")
    parser.add_argument("--threshold", type=float, default=REGRESSION_THRESHOLD)
    args = parser.parse_args()

    exit_code = asyncio.run(
        run_ci_gate(
            golden_set_path=args.golden_set,
            baseline_path=args.baseline,
            init_baseline=args.init_baseline,
            threshold=args.threshold,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

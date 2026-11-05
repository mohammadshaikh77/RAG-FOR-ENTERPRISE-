"""CI Quality Gate for Cite RAG platform.

Evaluates retrieval quality across the golden QA dataset (eval/golden_set/qa_golden_set.jsonl)
against absolute quality floors and regression baseline tolerance.

Absolute quality floors on held-out test set:
- HitRate@5 >= 0.75 (75%)
- Recall@5 >= 0.70 (70%)
- MRR >= 0.45
- HitRate@3 >= 0.60 (60%)

Exits with code 0 on PASS, and non-zero code (1) on gate failure.
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
REGRESSION_THRESHOLD = 0.05  # Max allowable 5% drop

# Absolute quality floors calibrated against empirical held-out test set distributions
ABSOLUTE_QUALITY_FLOORS = {
    "hit_rate_at_5": 0.75,
    "recall_at_5": 0.70,
    "mrr": 0.45,
    "hit_rate_at_3": 0.60,
}


def load_golden_set(path: Path, split: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                item = json.loads(line)
                if split and item.get("split") != split:
                    continue
                items.append(item)
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
    current: RetrievalMetrics,
    baseline: dict[str, float] | None = None,
    floors: dict[str, float] = ABSOLUTE_QUALITY_FLOORS,
    threshold: float = REGRESSION_THRESHOLD,
) -> tuple[bool, list[str]]:
    """Checks whether current metrics satisfy absolute floors and baseline tolerance."""
    failures: list[str] = []

    current_dict = {
        "mrr": current.mrr,
        "recall_at_5": current.recall_at_5,
        "hit_rate_at_5": current.hit_rate_at_5,
        "recall_at_3": current.recall_at_3,
        "hit_rate_at_3": current.hit_rate_at_3,
    }

    # 1. Absolute floor checks
    for metric_name, floor_val in floors.items():
        curr_val = current_dict.get(metric_name, 0.0)
        if curr_val < floor_val:
            failures.append(
                f"ABSOLUTE FLOOR VIOLATION in {metric_name}: current={curr_val:.4f} < minimum floor={floor_val:.4f}"
            )

    # 2. Baseline regression checks (if baseline provided)
    if baseline:
        for key in ["mrr", "recall_at_5", "hit_rate_at_5"]:
            if key in baseline:
                diff = current_dict[key] - baseline[key]
                if diff < -threshold:
                    failures.append(
                        f"REGRESSION in {key}: current={current_dict[key]:.4f}, baseline={baseline[key]:.4f}, delta={diff:+.4f} (exceeds tolerance -{threshold:.4f})"
                    )

    is_pass = len(failures) == 0
    return is_pass, failures


async def run_ci_gate(
    golden_set_path: Path = DEFAULT_GOLDEN_SET,
    baseline_path: Path = DEFAULT_BASELINE,
    split: str = "test",
    init_baseline: bool = False,
    threshold: float = REGRESSION_THRESHOLD,
    retriever: HybridRetriever | None = None,
) -> int:
    """Executes the CI quality gate on the held-out test set."""
    if not golden_set_path.exists():
        logger.error("Golden dataset not found", path=str(golden_set_path))
        return 1

    items = load_golden_set(golden_set_path, split=split)
    logger.info("Loaded golden dataset split", split=split, count=len(items))

    metrics, _ = await evaluate_retrieval(items, retriever=retriever)
    logger.info(
        "Retrieval evaluation complete",
        split=split,
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
        "split": split,
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

    is_pass, failures = check_gate(
        metrics, baseline=baseline_dict, floors=ABSOLUTE_QUALITY_FLOORS, threshold=threshold
    )

    print("\n" + "=" * 65)
    print(f" CITE CI QUALITY GATE RESULTS (Split: {split.upper()}, n={metrics.total_evaluated})")
    print("=" * 65)
    print(f"{'Metric':<16} | {'Current':<9} | {'Floor':<9} | {'Baseline':<9} | {'Status'}")
    print("-" * 65)
    for key, floor in ABSOLUTE_QUALITY_FLOORS.items():
        curr = float(getattr(metrics, key, 0.0))
        base = float(baseline_dict.get(key, 0.0))
        status = "✅ PASS" if (curr >= floor and curr - base >= -threshold) else "❌ FAIL"
        print(f"{key:<16} | {curr:<9.4f} | {floor:<9.4f} | {base:<9.4f} | {status}")
    print("=" * 65)

    if not is_pass:
        print("\n❌ CI QUALITY GATE FAILED! Gate violations detected:")
        for fail in failures:
            print(f"  • {fail}")
        return 1

    print(
        "\n✅ CI QUALITY GATE PASSED: All metrics satisfy absolute floors and baseline tolerance."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Cite CI Quality Gate")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--split", type=str, default="test", choices=["test", "dev", "all"])
    parser.add_argument("--init-baseline", action="store_true", help="Save current run as baseline")
    parser.add_argument("--threshold", type=float, default=REGRESSION_THRESHOLD)
    args = parser.parse_args()

    split_arg = None if args.split == "all" else args.split
    exit_code = asyncio.run(
        run_ci_gate(
            golden_set_path=args.golden_set,
            baseline_path=args.baseline,
            split=split_arg or "test",
            init_baseline=args.init_baseline,
            threshold=args.threshold,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

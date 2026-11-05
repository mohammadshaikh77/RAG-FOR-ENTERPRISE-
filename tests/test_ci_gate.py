"""Tests for the Cite CI Quality Gate and regression detection."""

import uuid
from typing import Any

import pytest

from eval.ci_gate import check_gate, run_ci_gate
from eval.metrics import RetrievalMetrics
from packages.rag.src.rag.search import HybridRetriever, RetrievalResult


def test_ci_gate_pass() -> None:
    """Verifies CI gate passes when metrics meet or exceed baseline."""
    baseline = {
        "mrr": 0.85,
        "recall_at_5": 0.88,
        "hit_rate_at_5": 0.95,
        "recall_at_3": 0.80,
        "hit_rate_at_3": 0.90,
    }
    current = RetrievalMetrics(
        mrr=0.86,
        recall_at_5=0.89,
        hit_rate_at_5=0.96,
        recall_at_3=0.81,
        hit_rate_at_3=0.91,
    )

    is_pass, failures = check_gate(current, baseline, threshold=0.03)
    assert is_pass is True
    assert len(failures) == 0


def test_ci_gate_within_tolerance() -> None:
    """Verifies CI gate passes when drop is within allowed 3% threshold."""
    baseline = {
        "mrr": 0.85,
        "recall_at_5": 0.88,
        "hit_rate_at_5": 0.95,
        "hit_rate_at_3": 0.90,
    }
    current = RetrievalMetrics(
        mrr=0.835,  # 1.5% drop (<= 3%)
        recall_at_5=0.86,  # 2% drop (<= 3%)
        hit_rate_at_5=0.94,
        hit_rate_at_3=0.89,
    )

    is_pass, failures = check_gate(current, baseline, threshold=0.03)
    assert is_pass is True
    assert len(failures) == 0


def test_ci_gate_catches_regression() -> None:
    """Verifies CI gate triggers failure when metrics drop by > 3%."""
    baseline = {
        "mrr": 0.85,
        "recall_at_5": 0.90,
        "hit_rate_at_5": 0.95,
        "hit_rate_at_3": 0.90,
    }
    current = RetrievalMetrics(
        mrr=0.80,  # 5% drop (> 3% threshold)
        recall_at_5=0.89,  # 1% drop
        hit_rate_at_5=0.95,
        hit_rate_at_3=0.90,
    )

    is_pass, failures = check_gate(current, baseline, threshold=0.03)
    assert is_pass is False
    assert len(failures) == 1
    assert "REGRESSION in mrr" in failures[0]
    assert "delta=-0.0500" in failures[0]


def test_ci_gate_catches_floor_violation() -> None:
    """Verifies CI gate triggers failure when metric is below absolute floor."""
    baseline = {
        "mrr": 0.50,
        "recall_at_5": 0.75,
        "hit_rate_at_5": 0.80,
        "hit_rate_at_3": 0.65,
    }
    current = RetrievalMetrics(
        mrr=0.40,  # Below absolute floor of 0.45
        recall_at_5=0.75,
        hit_rate_at_5=0.80,
        hit_rate_at_3=0.65,
    )

    is_pass, failures = check_gate(current, baseline, threshold=0.03)
    assert is_pass is False
    assert any("ABSOLUTE FLOOR VIOLATION in mrr" in f for f in failures)


class DegradedMockRetriever(HybridRetriever):
    """Simulates a broken/degraded retriever returning irrelevant documents."""

    def __init__(self) -> None:
        pass

    async def search(self, *args: Any, **kwargs: Any) -> list[RetrievalResult]:
        # Always returns chunks with random IDs that never match ground truth
        return [
            RetrievalResult(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                document_title="Irrelevant Random Drug",
                org_id=uuid.uuid4(),
                content="Irrelevant text content",
                section_title="Unknown",
                section_path=None,
                page_number=None,
                score=0.1,
            )
        ]


@pytest.mark.asyncio
async def test_degraded_retrieval_fails_ci_gate(tmp_path: Any) -> None:
    """End-to-end test proving that a degraded retriever fails the CI gate."""
    # Write sample golden set
    golden_file = tmp_path / "golden.jsonl"
    target_id = str(uuid.uuid4())
    golden_file.write_text(
        '{"id": "qa_1", "query": "test query", "category": "single_doc", "expected_answer": "ans", '
        f'"target_document_ids": ["{target_id}"], "should_refuse": false}}\n'
    )

    # Write high baseline
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        '{"mrr": 0.90, "recall_at_5": 0.90, "hit_rate_at_5": 0.90, "recall_at_3": 0.90, "hit_rate_at_3": 0.90}\n'
    )

    # Run CI gate with degraded retriever
    exit_code = await run_ci_gate(
        golden_set_path=golden_file,
        baseline_path=baseline_file,
        retriever=DegradedMockRetriever(),
        threshold=0.03,
    )

    # Must fail with exit code 1
    assert exit_code == 1

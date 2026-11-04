from typing import Any, Protocol

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger

logger = get_logger("cite.rag.reranker")
settings = get_settings()


class Reranker(Protocol):
    """Protocol for candidate rerankers."""

    def rerank(self, query: str, texts: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    """Local, lightweight cross-encoder reranker (e.g. TinyBERT or MiniLM)."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.reranker_model
        self._model: Any = None

    def _load_model(self) -> None:
        if self._model is None:
            logger.info("Loading cross-encoder reranker model", model=self._model_name)
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        self._load_model()
        assert self._model is not None
        pairs = [[query, text] for text in texts]
        scores = self._model.predict(pairs)
        return [float(s) for s in scores]


class MockReranker:
    """Deterministic mock reranker for tests."""

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        # Simple word-overlap ratio heuristic as deterministic mock score
        query_words = set(query.lower().split())
        scores: list[float] = []
        for text in texts:
            text_words = set(text.lower().split())
            overlap = len(query_words.intersection(text_words))
            scores.append(float(overlap) / (len(query_words) or 1.0))
        return scores


_global_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _global_reranker
    if _global_reranker is None:
        if settings.enable_reranker:
            _global_reranker = CrossEncoderReranker()
        else:
            _global_reranker = MockReranker()
    return _global_reranker

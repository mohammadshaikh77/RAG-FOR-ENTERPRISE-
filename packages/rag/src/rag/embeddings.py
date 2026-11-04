import hashlib
from typing import Any, Protocol

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger

logger = get_logger("cite.rag.embeddings")
settings = get_settings()


class Embedder(Protocol):
    """Protocol for embedding providers."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...
    @property
    def model_name(self) -> str: ...
    @property
    def dimension(self) -> int: ...


class LocalSentenceTransformerEmbedder:
    """Local, free embeddings via sentence-transformers."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.embedding_model
        self._dimension = settings.embedding_dimension
        self._model: Any = None
        self._cache: dict[str, list[float]] = {}

    def _load_model(self) -> None:
        if self._model is None:
            logger.info("Loading sentence-transformers embedding model", model=self._model_name)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []

        self._load_model()
        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        # Check in-memory cache
        for i, text in enumerate(texts):
            h = self._hash_text(text)
            if h in self._cache:
                results[i] = self._cache[h]
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if missing_texts:
            assert self._model is not None
            embeddings = self._model.encode(
                missing_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            for orig_idx, emb in zip(missing_indices, embeddings, strict=False):
                float_list = [float(x) for x in emb]
                results[orig_idx] = float_list
                self._cache[self._hash_text(texts[orig_idx])] = float_list

        return [r for r in results if r is not None]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


class MockEmbedder:
    """Deterministic mock embedder for rapid unit testing without loading weights."""

    def __init__(self, dimension: int = 384, model_name: str = "mock-embedder") -> None:
        self._dimension = dimension
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed(self, text: str) -> list[float]:
        # Generates deterministic unit-normalized pseudo-vector based on string hash
        h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        vec = [((h >> (i % 64)) & 1) * 2.0 - 1.0 for i in range(self._dimension)]
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [round(x / norm, 6) for x in vec]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)


_global_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Singleton factory for the embedding service."""
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = LocalSentenceTransformerEmbedder()
    return _global_embedder

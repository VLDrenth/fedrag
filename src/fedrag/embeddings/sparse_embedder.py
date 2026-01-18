"""Sparse BM25 embeddings using FastEmbed."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from fastembed import SparseTextEmbedding

logger = logging.getLogger(__name__)


@dataclass
class SparseVector:
    """A sparse vector with indices and values."""

    indices: List[int]
    values: List[float]


class SparseEmbedder:
    """BM25 sparse embeddings using FastEmbed."""

    def __init__(self, model_name: str = "Qdrant/bm25"):
        """Initialize the sparse embedder.

        Args:
            model_name: Name of the sparse embedding model
        """
        self.model_name = model_name
        self._model: Optional[SparseTextEmbedding] = None

    @property
    def model(self) -> SparseTextEmbedding:
        """Lazy load the model."""
        if self._model is None:
            logger.info(f"Loading sparse embedding model: {self.model_name}")
            self._model = SparseTextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> SparseVector:
        """Embed a single text.

        Args:
            text: Text to embed

        Returns:
            SparseVector with indices and values
        """
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[SparseVector]:
        """Embed a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of SparseVector objects
        """
        if not texts:
            return []

        embeddings = list(self.model.embed(texts))

        return [
            SparseVector(
                indices=emb.indices.tolist(),
                values=emb.values.tolist(),
            )
            for emb in embeddings
        ]

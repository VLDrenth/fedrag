"""Cross-encoder reranking service using sentence-transformers."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from sentence_transformers import CrossEncoder

from ..vector_store.qdrant_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RankedResult:
    """A reranked search result."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    rerank_score: float
    doc_type: str
    speaker: Optional[str]
    date: str
    title: str
    url: str

    @classmethod
    def from_search_result(
        cls, result: SearchResult, rerank_score: float
    ) -> "RankedResult":
        """Create a RankedResult from a SearchResult with rerank score."""
        return cls(
            chunk_id=result.chunk_id,
            doc_id=result.doc_id,
            text=result.text,
            score=result.score,
            rerank_score=rerank_score,
            doc_type=result.doc_type,
            speaker=result.speaker,
            date=result.date,
            title=result.title,
            url=result.url,
        )


class RerankerService:
    """Cross-encoder reranker using sentence-transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize the reranker service.

        Args:
            model_name: Name of the cross-encoder model to use
        """
        self._model: Optional[CrossEncoder] = None
        self.model_name = model_name

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5,
    ) -> List[RankedResult]:
        """Rerank search results using cross-encoder.

        Args:
            query: The original search query
            results: List of SearchResult objects to rerank
            top_k: Number of top results to return

        Returns:
            List of RankedResult objects sorted by rerank score
        """
        if not results:
            return []

        # Create query-document pairs for scoring
        pairs = [(query, r.text) for r in results]

        # Get cross-encoder scores
        scores = self.model.predict(pairs)

        # Create ranked results with scores
        ranked = [
            RankedResult.from_search_result(result, float(score))
            for result, score in zip(results, scores)
        ]

        # Sort by rerank score (descending) and return top_k
        ranked.sort(key=lambda r: r.rerank_score, reverse=True)
        return ranked[:top_k]

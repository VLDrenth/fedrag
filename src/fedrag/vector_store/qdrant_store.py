"""Qdrant vector database client with hybrid search support."""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from ..config import EmbeddingConfig, QdrantConfig, default_config
from ..embeddings.sparse_embedder import SparseVector as SparseVectorData

logger = logging.getLogger(__name__)

# Named vector identifiers
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@dataclass
class SearchResult:
    """A search result from Qdrant."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    doc_type: str
    speaker: Optional[str]
    date: str
    title: str
    url: str


class QdrantStore:
    """Qdrant vector database wrapper with hybrid search."""

    def __init__(
        self,
        qdrant_config: Optional[QdrantConfig] = None,
        embedding_config: Optional[EmbeddingConfig] = None,
    ):
        """Initialize Qdrant client with persistent storage.

        Args:
            qdrant_config: Qdrant configuration
            embedding_config: Embedding configuration for vector dimensions
        """
        self.qdrant_config = qdrant_config or default_config.qdrant
        self.embedding_config = embedding_config or default_config.embedding

        # Ensure path exists
        self.qdrant_config.path.mkdir(parents=True, exist_ok=True)

        # Initialize persistent client
        self._client = QdrantClient(path=str(self.qdrant_config.path))
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection with hybrid vector support if it doesn't exist."""
        collections = self._client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.qdrant_config.collection_name not in collection_names:
            self._client.create_collection(
                collection_name=self.qdrant_config.collection_name,
                vectors_config={
                    DENSE_VECTOR_NAME: VectorParams(
                        size=self.embedding_config.dimensions,
                        distance=Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: SparseVectorParams(),
                },
            )
            logger.info(
                f"Created hybrid collection: {self.qdrant_config.collection_name}"
            )

    def _chunk_id_to_int(self, chunk_id: str) -> int:
        """Convert chunk_id string to integer hash for Qdrant.

        Args:
            chunk_id: Chunk ID string

        Returns:
            Positive integer hash
        """
        hash_hex = hashlib.sha256(chunk_id.encode()).hexdigest()[:16]
        return int(hash_hex, 16)

    def upsert(
        self,
        chunk_ids: List[str],
        dense_embeddings: List[List[float]],
        sparse_embeddings: List[SparseVectorData],
        payloads: List[Dict[str, Any]],
    ) -> None:
        """Upsert vectors with both dense and sparse embeddings.

        Args:
            chunk_ids: List of chunk IDs
            dense_embeddings: List of dense embedding vectors
            sparse_embeddings: List of sparse embedding vectors
            payloads: List of metadata payloads
        """
        if not chunk_ids:
            return

        points = [
            PointStruct(
                id=self._chunk_id_to_int(chunk_id),
                vector={
                    DENSE_VECTOR_NAME: dense_emb,
                    SPARSE_VECTOR_NAME: SparseVector(
                        indices=sparse_emb.indices,
                        values=sparse_emb.values,
                    ),
                },
                payload={**payload, "chunk_id": chunk_id},
            )
            for chunk_id, dense_emb, sparse_emb, payload in zip(
                chunk_ids, dense_embeddings, sparse_embeddings, payloads
            )
        ]

        self._client.upsert(
            collection_name=self.qdrant_config.collection_name,
            points=points,
        )
        logger.debug(f"Upserted {len(points)} points")

    def search(
        self,
        dense_vector: List[float],
        sparse_vector: SparseVectorData,
        limit: int = 10,
        doc_type: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> List[SearchResult]:
        """Hybrid search using RRF fusion of dense and sparse vectors.

        Args:
            dense_vector: Dense query embedding
            sparse_vector: Sparse query embedding
            limit: Maximum results to return
            doc_type: Optional filter by document type
            speaker: Optional filter by speaker

        Returns:
            List of SearchResult objects
        """
        # Build filter conditions
        conditions = []
        if doc_type:
            conditions.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchValue(value=doc_type),
                )
            )
        if speaker:
            conditions.append(
                FieldCondition(
                    key="speaker",
                    match=MatchValue(value=speaker),
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        # Hybrid search with RRF fusion
        results = self._client.query_points(
            collection_name=self.qdrant_config.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=limit * 2,  # Fetch more for fusion
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=SparseVector(
                        indices=sparse_vector.indices,
                        values=sparse_vector.values,
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=limit * 2,
                    filter=query_filter,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        ).points

        return [
            SearchResult(
                chunk_id=r.payload.get("chunk_id", ""),
                doc_id=r.payload.get("doc_id", ""),
                text=r.payload.get("text", ""),
                score=r.score,
                doc_type=r.payload.get("doc_type", ""),
                speaker=r.payload.get("speaker"),
                date=r.payload.get("date", ""),
                title=r.payload.get("title", ""),
                url=r.payload.get("url", ""),
            )
            for r in results
        ]

    def get_indexed_doc_ids(self) -> set[str]:
        """Get all unique doc_ids that have been indexed.

        Returns:
            Set of doc_id strings
        """
        doc_ids = set()
        offset = None
        batch_size = 100

        while True:
            result = self._client.scroll(
                collection_name=self.qdrant_config.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=["doc_id"],
            )

            points, offset = result

            for point in points:
                if point.payload and "doc_id" in point.payload:
                    doc_ids.add(point.payload["doc_id"])

            if offset is None:
                break

        return doc_ids

    def count(self) -> int:
        """Get total number of vectors in collection.

        Returns:
            Vector count
        """
        info = self._client.get_collection(
            collection_name=self.qdrant_config.collection_name
        )
        return info.points_count

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self._client.delete_collection(
            collection_name=self.qdrant_config.collection_name
        )
        logger.info(f"Deleted collection: {self.qdrant_config.collection_name}")

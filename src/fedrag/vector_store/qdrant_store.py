"""Qdrant vector database client."""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..config import EmbeddingConfig, QdrantConfig, default_config

logger = logging.getLogger(__name__)


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
    """Qdrant vector database wrapper."""

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
        """Create collection if it doesn't exist."""
        collections = self._client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.qdrant_config.collection_name not in collection_names:
            self._client.create_collection(
                collection_name=self.qdrant_config.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_config.dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                f"Created collection: {self.qdrant_config.collection_name}"
            )

    def _chunk_id_to_int(self, chunk_id: str) -> int:
        """Convert chunk_id string to integer hash for Qdrant.

        Args:
            chunk_id: Chunk ID string

        Returns:
            Positive integer hash
        """
        # Use first 16 hex chars of SHA256 for a 64-bit integer
        hash_hex = hashlib.sha256(chunk_id.encode()).hexdigest()[:16]
        return int(hash_hex, 16)

    def upsert(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> None:
        """Upsert vectors with payloads.

        Args:
            chunk_ids: List of chunk IDs
            embeddings: List of embedding vectors
            payloads: List of metadata payloads
        """
        if not chunk_ids:
            return

        points = [
            PointStruct(
                id=self._chunk_id_to_int(chunk_id),
                vector=embedding,
                payload={**payload, "chunk_id": chunk_id},
            )
            for chunk_id, embedding, payload in zip(
                chunk_ids, embeddings, payloads
            )
        ]

        self._client.upsert(
            collection_name=self.qdrant_config.collection_name,
            points=points,
        )
        logger.debug(f"Upserted {len(points)} points")

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        doc_type: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding vector
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

        results = self._client.query_points(
            collection_name=self.qdrant_config.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
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

"""Indexing service to orchestrate chunking, embedding, and storage."""

import logging
from typing import Dict, List, Literal, Optional

from ..chunking import Chunk, DocumentChunker
from ..config import Config, default_config
from ..embeddings import OpenAIEmbedder, SparseEmbedder
from ..storage.document_store import DocumentStore
from ..vector_store import QdrantStore

logger = logging.getLogger(__name__)

DocType = Literal["statement", "minutes", "speech", "testimony"]


class IndexingService:
    """Orchestrates the document indexing pipeline with hybrid search."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the indexing service.

        Args:
            config: Configuration object
        """
        self.config = config or default_config
        self.document_store = DocumentStore(self.config.storage)
        self.chunker = DocumentChunker(self.config.chunking)
        self.dense_embedder = OpenAIEmbedder(self.config.embedding)
        self.sparse_embedder = SparseEmbedder()
        self.vector_store = QdrantStore(
            self.config.qdrant, self.config.embedding
        )

    def index_documents(
        self,
        doc_types: Optional[List[DocType]] = None,
        batch_size: int = 50,
    ) -> Dict[str, int]:
        """Index documents from JSONL files to Qdrant.

        Args:
            doc_types: Document types to index (None = all)
            batch_size: Number of chunks to process per batch

        Returns:
            Dict mapping doc_type to number of new documents indexed
        """
        if doc_types is None:
            doc_types = ["statement", "minutes", "speech", "testimony"]

        # Get already indexed doc_ids
        indexed_ids = self.vector_store.get_indexed_doc_ids()
        logger.info(f"Found {len(indexed_ids)} already indexed documents")

        results = {}

        for doc_type in doc_types:
            new_docs = self._index_doc_type(doc_type, indexed_ids, batch_size)
            results[doc_type] = new_docs

        return results

    def _index_doc_type(
        self,
        doc_type: DocType,
        indexed_ids: set[str],
        batch_size: int,
    ) -> int:
        """Index documents of a specific type.

        Args:
            doc_type: Document type to index
            indexed_ids: Set of already indexed doc_ids
            batch_size: Chunks per batch

        Returns:
            Number of new documents indexed
        """
        logger.info(f"Indexing {doc_type} documents...")

        new_doc_count = 0
        chunks_batch: List[Chunk] = []

        for doc in self.document_store.load_documents(doc_type):
            # Skip already indexed documents
            if doc.doc_id in indexed_ids:
                continue

            # Chunk the document
            chunks = self.chunker.chunk_document(doc)
            chunks_batch.extend(chunks)
            new_doc_count += 1

            # Process batch when it reaches batch_size
            if len(chunks_batch) >= batch_size:
                self._process_chunks_batch(chunks_batch)
                chunks_batch = []

        # Process remaining chunks
        if chunks_batch:
            self._process_chunks_batch(chunks_batch)

        logger.info(
            f"Indexed {new_doc_count} new {doc_type} documents"
        )
        return new_doc_count

    def _process_chunks_batch(self, chunks: List[Chunk]) -> None:
        """Embed and store a batch of chunks with both dense and sparse vectors.

        Args:
            chunks: List of chunks to process
        """
        if not chunks:
            return

        # Extract texts for embedding
        texts = [c.text for c in chunks]

        # Generate both dense and sparse embeddings
        dense_embeddings = self.dense_embedder.embed_batch(texts)
        sparse_embeddings = self.sparse_embedder.embed_batch(texts)

        # Prepare payloads
        chunk_ids = [c.chunk_id for c in chunks]
        payloads = [
            {
                "doc_id": c.doc_id,
                "text": c.text,
                "doc_type": c.doc_type,
                "speaker": c.speaker,
                "date": str(c.date),
                "title": c.title,
                "url": c.url,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        # Upsert to Qdrant with both vector types
        self.vector_store.upsert(
            chunk_ids, dense_embeddings, sparse_embeddings, payloads
        )
        logger.debug(f"Processed batch of {len(chunks)} chunks")

    def search(
        self,
        query: str,
        limit: int = 10,
        doc_type: Optional[str] = None,
        speaker: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ):
        """Hybrid search for relevant chunks using RRF fusion.

        Args:
            query: Search query text
            limit: Maximum results
            doc_type: Optional filter by document type
            speaker: Optional filter by speaker
            date_start: Optional start date filter (YYYY-MM-DD)
            date_end: Optional end date filter (YYYY-MM-DD)

        Returns:
            List of SearchResult objects
        """
        # Generate both dense and sparse query embeddings
        dense_vector = self.dense_embedder.embed(query)
        sparse_vector = self.sparse_embedder.embed(query)

        # Hybrid search in Qdrant
        return self.vector_store.search(
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            limit=limit,
            doc_type=doc_type,
            speaker=speaker,
            date_start=date_start,
            date_end=date_end,
        )

    def get_stats(self) -> Dict[str, int]:
        """Get indexing statistics.

        Returns:
            Dict with stats
        """
        return {
            "total_vectors": self.vector_store.count(),
            "indexed_documents": len(self.vector_store.get_indexed_doc_ids()),
        }

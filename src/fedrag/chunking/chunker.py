"""Token-based document chunking."""

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

import tiktoken

from ..config import ChunkingConfig, default_config
from ..models.document import FedDocument


@dataclass
class Chunk:
    """A chunk of text from a Fed document."""

    chunk_id: str  # {doc_id}_chunk_{idx}
    doc_id: str
    text: str
    token_count: int
    chunk_index: int
    # Inherited metadata
    doc_type: str
    speaker: Optional[str]
    date: dt.date
    title: str
    url: str


class DocumentChunker:
    """Chunks documents into overlapping token-based segments."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize the chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config or default_config.chunking
        self._encoder = tiktoken.get_encoding(self.config.encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self._encoder.encode(text))

    def chunk_text(self, text: str) -> List[tuple[str, int]]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of (chunk_text, token_count) tuples
        """
        tokens = self._encoder.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= self.config.chunk_size:
            return [(text, total_tokens)]

        chunks = []
        start = 0

        while start < total_tokens:
            end = min(start + self.config.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = self._encoder.decode(chunk_tokens)
            chunks.append((chunk_text, len(chunk_tokens)))

            # Move start by chunk_size - overlap
            start += self.config.chunk_size - self.config.chunk_overlap

            # Avoid tiny final chunks
            if total_tokens - start < self.config.chunk_overlap:
                break

        return chunks

    def chunk_document(self, doc: FedDocument) -> List[Chunk]:
        """Chunk a Fed document into overlapping segments.

        Args:
            doc: FedDocument to chunk

        Returns:
            List of Chunk objects with metadata
        """
        text_chunks = self.chunk_text(doc.content)

        return [
            Chunk(
                chunk_id=f"{doc.doc_id}_chunk_{idx}",
                doc_id=doc.doc_id,
                text=chunk_text,
                token_count=token_count,
                chunk_index=idx,
                doc_type=doc.doc_type,
                speaker=doc.speaker,
                date=doc.date,
                title=doc.title,
                url=str(doc.url),
            )
            for idx, (chunk_text, token_count) in enumerate(text_chunks)
        ]

    def chunk_documents(self, docs: List[FedDocument]) -> List[Chunk]:
        """Chunk multiple documents.

        Args:
            docs: List of FedDocument objects

        Returns:
            List of all chunks from all documents
        """
        all_chunks = []
        for doc in docs:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks

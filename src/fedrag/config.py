"""Configuration settings for the Fed scraper."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ScraperConfig(BaseModel):
    """Configuration for the web scraper."""

    # Rate limiting
    max_concurrent_requests: int = 3
    requests_per_second: float = 2.0

    # Retry settings
    max_retries: int = 5
    base_backoff_seconds: float = 5.0
    max_backoff_seconds: float = 300.0

    # Request settings
    request_timeout_seconds: int = 30
    user_agent: str = (
        "FedRAG/1.0 (Research Project; "
        "https://github.com/example/fedrag; "
        "Contact: research@example.com)"
    )

    # Year range
    start_year: int = 2015
    end_year: int = 2025

    # Base URLs
    fed_base_url: str = "https://www.federalreserve.gov"


class EmbeddingConfig(BaseModel):
    """Configuration for OpenAI embeddings."""

    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100  # Max texts per API call


class QdrantConfig(BaseModel):
    """Configuration for Qdrant vector database."""

    path: Path = Path("data/qdrant")  # Local persistent storage
    collection_name: str = "fed_documents"


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = 512  # tokens
    chunk_overlap: int = 50  # tokens
    encoding_name: str = "cl100k_base"  # GPT-4/embedding model tokenizer


class StorageConfig(BaseModel):
    """Configuration for document storage."""

    data_dir: Path = Path("data")
    documents_dir: Path = Path("data/documents")
    raw_dir: Path = Path("data/raw")

    # File names for each document type
    statements_file: str = "statements.jsonl"
    minutes_file: str = "minutes.jsonl"
    speeches_file: str = "speeches.jsonl"
    testimony_file: str = "testimony.jsonl"

    def get_file_path(self, doc_type: Literal["statement", "minutes", "speech", "testimony"]) -> Path:
        """Get the JSONL file path for a document type."""
        file_map = {
            "statement": self.statements_file,
            "minutes": self.minutes_file,
            "speech": self.speeches_file,
            "testimony": self.testimony_file,
        }
        return self.documents_dir / file_map[doc_type]

    def ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)


class RerankerConfig(BaseModel):
    """Configuration for cross-encoder reranking."""

    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class LLMConfig(BaseModel):
    """Configuration for LLM service."""

    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 4096


class Config(BaseModel):
    """Main configuration container."""

    scraper: ScraperConfig = ScraperConfig()
    storage: StorageConfig = StorageConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    qdrant: QdrantConfig = QdrantConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    reranker: RerankerConfig = RerankerConfig()
    llm: LLMConfig = LLMConfig()


# Default configuration instance
default_config = Config()

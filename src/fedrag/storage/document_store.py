"""Document storage using JSONL files."""

import fcntl
import logging
from pathlib import Path
from typing import Iterator, Literal, Optional, Set

from ..config import StorageConfig, default_config
from ..models.document import FedDocument

logger = logging.getLogger(__name__)

DocType = Literal["statement", "minutes", "speech", "testimony"]


class DocumentStore:
    """JSONL-based document storage with URL deduplication."""

    def __init__(self, config: Optional[StorageConfig] = None):
        """Initialize the document store.

        Args:
            config: Storage configuration
        """
        self.config = config or default_config.storage
        self.config.ensure_directories()
        self._url_cache: dict[DocType, Set[str]] = {}

    def get_file_path(self, doc_type: DocType) -> Path:
        """Get the JSONL file path for a document type."""
        return self.config.get_file_path(doc_type)

    def _ensure_url_cache(self, doc_type: DocType) -> Set[str]:
        """Load URL cache for a document type if not already loaded."""
        if doc_type not in self._url_cache:
            self._url_cache[doc_type] = self._load_urls(doc_type)
        return self._url_cache[doc_type]

    def _load_urls(self, doc_type: DocType) -> Set[str]:
        """Load all URLs from a JSONL file.

        Args:
            doc_type: Document type to load URLs for

        Returns:
            Set of URLs
        """
        file_path = self.get_file_path(doc_type)
        urls = set()

        if not file_path.exists():
            return urls

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        doc = FedDocument.from_jsonl(line)
                        urls.add(str(doc.url))
                    except Exception as e:
                        logger.warning(f"Failed to parse line: {e}")
                        continue

            logger.info(f"Loaded {len(urls)} existing URLs for {doc_type}")
        except Exception as e:
            logger.error(f"Failed to load URLs from {file_path}: {e}")

        return urls

    def get_existing_urls(self, doc_type: DocType) -> Set[str]:
        """Get set of already-scraped URLs for a document type.

        Args:
            doc_type: Document type

        Returns:
            Set of URLs already in storage
        """
        return self._ensure_url_cache(doc_type).copy()

    def save_document(self, doc: FedDocument) -> bool:
        """Save a document to the appropriate JSONL file.

        Uses file locking for atomic appends.

        Args:
            doc: Document to save

        Returns:
            True if saved successfully
        """
        file_path = self.get_file_path(doc.doc_type)
        url_str = str(doc.url)

        # Check cache for duplicates
        url_cache = self._ensure_url_cache(doc.doc_type)
        if url_str in url_cache:
            logger.debug(f"Skipping duplicate URL: {url_str}")
            return False

        try:
            # Atomic append with file locking
            with open(file_path, "a", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(doc.to_jsonl() + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Update cache
            url_cache.add(url_str)
            logger.debug(f"Saved document: {doc.doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save document {doc.doc_id}: {e}")
            return False

    def load_documents(self, doc_type: DocType) -> Iterator[FedDocument]:
        """Load all documents of a given type.

        Args:
            doc_type: Document type to load

        Yields:
            FedDocument objects
        """
        file_path = self.get_file_path(doc_type)

        if not file_path.exists():
            return

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield FedDocument.from_jsonl(line)
                except Exception as e:
                    logger.warning(f"Failed to parse line {line_num}: {e}")
                    continue

    def count_documents(self, doc_type: DocType) -> int:
        """Count documents of a given type.

        Args:
            doc_type: Document type to count

        Returns:
            Number of documents
        """
        return len(self._ensure_url_cache(doc_type))

    def clear_cache(self) -> None:
        """Clear the in-memory URL cache."""
        self._url_cache.clear()

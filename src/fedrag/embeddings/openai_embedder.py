"""OpenAI embeddings client."""

import logging
import time
from typing import List, Optional

from openai import OpenAI, RateLimitError

from ..config import EmbeddingConfig, default_config

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """OpenAI text embeddings client with batching and retry logic."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize the embedder.

        Args:
            config: Embedding configuration
        """
        self.config = config or default_config.embedding
        self._client = OpenAI()

    def embed(self, text: str) -> List[float]:
        """Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        return self.embed_batch([text])[0]

    def embed_batch(
        self,
        texts: List[str],
        max_retries: int = 5,
        base_delay: float = 1.0,
    ) -> List[List[float]]:
        """Embed a batch of texts with retry logic.

        Args:
            texts: List of texts to embed
            max_retries: Maximum number of retries on rate limit
            base_delay: Base delay for exponential backoff

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_embeddings = self._embed_with_retry(
                batch, max_retries, base_delay
            )
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _embed_with_retry(
        self,
        texts: List[str],
        max_retries: int,
        base_delay: float,
    ) -> List[List[float]]:
        """Embed texts with exponential backoff retry.

        Args:
            texts: Texts to embed
            max_retries: Maximum retries
            base_delay: Base delay for backoff

        Returns:
            List of embedding vectors
        """
        for attempt in range(max_retries):
            try:
                response = self._client.embeddings.create(
                    model=self.config.model,
                    input=texts,
                )
                return [item.embedding for item in response.data]

            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise

                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)

        # Should not reach here
        raise RuntimeError("Embedding failed after all retries")

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.config.dimensions

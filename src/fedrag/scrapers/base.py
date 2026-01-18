"""Base scraper class with common functionality."""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from datetime import date
from typing import AsyncIterator, Optional, Set

import aiohttp
from bs4 import BeautifulSoup

from ..config import ScraperConfig, default_config
from ..models.document import FedDocument
from ..utils.rate_limiter import RateLimiter
from ..utils.retry import retry_with_backoff, RateLimitError

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for Fed document scrapers."""

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        existing_urls: Optional[Set[str]] = None,
    ):
        """Initialize the scraper.

        Args:
            config: Scraper configuration
            existing_urls: Set of URLs already scraped (for deduplication)
        """
        self.config = config or default_config.scraper
        self.existing_urls = existing_urls or set()
        self.rate_limiter = RateLimiter(
            rate=self.config.requests_per_second,
            max_concurrent=self.config.max_concurrent_requests,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """Return the document type this scraper handles."""
        pass

    async def __aenter__(self) -> "BaseScraper":
        """Create aiohttp session on context enter."""
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout_seconds),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close aiohttp session on context exit."""
        if self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the aiohttp session, raising if not initialized."""
        if self._session is None:
            raise RuntimeError("Scraper must be used as async context manager")
        return self._session

    @retry_with_backoff()
    async def fetch_page(self, url: str) -> tuple[str, str]:
        """Fetch a page and return (url, html content).

        Args:
            url: URL to fetch

        Returns:
            Tuple of (final_url, html_content)

        Raises:
            RateLimitError: If rate limited (429)
            aiohttp.ClientResponseError: On 4xx errors (not retried)
            aiohttp.ClientError: On other request errors (retried)
        """
        async with self.rate_limiter:
            logger.debug(f"Fetching: {url}")
            async with self.session.get(url) as response:
                if response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", 60))
                    raise RateLimitError(retry_after)

                # Don't retry on 4xx client errors (404, 403, etc.) - these are definitive
                if 400 <= response.status < 500:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=f"HTTP {response.status}",
                    )

                response.raise_for_status()
                html = await response.text()
                return str(response.url), html

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object."""
        return BeautifulSoup(html, "lxml")

    def clean_text(self, text: str) -> str:
        """Clean extracted text content.

        - Normalize whitespace
        - Remove excessive newlines
        - Strip leading/trailing whitespace
        """
        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize newlines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Final strip
        return text.strip()

    def make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL."""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{self.config.fed_base_url}{url}"
        return f"{self.config.fed_base_url}/{url}"

    def is_already_scraped(self, url: str) -> bool:
        """Check if URL has already been scraped."""
        return url in self.existing_urls

    @abstractmethod
    async def get_document_urls(
        self,
        start_year: int,
        end_year: int,
    ) -> AsyncIterator[str]:
        """Get URLs for all documents in the year range.

        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Yields:
            Document URLs
        """
        pass

    @abstractmethod
    async def scrape_document(self, url: str) -> Optional[FedDocument]:
        """Scrape a single document.

        Args:
            url: URL of the document to scrape

        Returns:
            FedDocument if successful, None if skipped or failed
        """
        pass

    async def scrape_all(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> AsyncIterator[FedDocument]:
        """Scrape all documents in the year range.

        Args:
            start_year: Start year (defaults to config)
            end_year: End year (defaults to config)

        Yields:
            FedDocument objects
        """
        start = start_year or self.config.start_year
        end = end_year or self.config.end_year

        logger.info(f"Scraping {self.doc_type}s from {start} to {end}")

        async for url in self.get_document_urls(start, end):
            if self.is_already_scraped(url):
                logger.debug(f"Skipping already scraped: {url}")
                continue

            try:
                doc = await self.scrape_document(url)
                if doc:
                    self.existing_urls.add(url)
                    yield doc
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue

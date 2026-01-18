"""PDF download and text extraction handler."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
from pypdf import PdfReader

from ..utils.rate_limiter import RateLimiter
from ..utils.retry import retry_with_backoff, RateLimitError
from ..config import ScraperConfig, default_config

logger = logging.getLogger(__name__)


class PDFHandler:
    """Handler for downloading and extracting text from PDF files."""

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """Initialize PDF handler.

        Args:
            config: Scraper configuration
            rate_limiter: Shared rate limiter (or creates new one)
        """
        self.config = config or default_config.scraper
        self.rate_limiter = rate_limiter or RateLimiter(
            rate=self.config.requests_per_second,
            max_concurrent=self.config.max_concurrent_requests,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "PDFHandler":
        """Create aiohttp session on context enter."""
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout_seconds * 2),
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
            raise RuntimeError("PDFHandler must be used as async context manager")
        return self._session

    @retry_with_backoff()
    async def download_pdf(self, url: str) -> bytes:
        """Download a PDF file and return its contents.

        Args:
            url: URL of the PDF to download

        Returns:
            PDF file contents as bytes

        Raises:
            RateLimitError: If rate limited (429)
            aiohttp.ClientError: On other request errors
        """
        async with self.rate_limiter:
            logger.debug(f"Downloading PDF: {url}")
            async with self.session.get(url) as response:
                if response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", 60))
                    raise RateLimitError(retry_after)

                response.raise_for_status()
                return await response.read()

    def extract_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF content.

        Args:
            pdf_content: PDF file as bytes

        Returns:
            Extracted text content
        """
        # Write to temp file for pypdf
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_content)
            tmp.flush()

            try:
                reader = PdfReader(tmp.name)
                text_parts = []

                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                return "\n\n".join(text_parts)

            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {e}")
                return ""

    async def download_and_extract(self, url: str) -> Optional[str]:
        """Download a PDF and extract its text content.

        Args:
            url: URL of the PDF to download

        Returns:
            Extracted text, or None if failed
        """
        try:
            pdf_content = await self.download_pdf(url)
            text = self.extract_text(pdf_content)
            return text if text else None
        except Exception as e:
            logger.error(f"Failed to download/extract PDF {url}: {e}")
            return None

    async def save_pdf(self, url: str, output_path: Path) -> bool:
        """Download and save a PDF file to disk.

        Args:
            url: URL of the PDF to download
            output_path: Path to save the PDF

        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_content = await self.download_pdf(url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(pdf_content)
            logger.info(f"Saved PDF to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save PDF {url}: {e}")
            return False

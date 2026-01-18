"""FOMC statement scraper."""

import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, Optional

from ..models.document import FedDocument
from .base import BaseScraper

logger = logging.getLogger(__name__)


class FOMCStatementsScraper(BaseScraper):
    """Scraper for FOMC monetary policy statements."""

    CALENDAR_URL = "/monetarypolicy/fomccalendars.htm"
    STATEMENT_PATTERN = re.compile(r"/newsevents/pressreleases/monetary\d+a?\.htm")

    @property
    def doc_type(self) -> str:
        return "statement"

    async def get_document_urls(
        self,
        start_year: int,
        end_year: int,
    ) -> AsyncIterator[str]:
        """Get FOMC statement URLs from the calendar page.

        The Fed calendar page contains links to all FOMC meetings.
        Statement links match pattern: /newsevents/pressreleases/monetaryYYYYMMDD.htm
        """
        calendar_url = self.make_absolute_url(self.CALENDAR_URL)
        _, html = await self.fetch_page(calendar_url)
        soup = self.parse_html(html)

        # Find all links matching the statement pattern
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if self.STATEMENT_PATTERN.match(href):
                full_url = self.make_absolute_url(href)

                # Extract year from URL to filter
                year_match = re.search(r"/monetary(\d{4})", href)
                if year_match:
                    year = int(year_match.group(1))
                    if start_year <= year <= end_year:
                        yield full_url

    def _extract_date_from_url(self, url: str) -> Optional[date]:
        """Extract date from statement URL.

        URL format: /newsevents/pressreleases/monetary20231101a.htm
        """
        match = re.search(r"/monetary(\d{8})", url)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                pass
        return None

    def _extract_content(self, soup) -> str:
        """Extract statement content from parsed HTML."""
        # FOMC statements are typically in a div with class "col-xs-12 col-sm-8 col-md-8"
        # or in the main article content
        content_div = soup.find("div", class_="col-xs-12 col-sm-8 col-md-8")

        if not content_div:
            # Try alternative selectors
            content_div = soup.find("div", id="content")

        if not content_div:
            # Fallback to article or main
            content_div = soup.find("article") or soup.find("main")

        if content_div:
            # Remove navigation, headers, footers
            for tag in content_div.find_all(["nav", "header", "footer", "script", "style"]):
                tag.decompose()
            return self.clean_text(content_div.get_text())

        return ""

    def _extract_title(self, soup) -> str:
        """Extract statement title from parsed HTML."""
        # Try h1 first
        h1 = soup.find("h1")
        if h1:
            return self.clean_text(h1.get_text())

        # Try title tag
        title = soup.find("title")
        if title:
            return self.clean_text(title.get_text())

        return "FOMC Statement"

    async def scrape_document(self, url: str) -> Optional[FedDocument]:
        """Scrape a single FOMC statement."""
        logger.info(f"Scraping statement: {url}")

        try:
            final_url, html = await self.fetch_page(url)
            soup = self.parse_html(html)

            doc_date = self._extract_date_from_url(url)
            if not doc_date:
                logger.warning(f"Could not extract date from URL: {url}")
                return None

            title = self._extract_title(soup)
            content = self._extract_content(soup)

            if not content:
                logger.warning(f"No content found for: {url}")
                return None

            # Check for PDF link
            pdf_link = soup.find("a", href=re.compile(r"\.pdf$", re.I))
            has_pdf = pdf_link is not None
            pdf_url = self.make_absolute_url(pdf_link["href"]) if pdf_link else None

            return FedDocument.create(
                url=final_url,
                doc_type="statement",
                title=title,
                doc_date=doc_date,
                content=content,
                raw_html=html,
                speaker=None,  # Committee document, no single speaker
                has_pdf=has_pdf,
                pdf_url=pdf_url,
            )

        except Exception as e:
            logger.error(f"Error scraping statement {url}: {e}")
            raise

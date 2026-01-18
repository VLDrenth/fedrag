"""Congressional testimony scraper."""

import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, Optional

from ..models.document import FedDocument
from .base import BaseScraper

logger = logging.getLogger(__name__)


class TestimonyScraper(BaseScraper):
    """Scraper for Federal Reserve congressional testimony."""

    # URL format changed over time - try both patterns
    TESTIMONY_INDEX_TEMPLATES = [
        "/newsevents/testimony/{year}-testimony.htm",  # 2017+
        "/newsevents/testimony/{year}testimony.htm",   # 2015-2016
    ]
    TESTIMONY_PATTERN = re.compile(r"/newsevents/testimony/\w+\d+a?\.htm")

    # Speaker patterns for testimony
    SPEAKER_PATTERNS = [
        re.compile(r"^(Chair(?:man|woman)?)\s+(\w+)", re.I),
        re.compile(r"^(Vice Chair(?:man|woman)?)\s+(\w+)", re.I),
        re.compile(r"^(Governor)\s+(\w+)", re.I),
    ]

    @property
    def doc_type(self) -> str:
        return "testimony"

    async def get_document_urls(
        self,
        start_year: int,
        end_year: int,
    ) -> AsyncIterator[str]:
        """Get testimony URLs from yearly index pages."""
        for year in range(start_year, end_year + 1):
            html = None

            # Try each URL template until one works
            for template in self.TESTIMONY_INDEX_TEMPLATES:
                index_url = self.make_absolute_url(template.format(year=year))
                try:
                    _, html = await self.fetch_page(index_url)
                    break  # Success, stop trying templates
                except Exception:
                    continue  # Try next template

            if html is None:
                logger.warning(f"Could not fetch testimony index for {year} (tried all URL patterns)")
                continue

            soup = self.parse_html(html)

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if self.TESTIMONY_PATTERN.match(href):
                    yield self.make_absolute_url(href)

    def _extract_speaker(self, title: str, soup) -> Optional[str]:
        """Extract speaker name from title or page content."""
        for pattern in self.SPEAKER_PATTERNS:
            match = pattern.search(title)
            if match:
                role = match.group(1)
                name = match.group(2)
                return f"{role} {name}"

        # Try to find speaker in page metadata
        speaker_elem = soup.find("p", class_="speaker")
        if speaker_elem:
            return self.clean_text(speaker_elem.get_text())

        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"]

        return None

    def _extract_date_from_page(self, soup) -> Optional[date]:
        """Extract date from testimony page content."""
        date_elem = soup.find("p", class_="article__time")
        if date_elem:
            date_text = date_elem.get_text().strip()
            for fmt in ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(date_text, fmt).date()
                except ValueError:
                    continue

        meta_date = soup.find("meta", attrs={"name": "DC.date.issued"})
        if meta_date and meta_date.get("content"):
            try:
                return datetime.strptime(meta_date["content"], "%Y-%m-%d").date()
            except ValueError:
                pass

        return None

    def _extract_date_from_url(self, url: str) -> Optional[date]:
        """Extract date from testimony URL as fallback.

        URL format: /newsevents/testimony/powell20231115a.htm
        """
        match = re.search(r"/testimony/\w+(\d{8})", url)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                pass
        return None

    def _extract_content(self, soup) -> str:
        """Extract testimony content from parsed HTML."""
        content_div = soup.find("div", class_="col-xs-12 col-sm-8 col-md-8")

        if not content_div:
            content_div = soup.find("article")

        if not content_div:
            content_div = soup.find("div", id="content")

        if content_div:
            for tag in content_div.find_all(["nav", "header", "footer", "script", "style", "aside"]):
                tag.decompose()
            return self.clean_text(content_div.get_text())

        return ""

    def _extract_title(self, soup) -> str:
        """Extract testimony title from parsed HTML."""
        h1 = soup.find("h1")
        if h1:
            return self.clean_text(h1.get_text())

        h3 = soup.find("h3", class_="title")
        if h3:
            return self.clean_text(h3.get_text())

        title = soup.find("title")
        if title:
            return self.clean_text(title.get_text())

        return "Congressional Testimony"

    async def scrape_document(self, url: str) -> Optional[FedDocument]:
        """Scrape a single testimony document."""
        logger.info(f"Scraping testimony: {url}")

        try:
            final_url, html = await self.fetch_page(url)
            soup = self.parse_html(html)

            title = self._extract_title(soup)
            speaker = self._extract_speaker(title, soup)

            doc_date = self._extract_date_from_page(soup)
            if not doc_date:
                doc_date = self._extract_date_from_url(url)

            if not doc_date:
                logger.warning(f"Could not extract date for testimony: {url}")
                return None

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
                doc_type="testimony",
                title=title,
                doc_date=doc_date,
                content=content,
                raw_html=html,
                speaker=speaker,
                has_pdf=has_pdf,
                pdf_url=pdf_url,
            )

        except Exception as e:
            logger.error(f"Error scraping testimony {url}: {e}")
            raise

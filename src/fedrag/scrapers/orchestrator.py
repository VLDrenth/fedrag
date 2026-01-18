"""Scraping orchestrator to coordinate multiple scrapers."""

import asyncio
import logging
from typing import AsyncIterator, List, Literal, Optional, Set

from ..config import Config, default_config
from ..models.document import FedDocument
from ..storage.document_store import DocumentStore
from .fomc_statements import FOMCStatementsScraper
from .fomc_minutes import FOMCMinutesScraper
from .speeches import SpeechesScraper
from .testimony import TestimonyScraper

logger = logging.getLogger(__name__)

DocType = Literal["statement", "minutes", "speech", "testimony"]


class ScrapingOrchestrator:
    """Orchestrates scraping across multiple document types."""

    def __init__(
        self,
        config: Optional[Config] = None,
        store: Optional[DocumentStore] = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Configuration (uses default if not provided)
            store: Document store (creates new one if not provided)
        """
        self.config = config or default_config
        self.store = store or DocumentStore(self.config.storage)

    def _get_scraper_class(self, doc_type: DocType):
        """Get the scraper class for a document type."""
        scrapers = {
            "statement": FOMCStatementsScraper,
            "minutes": FOMCMinutesScraper,
            "speech": SpeechesScraper,
            "testimony": TestimonyScraper,
        }
        return scrapers[doc_type]

    async def scrape_type(
        self,
        doc_type: DocType,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> int:
        """Scrape all documents of a specific type.

        Args:
            doc_type: Type of document to scrape
            start_year: Start year (defaults to config)
            end_year: End year (defaults to config)

        Returns:
            Number of documents scraped
        """
        existing_urls = self.store.get_existing_urls(doc_type)
        scraper_class = self._get_scraper_class(doc_type)

        count = 0
        async with scraper_class(
            config=self.config.scraper,
            existing_urls=existing_urls,
        ) as scraper:
            async for doc in scraper.scrape_all(start_year, end_year):
                self.store.save_document(doc)
                count += 1
                logger.info(f"Saved: {doc.doc_id} - {doc.title[:50]}...")

        logger.info(f"Scraped {count} {doc_type} documents")
        return count

    async def scrape_all(
        self,
        doc_types: Optional[List[DocType]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> dict[str, int]:
        """Scrape all document types.

        Args:
            doc_types: List of document types to scrape (all if not provided)
            start_year: Start year (defaults to config)
            end_year: End year (defaults to config)

        Returns:
            Dictionary mapping doc_type to count of documents scraped
        """
        types_to_scrape = doc_types or ["statement", "minutes", "speech", "testimony"]
        results = {}

        for doc_type in types_to_scrape:
            logger.info(f"Starting scrape for: {doc_type}")
            count = await self.scrape_type(doc_type, start_year, end_year)
            results[doc_type] = count

        total = sum(results.values())
        logger.info(f"Total documents scraped: {total}")
        return results

    def get_stats(self) -> dict[str, int]:
        """Get statistics about stored documents.

        Returns:
            Dictionary mapping doc_type to document count
        """
        return {
            "statement": self.store.count_documents("statement"),
            "minutes": self.store.count_documents("minutes"),
            "speech": self.store.count_documents("speech"),
            "testimony": self.store.count_documents("testimony"),
        }

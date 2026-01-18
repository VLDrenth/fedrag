"""Federal Reserve document model."""

import datetime as dt
from hashlib import sha256
from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl, Field


class FedDocument(BaseModel):
    """A Federal Reserve document with metadata."""

    doc_id: str = Field(description="Unique document ID: {doc_type}_{YYYYMMDD}_{hash[:8]}")
    url: HttpUrl = Field(description="Source URL of the document")
    doc_type: Literal["statement", "minutes", "speech", "testimony"] = Field(
        description="Type of Fed document"
    )
    title: str = Field(description="Document title")
    speaker: Optional[str] = Field(default=None, description="Speaker name (None for committee docs)")
    date: dt.date = Field(description="Publication date")
    content: str = Field(description="Cleaned text content")
    raw_html: str = Field(description="Raw HTML for reprocessing")
    has_pdf: bool = Field(default=False, description="Whether PDF version exists")
    pdf_url: Optional[HttpUrl] = Field(default=None, description="URL to PDF version")
    scraped_at: str = Field(description="ISO timestamp of when document was scraped")
    content_hash: str = Field(description="SHA256 hash of content for deduplication")

    @classmethod
    def create(
        cls,
        url: str,
        doc_type: Literal["statement", "minutes", "speech", "testimony"],
        title: str,
        doc_date: dt.date,
        content: str,
        raw_html: str,
        speaker: Optional[str] = None,
        has_pdf: bool = False,
        pdf_url: Optional[str] = None,
    ) -> "FedDocument":
        """Factory method to create a FedDocument with computed fields."""
        content_hash = sha256(content.encode()).hexdigest()
        doc_id = f"{doc_type}_{doc_date.strftime('%Y%m%d')}_{content_hash[:8]}"
        scraped_at = dt.datetime.utcnow().isoformat() + "Z"

        return cls(
            doc_id=doc_id,
            url=url,
            doc_type=doc_type,
            title=title,
            speaker=speaker,
            date=doc_date,
            content=content,
            raw_html=raw_html,
            has_pdf=has_pdf,
            pdf_url=pdf_url,
            scraped_at=scraped_at,
            content_hash=content_hash,
        )

    def to_jsonl(self) -> str:
        """Serialize to JSONL-compatible string."""
        return self.model_dump_json()

    @classmethod
    def from_jsonl(cls, line: str) -> "FedDocument":
        """Deserialize from JSONL line."""
        return cls.model_validate_json(line)

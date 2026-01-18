"""LLM service using OpenAI with Pydantic tool definitions."""

import logging
from typing import List, Literal, Optional

import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchFedDocumentsArgs(BaseModel):
    """Arguments for the search_fed_documents tool."""

    query: str = Field(
        description="The search query to find relevant Fed documents"
    )
    speaker: Optional[str] = Field(
        default=None,
        description="Filter by speaker last name only (e.g., 'Powell', 'Waller', 'Yellen')",
    )
    doc_type: Optional[Literal["speech", "statement", "minutes", "testimony"]] = Field(
        default=None,
        description="Filter by document type",
    )
    date_start: Optional[str] = Field(
        default=None,
        description="Start date filter in YYYY-MM-DD format",
    )
    date_end: Optional[str] = Field(
        default=None,
        description="End date filter in YYYY-MM-DD format",
    )


class LLMService:
    """LLM service using OpenAI with tool calling support."""

    def __init__(
        self,
        model: str = "gpt-5.2",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        """Initialize the LLM service.

        Args:
            model: OpenAI model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self._client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Create tool from Pydantic model
        self._tools = [
            openai.pydantic_function_tool(
                SearchFedDocumentsArgs,
                name="search_fed_documents",
                description=(
                    "Search Federal Reserve speeches, statements, meeting minutes, "
                    "and congressional testimony. Use this tool to find relevant "
                    "information about Fed policy, economic outlook, and official "
                    "communications. You can filter by speaker, document type, and "
                    "date range."
                ),
            )
        ]

    def chat(self, messages: List[dict]) -> ChatCompletion:
        """Send a chat request with tool calling support.

        Args:
            messages: List of message dicts with role and content

        Returns:
            ChatCompletion response from OpenAI
        """
        return self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._tools,
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,
        )

    def chat_without_tools(self, messages: List[dict]) -> ChatCompletion:
        """Send a chat request without tools.

        Args:
            messages: List of message dicts with role and content

        Returns:
            ChatCompletion response from OpenAI
        """
        return self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,
        )

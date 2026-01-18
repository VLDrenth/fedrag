"""Query pipeline orchestrating LLM, search, and reranking."""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ..config import Config, default_config
from .indexing import IndexingService
from .llm import LLMService, SearchFedDocumentsArgs
from .reranker import RankedResult, RerankerService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful assistant specializing in Federal Reserve policy and communications.
You have access to a search tool that can find relevant information from Fed speeches,
FOMC statements, meeting minutes, and congressional testimony.

When answering questions:
1. Use the search tool to find relevant information before answering
2. You can make multiple search calls if needed to gather comprehensive information
3. Always cite your sources by mentioning the speaker, date, and document type
4. If the search returns no relevant results, say so honestly
5. Focus on factual information from the documents rather than speculation

For date-based queries, use the date_start and date_end filters (YYYY-MM-DD format).
For speaker-specific queries, use the speaker filter with their full name.
"""


@dataclass
class QueryResult:
    """Result from the query pipeline."""

    answer: str
    sources: List[RankedResult] = field(default_factory=list)
    tool_calls_made: int = 0


class QueryPipeline:
    """Orchestrates the full query flow with LLM tool calling."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the query pipeline.

        Args:
            config: Configuration object
        """
        self.config = config or default_config
        self.indexing_service = IndexingService(self.config)
        self.llm_service = LLMService(
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )
        self.reranker_service = RerankerService(
            model_name=self.config.reranker.model_name
        )

    def query(self, user_query: str, max_iterations: int = 5) -> QueryResult:
        """Execute a query through the pipeline.

        Args:
            user_query: The user's question
            max_iterations: Maximum number of LLM iterations to prevent infinite loops

        Returns:
            QueryResult with answer and sources
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]

        all_sources: List[RankedResult] = []
        tool_calls_made = 0

        # Agentic loop - LLM decides when to call tools
        for _ in range(max_iterations):
            response = self.llm_service.chat(messages)
            message = response.choices[0].message

            if message.tool_calls:
                # Add assistant message with tool calls
                messages.append(message.model_dump())

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_calls_made += 1
                    args = self._parse_tool_args(tool_call.function.arguments)
                    results = self._execute_search(args)
                    all_sources.extend(results)

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": self._format_results(results),
                    })
            else:
                # LLM has final answer
                break

        return QueryResult(
            answer=message.content or "",
            sources=all_sources,
            tool_calls_made=tool_calls_made,
        )

    def _parse_tool_args(self, arguments: str) -> SearchFedDocumentsArgs:
        """Parse tool call arguments into Pydantic model.

        Args:
            arguments: JSON string of arguments

        Returns:
            SearchFedDocumentsArgs model
        """
        args_dict = json.loads(arguments)
        return SearchFedDocumentsArgs(**args_dict)

    def _execute_search(self, args: SearchFedDocumentsArgs) -> List[RankedResult]:
        """Execute search and rerank results.

        Args:
            args: Search arguments from LLM tool call

        Returns:
            List of reranked results
        """
        logger.info(
            f"Searching: query='{args.query}', "
            f"speaker={args.speaker}, doc_type={args.doc_type}, "
            f"date_start={args.date_start}, date_end={args.date_end}"
        )

        # Hybrid search with filters
        results = self.indexing_service.search(
            query=args.query,
            doc_type=args.doc_type,
            speaker=args.speaker,
            date_start=args.date_start,
            date_end=args.date_end,
            limit=20,  # Fetch more for reranking
        )

        if not results:
            logger.info("No search results found")
            return []

        # Rerank and return top 5
        ranked = self.reranker_service.rerank(
            query=args.query,
            results=results,
            top_k=5,
        )

        logger.info(f"Reranked {len(results)} results, returning top {len(ranked)}")
        return ranked

    def _format_results(self, results: List[RankedResult]) -> str:
        """Format search results for LLM context.

        Args:
            results: List of reranked results

        Returns:
            Formatted string for LLM
        """
        if not results:
            return "No relevant documents found."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"[{i}] {r.title}\n"
                f"Type: {r.doc_type} | Date: {r.date}"
                + (f" | Speaker: {r.speaker}" if r.speaker else "")
                + f"\n{r.text}\n"
            )

        return "\n---\n".join(formatted)

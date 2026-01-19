"""Query pipeline orchestrating LLM, search, and reranking."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from ..config import Config, default_config
from .indexing import IndexingService
from .llm import LLMService, SearchFedDocumentsArgs
from .reranker import RankedResult, RerankerService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Today's date is {today}.

You are a research assistant for Federal Reserve policy documents. You have access to a search tool containing Fed speeches, FOMC statements, meeting minutes, and congressional testimony from 2015 to present.

IMPORTANT: You MUST use the search tool to answer questions. Do NOT rely on your training data for Fed-related information - your knowledge may be outdated. Base your answers ONLY on the search results returned.

When answering:
1. Always search first before answering
2. Think carefully about which filters best answer the question
3. Make multiple searches if needed - use iterative tool calls to refine and verify your results
4. Cite sources with speaker name, date, and document type
5. If no relevant results are found, say so honestly - do not make up information

Be thorough: make sure you are confident in your answer before responding. Don't hesitate to make multiple tool calls to refine your search or verify results. If a query requires the most recent data, verify you have found the newest content by searching with recent date filters.

Filters available:
- date_start / date_end: YYYY-MM-DD format
- speaker: Last name only (e.g., 'Powell', 'Waller')
- doc_type: 'speech', 'statement', 'minutes', or 'testimony'
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
            base_url=self.config.llm.base_url,
        )
        self.reranker_service = RerankerService(
            model_name=self.config.reranker.model_name
        )

    def query(
        self,
        user_query: str,
        history: list[dict] | None = None,
        max_iterations: int = 5,
    ) -> QueryResult:
        """Execute a query through the pipeline.

        Args:
            user_query: The user's question
            history: Previous conversation messages (role, content dicts)
            max_iterations: Maximum number of LLM iterations to prevent infinite loops

        Returns:
            QueryResult with answer and sources
        """
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today=date.today().isoformat())
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current query
        messages.append({"role": "user", "content": user_query})

        all_sources: List[RankedResult] = []
        tool_calls_made = 0
        total_llm_time = 0.0
        total_search_time = 0.0

        # Agentic loop - LLM decides when to call tools
        for _ in range(max_iterations):
            llm_start = time.time()
            response = self.llm_service.chat(messages)
            total_llm_time += time.time() - llm_start
            message = response.choices[0].message

            if message.tool_calls:
                # Add assistant message with tool calls
                messages.append(message.model_dump())

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_calls_made += 1
                    args = self._parse_tool_args(tool_call.function.arguments)

                    search_start = time.time()
                    results = self._execute_search(args)
                    total_search_time += time.time() - search_start

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

        logger.info(f"TIMING: LLM calls={total_llm_time:.2f}s, Search+Rerank={total_search_time:.2f}s")

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
        search_start = time.time()
        results = self.indexing_service.search(
            query=args.query,
            doc_type=args.doc_type,
            speaker=args.speaker,
            date_start=args.date_start,
            date_end=args.date_end,
            limit=20,  # Fetch more for reranking
        )
        search_time = time.time() - search_start

        if not results:
            logger.info("No search results found")
            return []

        # Rerank and return top 5
        rerank_start = time.time()
        ranked = self.reranker_service.rerank(
            query=args.query,
            results=results,
            top_k=5,
        )
        rerank_time = time.time() - rerank_start

        logger.info(f"TIMING: Search={search_time:.2f}s, Rerank={rerank_time:.2f}s (from {len(results)} to {len(ranked)})")
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

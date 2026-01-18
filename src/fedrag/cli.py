"""Command-line interface for Fed document scraper."""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import Config, default_config
from .scrapers.orchestrator import ScrapingOrchestrator
from .services.indexing import IndexingService

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="fedrag",
    help="Federal Reserve document collection system",
    add_completion=False,
)
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


@app.command()
def scrape(
    doc_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Document types to scrape (statement, minutes, speech, testimony). Can specify multiple.",
    ),
    start_year: Optional[int] = typer.Option(
        None,
        "--start-year",
        "-s",
        help="Start year for scraping (default: 2015)",
    ),
    end_year: Optional[int] = typer.Option(
        None,
        "--end-year",
        "-e",
        help="End year for scraping (default: current year)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Scrape Federal Reserve documents."""
    setup_logging(verbose)

    config = Config()

    # Validate doc types
    valid_types = {"statement", "minutes", "speech", "testimony"}
    if doc_types:
        for dt in doc_types:
            if dt not in valid_types:
                console.print(f"[red]Invalid document type: {dt}[/red]")
                console.print(f"Valid types: {', '.join(valid_types)}")
                raise typer.Exit(1)

    # Set defaults
    start = start_year or config.scraper.start_year
    end = end_year or datetime.now().year

    console.print(f"[bold]Fed Document Scraper[/bold]")
    console.print(f"Year range: {start} - {end}")
    if doc_types:
        console.print(f"Document types: {', '.join(doc_types)}")
    else:
        console.print("Document types: all")
    console.print()

    orchestrator = ScrapingOrchestrator(config)

    async def run_scrape():
        return await orchestrator.scrape_all(
            doc_types=doc_types,
            start_year=start,
            end_year=end,
        )

    try:
        results = asyncio.run(run_scrape())

        # Display results
        table = Table(title="Scraping Results")
        table.add_column("Document Type", style="cyan")
        table.add_column("Documents Scraped", justify="right", style="green")

        for doc_type, count in results.items():
            table.add_row(doc_type, str(count))

        table.add_row("", "")
        table.add_row("[bold]Total[/bold]", f"[bold]{sum(results.values())}[/bold]")

        console.print(table)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show statistics about stored documents."""
    config = Config()
    orchestrator = ScrapingOrchestrator(config)
    stats_data = orchestrator.get_stats()

    table = Table(title="Document Statistics")
    table.add_column("Document Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    total = 0
    for doc_type, count in stats_data.items():
        table.add_row(doc_type, str(count))
        total += count

    table.add_row("", "")
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

    console.print(table)


@app.command()
def list_docs(
    doc_type: str = typer.Argument(
        ...,
        help="Document type to list (statement, minutes, speech, testimony)",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of documents to show",
    ),
) -> None:
    """List stored documents of a given type."""
    from .storage.document_store import DocumentStore

    valid_types = {"statement", "minutes", "speech", "testimony"}
    if doc_type not in valid_types:
        console.print(f"[red]Invalid document type: {doc_type}[/red]")
        raise typer.Exit(1)

    config = Config()
    store = DocumentStore(config.storage)

    table = Table(title=f"{doc_type.title()} Documents")
    table.add_column("Date", style="cyan")
    table.add_column("Title", style="white", max_width=60)
    table.add_column("Speaker", style="yellow")

    count = 0
    for doc in store.load_documents(doc_type):
        if count >= limit:
            break
        table.add_row(
            str(doc.date),
            doc.title[:60] + "..." if len(doc.title) > 60 else doc.title,
            doc.speaker or "-",
        )
        count += 1

    if count == 0:
        console.print(f"[yellow]No {doc_type} documents found[/yellow]")
    else:
        console.print(table)
        total = store.count_documents(doc_type)
        if total > limit:
            console.print(f"[dim]Showing {limit} of {total} documents[/dim]")


@app.command()
def index(
    doc_types: Optional[List[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Document types to index (statement, minutes, speech, testimony). Can specify multiple.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Index documents to Qdrant vector database."""
    setup_logging(verbose)

    # Validate doc types
    valid_types = {"statement", "minutes", "speech", "testimony"}
    if doc_types:
        for dt in doc_types:
            if dt not in valid_types:
                console.print(f"[red]Invalid document type: {dt}[/red]")
                console.print(f"Valid types: {', '.join(valid_types)}")
                raise typer.Exit(1)

    console.print("[bold]Fed Document Indexer[/bold]")
    if doc_types:
        console.print(f"Document types: {', '.join(doc_types)}")
    else:
        console.print("Document types: all")
    console.print()

    try:
        config = Config()
        service = IndexingService(config)

        with console.status("[bold green]Indexing documents..."):
            results = service.index_documents(doc_types=doc_types)

        # Display results
        table = Table(title="Indexing Results")
        table.add_column("Document Type", style="cyan")
        table.add_column("New Documents", justify="right", style="green")

        for doc_type, count in results.items():
            table.add_row(doc_type, str(count))

        table.add_row("", "")
        table.add_row("[bold]Total[/bold]", f"[bold]{sum(results.values())}[/bold]")

        console.print(table)

        # Show total vectors
        stats = service.get_stats()
        console.print(
            f"\n[dim]Total vectors in database: {stats['total_vectors']}[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(
        ...,
        help="Search query text",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        "-n",
        help="Maximum number of results",
    ),
    doc_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by document type",
    ),
    speaker: Optional[str] = typer.Option(
        None,
        "--speaker",
        "-s",
        help="Filter by speaker name",
    ),
    date_start: Optional[str] = typer.Option(
        None,
        "--date-start",
        help="Filter by start date (YYYY-MM-DD)",
    ),
    date_end: Optional[str] = typer.Option(
        None,
        "--date-end",
        help="Filter by end date (YYYY-MM-DD)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Search indexed documents."""
    setup_logging(verbose)

    # Validate doc type
    valid_types = {"statement", "minutes", "speech", "testimony"}
    if doc_type and doc_type not in valid_types:
        console.print(f"[red]Invalid document type: {doc_type}[/red]")
        console.print(f"Valid types: {', '.join(valid_types)}")
        raise typer.Exit(1)

    try:
        config = Config()
        service = IndexingService(config)

        with console.status("[bold green]Searching..."):
            results = service.search(
                query=query,
                limit=limit,
                doc_type=doc_type,
                speaker=speaker,
                date_start=date_start,
                date_end=date_end,
            )

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        console.print(f"[bold]Search Results for:[/bold] {query}\n")

        for i, result in enumerate(results, 1):
            console.print(f"[bold cyan]{i}. {result.title}[/bold cyan]")
            console.print(f"   [dim]Type:[/dim] {result.doc_type} | "
                         f"[dim]Date:[/dim] {result.date} | "
                         f"[dim]Score:[/dim] {result.score:.3f}")
            if result.speaker:
                console.print(f"   [dim]Speaker:[/dim] {result.speaker}")

            # Show truncated text
            preview = result.text[:300].replace("\n", " ")
            if len(result.text) > 300:
                preview += "..."
            console.print(f"   {preview}\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def query(
    question: Optional[str] = typer.Argument(
        None,
        help="Question to ask about Federal Reserve communications",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    show_sources: bool = typer.Option(
        True,
        "--sources/--no-sources",
        help="Show source citations",
    ),
) -> None:
    """Ask questions about Federal Reserve communications."""
    from .services.query_pipeline import QueryPipeline

    setup_logging(verbose)

    try:
        config = Config()
        pipeline = QueryPipeline(config)

        if question:
            # Single question mode
            _run_query(pipeline, question, show_sources, verbose)
        else:
            # Interactive mode
            console.print("[bold]Fed RAG Query Interface[/bold]")
            console.print("Ask questions about Federal Reserve communications.")
            console.print("Type 'quit' or 'exit' to leave.\n")

            while True:
                try:
                    user_input = console.input("[bold cyan]Query:[/bold cyan] ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    console.print("[dim]Goodbye![/dim]")
                    break

                _run_query(pipeline, user_input, show_sources, verbose)
                console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _run_query(
    pipeline, question: str, show_sources: bool, verbose: bool = False
) -> None:
    """Execute a single query and display results."""
    with console.status("[bold green]Thinking..."):
        result = pipeline.query(question)

    console.print(f"\n[bold]Answer:[/bold]\n{result.answer}")

    if show_sources and result.sources:
        console.print("\n[bold]Sources:[/bold]")
        seen_docs = set()
        for source in result.sources:
            # Deduplicate by doc_id
            if source.doc_id in seen_docs:
                continue
            seen_docs.add(source.doc_id)

            console.print(
                f"  - [cyan]{source.title}[/cyan] "
                f"({source.doc_type}, {source.date}"
                + (f", {source.speaker}" if source.speaker else "")
                + ")"
            )

    if verbose:
        console.print(f"\n[dim]Tool calls: {result.tool_calls_made}[/dim]")


if __name__ == "__main__":
    app()

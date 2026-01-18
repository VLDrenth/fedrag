"""Command-line interface for Fed document scraper."""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .config import Config, default_config
from .scrapers.orchestrator import ScrapingOrchestrator

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


if __name__ == "__main__":
    app()

"""CLI tool for data management and analysis."""

import json
import sys
from pathlib import Path

import typer

from app.analysis.announcement_scraper import AnnouncementScraper
from app.analysis.data_loader import get_symbol_data_range, list_available_symbols

app = typer.Typer(
    name="peaches-analysis",
    help="Lightweight CLI tool for data management and analysis",
)
data_app = typer.Typer(name="data", help="Data management commands")
announcement_app = typer.Typer(name="announcements", help="ASX announcement scraping")

app.add_typer(data_app, name="data")
app.add_typer(announcement_app, name="announcements")


@data_app.command("list")
def list_symbols() -> None:
    """List all available symbols in the database."""
    symbols = list_available_symbols()

    if not symbols:
        typer.echo("No symbols found in database.")
        return

    typer.echo("Available symbols:")
    for symbol in symbols:
        range_info = get_symbol_data_range(symbol)
        if range_info:
            typer.echo(
                f"  {symbol}: {range_info['start']} to {range_info['end']} ({range_info['count']} bars)"
            )
        else:
            typer.echo(f"  {symbol}: No data range info")


@data_app.command("summary")
def symbol_summary(symbol: str) -> None:
    """Show detailed summary for a symbol."""
    range_info = get_symbol_data_range(symbol)

    if not range_info:
        typer.echo(f"No data found for symbol: {symbol}")
        raise typer.Exit(code=1)

    typer.echo(f"Symbol: {symbol}")
    typer.echo(f"Date Range: {range_info['start']} to {range_info['end']}")
    typer.echo(f"Total Bars: {range_info['count']}")


@announcement_app.command("get")
def get_announcements(
    ticker: str = typer.Argument(..., help="ASX ticker symbol"),
    period: str = typer.Option(
        "1M", help="Period: 1M, 3M, 6M, 1Y, YYYY, YYYY-MM, YYYY-MM-DD to YYYY-MM-DD"
    ),
    price_sensitive_only: bool = typer.Option(
        False, "--price-sensitive-only", "-p", help="Filter to price-sensitive only"
    ),
    output_format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json or table"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSON file"),  # noqa: B008
) -> None:
    """Get ASX announcements for a ticker."""
    scraper = AnnouncementScraper(timeout=30)
    start_date, end_date = scraper.parse_date_range(period)
    result = scraper.get_announcements(ticker, start_date, end_date)

    if not result.success:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(code=1)

    announcements = result.announcements
    if price_sensitive_only:
        announcements = [a for a in announcements if a.price_sensitive]

    if output_format == "table":
        _print_table(result.ticker, announcements)
    else:
        output_data = {
            "ticker": result.ticker,
            "period": {"start": result.period_start, "end": result.period_end},
            "count": len(announcements),
            "announcements": [a.model_dump() for a in announcements],
        }

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w") as f:
                json.dump(output_data, f, indent=2)
            typer.echo(f"Announcements saved to: {output}")
        else:
            typer.echo(json.dumps(output_data, indent=2))


def _print_table(ticker: str, announcements: list) -> None:
    """Print announcements in human-readable table format."""
    if not announcements:
        typer.echo(f"No announcements found for {ticker}.")
        return

    typer.echo(f"\nAnnouncements for {ticker} ({len(announcements)} results)\n")
    typer.echo(f"{'Date':<12} {'Time':<6} {'Sensitive':<10} {'Pages':<6} Headline")
    typer.echo("-" * 70)

    for ann in announcements:
        sensitive = "YES" if ann.price_sensitive else ""
        typer.echo(f"{ann.date:<12} {ann.time:<6} {sensitive:<10} {ann.pages:<6} {ann.headline}")


def cli() -> None:
    """Main CLI entry point."""
    app()

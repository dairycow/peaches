"""CLI tool for strategy backtesting and analysis."""

from datetime import datetime
from pathlib import Path

import typer
from loguru import logger

from app.analysis.backtest_engine import run_backtest
from app.analysis.data_loader import get_symbol_data_range, list_available_symbols
from app.analysis.results import ResultsExporter
from app.analysis.strategies.donchian_breakout import DonchianBreakoutStrategy
from app.config import config

app = typer.Typer(
    name="peaches-analysis",
    help="Lightweight CLI tool for strategy backtesting with daily data from data-prod/trading.db",
)
data_app = typer.Typer(name="data", help="Data management commands")
backtest_app = typer.Typer(name="backtest", help="Backtesting commands")

app.add_typer(data_app, name="data")
app.add_typer(backtest_app, name="backtest")


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
    """Show detailed summary for a symbol.

    Args:
        symbol: Trading symbol (e.g., "BHP")
    """
    range_info = get_symbol_data_range(symbol)

    if not range_info:
        typer.echo(f"No data found for symbol: {symbol}")
        raise typer.Exit(code=1)

    typer.echo(f"Symbol: {symbol}")
    typer.echo(f"Date Range: {range_info['start']} to {range_info['end']}")
    typer.echo(f"Total Bars: {range_info['count']}")


@backtest_app.command("run")
def run_backtest_command(
    symbol: str = typer.Argument(..., help="Trading symbol (e.g., BHP)"),
    strategy: str = typer.Option("donchian_breakout", help="Strategy name"),
    start_date: str = typer.Option(..., help="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="End date (ISO format: YYYY-MM-DD)"),
    channel_period: int = typer.Option(20, help="Donchian channel period"),
    stop_loss_pct: float = typer.Option(0.02, help="Stop loss percentage"),
    take_profit_pct: float = typer.Option(0.04, help="Take profit percentage"),
    risk_per_trade: float = typer.Option(0.02, help="Risk per trade percentage"),
    capital: float = typer.Option(None, help="Initial capital (default from config)"),
    output_dir: Path | None = typer.Option(None, help="Output directory"),  # noqa: B008
) -> None:
    """Run a single backtest.

    Args:
        symbol: Trading symbol (e.g., BHP)
        strategy: Strategy name
        start_date: Start date (ISO format: YYYY-MM-DD)
        end_date: End date (ISO format: YYYY-MM-DD)
        channel_period: Donchian channel period
        stop_loss_pct: Stop loss percentage
        take_profit_pct: Take profit percentage
        risk_per_trade: Risk per trade percentage
        capital: Initial capital (default from config)
        output: Output directory
    """
    if strategy != "donchian_breakout":
        typer.echo(f"Strategy '{strategy}' not implemented yet.")
        raise typer.Exit(code=1)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        typer.echo(f"Invalid date format: {e}")
        typer.echo("Use ISO format: YYYY-MM-DD")
        raise typer.Exit(code=1)  # noqa: B904

    if capital is None:
        capital = config.analysis.default_capital

    strategy_params: dict[str, float | str] = {
        "strategy_name": strategy,
        "channel_period": channel_period,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "risk_per_trade": risk_per_trade,
    }

    typer.echo(f"Running backtest: {symbol} - {strategy}")
    typer.echo(f"Period: {start_date} to {end_date}")
    typer.echo(f"Capital: ${capital:,.2f}")
    typer.echo("")

    try:
        result = run_backtest(
            symbol=symbol,
            strategy_class=DonchianBreakoutStrategy,
            strategy_params=strategy_params,
            start_date=start_dt,
            end_date=end_dt,
            capital=capital,
        )

        typer.echo(ResultsExporter.format_summary(result))

        if output_dir:
            output_path = Path(output_dir) / f"{symbol}_{strategy}_{start_date}_{end_date}"
            ResultsExporter.export_all(result, output_path)
            typer.echo("")
            typer.echo(f"Results exported to: {output_path}")

    except ValueError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)  # noqa: B904
    except Exception as e:
        logger.exception("Unexpected error during backtest")
        typer.echo(f"Unexpected error: {e}")
        raise typer.Exit(code=1)  # noqa: B904


@backtest_app.command("batch")
def run_batch_backtest(
    symbols: str = typer.Argument(..., help="Comma-separated symbols (e.g., BHP,CBA,RIO)"),
    strategy: str = typer.Option("donchian_breakout", help="Strategy name"),
    start_date: str = typer.Option(..., help="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="End date (ISO format: YYYY-MM-DD)"),
    channel_period: int = typer.Option(20, help="Donchian channel period"),
    stop_loss_pct: float = typer.Option(0.02, help="Stop loss percentage"),
    take_profit_pct: float = typer.Option(0.04, help="Take profit percentage"),
    risk_per_trade: float = typer.Option(0.02, help="Risk per trade percentage"),
    capital: float = typer.Option(None, help="Initial capital (default from config)"),
    output_dir: Path | None = typer.Option(None, help="Output directory"),  # noqa: B008
) -> None:
    """Run backtests for multiple symbols.

    Args:
        symbols: Comma-separated symbols (e.g., BHP,CBA,RIO)
        strategy: Strategy name
        start_date: Start date (ISO format: YYYY-MM-DD)
        end_date: End date (ISO format: YYYY-MM-DD)
        channel_period: Donchian channel period
        stop_loss_pct: Stop loss percentage
        take_profit_pct: Take profit percentage
        risk_per_trade: Risk per trade percentage
        capital: Initial capital (default from config)
        output: Output directory
    """
    if strategy != "donchian_breakout":
        typer.echo(f"Strategy '{strategy}' not implemented yet.")
        raise typer.Exit(code=1)

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        typer.echo(f"Invalid date format: {e}")
        typer.echo("Use ISO format: YYYY-MM-DD")
        raise typer.Exit(code=1)  # noqa: B904

    if capital is None:
        capital = config.analysis.default_capital

    if output_dir is None:
        output_dir = Path(config.analysis.output_dir)

    symbol_list = [s.strip().upper() for s in symbols.split(",")]

    typer.echo(f"Running batch backtest for {len(symbol_list)} symbols")
    typer.echo(f"Period: {start_date} to {end_date}")
    typer.echo(f"Capital: ${capital:,.2f}")
    typer.echo("")

    strategy_params: dict[str, float | str] = {
        "strategy_name": strategy,
        "channel_period": channel_period,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "risk_per_trade": risk_per_trade,
    }

    results_summary = []

    for symbol in symbol_list:
        typer.echo(f"Processing {symbol}...", nl=False)

        try:
            result = run_backtest(
                symbol=symbol,
                strategy_class=DonchianBreakoutStrategy,
                strategy_params=strategy_params,
                start_date=start_dt,
                end_date=end_dt,
                capital=capital,
            )

            results_summary.append(
                {
                    "symbol": symbol,
                    "total_return": result.metrics["total_return"],
                    "sharpe_ratio": result.metrics["sharpe_ratio"],
                    "max_drawdown": result.metrics["max_drawdown"],
                    "total_trades": result.metrics["total_trades"],
                }
            )

            typer.echo(
                f" ✓ (Return: {result.metrics['total_return']:.2%}, Sharpe: {result.metrics['sharpe_ratio']:.2f})"
            )

            if output_dir:
                output_path = output_dir / f"{symbol}_{strategy}_{start_date}_{end_date}"
                ResultsExporter.export_all(result, output_path)

        except ValueError as e:
            logger.warning(f"Value error for {symbol}: {e}")
            typer.echo(f" ✗ (Error: {e})")
        except Exception as e:
            logger.exception(f"Unexpected error for {symbol}")
            typer.echo(f" ✗ (Error: {e})")

    typer.echo("")
    typer.echo("Batch Summary:")
    typer.echo("-" * 80)

    import polars as pl

    df = pl.DataFrame(results_summary)
    if not df.is_empty():
        typer.echo(
            df.sort("total_return", descending=True).with_columns(
                pl.col("total_return").map_elements(lambda x: f"{x:.2%}"),
                pl.col("max_drawdown").map_elements(lambda x: f"{x:.2%}"),
            )
        )


def cli() -> None:
    """Main CLI entry point."""
    app()

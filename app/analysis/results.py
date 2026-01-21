"""Result formatting and export for backtesting outputs."""

import json
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel, Field


class TradeData(BaseModel):
    """Individual trade data."""

    entry_time: str = Field(description="Entry time ISO format")
    exit_time: str = Field(description="Exit time ISO format")
    entry_price: float = Field(description="Entry price")
    exit_price: float = Field(description="Exit price")
    quantity: int = Field(description="Trade quantity")
    pnl: float = Field(description="Profit/loss")


class EquityPoint(BaseModel):
    """Equity curve data point."""

    date: str = Field(description="Date ISO format")
    value: float = Field(description="Portfolio value")
    drawdown: float = Field(description="Drawdown percentage")


class BacktestResult(BaseModel):
    """Complete backtest result."""

    symbol: str = Field(description="Trading symbol")
    strategy: str = Field(description="Strategy name")
    period: dict[str, str] = Field(description="Backtest period")
    parameters: dict[str, Any] = Field(description="Strategy parameters")
    initial_capital: float = Field(description="Initial capital")
    final_capital: float = Field(description="Final capital")
    metrics: dict[str, float] = Field(description="Performance metrics")
    trades: list[TradeData] = Field(description="Trade list")
    equity_curve: list[EquityPoint] = Field(description="Equity curve")


class ResultsExporter:
    """Export backtest results to JSON and CSV formats."""

    @staticmethod
    def export_json(result: BacktestResult, output_path: Path) -> None:
        """Export result to JSON file.

        Args:
            result: Backtest result object
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    @staticmethod
    def export_csv(result: BacktestResult, output_dir: Path) -> None:
        """Export result to CSV files.

        Args:
            result: Backtest result object
            output_dir: Output directory path
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        trades_data = [t.model_dump() for t in result.trades]
        equity_data = [e.model_dump() for e in result.equity_curve]

        if trades_data:
            trades_df = pl.DataFrame(trades_data)
            trades_df.write_csv(output_dir / "trades.csv")

        if equity_data:
            equity_df = pl.DataFrame(equity_data)
            equity_df.write_csv(output_dir / "equity.csv")

    @staticmethod
    def export_all(result: BacktestResult, output_dir: Path) -> None:
        """Export result to all formats.

        Args:
            result: Backtest result object
            output_dir: Output directory path
        """
        ResultsExporter.export_json(result, output_dir / "result.json")
        ResultsExporter.export_csv(result, output_dir)

    @staticmethod
    def format_summary(result: BacktestResult) -> str:
        """Format result summary for console output.

        Args:
            result: Backtest result object

        Returns:
            Formatted summary string
        """
        lines = [
            f"Backtest Result: {result.symbol} - {result.strategy}",
            f"Period: {result.period['start']} to {result.period['end']}",
            "",
            "Parameters:",
            *[f"  {k}: {v}" for k, v in result.parameters.items()],
            "",
            "Performance:",
            f"  Total Return: {result.metrics['total_return']:.2%}",
            f"  CAGR: {result.metrics['cagr']:.2%}",
            f"  Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}",
            f"  Max Drawdown: {result.metrics['max_drawdown']:.2%}",
            f"  Calmar Ratio: {result.metrics['calmar_ratio']:.2f}",
            "",
            "Trading:",
            f"  Total Trades: {result.metrics['total_trades']}",
            f"  Win Rate: {result.metrics['win_rate']:.2%}",
            f"  Avg Win: ${result.metrics['avg_win']:.2f}",
            f"  Avg Loss: ${result.metrics['avg_loss']:.2f}",
            f"  Profit Factor: {result.metrics['profit_factor']:.2f}",
            "",
            f"Capital: ${result.initial_capital:,.2f} -> ${result.final_capital:,.2f}",
        ]
        return "\n".join(lines)

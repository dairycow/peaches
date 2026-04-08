"""Simple event-driven backtest engine."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.analysis.data_loader import load_bars
from app.analysis.metrics import MetricsCalculator
from app.analysis.results import BacktestResult, EquityPoint, ResultsExporter, TradeData
from app.analysis.types import BarData

if TYPE_CHECKING:
    from app.analysis.strategies.donchian_breakout import DonchianBreakoutStrategy


class BacktestPortfolio:
    """Tracks portfolio state during backtesting."""

    def __init__(self, capital: float, commission_rate: float, fixed_commission: float) -> None:
        self.capital = capital
        self.commission_rate = commission_rate
        self.fixed_commission = fixed_commission

        self.position: int = 0
        self.entry_price: float = 0.0
        self.equity = capital
        self.peak_equity = capital
        self.daily_pnl: list[tuple[datetime, float]] = []
        self.trades: list[dict[str, Any]] = []

    def buy(self, price: float, size: int, bar: BarData) -> None:
        cost = price * size
        commission = cost * self.commission_rate + self.fixed_commission
        self.equity -= commission
        self.position += size
        if self.entry_price == 0:
            self.entry_price = price
        logger.debug(f"BUY {size} @ {price:.2f} on {bar.datetime.date()}")

    def sell(self, price: float, size: int, bar: BarData) -> None:
        size = min(size, self.position)
        if size <= 0:
            return
        proceeds = price * size
        commission = proceeds * self.commission_rate + self.fixed_commission
        self.equity -= commission

        pnl = (price - self.entry_price) * size - self.fixed_commission * 2
        self.trades.append(
            {
                "entry_time": bar.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": bar.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "entry_price": self.entry_price,
                "exit_price": price,
                "quantity": size,
                "pnl": float(pnl),
            }
        )

        self.equity += pnl
        self.position = 0
        self.entry_price = 0.0
        logger.debug(f"SELL {size} @ {price:.2f} on {bar.datetime.date()} (PnL: {pnl:.2f})")

    def mark_to_market(self, bar: BarData) -> None:
        unrealised = self.position * bar.close_price
        total = self.equity + unrealised
        pnl = total - self.capital
        self.daily_pnl.append((bar.datetime, pnl))
        if total > self.peak_equity:
            self.peak_equity = total

    @property
    def final_equity(self) -> float:
        return self.equity


class CtaEngine:
    """Minimal CTA engine stub for strategy compatibility."""

    def __init__(self, portfolio: BacktestPortfolio, capital: float) -> None:
        self.portfolio = portfolio
        self.capital = capital
        self.current_bar: BarData | None = None

    def buy(self, price: float, volume: float, stop: bool = False) -> None:  # noqa: ARG002
        if self.current_bar:
            self.portfolio.buy(price, int(volume), self.current_bar)

    def sell(self, price: float, volume: float, stop: bool = False) -> None:  # noqa: ARG002
        if self.current_bar:
            self.portfolio.sell(price, int(volume), self.current_bar)

    def write_log(self, msg: str) -> None:
        logger.debug(msg)


def run_strategy_backtest(
    strategy: DonchianBreakoutStrategy,
    bars: list[BarData],
    capital: float,
    commission_rate: float,
    fixed_commission: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[datetime, float]]]:
    """Run a strategy against bar data.

    Returns:
        (trades, equity_points, daily_pnl)
    """
    portfolio = BacktestPortfolio(capital, commission_rate, fixed_commission)
    cta_engine = CtaEngine(portfolio, capital)

    strategy.on_init()
    strategy.on_start()

    for bar in bars:
        cta_engine.current_bar = bar
        strategy.on_bar(bar)

    strategy.on_stop()

    equity_curve = _build_equity_curve(portfolio, bars, capital)
    return portfolio.trades, equity_curve, portfolio.daily_pnl


def _build_equity_curve(
    portfolio: BacktestPortfolio, bars: list[BarData], capital: float
) -> list[dict[str, Any]]:
    cumulative_pnl = {}
    running = 0.0
    for dt, pnl in portfolio.daily_pnl:
        running += pnl
        cumulative_pnl[dt.date()] = running

    curve: list[dict[str, Any]] = []
    peak = capital

    for bar in bars:
        date = bar.datetime.date()
        if date in cumulative_pnl:
            value = capital + cumulative_pnl[date]
            peak = max(peak, value)
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            curve.append(
                {
                    "date": bar.datetime.strftime("%Y-%m-%d"),
                    "value": float(value),
                    "drawdown": float(drawdown),
                }
            )
        elif curve:
            curve.append(
                {
                    "date": bar.datetime.strftime("%Y-%m-%d"),
                    "value": float(curve[-1]["value"]),
                    "drawdown": 0.0,
                }
            )

    return curve


def run_backtest(
    symbol: str,
    strategy_class: type[DonchianBreakoutStrategy],
    strategy_params: dict[str, float | str],
    start_date: datetime,
    end_date: datetime,
    capital: float = 1_000_000,
    output_dir: Path | None = None,
) -> BacktestResult:
    """Run backtest and optionally export results.

    Args:
        symbol: Trading symbol
        strategy_class: Strategy class
        strategy_params: Strategy parameters
        start_date: Start date
        end_date: End date
        capital: Initial capital
        output_dir: Optional output directory

    Returns:
        BacktestResult object
    """
    from app.config import config

    commission_rate = config.analysis.commission_rate
    fixed_commission = config.analysis.fixed_commission

    bars = load_bars(symbol, start_date, end_date)

    if not bars:
        raise ValueError(f"No data found for {symbol} in specified date range")

    strategy = strategy_class(
        cta_engine=None,
        strategy_name=str(strategy_params.get("strategy_name", strategy_class.__name__)),
        vt_symbol=f"{symbol}.LOCAL",
        setting=strategy_params,
    )

    trades, equity_curve, _ = run_strategy_backtest(
        strategy, bars, capital, commission_rate, fixed_commission
    )

    metrics = MetricsCalculator.calculate_metrics(trades, equity_curve, capital)

    result = BacktestResult(
        symbol=symbol,
        strategy=str(strategy_params.get("strategy_name", strategy_class.__name__)),
        period={
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        },
        parameters=strategy_params,
        initial_capital=capital,
        final_capital=capital * (1 + metrics.get("total_return", 0)),
        metrics=metrics,
        trades=[TradeData(**t) for t in trades],  # type: ignore[arg-type]
        equity_curve=[EquityPoint(**e) for e in equity_curve],  # type: ignore[arg-type]
    )

    if output_dir:
        ResultsExporter.export_all(result, output_dir)

    return result

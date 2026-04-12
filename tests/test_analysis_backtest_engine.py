"""Tests for backtest engine module."""

from datetime import date, datetime

import pytest

from app.analysis.backtest_engine import BacktestPortfolio, run_strategy_backtest
from app.analysis.strategies.donchian_breakout import DonchianBreakoutStrategy
from app.analysis.types import BarData, Exchange, Interval


def _make_bar(
    symbol: str = "TEST",
    dt: datetime | None = None,
    open_price: float = 100.0,
    high_price: float = 105.0,
    low_price: float = 95.0,
    close_price: float = 100.0,
    volume: float = 1000.0,
) -> BarData:
    return BarData(
        symbol=symbol,
        exchange=Exchange.LOCAL,
        interval=Interval.DAILY,
        datetime=dt or datetime(2024, 1, 1),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        volume=volume,
    )


def test_backtest_portfolio_initialization():
    """Test BacktestPortfolio initialization."""
    portfolio = BacktestPortfolio(
        capital=1_000_000,
        commission_rate=0.001,
        fixed_commission=6.6,
    )

    assert portfolio.capital == 1_000_000
    assert portfolio.commission_rate == 0.001
    assert portfolio.fixed_commission == 6.6
    assert portfolio.position == 0
    assert portfolio.entry_price == 0.0


def test_portfolio_buy():
    """Test portfolio buy operation."""
    portfolio = BacktestPortfolio(capital=1_000_000, commission_rate=0.001, fixed_commission=6.6)
    bar = _make_bar()

    portfolio.buy(100.0, 10, bar)

    assert portfolio.position == 10
    assert portfolio.entry_price == 100.0


def test_portfolio_sell():
    """Test portfolio sell with PnL calculation."""
    portfolio = BacktestPortfolio(capital=1_000_000, commission_rate=0.001, fixed_commission=6.6)
    bar_buy = _make_bar(close_price=100.0)
    bar_sell = _make_bar(dt=datetime(2024, 1, 2), close_price=110.0)

    portfolio.buy(100.0, 10, bar_buy)
    portfolio.sell(110.0, 10, bar_sell)

    assert portfolio.position == 0
    assert len(portfolio.trades) == 1
    assert portfolio.trades[0]["pnl"] > 0


def test_portfolio_mark_to_market():
    """Test mark to market calculation."""
    portfolio = BacktestPortfolio(capital=1_000_000, commission_rate=0.001, fixed_commission=6.6)
    bar = _make_bar(close_price=100.0)

    portfolio.buy(100.0, 10, bar)
    bar2 = _make_bar(dt=datetime(2024, 1, 2), close_price=110.0)
    portfolio.mark_to_market(bar2)

    assert len(portfolio.daily_pnl) == 1


def test_run_strategy_backtest_basic():
    """Test run_strategy_backtest with basic strategy."""
    bars = [_make_bar(dt=datetime(2024, 1, i), close_price=100.0 + i) for i in range(1, 30)]

    strategy = DonchianBreakoutStrategy(
        cta_engine=None,
        strategy_name="test",
        vt_symbol="TEST.LOCAL",
        setting={"channel_period": 5, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    )

    trades, equity_curve, daily_pnl = run_strategy_backtest(
        strategy,
        bars,
        capital=1_000_000,
        commission_rate=0.001,
        fixed_commission=6.6,
    )

    assert isinstance(trades, list)
    assert isinstance(equity_curve, list)
    assert isinstance(daily_pnl, list)

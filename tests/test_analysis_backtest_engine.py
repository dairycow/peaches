"""Tests for backtest engine module."""

from datetime import datetime, date

import pandas as pd
import pytest
from vnpy.trader.constant import Direction, Exchange, Interval, Offset
from vnpy.trader.object import BarData, TradeData as VnpyTradeData

from app.analysis.backtest_engine import BacktestEngineWrapper


def test_backtest_engine_wrapper_initialization():
    """Test BacktestEngineWrapper initialization."""
    engine = BacktestEngineWrapper(
        capital=1_000_000,
        commission_rate=0.001,
        fixed_commission=6.6,
        slippage=0.02,
    )

    assert engine.capital == 1_000_000
    assert engine.commission_rate == 0.001
    assert engine.fixed_commission == 6.6
    assert engine.slippage == 0.02


def test_build_equity_curve_empty_daily_results():
    """Test _build_equity_curve with empty daily results."""
    engine = BacktestEngineWrapper()
    daily_results_df = None

    bars = []
    equity_curve = engine._build_equity_curve(daily_results_df, bars)

    assert equity_curve == []


def test_build_equity_curve_basic():
    """Test _build_equity_curve with basic data."""
    engine = BacktestEngineWrapper(capital=1_000_000)

    daily_results_df = pd.DataFrame(
        {"net_pnl": [100, 200, -50], "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]}
    ).set_index("date")

    dt2 = datetime.combine(date(2024, 1, 2), datetime.min.time())
    dt3 = datetime.combine(date(2024, 1, 3), datetime.min.time())
    dt4 = datetime.combine(date(2024, 1, 4), datetime.min.time())

    bars = [
        BarData(
            symbol="TEST",
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
            datetime=dt2,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=100.0,
            volume=1000,
            gateway_name="",
        ),
        BarData(
            symbol="TEST",
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
            datetime=dt3,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=100.0,
            volume=1000,
            gateway_name="",
        ),
        BarData(
            symbol="TEST",
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
            datetime=dt4,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=100.0,
            volume=1000,
            gateway_name="",
        ),
    ]

    equity_curve = engine._build_equity_curve(daily_results_df, bars)

    assert len(equity_curve) == 3
    assert equity_curve[0]["value"] == 1_000_100.0
    assert equity_curve[1]["value"] == 1_000_300.0
    assert equity_curve[2]["value"] == 1_000_250.0


def test_build_equity_curve_drawdown_calculation():
    """Test drawdown calculation in _build_equity_curve."""
    engine = BacktestEngineWrapper(capital=1_000_000)

    daily_results_df = pd.DataFrame(
        {"net_pnl": [100000, -200000], "date": [date(2024, 1, 2), date(2024, 1, 3)]}
    ).set_index("date")

    dt2 = datetime.combine(date(2024, 1, 2), datetime.min.time())
    dt3 = datetime.combine(date(2024, 1, 3), datetime.min.time())

    bars = [
        BarData(
            symbol="TEST",
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
            datetime=dt2,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=100.0,
            volume=1000,
            gateway_name="",
        ),
        BarData(
            symbol="TEST",
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
            datetime=dt3,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=100.0,
            volume=1000,
            gateway_name="",
        ),
    ]

    equity_curve = engine._build_equity_curve(daily_results_df, bars)

    assert len(equity_curve) == 2
    assert equity_curve[0]["drawdown"] == 0.0
    assert equity_curve[1]["drawdown"] == pytest.approx((1_100_000 - 900_000) / 1_100_000, rel=1e-4)


def test_build_trade_list_empty():
    """Test _build_trade_list with empty vnpy_trades."""
    engine = BacktestEngineWrapper()
    vnpy_trades = []

    trades = engine._build_trade_list(vnpy_trades)

    assert trades == []


def test_build_trade_list_basic():
    """Test _build_trade_list with basic trades."""
    engine = BacktestEngineWrapper()

    buy_trade = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="1",
        tradeid="1",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=100.0,
        volume=100.0,
        datetime=datetime(2024, 1, 1, 10, 0, 0),
    )

    sell_trade = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="2",
        tradeid="2",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=105.0,
        volume=100.0,
        datetime=datetime(2024, 1, 5, 14, 0, 0),
    )

    vnpy_trades = [buy_trade, sell_trade]

    trades = engine._build_trade_list(vnpy_trades)

    assert len(trades) == 1
    assert trades[0]["entry_price"] == 100.0
    assert trades[0]["exit_price"] == 105.0
    assert trades[0]["quantity"] == 100
    assert trades[0]["pnl"] == pytest.approx((105.0 - 100.0) * 100 - 6.6 * 2, rel=1e-4)


def test_build_trade_list_partial_fills():
    """Test _build_trade_list with partial fills."""
    engine = BacktestEngineWrapper()

    buy_trade1 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="1",
        tradeid="1",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=100.0,
        volume=100.0,
        datetime=datetime(2024, 1, 1, 10, 0, 0),
    )

    buy_trade2 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="2",
        tradeid="2",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=101.0,
        volume=50.0,
        datetime=datetime(2024, 1, 2, 10, 0, 0),
    )

    sell_trade1 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="3",
        tradeid="3",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=105.0,
        volume=120.0,
        datetime=datetime(2024, 1, 5, 14, 0, 0),
    )

    sell_trade2 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="4",
        tradeid="4",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=103.0,
        volume=30.0,
        datetime=datetime(2024, 1, 6, 14, 0, 0),
    )

    vnpy_trades = [buy_trade1, buy_trade2, sell_trade1, sell_trade2]

    trades = engine._build_trade_list(vnpy_trades)

    assert len(trades) == 3

    assert trades[0]["quantity"] == 100
    assert trades[0]["entry_price"] == 100.0
    assert trades[0]["exit_price"] == 105.0

    assert trades[1]["quantity"] == 20
    assert trades[1]["entry_price"] == 101.0
    assert trades[1]["exit_price"] == 105.0

    assert trades[2]["quantity"] == 30
    assert trades[2]["entry_price"] == 101.0
    assert trades[2]["exit_price"] == 103.0


def test_build_trade_list_multiple_exits():
    """Test _build_trade_list with multiple exit trades."""
    engine = BacktestEngineWrapper()

    buy_trade = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="1",
        tradeid="1",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        price=100.0,
        volume=100.0,
        datetime=datetime(2024, 1, 1, 10, 0, 0),
    )

    sell_trade1 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="2",
        tradeid="2",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=105.0,
        volume=50.0,
        datetime=datetime(2024, 1, 5, 14, 0, 0),
    )

    sell_trade2 = VnpyTradeData(
        gateway_name="TEST",
        symbol="TEST",
        exchange=Exchange.LOCAL,
        orderid="3",
        tradeid="3",
        direction=Direction.SHORT,
        offset=Offset.CLOSE,
        price=103.0,
        volume=50.0,
        datetime=datetime(2024, 1, 6, 14, 0, 0),
    )

    vnpy_trades = [buy_trade, sell_trade1, sell_trade2]

    trades = engine._build_trade_list(vnpy_trades)

    assert len(trades) == 2

    assert trades[0]["quantity"] == 50
    assert trades[0]["entry_price"] == 100.0
    assert trades[0]["exit_price"] == 105.0

    assert trades[1]["quantity"] == 50
    assert trades[1]["entry_price"] == 100.0
    assert trades[1]["exit_price"] == 103.0

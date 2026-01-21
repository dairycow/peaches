"""Tests for analysis metrics module."""

import polars as pl
import pytest

from app.analysis.metrics import MetricsCalculator


def test_calculate_metrics_empty_trades():
    """Test metrics calculation with empty trades list."""
    trades = []
    equity_curve = []

    metrics = MetricsCalculator.calculate_metrics(trades, equity_curve, 1_000_000)

    assert metrics["total_return"] == 0.0
    assert metrics["cagr"] == 0.0
    assert metrics["sharpe_ratio"] == 0.0
    assert metrics["sortino_ratio"] == 0.0
    assert metrics["max_drawdown"] == 0.0
    assert metrics["calmar_ratio"] == 0.0
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["avg_win"] == 0.0
    assert metrics["avg_loss"] == 0.0
    assert metrics["profit_factor"] == 0.0


def test_calculate_metrics_profitable():
    """Test metrics calculation with profitable trades."""
    trades = [
        {"pnl": 1000},
        {"pnl": 500},
        {"pnl": -200},
        {"pnl": 800},
    ]

    equity_curve = [
        {"date": "2024-01-01", "value": 1_000_000},
        {"date": "2024-01-02", "value": 1_001_000},
        {"date": "2024-01-03", "value": 1_001_500},
        {"date": "2024-01-04", "value": 1_001_300},
        {"date": "2024-01-05", "value": 1_002_100},
    ]

    metrics = MetricsCalculator.calculate_metrics(trades, equity_curve, 1_000_000)

    assert metrics["total_return"] == pytest.approx(0.0021, rel=1e-4)
    assert metrics["total_trades"] == 4
    assert metrics["win_rate"] == 0.75
    assert metrics["avg_win"] == pytest.approx(766.67, rel=1e-4)
    assert metrics["avg_loss"] == -200
    assert metrics["profit_factor"] == pytest.approx(11.5, rel=1e-4)


def test_calculate_drawdown_metrics():
    """Test drawdown calculation."""
    equity_curve = pl.DataFrame(
        [
            {"date": "2024-01-01", "value": 1000},
            {"date": "2024-01-02", "value": 1100},
            {"date": "2024-01-03", "value": 1050},
            {"date": "2024-01-04", "value": 900},
            {"date": "2024-01-05", "value": 1200},
        ]
    )

    metrics = MetricsCalculator._calculate_drawdown_metrics(equity_curve)

    assert metrics["max_drawdown"] == pytest.approx((1100 - 900) / 1100, rel=1e-4)
    assert metrics["calmar_ratio"] > 0


def test_calculate_drawdown_metrics_empty():
    """Test drawdown calculation with empty data."""
    equity_curve = pl.DataFrame()

    metrics = MetricsCalculator._calculate_drawdown_metrics(equity_curve)

    assert metrics["max_drawdown"] == 0.0
    assert metrics["calmar_ratio"] == 0.0


def test_calculate_return_metrics():
    """Test return-based metrics calculation."""
    equity_curve = pl.DataFrame(
        [
            {"date": "2024-01-01", "value": 1000},
            {"date": "2024-01-02", "value": 1010},
            {"date": "2024-01-03", "value": 1020},
        ]
    )

    metrics = MetricsCalculator._calculate_return_metrics(equity_curve, 1000)

    assert "cagr" in metrics
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "volatility" in metrics
    assert metrics["cagr"] > 0


def test_calculate_return_metrics_insufficient_data():
    """Test return metrics with insufficient data."""
    equity_curve = pl.DataFrame([{"date": "2024-01-01", "value": 1000}])

    metrics = MetricsCalculator._calculate_return_metrics(equity_curve, 1000)

    assert metrics["cagr"] == 0.0
    assert metrics["sharpe_ratio"] == 0.0
    assert metrics["sortino_ratio"] == 0.0
    assert metrics["volatility"] == 0.0


def test_calculate_trade_metrics():
    """Test trade-based metrics calculation."""
    trades_df = pl.DataFrame(
        [
            {"pnl": 1000},
            {"pnl": 500},
            {"pnl": -200},
            {"pnl": 800},
            {"pnl": -300},
        ]
    )

    metrics = MetricsCalculator._calculate_trade_metrics(trades_df)

    assert metrics["win_rate"] == 0.6
    assert metrics["avg_win"] == pytest.approx(766.67, rel=1e-4)
    assert metrics["avg_loss"] == -250
    assert metrics["profit_factor"] == pytest.approx(4.6, rel=1e-4)


def test_calculate_trade_metrics_empty():
    """Test trade metrics with empty data."""
    trades_df = pl.DataFrame()

    metrics = MetricsCalculator._calculate_trade_metrics(trades_df)

    assert metrics["win_rate"] == 0.0
    assert metrics["avg_win"] == 0.0
    assert metrics["avg_loss"] == 0.0
    assert metrics["profit_factor"] == 0.0
    assert metrics["avg_trade"] == 0.0


def test_profit_factor_all_losses():
    """Test profit factor with only losing trades."""
    trades_df = pl.DataFrame([{"pnl": -100}, {"pnl": -200}])

    metrics = MetricsCalculator._calculate_trade_metrics(trades_df)

    assert metrics["profit_factor"] == 0.0
    assert metrics["avg_win"] == 0.0
    assert metrics["avg_loss"] == -150


def test_profit_factor_all_wins():
    """Test profit factor with only winning trades."""
    trades_df = pl.DataFrame([{"pnl": 100}, {"pnl": 200}])

    metrics = MetricsCalculator._calculate_trade_metrics(trades_df)

    assert metrics["profit_factor"] == float("inf")
    assert metrics["avg_win"] == 150
    assert metrics["avg_loss"] == 0.0

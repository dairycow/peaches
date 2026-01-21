"""Tests for analysis results module."""

from app.analysis.results import BacktestResult, EquityPoint, ResultsExporter, TradeData


def test_trade_data_creation():
    """Test TradeData model creation."""
    trade = TradeData(
        entry_time="2024-01-01 10:00:00",
        exit_time="2024-01-05 14:00:00",
        entry_price=100.0,
        exit_price=105.0,
        quantity=100,
        pnl=500.0,
    )

    assert trade.entry_time == "2024-01-01 10:00:00"
    assert trade.exit_price == 105.0
    assert trade.quantity == 100
    assert trade.pnl == 500.0


def test_equity_point_creation():
    """Test EquityPoint model creation."""
    point = EquityPoint(
        date="2024-01-01",
        value=1_000_000.0,
        drawdown=0.05,
    )

    assert point.date == "2024-01-01"
    assert point.value == 1_000_000.0
    assert point.drawdown == 0.05


def test_backtest_result_creation():
    """Test BacktestResult model creation."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={"total_return": 0.1},
        trades=[],
        equity_curve=[],
    )

    assert result.symbol == "BHP"
    assert result.initial_capital == 1_000_000.0
    assert result.final_capital == 1_100_000.0
    assert result.metrics["total_return"] == 0.1


def test_export_json(tmp_path):
    """Test JSON export functionality."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={"total_return": 0.1},
        trades=[
            TradeData(
                entry_time="2024-01-01 10:00:00",
                exit_time="2024-01-05 14:00:00",
                entry_price=100.0,
                exit_price=105.0,
                quantity=100,
                pnl=500.0,
            )
        ],
        equity_curve=[
            EquityPoint(date="2024-01-01", value=1_000_000.0, drawdown=0.0),
            EquityPoint(date="2024-01-02", value=1_001_000.0, drawdown=0.0),
        ],
    )

    output_path = tmp_path / "result.json"
    ResultsExporter.export_json(result, output_path)

    assert output_path.exists()

    import json

    with open(output_path) as f:
        data = json.load(f)

    assert data["symbol"] == "BHP"
    assert data["strategy"] == "donchian_breakout"
    assert len(data["trades"]) == 1
    assert len(data["equity_curve"]) == 2


def test_export_csv(tmp_path):
    """Test CSV export functionality."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={"total_return": 0.1},
        trades=[
            TradeData(
                entry_time="2024-01-01 10:00:00",
                exit_time="2024-01-05 14:00:00",
                entry_price=100.0,
                exit_price=105.0,
                quantity=100,
                pnl=500.0,
            )
        ],
        equity_curve=[
            EquityPoint(date="2024-01-01", value=1_000_000.0, drawdown=0.0),
            EquityPoint(date="2024-01-02", value=1_001_000.0, drawdown=0.0),
        ],
    )

    ResultsExporter.export_csv(result, tmp_path)

    trades_path = tmp_path / "trades.csv"
    equity_path = tmp_path / "equity.csv"

    assert trades_path.exists()
    assert equity_path.exists()

    import polars as pl

    trades_df = pl.read_csv(trades_path)
    equity_df = pl.read_csv(equity_path)

    assert len(trades_df) == 1
    assert len(equity_df) == 2
    assert trades_df.row(0)[2] == 100.0


def test_export_csv_empty(tmp_path):
    """Test CSV export with empty data."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={"total_return": 0.1},
        trades=[],
        equity_curve=[],
    )

    ResultsExporter.export_csv(result, tmp_path)

    trades_path = tmp_path / "trades.csv"
    equity_path = tmp_path / "equity.csv"

    assert not trades_path.exists()
    assert not equity_path.exists()


def test_export_all(tmp_path):
    """Test export_all functionality."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={"total_return": 0.1},
        trades=[],
        equity_curve=[],
    )

    ResultsExporter.export_all(result, tmp_path)

    json_path = tmp_path / "result.json"
    assert json_path.exists()


def test_format_summary():
    """Test format_summary functionality."""
    result = BacktestResult(
        symbol="BHP",
        strategy="donchian_breakout",
        period={"start": "2024-01-01", "end": "2024-12-31"},
        parameters={"channel_period": 20},
        initial_capital=1_000_000.0,
        final_capital=1_100_000.0,
        metrics={
            "total_return": 0.1,
            "cagr": 0.1,
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.15,
            "calmar_ratio": 0.67,
            "total_trades": 10,
            "win_rate": 0.6,
            "avg_win": 1000.0,
            "avg_loss": -500.0,
            "profit_factor": 1.2,
        },
        trades=[],
        equity_curve=[],
    )

    summary = ResultsExporter.format_summary(result)

    assert "BHP - donchian_breakout" in summary
    assert "10.00%" in summary
    assert "Total Return: 10.00%" in summary
    assert "Sharpe Ratio: 1.50" in summary
    assert "Win Rate: 60.00%" in summary

"""Backtest engine wrapper for running strategies with vn.py."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vnpy.trader.constant import Direction, Exchange, Interval, Offset
from vnpy_ctastrategy.backtesting import BacktestingEngine

from app.analysis.data_loader import load_bars
from app.analysis.metrics import MetricsCalculator
from app.analysis.results import BacktestResult, EquityPoint, ResultsExporter, TradeData

if TYPE_CHECKING:
    from vnpy.trader.object import BarData
    from vnpy.trader.object import TradeData as VnpyTradeData


class BacktestEngineWrapper:
    """Wrapper around vn.py BacktestingEngine."""

    def __init__(
        self,
        capital: float = 1_000_000,
        commission_rate: float = 0.001,
        fixed_commission: float = 6.6,
        slippage: float = 0.02,
    ) -> None:
        """Initialize backtest engine.

        Args:
            capital: Initial capital
            commission_rate: Commission rate percentage
            fixed_commission: Fixed commission per trade ($6.60)
            slippage: Slippage percentage (2%)
        """
        self.capital = capital
        self.commission_rate = commission_rate
        self.fixed_commission = fixed_commission
        self.slippage = slippage

    def run_backtest(
        self,
        symbol: str,
        strategy_class: type,
        strategy_params: dict[str, float | str],
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Run backtest for a symbol and strategy.

        Args:
            symbol: Trading symbol (e.g., "BHP")
            strategy_class: Strategy class to backtest
            strategy_params: Strategy parameters
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            BacktestResult object with results
        """
        engine = BacktestingEngine()

        bars = load_bars(symbol, start_date, end_date, Exchange.LOCAL, Interval.DAILY)

        if not bars:
            raise ValueError(f"No data found for {symbol} in specified date range")

        engine.set_parameters(
            vt_symbol=f"{symbol}.LOCAL",
            interval=Interval.DAILY,
            start=start_date,
            end=end_date,
            capital=self.capital,
            rate=self.commission_rate,
            slippage=self.slippage,
            size=1,
            pricetick=0.01,
        )

        engine.add_strategy(
            strategy_class,
            setting=strategy_params,
        )

        engine.load_data()
        engine.run_backtesting()

        daily_results_df = engine.calculate_result()
        vnpy_trades = engine.get_all_trades()

        equity_curve = self._build_equity_curve(daily_results_df, bars)
        trade_list = self._build_trade_list(vnpy_trades)

        metrics = MetricsCalculator.calculate_metrics(trade_list, equity_curve, self.capital)

        return BacktestResult(
            symbol=symbol,
            strategy=str(strategy_params.get("strategy_name", strategy_class.__name__)),
            period={
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
            parameters=strategy_params,
            initial_capital=self.capital,
            final_capital=self.capital * (1 + metrics.get("total_return", 0)),
            metrics=metrics,
            trades=[TradeData(**t) for t in trade_list],  # type: ignore[arg-type]
            equity_curve=[EquityPoint(**e) for e in equity_curve],  # type: ignore[arg-type]
        )

    def _build_equity_curve(
        self, daily_results_df: Any, bars: list["BarData"]
    ) -> list[dict[str, float | str]]:
        """Build equity curve from daily results.

        Args:
            daily_results_df: vn.py daily results DataFrame
            bars: List of bar data

        Returns:
            List of equity point dicts
        """
        equity_curve: list[dict[str, float | str]] = []

        if daily_results_df is None or daily_results_df.empty:
            return equity_curve

        daily_results_df = daily_results_df.copy()
        daily_results_df = daily_results_df.sort_index()
        daily_results_df["cumulative_pnl"] = daily_results_df["net_pnl"].cumsum()

        daily_results_dict = daily_results_df.to_dict("index")

        running_peak = self.capital

        for bar in bars:
            if bar.datetime is None:
                continue
            date = bar.datetime.date()
            if date in daily_results_dict:
                daily_result = daily_results_dict[date]
                value = self.capital + float(daily_result["cumulative_pnl"])

                running_peak = max(running_peak, value)
                drawdown = (running_peak - value) / running_peak if running_peak > 0 else 0.0

                equity_curve.append(
                    {
                        "date": bar.datetime.strftime("%Y-%m-%d"),
                        "value": float(value),
                        "drawdown": float(drawdown),
                    }
                )
            elif equity_curve:
                equity_curve.append(
                    {
                        "date": bar.datetime.strftime("%Y-%m-%d"),
                        "value": float(equity_curve[-1]["value"]),
                        "drawdown": 0.0,
                    }
                )

        return equity_curve

    def _build_trade_list(self, vnpy_trades: list["VnpyTradeData"]) -> list[dict[str, float | str]]:
        """Build trade list from vn.py trades.

        Args:
            vnpy_trades: List of vn.py TradeData objects

        Returns:
            List of trade dicts with entry/exit paired data
        """
        buy_trades: list[dict[str, float | str]] = []
        sell_trades: list[dict[str, float | str]] = []

        for trade in vnpy_trades:
            if trade.datetime is None or trade.direction is None:
                continue
            trade_dict: dict[str, float | str] = {
                "time": trade.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "price": float(trade.price),
                "quantity": float(trade.volume),
                "direction": trade.direction.value,
            }

            if trade.direction == Direction.LONG and trade.offset == Offset.OPEN:
                buy_trades.append(trade_dict)
            elif trade.direction == Direction.SHORT and trade.offset == Offset.CLOSE:
                sell_trades.append(trade_dict)

        trades = []
        buy_queue = list(buy_trades)

        for sell in sell_trades:
            remaining_sell_qty = float(sell["quantity"])

            while remaining_sell_qty > 0 and buy_queue:
                buy = buy_queue[0]
                buy_qty = float(buy["quantity"])
                match_qty = min(remaining_sell_qty, buy_qty)

                pnl = (
                    float(sell["price"]) - float(buy["price"])
                ) * match_qty - self.fixed_commission * 2 * (match_qty / remaining_sell_qty)

                trades.append(
                    {
                        "entry_time": buy["time"],
                        "exit_time": sell["time"],
                        "entry_price": float(buy["price"]),
                        "exit_price": float(sell["price"]),
                        "quantity": int(match_qty),
                        "pnl": float(pnl),
                    }
                )

                remaining_sell_qty -= match_qty

                if match_qty >= buy_qty:
                    buy_queue.pop(0)
                else:
                    buy["quantity"] = buy_qty - match_qty

        return trades


def run_backtest(
    symbol: str,
    strategy_class: type,
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

    engine = BacktestEngineWrapper(
        capital=capital,
        commission_rate=config.analysis.commission_rate,
        fixed_commission=config.analysis.fixed_commission,
        slippage=config.analysis.slippage,
    )

    result = engine.run_backtest(symbol, strategy_class, strategy_params, start_date, end_date)

    if output_dir:
        ResultsExporter.export_all(result, output_dir)

    return result

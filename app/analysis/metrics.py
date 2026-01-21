"""Performance metrics calculator for backtesting results."""

import math
from typing import Any

import polars as pl


class MetricsCalculator:
    """Calculate performance metrics from backtest results."""

    @staticmethod
    def calculate_metrics(
        trades: list[dict[str, Any]],
        equity_curve: list[dict[str, Any]],
        initial_capital: float,
    ) -> dict[str, float]:
        """Calculate all performance metrics.

        Args:
            trades: List of trade dictionaries with 'pnl' field
            equity_curve: List of equity points with 'date' and 'value' fields
            initial_capital: Initial capital amount

        Returns:
            Dictionary of calculated metrics
        """
        df_trades = pl.DataFrame(trades)
        df_equity = pl.DataFrame(equity_curve)

        metrics = {}

        if df_trades.is_empty():
            metrics["total_return"] = 0.0
            metrics["cagr"] = 0.0
            metrics["sharpe_ratio"] = 0.0
            metrics["sortino_ratio"] = 0.0
            metrics["max_drawdown"] = 0.0
            metrics["calmar_ratio"] = 0.0
            metrics["total_trades"] = 0
            metrics["win_rate"] = 0.0
            metrics["avg_win"] = 0.0
            metrics["avg_loss"] = 0.0
            metrics["profit_factor"] = 0.0
            return metrics

        final_equity = df_equity["value"][-1]
        total_return = (final_equity - initial_capital) / initial_capital

        metrics["total_return"] = total_return
        metrics["total_trades"] = len(trades)

        metrics.update(MetricsCalculator._calculate_return_metrics(df_equity, initial_capital))
        metrics.update(MetricsCalculator._calculate_drawdown_metrics(df_equity))
        metrics.update(MetricsCalculator._calculate_trade_metrics(df_trades))

        return metrics

    @staticmethod
    def _calculate_return_metrics(
        df_equity: pl.DataFrame, _initial_capital: float
    ) -> dict[str, float]:
        """Calculate return-based metrics.

        Args:
            df_equity: Equity curve DataFrame
            initial_capital: Initial capital

        Returns:
            Dictionary with return metrics
        """
        if df_equity.is_empty() or len(df_equity) < 2:
            return {"cagr": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "volatility": 0.0}

        df_equity = df_equity.sort("date")
        df_equity = df_equity.with_columns(
            daily_return=(pl.col("value") / pl.col("value").shift(1) - 1).fill_null(0)
        )

        returns = df_equity["daily_return"].to_list()
        final_value = df_equity["value"][-1]
        first_value = df_equity["value"][0]

        years = len(returns) / 252 if len(returns) >= 252 else len(returns) / 365
        if years <= 0:
            return {"cagr": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "volatility": 0.0}

        cagr = (final_value / first_value) ** (1 / years) - 1

        mean_return = sum(returns) / len(returns)
        volatility = math.sqrt(
            sum([(r - mean_return) ** 2 for r in returns]) / len(returns)
        ) * math.sqrt(252)

        sharpe_ratio = (mean_return * 252) / volatility if volatility > 0 else 0.0

        negative_returns = [r for r in returns if r < 0]
        downside_deviation = (
            math.sqrt(sum([r**2 for r in negative_returns]) / len(negative_returns))
            * math.sqrt(252)
            if negative_returns
            else 0.0
        )
        sortino_ratio = (mean_return * 252) / downside_deviation if downside_deviation > 0 else 0.0

        return {
            "cagr": cagr,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "volatility": volatility,
        }

    @staticmethod
    def _calculate_drawdown_metrics(df_equity: pl.DataFrame) -> dict[str, float]:
        """Calculate drawdown-based metrics.

        Args:
            df_equity: Equity curve DataFrame

        Returns:
            Dictionary with drawdown metrics
        """
        if df_equity.is_empty():
            return {"max_drawdown": 0.0, "calmar_ratio": 0.0}

        df_equity = df_equity.sort("date")
        values = df_equity["value"].to_list()

        running_max = values[0]
        max_drawdown = 0.0

        for v in values:
            if v > running_max:
                running_max = v
            if running_max > 0:
                drawdown = (running_max - v) / running_max
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        total_return = (values[-1] - values[0]) / values[0]
        calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0.0

        return {
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
        }

    @staticmethod
    def _calculate_trade_metrics(df_trades: pl.DataFrame) -> dict[str, float]:
        """Calculate trade-based metrics.

        Args:
            df_trades: Trades DataFrame with 'pnl' field

        Returns:
            Dictionary with trade metrics
        """
        if df_trades.is_empty():
            return {
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "avg_trade": 0.0,
            }

        pnls = df_trades["pnl"].to_list()
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        win_rate = len(wins) / len(pnls) if pnls else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        total_win = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = total_win / total_loss if total_loss > 0 else float("inf")
        avg_trade = sum(pnls) / len(pnls) if pnls else 0.0

        return {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "avg_trade": avg_trade,
        }

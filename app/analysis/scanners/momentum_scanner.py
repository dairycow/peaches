"""Momentum and consolidation pattern detection for stocks."""

import statistics
from datetime import datetime

import polars as pl

from app.analysis.stock_data import StockData


class MomentumScanner:
    """Detects momentum bursts and consolidation patterns."""

    def __init__(self, stocks: dict[str, StockData]):
        """Initialize MomentumScanner.

        Args:
            stocks: Dictionary of ticker -> StockData
        """
        self.stocks = stocks

    def detect_momentum_bursts(
        self,
        stock: StockData,
        min_days: int = 3,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Detect momentum bursts (3+ consecutive up days) for a stock.

        Args:
            stock: StockData object
            min_days: Minimum consecutive up days (default: 3)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of momentum burst dictionaries
        """
        if stock.df is None or stock.df.is_empty():
            return []

        df = stock.df
        if start_date and end_date:
            df = stock.filter_by_date_range(start_date, end_date)

        if df.is_empty():
            return []

        bursts = []
        consecutive_up = 0
        burst_start_idx = None

        close_prices = df["close"].to_list()
        volumes = df["volume"].to_list()
        dates = df["date"].to_list()

        for i in range(1, len(close_prices)):
            if close_prices[i] is None or close_prices[i - 1] is None:
                if consecutive_up >= min_days and burst_start_idx is not None:
                    end_idx = i - 1
                    self._add_momentum_burst(
                        bursts,
                        stock,
                        dates,
                        close_prices,
                        volumes,
                        burst_start_idx,
                        end_idx,
                        consecutive_up,
                    )
                consecutive_up = 0
                burst_start_idx = None
                continue

            if close_prices[i] > close_prices[i - 1]:
                consecutive_up += 1
                if burst_start_idx is None:
                    burst_start_idx = i - 1
            else:
                if consecutive_up >= min_days and burst_start_idx is not None:
                    end_idx = i - 1
                    self._add_momentum_burst(
                        bursts,
                        stock,
                        dates,
                        close_prices,
                        volumes,
                        burst_start_idx,
                        end_idx,
                        consecutive_up,
                    )
                consecutive_up = 0
                burst_start_idx = None

        if consecutive_up >= min_days and burst_start_idx is not None:
            end_idx = len(close_prices) - 1
            self._add_momentum_burst(
                bursts,
                stock,
                dates,
                close_prices,
                volumes,
                burst_start_idx,
                end_idx,
                consecutive_up,
            )

        return bursts

    def _add_momentum_burst(
        self,
        bursts: list[dict],
        stock: StockData,
        dates: list,
        close_prices: list,
        volumes: list,
        start_idx: int,
        end_idx: int,
        consecutive_up: int,
    ) -> None:
        """Helper method to add a momentum burst to the list."""
        if close_prices[start_idx] is None or close_prices[end_idx] is None:
            return

        start_price = close_prices[start_idx]
        end_price = close_prices[end_idx]
        total_gain = ((end_price - start_price) / start_price) * 100

        avg_volume = sum(v for v in volumes[start_idx : end_idx + 1] if v is not None) / (
            end_idx - start_idx + 1
        )
        baseline_start = max(0, start_idx - 50)
        baseline_count = start_idx - baseline_start
        baseline_volume = (
            sum(v for v in volumes[baseline_start:start_idx] if v is not None) / baseline_count
            if baseline_count > 0
            else avg_volume
        )
        volume_multiple = avg_volume / baseline_volume if baseline_volume > 0 else 1.0

        daily_gains = []
        for j in range(start_idx + 1, end_idx + 1):
            if (
                close_prices[j - 1] is not None
                and close_prices[j] is not None
                and close_prices[j - 1] > 0
            ):
                daily_gains.append(
                    ((close_prices[j] - close_prices[j - 1]) / close_prices[j - 1]) * 100
                )

        bursts.append(
            {
                "ticker": stock.ticker,
                "pattern_type": "momentum_burst",
                "start_date": dates[start_idx].isoformat(),
                "end_date": dates[end_idx].isoformat(),
                "duration_days": consecutive_up,
                "consecutive_up_days": consecutive_up,
                "start_price": float(start_price),
                "end_price": float(end_price),
                "total_gain_pct": total_gain,
                "daily_gains": daily_gains,
                "avg_volume": int(avg_volume),
                "volume_spike_multiple": round(volume_multiple, 2),
            }
        )

    def detect_consolidation(
        self,
        stock: StockData,
        max_range_pct: float = 10.0,
        min_days: int = 5,
        volume_threshold: float = 0.5,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Detect consolidation patterns (flat price + low volume) for a stock.

        Args:
            stock: StockData object
            max_range_pct: Maximum price range percentage (default: 10%)
            min_days: Minimum consolidation duration (default: 5 days)
            volume_threshold: Volume ratio threshold (default: 0.5 = 50% of baseline)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of consolidation dictionaries
        """
        if stock.df is None or stock.df.is_empty():
            return []

        df = stock.df
        if start_date and end_date:
            df = stock.filter_by_date_range(start_date, end_date)

        if df.is_empty():
            return []

        consolidations = []
        close_prices = df["close"].to_list()
        volumes = df["volume"].to_list()
        dates = df["date"].to_list()
        highs = df["high"].to_list()
        lows = df["low"].to_list()

        window_size = min_days
        for i in range(len(close_prices) - window_size + 1):
            window_end = min(i + window_size, len(close_prices))

            max_price = max(highs[i:window_end])
            min_price = min(lows[i:window_end])
            avg_price = (max_price + min_price) / 2

            price_range_pct = ((max_price - min_price) / avg_price) * 100

            if price_range_pct <= max_range_pct:
                avg_volume = sum(volumes[i:window_end]) / (window_end - i)
                baseline_volume = (
                    sum(volumes[max(0, i - 50) : i]) / min(50, i) if i > 0 else avg_volume
                )
                volume_ratio = avg_volume / baseline_volume if baseline_volume > 0 else 1.0

                if volume_ratio <= volume_threshold:
                    volume_decline_pct = (
                        ((baseline_volume - avg_volume) / baseline_volume) * 100
                        if baseline_volume > 0
                        else 0
                    )

                    consolidations.append(
                        {
                            "ticker": stock.ticker,
                            "pattern_type": "consolidation",
                            "start_date": dates[i].isoformat(),
                            "end_date": dates[window_end - 1].isoformat(),
                            "duration_days": window_end - i,
                            "price_range_pct": round(price_range_pct, 2),
                            "start_price": float(close_prices[i]),
                            "end_price": float(close_prices[window_end - 1]),
                            "high": float(max_price),
                            "low": float(min_price),
                            "avg_volume": int(avg_volume),
                            "volume_decline_pct": round(volume_decline_pct, 2),
                            "volume_ratio_to_avg": round(volume_ratio, 2),
                        }
                    )

        return consolidations

    def analyze_stock_patterns(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Analyze all patterns for a specific stock.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            Dictionary with all detected patterns
        """
        if ticker not in self.stocks:
            return {"ticker": ticker, "error": "Stock not found"}

        stock = self.stocks[ticker]
        momentum_bursts = self.detect_momentum_bursts(
            stock, start_date=start_date, end_date=end_date
        )
        consolidations = self.detect_consolidation(stock, start_date=start_date, end_date=end_date)

        return {
            "ticker": ticker,
            "momentum_bursts": momentum_bursts,
            "consolidations": consolidations,
            "total_momentum_bursts": len(momentum_bursts),
            "total_consolidations": len(consolidations),
        }

    def find_all_momentum_bursts(
        self,
        start_date: datetime,
        end_date: datetime,
        min_days: int = 3,
        limit: int = 50,
    ) -> list[dict]:
        """Find all momentum bursts across all stocks.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            min_days: Minimum consecutive up days (default: 3)
            limit: Maximum number of results

        Returns:
            List of all momentum bursts
        """
        all_bursts = []

        for _ticker, stock in self.stocks.items():
            bursts = self.detect_momentum_bursts(
                stock,
                min_days=min_days,
                start_date=start_date,
                end_date=end_date,
            )
            all_bursts.extend(bursts)

        all_bursts.sort(key=lambda x: x["total_gain_pct"], reverse=True)
        return all_bursts[:limit]

    def find_all_consolidations(
        self,
        start_date: datetime,
        end_date: datetime,
        max_range_pct: float = 10.0,
        min_days: int = 5,
        limit: int = 50,
    ) -> list[dict]:
        """Find all consolidations across all stocks.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            max_range_pct: Maximum price range percentage (default: 10%)
            min_days: Minimum consolidation duration (default: 5 days)
            limit: Maximum number of results

        Returns:
            List of all consolidations
        """
        all_consolidations = []

        for _ticker, stock in self.stocks.items():
            consolidations = self.detect_consolidation(
                stock,
                max_range_pct=max_range_pct,
                min_days=min_days,
                start_date=start_date,
                end_date=end_date,
            )
            all_consolidations.extend(consolidations)

        all_consolidations.sort(key=lambda x: x["duration_days"], reverse=True)
        return all_consolidations[:limit]

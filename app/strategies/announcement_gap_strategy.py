"""ASX announcement gap breakout strategy.

Strategy logic:
1. Stock has made an announcement today
2. Positive gap with price > 6 month high
3. Stock price > 0.20
4. Enter after 5-minute opening range high is set with market stop order
5. Stop set to low of the day
6. Exit after 3 days
"""

from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from vnpy.trader.constant import Direction, Offset, OrderType
from vnpy.trader.object import BarData, OrderData, OrderRequest, TickData, TradeData
from vnpy_ctastrategy import CtaTemplate

STRATEGY_NAME = "announcement_gap_breakout"

ANNOUNCEMENT_TRACKER: dict[str, datetime] = {}


def register_announcement(symbol: str, announcement_time: datetime) -> None:
    """Register a price-sensitive announcement for a symbol.

    Args:
        symbol: Stock symbol
        announcement_time: When the announcement was made
    """
    ANNOUNCEMENT_TRACKER[symbol] = announcement_time
    logger.info(f"Registered announcement: {symbol} at {announcement_time}")


def check_announcement_today(symbol: str, lookback_hours: int = 24) -> bool:
    """Check if a symbol has made an announcement recently.

    Args:
        symbol: Stock symbol
        lookback_hours: Hours to look back for announcements

    Returns:
        True if announcement found within lookback period
    """
    if symbol not in ANNOUNCEMENT_TRACKER:
        return False

    announcement_time = ANNOUNCEMENT_TRACKER[symbol]
    cutoff = datetime.now() - timedelta(hours=lookback_hours)

    return announcement_time >= cutoff


DEFAULT_PARAMETERS = {
    "min_price": 0.20,
    "min_gap_pct": 0.0,
    "lookback_months": 6,
    "opening_range_minutes": 5,
    "position_size": 100,
    "max_positions": 10,
    "exit_days": 3,
}


class AnnouncementGapBreakoutStrategy(CtaTemplate):
    """ASX announcement gap breakout strategy.

    Features:
    - Multi-condition screening (announcement + gap + 6M high + price)
    - 5-minute opening range entry with market stop order
    - Day-low stop loss
    - 3-day time-based exit
    """

    parameters = [
        "min_price",
        "min_gap_pct",
        "lookback_months",
        "opening_range_minutes",
        "position_size",
        "max_positions",
        "exit_days",
    ]

    variables = [
        "entry_price",
        "entry_time",
        "day_low",
        "opening_range_high",
        "opening_range_low",
        "entry_triggered",
        "six_month_high",
        "announcement_found",
    ]

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        setting: dict[str, Any],
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.min_price: float = 0.20
        self.min_gap_pct: float = 0.0
        self.lookback_months: int = 6
        self.opening_range_minutes: int = 5
        self.position_size: int = 100
        self.max_positions: int = 10
        self.exit_days: int = 3

        self.entry_price: float = 0.0
        self.entry_time: datetime | None = None
        self.day_low: float = 0.0
        self.opening_range_high: float = 0.0
        self.opening_range_low: float = 0.0
        self.entry_triggered: bool = False
        self.six_month_high: float = 0.0
        self.announcement_found: bool = False

        self.bar_buffer: list[BarData] = []

    def on_init(self) -> None:
        """Initialize strategy."""
        self.write_log("Announcement Gap Breakout Strategy initialized")
        self.write_log(
            f"Parameters: MinPrice=${self.min_price:.2f}, Lookback={self.lookback_months}M, "
            f"OR={self.opening_range_minutes}min, Exit={self.exit_days}d"
        )

    def on_start(self) -> None:
        """Start strategy."""
        self.write_log("Announcement Gap Breakout Strategy started")

    def on_stop(self) -> None:
        """Stop strategy."""
        self.write_log("Announcement Gap Breakout Strategy stopped")

    def on_tick(self, tick: TickData) -> None:
        """Process tick data."""
        pass

    def on_bar(self, bar: BarData) -> None:
        """Process bar data and generate trading signals."""
        if not self.bar_buffer:
            self.bar_buffer.append(bar)
            self.day_low = bar.low_price
            self.six_month_high = self._calculate_six_month_high(bar)
            return

        if self._is_new_day(bar):
            self._on_new_day(bar)

        self._update_opening_range(bar)
        self._update_day_low(bar)

        if not self.entry_triggered and self._check_entry_conditions(bar):
            self._on_entry(bar)
        elif self.entry_triggered and self._check_exit_conditions(bar):
            self._on_exit(bar)

        self.bar_buffer.append(bar)
        if len(self.bar_buffer) > 1000:
            self.bar_buffer.pop(0)

    def _is_new_day(self, bar: BarData) -> bool:
        """Check if bar is from a new day.

        Args:
            bar: Current bar data

        Returns:
            True if new day, False otherwise
        """
        if not self.bar_buffer:
            return True

        return bar.datetime.date() != self.bar_buffer[-1].datetime.date()

    def _on_new_day(self, bar: BarData) -> None:
        """Handle new day reset.

        Args:
            bar: Current bar data
        """
        self.day_low = bar.low_price
        self.opening_range_high = 0.0
        self.opening_range_low = 0.0

    def _update_opening_range(self, bar: BarData) -> None:
        """Update opening range values.

        Args:
            bar: Current bar data
        """
        market_open = bar.datetime.replace(hour=10, minute=0, second=0, microsecond=0)

        if bar.datetime >= market_open and bar.datetime < market_open + timedelta(
            minutes=self.opening_range_minutes
        ):
            self.opening_range_high = max(self.opening_range_high, bar.high_price)
            self.opening_range_low = (
                min(self.opening_range_low, bar.low_price)
                if self.opening_range_low > 0
                else bar.low_price
            )

    def _update_day_low(self, bar: BarData) -> None:
        """Update day low for stop loss.

        Args:
            bar: Current bar data
        """
        self.day_low = min(self.day_low, bar.low_price)

    def _calculate_six_month_high(self, bar: BarData) -> float:
        """Calculate 6-month high from historical bars.

        Args:
            bar: Current bar data

        Returns:
            6-month high price
        """
        cutoff_date = bar.datetime - timedelta(days=180)

        high_bars = [b for b in self.bar_buffer if b.datetime >= cutoff_date]

        if not high_bars:
            return bar.close_price

        return max(b.high_price for b in high_bars)

    def _check_entry_conditions(self, bar: BarData) -> bool:
        """Check if entry conditions are met.

        Args:
            bar: Current bar data

        Returns:
            True if conditions met, False otherwise
        """
        if self.pos > 0:
            return False

        if bar.close_price < self.min_price:
            return False

        self.announcement_found = check_announcement_today(bar.symbol, lookback_hours=24)
        if not self.announcement_found:
            return False

        if not self._check_gap(bar):
            return False

        if bar.close_price <= self.six_month_high:
            return False

        market_open = bar.datetime.replace(hour=10, minute=0, second=0, microsecond=0)
        return bar.datetime >= market_open + timedelta(minutes=self.opening_range_minutes)

    def _check_gap(self, bar: BarData) -> bool:
        """Check if gap condition is met.

        Args:
            bar: Current bar data

        Returns:
            True if gap positive, False otherwise
        """
        if len(self.bar_buffer) < 1:
            return False

        prev_close = self.bar_buffer[-1].close_price
        curr_open = bar.open_price

        gap_pct = (curr_open - prev_close) / prev_close * 100

        return gap_pct >= self.min_gap_pct

    def _on_entry(self, bar: BarData) -> None:
        """Handle entry signal with market stop order at opening range high.

        Args:
            bar: Current bar data
        """
        if self.opening_range_high <= 0:
            return

        req = OrderRequest(
            symbol=bar.symbol,
            exchange=bar.exchange,
            direction=Direction.LONG,
            type=OrderType.STOP,
            volume=self.position_size,
            price=self.opening_range_high,
            offset=Offset.OPEN,
        )

        self.send_order(req)

        self.entry_triggered = True
        self.entry_price = self.opening_range_high
        self.entry_time = bar.datetime

        self.write_log(
            f"Entry triggered: {bar.vt_symbol} @ ${self.opening_range_high:.2f} "
            f"(ORH set, Stop @ ${self.day_low:.2f})"
        )

    def _check_exit_conditions(self, bar: BarData) -> bool:
        """Check if exit conditions are met.

        Args:
            bar: Current bar data

        Returns:
            True if exit triggered, False otherwise
        """
        if not self.entry_time:
            return False

        days_held = (bar.datetime.date() - self.entry_time.date()).days

        return days_held >= self.exit_days

    def _on_exit(self, bar: BarData) -> None:
        """Handle exit signal.

        Args:
            bar: Current bar data
        """
        if abs(self.pos) > 0:
            self.sell(bar.close_price, abs(self.pos), stop=False)
            self.write_log(
                f"Exit triggered: {bar.vt_symbol} @ ${bar.close_price:.2f} "
                f"(held {self.exit_days} days)"
            )

        self.entry_triggered = False
        self.entry_price = 0.0
        self.entry_time = None

    def on_order(self, order: OrderData) -> None:
        """Process order update."""
        if order.status.value == "全部成交":
            self.write_log(f"Order filled: {order.vt_orderid} {order.vt_symbol}")

    def on_trade(self, trade: TradeData) -> None:
        """Process trade update."""
        if trade.direction == Direction.LONG and trade.offset == Offset.OPEN:
            self.write_log(f"Buy trade: {trade.vt_symbol} {trade.volume} @ {trade.price}")

            if abs(self.pos) > 0 and self.day_low > 0:
                stop_req = OrderRequest(
                    symbol=trade.symbol,
                    exchange=trade.exchange,
                    direction=Direction.SHORT,
                    type=OrderType.STOP,
                    volume=abs(self.pos),
                    price=self.day_low,
                    offset=Offset.CLOSE,
                )
                self.send_order(stop_req)
                self.write_log(f"Stop order placed @ ${self.day_low:.2f}")

        elif trade.direction == Direction.SHORT and trade.offset == Offset.CLOSE:
            self.write_log(f"Sell trade: {trade.vt_symbol} {trade.volume} @ {trade.price}")

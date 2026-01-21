"""Donchian channel breakout strategy.

This strategy generates buy signals when price closes above the N-period high,
and sells when price closes below the N-period low.
"""

from typing import Any

from vnpy.trader.object import BarData, OrderData, TickData, TradeData
from vnpy_ctastrategy import CtaTemplate

STRATEGY_NAME = "donchian_breakout"
DEFAULT_PARAMETERS = {
    "channel_period": 20,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "risk_per_trade": 0.02,
}


class DonchianBreakoutStrategy(CtaTemplate):
    """Donchian channel breakout strategy.

    Features:
    - N-period high/low channel breakout
    - Risk-based position sizing (2% of capital)
    - Stop loss and take profit
    """

    parameters = [
        "channel_period",
        "stop_loss_pct",
        "take_profit_pct",
        "risk_per_trade",
    ]

    variables = [
        "entry_price",
        "highest_price",
        "lowest_price",
    ]

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,
        vt_symbol: str,
        setting: dict[str, Any],
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.high_buffer: list[float] = []
        self.low_buffer: list[float] = []
        self.close_buffer: list[float] = []

        self.entry_price: float = 0
        self.highest_price: float = 0
        self.lowest_price: float = 0

    def on_init(self) -> None:
        """Initialize strategy."""
        self.high_buffer = []
        self.low_buffer = []
        self.close_buffer = []
        print("[DEBUG INIT] Donchian Breakout Strategy initialized")
        self.write_log("Donchian Breakout Strategy initialized")
        self.write_log(
            f"Parameters: Channel={self.channel_period}, type={type(self.channel_period)}"
        )

    def on_start(self) -> None:
        """Start strategy."""
        self.write_log("Donchian Breakout Strategy started")

    def on_stop(self) -> None:
        """Stop strategy."""
        self.write_log("Donchian Breakout Strategy stopped")

    def on_tick(self, tick: TickData) -> None:
        """Process tick data."""
        pass

    def on_bar(self, bar: BarData) -> None:
        """Process bar data and generate trading signals."""
        if len(self.high_buffer) >= self.channel_period:
            channel_high = max(self.high_buffer)
            channel_low = min(self.low_buffer)

            if self.pos == 0:
                if bar.close_price > channel_high:
                    self.write_log(
                        f"Entry signal: Close {bar.close_price:.2f} > Channel High {channel_high:.2f}"
                    )
                    self._on_entry_signal(bar, channel_low)
            else:
                if bar.close_price < channel_low:
                    self.write_log(
                        f"Exit signal: Close {bar.close_price:.2f} < Channel Low {channel_low:.2f}"
                    )
                    self._on_exit_signal(bar)
                else:
                    self._check_stop_take_profit(bar)

        self.high_buffer.append(bar.high_price)
        self.low_buffer.append(bar.low_price)
        self.close_buffer.append(bar.close_price)

        if len(self.high_buffer) > self.channel_period:
            self.high_buffer.pop(0)
            self.low_buffer.pop(0)
            self.close_buffer.pop(0)

    def _on_entry_signal(self, bar: BarData, stop_level: float) -> None:
        """Handle entry signal with risk-based position sizing.

        Args:
            bar: Current bar data
            stop_level: Stop loss level for risk calculation
        """
        stop_distance = bar.close_price - stop_level
        if stop_distance <= 0:
            return

        capital: float = self.cta_engine.capital
        risk_amount = capital * self.risk_per_trade
        size = int(risk_amount / stop_distance)

        if size <= 0:
            return

        self.buy(bar.close_price, size, stop=False)
        self.entry_price = bar.close_price
        self.highest_price = bar.close_price

    def _on_exit_signal(self, bar: BarData) -> None:
        """Handle exit signal.

        Args:
            bar: Current bar data
        """
        if self.pos > 0:
            self.sell(bar.close_price, abs(self.pos), stop=False)

    def _check_stop_take_profit(self, bar: BarData) -> None:
        """Check stop loss and take profit levels.

        Args:
            bar: Current bar data
        """
        if self.pos > 0 and self.entry_price > 0:
            stop_loss = self.entry_price * (1 - self.stop_loss_pct)
            take_profit = self.entry_price * (1 + self.take_profit_pct)

            if bar.close_price <= stop_loss or bar.close_price >= take_profit:
                self.sell(bar.close_price, abs(self.pos), stop=False)

            if bar.close_price > self.highest_price:
                self.highest_price = bar.close_price

    def on_order(self, order: OrderData) -> None:
        """Process order update."""
        pass

    def on_trade(self, trade: TradeData) -> None:
        """Process trade update."""
        if trade.direction is not None and trade.offset is not None:
            if trade.direction.value == "多" and trade.offset.value == "开":
                self.write_log(f"Buy trade: {trade.vt_symbol} {trade.volume} @ {trade.price}")
            elif trade.direction.value == "空" and trade.offset.value == "平":
                self.write_log(f"Sell trade: {trade.vt_symbol} {trade.volume} @ {trade.price}")

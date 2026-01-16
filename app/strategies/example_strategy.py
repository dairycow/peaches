"""ASX-focused CTA strategy example.

This strategy demonstrates momentum trading on ASX stocks (e.g., BHP, CBA).
Designed for paper trading on ASX via Interactive Brokers.
"""

from vnpy.trader.object import BarData, OrderData, TickData, TradeData
from vnpy_ctastrategy import CtaTemplate

STRATEGY_NAME = "asx_momentum"
VT_SYMBOL = "BHP-STK-ASX"
DEFAULT_PARAMETERS = {
    "fast_period": 10,
    "slow_period": 20,
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "fixed_size": 100,
    "max_position_size": 100,
    "risk_per_trade": 0.02,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "max_daily_trades": 10,
    "max_drawdown_pct": 0.10,
}


class ASXMomentumStrategy(CtaTemplate):
    """Example momentum strategy for ASX trading.

    Features:
    - SMA crossover signals
    - RSI filter to avoid overbought/oversold
    - ATR-based position sizing
    - ASX trading hours consideration
    """

    parameters = [
        "fast_period",
        "slow_period",
        "rsi_period",
        "rsi_overbought",
        "rsi_oversold",
        "fixed_size",
        "max_position_size",
        "risk_per_trade",
        "stop_loss_pct",
        "take_profit_pct",
        "max_daily_trades",
        "max_drawdown_pct",
    ]

    variables = [
        "entry_price",
        "daily_trade_count",
        "high_watermark",
        "current_drawdown",
    ]

    def __init__(
        self,
        cta_engine,
        strategy_name: str,
        vt_symbol: str,
        setting: dict,
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.fast_period: int = 10
        self.slow_period: int = 20
        self.rsi_period: int = 14
        self.rsi_overbought: int = 70
        self.rsi_oversold: int = 30
        self.fixed_size: int = 100
        self.max_position_size: int = 100
        self.risk_per_trade: float = 0.02
        self.stop_loss_pct: float = 0.02
        self.take_profit_pct: float = 0.04
        self.max_daily_trades: int = 10
        self.max_drawdown_pct: float = 0.10
        self.bg: BarData | None = None
        self.rsi_buffer: list[float] = []
        self.bar_buffer: list[float] = []
        self.entry_price: float = 0
        self.daily_trade_count: int = 0
        self.high_watermark: float = 0
        self.current_drawdown: float = 0

    def on_init(self) -> None:
        """Initialize strategy."""
        self.write_log("ASX Momentum Strategy initialized")
        self.write_log(
            f"Parameters: Fast={self.fast_period}, Slow={self.slow_period}, RSI={self.rsi_period}"
        )

    def on_start(self) -> None:
        """Start strategy."""
        self.write_log("ASX Momentum Strategy started")
        self.write_log("Trading ASX market hours: 10:00-16:00 AEST")

    def on_stop(self) -> None:
        """Stop strategy."""
        self.write_log("ASX Momentum Strategy stopped")

    def on_tick(self, tick: TickData) -> None:
        """Process tick data."""
        pass

    def on_bar(self, bar: BarData) -> None:
        """Process bar data and generate trading signals."""
        if not self.bg:
            self.bg = bar
            return

        self._update_drawdown(bar.close_price)

        if self._check_drawdown_limit():
            self.write_log("Max drawdown limit reached, stopping trading")
            return

        fast_ma = self.calculate_sma(self.bg, self.fast_period)
        slow_ma = self.calculate_sma(self.bg, self.slow_period)
        rsi = self.calculate_rsi(bar.close_price)

        if self.has_entry_signal(fast_ma, slow_ma, rsi):
            self._on_entry_signal(bar)
        elif self.has_exit_signal(fast_ma, slow_ma, rsi):
            self._on_exit_signal(bar)

        self.bg = bar

    def _update_drawdown(self, current_price: float) -> None:
        """Update drawdown tracking.

        Args:
            current_price: Current price
        """
        if current_price > self.high_watermark:
            self.high_watermark = current_price

        if self.high_watermark > 0:
            self.current_drawdown = (self.high_watermark - current_price) / self.high_watermark

    def _check_drawdown_limit(self) -> bool:
        """Check if drawdown exceeds limit.

        Returns:
            True if drawdown exceeds limit, False otherwise
        """
        return self.current_drawdown > self.max_drawdown_pct

    def _check_daily_trade_limit(self) -> bool:
        """Check if daily trade limit reached.

        Returns:
            True if limit reached, False otherwise
        """
        return self.daily_trade_count >= self.max_daily_trades

    def _check_position_limit(self, proposed_size: int) -> bool:
        """Check if position size exceeds limit.

        Args:
            proposed_size: Proposed position size

        Returns:
            True if exceeds limit, False otherwise
        """
        new_position = abs(self.pos) + proposed_size
        return new_position > self.max_position_size

    def _on_entry_signal(self, bar: BarData) -> None:
        """Handle entry signal with risk checks.

        Args:
            bar: Current bar data
        """
        if self._check_daily_trade_limit():
            self.write_log(f"Daily trade limit reached: {self.daily_trade_count}")
            return

        if self._check_position_limit(self.fixed_size):
            self.write_log(f"Position size would exceed limit: {abs(self.pos)} + {self.fixed_size}")
            return

        self.buy(bar.close_price, self.fixed_size, stop=True)
        self.entry_price = bar.close_price

    def _on_exit_signal(self, bar: BarData) -> None:
        """Handle exit signal.

        Args:
            bar: Current bar data
        """
        if abs(self.pos) > 0:
            self.sell(bar.close_price, self.fixed_size, stop=True)

    def has_entry_signal(self, fast_ma: float, slow_ma: float, rsi: float) -> bool:
        """Check for buy entry signal.

        Args:
            fast_ma: Fast moving average
            slow_ma: Slow moving average
            rsi: RSI value

        Returns:
            True if entry signal, False otherwise
        """
        return fast_ma > slow_ma and rsi < self.rsi_overbought

    def has_exit_signal(self, fast_ma: float, slow_ma: float, rsi: float) -> bool:
        """Check for exit signal.

        Args:
            fast_ma: Fast moving average
            slow_ma: Slow moving average
            rsi: RSI value

        Returns:
            True if exit signal, False otherwise
        """
        return fast_ma < slow_ma or rsi > self.rsi_overbought

    def on_order(self, order: OrderData) -> None:
        """Process order update."""
        self.write_log(f"Order update: {order.orderid} {order.vt_symbol} {order.status}")

    def on_trade(self, trade: TradeData) -> None:
        """Process trade update."""
        self.write_log(
            f"Trade executed: {trade.tradeid} {trade.vt_symbol} {trade.direction} @ {trade.price}"
        )
        self.daily_trade_count += 1

    def calculate_sma(self, bar: BarData, period: int) -> float:
        """Calculate simple moving average.

        Args:
            bar: Bar data
            period: Period for SMA

        Returns:
            SMA value
        """
        self.bar_buffer.append(bar.close_price)
        if len(self.bar_buffer) > period:
            self.bar_buffer.pop(0)

        if len(self.bar_buffer) == period:
            return sum(self.bar_buffer) / period
        return bar.close_price

    def calculate_rsi(self, current_price: float, period: int = 14) -> float:
        """Calculate Relative Strength Index (RSI).

        Args:
            current_price: Current close price
            period: RSI period (default: 14)

        Returns:
            RSI value (0-100)
        """
        self.rsi_buffer.append(current_price)
        if len(self.rsi_buffer) > period:
            self.rsi_buffer.pop(0)

        if len(self.rsi_buffer) < 2:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(self.rsi_buffer)):
            change = self.rsi_buffer[i] - self.rsi_buffer[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < period:
            return 50.0

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

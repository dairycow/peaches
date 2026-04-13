"""Donchian channel breakout strategy.

This strategy generates buy signals when price closes above the N-period high,
and sells when price closes below the N-period low.
"""

from __future__ import annotations

from typing import Any

from app.analysis.types import BarData


class DonchianBreakoutStrategy:
    """Donchian channel breakout strategy.

    Features:
    - N-period high/low channel breakout
    - Risk-based position sizing (2% of capital)
    - Stop loss and take profit
    """

    def __init__(
        self,
        cta_engine: Any,
        strategy_name: str,  # noqa: ARG002
        vt_symbol: str,  # noqa: ARG002
        setting: dict[str, Any],
    ) -> None:
        self.cta_engine = cta_engine

        self.channel_period: float = setting.get("channel_period", 20)
        self.stop_loss_pct: float = setting.get("stop_loss_pct", 0.02)
        self.take_profit_pct: float = setting.get("take_profit_pct", 0.04)
        self.risk_per_trade: float = setting.get("risk_per_trade", 0.02)

        self.high_buffer: list[float] = []
        self.low_buffer: list[float] = []
        self.close_buffer: list[float] = []

        self.entry_price: float = 0
        self.highest_price: float = 0
        self.lowest_price: float = 0
        self.pos: int = 0

    def on_init(self) -> None:
        self.high_buffer = []
        self.low_buffer = []
        self.close_buffer = []

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def on_bar(self, bar: BarData) -> None:
        if len(self.high_buffer) >= int(self.channel_period):
            channel_high = max(self.high_buffer)
            channel_low = min(self.low_buffer)

            if self.pos == 0:
                if bar.close_price > channel_high:
                    self._on_entry_signal(bar, channel_low)
            else:
                if bar.close_price < channel_low:
                    self._on_exit_signal(bar)
                else:
                    self._check_stop_take_profit(bar)

        self.high_buffer.append(bar.high_price)
        self.low_buffer.append(bar.low_price)
        self.close_buffer.append(bar.close_price)

        if len(self.high_buffer) > int(self.channel_period):
            self.high_buffer.pop(0)
            self.low_buffer.pop(0)
            self.close_buffer.pop(0)

    def _on_entry_signal(self, bar: BarData, stop_level: float) -> None:
        stop_distance = bar.close_price - stop_level
        if stop_distance <= 0:
            return

        if self.cta_engine is None:
            return

        capital: float = self.cta_engine.capital
        risk_amount = capital * self.risk_per_trade
        size = int(risk_amount / stop_distance)

        if size <= 0:
            return

        self.cta_engine.buy(bar.close_price, size)
        self.pos = size
        self.entry_price = bar.close_price
        self.highest_price = bar.close_price

    def _on_exit_signal(self, bar: BarData) -> None:
        if self.pos > 0 and self.cta_engine is not None:
            self.cta_engine.sell(bar.close_price, abs(self.pos))
            self.pos = 0

    def _check_stop_take_profit(self, bar: BarData) -> None:
        if self.pos > 0 and self.entry_price > 0:
            stop_loss = self.entry_price * (1 - self.stop_loss_pct)
            take_profit = self.entry_price * (1 + self.take_profit_pct)

            if (
                bar.close_price <= stop_loss or bar.close_price >= take_profit
            ) and self.cta_engine is not None:
                self.cta_engine.sell(bar.close_price, abs(self.pos))
                self.pos = 0

            if bar.close_price > self.highest_price:
                self.highest_price = bar.close_price

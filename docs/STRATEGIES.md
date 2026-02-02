# Trading Strategies

## Runtime Strategies (Live Trading)

### Announcement Gap Breakout Strategy

**File**: `app/strategies/announcement_gap_strategy.py:66`

Strategy that trades ASX stocks following price-sensitive announcements.

**Entry Logic**:
1. Stock made price-sensitive announcement today (tracked by `ANNOUNCEMENT_TRACKER`)
2. Positive gap percentage ( configurable via `min_gap_pct`)
3. Price exceeds 6-month high
4. Price above minimum threshold (`min_price`)
5. After 5-minute opening range completes

**Entry Order**:
- Type: Market stop order at opening range high
- Size: `position_size` (default: 100 shares)

**Exit Logic**:
- Stop loss: Day low (trailing)
- Time exit: After 3 days (`exit_days` parameter)

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_price` | 0.20 | Minimum stock price |
| `min_gap_pct` | 0.0 | Minimum gap percentage |
| `lookback_months` | 6 | Period for high calculation |
| `opening_range_minutes` | 5 | Opening range duration |
| `position_size` | 100 | Fixed position size |
| `max_positions` | 10 | Maximum concurrent positions |
| `exit_days` | 3 | Days before forced exit |

**Usage**:
```python
from app.strategies.announcement_gap_strategy import (
    AnnouncementGapBreakoutStrategy,
    register_announcement,
)

# Register announcement (done by scanner)
register_announcement("BHP", datetime.now())
```

### ASX Momentum Strategy

**File**: `app/strategies/example_strategy.py:30`

Example momentum strategy for ASX trading with risk management.

**Entry Logic**:
- Fast SMA crosses above slow SMA
- RSI below overbought level (70)
- Not exceeding max drawdown (10%)
- Not exceeding daily trade limit (10)

**Exit Logic**:
- Fast SMA crosses below slow SMA
- RSI exceeds overbought level

**Risk Management**:
- Max position size: 100 shares
- Risk per trade: 2%
- Stop loss: 2%
- Take profit: 4%
- Max daily trades: 10
- Max drawdown: 10%

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast_period` | 10 | Fast SMA period |
| `slow_period` | 20 | Slow SMA period |
| `rsi_period` | 14 | RSI calculation period |
| `rsi_overbought` | 70 | RSI overbought threshold |
| `rsi_oversold` | 30 | RSI oversold threshold |
| `fixed_size` | 100 | Fixed trade size |
| `max_position_size` | 100 | Maximum position size |
| `risk_per_trade` | 0.02 | Risk per trade (2%) |
| `stop_loss_pct` | 0.02 | Stop loss percentage |
| `take_profit_pct` | 0.04 | Take profit percentage |
| `max_daily_trades` | 10 | Maximum daily trades |
| `max_drawdown_pct` | 0.10 | Maximum drawdown |

## Backtest Strategies (Analysis)

### Donchian Breakout Strategy

**File**: `app/analysis/strategies/donchian_breakout.py:21`

Trend-following strategy using N-period channel breakouts.

**Entry Logic**:
- Close price exceeds N-period high
- Position-based risk sizing (2% of capital)

**Exit Logic**:
- Close price below N-period low
- Stop loss: 2% below entry
- Take profit: 4% above entry

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `channel_period` | 20 | Donchian channel period |
| `stop_loss_pct` | 0.02 | Stop loss percentage |
| `take_profit_pct` | 0.04 | Take profit percentage |
| `risk_per_trade` | 0.02 | Risk per trade |

**CLI Usage**:
```bash
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = ['peaches-analysis', 'backtest', 'run', 'BHP', 
           '--start-date', '2015-01-01', '--end-date', '2018-12-31',
           '--channel-period', '20']
cli()
"
```

See `.opencode/skills/cli-analysis/SKILL.md` for comprehensive CLI guide.

## Strategy Registration

To register a new runtime strategy:

1. Create strategy file in `app/strategies/`
2. Inherit from `vnpy_ctastrategy.CtaTemplate`
3. Define `parameters` and `variables` lists
4. Implement required methods: `on_init`, `on_start`, `on_stop`, `on_bar`

To register a new backtest strategy:

1. Create strategy file in `app/analysis/strategies/`
2. Inherit from `vnpy_ctastrategy.CtaTemplate`
3. Add CLI command in `app/cli/analysis_cli.py`

## Related Files

- Runtime strategies: `app/strategies/`
- Backtest strategies: `app/analysis/strategies/`
- CLI interface: `app/cli/analysis_cli.py`
- Configuration: `app/config.py`

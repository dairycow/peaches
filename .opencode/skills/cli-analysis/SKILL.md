---
name: cli-analysis
description: Practical guide for peaches-analysis CLI backtesting
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: backtesting
---

## Quick Start

Always work from the **worktree directory**, not main repo:

```bash
cd /home/hf/peaches-feature-analysis-cli

# List available symbols
uv run python -c "from app.cli.analysis_cli import cli; import sys; sys.argv = ['peaches-analysis', 'data', 'list']; cli()"

# Run backtest
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = ['peaches-analysis', 'backtest', 'run', 'BHP', '--start-date', '2024-01-01', '--end-date', '2024-12-31']
cli()
"
```

## Data Commands

### Check Data Availability

Before running backtests, verify data exists:

```bash
# List all symbols
uv run python -c "from app.cli.analysis_cli import cli; import sys; sys.argv = ['peaches-analysis', 'data', 'list']; cli()"

# Check specific symbol
uv run python -c "from app.cli.analysis_cli import cli; import sys; sys.argv = ['peaches-analysis', 'data', 'summary', 'BHP']; cli()"
```

**Important**: BHP data range is 2015-01-01 to 2025-09-05. No 2025-2026 data exists yet.

### Available Blue Chips

Commonly tested ASX symbols:
- **BHP**: 2015-01-01 to 2025-09-05 (5,540 bars)
- **CBA**: 2015-01-01 to 2025-09-05 (2,770 bars)
- **ANZ**: 2015-01-01 to 2025-09-05 (2,769 bars)
- **RIO**: Check with `data summary`

## Backtesting Commands

### Single Backtest

```bash
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = [
    'peaches-analysis', 'backtest', 'run', 'BHP',
    '--start-date', '2015-01-01',
    '--end-date', '2018-12-31',
    '--channel-period', '20',
    '--stop-loss-pct', '0.02',
    '--take-profit-pct', '0.04',
    '--risk-per-trade', '0.02',
    '--capital', '1000000'
]
cli()
"
```

### Key Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `channel_period` | 20 | Lower = more signals, higher = fewer signals |
| `stop_loss_pct` | 0.02 | 2% stop loss - tighten for smaller losses, loosen for fewer exits |
| `take_profit_pct` | 0.04 | 4% take profit - widen for bigger wins |
| `risk_per_trade` | 0.02 | 2% capital risk - affects position sizing |
| `capital` | 1,000,000 | Initial capital in AUD |

## Troubleshooting

### Zero Trades

**Symptom**: Backtest completes with 0 trades

**Debug Steps**:

1. **Add print statements to strategy** (app/analysis/strategies/donchian_breakout.py:88):
   ```python
   def on_bar(self, bar: BarData) -> None:
       if not hasattr(self, '_bar_count'):
           self._bar_count = 0
       self._bar_count += 1
       
       if self._bar_count <= 5:
           print(f"[DEBUG] Bar #{self._bar_count}: {bar.datetime.date()} Close={bar.close_price:.2f} Pos={self.pos}")
   ```

2. **Check channel calculation logic**:
   - Are you using `max(self.high_buffer)` or `max(self.high_buffer[:-1])`?
   - Donchian breakout uses previous N periods, not including current bar

3. **Verify buffer management**:
   - Append BEFORE checking condition
   - Pop AFTER if exceeding period
   - Common bug: Wrong order leads to off-by-one errors

4. **Test with shorter periods**:
   ```bash
   --channel-period 5  # More signals for debugging
   ```

### Parameter Not Applied

**Symptom**: Strategy uses default values instead of CLI arguments

**Solution**: Parameters are passed via vn.py's `add_strategy(setting=...)`. The strategy `__init__` receives settings from parent class. Don't hardcode defaults in `__init__` after `super().__init__()`.

### Missing Dependency Error

**Symptom**: `ImportError: pyarrow is required...`

**Solution**:
```bash
uv add pyarrow
```

### Import Errors When Running CLI

**Symptom**: `ModuleNotFoundError: No module named 'app.cli'`

**Solution**: Always run from worktree with full path:
```bash
# WRONG - from main repo
cd /home/hf/peaches
uv run python -m app.cli.analysis_cli ...

# CORRECT - from worktree
cd /home/hf/peaches-feature-analysis-cli
uv run python -c "from app.cli.analysis_cli import cli; cli()"
```

### Trades Not Executing

**Symptom**: Signals generated but no trades in results

**Debug Steps**:

1. **Check order flags** (app/analysis/strategies/donchian_breakout.py:119):
   ```python
   # CORRECT for backtesting
   self.buy(bar.close_price, size, stop=False)
   self.sell(bar.close_price, abs(self.pos), stop=False)
   ```

2. **Verify position sizing calculation** (app/analysis/strategies/donchian_breakout.py:121):
   ```python
   size = int(risk_amount / stop_distance)
   # Ensure size > 0
   if size <= 0:
       return
   ```

3. **Check stop distance**:
   ```python
   stop_distance = bar.close_price - stop_level
   # If stop_distance <= 0, no trade will be placed
   ```

### Poor Strategy Performance

**Symptom**: High losses despite signals

**Analysis**:

1. **Check trade list** for outlier losses:
   ```python
   # Results shown in backtest output
   # Look for single trades wiping out profits
   ```

2. **Adjust risk parameters**:
   - Tighten `stop_loss_pct`: 0.02 → 0.01
   - Widen `take_profit_pct`: 0.04 → 0.06
   - Reduce `risk_per_trade`: 0.02 → 0.01

3. **Test different channel periods**:
   - Trend following: 20-50 day channels
   - Swing trading: 5-10 day channels
   - Scalping: 1-3 day channels (data-dependent)

4. **Analyze win rate vs profit factor**:
   - High win rate + poor performance = risk/reward mismatch
   - Low win rate + poor performance = strategy not working

## Strategy Development Tips

### Donchian Breakout Logic

The correct implementation:

```python
def on_bar(self, bar: BarData) -> None:
    # Add current bar to buffer
    self.high_buffer.append(bar.high_price)
    self.low_buffer.append(bar.low_price)
    
    # Maintain buffer size
    if len(self.high_buffer) > self.channel_period:
        self.high_buffer.pop(0)
        self.low_buffer.pop(0)
    
    # Check for signal (only if we have enough data)
    if len(self.high_buffer) >= self.channel_period:
        channel_high = max(self.high_buffer)
        channel_low = min(self.low_buffer)
        
        # Signal: Close > N-day high
        if self.pos == 0 and bar.close_price > channel_high:
            self.buy(bar.close_price, size, stop=False)
        
        # Exit: Close < N-day low
        elif self.pos > 0 and bar.close_price < channel_low:
            self.sell(bar.close_price, abs(self.pos), stop=False)
```

**Key Points**:
- Append BEFORE checking buffer size
- Use `>= channel_period` for signal check
- Channel uses ALL bars in buffer (not `[:-1]`)
- Donchian breakout uses CLOSE vs channel HIGH/LOW (same day)

### Common Bugs

1. **Off-by-one in buffer management**:
   ```python
   # WRONG - checks length AFTER pop
   if len(self.high_buffer) > self.channel_period:
       self.high_buffer.pop(0)
   if len(self.high_buffer) < self.channel_period:
       return
   
   # WRONG - excluding current bar from channel
   channel_high = max(self.high_buffer[:-1])
   
   # CORRECT - uses current day's data
   channel_high = max(self.high_buffer)
   ```

2. **Wrong order of operations**:
   ```python
   # WRONG - calculates channel before adding current bar
   channel_high = max(self.high_buffer)
   self.high_buffer.append(bar.high_price)
   
   # CORRECT - adds current bar first
   self.high_buffer.append(bar.high_price)
   channel_high = max(self.high_buffer)
   ```

3. **Hardcoded parameters**:
   ```python
   # WRONG - ignores CLI args
   def __init__(self, ...):
       super().__init__(...)
       self.channel_period = 20
   
   # CORRECT - uses setting from vn.py
   def __init__(self, ...):
       super().__init__(...)  # vn.py sets attributes from setting dict
       # channel_period is already set by super().__init__
   ```

## Performance Metrics Interpretation

### Key Metrics

| Metric | Good | Bad | Notes |
|--------|------|-----|-------|
| **Total Return** | >0% | <0% | Overall profitability |
| **Sharpe Ratio** | >1.0 | <0.5 | Risk-adjusted return |
| **Max Drawdown** | <10% | >20% | Worst peak-to-trough loss |
| **Win Rate** | >50% | <40% | Percentage of winning trades |
| **Profit Factor** | >2.0 | <1.0 | Gross wins / Gross losses |

### Red Flags

1. **High win rate, poor total return**: Risk/reward mismatch (wins too small, losses too large)
2. **Profit Factor < 1**: Losing money overall
3. **Max drawdown > 30%**: Too much risk per trade
4. **Fewer than 10 trades**: Not enough data for statistical significance

## File Locations

| Item | Path |
|------|------|
| CLI entry point | `app/cli/analysis_cli.py` |
| Strategy implementations | `app/analysis/strategies/` |
| Backtest engine | `app/analysis/backtest_engine.py` |
| Data loader | `app/analysis/data_loader.py` |
| Database | `data-prod/trading.db` (→ `/opt/peaches/data/trading.db`) |
| Configuration | `app/config.py` |

## Running from Main Repo

If you must run from `/home/hf/peaches` (not worktree):

```bash
# The worktree has separate .venv and data-prod symlinks
cd /home/hf/peaches-feature-analysis-cli

# Or run via full import path from main repo
cd /home/hf/peaches
uv run python -c "
import sys
sys.path.insert(0, '/home/hf/peaches-feature-analysis-cli')
from app.cli.analysis_cli import cli
sys.argv = ['peaches-analysis', 'backtest', 'run', 'BHP', ...]
cli()
"
```

## Summary Checklist

Before running backtests:
- [ ] In worktree directory (`cd /home/hf/peaches-feature-analysis-cli`)
- [ ] Verified symbol data exists (`data summary <symbol>`)
- [ ] Checked date range is within available data
- [ ] Strategy parameters are reasonable for timeframe
- [ ] Added debug print statements if troubleshooting

After running backtests:
- [ ] Check trade count (>10 for statistical significance)
- [ ] Analyze win rate vs profit factor
- [ ] Review max drawdown
- [ ] Look for outlier trades
- [ ] Document findings

# Trading Strategies

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

To register a new backtest strategy:

1. Create strategy file in `app/analysis/strategies/`
2. Implement `on_init`, `on_start`, `on_stop`, `on_bar` methods
3. Add CLI command in `app/cli/analysis_cli.py`

## Related Files

- Backtest strategies: `app/analysis/strategies/`
- CLI interface: `app/cli/analysis_cli.py`
- Configuration: `app/config.py`

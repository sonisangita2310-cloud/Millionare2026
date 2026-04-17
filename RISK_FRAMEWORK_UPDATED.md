# Risk Management Framework - UPDATED (INSTITUTIONAL APPROACH)

## Configuration Applied

### ✅ What Changed

#### FROM (Broken):
- Risk per trade: 1.5% (too aggressive)
- Notional cap: 1% per trade ($1,000 max)
- Daily loss limit: 1% ($1,000 max)
- Result: Only 12 trades, system was choking

#### TO (Institutional):
- Risk per trade: **1.0%** (safe, proven)
- Dynamic position sizing: **NO caps** (position derives from risk+SL)
- Daily loss limit: **3.0%** ($3,000 max)
- Max concurrent trades: **4** (prevents over-leverage)

---

## Core Philosophy

### Position Sizing Formula (CORRECT)

```
Position Size = Risk Amount ÷ (Entry Price - Stop Loss)

Example 1 (Tight SL):
  Capital: $100,000
  Risk: 1% = $1,000
  SL distance: $200
  → Position = $1,000 ÷ $200 = 5 BTC

Example 2 (Wide SL):
  Capital: $100,000
  Risk: 1% = $1,000
  SL distance: $1,000
  → Position = $1,000 ÷ $1,000 = 1 BTC
```

**KEY**: Position size is PROPORTIONAL to SL distance, not capped arbitrarily

---

## Risk Controls (What We Keep)

| Control | Setting | Purpose |
|---------|---------|---------|
| Risk/Trade | 1% | Limits loss per trade to $1,000 |
| Daily Loss | 3% | Allows 3 losers max per day |
| Open Trades | 4 max | Prevents over-leverage |
| Equity Stop | Capital ≤ 0 | Prevents bankruptcy |

---

## Why This Works

✅ Tight SL (e.g., $200) → Larger position is safe
- If SL hits: only $1,000 lost
- Same risk as wide SL trade

✅ Wide SL (e.g., $800) → Smaller position automatically
- Maintains $1,000 risk limit
- System self-adjusts

✅ System freedom maintained
- Conditions trigger naturally
- No artificial position rejections
- Expected 500-2,000 trades over 2 years

---

## What We're Testing

Files Updated:
- `src/backtest_engine.py` (1% risk, 3% daily, 4 max trades)
- `src/backtest_runner.py` (removed notional cap, added concurrent limit)

Next: **FULL BACKTEST** with institutional framework

Expected Results:
- 500-2,000 trades total across 10 strategies
- ~5-15% portfolio drawdown
- Realistic Sharpe ratios (0.8-1.5)
- Trade distribution showing system health

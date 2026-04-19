# ROLLING PERFORMANCE MONITORING GUIDE

## Overview

The paper trading simulator now includes **real-time rolling performance checks** that trigger every 10 trades. This enables early detection of strategy degradation without waiting for the full test to complete.

---

## How It Works

### Automatic Checks
- After every 10 trades, the system calculates:
  - **Win Rate (WR)**: Percentage of winning trades
  - **Profit Factor (PF)**: Ratio of wins to losses
  - **Max Drawdown (DD)**: Largest equity dip from peak

### Status Indicators
Each check is labeled with one of three statuses:

| Status | Symbol | Condition | Action |
|--------|--------|-----------|--------|
| **HEALTHY** | ✅ | PF ≥ 1.0 AND WR ≥ 25% | Continue monitoring |
| **WARNING** | ⚠️ | PF < 1.0 (but ≥ 0.8) | Increase monitoring frequency |
| **CRITICAL** | 🚨 | PF < 0.8 OR WR < 25% | Stop, investigate immediately |

---

## Example Output

```
✅ ROLLING CHECK @ Trade #10 (Last 10 trades)
  Win Rate: 50.0% (target: 30%+)
  PF: 2.05x (target: 1.0x+)
  Max DD: -1.01% (target: <5%)
  P&L: $+511.01
  STATUS: HEALTHY
```

This output shows:
- Trade #10 just completed
- Using the last 10 trades (1-10)
- Win rate is 50% (excellent)
- Profit factor is 2.05x (excellent)
- Maximum drawdown is -1.01% (healthy)
- Net P&L over these 10 trades: +$511.01
- Overall status: HEALTHY (no issues)

---

## Rolling Performance History

At the end of the simulation, a summary is printed:

```
====================================================================================================
ROLLING PERFORMANCE HISTORY (Every 10 Trades)
====================================================================================================

Trades 1-10: ✅ HEALTHY
  WR: 50.0% | PF: 2.05x | DD: -1.01% | P&L: $+511.01

Trades 11-20: ⚠️ WARNING
  WR: 35.0% | PF: 0.98x | DD: -2.1% | P&L: +$45.33

Trades 21-30: ✅ HEALTHY
  WR: 40.0% | PF: 1.15x | DD: -1.8% | P&L: +$120.50

✅ FINAL STATUS: HEALTHY - Performance within expected range
```

This shows the trend across the entire simulation, allowing you to see if performance is degrading over time.

---

## What Each Metric Means

### Win Rate (WR)
- **Definition**: Percentage of trades that profit
- **Formula**: (Winning Trades ÷ Total Trades) × 100
- **Target**: 30%+ (backtest: 37.9%)
- **Red Flag**: < 25% (CRITICAL)
- **Acceptable Range**: 25%-60%

Example:
- 5 winners out of 10 trades = 50% WR
- 3 winners out of 10 trades = 30% WR ← Minimum target

### Profit Factor (PF)
- **Definition**: Ratio of total gains to total losses
- **Formula**: Sum of Wins ÷ Absolute Value of Losses
- **Target**: 1.0x+ (backtest: 1.24x)
- **Red Flag**: < 0.8x (CRITICAL), < 1.0x (WARNING)
- **Acceptable Range**: 1.0x - 3.0x

Example:
- 5 winners totaling +$300, 5 losers totaling -$150 = $300/$150 = 2.0x PF
- 5 winners totaling +$200, 5 losers totaling -$200 = $200/$200 = 1.0x PF ← Break-even
- 5 winners totaling +$100, 5 losers totaling -$150 = $100/$150 = 0.67x PF ← CRITICAL

### Max Drawdown (DD)
- **Definition**: Largest peak-to-trough decline in equity
- **Formula**: (Lowest Equity - Previous Peak) ÷ Previous Peak × 100
- **Target**: < 5% (backtest: ~3%)
- **Red Flag**: > 10% (indicates excessive risk)
- **Acceptable Range**: 0% to 5%

Example:
- Starting equity: $10,000
- Peak equity: $10,500
- Lowest point: $10,200
- Drawdown: ($10,200 - $10,500) / $10,500 = -2.9%

---

## Interpretation Guide

### ✅ HEALTHY Status
**What it means**: Strategy is performing as expected
- PF ≥ 1.0x (profitable)
- WR ≥ 25% (hits minimum threshold)
- DD controlled (typically < 3%)

**What to do**:
- Continue monitoring
- No action required
- Proceed with Phase 2

---

### ⚠️ WARNING Status
**What it means**: Strategy is unprofitable in this 10-trade window
- PF < 1.0x (losing money)
- WR might still be acceptable
- Could be temporary variance

**What to do**:
1. Review the last 10 trades:
   - Are there patterns in losers?
   - Are entries getting worse?
2. Check market conditions:
   - Is trend still present?
   - Did volatility increase?
3. Monitor next 10 trades:
   - If still WARNING after 20 trades → investigate deeper
   - If returns to HEALTHY → likely random variance

**Example**: PF 0.98x with WR 35% in trades 11-20 could just be unlucky streak

---

### 🚨 CRITICAL Status
**What it means**: Strategy is severely degraded
- PF < 0.8x (significant losses)
- OR WR < 25% (very few wins)
- Signal generation likely broken

**What to do** (IMMEDIATELY):
1. **STOP** - Pause new trade entries
2. **INVESTIGATE** - Check recent trades:
   - Are signals still being generated?
   - Are entry prices correct?
   - Are exits triggering properly?
3. **DEBUG** - Compare to backtest:
   - Run same period through backtest framework
   - Check if backtest also shows degradation
   - If backtest OK but paper trading bad → execution issue
   - If backtest also bad → market regime changed
4. **REVIEW** - Fundamental checks:
   - Is time filter working? (skip UTC 10, 17, 22)
   - Is day filter working? (skip Friday)
   - Is ATR calculation correct?
   - Is position sizing correct?

**Example**: PF 0.75x with WR 22% = clear signal that something is wrong

---

## Use Cases

### Case 1: Mixed Performance
```
Trades 1-10: ✅ HEALTHY (PF 1.8x)
Trades 11-20: ⚠️ WARNING (PF 0.95x)
Trades 21-30: ✅ HEALTHY (PF 1.1x)
```
**Interpretation**: Normal variance, strategy working. Some 10-trade windows will underperform due to random luck.
**Action**: Continue monitoring, not a concern.

---

### Case 2: Degrading Performance
```
Trades 1-10: ✅ HEALTHY (PF 1.8x)
Trades 11-20: ✅ HEALTHY (PF 1.3x)
Trades 21-30: ⚠️ WARNING (PF 0.95x)
Trades 31-40: 🚨 CRITICAL (PF 0.72x)
```
**Interpretation**: Performance declining over time - signal degradation.
**Action**: Stop, investigate. Check if market regime changed (trend reversal, volatility spike).

---

### Case 3: Immediate Failure
```
Trades 1-10: 🚨 CRITICAL (PF 0.65x, WR 20%)
```
**Interpretation**: Something is fundamentally wrong from the start.
**Action**: Stop immediately. Check:
1. Is signal generator connected properly?
2. Is data corrupted?
3. Is position sizing calculating wrong?
4. Are exits triggering at wrong prices?

---

## Practical Monitoring Strategy

### During Phase 2 (Extended Paper Trading)

**Daily Check**:
1. Run simulator for latest data
2. Look for any CRITICAL status
3. If CRITICAL: investigate immediately
4. If WARNING: log it, but continue

**Weekly Review**:
1. Print rolling history
2. Trend analysis:
   - Is WR stable or declining?
   - Is PF stable or declining?
3. If declining: check market conditions
4. Report findings

**Decision Points**:

| After N Trades | Decision Point | Thresholds |
|---|---|---|
| 10 | Initial check | Check if not immediately failing |
| 20 | Trend confirmation | Pattern emerging? |
| 30 | Statistical significance | Clear trend or random variance? |
| 40 | Final go/no-go | PF > 1.0x, WR > 32%, DD < 5%? |

---

## Technical Details

### How Metrics Are Calculated

**Win Rate (Last 10 Trades)**:
```python
winners = len([t for t in last_10_trades if t['p_l'] > 0])
wr = (winners / 10) * 100
```

**Profit Factor (Last 10 Trades)**:
```python
total_wins = sum([t['p_l'] for t in last_10_trades if t['p_l'] > 0])
total_losses = abs(sum([t['p_l'] for t in last_10_trades if t['p_l'] < 0]))
pf = total_wins / total_losses if total_losses > 0 else 0
```

**Max Drawdown (Last 10 Trades + 1 prior equity)**:
```python
equity_slice = equity_history[-(10+1):]
running_max = cumulative_maximum(equity_slice)
drawdown = ((equity_slice - running_max) / running_max) * 100
max_dd = min(drawdown)
```

---

## Output Files

All rolling checks are recorded:
- **Console output**: Printed during execution
- **Rolling history**: Printed at end of simulation
- **Paper log**: `paper_trading_log.csv` contains all trades (for manual analysis)

---

## Integration with Phase 2 Plan

Rolling performance monitoring is a **key safeguard** for Phase 2:

1. **Real-time alerts**: Detect problems early, not at week 6
2. **Trend detection**: See if strategy is degrading
3. **Data logging**: Every 10-trade checkpoint recorded
4. **Decision support**: Use rolling history to support go/no-go decision

### Phase 2 Decision Workflow

```
Week 1-2: Gather 10-20 trades
  ├─ After 10 trades: Check rolling status
  ├─ If CRITICAL: Stop, debug
  └─ If HEALTHY/WARNING: Continue

Week 3-4: Gather 30 trades total
  ├─ Review rolling history trend
  ├─ If consistent HEALTHY: On track
  ├─ If mixed HEALTHY/WARNING: Monitor
  └─ If trend degrading: Investigate

Week 5-6: Reach 40+ trades
  ├─ Final rolling performance history
  ├─ Final metrics: WR > 32%? PF > 1.0x? DD < 5%?
  └─ GO or NO-GO decision
```

---

## Troubleshooting

### Issue: All Checks Show CRITICAL
**Likely cause**: Fundamental implementation issue
**Investigation**:
1. Check if simulator is running correctly
2. Verify signal generator is connected
3. Compare to backtest results
4. Check data quality

---

### Issue: First 10 Trades HEALTHY, Then Degrades
**Likely cause**: Market regime change or data quality issue
**Investigation**:
1. Check market conditions at that point (trend reversal?)
2. Verify no data gaps
3. Compare to backtest period

---

### Issue: Oscillates Between HEALTHY and WARNING
**Likely cause**: Normal variance or skill-dependent entries
**Investigation**:
1. This is expected with small sample sizes
2. Wait for 40+ trades before making decisions
3. Review losing trades for patterns

---

## Summary

Rolling performance monitoring provides **early warning** of strategy degradation:

✅ **HEALTHY**: Strategy working as designed  
⚠️ **WARNING**: Performance dips below profitability, monitor closely  
🚨 **CRITICAL**: Strategy broken or market regime incompatible, stop immediately  

Use the rolling history to make informed Phase 2 decisions and detect issues before they become expensive.

---

*Last Updated: 2026-04-19*  
*Feature: Rolling Performance Monitoring*  
*Integration: paper_trading_simulator_v2.py*

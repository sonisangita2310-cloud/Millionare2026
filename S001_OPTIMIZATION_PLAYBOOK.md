# S001 Variants Optimization Playbook
## Achieving Profit Factor >= 1.2 for Live Trading

**Status**: Ready for Comprehensive Testing  
**Date**: April 17, 2026  
**Goal**: Identify single profitable S001 configuration and expand to portfolio

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [What We're Testing](#whats-testing)
3. [Optimization Workflow](#workflow)
4. [Quick Start](#quickstart)
5. [Detailed Testing Guide](#detailed)
6. [Result Interpretation](#interpretation)
7. [Next Steps](#nextsteps)
8. [Troubleshooting](#troubleshooting)

---

## EXECUTIVE SUMMARY {#executive-summary}

### Current State
- **System Status**: ✅ Fully Functional
- **Base Strategy**: S001 (Trend Continuation with EMA/RSI filters)
- **Entry Signal**: Price > EMA(200) AND RSI(14) in 50-70 zone
- **Exit Strategy**: ATR-based Stop Loss and Take Profit
- **Current Challenge**: PF too low (< 1.2) → Need SL/TP optimization

### Available Variants
| Set | Count | Range | Use Case |
|-----|-------|-------|----------|
| **Base** | 8 | SL: 0.8-1.2x, TP: 3.0-4.0x | Initial testing |
| **Grid** | 60 | SL: 0.5-1.5x, TP: 2.0-5.0x | Broad coverage |
| **Focused RR=3.0** | 481 | ±30% around SL=1.0 TP=3.0 | Fine tuning |
| **Focused RR=5.0** | 490 | ±30% around SL=0.8 TP=4.0 | High R:R tuning |
| **TOTAL** | 1,039 | - | Comprehensive search space |

### Success Criteria
- **Profit Factor >= 1.2**: Deployed immediately
- **Profit Factor 1.0-1.2**: Viable with position sizing caution
- **Profit Factor < 1.0**: Requires parameter tuning

### Expected Outcomes
- **Best Case**: 3-5 profitable variants → Build diversified portfolio
- **Good Case**: 1-2 profitable variants → Deploy single strategy
- **Acceptable Case**: Several 1.0-1.2 variants → Build with strict position sizing

---

## WHAT WE'RE TESTING {#whats-testing}

### S001 Strategy Parameters

**Entry Conditions** (FIXED - Do NOT modify)
```
IF price > EMA(200, 3m) + 0.1% buffer
   AND RSI(14, 1h) > 50
   AND RSI(14, 1h) < 70
   AND price > EMA(200, 1h)
THEN → Entry Signal
```

**Exit Parameters** (OPTIMIZING these)
| Parameter | Current Range | Mathematical Definition |
|-----------|--------------|-------------------------|
| **SL Multiplier** | 0.8x - 1.2x ATR | SL = Entry - (ATR × multiplier) |
| **TP Multiplier** | 3.0x - 4.0x ATR | TP = Entry + (ATR × multiplier) |
| **R:R Ratio** | 2.5:1 to 5.0:1 | TP_distance / SL_distance |

**Example**
- Entry Price: $60,000
- ATR(14): $500
- Config: SL=1.0x, TP=3.0x
  - Stop Loss = $60,000 - (500 × 1.0) = **$59,500**
  - Take Profit = $60,000 + (500 × 3.0) = **$61,500**
  - Risk = $500, Reward = $1,500
  - R:R = 3.0:1

### Profit Factor (PF) Definition
$$PF = \frac{\text{Sum of Winning Trades}}{\text{Sum of Losing Trades}}$$

**Interpretation**
- PF = 1.0: Break-even
- PF = 1.2: $1.20 profit per $1 loss ✅ **TARGET**
- PF = 1.5: $1.50 profit per $1 loss ✅ **EXCELLENT**
- PF = 2.0: $2.00 profit per $1 loss ✅ **OUTSTANDING**

### Win Rate vs Profit Factor
```
PF = Win% × AvgWin + (1-Win%) × AvgLoss

Example scenarios:
1. Win% = 50%, AvgWin = $100, AvgLoss = $50
   PF = 0.50×100 + 0.50×(-50) = 50 - 25 = $25/trade

2. Win% = 40%, AvgWin = $150, AvgLoss = $50
   PF = 0.40×150 + 0.60×(-50) = 60 - 30 = $30/trade
   ✅ Lower win rate but better risk/reward
```

---

## OPTIMIZATION WORKFLOW {#workflow}

### Phase 1: Base Variant Testing (8 variants)
**Duration**: ~30 minutes per variant  
**Data**: BTC/USDT 3m+1h, ~90 days

```
START
  ↓
[Test SL=1.0, TP=3.0]
  ↓ [PF >= 1.2?]
     ├─ YES → Found Profitable! → Go to Phase 2
     └─ NO ↓
[Test SL=1.0, TP=4.0]
  ↓
[Test SL=0.8, TP=3.5]
  ↓
[Test SL=1.2, TP=4.0]
  ↓
[Test + 4 S001E variants]
  ↓ [Any PF >= 1.2?]
     ├─ YES → Found Profitable! → Go to Phase 2
     └─ NO ↓ [Best PF = ?]
            ├─ 1.0-1.2 → Go to Phase 3a (Grid)
            └─ < 1.0 → Go to Phase 3b (Focused)
```

### Phase 2: Validate Single Best (if found in Phase 1)
**Duration**: ~1 hour

```
Run Walk-Forward Validation
  ↓
[Split: 60% train, 40% test]
  ↓
Measure PF on unseen test data
  ↓ [Overfit?]
     ├─ PF_test >= 0.8 × PF_train → ROBUST ✅
     └─ PF_test < 0.8 × PF_train → OVERFIT ⚠️
```

### Phase 3a: Grid Expansion (if base 1.0-1.2)
**Duration**: ~2-3 hours  
**Strategy**: Test 60 combinations across full SL/TP space

```
Load: S001_GRID_EXPANSION.json (60 variants)
  ↓
Run: python optimize_s001_comprehensive.py
  ↓
Analyze: Results grouped by R:R ratio
  ↓ [Found PF >= 1.2?]
     ├─ YES → Go to Phase 2 (Validate)
     └─ NO → Manually review patterns, Go to Phase 3b
```

### Phase 3b: Focused Expansion (if base < 1.0)
**Duration**: ~4-6 hours  
**Strategy**: Test 481 + 490 fine-tuned variants

```
Load: S001_FOCUSED_RR3_EXPANSION.json (481 variants)
  ↓
Run: python optimize_s001_comprehensive.py
  ↓
Analyze: Identify best 5-10 variants
  ↓ [Found PF >= 1.2?]
     ├─ YES → Go to Phase 2 (Validate)
     └─ NO ↓
            Load: S001_FOCUSED_RR5_EXPANSION.json
            ↓
            Run: python optimize_s001_comprehensive.py
            ↓
            [If still no PF >= 1.2 → Entry logic needs review]
```

### Phase 4: Deployment & Scaling
**Duration**: Ongoing  
**Approach**: Start small, scale gradually

```
Select: Best PF >= 1.2 variant
  ↓
Risk Parameters:
  • Initial: 0.01 BTC (~$500-600)
  • Daily loss limit: 1% of capital
  • Position size: 1.5% risk per trade
  ↓
Monitor: 24-48 hours
  ↓
Scale: If performance matches backtest, increase by 50%
  ↓
Portfolio: Combine 2-3 profitable variants (low correlation)
```

---

## QUICK START {#quickstart}

### Option A: Test All 8 Base Variants (RECOMMENDED FIRST)

```bash
# Step 1: Run comprehensive optimization
python optimize_s001_comprehensive.py

# Expected: 30-40 minutes
# Output: 
#   √ backtest_results/s001_optimization_YYYYMMDD_HHMMSS.csv
#   √ backtest_results/s001_optimization_YYYYMMDD_HHMMSS.json
#   √ backtest_results/s001_optimization_YYYYMMDD_HHMMSS.md
```

**Expected Output**
```
================================================================================
                    COMPREHENSIVE RESULTS ANALYSIS
================================================================================

📊 Classification:
   ✅ PROFITABLE (PF >= 1.2):        ? variants
   ⚠️  ACCEPTABLE (1.0 <= PF < 1.2):  ? variants
   ❌ UNPROFITABLE (PF < 1.0):       ? variants

📈 All Results (ranked by Profit Factor):

1. ✅ S001_RR2
    ├─ PF: 1.25 | R:R: 4.00x | Trades: 124 | Win%: 48.2%
    ├─ P&L: $2,450 | Avg Win: $45.50 | Avg Loss: $35.25
    └─ Expectancy: $19.75/trade
```

**Decision Rules**
- ✅ If ≥1 variant with PF ≥ 1.2 → Go to validation
- ⚠️ If 1-2 variants with PF 1.0-1.2 → Use grid expansion
- ❌ If all < 1.0 → Use focused expansion

### Option B: Test Grid Expansion (if base < 1.2)

```bash
# Step 1: Generate expansions
python expand_s001_variants.py

# Step 2: Test grid variants
python optimize_s001_comprehensive.py \
  --scenarios scenarios/S001_GRID_EXPANSION.json

# Expected: 1-2 hours for 60 variants
```

### Option C: Test Focused Expansions (if grid < 1.2)

```bash
# Test RR=3.0 focused
python optimize_s001_comprehensive.py \
  --scenarios scenarios/S001_FOCUSED_RR3_EXPANSION.json

# If no PF >= 1.2, test RR=5.0 focused
python optimize_s001_comprehensive.py \
  --scenarios scenarios/S001_FOCUSED_RR5_EXPANSION.json

# Expected: 4-6 hours for 481 or 490 variants
```

---

## DETAILED TESTING GUIDE {#detailed}

### Understanding the Output CSV

```
variant_id,sl_multiplier,tp_multiplier,total_trades,winning_trades,losing_trades,win_rate,
profit_factor,total_profit,avg_win,avg_loss,expectancy,rr_ratio,status

S001_RR1,1.0,3.0,124,60,64,0.484,1.15,1456.20,24.27,-22.75,1.08,3.0,ACCEPTABLE
S001_RR2,1.0,4.0,98,48,50,0.490,1.28,1872.40,39.01,-14.62,2.45,4.0,PROFITABLE
```

**Key Columns**
- `profit_factor`: **PRIMARY METRIC** - Higher is better
- `win_rate`: Percentage of winning trades
- `total_profit`: Total P&L from all trades
- `expectancy`: Average profit per trade (risk/reward weighted)
- `rr_ratio`: Risk-to-Reward ratio (fixed for each variant)
- `status`: Classification (PROFITABLE/ACCEPTABLE/UNPROFITABLE)

**Quick Analysis**
```
Highest PF:          S001_RR2 (1.28) ✅
Best Win Rate:       S001_RR4 (52.1%)
Most Profitable Trade: S001_RR3 (Avg Win $45.50)
Best Expectancy:     S001_RR1 ($22.50/trade)
```

### Analyzing Patterns

**Pattern 1: Wider stops = Higher PF**
```
S001_RR1: SL=1.0, TP=3.0 → PF=1.15
S001_RR2: SL=1.0, TP=4.0 → PF=1.28  ✅ Better
S001_RR4: SL=1.2, TP=4.0 → PF=1.12

Insight: Tighter stops (1.0x) better than loose (1.2x)
Action: Focus next grid on SL = 0.8-1.0x
```

**Pattern 2: Tight stops = More trades, lower PF**
```
S001_RR3: SL=0.8, TP=3.5 → Trades=156, PF=1.09
S001_RR1: SL=1.0, TP=3.0 → Trades=124, PF=1.15

Insight: Tighter SL generates more trades but lower quality
Action: Don't go below SL=0.8x
```

**Pattern 3: High R:R = Better profit factor**
```
SL=1.0, TP=3.0 (R:R=3.0) → PF=1.15
SL=1.0, TP=4.0 (R:R=4.0) → PF=1.28 ✅ Better
SL=1.0, TP=5.0 (R:R=5.0) → PF=?

Insight: Market rewards higher R:R targets
Action: Test wider TP ranges
```

---

## RESULT INTERPRETATION {#interpretation}

### Scenario Analysis

**Scenario A: Found 3+ PF >= 1.2 variants**
```
Status: ✅ EXCELLENT - Multiple positive edges

Action:
1. Select top 3 by Sharpe ratio or consistency
2. Run walk-forward validation on each
3. Build portfolio combining all 3 (low correlation)
4. Start deployment with 0.01 BTC each (0.03 BTC total)

Timeline:
  Week 1: 0.03 BTC monitoring
  Week 2: 0.06 BTC (if profitable)
  Week 3: 0.12 BTC (if still positive)
  Week 4+: Full portfolio deployment
```

**Scenario B: Found 1-2 PF >= 1.2 variants**
```
Status: ✅ GOOD - Core strategy identified

Action:
1. Run walk-forward validation on the best
2. Measure consistency across different market conditions
3. Examine maximum drawdown (should be < 10%)
4. Start deployment with 0.01 BTC single variant
5. Consider adding S001 variants with 1.0-1.2 PF for diversification

Timeline:
  Week 1: 0.01 BTC of profitable variant
  Week 2: 0.02 BTC (if profitable)
  Week 3: 0.04 BTC + 0.01 BTC of secondary variant
  Week 4+: Full deployment as data confirms
```

**Scenario C: Found 3-5 with PF 1.0-1.2, none >= 1.2**
```
Status: ⚠️ ACCEPTABLE BUT RISKY - Market is favorable but not strong

Action:
1. Use grid expansion to find PF >= 1.2
2. If found → Follow Scenario B
3. If not found again → Consider entry logic improvements
   - Filter by volatility (only trade when ATR expanding)
   - Add momentum confirmation (MACD/slope)
   - Require higher RSI separation (must be < 65, not 70)

Deployment Caution:
- Position sizing: 0.5% risk per trade (instead of 1.5%)
- Max exposure: 2% of capital simultaneously
- Daily loss stops: 0.5% (instead of 1%)
```

**Scenario D: All variants PF < 1.0**
```
Status: ❌ CRITICAL - Entry logic may be broken

Diagnosis:
1. Check: Are we getting enough trades? (Should be 50-100+ per 90 days)
   If < 20 trades: Entry conditions too tight
   If > 200 trades: Entry conditions too loose

2. Check: Win rate reasonable? (Should be 40-55%)
   If < 30%: Entry is catching bad moves
   If > 70%: Likely overfitting to backtest period

3. Review: Are SL/TP being hit fairly?
   Run DEBUG:
   python -c "
   import json
   with open('backtest_results/latest_results.json') as f:
       results = json.load(f)
       for trade in results['trades']:
           if trade['exit_reason'] not in ['TP', 'SL']:
               print(f'SUSPICIOUS: {trade}')
   "

Action:
- ❌ Do NOT trade yet
- Review entry condition effectiveness
- Test S001 entry logic on different symbols (ETH)
- Consider alternative strategies (we have 31 others available)
- Schedule architecture review with team
```

---

## NEXT STEPS {#nextsteps}

### If Found PF >= 1.2 (Profitable)

**Immediate (Today)**
```
1. [] Run walk-forward validation
       python walk_forward_runner.py
   
2. [] Verify not overfitting
       Check: PF_test >= 0.8 × PF_train
       
3. [] Record variant configuration
       SL Multiplier: ______
       TP Multiplier: ______
       R:R Ratio: ______
       Backtest PF: ______
       Test PF: ______
```

**Short Term (Next 24-48 hours)**
```
4. [] Set up live trading with minimal size
       Position size: 0.01 BTC
       Max daily loss: 1% of $100k = $1,000
       Trade individually, don't scale yet
       
5. [] Monitor 24 hours live
       Compare live vs backtest statistics
       Are win rates similar?
       Are P&L similar?
       Are drawdowns acceptable?
       
6. [] Document results
       Date, Trades, W/L, P&L, Drawdown
```

**Medium Term (Week 1)**
```
7. [] After 24 hours if positive, scale to 0.02 BTC
8. [] Test during different market conditions
       Bull trend (last 48 hours) ✓
       Bear trend (if occurs) ✓
       Ranging market (if occurs) ✓
       High volatility (if occurs) ✓
       
9. [] Build second variant to diversify
       Find another variant with PF >= 1.2
       Or use 1.0-1.2 variant with reduced position size
```

**Long Term (Ongoing)**
```
10. [] Portfolio optimization
        Combine 2-3 variants with low correlation
        Target: Combined Sharpe ratio > 1.5
        
11. [] Parameter tuning
        After 4 weeks, analyze distribution
        Are entry conditions still effective?
        Should we adjust RSI thresholds?
        Should we adjust EMA periods?
        
12. [] Risk management refinement
        Measure maximum drawdown
        Adjust daily loss stops accordingly
        Implement volatility-based position sizing
```

### Implementation Examples

**Example 1: Python Live Trading Setup**
```python
# config.json for live trading
{
  "strategy": {
    "name": "S001_RR2",
    "sl_multiplier": 1.0,
    "tp_multiplier": 4.0,
    "entry_conditions": {...}
  },
  "trading": {
    "symbol": "BTC/USDT",
    "position_size_btc": 0.01,
    "risk_per_trade_pct": 1.5,
    "max_daily_loss_pct": 1.0,
    "max_daily_trades": 5
  }
}
```

**Example 2: Monitoring Dashboard**
```
Daily Report - 2026-04-18
├─ Trades Today: 2
│  ├─ 10:30 → WIN:  +$180 (TP hit)
│  └─ 14:45 → LOSS: -$120 (SL hit)
├─ Daily P&L: +$60
├─ Win Rate: 50% (1W/1L)
├─ Profit Factor: 1.5
├─ Comparison to Backtest:
│  ├─ Expected: PF=1.28, +$1850/month
│  ├─ Current:  PF=1.50 (BETTER!)
│  └─ Status: ✅ ON TRACK
└─ Max Drawdown: -$280 (2.8% of capital)
```

---

## TROUBLESHOOTING {#troubleshooting}

### Issue 1: Backtest Takes Too Long

**Symptom**: Script running for > 1 hour, still fetching data

**Root Cause**: Full 2-year data fetch → Max API hits

**Solution**:
```bash
# Use cached data only (fast path)
Edit optimize_s001_comprehensive.py:
- Comment out: use_real_data=True
- Change to: use_real_data=False
- Limits to last 90 days cached data

# OR: Reduce lookback manually
python -c "
import json
conf = json.load(open('scenarios/S001_RR_OPTIMIZATION.json'))
# Add lookback_days: 60
for s in conf['scenarios']:
    s['lookback_days'] = 60
json.dump(conf, open('scenarios/S001_RR_FAST.json', 'w'), indent=2)
"
```

### Issue 2: "No Trade Generated" for a Variant

**Symptom**: Variant shows 0 trades, PF=0

**Diagnosis**: Entry conditions too strict or data misaligned

**Solution**:
```python
# Debug entry conditions
python -c "
import json
from src.backtest_scenario_parser import ConditionEvaluator

with open('scenarios/S001_RR_OPTIMIZATION.json') as f:
    config = json.load(f)
    
variant = config['scenarios'][0]  # S001_RR1
print('Entry Conditions:')
for cond in variant['entry']['conditions']:
    print(f\"  {cond}\")
print()
print('Debugging on real data:')
# Check how many candles pass each condition
"
```

### Issue 3: Results Don't Match Expectations

**Symptom**: PF much lower than expected, or no trades

**Diagnosis**: Could be data quality, timeframe misalignment, or indicator calculation

**Solution - Verify Data**:
```bash
# Check data availability
python -c "
import pandas as pd

print('Checking cached data files:')
for tf in ['3m', '1h', '4h']:
    try:
        df = pd.read_csv(f'data_cache/BTC_USDT_{tf}.csv', 
                        parse_dates=['timestamp'])
        print(f'{tf}: {len(df)} candles, {df.index.min()} to {df.index.max()}')
    except FileNotFoundError:
        print(f'{tf}: NOT FOUND')
"
```

### Issue 4: Walk-Forward Validation Fails

**Symptom**: Walk-forward PF << Backtest PF (overfitting)

**Root Cause**: Variant optimized to specific market conditions

**Solution**:
```bash
# Use less correlated variant
1. Identify top 3 variants by backtest PF
2. Run each through walk-forward
3. Select variant with best PF_test/PF_train ratio
4. Even if it's not highest overall PF, it's more robust

# OR: Ensemble approach
Combine multiple robust variants (PF_test >= 0.9 × PF_train)
This reduces overfitting risk
```

---

## FILE REFERENCE

### Scenario Files
| File | Variants | Purpose | Status |
|------|----------|---------|--------|
| `scenarios/S001_RR_OPTIMIZATION.json` | 8 | Base testing | ✅ Ready |
| `scenarios/S001_GRID_EXPANSION.json` | 60 | Broad search | ✅ Ready |
| `scenarios/S001_FOCUSED_RR3_EXPANSION.json` | 481 | Fine tuning (R:R=3) | ✅ Ready |
| `scenarios/S001_FOCUSED_RR5_EXPANSION.json` | 490 | Fine tuning (R:R=5) | ✅ Ready |

### Optimizer Scripts
| Script | Variants Tested | Duration | Output |
|--------|-----------------|----------|--------|
| `optimize_s001_comprehensive.py` | Any file | 30-40 min/variant | CSV, JSON, MD |
| `expand_s001_variants.py` | Generator | ~1 sec | Creates JSON files |
| `optimize_s001_fast.py` | Any file | 10-15 min/variant | CSV, JSON |

### Analysis Output
| File | Purpose | Generated By |
|------|---------|--------------|
| `backtest_results/s001_optimization_*.csv` | Results table | optimize_s001_comprehensive.py |
| `backtest_results/s001_optimization_*.json` | Detailed metrics | optimize_s001_comprehensive.py |
| `backtest_results/s001_optimization_*.md` | Markdown report | optimize_s001_comprehensive.py |

---

## SUCCESS METRICS

### For Each Variant (Green Light)
- [ ] Profit Factor >= 1.2
- [ ] Win Rate 40-55%
- [ ] Total Trades >= 50 (in 90 days backtest)
- [ ] Max Drawdown <= 20%
- [ ] Avg Win > Avg Loss × 1.5

### For Walk-Forward Validation (Green Light)
- [ ] PF_test >= 0.8 × PF_train
- [ ] Win rate consistent ±5%
- [ ] No strategy whipsaws (opposite signals)
- [ ] Profitable in both train AND test periods

### For Live Trading (Green Light)
- [ ] Live PF >= 0.9 × Backtest PF (first 24 hours)
- [ ] Live Win Rate within ±10% of backtest
- [ ] Live Drawdown <= 50% of backtest max
- [ ] No major surprises (same entry/exit occurred)

---

## CONTACT & ESCALATION

**If you get stuck:**

1. **Data Issues** → Check `scenarios/temp_variant_*.json` cleanup
2. **Math Issues** → Verify ATR calculation and unit consistency
3. **Performance Issues** → Reduce lookback_days parameter
4. **No Profitable Variants** → Consider alternative entry filters

**Recommend escalating to team if:**
- All 1,039 variants test with PF < 1.0
- Walk-forward fails on all candidates
- Live trading doesn't match backtest within 20%

---

**END OF PLAYBOOK**

*Next: Execute Phase 1 testing with `python optimize_s001_comprehensive.py`*

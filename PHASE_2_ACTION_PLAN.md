# PHASE 2 - EXTENDED PAPER TRADING ACTION PLAN

## ✅ Phase 1 Complete
- ✓ Pullback v3.5 strategy locked and validated
- ✓ Paper trading simulator built with zero lookahead bias
- ✓ 11 trades executed over 73 days (Feb 3 - Apr 17, 2026)
- ✓ Validation passed: 1.71x PF, 45.5% WR, +1.43% return
- ✓ Risk management verified: 0.25% position sizing working
- ✓ Cross-validation complete: Signal frequency, exit quality, cost model all confirmed

---

## Phase 2: Extended Paper Trading (Next 30-60 Days)

### Objective
Collect 40-50 trades to reduce sample uncertainty and confirm strategy consistency

### Setup (Choose One)

#### Option A: Coinbase Paper Trading (Recommended)
- **Account**: Coinbase paper trading sandbox
- **Capital**: $10,000 (no real money)
- **Advantages**: Real API, actual exchange conditions
- **Setup time**: 1 hour

```python
# Setup steps:
1. Create Coinbase Account (free)
2. Enable Sandbox Mode
3. Set up API credentials (read-only)
4. Connect paper_trading_live.py (to be built)
5. Run continuous signal monitoring
```

#### Option B: Manual Live Signal Tracking
- **Method**: Generate signals daily, track manually
- **Capital**: Simulated on spreadsheet
- **Advantages**: No coding required
- **Disadvantages**: Manual error risk

#### Option C: Extended Simulator Run
- **Method**: Run simulator on newest data daily
- **Capital**: $10,000 simulated
- **Advantages**: Controlled environment
- **Disadvantages**: Not real-time (but closest to backtest)

**Recommendation**: Start with Option C (simulator), then move to Option A (live) after 20 trades

---

## Daily Monitoring Checklist

### Each Morning
```
1. Run paper trading update
2. Check signals generated yesterday
3. Log: trades opened, P&L
4. Calculate: Current WR, PF, DD
5. Alert if: Any trade violated assumptions
```

### Weekly Review
```
Metrics to track:
□ Win Rate (target: 30-50%, ok if 25-55%)
□ Profit Factor (target: 1.0x+, alarm if <0.8x)
□ Max Drawdown (target: <3%, alarm if >5%)
□ Avg Winner (target: $50-100, scale to account)
□ Avg Loser (target: $25-50, scale to account)
□ Trade frequency (target: 4-5 per week)
□ Slippage observed (target: <0.1%, note any >0.2%)
```

### Monthly Report
```
Generate report with:
- Trade count (target: 10-13 trades)
- Performance summary (WR, PF, return %)
- Largest winner & loser
- Equity curve (screenshot)
- Issues encountered
- Adjustments needed
```

---

## Go/No-Go Decision Criteria

### Decision Point: After 40 Trades (4-6 Weeks)

**GO to Live Trading if:**
- Win Rate: > 32% (backtest minimum is 37.9%, so 32% = 85% of target) ✅
- Profit Factor: > 1.0x (profitable, backtest is 1.24x) ✅
- Max Drawdown: < 5% (acceptable risk, backtest is 3%) ✅
- Return: > 0.5% per month (annualizes to 6%+) ✅
- Signal Frequency: 3-6 trades/week (matches backtest) ✅

**HOLD if:**
- Any metric below threshold BUT close (e.g., 31% WR vs 32% target)
- Account recovering from drawdown (wait for full recovery)
- Market in transition (sideways/unclear trend)
- Action: Run additional 2 weeks before decision

**NO-GO if:**
- Win Rate: < 25% (suggests signal breakdown)
- Profit Factor: < 0.7x (consistent losses)
- Drawdown: > 10% (excessive risk)
- Return: Negative for month (strategy not working)
- Signal Frequency: < 2 or > 8 trades/week (signal gen issue)
- Action: Stop, debug signal generator, return to backtest

---

## What Can Go Wrong

### 1. Lower Win Rate in Paper Trading
**Possible causes**:
- Market regime changed (less pullbacks)
- Signal generator needs tuning
- Execution slippage higher than modeled
- Entry timing slightly off

**Solution**: Review losing trades, compare entry prices to backtest, check if time filters are catching bad entries

### 2. Higher Drawdown Than Expected
**Possible causes**:
- Unlucky streak (statistically possible)
- Position sizing miscalculated
- Exit prices worse than modeled

**Solution**: Check position sizes match 0.25% risk, verify stop losses are being hit at correct price

### 3. Trades Fewer Than Expected
**Possible causes**:
- Signal generator has bug
- Time filters too aggressive
- Market not generating pullback setups

**Solution**: Debug signal generation, check if RSI/pullback conditions being met

### 4. Exchange Fails or Data Issue
**Possible causes**:
- API connection lost
- Data feed interrupted
- Server issues

**Solution**: Implement error handling, daily connection check, fallback to manual monitoring

---

## Code to Build (If Using Live API)

### paper_trading_live.py (To be built)
```python
class LivePaperTrader:
    """Connect to exchange API for live signal monitoring"""
    
    def __init__(self, exchange, sandbox_mode=True):
        # Initialize API connection
        # Load pullback_signal_generator_v35
        # Start monitoring loop
    
    def monitoring_loop(self):
        # Every hour:
        # 1. Fetch latest candle data
        # 2. Run signal generator
        # 3. If signal: Log trade entry
        # 4. Update open position tracking
        # 5. Check for SL/TP exits
        # 6. Update equity curve
    
    def generate_report(self):
        # Calculate: WR, PF, return %, DD
        # Print daily/weekly summary
        # Check against go/no-go criteria
```

**Note**: Only needed if doing live API connection. Simulator can run without.

---

## Success Scenario (Best Case)

### Week 1-2 (5-7 trades)
- WR: 42% (early trades lucky)
- PF: 1.6x (hot start)
- Action: Increase monitoring to ensure not getting overconfident

### Week 3-4 (10-13 trades total)
- WR: 38% (normalizing to backtest)
- PF: 1.35x (settling in)
- Return: +0.8% (on track)
- Action: Continue monitoring, start planning for Phase 3

### Week 5-6 (40+ trades total)
- WR: 36% (stable)
- PF: 1.28x (solid)
- Return: +1.2% monthly (6% annualized)
- Action: ✅ GO to Phase 3 - Live Trading

### Outcome
After 6 weeks: $10,000 → $10,120 simulated return, ready for live deployment ✓

---

## Failure Scenario (Problem Case)

### Week 1-2
- WR: 28% (below target)
- Action: Review losing trades, check signal generation

### Week 3-4
- WR: 25% (trend worsening)
- PF: 0.8x (not profitable)
- Return: -0.5% (losing money)
- Action: STOP, debug signal generator

### Problem Investigation
```
Questions to ask:
1. Are pullback detection thresholds still valid?
2. Is RSI filter too strict/loose?
3. Is time-of-day filter excluding good trades?
4. Is trend strength check correct?
5. Is ATR calculation different from backtest?
```

### Recovery Plan
```
If issue found:
1. Document the problem
2. Verify with historical data
3. If backtest still shows 1.24x PF, issue is environment not strategy
4. Adjust environment/API connection
5. If backtest fails, issue is strategy (go back to v3.5 lock)
```

---

## File Organization

### Phase 2 Working Files
```
d:\Millionaire 2026\
├── paper_trading_simulator_v2.py (daily run)
├── pullback_signal_generator_v35.py (locked, DO NOT MODIFY)
├── PHASE_2_PAPER_TRADING_LOG.md (daily update)
├── PHASE_2_WEEKLY_REPORT_*.md (weekly updates)
└── paper_trading_live_data/ (optional, for manual tracking)
```

### What NOT to Modify
```
❌ pullback_signal_generator_v35.py
❌ backtest_pullback_strategy.py
❌ Exit parameters (SL, TP)
❌ Position sizing (0.25% risk)
❌ Time filters
```

### What CAN Track/Update
```
✅ Daily paper trading results
✅ Weekly performance metrics
✅ Monitoring logs
✅ Issue notes
✅ Environmental fixes only
```

---

## Phase 3 Readiness (After Phase 2 Success)

### Prerequisites
- [ ] Completed 40+ trades in paper trading
- [ ] WR confirmed > 32%
- [ ] PF confirmed > 1.0x
- [ ] Max DD confirmed < 5%
- [ ] Signal frequency stable (4-5/week)
- [ ] All go/no-go criteria met

### Phase 3 Setup (1 week)
```
1. Set up real exchange account (Coinbase/Kraken)
2. Fund with 0.01 BTC (~$800 @ $80k price)
3. Configure order manager
4. Set up monitoring alerts
5. Do final system check
6. Start live trading with 0.005 BTC position sizing
```

### Phase 3 Monitoring
```
- Daily: Check if orders filled, P&L correct
- Weekly: WR, PF, return %, drawdown
- Stop-loss triggers: Daily loss > 1% → pause entries
- Weekly loss > 2% → review signals
- Monthly loss > 5% → pause all trading
```

---

## Document Templates (For Tracking)

### Daily Log Entry
```markdown
## Date: 2026-04-18
**Trades**
- Entry 1: [Signal Y/N, Trade Y/N, Price, Position]
- Exit 1: [Price, P&L, SL/TP]

**Metrics (Running)**
- Total Trades: 12
- Win Rate: 41.7%
- Profit Factor: 1.55x
- Return: +1.62%
- Max DD: -1.2%

**Notes**
- [Any issues or observations]
```

### Weekly Report Template
```markdown
# Week of April 18-24, 2026

## Summary
- Trades: 5
- Winners: 2 (40%)
- Losers: 3
- Net P&L: +$45

## Metrics
- Cumulative WR: 42% (12/26 trades)
- Cumulative PF: 1.6x
- Return: +1.8%
- Max DD: -1.2%

## Issues
- None

## Next Week Plan
- Continue monitoring
- Target: 3-5 more trades
```

---

## Key Reminders

1. **DO NOT modify strategy parameters** - Strategy is locked (STRICT MODE)
2. **DO NOT optimize on paper trading results** - This would curve-fit
3. **DO track all trades** - Need comprehensive log for Phase 3 decision
4. **DO check daily** - Early detection of issues is critical
5. **DO report weekly** - Weekly summaries prevent missing trends

---

## Contact/Escalation Points

| Issue | Action | Timeline |
|-------|--------|----------|
| WR drops below 25% | Review trades, check signal gen | 1 day |
| PF drops below 0.8x | Debug exit logic, check fills | 1 day |
| DD exceeds 5% | Pause new entries, investigate | 2 hours |
| API connection fails | Check logs, restart connection | 1 hour |
| Unclear what's wrong | Compare to backtest metrics | 1 day |

---

## Success Path Forward

```
Phase 1 (COMPLETE) ✅
  Paper Trading Simulator
  11 trades, 1.71x PF
  Validation PASSED
            ↓
Phase 2 (NEXT - 30-60 days)
  Extended Paper Trading
  Target: 40+ trades
  Decision point: Go/No-Go
            ↓ (if successful)
Phase 3 (LIVE - 4+ weeks)
  Live Trading
  0.005 BTC positions
  Real capital validation
            ↓ (if successful)
Phase 4 (SCALE - ongoing)
  Scale to 0.01-0.05 BTC
  Monitor monthly: 2%+ return
  Adjust with market regime
```

---

*Plan created: 2026-04-17*  
*Estimated start date: 2026-04-18*  
*Estimated Phase 2 completion: 2026-05-29 (6 weeks)*  
*Target Phase 3 start: 2026-05-30*

**Status: READY FOR PHASE 2 EXECUTION** ✅

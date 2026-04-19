# ROLLING PERFORMANCE MONITORING - QUICK REFERENCE

## Status Codes at a Glance

| Status | Symbol | Meaning | Action |
|--------|--------|---------|--------|
| ✅ HEALTHY | ✅ | PF ≥ 1.0x, WR ≥ 25% | Continue normally |
| ⚠️ WARNING | ⚠️ | PF < 1.0x (but ≥ 0.8x) | Increase monitoring |
| 🚨 CRITICAL | 🚨 | PF < 0.8x OR WR < 25% | STOP & INVESTIGATE |

---

## Output Interpretation

### What You'll See (Every 10 Trades)

```
✅ ROLLING CHECK @ Trade #20 (Last 10 trades)
  Win Rate: 45.0% (target: 30%+)
  PF: 1.15x (target: 1.0x+)
  Max DD: -2.5% (target: <5%)
  P&L: $+89.50
  STATUS: HEALTHY
```

**Read as**: 
- After 20 trades have completed
- Last 10 trades (11-20) show:
  - 4-5 wins out of 10 (45% win rate)
  - Total wins ÷ total losses = 1.15x ratio
  - Biggest dip in equity was -2.5%
  - Made $89.50 on these 10 trades
  - Overall: Working as expected ✅

---

## Thresholds (Memorize These)

### CRITICAL Triggers 🚨
**Stop everything if you see**:
- PF drops below 0.8x
- Win rate drops below 25%

### WARNING Triggers ⚠️
**Pay attention if you see**:
- PF drops below 1.0x
- (Even if WR is still OK)

### HEALTHY 
**Keep going if you see**:
- PF stays at 1.0x or higher
- Win rate stays at 25% or higher

---

## Phase 2 Checklist

### Daily (After Running Simulator)
- [ ] Check for any 🚨 CRITICAL status → STOP if found
- [ ] Note any ⚠️ WARNING status → Log for review
- [ ] Update daily log with latest check

### Weekly (Friday)
- [ ] Print rolling history summary
- [ ] Trend analysis:
  - Are statuses improving? (bad → warning → healthy)
  - Are statuses declining? (healthy → warning → critical)
  - Are they stable?
- [ ] Update weekly report

### Decision Points

**After 10 trades**:
- Status should be HEALTHY or WARNING
- If CRITICAL: Something is wrong

**After 20 trades**:
- Should start seeing pattern (consistent status)
- If oscillating wildly: Normal variance

**After 30 trades**:
- Clear trend should emerge
- Decision guidance becoming clear

**After 40 trades**:
- FINAL DECISION based on rolling history
- Use full summary to decide GO/NO-GO

---

## Problem Quick-Fix

### 🚨 CRITICAL Alert Appeared
1. **Immediate**: Note the trade number
2. **Within 1 hour**: Review those 10 trades
   - Are entry prices wrong?
   - Are exits triggering correctly?
   - Are position sizes too large?
3. **Within 4 hours**: Compare to backtest
   - Run backtest on same period
   - If backtest also shows issues → market problem
   - If backtest OK but paper bad → execution issue
4. **Within 24 hours**: Decide to continue or stop

### ⚠️ WARNING Alert
1. **Same day**: Note which trades caused it
2. **Next trading day**: Review pattern
3. **Continue monitoring**: See if returns to HEALTHY
4. **After 20 trades**: If still WARNING → deeper review

---

## Example Daily Log

```markdown
## April 19, 2026

**First 10 trades complete**
- Status: ✅ HEALTHY
- PF: 2.05x (excellent)
- WR: 50% (excellent)
- Plan: Continue trading

## April 21, 2026

**Second 10 trades complete**
- Status: ⚠️ WARNING
- PF: 0.95x (below 1.0x threshold)
- WR: 35% (still acceptable)
- Note: Market more sideways, fewer pullbacks
- Plan: Monitor closely, should recover

## April 23, 2026

**Third 10 trades complete**
- Status: ✅ HEALTHY
- PF: 1.10x (recovered)
- WR: 40% (stable)
- Note: Market trending again, signal quality back
- Plan: Continue normally
```

---

## Trading Decision Tree

```
EXECUTE SIMULATOR
        ↓
CHECK FOR 🚨 CRITICAL?
    ├─ YES → STOP IMMEDIATELY
    │        Contact researcher
    │        Do NOT trade further
    │
    └─ NO → Continue
            ↓
        CHECK FOR ⚠️ WARNING?
            ├─ YES → LOG IT
            │        Review trades
            │        Keep monitoring
            │
            └─ NO (✅ HEALTHY)
                ↓
            CONTINUE NORMAL OPERATION
            LOG ROLLING CHECK
```

---

## Communicating Status

When reporting Phase 2 progress:

**Email/Chat Format**:
```
Phase 2 Update - Trade #20
Status: ✅ HEALTHY
- Win Rate: 45% (7 winners, 3 losers)
- PF: 1.15x (total wins > total losses)
- Drawdown: -2.5% (acceptable)
- P&L: +$89.50
Plan: Continue to trade #30 checkpoint
```

---

## FAQ

**Q: What if I get WARNING on first check?**  
A: WARNING on first 10 trades is possible. Continue and monitor. If returns to HEALTHY by 20 trades, likely just variance. If stays WARNING, investigate.

**Q: How bad is a drawdown of -5%?**  
A: Still within acceptable range for HEALTHY status. Becomes concerning at -10%+.

**Q: Can I ignore WARNING and keep trading?**  
A: Yes, but increase monitoring. If next check is still WARNING or CRITICAL, investigate. Don't ignore multiple WARNINGs in a row.

**Q: What does CRITICAL mean exactly?**  
A: Either (1) losing 20%+ of money (PF < 0.8x) OR (2) winning fewer than 2 out of 10 trades (WR < 25%). Something is seriously wrong. Stop and debug.

**Q: Can I modify thresholds?**  
A: NO. These are locked in STRICT MODE. Modifying them would be curve-fitting to the current run.

---

## Key Takeaway

Use rolling checks to detect problems **early**, not late.

- ✅ HEALTHY = On track, continue
- ⚠️ WARNING = Caution flag, monitor closely  
- 🚨 CRITICAL = Stop, something wrong

**Don't wait for the final 40-trade summary** to realize things went wrong at trade 25. Rolling checks catch issues in real-time.

---

*Quick Reference - Keep This Handy During Phase 2*  
*Last Updated: April 19, 2026*

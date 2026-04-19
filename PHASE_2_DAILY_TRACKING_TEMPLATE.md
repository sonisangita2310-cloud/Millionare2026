# PHASE 2 - DAILY ROLLING MONITORING LOG TEMPLATE

Use this template to track rolling performance checks during Phase 2 extended paper trading.

---

## Daily Log Entry Template

```markdown
# Phase 2 Daily Log - [DATE: YYYY-MM-DD]

## Summary
- **Date**: [Date]
- **Trades Completed Today**: [N trades]
- **Total Trades to Date**: [N total]
- **New Checkpoints**: [Yes/No - did we hit a 10-trade checkpoint?]

## Rolling Checks Completed Today

### Checkpoint 1 (if hit today)
- **Checkpoint**: Trades [N-9] to [N]
- **Status**: ✅ HEALTHY / ⚠️ WARNING / 🚨 CRITICAL
- **Metrics**:
  - Win Rate: [X]% (target: 30%+)
  - PF: [X]x (target: 1.0x+)
  - Max DD: [X]% (target: <5%)
  - P&L: $[+/-X]
- **Notes**: [Any observations about this checkpoint]
- **Action**: Continue / Monitor / Investigate

### Checkpoint 2 (if hit today)
[Same format as above]

## Overall Phase 2 Status

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Trades | [N] | 40+ | ✅/⚠️/🚨 |
| Current WR | [X]% | 30%+ | ✅/⚠️/🚨 |
| Current PF | [X]x | 1.0x+ | ✅/⚠️/🚨 |
| Recent DD | [X]% | <5% | ✅/⚠️/🚨 |
| Overall Status | [Status] | HEALTHY | ✅/⚠️/🚨 |

## Issues or Observations
- [Any problems or interesting patterns noted today]
- [Market conditions observed]
- [Signal quality assessment]
- [Execution quality assessment]

## Plan for Next Day
- [ ] Continue trading normally
- [ ] Increase monitoring (some concern)
- [ ] Review signals before trading (warning detected)
- [ ] DEBUG before trading (critical alert)
- [ ] PAUSE trading (major issues detected)

## Researcher Notes
[Space for additional commentary or analysis]
```

---

## Weekly Summary Template

```markdown
# Phase 2 Weekly Report - Week [N]
**Period**: [Start Date] to [End Date]

## Weekly Statistics
| Metric | Week N | Target | Trend |
|--------|--------|--------|-------|
| Trades | [N] | 8-13 | ↑/→/↓ |
| Win Rate | [X]% | 30%+ | ↑/→/↓ |
| Profit Factor | [X]x | 1.0x+ | ↑/→/↓ |
| Return | [X]% | +0.5% | ↑/→/↓ |
| Drawdown | [X]% | <5% | ↑/→/↓ |

## Rolling Checkpoints This Week
- Checkpoint [N]: Status [✅/⚠️/🚨]
- Checkpoint [N]: Status [✅/⚠️/🚨]
- Checkpoint [N]: Status [✅/⚠️/🚨]

## Trend Analysis
- **WR Trend**: [Improving/Stable/Declining]
- **PF Trend**: [Improving/Stable/Declining]
- **DD Trend**: [Improving/Stable/Worsening]

## Market Context
- Price action: [Trending up/down/sideways]
- Volatility: [Low/Normal/High]
- Pullback quality: [Good/Average/Poor]

## Issues Encountered
- [Any WARNINGS or problems]
- [Resolution actions taken]

## Status for Next Week
- [ ] ON TRACK - Continue trading normally
- [ ] MONITORING - Some concern, keep watching
- [ ] INVESTIGATING - Issues detected, reviewing
- [ ] PAUSED - Critical alert, frozen pending investigation

## Decision Point Check (If Applicable)
- [ ] Reached 40 trades → Time for GO/NO-GO decision
- [ ] Latest rolling history attached
- [ ] GO/NO-GO: [GO / NO-GO / HOLD FOR MORE DATA]
```

---

## Monthly Executive Summary Template

```markdown
# Phase 2 Monthly Report - [Month/Year]

## Overall Results
- **Total Trades**: [N] (Target: 12-18 per month)
- **Total P&L**: $[+/-X] 
- **Return**: [X]%
- **Win Rate**: [X]%
- **Profit Factor**: [X]x

## Rolling Performance
- **Best Week**: [Week N] - [Status]
- **Worst Week**: [Week N] - [Status]
- **Consistency**: [Stable/Variable/Degrading]

## Status Progression
```
Week 1: [✅/⚠️/🚨]
Week 2: [✅/⚠️/🚨]
Week 3: [✅/⚠️/🚨]
Week 4: [✅/⚠️/🚨]
```

## Major Events
- [Any CRITICAL alerts and resolutions]
- [Market regime changes observed]
- [Signal quality changes]

## Decision & Recommendation
- **GO/NO-GO Status**: [GO / NO-GO / UNDECIDED]
- **Confidence Level**: [High / Medium / Low]
- **Recommendation**: [Proceed to Phase 3 / Continue Phase 2 / Halt & Debug]
- **Risk Assessment**: [Low / Moderate / High]
```

---

## Daily Monitoring Checklist

Print this and check off daily:

```
Daily Phase 2 Monitoring Checklist - ____/____/____

Before Running Simulator
☐ Verify latest market data is available
☐ Check system is ready (Python, dependencies)
☐ Review previous day's log

During Simulation
☐ Monitor for any error messages
☐ Take note of entry signals
☐ Watch for exit triggers

After Simulation Completes
☐ Check for 🚨 CRITICAL alerts → IF YES: STOP & INVESTIGATE
☐ Check for ⚠️ WARNING alerts → IF YES: Note and monitor
☐ Verify ✅ HEALTHY status (or acceptable variance)
☐ Record metrics in daily log
☐ Export CSV for trade analysis
☐ Update weekly summary with today's results

Status Decisions
☐ Continue normally (✅ HEALTHY)
☐ Increase monitoring (⚠️ WARNING)
☐ Halt & investigate (🚨 CRITICAL)
☐ Other: _________________

Researcher Notification
☐ Send daily status email if any issues
☐ Schedule review call if multiple WARNINGs
☐ Escalate CRITICAL immediately

End of Day
☐ All logs updated
☐ CSV backed up
☐ Tomorrow's targets set
☐ Ready for next run
```

---

## Example Completed Daily Log

```markdown
# Phase 2 Daily Log - 2026-04-22

## Summary
- **Date**: April 22, 2026
- **Trades Completed Today**: 2 new trades (Trade #18, #19)
- **Total Trades to Date**: 19
- **New Checkpoints**: No (next checkpoint at Trade #20)

## Rolling Checks Completed Today
None yet - will hit 20-trade checkpoint tomorrow

## Overall Phase 2 Status

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Trades | 19 | 40+ | ✅ On track |
| Current WR | 42% (8/19) | 30%+ | ✅ Excellent |
| Current PF | 1.42x | 1.0x+ | ✅ Excellent |
| Recent DD | -1.8% | <5% | ✅ Healthy |
| Overall Status | HEALTHY | HEALTHY | ✅ GOOD |

## Issues or Observations
- Market continues strong uptrend
- Pullback signals still high quality
- Both trades today hit take profit
- No execution issues observed

## Plan for Next Day
- [x] Continue trading normally
- [ ] Increase monitoring (some concern)
- [ ] Review signals before trading (warning detected)
- [ ] DEBUG before trading (critical alert)
- [ ] PAUSE trading (major issues detected)

## Researcher Notes
Strategy performing well. Rolling checkpoint #2 will occur after Trade #20 (expected tomorrow or next day). Current trajectory: Likely to exceed GO criteria by end of Phase 2.
```

---

## Rolling Check Recording Format

When a rolling check occurs, record it like this:

```
CHECKPOINT RECORD - Trade #20

Date/Time: 2026-04-23 08:45 UTC
Checkpoint: Trades 11-20
Status: ⚠️ WARNING

Metrics:
  Win Rate: 35% (7 winners, 3 losers in this batch)
  PF: 0.98x (just below profitability threshold)
  Max DD: -2.5%
  Total P&L: +$42.50

Action Taken: Logged warning, continuing to monitor. Market somewhat sideways this batch, normal variance expected.

Follow-up: Will review at next checkpoint if WR/PF trend continues down.
```

---

## What to Track for Go/No-Go Decision

At trade #40 decision point, compile:

1. **Rolling Check History**: All 4 checkpoints (10, 20, 30, 40)
2. **Trend Analysis**: Improving? Stable? Degrading?
3. **Status Distribution**: How many ✅ vs ⚠️ vs 🚨?
4. **Edge Consistency**: Does backtest edge show up in paper trading?
5. **Risk Management**: Are stops working? Drawdowns reasonable?

**Decision Grid**:
```
ROLLING CHECK STATUS:
Trades 1-10:   ✅ HEALTHY
Trades 11-20:  ✅ HEALTHY  
Trades 21-30:  ✅ HEALTHY
Trades 31-40:  ✅ HEALTHY
→ DECISION: GO to Phase 3 (Perfect record)

---

ROLLING CHECK STATUS:
Trades 1-10:   ✅ HEALTHY
Trades 11-20:  ⚠️ WARNING (but recovered)
Trades 21-30:  ✅ HEALTHY
Trades 31-40:  ✅ HEALTHY
→ DECISION: GO to Phase 3 (Normal variance)

---

ROLLING CHECK STATUS:
Trades 1-10:   ✅ HEALTHY
Trades 11-20:  ⚠️ WARNING
Trades 21-30:  ⚠️ WARNING
Trades 31-40:  🚨 CRITICAL
→ DECISION: NO-GO (Degrading performance)

---

ROLLING CHECK STATUS:
Trades 1-10:   🚨 CRITICAL
Trades 11-20:  🚨 CRITICAL
Trades 21-30:  🚨 CRITICAL
Trades 31-40:  🚨 CRITICAL
→ DECISION: NO-GO (Immediate halt)
```

---

## File Management

### Files to Create/Update Daily
- `PHASE_2_DAILY_LOG_[YYYY-MM-DD].md` - Daily entry
- `paper_trading_log.csv` - Trade export (auto-generated)

### Files to Review Weekly
- `PHASE_2_WEEKLY_REPORT_WEEK_[N].md` - Weekly summary
- All daily logs from that week

### Final Decision Package
- `PHASE_2_ROLLING_HISTORY_SUMMARY.md` - Complete rolling check history
- All rolling checkpoints compiled
- GO/NO-GO decision documented

---

## Reminder: STRICT MODE

**DO NOT**:
- Change strategy parameters based on rolling checks
- Modify thresholds (CRITICAL, WARNING, HEALTHY)
- Optimize entries/exits mid-Phase 2
- Add new filters or indicators

**ONLY**:
- Track metrics
- Monitor for issues
- Document performance
- Make GO/NO-GO decision at end

---

*Phase 2 Logging Template*  
*Last Updated: April 19, 2026*  
*Status: Ready for Phase 2 Deployment*

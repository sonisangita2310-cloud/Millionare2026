# MONITORING & ALERTING - QUICK REFERENCE

## 5 Features Added to Phase 2 System

### 1. TRADE SUMMARY LOGGER
```
[TRADE SUMMARY]
  Trade #: X
  Type: LONG
  Entry: $X @ timestamp
  Exit: $X @ timestamp (SL/TP)
  Duration: X hours
  Position: X BTC
  P&L: $+X
  Equity: $X
  Consecutive Losses: X
```

**When**: After every trade exit (SL or TP)  
**File**: Console output  
**Code**: `_print_trade_summary(trade)` - Lines 160-177

---

### 2. DAILY SUMMARY
```
[DAILY SUMMARY] YYYY-MM-DD
  Trades Today: X
  Wins: X | Losses: X
  Win Rate: X%
  Net P&L: $+X
  Current Equity: $X
```

**When**: Every 24 hours automatically  
**File**: Console output  
**Code**: `_print_daily_summary()` - Lines 192-218

---

### 3. SYSTEM HEALTH ALERTS

#### Alert 1: Consecutive Losses
```
[WARNING] 3 consecutive losses detected
          Last 3 trades all lost. Review signals.
```
**Trigger**: 3 or more losses in a row  
**Action**: Manual review recommended

#### Alert 2: Drawdown Exceeded
```
[ALERT] Drawdown threshold exceeded: 5.2%
        Max equity: $X | Current: $X
```
**Trigger**: Drawdown > 5%  
**Action**: Monitor carefully

#### Alert 3: No Trades
```
[INFO] No signals in last 48 hours (threshold: 48h)
```
**Trigger**: 48+ hours without a trade  
**Action**: Informational only

**Code**: `_check_health_alerts(trade)` - Lines 179-191

---

### 4. FILE LOGGING (CSV)
```
File: trading_journal.csv

timestamp,type,entry_price,exit_price,pnl,equity,result
2026-04-19 10:00:00,TP,42150.00,42480.00,85.50,585.50,WIN
2026-04-19 14:00:00,SL,42250.00,42100.00,-95.25,490.25,LOSS
2026-04-19 18:00:00,TP,42050.00,42400.00,125.75,616.00,WIN
```

**When**: After every trade exit  
**File**: trading_journal.csv (auto-created)  
**Code**: `_log_trade_to_csv(trade)` - Lines 143-158

---

### 5. STARTUP STATUS DISPLAY
```
[SESSION STATUS]
  Mode: LIVE PAPER TRADING
  Capital: $500.00
  Last State: Loaded (or New)
  Strategy: Pullback v3.5 (LOCKED)
  Monitoring: Enabled
  Logging: trading_journal.csv
```

**When**: On system startup  
**File**: Console output  
**Code**: `_print_session_status()` - Lines 234-245

---

## Integration Points

### Startup
```python
# In __init__():
self._initialize_journal()  # Create CSV

# In run_live_trading():
self._print_session_status()  # Show status
```

### After Every Trade Exit (SL or TP)
```python
self._log_trade_to_csv(trade)      # Log to CSV
self._print_trade_summary(trade)   # Print summary
self._check_health_alerts(trade)   # Check alerts
```

### Every 24 Hours
```python
self._print_daily_summary()  # Print daily metrics
```

### Every Candle Cycle
```python
self._check_no_trades_alert()  # Check 48h alert
```

---

## Monitoring Variables

| Variable | Tracks | Updated |
|----------|--------|---------|
| `consecutive_losses` | Loss streak | After each trade |
| `last_trade_timestamp` | Time of last exit | After each trade |
| `daily_summary_timestamp` | Last 24h summary | Every 24h |
| `max_equity` | Peak capital | After each trade |
| `journal_file` | CSV path | At startup |

---

## Console Output Order

```
[SESSION STATUS]          ← Startup
[BOT STARTED]             ← Startup

[CANDLE]                  ← Per candle
[SIGNAL]                  ← Signal detected
[TRADE] ENTRY             ← Entry executed

(hours later...)

[TRADE] EXIT              ← Exit executed
[TRADE SUMMARY]           ← Trade summary
[WARNING] / [ALERT]       ← If triggered
[ROLLING CHECK]           ← Every 10 trades

(24 hours later...)

[DAILY SUMMARY]           ← Every 24h
[INFO]                    ← If 48h+ no-trade
```

---

## CSV File Format

### Create
- Auto-created on first startup
- Headers: timestamp, type, entry_price, exit_price, pnl, equity, result

### Append
- After every trade exit
- One line per trade
- Fields: datetime, exit_type, entry $, exit $, P&L $, current equity $, WIN/LOSS

### Read
- Can import to Excel, Google Sheets, Python pandas
- Complete audit trail of all trades
- Easy to calculate additional metrics

---

## No Changes to Trading Logic

✅ Entry conditions: UNCHANGED  
✅ Exit rules: UNCHANGED  
✅ Position sizing: UNCHANGED  
✅ Risk management: UNCHANGED  
✅ Strategy parameters: UNCHANGED  

**Only metrics and monitoring added**

---

## Testing Checklist

- [x] CSV created on first run
- [x] Trade summary printed after exits
- [x] Trade logged to CSV
- [x] Health alerts trigger correctly
- [x] Daily summary prints every 24h
- [x] 48h no-trade alert works
- [x] Session status shows on startup
- [x] No trading logic changed
- [x] Code compiles without errors
- [x] System operational

---

## Deployment

```bash
python live_paper_trading_system.py
```

**Output**:
- Console: All messages and summaries
- CSV: trading_journal.csv with all trades
- State: trading_state.json for crash recovery

---

## Status

✅ **MONITORING & ALERTING COMPLETE**

Ready for Phase 2 deployment with full visibility

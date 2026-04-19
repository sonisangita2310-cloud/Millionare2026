# AUDIT LOGGING & SESSION TRACKING - QUICK REFERENCE

## ✅ TWO FEATURES ADDED

**Feature 1**: Config Hash Audit Logging  
**Feature 2**: Session Tracking  

---

## FEATURE 1: CONFIG HASH AUDIT LOGGING

### On Startup
```
[CONFIG HASH]
  Hash: 16c707d4793da00f266db02412b2f6e9
  Audit Log: config_audit.log
```

### Purpose
- Verify exact configuration used
- Detect if parameters were modified
- Maintain audit trail

### Files
- **config_audit.log** - Timestamped audit trail with hash and parameters

### Format
```
[2026-04-19 12:18:51] SESSION_ID: 20260419-121851-123456
[2026-04-19 12:18:51] CONFIG_HASH: 16c707d4793da00f266db02412b2f6e9
[2026-04-19 12:18:51] Strategy: Pullback v3.5
[2026-04-19 12:18:51] SL: 1.1x ATR
[2026-04-19 12:18:51] TP: 3.2x ATR
[2026-04-19 12:18:51] Risk: 0.25%
```

---

## FEATURE 2: SESSION TRACKING

### On Startup
```
[SESSION ID]: 20260419-122257-381221
```

### Purpose
- Unique identifier per session/restart
- Enable traceability across runs
- Filter trades by session

### Format
```
YYYYMMDD-HHMMSS-microseconds
Example: 20260419-122257-381221
```

### Used In
1. **trading_journal.csv** - First column
   ```
   session_id,timestamp,type,...
   20260419-122257-381221,2026-04-19 14:00:00,TP,...
   ```

2. **config_audit.log** - With each hash entry
   ```
   [2026-04-19 12:22:57] SESSION_ID: 20260419-122257-381221
   ```

---

## STARTUP OUTPUT

When you run: `python live_paper_trading_system.py`

You will see:

```
[STRATEGY LOCKED]
  Strategy: Pullback v3.5
  ...

[SYSTEM MODE]
  Phase: VALIDATION
  ...

[CONFIG HASH]
  Hash: 16c707d4793da00f266db02412b2f6e9
  Audit Log: config_audit.log

[SESSION ID]: 20260419-122257-381221

[BOT STARTED] 2026-04-19 12:22:57 - LIVE TRADING ACTIVE
```

---

## FILES & LOCATIONS

| File | Location | Purpose |
|------|----------|---------|
| config_audit.log | Root directory | Audit trail (timestamps, hashes, session IDs) |
| trading_journal.csv | Root directory | Trade log (now includes session_id column) |
| trading_state.json | Root directory | State persistence (unchanged) |

---

## VERIFICATION QUERIES

### Query 1: What hash was used for Session X?
```bash
grep "SESSION_ID: 20260419-122257-381221" config_audit.log
```
Result shows config hash immediately after

### Query 2: How many trades in Session X?
```bash
grep "^20260419-122257-381221," trading_journal.csv | wc -l
```

### Query 3: Did config change?
```bash
grep "CONFIG_HASH:" config_audit.log | sort | uniq
```
If only 1 hash: Config unchanged ✓

### Query 4: What's the CSV header?
```bash
head -1 trading_journal.csv
```
Should show: `session_id,timestamp,type,...`

---

## PYTHON EXAMPLES

### Example 1: Get Session Config
```python
import re

with open('config_audit.log', 'r') as f:
    lines = f.readlines()

# Find session
session = '20260419-122257-381221'
session_config = [l for l in lines if session in l]

for line in session_config[:7]:
    print(line.strip())
```

### Example 2: Filter Trades by Session
```python
import pandas as pd

df = pd.read_csv('trading_journal.csv')
session_trades = df[df['session_id'] == '20260419-122257-381221']

print(f"Trades: {len(session_trades)}")
print(f"Win rate: {(session_trades['result']=='WIN').sum()/len(session_trades)*100:.1f}%")
```

### Example 3: Verify Config Unchanged
```python
import re

with open('config_audit.log', 'r') as f:
    hashes = re.findall(r'CONFIG_HASH: (\w+)', f.read())

unique_hashes = set(hashes)
print(f"Unique configs: {len(unique_hashes)}")

if len(unique_hashes) == 1:
    print(f"✓ NO CHANGES - All sessions same config")
    print(f"  Hash: {list(unique_hashes)[0]}")
```

---

## KEY METHODS

### Generate Session ID
```python
system.session_id  # Access current session ID
# Format: YYYYMMDD-HHMMSS-microseconds
```

### Calculate Config Hash
```python
hash = system._calculate_strategy_hash()
# Returns: MD5 hash (32 characters)
```

### Methods Available
- `_generate_session_id()` - Create timestamp-based ID
- `_print_session_id()` - Print [SESSION ID]: XXXXX
- `_log_config_hash_to_audit()` - Log to config_audit.log
- `_print_config_hash()` - Print [CONFIG HASH]: XXXXX

---

## TRACEABILITY EXAMPLE

### Track Single Trade
```
1. Find in trading_journal.csv:
   20260419-122257-381221,2026-04-19 14:00:00,TP,...,+$85.50

2. Get session ID: 20260419-122257-381221

3. Look up in config_audit.log:
   CONFIG_HASH: 16c707d4793da00f266db02412b2f6e9
   Strategy: Pullback v3.5
   SL: 1.1x ATR
   TP: 3.2x ATR

4. Verify config unchanged:
   grep "16c707d4793da00f266db02412b2f6e9" config_audit.log
   (Shows all sessions used same hash)
```

---

## AUDIT TRAIL EXAMPLE

### Multiple Sessions
```
[2026-04-19 12:18:51] SESSION_ID: session-001
[2026-04-19 12:18:51] CONFIG_HASH: 16c707d4793da00f266db02412b2f6e9
[2026-04-19 12:18:51] Strategy: Pullback v3.5
[2026-04-19 12:18:51] SL: 1.1x ATR
[2026-04-19 12:18:51] TP: 3.2x ATR
[2026-04-19 12:18:51] Risk: 0.25%
[2026-04-19 12:18:51] ---
[2026-04-19 12:18:51] SESSION_START: session-001

[2026-04-19 12:30:00] SESSION_ID: session-002
[2026-04-19 12:30:00] CONFIG_HASH: 16c707d4793da00f266db02412b2f6e9
[2026-04-19 12:30:00] Strategy: Pullback v3.5
[2026-04-19 12:30:00] SL: 1.1x ATR
[2026-04-19 12:30:00] TP: 3.2x ATR
[2026-04-19 12:30:00] Risk: 0.25%
[2026-04-19 12:30:00] ---
[2026-04-19 12:30:00] SESSION_START: session-002
```

Both sessions use same hash ✓

---

## CSV FORMAT

### Before (Old)
```
timestamp,type,entry_price,exit_price,pnl,equity,result
2026-04-19 14:00:00,TP,42150.00,42480.00,85.50,585.50,WIN
```

### After (New)
```
session_id,timestamp,type,entry_price,exit_price,pnl,equity,result
20260419-122257-381221,2026-04-19 14:00:00,TP,42150.00,42480.00,85.50,585.50,WIN
```

Session ID added as first column

---

## CHECKING STATUS

### Verify Features Working
```bash
# Check CSV has session_id
head -1 trading_journal.csv

# Check audit log exists
ls -la config_audit.log

# Verify hash in audit log
grep "CONFIG_HASH:" config_audit.log
```

### Expected Output
```
session_id,timestamp,type,entry_price,...

config_audit.log exists

CONFIG_HASH: 16c707d4793da00f266db02412b2f6e9
```

---

## SUMMARY

| Item | Location | Purpose |
|------|----------|---------|
| **CONFIG_HASH** | Printed at startup + config_audit.log | Verify exact configuration |
| **SESSION_ID** | Printed at startup + all logs + CSV | Enable traceability |
| **config_audit.log** | Root directory | Timestamped audit trail |
| **trading_journal.csv** | Root directory | Trades with session ID |

---

## STRICT MODE: Maintained ✅

- No strategy changes
- Only logging/tracking added
- All trading logic unchanged
- VALIDATION mode still active

---

## Status

✅ **AUDIT LOGGING READY**

Both features operational:
1. Config hash logging
2. Session tracking

**Ready for Phase 2 validation**

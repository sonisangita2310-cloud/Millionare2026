# QUICK START: Phase 2 Paper Trading

## ONE-COMMAND EXECUTION

### For Fast Validation (Backtest Mode - 30 seconds)
```bash
python run_phase2_full.py
```

### For Real-Time Simulation (with candle waiting)
```python
from paper_trading_simulator_v2 import PaperTradingSimulatorV2
import pandas as pd

data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data_sim = data.iloc[-2000:].reset_index(drop=True)

sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
sim.run_simulation(verbose=True, mode='realtime')
sim.print_results()
sim.save_trades_csv()
```

---

## What to Expect

### Initial Output
```
====================================================================================================
PAPER TRADING SIMULATOR v2 - BACKTEST MODE
====================================================================================================
[BOT STARTED] System initialized successfully
Mode: BACKTEST
Period: 2026-02-03 17:00:00 to 2026-04-17 14:00:00
Initial capital: $500
Risk per trade: 0.25%
Status: Running continuously...
```

### Trading Signals
```
[CANDLE] Processed 100 candles | Time: 2026-02-07 20:00:00
[SIGNAL] LONG signal @ 2026-02-14 12:00:00
[TRADE] #1: ENTRY | Price: $69,661.09 @ 2026-02-14 13:00:00 | Position: 0.003169 BTC | SL: $69,266.60 | TP: $70,808.70 | Risk: $1.25
```

### Trade Exits
```
[TRADE] #1: EXIT TP | Entry: $69,661.09 @ 2026-02-14 13:00:00 | Exit: $70,829.95 @ 2026-02-15 07:00:00 | P&L: $+3.26 | Equity: $503.26
```

### Rolling Performance Check (Every 10 Trades)
```
[OK] ROLLING CHECK @ Trade #10 (Last 10 trades)
  Win Rate: 50.0% (target: 30%+)
  PF: 2.05x (target: 1.0x+)
  Max DD: -1.01% (target: <5%)
  P&L: $+25.55
  STATUS: HEALTHY
```

### Final Summary
```
====================================================================================================
RESULTS SUMMARY
====================================================================================================
Total Return: +1.43%
Win Rate: 45.5% (11 winners, 13 losers)
Profit Factor: 1.71x
Max Drawdown: -3.21%
Sharpe Ratio: 0.41
Trades: 24
Winning Trades: $42.50
Losing Trades: $-24.85
Average Trade: $+0.73
```

---

## Key Metrics to Monitor

### During Execution
- **Win Rate**: Should stay ≥30%
- **Profit Factor**: Should stay ≥1.0x
- **Drawdown**: Should stay <5%
- **Status**: Watch for [OK]/[WARN]/[CRITICAL]

### Every 10 Trades
- Rolling metrics update automatically
- Heartbeat every 5 minutes: [BOT ALIVE]
- Trade log saved to CSV

### Decision Point (40+ Trades)
- Final Win Rate target: ≥30%
- Final Profit Factor target: ≥1.0x
- Max Drawdown target: <5%
- Average Trade target: >0%

---

## Files Generated

```
paper_trading_log.csv          # Auto-generated trade log
REALTIME_PAPER_TRADING_DEPLOYMENT.md  # Full documentation
```

---

## Modes Explained

| Aspect | Backtest Mode | Real-Time Mode |
|--------|---------------|----------------|
| Execution | Fast (2000 candles in 30s) | Realistic (1 candle/hour) |
| Purpose | Validation, testing | Live simulation |
| Use Case | Quick checks | Extended Phase 2 |
| Processing | All candles in loop | One candle at a time |
| Waiting | No | Yes (waits for next 1H candle) |

---

## Status: READY FOR PHASE 2

✅ Real-time mode framework complete
✅ Backtest mode fast validation ready
✅ Rolling performance monitoring active
✅ Comprehensive logging enabled
✅ CSV trade export working

**Next: Run Phase 2 extended testing with $500 capital**

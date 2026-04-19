# LIVE PAPER TRADING - QUICK START GUIDE

## ONE-COMMAND DEPLOYMENT

```bash
python live_paper_trading_system.py
```

That's it. System connects to Binance, fetches live candles, processes one per hour, executes trades.

---

## Before You Start

### 1. Validate Components (1 minute)
```bash
python validate_live_system.py
```

Expect:
```
[PASS] Fetched 50 real candles from Binance
[PASS] Signal generator working
[PASS] System initialized successfully
[PASS] All parameters locked (STRICT MODE enforced)

ALL VALIDATION TESTS PASSED
```

### 2. Test Live Data (30 seconds)
```bash
python live_data_fetcher.py
```

Expect:
```
[API] Fetched 10 candles
[DATA] Latest candle: 2026-04-19 03:00:00 | Close: $75546.02
[SUCCESS] Fetched 10 candles
```

---

## What Happens When You Start

```
[BOT INITIALIZED] System ready for live trading
Initial capital: $500
Data source: LIVE Binance API (BTCUSDT 1H candles)

[BOT STARTED] 2026-04-19 14:23:45 - LIVE TRADING ACTIVE

[CANDLE] New 1H candle closed @ 2026-04-19 14:00:00
[SIGNAL] LONG signal detected
[TRADE] ENTRY | Price: $75,546.02 | Position: 0.003169 BTC | Risk: $1.25

[WAIT] Waiting 3545s for next candle...
[BOT ALIVE] Equity: $500.00 | Trades: 0 | Candles: 1
```

The system:
- ✅ Fetches real candles from Binance
- ✅ Processes only CLOSED candles
- ✅ Generates signals (pullback strategy)
- ✅ Executes trades when conditions met
- ✅ Waits ~1 hour for next candle
- ✅ Reports every 5 minutes (heartbeat)
- ✅ Checks performance every 10 trades

---

## Key Differences from Backtest

| Feature | Backtest (old) | Live (new) |
|---------|----------|--------|
| **Data** | CSV file (historical) | API (real-time) |
| **Speed** | 2000 candles in 30s | 1 candle per hour |
| **Duration** | Seconds | Weeks/months |
| **Realism** | Simulation | Actual market |
| **Lookahead** | None | None (only closed candles) |

---

## Monitoring During Execution

### Every Hour (New Candle)
System fetches latest candle, processes it, executes trade if signal

### Every 5 Minutes
```
[BOT ALIVE] 14:28:45 | Equity: $500.00 | Trades: 0 | Candles: 1
```

### Every 10 Trades (Rolling Check)
```
[OK] ROLLING CHECK @ Trade #10
  Win Rate: 50.0% (target: 30%+)
  PF: 2.05x (target: 1.0x+)
  STATUS: HEALTHY
```

### When Trade Exits
```
[TRADE] #1: EXIT TP | P&L: $+5.40 | Equity: $505.40
```

---

## Goals for Phase 2

Execute minimum **40 trades** to validate strategy on live market data:

✅ **Win Rate**: ≥30%
✅ **Profit Factor**: ≥1.0x  
✅ **Max Drawdown**: <5%
✅ **Status**: HEALTHY (rolling checks)

---

## Expected Timeline

- **Week 1**: 5-8 trades (market conditions)
- **Week 2**: 5-8 trades
- **Week 3**: Final trades → Decision point (40+ total)

**Note**: Real trading is slower than backtest. Pullback signals occur ~1-2 per day on BTC 1H timeframe.

---

## STRICT MODE: Strategy Locked

NO changes to:
- Entry logic (pullback strategy)
- Stop loss (1.1x ATR)
- Take profit (3.2x ATR)
- Position sizing (0.25% risk)
- Fees (0.1% entry/exit)

All verified at startup ✓

---

## If Something Goes Wrong

### No Data
```
[ERROR] Failed to fetch candles
```
→ Check internet connection, retry

### No Signals
```
[SIGNAL] No entry signal
```
→ Normal - pullback conditions not met. Average 1 signal/24h

### System Crashes
```
[ERROR] Exception in live trading
```
→ Restart: `python live_paper_trading_system.py`

---

## Files You'll See

```
paper_trading_log.csv        # Auto-saved trade log
LIVE_PAPER_TRADING_DEPLOYMENT.md  # Full documentation
```

---

## Exit Strategy

Press `Ctrl+C` to stop. System gracefully shuts down and prints final results:

```
====================================================================================================
LIVE PAPER TRADING RESULTS
====================================================================================================
Initial capital: $500.00
Final capital: $523.50
Total return: +4.70%
Total trades: 12
Win rate: 58.3%
Profit factor: 2.15x
```

---

## Remember

✅ Real market data (Binance API)
✅ Only closed candles (zero lookahead)
✅ One candle per hour (realistic waiting)
✅ Rolling performance checks (early warning)
✅ STRICT MODE (no strategy changes)
✅ 40+ trades minimum (statistical validity)

**Ready? Start with:**
```bash
python live_paper_trading_system.py
```

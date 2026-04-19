# PHASE 2 QUICK START CARD

## Deploy Now

```bash
cd "d:\Millionaire 2026"
python live_paper_trading_system.py
```

---

## What This Does

- Fetches 200 BTCUSDT 1H candles from Binance (live)
- Generates trading signals (Pullback v3.5 strategy)
- Enters/exits trades automatically
- Saves state after every action
- Runs 24/7 for 2-3 weeks
- Collects 40+ trades for evaluation

---

## What You'll See

```
[NEW SESSION] Starting fresh
[BOT INITIALIZED] Ready for live trading
[BOT STARTED] LIVE TRADING ACTIVE

[API] Fetched 200 candles (attempt 1/3)
[CANDLE] Processing new 1H candle
[TRADE] ENTRY @ $42,250
[TRADE] EXIT @ $42,500 (WIN)

[ROLLING CHECK] Trades: 3 | Wins: 2 | Equity: $502.50
```

---

## Safety Features

✅ **Crash Recovery** - Restarts from last saved state  
✅ **Network Retry** - 3 auto-retries on API failure  
✅ **State Corruption** - Auto-recovery from bad files  
✅ **No Lookahead** - Only closed candles processed  

---

## If System Crashes

Just restart:
```bash
python live_paper_trading_system.py
```

System will detect `[STATE LOADED]` and continue from crash point.

---

## If API Fails

System auto-retries:
```
[API ERROR] Request timeout (attempt 1/3)
[API RETRY] Waiting 60s before retry...
[API] Fetched 200 candles (attempt 2/3)
```

---

## Success Criteria (After 40+ Trades)

- ✅ Win rate ≥ 30%
- ✅ Profit factor ≥ 1.0x
- ✅ Max drawdown < 5%

**All 3**: → GO to Phase 3  
**Any fail**: → Review strategy  

---

## Configuration

**Capital**: $500  
**Risk/Trade**: 0.25% equity  
**Max Position**: 0.1 BTC  
**Entry Fee**: 0.1%  
**Exit Fee**: 0.1%  

---

## Files

**Core**:
- `live_paper_trading_system.py` - Main engine
- `live_data_fetcher.py` - Data with retry
- `pullback_signal_generator_v35.py` - Strategy (LOCKED)

**State**:
- `trading_state.json` - Auto-created, auto-saved

**Tests**:
- `test_api_retry_quick.py` - Verify system (6 tests, all passing)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Won't start | Check Python: `python --version` |
| API errors | System auto-retries (wait) |
| Crashed | Restart: `python live_paper_trading_system.py` |
| State corrupted | Auto-recovered, logs [STATE ERROR] |

---

## Monitoring

**Hourly**: Watch for `[CANDLE]` message  
**Per trade**: Watch for `[TRADE]` entry/exit  
**Every 10 trades**: Check rolling equity  
**Weekly**: Review trade log  

---

## Status

🎉 **PRODUCTION READY**

All 4 safety layers active.  
All tests passing (6/6).  
System tested for 2-3 week deployment.  

---

## Next Step

```bash
python live_paper_trading_system.py
```

**System runs continuously.**  
**Collect 40+ trades over 2-3 weeks.**  
**Evaluate and make GO/NO-GO decision.**

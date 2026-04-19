# LIVE PAPER TRADING SYSTEM - TECHNICAL SPECIFICATION

## System Overview

The live paper trading system converts the historical backtesting simulator into a production-ready paper trading engine using real Binance market data. It processes exactly ONE 1-hour candle per iteration, preventing lookahead bias and ensuring realistic execution.

---

## Component Architecture

### 1. LiveDataFetcher (`live_data_fetcher.py`)

**Purpose**: Fetch and manage real market data from Binance API

**Key Methods**:
```python
fetch_candles(verbose=False)
  → Returns: DataFrame with latest 200 BTC/USDT 1H candles
  → Raises: ConnectionError, TimeoutError (gracefully handled)
  
is_new_candle(df)
  → Returns: True if new candle detected vs last processed
  → Uses: Timestamp comparison with self.last_candle_timestamp
  
get_time_until_next_candle(verbose=False)
  → Returns: Seconds until next 1H candle close (with 30s buffer)
  → Calculation: 60 - current_minute * 60 + buffer
  
wait_for_next_candle(check_interval=30, verbose=False)
  → Blocks: Until new candle detected or timeout
  → Check frequency: Every 30 seconds
  → Progress: Reports every 60 seconds
```

**API Endpoint**:
```
GET https://api.binance.com/api/v3/klines
params: symbol=BTCUSDT, interval=1h, limit=200
```

**Error Handling**:
```python
consecutive_errors = 0
max_consecutive_errors = 5

if errors >= max_consecutive_errors:
    system.status = CRITICAL
else:
    retry_after = 60 seconds
```

**Data Format**:
```python
DataFrame with columns:
  timestamp   [datetime] - Candle close time (UTC)
  open        [float]    - Opening price
  high        [float]    - Highest price
  low         [float]    - Lowest price
  close       [float]    - Closing price
  volume      [float]    - Volume in BTC
```

---

### 2. LivePaperTradingSystem (`live_paper_trading_system.py`)

**Purpose**: Main trading engine orchestrating signal generation, position management, and trade execution

**Initialization**:
```python
__init__(initial_capital=500, risk_per_trade=0.0025, lookback_candles=200)
```

**Key State Variables**:
```python
self.current_capital        # Current available capital ($)
self.position              # Active position dict or None
self.trades                # List of completed trades
self.equity_curve          # Historical capital after each trade
self.rolling_checks        # Performance metrics every 10 trades
self.candle_history        # Latest fetched candles DataFrame
```

**Trading Parameters (STRICT MODE - LOCKED)**:
```python
self.sl_mult = 1.1         # Stop loss: 1.1x ATR below entry
self.tp_mult = 3.2         # Take profit: 3.2x ATR above entry
self.entry_slippage = 0.0003    # 0.03% slippage on entry
self.exit_slippage = 0.0003     # 0.03% slippage on exit
self.entry_fee_pct = 0.001      # 0.1% entry fee
self.exit_fee_pct = 0.001       # 0.1% exit fee
self.risk_per_trade = 0.0025    # 0.25% equity risk per trade
```

---

### 3. Signal Generation

**Workflow** (NO LOOKAHEAD):
```python
def get_signal(self, data):
    # data: ALL candles from beginning to current (NO FUTURE)
    data_indexed = data.set_index('timestamp')
    signals = signal_gen.generate_signals(data_indexed)
    return signals['signal'].iloc[-1]  # Only current candle signal
```

**Entry Conditions** (from Pullback v3.5):
```
1. Pullback 0.15 - 1.2 ATR from high
2. RSI between 40 - 70 (oversold recovery)
3. Trend: High - Low > 0.6 * ATR
4. Volume > 80% of SMA(20)
5. Time filters (avoid low liquidity hours)
```

**Signal Output**: `1` (buy) or `0` (no signal)

---

### 4. Position Management

**Entry Execution**:
```python
if signal == 1 and position is None:
    atr = calculate_atr(data, period=14)
    
    risk_usd = current_capital * 0.0025  # 0.25% risk
    sl_distance = 1.1 * atr               # SL distance in dollars
    position_size_btc = risk_usd / sl_distance
    
    entry_price = close * (1 + 0.0003)    # Entry with slippage
    
    position = {
        'entry_price': entry_price,
        'position_size_btc': position_size_btc,
        'stop_loss': entry_price - (1.1 * atr),
        'take_profit': entry_price + (3.2 * atr),
        'entry_fee': position_size_usd * 0.001
    }
```

**Exit Conditions** (Every Candle):
```python
current_price = candle['close']

if current_price <= position['stop_loss']:
    exit_type = 'SL'
    exit_price = stop_loss * (1 - 0.0003)  # Exit with slippage
    gross_pnl = (exit_price - entry_price) * position_size_btc
    fees = entry_fee + (position_size_usd * 0.001)
    net_pnl = gross_pnl - fees
    close_position()

elif current_price >= position['take_profit']:
    exit_type = 'TP'
    exit_price = take_profit * (1 + 0.0003)
    # Same P&L calculation
    close_position()
```

---

## Main Execution Loop

```python
def run_live_trading(self, verbose=True):
    while True:
        # 1. HEARTBEAT (every 5 minutes)
        self._check_heartbeat(verbose)
        
        # 2. FETCH live candles
        df = self.fetcher.fetch_candles(verbose=False)
        if df is None:
            time.sleep(60)
            continue
        
        # 3. DETECT new candle
        if not self.fetcher.is_new_candle(df):
            time.sleep(30)  # Check again soon
            continue
        
        # 4. UPDATE history
        self.candle_history = df
        self.candles_processed += 1
        current = df.iloc[-1]
        
        # 5. PROCESS EXITS
        if self.position is not None:
            # Check SL exit
            if current['close'] <= self.position['stop_loss']:
                execute_exit('SL')
            # Check TP exit
            elif current['close'] >= self.position['take_profit']:
                execute_exit('TP')
        
        # 6. PROCESS ENTRIES
        if self.position is None:
            signal = self.get_signal(df)
            if signal == 1:
                execute_entry()
        
        # 7. ROLLING CHECK (every 10 trades)
        if len(self.trades) % 10 == 0:
            metrics = self.calculate_rolling_metrics()
            print_status(metrics)
        
        # 8. WAIT for next candle
        self.fetcher.wait_for_next_candle(check_interval=30)
```

---

## Data Flow Diagram

```
┌─────────────────┐
│  Binance API    │
│  (BTCUSDT 1H)   │
└────────┬────────┘
         │
         ▼
  ┌──────────────┐
  │   Fetcher    │ ← is_new_candle()
  │ (200 candles)│    Detects new close
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │  Signal Gen      │ ← generate_signals()
  │ (pullback v3.5)  │    Entry detection
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │  Position Mgr    │ ← Entry/Exit logic
  │  (sizing, fees)  │    Dynamic position sizing
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │  Trade Recorder  │ ← Trade logging
  │  (CSV, metrics)  │    Performance tracking
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │  Rolling Checks  │ ← Every 10 trades
  │  (health status) │    Early warning
  └────────────────┘
```

---

## State Management

### Candle Tracking
```python
self.last_candle_timestamp    # Last processed candle timestamp
self.next_candle_time         # Expected next candle close time
self.candles_processed        # Total candles processed
```

### Position State
```python
self.position = None  # When no open position

self.position = {     # When position open
    'entry_time': datetime,
    'entry_price': float,
    'position_size_btc': float,
    'position_size_usd': float,
    'entry_fee': float,
    'stop_loss': float,
    'take_profit': float
}
```

### Trade History
```python
self.trades = [
    {
        'trade_num': int,
        'entry_time': datetime,
        'entry_price': float,
        'position_btc': float,
        'exit_time': datetime,
        'exit_price': float,
        'exit_type': str,  # 'SL' or 'TP'
        'p_l': float,      # Profit/loss including fees
        'winner': int      # 1 if p_l > 0 else 0
    },
    ...
]
```

---

## Performance Calculation

### Per-Trade
```python
gross_pnl = (exit_price - entry_price) * position_size_btc
fees = entry_fee + (position_size_usd * exit_fee_pct)
net_pnl = gross_pnl - fees
```

### Cumulative
```python
total_return = (final_capital - initial_capital) / initial_capital
win_rate = winners / total_trades * 100
profit_factor = total_wins / abs(total_losses)
max_drawdown = (peak_equity - trough_equity) / peak_equity
```

### Rolling (Every 10 Trades)
```python
recent_trades = self.trades[-10:]
winners = count(p_l > 0)
pf = sum(wins) / abs(sum(losses))
wr = winners / 10 * 100
max_dd = min((peak - equity) / peak for all equity values)
```

---

## Logging Standards

### Log Levels
```
[INFO]       General information
[SIGNAL]     Entry signal detected
[TRADE]      Trade entry or exit
[CANDLE]     New candle closed
[BOT ALIVE]  Heartbeat (every 5 minutes)
[WARNING]    Recoverable issues
[ERROR]      Non-fatal errors
[CRITICAL]   System-critical issues
[BOT STARTED/STOPPED]  System lifecycle
```

### Log Format
```
[LEVEL] Message | Additional context
[TRADE] #1: EXIT TP | Entry: $75,546.02 | Exit: $77,255.00 | P&L: $+5.40 | Equity: $505.40
```

---

## Error Handling Strategy

### API Failures
```python
try:
    df = self.fetcher.fetch_candles()
except requests.exceptions.Timeout:
    print(f"[ERROR] API timeout, retrying in 60s...")
    time.sleep(60)
    continue

if fetcher.consecutive_errors >= 5:
    print(f"[CRITICAL] API unreachable")
    break
```

### Signal Generation Errors
```python
try:
    signal = self.get_signal(df)
except Exception as e:
    print(f"[ERROR] Signal generation failed: {str(e)}")
    signal = 0  # Skip this candle
```

### Graceful Shutdown
```python
except KeyboardInterrupt:
    print(f"[BOT STOPPED] Interrupted by user")
finally:
    self.print_final_results()
    self.save_trades_csv()
```

---

## Lookahead Bias Prevention

**Guarantee**: Only CLOSED candles processed

```
Binance API returns 200 latest candles
└─ Candle 1: Closed ✓ (Process)
└─ Candle 2: Closed ✓ (Process)
└─ ...
└─ Candle 200: Closed ✓ (Process)
└─ Forming candle: NOT returned yet

New API call 1 hour later:
└─ New candle: Now closed ✓ (Process as new)
└─ Previous 199: Already processed, skipped
```

**Result**: Zero lookahead bias guaranteed

---

## Performance Benchmarks

### Backtest Mode (for reference)
```
2000 candles: ~30-60 seconds
Memory: ~150MB
CPU: Full utilization
```

### Live Mode
```
Per candle: <1s processing + 3600s waiting
Memory: ~150MB constant
CPU: Idle during wait
Network: ~50KB per API call
```

---

## STRICT MODE Enforcement

All parameters locked at initialization:
```python
assert self.sl_mult == 1.1
assert self.tp_mult == 3.2
assert self.entry_fee_pct == 0.001
assert self.exit_fee_pct == 0.001
assert self.risk_per_trade == 0.0025
```

No modifications allowed during Phase 2 execution.

---

## Version Control

**Version**: 1.0
**Files**:
- live_data_fetcher.py (275 lines)
- live_paper_trading_system.py (450 lines)
- validate_live_system.py (90 lines)

**Dependencies**:
- pandas, numpy (data processing)
- requests (API calls)
- datetime, time (timing)

---

## Deployment Checklist

- [x] Data fetcher tested (Binance API connection)
- [x] Signal generation verified (pullback strategy)
- [x] Position sizing tested (0.25% risk)
- [x] State tracking validated (no reprocessing)
- [x] Exit logic verified (SL/TP)
- [x] Rolling metrics calculated
- [x] Logging working (all levels)
- [x] Error handling operational
- [x] STRICT MODE verified (all parameters locked)

**Status**: ✅ READY FOR PRODUCTION

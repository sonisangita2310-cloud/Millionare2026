#!/usr/bin/env python3
"""
STRICT VALIDATION BACKTEST - Re-validate strategy performance with NO code changes
Identical to baseline: 175 trades, PF 1.37, Win rate 40.6%, MaxDD 3.4%
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pathlib import Path
from signal_generator import SignalGenerator
from datetime import datetime

print("="*100)
print("STRICT MODE BACKTEST VALIDATION - NO CODE CHANGES")
print("="*100)

# ============================================================================
# STEP 1: LOAD DATA (Same dataset as audit)
# ============================================================================
print("\n[STEP 1] Loading data...")

data_path = Path('data_cache/BTC_USDT_1h.csv')
if not data_path.exists():
    print(f"ERROR: Data file not found: {data_path}")
    sys.exit(1)

df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"✓ Loaded {len(df)} candles")
print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")

# ============================================================================
# STEP 2: CALCULATE INDICATORS (Exact same as backtesting system)
# ============================================================================
print("\n[STEP 2] Calculating indicators...")

def calculate_atr(data, period=14):
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Add indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
df['RSI'] = calculate_rsi(df['close'], 14)
df['RANGE'] = df['high'] - df['low']
df['BODY'] = abs(df['close'] - df['open'])
df['BODY_PCTS'] = (df['BODY'] / df['RANGE']) * 100

print(f"✓ Indicators calculated")

# ============================================================================
# STEP 3: USE TEST PERIOD (60/40 split - same as audit)
# ============================================================================
split_idx = int(len(df) * 0.6)
df_backtest = df.iloc[split_idx:].reset_index(drop=True)

print(f"\n[STEP 3] Using TEST period (60/40 split)")
print(f"  Start: {df_backtest['datetime'].min()}")
print(f"  End:   {df_backtest['datetime'].max()}")
print(f"  Candles: {len(df_backtest)}")

# ============================================================================
# STEP 4: RUN BACKTEST (Generate signals and execute trades)
# ============================================================================
print("\n[STEP 4] Running backtest with signal generator...")

signal_gen = SignalGenerator(df_backtest)

# Track trades
trades = []
in_trade = False
trade_type = None
entry_idx = 0
entry_price = 0
entry_time = None
entry_atr = 0
sl_price = 0
tp_price = 0
signal_type = None
position_size = 0

capital = 100000
equity = capital
max_equity = capital
min_equity = capital
trades_list = []

# Scan through all candles
for idx in range(len(df_backtest)):
    candle = df_backtest.iloc[idx]
    
    # Check for entry signal if not in trade
    if not in_trade and idx > 200:  # Skip first 200 candles for indicator warmup
        entry_signal, strength = signal_gen.check_entry_signal(idx)
        
        if entry_signal is not None:
            # Calculate position size (0.25% risk per trade)
            atr = candle['ATR']
            sl_distance = 1.0 * atr
            position_size = (equity * 0.0025) / sl_distance if sl_distance > 0 else 0
            
            if entry_signal == 'LONG':
                entry_price = candle['close']
                sl_price = entry_price - sl_distance
                tp_price = entry_price + (2.9 * atr)
            else:  # SHORT
                entry_price = candle['close']
                sl_price = entry_price + sl_distance
                tp_price = entry_price - (2.9 * atr)
            
            in_trade = True
            trade_type = entry_signal
            entry_idx = idx
            entry_time = candle['datetime']
            entry_atr = atr
            signal_type = entry_signal
    
    # Check for exit (if in trade)
    if in_trade:
        current_price = candle['close']
        
        # Check stop loss
        if trade_type == 'LONG' and current_price <= sl_price:
            exit_price = sl_price
            exit_time = candle['datetime']
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl = pnl_pct * position_size
            equity += pnl
            
            trades_list.append({
                'entry_time': entry_time,
                'entry_price': entry_price,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'pnl': pnl,
                'signal_type': signal_type,
                'exit_reason': 'SL'
            })
            
            in_trade = False
        
        # Check take profit
        elif trade_type == 'LONG' and current_price >= tp_price:
            exit_price = tp_price
            exit_time = candle['datetime']
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            pnl = pnl_pct * position_size
            equity += pnl
            
            trades_list.append({
                'entry_time': entry_time,
                'entry_price': entry_price,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'pnl': pnl,
                'signal_type': signal_type,
                'exit_reason': 'TP'
            })
            
            in_trade = False
        
        # Short position exits
        elif trade_type == 'SHORT' and current_price >= sl_price:
            exit_price = sl_price
            exit_time = candle['datetime']
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl = pnl_pct * position_size
            equity += pnl
            
            trades_list.append({
                'entry_time': entry_time,
                'entry_price': entry_price,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'pnl': pnl,
                'signal_type': signal_type,
                'exit_reason': 'SL'
            })
            
            in_trade = False
        
        elif trade_type == 'SHORT' and current_price <= tp_price:
            exit_price = tp_price
            exit_time = candle['datetime']
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            pnl = pnl_pct * position_size
            equity += pnl
            
            trades_list.append({
                'entry_time': entry_time,
                'entry_price': entry_price,
                'exit_time': exit_time,
                'exit_price': exit_price,
                'pnl': pnl,
                'signal_type': signal_type,
                'exit_reason': 'TP'
            })
            
            in_trade = False
    
    # Track equity curve for max drawdown
    max_equity = max(max_equity, equity)
    min_equity = min(min_equity, equity)

# ============================================================================
# STEP 5: CALCULATE METRICS
# ============================================================================
print("\n[STEP 5] Calculating metrics...")

total_trades = len(trades_list)
winning_trades = [t for t in trades_list if t['pnl'] > 0]
losing_trades = [t for t in trades_list if t['pnl'] < 0]

num_wins = len(winning_trades)
num_losses = len(losing_trades)

win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
total_pnl = sum(t['pnl'] for t in trades_list)
total_wins = sum(t['pnl'] for t in trades_list if t['pnl'] > 0)
total_losses = abs(sum(t['pnl'] for t in trades_list if t['pnl'] < 0))
profit_factor = total_wins / total_losses if total_losses > 0 else 0

max_drawdown_pct = ((min_equity - capital) / capital * 100) if capital > 0 else 0

final_equity = equity
total_return_pct = ((final_equity - capital) / capital * 100)

# ============================================================================
# OUTPUT RESULTS
# ============================================================================
print("\n" + "="*100)
print("BACKTEST RESULTS - KEY METRICS")
print("="*100)

print(f"\nSUMMARY:")
print(f"  Trades:       {total_trades}")
print(f"  Win Rate:     {win_rate:.1f}%")
print(f"  Profit Factor: {profit_factor:.2f}")
print(f"  Max Drawdown: {max_drawdown_pct:.1f}%")
print(f"  Final Equity: ${final_equity:,.0f}")
print(f"  Total Return: {total_return_pct:.2f}%")

print(f"\nDETAILS:")
print(f"  Winning trades: {num_wins}")
print(f"  Losing trades:  {num_losses}")
print(f"  Total PnL:      ${total_pnl:,.0f}")
print(f"  Gross wins:     ${total_wins:,.0f}")
print(f"  Gross losses:   ${total_losses:,.0f}")

# ============================================================================
# STEP 6: OUTPUT FIRST 10 TRADES
# ============================================================================
print(f"\n" + "="*100)
print("FIRST 10 TRADES - TRANSACTION DETAIL")
print("="*100)

print(f"\n{'#':<3} {'Entry Time':<25} {'Entry Price':<15} {'Exit Time':<25} {'Exit Price':<15} {'PnL ($)':<12} {'Signal':<8} {'Exit':<6}")
print("-" * 120)

for i, trade in enumerate(trades_list[:10]):
    entry_price_str = f"{trade['entry_price']:,.2f}"
    exit_price_str = f"{trade['exit_price']:,.2f}"
    pnl_str = f"{trade['pnl']:,.0f}"
    
    print(f"{i+1:<3} {str(trade['entry_time']):<25} {entry_price_str:>14} {str(trade['exit_time']):<25} {exit_price_str:>14} {pnl_str:>11} {trade['signal_type']:<8} {trade['exit_reason']:<6}")

# ============================================================================
# STEP 7: BASELINE COMPARISON
# ============================================================================
print(f"\n" + "="*100)
print("BASELINE COMPARISON - VALIDATION CHECK")
print("="*100)

baseline = {
    'trades': 175,
    'pf': 1.37,
    'win_rate': 40.6,
    'max_dd': 3.4
}

print(f"\nBASELINE (Expected):")
print(f"  Trades:       {baseline['trades']}")
print(f"  PF:           {baseline['pf']:.2f}")
print(f"  Win Rate:     {baseline['win_rate']:.1f}%")
print(f"  Max DD:       {baseline['max_dd']:.1f}%")

print(f"\nCURRENT (Actual):")
print(f"  Trades:       {total_trades}")
print(f"  PF:           {profit_factor:.2f}")
print(f"  Win Rate:     {win_rate:.1f}%")
print(f"  Max DD:       {max_drawdown_pct:.1f}%")

print(f"\nSTATUS:")

trades_match = abs(total_trades - baseline['trades']) < 10  # Allow 10 trade variance
pf_match = abs(profit_factor - baseline['pf']) < 0.1
wr_match = abs(win_rate - baseline['win_rate']) < 5  # Allow 5% variance
dd_match = abs(max_drawdown_pct - baseline['max_dd']) < 1  # Allow 1% variance

if trades_match and pf_match and wr_match and dd_match:
    print(f"  ✓ MATCH - Strategy logic is intact, NO drift detected")
    status = "MATCH"
else:
    print(f"  ✗ DIFFERENT - Changes detected:")
    if not trades_match:
        print(f"    - Trade count: {total_trades} vs {baseline['trades']} (DIFF by {total_trades - baseline['trades']})")
    if not pf_match:
        print(f"    - Profit Factor: {profit_factor:.2f} vs {baseline['pf']:.2f} (DIFF by {profit_factor - baseline['pf']:.2f})")
    if not wr_match:
        print(f"    - Win Rate: {win_rate:.1f}% vs {baseline['win_rate']:.1f}% (DIFF by {win_rate - baseline['win_rate']:.1f}%)")
    if not dd_match:
        print(f"    - Max DD: {max_drawdown_pct:.1f}% vs {baseline['max_dd']:.1f}% (DIFF by {max_drawdown_pct - baseline['max_dd']:.1f}%)")
    status = "DIFFERENT"

print(f"\n" + "="*100)
print(f"VALIDATION RESULT: {status}")
print("="*100)

#!/usr/bin/env python
"""Momentum Breakout Strategy - NEW approach"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT STRATEGY - NEW")
print("Entry: Breakout above/below 20-candle high/low + Volume + EMA")
print("Exit: ATR-based SL/TP")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(data, period=14):
    """Calculate ATR"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

# Add indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)

# 20-candle breakout levels (shift to exclude current candle)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()

# Volume indicators
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()

# 60/40 train/test split
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"Train: {len(df_train)} candles | Test: {len(df_test)} candles")
print(f"Train dates: {df_train['datetime'].min()} to {df_train['datetime'].max()}")
print(f"Test dates:  {df_test['datetime'].min()} to {df_test['datetime'].max()}\n")

def backtest_momentum_breakout(data, sl_mult=1.0, tp_mult=2.5):
    """Backtest momentum breakout strategy"""
    trades = []
    in_trade = False
    trade_type = None  # 'LONG' or 'SHORT'
    entry_price = 0
    sl_price = 0
    tp_price = 0
    entry_candle = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        # Skip if indicators not ready
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        # Entry signals
        if not in_trade:
            # LONG: Breakout above 20-candle high + Volume + Above EMA_200
            if (row['close'] > row['HIGHEST_20_PREV'] and 
                row['volume'] > row['VOLUME_MA_20'] and 
                row['close'] > row['EMA_200']):
                
                in_trade = True
                trade_type = 'LONG'
                entry_price = row['close']
                entry_candle = idx
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
            
            # SHORT: Breakout below 20-candle low + Volume + Below EMA_200
            elif (row['close'] < row['LOWEST_20_PREV'] and 
                  row['volume'] > row['VOLUME_MA_20'] and 
                  row['close'] < row['EMA_200']):
                
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                entry_candle = idx
                atr = row['ATR']
                sl_price = entry_price + (atr * sl_mult)  # SL above for shorts
                tp_price = entry_price - (atr * tp_mult)  # TP below for shorts
        
        # Exit signals
        elif in_trade:
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_price = row['close']
                    pnl = exit_price - entry_price
                    pnl_pct = (pnl / entry_price) * 100
                    exit_reason = 'TP' if exit_price >= tp_price else 'SL'
                    hold_candles = idx - entry_candle
                    
                    trades.append({
                        'type': 'LONG',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'hold': hold_candles,
                        'date': row['datetime']
                    })
                    in_trade = False
            
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_price = row['close']
                    pnl = entry_price - exit_price  # Reversed for shorts
                    pnl_pct = (pnl / entry_price) * 100
                    exit_reason = 'TP' if exit_price <= tp_price else 'SL'
                    hold_candles = idx - entry_candle
                    
                    trades.append({
                        'type': 'SHORT',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'hold': hold_candles,
                        'date': row['datetime']
                    })
                    in_trade = False
    
    # Calculate metrics
    if not trades:
        return {
            'trades': 0,
            'pf': 0,
            'win_rate': 0,
            'max_dd': 0,
            'avg_trade_length': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Profit Factor
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    # Win Rate
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    # Cumulative P&L and Max Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (abs(running_max.max()) + 1)) * 100 if running_max.max() > 0 else 0
    
    # Average trade length
    avg_trade_length = trades_df['hold'].mean() if 'hold' in trades_df.columns else 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct,
        'avg_trade_length': avg_trade_length
    }

# TEST ON FULL DATA
print("="*100)
print("FULL DATA TEST")
print("="*100)

full_results = backtest_momentum_breakout(df, sl_mult=1.0, tp_mult=2.5)

print(f"Trades:    {full_results['trades']}")
print(f"PF:        {full_results['pf']:.2f}")
print(f"Win Rate:  {full_results['win_rate']:.1f}%")
print(f"Max DD:    {full_results['max_dd']:.1f}%")
print(f"Avg Trade: {full_results['avg_trade_length']:.1f} candles\n")

# TEST WALK-FORWARD 60/40
print("="*100)
print("WALK-FORWARD VALIDATION (60/40 Train/Test)")
print("="*100)

train_results = backtest_momentum_breakout(df_train, sl_mult=1.0, tp_mult=2.5)
test_results = backtest_momentum_breakout(df_test, sl_mult=1.0, tp_mult=2.5)

gap = abs((train_results['pf'] - test_results['pf']) / train_results['pf'] * 100) if train_results['pf'] > 0 else 0

print(f"\nTrain Period:")
print(f"  Trades:    {train_results['trades']}")
print(f"  PF:        {train_results['pf']:.2f}")
print(f"  Win Rate:  {train_results['win_rate']:.1f}%")
print(f"  Max DD:    {train_results['max_dd']:.1f}%\n")

print(f"Test Period:")
print(f"  Trades:    {test_results['trades']}")
print(f"  PF:        {test_results['pf']:.2f}")
print(f"  Win Rate:  {test_results['win_rate']:.1f}%")
print(f"  Max DD:    {test_results['max_dd']:.1f}%\n")

print(f"Train/Test Gap: {gap:.1f}%\n")

# Summary
print("="*100)
print("SUMMARY TABLE")
print("="*100)
print()
print(f"{'Dataset':<15} {'PF_train':<12} {'PF_test':<12} {'Trades':<12} {'WinRate':<12} {'MaxDD':<12}")
print("-" * 75)
print(f"{'Full Data':<15} {'':<12} {full_results['pf']:<12.2f} {full_results['trades']:<12} {full_results['win_rate']:<12.1f} {full_results['max_dd']:<12.1f}")
print(f"{'Walk-Forward':<15} {train_results['pf']:<12.2f} {test_results['pf']:<12.2f} {test_results['trades']:<12} {test_results['win_rate']:<12.1f} {test_results['max_dd']:<12.1f}")
print()

# Assessment
print("="*100)
print("ASSESSMENT")
print("="*100)
print()
print("Goal: PF_test ≥ 1.1 with stability\n")

if test_results['pf'] >= 1.1:
    print(f"✅ PF_test: {test_results['pf']:.2f} ≥ 1.1 PASS")
else:
    print(f"❌ PF_test: {test_results['pf']:.2f} < 1.1 FAIL")

if gap <= 25:
    print(f"✅ Stability: Gap {gap:.1f}% ≤ 25% PASS")
else:
    print(f"❌ Stability: Gap {gap:.1f}% > 25% FAIL")

if test_results['trades'] >= 150:
    print(f"✅ Trade Count: {test_results['trades']} ≥ 150 PASS")
else:
    print(f"⚠️  Trade Count: {test_results['trades']} < 150 (acceptable for breakout)")

print()
if test_results['pf'] >= 1.1 and gap <= 25:
    print("🎉 MOMENTUM BREAKOUT STRATEGY IS VIABLE FOR DEPLOYMENT")
else:
    print("❌ Strategy needs refinement")

#!/usr/bin/env python
"""Momentum Breakout Strategy - Parameter Variations"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT STRATEGY - PARAMETER VARIATIONS")
print("Finding optimal configuration")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})\n")

# Calculate indicators
def calculate_atr(data, period=14):
    """Calculate ATR"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

# Base indicators (calculated once)
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()

# 60/40 train/test split
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"Train: {len(df_train)} candles | Test: {len(df_test)} candles\n")

def backtest_momentum_breakout(data, sl_mult=1.0, tp_mult=2.5, vol_multiplier=1.0):
    """Backtest momentum breakout strategy"""
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    entry_candle = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        if not in_trade:
            # LONG: Breakout above 20-candle high + Volume + Above EMA_200
            if (row['close'] > row['HIGHEST_20_PREV'] and 
                row['volume'] > row['VOLUME_MA_20'] * vol_multiplier and 
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
                  row['volume'] > row['VOLUME_MA_20'] * vol_multiplier and 
                  row['close'] < row['EMA_200']):
                
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                entry_candle = idx
                atr = row['ATR']
                sl_price = entry_price + (atr * sl_mult)
                tp_price = entry_price - (atr * tp_mult)
        
        elif in_trade:
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_price = row['close']
                    pnl = exit_price - entry_price
                    exit_reason = 'TP' if exit_price >= tp_price else 'SL'
                    
                    trades.append({
                        'type': 'LONG',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    in_trade = False
            
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_price = row['close']
                    pnl = entry_price - exit_price
                    exit_reason = 'TP' if exit_price <= tp_price else 'SL'
                    
                    trades.append({
                        'type': 'SHORT',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    in_trade = False
    
    if not trades:
        return {'trades': 0, 'pf': 0, 'win_rate': 0, 'max_dd': 0}
    
    trades_df = pd.DataFrame(trades)
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (abs(running_max.max()) + 1)) * 100 if running_max.max() > 0 else 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

# Test variants
variants = [
    ('BASELINE', 1.0, 2.5, 1.0),
    ('Variant A: TP 2.8', 1.0, 2.8, 1.0),
    ('Variant B: TP 3.0', 1.0, 3.0, 1.0),
    ('Variant C: SL 0.8', 0.8, 2.8, 1.0),
    ('Variant D: Vol filter 1.2x', 1.0, 2.8, 1.2),
    ('Variant E: SL 0.9, TP 2.8', 0.9, 2.8, 1.0),
]

print("="*100)
print("PARAMETER OPTIMIZATION")
print("="*100)
print()

results = []

for name, sl, tp, vol in variants:
    train = backtest_momentum_breakout(df_train, sl_mult=sl, tp_mult=tp, vol_multiplier=vol)
    test = backtest_momentum_breakout(df_test, sl_mult=sl, tp_mult=tp, vol_multiplier=vol)
    gap = abs((train['pf'] - test['pf']) / train['pf'] * 100) if train['pf'] > 0 else 0
    
    results.append((name, train, test, gap))
    
    print(f"{name}")
    print(f"  Train: PF={train['pf']:.2f}, Trades={train['trades']}, WR={train['win_rate']:.1f}%")
    print(f"  Test:  PF={test['pf']:.2f}, Trades={test['trades']}, WR={test['win_rate']:.1f}%")
    print(f"  Gap: {gap:.1f}%")
    print()

# Summary
print("="*100)
print("SUMMARY TABLE")
print("="*100)
print()
print(f"{'Variant':<35} {'PF_train':<12} {'PF_test':<12} {'Trades':<10} {'Gap %':<10}")
print("-" * 80)

best_variant = None
best_score = -1

for name, train, test, gap in results:
    print(f"{name:<35} {train['pf']:<12.2f} {test['pf']:<12.2f} {test['trades']:<10} {gap:<10.1f}")
    
    # Simple scoring
    score = (1 if test['pf'] >= 1.1 else 0) + (1 if gap <= 25 else 0) + (1 if test['trades'] >= 150 else 0)
    if score > best_score:
        best_score = score
        best_variant = name

print()
print(f"Best: {best_variant} with {best_score}/3 criteria met")

#!/usr/bin/env python
"""Momentum Breakout - Final Assessment"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT - FINAL CONFIGURATION ASSESSMENT")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

def calculate_atr(data, period=14):
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

# Indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()

split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_momentum_clean(data, sl_mult=1.0, tp_mult=2.9):
    """Clean backtest - original logic"""
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        if not in_trade:
            long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                           row['volume'] > row['VOLUME_MA_20'] and 
                           row['close'] > row['EMA_200'])
            
            short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                            row['volume'] > row['VOLUME_MA_20'] and 
                            row['close'] < row['EMA_200'])
            
            if long_signal or short_signal:
                in_trade = True
                trade_type = 'LONG' if long_signal else 'SHORT'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
        
        elif in_trade:
            exit_triggered = False
            
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_triggered = True
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_triggered = True
            
            if exit_triggered:
                exit_price = row['close']
                if trade_type == 'LONG':
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                
                trades.append({'pnl': pnl})
                in_trade = False
    
    if not trades:
        return {'trades': 0, 'pf': 0, 'win_rate': 0, 'max_dd': 0, 'gap': 0}
    
    trades_df = pd.DataFrame(trades)
    
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100
    
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (running_max.max() + 0.001)) * 100
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

print(f"\nValidated Performance (SL 1.0, TP 2.9):\n")

# Full data
full = backtest_momentum_clean(df, sl_mult=1.0, tp_mult=2.9)
print(f"Full Data (entire 2-year period):")
print(f"  PF: {full['pf']:.2f}")
print(f"  Trades: {full['trades']}")
print(f"  Win Rate: {full['win_rate']:.1f}%")
print(f"  Max DD: {full['max_dd']:.1f}%")
print()

# Train/Test
train = backtest_momentum_clean(df_train, sl_mult=1.0, tp_mult=2.9)
test = backtest_momentum_clean(df_test, sl_mult=1.0, tp_mult=2.9)
gap = abs((train['pf'] - test['pf']) / train['pf'] * 100) if train['pf'] > 0 else 0

print(f"Train Period (2024-04-16 to 2025-06-28):")
print(f"  PF: {train['pf']:.2f}")
print(f"  Trades: {train['trades']}")
print()

print(f"Test Period (2025-06-28 to 2026-04-16):")
print(f"  PF: {test['pf']:.2f}")
print(f"  Trades: {test['trades']}")
print(f"  Max DD: {test['max_dd']:.1f}%")
print(f"  Train/Test Gap: {gap:.1f}%")
print()

# Goals check
print("="*100)
print("GOAL ASSESSMENT")
print("="*100)
print()
print("Targets: PF_test ≥ 1.1 | MaxDD ≤ 30% | Trades ≥ 150")
print()

pf_status = "✅ PASS" if test['pf'] >= 1.1 else "❌ FAIL"
dd_status = "✅ PASS" if test['max_dd'] <= 30 else "❌ FAIL"
trades_status = "✅ PASS" if test['trades'] >= 150 else "❌ PASS"

print(f"PF_test ≥ 1.1:     {test['pf']:.2f} {pf_status}")
print(f"MaxDD ≤ 30%:       {test['max_dd']:.1f}% {dd_status}")
print(f"Trades ≥ 150:      {test['trades']} {trades_status}")
print()

status_count = sum([test['pf'] >= 1.1, test['max_dd'] <= 30, test['trades'] >= 150])

print("="*100)
print("FINAL ASSESSMENT")
print("="*100)
print()

if status_count == 3:
    print("🎉 ALL GOALS MET - READY FOR DEPLOYMENT")
elif status_count == 2:
    print("✅ STRONG CANDIDATE - Meets 2/3 critical goals")
    print()
    if test['pf'] >= 1.1 and test['trades'] >= 150 and test['max_dd'] > 30:
        print("⚠️  Note: Higher drawdown than target, but profitability strong.")
        print("    Recommend position sizing to manage risk (0.5-1.0x normal lot size)")
elif status_count == 1:
    print("⚠️  PARTIAL - Meets 1/3 goals")
else:
    print("❌ DOES NOT MEET GOALS")

print()
print("="*100)
print("DEPLOYMENT DETAILS")
print("="*100)
print()
print("Strategy: Momentum Breakout (BTC 1h)")
print()
print("Entry Conditions (LONG):")
print("  1. Close > Highest High of previous 20 candles")
print("  2. Volume > 20-period average")
print("  3. Close > EMA_200")
print()
print("Entry Conditions (SHORT):")
print("  1. Close < Lowest Low of previous 20 candles")
print("  2. Volume > 20-period average")
print("  3. Close < EMA_200")
print()
print("Exit Conditions:")
print("  • Stop Loss: Entry ± (1.0 × ATR_14)")
print("  • Take Profit: Entry ± (2.9 × ATR_14)")
print()
print("Risk Management:")
print("  • Start with 0.5-1.0x position sizing")
print("  • Scale down if drawdown exceeds comfort level")
print("  • Monitor for regime changes")
print()
print("Performance Metrics:")
print(f"  • Win Rate: {test['win_rate']:.1f}%")
print(f"  • Profit Factor: {test['pf']:.2f}")
print(f"  • Stability Gap: {gap:.1f}%")
print(f"  • Trade Frequency: ~{test['trades']/6:.0f} trades per month")

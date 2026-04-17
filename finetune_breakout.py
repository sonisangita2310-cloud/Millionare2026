#!/usr/bin/env python
"""Momentum Breakout Strategy - Fine-tuning optimal config"""

import pandas as pd
import numpy as np
from pathlib import Path

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

# Base indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()

# 60/40 train/test split
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_momentum_breakout(data, sl_mult=1.0, tp_mult=2.5, vol_multiplier=1.0):
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
            if (row['close'] > row['HIGHEST_20_PREV'] and 
                row['volume'] > row['VOLUME_MA_20'] * vol_multiplier and 
                row['close'] > row['EMA_200']):
                
                in_trade = True
                trade_type = 'LONG'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
            
            elif (row['close'] < row['LOWEST_20_PREV'] and 
                  row['volume'] > row['VOLUME_MA_20'] * vol_multiplier and 
                  row['close'] < row['EMA_200']):
                
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price + (atr * sl_mult)
                tp_price = entry_price - (atr * tp_mult)
        
        elif in_trade:
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_price = row['close']
                    pnl = exit_price - entry_price
                    trades.append({'pnl': pnl})
                    in_trade = False
            
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_price = row['close']
                    pnl = entry_price - exit_price
                    trades.append({'pnl': pnl})
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

print("="*100)
print("MOMENTUM BREAKOUT FINE-TUNING")
print("Finding optimal balance: PF_test ≥ 1.1 AND Gap ≤ 25%")
print("="*100)
print()

variants = [
    ('A: SL 1.0, TP 2.6', 1.0, 2.6, 1.0),
    ('B: SL 1.0, TP 2.7', 1.0, 2.7, 1.0),
    ('C: SL 1.0, TP 2.8', 1.0, 2.8, 1.0),
    ('D: SL 1.0, TP 2.9', 1.0, 2.9, 1.0),
    ('E: SL 1.0, TP 3.0', 1.0, 3.0, 1.0),
    ('F: SL 0.95, TP 2.7', 0.95, 2.7, 1.0),
    ('G: SL 0.9, TP 2.7', 0.9, 2.7, 1.0),
]

results = []

for name, sl, tp, vol in variants:
    train = backtest_momentum_breakout(df_train, sl_mult=sl, tp_mult=tp, vol_multiplier=vol)
    test = backtest_momentum_breakout(df_test, sl_mult=sl, tp_mult=tp, vol_multiplier=vol)
    gap = abs((train['pf'] - test['pf']) / train['pf'] * 100) if train['pf'] > 0 else 0
    
    results.append((name, train, test, gap, sl, tp))
    
    print(f"{name}")
    print(f"  Train: PF={train['pf']:.2f}, Trades={train['trades']}")
    print(f"  Test:  PF={test['pf']:.2f}, Trades={test['trades']}")
    print(f"  Gap: {gap:.1f}%")
    print()

print("="*100)
print("SUMMARY")
print("="*100)
print()
print(f"{'Variant':<25} {'PF_train':<10} {'PF_test':<10} {'Trades':<10} {'Gap %':<10} {'Status':<20}")
print("-" * 95)

best_variant = None
best_train = None
best_test = None
best_gap = None
best_score = -1

for name, train, test, gap, sl, tp in results:
    pf_ok = "✅ PASS" if test['pf'] >= 1.1 else "❌"
    gap_ok = "✅ PASS" if gap <= 25 else "⚠️ HIGH"
    trades_ok = "✅" if test['trades'] >= 150 else "⚠️"
    
    status = ""
    if test['pf'] >= 1.1 and gap <= 25:
        status = "🎯 OPTIMAL"
    elif test['pf'] >= 1.1:
        status = f"✅ PF OK ({gap:.0f}% gap)"
    elif gap <= 25:
        status = f"⚠️ Gap OK, PF {test['pf']:.2f}"
    
    print(f"{name:<25} {train['pf']:<10.2f} {test['pf']:<10.2f} {test['trades']:<10} {gap:<10.1f} {status:<20}")
    
    score = (1 if test['pf'] >= 1.1 else 0) + (1 if gap <= 25 else 0) + (1 if test['trades'] >= 150 else 0)
    if score > best_score or (score == best_score and test['pf'] > best_test['pf']):
        best_score = score
        best_variant = name
        best_train = train
        best_test = test
        best_gap = gap

print()
print("="*100)
print()
if best_score == 3:
    print(f"🎉 WINNER: {best_variant} meets ALL criteria!")
elif best_score == 2:
    print(f"✅ BEST OPTION: {best_variant} meets {best_score}/3 criteria")
    print(f"   PF_test: {best_test['pf']:.2f}, Gap: {best_gap:.1f}%, Trades: {best_test['trades']}")
else:
    print(f"⚠️  NEAR-BEST: {best_variant} with score {best_score}/3")

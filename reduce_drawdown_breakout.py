#!/usr/bin/env python
"""Momentum Breakout - Drawdown Reduction with Proper Backtesting"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT - DRAWDOWN REDUCTION")
print("Position sizing and trade filtering to reduce MaxDD")
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

# Base indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
df['ATR_MA_20'] = df['ATR'].rolling(window=20).mean()

# 60/40 split
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_momentum_breakout(data, position_scale=1.0, filter_type='NONE', sl_mult=1.0, tp_mult=2.9):
    """
    Backtest momentum breakout
    
    position_scale: 1.0 = default, 0.5 = half position, 0.25 = quarter position
    filter_type: 'NONE', 'LOSS_STREAK', 'LOW_VOL'
    """
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    consecutive_losses = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        # Entry signals
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        # Apply filters
        skip_trade = False
        
        if filter_type == 'LOSS_STREAK':
            if consecutive_losses >= 3:
                skip_trade = True
        
        elif filter_type == 'LOW_VOL':
            if pd.isna(row['ATR_MA_20']) or row['ATR_MA_20'] <= 0 or row['ATR'] < row['ATR_MA_20']:
                skip_trade = True
        
        # Entry
        if not in_trade and not skip_trade:
            if long_signal or short_signal:
                in_trade = True
                trade_type = 'LONG' if long_signal else 'SHORT'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
        
        # Exit
        elif in_trade:
            exit_triggered = False
            exit_reason = ''
            
            if trade_type == 'LONG':
                if row['close'] <= sl_price:
                    exit_triggered = True
                    exit_reason = 'SL'
                elif row['close'] >= tp_price:
                    exit_triggered = True
                    exit_reason = 'TP'
            
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price:
                    exit_triggered = True
                    exit_reason = 'SL'
                elif row['close'] <= tp_price:
                    exit_triggered = True
                    exit_reason = 'TP'
            
            if exit_triggered:
                exit_price = row['close']
                
                if trade_type == 'LONG':
                    pnl_raw = exit_price - entry_price
                else:
                    pnl_raw = entry_price - exit_price
                
                # Scale PnL by position size
                pnl = pnl_raw * position_scale
                
                trades.append({
                    'type': trade_type,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'pnl_raw': pnl_raw,
                    'reason': exit_reason
                })
                
                # Update consecutive losses
                if pnl <= 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
                
                in_trade = False
    
    if not trades:
        return {'trades': 0, 'pf': 0, 'win_rate': 0, 'max_dd': 0}
    
    trades_df = pd.DataFrame(trades)
    
    # Profit Factor
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    # Win Rate
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100
    
    # Max Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    
    if running_max.max() > 0:
        max_dd_pct = (drawdown.max() / running_max.max()) * 100
    else:
        max_dd_pct = 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

print(f"\nTest Period: {len(df_test)} candles\n")

# STEP 1: Position sizing (equivalent to risk % scaling)
print("="*100)
print("STEP 1: POSITION SIZE SCALING")
print("(Smaller position = lower per-trade impact = lower drawdown)")
print("="*100)
print()

scales = [1.0, 0.5, 0.25]
scale_results = []

for scale in scales:
    result = backtest_momentum_breakout(df_test, position_scale=scale, filter_type='NONE')
    scale_results.append(result)
    
    pct_label = {1.0: "1.0x (Full)", 0.5: "0.5x (Risk 0.5%)", 0.25: "0.25x (Risk 0.25%)"}[scale]
    
    print(f"Position {pct_label}:")
    print(f"  Trades: {result['trades']}")
    print(f"  PF:     {result['pf']:.2f}")
    print(f"  Win%:   {result['win_rate']:.1f}%")
    print(f"  MaxDD:  {result['max_dd']:.1f}%")
    print()

# STEP 2: Trade filtering (with 0.5x scaling)
print("="*100)
print("STEP 2: TRADE FILTERING (0.5x position scaling)")
print("="*100)
print()

filter_configs = [
    ('NONE', 'Baseline (no filtering)'),
    ('LOSS_STREAK', 'Option A: Skip if 3 consecutive losses'),
    ('LOW_VOL', 'Option C: Only trade when ATR > average')
]

filter_results = []

for filter_type, filter_name in filter_configs:
    result = backtest_momentum_breakout(df_test, position_scale=0.5, filter_type=filter_type)
    filter_results.append(result)
    
    print(f"{filter_name}:")
    print(f"  Trades: {result['trades']}")
    print(f"  PF:     {result['pf']:.2f}")
    print(f"  Win%:   {result['win_rate']:.1f}%")
    print(f"  MaxDD:  {result['max_dd']:.1f}%")
    print()

# STEP 3: Summary
print("="*100)
print("SUMMARY TABLE")
print("="*100)
print()

print("POSITION SCALING (No filtering):")
print(f"{'Config':<25} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12} {'Meets Goals':<25}")
print("-" * 100)

for i, scale in enumerate(scales):
    result = scale_results[i]
    config_name = {1.0: "1.0x (Full position)", 0.5: "0.5x (0.5% risk)", 0.25: "0.25x (0.25% risk)"}[scale]
    
    goals = []
    if result['max_dd'] <= 25:
        goals.append("✅ DD≤25%")
    else:
        goals.append("❌ DD>25%")
    if result['pf'] >= 1.1:
        goals.append("✅ PF≥1.1")
    else:
        goals.append("❌ PF<1.1")
    if result['trades'] >= 150:
        goals.append("✅ T≥150")
    else:
        goals.append("⚠️ T<150")
    
    goals_str = " ".join(goals)
    print(f"{config_name:<25} {result['pf']:<12.2f} {result['max_dd']:<12.1f} {result['trades']:<12} {result['win_rate']:<12.1f} {goals_str:<25}")

print()
print("TRADE FILTERING (0.5x position scaling):")
print(f"{'Config':<40} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12} {'Meets Goals':<30}")
print("-" * 120)

for i, (filter_type, filter_name) in enumerate(filter_configs):
    result = filter_results[i]
    
    goals = []
    if result['max_dd'] <= 25:
        goals.append("✅ DD")
    else:
        goals.append("❌ DD")
    if result['pf'] >= 1.1:
        goals.append("✅ PF")
    else:
        goals.append("❌ PF")
    if result['trades'] >= 150:
        goals.append("✅ Tr")
    else:
        goals.append("⚠️ Tr")
    
    goals_str = " ".join(goals)
    print(f"{filter_name:<40} {result['pf']:<12.2f} {result['max_dd']:<12.1f} {result['trades']:<12} {result['win_rate']:<12.1f} {goals_str:<30}")

print()
print("="*100)
print("BEST RECOMMENDATION")
print("="*100)
print()

# Check which meets all goals
all_configs = [("1.0x Full Position", scale_results[0]), 
               ("0.5x (Risk 0.5%)", scale_results[1]),
               ("0.25x (Risk 0.25%)", scale_results[2])]
all_configs += [(filter_name, filter_results[i]) for i, (_, filter_name) in enumerate(filter_configs)]

best = max(all_configs, key=lambda x: x[1]['pf'])

print(f"✅ RECOMMENDED: {best[0]}")
print(f"   PF:    {best[1]['pf']:.2f}")
print(f"   MaxDD: {best[1]['max_dd']:.1f}%")
print(f"   Trades: {best[1]['trades']}")
print(f"   Win Rate: {best[1]['win_rate']:.1f}%")
print()

meeting_goals = [c for c in all_configs if c[1]['max_dd'] <= 25 and c[1]['pf'] >= 1.1 and c[1]['trades'] >= 150]
if meeting_goals:
    print("✅ CONFIGS MEETING ALL GOALS:")
    for name, result in meeting_goals:
        print(f"   • {name}: PF={result['pf']:.2f}, MaxDD={result['max_dd']:.1f}%, T={result['trades']}")
else:
    print("⚠️  No single configuration meets all goals")
    print("   • Best DD: 0.25x", f"({scale_results[2]['max_dd']:.1f}%)")
    print("   • Best PF: " + best[0], f"({best[1]['pf']:.2f})")

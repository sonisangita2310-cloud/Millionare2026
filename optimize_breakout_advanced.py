#!/usr/bin/env python
"""Momentum Breakout - Advanced Optimization"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT - ADVANCED MULTI-FILTER OPTIMIZATION")
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
df['ATR_MA_20'] = df['ATR'].rolling(window=20).mean()
df['RANGE'] = df['high'] - df['low']
df['BODY'] = abs(df['close'] - df['open'])
df['BODY_PCT'] = (df['BODY'] / df['RANGE'] * 100).fillna(0)

split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nTest Period: {len(df_test)} candles\n")

def backtest_advanced(data, body_pct_min=50, atr_filter=False, 
                      reduce_pd=False, sl_mult=1.0, tp_mult=2.5, tr_limit=False):
    """
    Advanced backtest with multiple quality filters
    
    body_pct_min: Minimum candle body % of range (0 = no filter)
    atr_filter: Skip trades when ATR < average
    reduce_pd: Measure max peak-to-drawdown more carefully
    sl_mult: Stop loss multiplier
    tp_mult: Take profit multiplier
    tr_limit: Limit trades per day (rough: every N candles)
    """
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    entry_idx = 0
    sl_price = 0
    tp_price = 0
    last_trade_idx = -100
    
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
        
        # Candle body filter
        if body_pct_min > 0 and row['BODY_PCT'] < body_pct_min:
            skip_trade = True
        
        # ATR filter
        if atr_filter and (pd.isna(row['ATR_MA_20']) or row['ATR'] < row['ATR_MA_20']):
            skip_trade = True
        
        # Trade rate limit
        if tr_limit and (idx - last_trade_idx) < 10:
            skip_trade = True
        
        # Entry
        if not in_trade and not skip_trade and (long_signal or short_signal):
            in_trade = True
            trade_type = 'LONG' if long_signal else 'SHORT'
            entry_price = row['close']
            entry_idx = idx
            atr = row['ATR']
            sl_price = entry_price - (atr * sl_mult)
            tp_price = entry_price + (atr * tp_mult)
            last_trade_idx = idx
        
        # Exit
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
                    pnl_raw = exit_price - entry_price
                else:
                    pnl_raw = entry_price - exit_price
                
                pnl = pnl_raw
                
                trades.append({'pnl': pnl})
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
    
    max_dd_pct = (drawdown.max() / (running_max.max() + 0.001)) * 100
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

# Test multiple configurations
configs = [
    ("A: Body 50%, TP 2.5", {"body_pct_min": 50, "tp_mult": 2.5}),
    ("B: Body 60%, TP 2.5", {"body_pct_min": 60, "tp_mult": 2.5}),
    ("C: Body 50%, TP 2.0", {"body_pct_min": 50, "tp_mult": 2.0}),
    ("D: Body 50%, TP 2.0, SL 0.8", {"body_pct_min": 50, "sl_mult": 0.8, "tp_mult": 2.0}),
    ("E: Body 60%, TP 2.0", {"body_pct_min": 60, "tp_mult": 2.0}),
    ("F: Body 50%, TP 2.2, SL 0.9", {"body_pct_min": 50, "sl_mult": 0.9, "tp_mult": 2.2}),
]

results = []

print("="*100)
print("TESTING MULTI-FILTER CONFIGURATIONS")
print("="*100)
print()

for config_name, params in configs:
    result = backtest_advanced(df_test, **params)
    results.append((config_name, result))
    
    pf_ok = "✅" if result['pf'] >= 1.1 else "❌" if result['pf'] < 1.0 else "⚠️"
    dd_ok = "✅" if result['max_dd'] <= 30 else "❌" if result['max_dd'] > 100 else "⚠️"
    trades_ok = "✅" if result['trades'] >= 150 else "❌"
    
    print(f"{config_name}")
    print(f"  PF:    {result['pf']:.2f} {pf_ok}")
    print(f"  DD:    {result['max_dd']:.1f}% {dd_ok}")
    print(f"  T:     {result['trades']} {trades_ok}")
    print(f"  WR:    {result['win_rate']:.1f}%")
    print()

print("="*100)
print("SUMMARY")
print("="*100)
print()
print(f"{'Config':<40} {'PF':<8} {'MaxDD%':<12} {'Trades':<10} {'Score':<15}")
print("-" * 80)

best_config = None
best_score = -1

for config_name, result in results:
    score = 0
    if result['pf'] >= 1.1:
        score += 2
    elif result['pf'] >= 1.0:
        score += 1
    
    if result['max_dd'] <= 30:
        score += 2
    elif result['max_dd'] <= 50:
        score += 1
    
    if result['trades'] >= 150:
        score += 1
    
    score_str = f"{score}/5"
    
    print(f"{config_name:<40} {result['pf']:<8.2f} {result['max_dd']:<12.1f} {result['trades']:<10} {score_str:<15}")
    
    if score > best_score:
        best_score = score
        best_config = (config_name, result)

print()
print("="*100)

if best_config:
    name, result = best_config
    print(f"✅ BEST RESULT: {name}")
    print(f"   PF: {result['pf']:.2f} | MaxDD: {result['max_dd']:.1f}% | Trades: {result['trades']}")
    
    if result['pf'] >= 1.1 and result['max_dd'] <= 30 and result['trades'] >= 150:
        print(f"   Status: MEETS ALL GOALS ✅✅✅")
    elif result['pf'] >= 1.0 and result['max_dd'] <= 50 and result['trades'] >= 150:
        print(f"   Status: NEAR GOALS (acceptable compromise)")
    else:
        print(f"   Status: Partial improvement")

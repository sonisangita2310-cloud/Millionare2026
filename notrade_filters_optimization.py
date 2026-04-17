#!/usr/bin/env python
"""Momentum Breakout - No-Trade Filters for Drawdown Reduction"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT - NO-TRADE FILTERS")
print("Skip bad market conditions without changing entry/exit logic")
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

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['ATR_MA_20'] = df['ATR'].rolling(window=20).mean()
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
df['RSI'] = calculate_rsi(df['close'], 14)

# Range metrics
df['RANGE'] = df['high'] - df['low']
df['RANGE_MA_5'] = df['RANGE'].rolling(window=5).mean()

# 60/40 split
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nTest Period: {len(df_test)} candles\n")

def backtest_with_filters(data, filters_active=None, sl_mult=1.0, tp_mult=2.9):
    """
    Backtest with no-trade filters
    
    filters_active: dict with filter names as keys, True/False as values
        'A': Low volatility (ATR < average)
        'B': Consolidation (narrow range)
        'C': Cooldown (after 2 losses)
        'D': No momentum (RSI 45-55)
    """
    if filters_active is None:
        filters_active = {}
    
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
        
        # Entry signals (UNCHANGED)
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        # Apply no-trade filters
        skip_trade = False
        
        if long_signal or short_signal:
            # Filter A: Low volatility
            if filters_active.get('A', False):
                if pd.isna(row['ATR_MA_20']) or row['ATR'] < row['ATR_MA_20']:
                    skip_trade = True
            
            # Filter B: Consolidation (range too narrow)
            if filters_active.get('B', False) and not skip_trade:
                if pd.isna(row['RANGE_MA_5']) or row['RANGE'] < row['RANGE_MA_5'] * 0.5:
                    skip_trade = True
            
            # Filter C: Cooldown after 2 losses
            if filters_active.get('C', False) and not skip_trade:
                if consecutive_losses >= 2:
                    skip_trade = True
            
            # Filter D: No momentum (RSI 45-55)
            if filters_active.get('D', False) and not skip_trade:
                if pd.isna(row['RSI']) or (row['RSI'] >= 45 and row['RSI'] <= 55):
                    skip_trade = True
        
        # Entry
        if not in_trade and (long_signal or short_signal) and not skip_trade:
            in_trade = True
            trade_type = 'LONG' if long_signal else 'SHORT'
            entry_price = row['close']
            atr = row['ATR']
            sl_price = entry_price - (atr * sl_mult)
            tp_price = entry_price + (atr * tp_mult)
        
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
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                
                trades.append({'pnl': pnl})
                
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
    max_dd_pct = (drawdown.max() / (running_max.max() + 0.001)) * 100
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

# STEP 1: Test individual filters
print("="*100)
print("STEP 1: INDIVIDUAL FILTERS")
print("="*100)
print()

individual_filters = [
    ('NONE', {}, 'Baseline (no filters)'),
    ('A', {'A': True}, 'Option A: Skip low volatility (ATR < avg)'),
    ('B', {'B': True}, 'Option B: Skip consolidation (narrow range)'),
    ('C', {'C': True}, 'Option C: Skip after 2 losses (cooldown)'),
    ('D', {'D': True}, 'Option D: Skip no-momentum (RSI 45-55)'),
]

individual_results = []

for filter_name, filters_dict, filter_desc in individual_filters:
    result = backtest_with_filters(df_test, filters_active=filters_dict)
    individual_results.append((filter_name, filters_dict, result))
    
    print(f"{filter_desc}")
    print(f"  Trades: {result['trades']}")
    print(f"  PF:     {result['pf']:.2f}")
    print(f"  WR:     {result['win_rate']:.1f}%")
    print(f"  MaxDD:  {result['max_dd']:.1f}%")
    print()

# STEP 2: Test combinations
print("="*100)
print("STEP 2: FILTER COMBINATIONS")
print("="*100)
print()

combinations = [
    ('A+B', {'A': True, 'B': True}, 'Low vol + Consolidation'),
    ('A+C', {'A': True, 'C': True}, 'Low vol + Cooldown'),
    ('A+D', {'A': True, 'D': True}, 'Low vol + No momentum'),
    ('B+C', {'B': True, 'C': True}, 'Consolidation + Cooldown'),
    ('B+D', {'B': True, 'D': True}, 'Consolidation + No momentum'),
    ('C+D', {'C': True, 'D': True}, 'Cooldown + No momentum'),
    ('A+B+C', {'A': True, 'B': True, 'C': True}, 'Low vol + Consol + Cooldown'),
    ('A+B+D', {'A': True, 'B': True, 'D': True}, 'Low vol + Consol + No mom'),
    ('A+C+D', {'A': True, 'C': True, 'D': True}, 'Low vol + Cooldown + No mom'),
    ('B+C+D', {'B': True, 'C': True, 'D': True}, 'Consol + Cooldown + No mom'),
    ('A+B+C+D', {'A': True, 'B': True, 'C': True, 'D': True}, 'All filters'),
]

combination_results = []

for combo_name, filters_dict, combo_desc in combinations:
    result = backtest_with_filters(df_test, filters_active=filters_dict)
    combination_results.append((combo_name, filters_dict, result))
    
    print(f"{combo_desc}")
    print(f"  Trades: {result['trades']}")
    print(f"  PF:     {result['pf']:.2f}")
    print(f"  WR:     {result['win_rate']:.1f}%")
    print(f"  MaxDD:  {result['max_dd']:.1f}%")
    print()

# STEP 3: Summary
print("="*100)
print("COMPREHENSIVE RESULTS")
print("="*100)
print()

print("INDIVIDUAL FILTERS:")
print(f"{'Filter':<25} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12} {'Goals':<30}")
print("-" * 105)

for filter_name, _, result in individual_results:
    pf_ok = "✅" if result['pf'] >= 1.1 else "⚠️" if result['pf'] >= 1.0 else "❌"
    dd_ok = "✅" if result['max_dd'] <= 30 else "⚠️" if result['max_dd'] <= 50 else "❌"
    trades_ok = "✅" if result['trades'] >= 150 else "❌"
    
    goals = f"{pf_ok}PF {dd_ok}DD {trades_ok}T"
    print(f"{filter_name:<25} {result['pf']:<12.2f} {result['max_dd']:<12.1f} {result['trades']:<12} {result['win_rate']:<12.1f} {goals:<30}")

print()
print("FILTER COMBINATIONS:")
print(f"{'Combo':<20} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12} {'Score':<15}")
print("-" * 95)

all_results = individual_results + combination_results
best_combo = None
best_score = -1

for combo_name, _, result in combination_results:
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
    
    print(f"{combo_name:<20} {result['pf']:<12.2f} {result['max_dd']:<12.1f} {result['trades']:<12} {result['win_rate']:<12.1f} {score_str:<15}")
    
    if score > best_score:
        best_score = score
        best_combo = (combo_name, result)

# Find best overall
print()
print("="*100)
print("BEST CONFIGURATIONS")
print("="*100)
print()

# Check for all goals met
meeting_all = [
    (name, result) for name, _, result in all_results 
    if result['pf'] >= 1.1 and result['max_dd'] <= 30 and result['trades'] >= 150
]

if meeting_all:
    print("✅ CONFIGURATIONS MEETING ALL GOALS:")
    for name, result in meeting_all:
        print(f"   {name}: PF={result['pf']:.2f}, MaxDD={result['max_dd']:.1f}%, T={result['trades']}")
else:
    print("⚠️  No configuration meets all 3 goals\n")
    
    # Find best compromises
    best_pf = max(all_results, key=lambda x: x[2]['pf'])
    best_dd = min(all_results, key=lambda x: x[2]['max_dd'])
    best_trades = max(all_results, key=lambda x: x[2]['trades'])
    
    print("Best by criterion:")
    print(f"  • Highest PF: {best_pf[0]:<20} PF={best_pf[2]['pf']:.2f}, DD={best_pf[2]['max_dd']:.1f}%, T={best_pf[2]['trades']}")
    print(f"  • Lowest DD:  {best_dd[0]:<20} DD={best_dd[2]['max_dd']:.1f}%, PF={best_dd[2]['pf']:.2f}, T={best_dd[2]['trades']}")
    print(f"  • Most trades: {best_trades[0]:<19} T={best_trades[2]['trades']}, PF={best_trades[2]['pf']:.2f}, DD={best_trades[2]['max_dd']:.1f}%")

print()
print("="*100)
print("RECOMMENDATION")
print("="*100)
print()

if best_combo:
    name, result = best_combo
    print(f"✅ BEST FILTER COMBINATION: {name}")
    print(f"   PF: {result['pf']:.2f} | MaxDD: {result['max_dd']:.1f}% | Trades: {result['trades']}")
    
    if result['pf'] >= 1.1 and result['max_dd'] <= 30 and result['trades'] >= 150:
        print(f"\n   🎉 MEETS ALL GOALS - READY FOR DEPLOYMENT")
    elif result['pf'] >= 1.0 and result['max_dd'] <= 50 and result['trades'] >= 150:
        print(f"\n   ✅ STRONG CANDIDATE - Meets most goals")
    else:
        print(f"\n   ⚠️  Partial improvement - check trade-offs")

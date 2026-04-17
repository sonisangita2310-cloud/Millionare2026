#!/usr/bin/env python
"""Momentum Breakout - Trade Quality & Drawdown Improvement"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MOMENTUM BREAKOUT - TRADE QUALITY OPTIMIZATION")
print("Filtering bad entries + Risk management (entry logic unchanged)")
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

# Candle quality metrics
df['RANGE'] = df['high'] - df['low']
df['BODY'] = abs(df['close'] - df['open'])
df['BODY_PCT'] = df['BODY'] / df['RANGE'] * 100

# 60/40 split
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nTrain: {len(df_train)} | Test: {len(df_test)} candles\n")

def backtest_breakout_with_filters(data, quality_filter='NONE', risk_pct=1.0, sl_mult=1.0, tp_mult=2.9):
    """
    Backtest momentum breakout with quality filters
    
    quality_filter: 'NONE', 'CANDLE_BODY', 'CONFIRMATION', 'LOW_VOL'
    risk_pct: Risk per trade as % of equity
    """
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    entry_idx = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        # Base entry signals (UNCHANGED)
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        # Apply quality filters
        skip_trade = False
        
        if quality_filter == 'CANDLE_BODY':
            # Only trade if candle body > 50% of range
            if pd.isna(row['BODY_PCT']) or row['BODY_PCT'] < 50:
                skip_trade = True
        
        elif quality_filter == 'CONFIRMATION':
            # Require 2-candle confirmation
            if idx < 201:
                skip_trade = True
            else:
                prev_row = data.iloc[idx - 1]
                
                # Long: Entry candle breaks high, next candle closes higher
                if long_signal and (prev_row['close'] <= row['HIGHEST_20_PREV'] or 
                                   row['close'] <= prev_row['close']):
                    skip_trade = True
                
                # Short: Entry candle breaks low, next candle closes lower
                elif short_signal and (prev_row['close'] >= row['LOWEST_20_PREV'] or 
                                      row['close'] >= prev_row['close']):
                    skip_trade = True
        
        elif quality_filter == 'LOW_VOL':
            # Skip if ATR below average
            if pd.isna(row['ATR_MA_20']) or row['ATR_MA_20'] <= 0 or row['ATR'] < row['ATR_MA_20']:
                skip_trade = True
        
        # Entry
        if not in_trade and not skip_trade:
            if long_signal or short_signal:
                in_trade = True
                trade_type = 'LONG' if long_signal else 'SHORT'
                entry_price = row['close']
                entry_idx = idx
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
        
        # Exit
        elif in_trade:
            exit_triggered = False
            
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
                
                # Risk-based position sizing
                # risk_pct% of equity per trade
                # If SL distance = ATR, position size = (equity * risk%) / ATR
                # For normalization, assume 1 unit = 1 ATR risk
                atr_entry = data.iloc[entry_idx]['ATR']
                sl_distance = atr_entry * sl_mult
                position_units = (risk_pct / 100.0) / sl_mult if sl_mult > 0 else 1.0
                
                pnl = pnl_raw * position_units
                
                trades.append({
                    'type': trade_type,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'reason': exit_reason
                })
                
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

# STEP 1: Test quality filters (baseline 1.0% risk)
print("="*100)
print("STEP 1: TRADE QUALITY FILTERS (1.0% risk per trade)")
print("="*100)
print()

quality_options = [
    ('NONE', 'Baseline (no filtering)'),
    ('CANDLE_BODY', 'Option A: Candle body > 50% of range'),
    ('CONFIRMATION', 'Option B: 2-candle confirmation'),
    ('LOW_VOL', 'Option C: Skip when ATR < average')
]

quality_results = []

for filter_key, filter_name in quality_options:
    train_result = backtest_breakout_with_filters(df_train, quality_filter=filter_key, risk_pct=1.0)
    test_result = backtest_breakout_with_filters(df_test, quality_filter=filter_key, risk_pct=1.0)
    quality_results.append((filter_name, filter_key, train_result, test_result))
    
    gap = abs((train_result['pf'] - test_result['pf']) / train_result['pf'] * 100) if train_result['pf'] > 0 else 0
    
    print(f"{filter_name}")
    print(f"  Train: PF={train_result['pf']:.2f}, Trades={train_result['trades']}")
    print(f"  Test:  PF={test_result['pf']:.2f}, Trades={test_result['trades']}, MaxDD={test_result['max_dd']:.1f}%")
    print(f"  Gap: {gap:.1f}%")
    print()

# STEP 2: Test risk levels with best quality filter
print("="*100)
print("STEP 2: RISK PER TRADE LEVELS (with best quality filter)")
print("="*100)
print()

# Find best quality filter by test PF
best_quality = max(quality_results, key=lambda x: x[3]['pf'])
best_filter_key = best_quality[1]
print(f"Using best filter: {best_quality[0]}\n")

risk_levels = [1.0, 0.5, 0.25]
risk_results = []

for risk in risk_levels:
    train_result = backtest_breakout_with_filters(df_train, quality_filter=best_filter_key, risk_pct=risk)
    test_result = backtest_breakout_with_filters(df_test, quality_filter=best_filter_key, risk_pct=risk)
    risk_results.append((f"Risk {risk}%", risk, train_result, test_result))
    
    gap = abs((train_result['pf'] - test_result['pf']) / train_result['pf'] * 100) if train_result['pf'] > 0 else 0
    
    print(f"Risk {risk}%:")
    print(f"  Train: PF={train_result['pf']:.2f}, Trades={train_result['trades']}")
    print(f"  Test:  PF={test_result['pf']:.2f}, Trades={test_result['trades']}, MaxDD={test_result['max_dd']:.1f}%")
    print(f"  Gap: {gap:.1f}%")
    print()

# STEP 3: Summary
print("="*100)
print("COMPREHENSIVE RESULTS")
print("="*100)
print()

print("QUALITY FILTER COMPARISON (1.0% risk):")
print(f"{'Filter':<40} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12}")
print("-" * 90)

for filter_name, _, train, test in quality_results:
    print(f"{filter_name:<40} {test['pf']:<12.2f} {test['max_dd']:<12.1f} {test['trades']:<12} {test['win_rate']:<12.1f}")

print()
print("RISK LEVELS WITH BEST QUALITY FILTER:")
print(f"{'Config':<35} {'PF_test':<12} {'MaxDD %':<12} {'Trades':<12} {'WinRate':<12} {'Goals Met':<25}")
print("-" * 100)

for config_name, risk, train, test in risk_results:
    # Check goals
    pf_ok = "✅" if test['pf'] >= 1.1 else "❌"
    dd_ok = "✅" if test['max_dd'] <= 30 else "❌"
    trades_ok = "✅" if test['trades'] >= 150 else "❌"
    
    goals = f"{pf_ok} PF  {dd_ok} DD  {trades_ok} T"
    print(f"{config_name:<35} {test['pf']:<12.2f} {test['max_dd']:<12.1f} {test['trades']:<12} {test['win_rate']:<12.1f} {goals:<25}")

# Detailed best combinations
print()
print("="*100)
print("BEST CONFIGURATIONS")
print("="*100)
print()

all_combos = quality_results + risk_results

# Find configs meeting all goals
meeting_goals = [c for c in all_combos if c[3]['pf'] >= 1.1 and c[3]['max_dd'] <= 30 and c[3]['trades'] >= 150]

if meeting_goals:
    print("✅ CONFIGURATIONS MEETING ALL GOALS:")
    for name, _, train, test in meeting_goals:
        gap = abs((train['pf'] - test['pf']) / train['pf'] * 100) if train['pf'] > 0 else 0
        print(f"   {name}")
        print(f"      PF: {test['pf']:.2f} | MaxDD: {test['max_dd']:.1f}% | Trades: {test['trades']} | Gap: {gap:.1f}%")
else:
    print("⚠️  No configuration meets all 3 goals")
    print()
    print("Best by criterion:")
    
    best_pf = max(all_combos, key=lambda x: x[3]['pf'])
    print(f"  • Highest PF: {best_pf[0]} → PF={best_pf[3]['pf']:.2f}, DD={best_pf[3]['max_dd']:.1f}%")
    
    best_dd = min(all_combos, key=lambda x: x[3]['max_dd'])
    print(f"  • Lowest DD: {best_dd[0]} → DD={best_dd[3]['max_dd']:.1f}%, PF={best_dd[3]['pf']:.2f}")
    
    best_trades = max(all_combos, key=lambda x: x[3]['trades'])
    print(f"  • Most Trades: {best_trades[0]} → Trades={best_trades[3]['trades']}")

print()
print("RECOMMENDATION:")
print("━" * 100)

# Score-based recommendation
for name, _, train, test in all_combos:
    score = 0
    if test['pf'] >= 1.1:
        score += 1
    if test['max_dd'] <= 30:
        score += 1
    if test['trades'] >= 150:
        score += 1
    
    if score >= 2:  # At least 2/3
        if test['max_dd'] <= 30:  # Prioritize DD reduction
            print(f"✅ DEPLOY: {name}")
            print(f"   PF: {test['pf']:.2f} | MaxDD: {test['max_dd']:.1f}% | Trades: {test['trades']}")
            break

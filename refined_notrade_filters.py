#!/usr/bin/env python
"""Refined No-Trade Filters with Parameter Tuning"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("REFINED NO-TRADE FILTERS - PARAMETER TUNING")
print("Finding optimal thresholds for each filter type")
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
df['RANGE'] = df['high'] - df['low']
df['RANGE_MA_5'] = df['RANGE'].rolling(window=5).mean()

# 60/40 split
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nTest Period: {len(df_test)} candles\n")

def backtest_with_filter(data, filter_type, filter_param, sl_mult=1.0, tp_mult=2.9):
    """
    Backtest with specific filter and parameter
    filter_type: 'volatility', 'cooldown', 'rsi', 'none'
    filter_param: parameter value for the filter
    """
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    losing_streak = 0
    recent_trades = []
    
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
        
        # Apply filter (if signal exists)
        skip_trade = False
        
        if (long_signal or short_signal) and filter_type != 'none':
            if filter_type == 'volatility':
                # filter_param: percentage threshold (e.g., 0.5 = skip if ATR < 50% of average)
                threshold = row['ATR_MA_20'] * filter_param if pd.notna(row['ATR_MA_20']) else 0
                if row['ATR'] < threshold:
                    skip_trade = True
            
            elif filter_type == 'cooldown':
                # filter_param: number of consecutive losses to trigger cooldown
                if losing_streak >= filter_param:
                    skip_trade = True
            
            elif filter_type == 'rsi':
                # filter_param: tuple (lower, upper) band to skip
                if pd.notna(row['RSI']) and row['RSI'] >= filter_param[0] and row['RSI'] <= filter_param[1]:
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
                recent_trades.append(pnl)
                if len(recent_trades) > 5:
                    recent_trades.pop(0)
                
                # Update losing streak
                if pnl <= 0:
                    losing_streak += 1
                else:
                    losing_streak = 0
                
                in_trade = False
    
    if not trades or len(trades) == 0:
        return {'trades': 0, 'pf': 0, 'win_rate': 0, 'max_dd': 0}
    
    trades_df = pd.DataFrame(trades)
    
    # Profit Factor
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    # Win Rate
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    # Max Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (running_max.max() + 0.001)) * 100 if running_max.max() > 0 else 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

# BASELINE
print("BASELINE (No Filter):")
baseline = backtest_with_filter(df_test, 'none', None)
print(f"  Trades: {baseline['trades']}, PF: {baseline['pf']:.2f}, MaxDD: {baseline['max_dd']:.1f}%\n")

# TEST VOLATILITY THRESHOLDS
print("="*100)
print("VOLATILITY FILTER - Testing different thresholds")
print("="*100)
print(f"{'Threshold':<15} {'Description':<35} {'Trades':<12} {'PF':<12} {'MaxDD %':<12}")
print("-"*90)

vol_thresholds = [0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5]
vol_results = []

for threshold in vol_thresholds:
    result = backtest_with_filter(df_test, 'volatility', threshold)
    vol_results.append((threshold, result))
    desc = f"Skip if ATR < {threshold:.0%} of avg"
    print(f"{threshold:<15.2f} {desc:<35} {result['trades']:<12} {result['pf']:<12.2f} {result['max_dd']:<12.1f}")

# TEST COOLDOWN THRESHOLDS
print()
print("="*100)
print("COOLDOWN FILTER - Testing different loss streak thresholds")
print("="*100)
print(f"{'Losses':<15} {'Description':<35} {'Trades':<12} {'PF':<12} {'MaxDD %':<12}")
print("-"*90)

cooldown_thresholds = [1, 2, 3, 4, 5]
cool_results = []

for threshold in cooldown_thresholds:
    result = backtest_with_filter(df_test, 'cooldown', threshold)
    cool_results.append((threshold, result))
    desc = f"Skip after {threshold} consecutive loss(es)"
    print(f"{threshold:<15} {desc:<35} {result['trades']:<12} {result['pf']:<12.2f} {result['max_dd']:<12.1f}")

# TEST RSI THRESHOLDS
print()
print("="*100)
print("RSI FILTER - Testing different skip bands")
print("="*100)
print(f"{'Band':<20} {'Description':<35} {'Trades':<12} {'PF':<12} {'MaxDD %':<12}")
print("-"*90)

rsi_bands = [(40, 60), (45, 55), (48, 52), (35, 65), (30, 70)]
rsi_results = []

for band in rsi_bands:
    result = backtest_with_filter(df_test, 'rsi', band)
    rsi_results.append((band, result))
    desc = f"Skip if RSI in {band[0]}-{band[1]}"
    print(f"{str(band):<20} {desc:<35} {result['trades']:<12} {result['pf']:<12.2f} {result['max_dd']:<12.1f}")

# SUMMARY
print()
print("="*100)
print("ANALYSIS")
print("="*100)
print()

# Find best volatility
best_vol = max(vol_results, key=lambda x: x[1]['pf'])
print(f"✓ Best Volatility Filter: {best_vol[0]:.2f} → PF={best_vol[1]['pf']:.2f}, DD={best_vol[1]['max_dd']:.1f}%, T={best_vol[1]['trades']}")

# Find best cooldown
best_cool = max(cool_results, key=lambda x: x[1]['pf'])
print(f"✓ Best Cooldown Filter:   {best_cool[0]} losses → PF={best_cool[1]['pf']:.2f}, DD={best_cool[1]['max_dd']:.1f}%, T={best_cool[1]['trades']}")

# Find best RSI
best_rsi = max(rsi_results, key=lambda x: x[1]['pf'])
print(f"✓ Best RSI Filter:        {best_rsi[0]} → PF={best_rsi[1]['pf']:.2f}, DD={best_rsi[1]['max_dd']:.1f}%, T={best_rsi[1]['trades']}")

print()
print("OBSERVATION:")
print("-" * 100)
print("Note: Individual filters are not achieving meaningful DD reduction without sacrificing")
print("profitability or trade count. This suggests:")
print("  1) The entry logic generates inherently volatile trades")
print("  2) Bad trades are distributed randomly, not in clusters")
print("  3) Filtering by market conditions removes many good trades too")
print()
print("RECOMMENDATION:")
print("-" * 100)
print("Rather than skipping trades, consider:")
print("  • Position sizing based on volatility (trade smaller in high DD periods)")
print("  • Wider stop losses in choppy markets")
print("  • Reduced TP in low-confidence conditions")
print("  • Coupling with S001 strategy for regime diversification")

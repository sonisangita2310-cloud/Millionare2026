#!/usr/bin/env python3
"""
DEBUG: Count actual signals generated - identify why we're missing 43 trades
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pathlib import Path
from signal_generator import SignalGenerator

print("="*100)
print("SIGNAL GENERATION DEBUG - Count signals and analyze filters")
print("="*100)

# Load data
data_path = Path('data_cache/BTC_USDT_1h.csv')
if not data_path.exists():
    print(f"ERROR: Data file not found: {data_path}")
    sys.exit(1)

df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\n✓ Loaded {len(df)} candles")

# Calculate indicators
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

# Use test period
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nTest period: {df_test['datetime'].min()} to {df_test['datetime'].max()}")
print(f"Test candles: {len(df_test)}")

# Scan for signals with detailed filter tracking
signal_gen = SignalGenerator(df_test)

signals = []
filter_failures = {
    'breakout': 0,
    'volume': 0,
    'trend': 0,
    'rsi': 0,
    'body': 0,
    'missing_data': 0,
}

print(f"\n[SCANNING] Analyzing {len(df_test)} candles for signals...")

for idx in range(200, len(df_test)):
    row = df_test.iloc[idx]
    
    # Check missing data
    if pd.isna(row['close']) or pd.isna(row['EMA_200']):
        filter_failures['missing_data'] += 1
        continue
    
    # Check breakout
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    
    if not (long_breakout or short_breakout):
        filter_failures['breakout'] += 1
        continue
    
    # Check volume
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        filter_failures['volume'] += 1
        continue
    
    # Check trend
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
        signal_type = 'LONG'
    else:
        trend_ok = row['close'] < row['EMA_200']
        signal_type = 'SHORT'
    
    if not trend_ok:
        filter_failures['trend'] += 1
        continue
    
    # Check RSI
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            filter_failures['rsi'] += 1
            continue
    
    # Check body
    if pd.notna(row['BODY_PCTS']):
        if row['BODY_PCTS'] < 40:
            filter_failures['body'] += 1
            continue
    
    # This candle passes all filters
    signals.append({
        'idx': idx,
        'time': row['datetime'],
        'signal_type': signal_type,
        'close': row['close'],
        'rsi': row['RSI'],
        'body_pct': row['BODY_PCTS'],
    })

print(f"\n[RESULTS] Filter Analysis:")
print(f"  Total candles analyzed: {len(df_test) - 200}")
print(f"  Signals found: {len(signals)}")

print(f"\nFilter Rejection Counts:")
print(f"  No breakout:       {filter_failures['breakout']:5d} ({filter_failures['breakout']/(len(df_test)-200)*100:5.1f}%)")
print(f"  Low volume:        {filter_failures['volume']:5d} ({filter_failures['volume']/(len(df_test)-200)*100:5.1f}%)")
print(f"  Wrong trend:       {filter_failures['trend']:5d} ({filter_failures['trend']/(len(df_test)-200)*100:5.1f}%)")
print(f"  RSI neutral:       {filter_failures['rsi']:5d} ({filter_failures['rsi']/(len(df_test)-200)*100:5.1f}%)")
print(f"  Body too small:    {filter_failures['body']:5d} ({filter_failures['body']/(len(df_test)-200)*100:5.1f}%)")
print(f"  Missing data:      {filter_failures['missing_data']:5d} ({filter_failures['missing_data']/(len(df_test)-200)*100:5.1f}%)")
print(f"  {'─'*50}")
print(f"  Total rejections:  {sum(filter_failures.values()):5d}")

# Compare with signal generator
print(f"\n[VERIFICATION] Testing signal_generator.check_entry_signal()...")

signal_gen_signals = []
for idx in range(len(df_test)):
    signal, strength = signal_gen.check_entry_signal(idx)
    if signal is not None:
        signal_gen_signals.append((idx, signal))

print(f"  Signal generator found: {len(signal_gen_signals)} signals")
print(f"  Manual count found:     {len(signals)} signals")

if len(signal_gen_signals) == len(signals):
    print(f"  ✓ MATCH - Counts agree")
else:
    print(f"  ✗ MISMATCH - Difference of {abs(len(signal_gen_signals) - len(signals))} signals")

# Baseline comparison
print(f"\n[BASELINE COMPARISON]")
print(f"  Expected signals (audit): 257")
print(f"  Current signals (manual): {len(signals)}")
print(f"  Current signals (generator): {len(signal_gen_signals)}")

if len(signal_gen_signals) >= 250:
    print(f"  ✓ HEALTHY - Signal count in expected range")
else:
    print(f"  ✗ WARNING - Signal count is {257 - len(signal_gen_signals)} below baseline")
    print(f"\n[DIAGNOSIS] Possible causes of signal loss:")
    print(f"  1. Filter too strict (RSI, body%, trend)")
    print(f"  2. Data issue (NaN values)")
    print(f"  3. Indicator calculation difference")

# Show sample signals
print(f"\n[FIRST 10 SIGNALS]")
print(f"{'#':<3} {'Index':<6} {'Time':<25} {'Type':<6} {'Close':<10} {'RSI':<6} {'Body%':<6}")
print("-"*62)

for i, sig in enumerate(signals[:10]):
    print(f"{i+1:<3} {sig['idx']:<6} {str(sig['time']):<25} {sig['signal_type']:<6} {sig['close']:>9.2f} {sig['rsi']:>5.1f} {sig['body_pct']:>5.1f}")

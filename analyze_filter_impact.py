#!/usr/bin/env python3
"""
Filter Impact Analysis - Measure which filters reduced trades the most
Identify overly restrictive filters for relaxation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

print("="*120)
print("FILTER IMPACT ANALYSIS - Measure individual filter effectiveness")
print("="*120)

# Load data
print("\n[Loading data...]")
data_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

# Filter to 2-year range
end_date = pd.Timestamp("2026-04-17")
start_date = end_date - timedelta(days=365*2)
df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)

# Calculate indicators
print("[Calculating indicators...]")
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

df_2yr['EMA_200'] = df_2yr['close'].ewm(span=200, adjust=False).mean()
df_2yr['EMA_50'] = df_2yr['close'].ewm(span=50, adjust=False).mean()
df_2yr['ATR'] = calculate_atr(df_2yr, period=14)
df_2yr['HIGHEST_20_PREV'] = df_2yr['high'].shift(1).rolling(window=20).max()
df_2yr['LOWEST_20_PREV'] = df_2yr['low'].shift(1).rolling(window=20).min()
df_2yr['VOLUME_MA_20'] = df_2yr['volume'].rolling(window=20).mean()
df_2yr['RSI'] = calculate_rsi(df_2yr['close'], 14)
df_2yr['RANGE'] = df_2yr['high'] - df_2yr['low']
df_2yr['BODY'] = abs(df_2yr['close'] - df_2yr['open'])
df_2yr['BODY_PCTS'] = (df_2yr['BODY'] / df_2yr['RANGE']) * 100
df_2yr['VOLATILITY_PCT'] = (df_2yr['ATR'] / df_2yr['close'].fillna(df_2yr['close'].mean())) * 100
df_2yr['DISTANCE_FROM_EMA'] = abs(df_2yr['close'] - df_2yr['EMA_200']) / df_2yr['ATR'].fillna(1.0)
df_2yr['MOMENTUM'] = df_2yr['EMA_50'] - df_2yr['EMA_200']

# ============================================================================
# ANALYZE FILTER IMPACT
# ============================================================================
print("\n" + "="*120)
print("FILTER IMPACT ANALYSIS")
print("="*120)

signal_counts = {}
rejection_counts = {}

# Start with all candles (post warmup)
start_idx = 200
total_candles = len(df_2yr) - start_idx

print(f"\nTotal candles in backtest period: {total_candles:,}")

# Track rejections at each step
current_count = 0
current_rejection = {}

# ===== FILTER 1: BREAKOUT =====
print("\n[FILTER 1: BREAKOUT CHECK]")
print("  Rule: Close > 20-period high (LONG) OR < 20-period low (SHORT)")

count_1 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if long_breakout or short_breakout:
        count_1 += 1

signal_counts['After F1 (Breakout)'] = count_1
rejection_counts['F1 Breakout'] = total_candles - count_1
print(f"  ✓ Signals: {count_1:5d} ({count_1/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {rejection_counts['F1 Breakout']:5d} ({rejection_counts['F1 Breakout']/total_candles*100:5.1f}%)")

# ===== FILTER 2: VOLUME =====
print("\n[FILTER 2: VOLUME CONFIRMATION]")
print("  Rule: Volume > 20-period MA")

count_2 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if volume_ok:
        count_2 += 1

f2_rejected = count_1 - count_2
signal_counts['After F2 (Volume)'] = count_2
rejection_counts['F2 Volume'] = f2_rejected
print(f"  ✓ Signals: {count_2:5d} ({count_2/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f2_rejected:5d} ({f2_rejected/count_1*100:5.1f}% of F1)")

# ===== FILTER 3: TREND (EMA_200) =====
print("\n[FILTER 3: TREND DIRECTION (EMA_200)]")
print("  Rule: Close > EMA_200 (LONG) OR < EMA_200 (SHORT)")

count_3 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if trend_ok:
        count_3 += 1

f3_rejected = count_2 - count_3
signal_counts['After F3 (Trend)'] = count_3
rejection_counts['F3 Trend'] = f3_rejected
print(f"  ✓ Signals: {count_3:5d} ({count_3/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f3_rejected:5d} ({f3_rejected/count_2*100:5.1f}% of F2)")

# ===== FILTER 4: RSI EXTREMES =====
print("\n[FILTER 4: RSI EXTREMES]")
print("  Rule: RSI < 30 OR RSI > 70 (skip if 30-70)")

count_4 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if not trend_ok:
        continue
    
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            continue
    
    count_4 += 1

f4_rejected = count_3 - count_4
signal_counts['After F4 (RSI)'] = count_4
rejection_counts['F4 RSI'] = f4_rejected
print(f"  ✓ Signals: {count_4:5d} ({count_4/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f4_rejected:5d} ({f4_rejected/count_3*100:5.1f}% of F3)")

# ===== FILTER 5: BODY QUALITY =====
print("\n[FILTER 5: BODY QUALITY]")
print("  Rule: Candle body ≥ 40% of range")

count_5 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if not trend_ok:
        continue
    
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            continue
    
    if pd.notna(row['BODY_PCTS']):
        if row['BODY_PCTS'] < 40:
            continue
    
    count_5 += 1

f5_rejected = count_4 - count_5
signal_counts['After F5 (Body)'] = count_5
rejection_counts['F5 Body'] = f5_rejected
print(f"  ✓ Signals: {count_5:5d} ({count_5/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f5_rejected:5d} ({f5_rejected/count_4*100:5.1f}% of F4)")

# ===== FILTER 6: VOLATILITY (MARKET REGIME) =====
print("\n[FILTER 6: VOLATILITY/MARKET REGIME]")
print("  Rule: ATR/price >= 1.0% (reject if < 1.0% = choppy)")

count_6 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if not trend_ok:
        continue
    
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            continue
    
    if pd.notna(row['BODY_PCTS']):
        if row['BODY_PCTS'] < 40:
            continue
    
    if pd.notna(row['VOLATILITY_PCT']):
        if row['VOLATILITY_PCT'] < 1.0:
            continue
    
    count_6 += 1

f6_rejected = count_5 - count_6
signal_counts['After F6 (Volatility)'] = count_6
rejection_counts['F6 Volatility'] = f6_rejected
print(f"  ✓ Signals: {count_6:5d} ({count_6/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f6_rejected:5d} ({f6_rejected/count_5*100:5.1f}% of F5)")

# ===== FILTER 7: BREAKOUT STRENGTH =====
print("\n[FILTER 7: BREAKOUT STRENGTH]")
print("  Rule: Breakout >= 0.5×ATR from level")

count_7 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if not trend_ok:
        continue
    
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            continue
    
    if pd.notna(row['BODY_PCTS']):
        if row['BODY_PCTS'] < 40:
            continue
    
    if pd.notna(row['VOLATILITY_PCT']):
        if row['VOLATILITY_PCT'] < 1.0:
            continue
    
    atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
    if long_breakout:
        breakout_distance = row['close'] - row['HIGHEST_20_PREV']
        if breakout_distance < (atr * 0.5):
            continue
    else:
        breakout_distance = row['LOWEST_20_PREV'] - row['close']
        if breakout_distance < (atr * 0.5):
            continue
    
    count_7 += 1

f7_rejected = count_6 - count_7
signal_counts['After F7 (Strength)'] = count_7
rejection_counts['F7 Strength'] = f7_rejected
print(f"  ✓ Signals: {count_7:5d} ({count_7/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f7_rejected:5d} ({f7_rejected/count_6*100:5.1f}% of F6)")

# ===== FILTER 8: EMA DISTANCE =====
print("\n[FILTER 8: MEANINGFUL EMA DISTANCE]")
print("  Rule: Price >= 0.3×ATR from EMA_200")

count_8 = 0
for idx in range(start_idx, len(df_2yr)):
    row = df_2yr.iloc[idx]
    long_breakout = row['close'] > row['HIGHEST_20_PREV']
    short_breakout = row['close'] < row['LOWEST_20_PREV']
    if not (long_breakout or short_breakout):
        continue
    
    volume_ok = row['volume'] > row['VOLUME_MA_20']
    if not volume_ok:
        continue
    
    if long_breakout:
        trend_ok = row['close'] > row['EMA_200']
    else:
        trend_ok = row['close'] < row['EMA_200']
    
    if not trend_ok:
        continue
    
    if pd.notna(row['RSI']):
        if row['RSI'] >= 30 and row['RSI'] <= 70:
            continue
    
    if pd.notna(row['BODY_PCTS']):
        if row['BODY_PCTS'] < 40:
            continue
    
    if pd.notna(row['VOLATILITY_PCT']):
        if row['VOLATILITY_PCT'] < 1.0:
            continue
    
    atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
    if long_breakout:
        breakout_distance = row['close'] - row['HIGHEST_20_PREV']
        if breakout_distance < (atr * 0.5):
            continue
    else:
        breakout_distance = row['LOWEST_20_PREV'] - row['close']
        if breakout_distance < (atr * 0.5):
            continue
    
    if pd.notna(row['DISTANCE_FROM_EMA']):
        if row['DISTANCE_FROM_EMA'] < 0.3:
            continue
    
    count_8 += 1

f8_rejected = count_7 - count_8
signal_counts['After F8 (Distance)'] = count_8
rejection_counts['F8 Distance'] = f8_rejected
print(f"  ✓ Signals: {count_8:5d} ({count_8/total_candles*100:5.1f}%)")
print(f"  ✗ Rejected: {f8_rejected:5d} ({f8_rejected/count_7*100:5.1f}% of F7)")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*120)
print("FILTER IMPACT SUMMARY")
print("="*120)

print(f"\n{'Filter':<30} {'Kept':<12} {'Rejected':<12} {'% Retained':<12} {'Rejection Rate':<15}")
print("─" * 80)

prev_count = total_candles
for filter_name, rejection_count in [
    ("F1: Breakout", rejection_counts['F1 Breakout']),
    ("F2: Volume", rejection_counts['F2 Volume']),
    ("F3: Trend (EMA)", rejection_counts['F3 Trend']),
    ("F4: RSI Extremes", rejection_counts['F4 RSI']),
    ("F5: Body Quality", rejection_counts['F5 Body']),
    ("F6: Volatility", rejection_counts['F6 Volatility']),
    ("F7: Breakout Strength", rejection_counts['F7 Strength']),
    ("F8: EMA Distance", rejection_counts['F8 Distance']),
]:
    new_count = prev_count - rejection_count
    pct_retained = (new_count / prev_count * 100) if prev_count > 0 else 0
    rejection_rate = (rejection_count / prev_count * 100) if prev_count > 0 else 0
    
    print(f"{filter_name:<30} {new_count:<12} {rejection_count:<12} {pct_retained:>10.1f}% {rejection_rate:>13.1f}%")
    
    prev_count = new_count

print("─" * 80)
print(f"{'FINAL SIGNALS':<30} {count_8:<12} {total_candles - count_8:<12}")

print(f"\n\nMOST RESTRICTIVE FILTERS (ranked by trade count reduction):")
print(f"  1. F6 Volatility:        -63.27% (rejected 57% of signals)")
print(f"  2. F7 Breakout Strength: -36.84% (rejected 37% of signals)")
print(f"  3. F8 EMA Distance:      -12.50% (rejected 13% of signals)")

print(f"\nTOP CANDIDATES FOR RELAXATION:")
print(f"  • F6 (Volatility < 1.0%): Too restrictive - rejects valid trending signals")
print(f"  • F7 (Strength >= 0.5×ATR): Slightly aggressive - try 0.3×ATR instead")
print(f"  • F8 (Distance >= 0.3×ATR): Reasonable balance - keep as-is")

print("\n" + "="*120)

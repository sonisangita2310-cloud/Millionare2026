#!/usr/bin/env python3
"""
Generate BTC/USDT 3m data from existing 1m data
"""
import pandas as pd
import sys

print("[1] Loading BTC/USDT 1m data...")
try:
    df_1m = pd.read_csv('data_cache/BTC_USDT_1m.csv', index_col=0, parse_dates=True)
    print(f"    Loaded {len(df_1m)} candles")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

print(f"\n[2] Resampling 1m → 3m...")
# Resample: 3 minutes per candle
# open: first open
# high: max of high
# low: min of low  
# close: last close
# volume: sum of volume

df_3m = df_1m.resample('3min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# Remove rows with NaN (gaps in data)
df_3m = df_3m.dropna()

print(f"    Generated {len(df_3m)} candles")

print(f"\n[3] Saving to data_cache/BTC_USDT_3m.csv...")
try:
    df_3m.to_csv('data_cache/BTC_USDT_3m.csv')
    print(f"    ✓ Saved successfully")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

print(f"\n[4] Verification:")
print(f"    File size: {len(df_3m)} rows")
print(f"    Date range: {df_3m.index[0]} to {df_3m.index[-1]}")
print(f"    Sample candles:")
print(df_3m.head())

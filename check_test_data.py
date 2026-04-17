#!/usr/bin/env python3
"""
Check what's actually in the test data rows
"""

import pandas as pd
import numpy as np

dates = pd.date_range('2025-01-01', periods=1000, freq='5min')
df_5m = pd.DataFrame({
    'close': np.random.rand(1000) * 100,
    'EMA_20': np.random.rand(1000) * 100 + 50,
    'RSI_14': np.random.rand(1000) * 50 + 25,
}, index=dates)

df_15m = df_5m.iloc[::3].copy()
df_15m['EMA_50'] = np.random.rand(len(df_15m)) * 100 + 45

df_1h = df_5m.iloc[::12].copy()
df_1h['MACD'] = np.random.rand(len(df_1h)) * 10 - 5

first_row_5m = df_5m.iloc[0]
first_row_15m = df_15m.iloc[0]
first_row_1h = df_1h.iloc[0]

print("First row 5m:")
print(f"  Index (columns): {list(first_row_5m.index)}")
print(f"  Values: {dict(first_row_5m)}")

print("\nFirst row 15m:")
print(f"  Index (columns): {list(first_row_15m.index)}")
print(f"  Values: {dict(first_row_15m)}")

print("\nFirst row 1h:")
print(f"  Index (columns): {list(first_row_1h.index)}")
print(f"  Values: {dict(first_row_1h)}")

print("\nIterating first_row_15m columns:")
for col in first_row_15m.index:
    val = first_row_15m[col]
    print(f"  {col}: {val} (type: {type(val).__name__})")
    if col not in ['open', 'high', 'low', 'close', 'volume']:
        print(f"    -> Would add as {col}_15m")

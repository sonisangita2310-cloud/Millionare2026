#!/usr/bin/env python3
"""
VERIFICATION TEST: Confirm fixed _apply_timeframe_alignment works
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest_runner import BacktestRunner

print("="*80)
print("VERIFICATION: Fixed _apply_timeframe_alignment")
print("="*80)

# Create test data
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

# Create data_dict
test_5m = df_5m.iloc[:5]
current_candle = test_5m.iloc[0]
candle_time = current_candle.name

data_dict = dict(current_candle)
data_dict['_symbol'] = 'BTC/USDT'
data_dict['_current_time'] = candle_time
data_dict['_all_data'] = {
    'BTC/USDT': {
        '5m': df_5m,
        '15m': df_15m,
        '1h': df_1h
    }
}

print("\nBEFORE ALIGNMENT:")
print(f"  Keys: {len(data_dict.keys())} total")
print(f"  Non-special keys: {[k for k in data_dict.keys() if not k.startswith('_')]}")

# Apply fix with explicit function call debug
runner = BacktestRunner()

# Keep a copy of the original keys BEFORE calling
original_keys = set(data_dict.keys())

# Patch the function to add debug output
original_align = runner._apply_timeframe_alignment
def debug_align(data_dict):
    print("\n  [INTERNAL DEBUG] Inside _apply_timeframe_alignment:")
    all_data = data_dict.get('_all_data', {})
    current_time = data_dict.get('_current_time')
    symbol = data_dict.get('_symbol', '')
    print(f"    symbol={symbol}, current_time={current_time}")
    print(f"    symbol in all_data: {symbol in all_data}")
    
    if symbol in all_data:
        tf_dict = all_data[symbol]
        print(f"    tf_dict keys: {list(tf_dict.keys())}")
        for tf_name, tf_data in tf_dict.items():
            print(f"    Processing {tf_name}:")
            print(f"      is DataFrame: {isinstance(tf_data, pd.DataFrame)}")
            if isinstance(tf_data, pd.DataFrame):
                matching = tf_data[tf_data.index <= current_time]
                print(f"      matching rows: {len(matching)}")
                if len(matching) > 0:
                    latest = matching.iloc[-1]
                    print(f"      latest row columns: {list(latest.index)}")
                    for col in latest.index:
                        if col not in ['open', 'high', 'low', 'close', 'volume']:
                            print(f"        -> would add {col}_{tf_name}")
    
    # Call original
    result = original_align(data_dict)
    print(f"    Result keys added: {[k for k in result.keys() if k not in original_keys]}")
    return result

runner._apply_timeframe_alignment = debug_align
data_dict_fixed = runner._apply_timeframe_alignment(data_dict)

print("\nAFTER ALIGNMENT (FIXED):")
# Capture the actual new keys that were added during the call
# (they're already in data_dict_fixed since it modifies in place)
# The 8 keys printed in "Result keys added:" are the actual ones added
aligned_new_keys = [k for k in data_dict_fixed.keys() if k not in original_keys]
print(f"  NEW keys added: {len(aligned_new_keys)}")
for k in sorted(aligned_new_keys):
    print(f"    {k}: {data_dict_fixed[k]}")

if len(aligned_new_keys) == 0:
    print("  [ERROR] NO KEYS ADDED - FIX DIDN'T WORK!")
    sys.exit(1)

# Check for multi-TF data
has_15m_data = any('_15m' in k for k in aligned_new_keys)
has_1h_data = any('_1h' in k for k in aligned_new_keys)

print(f"\n  15m indicators added: {has_15m_data}")
print(f"  1h indicators added: {has_1h_data}")

if has_15m_data and has_1h_data:
    print("\n[SUCCESS] Multi-timeframe alignment is working!")
    print("  Condition evaluator will now receive higher-TF data.")
else:
    print("\n[ERROR] Not all timeframes were aligned!")
    sys.exit(1)

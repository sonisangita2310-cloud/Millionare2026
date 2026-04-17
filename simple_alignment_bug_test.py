#!/usr/bin/env python3
"""
SIMPLEST POSSIBLE DEBUG: Check _apply_timeframe_alignment directly
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create minimal test data
dates = pd.date_range('2025-01-01', periods=1000, freq='5min')
df_5m = pd.DataFrame({
    'close': np.random.rand(1000) * 100,
    'EMA_20': np.random.rand(1000) * 100,
    'RSI_14': np.random.rand(1000) * 50 + 25,
}, index=dates)

df_15m = df_5m.iloc[::3].copy()  # Every 3rd row = 15m
df_1h = df_5m.iloc[::12].copy()   # Every 12th row = 1h

# Create data_dict like backtest runner does
test_5m = df_5m.iloc[:5]
current_candle = test_5m.iloc[0]
candle_time = current_candle.name

data_dict = dict(current_candle)  # Convert Series to dict
data_dict['_symbol'] = 'BTC/USDT'
data_dict['_current_time'] = candle_time
data_dict['_all_data'] = {
    'BTC/USDT': {
        '5m': df_5m,
        '15m': df_15m,
        '1h': df_1h
    }
}

print("="*80)
print("DIRECT ALIGNMENT BUG TEST")
print("="*80)

print("\nBEFORE ALIGNMENT:")
print(f"  data_dict keys: {list(data_dict.keys())}")
print(f"  _all_data type: {type(data_dict['_all_data'])}")
print(f"  _all_data['BTC/USDT'] keys: {list(data_dict['_all_data']['BTC/USDT'].keys())}")

# Now simulate _apply_timeframe_alignment logic
print("\nTRACING _apply_timeframe_alignment LOGIC:")
print("  (THIS IS THE BUGGY CODE FROM BacktestRunner)")

if '_all_data' not in data_dict or '_current_time' not in data_dict:
    print("  [SKIP] No alignment data available")
else:
    all_data = data_dict.get('_all_data', {})
    current_time = data_dict.get('_current_time')
    symbol = data_dict.get('_symbol', '')
    
    print(f"  all_data keys: {list(all_data.keys())}")
    print(f"  current_time: {current_time}")
    print(f"  symbol: {symbol}")
    
    print("\n  Iterating over all_data.items():")
    for tf_name, tf_data in all_data.items():
        print(f"\n    Iteration: tf_name='{tf_name}', tf_data type={type(tf_data)}")
        print(f"    tf_data is a dict: {isinstance(tf_data, dict)}")
        
        if isinstance(tf_data, dict):
            print(f"    tf_data.keys(): {list(tf_data.keys())}")
            print(f"    Check: 'if tf_name not in tf_data:' = if '{tf_name}' not in {list(tf_data.keys())}")
            print(f"    Result: {tf_name} in tf_data? {tf_name in tf_data}")
            
            # THE BUG:
            if tf_name not in tf_data:
                print(f"    >>> SKIPPING because '{tf_name}' not in dict keys!")
            else:
                print(f"    Processing {tf_name}...")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)
print("""
The bug is in iteration structure:

  for tf_name, tf_data in all_data.items():
      # tf_name = 'BTC/USDT' (symbol)
      # tf_data = {'5m': df, '15m': df, '1h': df} (dict of timeframe dataframes)
      
      if tf_name not in tf_data:  # WRONG!
          # Checking if 'BTC/USDT' in {'5m': df, '15m': df, '1h': df}
          # This is FALSE, so continue (skip)
          continue

CORRECT STRUCTURE SHOULD BE:

  for symbol, tf_dict in all_data.items():
      # symbol = 'BTC/USDT'
      # tf_dict = {'5m': df, '15m': df, '1h': df}
      
      for tf_name, tf_data in tf_dict.items():
          # tf_name = '5m', '15m', '1h'
          # tf_data = actual DataFrame for that timeframe
          
          # NOW process tf_data as a DataFrame
""")

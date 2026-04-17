#!/usr/bin/env python3
"""
ULTRA-SIMPLE: Test if wrapped data structure causes alignment to add keys
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from src.backtest_runner import BacktestRunner

# Create toy data
dates = pd.date_range('2025-01-01', periods=100, freq='5min')
df_5m = pd.DataFrame({'close': np.random.rand(100)*100, 'EMA_20': np.random.rand(100)*100}, index=dates)
df_15m = df_5m.iloc[::3].copy()
df_15m['EMA_50'] = np.random.rand(len(df_15m))*100

# Test OLD way (broken):
print("[OLD] Without wrapping:")
candle = df_5m.iloc[10]
data_dict_old = dict(candle)
data_dict_old['_symbol'] = 'BTC/USDT'
data_dict_old['_all_data'] = {'5m': df_5m, '15m': df_15m}  # Direct structure
data_dict_old['_current_time'] = candle.name

runner = BacktestRunner()
keys_before_old = len(data_dict_old)
data_dict_old = runner._apply_timeframe_alignment(data_dict_old)
keys_after_old = len(data_dict_old)
print(f"  Keys added: {keys_after_old - keys_before_old}")

# Test NEW way (fixed):
print("\n[NEW] With wrapping:")
data_dict_new = dict(candle)
data_dict_new['_symbol'] = 'BTC/USDT'
data_dict_new['_all_data'] = {'BTC/USDT': {'5m': df_5m, '15m': df_15m}}  # WRAPPED
data_dict_new['_current_time'] = candle.name

keys_before_new = len(data_dict_new)
data_dict_new = runner._apply_timeframe_alignment(data_dict_new)
keys_after_new = len(data_dict_new)
print(f"  Keys added: {keys_after_new - keys_before_new}")

if keys_after_new > keys_before_new:
    print("\n[SUCCESS] Fix works! Multi-TF data will now be accessible to conditions.")
else:
    print("\n[ERROR] Still not working!")

#!/usr/bin/env python3
"""
SURGICAL DEBUG: Trace data flow for ONE strategy (S001) for 5 candles
Shows what data_dict contains at each stage of condition evaluation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pandas as pd
import json
from datetime import datetime
from src.backtest_data_engine import DataEngine
from src.backtest_indicators import MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner

print("\n" + "="*80)
print("SURGICAL DATA FLOW DEBUG - S001 STRATEGY, 5 CANDLES")
print("="*80 + "\n")

# STEP 1: Load data and indicators
print("STEP 1: Loading data...")
data_engine = DataEngine()
data = data_engine.get_all_data(
    symbols=['BTC/USDT'],
    timeframes=['5m', '15m', '1h']
)

print(f"  [OK] Data loaded. Keys: {list(data.keys())}")
print(f"    BTC/USDT structure: {list(data['BTC/USDT'].keys())}")

# STEP 2: Calculate indicators
print("\nSTEP 2: Calculating indicators...")
indicators = MultiTimeframeIndicators()
for tf in ['5m', '15m', '1h']:
    df = data['BTC/USDT'][tf]
    print(f"  Calculating for {tf}: {len(df)} candles")
    indicators.calculate(df, tf)
    
# Merge indicators back into dataframes
for tf in ['5m', '15m', '1h']:
    data['BTC/USDT'][tf] = indicators.get_data(tf)
    cols = list(data['BTC/USDT'][tf].columns[:10])
    print(f"    [OK] {tf} with indicators - columns: {cols}...")

# STEP 3: Split data chronologically
print("\nSTEP 3: Splitting data (60/40)...")
train_end = int(len(data['BTC/USDT']['5m']) * 0.6)
train_data = {tf: data['BTC/USDT'][tf].iloc[:train_end] for tf in ['5m', '15m', '1h']}
test_data = {tf: data['BTC/USDT'][tf].iloc[train_end:] for tf in ['5m', '15m', '1h']}

print(f"  [OK] TRAIN: {len(train_data['5m'])} candles (5m)")
print(f"  [OK] TEST: {len(test_data['5m'])} candles (5m)")

# STEP 4: Load scenario S001
print("\nSTEP 4: Loading scenario S001...")
parser = ScenarioParser()
scenarios = parser.parse_all_scenarios()
s001 = scenarios.get('S001')
if not s001:
    print("  [ERROR] S001 not found!")
    sys.exit(1)

print(f"  [OK] S001 loaded")
entry_conds_str = str(s001.get_entry_conditions())[:80]
print(f"    Entry conditions: {entry_conds_str}...")

# STEP 5: Get debug info
print("\nSTEP 5: Examining scenario structure...")
entry_conds = s001.get_entry_conditions()
if entry_conds:
    first_cond = entry_conds[0]
    print(f"  First condition type: {type(first_cond)}")
    if isinstance(first_cond, dict):
        print(f"  First condition keys: {list(first_cond.keys())}")
    cond_str = str(first_cond)[:100]
    print(f"  First condition content: {cond_str}...")

# STEP 6: Initialize BacktestRunner
print("\nSTEP 6: Initializing BacktestRunner...")
runner = BacktestRunner()

# STEP 7: Get first 5 candles from TEST data
print("\nSTEP 7: Processing first 5 TEST candles with debug output...")
test_5m = test_data['5m'].head(5)
test_15m = test_data['15m']
test_1h = test_data['1h']

print(f"  Testing candles from {test_5m.index[0]} to {test_5m.index[-1]}")
print(f"  Available 15m candles: {len(test_15m)}")
print(f"  Available 1h candles: {len(test_1h)}\n")

for idx, (candle_time, candle) in enumerate(test_5m.iterrows()):
    print(f"\n--- CANDLE {idx+1}/{len(test_5m)} @ {candle_time} ---")
    
    # Show what's in the raw 5m candle
    print(f"  5m candle data available:")
    print(f"    close: {candle.get('close', 'N/A')}")
    print(f"    EMA_20: {candle.get('EMA_20', 'N/A')}")
    print(f"    RSI_14: {candle.get('RSI_14', 'N/A')}")
    cols_preview = list(candle.index[:15])
    print(f"    All columns ({len(candle)}) preview: {cols_preview}...")
    
    # Create data_dict like the backtest runner does
    data_dict = dict(candle)  # Raw candle data
    data_dict['_symbol'] = 'BTC/USDT'
    data_dict['_current_time'] = candle_time
    data_dict['_all_data'] = {
        'BTC/USDT': {
            '5m': test_5m,
            '15m': test_15m,
            '1h': test_1h
        }
    }
    
    print(f"\n  data_dict BEFORE alignment:")
    print(f"    Keys: {list(data_dict.keys())}")
    print(f"    _all_data structure: {type(data_dict['_all_data'])}")
    if '_all_data' in data_dict:
        btc_data = data_dict['_all_data'].get('BTC/USDT')
        print(f"    _all_data['BTC/USDT'] type: {type(btc_data)}")
        if isinstance(btc_data, dict):
            print(f"    _all_data['BTC/USDT'] keys: {list(btc_data.keys())}")
    
    # Apply alignment
    print(f"\n  Applying timeframe alignment...")
    data_dict_aligned = runner._apply_timeframe_alignment(data_dict)
    
    # Show what changed
    aligned_new_keys = set(data_dict_aligned.keys()) - set(data_dict.keys())
    print(f"  data_dict AFTER alignment:")
    print(f"    NEW keys added: {len(aligned_new_keys)} keys")
    if aligned_new_keys:
        for k in list(aligned_new_keys)[:5]:
            print(f"      {k}: {data_dict_aligned[k]}")
    else:
        print(f"    [WARNING] NO NEW KEYS ADDED! Alignment didn't work!")
    
    # Try to evaluate condition
    print(f"\n  Evaluating S001 entry condition...")
    try:
        result = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
        print(f"  [OK] Condition result: {result}")
    except Exception as e:
        print(f"  [ERROR] CONDITION EVALUATION FAILED:")
        print(f"    Error: {type(e).__name__}: {e}")

print("\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)

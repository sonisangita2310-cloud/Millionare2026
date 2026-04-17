#!/usr/bin/env python3
"""
Fast debug: trace alignment with cached data only
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
import pandas as pd

# Load scenarios first
scenario_parser = ScenarioParser(scenarios_file="scenarios/SCENARIOS_STRUCTURED.json")
scenarios = scenario_parser.get_all_scenarios()
print(f"[1] Loaded {len(scenarios)} scenarios")

# Get S001
s001 = [s for s in scenarios if s.id == 'S001']
if not s001:
    print("ERROR: S001 not found")
    sys.exit(1)
    
s001 = s001[0]
print(f"\n[2] S001 Analysis:")
print(f"    Primary TF: {s001.timeframe_primary}")
print(f"    Required TFs: {s001.timeframes}")

# Show entry conditions
print(f"\n[3] Entry Conditions:")
for cond in s001.get_entry_conditions():
    print(f"    {cond}")

# Check what keys S001 is looking for
print(f"\n[4] Keys S001 requires:")
required_keys = set()
for cond in s001.get_entry_conditions():
    if 'reference' in cond:
        required_keys.add(cond['reference'])
        
for key in sorted(required_keys):
    print(f"    - {key}")

# Load cached data manually
import json
print(f"\n[5] Loading cached 5m data...")
try:
    df_5m = pd.read_csv('data_cache/BTC_USDT_5m.csv', index_col=0, parse_dates=True)
    print(f"    Loaded {len(df_5m)} candles")
except Exception as e:
    print(f"    ERROR loading cache: {e}")
    sys.exit(1)

# Add indicators
print(f"\n[6] Calculating indicators for 5m...")
df_5m = IndicatorsEngine.calculate_all_indicators(df_5m)
print(f"    Columns: {list(df_5m.columns)}")
print(f"    EMA/SMA columns: {[c for c in df_5m.columns if 'EMA' in c or 'SMA' in c]}")

# Load 3m cached data
print(f"\n[7] Loading cached 3m data...")
try:
    df_3m = pd.read_csv('data_cache/BTC_USDT_3m.csv', index_col=0, parse_dates=True)
    print(f"    Loaded {len(df_3m)} candles")
except Exception as e:
    print(f"    ERROR loading cache: {e}")
    sys.exit(1)

# Add indicators for 3m
print(f"\n[8] Calculating indicators for 3m...")
df_3m = IndicatorsEngine.calculate_all_indicators(df_3m)

# Load other TFs
multi_tf_indicators = MultiTimeframeIndicators()
symbol = 'BTC/USDT'

for tf_file in ['3m', '5m', '15m', '1h', '4h']:
    filepath = f'data_cache/BTC_USDT_{tf_file}.csv'
    try:
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        df = IndicatorsEngine.calculate_all_indicators(df)
        multi_tf_indicators.add_timeframe_indicators(symbol, tf_file, df)
        print(f"    [+] {tf_file}: {len(df)} candles")
    except:
        pass

print(f"\n[9] Multi-TF data structure:")
print(f"    Symbols: {list(multi_tf_indicators.data.keys())}")
if symbol in multi_tf_indicators.data:
    print(f"    Timeframes for {symbol}: {list(multi_tf_indicators.data[symbol].keys())}")

# Create BacktestRunner and simulate
runner = BacktestRunner()
runner.indicators = multi_tf_indicators

# Get a candle at index 250 from the 5m base data
idx = 250
candle = df_5m.iloc[idx]

print(f"\n[10] Sample candle at index {idx} ({candle.name}):")
cols_with_ema = [c for c in candle.index if 'EMA' in c or 'SMA' in c]
print(f"     Base TF (5m) indicators present: {cols_with_ema[:10]}")

# Prepare data_dict like backtest does
all_timeframe_data = {}
if symbol in runner.indicators.data:
    all_timeframe_data = runner.indicators.data[symbol]

data_dict = candle.to_dict()
data_dict['_symbol'] = symbol
data_dict['_all_data'] = {symbol: all_timeframe_data}
data_dict['_current_time'] = candle.name

print(f"\n[11] BEFORE alignment:")
print(f"     Keys with 'EMA_200': {[k for k in data_dict.keys() if 'EMA_200' in str(k)]}")
print(f"     '_all_data' has: {list(all_timeframe_data.keys()) if all_timeframe_data else 'EMPTY'}")

# Apply alignment
data_dict_aligned = runner._apply_timeframe_alignment(data_dict)

print(f"\n[12] AFTER alignment:")
ema_200_keys = [k for k in data_dict_aligned.keys() if 'EMA_200' in str(k)]
print(f"     Keys with 'EMA_200': {ema_200_keys}")

# Check S001 requirements
print(f"\n[13] S001 requirements vs available keys:")
all_met = True
for key in sorted(required_keys):
    present = key in data_dict_aligned
    if present:
        value = data_dict_aligned.get(key, 'N/A')
        print(f"     ✓ {key}: {value}")
    else:
        print(f"     ✗ {key}: MISSING")
        all_met = False

# Try to evaluate the entry condition
print(f"\n[14] Evaluating S001 entry conditions:")
try:
    result = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
    print(f"     Result: {result}")
    if not result:
        print(f"     → Entry signal NOT triggered")
    else:
        print(f"     → Entry signal TRIGGERED ✓")
except Exception as e:
    print(f"     ERROR: {e}")
    import traceback
    traceback.print_exc()

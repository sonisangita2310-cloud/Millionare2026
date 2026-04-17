#!/usr/bin/env python3
"""
Runtime debug: trace alignment and data keys during backtest
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
import pandas as pd

# Load data
data_engine = DataEngine()
print("[1] Loading market data...")
all_data = data_engine.get_all_data(
    symbols=['BTC/USDT'],
    timeframes=['3m', '5m', '15m', '1h', '4h']
)

if not all_data:
    print("ERROR: No data loaded")
    sys.exit(1)

print(f"[2] Data loaded for: {list(all_data.keys())}")

# Calculate indicators
print("[3] Calculating indicators...")
multi_tf_indicators = MultiTimeframeIndicators()

symbol = 'BTC/USDT'
for tf_name, df in all_data[symbol].items():
    print(f"  → {tf_name}: {len(df)} candles")
    df_with_indicators = IndicatorsEngine.calculate_all_indicators(df)
    multi_tf_indicators.add_timeframe_indicators(symbol, tf_name, df_with_indicators)

print("[4] Multi-timeframe indicators loaded")

# Load strategies
scenario_parser = ScenarioParser()
scenarios = scenario_parser.parse_scenarios()
print(f"[5] Loaded {len(scenarios)} scenarios")

# Get first strategy
s001 = [s for s in scenarios if s.scenario_id == 'S001']
if not s001:
    print("ERROR: S001 not found")
    sys.exit(1)
    
s001 = s001[0]
print(f"\n[6] S001 Entry Conditions:")
for cond in s001.get_entry_conditions():
    print(f"    {cond}")

# Now simulate what happens during backtest
runner = BacktestRunner()
runner.scenario_parser = scenario_parser
runner.indicators = multi_tf_indicators

# Get the 5m timeframe data (typical base timeframe)
base_tf = '5m'
df_base = all_data[symbol][base_tf].copy()
df_base = IndicatorsEngine.calculate_all_indicators(df_base)

print(f"\n[7] Base timeframe ({base_tf}) columns: {list(df_base.columns)[:20]}...")

# Check a single candle
idx = 250
candle = df_base.iloc[idx]
print(f"\n[8] Sample candle at index {idx}:")
print(f"    Columns present: {[col for col in candle.index if 'EMA' in col or 'RSI' in col]}")

# Prepare data_dict like backtest does
all_timeframe_data = {}
if symbol in runner.indicators.data:
    all_timeframe_data = runner.indicators.data[symbol]

data_dict = candle.to_dict()
data_dict['_symbol'] = symbol
data_dict['_all_data'] = {symbol: all_timeframe_data}  # Wrapped
data_dict['_current_time'] = candle.name

print(f"\n[9] Before alignment:")
print(f"    Keys with 'EMA_200': {[k for k in data_dict.keys() if 'EMA_200' in str(k)]}")
print(f"    '_all_data' structure: {list(data_dict.get('_all_data', {}).keys())}")
if symbol in data_dict.get('_all_data', {}):
    print(f"    Symbol sub-keys: {list(data_dict['_all_data'][symbol].keys())}")

# Apply alignment
data_dict_aligned = runner._apply_timeframe_alignment(data_dict)

print(f"\n[10] After alignment:")
print(f"     Keys with 'EMA_200': {[k for k in data_dict_aligned.keys() if 'EMA_200' in str(k)]}")
print(f"     Total new keys from alignment: {len(data_dict_aligned) - len(data_dict)}")

# Check S001 condition requirements
print(f"\n[11] S001 requires (from conditions):")
required_keys = set()
for cond in s001.get_entry_conditions():
    if 'reference' in cond:
        required_keys.add(cond['reference'])
    
for key in sorted(required_keys):
    present = key in data_dict_aligned
    value = data_dict_aligned.get(key, 'NOT FOUND')
    print(f"    {key}: {'✓' if present else '✗'} = {value if present else 'MISSING'}")

# Try evaluating conditions
print(f"\n[12] Evaluating S001 entry conditions:")
try:
    result = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
    print(f"    Result: {result}")
except Exception as e:
    print(f"    ERROR: {e}")

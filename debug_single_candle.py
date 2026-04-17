#!/usr/bin/env python3
"""
Test evaluator on ONE candle to see data flow
"""
import pandas as pd
import sys
sys.path.insert(0, '.')

from src.backtest_indicators import IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine
from src.backtest_engine import BacktestEngine

# Quick load
runner = BacktestRunner()
sp = ScenarioParser(scenarios_file='scenarios/SCENARIOS_STRUCTURED.json')
data_engine = DataEngine()
data = data_engine.get_all_data(['BTC/USDT'], ['3m', '5m', '15m', '1h', '4h'], force_real_data=False)

for symbol, timeframes_data in data.items():
    for timeframe, df in timeframes_data.items():
        if len(df) < 200:
            continue
        df_with_indicators = IndicatorsEngine.calculate_all_indicators(df)
        runner.indicators.add_timeframe_indicators(symbol, timeframe, df_with_indicators)

runner._precompute_aligned_data()
df_aligned = runner.aligned_data['BTC/USDT']

# Get S001
s001 = [s for s in sp.get_all_scenarios() if s.id == 'S001'][0]

# Test on candle 5175 (where we expect condition to be TRUE based on manual calc)
test_idx = 5175
candle = df_aligned.iloc[test_idx]

data_dict = candle.to_dict()
data_dict['_symbol'] = 'BTC/USDT'
data_dict['_current_time'] = candle.name

print(f"\nCandle {test_idx}: {candle.name}")
print(f"Data dict has {len(data_dict)} keys")
print(f"\nFirst 30 keys in data_dict:")
for i, key in enumerate(list(data_dict.keys())[:30]):
    print(f"  {key}: {data_dict[key]}")

print(f"\n\nS001 conditions:")
conditions = s001.get_entry_conditions()
for cond in conditions:
    print(f"  {cond}")

# Now try to evaluate manually
print(f"\n\nManual condition check:")
close = data_dict.get('close')
ema_200_3m = data_dict.get('EMA_200_3m')
ema_200_1h = data_dict.get('EMA_200_1h')
rsi_1h = data_dict.get('RSI_14_1h')

print(f"close: {close}")
print(f"EMA_200_3m: {ema_200_3m}")
print(f"EMA_200_1h: {ema_200_1h}")
print(f"RSI_14_1h: {rsi_1h}")

e1 = close > ema_200_3m * 1.001 if (close and ema_200_3m and not pd.isna(ema_200_3m)) else False
print(f"\ne1 [price > EMA_200_3m*1.001]: {e1}")

# Now test the evaluator
print(f"\n\nTesting evaluator:")
result = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
print(f"Evaluator result: {result}")

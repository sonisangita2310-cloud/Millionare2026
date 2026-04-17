#!/usr/bin/env python3
"""Check how many cases have price > EMA * 1.1 (the CORRECT buffer_pct)"""
import pandas as pd
import sys
sys.path.insert(0, '.')

from src.backtest_indicators import IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine

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

# COUNT WITH CORRECT BUFFER
count_10pct = 0
count_0pct = 0

for idx in range(200, len(df_aligned)):
    candle = df_aligned.iloc[idx]
    
    close = candle.get('close')
    ema_200_3m = candle.get('EMA_200_3m')
    
    if close is not None and ema_200_3m is not None and not pd.isna(ema_200_3m):
        # What the scenario ACTUALLY asks for (buffer_pct: 0.1 = 10%)
        if close > ema_200_3m * 1.1:
            count_10pct += 1
        
        # What I mistakenly checked (0.1%)
        if close > ema_200_3m * 1.001:
            count_0pct += 1

print(f"price > EMA_200_3m * 1.1  (10%, scenario):  {count_10pct} TRUE")
print(f"price > EMA_200_3m * 1.001 (0.1%, my error): {count_0pct} TRUE")
print(f"\n✅ Ah! The evaluator is CORRECT - I was checking the WRONG buffer!")
print(f"The strategy is just very strict (requires 10% above EMA)")

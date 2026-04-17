#!/usr/bin/env python3
"""FAST: Just check ALL conditions TRUE count"""
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

# COUNT ALL CONDITIONS TRUE
all_true = 0
for idx in range(200, len(df_aligned)):
    candle = df_aligned.iloc[idx]
    
    close = candle.get('close')
    ema_200_3m = candle.get('EMA_200_3m')
    ema_200_1h = candle.get('EMA_200_1h')
    rsi_1h = candle.get('RSI_14_1h')
    open_p = candle.get('open')
    high_p = candle.get('high')
    low_p = candle.get('low')
    
    # e1: price > EMA_200_3m * 1.001
    e1 = (close and ema_200_3m and not pd.isna(ema_200_3m) and 
          close > ema_200_3m * 1.001)
    
    # e2: candle_body_ratio > 0.6
    range_size = high_p - low_p if (high_p and low_p and (high_p - low_p) > 0) else 0
    body_ratio = abs(close - open_p) / range_size if range_size > 0 else 0
    e2 = body_ratio > 0.6 if (open_p and close) else False
    
    # e3: price > EMA_200_1h
    e3 = (close and ema_200_1h and not pd.isna(ema_200_1h) and 
          close > ema_200_1h)
    
    # e4: RSI_14_1h > 50
    e4 = (rsi_1h and not pd.isna(rsi_1h) and rsi_1h > 50)
    
    # e5: RSI_14_1h < 70
    e5 = (rsi_1h and not pd.isna(rsi_1h) and rsi_1h < 70)
    
    if e1 and e2 and e3 and e4 and e5:
        all_true += 1

print(f"\n✅ ALL 5 CONDITIONS TRUE (AND logic): {all_true}")
print(f"Dataset size: {len(df_aligned)}")
print(f"Percentage: {all_true/len(df_aligned)*100:.2f}%")

if all_true > 0:
    print(f"\n✅ CONDITIONS WORK - Entry signals exist")
    print(f"Expected {all_true} trades in backtest")
    print(f"❌ If backtest = 0, then it's an evaluator/backtest bug")
else:
    print(f"\n❌ NO CONDITIONS TRUE - Logic too strict OR data mismatch")

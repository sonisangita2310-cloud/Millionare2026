#!/usr/bin/env python3
"""Find a candle where ALL conditions are TRUE and test it"""
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

# Get S001
s001 = [s for s in sp.get_all_scenarios() if s.id == 'S001'][0]

# Find a candle where all conditions are TRUE
print("Searching for candle with ALL conditions TRUE...")
found_count = 0

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
        found_count += 1
        
        if found_count <= 3:  # Print first 3
            print(f"\n✅ Found at index {idx}: {candle.name}")
            print(f"  close={close:.2f}, EMA_200_3m={ema_200_3m:.2f}, RSI_1h={rsi_1h:.2f}")
            
            # Test this candle with evaluator
            data_dict = candle.to_dict()
            data_dict['_symbol'] = 'BTC/USDT'
            data_dict['_current_time'] = candle.name
            
            print(f"  Testing evaluator...")
            result = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
            print(f"  Evaluator result: {result}")
            
            if not result:
                print(f"  ❌ MISMATCH: Manual=TRUE but Evaluator=FALSE")
                
                # Try with debug enabled
                print(f"\n  Retrying with debug...")
                runner.modular_evaluator.debug = True
                result_debug = runner._evaluate_conditions_hybrid(s001, candle, data_dict)
                print(f"  With debug: {result_debug}")

print(f"\nTotal candles with ALL 5 conditions TRUE: {found_count}")

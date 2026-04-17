#!/usr/bin/env python3
"""
SURGICAL CONDITION DEBUG
- Check column existence
- Count condition TRUE evaluations
- Print sample values
- Identify NaN issues
"""
import pandas as pd
import sys
sys.path.insert(0, '.')

from src.backtest_indicators import IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine

print("\n" + "="*80)
print("CONDITION EVALUATION DEBUG - S001 ONLY")
print("="*80)

# [1] Load aligned data
print("\n[1] Loading data and pre-alignment...")
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

runner._precompute_aligned_data()  # Run pre-alignment

if 'BTC/USDT' not in runner.aligned_data:
    print("[ERROR] No aligned data for BTC/USDT")
    sys.exit(1)

df_aligned = runner.aligned_data['BTC/USDT']
print(f"✓ Loaded {len(df_aligned)} candles")

# [2] Validate columns
print("\n[2] COLUMN VALIDATION")
print(f"Total columns: {len(df_aligned.columns)}")
print(f"Columns (first 15): {list(df_aligned.columns[:15])}")

required_cols = [
    'EMA_200_3m', 'EMA_200_1h', 'RSI_14_3m', 'EMA_200', 
    'open', 'high', 'low', 'close', 'volume', 'ATR_14'
]

missing_cols = [c for c in required_cols if c not in df_aligned.columns]
if missing_cols:
    print(f"❌ MISSING COLUMNS: {missing_cols}")
else:
    print(f"✓ All required columns present")

# [3] Get S001
s001 = [s for s in sp.get_all_scenarios() if s.id == 'S001'][0]
entry_conditions = s001.get_entry_conditions()

print(f"\n[3] S001 ENTRY CONDITIONS")
print(f"Strategy: {s001.name}")
print(f"Number of conditions: {len(entry_conditions)}")
for i, cond in enumerate(entry_conditions):
    print(f"  [{i}] {cond}")

# [4] SAMPLE VALUES
print(f"\n[4] SAMPLE VALUES (first 10 candles with valid data)")
print("-" * 100)

for idx in range(200, min(210, len(df_aligned))):
    candle = df_aligned.iloc[idx]
    
    print(f"\nCandle {idx}:")
    print(f"  Time: {candle.name}")
    print(f"  Close: {candle['close']:.2f}")
    
    # Print key columns
    for col in ['EMA_200_3m', 'EMA_200_1h', 'RSI_14_3m', 'EMA_200']:
        val = candle.get(col, None)
        is_nan = pd.isna(val) if val is not None else True
        print(f"  {col}: {val} {'(NaN)' if is_nan else ''}")

# [5] CONDITION EVALUATION COUNTS
print(f"\n[5] CONDITION EVALUATION COUNTS (full dataset)")
print("-" * 100)

# Manually evaluate each condition
condition_counts = {}

# e1: price > EMA_200_3m with 0.1% buffer
price_gt_ema200_3m_count = 0
e1_conditions = []

# e2: candle_body_ratio > 0.6
candle_body_gt_06_count = 0

# e3: price_1h > EMA_200_1h
price_1h_gt_ema200_1h_count = 0

# e4: RSI_14_1h > 50
rsi_1h_gt_50_count = 0

# e5: RSI_14_1h < 70
rsi_1h_lt_70_count = 0

# Process all candles
for idx in range(200, len(df_aligned)):
    candle = df_aligned.iloc[idx]
    
    # e1: price > EMA_200_3m * 1.001
    close = candle.get('close')
    ema_200_3m = candle.get('EMA_200_3m')
    if close is not None and ema_200_3m is not None and not pd.isna(ema_200_3m):
        if close > ema_200_3m * 1.001:
            price_gt_ema200_3m_count += 1
            e1_conditions.append((idx, close, ema_200_3m))
    
    # e2: candle_body_ratio > 0.6
    open_p = candle.get('open')
    close_p = candle.get('close')
    high_p = candle.get('high')
    low_p = candle.get('low')
    
    if open_p is not None and close_p is not None and high_p is not None and low_p is not None:
        range_size = high_p - low_p
        if range_size > 0:
            body_ratio = abs(close_p - open_p) / range_size
            if body_ratio > 0.6:
                candle_body_gt_06_count += 1
    
    # e3: price_1h > EMA_200_1h
    ema_200_1h = candle.get('EMA_200_1h')
    if close is not None and ema_200_1h is not None and not pd.isna(ema_200_1h):
        if close > ema_200_1h:
            price_1h_gt_ema200_1h_count += 1
    
    # e4: RSI_14_1h > 50
    rsi_1h = candle.get('RSI_14_1h')
    if rsi_1h is not None and not pd.isna(rsi_1h):
        if rsi_1h > 50:
            rsi_1h_gt_50_count += 1
    
    # e5: RSI_14_1h < 70
    if rsi_1h is not None and not pd.isna(rsi_1h):
        if rsi_1h < 70:
            rsi_1h_lt_70_count += 1

print(f"e1 [price > EMA_200_3m * 1.001]: {price_gt_ema200_3m_count} TRUE")
print(f"e2 [candle_body_ratio > 0.6]: {candle_body_gt_06_count} TRUE")
print(f"e3 [price > EMA_200_1h]: {price_1h_gt_ema200_1h_count} TRUE")
print(f"e4 [RSI_14_1h > 50]: {rsi_1h_gt_50_count} TRUE")
print(f"e5 [RSI_14_1h < 70]: {rsi_1h_lt_70_count} TRUE")

# All 5 must be TRUE (AND logic)
all_conditions_true = 0
for idx in range(200, len(df_aligned)):
    candle = df_aligned.iloc[idx]
    
    close = candle.get('close')
    ema_200_3m = candle.get('EMA_200_3m')
    ema_200_1h = candle.get('EMA_200_1h')
    rsi_1h = candle.get('RSI_14_1h')
    open_p = candle.get('open')
    high_p = candle.get('high')
    low_p = candle.get('low')
    
    # Check all conditions
    e1 = (close and ema_200_3m and not pd.isna(ema_200_3m) and 
          close > ema_200_3m * 1.001)
    
    range_size = high_p - low_p if (high_p and low_p and low_p != 0) else 0
    body_ratio = abs(close_p - open_p) / range_size if range_size > 0 else 0
    e2 = body_ratio > 0.6 if (open_p and close_p) else False
    
    e3 = (close and ema_200_1h and not pd.isna(ema_200_1h) and 
          close > ema_200_1h)
    
    e4 = (rsi_1h and not pd.isna(rsi_1h) and rsi_1h > 50)
    e5 = (rsi_1h and not pd.isna(rsi_1h) and rsi_1h < 70)
    
    if e1 and e2 and e3 and e4 and e5:
        all_conditions_true += 1

print(f"\n🎯 ALL CONDITIONS TRUE (AND): {all_conditions_true} entries")

# [6] NaN CHECK
print(f"\n[6] NaN / NULL ANALYSIS")
print("-" * 100)

for col in ['EMA_200_3m', 'EMA_200_1h', 'RSI_14_3m', 'RSI_14_1h', 'EMA_200']:
    if col in df_aligned.columns:
        nan_count = df_aligned[col].isna().sum()
        valid_count = len(df_aligned) - nan_count
        print(f"{col:20s}: {valid_count:6d} valid, {nan_count:6d} NaN ({nan_count/len(df_aligned)*100:.1f}%)")

print("\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80 + "\n")

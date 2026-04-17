#!/usr/bin/env python3
"""
ISOLATED S001 DEBUG - Trace condition evaluation on small dataset
Goal: Determine if S001 can generate ANY conditions or if logic is broken
"""
import pandas as pd
import sys
sys.path.insert(0, '.')

from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner

print("\n" + "="*70)
print("S001 ISOLATED DEBUG - 2000 CANDLES CONDITION TRACE")
print("="*70)

# Load S001 scenario
print("\n[1] Loading S001...")
sp = ScenarioParser(scenarios_file='scenarios/SCENARIOS_STRUCTURED.json')
scenarios = sp.get_all_scenarios()
s001 = [s for s in scenarios if s.id == 'S001'][0]
print(f"    S001: {s001.name}")
print(f"    Asset pairs: {s001.asset_pairs}")
print(f"    Primary TF: {s001.timeframe_primary}")
print(f"    Required TFs: {s001.timeframes}")

# Load data - ONLY 2000 candles from 5m
print("\n[2] Loading 2000 candles (5m)...")
try:
    df_full = pd.read_csv('data_cache/BTC_USDT_5m.csv', index_col=0, parse_dates=True)
    df = df_full.iloc[-2000:].copy()  # Last 2000 only
    print(f"    Loaded {len(df)} candles | Date range: {df.index[0]} to {df.index[-1]}")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

# Add indicators
print("\n[3] Calculating indicators...")
df = IndicatorsEngine.calculate_all_indicators(df)
print(f"    Indicators added: {[c for c in df.columns if 'EMA' in c or 'RSI' in c]}")

# Load multi-timeframe data
print("\n[4] Loading all timeframes for alignment...")
multi_tf = MultiTimeframeIndicators()
symbol = 'BTC/USDT'
for tf in ['3m', '5m', '15m', '1h', '4h']:
    filepath = f'data_cache/BTC_USDT_{tf}.csv'
    try:
        df_tf = pd.read_csv(filepath, index_col=0, parse_dates=True)
        df_tf = IndicatorsEngine.calculate_all_indicators(df_tf)
        multi_tf.add_timeframe_indicators(symbol, tf, df_tf)
        print(f"    ✓ {tf}")
    except:
        print(f"    ✗ {tf} (skipped)")

# Create runner for alignment
runner = BacktestRunner()
runner.indicators = multi_tf

# Now trace conditions
print("\n" + "="*70)
print("CONDITION EVALUATION TRACE")
print("="*70)

all_timeframe_data = multi_tf.data.get(symbol, {})

# Counters
condition_hits = {
    'e1_price_ema': 0,
    'e2_candle_body': 0,
    'e3_price_1h_ema': 0,
    'e4_rsi_gt_50': 0,
    'e5_rsi_lt_70': 0,
    'ALL_CONDITIONS': 0
}

trade_count = 0
near_misses = []

print("\nEvaluating conditions across 2000 candles...")
print(f"Expected condition count: {len(df) - 200} evaluations\n")

# Loop through candles (start at 200 for warmup)
for idx in range(200, len(df)):
    candle = df.iloc[idx]
    
    # Prepare data_dict with alignment
    data_dict = candle.to_dict()
    data_dict['_symbol'] = symbol
    data_dict['_all_data'] = {symbol: all_timeframe_data}
    data_dict['_current_time'] = candle.name
    
    # Apply alignment
    data_dict_aligned = runner._apply_timeframe_alignment(data_dict)
    
    # Get entry conditions
    conditions = s001.get_entry_conditions()
    
    condition_results = {}
    for cond in conditions:
        cond_id = cond.get('id', '')
        
        # e1: price > EMA_200_3m * 1.1
        if cond_id == 'e1':
            price = data_dict_aligned.get('close', 0)
            ema = data_dict_aligned.get('EMA_200_3m', 0)
            if ema > 0 and price > ema * 1.1:
                condition_hits['e1_price_ema'] += 1
                condition_results['e1'] = True
            else:
                condition_results['e1'] = False
        
        # e2: candle body ratio > 0.6
        elif cond_id == 'e2':
            close = data_dict_aligned.get('close', 0)
            open_ = data_dict_aligned.get('open', 0)
            high = data_dict_aligned.get('high', 0)
            low = data_dict_aligned.get('low', 0)
            range_size = high - low
            if range_size > 0:
                body_ratio = abs(close - open_) / range_size
                if body_ratio > 0.6:
                    condition_hits['e2_candle_body'] += 1
                    condition_results['e2'] = True
                else:
                    condition_results['e2'] = False
            else:
                condition_results['e2'] = False
        
        # e3: price > EMA_200_1h
        elif cond_id == 'e3':
            price = data_dict_aligned.get('close', 0)
            ema_1h = data_dict_aligned.get('EMA_200_1h', 0)
            if ema_1h > 0 and price > ema_1h:
                condition_hits['e3_price_1h_ema'] += 1
                condition_results['e3'] = True
            else:
                condition_results['e3'] = False
        
        # e4: RSI_14 (1h) > 50
        elif cond_id == 'e4':
            rsi = data_dict_aligned.get('RSI_14_1h', 0)
            if rsi > 50:
                condition_hits['e4_rsi_gt_50'] += 1
                condition_results['e4'] = True
            else:
                condition_results['e4'] = False
        
        # e5: RSI_14 (1h) < 70
        elif cond_id == 'e5':
            rsi = data_dict_aligned.get('RSI_14_1h', 0)
            if rsi < 70:
                condition_hits['e5_rsi_lt_70'] += 1
                condition_results['e5'] = True
            else:
                condition_results['e5'] = False
    
    # Check if ALL are true
    if all(condition_results.values()):
        condition_hits['ALL_CONDITIONS'] += 1
        trade_count += 1
        print(f"  [TRADE SIGNAL] Candle {idx} ({candle.name}): ALL CONDITIONS TRUE ✓")
    else:
        # Track near misses (4 out of 5 true)
        true_count = sum(condition_results.values())
        if true_count == 4:
            near_misses.append({
                'idx': idx,
                'time': candle.name,
                'conditions': condition_results,
                'true_count': 4
            })

print("\n" + "="*70)
print("RESULTS SUMMARY")
print("="*70)

total_evals = len(df) - 200
print(f"\nTotal candles evaluated: {total_evals}")
print(f"\nCondition hit counts:")
for cond, count in condition_hits.items():
    pct = (count / total_evals * 100) if total_evals > 0 else 0
    print(f"  {cond:20s}: {count:5d} ({pct:5.2f}%)")

print(f"\nTotal trades triggered: {trade_count}")

if near_misses:
    print(f"\nNear misses (4/5 conditions true): {len(near_misses)}")
    for nm in near_misses[:3]:
        print(f"  {nm['time']}: {nm['conditions']}")

print("\n" + "="*70)
if trade_count > 0:
    print("✓ GOOD NEWS: S001 CAN trigger on this dataset")
    print("  → Problem is likely performance/inefficiency")
    print("  → Full run will work, just slow")
else:
    print("✗ CRITICAL: S001 generates 0 trades even on isolated test")
    print(f"  → {condition_hits['ALL_CONDITIONS']} instances of ALL conditions true")
    if near_misses:
        print(f"  → But {len(near_misses)} near-misses (4/5 true)")
        print(f"  → See which condition blocks most often:")
        condition_blocks = {}
        for nm in near_misses:
            for cond, result in nm['conditions'].items():
                if not result:
                    condition_blocks[cond] = condition_blocks.get(cond, 0) + 1
        for cond in sorted(condition_blocks, key=lambda x: condition_blocks[x], reverse=True):
            print(f"     {cond}: blocks {condition_blocks[cond]} times")

print("="*70 + "\n")

#!/usr/bin/env python
"""
SURGICAL DEBUG: Why does S002 generate 0 trades?
Extract condition counts, verify indicators, identify breakdown point
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_runner import BacktestRunner
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_data_engine import DataEngine
import pandas as pd
import json

def debug_s002():
    print("\n" + "="*100)
    print(" "*30 + "S002 SIGNAL GENERATION DEBUG")
    print("="*100)
    
    # Step 1: Load S002 scenario definition
    print("\n[STEP 1] Loading S002 scenario definition...")
    parser = ScenarioParser(scenarios_file="scenarios/SCENARIOS_STRUCTURED.json")
    s002 = parser.get_scenario("S002")
    
    if not s002:
        print("❌ S002 not found in scenarios")
        return
    
    print(f"\n📋 S002: {s002.name}")
    print(f"   Type: {s002.type}")
    print(f"   Primary timeframe: {s002.timeframe_primary}")
    print(f"   Used timeframes: {s002.timeframes}")
    
    # Step 2: Fetch real data
    print("\n[STEP 2] Fetching market data...")
    data_engine = DataEngine()
    all_required_timeframes = ['1m', '3m', '4h', '5m', '15m', '1h', 'Weekly']
    data = data_engine.get_all_data(['BTC/USDT', 'ETH/USDT'], all_required_timeframes, force_real_data=True)
    data = data_engine.sync_multiframe_data(data)
    
    print(f"✅ Fetched data for {len(data)} symbols and {sum(len(data[s]) for s in data)} timeframes")
    
    # Step 3: Calculate indicators for BTC/USDT 5m base
    print("\n[STEP 3] Calculating technical indicators...")
    from src.backtest_indicators import IndicatorsEngine
    for symbol in data:
        for timeframe in data[symbol]:
            if len(data[symbol][timeframe]) < 200:
                continue
            data[symbol][timeframe] = IndicatorsEngine.calculate_all_indicators(data[symbol][timeframe])
    
    print("✅ Indicators calculated")
    
    # Step 4: Pre-align multi-timeframe data
    print("\n[STEP 4] Pre-computing aligned multi-timeframe data...")
    runner = BacktestRunner(initial_capital=100000.0)
    runner.data_engine = data_engine
    runner.indicators = runner.IndicatorsEngine()
    
    # Manually set up aligned data
    for symbol in data:
        runner.indicators.add_symbol(symbol)
        for timeframe in data[symbol]:
            runner.indicators.add_timeframe_indicators(symbol, timeframe, data[symbol][timeframe])
    
    runner._precompute_aligned_data()
    print("✅ Multi-timeframe alignment complete")
    
    # Step 5: Get BTC/USDT aligned data
    print("\n[STEP 5] Analyzing S002 conditions on BTC/USDT...")
    
    aligned_btc = runner.aligned_data.get('BTC/USDT')
    if aligned_btc is None:
        print("❌ No aligned data for BTC/USDT")
        return
    
    print(f"\n   Data points: {len(aligned_btc):,} candles")
    print(f"   Columns: {len(aligned_btc.columns)} available")
    
    # Step 6: Extract S002 entry conditions
    print("\n[STEP 6] S002 Entry Conditions:")
    print("-" * 100)
    
    if not s002.entry.get('conditions'):
        print("❌ No entry conditions defined for S002")
        return
    
    conditions = s002.entry['conditions']
    print(f"   Total conditions: {len(conditions)}")
    print(f"   Logic: AND (all must be true)")
    
    condition_results = []
    
    for i, cond in enumerate(conditions):
        cond_id = cond.get('id', f'C{i}')
        indicator = cond.get('indicator', '?')
        comparison = cond.get('comparison', '?')
        value_ref = cond.get('value') or cond.get('reference', '?')
        timeframe = cond.get('timeframe', s002.timeframe_primary)
        
        print(f"\n   [{cond_id}] {indicator} {comparison} {value_ref} (timeframe: {timeframe})")
        
        # Try to evaluate this condition
        try:
            # Build column name based on indicator type
            if indicator.startswith('EMA'):
                parts = indicator.split('_')
                period = parts[1]
                col = f"EMA_{period}_{timeframe}"
            elif indicator.startswith('SMA'):
                parts = indicator.split('_')
                period = parts[1]
                col = f"SMA_{period}_{timeframe}"
            elif indicator.startswith('RSI'):
                parts = indicator.split('_')
                period = parts[1]
                col = f"RSI_{period}_{timeframe}"
            elif indicator.startswith('MACD'):
                col = f"MACD_line_{timeframe}"
            elif indicator == 'price':
                col = 'close'
            elif indicator == 'volume':
                col = 'volume'
            else:
                col = None
            
            if col is None or col not in aligned_btc.columns:
                print(f"       ❌ COLUMN NOT FOUND: {col}")
                print(f"          Available similar: {[c for c in aligned_btc.columns if indicator.lower() in c.lower()][:3]}")
                condition_results.append({'condition': cond_id, 'status': 'MISSING_COLUMN', 'true_count': 0})
                continue
            
            # Check data availability
            non_null = aligned_btc[col].notna().sum()
            print(f"       ✓ Column exists: {col}")
            print(f"         Data points: {non_null:,} non-null")
            
            # Evaluate condition
            if comparison == '>':
                mask = aligned_btc[col] > value_ref
            elif comparison == '<':
                mask = aligned_btc[col] < value_ref
            elif comparison == '>=':
                mask = aligned_btc[col] >= value_ref
            elif comparison == '<=':
                mask = aligned_btc[col] <= value_ref
            else:
                print(f"       ❌ UNSUPPORTED COMPARISON: {comparison}")
                mask = pd.Series(False, index=aligned_btc.index)
            
            true_count = mask.sum()
            print(f"         Condition TRUE count: {true_count:,} candles ({100*true_count/len(aligned_btc):.2f}%)")
            
            # Show sample values
            true_indices = mask[mask].index[:3]
            if len(true_indices) > 0:
                print(f"         Sample TRUE values:")
                for idx in true_indices:
                    print(f"           [{aligned_btc.index[aligned_btc.index.get_loc(idx)]}] {col}={aligned_btc.loc[idx, col]:.2f} {comparison} {value_ref}")
            else:
                print(f"         ⚠️  NO TRUE VALUES FOUND")
                # Show range of values
                print(f"         Value range: {aligned_btc[col].min():.2f} to {aligned_btc[col].max():.2f}")
            
            condition_results.append({
                'condition': cond_id,
                'status': 'OK',
                'true_count': true_count,
                'total': len(aligned_btc),
                'pct': 100 * true_count / len(aligned_btc)
            })
            
        except Exception as e:
            print(f"       ❌ ERROR: {e}")
            condition_results.append({'condition': cond_id, 'status': 'ERROR', 'error': str(e)})
    
    # Step 7: Check if ALL conditions are ever simultaneously TRUE
    print("\n" + "="*100)
    print("[STEP 7] Combination Analysis (AND logic - all must be TRUE):")
    print("="*100)
    
    # Try to get evaluator results
    try:
        from src.condition_engine import ModularConditionEvaluator
        evaluator = ModularConditionEvaluator()
        
        # Check a sample of candles
        print("\nTesting evaluator on sample candles...")
        sample_indices = aligned_btc.index[::10000]  # Every 10k candles
        
        true_count = 0
        for idx in sample_indices:
            # Prepare data_dict for evaluator
            data_dict = aligned_btc.loc[idx].to_dict()
            
            # Call evaluator
            result = evaluator.evaluate_entry_conditions(s002, data_dict)
            if result:
                true_count += 1
        
        print(f"\n✅ Evaluator TRUE count (sample of {len(sample_indices)}): {true_count}")
        
        if true_count == 0:
            print("\n🚨 CONCLUSION: Evaluator NEVER returns TRUE for S002")
            print("   Likely cause: Conditions never simultaneously met OR condition type not supported")
        else:
            print(f"\n✅ Evaluator can return TRUE, but {len(aligned_btc) - true_count} candles are FALSE")
    
    except Exception as e:
        print(f"❌ Could not test evaluator: {e}")
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY:")
    print("="*100)
    
    for r in condition_results:
        if r['status'] == 'OK':
            print(f"  {r['condition']}: {r['true_count']:>6} TRUE ({r['pct']:>5.2f}%)")
        else:
            print(f"  {r['condition']}: {r['status']}")
    
    print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    debug_s002()

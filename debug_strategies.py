# -*- coding: utf-8 -*-
"""
Debug script to understand strategy condition matching
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser, ConditionEvaluator
import pandas as pd

def main():
    try:
        print("\n" + "="*70)
        print("STRATEGY CONDITION DEBUG - CHECKING WHY FEW TRADES ARE GENERATED")
        print("="*70)
        
        # Step 1: Get data
        print("\n[1] Fetching data...")
        data_engine = DataEngine()
        data = data_engine.get_all_data(['BTC/USDT'], ['1h'], force_real_data=True)
        data = data_engine.sync_multiframe_data(data)
        print("[OK] Data fetched")
        
        # Step 2: Calculate indicators
        print("\n[2] Calculating indicators...")
        indicators = MultiTimeframeIndicators()
        for symbol, timeframes_data in data.items():
            for timeframe, df in timeframes_data.items():
                if len(df) < 200:
                    print(f"  WARNING: Insufficient data for {symbol} {timeframe}")
                    continue
                df_with_ind = IndicatorsEngine.calculate_all_indicators(df)
                indicators.add_timeframe_indicators(symbol, timeframe, df_with_ind)
        print("[OK] Indicators calculated")
        
        # Step 3: Load scenarios
        print("\n[3] Loading scenarios...")
        parser = ScenarioParser()
        scenarios = parser.get_all_scenarios()
        print(f"[OK] Loaded {len(scenarios)} scenarios")
        
        # Step 4: Test each scenario
        print(f"\n[4] Testing conditions on {len(scenarios)} scenarios...")
        print("-"*70)
        
        df = indicators.get('BTC/USDT', '1h')
        if df is None:
            print("ERROR: No data for BTC/USDT 1h")
            return
        
        print(f"DataFrame shape: {df.shape}")
        print(f"Columns: {len(df.columns)} total")
        print(f"Sample columns: {list(df.columns)[:5]}")
        print()
        
        for scenario in scenarios[:3]:  # Test first 3
            print(f"\n{scenario.id}")
            print(f"  Rules:")
            
            # Check what rules look for
            for rule in scenario.get_entry_conditions():
                print(f"    - {rule['rule']}")
            
            # Test condition evaluation
            trigger_count = 0
            test_idx = -1
            for idx in range(200, min(220, len(df))):
                candle = df.iloc[idx]
                data_dict = candle.to_dict()
                
                try:
                    result = ConditionEvaluator.evaluate_entry_conditions(scenario, candle, data_dict)
                    if result:
                        trigger_count += 1
                        if test_idx < 0:
                            test_idx = idx
                except Exception as e:
                    print(f"  ERROR: {e}")
            
            print(f"  Conditions triggered: {trigger_count}/20 candles")
            
            if test_idx >= 0:
                candle = df.iloc[test_idx]
                print(f"  Sample values at trigger:")
                test_rules = [r['rule'] for r in scenario.get_entry_conditions()]
                for rule in test_rules[:3]:
                    print(f"    {rule}")
                    # Try to extract what's being checked
                    if 'EMA_12' in rule:
                        e12 = candle.get('EMA_12', 'NOT FOUND')
                        e21 = candle.get('EMA_21', 'NOT FOUND')
                        print(f"      EMA_12={e12}, EMA_21={e21}")
    
    except Exception as e:
        import traceback
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

"""
Backtest debugging engine - trace condition evaluation
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import MultiTimeframeIndicators, IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser, ConditionEvaluator, Scenario
from collections import defaultdict

class BacktestDebugger:
    """Debug backtest execution"""
    
    def __init__(self):
        self.data_engine = DataEngine()
        self.indicators = MultiTimeframeIndicators()
        self.condition_stats = defaultdict(int)
        self.near_misses = []
    
    def run_debug(self):
        """Run debug backtest"""
        print("\n" + "="*80)
        print("BACKTEST ENGINE DEBUG")
        print("="*80)
        
        # Step 1: Fetch data
        print("\n[STEP 1] Fetching data...")
        data = self.data_engine.get_all_data(
            symbols=['BTC/USDT'],
            timeframes=['1h'],
            force_real_data=True
        )
        
        if not data:
            print("[ERROR] No data fetched")
            return
        
        print(f"[OK] Fetched data")
        
        # Step 2: Calculate indicators
        print("\n[STEP 2] Calculating indicators...")
        for symbol, timeframes_data in data.items():
            for timeframe, df in timeframes_data.items():
                if len(df) < 200:
                    print(f"[ERROR] Insufficient data: {len(df)} candles")
                    continue
                
                df_with_indicators = IndicatorsEngine.calculate_all_indicators(df)
                self.indicators.add_timeframe_indicators(symbol, timeframe, df_with_indicators)
                print(f"[OK] Indicators calculated for {symbol} {timeframe}: {len(df_with_indicators)} candles")
        
        # Step 3: Load scenarios
        print("\n[STEP 3] Loading scenarios...")
        parser = ScenarioParser()
        all_scenarios = parser.get_all_scenarios()
        print(f"[OK] Loaded {len(all_scenarios)} scenarios")
        
        # Step 4: Debug S001 (first scenario)
        print("\n[STEP 4] Debugging scenario S001...")
        scenario_df = self.indicators.get('BTC/USDT', '1h')
        if scenario_df is None:
            print("[ERROR] Could not get dataframe with indicators")
            return
        self._debug_scenario(all_scenarios[0], scenario_df)
        
        # Step 5: Test simple RSI < 30 rule
        print("\n[STEP 5] Testing simple RSI < 30 rule...")
        self._test_simple_rsi_rule(scenario_df)
    
    def _debug_scenario(self, scenario: Scenario, df: pd.DataFrame):
        """Debug a single scenario"""
        print(f"\nScenario: {scenario.id} - {scenario.name}")
        print(f"Type: {scenario.type}")
        print(f"Timeframe: {scenario.timeframe_primary}")
        
        conditions = scenario.get_entry_conditions()
        print(f"\nEntry conditions ({len(conditions)}):")
        for i, cond in enumerate(conditions):
            print(f"  Condition {i+1}:")
            for key, val in cond.items():
                print(f"    {key}: {val}")
        
        # Track statistics
        condition_triggers = [defaultdict(int) for _ in range(len(conditions))]
        all_true_count = 0
        near_miss_examples = []
        
        # Simulate through data
        print(f"\nEvaluating {len(df)} candles...")
        sample_evaluated = 0
        for idx in range(200, min(len(df), 1000)):  # Test first 800 candles
            candle = df.iloc[idx]
            
            if pd.isna(candle.get('close')):
                continue
            
            data_dict = candle.to_dict()
            results = []
            
            for cond_idx, condition in enumerate(conditions):
                try:
                    # Extract rule if it exists
                    if 'rule' in condition:
                        rule = condition.get('rule', '')
                        result = ConditionEvaluator._evaluate_rule(rule, data_dict)
                        results.append(result)
                        if result:
                            condition_triggers[cond_idx][condition.get('id', f'cond_{cond_idx}')] += 1
                        
                        # Debug first few evaluations
                        if sample_evaluated < 3:
                            print(f"[DEBUG] Candle {idx}, Condition {cond_idx}: rule='{rule}' -> {result}")
                    else:
                        # OLD format - try to evaluate
                        results.append(False)
                        if sample_evaluated < 3:
                            print(f"    [WARNING] Condition {cond_idx} uses OLD format (not 'rule'): {list(condition.keys())}")
            
                except Exception as e:
                    results.append(False)
                    if sample_evaluated < 3:
                        print(f"    [ERROR] Condition {cond_idx} evaluation failed: {e}")
            
            sample_evaluated += 1
            
            # Check if all conditions are true
            all_true = all(results) if results else False
            if all_true:
                all_true_count += 1
            
            # Near miss: 1 condition away from entry
            true_count = sum(results)
            if true_count == len(conditions) - 1:
                near_miss_examples.append({
                    'candle_idx': idx,
                    'time': df.index[idx] if hasattr(df, 'index') else idx,
                    'close': candle['close'],
                    'condition_results': results
                })
        
        # Print results
        print(f"\n[RESULTS] Condition Trigger Frequencies:")
        for cond_idx, triggers in enumerate(condition_triggers):
            print(f"\n  Condition {cond_idx}: {conditions[cond_idx].get('id', f'condition_{cond_idx}')}")
            if triggers:
                for key, count in triggers.items():
                    print(f"    - Triggered {count} times out of 800 candles")
            else:
                print(f"    - Triggered 0 times")
        
        print(f"\n[RESULTS] All conditions TRUE simultaneously: {all_true_count} times")
        
        if near_miss_examples:
            print(f"\n[RESULTS] Near-miss examples ({len(near_miss_examples[:5])} shown):")
            for example in near_miss_examples[:5]:
                print(f"  Candle {example['candle_idx']}: {example['condition_results']}")
        
        return all_true_count > 0
    
    def _test_simple_rsi_rule(self, df: pd.DataFrame):
        """Test a super-simple RSI < 30 rule"""
        print(f"\nTesting: RSI_14_1h < 30 on {len(df)} candles...")
        
        # First, check what columns exist
        print(f"\n[DEBUG] DataFrame columns ({len(df.columns)}):")
        print(f"  {list(df.columns[:20])}")  # First 20 columns
        
        # Check if RSI exists
        if 'RSI_14' in df.columns:
            rsi_col = df['RSI_14']
            print(f"\n[DEBUG] RSI_14 column found!")
            print(f"  Type: {rsi_col.dtype}")
            print(f"  Non-null count: {rsi_col.notna().sum()} / {len(df)}")
            print(f"  Sample values (indices 200-210):")
            for idx in range(200, min(210, len(df))):
                val = df.iloc[idx]['RSI_14']
                print(f"    [{idx}] RSI = {val}")
        else:
            print(f"\n[ERROR] RSI_14 column NOT FOUND in dataframe!")
        
        # Check EMA columns
        ema_cols = [col for col in df.columns if 'EMA' in col]
        print(f"\n[DEBUG] EMA columns found: {ema_cols}")
        if ema_cols:
            for col in ema_cols[:5]:  # Show first 5
                non_null = df[col].notna().sum()
                print(f"    {col}: {non_null} / {len(df)} non-null")
        
        count = 0
        examples = []
        
        for idx in range(200, len(df)):
            candle = df.iloc[idx]
            
            if 'RSI_14' in candle and not pd.isna(candle['RSI_14']):
                rsi = candle['RSI_14']
                if rsi < 30:
                    count += 1
                    if len(examples) < 5:
                        examples.append({'idx': idx, 'RSI': rsi, 'close': candle['close']})
        
        print(f"\n[RESULTS] RSI < 30 triggered {count} times")
        if examples:
            print(f"\n[EXAMPLES] First 5 triggers:")
            for ex in examples:
                print(f"  Candle {ex['idx']}: RSI={ex['RSI']:.2f}, Close={ex['close']:.2f}")
        
        if count == 0:
            print("\n[ERROR] SUPER SIMPLE RSI RULE DID NOT TRIGGER ONCE!")
            print("         This means either:")
            print("         1. Data issue (no RSI values)")
            print("         2. Condition evaluation is completely broken")
            print("         3. Data range is wrong")
        else:
            print(f"\n[OK] Simple rule works! Engine is functional.")
            return True
        
        return False


if __name__ == "__main__":
    debugger = BacktestDebugger()
    debugger.run_debug()

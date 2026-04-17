#!/usr/bin/env python3
"""
MINIMAL INTEGRATION TEST: One scenario on real walk-forward data
Adds debug output to trace data flow through the entire pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_data_engine import DataEngine
from src.backtest_runner import BacktestRunner
import pandas as pd

print("="*80)
print("MINIMAL INTEGRATION TEST - ONE SCENARIO")
print("="*80)

# Step 1: Fetch real market data
print("\n[STEP 1] Fetching market data...")
data_engine = DataEngine()
data = data_engine.get_all_data(
    symbols=['BTC/USDT'],
    timeframes=['5m', '15m', '1h']
)
print(f"  Fetched: {list(data.keys())}")
for sym in data:
    for tf in data[sym]:
        print(f"    {sym} {tf}: {len(data[sym][tf])} candles")

# Step 2: Split data
print("\n[STEP 2] Splitting data 60/40...")
train_data = {}
for symbol in data:
    train_data[symbol] = {}
    for timeframe in data[symbol]:
        df = data[symbol][timeframe]
        split_idx = int(len(df) * 0.6)
        train_data[symbol][timeframe] = df.iloc[:split_idx]
        print(f"  {symbol} {timeframe}: {len(train_data[symbol][timeframe])} train candles")

# Step 3: Run backtest
print("\n[STEP 3] Running backtest on TRAIN data with ONE scenario...")
try:
    runner = BacktestRunner(initial_capital=100000.0)
    results = runner.run_full_backtest(
        symbols=['BTC/USDT'],
        timeframes=['5m', '15m', '1h'],
        use_real_data=True,
        data=train_data
    )
    
    print("\n[RESULTS]")
    if results and 'results' in results:
        result_dict = results['results']
        print(f"  Total scenarios: {len(result_dict)}")
        
        # Show first 5 scenarios
        for idx, (scenario_id, scenario_result) in enumerate(list(result_dict.items())[:5]):
            trades = scenario_result.get('trades', 0)
            pf = scenario_result.get('profit_factor', 0)
            print(f"    {scenario_id}: {trades} trades, PF={pf:.2f}")
        
        # Count trades
        total_trades = sum(r.get('trades', 0) for r in result_dict.values())
        print(f"\n  Total trades generated: {total_trades}")
        if total_trades > 0:
            print("[SUCCESS] Trades are being generated!")
        else:
            print("[ERROR] Still 0 trades after fix!")
    else:
        print("  [ERROR] No results returned!")
        print(f"  Results structure: {results}")
        
except Exception as e:
    print(f"[EXCEPTION] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

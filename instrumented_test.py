#!/usr/bin/env python3
"""
INSTRUMENTED SINGLE-SCENARIO TEST
Run ONE scenario with full debug output
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_data_engine import DataEngine
from src.backtest_runner import BacktestRunner

print("="*80)
print("INSTRUMENTED TEST: ONE SCENARIO WITH DEBUG OUTPUT")
print("="*80)

# Fetch data
print("\n[1] Fetching market data...")
data_engine = DataEngine()
data = data_engine.get_all_data(
    symbols=['BTC/USDT'],
    timeframes=['5m', '15m', '1h']
)

# Split 60/40
print("[2] Splitting data...")
train_data = {}
for symbol in data:
    train_data[symbol] = {}
    for timeframe in data[symbol]:
        split_idx = int(len(data[symbol][timeframe]) * 0.6)
        train_data[symbol][timeframe] = data[symbol][timeframe].iloc[:split_idx]

# Run backtest with instrumentation
print("[3] Running backtest with instrumentation...\n")
runner = BacktestRunner(initial_capital=100000.0)

try:
    results = runner.run_full_backtest(
        symbols=['BTC/USDT'],
        timeframes=['5m', '15m', '1h'],
        use_real_data=True,
        data=train_data
    )
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    if results and 'results' in results:
        result_dict = results['results']
        
        # Show summary
        total_trades = sum(r.get('trades', 0) for r in result_dict.values())
        print(f"\nTotal scenarios: {len(result_dict)}")
        print(f"Total trades: {total_trades}")
        
        # Show first 5 scenarios
        print("\nFirst 5 scenarios:")
        for idx, (scenario_id, sr) in enumerate(list(result_dict.items())[:5]):
            trades = sr.get('trades', 0)
            pf = sr.get('profit_factor', 0)
            print(f"  {scenario_id}: {trades} trades, PF={pf:.2f}")
        
        if total_trades > 0:
            print("\n[SUCCESS] Trades generated!")
        else:
            print("\n[ERROR] STILL 0 TRADES - Check debug output above")
    
except Exception as e:
    print(f"\n[EXCEPTION] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

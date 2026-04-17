#!/usr/bin/env python
import json

try:
    with open('backtest_results/filtered_results.json', 'r') as f:
        data = json.load(f)
    
    print("\n" + "="*100)
    print("S001 VARIANTS BACKTEST RESULTS")
    print("="*100)
    
    print(f"\n{'Strategy':<12} | {'Trades':>7} | {'PF':>6} | {'WinRate':>8} | {'Expectancy':>10} | {'MaxDD':>6}")
    print("-" * 100)
    
    for strat_id in ['S001', 'S001_A', 'S001_B', 'S001_C', 'S001_D', 'S001_E']:
        if strat_id in data:
            m = data[strat_id]
            trades = int(m.get('total_trades', 0))
            pf = m.get('profit_factor', 0)
            wr = m.get('win_rate', 0) * 100
            exp = m.get('expectancy', 0)
            dd = m.get('max_drawdown', 0)
            
            marker = "✅" if pf >= 1.3 else ("⚠️ " if pf >= 1.0 else "❌")
            print(f"{marker} {strat_id:<10} | {trades:>7} | {pf:>6.2f} | {wr:>7.1f}% | {exp:>10.2f} | {dd:>6.3f}")
    
    print("\n" + "="*100 + "\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

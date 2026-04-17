#!/usr/bin/env python
import json

try:
    with open('backtest_results/filtered_results.json', 'r') as f:
        data = json.load(f)
    
    print("\n" + "="*90)
    print(" "*25 + "VALIDATION RESULTS SUMMARY")
    print("="*90)
    
    # Extract and sort by profit_factor
    results = []
    for strat_id, metrics in data.items():
        results.append({
            'Strategy': strat_id,
            'Trades': int(metrics.get('total_trades', 0)),
            'PF': round(metrics.get('profit_factor', 0), 2),
            'WinRate': round(metrics.get('win_rate', 0), 1),
            'Expectancy': round(metrics.get('expectancy', 0), 2),
            'MaxDD': round(metrics.get('max_drawdown', 0), 3)
        })
    
    # Sort by trades (descending) then PF
    results_sorted = sorted(results, key=lambda x: (x['Trades'], x['PF']), reverse=True)
    
    # Print header
    print(f"\n{'Strategy':<8} | {'Trades':>7} | {'PF':>6} | {'WinRate':>8} | {'Expectancy':>10} | {'MaxDD':>6}")
    print("-" * 90)
    
    # Print top 15
    for r in results_sorted[:15]:
        print(f"{r['Strategy']:<8} | {r['Trades']:>7} | {r['PF']:>6} | {r['WinRate']:>8}% | {r['Expectancy']:>10} | {r['MaxDD']:>6}")
    
    # Summary stats
    total_trades = sum(r['Trades'] for r in results)
    strategies_with_trades = len([r for r in results if r['Trades'] > 0])
    avg_pf = sum(r['PF'] for r in results if r['Trades'] > 0) / max(1, strategies_with_trades)
    
    print("\n" + "="*90)
    print(f"SUMMARY:")
    print(f"  Total strategies: {len(results)}")
    print(f"  Strategies with trades: {strategies_with_trades}")
    print(f"  Total trades (all): {total_trades}")
    print(f"  Avg PF (only w/ trades): {avg_pf:.2f}")
    print("="*90 + "\n")

except FileNotFoundError:
    print("❌ No results file found at backtest_results/filtered_results.json")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

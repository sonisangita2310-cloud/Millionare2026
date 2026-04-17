#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Read and display backtest results
"""
import json
import sys

with open('backtest_results/filtered_results.json', 'r') as f:
    data = json.load(f)

print("="*80)
print("BACKTEST RESULTS - FINAL VALIDATION (2-YEAR REAL DATA)")
print("="*80)
print(f"\nTotal strategies tested: {len(data)}\n")

# Collect results
results = []
for strategy_id, metrics in sorted(data.items()):
    if metrics['total_trades'] > 0:
        results.append(metrics)

if results:
    print(f"Strategies with trades: {len(results)}\n")
    
    # Sort by Sharpe ratio (best risk-adjusted returns)
    results_sorted = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)
    
    for i, metrics in enumerate(results_sorted, 1):
        print(f"{i}. {metrics['scenario_id']}: {metrics['scenario_name']}")
        print(f"   Trades: {metrics['total_trades']:4d} | Win Rate: {metrics['win_rate']:5.1%} | Profit Factor: {metrics['profit_factor']:5.2f}x")
        print(f"   Max DD: {metrics['max_drawdown']:6.1%} | Sharpe: {metrics['sharpe_ratio']:6.3f} | Expectancy: {metrics['expectancy']:5.2f}")
        print(f"   Net P&L: {metrics['total_pnl_pct']:7.1%} (${metrics['total_pnl']:10,.0f})")
        print()
    
    # Apply Phase 4 filters
    print("\n" + "="*80)
    print("PHASE 4 FILTER RESULTS (Win Rate >= 42%, Profit Factor >= 1.4, Max DD <= 8%)")
    print("="*80)
    
    passed = [m for m in results if 
              m['win_rate'] >= 0.42 and 
              m['profit_factor'] >= 1.4 and 
              m['max_drawdown'] <= 0.08]
    
    if passed:
        print(f"\nStrategies PASSED filters: {len(passed)}\n")
        passed_sorted = sorted(passed, key=lambda x: x['sharpe_ratio'], reverse=True)
        for i, m in enumerate(passed_sorted, 1):
            print(f"{i}. {m['scenario_id']}: {m['scenario_name']}")
            print(f"   WR: {m['win_rate']:.1%} | PF: {m['profit_factor']:.2f}x | DD: {m['max_drawdown']:.1%} | Sharpe: {m['sharpe_ratio']:.3f}")
    else:
        print("\nNo strategies passed Phase 4 filters")
        print("\nStrategies closest to passing:")
        for m in sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)[:3]:
            print(f"  {m['scenario_id']}: WR={m['win_rate']:.1%}, PF={m['profit_factor']:.2f}, DD={m['max_drawdown']:.1%}")
else:
    print("No trades generated for any strategy")

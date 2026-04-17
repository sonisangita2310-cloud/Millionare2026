#!/usr/bin/env python
"""Quick results analysis"""
import json

with open('backtest_results/filtered_results.json', 'r') as f:
    data = json.load(f)

total_trades = sum(s.get('total_trades', 0) for s in data.values())
print(f'\n✅ VALIDATION RESULTS')
print(f'Total trades across all strategies: {total_trades}')

if total_trades > 0:
    print(f'\n🎯 TOP 10 STRATEGIES BY PROFIT FACTOR:\n')
    top_10 = sorted(
        [(k, v) for k, v in data.items() if v.get('total_trades', 0) > 0],
        key=lambda x: x[1]['profit_factor'],
        reverse=True
    )[:10]
    
    for i, (strat_id, metrics) in enumerate(top_10, 1):
        print(f'{i:2d}. {strat_id:6s} | Trades: {metrics["total_trades"]:3d} | PF: {metrics["profit_factor"]:6.2f} | WR: {metrics["win_rate"]*100:5.1f}% | DD: {metrics["max_drawdown"]*100:5.1f}%')
else:
    print('\n❌ NO TRADES GENERATED - Configuration issue detected')
    print('\nFirst 5 strategies in file:')
    for strat_id, metrics in list(data.items())[:5]:
        print(f'  {strat_id}: {metrics.get("total_trades", 0)} trades')

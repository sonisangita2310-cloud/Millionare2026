#!/usr/bin/env python3
"""
Verify data keys match strategy expectations - confirm consistency
"""
import pandas as pd
from src.backtest_indicators import IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser

print('\n[DATA KEY VERIFICATION]')
print('='*60)

for tf in ['3m', '5m', '1h']:
    try:
        df = pd.read_csv(f'data_cache/BTC_USDT_{tf}.csv', index_col=0, parse_dates=True, nrows=1)
        df_with_ind = IndicatorsEngine.calculate_all_indicators(df)
        cols = sorted([c for c in df_with_ind.columns if 'EMA' in c or 'RSI' in c])
        print(f'✓ BTC {tf}: {cols}')
    except Exception as e:
        print(f'✗ BTC {tf}: {e}')

print('\n[STRATEGY EXPECTATIONS]')
print('='*60)

# Check what S001 expects
sp = ScenarioParser(scenarios_file='scenarios/SCENARIOS_STRUCTURED.json')
s001 = [s for s in sp.get_all_scenarios() if s.id == 'S001'][0]
required = set()
for cond in s001.get_entry_conditions():
    if 'reference' in cond:
        required.add(cond['reference'])
print(f'S001 requires: {sorted(required)}')

# Count strategies by required TF
print('\n[STRATEGY COVERAGE BY TIMEFRAME]')
print('='*60)
tfs_needed = {}
strat_list = {}

for s in sp.get_all_scenarios():
    refs = []
    for cond in s.get_entry_conditions():
        if 'reference' in cond:
            ref = cond['reference']
            refs.append(ref)
            # Extract TF from reference (e.g., EMA_200_3m → 3m)
            if '_' in ref:
                parts = ref.split('_')
                if len(parts) >= 2:
                    tf = parts[-1]
                    if tf in ['3m', '5m', '15m', '1h', '4h', '1m']:
                        tfs_needed[tf] = tfs_needed.get(tf, 0) + 1
                        if tf not in strat_list:
                            strat_list[tf] = []
                        strat_list[tf].append(s.id)

print(f'Strategies requiring 3m: {tfs_needed.get("3m", 0)}')
print(f'Strategies requiring 5m: {tfs_needed.get("5m", 0)}')
print(f'Strategies requiring 1h: {tfs_needed.get("1h", 0)}')
print(f'Strategies requiring 4h: {tfs_needed.get("4h", 0)}')

print('\n[VERDICT]')
print('='*60)
if tfs_needed.get('3m', 0) > 0:
    print(f'✓ BTC 3m available: {tfs_needed["3m"]} strategies can now trigger')
else:
    print('✗ No strategies require 3m')

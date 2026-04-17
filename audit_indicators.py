#!/usr/bin/env python
import json

with open('scenarios/SCENARIOS_STRUCTURED.json', 'r') as f:
    data = json.load(f)

standard_indicators = {'price', 'EMA', 'SMA', 'RSI', 'MACD', 'ATR', 'Bollinger', 'VWAP', 'volume', 'close', 'high', 'low', 'open'}
custom_patterns = {}

for scenario in data['scenarios']:
    scenario_id = scenario['id']
    entry = scenario.get('entry', {})
    conditions = entry.get('conditions', [])
    
    custom = []
    for cond in conditions:
        if 'indicator' in cond:
            indicator = str(cond.get('indicator', ''))
            # Check if it's a custom pattern
            is_standard = any(std in indicator for std in standard_indicators)
            if not is_standard:
                custom.append(indicator)
    
    if custom:
        custom_patterns[scenario_id] = list(set(custom))

print("\n" + "="*100)
print("STRATEGIES WITH CUSTOM (NON-STANDARD) INDICATORS:")
print("="*100)

for scenario_id, indicators in sorted(custom_patterns.items()):
    print(f"\n{scenario_id}:")
    for ind in indicators:
        print(f"  - {ind}")

print("\n" + "="*100)
print(f"SUMMARY: {len(custom_patterns)} strategies use custom patterns")
print(f"Standard-only: {len(data['scenarios']) - len(custom_patterns)} strategies")
print("="*100 + "\n")

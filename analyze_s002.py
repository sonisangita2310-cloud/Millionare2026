#!/usr/bin/env python
import json

with open('scenarios/SCENARIOS_STRUCTURED.json', 'r') as f:
    data = json.load(f)

# Find S002
s002 = None
for scenario in data['scenarios']:
    if scenario['id'] == 'S002':
        s002 = scenario
        break

if s002:
    print("\n" + "="*100)
    print(f"S002: {s002['name']}")
    print("="*100)
    
    print(f"\nType: {s002.get('type')}")
    print(f"Primary TF: {s002.get('timeframe_primary')}")
    print(f"Used TFs: {s002.get('timeframes')}")
    
    print("\n" + "="*100)
    print("ENTRY CONDITIONS:")
    print("="*100)
    
    entry = s002.get('entry', {})
    conditions = entry.get('conditions', [])
    
    for i, cond in enumerate(conditions, 1):
        print(f"\n[{i}] ID: {cond.get('id')}")
        
        # Determine condition type
        if 'indicator' in cond:
            ind_type = 'SIMPLE'
            indicator = cond.get('indicator')
            comparison = cond.get('comparison')
            value = cond.get('value')
            reference = cond.get('reference')
            timeframe = cond.get('timeframe', s002.get('timeframe_primary'))
            
            print(f"    Type: {ind_type}")
            print(f"    Indicator: {indicator}")
            print(f"    Comparison: {comparison}")
            print(f"    Value/Ref: {value or reference}")
            print(f"    Timeframe: {timeframe}")
        
        elif 'rule' in cond:
            print(f"    Type: RULE-BASED")
            print(f"    Rule: {cond.get('rule')}")
        
        elif 'pattern' in cond:
            print(f"    Type: PATTERN")
            print(f"    Pattern: {cond.get('pattern')}")
            print(f"    Definition: {cond.get('definition')}")
        
        else:
            print(f"    Type: UNKNOWN")
            print(f"    Condition: {cond}")
    
    print("\n" + "="*100)
    
    # Check for unsupported condition types
    unsupported = []
    for cond in conditions:
        if 'pattern' in cond:
            unsupported.append(f"{cond.get('id')}: Pattern-based condition")
        elif 'rule' in cond and 'indicator' not in cond:
            rule = cond.get('rule', '')
            if 'Engulfing' in rule or 'Doji' in rule or 'Hammer' in rule:
                unsupported.append(f"{cond.get('id')}: Candle pattern")
    
    if unsupported:
        print("\n⚠️  UNSUPPORTED CONDITIONS:")
        for item in unsupported:
            print(f"   - {item}")
    else:
        print("\n✅ All conditions appear to be simple indicator-based")

else:
    print("❌ S002 not found")

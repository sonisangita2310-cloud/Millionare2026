#!/usr/bin/env python3
import json

with open('scenarios/SCENARIOS_STRUCTURED.json') as f:
    data = json.load(f)

compatible = []
incompatible = []

for s in data['scenarios']:
    tfs_needed = set(s.get('timeframes', []))
    tfs_available = {'5m', '15m', '1h'}
    if tfs_needed.issubset(tfs_available):
        compatible.append(s['id'])
    else:
        incompatible.append((s['id'], tfs_needed))

print(f"✅ Compatible with [5m, 15m, 1h]: {len(compatible)}/{len(compatible)+len(incompatible)}")
print(f"\nCompatible: {compatible}")
print(f"\n❌ Incompatible ({len(incompatible)}):")
for sid, tfs in incompatible:
    print(f"  {sid}: needs {tfs}")

# -*- coding: utf-8 -*-
"""
DEBUG: Strategy-System Mismatch Detection
Identifies EXACTLY why no trades are being generated
"""

import sys
import os
import json
import pandas as pd
from collections import defaultdict

# Fix encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import IndicatorsEngine
from src.backtest_scenario_parser import ScenarioParser

print("\n" + "="*80)
print("STRATEGY SYSTEM DEBUG".center(80))
print("="*80)

# ============================================================================
# STEP 1: Load scenarios and identify required timeframes
# ============================================================================
print("\n[STEP 1] Loading scenarios...")
parser = ScenarioParser(scenarios_file="scenarios/SCENARIOS_STRUCTURED.json")
scenarios = parser.get_all_scenarios()

required_timeframes = set()
required_indicators_by_strategy = defaultdict(set)
required_data_by_strategy = defaultdict(dict)

for scenario in scenarios:
    required_data_by_strategy[scenario.id] = {
        'primary_tf': scenario.timeframe_primary,
        'all_tfs': scenario.timeframes,
        'assets': scenario.asset_pairs
    }
    
    for tf in scenario.timeframes:
        required_timeframes.add(tf)
    
    # Extract from entry conditions
    if hasattr(scenario, 'entry_conditions'):
        for cond in scenario.entry_conditions:
            if isinstance(cond, dict):
                for key in cond.keys():
                    if 'indicator' in key.lower() or 'reference' in key.lower():
                        required_indicators_by_strategy[scenario.id].add(str(cond.get(key, '')))

print(f"[OK] Loaded {len(scenarios)} scenarios")
print(f"\n  Required timeframes across all strategies:")
for tf in sorted(required_timeframes):
    strategies_needing_it = [s.id for s in scenarios if tf in s.timeframes]
    print(f"    {tf:8s} -> {len(strategies_needing_it):2d} strategies: {', '.join(strategies_needing_it[:5])}{'...' if len(strategies_needing_it) > 5 else ''}")

# ============================================================================
# STEP 2: Fetch available data and check coverage
# ============================================================================
print("\n[STEP 2] Fetching available data from Binance...")
data_engine = DataEngine()
available_data = data_engine.get_all_data(
    symbols=['BTC/USDT', 'ETH/USDT'],
    timeframes=['5m', '15m', '1h'],
    force_real_data=True
)

available_timeframes = set()
for symbol, tfs in available_data.items():
    for tf in tfs.keys():
        available_timeframes.add(tf)

print(f"✓ Available timeframes: {sorted(available_timeframes)}")

# ============================================================================
# STEP 3: Identify MISSING timeframes (ROOT CAUSE)
# ============================================================================
print("\n[STEP 3] TIMEFRAME COVERAGE ANALYSIS")
print("="*80)

missing_tfs = required_timeframes - available_timeframes
available_tfs = required_timeframes & available_timeframes

print(f"\n✅ AVAILABLE timeframes ({len(available_tfs)}):")
for tf in sorted(available_tfs):
    count = len([s.id for s in scenarios if tf in s.timeframes])
    print(f"    {tf:8s} → {count} strategies can use this")

print(f"\n❌ MISSING timeframes ({len(missing_tfs)}):")
for tf in sorted(missing_tfs):
    strategies_needing_it = [s.id for s in scenarios if tf in s.timeframes]
    print(f"    {tf:8s} → {len(strategies_needing_it)} strategies BLOCKED: {', '.join(strategies_needing_it)}")

# ============================================================================
# STEP 4: Classify each strategy
# ============================================================================
print("\n[STEP 4] STRATEGY CLASSIFICATION BY DATA AVAILABILITY")
print("="*80)

can_run = []
cannot_run = []

for scenario in scenarios:
    required = set(scenario.timeframes)
    available = required & available_timeframes
    missing = required - available_timeframes
    
    if len(missing) == 0:
        can_run.append(scenario)
        status = "✅ CAN RUN"
    else:
        cannot_run.append((scenario, missing))
        status = f"❌ BLOCKED (missing {missing})"
    
    print(f"  {scenario.id:6s} {scenario.name:40s} {status}")

print(f"\n  Summary: {len(can_run)}/{len(scenarios)} strategies can run ({len(can_run)*100//len(scenarios)}%)")

# ============================================================================
# STEP 5: Deep dive on S001
# ============================================================================
print("\n[STEP 5] DETAILED ANALYSIS: S001 (200 EMA Golden Cross Scalp)")
print("="*80)

s001 = scenarios[0]  # Assuming S001 is first
print(f"\nStrategy Requirements:")
print(f"  Primary timeframe: {s001.timeframe_primary}")
print(f"  All timeframes:    {s001.timeframes}")
print(f"  Assets:            {s001.asset_pairs}")

print(f"\nWhat we have for BTC/USDT:")
if 'BTC/USDT' in available_data:
    for tf, df in available_data['BTC/USDT'].items():
        print(f"  {tf:8s}: {len(df)} candles, {df.index[0]} to {df.index[-1]}")

print(f"\nWhat S001 needs:")
for tf in s001.timeframes:
    status = "✅ AVAILABLE" if tf in available_timeframes else "❌ MISSING"
    print(f"  {tf:8s}: {status}")

# ============================================================================
# STEP 6: Check indicator availability
# ============================================================================
print("\n[STEP 6] INDICATOR AVAILABILITY CHECK")
print("="*80)

# Calculate indicators for 5m data
print("\nCalculating indicators for BTC/USDT 5m...")
btc_5m = available_data['BTC/USDT']['5m']
btc_5m_with_indicators = IndicatorsEngine.calculate_all_indicators(btc_5m.copy())

available_indicators = set(btc_5m_with_indicators.columns)
print(f"✓ Calculated {len(available_indicators)} indicators")

print("\nSample indicators available:")
for ind in sorted(list(available_indicators))[:20]:
    sample_val = btc_5m_with_indicators[ind].iloc[-1]
    is_nan = pd.isna(sample_val)
    status = "❌ NaN" if is_nan else f"✅ {sample_val:.2f}"
    print(f"    {ind:20s} {status}")

print("\nRequired indicators for S001:")
s001_cond = s001.entry_conditions
for i, cond in enumerate(s001_cond):
    print(f"  Condition {i+1}: {cond}")
    if 'reference' in cond:
        ref = cond['reference']
        status = "✅ EXISTS" if ref in available_indicators else f"❌ MISSING"
        print(f"    → {ref}: {status}")

# ============================================================================
# STEP 7: Root cause analysis
# ============================================================================
print("\n[STEP 7] ROOT CAUSE ANALYSIS")
print("="*80)

print("\n🔴 PRIMARY ISSUE:")
if len(cannot_run) > 0:
    print(f"   {len(cannot_run)} strategies require timeframes we didn't fetch")
    print(f"   Example: S001 needs 3m data, but we only fetched 5m, 15m, 1h")
    print(f"\n   Missing timeframes: {sorted(missing_tfs)}")
    print(f"   This explains the 0/32 trades!")
else:
    print("   ✅ All timeframes available")

if len(cannot_run) == 0:
    print("\n🟡 SECONDARY ISSUE TO CHECK:")
    print("   If timeframes are Ok, problem is in condition evaluation:")
    print("   - Indicators not calculating correctly")
    print("   - Condition logic too strict")
    print("   - Timeframe misalignment in evaluator")

# ============================================================================
# STEP 8: Recommended fix
# ============================================================================
print("\n[STEP 8] RECOMMENDED FIX")
print("="*80)

if len(cannot_run) > 0:
    print("\n✅ SOLUTION 1: Fetch missing timeframes")
    print(f"   Update walk_forward_validator.py to fetch: {sorted(required_timeframes)}")
    print(f"\n   Change line ~102 from:")
    print(f"     timeframes=['5m', '15m', '1h']")
    print(f"   To:")
    print(f"     timeframes={sorted(list(required_timeframes))}")
    
    print("\n✅ SOLUTION 2: Symplify to available timeframes")
    print(f"   Or use only strategies that work with 5m, 15m, 1h:")
    can_run_here = [s.id for s in can_run]
    print(f"   Strategies that CAN run: {len(can_run_here)}")
    for s in can_run:
        print(f"     {s.id} ({s.name})")

print("\n" + "="*80)
print("DEBUG COMPLETE".center(80))
print("="*80 + "\n")


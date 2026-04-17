#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WALK-FORWARD VALIDATION RESULT ANALYZER
Fast extraction of real edge from validation results
"""

import pandas as pd
import json
import sys
from pathlib import Path

print("\n" + "="*80)
print("WALK-FORWARD VALIDATION RESULT ANALYZER")
print("="*80)

results_file = Path("backtest_results/walk_forward_validation.json")

if not results_file.exists():
    print("[ERROR] Results file not found. Validation may still be running.")
    sys.exit(1)

# Load results
with open(results_file) as f:
    results = json.load(f)

robust_list = results.get('robust', [])
overfit_list = results.get('overfit', [])
weak_list = results.get('weak', [])
summary = results.get('summary', [])

if not summary:
    print("[ERROR] No summary data available yet.")
    sys.exit(1)

print(f"\n[VALIDATION COMPLETE]")
print(f"  ROBUST:  {len(robust_list)} strategies")
print(f"  OVERFIT: {len(overfit_list)} strategies")
print(f"  WEAK:    {len(weak_list)} strategies")
print(f"  TOTAL:   {len(summary)} strategies tested")

# Convert to DataFrame for filtering
df = pd.DataFrame(summary)

print("\n" + "="*80)
print("STEP 1: HARD FILTER (Quality + Stability Criteria)")
print("="*80)

# Calculate win rate difference for stability check
df['wr_diff_abs'] = abs(df['train_wr'] - df['test_wr'])
df['train_exp_ok'] = df['train_expectancy'] > 0

# Hard filters (WITH STABILITY CHECKS)
filtered = df[
    (df['train_pf'] >= 1.35) &  # GUARD: Stricter PF buffer (avoid borderline 1.30)
    (df['test_pf'] >= 1.35) &   # GUARD: Stricter PF buffer (avoid borderline 1.30)
    (df['train_trades'] >= 30) &
    (df['test_trades'] >= 20) &
    (df['test_expectancy'] > 0) &
    (df['train_exp_ok']) &  # STABILITY: Both periods must be profitable
    (df['wr_diff_abs'] <= 0.10) &  # STABILITY: Win rate swing <= 10%
    (df['test_trades'] >= df['train_trades'] * 0.5) &  # STABILITY: Didn't disappear in test
    (df['classification'] == 'ROBUST')
].copy()

print(f"\nFilters applied (STRICT):")
print(f"  Train PF >= 1.35 (GUARD: buffer above bare minimum)")
print(f"  Test PF >= 1.35 (GUARD: avoid borderline passes)")
print(f"  Train trades >= 30")
print(f"  Test trades >= 20")
print(f"  Test expectancy > 0")
print(f"  Train expectancy > 0 (STABILITY)")
print(f"  Win rate stability: |train_wr - test_wr| <= 10% (STABILITY)")
print(f"  Trade distribution: test_trades >= train_trades × 0.5 (STABILITY)")
print(f"  Classification = ROBUST")
print(f"\nResult: {len(filtered)}/{len(df)} strategies passed (STRICT filters)")

if len(filtered) == 0:
    print("\n[WARNING] No strategies passed hard filter!")
    print("\nShowing closest candidates (with stability metrics):")
    candidates = df.nlargest(10, 'test_expectancy')
    print(candidates[['strategy', 'classification', 'train_pf', 'test_pf', 'test_expectancy', 'wr_diff_abs', 'train_trades', 'test_trades']].to_string(index=False))
    print("\n[NOTE] Common reasons for rejection:")
    print("  - Win rate swings > 10% (unstable)")
    print("  - Trades disappeared in test period (< 50% of training)")
    print("  - Negative expectancy in either period")
    sys.exit(0)

# STEP 2: Quality ranking
print("\n" + "="*80)
print("STEP 2: QUALITY RANKING")
print("="*80)

filtered = filtered.sort_values('test_expectancy', ascending=False)

print("\nTop candidates by test expectancy:")
top_candidates = filtered.head(15)
print(top_candidates[['strategy', 'train_pf', 'test_pf', 'train_wr', 'test_wr', 'wr_diff_abs', 'test_expectancy', 'train_trades', 'test_trades']].to_string(index=False))

# Assessment of deployment readiness
print("\n" + "="*80)
print("DEPLOYMENT READINESS ASSESSMENT")
print("="*80)

for idx, row in top_candidates.head(5).iterrows():
    strategy = row['strategy']
    train_pf = row['train_pf']
    test_pf = row['test_pf']
    wr_diff = row['wr_diff_abs']
    expectancy = row['test_expectancy']
    
    # Scoring
    pf_strength = "STRONG" if test_pf >= 1.5 else ("SOLID" if test_pf >= 1.35 else "MARGINAL")
    stability = "STABLE" if wr_diff <= 0.05 else ("ACCEPTABLE" if wr_diff <= 0.10 else "RISKY")
    edge_quality = "HIGH" if expectancy > 0.01 else ("MEDIUM" if expectancy > 0.005 else "LOW")
    
    print(f"\n  {strategy}")
    print(f"    PF Profile: {pf_strength} ({test_pf:.2f}x)")
    print(f"    Stability:  {stability} (WR swing: {wr_diff:.1%})")
    print(f"    Edge:       {edge_quality} (exp: {expectancy:.6f})")
    print(f"    ✓ DEPLOYABLE")

# STEP 3: Identify category groups
print("\n" + "="*80)
print("STEP 3: CATEGORY ANALYSIS (Avoiding Redundancy)")
print("="*80)

# Try to infer strategy type from name
def get_strategy_type(name):
    name_lower = name.lower()
    if 'ema' in name_lower or 'cross' in name_lower:
        return 'TREND'
    elif 'breakout' in name_lower or 'break' in name_lower:
        return 'BREAKOUT'
    elif 'reversal' in name_lower or 'bounce' in name_lower or 'retest' in name_lower:
        return 'REVERSAL'
    elif 'pullback' in name_lower:
        return 'PULLBACK'
    elif 'volatility' in name_lower or 'squeeze' in name_lower or 'expansion' in name_lower:
        return 'VOLATILITY'
    elif 'support' in name_lower or 'resistance' in name_lower or 'level' in name_lower:
        return 'SUPPORT_RESISTANCE'
    else:
        return 'OTHER'

filtered['type'] = filtered['strategy'].apply(get_strategy_type)

type_counts = filtered['type'].value_counts()
print(f"\nStrategy types in top candidates:")
for stype, count in type_counts.items():
    print(f"  {stype:25s}: {count}")

# STEP 4: Select best from each type (portfolio diversity)
print("\n" + "="*80)
print("STEP 4: PORTFOLIO SELECTION (Diverse Mix)")
print("="*80)

selection = []
for stype in filtered['type'].unique():
    type_group = filtered[filtered['type'] == stype].head(2)
    selection.extend(type_group['strategy'].tolist())

selection = filtered[filtered['strategy'].isin(selection)].sort_values('test_expectancy', ascending=False)

print(f"\nRecommended portfolio ({len(selection)} strategies):")
print(selection[['strategy', 'type', 'train_pf', 'test_pf', 'test_expectancy', 'test_wr']].to_string(index=False))

# STEP 5: Performance summary
print("\n" + "="*80)
print("STEP 5: PORTFOLIO METRICS")
print("="*80)

portfolio_metrics = {
    'count': len(selection),
    'avg_test_pf': selection['test_pf'].mean(),
    'min_test_pf': selection['test_pf'].min(),
    'avg_test_wr': selection['test_wr'].mean(),
    'total_test_trades': selection['test_trades'].sum(),
    'avg_test_expectancy': selection['test_expectancy'].mean(),
}

print(f"\nPortfolio Summary:")
print(f"  Strategies:          {portfolio_metrics['count']}")
print(f"  Avg Test PF:         {portfolio_metrics['avg_test_pf']:.2f}x")
print(f"  Min Test PF:         {portfolio_metrics['min_test_pf']:.2f}x")
print(f"  Avg Test Win Rate:   {portfolio_metrics['avg_test_wr']:.1f}%")
print(f"  Total Test Trades:   {int(portfolio_metrics['total_test_trades'])}")
print(f"  Avg Expectancy:      {portfolio_metrics['avg_test_expectancy']:.4f}")

# STEP 6: Export for next phase
output_file = Path("backtest_results/selected_strategies.json")
selection_data = selection[['strategy', 'type', 'train_pf', 'test_pf', 'train_wr', 'test_wr', 'test_expectancy', 'train_trades', 'test_trades']].to_dict('records')

with open(output_file, 'w') as f:
    json.dump({
        'selected_strategies': selection_data,
        'portfolio_metrics': portfolio_metrics,
        'timestamp': str(pd.Timestamp.now())
    }, f, indent=2)

print(f"\n[OK] Selected strategies exported to: {output_file}")

print("\n" + "="*80)
print("READY FOR PORTFOLIO CONSTRUCTION")
print("="*80 + "\n")

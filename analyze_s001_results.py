#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Results Analyzer & Dashboard
Quick analysis tool for backtest results
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class S001ResultsAnalyzer:
    """Analyzes S001 optimization results and provides actionable insights"""
    
    def __init__(self, results_file: Optional[str] = None):
        """
        Initialize analyzer
        
        Args:
            results_file: Path to CSV or JSON results file (auto-detect if None)
        """
        self.results_df = None
        self.results_file = results_file
        
        if results_file:
            self.load_results(results_file)
        else:
            self.auto_find_results()
    
    def auto_find_results(self):
        """Auto-find the most recent results file"""
        
        results_dir = Path("backtest_results")
        if not results_dir.exists():
            print("❌ No backtest_results directory found")
            return
        
        # Find most recent CSV
        csv_files = sorted(results_dir.glob("s001_optimization_*.csv"), reverse=True)
        if csv_files:
            latest = csv_files[0]
            print(f"✅ Found latest results: {latest.name}")
            self.load_results(str(latest))
            return
        
        print("❌ No S001 results found in backtest_results/")
    
    def load_results(self, filepath: str):
        """Load results from CSV or JSON"""
        
        if filepath.endswith('.csv'):
            self.results_df = pd.read_csv(filepath)
        elif filepath.endswith('.json'):
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Extract scenarios from JSON
            scenarios = []
            scenarios.extend(data.get('profitable', []))
            scenarios.extend(data.get('acceptable', []))
            scenarios.extend(data.get('unprofitable', []))
            
            self.results_df = pd.DataFrame(scenarios)
        
        else:
            print(f"❌ Unknown file format: {filepath}")
            return
        
        print(f"✅ Loaded {len(self.results_df)} variants")
        self.results_file = filepath
    
    def print_summary(self):
        """Print high-level summary"""
        
        if self.results_df is None:
            print("❌ No results loaded")
            return
        
        df = self.results_df
        
        print("\n" + "="*100)
        print(" "*35 + "RESULTS SUMMARY")
        print("="*100)
        
        # Count by status
        profitable = len(df[df['profit_factor'] >= 1.2])
        acceptable = len(df[(df['profit_factor'] >= 1.0) & (df['profit_factor'] < 1.2)])
        unprofitable = len(df[df['profit_factor'] < 1.0])
        
        print(f"\n📊 Status Distribution:")
        print(f"   ✅ Profitable (PF >= 1.2):       {profitable:3d} ({profitable/len(df)*100:5.1f}%)")
        print(f"   ⚠️  Acceptable (1.0 <= PF < 1.2): {acceptable:3d} ({acceptable/len(df)*100:5.1f}%)")
        print(f"   ❌ Unprofitable (PF < 1.0):      {unprofitable:3d} ({unprofitable/len(df)*100:5.1f}%)")
        
        # Statistics
        print(f"\n📈 Metrics Summary (all variants):")
        print(f"   Profit Factor:")
        print(f"      Mean: {df['profit_factor'].mean():.2f}")
        print(f"      Std:  {df['profit_factor'].std():.2f}")
        print(f"      Min:  {df['profit_factor'].min():.2f}")
        print(f"      Max:  {df['profit_factor'].max():.2f}")
        
        print(f"\n   Win Rate:")
        print(f"      Mean: {df['win_rate'].mean()*100:.1f}%")
        print(f"      Std:  {df['win_rate'].std()*100:.1f}%")
        print(f"      Min:  {df['win_rate'].min()*100:.1f}%")
        print(f"      Max:  {df['win_rate'].max()*100:.1f}%")
        
        print(f"\n   Total P&L:")
        print(f"      Mean: ${df['total_profit'].mean():+,.0f}")
        print(f"      Std:  ${df['total_profit'].std():,.0f}")
        print(f"      Min:  ${df['total_profit'].min():+,.0f}")
        print(f"      Max:  ${df['total_profit'].max():+,.0f}")
        
        print(f"\n   Average Trades per Variant: {df['total_trades'].mean():.0f}")
    
    def print_top_variants(self, top_n: int = 10):
        """Print top variants sorted by profit factor"""
        
        if self.results_df is None:
            print("❌ No results loaded")
            return
        
        df_sorted = self.results_df.sort_values('profit_factor', ascending=False)
        
        print("\n" + "="*100)
        print(f" "*30 + f"TOP {min(top_n, len(df_sorted))} VARIANTS")
        print("="*100)
        print()
        
        for idx, (_, row) in enumerate(df_sorted.head(top_n).iterrows(), 1):
            pf = row['profit_factor']
            status = row.get('status', 'UNKNOWN')
            
            # Status emoji
            if pf >= 1.2:
                emoji = "✅"
            elif pf >= 1.0:
                emoji = "⚠️ "
            else:
                emoji = "❌"
            
            print(f"{idx:2d}. {emoji} {row['variant_id']:20s}")
            print(f"     SL: {row['sl_multiplier']:5.2f}x ATR | TP: {row['tp_multiplier']:5.2f}x ATR | "
                  f"R:R: {row.get('rr_ratio', row['tp_multiplier']/row['sl_multiplier']):5.2f}x")
            print(f"     PF: {pf:5.2f} | Trades: {row['total_trades']:3d} | "
                  f"Win%: {row['win_rate']*100:5.1f}% | P&L: ${row['total_profit']:10,.0f}")
            print()
    
    def print_sl_tp_analysis(self):
        """Analyze SL/TP patterns"""
        
        if self.results_df is None:
            print("❌ No results loaded")
            return
        
        df = self.results_df
        
        print("\n" + "="*100)
        print(" "*25 + "SL/TP PARAMETER ANALYSIS")
        print("="*100)
        
        # Group by SL multiplier
        print(f"\n📊 Profit Factor by SL Multiplier:")
        print(f"(Higher SL = wider stop)")
        print()
        
        sl_groups = df.groupby('sl_multiplier')['profit_factor'].agg(['mean', 'max', 'count'])
        sl_groups = sl_groups.sort_values('mean', ascending=False)
        
        for sl_mult, row in sl_groups.iterrows():
            print(f"   SL = {sl_mult:5.2f}x ATR: Mean PF = {row['mean']:5.2f}, "
                  f"Max = {row['max']:5.2f}, Variants = {int(row['count']):3d}")
        
        print(f"\n📊 Profit Factor by TP Multiplier:")
        print(f"(Higher TP = wider target)")
        print()
        
        tp_groups = df.groupby('tp_multiplier')['profit_factor'].agg(['mean', 'max', 'count'])
        tp_groups = tp_groups.sort_values('mean', ascending=False)
        
        for tp_mult, row in tp_groups.iterrows():
            print(f"   TP = {tp_mult:5.2f}x ATR: Mean PF = {row['mean']:5.2f}, "
                  f"Max = {row['max']:5.2f}, Variants = {int(row['count']):3d}")
        
        # R:R Analysis
        if 'rr_ratio' in df.columns:
            print(f"\n📊 Profit Factor by R:R Ratio:")
            print()
            
            df_sorted = df.sort_values('rr_ratio')
            rr_groups = df_sorted.groupby(pd.cut(df_sorted['rr_ratio'], 
                                                 bins=[0, 2, 3, 4, 5, 10]))['profit_factor'].agg(['mean', 'count'])
            
            for rr_range, row in rr_groups.iterrows():
                print(f"   R:R {rr_range}: Mean PF = {row['mean']:5.2f}, "
                      f"Variants = {int(row['count']):3d}")
    
    def print_entry_analysis(self):
        """Analyze entry signal effectiveness"""
        
        if self.results_df is None:
            print("❌ No results loaded")
            return
        
        df = self.results_df
        
        print("\n" + "="*100)
        print(" "*25 + "ENTRY SIGNAL ANALYSIS")
        print("="*100)
        
        print(f"\n📊 Trade Frequency:")
        print(f"   Median trades per variant: {df['total_trades'].median():.0f}")
        print(f"   Range: {df['total_trades'].min():.0f} - {df['total_trades'].max():.0f}")
        
        if df['total_trades'].median() < 20:
            print(f"   ⚠️  WARNING: Very few trades - entry conditions may be too strict")
        elif df['total_trades'].median() > 150:
            print(f"   ⚠️  WARNING: Too many trades - entry conditions may be too loose")
        else:
            print(f"   ✅ GOOD: Trade frequency is reasonable")
        
        print(f"\n📊 Win Rate Distribution:")
        print(f"   Mean: {df['win_rate'].mean()*100:.1f}%")
        print(f"   Median: {df['win_rate'].median()*100:.1f}%")
        print(f"   Range: {df['win_rate'].min()*100:.1f}% - {df['win_rate'].max()*100:.1f}%")
        
        if df['win_rate'].mean() < 0.35:
            print(f"   ❌ PROBLEM: Win rate too low - entry logic needs improvement")
        elif df['win_rate'].mean() > 0.65:
            print(f"   ⚠️  WARNING: Win rate too high - may be overfitting")
        else:
            print(f"   ✅ GOOD: Win rates are reasonable")
        
        print(f"\n📊 Average Trade Size (Expectancy):")
        print(f"   Mean: ${df['expectancy'].mean():.2f} per trade")
        print(f"   Best: ${df['expectancy'].max():.2f} per trade")
        print(f"   Worst: ${df['expectancy'].min():.2f} per trade")
    
    def get_next_steps(self) -> str:
        """Generate actionable next steps based on results"""
        
        if self.results_df is None:
            return "❌ No results to analyze"
        
        df = self.results_df
        
        # Count profitable
        profitable_count = len(df[df['profit_factor'] >= 1.2])
        acceptable_count = len(df[(df['profit_factor'] >= 1.0) & (df['profit_factor'] < 1.2)])
        
        best_pf = df['profit_factor'].max()
        best_variant = df[df['profit_factor'] == best_pf].iloc[0]
        
        # Generate recommendations
        if profitable_count > 0:
            return f"""
✅ SUCCESS: {profitable_count} PROFITABLE VARIANTS FOUND

IMMEDIATE ACTIONS:
1. Run Walk-Forward Validation on top 3 variants
   python walk_forward_runner.py
   
2. Record configurations:
   - Best: {best_variant['variant_id']} (PF={best_pf:.2f})
   - Backtest on next 4 weeks of data
   - Verify PF > 1.0 on unseen data
   
3. Start Live Trading:
   - Position size: 0.01 BTC
   - Risk per trade: 1.5% of $100k
   - Monitor 24-48 hours before scaling

4. Consider Portfolio:
   - Find 2-3 other profitable variants
   - Ensure low correlation
   - Combine for diversification
"""
        
        elif acceptable_count > 0:
            best_acceptable = df[df['profit_factor'] < 1.2].sort_values('profit_factor', 
                                                                         ascending=False).iloc[0]
            return f"""
⚠️  PARTIAL SUCCESS: {acceptable_count} ACCEPTABLE VARIANTS (PF={best_acceptable['profit_factor']:.2f})

OPTIMIZATION REQUIRED:
1. Grid Expansion Testing:
   python expand_s001_variants.py
   python optimize_s001_comprehensive.py --scenarios scenarios/S001_GRID_EXPANSION.json
   
2. If still no PF >= 1.2:
   Test Focused Expansions on best parameters:
   - SL around {best_acceptable['sl_multiplier']:.1f}x ATR
   - TP around {best_acceptable['tp_multiplier']:.1f}x ATR
   
3. Review Entry Logic:
   - Are we missing high-probability setups?
   - Should we add volatility filter?
   - Should we require RSI closer to oversold (< 45)?

4. Consider Alternative:
   - Test alternative strategies (we have 31 others)
   - Combine multiple weak signals
"""
        
        else:
            return f"""
❌ NO PROFITABLE VARIANTS FOUND (Best PF={best_pf:.2f})

CRITICAL REVIEW:
1. Entry Signal Analysis:
   - Trade count: {df['total_trades'].mean():.0f} (expecting 50-100)
   - Win rate: {df['win_rate'].mean()*100:.1f}% (expecting 40-55%)
   
2. Diagnosis:
   If too few trades: Entry conditions too strict
   If too many trades: Entry conditions too loose
   If low win rate: Entry catching bad moves
   
3. Actions:
   - Review entry condition specifications
   - Test entry logic in isolation
   - Consider adding secondary confirmation
   - Test on ETH/USDT to verify across assets
   
4. Fallback:
   - Review alternative strategies (S002, S003, etc)
   - Consider combining multiple weak signals
   - Explore different entry indicators (MACD, etc)
"""
    
    def print_recommendations(self):
        """Print actionable recommendations"""
        
        print("\n" + "="*100)
        print(" "*28 + "RECOMMENDATIONS & NEXT STEPS")
        print("="*100)
        print(self.get_next_steps())
    
    def export_summary(self, output_file: str = None):
        """Export analysis summary to markdown file"""
        
        if self.results_df is None:
            print("❌ No results to export")
            return
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"backtest_results/S001_ANALYSIS_{timestamp}.md"
        
        df = self.results_df
        
        with open(output_file, 'w') as f:
            f.write("# S001 Results Analysis\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            # Summary
            profitable = len(df[df['profit_factor'] >= 1.2])
            acceptable = len(df[(df['profit_factor'] >= 1.0) & (df['profit_factor'] < 1.2)])
            unprofitable = len(df[df['profit_factor'] < 1.0])
            
            f.write("## Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Profitable (PF >= 1.2) | {profitable} |\n")
            f.write(f"| Acceptable (1.0 <= PF < 1.2) | {acceptable} |\n")
            f.write(f"| Unprofitable (PF < 1.0) | {unprofitable} |\n")
            f.write(f"| Mean Profit Factor | {df['profit_factor'].mean():.2f} |\n")
            f.write(f"| Mean Win Rate | {df['win_rate'].mean()*100:.1f}% |\n")
            f.write(f"| Mean P&L | ${df['total_profit'].mean():,.0f} |\n\n")
            
            # Top variants
            f.write("## Top 10 Variants\n\n")
            df_sorted = df.sort_values('profit_factor', ascending=False)
            for idx, (_, row) in enumerate(df_sorted.head(10).iterrows(), 1):
                f.write(f"{idx}. **{row['variant_id']}** - PF: {row['profit_factor']:.2f}\n")
                f.write(f"   - SL: {row['sl_multiplier']}x | TP: {row['tp_multiplier']}x | ")
                f.write(f"Trades: {row['total_trades']} | Win%: {row['win_rate']*100:.1f}%\n\n")
            
            # Analysis
            f.write("## Analysis\n\n")
            f.write(self.get_next_steps())
            f.write("\n\n## Full Results Table\n\n")
            f.write(df_sorted.to_markdown())
        
        print(f"✅ Analysis exported to: {output_file}")


def main():
    print("\n" + "="*100)
    print(" "*25 + "S001 RESULTS ANALYZER & DASHBOARD")
    print("="*100)
    
    # Initialize analyzer
    analyzer = S001ResultsAnalyzer()
    
    if analyzer.results_df is None:
        print("\n❌ No results file found or loaded")
        print("Run: python optimize_s001_comprehensive.py")
        sys.exit(1)
    
    # Print analysis
    analyzer.print_summary()
    analyzer.print_top_variants(top_n=10)
    analyzer.print_sl_tp_analysis()
    analyzer.print_entry_analysis()
    analyzer.print_recommendations()
    
    # Export
    analyzer.export_summary()
    
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    main()

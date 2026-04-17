#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Variants Optimization Runner
Tests all SL/TP combinations to find configurations with PF >= 1.2
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_runner import BacktestRunner


class S001OptimizationRunner:
    """Runs all S001 variants and identifies profitable configurations"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.runner = BacktestRunner(initial_capital)
        self.results_summary = []
        self.variants_file = "scenarios/S001_RR_OPTIMIZATION.json"
        
    def load_scenarios(self) -> List[Dict]:
        """Load S001 variants from configuration file"""
        with open(self.variants_file, 'r') as f:
            config = json.load(f)
        return config.get('scenarios', [])
    
    def run_optimization(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict:
        """Run backtest for all S001 variants and analyze results"""
        
        if symbols is None:
            symbols = ['BTC/USDT']
        if timeframes is None:
            timeframes = ['3m', '1h', '4h', '1d']
        
        scenarios = self.load_scenarios()
        
        print("\n" + "="*100)
        print(" "*25 + "S001 VARIANTS OPTIMIZATION")
        print(" "*15 + "Testing SL/TP combinations to achieve PF >= 1.2")
        print("="*100)
        print(f"\n📊 Configuration:")
        print(f"   • Initial Capital: ${self.initial_capital:,.0f}")
        print(f"   • Total Variants: {len(scenarios)}")
        print(f"   • Symbols: {', '.join(symbols)}")
        print(f"   • Timeframes: {', '.join(timeframes)}")
        print(f"   • Goal: Profit Factor >= 1.2")
        
        # Process each variant
        for i, scenario in enumerate(scenarios, 1):
            variant_id = scenario.get('id', f'Variant_{i}')
            sl_mult = scenario.get('sl_multiplier', 'N/A')
            tp_mult = scenario.get('tp_multiplier', 'N/A')
            
            print(f"\n{'─'*100}")
            print(f"[{i}/{len(scenarios)}] Testing {variant_id}")
            print(f"     SL Multiplier: {sl_mult}x ATR | TP Multiplier: {tp_mult}x ATR")
            print(f"     Expected R:R: {tp_mult / sl_mult if isinstance(sl_mult, (int, float)) and isinstance(tp_mult, (int, float)) else 'N/A'}")
            
            try:
                # Create temporary scenarios file with single variant for testing
                temp_config = {
                    "metadata": {
                        "total_scenarios": 1,
                        "version": "3.0",
                        "phase": "Single Variant Test"
                    },
                    "scenarios": [scenario]
                }
                
                temp_file = f"scenarios/temp_variant_{variant_id}.json"
                with open(temp_file, 'w') as f:
                    json.dump(temp_config, f, indent=2)
                
                # Run backtest for this variant
                results = self.runner.run_full_backtest(
                    symbols=symbols,
                    timeframes=timeframes,
                    scenarios_file=temp_file,
                    use_real_data=True
                )
                
                # Extract metrics for this variant
                metrics = self._extract_metrics(results, variant_id, sl_mult, tp_mult)
                self.results_summary.append(metrics)
                
                # Display variant results
                self._display_variant_results(metrics)
                
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"     ❌ Error: {str(e)}")
                self.results_summary.append({
                    'variant_id': variant_id,
                    'sl_multiplier': sl_mult,
                    'tp_multiplier': tp_mult,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_profit': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'status': 'ERROR'
                })
        
        # Analyze and report
        return self._analyze_results()
    
    def _extract_metrics(self, results: Dict, variant_id: str, sl_mult: float, tp_mult: float) -> Dict:
        """Extract key metrics from backtest results"""
        
        # Get all trades from results
        all_trades = []
        for symbol, symbol_results in results.items():
            if isinstance(symbol_results, dict) and 'trades' in symbol_results:
                all_trades.extend(symbol_results['trades'])
        
        if not all_trades:
            return {
                'variant_id': variant_id,
                'sl_multiplier': sl_mult,
                'tp_multiplier': tp_mult,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_profit': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'status': 'NO_TRADES'
            }
        
        # Calculate metrics
        df_trades = pd.DataFrame(all_trades)
        
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_wins = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        total_losses = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        total_profit = df_trades['pnl'].sum()
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Determine status
        status = 'PROFITABLE' if profit_factor >= 1.2 else 'ACCEPTABLE' if profit_factor >= 1.0 else 'UNPROFITABLE'
        
        return {
            'variant_id': variant_id,
            'sl_multiplier': sl_mult,
            'tp_multiplier': tp_mult,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'status': status
        }
    
    def _display_variant_results(self, metrics: Dict):
        """Display results for a single variant"""
        
        pf = metrics['profit_factor']
        status = metrics['status']
        
        # Status emoji
        if status == 'PROFITABLE':
            emoji = "✅"
        elif status == 'ACCEPTABLE':
            emoji = "⚠️ "
        else:
            emoji = "❌"
        
        print(f"     {emoji} Profit Factor: {pf:.2f} ({status})")
        print(f"        • Total Trades: {metrics['total_trades']}")
        print(f"        • Win Rate: {metrics['win_rate']*100:.1f}% ({metrics['winning_trades']}W / {metrics['losing_trades']}L)")
        print(f"        • Total P&L: ${metrics['total_profit']:,.2f}")
        print(f"        • Avg Win: ${metrics['avg_win']:.2f} | Avg Loss: ${metrics['avg_loss']:.2f}")
    
    def _analyze_results(self) -> Dict:
        """Analyze all results and identify top performers"""
        
        df = pd.DataFrame(self.results_summary)
        
        # Sort by profit factor descending
        df_sorted = df.sort_values('profit_factor', ascending=False)
        
        print("\n" + "="*100)
        print(" "*30 + "COMPREHENSIVE RESULTS")
        print("="*100)
        
        # Display all results in table format
        print("\n📊 All Variants Ranked by Profit Factor:\n")
        
        display_df = df_sorted[[
            'variant_id', 'sl_multiplier', 'tp_multiplier', 'total_trades',
            'win_rate', 'profit_factor', 'total_profit', 'status'
        ]].copy()
        
        display_df.columns = [
            'Variant', 'SL x', 'TP x', 'Trades',
            'Win %', 'PF', 'Profit', 'Status'
        ]
        
        # Format display
        for col in ['Win %', 'PF']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x*100:.1f}%" if col == 'Win %' else f"{x:.2f}")
        
        display_df['Profit'] = display_df['Profit'].apply(lambda x: f"${float(x):,.0f}")
        
        print(display_df.to_string(index=False))
        
        # Identify profitable variants (PF >= 1.2)
        profitable = df_sorted[df_sorted['profit_factor'] >= 1.2]
        acceptable = df_sorted[(df_sorted['profit_factor'] >= 1.0) & (df_sorted['profit_factor'] < 1.2)]
        unprofitable = df_sorted[df_sorted['profit_factor'] < 1.0]
        
        print("\n" + "="*100)
        print(" "*28 + "OPTIMIZATION SUMMARY & RECOMMENDATIONS")
        print("="*100)
        
        print(f"\n📈 Classification:")
        print(f"   ✅ PROFITABLE (PF >= 1.2):   {len(profitable):2d} variants")
        print(f"   ⚠️  ACCEPTABLE (1.0 <= PF < 1.2): {len(acceptable):2d} variants")
        print(f"   ❌ UNPROFITABLE (PF < 1.0):  {len(unprofitable):2d} variants")
        
        if len(profitable) > 0:
            print(f"\n🎯 Top Profitable Variants:")
            for idx, (_, row) in enumerate(profitable.head(3).iterrows(), 1):
                print(f"   {idx}. {row['variant_id']}")
                print(f"      → SL: {row['sl_multiplier']}x ATR | TP: {row['tp_multiplier']}x ATR")
                print(f"      → PF: {row['profit_factor']:.2f} | Win Rate: {row['win_rate']*100:.1f}%")
                print(f"      → Total P&L: ${row['total_profit']:,.2f} | Trades: {row['total_trades']}")
        else:
            print(f"\n⚠️  No variants achieved PF >= 1.2")
            if len(acceptable) > 0:
                print(f"   Recommendation: Tune entry conditions or expand SL/TP range")
                print(f"   Best current: {acceptable.iloc[0]['variant_id']} (PF: {acceptable.iloc[0]['profit_factor']:.2f})")
        
        # Save detailed results
        self._save_results(df_sorted, profitable, acceptable, unprofitable)
        
        return {
            'total_variants': len(df),
            'profitable': len(profitable),
            'acceptable': len(acceptable),
            'unprofitable': len(unprofitable),
            'top_variant': profitable.iloc[0] if len(profitable) > 0 else acceptable.iloc[0] if len(acceptable) > 0 else df_sorted.iloc[0],
            'results_dataframe': df_sorted
        }
    
    def _save_results(self, df_all: pd.DataFrame, df_profitable: pd.DataFrame, 
                     df_acceptable: pd.DataFrame, df_unprofitable: pd.DataFrame):
        """Save detailed results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save CSV
        csv_file = f"backtest_results/s001_optimization_{timestamp}.csv"
        df_all.to_csv(csv_file, index=False)
        print(f"\n📁 Results saved to: {csv_file}")
        
        # Save JSON
        json_file = f"backtest_results/s001_optimization_{timestamp}.json"
        results_dict = {
            'timestamp': datetime.now().isoformat(),
            'profitable': df_profitable.to_dict(orient='records'),
            'acceptable': df_acceptable.to_dict(orient='records'),
            'unprofitable': df_unprofitable.to_dict(orient='records'),
            'summary': {
                'total_variants': len(df_all),
                'profitable_count': len(df_profitable),
                'acceptable_count': len(df_acceptable),
                'unprofitable_count': len(df_unprofitable)
            }
        }
        
        with open(json_file, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        print(f"📁 Detailed JSON: {json_file}")
        
        print("\n" + "="*100 + "\n")


def main():
    try:
        optimizer = S001OptimizationRunner(initial_capital=100000.0)
        results = optimizer.run_optimization(
            symbols=['BTC/USDT'],
            timeframes=['3m', '1h', '4h', '1d']
        )
        
        if results['profitable'] > 0:
            print(f"\n✅ SUCCESS: Found {results['profitable']} profitable variant(s)")
            sys.exit(0)
        else:
            print(f"\n⚠️  No profitable variants found - requires parameter tuning")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ OPTIMIZATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Variants Comprehensive Optimizer
Uses existing BacktestRunner with focused testing on 8 S001 variants
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_runner import BacktestRunner


class S001ComprehensiveOptimizer:
    """Tests all 8 S001 variants to find profitable configurations"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.variants_file = "scenarios/S001_RR_OPTIMIZATION.json"
        self.results_summary = []
        
    def load_s001_variants(self) -> List[Dict]:
        """Load S001 variants from configuration file"""
        with open(self.variants_file, 'r') as f:
            config = json.load(f)
        return config.get('scenarios', [])
    
    def run_comprehensive_optimization(self) -> Dict:
        """Run comprehensive testing of all S001 variants"""
        
        print("\n" + "="*100)
        print(" "*20 + "S001 VARIANTS COMPREHENSIVE OPTIMIZATION")
        print(" "*15 + "Testing 8 SL/TP combinations to achieve PF >= 1.2")
        print("="*100)
        
        scenarios = self.load_s001_variants()
        
        print(f"\n📊 Configuration:")
        print(f"   • Initial Capital: ${self.initial_capital:,.0f}")
        print(f"   • Total Variants: {len(scenarios)}")
        print(f"   • Symbol: BTC/USDT")
        print(f"   • Approach: Full backtest with institutional engine")
        print(f"   • Goal: PF >= 1.2")
        
        # Process each variant
        for i, scenario in enumerate(scenarios, 1):
            variant_id = scenario.get('id', f'Variant_{i}')
            sl_mult = scenario.get('sl_multiplier', 'N/A')
            tp_mult = scenario.get('tp_multiplier', 'N/A')
            
            rr = tp_mult / sl_mult if isinstance(sl_mult, (int, float)) and isinstance(tp_mult, (int, float)) else 'N/A'
            
            print(f"\n{'─'*100}")
            print(f"[{i}/{len(scenarios)}] {variant_id}")
            print(f"     SL: {sl_mult}x ATR | TP: {tp_mult}x ATR | R:R: {rr}")
            print(f"     ⏳ Running backtest...")
            
            try:
                # Test this variant
                metrics = self._test_variant(scenario, variant_id, sl_mult, tp_mult)
                self.results_summary.append(metrics)
                
                # Display results
                pf = metrics['profit_factor']
                status = metrics['status']
                emoji = "✅" if status == 'PROFITABLE' else "⚠️ " if status == 'ACCEPTABLE' else "❌"
                
                print(f"     {emoji} PF: {pf:.2f} | Trades: {metrics['total_trades']} | "
                      f"Win%: {metrics['win_rate']*100:.1f}% | P&L: ${metrics['total_profit']:,.0f}")
                
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
                    'expectancy': 0,
                    'rr_ratio': rr,
                    'status': 'ERROR'
                })
        
        # Analyze and report
        return self._analyze_results()
    
    def _test_variant(self, scenario: Dict, variant_id: str, sl_mult: float, tp_mult: float) -> Dict:
        """Test a single variant using BacktestRunner"""
        
        # Create temp config with just this scenario
        temp_config = {
            "metadata": {
                "total_scenarios": 1,
                "version": "3.0",
                "phase": "Single Variant Test"
            },
            "scenarios": [scenario]
        }
        
        temp_file = f"scenarios/temp_{variant_id}.json"
        with open(temp_file, 'w') as f:
            json.dump(temp_config, f, indent=2)
        
        try:
            # Run backtest
            runner = BacktestRunner(self.initial_capital)
            results = runner.run_full_backtest(
                symbols=['BTC/USDT'],
                timeframes=['3m', '1h', '4h'],
                scenarios_file=temp_file,
                use_real_data=True
            )
            
            # Extract metrics
            all_trades = []
            for symbol_key, symbol_res in results.items():
                if isinstance(symbol_res, dict) and 'trades' in symbol_res:
                    all_trades.extend(symbol_res['trades'])
            
            metrics = self._calculate_metrics(variant_id, sl_mult, tp_mult, all_trades)
            
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        return metrics
    
    def _calculate_metrics(self, variant_id: str, sl_mult: float, tp_mult: float, 
                          trades: List[Dict]) -> Dict:
        """Calculate backtest metrics from trades"""
        
        rr = tp_mult / sl_mult if sl_mult > 0 else 0
        
        if not trades:
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
                'expectancy': 0,
                'rr_ratio': rr,
                'status': 'NO_TRADES'
            }
        
        df_trades = pd.DataFrame(trades)
        
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_wins = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        total_losses = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else (1.0 if total_wins > 0 else 0)
        
        total_profit = df_trades['pnl'].sum()
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Expectancy = (Win% * Avg Win) + (Loss% * Avg Loss)
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # Status
        if profit_factor >= 1.2:
            status = 'PROFITABLE'
        elif profit_factor >= 1.0:
            status = 'ACCEPTABLE'
        else:
            status = 'UNPROFITABLE'
        
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
            'expectancy': expectancy,
            'rr_ratio': rr,
            'status': status
        }
    
    def _analyze_results(self) -> Dict:
        """Analyze and report comprehensive results"""
        
        if not self.results_summary:
            print("❌ No results to analyze")
            return {}
        
        df = pd.DataFrame(self.results_summary)
        df_sorted = df.sort_values('profit_factor', ascending=False)
        
        profitable = df_sorted[df_sorted['profit_factor'] >= 1.2]
        acceptable = df_sorted[(df_sorted['profit_factor'] >= 1.0) & (df_sorted['profit_factor'] < 1.2)]
        unprofitable = df_sorted[df_sorted['profit_factor'] < 1.0]
        
        print("\n" + "="*100)
        print(" "*25 + "COMPREHENSIVE RESULTS ANALYSIS")
        print("="*100)
        
        print(f"\n📊 Classification:")
        print(f"   ✅ PROFITABLE (PF >= 1.2):       {len(profitable):2d} variants")
        print(f"   ⚠️  ACCEPTABLE (1.0 <= PF < 1.2): {len(acceptable):2d} variants")
        print(f"   ❌ UNPROFITABLE (PF < 1.0):      {len(unprofitable):2d} variants")
        
        print(f"\n📈 All Results (ranked by Profit Factor):\n")
        
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            emoji = "✅" if row['status'] == 'PROFITABLE' else "⚠️ " if row['status'] == 'ACCEPTABLE' else "❌"
            print(f"{idx}. {emoji} {row['variant_id']:15s}")
            print(f"    ├─ PF: {row['profit_factor']:5.2f} | R:R: {row['rr_ratio']:5.2f}x | "
                  f"Trades: {row['total_trades']:3d} | Win%: {row['win_rate']*100:5.1f}%")
            print(f"    ├─ P&L: ${row['total_profit']:10,.0f} | Avg Win: ${row['avg_win']:8.2f} | "
                  f"Avg Loss: ${row['avg_loss']:8.2f}")
            print(f"    └─ Expectancy: ${row['expectancy']:8.2f}/trade")
            print()
        
        # Recommendations
        print("="*100)
        print(" "*28 + "RECOMMENDATIONS & NEXT STEPS")
        print("="*100)
        
        if len(profitable) > 0:
            print(f"\n✅ SUCCESS: {len(profitable)} PROFITABLE VARIANT(S) FOUND\n")
            
            for idx, (_, row) in enumerate(profitable.iterrows(), 1):
                print(f"TOP {idx}: {row['variant_id']}")
                print(f"   ├─ Profit Factor: {row['profit_factor']:.2f}")
                print(f"   ├─ SL Multiplier: {row['sl_multiplier']}x ATR")
                print(f"   ├─ TP Multiplier: {row['tp_multiplier']}x ATR")
                print(f"   ├─ R:R Ratio: {row['rr_ratio']:.2f}x")
                print(f"   ├─ Win Rate: {row['win_rate']*100:.1f}%")
                print(f"   ├─ Total Trades: {row['total_trades']}")
                print(f"   ├─ Total P&L: ${row['total_profit']:,.0f}")
                print(f"   └─ Expectancy/Trade: ${row['expectancy']:.2f}")
                print()
            
            print(f"📋 NEXT STEPS:")
            print(f"   1. ✅ Deploy top profitable variant in live trading")
            print(f"   2. ✅ Use walk-forward validation to reduce overfitting")
            print(f"   3. ✅ Start with 0.01 BTC position size ($500-600 at current prices)")
            print(f"   4. ✅ Monitor for 24-48 hours before scaling up")
            print(f"   5. ✅ Build portfolio by combining multiple profitable variants")
            
        elif len(acceptable) > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {len(acceptable)} ACCEPTABLE VARIANT(S) (PF 1.0-1.2)\n")
            
            best = acceptable.iloc[0]
            print(f"BEST CANDIDATE: {best['variant_id']}")
            print(f"   ├─ Profit Factor: {best['profit_factor']:.2f} (below 1.2 target)")
            print(f"   ├─ SL Multiplier: {best['sl_multiplier']}x ATR")
            print(f"   ├─ TP Multiplier: {best['tp_multiplier']}x ATR")
            print(f"   └─ Status: Viable with cautious position sizing\n")
            
            print(f"📋 OPTIMIZATION NEEDED:")
            print(f"   1. Expand SL/TP testing range around current best")
            print(f"   2. Fine-tune entry conditions (RSI thresholds, EMA periods)")
            print(f"   3. Consider combining with entry filter (volatility, momentum)")
            print(f"   4. Test on different market regimes (bull/bear/range)")
            print(f"   5. Implement position sizing optimization")
            
        else:
            print(f"\n❌ NO PROFITABLE VARIANTS FOUND\n")
            
            best = df_sorted.iloc[0]
            print(f"BEST CURRENT: {best['variant_id']}")
            print(f"   ├─ Profit Factor: {best['profit_factor']:.2f}")
            print(f"   ├─ Win Rate: {best['win_rate']*100:.1f}%")
            print(f"   └─ Total P&L: ${best['total_profit']:,.0f}\n")
            
            print(f"📋 REQUIRED ACTIONS:")
            print(f"   1. ❌ S001 entry logic may be too weak")
            print(f"   2. ❌ Expand SL/TP range testing (wider and tighter)")
            print(f"   3. ❌ Review entry condition filters")
            print(f"   4. ❌ Test on alternative symbols (ETH/USDT)")
            print(f"   5. ❌ Consider alternative strategies if no improvement")
        
        # Save detailed results
        self._save_results(df_sorted, profitable, acceptable, unprofitable)
        
        return {
            'total_variants': len(df),
            'profitable_count': len(profitable),
            'acceptable_count': len(acceptable),
            'unprofitable_count': len(unprofitable),
            'results': df_sorted
        }
    
    def _save_results(self, df_all: pd.DataFrame, df_profitable: pd.DataFrame,
                     df_acceptable: pd.DataFrame, df_unprofitable: pd.DataFrame):
        """Save detailed results to files"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV file
        csv_file = f"backtest_results/s001_optimization_{timestamp}.csv"
        df_all.to_csv(csv_file, index=False)
        
        # JSON file
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
        
        # Markdown report
        md_file = f"backtest_results/s001_optimization_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write("# S001 Variants Optimization Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"## Summary\n")
            f.write(f"- Total Variants: {len(df_all)}\n")
            f.write(f"- Profitable (PF >= 1.2): {len(df_profitable)}\n")
            f.write(f"- Acceptable (PF 1.0-1.2): {len(df_acceptable)}\n")
            f.write(f"- Unprofitable (PF < 1.0): {len(df_unprofitable)}\n\n")
            f.write(f"## Results\n\n")
            f.write(df_all.to_markdown())
        
        print(f"\n📁 Results saved to:")
        print(f"   • {csv_file}")
        print(f"   • {json_file}")
        print(f"   • {md_file}")
        print(f"\n" + "="*100 + "\n")


def main():
    try:
        optimizer = S001ComprehensiveOptimizer(initial_capital=100000.0)
        results = optimizer.run_comprehensive_optimization()
        
        if results.get('profitable_count', 0) > 0:
            print(f"✅ SUCCESS: Optimization complete with {results['profitable_count']} profitable variant(s)")
        else:
            print(f"⚠️  Optimization complete - review results and requirements for tuning")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

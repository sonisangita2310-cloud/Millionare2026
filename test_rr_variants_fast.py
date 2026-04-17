#!/usr/bin/env python
"""
Fast R:R Variant Backtest
Tests 5 strategies: S001_E baseline + 4 R:R optimizations
BTC only, minimal timeframes for speed
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_runner import BacktestRunner
from pathlib import Path
import json
import datetime

if __name__ == "__main__":
    print("\n" + "="*100)
    print(" "*20 + "S001 RISK/REWARD OPTIMIZATION - FAST TEST")
    print("="*100)
    print("\nTesting: S001_E baseline + 4 R:R variants (S001_RR1-4)")
    print("Pair: BTC/USDT only | Timeframes: 3m, 1h | Capital: $100,000\n")
    
    try:
        runner = BacktestRunner(initial_capital=100000.0)
        
        # Test ONLY S001_E and 4 R:R variants on BTC
        results = runner.run_full_backtest(
            symbols=['BTC/USDT'],  # BTC only for speed
            timeframes=['3m', '1h'],  # Minimal timeframes
            use_real_data=True,
            scenarios_file="scenarios/S001_VARIANTS.json"
        )
        
        if results and 'results' in results:
            print("\n" + "="*100)
            print("✅ BACKTEST COMPLETE")
            print("="*100 + "\n")
            
            # Filter to just S001_E and S001_RR variants
            strategies = {k: v for k, v in results['results'].items() 
                         if k in ['S001_E', 'S001_RR1', 'S001_RR2', 'S001_RR3', 'S001_RR4']}
            
            # Sort by PF descending
            strategies_sorted = sorted(
                strategies.items(),
                key=lambda x: x[1].get('profit_factor', 0),
                reverse=True
            )
            
            # Print results
            print(f"{'Strategy':<12} | {'Trades':>7} | {'Win%':>7} | {'PF':>6} | {'MaxDD%':>8} | {'PnL':>12}")
            print("-" * 100)
            
            for strat_id, metrics in strategies_sorted:
                trades = metrics.get('total_trades', metrics.get('trades', 0))
                wr = metrics.get('win_rate', 0) * 100
                pf = metrics.get('profit_factor', 0)
                dd = metrics.get('max_drawdown', 0) * 100
                pnl = metrics.get('total_pnl', 0)
                
                status = ""
                if pf >= 1.2 and wr >= 40:
                    status = " ✅ PROFITABLE"
                elif pf >= 1.0:
                    status = " ⚠️  BREAKEVEN"
                else:
                    status = " ❌ LOSING"
                
                print(f"{strat_id:<12} | {trades:>7.0f} | {wr:>7.1f} | {pf:>6.2f} | {dd:>8.1f} | ${pnl:>11,.0f}{status}")
            
            # Analysis
            print("\n" + "="*100)
            print("ANALYSIS")
            print("="*100 + "\n")
            
            profitable = [(k, v) for k, v in strategies_sorted 
                         if v.get('profit_factor', 0) >= 1.2 and v.get('win_rate', 0) >= 0.40]
            near_profitable = [(k, v) for k, v in strategies_sorted 
                              if 1.0 <= v.get('profit_factor', 0) < 1.2]
            
            if profitable:
                print(f"✅ PROFITABLE CONFIGS (PF ≥ 1.2): {len(profitable)}")
                for strat_id, metrics in profitable:
                    pf = metrics.get('profit_factor', 0)
                    wr = metrics.get('win_rate', 0) * 100
                    trades = metrics.get('total_trades', metrics.get('trades', 0))
                    print(f"   {strat_id:12} → PF={pf:.2f}, WR={wr:.1f}%, Trades={int(trades)}")
                print("\n🎯 WINNER FOUND! This configuration is ready for trading.")
            elif near_profitable:
                print(f"⚠️  NEAR-PROFITABLE (1.0 ≤ PF < 1.2): {len(near_profitable)}")
                for strat_id, metrics in near_profitable:
                    pf = metrics.get('profit_factor', 0)
                    print(f"   {strat_id:12} → PF={pf:.2f}")
                print("\n📊 Close but not quite. Further tuning may help.")
            else:
                print("❌ NO PROFITABLE CONFIG FOUND")
                print("All ratios tested. Current best:")
                if strategies_sorted:
                    best_id, best_metrics = strategies_sorted[0]
                    best_pf = best_metrics.get('profit_factor', 0)
                    print(f"   {best_id}: PF={best_pf:.2f}")
            
            # Export summary
            summary_file = Path("backtest_results") / "S001_RR_VARIANTS_SUMMARY.json"
            summary_file.parent.mkdir(exist_ok=True)
            
            summary = {
                "test": "S001 R:R Optimization",
                "timestamp": datetime.datetime.now().isoformat(),
                "strategies_tested": [x[0] for x in strategies_sorted],
                "results": {k: {
                    "trades": v.get('total_trades', v.get('trades', 0)),
                    "pf": round(v.get('profit_factor', 0), 2),
                    "win_rate": round(v.get('win_rate', 0) * 100, 1),
                    "max_dd": round(v.get('max_drawdown', 0) * 100, 1),
                    "pnl": round(v.get('total_pnl', 0), 0)
                } for k, v in strategies_sorted}
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"\n✅ Results saved to: {summary_file}\n")
            print("="*100 + "\n")
        else:
            print("\n❌ No results returned - backtest may have failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] User stopped test")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

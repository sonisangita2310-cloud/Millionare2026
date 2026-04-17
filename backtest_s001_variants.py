#!/usr/bin/env python
"""
S001 Variants Backtest Runner
Test 6 S001 variants to find optimal edge parameters
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_runner import BacktestRunner

if __name__ == "__main__":
    print("\n" + "="*100)
    print(" "*25 + "S001 VARIANTS OPTIMIZATION BACKTEST")
    print("="*100)
    
    try:
        runner = BacktestRunner(initial_capital=100000.0)
        
        # Run backtest with S001 variants only
        results = runner.run_full_backtest(
            symbols=['BTC/USDT', 'ETH/USDT'],
            timeframes=['5m', '3m', '1h'],  # Include 5m for pre-alignment base
            use_real_data=True,
            scenarios_file="scenarios/S001_VARIANTS.json"  # Use variants only
        )
        
        if results and results.get('results'):
            print("\n" + "="*100)
            print("✅ S001 VARIANTS BACKTEST COMPLETE")
            print("="*100)
            
            # Extract results
            strategies = list(results['results'].items())
            strategies_sorted = sorted(
                strategies,
                key=lambda x: x[1].get('profit_factor', 0),
                reverse=True
            )
            
            print(f"\n{'Strategy':<12} | {'Trades':>7} | {'PF':>6} | {'WinRate':>8} | {'Expectancy':>10} | {'MaxDD':>6}")
            print("-" * 100)
            
            for strat_id, metrics in strategies_sorted:
                trades = metrics.get('trades', 0)
                pf = metrics.get('profit_factor', 0)
                wr = metrics.get('win_rate', 0) * 100
                exp = metrics.get('expectancy', 0)
                dd = metrics.get('max_drawdown', 0)
                
                # Highlight profitable strategies
                if pf >= 1.3:
                    marker = "✅"
                elif pf >= 1.0:
                    marker = "⚠️ "
                else:
                    marker = "❌"
                
                print(f"{marker} {strat_id:<10} | {trades:>7} | {pf:>6.2f} | {wr:>7.1f}% | {exp:>10.2f} | {dd:>6.3f}")
            
            # Summary
            total_trades = sum(m.get('trades', 0) for _, m in strategies)
            profitable = [s for s, m in strategies if m.get('profit_factor', 0) >= 1.3]
            breakeven = [s for s, m in strategies if 1.0 <= m.get('profit_factor', 0) < 1.3]
            
            print("\n" + "="*100)
            print("SUMMARY:")
            print(f"  Total trades (all variants): {total_trades}")
            print(f"  Profitable (PF ≥ 1.3): {len(profitable)} strategies")
            if profitable:
                print(f"    {', '.join(profitable)}")
            print(f"  Breakeven (1.0 ≤ PF < 1.3): {len(breakeven)} strategies")
            if breakeven:
                print(f"    {', '.join(breakeven)}")
            print("="*100 + "\n")
            
            if not profitable:
                print("⚠️  No profitable variants yet. May need further tuning or market conditions not favorable.")
            else:
                print(f"✅ Found {len(profitable)} profitable variant(s). Ready for portfolio construction!")
        
        else:
            print("\n❌ Backtest failed or no results")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

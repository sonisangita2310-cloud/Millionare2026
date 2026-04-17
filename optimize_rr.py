"""
S001 Risk/Reward Optimization Backtest
====================================
Test 4 R:R combinations on S001 + S001_E
Find profitable configuration (PF ≥ 1.2, WR ≥ 40%)
"""

import json
import pandas as pd
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from backtest_runner import BacktestRunner
from backtest_data_engine import DataEngine

def run_rr_optimization():
    """Run R:R optimization backtest suite using existing infrastructure"""
    
    print("\n" + "="*80)
    print("S001 RISK/REWARD OPTIMIZATION BACKTEST")
    print("="*80)
    print("\nTesting 4 R:R combinations across S001 + S001_E")
    print("Goal: Find PF ≥ 1.2 with Win Rate ≥ 40%\n")
    
    # Step 1: Fetch data
    print("[STEP 1] Fetching market data...")
    data_engine = DataEngine()
    try:
        data = data_engine.get_all_data(
            symbols=['BTC/USDT'],
            timeframes=['3m', '1h'],
            force_real_data=True
        )
        print(f"✅ Data fetched successfully")
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return
    
    # Step 2: Sync timeframes
    print("[STEP 2] Syncing multi-timeframe data...")
    data = data_engine.sync_multiframe_data(data)
    
    # Step 3: Use existing backtest runner with fetched data
    print("[STEP 3] Running optimization backtests...\n")
    runner = BacktestRunner(initial_capital=100000.0)
    
    results = runner.run_full_backtest(
        symbols=['BTC/USDT'],
        timeframes=['3m', '1h'],
        use_real_data=True,
        scenarios_file="scenarios/S001_RR_OPTIMIZATION.json",
        data=data  # Pass pre-fetched data
    )
    
    if not results:
        print("❌ No results returned from backtest")
        return
    
    # Extract results for display
    display_results = []
    
    for scenario_id, metrics in results.items():
        if isinstance(metrics, dict) and 'profit_factor' in metrics:
            # Parse scenario info from ID
            sl_val = metrics.get('sl_multiplier', '?')
            tp_val = metrics.get('tp_multiplier', '?')
            
            pf = metrics.get('profit_factor', 0)
            wr = metrics.get('win_rate', 0)
            trades = metrics.get('total_trades', 0)
            max_dd = metrics.get('max_drawdown', 0)
            pnl = metrics.get('total_pnl', 0)
            
            display_results.append({
                "Strategy": scenario_id,
                "SL": f"ATR*{sl_val}",
                "TP": f"ATR*{tp_val}",
                "Trades": trades,
                "PF": round(pf, 2),
                "Win%": f"{wr:.1%}",
                "MaxDD": f"{max_dd:.1%}",
                "PnL": f"${pnl:,.0f}"
            })
            
            # Quick feedback
            status = ""
            if pf >= 1.2 and wr >= 0.40:
                status = "✅ PROFITABLE"
            elif pf >= 1.0:
                status = "⚠️  BREAKEVEN"
            else:
                status = "❌ LOSING"
            
            print(f"{scenario_id:12} | PF={pf:.2f} | WR={wr:.1%} | Trades={trades:3} | {status}")
    
    # Print summary table
    print("\n" + "="*80)
    print("DETAILED RESULTS")
    print("="*80 + "\n")
    
    if display_results:
        results_df = pd.DataFrame(display_results)
        print(results_df.to_string(index=False))
    else:
        print("No results to display")
    
    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80 + "\n")
    
    profitable = [r for r in display_results if isinstance(r.get("PF"), (int, float)) and r.get("PF") >= 1.2]
    near_profitable = [r for r in display_results if isinstance(r.get("PF"), (int, float)) and 1.0 <= r.get("PF") < 1.2]
    losing = [r for r in display_results if isinstance(r.get("PF"), (int, float)) and r.get("PF") < 1.0]
    
    if profitable:
        print(f"✅ PROFITABLE (PF ≥ 1.2): {len(profitable)} configuration(s)")
        for config in profitable:
            print(f"   {config['Strategy']}: PF={config['PF']}, WR={config['Win%']}, Trades={config['Trades']}")
    
    if near_profitable:
        print(f"⚠️  NEAR-PROFITABLE (1.0 ≤ PF < 1.2): {len(near_profitable)} configuration(s)")
        for config in near_profitable:
            print(f"   {config['Strategy']}: PF={config['PF']}, WR={config['Win%']}, Trades={config['Trades']}")
    
    if losing:
        print(f"❌ LOSING (PF < 1.0): {len(losing)} configuration(s)")
    
    # Export detailed results
    results_file = Path(__file__).parent / "backtest_results" / "S001_RR_OPTIMIZATION_RESULTS.json"
    results_file.parent.mkdir(exist_ok=True)
    
    export_data = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "summary": {
            "total_scenarios": len(display_results),
            "profitable": len(profitable),
            "near_profitable": len(near_profitable),
            "losing": len(losing)
        },
        "results": display_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✅ Detailed results saved to: {results_file}")
    print("="*80 + "\n")
    
    return display_results


if __name__ == "__main__":
    run_rr_optimization()

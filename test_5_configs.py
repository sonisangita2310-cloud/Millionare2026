#!/usr/bin/env python
"""Minimal test for 5 S001_E configurations - using cached data only"""

import sys
import os
sys.path.insert(0, '.')

import json
import pandas as pd
from pathlib import Path
from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine

# Define the 5 test configs for S001_E
configs = [
    {"sl": 1.0, "tp": 3.0},
    {"sl": 1.0, "tp": 4.0},
    {"sl": 0.8, "tp": 3.5},
    {"sl": 1.2, "tp": 4.0},
    {"sl": 1.0, "tp": 2.5},
]

# Load base S001 scenario structure
with open('scenarios/S001_RR_OPTIMIZATION.json') as f:
    base_scenarios = json.load(f)

base_scenario = base_scenarios['scenarios'][0]  # Use first S001 as template

print("\n" + "="*80)
print("S001_E - 5 Configuration Test (CACHED DATA: ETH 3m+1h)")
print("="*80)

# Load cached data
print("Loading cached data from CSV files...")
data_engine = DataEngine()
data = {}

# S001 strategy uses 3m as primary timeframe, with 1h as higher TF
# We have ETH_USDT_3m and ETH_USDT_1h available - use those
eth_3m_path = Path('data_cache/ETH_USDT_3m.csv')
eth_1h_path = Path('data_cache/ETH_USDT_1h.csv')

if eth_3m_path.exists() and eth_1h_path.exists():
    print(f"✓ Found ETH cached data (3m + 1h)")
    try:
        eth_3m = pd.read_csv(eth_3m_path)
        eth_1h = pd.read_csv(eth_1h_path)
        
        # Set datetime as index if present
        if 'Datetime' in eth_3m.columns:
            eth_3m.set_index('Datetime', inplace=True)
            eth_3m.index = pd.to_datetime(eth_3m.index)
        if 'Datetime' in eth_1h.columns:
            eth_1h.set_index('Datetime', inplace=True)
            eth_1h.index = pd.to_datetime(eth_1h.index)
        
        # Use ETH/USDT for testing (S001 strategy agnostic to asset)
        data['ETH/USDT'] = {
            '3m': eth_3m,
            '1h': eth_1h
        }
        print(f"  • ETH 3m: {len(eth_3m)} candles")
        print(f"  • ETH 1h: {len(eth_1h)} candles")
    except Exception as e:
        print(f"ERROR loading CSVs: {e}")
        sys.exit(1)
else:
    print("ERROR: Could not find cached ETH data")

print(f"\n{'SL':<6} {'TP':<6} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

results = []

for config in configs:
    # Create scenario variant
    scenario_dict = base_scenario.copy()
    scenario_dict['sl_multiplier'] = config['sl']
    scenario_dict['tp_multiplier'] = config['tp']
    scenario_dict['id'] = f"S001_E_SL{config['sl']}_TP{config['tp']}"
    scenario_dict['name'] = f"S001_E - SL={config['sl']}, TP={config['tp']}"
    
    try:
        # Create temp config with this scenario
        temp_config = {
            "metadata": {
                "total_scenarios": 1,
                "version": "3.0",
                "phase": "5-Config Test"
            },
            "scenarios": [scenario_dict]
        }
        
        temp_file = f"scenarios/temp_test_SL{config['sl']}_TP{config['tp']}.json"
        with open(temp_file, 'w') as f:
            json.dump(temp_config, f, indent=2)
        
        # Run backtest with cached data (pass data directly)
        runner = BacktestRunner(initial_capital=100000.0)
        backtest_results = runner.run_full_backtest(
            symbols=['ETH/USDT'],
            timeframes=['3m', '1h'],
            scenarios_file=temp_file,
            use_real_data=True,
            data=data  # Pass cached data directly
        )
        
        # Extract trades
        all_trades = []
        if backtest_results:
            for symbol_key, symbol_res in backtest_results.items():
                if isinstance(symbol_res, dict) and 'trades' in symbol_res:
                    all_trades.extend(symbol_res['trades'])
        
        # Calculate metrics
        if all_trades:
            df = pd.DataFrame(all_trades)
            trades = len(df)
            wins = len(df[df['pnl'] > 0])
            losses = len(df[df['pnl'] < 0])
            wr = wins / trades if trades > 0 else 0
            
            total_win = df[df['pnl'] > 0]['pnl'].sum() if wins > 0 else 0
            total_loss = abs(df[df['pnl'] < 0]['pnl'].sum()) if losses > 0 else 1
            pf = total_win / total_loss if total_loss > 0 else (1.0 if total_win > 0 else 0)
            
            maxdd = df['max_drawdown_pct'].max() * 100 if 'max_drawdown_pct' in df.columns else 0
        else:
            trades = 0
            pf = 0
            wr = 0
            maxdd = 0
        
        print(f"{config['sl']:<6} {config['tp']:<6} {trades:<8} {pf:<8.2f} {wr*100:<10.1f}% {maxdd:<8.1f}%")
        
        results.append({
            'sl': config['sl'],
            'tp': config['tp'],
            'trades': trades,
            'pf': pf,
            'win_rate': wr,
            'max_dd': maxdd
        })
        
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    except Exception as e:
        print(f"{config['sl']:<6} {config['tp']:<6} ERROR: {str(e)[:40]}")
        import traceback
        traceback.print_exc()
        # Clean up
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass

print("-"*80)

# Check for PF >= 1.2
profitable = [r for r in results if r['pf'] >= 1.2]
if profitable:
    print(f"\n✅ FOUND {len(profitable)} profitable configuration(s):")
    for r in profitable:
        print(f"   SL={r['sl']}, TP={r['tp']}: PF={r['pf']:.2f}, WR={r['win_rate']*100:.1f}%")
else:
    print(f"\n❌ No PF >= 1.2 found")
    if results:
        best = max(results, key=lambda x: x['pf'])
        print(f"   Best: SL={best['sl']}, TP={best['tp']}: PF={best['pf']:.2f}")

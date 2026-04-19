#!/usr/bin/env python
"""Run full Phase 2 simulation in BACKTEST mode"""

import pandas as pd
import sys
sys.path.append('.')
from paper_trading_simulator_v2 import PaperTradingSimulatorV2

def main():
    """Run Phase 2 paper trading simulation"""
    print("\n" + "="*100)
    print("PHASE 2: PAPER TRADING VALIDATION - FULL DATASET (2000 candles)")
    print("="*100 + "\n")
    
    try:
        # Load data
        data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        # Last 2000 candles for comprehensive testing
        data_sim = data.iloc[-2000:].reset_index(drop=True)
        
        print(f"Data loaded: {len(data_sim)} candles")
        print(f"Date range: {data_sim.iloc[0]['timestamp']} to {data_sim.iloc[-1]['timestamp']}\n")
        
        # Run Phase 2 simulation
        # Using BACKTEST mode for fast execution (real-time mode processes one candle at a time with waiting)
        sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
        results = sim.run_simulation(verbose=True, mode='backtest')
        
        # Print results
        sim.print_results()
        
        # Save trades
        sim.save_trades_csv()
        
        print("\n" + "="*100)
        print("PHASE 2 VALIDATION COMPLETE")
        print("="*100)
        
        # Summary stats
        if len(sim.trades) > 0:
            winners = sum(1 for t in sim.trades if t['winner'] == 1)
            losers = len(sim.trades) - winners
            win_rate = winners / len(sim.trades) * 100
            
            print(f"\n[SUMMARY]")
            print(f"  Total trades: {len(sim.trades)}")
            print(f"  Winners: {winners} ({win_rate:.1f}%)")
            print(f"  Losers: {losers} ({100-win_rate:.1f}%)")
            print(f"  Profit factor: {results.get('profit_factor', 0):.2f}x")
            print(f"  Max drawdown: {results.get('max_drawdown_pct', 0):.2f}%")
            print(f"  Final return: {results.get('total_return_pct', 0):.2f}%")
            print(f"  Rolling checks: {len(sim.rolling_checks)}")
            
            if len(sim.rolling_checks) > 0:
                latest = sim.rolling_checks[-1]
                print(f"\n[LATEST ROLLING CHECK (last 10 trades)]")
                print(f"  Win rate: {latest['win_rate']:.1f}%")
                print(f"  Profit factor: {latest['profit_factor']:.2f}x")
                print(f"  Status: {latest['status']}")
        else:
            print("\n[NO TRADES] System ran but generated no trades")
        
        return 0
        
    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

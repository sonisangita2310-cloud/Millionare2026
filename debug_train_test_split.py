#!/usr/bin/env python
"""
Debug script to run backtest on TRAIN vs TEST periods separately
and see which generates trades
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine

def main():
    print("\n" + "="*80)
    print("TRAIN vs TEST SPLIT ANALYSIS")
    print("="*80)
    
    # Step 1: Fetch full data with ALL required timeframes
    print("\n[STEP 1] Fetching full market data...")
    data_engine = DataEngine()
    # ALL 32 strategies need these timeframes (S017 needs Weekly but skip for API compatibility)
    all_required_timeframes = ['1m', '3m', '4h', '5m', '15m', '1h']
    full_data = data_engine.get_all_data(['BTC/USDT', 'ETH/USDT'], all_required_timeframes, force_real_data=True)
    full_data = data_engine.sync_multiframe_data(full_data)
    
    # Step 2: Split chronologically
    print("\n[STEP 2] Splitting data 60/40...")
    train_data = {}
    test_data = {}
    
    for symbol in full_data:
        train_data[symbol] = {}
        test_data[symbol] = {}
        
        for timeframe in full_data[symbol]:
            df = full_data[symbol][timeframe].copy()
            split_idx = int(len(df) * 0.6)
            
            train_data[symbol][timeframe] = df.iloc[:split_idx].copy()
            test_data[symbol][timeframe] = df.iloc[split_idx:].copy()
            
            print(f"{symbol} {timeframe}: TRAIN={len(train_data[symbol][timeframe]):,} candles | TEST={len(test_data[symbol][timeframe]):,} candles")
    
    # Step 3: Run backtest on TRAIN period
    print("\n" + "="*80)
    print("RUNNING BACKTEST ON TRAIN PERIOD (60% of data)")
    print("="*80)
    
    runner_train = BacktestRunner(initial_capital=100000.0)
    runner_train.data_engine.exchange = data_engine.exchange
    
    # Use ALL required timeframes for runner
    all_required_timeframes = ['1m', '3m', '4h', '5m', '15m', '1h']
    
    train_results = runner_train.run_full_backtest(
        symbols=['BTC/USDT', 'ETH/USDT'],
        timeframes=all_required_timeframes,
        use_real_data=True,
        data=train_data
    )
    
    print("\n[TRAIN RESULTS]")
    if train_results and train_results.get('results'):
        total_trades = sum(r.get('trades', 0) for r in train_results['results'].values())
        print(f"Total trades across all strategies: {total_trades}")
        
        # Show top 5
        sorted_strats = sorted(
            train_results['results'].items(),
            key=lambda x: x[1].get('trades', 0),
            reverse=True
        )
        print(f"\nTop 5 by trades in TRAIN period:")
        for strat_id, metrics in sorted_strats[:5]:
            print(f"  {strat_id}: {metrics.get('trades', 0)} trades, PF={metrics.get('profit_factor', 0):.2f}")
    
    # Step 4: Run backtest on TEST period
    print("\n" + "="*80)
    print("RUNNING BACKTEST ON TEST PERIOD (40% of data)")
    print("="*80)
    
    runner_test = BacktestRunner(initial_capital=100000.0)
    runner_test.data_engine.exchange = data_engine.exchange
    
    # Use ALL required timeframes for runner
    all_required_timeframes = ['1m', '3m', '4h', '5m', '15m', '1h']
    
    test_results = runner_test.run_full_backtest(
        symbols=['BTC/USDT', 'ETH/USDT'],
        timeframes=all_required_timeframes,
        use_real_data=True,
        data=test_data
    )
    
    print("\n[TEST RESULTS]")
    if test_results and test_results.get('results'):
        total_trades = sum(r.get('trades', 0) for r in test_results['results'].values())
        print(f"Total trades across all strategies: {total_trades}")
        
        # Show top 5
        sorted_strats = sorted(
            test_results['results'].items(),
            key=lambda x: x[1].get('trades', 0),
            reverse=True
        )
        print(f"\nTop 5 by trades in TEST period:")
        for strat_id, metrics in sorted_strats[:5]:
            print(f"  {strat_id}: {metrics.get('trades', 0)} trades, PF={metrics.get('profit_factor', 0):.2f}")
    
    # Summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    train_trades = sum(r.get('trades', 0) for r in (train_results.get('results', {}) if train_results else {}).values())
    test_trades = sum(r.get('trades', 0) for r in (test_results.get('results', {}) if test_results else {}).values())
    
    print(f"TRAIN period: {train_trades} total trades")
    print(f"TEST period:  {test_trades} total trades")
    
    if train_trades > 0 and test_trades == 0:
        print("\n⚠️  INTERPRETATION: Strategies generate signals in TRAIN period but not in TEST period")
        print("This suggests recent market conditions don't match the trading logic")
    elif train_trades > 0 and test_trades > 0:
        print(f"\n✅ Both periods generating trades. Ratio: {test_trades/train_trades*100:.1f}% of train trades")
    elif train_trades == 0:
        print("\n❌ No trades in either period - possible issue with scenarios or conditions")

if __name__ == "__main__":
    main()

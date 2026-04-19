#!/usr/bin/env python
"""Test real-time and backtest modes for paper trading simulator"""

import pandas as pd
import sys
sys.path.append('.')
from paper_trading_simulator_v2 import PaperTradingSimulatorV2

def test_backtest_mode():
    """Test backtest mode with small subset of data"""
    print("="*80)
    print("TEST 1: BACKTEST MODE (should complete quickly)")
    print("="*80)
    
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    # Use just 500 candles for quick test
    data_sim = data.iloc[-500:].reset_index(drop=True)
    
    sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
    results = sim.run_simulation(verbose=False, mode='backtest')
    
    print(f"\n[BACKTEST COMPLETE]")
    print(f"  Total candles: {len(data_sim)}")
    print(f"  Total trades: {len(sim.trades)}")
    print(f"  Final equity: ${sim.current_capital:,.2f}")
    print(f"  Return: {((sim.current_capital - 500) / 500 * 100):.2f}%")
    print()
    
    return True

def test_realtime_mode():
    """Test real-time mode with limited candles"""
    print("="*80)
    print("TEST 2: REAL-TIME MODE (limited to 100 candles for quick test)")
    print("="*80)
    
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    # Use just 100 candles for quick test
    data_sim = data.iloc[-100:].reset_index(drop=True)
    
    print("Starting real-time mode with 100 candles...")
    print("(This will process one candle at a time with waiting)")
    print()
    
    sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
    results = sim.run_simulation(verbose=True, mode='realtime')
    
    print(f"\n[REALTIME COMPLETE]")
    print(f"  Total candles: {len(data_sim)}")
    print(f"  Total trades: {len(sim.trades)}")
    print(f"  Final equity: ${sim.current_capital:,.2f}")
    print(f"  Return: {((sim.current_capital - 500) / 500 * 100):.2f}%")
    print()
    
    return True

if __name__ == '__main__':
    try:
        # Test backtest mode first
        if test_backtest_mode():
            print("[PASS] Backtest mode test PASSED\n")
        
        # Test real-time mode with minimal candles
        print("="*80)
        print("TEST 2: REAL-TIME MODE (testing with 50 candles)")
        print("="*80)
        data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data_sim = data.iloc[-50:].reset_index(drop=True)
        
        print("Starting real-time mode (fast iteration, no actual waiting)")
        print()
        
        sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
        
        # Monkey-patch wait_for_next_candle to skip actual waiting
        original_wait = sim.wait_for_next_candle
        sim.wait_for_next_candle = lambda verbose=False: None
        
        results = sim.run_simulation(verbose=False, mode='realtime')
        
        print(f"[REALTIME COMPLETE]")
        print(f"  Total candles: {len(data_sim)}")
        print(f"  Total trades: {len(sim.trades)}")
        print(f"  Final equity: ${sim.current_capital:,.2f}")
        print(f"  Return: {((sim.current_capital - 500) / 500 * 100):.2f}%")
        print()
        print("[PASS] Real-time mode test PASSED\n")
        
        print("\n" + "="*80)
        print("SUCCESS: Code structure validated")
        print("="*80)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

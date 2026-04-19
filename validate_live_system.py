#!/usr/bin/env python
"""Quick validation test for live paper trading system"""

import sys
import pandas as pd
from live_data_fetcher import LiveDataFetcher
from live_paper_trading_system import LivePaperTradingSystem

def test_live_system():
    """Test live paper trading system components"""
    print("\n" + "="*100)
    print("LIVE PAPER TRADING SYSTEM - COMPONENT VALIDATION")
    print("="*100 + "\n")
    
    # Test 1: Data fetcher
    print("[TEST 1] Live data fetcher")
    fetcher = LiveDataFetcher(lookback_candles=50)
    df = fetcher.fetch_candles(verbose=True)
    
    if df is None:
        print("[FAILED] Could not fetch live data")
        return False
    
    print(f"[PASS] Fetched {len(df)} real candles from Binance\n")
    
    # Test 2: Signal generation with live data
    print("[TEST 2] Signal generation with live data")
    try:
        from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
        gen = PullbackSignalGeneratorV35()
        df_indexed = df.set_index('timestamp')
        signals = gen.generate_signals(df_indexed)
        signal = signals['signal'].iloc[-1] if len(signals) > 0 else 0
        print(f"[PASS] Signal generator working: signal = {signal}\n")
    except Exception as e:
        print(f"[FAILED] Signal generator error: {str(e)}\n")
        return False
    
    # Test 3: System initialization
    print("[TEST 3] System initialization")
    try:
        system = LivePaperTradingSystem(
            initial_capital=500,
            risk_per_trade=0.0025,
            lookback_candles=50
        )
        print(f"[PASS] System initialized successfully\n")
    except Exception as e:
        print(f"[FAILED] System initialization failed: {str(e)}\n")
        return False
    
    # Test 4: Verify strict mode (strategy unchanged)
    print("[TEST 4] Verify strategy parameters (STRICT MODE)")
    print(f"  SL multiplier: {system.sl_mult}x (target: 1.1x)")
    print(f"  TP multiplier: {system.tp_mult}x (target: 3.2x)")
    print(f"  Entry slippage: {system.entry_slippage*100:.3f}% (target: 0.03%)")
    print(f"  Exit slippage: {system.exit_slippage*100:.3f}% (target: 0.03%)")
    print(f"  Entry fee: {system.entry_fee_pct*100:.2f}% (target: 0.1%)")
    print(f"  Exit fee: {system.exit_fee_pct*100:.2f}% (target: 0.1%)")
    
    if (system.sl_mult == 1.1 and system.tp_mult == 3.2 and 
        system.entry_slippage == 0.0003 and system.exit_slippage == 0.0003):
        print("[PASS] All parameters locked (STRICT MODE enforced)\n")
    else:
        print("[FAILED] Parameters do not match expected values\n")
        return False
    
    print("="*100)
    print("ALL VALIDATION TESTS PASSED")
    print("="*100)
    print("\nSystem is ready for Phase 2 live paper trading")
    print("\nTo start live trading:")
    print("  python live_paper_trading_system.py\n")
    
    return True


if __name__ == '__main__':
    if test_live_system():
        sys.exit(0)
    else:
        sys.exit(1)

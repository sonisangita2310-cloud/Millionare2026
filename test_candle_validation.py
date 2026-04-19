#!/usr/bin/env python
"""
Test Script: DEFENSIVE CANDLE VALIDATION
Demonstrates the closed candle validation with real examples
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
sys.path.append('.')

from live_paper_trading_system import LivePaperTradingSystem


def test_validation_with_real_data():
    """Test validation with real Binance data"""
    
    print("\n" + "="*100)
    print("TEST 1: VALIDATION WITH REAL BINANCE DATA")
    print("="*100 + "\n")
    
    # Initialize system
    system = LivePaperTradingSystem(initial_capital=500)
    
    # Fetch real candles
    print("[FETCH] Getting real data from Binance...")
    df = system.fetcher.fetch_candles(verbose=True)
    
    if df is None:
        print("[ERROR] Failed to fetch candles")
        return False
    
    print()
    
    # Test with latest real candle
    print("[TEST] Validating latest real candle...")
    latest_candle = df.iloc[-1]
    
    result = system._validate_candle_is_closed(latest_candle, verbose=True)
    print(f"\n[RESULT] Validation: {'PASSED ✅' if result else 'FAILED ❌'}\n")
    
    return result


def test_validation_with_synthetic_closed():
    """Test with synthetic CLOSED candle"""
    
    print("\n" + "="*100)
    print("TEST 2: SYNTHETIC CLOSED CANDLE")
    print("="*100 + "\n")
    
    system = LivePaperTradingSystem(initial_capital=500)
    
    # Create a candle that is definitely CLOSED
    # Candle from 2 hours ago
    now = datetime.now()
    candle_timestamp = now - timedelta(hours=2)
    
    closed_candle = pd.Series({
        'timestamp': pd.Timestamp(candle_timestamp),
        'open': 75000.0,
        'high': 75500.0,
        'low': 74500.0,
        'close': 75250.0,
        'volume': 100.0
    })
    
    print(f"[CANDLE] Creating synthetic CLOSED candle from 2 hours ago...")
    
    result = system._validate_candle_is_closed(closed_candle, verbose=True)
    print(f"\n[RESULT] Validation: {'PASSED ✅' if result else 'FAILED ❌'}\n")
    
    return result


def test_validation_with_synthetic_forming():
    """Test with synthetic FORMING candle"""
    
    print("\n" + "="*100)
    print("TEST 3: SYNTHETIC FORMING CANDLE")
    print("="*100 + "\n")
    
    system = LivePaperTradingSystem(initial_capital=500)
    
    # Create a candle that is currently FORMING
    # Candle that will close in the future
    now = datetime.now()
    # Create a candle that started 30 minutes from now (will close 30 minutes + 1h in future)
    candle_timestamp = now + timedelta(minutes=30)
    
    forming_candle = pd.Series({
        'timestamp': pd.Timestamp(candle_timestamp),
        'open': 75000.0,
        'high': 75500.0,
        'low': 74500.0,
        'close': 75250.0,
        'volume': 100.0
    })
    
    print(f"[CANDLE] Creating synthetic FORMING candle (closes in future)...")
    
    result = system._validate_candle_is_closed(forming_candle, verbose=True)
    
    if result:
        print(f"\n[RESULT] Validation: PASSED ✅ (Unexpected - candle should be forming)\n")
        return False
    else:
        print(f"\n[RESULT] Validation: FAILED as expected ❌ (Candle is still forming)\n")
        return True  # Expected to fail


def test_validation_edge_cases():
    """Test edge cases"""
    
    print("\n" + "="*100)
    print("TEST 4: EDGE CASES")
    print("="*100 + "\n")
    
    system = LivePaperTradingSystem(initial_capital=500)
    
    # Test 1: Just closed (1 second ago)
    print("[EDGE CASE 1] Candle that just closed (1 second ago)...")
    now = datetime.now()
    candle_timestamp = now - timedelta(hours=1, seconds=1)
    
    just_closed = pd.Series({
        'timestamp': pd.Timestamp(candle_timestamp),
        'open': 75000.0,
        'high': 75500.0,
        'low': 74500.0,
        'close': 75250.0,
        'volume': 100.0
    })
    
    result1 = system._validate_candle_is_closed(just_closed, verbose=True)
    print(f"Result: {'PASSED ✅' if result1 else 'FAILED ❌'}\n")
    
    # Test 2: About to close (1 minute remaining)
    print("[EDGE CASE 2] Candle about to close (1 minute remaining)...")
    now = datetime.now()
    candle_timestamp = now - timedelta(hours=1, minutes=59)
    
    almost_closed = pd.Series({
        'timestamp': pd.Timestamp(candle_timestamp),
        'open': 75000.0,
        'high': 75500.0,
        'low': 74500.0,
        'close': 75250.0,
        'volume': 100.0
    })
    
    result2 = system._validate_candle_is_closed(almost_closed, verbose=True)
    print(f"Result: {'PASSED ✅' if result2 else 'FAILED ❌'}\n")
    
    return result1 and result2


def main():
    """Run all validation tests"""
    
    print("\n" + "="*120)
    print("DEFENSIVE CLOSED CANDLE VALIDATION - TEST SUITE")
    print("="*120)
    
    all_passed = True
    
    # Test 1: Real data
    try:
        if not test_validation_with_real_data():
            all_passed = False
    except Exception as e:
        print(f"[ERROR] Test 1 failed: {str(e)}")
        all_passed = False
    
    # Test 2: Synthetic closed
    try:
        if not test_validation_with_synthetic_closed():
            all_passed = False
    except Exception as e:
        print(f"[ERROR] Test 2 failed: {str(e)}")
        all_passed = False
    
    # Test 3: Synthetic forming
    try:
        if not test_validation_with_synthetic_forming():
            all_passed = False
    except Exception as e:
        print(f"[ERROR] Test 3 failed: {str(e)}")
        all_passed = False
    
    # Test 4: Edge cases
    try:
        if not test_validation_edge_cases():
            all_passed = False
    except Exception as e:
        print(f"[ERROR] Test 4 failed: {str(e)}")
        all_passed = False
    
    # Summary
    print("\n" + "="*120)
    print("TEST SUMMARY")
    print("="*120 + "\n")
    
    if all_passed:
        print("✅ ALL TESTS PASSED\n")
        print("VALIDATION FEATURES:")
        print("  ✅ Checks: candle_close_time < current_time")
        print("  ✅ Logs: [CANDLE VALIDATION] with current time, candle close time, status")
        print("  ✅ Skips: Partially forming candles (return False)")
        print("  ✅ Defensive: Extra layer to prevent lookahead bias\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

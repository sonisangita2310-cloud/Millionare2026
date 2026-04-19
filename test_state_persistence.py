#!/usr/bin/env python
"""
Test Script: STATE PERSISTENCE AND CRASH RECOVERY
Demonstrates save/load functionality and restart safety
"""

import pandas as pd
from datetime import datetime
import sys
import json
import os
sys.path.append('.')

from live_paper_trading_system import LivePaperTradingSystem


def test_state_save_and_load():
    """Test state saving and loading"""
    
    print("\n" + "="*100)
    print("TEST 1: STATE SAVE AND LOAD")
    print("="*100 + "\n")
    
    # Clean up any existing state
    state_file = os.path.join(os.path.dirname(__file__), 'trading_state.json')
    if os.path.exists(state_file):
        os.remove(state_file)
        print("[CLEANUP] Removed existing state file\n")
    
    # Initialize system - should say NEW SESSION
    print("[INIT 1] Initializing system (new session)...")
    system1 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Simulate some state changes
    print("[MODIFY] Simulating state changes...")
    system1.last_processed_candle_time = pd.Timestamp('2026-04-19 14:00:00')
    system1.current_capital = 525.50
    system1.candles_processed = 5
    system1.trades = [
        {
            'trade_num': 1,
            'entry_time': pd.Timestamp('2026-04-19 13:00:00'),
            'entry_price': 75000.00,
            'position_btc': 0.1,
            'exit_time': pd.Timestamp('2026-04-19 14:00:00'),
            'exit_price': 75500.00,
            'exit_type': 'TP',
            'p_l': 12.50,
            'winner': 1,
        }
    ]
    system1.equity_curve = [500.00, 512.50, 525.50]
    system1._save_state()
    print("  - Saved: equity=$525.50, trades=1, candles=5\n")
    
    # Load from another system instance
    print("[INIT 2] Initializing new system instance (load from state)...")
    system2 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Verify state was loaded correctly
    print("[VERIFY] Checking loaded state...")
    print(f"  Equity: ${system2.current_capital:.2f} (expected: $525.50)")
    print(f"  Trades: {len(system2.trades)} (expected: 1)")
    print(f"  Candles processed: {system2.candles_processed} (expected: 5)")
    print(f"  Last candle: {system2.last_processed_candle_time} (expected: 2026-04-19 14:00:00)")
    
    # Verify trade details
    if len(system2.trades) > 0:
        trade = system2.trades[0]
        print(f"\n[TRADE] Loaded trade details:")
        print(f"  Entry: ${trade['entry_price']:.2f}")
        print(f"  Exit: ${trade['exit_price']:.2f}")
        print(f"  P&L: ${trade['p_l']:.2f}")
    
    success = (
        abs(system2.current_capital - 525.50) < 0.01 and
        len(system2.trades) == 1 and
        system2.candles_processed == 5
    )
    
    if success:
        print("\n[RESULT] PASSED ✅ - State correctly saved and loaded\n")
    else:
        print("\n[RESULT] FAILED ❌ - State mismatch\n")
    
    return success


def test_open_position_persistence():
    """Test open position persistence"""
    
    print("\n" + "="*100)
    print("TEST 2: OPEN POSITION PERSISTENCE")
    print("="*100 + "\n")
    
    # Clean up
    state_file = os.path.join(os.path.dirname(__file__), 'trading_state.json')
    if os.path.exists(state_file):
        os.remove(state_file)
        print("[CLEANUP] Removed existing state file\n")
    
    # Initialize and create open position
    print("[INIT 1] Creating system with open position...")
    system1 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Create an open position
    print("[CREATE] Creating open trade...")
    system1.last_processed_candle_time = pd.Timestamp('2026-04-19 14:00:00')
    system1.position = {
        'entry_time': pd.Timestamp('2026-04-19 13:00:00'),
        'entry_price': 75000.00,
        'position_size_btc': 0.0667,
        'position_size_usd': 5000.00,
        'entry_fee': 5.00,
        'stop_loss': 74185.00,
        'take_profit': 76024.00,
    }
    system1.current_capital = 495.00  # Capital reduced by position + fee
    system1._save_state()
    print(f"  Entry: ${system1.position['entry_price']:.2f}")
    print(f"  Position: {system1.position['position_size_btc']:.4f} BTC")
    print(f"  SL: ${system1.position['stop_loss']:.2f}")
    print(f"  TP: ${system1.position['take_profit']:.2f}\n")
    
    # Load into new instance
    print("[INIT 2] Loading system from state...")
    system2 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Verify position was loaded
    print("[VERIFY] Checking loaded position...")
    if system2.position is not None:
        print(f"  Entry: ${system2.position['entry_price']:.2f} (expected: $75,000.00)")
        print(f"  Position: {system2.position['position_size_btc']:.4f} BTC (expected: 0.0667)")
        print(f"  SL: ${system2.position['stop_loss']:.2f} (expected: $74,185.00)")
        print(f"  TP: ${system2.position['take_profit']:.2f} (expected: $76,024.00)")
        
        success = (
            abs(system2.position['entry_price'] - 75000.00) < 0.01 and
            abs(system2.position['position_size_btc'] - 0.0667) < 0.0001 and
            abs(system2.position['stop_loss'] - 74185.00) < 0.01 and
            abs(system2.position['take_profit'] - 76024.00) < 0.01
        )
        
        if success:
            print("\n[RESULT] PASSED ✅ - Open position correctly saved and loaded\n")
        else:
            print("\n[RESULT] FAILED ❌ - Position values mismatch\n")
        
        return success
    else:
        print("\n[RESULT] FAILED ❌ - Position not loaded\n")
        return False


def test_crash_recovery():
    """Test crash recovery scenario"""
    
    print("\n" + "="*100)
    print("TEST 3: CRASH RECOVERY SCENARIO")
    print("="*100 + "\n")
    
    # Clean up
    state_file = os.path.join(os.path.dirname(__file__), 'trading_state.json')
    if os.path.exists(state_file):
        os.remove(state_file)
        print("[CLEANUP] Removed existing state file\n")
    
    # Session 1: Do some trading
    print("[SESSION 1] Starting fresh trading session...")
    system1 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Simulate trading
    print("[SIMULATE] Running 3 candles of trading...")
    for candle_num in range(1, 4):
        system1.last_processed_candle_time = pd.Timestamp(f'2026-04-19 {12+candle_num}:00:00')
        system1.candles_processed = candle_num
        system1.current_capital = 500 + (candle_num * 10)
        system1._save_state()
        print(f"  Candle {candle_num}: Equity = ${system1.current_capital:.2f}")
    
    print(f"\n[CRASH] Session interrupted (simulating crash)...\n")
    
    # Session 2: Restart and verify recovery
    print("[SESSION 2] Restarting system after crash...")
    system2 = LivePaperTradingSystem(initial_capital=500)
    print()
    
    # Verify all state recovered
    print("[VERIFY] Checking recovery...")
    print(f"  Candles processed: {system2.candles_processed} (expected: 3)")
    print(f"  Current equity: ${system2.current_capital:.2f} (expected: $530.00)")
    
    success = (
        system2.candles_processed == 3 and
        abs(system2.current_capital - 530.00) < 0.01
    )
    
    if success:
        print("\n[RESULT] PASSED ✅ - Successfully recovered from crash\n")
    else:
        print("\n[RESULT] FAILED ❌ - Recovery failed\n")
    
    return success


def main():
    """Run all persistence tests"""
    
    print("\n" + "="*120)
    print("STATE PERSISTENCE AND CRASH RECOVERY - TEST SUITE")
    print("="*120)
    
    results = []
    
    # Test 1
    try:
        results.append(test_state_save_and_load())
    except Exception as e:
        print(f"[ERROR] Test 1 failed: {str(e)}")
        results.append(False)
    
    # Test 2
    try:
        results.append(test_open_position_persistence())
    except Exception as e:
        print(f"[ERROR] Test 2 failed: {str(e)}")
        results.append(False)
    
    # Test 3
    try:
        results.append(test_crash_recovery())
    except Exception as e:
        print(f"[ERROR] Test 3 failed: {str(e)}")
        results.append(False)
    
    # Summary
    print("\n" + "="*120)
    print("TEST SUMMARY")
    print("="*120 + "\n")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Results: {passed}/{total} tests passed\n")
    
    if all(results):
        print("✅ ALL TESTS PASSED\n")
        print("PERSISTENCE FEATURES:")
        print("  ✅ State saved to JSON file")
        print("  ✅ State loaded on startup")
        print("  ✅ Open positions persisted")
        print("  ✅ Equity and trades preserved")
        print("  ✅ Crash recovery working\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

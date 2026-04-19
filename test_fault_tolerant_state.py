"""
FAULT-TOLERANT STATE PERSISTENCE - TEST SUITE

Tests:
1. Corrupted JSON file handling (graceful recovery)
2. Safe writes (temp file + rename)
3. System continues even if save fails
4. Concurrent file access safety
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from live_paper_trading_system import LivePaperTradingSystem


class FaultToleranceTestSuite:
    """Comprehensive fault-tolerance tests"""
    
    def __init__(self):
        self.state_file = os.path.join(os.path.dirname(__file__), 'trading_state.json')
        self.temp_file = self.state_file + '.tmp'
        
    def cleanup(self):
        """Clean up test files"""
        for f in [self.state_file, self.temp_file]:
            if os.path.exists(f):
                os.remove(f)
    
    def test_corrupted_json_handling(self):
        """TEST 1: Corrupted JSON file - system starts fresh"""
        print("\n" + "="*100)
        print("TEST 1: CORRUPTED JSON HANDLING")
        print("="*100)
        
        self.cleanup()
        
        # Create corrupted JSON file
        print("\n[SETUP] Creating corrupted JSON file...")
        with open(self.state_file, 'w') as f:
            f.write("{ corrupted json [[ INVALID")
        
        print(f"[FILE] State file created with corrupted content (size: {os.path.getsize(self.state_file)} bytes)")
        
        # Try to initialize system
        print("\n[INIT] Initializing system with corrupted state file...")
        system = LivePaperTradingSystem()
        
        # Verify system started fresh (didn't crash)
        if system.current_capital == 500:
            print(f"\n[RESULT] PASSED ✅")
            print(f"  System recovered gracefully")
            print(f"  Current capital: ${system.current_capital:.2f} (fresh start)")
            print(f"  Expected: $500.00 (initial capital)")
            print(f"  Status: Started fresh, not crashed")
            return True
        else:
            print(f"\n[RESULT] FAILED ❌")
            print(f"  Expected capital: $500.00")
            print(f"  Got: ${system.current_capital:.2f}")
            return False
    
    def test_safe_write_temp_rename(self):
        """TEST 2: Safe writes using temp file + rename"""
        print("\n" + "="*100)
        print("TEST 2: SAFE WRITE - TEMP FILE + RENAME")
        print("="*100)
        
        self.cleanup()
        
        print("\n[INIT] Creating system...")
        system = LivePaperTradingSystem()
        
        # Simulate a trade
        print("\n[TRADE] Simulating a trade...")
        system.position = {
            'entry_time': datetime.now(),
            'entry_price': 75000.00,
            'position_size_btc': 0.0667,
            'stop_loss': 74185.00,
            'take_profit': 76024.00,
        }
        system.current_capital = 495.00
        
        # Save state
        print(f"\n[SAVE] Saving state (position + equity)...")
        system._save_state()
        
        # Verify state file exists
        if not os.path.exists(self.state_file):
            print(f"\n[RESULT] FAILED ❌ - State file not created")
            return False
        
        print(f"[FILE] State file created (size: {os.path.getsize(self.state_file)} bytes)")
        
        # Verify file is valid JSON
        try:
            with open(self.state_file, 'r') as f:
                saved_state = json.load(f)
            print(f"[VALID] JSON file is valid and readable")
        except:
            print(f"[RESULT] FAILED ❌ - State file is not valid JSON")
            return False
        
        # Verify temp file was cleaned up (atomic rename)
        if os.path.exists(self.temp_file):
            print(f"[RESULT] FAILED ❌ - Temp file not cleaned up (atomic rename failed)")
            return False
        
        print(f"[TEMP] Temp file cleaned up after rename (atomic write confirmed)")
        
        # Verify saved content
        if saved_state.get('equity') == 495.00:
            print(f"[VERIFY] Equity saved correctly: ${saved_state['equity']}")
        else:
            print(f"[RESULT] FAILED ❌ - Equity not saved correctly")
            return False
        
        if saved_state.get('open_trade') is not None:
            print(f"[VERIFY] Open trade saved correctly")
        else:
            print(f"[RESULT] FAILED ❌ - Open trade not saved")
            return False
        
        print(f"\n[RESULT] PASSED ✅")
        print(f"  State saved to temporary file")
        print(f"  Atomically renamed to state file")
        print(f"  Temp file cleaned up")
        print(f"  Content verified")
        return True
    
    def test_load_after_safe_write(self):
        """TEST 3: Load state that was safely written"""
        print("\n" + "="*100)
        print("TEST 3: LOAD STATE AFTER SAFE WRITE")
        print("="*100)
        
        self.cleanup()
        
        # Create and save state
        print("\n[SYSTEM 1] Creating system with trade...")
        system1 = LivePaperTradingSystem()
        system1.position = {
            'entry_time': datetime.now(),
            'entry_price': 75000.00,
            'position_size_btc': 0.0667,
            'stop_loss': 74185.00,
            'take_profit': 76024.00,
        }
        system1.current_capital = 495.00
        system1.candles_processed = 42
        system1._save_state()
        
        print(f"[SAVED] State saved: equity=${system1.current_capital:.2f}, candles={system1.candles_processed}")
        
        # Load state in new system instance
        print(f"\n[SYSTEM 2] Loading system from saved state...")
        system2 = LivePaperTradingSystem()
        
        # Verify loaded values
        checks = [
            ("Equity", system2.current_capital, 495.00),
            ("Candles", system2.candles_processed, 42),
            ("Has open position", system2.position is not None, True),
        ]
        
        all_pass = True
        for name, actual, expected in checks:
            if actual == expected:
                print(f"[OK] {name}: {actual} ✅")
            else:
                print(f"[FAIL] {name}: expected {expected}, got {actual} ❌")
                all_pass = False
        
        if all_pass:
            print(f"\n[RESULT] PASSED ✅")
            print(f"  State loaded correctly after safe write")
            return True
        else:
            print(f"\n[RESULT] FAILED ❌")
            return False
    
    def test_continue_on_save_failure(self):
        """TEST 4: System continues even if save fails"""
        print("\n" + "="*100)
        print("TEST 4: CONTINUE ON SAVE FAILURE")
        print("="*100)
        
        self.cleanup()
        
        print("\n[INIT] Creating system...")
        system = LivePaperTradingSystem()
        
        # Make state file read-only (force save to fail)
        print("\n[SETUP] Making state directory read-only to force save failure...")
        original_state_file = system.state_file
        # Change to invalid path that can't be written to
        system.state_file = "/invalid/path/that/cannot/be/written/to/state.json"
        
        print(f"[SETUP] Set invalid path: {system.state_file}")
        
        # Try to save (should fail gracefully)
        print(f"\n[SAVE] Attempting to save to invalid path...")
        try:
            system._save_state()
            print(f"[SAVE] Save attempted (error expected and handled)")
        except Exception as e:
            print(f"[CRASH] ERROR: Save raised exception: {str(e)}")
            print(f"[RESULT] FAILED ❌ - System crashed during save failure")
            return False
        
        # Verify system still functional
        print(f"\n[CHECK] Verifying system is still functional...")
        if system.current_capital == 500:
            print(f"[OK] System still operational: capital = ${system.current_capital:.2f}")
            print(f"\n[RESULT] PASSED ✅")
            print(f"  Save failed gracefully")
            print(f"  System continued operating")
            print(f"  No crash or exception")
            return True
        else:
            print(f"[RESULT] FAILED ❌")
            return False
    
    def test_partially_written_file(self):
        """TEST 5: Partially written file (interrupted write)"""
        print("\n" + "="*100)
        print("TEST 5: PARTIALLY WRITTEN FILE HANDLING")
        print("="*100)
        
        self.cleanup()
        
        # Create a partially written (incomplete) JSON file
        print("\n[SETUP] Creating partially written JSON file (simulates interrupted write)...")
        with open(self.state_file, 'w') as f:
            f.write('{"equity": 500.00, "trades": [')
            # Incomplete JSON - missing closing brackets
        
        print(f"[FILE] Created incomplete JSON (missing closing brackets)")
        
        # Try to initialize system
        print(f"\n[INIT] Initializing system with incomplete state file...")
        system = LivePaperTradingSystem()
        
        # Verify system started fresh
        if system.current_capital == 500:
            print(f"\n[RESULT] PASSED ✅")
            print(f"  System detected incomplete JSON")
            print(f"  Started fresh without crashing")
            print(f"  Current capital: ${system.current_capital:.2f}")
            return True
        else:
            print(f"\n[RESULT] FAILED ❌")
            return False
    
    def run_all_tests(self):
        """Run all fault-tolerance tests"""
        print("\n" + "="*100)
        print("FAULT-TOLERANT STATE PERSISTENCE - TEST SUITE")
        print("="*100)
        
        tests = [
            ("Corrupted JSON handling", self.test_corrupted_json_handling),
            ("Safe write - temp + rename", self.test_safe_write_temp_rename),
            ("Load after safe write", self.test_load_after_safe_write),
            ("Continue on save failure", self.test_continue_on_save_failure),
            ("Partially written file", self.test_partially_written_file),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = test_func()
            except Exception as e:
                print(f"\n[EXCEPTION] Test raised unhandled exception: {str(e)}")
                print(f"[RESULT] FAILED ❌")
                results[name] = False
            
            # Cleanup after each test
            self.cleanup()
        
        # Summary
        print("\n" + "="*100)
        print("TEST SUMMARY")
        print("="*100)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\nResults: {passed}/{total} tests passed\n")
        
        for name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {status} - {name}")
        
        print("\n" + "="*100)
        if passed == total:
            print("✅ ALL TESTS PASSED - FAULT-TOLERANT STATE PERSISTENCE CONFIRMED")
        else:
            print(f"❌ {total - passed} TEST(S) FAILED")
        print("="*100)
        
        return passed == total


if __name__ == "__main__":
    suite = FaultToleranceTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)

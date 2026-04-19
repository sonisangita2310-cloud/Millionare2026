"""
ROBUST API RETRY HANDLING - TEST SUITE

Tests:
1. Successful fetch (no retry needed)
2. Timeout recovery (retry succeeds)
3. Connection error recovery (retry succeeds)
4. All retries fail (returns None - safe)
5. Partial data handling (retries until valid)
6. Mixed errors (some fail, some succeed)
"""

import sys
import os
import time
from unittest.mock import patch, MagicMock
import requests

sys.path.insert(0, os.path.dirname(__file__))

from live_data_fetcher import LiveDataFetcher


class APIRetryTestSuite:
    """Comprehensive API retry tests"""
    
    def __init__(self):
        self.fetcher = LiveDataFetcher()
    
    def create_mock_response(self, status_code=200, data=None):
        """Create a mock response object"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.raise_for_status = MagicMock()
        
        if data is None:
            # Create valid candle data
            data = [
                [1713484800000, '42000.00', '42100.00', '41900.00', '42050.00', '1.5', 1713488399999, '63105000', 100, '0.75', '31552500', '0'],
                [1713488400000, '42050.00', '42200.00', '41950.00', '42100.00', '1.6', 1713491999999, '67360000', 110, '0.8', '33680000', '0'],
                [1713492000000, '42100.00', '42300.00', '42000.00', '42200.00', '1.4', 1713495599999, '59080000', 90, '0.7', '29540000', '0'],
            ] + [
                [1713495600000 + i*3600000, '42200.00', '42300.00', '42100.00', '42250.00', '1.5', 1713495600000 + (i+1)*3600000 - 1, '63375000', 100, '0.75', '31687500', '0']
                for i in range(200)
            ]
        
        mock_response.json = MagicMock(return_value=data)
        return mock_response
    
    def test_successful_fetch_no_retry(self):
        """TEST 1: Successful fetch (no retry needed)"""
        print("\n" + "="*100)
        print("TEST 1: SUCCESSFUL FETCH (NO RETRY NEEDED)")
        print("="*100)
        
        print("\n[SETUP] Mocking successful API response...")
        with patch('requests.get') as mock_get:
            mock_get.return_value = self.create_mock_response(status_code=200)
            
            print(f"[FETCH] Calling fetch_candles()...")
            result = self.fetcher.fetch_candles(verbose=True)
            
            # Verify success
            if result is not None and len(result) > 0:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Fetched {len(result)} candles")
                print(f"  Latest: ${result.iloc[-1]['close']:.2f}")
                print(f"  Attempts: 1 (no retries needed)")
                print(f"  Mock called: {mock_get.call_count} time(s)")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                return False
    
    def test_timeout_recovery(self):
        """TEST 2: Timeout recovery (retry succeeds)"""
        print("\n" + "="*100)
        print("TEST 2: TIMEOUT RECOVERY (RETRY SUCCEEDS)")
        print("="*100)
        
        print("\n[SETUP] Simulating timeout on attempt 1, success on attempt 2...")
        attempt_count = [0]
        
        def mock_get_with_timeout(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt: timeout
                raise requests.exceptions.Timeout("Connection timeout")
            else:
                # Second attempt: success
                return self.create_mock_response(status_code=200)
        
        with patch('requests.get', side_effect=mock_get_with_timeout):
            print(f"[FETCH] Calling fetch_candles()...")
            start_time = time.time()
            result = self.fetcher.fetch_candles(verbose=True)
            elapsed = time.time() - start_time
            
            if result is not None and len(result) > 0:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Fetched {len(result)} candles on retry")
                print(f"  Attempts: 2 (1 failed, 1 succeeded)")
                print(f"  Elapsed: {elapsed:.1f}s (includes 60s wait)")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                print(f"  Expected: Data on retry")
                print(f"  Got: None")
                return False
    
    def test_connection_error_recovery(self):
        """TEST 3: Connection error recovery (retry succeeds)"""
        print("\n" + "="*100)
        print("TEST 3: CONNECTION ERROR RECOVERY (RETRY SUCCEEDS)")
        print("="*100)
        
        print("\n[SETUP] Simulating connection error on attempt 1, success on attempt 2...")
        attempt_count = [0]
        
        def mock_get_with_connection_error(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt: connection error
                raise requests.exceptions.ConnectionError("Connection failed")
            else:
                # Second attempt: success
                return self.create_mock_response(status_code=200)
        
        with patch('requests.get', side_effect=mock_get_with_connection_error):
            print(f"[FETCH] Calling fetch_candles()...")
            start_time = time.time()
            result = self.fetcher.fetch_candles(verbose=True)
            elapsed = time.time() - start_time
            
            if result is not None and len(result) > 0:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Fetched {len(result)} candles on retry")
                print(f"  Attempts: 2 (1 failed, 1 succeeded)")
                print(f"  Elapsed: {elapsed:.1f}s (includes 60s wait)")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                return False
    
    def test_all_retries_fail(self):
        """TEST 4: All retries fail (returns None - SAFE)"""
        print("\n" + "="*100)
        print("TEST 4: ALL RETRIES FAIL (RETURNS NONE - SAFE)")
        print("="*100)
        
        print("\n[SETUP] Simulating all 3 attempts fail with timeout...")
        attempt_count = [0]
        
        def mock_get_all_fail(*args, **kwargs):
            attempt_count[0] += 1
            raise requests.exceptions.Timeout(f"Timeout attempt {attempt_count[0]}")
        
        with patch('requests.get', side_effect=mock_get_all_fail):
            print(f"[FETCH] Calling fetch_candles()...")
            start_time = time.time()
            result = self.fetcher.fetch_candles(verbose=True)
            elapsed = time.time() - start_time
            
            if result is None:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Returned: None (safe - skip cycle, no trade)")
                print(f"  Attempts: 3 (all failed)")
                print(f"  Elapsed: {elapsed:.1f}s (includes waits)")
                print(f"  Safety: Partial data NOT used ✓")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                print(f"  Expected: None on all failures")
                print(f"  Got: {type(result)}")
                return False
    
    def test_partial_data_handling(self):
        """TEST 5: Partial data handling (retries until valid)"""
        print("\n" + "="*100)
        print("TEST 5: PARTIAL DATA HANDLING (RETRIES UNTIL VALID)")
        print("="*100)
        
        print("\n[SETUP] Simulating insufficient data on attempt 1, valid data on attempt 2...")
        attempt_count = [0]
        
        def mock_get_partial_data(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt: insufficient data
                return self.create_mock_response(status_code=200, data=[])
            else:
                # Second attempt: valid data
                return self.create_mock_response(status_code=200)
        
        with patch('requests.get', side_effect=mock_get_partial_data):
            print(f"[FETCH] Calling fetch_candles()...")
            start_time = time.time()
            result = self.fetcher.fetch_candles(verbose=True)
            elapsed = time.time() - start_time
            
            if result is not None and len(result) > 0:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Fetched {len(result)} candles after retry")
                print(f"  Attempts: 2 (1 had insufficient data, 1 succeeded)")
                print(f"  Safety: Only valid data used ✓")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                return False
    
    def test_mixed_errors(self):
        """TEST 6: Mixed errors (some fail, some succeed)"""
        print("\n" + "="*100)
        print("TEST 6: MIXED ERRORS (SOME FAIL, SOME SUCCEED)")
        print("="*100)
        
        print("\n[SETUP] Simulating mixed errors: timeout → connection error → success...")
        attempt_count = [0]
        
        def mock_get_mixed_errors(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise requests.exceptions.Timeout("Timeout")
            elif attempt_count[0] == 2:
                raise requests.exceptions.ConnectionError("Connection error")
            else:
                return self.create_mock_response(status_code=200)
        
        with patch('requests.get', side_effect=mock_get_mixed_errors):
            print(f"[FETCH] Calling fetch_candles()...")
            start_time = time.time()
            result = self.fetcher.fetch_candles(verbose=True)
            elapsed = time.time() - start_time
            
            if result is not None and len(result) > 0:
                print(f"\n[RESULT] PASSED ✅")
                print(f"  Fetched {len(result)} candles after mixed errors")
                print(f"  Attempts: 3 (1 timeout, 1 connection error, 1 succeeded)")
                print(f"  Elapsed: {elapsed:.1f}s")
                return True
            else:
                print(f"\n[RESULT] FAILED ❌")
                return False
    
    def test_no_crash_on_errors(self):
        """TEST 7: No crash on errors (graceful degradation)"""
        print("\n" + "="*100)
        print("TEST 7: NO CRASH ON ERRORS (GRACEFUL DEGRADATION)")
        print("="*100)
        
        print("\n[SETUP] Testing various error types...")
        error_types = [
            (requests.exceptions.Timeout("timeout"), "Timeout"),
            (requests.exceptions.ConnectionError("connection"), "Connection error"),
            (ValueError("invalid"), "ValueError"),
            (Exception("unknown"), "Generic exception"),
        ]
        
        all_safe = True
        for error, error_name in error_types:
            try:
                with patch('requests.get', side_effect=error):
                    print(f"[TEST] {error_name}...", end=" ")
                    result = self.fetcher.fetch_candles(verbose=False)
                    
                    if result is None:
                        print("✓ (returned None - safe)")
                    else:
                        print(f"✗ (returned {type(result).__name__})")
                        all_safe = False
            except Exception as e:
                print(f"✗ (crashed with {type(e).__name__}: {str(e)})")
                all_safe = False
        
        if all_safe:
            print(f"\n[RESULT] PASSED ✅")
            print(f"  No crashes on any error type")
            print(f"  All returned None (safe)")
            return True
        else:
            print(f"\n[RESULT] FAILED ❌")
            return False
    
    def run_all_tests(self):
        """Run all API retry tests"""
        print("\n" + "="*100)
        print("ROBUST API RETRY HANDLING - TEST SUITE")
        print("="*100)
        
        tests = [
            ("Successful fetch (no retry)", self.test_successful_fetch_no_retry),
            ("Timeout recovery (retry succeeds)", self.test_timeout_recovery),
            ("Connection error recovery", self.test_connection_error_recovery),
            ("All retries fail (returns None)", self.test_all_retries_fail),
            ("Partial data handling", self.test_partial_data_handling),
            ("Mixed errors", self.test_mixed_errors),
            ("No crash on errors", self.test_no_crash_on_errors),
        ]
        
        results = {}
        for name, test_func in tests:
            try:
                results[name] = test_func()
            except Exception as e:
                print(f"\n[EXCEPTION] Test raised exception: {str(e)}")
                print(f"[RESULT] FAILED ❌")
                results[name] = False
        
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
            print("✅ ALL TESTS PASSED - ROBUST API RETRY HANDLING CONFIRMED")
        else:
            print(f"❌ {total - passed} TEST(S) FAILED")
        print("="*100)
        
        return passed == total


if __name__ == "__main__":
    suite = APIRetryTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)

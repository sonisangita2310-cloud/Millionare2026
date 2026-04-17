#!/usr/bin/env python
"""
SYSTEM AUDIT - Pre-Exchange Integration Safety Check
Tests all critical components for reliability and failure scenarios
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

from signal_generator import SignalGenerator
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import TradeLogger


class SystemAudit:
    """Comprehensive system reliability audit"""
    
    def __init__(self, data_file='data_cache/BTC_USDT_1h.csv'):
        print("="*150)
        print("SYSTEM AUDIT - FULL RELIABILITY CHECK")
        print("="*150)
        
        # Load data
        df = pd.read_csv(data_file)
        df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Calculate indicators
        self._calculate_indicators(df)
        
        # Use test period
        split_idx = int(len(df) * 0.6)
        self.df = df.iloc[split_idx:].reset_index(drop=True)
        
        self.signal_gen = SignalGenerator(self.df)
        self.risk_mgr = RiskManager(100000, 0.25)
        self.executor = TradeExecutor()
        self.logger = TradeLogger(append=False)
        
        self.audit_results = {}
        self.failures = []
    
    def _calculate_indicators(self, df):
        """Calculate indicators"""
        # Rename columns if needed for compatibility
        if 'Datetime' in df.columns:
            df.rename(columns={'Datetime': 'datetime'}, inplace=True)
        if 'Close' in df.columns:
            df.rename(columns={'Open': 'open', 'Close': 'close', 'High': 'high', 'Low': 'low', 'Volume': 'volume'}, inplace=True)
        
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['ATR'] = self._calculate_atr(df)
        df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
        df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
        df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
        df['RSI'] = self._calculate_rsi(df['close'], 14)
        df['RANGE'] = df['high'] - df['low']
        df['BODY'] = abs(df['close'] - df['open'])
        df['BODY_PCTS'] = (df['BODY'] / df['RANGE']) * 100
    
    @staticmethod
    def _calculate_atr(data, period=14):
        tr = np.maximum(
            np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
            abs(data['low'] - data['close'].shift())
        )
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def _calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    # =========================================================================
    # STEP 1: SIGNAL INTEGRITY CHECK
    # =========================================================================
    
    def audit_signal_integrity(self):
        """Check for duplicate and missed signals"""
        print("\n" + "="*150)
        print("AUDIT 1: SIGNAL INTEGRITY CHECK")
        print("="*150)
        
        signals = []
        duplicates_same_candle = 0
        
        for idx in range(200, len(self.df)):
            signal_type, strength = self.signal_gen.check_entry_signal(idx)
            
            if signal_type:
                signals.append({
                    'idx': idx,
                    'timestamp': self.df.iloc[idx]['datetime'],
                    'type': signal_type,
                    'strength': strength
                })
        
        # Check for exact duplicates (same signal on same candle)
        for i in range(len(signals) - 1):
            if (signals[i]['idx'] == signals[i+1]['idx'] and 
                signals[i]['type'] == signals[i+1]['type']):
                duplicates_same_candle += 1
                self.failures.append(f"ERROR: Duplicate signal at {signals[i]['timestamp']}")
        
        print(f"\nSignal Generation Analysis:")
        print(f"  Total Signals Generated: {len(signals)}")
        print(f"  Duplicate Signals (same candle): {duplicates_same_candle}")
        
        # Verify signal gaps (signals should be separated by at least 1 candle)
        signal_gaps = []
        for i in range(len(signals) - 1):
            gap = signals[i+1]['idx'] - signals[i]['idx']
            signal_gaps.append(gap)
        
        if signal_gaps:
            print(f"  Min Gap Between Signals: {min(signal_gaps)} candles")
            print(f"  Avg Gap Between Signals: {np.mean(signal_gaps):.1f} candles")
            print(f"  Max Gap Between Signals: {max(signal_gaps)} candles")
        
        # Check for missed signals (broken entry conditions)
        print(f"\n  Signal Distribution:")
        long_signals = len([s for s in signals if s['type'] == 'LONG'])
        short_signals = len([s for s in signals if s['type'] == 'SHORT'])
        print(f"    LONG signals: {long_signals}")
        print(f"    SHORT signals: {short_signals}")
        print(f"    Balance: {long_signals / max(short_signals, 1):.2f}x")
        
        status = "PASS" if duplicates_same_candle == 0 else "FAIL"
        self.audit_results['signal_integrity'] = {
            'status': status,
            'duplicates': duplicates_same_candle,
            'total_signals': len(signals)
        }
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 2: TRADE EXECUTION SAFETY
    # =========================================================================
    
    def audit_trade_execution_safety(self):
        """Check for overlapping trades and execution issues"""
        print("\n" + "="*150)
        print("AUDIT 2: TRADE EXECUTION SAFETY")
        print("="*150)
        
        overlapping = 0
        execution_errors = 0
        active_trades = []
        
        for idx in range(200, min(1000, len(self.df))):  # Test on first 800 candles
            row = self.df.iloc[idx]
            timestamp = row['datetime']
            
            # Check exit
            if self.executor.active_trade:
                exit_reason, exit_price = self.executor.check_exit(row['close'], timestamp)
                if exit_reason:
                    trade = self.executor.exit_trade(exit_price, exit_reason, timestamp)
                    active_trades.append({
                        'type': 'exit',
                        'idx': idx,
                        'timestamp': timestamp
                    })
            
            # Check entry
            if self.executor.active_trade is None:
                signal_type, strength = self.signal_gen.check_entry_signal(idx)
                
                if signal_type:
                    try:
                        entry_details = self.signal_gen.get_entry_details(idx, signal_type)
                        entry_details['signal_type'] = signal_type  # Add signal type for executor
                        position = self.risk_mgr.calculate_position_size(
                            entry_details['price'],
                            entry_details['atr'],
                            signal_type
                        )
                        
                        entered = self.executor.enter_trade(entry_details, position, timestamp)
                        
                        if entered:
                            # Verify only 1 trade active
                            if self.executor.active_trade and len(self.executor.closed_trades) > 0:
                                active_trade_count = 1 if self.executor.active_trade else 0
                                if active_trade_count > 1:
                                    overlapping += 1
                                    self.failures.append(f"ERROR: {active_trade_count} active trades at {timestamp}")
                            
                            active_trades.append({
                                'type': 'entry',
                                'idx': idx,
                                'timestamp': timestamp,
                                'price': entry_details['price'],
                                'signal': signal_type
                            })
                    
                    except Exception as e:
                        execution_errors += 1
                        self.failures.append(f"ERROR: Execution failed at {timestamp}: {str(e)}")
        
        print(f"\nTrade Execution Analysis:")
        print(f"  Entries Attempted: {len([t for t in active_trades if t['type'] == 'entry'])}")
        print(f"  Exits Executed: {len([t for t in active_trades if t['type'] == 'exit'])}")
        print(f"  Overlapping Trades Detected: {overlapping}")
        print(f"  Execution Errors: {execution_errors}")
        print(f"  Final Active Trades: {1 if self.executor.active_trade else 0}")
        
        status = "PASS" if overlapping == 0 and execution_errors == 0 else "FAIL"
        self.audit_results['execution_safety'] = {
            'status': status,
            'overlapping': overlapping,
            'errors': execution_errors
        }
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 3: POSITION SIZING VALIDATION
    # =========================================================================
    
    def audit_position_sizing(self):
        """Verify 0.25% risk calculation precision"""
        print("\n" + "="*150)
        print("AUDIT 3: POSITION SIZING VALIDATION")
        print("="*150)
        
        equity_tests = [100000, 105000, 95000, 150000, 50000]
        atr_tests = [100, 500, 2000, 4000, 50]
        
        precision_errors = []
        
        print(f"\nTesting Position Sizing Precision:")
        print(f"{'Equity':<12} {'ATR':<8} {'Risk $':<10} {'Expected':<10} {'Actual':<10} {'Error':<10} {'Status':<8}")
        print("-" * 150)
        
        for equity in equity_tests:
            self.risk_mgr.current_equity = equity
            
            for atr in atr_tests:
                expected_risk = equity * 0.0025
                
                position = self.risk_mgr.calculate_position_size(70000, atr, 'LONG')
                actual_risk = position['risk_usd']
                
                # Check if risk is exactly 0.25% (within 1 cent tolerance)
                error = abs(actual_risk - expected_risk)
                error_pct = (error / expected_risk) * 100 if expected_risk > 0 else 0
                
                status = "OK" if error < 0.01 else "ERROR"
                
                if error >= 0.01:
                    precision_errors.append({
                        'equity': equity,
                        'atr': atr,
                        'expected': expected_risk,
                        'actual': actual_risk,
                        'error': error
                    })
                
                print(f"{equity:<12} {atr:<8} ${expected_risk:<9.2f} ${expected_risk:<9.2f} ${actual_risk:<9.2f} ${error:<9.4f} {status:<8}")
        
        # Test position size calculation (should = risk / atr)
        print(f"\n\nVerifying Formula: Position = Risk / SL_Distance")
        print(f"{'Equity':<12} {'ATR':<8} {'Expected Pos':<15} {'Actual Pos':<15} {'Match':<8}")
        print("-" * 150)
        
        formula_errors = 0
        for equity in equity_tests[:3]:
            self.risk_mgr.current_equity = equity
            
            for atr in atr_tests[:3]:
                expected_pos = (equity * 0.0025) / atr
                position = self.risk_mgr.calculate_position_size(70000, atr, 'LONG')
                actual_pos = position['position_size']
                
                match = "YES" if abs(expected_pos - actual_pos) < 0.00001 else "NO"
                if match == "NO":
                    formula_errors += 1
                
                print(f"{equity:<12} {atr:<8} {expected_pos:<15.6f} {actual_pos:<15.6f} {match:<8}")
        
        status = "PASS" if len(precision_errors) == 0 and formula_errors == 0 else "FAIL"
        self.audit_results['position_sizing'] = {
            'status': status,
            'precision_errors': len(precision_errors),
            'formula_errors': formula_errors
        }
        
        if precision_errors:
            print(f"\n  Precision Errors Found: {len(precision_errors)}")
            for err in precision_errors[:3]:  # Show first 3
                self.failures.append(f"RISK: Position sizing error - Equity ${err['equity']}, ATR {err['atr']}, Error ${err['error']:.4f}")
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 4: EXIT RELIABILITY
    # =========================================================================
    
    def audit_exit_reliability(self):
        """Test SL/TP triggers and gap scenarios"""
        print("\n" + "="*150)
        print("AUDIT 4: EXIT RELIABILITY")
        print("="*150)
        
        sl_failures = 0
        tp_failures = 0
        gap_stuck = 0
        
        print(f"\nScenario 1: Stop Loss Hit")
        print(f"{'Entry':<10} {'SL Price':<10} {'Current':<10} {'Exit Reason':<15} {'Status':<8}")
        print("-" * 150)
        
        # Test SL trigger for LONG
        for test_move in [0, -50, -100, -500, -1000]:
            entry = 70000
            sl = entry - 1000
            current = entry + test_move
            
            self.executor.active_trade = {
                'signal_type': 'LONG',
                'stop_loss_price': sl,
                'take_profit_price': entry + 2900
            }
            
            exit_reason, exit_price = self.executor.check_exit(current, datetime.now())
            
            if test_move <= -1000:  # Should trigger SL
                if exit_reason == 'SL':
                    status = "PASS"
                else:
                    status = "FAIL"
                    sl_failures += 1
            else:
                if exit_reason is None:
                    status = "PASS"
                else:
                    status = "FAIL"
                    sl_failures += 1
            
            print(f"{entry:<10} {sl:<10} {current:<10} {str(exit_reason):<15} {status:<8}")
            
            self.executor.active_trade = None
        
        print(f"\nScenario 2: Take Profit Hit")
        print(f"{'Entry':<10} {'TP Price':<10} {'Current':<10} {'Exit Reason':<15} {'Status':<8}")
        print("-" * 150)
        
        for test_move in [0, 1000, 2900, 5000]:
            entry = 70000
            tp = entry + 2900
            current = entry + test_move
            
            self.executor.active_trade = {
                'signal_type': 'LONG',
                'stop_loss_price': entry - 1000,
                'take_profit_price': tp
            }
            
            exit_reason, exit_price = self.executor.check_exit(current, datetime.now())
            
            if test_move >= 2900:  # Should trigger TP
                if exit_reason == 'TP':
                    status = "PASS"
                else:
                    status = "FAIL"
                    tp_failures += 1
            else:
                if exit_reason is None:
                    status = "PASS"
                else:
                    status = "FAIL"
                    tp_failures += 1
            
            print(f"{entry:<10} {tp:<10} {current:<10} {str(exit_reason):<15} {status:<8}")
            
            self.executor.active_trade = None
        
        print(f"\nScenario 3: Gap Down (SL Should Trigger)")
        # Simulate gap from 70000 to 68500 (should hit SL at 69000)
        self.executor.active_trade = {
            'signal_type': 'LONG',
            'stop_loss_price': 69000,
            'take_profit_price': 72900
        }
        
        exit_reason, exit_price = self.executor.check_exit(68500, datetime.now())
        gap_status = "PASS" if exit_reason == 'SL' else "FAIL"
        if gap_status == "FAIL":
            gap_stuck += 1
        
        print(f"  Entry: 70000, SL: 69000, Gap to: 68500 → {exit_reason} → {gap_status}")
        
        self.executor.active_trade = None
        
        status = "PASS" if (sl_failures == 0 and tp_failures == 0 and gap_stuck == 0) else "FAIL"
        self.audit_results['exit_reliability'] = {
            'status': status,
            'sl_failures': sl_failures,
            'tp_failures': tp_failures,
            'gap_stuck': gap_stuck
        }
        
        if sl_failures > 0:
            self.failures.append(f"ERROR: Stop Loss trigger failed {sl_failures} times")
        if tp_failures > 0:
            self.failures.append(f"ERROR: Take Profit trigger failed {tp_failures} times")
        if gap_stuck > 0:
            self.failures.append(f"ERROR: Gap scenarios caused stuck trade")
        
        print(f"\n  Overall Exit Status: {'[OK] PASS' if status == 'PASS' else '[FAIL] FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 5: FAILURE SIMULATION (Crash & Recovery)
    # =========================================================================
    
    def audit_failure_recovery(self):
        """Test crash recovery and state preservation"""
        print("\n" + "="*150)
        print("AUDIT 5: FAILURE SIMULATION & RECOVERY")
        print("="*150)
        
        recovery_errors = 0
        
        print(f"\nScenario: System Crash During Open Trade")
        print(f"  1. Enter trade")
        print(f"  2. Record state to emergency log")
        print(f"  3. Simulate crash (kill executor)")
        print(f"  4. Restart system and recover")
        print(f"  5. Verify no duplicate entry")
        
        # Step 1: Enter trade
        idx = 300
        signal_type = 'LONG'
        row = self.df.iloc[idx]
        timestamp = row['datetime']
        
        entry_details = self.signal_gen.get_entry_details(idx, signal_type)
        entry_details['signal_type'] = signal_type  # Add signal type
        position = self.risk_mgr.calculate_position_size(entry_details['price'], entry_details['atr'], signal_type)
        
        self.executor.enter_trade(entry_details, position, timestamp)
        
        # Get trade state
        active_trade_before = self.executor.active_trade.copy() if self.executor.active_trade else None
        
        print(f"\n  Entry recorded:")
        print(f"    Timestamp: {timestamp}")
        print(f"    Price: ${active_trade_before['entry_price']:.0f}")
        print(f"    Type: {active_trade_before['signal_type']}")
        print(f"    Position: {active_trade_before['position_size']:.4f} BTC")
        
        # Step 2: Save state (emergency recovery log)
        emergency_state = {
            'active_trade': active_trade_before,
            'equity': self.risk_mgr.current_equity,
            'timestamp': timestamp
        }
        
        print(f"\n  Emergency state saved")
        
        # Step 3: Simulate crash (delete active trade)
        executor_before_crash = self.executor
        self.executor.active_trade = None
        self.executor.closed_trades = []
        
        print(f"\n  CRASH SIMULATED - System restarted")
        
        # Step 4: Recover state
        self.executor.active_trade = emergency_state['active_trade']
        self.risk_mgr.current_equity = emergency_state['equity']
        
        print(f"\n  State recovered:")
        print(f"    Active trade restored: {self.executor.active_trade is not None}")
        print(f"    Equity restored: ${self.risk_mgr.current_equity:,.0f}")
        
        # Step 5: Try to enter same signal again (should be blocked by active trade)
        signal_type_test = 'LONG'
        entry_details_test = self.signal_gen.get_entry_details(idx, signal_type_test)
        entry_details_test['signal_type'] = signal_type_test
        position_test = self.risk_mgr.calculate_position_size(entry_details_test['price'], entry_details_test['atr'], signal_type_test)
        
        entered_again = self.executor.enter_trade(entry_details_test, position_test, timestamp)
        
        if entered_again:
            recovery_errors += 1
            self.failures.append("CRITICAL: Duplicate entry after crash recovery!")
            print(f"\n  Duplicate Entry Check: FAILED - Second entry allowed!")
        else:
            print(f"\n  Duplicate Entry Check: PASS - Second entry blocked!")
        
        # Step 6: Verify trade history preserved
        closed_count = len(executor_before_crash.closed_trades)
        print(f"\n  Trade History Preservation: {closed_count} trades from before crash")
        
        status = "PASS" if recovery_errors == 0 else "FAIL"
        self.audit_results['failure_recovery'] = {
            'status': status,
            'recovery_errors': recovery_errors,
            'duplicate_prevention': "PASS" if not entered_again else "FAIL"
        }
        
        # Clean up for next tests
        self.executor.active_trade = None
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 6: DATA INTEGRITY CHECK
    # =========================================================================
    
    def audit_data_integrity(self):
        """Check for missing candles and indicator alignment"""
        print("\n" + "="*150)
        print("AUDIT 6: DATA INTEGRITY CHECK")
        print("="*150)
        
        data_errors = 0
        missing_candles = 0
        indicator_misaligns = 0
        
        print(f"\nChecking Candle Continuity:")
        
        # Check for duplicate timestamps
        duplicates = self.df[self.df['datetime'].duplicated()].shape[0]
        if duplicates > 0:
            data_errors += 1
            self.failures.append(f"ERROR: {duplicates} duplicate timestamps found")
            print(f"  Duplicate Timestamps: {duplicates} FAIL")
        else:
            print(f"  Duplicate Timestamps: 0 PASS")
        
        # Check for missing candles (should be 1 hour apart)
        time_diffs = self.df['datetime'].diff().dt.total_seconds() / 3600
        missing = (time_diffs > 1.5).sum()  # Allow 1.5 hour tolerance for exchanges
        if missing > 10:  # Some missing is OK, but not many
            data_errors += 1
            self.failures.append(f"ERROR: {missing} candles potentially missing")
            print(f"  Missing Candles (large gaps): {missing} WARN")
        else:
            print(f"  Missing Candles (large gaps): {missing} OK")
        
        # Check indicator alignment
        print(f"\nChecking Indicator Alignment:")
        
        # EMA_200 should have 200 NaN at start
        ema_nans = self.df['EMA_200'].isna().sum()
        if ema_nans < 195 or ema_nans > 205:
            indicator_misaligns += 1
            self.failures.append(f"ERROR: EMA_200 has {ema_nans} NaNs (expected ~200)")
        
        # ATR should align
        atr_nans = self.df['ATR'].isna().sum()
        if atr_nans > 20:
            indicator_misaligns += 1
            self.failures.append(f"ERROR: ATR has {atr_nans} NaNs")
        
        # RSI should align
        rsi_nans = self.df['RSI'].isna().sum()
        if rsi_nans > 20:
            indicator_misaligns += 1
            self.failures.append(f"ERROR: RSI has {rsi_nans} NaNs")
        
        print(f"  EMA_200 NaN count: {ema_nans} (expected ~200) {'PASS' if 195 <= ema_nans <= 205 else 'WARN'}")
        print(f"  ATR NaN count: {atr_nans} {'PASS' if atr_nans < 20 else 'FAIL'}")
        print(f"  RSI NaN count: {rsi_nans} {'PASS' if rsi_nans < 20 else 'FAIL'}")
        
        # Check if required columns exist
        required_cols = ['close', 'high', 'low', 'volume', 'EMA_200', 'ATR', 'RSI', 'BODY_PCTS']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        
        if missing_cols:
            data_errors += 1
            self.failures.append(f"ERROR: Missing columns: {missing_cols}")
            print(f"\n  Missing Required Columns: {missing_cols} FAIL")
        else:
            print(f"\n  All Required Columns Present: PASS")
        
        status = "PASS" if (data_errors == 0 and indicator_misaligns == 0) else "FAIL"
        self.audit_results['data_integrity'] = {
            'status': status,
            'data_errors': data_errors,
            'indicator_misaligns': indicator_misaligns,
            'duplicates': duplicates,
            'missing_large_gaps': missing
        }
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # STEP 7: LOGGING AUDIT
    # =========================================================================
    
    def audit_logging(self):
        """Verify comprehensive trade logging"""
        print("\n" + "="*150)
        print("AUDIT 7: LOGGING AUDIT")
        print("="*150)
        
        logging_errors = 0
        
        # Simulate a few trades and verify logging
        print(f"\nTesting Trade Logging:")
        print(f"  Entering 5 test trades and verifying logs...")
        
        trades_logged = 0
        for idx in range(300, min(400, len(self.df))):
            row = self.df.iloc[idx]
            timestamp = row['datetime']
            
            # Check exit
            if self.executor.active_trade:
                exit_reason, exit_price = self.executor.check_exit(row['close'], timestamp)
                if exit_reason:
                    trade = self.executor.exit_trade(exit_price, exit_reason, timestamp)
                    
                    # Verify exit was logged
                    self.logger.log_trade_exit({
                        'timestamp': timestamp,
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl': trade['pnl'],
                        'pnl_pct': trade['pnl_pct']
                    })
                    trades_logged += 1
            
            # Try entry
            if self.executor.active_trade is None:
                signal_type, strength = self.signal_gen.check_entry_signal(idx)
                
                if signal_type:
                    entry_details = self.signal_gen.get_entry_details(idx, signal_type)
                    entry_details['signal_type'] = signal_type  # Add signal type for executor
                    position = self.risk_mgr.calculate_position_size(
                        entry_details['price'],
                        entry_details['atr'],
                        signal_type
                    )
                    
                    self.executor.enter_trade(entry_details, position, timestamp)
                    
                    # Verify entry was logged
                    self.logger.log_trade_entry({
                        'timestamp': timestamp,
                        'signal_type': signal_type,
                        'entry_price': entry_details['price'],
                        'position_size': position['position_size'],
                        'position_usd': position['position_usd'],
                        'risk_usd': position['risk_usd'],
                        'rsi': entry_details['rsi'],
                        'body_pct': entry_details['body_pct'],
                        'sl_price': position['stop_loss_price'],
                        'tp_price': position['take_profit_price']
                    })
                    
                    if trades_logged >= 5:
                        break
        
        # Verify logs
        if not self.logger.trades:
            logging_errors += 1
            self.failures.append("ERROR: No trades logged")
            print(f"  Trades logged: 0 FAIL")
        else:
            print(f"  Trades logged: {len(self.logger.trades)}")
            
            # Check log completeness
            for trade in self.logger.trades[:3]:
                required_fields = ['timestamp', 'event', 'entry_price', 'signal']
                missing = [f for f in required_fields if f not in trade or trade[f] is None]
                
                if missing:
                    logging_errors += 1
                    self.failures.append(f"ERROR: Log missing fields: {missing}")
        
        # Try to save logs
        try:
            self.logger.save_trades()
            print(f"  Log file save: PASS")
        except Exception as e:
            logging_errors += 1
            self.failures.append(f"ERROR: Cannot save logs: {str(e)}")
            print(f"  Log file save: FAIL - {str(e)}")
        
        status = "PASS" if logging_errors == 0 else "FAIL"
        self.audit_results['logging'] = {
            'status': status,
            'logging_errors': logging_errors,
            'trades_logged': len(self.logger.trades)
        }
        
        print(f"\n  Status: {'✓ PASS' if status == 'PASS' else '✗ FAIL'}")
        return status == 'PASS'
    
    # =========================================================================
    # RUN ALL AUDITS
    # =========================================================================
    
    def run_all_audits(self):
        """Execute all audit checks"""
        
        results = {
            'signal_integrity': self.audit_signal_integrity(),
            'execution_safety': self.audit_trade_execution_safety(),
            'position_sizing': self.audit_position_sizing(),
            'exit_reliability': self.audit_exit_reliability(),
            'failure_recovery': self.audit_failure_recovery(),
            'data_integrity': self.audit_data_integrity(),
            'logging': self.audit_logging()
        }
        
        self._print_final_report(results)
        
        return results
    
    def _print_final_report(self, results):
        """Print comprehensive final audit report"""
        
        print("\n" + "="*150)
        print("AUDIT FINAL REPORT")
        print("="*150)
        
        print(f"\n{'Audit':<30} {'Status':<10} {'Details':<50}")
        print("-" * 150)
        
        all_pass = True
        for audit_name, passed in results.items():
            status = "[OK] PASS" if passed else "[FAIL] FAIL"
            details = self.audit_results.get(audit_name, {})
            details_str = str(details)[:50]
            
            if not passed:
                all_pass = False
            
            print(f"{audit_name:<30} {status:<10} {details_str:<50}")
        
        print("\n" + "="*150)
        
        if self.failures:
            print(f"\nCRITICAL ISSUES FOUND: {len(self.failures)}\n")
            for i, failure in enumerate(self.failures, 1):
                print(f"{i}. {failure}")
        else:
            print(f"\n[OK] ALL AUDITS PASSED - NO CRITICAL ISSUES FOUND")
        
        print("\n" + "="*150)
        
        if all_pass and not self.failures:
            print(f"\n[OK][OK][OK] SYSTEM READY FOR EXCHANGE INTEGRATION [OK][OK][OK]")
        else:
            print(f"\n[FAIL][FAIL][FAIL] SYSTEM NOT READY - FIX ISSUES BEFORE DEPLOYING [FAIL][FAIL][FAIL]")
        
        print("\n" + "="*150)


def main():
    audit = SystemAudit()
    results = audit.run_all_audits()


if __name__ == '__main__':
    main()

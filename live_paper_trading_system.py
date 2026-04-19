"""
LIVE PAPER TRADING SYSTEM - Real-Time Execution with Binance API

Converts the paper trading simulator to use LIVE market data instead of
preloaded historical data. Processes one 1-hour candle at a time as it
closes on the live market.

STRICT MODE:
- Strategy logic UNCHANGED
- Signal generation UNCHANGED
- Exit rules UNCHANGED
- Position sizing UNCHANGED
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import time
import json

sys.path.insert(0, os.path.dirname(__file__))

from paper_trading_simulator_v2 import PaperTradingSimulatorV2
from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
from live_data_fetcher import LiveDataFetcher


class LivePaperTradingSystem:
    """Live paper trading system with real market data"""
    
    # STRICT MODE: System lock flag for validation phase
    MODE = "VALIDATION"  # Set to "VALIDATION" during Phase 2 - prevents parameter changes
    
    def __init__(self, initial_capital=500, risk_per_trade=0.0025, lookback_candles=200):
        """
        Initialize live trading system
        
        Args:
            initial_capital: Starting capital ($) - Phase 2: $500
            risk_per_trade: Risk per trade as % of equity (0.25%)
            lookback_candles: Number of historical candles for indicators (200)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.lookback_candles = lookback_candles
        
        # Initialize live data fetcher
        self.fetcher = LiveDataFetcher(
            symbol='BTCUSDT',
            interval='1h',
            lookback_candles=lookback_candles
        )
        
        # Initialize signal generator
        self.signal_gen = PullbackSignalGeneratorV35()
        
        # Trading parameters (from PaperTradingSimulatorV2)
        self.sl_mult = 1.1
        self.tp_mult = 3.2
        self.entry_slippage = 0.0003
        self.exit_slippage = 0.0003
        self.entry_fee_pct = 0.001
        self.exit_fee_pct = 0.001
        
        # State
        self.position = None
        self.trades = []
        self.equity_curve = [initial_capital]
        self.rolling_checks = []
        
        # Heartbeat logging
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 300  # 5 minutes
        self.candles_processed = 0
        
        # Data cache for indicator calculations
        self.candle_history = None  # Store fetched candles for indicators
        
        # State persistence
        self.state_file = os.path.join(os.path.dirname(__file__), 'trading_state.json')
        self.last_processed_candle_time = None  # Track last processed candle
        
        # MONITORING & ALERTING
        self.consecutive_losses = 0  # Track consecutive losses for alerts
        self.last_trade_timestamp = None  # Track last trade time for 48h no-trade alert
        self.daily_summary_timestamp = None  # Track daily summary for 24h intervals
        self.max_equity = initial_capital  # Track max equity for drawdown calculation
        self.session_start_timestamp = datetime.now()  # When this session started
        self.journal_file = os.path.join(os.path.dirname(__file__), 'trading_journal.csv')
        self.last_status_print = time.time()  # Track last LIVE STATUS print (every 5 min)
        self.status_print_interval = 300  # 5 minutes
        
        # SESSION TRACKING & AUDIT LOGGING
        self.session_id = self._generate_session_id()  # Timestamp-based unique session ID
        self.audit_log_file = os.path.join(os.path.dirname(__file__), 'config_audit.log')
        
        print("\n" + "="*100)
        print("LIVE PAPER TRADING SYSTEM - PHASE 2 EXTENDED VALIDATION")
        print("="*100)
        
        # Load previous state if exists, otherwise start fresh
        if self._load_state():
            print(f"[STATE LOADED] Resumed from previous session")
            print(f"  Last candle: {self.last_processed_candle_time}")
            print(f"  Equity: ${self.current_capital:,.2f}")
            if self.position is not None:
                print(f"  Open trade: Entry @ ${self.position['entry_price']:,.2f}")
            else:
                print(f"  Open trade: None")
        else:
            print(f"[NEW SESSION] Starting fresh")
        
        print(f"[BOT INITIALIZED] System ready for live trading")
        print(f"Initial capital: ${self.initial_capital:,.0f}")
        print(f"Risk per trade: {self.risk_per_trade*100:.2f}%")
        print(f"Strategy: Pullback v3.5 (NO LOOKAHEAD BIAS)")
        print(f"Data source: LIVE Binance API (BTCUSDT 1H candles)")
        print(f"Status: Waiting for market data...\n")
        
        # Initialize CSV journal
        self._initialize_journal()
        
        # STRICT MODE: Print strategy lock confirmation
        self._print_strategy_lock_confirmation()
        
        # STRICT MODE: Print system mode safety log
        self._print_system_mode_safety_log()
        
        # AUDIT LOGGING: Print and log config hash
        self._print_config_hash()
        self._log_config_hash_to_audit()
        
        # SESSION TRACKING: Print and log session ID
        self._print_session_id()
    
    def _generate_session_id(self):
        """Generate timestamp-based unique session ID"""
        # Format: YYYYMMDD-HHMMSS-microseconds
        now = datetime.now()
        session_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{now.microsecond:06d}"
        return session_id
    
    def _print_session_id(self):
        """Print session ID on startup"""
        print(f"\n[SESSION ID]: {self.session_id}\n")
    
    def _log_config_hash_to_audit(self):
        """Log configuration hash to audit trail file"""
        try:
            config_hash = self._calculate_strategy_hash()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.audit_log_file, 'a') as f:
                f.write(f"[{timestamp}] SESSION_ID: {self.session_id}\n")
                f.write(f"[{timestamp}] CONFIG_HASH: {config_hash}\n")
                f.write(f"[{timestamp}] Strategy: Pullback v3.5\n")
                f.write(f"[{timestamp}] SL: {self.sl_mult}x ATR\n")
                f.write(f"[{timestamp}] TP: {self.tp_mult}x ATR\n")
                f.write(f"[{timestamp}] Risk: {self.risk_per_trade*100:.2f}%\n")
                f.write(f"[{timestamp}] ---\n")
        except Exception as e:
            print(f"[WARNING] Failed to log config hash to audit: {str(e)}")
    
    def _print_config_hash(self):
        """Print config hash on startup"""
        config_hash = self._calculate_strategy_hash()
        print(f"\n[CONFIG HASH]")
        print(f"  Hash: {config_hash}")
        print(f"  Audit Log: config_audit.log\n")
    
    def _initialize_journal(self):
        """Initialize trading journal CSV file"""
        try:
            if not os.path.exists(self.journal_file):
                with open(self.journal_file, 'w') as f:
                    f.write('session_id,timestamp,type,entry_price,exit_price,pnl,equity,result\n')
        except Exception as e:
            print(f"[WARNING] Failed to initialize journal: {str(e)}")
    
    def _log_trade_to_csv(self, trade):
        """Log completed trade to CSV journal"""
        try:
            with open(self.journal_file, 'a') as f:
                result = 'WIN' if trade['winner'] == 1 else 'LOSS'
                f.write(f"{self.session_id},"
                       f"{trade['exit_time']},"
                       f"{trade['exit_type']},"
                       f"{trade['entry_price']:.2f},"
                       f"{trade['exit_price']:.2f},"
                       f"{trade['p_l']:.2f},"
                       f"{self.current_capital:.2f},"
                       f"{result}\n")
        except Exception as e:
            print(f"[WARNING] Failed to log trade to journal: {str(e)}")
    
    def _print_trade_summary(self, trade):
        """Print detailed trade summary after exit"""
        result = "WIN" if trade['winner'] == 1 else "LOSS"
        held_candles = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600
        
        print(f"\n[TRADE SUMMARY]")
        print(f"  Trade #{trade['trade_num']:2d}: {result}")
        print(f"  Type: LONG")
        print(f"  Entry: ${trade['entry_price']:,.2f} @ {trade['entry_time']}")
        print(f"  Exit: ${trade['exit_price']:,.2f} @ {trade['exit_time']} ({trade['exit_type']})")
        print(f"  Duration: {held_candles:.1f} hours")
        print(f"  Position: {trade['position_btc']:.6f} BTC")
        print(f"  P&L: ${trade['p_l']:+.2f}")
        print(f"  Equity: ${self.current_capital:,.2f}")
        print(f"  Consecutive Losses: {self.consecutive_losses}\n")
    
    def _check_health_alerts(self, trade):
        """Check for system health issues and alert"""
        # Update consecutive losses
        if trade['winner'] == 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Alert 1: 3 consecutive losses
        if self.consecutive_losses >= 3:
            print(f"\n[WARNING] {self.consecutive_losses} consecutive losses detected")
            print(f"          Last {self.consecutive_losses} trades all lost. Review signals.\n")
        
        # Alert 2: Drawdown > 5%
        current_drawdown = ((self.max_equity - self.current_capital) / self.max_equity) * 100
        if current_drawdown > 5.0:
            print(f"\n[ALERT] Drawdown threshold exceeded: {current_drawdown:.2f}%")
            print(f"        Max equity: ${self.max_equity:,.2f} | Current: ${self.current_capital:,.2f}\n")
    
    def _print_daily_summary(self):
        """Print daily trading summary"""
        # Filter trades from today
        today = datetime.now().date()
        today_trades = [t for t in self.trades if t['exit_time'].date() == today]
        
        if len(today_trades) == 0:
            print(f"\n[DAILY SUMMARY] {today.strftime('%Y-%m-%d')}")
            print(f"  Trades Today: 0")
            print(f"  Status: No trading activity\n")
            return
        
        winners = sum(1 for t in today_trades if t['winner'] == 1)
        losers = len(today_trades) - winners
        win_rate = (winners / len(today_trades)) * 100 if len(today_trades) > 0 else 0
        
        total_pnl = sum(t['p_l'] for t in today_trades)
        total_wins = sum(t['p_l'] for t in today_trades if t['winner'] == 1)
        total_losses = sum(t['p_l'] for t in today_trades if t['winner'] == 0)
        
        print(f"\n[DAILY SUMMARY] {today.strftime('%Y-%m-%d')}")
        print(f"  Trades Today: {len(today_trades)}")
        print(f"  Wins: {winners} | Losses: {losers}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Net P&L: ${total_pnl:+.2f}")
        print(f"  Current Equity: ${self.current_capital:,.2f}\n")
    
    def _check_no_trades_alert(self):
        """Check if no trades in last 48 hours and alert"""
        if len(self.trades) == 0:
            return  # Haven't had any trades yet
        
        if self.last_trade_timestamp is None:
            return
        
        hours_since_trade = (datetime.now() - self.last_trade_timestamp).total_seconds() / 3600
        
        if hours_since_trade > 48:
            print(f"[INFO] No signals in last {int(hours_since_trade)} hours (threshold: 48h)")
    
    def _print_session_status(self):
        """Print session status on startup"""
        mode = "LIVE PAPER TRADING"
        last_state = "Loaded" if self.last_processed_candle_time is not None else "New"
        
        print(f"\n[SESSION STATUS]")
        print(f"  Mode: {mode}")
        print(f"  Capital: ${self.initial_capital:,.2f}")
        print(f"  Last State: {last_state}")
        print(f"  Strategy: Pullback v3.5 (LOCKED)")
        print(f"  Monitoring: Enabled")
        print(f"  Logging: trading_journal.csv\n")
    
    def _get_strategy_parameters_dict(self):
        """Get key strategy parameters as a dictionary"""
        return {
            'strategy_name': 'Pullback v3.5',
            'sl_multiplier': self.sl_mult,
            'tp_multiplier': self.tp_mult,
            'risk_per_trade': self.risk_per_trade,
            'entry_slippage': self.entry_slippage,
            'exit_slippage': self.exit_slippage,
            'entry_fee_pct': self.entry_fee_pct,
            'exit_fee_pct': self.exit_fee_pct,
            'lookback_candles': self.lookback_candles
        }
    
    def _calculate_strategy_hash(self):
        """Calculate hash of key strategy parameters"""
        import hashlib
        params = self._get_strategy_parameters_dict()
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def _verify_strategy_locked(self):
        """Verify strategy parameters haven't been modified"""
        # Expected parameters for Pullback v3.5 in Phase 2
        expected_params = {
            'strategy_name': 'Pullback v3.5',
            'sl_multiplier': 1.1,
            'tp_multiplier': 3.2,
            'risk_per_trade': 0.0025,
            'entry_slippage': 0.0003,
            'exit_slippage': 0.0003,
            'entry_fee_pct': 0.001,
            'exit_fee_pct': 0.001
        }
        
        current_params = {
            'strategy_name': 'Pullback v3.5',
            'sl_multiplier': self.sl_mult,
            'tp_multiplier': self.tp_mult,
            'risk_per_trade': self.risk_per_trade,
            'entry_slippage': self.entry_slippage,
            'exit_slippage': self.exit_slippage,
            'entry_fee_pct': self.entry_fee_pct,
            'exit_fee_pct': self.exit_fee_pct
        }
        
        # Check if all parameters match
        for key, expected_value in expected_params.items():
            current_value = current_params.get(key)
            # Handle string comparisons separately from numeric comparisons
            if isinstance(expected_value, str):
                if current_value != expected_value:
                    return False, f"{key}: expected {expected_value}, got {current_value}"
            else:
                if abs(current_value - expected_value) > 1e-9:  # Float comparison with tolerance
                    return False, f"{key}: expected {expected_value}, got {current_value}"

        return True, "All parameters locked and verified"
    
    def _print_strategy_lock_confirmation(self):
        """Print strategy lock confirmation on startup"""
        print(f"\n{'='*100}")
        print(f"[STRATEGY LOCKED]")
        print(f"  Strategy: Pullback v3.5")
        print(f"  SL: {self.sl_mult}x ATR")
        print(f"  TP: {self.tp_mult}x ATR")
        print(f"  Risk: {self.risk_per_trade*100:.2f}%")
        print(f"  Entry Slippage: {self.entry_slippage*100:.2f}%")
        print(f"  Exit Slippage: {self.exit_slippage*100:.2f}%")
        print(f"  Entry Fee: {self.entry_fee_pct*100:.2f}%")
        print(f"  Exit Fee: {self.exit_fee_pct*100:.2f}%")
        print(f"{'='*100}\n")
    
    def _print_system_mode_safety_log(self):
        """Print system mode and safety log on startup"""
        print(f"\n{'='*100}")
        print(f"[SYSTEM MODE]")
        print(f"  Phase: {self.MODE}")
        print(f"  Changes Allowed: NO")
        print(f"  Goal: Collect 40+ trades without modification")
        print(f"  Status: System locked - no runtime parameter changes")
        print(f"{'='*100}\n")
    
    def calculate_atr(self, data, period=14):
        """Calculate ATR from OHLC data"""
        if len(data) < period:
            return 0
        
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def _load_state(self):
        """
        Load trading state from JSON file if it exists
        
        FAULT-TOLERANT: Handles corrupted files gracefully
        - If file doesn't exist: return False (new session)
        - If file is corrupted: log error, return False (new session)
        - System NEVER crashes due to state file issues
        
        Returns:
            True if state loaded, False if starting fresh
        """
        if not os.path.exists(self.state_file):
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore state
            self.current_capital = state.get('equity', self.initial_capital)
            self.last_processed_candle_time = state.get('last_processed_candle_time')
            self.candles_processed = state.get('candles_processed', 0)
            self.trades = state.get('trades', [])
            self.equity_curve = state.get('equity_curve', [self.initial_capital])
            self.rolling_checks = state.get('rolling_checks', [])
            
            # Restore open position if exists
            if state.get('open_trade') is not None:
                position_data = state['open_trade']
                # Convert timestamp string back to pandas Timestamp
                position_data['entry_time'] = pd.Timestamp(position_data['entry_time'])
                self.position = position_data
            else:
                self.position = None
            
            return True
        
        except json.JSONDecodeError as e:
            # Corrupted JSON file
            print(f"[STATE ERROR] Corrupted file detected, starting fresh")
            return False
        except Exception as e:
            # Other errors (permission denied, etc.)
            print(f"[STATE ERROR] Failed to load state ({type(e).__name__}), starting fresh")
            return False
    
    def _save_state(self):
        """
        Save trading state to JSON file for crash recovery
        
        FAULT-TOLERANT: Uses atomic writes
        - Write to temp file (.tmp)
        - Then rename to actual file
        - Prevents corruption if write is interrupted
        
        Saves:
        - last_processed_candle_time
        - open_trade (if any)
        - equity
        - all trades
        - equity curve
        """
        try:
            # Prepare position data (convert timestamps to strings for JSON)
            open_trade_data = None
            if self.position is not None:
                open_trade_data = self.position.copy()
                open_trade_data['entry_time'] = str(open_trade_data['entry_time'])
            
            state = {
                'last_processed_candle_time': str(self.last_processed_candle_time) if self.last_processed_candle_time else None,
                'open_trade': open_trade_data,
                'equity': self.current_capital,
                'candles_processed': self.candles_processed,
                'trades': self.trades,
                'equity_curve': self.equity_curve,
                'rolling_checks': self.rolling_checks,
                'timestamp_saved': datetime.now().isoformat(),
            }
            
            # Safe write: Write to temp file first
            temp_file = self.state_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            # Then atomically rename temp file to actual state file
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            os.rename(temp_file, self.state_file)
        
        except Exception as e:
            print(f"[STATE ERROR] Failed to save state, continuing anyway: {str(e)}")
            # Don't crash - continue trading even if state save fails
            # Next restart will start fresh
    
    def _validate_candle_is_closed(self, current_candle, verbose=True):
        """
        DEFENSIVE VALIDATION: Verify candle is actually CLOSED before processing
        
        Checks if: candle_close_time < current_time
        If candle is still forming (close_time >= current_time), skip processing
        
        Args:
            current_candle: The candle to validate (must have 'timestamp')
            verbose: Whether to log validation results
        
        Returns:
            True if candle is CLOSED, False if still FORMING
        """
        
        # Get current system time
        current_time = datetime.now()
        
        # Calculate when this candle closes (timestamp + 1 hour)
        # Candle timestamp is the START time of the 1H period
        candle_close_time = current_candle['timestamp'] + pd.Timedelta(hours=1)
        
        # Validate: Close time must be in the past
        is_closed = candle_close_time < pd.Timestamp(current_time)
        
        if verbose:
            status = "CLOSED" if is_closed else "SKIPPED (still forming)"
            print(f"[CANDLE VALIDATION]")
            print(f"  Current time:       {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Candle period:      {current_candle['timestamp'].strftime('%Y-%m-%d %H:%M')} - {candle_close_time.strftime('%H:%M')}")
            print(f"  Candle close time:  {candle_close_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Status:             {status}")
            if not is_closed:
                seconds_until_close = (candle_close_time - pd.Timestamp(current_time)).total_seconds()
                print(f"  Seconds until close: {int(seconds_until_close)}s")
        
        return is_closed
    
    def get_signal(self, data):
        """Generate entry signal using signal generator (NO LOOKAHEAD)"""
        try:
            if data is None or len(data) < 50:
                return 0
            
            # Use signal generator on indexed data
            data_indexed = data.set_index('timestamp')
            signals = self.signal_gen.generate_signals(data_indexed)
            
            return signals['signal'].iloc[-1] if len(signals) > 0 else 0
        except Exception as e:
            print(f"[ERROR] Signal generation failed: {str(e)}")
            return 0
    
    def calculate_rolling_metrics(self, last_n_trades=10):
        """Calculate metrics for rolling window of trades"""
        if len(self.trades) < last_n_trades:
            return None
        
        recent_trades = self.trades[-last_n_trades:]
        trades_df = pd.DataFrame(recent_trades)
        
        winners = trades_df[trades_df['winner'] == 1]
        losers = trades_df[trades_df['winner'] == 0]
        
        total_win = winners['p_l'].sum() if len(winners) > 0 else 0
        total_loss = abs(losers['p_l'].sum()) if len(losers) > 0 else 1
        pf = total_win / total_loss if total_loss > 0 else 0
        wr = (len(winners) / len(trades_df) * 100) if len(trades_df) > 0 else 0
        
        # Calculate drawdown for rolling window
        equity_slice = self.equity_curve[-(last_n_trades+1):]
        equity_array = np.array(equity_slice)
        running_max = np.maximum.accumulate(equity_array)
        drawdown_pct = ((equity_array - running_max) / running_max) * 100
        max_dd = np.min(drawdown_pct)
        
        return {
            'trades': len(recent_trades),
            'winners': len(winners),
            'pf': pf,
            'wr': wr,
            'max_dd': max_dd,
            'total_pnl': total_win + total_loss,
        }
    
    def evaluate_health_status(self, metrics):
        """Evaluate performance health and return status"""
        if metrics is None:
            return "PENDING"
        
        pf = metrics['pf']
        wr = metrics['wr']
        
        # Critical: Both PF < 0.8 AND WR < 25%
        if pf < 0.8 and wr < 25:
            return "CRITICAL"
        # Warning: Either PF < 1.0 OR WR < 25%
        elif pf < 1.0 or wr < 25:
            return "WARNING"
        # Healthy: PF >= 1.0 AND WR >= 25%
        else:
            return "HEALTHY"
    
    def print_rolling_check(self, metrics):
        """Print rolling performance check"""
        if metrics is None:
            return
        
        status = self.evaluate_health_status(metrics)
        status_symbol = "[OK]" if status == "HEALTHY" else ("[WARN]" if status == "WARNING" else "[CRITICAL]")
        
        print(f"\n{status_symbol} ROLLING CHECK @ Trade #{len(self.trades)} (Last 10 trades)")
        print(f"  Win Rate: {metrics['wr']:.1f}% (target: 30%+)")
        print(f"  PF: {metrics['pf']:.2f}x (target: 1.0x+)")
        print(f"  Max DD: {metrics['max_dd']:.2f}% (target: <5%)")
        print(f"  P&L: ${metrics['total_pnl']:+.2f}")
        print(f"  STATUS: {status}\n")
    
    def _check_heartbeat(self, verbose):
        """Print heartbeat every 5 minutes"""
        now = time.time()
        if now - self.last_heartbeat >= self.heartbeat_interval:
            if verbose:
                equity = self.current_capital
                trades = len(self.trades)
                print(f"[BOT ALIVE] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"Equity: ${equity:,.2f} | Trades: {trades} | Candles: {self.candles_processed}")
            self.last_heartbeat = now
    
    def _print_live_status(self, verbose, next_candle_seconds=None):
        """Print clean LIVE STATUS display every 5 minutes (visibility-only)"""
        now = time.time()
        if now - self.last_status_print < self.status_print_interval:
            return  # Not time yet
        
        if not verbose:
            return
        
        # Get last signal and trade info
        last_signal_str = "None"
        last_trade_str = "None"
        
        if len(self.trades) > 0:
            last_trade = self.trades[-1]
            result = "WIN" if last_trade['winner'] == 1 else "LOSS"
            pnl_str = f"{last_trade['p_l']:+.2f}"
            last_trade_str = f"{last_trade['exit_type']} {result} (${pnl_str})"
        
        # Calculate position status
        position_str = "NONE"
        if self.position is not None:
            position_str = f"OPEN @ ${self.position['entry_price']:.2f}"
        
        # Time to next candle
        next_candle_str = "unknown"
        if next_candle_seconds is not None:
            mins = int(next_candle_seconds // 60)
            secs = int(next_candle_seconds % 60)
            next_candle_str = f"{mins}m {secs}s"
        
        # Print clean status
        print(f"\n{'='*80}")
        print(f"[LIVE STATUS] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"  Equity: ${self.current_capital:>12,.2f}  |  Trades: {len(self.trades):>3}  |  Candles: {self.candles_processed:>4}")
        print(f"  Position: {position_str:<30} |  Last Trade: {last_trade_str:<30}")
        print(f"  Next Candle: {next_candle_str:<25} |  System Status: RUNNING")
        print(f"{'='*80}\n")
        
        self.last_status_print = now
    
    def run_live_trading(self, verbose=True):
        """
        Main live trading loop
        
        while True:
            - Fetch latest candles from Binance
            - Detect if new candle has closed
            - Process only the latest closed candle
            - Check exits (SL/TP)
            - Check entries (signals)
            - Wait for next candle
        """
        
        # STRICT MODE: Verify strategy is locked before starting
        is_locked, lock_message = self._verify_strategy_locked()
        if not is_locked:
            print(f"\n{'='*100}")
            print(f"[CRITICAL] Strategy parameters modified - STOP execution")
            print(f"[CRITICAL] {lock_message}")
            print(f"[CRITICAL] System cannot proceed with modified parameters")
            print(f"{'='*100}\n")
            return  # Exit immediately
        
        print(f"[STRATEGY VERIFIED] All parameters locked and valid")
        # AUDIT: Log session start to audit trail
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.audit_log_file, 'a') as f:
                f.write(f"[{timestamp}] SESSION_START: {self.session_id}\n")
        except Exception:
            pass  # Fail silently
        
        print(f"[BOT STARTED] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - LIVE TRADING ACTIVE")
        
        # Print session status
        self._print_session_status()
        
        # Initialize daily summary timestamp
        self.daily_summary_timestamp = datetime.now()
        
        # STRICT MODE: Verify MODE is set to VALIDATION
        if self.MODE != "VALIDATION":
            print(f"\n[WARNING] System MODE is not set to VALIDATION")
            print(f"[WARNING] Current MODE: {self.MODE}")
            print(f"[WARNING] System should be locked during Phase 2 validation\n")
        else:
            print(f"[MODE CONFIRMED] System is in VALIDATION mode - No changes allowed\n")
        
        try:
            while True:
                # Heartbeat
                self._check_heartbeat(verbose)
                
                # LIVE STATUS - Clean display every 5 minutes (visibility-only)
                wait_until_next = self.fetcher.get_time_until_next_candle(verbose=False)
                self._print_live_status(verbose, next_candle_seconds=wait_until_next)
                
                # Fetch latest candles from Binance (with robust retry)
                # Returns None if all retries fail - safe: skip cycle, don't trade
                df = self.fetcher.fetch_candles(verbose=verbose)
                
                if df is None:
                    # API failed after retries - SKIP CYCLE, DO NOT TRADE
                    # Log message already printed by fetcher
                    if verbose:
                        print(f"[SKIP CYCLE] API failed, waiting before next attempt...\n")
                    time.sleep(60)  # Wait before next cycle
                    continue
                
                # Check if new candle has closed
                if not self.fetcher.is_new_candle(df):
                    if verbose and self.candles_processed % 10 == 0:
                        print(f"[CHECK] No new candle yet, waiting... ({datetime.now().strftime('%H:%M:%S')})")
                    time.sleep(30)  # Check every 30 seconds
                    continue
                
                # New candle detected - validate before processing
                current_candle = df.iloc[-1]
                
                # DEFENSIVE: Verify candle is actually CLOSED (not forming)
                if not self._validate_candle_is_closed(current_candle, verbose=verbose):
                    if verbose:
                        print(f"[WARNING] Candle validation failed - skipping partially formed candle\n")
                    time.sleep(30)  # Check again in 30 seconds
                    continue
                
                # Update history and mark as processed
                self.candle_history = df.copy()
                self.candles_processed += 1
                self.last_processed_candle_time = current_candle['timestamp']
                
                if verbose:
                    print(f"[CANDLE] New 1H candle closed @ {current_candle['timestamp']}")
                    print(f"         Close: ${current_candle['close']:8,.2f} | "
                          f"Volume: {current_candle['volume']:,.0f} BTC")
                    print()  # Blank line for readability
                
                # PROCESS EXITS (Check SL and TP)
                if self.position is not None:
                    current_price = current_candle['close']
                    
                    # Check Stop Loss
                    if current_price <= self.position['stop_loss']:
                        exit_price = self.position['stop_loss'] * (1 - self.exit_slippage)
                        exit_type = 'SL'
                        
                        gross_pnl = (exit_price - self.position['entry_price']) * self.position['position_size_btc']
                        fees = self.position['entry_fee'] + (self.position['position_size_usd'] * self.exit_fee_pct)
                        net_pnl = gross_pnl - fees
                        
                        trade = {
                            'trade_num': len(self.trades) + 1,
                            'entry_time': self.position['entry_time'],
                            'entry_price': self.position['entry_price'],
                            'position_btc': self.position['position_size_btc'],
                            'exit_time': current_candle['timestamp'],
                            'exit_price': exit_price,
                            'exit_type': exit_type,
                            'p_l': net_pnl,
                            'winner': 1 if net_pnl > 0 else 0,
                        }
                        
                        self.current_capital += net_pnl
                        self.equity_curve.append(self.current_capital)
                        self.trades.append(trade)
                        self.position = None
                        self._save_state()  # Persist state after exit
                        
                        # Update max equity for drawdown calculation
                        if self.current_capital > self.max_equity:
                            self.max_equity = self.current_capital
                        
                        # Update last trade timestamp
                        self.last_trade_timestamp = current_candle['timestamp']
                        
                        if verbose:
                            print(f"[TRADE] #{trade['trade_num']:2d}: EXIT {exit_type} | "
                                  f"Entry: ${trade['entry_price']:8,.2f} @ {trade['entry_time']} | "
                                  f"Exit: ${exit_price:8,.2f} | "
                                  f"P&L: ${trade['p_l']:+8.2f} | "
                                  f"Equity: ${self.current_capital:10,.2f}")
                            
                            # Log trade to journal and print summary
                            self._log_trade_to_csv(trade)
                            self._print_trade_summary(trade)
                            self._check_health_alerts(trade)
                        
                        # Rolling check every 10 trades
                        if len(self.trades) % 10 == 0:
                            metrics = self.calculate_rolling_metrics(last_n_trades=10)
                            self.rolling_checks.append(metrics)
                            if verbose:
                                self.print_rolling_check(metrics)
                    
                    # Check Take Profit
                    elif current_price >= self.position['take_profit']:
                        exit_price = self.position['take_profit'] * (1 + self.exit_slippage)
                        exit_type = 'TP'
                        
                        gross_pnl = (exit_price - self.position['entry_price']) * self.position['position_size_btc']
                        fees = self.position['entry_fee'] + (self.position['position_size_usd'] * self.exit_fee_pct)
                        net_pnl = gross_pnl - fees
                        
                        trade = {
                            'trade_num': len(self.trades) + 1,
                            'entry_time': self.position['entry_time'],
                            'entry_price': self.position['entry_price'],
                            'position_btc': self.position['position_size_btc'],
                            'exit_time': current_candle['timestamp'],
                            'exit_price': exit_price,
                            'exit_type': exit_type,
                            'p_l': net_pnl,
                            'winner': 1 if net_pnl > 0 else 0,
                        }
                        
                        self.current_capital += net_pnl
                        self.equity_curve.append(self.current_capital)
                        self.trades.append(trade)
                        self.position = None
                        self._save_state()  # Persist state after exit
                        
                        if verbose:
                            print(f"[TRADE] #{trade['trade_num']:2d}: EXIT {exit_type} | "
                                  f"Entry: ${trade['entry_price']:8,.2f} @ {trade['entry_time']} | "
                                  f"Exit: ${exit_price:8,.2f} | "
                                  f"P&L: ${trade['p_l']:+8.2f} | "
                                  f"Equity: ${self.current_capital:10,.2f}")
                        
                        # Rolling check every 10 trades
                        if len(self.trades) % 10 == 0:
                            metrics = self.calculate_rolling_metrics(last_n_trades=10)
                            self.rolling_checks.append(metrics)
                            if verbose:
                                self.print_rolling_check(metrics)
                        
                        # Update max equity for drawdown calculation
                        if self.current_capital > self.max_equity:
                            self.max_equity = self.current_capital
                        
                        # Update last trade timestamp
                        self.last_trade_timestamp = current_candle['timestamp']
                        
                        if verbose:
                            # Log trade to journal and print summary
                            self._log_trade_to_csv(trade)
                            self._print_trade_summary(trade)
                            self._check_health_alerts(trade)
                
                # PROCESS ENTRIES (Check signals)
                if self.position is None:
                    signal = self.get_signal(df)
                    
                    if signal == 1:
                        # Entry on next candle (wait for next close)
                        entry_price = current_candle['close'] * (1 + self.entry_slippage)
                        
                        # Calculate ATR for position sizing
                        atr = self.calculate_atr(df, period=14)
                        if atr == 0:
                            if verbose:
                                print(f"[SIGNAL] LONG signal detected but ATR=0, skipping entry")
                            signal = 0
                        else:
                            # Position sizing
                            risk_usd = self.current_capital * self.risk_per_trade
                            sl_distance_usd = self.sl_mult * atr
                            position_size_btc = risk_usd / sl_distance_usd
                            position_size_usd = entry_price * position_size_btc
                            entry_fee = position_size_usd * self.entry_fee_pct
                            
                            self.position = {
                                'entry_time': current_candle['timestamp'],
                                'entry_price': entry_price,
                                'position_size_btc': position_size_btc,
                                'position_size_usd': position_size_usd,
                                'entry_fee': entry_fee,
                                'stop_loss': entry_price - (self.sl_mult * atr),
                                'take_profit': entry_price + (self.tp_mult * atr),
                            }
                            self._save_state()  # Persist state after entry
                            
                            if verbose:
                                print(f"[SIGNAL] LONG signal detected @ {current_candle['timestamp']}")
                                print(f"[TRADE] ENTRY | "
                                      f"Price: ${entry_price:8,.2f} | "
                                      f"Position: {position_size_btc:.6f} BTC | "
                                      f"SL: ${self.position['stop_loss']:,.2f} | "
                                      f"TP: ${self.position['take_profit']:,.2f} | "
                                      f"Risk: ${risk_usd:.2f}")
                    else:
                        if verbose and self.candles_processed % 50 == 0:
                            print(f"[SIGNAL] No entry signal @ {current_candle['timestamp']}")
                
                # Save state after candle processing (even if no trades)
                self._save_state()
                
                # Check for daily summary (every 24 hours)
                if self.daily_summary_timestamp is not None:
                    hours_since_summary = (datetime.now() - self.daily_summary_timestamp).total_seconds() / 3600
                    if hours_since_summary >= 24 and verbose:
                        self._print_daily_summary()
                        self.daily_summary_timestamp = datetime.now()
                
                # Check for 48-hour no-trade alert
                self._check_no_trades_alert()
                
                # Wait for next 1-hour candle to close
                # Pass status callback so LIVE STATUS prints every 5 minutes during wait
                wait_seconds = self.fetcher.get_time_until_next_candle(verbose=False)
                if verbose:
                    print(f"[WAIT] Waiting {wait_seconds}s for next candle...\n")
                
                # Call wait with status callback for LIVE STATUS display during wait period
                self.fetcher.wait_for_next_candle(
                    check_interval=30, 
                    verbose=False,
                    status_callback=lambda: self._print_live_status(verbose, wait_seconds),
                    status_callback_interval=self.status_print_interval
                )
        
        except KeyboardInterrupt:
            print(f"\n[BOT STOPPED] Interrupted by user")
        
        except Exception as e:
            print(f"\n[ERROR] Exception in live trading: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.print_final_results()
    
    def print_final_results(self):
        """Print final trading results"""
        print("\n" + "="*100)
        print("LIVE PAPER TRADING RESULTS")
        print("="*100)
        
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print(f"Final capital: ${self.current_capital:,.2f}")
        print(f"Total return: {total_return_pct:+.2f}%")
        print(f"Total candles processed: {self.candles_processed}")
        print(f"Total trades executed: {len(self.trades)}")
        
        if len(self.trades) > 0:
            winners = sum(1 for t in self.trades if t['winner'] == 1)
            losers = len(self.trades) - winners
            win_rate = (winners / len(self.trades)) * 100
            
            total_win = sum(t['p_l'] for t in self.trades if t['winner'] == 1)
            total_loss = sum(t['p_l'] for t in self.trades if t['winner'] == 0)
            
            pf = total_win / abs(total_loss) if total_loss != 0 else 0
            
            print(f"\nTrade statistics:")
            print(f"  Winners: {winners} ({win_rate:.1f}%)")
            print(f"  Losers: {losers} ({100-win_rate:.1f}%)")
            print(f"  Profit factor: {pf:.2f}x")
            print(f"  Winning trades: ${total_win:+.2f}")
            print(f"  Losing trades: ${total_loss:+.2f}")
            print(f"  Average trade: ${(total_win + total_loss) / len(self.trades):+.2f}")
            
            # Drawdown
            equity_array = np.array(self.equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown_pct = ((equity_array - running_max) / running_max) * 100
            max_dd = np.min(drawdown_pct)
            
            print(f"\nRisk metrics:")
            print(f"  Max drawdown: {max_dd:.2f}%")
            
            print(f"\nTrades log:")
            trades_df = pd.DataFrame(self.trades)
            print(trades_df.to_string(index=False))
        
        print("\n" + "="*100)


def main():
    """Main entry point for live paper trading"""
    try:
        # Initialize system
        system = LivePaperTradingSystem(
            initial_capital=500,
            risk_per_trade=0.0025,
            lookback_candles=200
        )
        
        # Run live trading
        system.run_live_trading(verbose=True)
    
    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
PAPER TRADING SIMULATOR v2 - FIXED POSITION SIZING

Issue in v1: Position sizing was calculated incorrectly
- Was using dollars as a multiplier when it should be BTC amount

Fix:
- Position size = risk_amount / (price * sl_multiplier)
- This gives position size in BTC
- P&L = (exit_price - entry_price) * position_size_btc
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import time

sys.path.insert(0, os.path.dirname(__file__))

class PaperTradingSimulatorV2:
    """Paper trading simulator with correct position sizing"""
    
    def __init__(self, data_df, initial_capital=500, risk_per_trade=0.0025):
        """
        Args:
            data_df: DataFrame with OHLCV data
            initial_capital: Starting capital ($) - Phase 2: $500
            risk_per_trade: Risk per trade as % of equity (0.25%)
        """
        self.data = data_df.reset_index(drop=True).copy()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        
        # Trading parameters
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
        
        # Rolling monitoring
        self.rolling_checks = []  # History of every 10-trade check
        
        # Heartbeat logging
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 300  # 5 minutes in seconds
        self.candles_processed = 0
        self.startup_printed = False
        
        # Real-time state tracking
        self.last_processed_idx = -1  # Track last processed candle
        self.next_candle_time = None  # When to expect next candle
        self.last_check_time = time.time()  # For timing between candle checks
    
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
        
        # CRITICAL: Major issues
        if pf < 0.8 or wr < 25:
            return "CRITICAL"
        
        # WARNING: Performance degrading
        if pf < 1.0:
            return "WARNING"
        
        # HEALTHY: Within expected range
        return "HEALTHY"
    
    def print_rolling_check(self, metrics):
        """Print rolling performance check"""
        if metrics is None:
            return
        
        status = self.evaluate_health_status(metrics)
        trade_num = len(self.trades)
        
        # ASCII status symbols (Windows compatible)
        status_symbol = {
            'HEALTHY': '[OK]',
            'WARNING': '[WARN]',
            'CRITICAL': '[CRITICAL]',
            'PENDING': '[.....]'
        }.get(status, '?')
        
        print(f"\n{status_symbol} ROLLING CHECK @ Trade #{trade_num} (Last {metrics['trades']} trades)")
        print(f"  Win Rate: {metrics['wr']:.1f}% (target: 30%+)")
        print(f"  PF: {metrics['pf']:.2f}x (target: 1.0x+)")
        print(f"  Max DD: {metrics['max_dd']:.2f}% (target: <5%)")
        print(f"  P&L: ${metrics['total_pnl']:+.2f}")
        print(f"  STATUS: {status}")
        
        if status == "CRITICAL":
            print(f"  WARNING! Performance severely degraded.")
            print(f"  Consider reviewing signal generation or market conditions.")
        elif status == "WARNING":
            print(f"  WARNING: Profit factor below 1.0x - monitor closely.")
    
    def calculate_atr(self, data_slice, period=14):
        """Calculate ATR for given data slice"""
        if len(data_slice) < period:
            return 0
        tr = np.maximum(
            np.maximum(data_slice['high'] - data_slice['low'], 
                      abs(data_slice['high'] - data_slice['close'].shift())),
            abs(data_slice['low'] - data_slice['close'].shift())
        )
        return tr.rolling(window=period).mean().iloc[-1]
    
    def get_signal(self, candle_idx):
        """Get signal at candle_idx using NO lookahead"""
        if candle_idx < 250:
            return 0
        
        # Use ONLY data up to current candle
        data_slice = self.data.iloc[:candle_idx+1].copy()
        
        from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
        gen = PullbackSignalGeneratorV35()
        
        data_indexed = data_slice.set_index('timestamp')
        signals = gen.generate_signals(data_indexed)
        
        return signals['signal'].iloc[-1] if len(signals) > 0 else 0
    
    def get_latest_candle_idx(self):
        """Get the index of the latest candle (based on current time for real-time mode)"""
        # For real-time mode: find the most recent complete candle
        # In backtest mode with historical data: return next index to process
        current_idx = len(self.data) - 1
        return current_idx
    
    def get_time_until_next_candle(self):
        """Calculate seconds until next 1H candle forms"""
        if len(self.data) == 0:
            return 3600  # 1 hour in seconds
        
        last_candle_time = pd.Timestamp(self.data.iloc[-1]['timestamp'])
        next_candle_time = last_candle_time + pd.Timedelta(hours=1)
        
        # Simulate current time (in real-time mode, this would be datetime.now())
        # For now, use the data timestamps as reference
        current_time = last_candle_time
        
        seconds_until_next = (next_candle_time - current_time).total_seconds()
        return max(1, int(seconds_until_next))  # At least 1 second, cap at next hour
    
    def wait_for_next_candle(self, verbose=False):
        """Wait until the next candle should arrive (in real-time simulation)"""
        # In demo mode: minimal wait (1-2 seconds per candle for realistic feel)
        # In production: would wait actual hours
        
        # For now, return immediately to allow fast backtesting
        # In real-time mode: use the time calculation above
        return True
    
    def run_simulation(self, verbose=True, mode='realtime'):
        """
        Run paper trading with real-time execution
        
        Args:
            verbose: Print execution logs
            mode: 'realtime' (process one candle at a time) or 'backtest' (process all candles)
        """
        
        print("\n" + "="*100)
        if mode == 'realtime':
            print("PAPER TRADING SIMULATOR v2 - REAL-TIME EXECUTION")
        else:
            print("PAPER TRADING SIMULATOR v2 - BACKTEST MODE")
        print("="*100)
        print(f"[BOT STARTED] System initialized successfully")
        print(f"Mode: {mode.upper()}")
        
        # Handle short datasets (< 250 candles)
        start_idx = min(250, len(self.data) // 2)
        end_time = self.data.iloc[-1]['timestamp']
        start_time = self.data.iloc[start_idx]['timestamp'] if start_idx < len(self.data) else self.data.iloc[0]['timestamp']
        
        print(f"Period: {start_time} to {end_time}")
        print(f"Initial capital: ${self.initial_capital:,.0f}")
        print(f"Risk per trade: {self.risk_per_trade*100:.2f}%")
        print(f"Fees: 0.20% per trade (entry + exit)")
        print(f"Strategy: Pullback v3.5 (NO LOOKAHEAD BIAS)")
        print(f"Status: Running continuously...")
        print()
        
        trade_count = 0
        self.last_processed_idx = start_idx - 1
        
        try:
            if mode == 'realtime':
                # Real-time mode: process one candle at a time
                while True:
                    # Get the next candle to process
                    next_idx = self.last_processed_idx + 1
                    
                    # Check if we've reached the end of historical data
                    if next_idx >= len(self.data):
                        print(f"[INFO] Reached end of historical data at {len(self.data)} candles")
                        break
                    
                    # Process this one candle
                    idx = next_idx
                    self.last_processed_idx = idx
                    
                    # Heartbeat logging
                    self._check_heartbeat(verbose)
                    
                    current = self.data.iloc[idx]
                    self.candles_processed += 1
                    
                    # Candle processing log (every 100 candles to reduce spam)
                    if self.candles_processed % 100 == 0 and verbose:
                        print(f"[CANDLE] Processed {self.candles_processed} candles | Time: {current['timestamp']}")
                    
                    # EXECUTE TRADES ON THIS SINGLE CANDLE
                    self._process_single_candle(idx, current, verbose, trade_count)
                    
                    # Wait for next candle (in real-time mode)
                    self.wait_for_next_candle(verbose=False)
            
            else:
                # Backtest mode: original fast processing
                for idx in range(start_idx, len(self.data)):
                    self.last_processed_idx = idx
                    
                    # Heartbeat logging
                    self._check_heartbeat(verbose)
                    
                    current = self.data.iloc[idx]
                    self.candles_processed += 1
                    
                    # Candle processing log (every 100 candles to reduce spam)
                    if self.candles_processed % 100 == 0 and verbose:
                        print(f"[CANDLE] Processed {self.candles_processed} candles | Time: {current['timestamp']}")
                    
                    # EXECUTE TRADES ON THIS CANDLE
                    self._process_single_candle(idx, current, verbose, trade_count)
        
        except Exception as e:
            print(f"\n[ERROR] Exception in run_simulation: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"[RECOVERY] Gracefully shutting down...")
        
        finally:
            print(f"\n[BOT STOPPED] Execution completed")
            print(f"Total candles processed: {self.candles_processed}")
            print(f"Total trades executed: {len(self.trades)}")
        
        return self.get_results()
    
    def _process_single_candle(self, idx, current, verbose, trade_count):
        """Process a single candle: check exits, check entries"""
        
        # Check for exit
        if self.position is not None:
            current_price = current['close']
            
            # Check SL
            if current_price <= self.position['stop_loss']:
                exit_price = self.position['stop_loss'] * (1 - self.exit_slippage)
                exit_type = 'SL'
                
                # Calculate exit (in BTC amounts)
                gross_pnl = (exit_price - self.position['entry_price']) * self.position['position_size_btc']
                fees = self.position['entry_fee'] + (self.position['position_size_usd'] * self.exit_fee_pct)
                net_pnl = gross_pnl - fees
                
                trade = {
                    'trade_num': len(self.trades) + 1,
                    'entry_time': self.position['entry_time'],
                    'entry_price': self.position['entry_price'],
                    'position_btc': self.position['position_size_btc'],
                    'exit_time': current['timestamp'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'p_l': net_pnl,
                    'winner': 1 if net_pnl > 0 else 0,
                }
                
                self.current_capital += net_pnl
                self.equity_curve.append(self.current_capital)
                self.trades.append(trade)
                self.position = None
                
                if verbose:
                    print(f"[TRADE] #{trade['trade_num']:2d}: EXIT {exit_type} | "
                          f"Entry: ${trade['entry_price']:8,.2f} @ {trade['entry_time']} | "
                          f"Exit: ${exit_price:8,.2f} @ {current['timestamp']} | "
                          f"P&L: ${trade['p_l']:+8.2f} | "
                          f"Equity: ${self.current_capital:10,.2f}")
                
                # Rolling performance check every 10 trades
                if len(self.trades) % 10 == 0:
                    metrics = self.calculate_rolling_metrics(last_n_trades=10)
                    self.rolling_checks.append(metrics)
                    if verbose:
                        self.print_rolling_check(metrics)
            
            # Check TP
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
                    'exit_time': current['timestamp'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'p_l': net_pnl,
                    'winner': 1 if net_pnl > 0 else 0,
                }
                
                self.current_capital += net_pnl
                self.equity_curve.append(self.current_capital)
                self.trades.append(trade)
                self.position = None
                
                if verbose:
                    print(f"[TRADE] #{trade['trade_num']:2d}: EXIT {exit_type} | "
                          f"Entry: ${trade['entry_price']:8,.2f} @ {trade['entry_time']} | "
                          f"Exit: ${exit_price:8,.2f} @ {current['timestamp']} | "
                          f"P&L: ${trade['p_l']:+8.2f} | "
                          f"Equity: ${self.current_capital:10,.2f}")
                
                # Rolling performance check every 10 trades
                if len(self.trades) % 10 == 0:
                    metrics = self.calculate_rolling_metrics(last_n_trades=10)
                    self.rolling_checks.append(metrics)
                    if verbose:
                        self.print_rolling_check(metrics)
        
        # Check for entry
        if self.position is None:
            signal = self.get_signal(idx)
            if signal == 1:
                # Entry on next candle
                if idx + 1 < len(self.data):
                    next_candle = self.data.iloc[idx + 1]
                    entry_price = next_candle['open'] * (1 + self.entry_slippage)
                    
                    # Calculate ATR
                    atr = self.calculate_atr(self.data.iloc[:idx+1], period=14)
                    if atr == 0:
                        return
                    
                    # Position sizing (in BTC)
                    risk_usd = self.current_capital * self.risk_per_trade
                    sl_distance_usd = self.sl_mult * atr
                    position_size_btc = risk_usd / sl_distance_usd
                    position_size_usd = entry_price * position_size_btc
                    
                    entry_fee = position_size_usd * self.entry_fee_pct
                    
                    self.position = {
                        'entry_time': next_candle['timestamp'],
                        'entry_price': entry_price,
                        'position_size_btc': position_size_btc,
                        'position_size_usd': position_size_usd,
                        'entry_fee': entry_fee,
                        'stop_loss': entry_price - (self.sl_mult * atr),
                        'take_profit': entry_price + (self.tp_mult * atr),
                    }
                    
                    trade_count += 1
                    if verbose:
                        print(f"[SIGNAL] LONG signal @ {current['timestamp']}")
                        print(f"[TRADE] #{trade_count}: ENTRY | "
                              f"Price: ${entry_price:8,.2f} @ {next_candle['timestamp']} | "
                              f"Position: {position_size_btc:.6f} BTC | "
                              f"SL: ${self.position['stop_loss']:,.2f} | "
                              f"TP: ${self.position['take_profit']:,.2f} | "
                              f"Risk: ${risk_usd:.2f}")
            elif verbose and self.candles_processed % 500 == 0:
                print(f"[SIGNAL] NO SIGNAL @ {current['timestamp']}")
    
    def _check_heartbeat(self, verbose):
        """Print heartbeat message every 5 minutes (or similar interval)"""
        current_time = time.time()
        if current_time - self.last_heartbeat >= self.heartbeat_interval:
            if verbose:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[BOT ALIVE] Time: {timestamp} | Waiting for signal... | "
                      f"Candles: {self.candles_processed} | Trades: {len(self.trades)} | "
                      f"Capital: ${self.current_capital:,.2f}")
            self.last_heartbeat = current_time
    
    def get_results(self):
        """Get performance summary"""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'winners': 0,
                'win_rate': 0,
                'pf': 0,
                'total_return_pct': 0,
                'total_return_usd': 0,
            }
        
        trades_df = pd.DataFrame(self.trades)
        winners = trades_df[trades_df['winner'] == 1]
        losers = trades_df[trades_df['winner'] == 0]
        
        total_win = winners['p_l'].sum() if len(winners) > 0 else 0
        total_loss = abs(losers['p_l'].sum()) if len(losers) > 0 else 1  # Avoid div by 0
        pf = total_win / total_loss if total_loss > 0 else 0
        
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = ((equity_array - running_max) / running_max) * 100
        max_dd = np.min(drawdown)
        
        return {
            'total_trades': len(trades_df),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': (len(winners) / len(trades_df) * 100) if len(trades_df) > 0 else 0,
            'pf': pf,
            'avg_win': winners['p_l'].mean() if len(winners) > 0 else 0,
            'avg_loss': losers['p_l'].mean() if len(losers) > 0 else 0,
            'total_pnl': total_win + total_loss,
            'total_return_usd': self.current_capital - self.initial_capital,
            'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'final_equity': self.current_capital,
            'max_dd_pct': max_dd,
        }
    
    def save_trades_csv(self, filename='paper_trading_log.csv'):
        """Save trades to CSV"""
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(filename, index=False)
        print(f"[SAVED] Trades saved to: {filename}")
    
    def print_rolling_performance_summary(self):
        """Print rolling performance history"""
        if len(self.rolling_checks) == 0:
            return
        
        print("\n" + "="*100)
        print("ROLLING PERFORMANCE HISTORY (Every 10 Trades)")
        print("="*100)
        
        for i, check in enumerate(self.rolling_checks):
            trade_num = (i + 1) * 10
            status = self.evaluate_health_status(check)
            status_symbol = {
                'HEALTHY': '[OK]',
                'WARNING': '[WARN]',
                'CRITICAL': '[CRITICAL]',
            }.get(status, '?')
            
            print(f"\nTrades {trade_num-9}-{trade_num}: {status_symbol} {status}")
            print(f"  WR: {check['wr']:.1f}% | PF: {check['pf']:.2f}x | DD: {check['max_dd']:.2f}% | P&L: ${check['total_pnl']:+.2f}")
        
        # Final summary of rolling checks
        if len(self.rolling_checks) > 0:
            final_check = self.rolling_checks[-1]
            final_status = self.evaluate_health_status(final_check)
            
            if final_status == "CRITICAL":
                print(f"\n[CRITICAL] FINAL STATUS: CRITICAL - Strategy may need adjustment")
            elif final_status == "WARNING":
                print(f"\n[WARN] FINAL STATUS: WARNING - Monitor performance closely")
            else:
                print(f"\n[OK] FINAL STATUS: HEALTHY - Performance within expected range")
    
    def print_results(self):
        """Print summary"""
        results = self.get_results()
        
        print("\n" + "="*100)
        print("RESULTS")
        print("="*100)
        
        if results['total_trades'] == 0:
            print("No trades generated")
            return
        
        print(f"\nTRADES:")
        print(f"  Total: {results['total_trades']}")
        print(f"  Winners: {results['winners']}")
        print(f"  Losers: {results['losers']}")
        print(f"  Win Rate: {results['win_rate']:.1f}%")
        
        print(f"\nPERFORMANCE:")
        print(f"  Profit Factor: {results['pf']:.2f}x")
        print(f"  Avg Winner: ${results['avg_win']:+.2f}")
        print(f"  Avg Loser: ${results['avg_loss']:+.2f}")
        print(f"  Total P&L: ${results['total_pnl']:+.2f}")
        
        print(f"\nRETURN:")
        print(f"  Starting: ${self.initial_capital:,.2f}")
        print(f"  Final: ${results['final_equity']:,.2f}")
        print(f"  P&L: ${results['total_return_usd']:+,.2f}")
        print(f"  Return: {results['total_return_pct']:+.2f}%")
        print(f"  Max DD: {results['max_dd_pct']:.2f}%")
        
        # Compare to backtest
        print(f"\n" + "="*100)
        print(f"COMPARISON TO BACKTEST")
        print(f"="*100)
        print(f"  Backtest (2-year): 37.9% WR, 1.24x PF, +8.38% return")
        print(f"  Paper (73 days): {results['win_rate']:.1f}% WR, {results['pf']:.2f}x PF, {results['total_return_pct']:+.2f}% return")
        
        if results['win_rate'] > 30 and results['pf'] > 0.9:
            print(f"\n[OK] Paper trading performance is GOOD - within expected range")
        elif results['total_trades'] < 5:
            print(f"\n[INFO] Only {results['total_trades']} trades - too few to validate")
        else:
            print(f"\n[WARN] Performance below target - review signals")
        
        # Print rolling performance history
        self.print_rolling_performance_summary()
        
        # Save trades
        self.save_trades_csv()

# Run it
if __name__ == '__main__':
    try:
        data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        # Last 2000 candles for continuous testing
        data_sim = data.iloc[-2000:].reset_index(drop=True)
        
        # Phase 2: $500 starting capital (0.25% risk per trade)
        # Run in REAL-TIME mode (process one candle at a time)
        sim = PaperTradingSimulatorV2(data_sim, initial_capital=500, risk_per_trade=0.0025)
        results = sim.run_simulation(verbose=True, mode='realtime')
        sim.print_results()
    
    except Exception as e:
        print(f"\n[FATAL ERROR] Failed to initialize simulator: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

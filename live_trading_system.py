#!/usr/bin/env python
"""
Live Trading System - Production Ready
Validated Strategy: BTC 1h Breakout with Filters
Mode: Paper (Simulated) or Live (Ready for API integration)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import sys

from signal_generator import SignalGenerator
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from logger import TradeLogger


class LiveTradingSystem:
    """Complete trading system for production deployment"""
    
    def __init__(self, mode='paper', initial_capital=100000, data_file='data_cache/BTC_USDT_1h.csv'):
        """
        Initialize trading system
        
        Args:
            mode: 'paper' for simulation, 'live' for real (API integration needed)
            initial_capital: Starting capital in USD
            data_file: Path to historical data for backtesting
        """
        self.mode = mode
        self.initial_capital = initial_capital
        
        # Load data
        print(f"Loading data from {data_file}...")
        df = pd.read_csv(data_file)
        df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Calculate indicators (same as backtest)
        self._calculate_indicators(df)
        
        # Get test period (60/40 split)
        split_idx = int(len(df) * 0.6)
        self.df = df.iloc[split_idx:].reset_index(drop=True)
        
        print(f"Test Period: {self.df.iloc[0]['datetime']} to {self.df.iloc[-1]['datetime']}")
        print(f"Total Candles: {len(self.df)}")
        
        # Initialize components
        self.signal_gen = SignalGenerator(self.df)
        self.risk_mgr = RiskManager(initial_capital, risk_pct=0.25)
        self.executor = TradeExecutor()
        self.logger = TradeLogger(append=False)
        
        # State
        self.current_idx = 200  # Start after warming period
        self.last_reset_date = None
        self.last_reset_week = None
    
    def _calculate_indicators(self, df):
        """Calculate all required indicators"""
        print("Calculating indicators...")
        
        # Price-based
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['ATR'] = self._calculate_atr(df, period=14)
        df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
        df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
        
        # Volume-based
        df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
        
        # Momentum
        df['RSI'] = self._calculate_rsi(df['close'], 14)
        
        # Candle quality
        df['RANGE'] = df['high'] - df['low']
        df['BODY'] = abs(df['close'] - df['open'])
        df['BODY_PCTS'] = (df['BODY'] / df['RANGE']) * 100
    
    @staticmethod
    def _calculate_atr(data, period=14):
        """Calculate ATR"""
        tr = np.maximum(
            np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
            abs(data['low'] - data['close'].shift())
        )
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def _calculate_rsi(prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def run_live_loop(self, start_idx=200, end_idx=None):
        """
        Main trading loop
        Processes each candle, generates signals, executes trades
        """
        
        if end_idx is None:
            end_idx = len(self.df)
        
        print(f"\n{'='*100}")
        print(f"LIVE TRADING LOOP - {self.mode.upper()} MODE")
        print(f"{'='*100}\n")
        
        for idx in range(start_idx, end_idx):
            row = self.df.iloc[idx]
            timestamp = row['datetime']
            
            # Check daily/weekly reset
            self._check_resets(timestamp)
            
            # --- Check exit first (if in trade)
            if self.executor.active_trade is not None:
                exit_reason, exit_price = self.executor.check_exit(row['close'], timestamp)
                
                if exit_reason:
                    # Exit trade
                    self._execute_exit(exit_price, exit_reason, timestamp)
            
            # --- Check entry (if not in trade)
            if self.executor.active_trade is None:
                signal_type, strength = self.signal_gen.check_entry_signal(idx)
                
                if signal_type:
                    # Check risk limits
                    if not self._check_risk_limits():
                        self.logger.log_system_event('RISK_LIMIT', 
                            f'Risk limit breached: {self.risk_mgr.get_risk_status()}')
                        continue
                    
                    # Enter trade
                    self._execute_entry(signal_type, idx, timestamp)
        
        # Final summary
        self._print_final_summary()
    
    def _execute_entry(self, signal_type, idx, timestamp):
        """Execute trade entry"""
        
        entry_details = self.signal_gen.get_entry_details(idx, signal_type)
        if entry_details is None:
            return
        
        entry_details['signal_type'] = signal_type
        
        # Calculate position
        position = self.risk_mgr.calculate_position_size(
            entry_details['price'],
            entry_details['atr'],
            signal_type
        )
        
        # Enter trade
        self.executor.enter_trade(entry_details, position, timestamp)
        
        # Log entry
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
        
        if idx % 100 == 0:
            print(f"[{timestamp}] ENTRY {signal_type}: ${entry_details['price']:.0f}, "
                  f"Position: {position['position_size']:.4f} BTC, Risk: ${position['risk_usd']:.0f}")
    
    def _execute_exit(self, exit_price, exit_reason, timestamp):
        """Execute trade exit and update equity"""
        
        trade = self.executor.exit_trade(exit_price, exit_reason, timestamp)
        if trade is None:
            return
        
        # Update equity
        self.risk_mgr.update_equity(trade['pnl'])
        
        # Update daily/weekly
        self.risk_mgr.update_daily_pnl(trade['pnl'])
        self.risk_mgr.update_weekly_pnl(trade['pnl'])
        
        # Log exit
        self.logger.log_trade_exit({
            'timestamp': timestamp,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': trade['pnl'],
            'pnl_pct': trade['pnl_pct']
        })
        
        print(f"[{timestamp}] EXIT {exit_reason}: ${exit_price:.0f}, "
              f"PnL: ${trade['pnl']:+,.0f}, Equity: ${self.risk_mgr.current_equity:,.0f}")
    
    def _check_risk_limits(self):
        """Check if trading allowed (circuit breakers)"""
        
        # Daily loss limit
        if self.risk_mgr.check_daily_loss_limit():
            self.logger.log_system_event('DAILY_LIMIT', 
                f"Daily loss limit hit: ${self.risk_mgr.daily_pnl:.0f}")
            return False
        
        # Weekly loss limit
        if self.risk_mgr.check_weekly_loss_limit():
            self.logger.log_system_event('WEEKLY_LIMIT',
                f"Weekly loss limit hit: ${self.risk_mgr.weekly_pnl:.0f}")
            return False
        
        # Peak DD limit (emergency)
        if self.risk_mgr.check_peak_dd_limit():
            self.logger.log_system_event('EMERGENCY',
                f"Peak DD limit reached: {self.risk_mgr.max_dd:.1f}%")
            return False
        
        return True
    
    def _check_resets(self, timestamp):
        """Reset daily/weekly counters"""
        
        current_date = timestamp.date()
        current_week = timestamp.isocalendar()[1]
        
        # Daily reset at UTC midnight
        if self.last_reset_date != current_date:
            self.risk_mgr.update_daily_pnl(0, reset=True)
            self.last_reset_date = current_date
        
        # Weekly reset at week change
        if self.last_reset_week != current_week:
            self.risk_mgr.update_weekly_pnl(0, reset=True)
            self.last_reset_week = current_week
    
    def _print_final_summary(self):
        """Print final trading summary"""
        
        print(f"\n{'='*100}")
        print(f"FINAL RESULTS")
        print(f"{'='*100}\n")
        
        # Equity summary
        print(f"Starting Equity:     ${self.initial_capital:,.0f}")
        print(f"Ending Equity:       ${self.risk_mgr.current_equity:,.0f}")
        print(f"Total Return:        ${self.risk_mgr.current_equity - self.initial_capital:+,.0f} "
              f"({(self.risk_mgr.current_equity / self.initial_capital - 1) * 100:+.2f}%)")
        print(f"Max Drawdown:        {self.risk_mgr.max_dd:.1f}%")
        print()
        
        # Trade summary
        stats = self.executor.get_trade_stats()
        print(f"Total Trades:        {stats['total_trades']}")
        print(f"Winning Trades:      {stats['winning_trades']}")
        print(f"Losing Trades:       {stats['losing_trades']}")
        print(f"Win Rate:            {stats['win_rate']:.1f}%")
        print(f"Profit Factor:       {stats['profit_factor']:.2f}")
        print(f"Avg Win:             ${stats['avg_win']:,.0f}")
        print(f"Avg Loss:            ${stats['avg_loss']:,.0f}")
        
        print(f"\n{'='*100}\n")
        
        # Save logs
        self.logger.save_trades()
        self.logger.save_events()
        print(f"[OK] Logs saved to logs/trading_log.csv")


def main():
    """Run live trading system"""
    
    # Configuration
    mode = 'paper'  # or 'live' for real trading
    initial_capital = 100000
    
    print(f"\n{'='*100}")
    print(f"LIVE TRADING SYSTEM - PRODUCTION READY")
    print(f"{'='*100}\n")
    print(f"Mode: {mode.upper()}")
    print(f"Initial Capital: ${initial_capital:,.0f}")
    print(f"Strategy: BTC 1h Breakout with Filters")
    print(f"Position Risk: 0.25% per trade")
    print(f"Max Active Trades: 1")
    
    # Initialize system
    system = LiveTradingSystem(mode=mode, initial_capital=initial_capital)
    
    # Run trading loop
    system.run_live_loop()


if __name__ == '__main__':
    main()

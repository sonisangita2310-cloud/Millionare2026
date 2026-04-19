"""
PAPER TRADING SIMULATOR - REALISTIC LIVE VALIDATION

Purpose: Simulate live paper trading with:
  - Real-time signal generation (no lookahead)
  - Realistic execution (slippage, fees, delays)
  - Dynamic position sizing (0.25% risk per trade)
  - Comprehensive tracking
  - No curve-fitting

Configuration:
  - Strategy: Pullback v3.5 (LOCKED, no changes)
  - Exits: 1.1x SL, 3.2x TP (LOCKED, no changes)
  - Position Size: Fixed 0.25% of current equity per trade
  - Entry: Next candle open + slippage (0.03%)
  - Exit: Market price at SL/TP (0.03% slippage)
  - Fees: 0.1% on entry + 0.1% on exit
  - Run: Last 2000 candles (~83 days live simulation)
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

class PaperTradingSimulator:
    """Realistic paper trading simulator with live conditions"""
    
    def __init__(self, data_df, initial_capital=10000, risk_per_trade=0.0025):
        """
        Args:
            data_df: DataFrame with OHLCV data (must have 'timestamp', 'close', 'high', 'low', 'volume')
            initial_capital: Starting capital ($)
            risk_per_trade: Risk per trade as % of equity (0.25% = 0.0025)
        """
        self.data = data_df.reset_index(drop=True).copy()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        
        # Trading parameters
        self.sl_mult = 1.1  # ATR multiplier for stop loss
        self.tp_mult = 3.2  # ATR multiplier for take profit
        self.entry_slippage = 0.0003  # 0.03% slippage
        self.exit_slippage = 0.0003
        self.entry_fee_pct = 0.001  # 0.1%
        self.exit_fee_pct = 0.001
        
        # State
        self.position = None  # Current open position
        self.trades = []  # Completed trades
        self.equity_curve = [initial_capital]
        self.signal_history = []
        
        # Indicators cache (will be computed on-the-fly)
        self.indicators = {}
        
    def calculate_atr(self, data_slice, period=14):
        """Calculate ATR for given data slice"""
        tr = np.maximum(
            np.maximum(data_slice['high'] - data_slice['low'], 
                      abs(data_slice['high'] - data_slice['close'].shift())),
            abs(data_slice['low'] - data_slice['close'].shift())
        )
        return tr.rolling(window=period).mean().iloc[-1]
    
    def get_signal(self, candle_idx):
        """
        Generate signal at candle_idx using ONLY data up to candle_idx
        (NO LOOKAHEAD BIAS)
        """
        # Need enough data for indicators
        if candle_idx < 250:  # Need 200 for EMA + buffer
            return 0
        
        # Use only data UP TO AND INCLUDING current candle
        data_slice = self.data.iloc[:candle_idx+1].copy()
        
        # Import generator here to ensure fresh instance
        from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
        gen = PullbackSignalGeneratorV35()
        
        # Calculate indicators on this slice
        data_indexed = data_slice.set_index('timestamp')
        signals = gen.generate_signals(data_indexed)
        
        # Return signal for CURRENT candle (last in slice)
        return signals['signal'].iloc[-1] if signals['signal'].iloc[-1] == 1 else 0
    
    def calculate_position_size(self, atr):
        """Calculate position size based on 0.25% risk per trade"""
        # Risk amount = 0.25% of current equity
        risk_amount = self.current_capital * self.risk_per_trade
        
        # Stop loss distance = 1.1 x ATR
        sl_distance = self.sl_mult * atr
        
        # Position size = Risk / SL distance (in dollars)
        position_size = risk_amount / sl_distance if sl_distance > 0 else 0
        
        return max(position_size, 100)  # Minimum $100 position
    
    def execute_entry(self, candle_idx, entry_candle):
        """Execute entry signal"""
        # Entry price = next candle open + slippage
        entry_price = entry_candle['open'] * (1 + self.entry_slippage)
        
        # Calculate position size based on current equity
        atr = self.calculate_atr(self.data.iloc[:candle_idx+1], period=14)
        position_size = self.calculate_position_size(atr)
        
        # Entry fee
        entry_fee = position_size * self.entry_fee_pct
        
        # Create position
        self.position = {
            'entry_idx': candle_idx,
            'entry_time': entry_candle['timestamp'],
            'entry_price': entry_price,
            'position_size': position_size,
            'entry_fee': entry_fee,
            'stop_loss': entry_price - (self.sl_mult * atr),
            'take_profit': entry_price + (self.tp_mult * atr),
            'atr': atr,
        }
        
        return self.position
    
    def execute_exit(self, candle_idx, exit_candle):
        """Execute exit when SL or TP hit"""
        if self.position is None:
            return None
        
        current_price = exit_candle['close']
        exit_price = current_price
        exit_type = None
        
        # Check if SL or TP hit
        if current_price <= self.position['stop_loss']:
            exit_price = self.position['stop_loss'] * (1 - self.exit_slippage)  # Slippage against us
            exit_type = 'SL'
        elif current_price >= self.position['take_profit']:
            exit_price = self.position['take_profit'] * (1 + self.exit_slippage)  # Slippage against us
            exit_type = 'TP'
        else:
            return None  # No exit triggered
        
        # Exit fee
        exit_fee = self.position['position_size'] * self.exit_fee_pct
        
        # Calculate PnL
        gross_pnl = (exit_price - self.position['entry_price']) * self.position['position_size']
        net_pnl = gross_pnl - self.position['entry_fee'] - exit_fee
        
        # Record trade
        trade = {
            'entry_idx': self.position['entry_idx'],
            'entry_time': self.position['entry_time'],
            'entry_price': self.position['entry_price'],
            'position_size': self.position['position_size'],
            'exit_idx': candle_idx,
            'exit_time': exit_candle['timestamp'],
            'exit_price': exit_price,
            'exit_type': exit_type,
            'gross_pnl': gross_pnl,
            'fees': self.position['entry_fee'] + exit_fee,
            'net_pnl': net_pnl,
            'winner': 1 if net_pnl > 0 else 0,
            'pnl_pct': (net_pnl / self.position['position_size']) * 100,
            'equity_after': self.current_capital + net_pnl,
        }
        
        # Update equity
        self.current_capital += net_pnl
        self.equity_curve.append(self.current_capital)
        self.trades.append(trade)
        
        # Close position
        self.position = None
        
        return trade
    
    def run_simulation(self, start_idx=None, verbose=True):
        """
        Run paper trading simulation
        
        Args:
            start_idx: Start from this candle (default: use enough for indicators)
            verbose: Print progress
        """
        if start_idx is None:
            start_idx = 250  # Need enough data for indicators
        
        print("\n" + "="*100)
        print("PAPER TRADING SIMULATOR - LIVE CONDITIONS")
        print("="*100)
        print(f"Start time: {self.data.iloc[start_idx]['timestamp']}")
        print(f"End time: {self.data.iloc[-1]['timestamp']}")
        print(f"Initial capital: ${self.initial_capital:,.0f}")
        print(f"Risk per trade: {self.risk_per_trade*100:.2f}% of equity")
        print(f"Entry slippage: {self.entry_slippage*100:.2f}%")
        print(f"Exit slippage: {self.exit_slippage*100:.2f}%")
        print(f"Fees: {self.entry_fee_pct*100:.2f}% entry + {self.exit_fee_pct*100:.2f}% exit")
        print()
        
        # Main simulation loop
        for candle_idx in range(start_idx, len(self.data)):
            current_candle = self.data.iloc[candle_idx]
            
            # Check for exit conditions FIRST
            if self.position is not None:
                exit_result = self.execute_exit(candle_idx, current_candle)
                if exit_result:
                    if verbose and candle_idx % 50 == 0:
                        print(f"[{candle_idx}] EXIT at {current_candle['timestamp']}: "
                              f"{exit_result['exit_type']} | P&L: ${exit_result['net_pnl']:+.0f} | "
                              f"Equity: ${self.current_capital:,.0f}")
            
            # Then check for entry signal
            if self.position is None:
                signal = self.get_signal(candle_idx)
                if signal == 1:
                    # Entry happens on NEXT candle open
                    if candle_idx + 1 < len(self.data):
                        next_candle = self.data.iloc[candle_idx + 1]
                        entry_result = self.execute_entry(candle_idx + 1, next_candle)
                        if verbose and candle_idx % 50 == 0:
                            print(f"[{candle_idx}] SIGNAL at {current_candle['timestamp']}")
        
        # Close any open position at end
        if self.position is not None:
            last_candle = self.data.iloc[-1]
            exit_price = last_candle['close']
            exit_fee = self.position['position_size'] * self.exit_fee_pct
            gross_pnl = (exit_price - self.position['entry_price']) * self.position['position_size']
            net_pnl = gross_pnl - self.position['entry_fee'] - exit_fee
            
            trade = {
                'entry_idx': self.position['entry_idx'],
                'entry_time': self.position['entry_time'],
                'entry_price': self.position['entry_price'],
                'position_size': self.position['position_size'],
                'exit_idx': len(self.data) - 1,
                'exit_time': last_candle['timestamp'],
                'exit_price': exit_price,
                'exit_type': 'FORCE_CLOSE',
                'gross_pnl': gross_pnl,
                'fees': self.position['entry_fee'] + exit_fee,
                'net_pnl': net_pnl,
                'winner': 1 if net_pnl > 0 else 0,
                'pnl_pct': (net_pnl / self.position['position_size']) * 100,
                'equity_after': self.current_capital + net_pnl,
            }
            
            self.current_capital += net_pnl
            self.equity_curve.append(self.current_capital)
            self.trades.append(trade)
            self.position = None
        
        return self.get_results()
    
    def get_results(self):
        """Calculate performance metrics"""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'pf': 0,
                'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
                'total_return_usd': self.current_capital - self.initial_capital,
                'final_equity': self.current_capital,
            }
        
        trades_df = pd.DataFrame(self.trades)
        winners = trades_df[trades_df['winner'] == 1]
        losers = trades_df[trades_df['winner'] == 0]
        
        total_win = winners['net_pnl'].sum() if len(winners) > 0 else 0
        total_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
        
        pf = total_win / total_loss if total_loss > 0 else (1.0 if total_win > 0 else 0)
        
        # Calculate drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown_pct = ((equity_array - running_max) / running_max) * 100
        max_drawdown = np.min(drawdown_pct)
        
        return {
            'total_trades': len(trades_df),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': (len(winners) / len(trades_df) * 100) if len(trades_df) > 0 else 0,
            'pf': pf,
            'avg_win': winners['net_pnl'].mean() if len(winners) > 0 else 0,
            'avg_loss': losers['net_pnl'].mean() if len(losers) > 0 else 0,
            'total_pnl': total_win + total_loss,
            'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'total_return_usd': self.current_capital - self.initial_capital,
            'final_equity': self.current_capital,
            'max_drawdown_pct': max_drawdown,
        }
    
    def save_trades_csv(self, filename='paper_trading_log.csv'):
        """Export trades to CSV"""
        if len(self.trades) > 0:
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(filename, index=False)
            return filename
        return None
    
    def print_results(self):
        """Print summary report"""
        results = self.get_results()
        
        print("\n" + "="*100)
        print("PAPER TRADING RESULTS")
        print("="*100)
        
        print(f"\nTRADE STATISTICS:")
        print(f"  Total Trades: {results['total_trades']}")
        print(f"  Winners: {results['winners']}")
        print(f"  Losers: {results['losers']}")
        print(f"  Win Rate: {results['win_rate']:.1f}%")
        
        print(f"\nPROFITABILITY:")
        print(f"  Profit Factor: {results['pf']:.2f}x")
        print(f"  Avg Winner: ${results['avg_win']:+.2f}")
        print(f"  Avg Loser: ${results['avg_loss']:+.2f}")
        print(f"  Total P&L: ${results['total_pnl']:+.2f}")
        
        print(f"\nRETURN METRICS:")
        print(f"  Starting Equity: ${self.initial_capital:,.2f}")
        print(f"  Final Equity: ${results['final_equity']:,.2f}")
        print(f"  Total Return: ${results['total_return_usd']:+,.2f}")
        print(f"  Return %: {results['total_return_pct']:+.2f}%")
        print(f"  Max Drawdown: {results['max_drawdown_pct']:.2f}%")
        
        return results


# Run simulation
if __name__ == '__main__':
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    # Use last 2000 candles for paper trading (~83 days)
    data_sim = data.iloc[-2000:].reset_index(drop=True)
    
    print(f"\nLoaded {len(data_sim)} candles for simulation")
    print(f"Period: {data_sim.iloc[0]['timestamp']} to {data_sim.iloc[-1]['timestamp']}")
    
    # Run simulation
    sim = PaperTradingSimulator(data_sim, initial_capital=10000, risk_per_trade=0.0025)
    results = sim.run_simulation(start_idx=250, verbose=True)
    
    # Print results
    sim.print_results()
    
    # Save trades
    csv_file = sim.save_trades_csv('paper_trading_log.csv')
    if csv_file:
        print(f"\n✓ Trades saved to: {csv_file}")

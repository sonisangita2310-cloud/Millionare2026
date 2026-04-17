"""
Trade Executor - Simulates or executes trades with proper SL/TP exit logic
Handles one trade at a time (validated maximum)
"""

import pandas as pd
import numpy as np
from datetime import datetime


class TradeExecutor:
    """Execute trades with SL/TP exits"""
    
    def __init__(self):
        """Initialize executor"""
        self.active_trade = None  # None or dict with trade info
        self.closed_trades = []   # List of completed trades
    
    def enter_trade(self, entry_details, position_details, timestamp):
        """
        Enter a new trade
        
        Args:
            entry_details: Dict with timestamp, price, rsi, body_pct, etc.
            position_details: Dict with position_size, SL price, TP price, atr, etc.
            timestamp: Entry timestamp
        
        Returns:
            True if trade entered, False if already in trade
        """
        
        if self.active_trade is not None:
            return False  # Already in a trade (max 1 active)
        
        self.active_trade = {
            'entry_timestamp': timestamp,
            'entry_price': entry_details['price'],
            'entry_rsi': entry_details['rsi'],
            'entry_body_pct': entry_details['body_pct'],
            'signal_type': entry_details['signal_type'],
            'position_size': position_details['position_size'],
            'position_usd': position_details['position_usd'],
            'stop_loss_price': position_details['stop_loss_price'],
            'take_profit_price': position_details['take_profit_price'],
            'risk_usd': position_details['risk_usd'],
            'sl_distance': position_details['sl_distance'],
            'tp_distance': position_details['tp_distance'],
            'atr': position_details['atr'],
            'bars_held': 0
        }
        
        return True
    
    def check_exit(self, current_price, current_timestamp):
        """
        Check if trade should exit (SL or TP hit)
        
        Returns:
            ('TP', exit_price) or ('SL', exit_price) or (None, None) if still in trade
        """
        
        if self.active_trade is None:
            return None, None
        
        trade = self.active_trade
        signal_type = trade['signal_type']
        
        # Check exit conditions
        if signal_type == 'LONG':
            if current_price <= trade['stop_loss_price']:
                return 'SL', trade['stop_loss_price']
            elif current_price >= trade['take_profit_price']:
                return 'TP', trade['take_profit_price']
        
        else:  # SHORT
            if current_price >= trade['stop_loss_price']:
                return 'SL', trade['stop_loss_price']
            elif current_price <= trade['take_profit_price']:
                return 'TP', trade['take_profit_price']
        
        # Still in trade
        return None, None
    
    def exit_trade(self, exit_price, exit_reason, exit_timestamp):
        """
        Exit current trade
        
        Args:
            exit_price: Price at exit
            exit_reason: 'SL' or 'TP'
            exit_timestamp: Exit timestamp
        
        Returns:
            Trade record dict with PnL info, or None if no active trade
        """
        
        if self.active_trade is None:
            return None
        
        trade = self.active_trade
        
        # Calculate PnL
        if trade['signal_type'] == 'LONG':
            pnl = (exit_price - trade['entry_price']) * trade['position_size']
        else:  # SHORT
            pnl = (trade['entry_price'] - exit_price) * trade['position_size']
        
        # Create closed trade record
        closed_trade = {
            'entry_timestamp': trade['entry_timestamp'],
            'exit_timestamp': exit_timestamp,
            'entry_price': trade['entry_price'],
            'exit_price': exit_price,
            'signal_type': trade['signal_type'],
            'position_size': trade['position_size'],
            'position_usd': trade['position_usd'],
            'pnl': pnl,
            'pnl_pct': (pnl / trade['risk_usd']) * 100 if trade['risk_usd'] != 0 else 0,
            'exit_reason': exit_reason,
            'entry_rsi': trade['entry_rsi'],
            'entry_body_pct': trade['entry_body_pct'],
            'atr': trade['atr'],
            'bars_held': trade['bars_held']
        }
        
        # Track in history
        self.closed_trades.append(closed_trade)
        
        # Clear active trade
        self.active_trade = None
        
        return closed_trade
    
    def get_active_trade_info(self):
        """Get info about current trade (if any)"""
        return self.active_trade
    
    def get_trade_history(self):
        """Get all closed trades"""
        return pd.DataFrame(self.closed_trades) if self.closed_trades else pd.DataFrame()
    
    def get_trade_stats(self):
        """Calculate summary stats from closed trades"""
        
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_pnl': 0
            }
        
        df = pd.DataFrame(self.closed_trades)
        
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])
        
        wins = df[df['pnl'] > 0]['pnl'].sum()
        losses = abs(df[df['pnl'] < 0]['pnl'].sum())
        pf = wins / losses if losses > 0 else 0
        
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'profit_factor': pf,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': df['pnl'].sum()
        }

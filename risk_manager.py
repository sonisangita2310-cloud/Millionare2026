"""
Risk Manager - Handles position sizing, SL/TP, and risk controls
Enforces 0.25% risk per trade and max 1 active position
"""

import pandas as pd
import numpy as np


class RiskManager:
    """Manage position sizing, stops, and risk limits"""
    
    def __init__(self, starting_equity=100000, risk_pct=0.25):
        """
        Initialize risk manager
        
        Args:
            starting_equity: Initial capital in USD
            risk_pct: Risk per trade as % of current equity (0.25 = 0.25%)
        """
        self.starting_equity = starting_equity
        self.current_equity = starting_equity
        self.peak_equity = starting_equity
        self.risk_pct = risk_pct
        
        # Safety controls
        self.daily_pnl = 0
        self.daily_loss_cap = starting_equity * 0.02  # 2% daily loss cap
        self.weekly_pnl = 0
        self.weekly_loss_cap = starting_equity * 0.05  # 5% weekly loss cap
        self.peak_dd_limit = starting_equity * 0.20  # 20% peak DD cap
        
        # State
        self.active_trade = False
        self.max_dd = 0
    
    def calculate_position_size(self, entry_price, atr, signal_type):
        """
        Calculate position size using 0.25% risk rule
        
        Position Size = (Equity × 0.0025) / SL_Distance
        
        Args:
            entry_price: Entry price in USD
            atr: ATR value (stop loss distance)
            signal_type: 'LONG' or 'SHORT'
        
        Returns:
            {
                'position_size': BTC amount,
                'position_usd': Notional USD value,
                'stop_loss_price': SL price
                'take_profit_price': TP price,
                'risk_usd': Max loss if SL hits
            }
        """
        
        # SL distance = 1.0 × ATR (validated)
        sl_distance = atr * 1.0
        
        # TP distance = 2.9 × ATR (validated)
        tp_distance = atr * 2.9
        
        # Position size = (equity × 0.0025) / SL_distance
        risk_usd = self.current_equity * (self.risk_pct / 100.0)
        position_size = risk_usd / sl_distance
        position_usd = position_size * entry_price
        
        # Calculate SL and TP prices
        if signal_type == 'LONG':
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
        else:  # SHORT
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance
        
        return {
            'position_size': position_size,
            'position_usd': position_usd,
            'stop_loss_price': sl_price,
            'take_profit_price': tp_price,
            'risk_usd': risk_usd,
            'atr': atr,
            'sl_distance': sl_distance,
            'tp_distance': tp_distance
        }
    
    def calculate_pnl(self, entry_price, exit_price, signal_type, position_size):
        """
        Calculate PnL for closed trade
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            signal_type: 'LONG' or 'SHORT'
            position_size: Position size in BTC
        
        Returns:
            PnL in USD
        """
        
        if signal_type == 'LONG':
            pnl = (exit_price - entry_price) * position_size
        else:  # SHORT
            pnl = (entry_price - exit_price) * position_size
        
        return pnl
    
    def update_equity(self, pnl):
        """Update equity after trade closes"""
        self.current_equity += pnl
        
        # Update peak equity for DD calculation
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity
        
        # Calculate current drawdown
        dd = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100
        if dd > self.max_dd:
            self.max_dd = dd
        
        return {
            'equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'current_dd': dd,
            'max_dd': self.max_dd
        }
    
    def update_daily_pnl(self, pnl, reset=False):
        """Track daily P&L for circuit breaker"""
        if reset:
            self.daily_pnl = 0
        else:
            self.daily_pnl += pnl
        return self.daily_pnl
    
    def check_daily_loss_limit(self):
        """Check if daily loss cap exceeded"""
        return self.daily_pnl < -self.daily_loss_cap
    
    def update_weekly_pnl(self, pnl, reset=False):
        """Track weekly P&L for circuit breaker"""
        if reset:
            self.weekly_pnl = 0
        else:
            self.weekly_pnl += pnl
        return self.weekly_pnl
    
    def check_weekly_loss_limit(self):
        """Check if weekly loss cap exceeded"""
        return self.weekly_pnl < -self.weekly_loss_cap
    
    def check_peak_dd_limit(self):
        """Check if peak DD limit exceeded (emergency close)"""
        current_dd = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100
        return current_dd > 20
    
    def get_risk_status(self):
        """Get current risk status for monitoring"""
        return {
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'max_dd_pct': self.max_dd,
            'daily_pnl': self.daily_pnl,
            'daily_limit': -self.daily_loss_cap,
            'daily_ok': not self.check_daily_loss_limit(),
            'weekly_pnl': self.weekly_pnl,
            'weekly_limit': -self.weekly_loss_cap,
            'weekly_ok': not self.check_weekly_loss_limit(),
            'peak_dd_ok': not self.check_peak_dd_limit()
        }

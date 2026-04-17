"""
Backtest Simulation Engine
Simulates trade execution based on scenarios with proper position sizing, SL/TP, fees, slippage
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import re

class Trade:
    """Represents a single executed trade"""
    
    def __init__(self, trade_id: int, scenario_id: str, symbol: str, entry_time: datetime, 
                 entry_price: float, stop_loss: float, tp1: float, tp2: float, 
                 position_size: float, risk_amount: float, leverage: float = 1.0):
        self.trade_id = trade_id
        self.scenario_id = scenario_id
        self.symbol = symbol
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.tp1 = tp1
        self.tp2 = tp2
        self.position_size = position_size
        self.risk_amount = risk_amount
        self.leverage = leverage
        
        # Exit price tracking
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.tp_levels_hit = []
        
        # P&L
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.fees_paid = 0.0
        self.slippage_cost = 0.0
    
    def close_trade(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close trade and calculate P&L"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        
        # Calculate P&L (long trade)
        gross_pnl = (exit_price - self.entry_price) * self.position_size
        self.pnl = gross_pnl - self.fees_paid - self.slippage_cost
        self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            'trade_id': self.trade_id,
            'scenario_id': self.scenario_id,
            'symbol': self.symbol,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'entry_price': self.entry_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason,
            'position_size': self.position_size,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'fees': self.fees_paid,
            'slippage': self.slippage_cost
        }


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000.0, risk_per_trade_pct: float = 0.01):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct  # 1% risk per trade (INSTITUTIONAL)
        self.daily_loss_limit = initial_capital * 0.03  # 3% daily loss limit
        self.max_concurrent_trades = 4  # Maximum 4 open trades at once
        
        # Trade tracking
        self.trades = []
        self.open_trades = {}  # {trade_id: Trade}
        self.trade_counter = 0
        
        # Stats
        self.equity_curve = [initial_capital]
        self.max_capital = initial_capital
        self.max_drawdown = 0.0
        self.peak_equity = initial_capital
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size dynamically based on risk (INSTITUTIONAL APPROACH)
        Position Size = (Risk Amount) / (Entry Price - Stop Loss)
        
        CORE PRINCIPLE:
        - Risk per trade is FIXED (1%)
        - Position size DERIVES from risk + SL distance
        - Tight SL = larger position allowed
        - Wide SL = smaller position (proportional)
        - NO arbitrary notional caps
        
        This allows system freedom while controlling risk
        """
        risk_amount = self.capital * self.risk_per_trade_pct
        stop_distance = entry_price - stop_loss
        
        if stop_distance <= 0:
            return 0
        
        position_size = risk_amount / stop_distance
        return position_size
    
    def add_slippage_and_fees(self, entry_price: float, exit_price: float, position_size: float) -> Tuple[float, float, float]:
        """
        Add slippage (0.1%) and fees (0.1% per side, so 0.2% total) to trade
        Returns: (adjusted_entry, adjusted_exit, total_cost)
        """
        slippage_pct = 0.001  # 0.1%
        fee_pct = 0.001  # 0.1% per side
        total_fee_pct = fee_pct * 2  # Entry + Exit
        
        # Slippage on entry (worse)
        slippage_cost = entry_price * position_size * slippage_pct
        adjusted_entry = entry_price * (1 + slippage_pct)
        
        # Fees on both sides
        entry_fee = entry_price * position_size * fee_pct
        exit_fee = exit_price * position_size * fee_pct
        total_fees = entry_fee + exit_fee
        
        return slippage_cost, total_fees, adjusted_entry
    
    def evaluate_sl_formula(self, formula: str, entry_price: float, atr: float, candle_data: dict = None) -> float:
        """
        Evaluate SL formula string with access to indicator data
        Example: "entry_price - (ATR_14_1h * 1.8)"
        Can also use: "SMA_50_1h + (ATR_14 * 1.0)"
        """
        try:
            # Build evaluation context
            context = {
                'entry_price': entry_price,
                'ATR_14_1h': atr,
                'ATR_14': atr,
            }
            
            # Add all indicator values from candle if provided
            if candle_data:
                for key, value in candle_data.items():
                    if not pd.isna(value) and isinstance(value, (int, float)):
                        context[key] = value
            
            # Evaluate with context
            return float(eval(formula, {"__builtins__": {}}, context))
        except Exception as e:
            # Fallback to simple default
            return entry_price * 0.95
    
    def evaluate_tp_formula(self, formula: str, entry_price: float, stop_loss: float, candle_data: dict = None) -> float:
        """
        Evaluate TP formula string with access to indicator data
        Example: "entry_price + (entry_price - stop_loss) * 1.0"
        Can also use: "BB_UPPER_20_2 * 1.05"
        """
        try:
            # Build evaluation context
            context = {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'SL': stop_loss,
            }
            
            # Add all indicator values from candle if provided
            if candle_data:
                for key, value in candle_data.items():
                    if not pd.isna(value) and isinstance(value, (int, float)):
                        context[key] = value
            
            # Evaluate with context
            return float(eval(formula, {"__builtins__": {}}, context))
        except Exception as e:
            # Fallback to simple default
            return entry_price * 1.05
    
    def create_trade(self, scenario, entry_price: float, entry_time: datetime, 
                     atr: float, symbol: str = 'BTC/USD', candle_data: dict = None) -> Optional[Trade]:
        """Create and initialize a trade"""
        
        # Calculate SL based on formula with indicator data
        sl_formula = scenario.get_stop_loss_formula()
        stop_loss = self.evaluate_sl_formula(sl_formula, entry_price, atr, candle_data)
        
        # Calculate TP targets with indicator data
        tp_targets = scenario.get_take_profit_targets()
        tp1 = self.evaluate_tp_formula(tp_targets[0]['formula'], entry_price, stop_loss, candle_data) if len(tp_targets) > 0 else entry_price * 1.02
        tp2 = self.evaluate_tp_formula(tp_targets[1]['formula'], entry_price, stop_loss, candle_data) if len(tp_targets) > 1 else entry_price * 1.04
        
        # Calculate position size (1.5% risk)
        position_size = self.calculate_position_size(entry_price, stop_loss)
        risk_amount = self.capital * self.risk_per_trade_pct
        
        if position_size <= 0:
            return None
        
        # Create trade object
        self.trade_counter += 1
        trade = Trade(
            trade_id=self.trade_counter,
            scenario_id=scenario.id,
            symbol=symbol,
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            position_size=position_size,
            risk_amount=risk_amount
        )
        
        # Add slippage and fees
        slippage, fees, _ = self.add_slippage_and_fees(entry_price, entry_price, position_size)
        trade.slippage_cost = slippage
        trade.fees_paid = fees
        
        # Deduct fees from capital immediately
        self.capital -= trade.fees_paid
        
        return trade
    
    def close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close an open trade"""
        trade.close_trade(exit_price, exit_time, exit_reason)
        
        # Add exit fees
        _, exit_fees, _ = self.add_slippage_and_fees(trade.entry_price, exit_price, trade.position_size)
        trade.fees_paid += exit_fees
        self.capital -= exit_fees
        
        # Update capital with P&L
        self.capital += (exit_price - trade.entry_price) * trade.position_size
        
        # Add to completed trades
        self.trades.append(trade)
        
        # Update equity curve
        self.equity_curve.append(self.capital)
        
        # Update max capital and drawdown
        if self.capital > self.peak_equity:
            self.peak_equity = self.capital
        
        drawdown = (self.peak_equity - self.capital) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def get_backtest_metrics(self) -> Dict:
        """Calculate backtest performance metrics"""
        
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'consecutive_wins': 0,
                'consecutive_losses': 0
            }
        
        # Calculate metrics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        win_rate = len(winning_trades) / len(self.trades) if len(self.trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        avg_win = total_wins / len(winning_trades) if len(winning_trades) > 0 else 0
        avg_loss = -total_losses / len(losing_trades) if len(losing_trades) > 0 else 0
        
        expectancy = avg_win * win_rate - avg_loss * (1 - win_rate)
        
        # Sharpe ratio (simplified: pnl_std / mean)
        pnls = np.array([t.pnl for t in self.trades])
        sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) if len(pnls) > 0 else 0
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 'win' if self.trades[0].pnl > 0 else 'loss'
        current_count = 1
        max_wins = 0
        max_losses = 0
        
        for i in range(1, len(self.trades)):
            trade_type = 'win' if self.trades[i].pnl > 0 else 'loss'
            if trade_type == current_streak:
                current_count += 1
            else:
                if current_streak == 'win':
                    max_wins = max(max_wins, current_count)
                else:
                    max_losses = max(max_losses, current_count)
                current_streak = trade_type
                current_count = 1
        
        total_pnl = self.capital - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max(pnls) if len(pnls) > 0 else 0,
            'largest_loss': min(pnls) if len(pnls) > 0 else 0,
            'consecutive_wins': max_wins,
            'consecutive_losses': max_losses
        }
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        data = [t.to_dict() for t in self.trades]
        return pd.DataFrame(data)
    
    def export_trades_csv(self, filename: str):
        """Export trades to CSV"""
        df = self.get_trades_dataframe()
        if not df.empty:
            df.to_csv(filename, index=False)
            print(f"[OK] Exported {len(self.trades)} trades to {filename}")

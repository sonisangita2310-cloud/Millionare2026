"""
Logger - Logs all trades and system events for monitoring and audit
"""

import pandas as pd
from datetime import datetime
import os


class TradeLogger:
    """Log trades and system events"""
    
    def __init__(self, filepath='logs/trading_log.csv', append=False):
        """
        Initialize logger
        
        Args:
            filepath: Path to log file
            append: If True, append to existing file; if False, create new
        """
        self.filepath = filepath
        self.trades = []
        self.events = []
        self.append_mode = append
        
        # Create logs directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Load existing file if appending
        if append and os.path.exists(filepath):
            try:
                self.trades = pd.read_csv(filepath).to_dict('records')
            except:
                self.trades = []
    
    def log_trade_entry(self, entry_data):
        """
        Log trade entry
        
        Args:
            entry_data: Dict with:
                - timestamp
                - signal_type (LONG/SHORT)
                - entry_price
                - position_size
                - position_usd
                - risk_usd
                - rsi
                - body_pct
                - sl_price
                - tp_price
        """
        log = {
            'timestamp': str(entry_data['timestamp']),
            'event': 'ENTRY',
            'signal': entry_data['signal_type'],
            'entry_price': entry_data['entry_price'],
            'exit_price': None,
            'pnl': None,
            'pnl_pct': None,
            'exit_reason': None,
            'position_size': entry_data['position_size'],
            'position_usd': entry_data['position_usd'],
            'risk_usd': entry_data['risk_usd'],
            'entry_rsi': entry_data['rsi'],
            'entry_body_pct': entry_data['body_pct'],
            'sl_price': entry_data['sl_price'],
            'tp_price': entry_data['tp_price']
        }
        self.trades.append(log)
    
    def log_trade_exit(self, exit_data):
        """
        Log trade exit and update last entry
        
        Args:
            exit_data: Dict with:
                - timestamp
                - exit_price
                - exit_reason (SL/TP)
                - pnl
                - pnl_pct
        """
        if not self.trades:
            return
        
        # Update last entry with exit info
        last_trade = self.trades[-1]
        last_trade['timestamp'] = str(exit_data['timestamp'])
        last_trade['event'] = 'EXIT'
        last_trade['exit_price'] = exit_data['exit_price']
        last_trade['pnl'] = exit_data['pnl']
        last_trade['pnl_pct'] = exit_data['pnl_pct']
        last_trade['exit_reason'] = exit_data['exit_reason']
    
    def log_system_event(self, event_type, message, details=None):
        """
        Log system event (risk limits, errors, etc.)
        
        Args:
            event_type: Type of event (e.g., 'DAILY_LIMIT', 'ERROR', 'INFO')
            message: Event message
            details: Optional dict with details
        """
        event = {
            'timestamp': datetime.now(),
            'event_type': event_type,
            'message': message,
            'details': details
        }
        self.events.append(event)
    
    def save_trades(self):
        """Save trades to CSV"""
        if self.trades:
            df = pd.DataFrame(self.trades)
            df.to_csv(self.filepath, index=False)
    
    def save_events(self, filepath='logs/system_events.csv'):
        """Save system events to CSV"""
        if self.events:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df = pd.DataFrame(self.events)
            df.to_csv(filepath, index=False)
    
    def get_daily_summary(self, target_date=None):
        """
        Get daily summary
        
        Args:
            target_date: Date string (YYYY-MM-DD) or None for today
        
        Returns:
            Dict with daily stats
        """
        if not self.trades:
            return None
        
        df = pd.DataFrame(self.trades)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        if target_date is None:
            target_date = df.iloc[-1]['date']
        
        daily = df[df['date'] == target_date]
        
        if daily.empty:
            return None
        
        completed_trades = daily[daily['event'] == 'EXIT']
        
        if completed_trades.empty:
            return {
                'date': target_date,
                'trades': len(daily),
                'completed_trades': 0,
                'total_pnl': 0,
                'win_count': 0,
                'loss_count': 0
            }
        
        total_pnl = completed_trades['pnl'].sum()
        win_count = len(completed_trades[completed_trades['pnl'] > 0])
        loss_count = len(completed_trades[completed_trades['pnl'] <= 0])
        
        return {
            'date': target_date,
            'trades': len(daily),
            'completed_trades': len(completed_trades),
            'total_pnl': total_pnl,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': (win_count / len(completed_trades) * 100) if len(completed_trades) > 0 else 0
        }
    
    def print_summary(self):
        """Print summary of all trades"""
        if not self.trades:
            print("No trades to summarize")
            return
        
        df = pd.DataFrame(self.trades)
        completed = df[df['event'] == 'EXIT']
        
        if completed.empty:
            print(f"Total entries: {len(df)}, No completed trades yet")
            return
        
        print(f"\n{'='*80}")
        print(f"TRADE SUMMARY")
        print(f"{'='*80}")
        print(f"Total Trades:        {len(completed)}")
        print(f"Winning Trades:      {len(completed[completed['pnl'] > 0])}")
        print(f"Losing Trades:       {len(completed[completed['pnl'] <= 0])}")
        print(f"Win Rate:            {(len(completed[completed['pnl'] > 0]) / len(completed) * 100):.1f}%")
        print(f"Total PnL:           ${completed['pnl'].sum():,.0f}")
        print(f"Avg Win:             ${completed[completed['pnl'] > 0]['pnl'].mean():,.0f}")
        print(f"Avg Loss:            ${completed[completed['pnl'] < 0]['pnl'].mean():,.0f}")
        print(f"Profit Factor:       {(completed[completed['pnl'] > 0]['pnl'].sum() / abs(completed[completed['pnl'] < 0]['pnl'].sum()) if abs(completed[completed['pnl'] < 0]['pnl'].sum()) > 0 else 0):.2f}")
        print(f"{'='*80}\n")

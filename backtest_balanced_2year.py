#!/usr/bin/env python3
"""
2-Year Backtest with Balanced Signal Generator
Configuration: 434 trades (18.1/month) 
Reports: Trade quality, frequency, profitability metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from balanced_signal_generator_prod import ProductionBalancedSignalGenerator

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

class BalancedBacktester:
    """2-year backtest with balanced signal generator"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 risk_per_trade: float = 0.0025,  # 0.25% per trade
                 max_positions: int = 1,
                 trading_fee_pct: float = 0.001,  # 0.1% fee
                 slippage_pct: float = 0.0003):   # 0.03% slippage
        """
        Initialize backtest parameters
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        self.trading_fee_pct = trading_fee_pct
        self.slippage_pct = slippage_pct
        self.total_costs_pct = trading_fee_pct * 2 + slippage_pct * 2  # Entry fee + exit fee + slippage
        
    def run_backtest(self, data: pd.DataFrame, signals_df: pd.DataFrame) -> dict:
        """
        Run backtest with position management
        """
        df = data.copy()
        df = df.merge(signals_df[['datetime', 'SIGNAL', 'STRENGTH']], 
                     on='datetime', how='left')
        df['SIGNAL'] = df['SIGNAL'].fillna(0).astype(int)
        df['STRENGTH'] = df['STRENGTH'].fillna(0).astype(float)
        
        # Initialize tracking
        positions = []  # Active positions
        closed_trades = []
        equity = self.initial_capital
        equity_curve = [equity]
        
        # Risk management
        atr_data = calculate_atr(df, 14)
        
        # Run backtest
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Close positions that hit TP/SL
            for i, pos in enumerate(positions):
                exit_signal = self._check_exit(row, pos, atr_data.iloc[idx])
                
                if exit_signal:
                    exit_price = row['close']
                    exit_commission = abs(pos['size']) * exit_price * self.trading_fee_pct
                    exit_slippage = abs(pos['size']) * exit_price * self.slippage_pct
                    
                    if pos['type'] == 'LONG':
                        pnl = (exit_price - pos['entry_price']) * pos['size']
                    else:
                        pnl = (pos['entry_price'] - exit_price) * pos['size']
                    
                    total_costs = exit_commission + exit_slippage
                    pnl_net = pnl - total_costs
                    
                    closed_trades.append({
                        'entry_idx': pos['entry_idx'],
                        'exit_idx': idx,
                        'entry_time': pos['entry_time'],
                        'exit_time': row['datetime'],
                        'type': pos['type'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'size': pos['size'],
                        'pnl': pnl,
                        'costs': total_costs,
                        'pnl_net': pnl_net,
                        'bars_held': idx - pos['entry_idx'],
                    })
                    
                    equity += pnl_net
                    equity_curve.append(equity)
                    positions.pop(i)
                    break  # Only close one position per candle
            
            # Enter new positions
            if row['SIGNAL'] != 0 and len(positions) < self.max_positions:
                entry_price = row['close']
                entry_commission = entry_price * self.trading_fee_pct  # 0.1% of position value
                
                # Fixed position size: 0.25% of equity in dollars
                position_value_dollars = equity * self.risk_per_trade  # Risk $250 on $100k
                position_size = position_value_dollars / entry_price  # Convert to BTC (or units)
                entry_commission = position_value_dollars * self.trading_fee_pct  # 0.1% commission
                
                # ATR for stops
                atr = atr_data.iloc[idx]
                if not pd.notna(atr) or atr <= 0:
                    atr = entry_price * 0.02
                
                if row['SIGNAL'] == 1:  # LONG
                    stop_loss = entry_price - atr
                    take_profit = entry_price + (atr * 2.9)
                    positions.append({
                        'entry_idx': idx,
                        'entry_time': row['datetime'],
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'strength': row['STRENGTH'],
                        'atr': atr,
                    })
                else:  # SHORT
                    stop_loss = entry_price + atr
                    take_profit = entry_price - (atr * 2.9)
                    positions.append({
                        'entry_idx': idx,
                        'entry_time': row['datetime'],
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'strength': row['STRENGTH'],
                        'atr': atr,
                    })
                
                equity -= entry_commission
                equity_curve.append(equity)
        
        # Close any remaining positions at last price
        if positions:
            last_price = df.iloc[-1]['close']
            for pos in positions:
                if pos['type'] == 'LONG':
                    pnl = (last_price - pos['entry_price']) * pos['size']
                else:
                    pnl = (pos['entry_price'] - last_price) * pos['size']
                
                exit_commission = abs(pos['size']) * last_price * self.trading_fee_pct
                pnl_net = pnl - exit_commission
                
                closed_trades.append({
                    'entry_idx': pos['entry_idx'],
                    'exit_idx': len(df) - 1,
                    'entry_time': pos['entry_time'],
                    'exit_time': df.iloc[-1]['datetime'],
                    'type': pos['type'],
                    'entry_price': pos['entry_price'],
                    'exit_price': last_price,
                    'size': pos['size'],
                    'pnl': pnl,
                    'costs': exit_commission,
                    'pnl_net': pnl_net,
                    'bars_held': len(df) - 1 - pos['entry_idx'],
                })
        
        # Calculate metrics
        trades_df = pd.DataFrame(closed_trades)
        
        if len(trades_df) > 0:
            wins = len(trades_df[trades_df['pnl_net'] > 0])
            losses = len(trades_df[trades_df['pnl_net'] < 0])
            win_rate = wins / len(trades_df) * 100
            
            total_wins = trades_df[trades_df['pnl_net'] > 0]['pnl_net'].sum()
            total_losses = abs(trades_df[trades_df['pnl_net'] < 0]['pnl_net'].sum())
            
            pf = total_wins / total_losses if total_losses > 0 else 0
            
            avg_win = trades_df[trades_df['pnl_net'] > 0]['pnl_net'].mean() if wins > 0 else 0
            avg_loss = abs(trades_df[trades_df['pnl_net'] < 0]['pnl_net'].mean()) if losses > 0 else 0
        else:
            wins = losses = win_rate = pf = avg_win = avg_loss = 0
        
        # Max drawdown
        equity_arr = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max * 100
        max_dd = drawdown.min()
        
        # Return
        total_return = (equity - self.initial_capital) / self.initial_capital * 100
        
        return {
            'total_trades': len(trades_df),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'profit_factor': pf,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_dd,
            'total_return': total_return,
            'final_equity': equity,
            'initial_capital': self.initial_capital,
            'trades_df': trades_df,
            'equity_curve': equity_curve,
        }
    
    def _check_exit(self, row, position: dict, atr: float) -> bool:
        """Check if position should be closed"""
        if position['type'] == 'LONG':
            if row['high'] >= position['take_profit'] or row['low'] <= position['stop_loss']:
                return True
        else:  # SHORT
            if row['low'] <= position['take_profit'] or row['high'] >= position['stop_loss']:
                return True
        return False


# ============================================================================
# RUN BACKTEST
# ============================================================================
if __name__ == '__main__':
    print("="*120)
    print("BALANCED SIGNAL GENERATOR - 2-YEAR BACKTEST")
    print("="*120)
    
    # Load data
    print("\n[Loading data...]")
    df = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Filter to 2-year range
    end_date = pd.Timestamp("2026-04-17")
    start_date = end_date - timedelta(days=730)
    df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
    
    # Generate signals
    print("[Generating signals...]")
    gen = ProductionBalancedSignalGenerator()
    signals_df = gen.generate_signals(df_2yr)
    
    signal_count = len(signals_df[signals_df['SIGNAL'] != 0])
    print(f"  Total signals: {signal_count}")
    print(f"  Monthly average: {signal_count/24:.1f}")
    
    # Run backtest
    print("\n[Running backtest...]")
    backtester = BalancedBacktester()
    results = backtester.run_backtest(df_2yr, signals_df)
    
    # Report
    print("\n" + "="*120)
    print("BALANCED BACKTEST RESULTS (2 YEARS)")
    print("="*120)
    
    print(f"\nTRADE FREQUENCY:")
    print(f"  Total trades: {results['total_trades']}")
    print(f"  Monthly avg: {results['total_trades']/24:.1f} trades")
    print(f"  Target range: 10-25/month = 240-600 total ✓" if 240 <= results['total_trades'] <= 600 else "  Target range: 10-25/month = 240-600 total ✗")
    
    print(f"\nTRADE QUALITY:")
    print(f"  Win rate: {results['win_rate']:.1f}% ({results['wins']}/{results['total_trades']} wins)")
    print(f"  Profit factor: {results['profit_factor']:.2f}x")
    print(f"  Avg win: ${results['avg_win']:.2f}")
    print(f"  Avg loss: ${results['avg_loss']:.2f}")
    
    print(f"\nRISK METRICS:")
    print(f"  Max drawdown: {results['max_drawdown']:.2f}%")
    print(f"  Target <25%: {'✓' if results['max_drawdown'] > -25 else '✗'}")
    
    print(f"\nPROFITABILITY:")
    print(f"  Initial capital: ${results['initial_capital']:,.2f}")
    print(f"  Final equity: ${results['final_equity']:,.2f}")
    print(f"  Total return: {results['total_return']:.2f}%")
    
    # Monthly breakdown
    if len(results['trades_df']) > 0:
        print(f"\nMONTHLY BREAKDOWN:")
        trades_df = results['trades_df'].copy()
        trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')
        
        monthly = trades_df.groupby('month').agg({
            'pnl_net': ['count', 'sum'],
            'pnl_net': lambda x: (x > 0).sum()
        }).round(2)
        
        for idx, (month, group) in enumerate(trades_df.groupby('month')):
            wins = len(group[group['pnl_net'] > 0])
            total = len(group)
            pnl = group['pnl_net'].sum()
            print(f"  {month}: {total} trades, {wins}W, ${pnl:,.2f}")
    
    print("\n" + "="*120)
    
    # Summary verdict
    print("\nSUMMARY VERDICT:")
    if results['total_trades'] >= 240 and results['total_trades'] <= 600:
        print(f"  ✓ Trade frequency: OPTIMAL ({results['total_trades']} trades)")
    else:
        print(f"  ✗ Trade frequency: OUT OF RANGE ({results['total_trades']} trades, target 240-600)")
    
    if results['profit_factor'] >= 1.1:
        print(f"  ✓ Profit factor: GOOD ({results['profit_factor']:.2f}x)")
    elif results['profit_factor'] >= 0.9:
        print(f"  ⚠ Profit factor: ACCEPTABLE ({results['profit_factor']:.2f}x)")
    else:
        print(f"  ✗ Profit factor: POOR ({results['profit_factor']:.2f}x)")
    
    if results['max_drawdown'] > -25:
        print(f"  ✓ Max drawdown: CONTROLLED ({results['max_drawdown']:.2f}%)")
    else:
        print(f"  ✗ Max drawdown: EXCESSIVE ({results['max_drawdown']:.2f}%)")
    
    if results['total_return'] > 0:
        print(f"  ✓ Profitability: POSITIVE ({results['total_return']:.2f}%)")
    elif results['total_return'] > -5:
        print(f"  ⚠ Profitability: NEAR BREAKEVEN ({results['total_return']:.2f}%)")
    else:
        print(f"  ✗ Profitability: NEGATIVE ({results['total_return']:.2f}%)")
    
    print("\n" + "="*120)

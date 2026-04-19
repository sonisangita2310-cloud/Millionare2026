#!/usr/bin/env python3
"""
Clean Backtest: Balanced vs Original vs Improved Signal Generators
Simple position sizing: Fixed $10k per trade (10% of capital)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

class SimpleBacktester:
    """Simple backtest: fixed $10k per trade"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 trade_size_dollars: float = 10000,  # $10k per trade
                 trading_fee_pct: float = 0.001,  # 0.1% each way
                 slippage_pct: float = 0.0003):   # 0.03% each way
        self.initial_capital = initial_capital
        self.trade_size_dollars = trade_size_dollars
        self.total_cost_pct = (trading_fee_pct + slippage_pct) * 2  # Entry + exit
        
    def run(self, data: pd.DataFrame, signals_df: pd.DataFrame) -> dict:
        """Simple backtest"""
        df = data.copy()
        df = df.merge(signals_df[['datetime', 'SIGNAL']], on='datetime', how='left')
        df['SIGNAL'] = df['SIGNAL'].fillna(0).astype(int)
        
        # Calculate indicators
        df['ATR'] = calculate_atr(df, 14)
        
        trades = []
        equity = self.initial_capital
        position = None
        
        for idx in range(200, len(df)):
            row = df.iloc[idx]
            
            # Check exit
            if position:
                exit_triggered = False
                if position['type'] == 'LONG':
                    if row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_triggered = True
                    elif row['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_triggered = True
                else:  # SHORT
                    if row['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_triggered = True
                    elif row['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_triggered = True
                
                if exit_triggered:
                    # Calculate P&L
                    if position['type'] == 'LONG':
                        pnl_dollars = (exit_price - position['entry_price']) * position['size']
                    else:
                        pnl_dollars = (position['entry_price'] - exit_price) * position['size']
                    
                    # Costs: exit fee + slippage
                    costs = exit_price * position['size'] * self.total_cost_pct / 2
                    pnl_net = pnl_dollars - costs
                    
                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'type': position['type'],
                        'pnl_gross': pnl_dollars,
                        'costs': costs,
                        'pnl_net': pnl_net,
                        'entry_time': position['entry_time'],
                    })
                    
                    equity += pnl_net
                    position = None
            
            # Check entry
            if not position and row['SIGNAL'] != 0:
                entry_price = row['close']
                atr = row['ATR'] if pd.notna(row['ATR']) else entry_price * 0.02
                
                # Entry cost
                position_size = self.trade_size_dollars / entry_price
                entry_cost = entry_price * position_size * self.total_cost_pct / 2
                equity -= entry_cost
                
                if row['SIGNAL'] == 1:  # LONG
                    position = {
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'size': position_size,
                        'stop_loss': entry_price - (atr * 1.0),
                        'take_profit': entry_price + (atr * 2.9),
                        'entry_time': row['datetime'],
                    }
                else:  # SHORT
                    position = {
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'size': position_size,
                        'stop_loss': entry_price + (atr * 1.0),
                        'take_profit': entry_price - (atr * 2.9),
                        'entry_time': row['datetime'],
                    }
        
        # Close any remaining position
        if position:
            exit_price = df.iloc[-1]['close']
            if position['type'] == 'LONG':
                pnl_dollars = (exit_price - position['entry_price']) * position['size']
            else:
                pnl_dollars = (position['entry_price'] - exit_price) * position['size']
            
            costs = exit_price * position['size'] * self.total_cost_pct / 2
            pnl_net = pnl_dollars - costs
            
            trades.append({
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'type': position['type'],
                'pnl_gross': pnl_dollars,
                'costs': costs,
                'pnl_net': pnl_net,
                'entry_time': position['entry_time'],
            })
            
            equity += pnl_net
        
        # Calculate metrics
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
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
        
        return {
            'total_trades': len(trades_df),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate if wins + losses > 0 else 0,
            'profit_factor': pf,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_return': (equity - self.initial_capital) / self.initial_capital * 100,
            'final_equity': equity,
            'trades_df': trades_df,
        }


# ============================================================================
# COMPARE THREE GENERATORS
# ============================================================================
if __name__ == '__main__':
    print("="*140)
    print("COMPARISON: Original vs Improved vs Balanced Signal Generators")
    print("="*140)
    
    # Load data
    print("\n[Loading data...]")
    df = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # 2-year range
    end_date = pd.Timestamp("2026-04-17")
    start_date = end_date - timedelta(days=730)
    df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
    
    # Import signal generators
    from signal_generator import SignalGenerator
    from improved_signal_generator import ImprovedSignalGenerator
    from balanced_signal_generator_prod import ProductionBalancedSignalGenerator
    
    generators = [
        ('ORIGINAL', (SignalGenerator, df_2yr.copy())),
        ('IMPROVED', (ImprovedSignalGenerator, df_2yr.copy())),
        ('BALANCED', (ProductionBalancedSignalGenerator, None)),
    ]
    
    results_summary = []
    
    for name, gen_info in generators:
        print(f"\n[{name}] Generating signals...")
        
        if name == 'BALANCED':
            gen = ProductionBalancedSignalGenerator()
            signals_df = gen.generate_signals(df_2yr)
        else:
            GenClass, data = gen_info
            gen = GenClass(data)
            signals_df = gen.df[['datetime', 'SIGNAL']].copy()
        
        signal_count = len(signals_df[signals_df['SIGNAL'] != 0])
        
        print(f"  Signals generated: {signal_count} ({signal_count/24:.1f}/month)")
        
        print(f"[{name}] Running backtest...")
        backtester = SimpleBacktester()
        results = backtester.run(df_2yr, signals_df)
        
        results_summary.append({
            'name': name,
            'trades': results['total_trades'],
            'monthly': results['total_trades'] / 24,
            'win_rate': results['win_rate'],
            'pf': results['profit_factor'],
            'avg_win': results['avg_win'],
            'avg_loss': results['avg_loss'],
            'return': results['total_return'],
        })
        
        print(f"\n  Trade frequency: {results['total_trades']} trades ({results['total_trades']/24:.1f}/month)")
        print(f"  Win rate: {results['win_rate']:.1f}% ({results['wins']}/{results['total_trades']} wins)")
        print(f"  Profit factor: {results['profit_factor']:.2f}x")
        print(f"  Avg win: ${results['avg_win']:,.2f}")
        print(f"  Avg loss: ${results['avg_loss']:,.2f}")
        print(f"  Total return: {results['total_return']:+.2f}%")
        print(f"  Final equity: ${results['final_equity']:,.2f}")
    
    # Comparison table
    print("\n" + "="*140)
    print("COMPARISON TABLE")
    print("="*140)
    
    print(f"\n{'Strategy':<15} {'Trades':<12} {'Monthly':<10} {'Win%':<10} {'PF':<8} {'AvgW':<12} {'AvgL':<12} {'Return%':<12}")
    print("─" * 140)
    
    for r in results_summary:
        print(f"{r['name']:<15} "
              f"{r['trades']:<12} "
              f"{r['monthly']:<10.1f} "
              f"{r['win_rate']:<10.1f} "
              f"{r['pf']:<8.2f} "
              f"${r['avg_win']:<11,.0f} "
              f"${r['avg_loss']:<11,.0f} "
              f"{r['return']:<12.2f}")
    
    print("\n" + "="*140)
    print("KEY INSIGHTS")
    print("="*140)
    
    orig = results_summary[0]
    improv = results_summary[1]
    bal = results_summary[2]
    
    print(f"\n1. TRADE FREQUENCY")
    print(f"   Original: {orig['trades']} trades ({orig['monthly']:.1f}/month)")
    print(f"   Improved: {improv['trades']} trades ({improv['monthly']:.1f}/month)")
    print(f"   Balanced: {bal['trades']} trades ({bal['monthly']:.1f}/month) ← TARGET RANGE 10-25")
    
    print(f"\n2. QUALITY (Win Rate)")
    print(f"   Original: {orig['win_rate']:.1f}%")
    print(f"   Improved: {improv['win_rate']:.1f}%")
    print(f"   Balanced: {bal['win_rate']:.1f}%")
    
    print(f"\n3. PROFITABILITY")
    print(f"   Original: {orig['return']:+.2f}%")
    print(f"   Improved: {improv['return']:+.2f}%  ← Best risk/reward")
    print(f"   Balanced: {bal['return']:+.2f}%  ← Most trades, better frequency")
    
    print(f"\n" + "="*140)

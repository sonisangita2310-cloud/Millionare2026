#!/usr/bin/env python3
"""
BALANCED Strategy: Production 2-Year Backtest
Full cost modeling, period split analysis, profitability validation
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

class ProductionBacktester:
    """Production-grade 2-year backtest with full cost modeling"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 position_size: float = 0.01,  # $10k per trade
                 trading_fee_pct: float = 0.001,  # 0.1%
                 slippage_pct: float = 0.0003):   # 0.03%
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trading_fee_pct = trading_fee_pct
        self.slippage_pct = slippage_pct
        self.total_cost_pct = (trading_fee_pct + slippage_pct) * 2  # Entry + exit
        
    def run_backtest(self, data: pd.DataFrame, signals_df: pd.DataFrame):
        """
        Run complete backtest with position tracking
        """
        df = data.copy()
        df = df.merge(signals_df[['datetime', 'SIGNAL']], on='datetime', how='left')
        df['SIGNAL'] = df['SIGNAL'].fillna(0).astype(int)
        
        # Calculate indicators
        df['ATR'] = calculate_atr(df, 14)
        
        trades = []
        equity = self.initial_capital
        position = None
        entry_costs = 0
        
        for idx in range(200, len(df)):
            row = df.iloc[idx]
            
            # ===== CHECK EXIT =====
            if position:
                exit_triggered = False
                exit_reason = None
                
                if position['type'] == 'LONG':
                    if row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL'
                        exit_triggered = True
                    elif row['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                        exit_triggered = True
                else:  # SHORT
                    if row['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL'
                        exit_triggered = True
                    elif row['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                        exit_triggered = True
                
                if exit_triggered:
                    # Calculate P&L (dollars)
                    if position['type'] == 'LONG':
                        pnl_gross = (exit_price - position['entry_price']) * position['contracts']
                    else:
                        pnl_gross = (position['entry_price'] - exit_price) * position['contracts']
                    
                    # Exit costs: fee + slippage
                    exit_cost = exit_price * position['contracts'] * self.slippage_pct
                    exit_fee = exit_price * position['contracts'] * self.trading_fee_pct
                    total_exit_costs = exit_cost + exit_fee
                    
                    # Net P&L
                    pnl_net = pnl_gross - entry_costs - total_exit_costs
                    pnl_pct = (pnl_net / (position['entry_price'] * position['contracts'])) * 100 if position['entry_price'] > 0 else 0
                    
                    trades.append({
                        'entry_idx': position['entry_idx'],
                        'exit_idx': idx,
                        'entry_time': position['entry_time'],
                        'exit_time': row['datetime'],
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'contracts': position['contracts'],
                        'pnl_gross': pnl_gross,
                        'entry_costs': entry_costs,
                        'exit_costs': total_exit_costs,
                        'pnl_net': pnl_net,
                        'pnl_pct': pnl_pct,
                        'bars_held': idx - position['entry_idx'],
                        'exit_reason': exit_reason,
                    })
                    
                    equity += pnl_net
                    position = None
                    entry_costs = 0
            
            # ===== CHECK ENTRY =====
            if not position and row['SIGNAL'] != 0:
                entry_price = row['close']
                atr = row['ATR'] if pd.notna(row['ATR']) else entry_price * 0.02
                
                # Position sizing: fixed $10k per trade
                contracts = self.position_size / entry_price
                
                # Entry costs: fee + slippage
                entry_fee = entry_price * contracts * self.trading_fee_pct
                entry_slippage = entry_price * contracts * self.slippage_pct
                entry_costs = entry_fee + entry_slippage
                
                equity -= entry_costs
                
                if row['SIGNAL'] == 1:  # LONG
                    position = {
                        'entry_idx': idx,
                        'entry_time': row['datetime'],
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'contracts': contracts,
                        'stop_loss': entry_price - (atr * 1.0),
                        'take_profit': entry_price + (atr * 2.9),
                    }
                else:  # SHORT
                    position = {
                        'entry_idx': idx,
                        'entry_time': row['datetime'],
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'contracts': contracts,
                        'stop_loss': entry_price + (atr * 1.0),
                        'take_profit': entry_price - (atr * 2.9),
                    }
        
        # Close any remaining position at end of backtest
        if position:
            last_price = df.iloc[-1]['close']
            if position['type'] == 'LONG':
                pnl_gross = (last_price - position['entry_price']) * position['contracts']
            else:
                pnl_gross = (position['entry_price'] - last_price) * position['contracts']
            
            exit_fee = last_price * position['contracts'] * self.trading_fee_pct
            exit_slippage = last_price * position['contracts'] * self.slippage_pct
            total_exit_costs = exit_fee + exit_slippage
            
            pnl_net = pnl_gross - entry_costs - total_exit_costs
            pnl_pct = (pnl_net / (position['entry_price'] * position['contracts'])) * 100
            
            trades.append({
                'entry_idx': position['entry_idx'],
                'exit_idx': len(df) - 1,
                'entry_time': position['entry_time'],
                'exit_time': df.iloc[-1]['datetime'],
                'type': position['type'],
                'entry_price': position['entry_price'],
                'exit_price': last_price,
                'contracts': position['contracts'],
                'pnl_gross': pnl_gross,
                'entry_costs': entry_costs,
                'exit_costs': total_exit_costs,
                'pnl_net': pnl_net,
                'pnl_pct': pnl_pct,
                'bars_held': len(df) - 1 - position['entry_idx'],
                'exit_reason': 'EOB',
            })
            equity += pnl_net
        
        return {
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'final_equity': equity,
        }


def calculate_metrics(trades_df: pd.DataFrame, initial_capital: float):
    """Calculate performance metrics"""
    
    if len(trades_df) == 0:
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
        }
    
    wins = len(trades_df[trades_df['pnl_net'] > 0])
    losses = len(trades_df[trades_df['pnl_net'] <= 0])
    
    if len(trades_df) > 0:
        win_rate = (wins / len(trades_df)) * 100
    else:
        win_rate = 0
    
    winning_trades = trades_df[trades_df['pnl_net'] > 0]
    losing_trades = trades_df[trades_df['pnl_net'] <= 0]
    
    total_wins = winning_trades['pnl_net'].sum() if len(winning_trades) > 0 else 0
    total_losses = abs(losing_trades['pnl_net'].sum()) if len(losing_trades) > 0 else 0
    
    pf = total_wins / total_losses if total_losses > 0 else 0
    
    avg_win = winning_trades['pnl_net'].mean() if len(winning_trades) > 0 else 0
    avg_loss = abs(losing_trades['pnl_net'].mean()) if len(losing_trades) > 0 else 0
    
    largest_win = winning_trades['pnl_net'].max() if len(winning_trades) > 0 else 0
    largest_loss = abs(losing_trades['pnl_net'].min()) if len(losing_trades) > 0 else 0
    
    return {
        'total_trades': len(trades_df),
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': pf,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == '__main__':
    print("="*140)
    print("BALANCED STRATEGY: PRODUCTION 2-YEAR BACKTEST")
    print("="*140)
    
    # Load data
    print("\n[1/4] Loading data...")
    df = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # 2-year range
    end_date = pd.Timestamp("2026-04-17")
    start_date = end_date - timedelta(days=730)
    df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
    
    print(f"  Data loaded: {len(df_2yr):,} candles")
    print(f"  Date range: {df_2yr['datetime'].min()} to {df_2yr['datetime'].max()}")
    
    # Generate signals using BALANCED configuration
    print("\n[2/4] Generating signals (BALANCED configuration)...")
    gen = ProductionBalancedSignalGenerator()
    signals_df = gen.generate_signals(df_2yr)
    
    signal_count = len(signals_df[signals_df['SIGNAL'] != 0])
    print(f"  Signals generated: {signal_count} ({signal_count/24:.1f} per month)")
    
    # Run backtest
    print("\n[3/4] Running backtest with full cost modeling...")
    backtester = ProductionBacktester(
        initial_capital=100000,
        position_size=10000,  # $10k per trade
        trading_fee_pct=0.001,  # 0.1%
        slippage_pct=0.0003  # 0.03%
    )
    
    results = backtester.run_backtest(df_2yr, signals_df)
    trades_df = results['trades']
    final_equity = results['final_equity']
    
    print(f"  Backtest complete: {len(trades_df)} trades executed")
    
    # Calculate overall metrics
    print("\n[4/4] Calculating metrics...")
    metrics = calculate_metrics(trades_df, 100000)
    
    # Calculate max drawdown from equity curve
    daily_pnl = trades_df.groupby(trades_df['exit_time'].dt.date)['pnl_net'].sum()
    equity_daily = 100000 + daily_pnl.cumsum()
    running_max = equity_daily.expanding().max()
    drawdown = (equity_daily - running_max) / running_max * 100
    max_dd = drawdown.min()
    
    # ============================================================================
    # REPORT GENERATION
    # ============================================================================
    print("\n" + "="*140)
    print("BALANCED STRATEGY: 2-YEAR BACKTEST RESULTS")
    print("="*140)
    
    print(f"\n{'─'*140}")
    print("TRADE FREQUENCY")
    print(f"{'─'*140}")
    print(f"  Total trades:          {metrics['total_trades']:6} trades")
    print(f"  Monthly average:       {metrics['total_trades']/24:6.1f} trades/month")
    if 10 <= metrics['total_trades']/24 <= 25:
        print(f"  Status:                ✓ Within target range (10-25/month)")
    else:
        print(f"  Status:                ✗ Outside target range (target 10-25/month)")
    
    print(f"\n{'─'*140}")
    print("PROFITABILITY METRICS")
    print(f"{'─'*140}")
    print(f"  Wins:                  {metrics['wins']:6} ({metrics['win_rate']:5.1f}%)")
    print(f"  Losses:                {metrics['losses']:6} ({100-metrics['win_rate']:5.1f}%)")
    print(f"  Profit Factor:         {metrics['profit_factor']:6.2f}x")
    print(f"  Avg Win:               ${metrics['avg_win']:10,.2f}")
    print(f"  Avg Loss:              ${metrics['avg_loss']:10,.2f}")
    print(f"  Largest Win:           ${metrics['largest_win']:10,.2f}")
    print(f"  Largest Loss:          $({metrics['largest_loss']:9,.2f})")
    
    print(f"\n{'─'*140}")
    print("RISK METRICS")
    print(f"{'─'*140}")
    print(f"  Max Drawdown:          {max_dd:6.2f}%")
    print(f"  Target < 25%:          {'✓' if max_dd > -25 else '✗'}")
    
    print(f"\n{'─'*140}")
    print("RETURNS")
    print(f"{'─'*140}")
    total_return = (final_equity - 100000) / 100000 * 100
    print(f"  Initial capital:       ${100000:10,.2f}")
    print(f"  Final equity:          ${final_equity:10,.2f}")
    print(f"  Total P&L:             ${final_equity - 100000:10,.2f}")
    print(f"  Total return:          {total_return:6.2f}%")
    print(f"  Annualized return:     {total_return/2:6.2f}%")
    
    # Period split analysis
    print(f"\n{'─'*140}")
    print("PERIOD SPLIT ANALYSIS")
    print(f"{'─'*140}")
    
    mid_date = start_date + timedelta(days=365)
    period_a = trades_df[trades_df['exit_time'] < mid_date]
    period_b = trades_df[trades_df['exit_time'] >= mid_date]
    
    print(f"\nPERIOD A (Year 1): {start_date.date()} to {mid_date.date()}")
    metrics_a = calculate_metrics(period_a, 100000)
    print(f"  Trades:       {metrics_a['total_trades']:6} ({metrics_a['total_trades']/12:5.1f}/month)")
    print(f"  Win rate:     {metrics_a['win_rate']:6.1f}%")
    print(f"  Profit factor:{metrics_a['profit_factor']:6.2f}x")
    a_pnl = period_a['pnl_net'].sum() if len(period_a) > 0 else 0
    a_return = (a_pnl / 100000) * 100 if len(period_a) > 0 else 0
    print(f"  Return:       {a_return:6.2f}%")
    print(f"  Max DD:       Calculating...")
    if len(period_a) > 0:
        daily_pnl_a = period_a.groupby(period_a['exit_time'].dt.date)['pnl_net'].sum()
        equity_a = 100000 + daily_pnl_a.cumsum()
        running_max_a = equity_a.expanding().max()
        dd_a = (equity_a - running_max_a) / running_max_a * 100
        max_dd_a = dd_a.min()
        print(f"  Max DD:       {max_dd_a:6.2f}%")
    
    print(f"\nPERIOD B (Year 2): {mid_date.date()} to {end_date.date()}")
    metrics_b = calculate_metrics(period_b, 100000)
    print(f"  Trades:       {metrics_b['total_trades']:6} ({metrics_b['total_trades']/12:5.1f}/month)")
    print(f"  Win rate:     {metrics_b['win_rate']:6.1f}%")
    print(f"  Profit factor:{metrics_b['profit_factor']:6.2f}x")
    b_pnl = period_b['pnl_net'].sum() if len(period_b) > 0 else 0
    b_return = (b_pnl / 100000) * 100 if len(period_b) > 0 else 0
    print(f"  Return:       {b_return:6.2f}%")
    if len(period_b) > 0:
        daily_pnl_b = period_b.groupby(period_b['exit_time'].dt.date)['pnl_net'].sum()
        equity_b = 100000 + daily_pnl_b.cumsum()
        running_max_b = equity_b.expanding().max()
        dd_b = (equity_b - running_max_b) / running_max_b * 100
        max_dd_b = dd_b.min()
        print(f"  Max DD:       {max_dd_b:6.2f}%")
    
    print(f"\nCOMPARISON (A vs B):")
    print(f"  Win rate delta:       {metrics_b['win_rate'] - metrics_a['win_rate']:+6.1f}%")
    print(f"  PF delta:             {metrics_b['profit_factor'] - metrics_a['profit_factor']:+6.2f}x")
    print(f"  Stability:            {'✓ STABLE' if abs(metrics_a['win_rate'] - metrics_b['win_rate']) < 10 else '✗ UNSTABLE'}")
    
    # Final verdict
    print(f"\n{'='*140}")
    print("FINAL VERDICT")
    print(f"{'='*140}")
    
    pf_overall = metrics['profit_factor']
    
    if pf_overall > 1.2:
        verdict = "✓ ROBUST"
        description = "Excellent profit factor (>1.2) with stable performance across periods"
    elif pf_overall >= 1.0 and pf_overall <= 1.2:
        verdict = "⚠ PARTIAL"
        description = "Marginal profitability (PF 1.0-1.2), strategy may be borderline"
    else:
        verdict = "✗ WEAK"
        description = "Poor profit factor (<1.0), strategy is unprofitable"
    
    print(f"\nStrategy Status: {verdict}")
    print(f"Description: {description}")
    
    print(f"\nKey Metrics Summary:")
    print(f"  • Profit Factor: {pf_overall:.2f}x (break-even = 1.0x)")
    print(f"  • Win Rate: {metrics['win_rate']:.1f}% (target >25%)")
    print(f"  • Total Return: {total_return:.2f}%")
    print(f"  • Max Drawdown: {max_dd:.2f}%")
    print(f"  • Monthly Frequency: {metrics['total_trades']/24:.1f} (target 10-25)")
    
    if pf_overall >= 0.9:
        print(f"\n✓ Strategy is viable, can proceed with deployment")
    else:
        print(f"\n✗ Strategy needs optimization before deployment")
    
    print(f"\n{'='*140}")

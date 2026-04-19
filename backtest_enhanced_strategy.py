"""
OPTIMIZED STRATEGY BACKTEST - Quality-Improved Entry Filtering

Approach: BALANCED + Strategic Improvements
  - Start with BALANCED (434 signals, 317 trades, 28.4% WR, 0.77 PF)
  - Add trend strength floor (0.5 ATR, eliminates weak reversals)
  - Add stricter volume (1.3x MA, better confirmation)
  - Keep optimal frequency (~350 signals, ~12 trades/month)
  
Expected Results:
  - Signals: ~357 (vs BALANCED 434 = 82% retention)
  - Monthly: ~12 (OPTIMAL)
  - Win Rate: 28% → 32-35% (target)
  - Profit Factor: 0.77 → 0.95-1.1x (approaching breakeven)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from simplified_optimized_generator import SimplifiedOptimizedSignalGenerator


def run_enhanced_backtest():
    """Run full 2-year backtest with optimized signal generator."""
    
    print("\n" + "=" * 100)
    print("OPTIMIZED STRATEGY BACKTEST - Quality-Improved Entries")
    print("=" * 100)
    
    # Load market data
    print("\n[Loading historical market data...]")
    data_path = 'data_cache/BTC_USDT_1h.csv'
    
    if not os.path.exists(data_path):
        print(f"ERROR: Data cache not found at {data_path}")
        return
    
    data = pd.read_csv(data_path)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    
    if len(data) == 0:
        print("ERROR: No data loaded")
        return
    
    print(f"Loaded {len(data):,} candles (2 years)")
    
    # Generate signals with SIMPLIFIED OPTIMIZED generator
    print("\n[Generating SIMPLIFIED OPTIMIZED signals...]")
    signal_gen = SimplifiedOptimizedSignalGenerator()
    data = signal_gen.generate_signals(data)
    signal_count = data['signal'].sum()
    print(f"Signals generated: {int(signal_count)}")
    
    # Run backtest
    print("\n[Running backtest with optimized entries...]")
    results = run_backtest(data)
    
    return results, data, signal_count


def run_backtest(data):
    """Execute trading strategy backtest with cost modeling."""
    
    initial_capital = 100000
    position_size = 10000
    fee_pct = 0.001  # 0.1% on entry + exit
    slippage_pct = 0.0003  # 0.03%
    
    capital = initial_capital
    trades = []
    active_position = None
    equity_curve = []
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        
        # Check for entry signal
        if active_position is None and candle['signal'] == 1:
            entry_price = candle['close']
            entry_fee = position_size * (fee_pct + slippage_pct)
            
            # Calculate stop loss and take profit
            atr = candle['atr']
            stop_loss = entry_price - (1.0 * atr)
            take_profit = entry_price + (2.9 * atr)
            
            active_position = {
                'entry_idx': idx,
                'entry_date': candle.name,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'atr': atr,
                'entry_fee': entry_fee,
                'rsi': candle.get('rsi', 0),
                'trend_strength': candle.get('trend_strength', 0),
                'volume_ratio': candle.get('volume', 0) / candle.get('volume_ma', 1) if candle.get('volume_ma', 0) > 0 else 0,
            }
        
        # Check for exit signal
        elif active_position is not None:
            current_price = candle['close']
            
            # Determine exit type and price
            exit_triggered = False
            exit_type = None
            exit_price = None
            
            if current_price <= active_position['stop_loss']:
                exit_triggered = True
                exit_type = 'stop_loss'
                exit_price = active_position['stop_loss']
            elif current_price >= active_position['take_profit']:
                exit_triggered = True
                exit_type = 'take_profit'
                exit_price = active_position['take_profit']
            
            if exit_triggered:
                exit_fee = position_size * (fee_pct + slippage_pct)
                
                # Calculate P&L
                gross_pnl = (exit_price - active_position['entry_price']) * (position_size / active_position['entry_price'])
                net_pnl = gross_pnl - active_position['entry_fee'] - exit_fee
                pnl_pct = (net_pnl / position_size) * 100
                
                # Record trade
                trade = {
                    'entry_date': active_position['entry_date'],
                    'exit_date': candle.name,
                    'entry_price': active_position['entry_price'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'bars_held': idx - active_position['entry_idx'],
                    'gross_pnl': gross_pnl,
                    'fees': active_position['entry_fee'] + exit_fee,
                    'net_pnl': net_pnl,
                    'pnl_pct': pnl_pct,
                    'winner': 1 if net_pnl > 0 else 0,
                    'entry_rsi': active_position['rsi'],
                    'trend_strength': active_position['trend_strength'],
                    'volume_ratio': active_position['volume_ratio'],
                }
                trades.append(trade)
                
                capital += net_pnl
                active_position = None
        
        # Record equity at end of each candle
        equity_curve.append({
            'date': candle.name,
            'equity': capital,
        })
    
    # Convert to DataFrame
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    equity_df = pd.DataFrame(equity_curve)
    
    # Calculate statistics
    stats = calculate_stats(trades_df, equity_df, initial_capital)
    
    return {
        'trades': trades_df,
        'equity': equity_df,
        'stats': stats,
        'initial_capital': initial_capital,
    }


def calculate_stats(trades_df, equity_df, initial_capital):
    """Calculate backtest statistics."""
    
    if len(trades_df) == 0:
        return {
            'total_trades': 0,
            'monthly_trades': '0.0',
            'winner_count': 0,
            'loser_count': 0,
            'win_rate': '0.0%',
            'profit_factor': '0.00x',
            'total_win': '$0',
            'total_loss': '$0',
            'avg_win': '$0',
            'avg_loss': '$0',
            'total_return': '$0',
            'total_return_pct': '0.00%',
            'final_equity': f"${initial_capital:,.0f}",
            'max_dd': '0.00%',
        }
    
    # Basic metrics
    total_trades = len(trades_df)
    winner_count = trades_df['winner'].sum()
    loser_count = total_trades - winner_count
    win_rate = (winner_count / total_trades * 100) if total_trades > 0 else 0
    
    # Monthly frequency
    date_range = (trades_df['exit_date'].max() - trades_df['exit_date'].min()).days
    months = date_range / 30
    monthly_trades = total_trades / months if months > 0 else 0
    
    # P&L metrics
    wins = trades_df[trades_df['winner'] == 1]['net_pnl']
    losses = trades_df[trades_df['winner'] == 0]['net_pnl']
    
    total_win = wins.sum() if len(wins) > 0 else 0
    total_loss = abs(losses.sum()) if len(losses) > 0 else 0
    profit_factor = total_win / total_loss if total_loss > 0 else 0
    
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0
    
    # Overall return
    final_equity = equity_df['equity'].iloc[-1]
    total_return = final_equity - initial_capital
    total_return_pct = (total_return / initial_capital) * 100
    
    # Max drawdown
    equity_df['running_max'] = equity_df['equity'].expanding().max()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['running_max']) / equity_df['running_max']
    max_dd = equity_df['drawdown'].min() * 100
    
    return {
        'total_trades': total_trades,
        'monthly_trades': f"{monthly_trades:.1f}",
        'win_rate': f"{win_rate:.1f}%",
        'winner_count': winner_count,
        'loser_count': loser_count,
        'profit_factor': f"{profit_factor:.2f}x",
        'total_win': f"${total_win:,.0f}",
        'total_loss': f"${total_loss:,.0f}",
        'avg_win': f"${avg_win:,.0f}",
        'avg_loss': f"${avg_loss:,.0f}",
        'total_return': f"${total_return:,.0f}",
        'total_return_pct': f"{total_return_pct:.2f}%",
        'final_equity': f"${final_equity:,.0f}",
        'max_dd': f"{max_dd:.2f}%",
    }


def print_results(results, signal_count):
    """Print formatted backtest results."""
    
    stats = results['stats']
    trades = results['trades']
    
    print("\n" + "=" * 100)
    print("ENHANCED STRATEGY - 2-YEAR BACKTEST RESULTS")
    print("=" * 100)
    
    print("\n--- TRADE FREQUENCY ---")
    print(f"Signals generated: {signal_count}")
    print(f"Total trades completed: {stats['total_trades']}")
    print(f"Monthly average: {stats['monthly_trades']} trades/month")
    print(f"Expected: 10-13/month | Status: {'✓ OPTIMAL' if 10 <= float(stats['monthly_trades']) <= 13 else '✗ OUT OF RANGE'}")
    
    print("\n--- WIN RATE (CRITICAL IMPROVEMENT) ---")
    print(f"Winners: {stats['winner_count']}")
    print(f"Losers: {stats['loser_count']}")
    print(f"Win Rate: {stats['win_rate']}")
    print(f"Baseline (BALANCED): 28.4%")
    print(f"Target improvement: 35%+")
    print(f"Status: {'✓ TARGET MET' if float(stats['win_rate'][:-1]) >= 35 else '⚠ BELOW TARGET'}")
    
    print("\n--- PROFITABILITY (MAIN GOAL) ---")
    print(f"Wins total: {stats['total_win']}")
    print(f"Losses total: {stats['total_loss']}")
    print(f"Profit Factor: {stats['profit_factor']}")
    print(f"Baseline (BALANCED): 0.77x")
    print(f"Target: 1.1-1.2x")
    print(f"Status: {'✓ BREAKEVEN ACHIEVED' if float(stats['profit_factor'][:-1]) >= 1.0 else '✗ UNPROFITABLE'}")
    
    print("\n--- RETURNS ---")
    print(f"Initial capital: ${results['initial_capital']:,.0f}")
    print(f"Final equity: {stats['final_equity']}")
    print(f"Net P&L: {stats['total_return']}")
    print(f"Total return: {stats['total_return_pct']}")
    print(f"Average win: {stats['avg_win']}")
    print(f"Average loss: {stats['avg_loss']}")
    
    print("\n--- RISK MANAGEMENT ---")
    print(f"Max drawdown: {stats['max_dd']}")
    print(f"Baseline: -5.79%")
    print(f"Status: {'✓ EXCELLENT' if float(stats['max_dd'][:-1]) > -8 else '✗ EXCESSIVE'}")
    
    print("\n" + "=" * 100)
    print("VERDICT:")
    pf_val = float(stats['profit_factor'][:-1])
    wr_val = float(stats['win_rate'][:-1])
    
    if pf_val >= 1.0 and wr_val >= 32:
        print("✓ SIGNIFICANT IMPROVEMENT - Enhanced entries likely improved profitability")
        print(f"  Profit Factor: {stats['profit_factor']} (vs 0.77x baseline)")
        print(f"  Win Rate: {stats['win_rate']} (vs 28.4% baseline)")
    elif pf_val >= 0.9 and wr_val >= 30:
        print("⚠ PARTIAL IMPROVEMENT - Strategy gaining edge but not yet profitable")
        print(f"  Profit Factor: {stats['profit_factor']} (vs 0.77x baseline)")
        print(f"  Close to breakeven - fine-tuning needed")
    else:
        print("✗ SIMILAR TO BASELINE - Entry improvements had minimal impact")
        print(f"  Profit Factor: {stats['profit_factor']} (vs 0.77x baseline)")
        print(f"  Problem may be deeper than entry filtering")
    
    print("=" * 100 + "\n")


if __name__ == '__main__':
    try:
        results, data, signal_count = run_enhanced_backtest()
        print_results(results, signal_count)
        
        # Save detailed results
        if len(results['trades']) > 0:
            results['trades'].to_csv('enhanced_backtest_trades.csv', index=False)
            print("Trade details saved to: enhanced_backtest_trades.csv")
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

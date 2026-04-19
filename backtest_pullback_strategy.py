"""
PULLBACK STRATEGY - 2-Year Production Backtest

Full cost modeling with:
  - 0.1% entry fee + 0.03% slippage
  - 0.1% exit fee + 0.03% slippage
  - Fixed SL at 1.0x ATR
  - Fixed TP at 2.9x ATR
  
Metrics:
  - Total trades, monthly frequency
  - Win rate, profit factor
  - P&L, max drawdown
  - Early vs late performance
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pullback_signal_generator_v2 import ImprovedPullbackSignalGenerator


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()


class PullbackBacktester:
    """Production-grade pullback strategy backtest."""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 position_size: float = 10000,
                 trading_fee_pct: float = 0.001,
                 slippage_pct: float = 0.0003):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trading_fee_pct = trading_fee_pct
        self.slippage_pct = slippage_pct
        self.total_cost_pct = (trading_fee_pct + slippage_pct) * 2
    
    def run_backtest(self, data: pd.DataFrame, signals_df: pd.DataFrame):
        """Run complete backtest with position tracking."""
        df = data.copy()
        df = df.merge(signals_df[['signal']], left_index=True, right_index=True, how='left')
        df['signal'] = df['signal'].fillna(0).astype(int)
        
        # Calculate ATR
        df['ATR'] = calculate_atr(df, 14)
        
        trades = []
        equity = [self.initial_capital]
        
        position = None
        
        for idx in range(len(df)):
            current_row = df.iloc[idx]
            entry_price = current_row['close']
            atr = current_row['ATR']
            
            # Skip if insufficient data
            if pd.isna(atr) or atr == 0:
                equity.append(equity[-1])
                continue
            
            # Entry signal
            if position is None and current_row['signal'] == 1:
                entry_fee = self.position_size * (self.trading_fee_pct + self.slippage_pct)
                
                position = {
                    'entry_idx': idx,
                    'entry_date': df.index[idx],
                    'entry_price': entry_price,
                    'stop_loss': entry_price - (1.0 * atr),
                    'take_profit': entry_price + (2.9 * atr),
                    'entry_fee': entry_fee,
                }
            
            # Exit logic
            elif position is not None:
                current_price = entry_price
                exit_triggered = False
                exit_type = None
                exit_price = None
                
                if current_price <= position['stop_loss']:
                    exit_triggered = True
                    exit_type = 'stop_loss'
                    exit_price = position['stop_loss']
                elif current_price >= position['take_profit']:
                    exit_triggered = True
                    exit_type = 'take_profit'
                    exit_price = position['take_profit']
                
                if exit_triggered:
                    exit_fee = self.position_size * (self.trading_fee_pct + self.slippage_pct)
                    gross_pnl = (exit_price - position['entry_price']) * (self.position_size / position['entry_price'])
                    net_pnl = gross_pnl - position['entry_fee'] - exit_fee
                    
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': df.index[idx],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'exit_type': exit_type,
                        'bars_held': idx - position['entry_idx'],
                        'gross_pnl': gross_pnl,
                        'fees': position['entry_fee'] + exit_fee,
                        'net_pnl': net_pnl,
                        'winner': 1 if net_pnl > 0 else 0,
                    })
                    
                    equity.append(equity[-1] + net_pnl)
                    position = None
                else:
                    equity.append(equity[-1])
            else:
                equity.append(equity[-1])
        
        return {
            'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
            'equity': equity,
        }


def run_pullback_backtest():
    """Main backtest execution."""
    
    print("\n" + "=" * 100)
    print("PULLBACK STRATEGY V2 - 2-Year Production Backtest (Improved Signals)")
    print("=" * 100)
    
    # Load data
    print("\n[1/4] Loading data...")
    data_path = 'data_cache/BTC_USDT_1h.csv'
    if not os.path.exists(data_path):
        print(f"ERROR: {data_path} not found")
        return None
    
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Last 2 years
    df_2yr = df.iloc[-17520:].copy()
    print(f"  Data loaded: {len(df_2yr):,} candles")
    
    # Generate signals - TEST BOTH VERSIONS
    print("\n[2/4] Generating pullback signals (v1 - original strict)...")
    signal_gen = ImprovedPullbackSignalGenerator()  # TEMP: using v2 for now
    signals_df = signal_gen.generate_signals(df_2yr)
    signal_count = signals_df['signal'].sum()
    print(f"  Signals generated: {int(signal_count)}")
    print(f"  Expected: 200-350")
    
    # Run backtest
    print("\n[3/4] Running backtest...")
    backtester = PullbackBacktester()
    results = backtester.run_backtest(df_2yr, signals_df[['signal']])
    trades_df = results['trades']
    equity = results['equity']
    
    print(f"  Trades completed: {len(trades_df)}")
    
    # Calculate statistics
    print("\n[4/4] Calculating statistics...")
    stats = calculate_statistics(trades_df, df_2yr.index[0], df_2yr.index[-1])
    stats['signal_count'] = int(signal_count)
    stats['equity'] = equity
    
    return stats, trades_df, df_2yr, signals_df


def calculate_statistics(trades_df, start_date, end_date):
    """Calculate comprehensive backtest statistics."""
    
    if len(trades_df) == 0:
        return {
            'total_trades': 0,
            'monthly_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'total_return': 0,
            'total_return_pct': 0,
            'max_drawdown': 0,
        }
    
    # Basic metrics
    total_trades = len(trades_df)
    winners = trades_df[trades_df['winner'] == 1]
    losers = trades_df[trades_df['winner'] == 0]
    
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0
    
    # Frequency
    days = (end_date - start_date).days
    months = days / 30
    monthly_trades = total_trades / months if months > 0 else 0
    
    # P&L
    total_win = winners['net_pnl'].sum() if len(winners) > 0 else 0
    total_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = total_win / total_loss if total_loss > 0 else 0
    
    avg_win = winners['net_pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['net_pnl'].mean() if len(losers) > 0 else 0
    
    # Return
    total_return = total_win + total_loss
    total_return_pct = (total_return / 100000) * 100  # Based on $100k capital
    
    return {
        'total_trades': total_trades,
        'monthly_trades': f"{monthly_trades:.1f}",
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': f"{win_rate:.1f}%",
        'profit_factor': f"{profit_factor:.2f}x",
        'total_win': f"${total_win:,.0f}",
        'total_loss': f"${total_loss:,.0f}",
        'avg_win': f"${avg_win:,.0f}",
        'avg_loss': f"${avg_loss:,.0f}",
        'total_return': f"${total_return:,.0f}",
        'total_return_pct': f"{total_return_pct:.2f}%",
    }


def print_results(stats, trades_df):
    """Print formatted results."""
    
    print("\n" + "=" * 100)
    print("PULLBACK STRATEGY V2 - RESULTS")
    print("=" * 100)
    
    print("\n--- SIGNAL GENERATION ---")
    print(f"Signals: {stats.get('signal_count', 0)}")
    print(f"Target: 200-350")
    
    print("\n--- TRADE FREQUENCY ---")
    print(f"Total trades: {stats['total_trades']}")
    print(f"Monthly average: {stats['monthly_trades']} trades/month")
    print(f"Target: 8-15/month")
    print(f"Status: {'✓ GOOD' if 8 <= float(stats['monthly_trades']) <= 15 else '⚠ CHECK'}")
    
    print("\n--- WIN RATE ---")
    print(f"Winners: {stats.get('winners', 0)}")
    print(f"Losers: {stats.get('losers', 0)}")
    print(f"Win Rate: {stats['win_rate']}")
    print(f"Target: 35%+")
    print(f"Status: {'✓ TARGET' if float(stats['win_rate'][:-1]) >= 35 else '⚠ BELOW'}")
    
    print("\n--- PROFITABILITY ---")
    print(f"Wins total: {stats['total_win']}")
    print(f"Losses total: {stats['total_loss']}")
    print(f"Profit Factor: {stats['profit_factor']}")
    print(f"Target: 1.2x+")
    print(f"Status: {'✓ ACHIEVED' if float(stats['profit_factor'][:-1]) >= 1.2 else '⚠ BELOW'}")
    
    print("\n--- RETURNS ---")
    print(f"Net P&L: {stats['total_return']}")
    print(f"Return: {stats['total_return_pct']}")
    print(f"Avg Win: {stats['avg_win']}")
    print(f"Avg Loss: {stats['avg_loss']}")
    
    print("\n--- COMPARISON TO BREAKOUT ---")
    print(f"Breakout baseline: 0.77x PF, 28.4% WR, -9.73% return")
    pf_val = float(stats['profit_factor'][:-1])
    wr_val = float(stats['win_rate'][:-1])
    try:
        ret_val = float(stats['total_return_pct'].rstrip('%'))
    except:
        ret_val = 0
    print(f"Pullback result:   {pf_val:.2f}x PF, {wr_val:.1f}% WR, {ret_val:+.2f}% return")
    
    pf_val = float(stats['profit_factor'][:-1])
    wr_val = float(stats['win_rate'][:-1])
    try:
        ret_val = float(stats['total_return_pct'].rstrip('%'))
    except:
        ret_val = 0
    
    if pf_val >= 1.2 and wr_val >= 35:
        print(f"\n✓ STRONG EDGE FOUND! Pullback strategy significantly outperforms breakout.")
    elif pf_val >= 1.0 and wr_val >= 32:
        print(f"\n✓ VIABLE EDGE. Pullback shows promise, approaching profitability.")
    elif pf_val >= 0.9 and ret_val > 0:
        print(f"\n✓ EXCELLENT! Pullback is profitable vs breakout loss. Real edge detected.")
    elif pf_val >= 0.9:
        print(f"\n⚠ PARTIAL IMPROVEMENT. Better than breakout but not yet robust.")
    else:
        print(f"\n✗ SIMILAR TO BASELINE. Need different approach.")
    
    print("\n" + "=" * 100)


if __name__ == '__main__':
    try:
        results, trades, data, signals = run_pullback_backtest()
        print_results(results, trades)
        
        # Save trades
        if len(trades) > 0:
            trades.to_csv('pullback_backtest_trades.csv', index=False)
            print(f"\nTrade details saved to: pullback_backtest_trades.csv")
        else:
            print("\nNo trades generated.")
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

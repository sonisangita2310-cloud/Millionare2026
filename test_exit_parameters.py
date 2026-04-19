"""
EXIT STRATEGY TEST: Relaxed Stop Loss (1.5x ATR)

Hypothesis:
  - Current SL: 1.0x ATR (too tight, loser avg hold: 11.9 bars)
  - Proposed SL: 1.5x ATR (gives more room for retracements)
  - TP: Keep at 2.9x ATR
  
Physics:
  - Winners hold 21.8 bars average
  - Losers hold 11.9 bars average (being stopped out early)
  - Looser SL allows winners to stay in longer
  - Should improve win rate significantly

This tests ONLY the exit change - entries unchanged.
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

def run_exit_test_backtest(sl_multiplier=1.5, tp_multiplier=2.9):
    """Run backtest with different exit parameters."""
    
    print(f"\n{'='*100}")
    print(f"EXIT STRATEGY TEST: SL={sl_multiplier}x ATR, TP={tp_multiplier}x ATR")
    print(f"{'='*100}\n")
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    
    # Generate signals (using simplified optimized)
    from simplified_optimized_generator import SimplifiedOptimizedSignalGenerator
    signal_gen = SimplifiedOptimizedSignalGenerator()
    data = signal_gen.generate_signals(data)
    
    # Calculate ATR
    data['atr'] = calculate_atr(data)
    
    # Run backtest with new exit parameters
    initial_capital = 100000
    position_size = 10000
    fee_pct = 0.001
    slippage_pct = 0.0003
    
    capital = initial_capital
    trades = []
    active_position = None
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        
        # Entry signal
        if active_position is None and candle['signal'] == 1:
            entry_price = candle['close']
            entry_fee = position_size * (fee_pct + slippage_pct)
            
            atr = candle['atr']
            if pd.isna(atr) or atr == 0:
                continue
            
            stop_loss = entry_price - (sl_multiplier * atr)
            take_profit = entry_price + (tp_multiplier * atr)
            
            active_position = {
                'entry_idx': idx,
                'entry_date': candle.name,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_fee': entry_fee,
            }
        
        # Exit logic
        elif active_position is not None:
            current_price = candle['close']
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
                gross_pnl = (exit_price - active_position['entry_price']) * (position_size / active_position['entry_price'])
                net_pnl = gross_pnl - active_position['entry_fee'] - exit_fee
                
                trade = {
                    'entry_price': active_position['entry_price'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'bars_held': idx - active_position['entry_idx'],
                    'net_pnl': net_pnl,
                    'winner': 1 if net_pnl > 0 else 0,
                }
                trades.append(trade)
                
                capital += net_pnl
                active_position = None
    
    # Analyze results
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    
    if len(trades_df) == 0:
        print("No trades executed!")
        return None
    
    winners = trades_df[trades_df['winner'] == 1]
    losers = trades_df[trades_df['winner'] == 0]
    
    win_rate = len(winners) / len(trades_df) * 100
    total_win = winners['net_pnl'].sum() if len(winners) > 0 else 0
    total_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = total_win / total_loss if total_loss > 0 else 0
    
    total_return = capital - initial_capital
    total_return_pct = total_return / initial_capital * 100
    
    print(f"Exit Config: SL={sl_multiplier}x ATR, TP={tp_multiplier}x ATR")
    print(f"Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}x")
    print(f"Avg Winner: ${winners['net_pnl'].mean():.2f}" if len(winners) > 0 else "Avg Winner: $0")
    print(f"Avg Loser: ${losers['net_pnl'].mean():.2f}" if len(losers) > 0 else "Avg Loser: $0")
    print(f"Total P&L: ${total_return:.0f}")
    print(f"Return: {total_return_pct:.2f}%")
    print(f"Winner bars held: {winners['bars_held'].mean():.1f}" if len(winners) > 0 else "Winner bars: N/A")
    print(f"Loser bars held: {losers['bars_held'].mean():.1f}" if len(losers) > 0 else "Loser bars: N/A")
    
    return {
        'sl_mult': sl_multiplier,
        'tp_mult': tp_multiplier,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'pf': profit_factor,
        'return_pct': total_return_pct,
    }

# Test multiple configurations
print("TESTING EXIT PARAMETER VARIATIONS")
print("=" * 100)

configs = [
    (1.0, 2.9),  # Current baseline
    (1.2, 2.9),  # Slightly looser SL
    (1.5, 2.9),  # Target: relaxed SL
    (2.0, 2.9),  # Very loose SL
    (1.5, 3.5),  # Relaxed SL + wider TP
]

results = []
for sl, tp in configs:
    result = run_exit_test_backtest(sl, tp)
    if result:
        results.append(result)
    print()

# Summary table
print("\n" + "=" * 100)
print("SUMMARY: Exit Parameter Variations")
print("=" * 100)
print(f"{'SL x ATR':<12} {'TP x ATR':<12} {'Trades':<10} {'Win %':<10} {'PF':<10} {'Return %':<12}")
print("-" * 100)
for r in results:
    print(f"{r['sl_mult']:<12.1f} {r['tp_mult']:<12.1f} {r['trades']:<10} {r['win_rate']:<10.1f} {r['pf']:<10.2f} {r['return_pct']:<12.2f}")

# Find best
if results:
    best = max(results, key=lambda x: x['pf'])
    print(f"\nBest configuration: SL={best['sl_mult']:.1f}x ATR, TP={best['tp_mult']:.1f}x ATR")
    print(f"  Profit Factor: {best['pf']:.2f}x")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  Return: {best['return_pct']:.2f}%")

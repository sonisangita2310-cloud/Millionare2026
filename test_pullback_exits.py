"""
PULLBACK EXIT OPTIMIZATION

Hypothesis:
  - Pullback entries are at different price points (closer to support)
  - May need tighter stops (entries already have less risk)
  - Or wider TP targets since we're entering on retracements
  
Test multiple SL/TP combinations on pullback v2:
  A) Current: 1.0x SL, 2.9x TP (0.84 PF, 13.33% return)
  B) Tighter: 0.7x SL, 2.5x TP
  C) Wider: 1.5x SL, 3.5x TP
  D) Aggressive: 0.8x SL, 3.5x TP (tight stop, wide TP)
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

def run_pullback_exit_test(sl_mult, tp_mult):
    """Test pullback strategy with different exit parameters."""
    
    print(f"\nTesting: SL={sl_mult}x ATR, TP={tp_mult}x ATR")
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    
    # Generate signals v2
    from pullback_signal_generator_v2 import ImprovedPullbackSignalGenerator
    gen = ImprovedPullbackSignalGenerator()
    signals_df = gen.generate_signals(data)
    
    # Add ATR
    data['atr'] = calculate_atr(data)
    
    # Backtest
    initial_capital = 100000
    position_size = 10000
    fee_pct = 0.001
    slippage_pct = 0.0003
    
    capital = initial_capital
    trades = []
    position = None
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        signal = signals_df.iloc[idx]['signal']
        
        if position is None and signal == 1:
            entry_price = candle['close']
            atr = candle['atr']
            
            if pd.isna(atr) or atr == 0:
                continue
            
            entry_fee = position_size * (fee_pct + slippage_pct)
            position = {
                'entry_idx': idx,
                'entry_price': entry_price,
                'stop_loss': entry_price - (sl_mult * atr),
                'take_profit': entry_price + (tp_mult * atr),
                'entry_fee': entry_fee,
            }
        
        elif position is not None:
            current_price = candle['close']
            exit_triggered = False
            exit_price = None
            
            if current_price <= position['stop_loss']:
                exit_triggered = True
                exit_price = position['stop_loss']
            elif current_price >= position['take_profit']:
                exit_triggered = True
                exit_price = position['take_profit']
            
            if exit_triggered:
                exit_fee = position_size * (fee_pct + slippage_pct)
                gross_pnl = (exit_price - position['entry_price']) * (position_size / position['entry_price'])
                net_pnl = gross_pnl - position['entry_fee'] - exit_fee
                
                trade = {
                    'net_pnl': net_pnl,
                    'winner': 1 if net_pnl > 0 else 0,
                }
                trades.append(trade)
                capital += net_pnl
                position = None
    
    # Analyze
    if len(trades) == 0:
        return None
    
    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['winner'] == 1]
    losers = trades_df[trades_df['winner'] == 0]
    
    total_win = winners['net_pnl'].sum() if len(winners) > 0 else 0
    total_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    pf = total_win / total_loss if total_loss > 0 else 0
    
    wr = len(winners) / len(trades_df) * 100
    total_return = total_win + total_loss
    total_return_pct = (total_return / 100000) * 100
    
    print(f"  Trades: {len(trades_df)}, WR: {wr:.1f}%, PF: {pf:.2f}x, Return: {total_return_pct:+.2f}%")
    
    return {
        'sl': sl_mult,
        'tp': tp_mult,
        'trades': len(trades_df),
        'wr': wr,
        'pf': pf,
        'return': total_return_pct,
    }

# Test multiple configurations
print("\n" + "=" * 100)
print("PULLBACK STRATEGY - EXIT PARAMETER OPTIMIZATION")
print("=" * 100)

configs = [
    (1.0, 2.9),  # Current
    (0.7, 2.5),  # Tighter
    (1.5, 3.5),  # Wider
    (0.8, 3.5),  # Aggressive
    (0.9, 3.0),  # Medium
    (1.2, 3.0),  # Medium-loose
]

results = []
for sl, tp in configs:
    result = run_pullback_exit_test(sl, tp)
    if result:
        results.append(result)

# Summary
print(f"\n{'=' * 100}")
print(f"SUMMARY: Pullback Exit Variations")
print(f"{'=' * 100}")
print(f"{'SL xATR':<10} {'TP xATR':<10} {'Trades':<10} {'WR %':<10} {'PF':<10} {'Return %':<12}")
print("-" * 100)
for r in results:
    print(f"{r['sl']:<10.1f} {r['tp']:<10.1f} {r['trades']:<10} {r['wr']:<10.1f} {r['pf']:<10.2f} {r['return']:<12.2f}")

# Find best by PF
if results:
    best_pf = max(results, key=lambda x: x['pf'])
    best_return = max(results, key=lambda x: x['return'])
    print(f"\nBest PF: SL={best_pf['sl']:.1f}x, TP={best_pf['tp']:.1f}x → {best_pf['pf']:.2f}x")
    print(f"Best Return: SL={best_return['sl']:.1f}x, TP={best_return['tp']:.1f}x → {best_return['return']:+.2f}%")

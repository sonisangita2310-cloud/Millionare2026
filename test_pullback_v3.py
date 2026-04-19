"""
BACKTEST PULLBACK v3 WITH OPTIMIZED EXITS

v3 improvements:
- Time-of-day filter (skip bad hours)
- Day-of-week filter (skip Friday)
- Better RSI targeting (45-65, avoid extremes)
- Tighter pullback range (0.2-1.0 instead of 0.15-1.5)
- Minimum trend strength (0.7x ATR from EMA)

Expected: Fewer but higher-quality signals, better win rate
Goal: Achieve PF > 1.1 with 38%+ win rate
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def calculate_atr(data, period=14):
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

def run_backtest_v3(sl_mult, tp_mult):
    """Run backtest on pullback v3 signals"""
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    data = data.reset_index()
    
    # Generate signals v3
    from pullback_signal_generator_v3 import PullbackSignalGeneratorV3
    gen = PullbackSignalGeneratorV3()
    
    data_indexed = data.set_index('timestamp')
    signals_df = gen.generate_signals(data_indexed)
    data['signal'] = signals_df['signal'].values
    
    # Add ATR
    data_indexed = data.set_index('timestamp')
    data_indexed['atr'] = calculate_atr(data_indexed)
    data['atr'] = data_indexed['atr'].values
    
    # Backtest
    initial_capital = 100000
    position_size = 10000
    fee_pct = 0.001
    slippage_pct = 0.0003
    
    trades = []
    position = None
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        signal = candle['signal']
        
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
            
            if current_price <= position['stop_loss']:
                exit_triggered = True
                exit_price = position['stop_loss']
            elif current_price >= position['take_profit']:
                exit_triggered = True
                exit_price = position['take_profit']
            else:
                exit_triggered = False
            
            if exit_triggered:
                exit_fee = position_size * (fee_pct + slippage_pct)
                gross_pnl = (exit_price - position['entry_price']) * (position_size / position['entry_price'])
                net_pnl = gross_pnl - position['entry_fee'] - exit_fee
                
                trade = {
                    'net_pnl': net_pnl,
                    'winner': 1 if net_pnl > 0 else 0,
                }
                trades.append(trade)
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
    
    return {
        'sl': sl_mult,
        'tp': tp_mult,
        'trades': len(trades_df),
        'wr': wr,
        'pf': pf,
        'return': total_return_pct,
    }

# Test configurations
print("\n" + "="*100)
print("PULLBACK v3 - TESTING OPTIMIZED EXIT CONFIGURATIONS")
print("="*100)

configs = [
    (0.8, 2.5),  # Tight SL, tight TP
    (0.9, 2.8),  # Medium-tight
    (1.0, 3.0),  # Balanced (breakout baseline)
    (0.8, 3.5),  # Aggressive TP
    (1.1, 3.2),  # Medium-loose
    (1.2, 3.5),  # Loose (wider targets)
]

results = []
for sl, tp in configs:
    result = run_backtest_v3(sl, tp)
    if result:
        results.append(result)
        print(f"\nSL={sl:.1f}x, TP={tp:.1f}x → Trades: {result['trades']}, WR: {result['wr']:.1f}%, PF: {result['pf']:.2f}x, Return: {result['return']:+.2f}%")

# Summary
print(f"\n{'='*100}")
print(f"SUMMARY")
print(f"{'='*100}")
print(f"{'SL':<8} {'TP':<8} {'Trades':<10} {'WR %':<10} {'PF':<10} {'Return %':<12}")
print("-"*100)
for r in results:
    print(f"{r['sl']:<8.1f} {r['tp']:<8.1f} {r['trades']:<10} {r['wr']:<10.1f} {r['pf']:<10.2f} {r['return']:<12.2f}")

if results:
    best_pf = max(results, key=lambda x: x['pf'])
    best_wr = max(results, key=lambda x: x['wr'])
    best_return = max(results, key=lambda x: x['return'])
    
    print(f"\n{'='*100}")
    print(f"BEST CONFIGURATIONS")
    print(f"{'='*100}")
    print(f"Best PF: SL={best_pf['sl']:.1f}x, TP={best_pf['tp']:.1f}x → {best_pf['pf']:.2f}x")
    print(f"Best WR: SL={best_wr['sl']:.1f}x, TP={best_wr['tp']:.1f}x → {best_wr['wr']:.1f}%")
    print(f"Best Return: SL={best_return['sl']:.1f}x, TP={best_return['tp']:.1f}x → {best_return['return']:+.2f}%")

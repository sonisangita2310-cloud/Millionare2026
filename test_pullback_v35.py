"""
BACKTEST PULLBACK v3.5 - BALANCED APPROACH

Testing v3.5 (relaxed v3) to find sweet spot between:
- v3: 26 trades, 1.18x PF (too few trades)
- v2: 99 trades, 0.84x PF (too many marginal winners)
- Target: 50-70 trades with PF > 1.05x
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

def run_backtest(signal_gen, sl_mult, tp_mult, name=""):
    """Run backtest on pullback signals"""
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    data = data.reset_index()
    
    # Generate signals
    data_indexed = data.set_index('timestamp')
    signals_df = signal_gen.generate_signals(data_indexed)
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
        'name': name,
    }

# Test v3.5
print("\n" + "="*100)
print("PULLBACK v3.5 - BALANCED QUALITY & FREQUENCY")
print("="*100)

from pullback_signal_generator_v35 import PullbackSignalGeneratorV35

gen = PullbackSignalGeneratorV35()

# First, count signals
data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')
data = data.iloc[-17520:]
signals = gen.generate_signals(data)
signal_count = signals['signal'].sum()
print(f"\nSignal count: {signal_count}")
print(f"Expected trades/month: {signal_count / 24:.1f}")

# Test configurations
configs = [
    (0.8, 2.5),
    (0.9, 2.8),
    (1.0, 3.0),
    (0.9, 3.0),
    (1.1, 3.2),
    (1.0, 3.2),
]

results = []
for sl, tp in configs:
    result = run_backtest(gen, sl, tp)
    if result:
        results.append(result)
        print(f"\nSL={sl:.1f}x, TP={tp:.1f}x → Trades: {result['trades']}, WR: {result['wr']:.1f}%, PF: {result['pf']:.2f}x, Return: {result['return']:+.2f}%")

# Summary
print(f"\n{'='*100}")
print(f"SUMMARY - v3.5 CONFIGURATIONS")
print(f"{'='*100}")
print(f"{'SL':<8} {'TP':<8} {'Trades':<10} {'WR %':<10} {'PF':<10} {'Return %':<12}")
print("-"*100)
for r in results:
    print(f"{r['sl']:<8.1f} {r['tp']:<8.1f} {r['trades']:<10} {r['wr']:<10.1f} {r['pf']:<10.2f} {r['return']:<12.2f}")

if results:
    best_pf = max(results, key=lambda x: x['pf'])
    best_return = max(results, key=lambda x: x['return'])
    best_wr = max(results, key=lambda x: x['wr'])
    
    print(f"\n{'='*100}")
    print(f"BEST CONFIGURATIONS")
    print(f"{'='*100}")
    print(f"Best PF: SL={best_pf['sl']:.1f}x, TP={best_pf['tp']:.1f}x → {best_pf['pf']:.2f}x ({best_pf['trades']} trades)")
    print(f"Best Return: SL={best_return['sl']:.1f}x, TP={best_return['tp']:.1f}x → {best_return['return']:+.2f}% ({best_return['trades']} trades)")
    print(f"Best WR: SL={best_wr['sl']:.1f}x, TP={best_wr['tp']:.1f}x → {best_wr['wr']:.1f}% ({best_wr['trades']} trades)")

"""
ROBUSTNESS TEST: WITH FILTERS vs WITHOUT FILTERS

Compare:
  - v3.5 (WITH time-of-day + day-of-week filters)
  - v3.5-NO-FILTERS (WITHOUT time filters)

Goal: Quantify how much edge comes ONLY from time-based filtering
      vs core strategy logic (pullback + RSI + trend + volume)
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

# Run comparison test
print("\n" + "="*100)
print("ROBUSTNESS TEST: IMPACT OF TIME-BASED FILTERS")
print("="*100)

print("\n[TEST 1] WITH TIME FILTERS (v3.5 - Current Strategy)")
from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
gen_with_filters = PullbackSignalGeneratorV35()

data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')
data = data.iloc[-17520:]
signals_with = gen_with_filters.generate_signals(data)
signal_count_with = signals_with['signal'].sum()
print(f"  Signals generated: {signal_count_with}")

result_with = run_backtest(gen_with_filters, 1.1, 3.2, "WITH Filters")
if result_with:
    print(f"  Trades: {result_with['trades']}")
    print(f"  Win Rate: {result_with['wr']:.1f}%")
    print(f"  Profit Factor: {result_with['pf']:.2f}x")
    print(f"  Return: {result_with['return']:+.2f}%")

print("\n[TEST 2] WITHOUT TIME FILTERS (v3.5-NO-FILTERS - Core Strategy Only)")
from pullback_signal_generator_v35_no_filters import PullbackSignalGeneratorV35NoFilters
gen_without_filters = PullbackSignalGeneratorV35NoFilters()

signals_without = gen_without_filters.generate_signals(data)
signal_count_without = signals_without['signal'].sum()
print(f"  Signals generated: {signal_count_without}")

result_without = run_backtest(gen_without_filters, 1.1, 3.2, "WITHOUT Filters")
if result_without:
    print(f"  Trades: {result_without['trades']}")
    print(f"  Win Rate: {result_without['wr']:.1f}%")
    print(f"  Profit Factor: {result_without['pf']:.2f}x")
    print(f"  Return: {result_without['return']:+.2f}%")

# Analysis
print(f"\n{'='*100}")
print(f"IMPACT ANALYSIS - How much improvement from time filters?")
print(f"{'='*100}")

if result_with and result_without:
    pf_diff = result_with['pf'] - result_without['pf']
    wr_diff = result_with['wr'] - result_without['wr']
    return_diff = result_with['return'] - result_without['return']
    signal_increase = ((signal_count_without - signal_count_with) / signal_count_without) * 100 if signal_count_without > 0 else 0
    trades_increase = ((result_without['trades'] - result_with['trades']) / result_without['trades']) * 100 if result_without['trades'] > 0 else 0
    
    print(f"\nSignals:")
    print(f"  WITH filters: {signal_count_with}")
    print(f"  WITHOUT filters: {signal_count_without}")
    print(f"  Reduction from filters: {signal_increase:.1f}%")
    
    print(f"\nMetrics Comparison:")
    print(f"  {'Metric':<30} {'WITH Filters':<20} {'WITHOUT Filters':<20} {'Difference':<15}")
    print("-" * 85)
    print(f"  {'PF':<30} {result_with['pf']:<20.2f} {result_without['pf']:<20.2f} {pf_diff:+.2f}x")
    print(f"  {'Win Rate':<30} {result_with['wr']:<20.1f}% {result_without['wr']:<20.1f}% {wr_diff:+.1f}%")
    print(f"  {'Return':<30} {result_with['return']:<20.2f}% {result_without['return']:<20.2f}% {return_diff:+.2f}%")
    print(f"  {'Trades':<30} {result_with['trades']:<20} {result_without['trades']:<20} {trades_increase:+.1f}%")
    
    print(f"\n{'='*100}")
    print(f"ROBUSTNESS VERDICT")
    print(f"{'='*100}")
    
    if result_without['pf'] >= 1.0:
        print(f"✅ ROBUST - Edge exists WITHOUT time filters (PF={result_without['pf']:.2f}x)")
        print(f"   Time filters improve PF by {pf_diff:.2f}x ({pf_diff/result_without['pf']*100:.1f}% boost)")
        print(f"   Core strategy is fundamentally profitable")
    elif result_without['pf'] >= 0.95:
        print(f"⚠️  PARTIALLY ROBUST - Core strategy near breakeven (PF={result_without['pf']:.2f}x)")
        print(f"   Time filters critical for profitability (+{pf_diff:.2f}x improvement)")
        print(f"   Risk: Dependent on time-based overfitting")
    else:
        print(f"❌ NOT ROBUST - Strategy unprofitable without time filters (PF={result_without['pf']:.2f}x)")
        print(f"   Time filters provide {pf_diff:.2f}x improvement")
        print(f"   CONCERN: Edge may be overfitted to time patterns")

"""
ANALYZE v3.5 PERFORMANCE BY YEAR - VERIFY CONSISTENT EDGE

Goal: Ensure the 1.24x PF is consistent across both years, not just lucky in one period
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

def run_backtest_by_period(signal_gen, sl_mult, tp_mult, start_idx, end_idx, period_name=""):
    """Run backtest on specific period"""
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]  # Load full 2 years
    data = data.reset_index()
    
    # Filter to period
    data = data.iloc[start_idx:end_idx].reset_index(drop=True)
    
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
        'period': period_name,
        'trades': len(trades_df),
        'wr': wr,
        'pf': pf,
        'return': total_return_pct,
    }

# Load data to find year boundaries
data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])

# Full 2 years: April 2024 - April 2026
total_rows = len(data)
mid_point = total_rows // 2

# Get dates
first_date = data['timestamp'].iloc[0]
mid_date = data['timestamp'].iloc[-8760]  # Roughly 1 year from end
last_date = data['timestamp'].iloc[-1]

print("\n" + "="*100)
print("PULLBACK v3.5 - YEAR-BY-YEAR PERFORMANCE ANALYSIS")
print("="*100)
print(f"Dataset: {first_date} to {last_date}")
print(f"Total candles: {total_rows}")

from pullback_signal_generator_v35 import PullbackSignalGeneratorV35
gen = PullbackSignalGeneratorV35()

# Load full data for analysis
full_data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
full_data['timestamp'] = pd.to_datetime(full_data['timestamp'])
full_data = full_data.set_index('timestamp')
full_data = full_data.iloc[-17520:]

# Year 1: First 8760 hours (1 year)
print(f"\nYEAR 1 (Apr 2024 - Apr 2025):")
year1_data = full_data.iloc[:8760].copy()
result1 = run_backtest_by_period(gen, 1.1, 3.2, 0, 8760, "Year 1")
if result1:
    print(f"  Trades: {result1['trades']}")
    print(f"  Win Rate: {result1['wr']:.1f}%")
    print(f"  Profit Factor: {result1['pf']:.2f}x")
    print(f"  Return: {result1['return']:+.2f}%")

# Year 2: Last 8760 hours (1 year)
print(f"\nYEAR 2 (Apr 2025 - Apr 2026):")
result2 = run_backtest_by_period(gen, 1.1, 3.2, 8760, 17520, "Year 2")
if result2:
    print(f"  Trades: {result2['trades']}")
    print(f"  Win Rate: {result2['wr']:.1f}%")
    print(f"  Profit Factor: {result2['pf']:.2f}x")
    print(f"  Return: {result2['return']:+.2f}%")

# Full 2 years
print(f"\nFULL 2 YEARS (Apr 2024 - Apr 2026):")
result_full = run_backtest_by_period(gen, 1.1, 3.2, 0, 17520, "Full Period")
if result_full:
    print(f"  Trades: {result_full['trades']}")
    print(f"  Win Rate: {result_full['wr']:.1f}%")
    print(f"  Profit Factor: {result_full['pf']:.2f}x")
    print(f"  Return: {result_full['return']:+.2f}%")

# Consistency analysis
print(f"\n{'='*100}")
print(f"CONSISTENCY ANALYSIS")
print(f"{'='*100}")

if result1 and result2:
    pf_diff = abs(result1['pf'] - result2['pf'])
    wr_diff = abs(result1['wr'] - result2['wr'])
    return_diff = abs(result1['return'] - result2['return'])
    
    print(f"PF Difference (Year 1 vs Year 2): {pf_diff:.3f}x")
    print(f"WR Difference (Year 1 vs Year 2): {wr_diff:.1f}%")
    print(f"Return Difference (Year 1 vs Year 2): {return_diff:.2f}%")
    
    if pf_diff < 0.15 and wr_diff < 10 and return_diff < 3:
        print(f"\n✓ CONSISTENT EDGE ACROSS YEARS")
    else:
        print(f"\n⚠ Performance varies between years - check for regime shifts")

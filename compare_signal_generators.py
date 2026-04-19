#!/usr/bin/env python3
"""
Improved Signal Generator Comparison
Compare original vs improved signal generation on 2-year dataset
Focus: Trade quality, profitability per trade, win rate
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pathlib import Path
from signal_generator import SignalGenerator as OriginalSignalGenerator
from improved_signal_generator import ImprovedSignalGenerator
from datetime import datetime, timedelta

print("="*120)
print("IMPROVED SIGNAL GENERATOR - QUALITY COMPARISON TEST")
print("="*120)

# ============================================================================
# CONFIGURATION
# ============================================================================
TRADING_FEE = 0.001  # 0.1%
SLIPPAGE = 0.0003   # 0.03%
INITIAL_CAPITAL = 100000

# Load data
print("\n[STEP 1] Loading 2-year data...")
data_path = Path('data_cache/BTC_USDT_1h.csv')
if not data_path.exists():
    print(f"ERROR: Data file not found: {data_path}")
    sys.exit(1)

df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

# Filter to 2-year range
end_date = pd.Timestamp("2026-04-17")
start_date = end_date - timedelta(days=365*2)
df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)

print(f"✓ Loaded {len(df_2yr):,} candles")

# Calculate indicators
print("\n[STEP 2] Calculating indicators...")
def calculate_atr(data, period=14):
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df_2yr['EMA_200'] = df_2yr['close'].ewm(span=200, adjust=False).mean()
df_2yr['ATR'] = calculate_atr(df_2yr, period=14)
df_2yr['HIGHEST_20_PREV'] = df_2yr['high'].shift(1).rolling(window=20).max()
df_2yr['LOWEST_20_PREV'] = df_2yr['low'].shift(1).rolling(window=20).min()
df_2yr['VOLUME_MA_20'] = df_2yr['volume'].rolling(window=20).mean()
df_2yr['RSI'] = calculate_rsi(df_2yr['close'], 14)
df_2yr['RANGE'] = df_2yr['high'] - df_2yr['low']
df_2yr['BODY'] = abs(df_2yr['close'] - df_2yr['open'])
df_2yr['BODY_PCTS'] = (df_2yr['BODY'] / df_2yr['RANGE']) * 100

print(f"✓ Indicators calculated")

# ============================================================================
# BACKTEST FUNCTION
# ============================================================================
def run_backtest(data, signal_gen, name="Backtest"):
    """Run backtest with given signal generator"""
    
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    entry_time = None
    sl_price = 0
    tp_price = 0
    position_size = 0
    
    equity = INITIAL_CAPITAL
    max_equity = INITIAL_CAPITAL
    min_equity = INITIAL_CAPITAL
    total_fees = 0
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        
        if not in_trade and idx > 200:
            entry_signal, strength = signal_gen.check_entry_signal(idx)
            
            if entry_signal is not None:
                atr = candle['ATR']
                sl_distance = 1.0 * atr
                position_size = (equity * 0.0025) / sl_distance if sl_distance > 0 else 0
                
                # Apply entry costs
                entry_cost = position_size * candle['close'] * (TRADING_FEE + SLIPPAGE)
                equity -= entry_cost
                total_fees += entry_cost
                
                if entry_signal == 'LONG':
                    entry_price = candle['close'] * (1 + SLIPPAGE)
                    sl_price = entry_price - sl_distance
                    tp_price = entry_price + (2.9 * atr)
                else:
                    entry_price = candle['close'] * (1 - SLIPPAGE)
                    sl_price = entry_price + sl_distance
                    tp_price = entry_price - (2.9 * atr)
                
                in_trade = True
                trade_type = entry_signal
                entry_time = candle['datetime']
        
        if in_trade:
            current_price = candle['close']
            
            if trade_type == 'LONG' and current_price <= sl_price:
                exit_price = sl_price * (1 - SLIPPAGE)
                pnl = (exit_price - entry_price) * position_size
                exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                pnl -= exit_fee
                equity += pnl
                total_fees += exit_fee
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': candle['datetime'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': trade_type,
                    'reason': 'SL'
                })
                in_trade = False
            
            elif trade_type == 'LONG' and current_price >= tp_price:
                exit_price = tp_price * (1 - SLIPPAGE)
                pnl = (exit_price - entry_price) * position_size
                exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                pnl -= exit_fee
                equity += pnl
                total_fees += exit_fee
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': candle['datetime'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': trade_type,
                    'reason': 'TP'
                })
                in_trade = False
            
            elif trade_type == 'SHORT' and current_price >= sl_price:
                exit_price = sl_price * (1 + SLIPPAGE)
                pnl = (entry_price - exit_price) * position_size
                exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                pnl -= exit_fee
                equity += pnl
                total_fees += exit_fee
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': candle['datetime'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': trade_type,
                    'reason': 'SL'
                })
                in_trade = False
            
            elif trade_type == 'SHORT' and current_price <= tp_price:
                exit_price = tp_price * (1 + SLIPPAGE)
                pnl = (entry_price - exit_price) * position_size
                exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                pnl -= exit_fee
                equity += pnl
                total_fees += exit_fee
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': candle['datetime'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': trade_type,
                    'reason': 'TP'
                })
                in_trade = False
        
        max_equity = max(max_equity, equity)
        min_equity = min(min_equity, equity)
    
    # Calculate metrics
    total_trades = len(trades)
    winning = [t for t in trades if t['pnl'] > 0]
    losing = [t for t in trades if t['pnl'] < 0]
    
    win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0
    total_wins = sum(t['pnl'] for t in winning)
    total_losses = abs(sum(t['pnl'] for t in losing))
    pf = total_wins / total_losses if total_losses > 0 else 0
    
    avg_win = (total_wins / len(winning)) if len(winning) > 0 else 0
    avg_loss = (total_losses / len(losing)) if len(losing) > 0 else 0
    
    max_dd = ((min_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100)
    return_pct = ((equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100)
    
    return {
        'trades': trades,
        'total_trades': total_trades,
        'wins': len(winning),
        'losses': len(losing),
        'win_rate': win_rate,
        'pf': pf,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_dd': max_dd,
        'equity': equity,
        'return_pct': return_pct,
        'fees': total_fees,
        'name': name
    }

# ============================================================================
# RUN COMPARISONS
# ============================================================================
print("\n" + "="*120)
print("COMPARING SIGNAL GENERATORS")
print("="*120)

print("\n[Testing ORIGINAL signal generator...]")
original_gen = OriginalSignalGenerator(df_2yr)
results_original = run_backtest(df_2yr, original_gen, "Original")

print(f"\n[Testing IMPROVED signal generator...]")
improved_gen = ImprovedSignalGenerator(df_2yr)
results_improved = run_backtest(df_2yr, improved_gen, "Improved")

# ============================================================================
# RESULTS COMPARISON
# ============================================================================
print("\n" + "="*120)
print("RESULTS COMPARISON - QUALITY METRICS")
print("="*120)

print(f"\n{'Metric':<30} {'Original':<20} {'Improved':<20} {'Change':<12} {'Improvement':<15}")
print("─" * 98)

# Trade count
trade_diff = results_improved['total_trades'] - results_original['total_trades']
trade_pct = (trade_diff / results_original['total_trades'] * 100) if results_original['total_trades'] > 0 else 0
print(f"{'Total Trades':<30} {results_original['total_trades']:<20} {results_improved['total_trades']:<20} {trade_diff:+.0f}{'':<7} {trade_pct:+.1f}%")

# Win rate
wr_diff = results_improved['win_rate'] - results_original['win_rate']
wr_pct = (wr_diff / results_original['win_rate'] * 100) if results_original['win_rate'] > 0 else 0
print(f"{'Win Rate':<30} {results_original['win_rate']:.1f}%{'':<15} {results_improved['win_rate']:.1f}%{'':<15} {wr_diff:+.1f}%{'':<6} {wr_pct:+.1f}%")

# Profit Factor
pf_diff = results_improved['pf'] - results_original['pf']
pf_pct = (pf_diff / results_original['pf'] * 100) if results_original['pf'] > 0 else 0
print(f"{'Profit Factor':<30} {results_original['pf']:.2f}x{'':<16} {results_improved['pf']:.2f}x{'':<16} {pf_diff:+.2f}x{'':<7} {pf_pct:+.1f}%")

# Average Win
aw_diff = results_improved['avg_win'] - results_original['avg_win']
aw_pct = (aw_diff / results_original['avg_win'] * 100) if results_original['avg_win'] > 0 else 0
print(f"{'Avg Win ($)':<30} {results_original['avg_win']:>8.0f}{'':<11} {results_improved['avg_win']:>8.0f}{'':<11} {aw_diff:+.0f}{'':<7} {aw_pct:+.1f}%")

# Average Loss
al_diff = results_improved['avg_loss'] - results_original['avg_loss']
al_pct = (al_diff / results_original['avg_loss'] * 100) if results_original['avg_loss'] > 0 else 0
print(f"{'Avg Loss ($)':<30} {results_original['avg_loss']:>8.0f}{'':<11} {results_improved['avg_loss']:>8.0f}{'':<11} {al_diff:+.0f}{'':<7} {al_pct:+.1f}%")

# Max Drawdown
dd_diff = results_improved['max_dd'] - results_original['max_dd']
dd_pct = (dd_diff / abs(results_original['max_dd']) * 100) if results_original['max_dd'] != 0 else 0
print(f"{'Max Drawdown':<30} {results_original['max_dd']:.2f}%{'':<14} {results_improved['max_dd']:.2f}%{'':<14} {dd_diff:+.2f}%{'':<7} {dd_pct:+.1f}%")

# Return
ret_diff = results_improved['return_pct'] - results_original['return_pct']
ret_pct = (ret_diff / results_original['return_pct'] * 100) if results_original['return_pct'] != 0 else 0
print(f"{'Total Return':<30} {results_original['return_pct']:.2f}%{'':<14} {results_improved['return_pct']:.2f}%{'':<14} {ret_diff:+.2f}%{'':<7} {ret_pct:+.1f}%")

# Final Equity
eq_diff = results_improved['equity'] - results_original['equity']
eq_pct = (eq_diff / INITIAL_CAPITAL * 100)
print(f"{'Final Equity':<30} ${results_original['equity']:>18,.0f} ${results_improved['equity']:>18,.0f} ${eq_diff:+.0f}{'':<5} {eq_pct:+.2f}%")

# ============================================================================
# QUALITY VERDICT
# ============================================================================
print("\n" + "="*120)
print("QUALITY ANALYSIS")
print("="*120)

print(f"\nKEY IMPROVEMENTS:")

# Count improvements
improvements = 0
if results_improved['win_rate'] > results_original['win_rate']:
    print(f"  ✓ Win Rate: {results_original['win_rate']:.1f}% → {results_improved['win_rate']:.1f}% (+{results_improved['win_rate'] - results_original['win_rate']:.1f}pp)")
    improvements += 1

if results_improved['pf'] > results_original['pf']:
    print(f"  ✓ Profit Factor: {results_original['pf']:.2f}x → {results_improved['pf']:.2f}x (+{pf_pct:.1f}%)")
    improvements += 1

if results_improved['avg_win'] > results_original['avg_win']:
    print(f"  ✓ Avg Win: ${results_original['avg_win']:.0f} → ${results_improved['avg_win']:.0f} (+{aw_pct:.1f}%)")
    improvements += 1

if abs(results_improved['max_dd']) < abs(results_original['max_dd']):
    print(f"  ✓ Max Drawdown: {results_original['max_dd']:.2f}% → {results_improved['max_dd']:.2f}% (reduced by {abs(dd_diff):.2f}%)")
    improvements += 1

if results_improved['total_trades'] < results_original['total_trades'] and results_improved['return_pct'] > results_original['return_pct']:
    print(f"  ✓ Fewer trades ({trade_diff:.0f}), higher return (+{ret_diff:.2f}%)")
    improvements += 1

print(f"\nTrade Frequency:")
print(f"  Original: {results_original['total_trades']} trades (37% win rate expected loss)")
print(f"  Improved: {results_improved['total_trades']} trades ({results_improved['win_rate']:.1f}% win rate)")

if results_improved['total_trades'] < results_original['total_trades']:
    reduction_pct = (1 - results_improved['total_trades'] / results_original['total_trades']) * 100
    print(f"  → {reduction_pct:.1f}% fewer trades (higher quality filtering)")
else:
    increase_pct = (results_improved['total_trades'] / results_original['total_trades'] - 1) * 100
    print(f"  → {increase_pct:.1f}% more trades (accepting additional opportunities)")

# Verdict
print(f"\n{'═'*98}")
if improvements >= 3:
    print(f"VERDICT: SIGNIFICANT QUALITY IMPROVEMENT ✓")
elif improvements >= 2:
    print(f"VERDICT: MODERATE QUALITY IMPROVEMENT ✓")
elif improvements >= 1:
    print(f"VERDICT: SLIGHT QUALITY IMPROVEMENT ✓")
else:
    print(f"VERDICT: NO IMPROVEMENT (Revert to original)")

print(f"{'═'*98}")

# Summary
print(f"\nSUMMARY:")
print(f"  Strategy: Breakout with trend filter + quality enhancements")
print(f"  Filter Additions: Market regime (volatility check) + Breakout strength + Momentum confirmation")
print(f"  Trade Quality Goal: Reduce losses from choppy market false signals")
print(f"  Result: {results_improved['total_trades']} trades, {results_improved['win_rate']:.1f}% win rate, PF {results_improved['pf']:.2f}x")

print("\n" + "="*120)

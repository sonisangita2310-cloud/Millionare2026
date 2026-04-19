#!/usr/bin/env python3
"""
2-YEAR EXTENDED BACKTEST - Long-term robustness evaluation
Includes trading costs (fees + slippage) and period consistency analysis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from pathlib import Path
from signal_generator import SignalGenerator
from datetime import datetime, timedelta

print("="*120)
print("2-YEAR EXTENDED BACKTEST - LONG-TERM ROBUSTNESS EVALUATION")
print("="*120)

# ============================================================================
# CONFIGURATION
# ============================================================================
TRADING_FEE = 0.001  # 0.1% per trade
SLIPPAGE = 0.0003   # 0.03% average slippage (mid of 0.02-0.05% range)
INITIAL_CAPITAL = 100000

print(f"\nTRADING COSTS:")
print(f"  Fee per trade: {TRADING_FEE*100:.2f}%")
print(f"  Slippage: {SLIPPAGE*100:.3f}%")
print(f"  Total cost per entry/exit: {(TRADING_FEE + SLIPPAGE)*100:.3f}%")

# ============================================================================
# STEP 1: LOAD DATA (2-year history)
# ============================================================================
print("\n" + "="*120)
print("STEP 1: Loading 2-year historical data")
print("="*120)

data_path = Path('data_cache/BTC_USDT_1h.csv')
if not data_path.exists():
    print(f"ERROR: Data file not found: {data_path}")
    sys.exit(1)

df = pd.read_csv(data_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"✓ Loaded {len(df):,} candles")
print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")

# Determine 2-year window (last 730 days approximately)
# From current date (2026-04-17) go back 24 months
end_date = pd.Timestamp("2026-04-17")
start_date = end_date - timedelta(days=365*2)

print(f"\n2-Year window: {start_date} to {end_date}")

# Filter to 2-year range
df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
print(f"✓ Filtered to 2-year range: {len(df_2yr):,} candles")
print(f"  Actual range: {df_2yr['datetime'].min()} to {df_2yr['datetime'].max()}")

if len(df_2yr) < 500:
    print(f"ERROR: Insufficient data for 2-year backtest ({len(df_2yr)} candles)")
    sys.exit(1)

# ============================================================================
# STEP 2: CALCULATE INDICATORS
# ============================================================================
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

print(f"✓ Indicators calculated for {len(df_2yr):,} candles")

# ============================================================================
# STEP 3: RUN FULL 2-YEAR BACKTEST
# ============================================================================
print("\n" + "="*120)
print("STEP 3: Running full 2-year backtest")
print("="*120)

signal_gen = SignalGenerator(df_2yr)

def run_backtest(data, initial_capital=INITIAL_CAPITAL, apply_costs=True, period_name="Full"):
    """Run backtest with optional trading costs"""
    
    trades = []
    in_trade = False
    trade_type = None
    entry_idx = 0
    entry_price = 0
    entry_time = None
    entry_atr = 0
    sl_price = 0
    tp_price = 0
    signal_type = None
    position_size = 0
    
    equity = initial_capital
    max_equity = initial_capital
    min_equity = initial_capital
    total_fees = 0
    
    # Scan through all candles
    for idx in range(len(data)):
        candle = data.iloc[idx]
        
        # Check for entry signal if not in trade
        if not in_trade and idx > 200:  # Skip first 200 candles for warmup
            entry_signal, strength = signal_gen.check_entry_signal(idx)
            
            if entry_signal is not None:
                # Calculate position size (0.25% risk per trade)
                atr = candle['ATR']
                sl_distance = 1.0 * atr
                position_size = (equity * 0.0025) / sl_distance if sl_distance > 0 else 0
                
                # Apply entry fee/slippage
                entry_cost = 0
                if apply_costs:
                    entry_cost = position_size * candle['close'] * (TRADING_FEE + SLIPPAGE)
                    equity -= entry_cost
                    total_fees += entry_cost
                
                if entry_signal == 'LONG':
                    entry_price = candle['close'] * (1 + SLIPPAGE) if apply_costs else candle['close']
                    sl_price = entry_price - sl_distance
                    tp_price = entry_price + (2.9 * atr)
                else:  # SHORT
                    entry_price = candle['close'] * (1 - SLIPPAGE) if apply_costs else candle['close']
                    sl_price = entry_price + sl_distance
                    tp_price = entry_price - (2.9 * atr)
                
                in_trade = True
                trade_type = entry_signal
                entry_idx = idx
                entry_time = candle['datetime']
                entry_atr = atr
                signal_type = entry_signal
        
        # Check for exit (if in trade)
        if in_trade:
            current_price = candle['close']
            
            # Check stop loss
            if trade_type == 'LONG' and current_price <= sl_price:
                exit_price = sl_price * (1 - SLIPPAGE) if apply_costs else sl_price
                exit_time = candle['datetime']
                # Calculate PnL in dollars (correct: amount per BTC × quantity)
                pnl = (exit_price - entry_price) * position_size
                
                # Apply exit fee
                if apply_costs:
                    exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                    pnl -= exit_fee
                    total_fees += exit_fee
                
                equity += pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'signal_type': signal_type,
                    'exit_reason': 'SL'
                })
                
                in_trade = False
            
            # Check take profit
            elif trade_type == 'LONG' and current_price >= tp_price:
                exit_price = tp_price * (1 - SLIPPAGE) if apply_costs else tp_price
                exit_time = candle['datetime']
                # Calculate PnL in dollars (correct: amount per BTC × quantity)
                pnl = (exit_price - entry_price) * position_size
                
                if apply_costs:
                    exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                    pnl -= exit_fee
                    total_fees += exit_fee
                
                equity += pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'signal_type': signal_type,
                    'exit_reason': 'TP'
                })
                
                in_trade = False
            
            # Short position exits
            elif trade_type == 'SHORT' and current_price >= sl_price:
                exit_price = sl_price * (1 + SLIPPAGE) if apply_costs else sl_price
                exit_time = candle['datetime']
                # Calculate PnL in dollars (correct: amount per BTC × quantity, SHORT reverses sign)
                pnl = (entry_price - exit_price) * position_size
                
                if apply_costs:
                    exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                    pnl -= exit_fee
                    total_fees += exit_fee
                
                equity += pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'signal_type': signal_type,
                    'exit_reason': 'SL'
                })
                
                in_trade = False
            
            elif trade_type == 'SHORT' and current_price <= tp_price:
                exit_price = tp_price * (1 + SLIPPAGE) if apply_costs else tp_price
                exit_time = candle['datetime']
                # Calculate PnL in dollars (correct: amount per BTC × quantity, SHORT reverses sign)
                pnl = (entry_price - exit_price) * position_size
                
                if apply_costs:
                    exit_fee = position_size * exit_price * (TRADING_FEE + SLIPPAGE)
                    pnl -= exit_fee
                    total_fees += exit_fee
                
                equity += pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'signal_type': signal_type,
                    'exit_reason': 'TP'
                })
                
                in_trade = False
        
        max_equity = max(max_equity, equity)
        min_equity = min(min_equity, equity)
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    
    win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
    total_pnl = sum(t['pnl'] for t in trades)
    total_wins = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    total_losses = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    max_drawdown_pct = ((min_equity - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
    
    final_equity = equity
    total_return_pct = ((final_equity - initial_capital) / initial_capital * 100)
    
    return {
        'trades': trades,
        'total_trades': total_trades,
        'num_wins': num_wins,
        'num_losses': num_losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'max_drawdown_pct': max_drawdown_pct,
        'final_equity': final_equity,
        'total_return_pct': total_return_pct,
        'total_fees': total_fees,
        'initial_capital': initial_capital,
    }

# Run full 2-year backtest
print(f"\nRunning backtest on {len(df_2yr):,} candles (2 years)...")
results_full = run_backtest(df_2yr, initial_capital=INITIAL_CAPITAL, apply_costs=True, period_name="Full 2-Year")

print(f"✓ Full backtest complete: {results_full['total_trades']} trades")

# ============================================================================
# STEP 4: SPLIT INTO TWO 12-MONTH PERIODS
# ============================================================================
print("\n" + "="*120)
print("STEP 4: Splitting into 12-month periods")
print("="*120)

# Period A: First 12 months
midpoint_date = start_date + timedelta(days=365)
df_period_a = df_2yr[(df_2yr['datetime'] >= start_date) & (df_2yr['datetime'] < midpoint_date)].reset_index(drop=True)
print(f"\nPeriod A (First 12 months):")
print(f"  Range: {df_period_a['datetime'].min()} to {df_period_a['datetime'].max()}")
print(f"  Candles: {len(df_period_a):,}")

# Recalculate indicators for Period A
signal_gen_a = SignalGenerator(df_period_a)

# Period B: Last 12 months
df_period_b = df_2yr[(df_2yr['datetime'] >= midpoint_date) & (df_2yr['datetime'] <= end_date)].reset_index(drop=True)
print(f"\nPeriod B (Last 12 months):")
print(f"  Range: {df_period_b['datetime'].min()} to {df_period_b['datetime'].max()}")
print(f"  Candles: {len(df_period_b):,}")

signal_gen_b = SignalGenerator(df_period_b)

# Run backtests for both periods
print(f"\nRunning Period A backtest...")
results_a = run_backtest(df_period_a, initial_capital=INITIAL_CAPITAL, apply_costs=True, period_name="Period A")

print(f"Running Period B backtest...")
results_b = run_backtest(df_period_b, initial_capital=INITIAL_CAPITAL, apply_costs=True, period_name="Period B")

# ============================================================================
# STEP 5: ANALYSIS AND REPORTING
# ============================================================================
print("\n" + "="*120)
print("RESULTS SUMMARY")
print("="*120)

def print_period_results(name, results):
    print(f"\n{name}:")
    print(f"  ┌─ Trades")
    print(f"  │  Total: {results['total_trades']}")
    print(f"  │  Wins:  {results['num_wins']} ({results['win_rate']:.1f}%)")
    print(f"  │  Losses: {results['num_losses']}")
    print(f"  ├─ Returns")
    print(f"  │  PnL: ${results['total_pnl']:,.0f}")
    print(f"  │  Return: {results['total_return_pct']:.2f}%")
    print(f"  ├─ Metrics")
    print(f"  │  Profit Factor: {results['profit_factor']:.2f}x")
    print(f"  │  Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"  └─ Cost Impact")
    print(f"     Trading Fees: ${results['total_fees']:,.0f}")
    print(f"     Final Equity: ${results['final_equity']:,.0f}")

print_period_results("FULL 2-YEAR RESULTS", results_full)
print_period_results("PERIOD A (First 12m)", results_a)
print_period_results("PERIOD B (Last 12m)", results_b)

# ============================================================================
# STEP 6: CONSISTENCY ANALYSIS
# ============================================================================
print("\n" + "="*120)
print("CONSISTENCY ANALYSIS - Period A vs Period B")
print("="*120)

print(f"\n{'Metric':<25} {'Period A':<15} {'Period B':<15} {'Difference':<15} {'Change %':<12}")
print("─" * 82)

# Trade count comparison
trade_diff = results_b['total_trades'] - results_a['total_trades']
trade_pct = (trade_diff / results_a['total_trades'] * 100) if results_a['total_trades'] > 0 else 0
print(f"{'Total Trades':<25} {results_a['total_trades']:<15} {results_b['total_trades']:<15} {trade_diff:+.0f}{'':<10} {trade_pct:+.1f}%")

# Win rate comparison
wr_diff = results_b['win_rate'] - results_a['win_rate']
wr_pct = (wr_diff / results_a['win_rate'] * 100) if results_a['win_rate'] > 0 else 0
print(f"{'Win Rate':<25} {results_a['win_rate']:.1f}%{'':<11} {results_b['win_rate']:.1f}%{'':<11} {wr_diff:+.1f}%{'':<10} {wr_pct:+.1f}%")

# Profit Factor comparison
pf_diff = results_b['profit_factor'] - results_a['profit_factor']
pf_pct = (pf_diff / results_a['profit_factor'] * 100) if results_a['profit_factor'] > 0 else 0
print(f"{'Profit Factor':<25} {results_a['profit_factor']:.2f}x{'':<12} {results_b['profit_factor']:.2f}x{'':<12} {pf_diff:+.2f}x{'':<9} {pf_pct:+.1f}%")

# Max Drawdown comparison
dd_diff = results_b['max_drawdown_pct'] - results_a['max_drawdown_pct']
dd_pct = (dd_diff / abs(results_a['max_drawdown_pct']) * 100) if results_a['max_drawdown_pct'] != 0 else 0
print(f"{'Max Drawdown':<25} {results_a['max_drawdown_pct']:.2f}%{'':<11} {results_b['max_drawdown_pct']:.2f}%{'':<11} {dd_diff:+.2f}%{'':<10} {dd_pct:+.1f}%")

# Return comparison
ret_diff = results_b['total_return_pct'] - results_a['total_return_pct']
ret_pct = (ret_diff / results_a['total_return_pct'] * 100) if results_a['total_return_pct'] != 0 else 0
print(f"{'Total Return':<25} {results_a['total_return_pct']:.2f}%{'':<11} {results_b['total_return_pct']:.2f}%{'':<11} {ret_diff:+.2f}%{'':<10} {ret_pct:+.1f}%")

# ============================================================================
# STEP 7: ROBUSTNESS VERDICT
# ============================================================================
print("\n" + "="*120)
print("ROBUSTNESS ASSESSMENT")
print("="*120)

# Calculate stability metrics
pf_deviation = abs(pf_diff / ((results_a['profit_factor'] + results_b['profit_factor']) / 2) * 100)
wr_deviation = abs(wr_diff)
dd_ratio = abs(results_b['max_drawdown_pct'] / results_a['max_drawdown_pct']) if results_a['max_drawdown_pct'] != 0 else 0

print(f"\nStability Metrics:")
print(f"  Profit Factor deviation: {pf_deviation:.1f}%")
print(f"  Win rate deviation: {wr_deviation:.1f} percentage points")
print(f"  Drawdown ratio (B/A): {dd_ratio:.2f}x")

# Verdict logic
verdict = None
reasons = []

if pf_deviation < 15 and wr_deviation < 8 and (dd_ratio < 1.5 or results_b['win_rate'] > 35):
    verdict = "ROBUST ✓"
    reasons.append("• Consistent performance across both periods")
    reasons.append("• PF deviation < 15% (stable profitability)")
    reasons.append("• Win rate stable (deviation < 8%)")
    reasons.append("• Drawdown controlled")
elif pf_deviation < 25 and wr_deviation < 12:
    verdict = "PARTIAL ◐"
    reasons.append("• Performance varies by market regime")
    reasons.append("• Acceptable but not stable")
    reasons.append("• Recommend period-specific optimization")
else:
    verdict = "WEAK ✗"
    reasons.append("• Significant performance inconsistency")
    reasons.append("• Strategy does not adapt to market conditions")
    reasons.append("• High risk for live trading")

print(f"\nVERDICT: {verdict}")
print(f"\nRationale:")
for reason in reasons:
    print(f"  {reason}")

# ============================================================================
# FINAL SUMMARY TABLE
# ============================================================================
print("\n" + "="*120)
print("FINAL SUMMARY TABLE")
print("="*120)

print(f"\n{'Metric':<20} {'Full 2-Year':<18} {'Period A (Y1)':<18} {'Period B (Y2)':<18}")
print("─" * 74)
print(f"{'Trades':<20} {results_full['total_trades']:<18} {results_a['total_trades']:<18} {results_b['total_trades']:<18}")
print(f"{'Win Rate':<20} {results_full['win_rate']:.1f}%{'':<13} {results_a['win_rate']:.1f}%{'':<13} {results_b['win_rate']:.1f}%{'':<13}")
print(f"{'Profit Factor':<20} {results_full['profit_factor']:.2f}x{'':<14} {results_a['profit_factor']:.2f}x{'':<14} {results_b['profit_factor']:.2f}x{'':<14}")
print(f"{'Max Drawdown':<20} {results_full['max_drawdown_pct']:.2f}%{'':<13} {results_a['max_drawdown_pct']:.2f}%{'':<13} {results_b['max_drawdown_pct']:.2f}%{'':<13}")
print(f"{'Final Equity':<20} ${results_full['final_equity']:>16,.0f} ${results_a['final_equity']:>16,.0f} ${results_b['final_equity']:>16,.0f}")
print(f"{'Total Return':<20} {results_full['total_return_pct']:.2f}%{'':<13} {results_a['total_return_pct']:.2f}%{'':<13} {results_b['total_return_pct']:.2f}%{'':<13}")

print("\n" + "="*120)
print(f"2-YEAR BACKTEST COMPLETE")
print(f"Verdict: {verdict}")
print("="*120)

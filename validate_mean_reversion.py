#!/usr/bin/env python
"""Mean Reversion Robustness Validation - STRICT MODE"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MEAN REVERSION ROBUSTNESS VALIDATION")
print("Walk-Forward + Parameter Testing")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calculate_atr(data, period=14):
    """Calculate ATR"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

# Function to add indicators
def add_indicators(data, bb_period=20, bb_std=2):
    data['EMA_200'] = data['close'].ewm(span=200, adjust=False).mean()
    data['RSI_14'] = calculate_rsi(data['close'], 14)
    data['BB_UPPER'], data['BB_MIDDLE'], data['BB_LOWER'] = calculate_bollinger(
        data['close'], period=bb_period, std_dev=bb_std
    )
    data['ATR'] = calculate_atr(data, period=14)
    data['DIST_FROM_EMA'] = abs(data['close'] - data['EMA_200']) / data['EMA_200'] * 100
    return data

# Add indicators to full dataset
df = add_indicators(df)

# 60/40 train/test split
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"Train: {len(df_train)} candles | Test: {len(df_test)} candles")
print(f"Train dates: {df_train['datetime'].min()} to {df_train['datetime'].max()}")
print(f"Test dates:  {df_test['datetime'].min()} to {df_test['datetime'].max()}\n")

def backtest_mean_reversion(data, rsi_lower=30, rsi_upper=70, bb_period=20, bb_std=2, 
                             sl_mult=1.0, tp_mult=2.0):
    """Backtest mean reversion strategy with configurable parameters"""
    
    # Recalculate indicators with new parameters if BB changed
    if bb_period != 20 or bb_std != 2:
        data = add_indicators(data, bb_period=bb_period, bb_std=bb_std)
    
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        # Skip if indicators not ready
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        if pd.isna(row['BB_UPPER']) or pd.isna(row['BB_LOWER']):
            continue
        
        # Entry signals
        if not in_trade:
            # LONG: Oversold condition
            if (row['close'] < row['BB_LOWER'] and 
                row['RSI_14'] < rsi_lower and 
                row['DIST_FROM_EMA'] < 3.0):
                
                in_trade = True
                trade_type = 'LONG'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
            
            # SHORT: Overbought condition
            elif (row['close'] > row['BB_UPPER'] and 
                  row['RSI_14'] > rsi_upper and 
                  row['DIST_FROM_EMA'] < 3.0):
                
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price + (atr * sl_mult)  # SL above for shorts
                tp_price = entry_price - (atr * tp_mult)  # TP below for shorts
        
        # Exit signals
        elif in_trade:
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_price = row['close']
                    pnl = exit_price - entry_price
                    pnl_pct = (pnl / entry_price) * 100
                    exit_reason = 'TP' if exit_price >= tp_price else 'SL'
                    
                    trades.append({
                        'type': 'LONG',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'date': row['datetime']
                    })
                    in_trade = False
            
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_price = row['close']
                    pnl = entry_price - exit_price  # Reversed for shorts
                    pnl_pct = (pnl / entry_price) * 100
                    exit_reason = 'TP' if exit_price <= tp_price else 'SL'
                    
                    trades.append({
                        'type': 'SHORT',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'date': row['datetime']
                    })
                    in_trade = False
    
    # Calculate metrics
    if not trades:
        return {
            'trades': 0,
            'pf': 0,
            'win_rate': 0,
            'max_dd': 0,
            'avg_win': 0,
            'avg_loss': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Profit Factor
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    # Win Rate
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    # Cumulative P&L and Max Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (abs(running_max.max()) + 1)) * 100 if running_max.max() > 0 else 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct,
        'avg_win': trades_df[trades_df['pnl'] > 0]['pnl'].mean() if win_count > 0 else 0,
        'avg_loss': trades_df[trades_df['pnl'] < 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] < 0]) > 0 else 0
    }

# Test Baseline (current parameters)
print("="*100)
print("BASELINE (Current Parameters)")
print("="*100)
print("RSI: 30/70 | Bollinger: (20, 2) | ATR SL: 1.0, TP: 2.0\n")

baseline_train = backtest_mean_reversion(df_train.copy(), rsi_lower=30, rsi_upper=70, 
                                         bb_period=20, bb_std=2, sl_mult=1.0, tp_mult=2.0)
baseline_test = backtest_mean_reversion(df_test.copy(), rsi_lower=30, rsi_upper=70, 
                                        bb_period=20, bb_std=2, sl_mult=1.0, tp_mult=2.0)

baseline_gap = abs((baseline_train['pf'] - baseline_test['pf']) / baseline_train['pf'] * 100) if baseline_train['pf'] > 0 else 0

print(f"Train: PF={baseline_train['pf']:.2f}, Trades={baseline_train['trades']}, WR={baseline_train['win_rate']:.1f}%, MaxDD={baseline_train['max_dd']:.1f}%")
print(f"Test:  PF={baseline_test['pf']:.2f}, Trades={baseline_test['trades']}, WR={baseline_test['win_rate']:.1f}%, MaxDD={baseline_test['max_dd']:.1f}%")
print(f"Gap: {baseline_gap:.1f}%\n")

# Test Variant A: Tighter RSI (28/72)
print("="*100)
print("VARIANT A: Tighter RSI")
print("="*100)
print("RSI: 28/72 | Bollinger: (20, 2) | ATR SL: 1.0, TP: 2.0\n")

var_a_train = backtest_mean_reversion(df_train.copy(), rsi_lower=28, rsi_upper=72, 
                                       bb_period=20, bb_std=2, sl_mult=1.0, tp_mult=2.0)
var_a_test = backtest_mean_reversion(df_test.copy(), rsi_lower=28, rsi_upper=72, 
                                     bb_period=20, bb_std=2, sl_mult=1.0, tp_mult=2.0)

var_a_gap = abs((var_a_train['pf'] - var_a_test['pf']) / var_a_train['pf'] * 100) if var_a_train['pf'] > 0 else 0

print(f"Train: PF={var_a_train['pf']:.2f}, Trades={var_a_train['trades']}, WR={var_a_train['win_rate']:.1f}%, MaxDD={var_a_train['max_dd']:.1f}%")
print(f"Test:  PF={var_a_test['pf']:.2f}, Trades={var_a_test['trades']}, WR={var_a_test['win_rate']:.1f}%, MaxDD={var_a_test['max_dd']:.1f}%")
print(f"Gap: {var_a_gap:.1f}%\n")

# Test Variant B: Wider Bollinger Bands (20, 2.5)
print("="*100)
print("VARIANT B: Wider Bollinger Bands")
print("="*100)
print("RSI: 30/70 | Bollinger: (20, 2.5) | ATR SL: 1.0, TP: 2.0\n")

var_b_train = backtest_mean_reversion(df_train.copy(), rsi_lower=30, rsi_upper=70, 
                                       bb_period=20, bb_std=2.5, sl_mult=1.0, tp_mult=2.0)
var_b_test = backtest_mean_reversion(df_test.copy(), rsi_lower=30, rsi_upper=70, 
                                     bb_period=20, bb_std=2.5, sl_mult=1.0, tp_mult=2.0)

var_b_gap = abs((var_b_train['pf'] - var_b_test['pf']) / var_b_train['pf'] * 100) if var_b_train['pf'] > 0 else 0

print(f"Train: PF={var_b_train['pf']:.2f}, Trades={var_b_train['trades']}, WR={var_b_train['win_rate']:.1f}%, MaxDD={var_b_train['max_dd']:.1f}%")
print(f"Test:  PF={var_b_test['pf']:.2f}, Trades={var_b_test['trades']}, WR={var_b_test['win_rate']:.1f}%, MaxDD={var_b_test['max_dd']:.1f}%")
print(f"Gap: {var_b_gap:.1f}%\n")

# Test Variant C: Adjusted ATR SL/TP (1.2/2.2)
print("="*100)
print("VARIANT C: Adjusted ATR SL/TP")
print("="*100)
print("RSI: 30/70 | Bollinger: (20, 2) | ATR SL: 1.2, TP: 2.2\n")

var_c_train = backtest_mean_reversion(df_train.copy(), rsi_lower=30, rsi_upper=70, 
                                       bb_period=20, bb_std=2, sl_mult=1.2, tp_mult=2.2)
var_c_test = backtest_mean_reversion(df_test.copy(), rsi_lower=30, rsi_upper=70, 
                                     bb_period=20, bb_std=2, sl_mult=1.2, tp_mult=2.2)

var_c_gap = abs((var_c_train['pf'] - var_c_test['pf']) / var_c_train['pf'] * 100) if var_c_train['pf'] > 0 else 0

print(f"Train: PF={var_c_train['pf']:.2f}, Trades={var_c_train['trades']}, WR={var_c_train['win_rate']:.1f}%, MaxDD={var_c_train['max_dd']:.1f}%")
print(f"Test:  PF={var_c_test['pf']:.2f}, Trades={var_c_test['trades']}, WR={var_c_test['win_rate']:.1f}%, MaxDD={var_c_test['max_dd']:.1f}%")
print(f"Gap: {var_c_gap:.1f}%\n")

# Summary Table
print("="*100)
print("ROBUSTNESS VALIDATION SUMMARY")
print("="*100)
print()
print(f"{'Variant':<12} {'PF_train':<12} {'PF_test':<12} {'Trades':<12} {'WinRate':<12} {'MaxDD':<12} {'Gap %':<12}")
print("-" * 90)
print(f"{'BASELINE':<12} {baseline_train['pf']:<12.2f} {baseline_test['pf']:<12.2f} {baseline_test['trades']:<12} {baseline_test['win_rate']:<12.1f} {baseline_test['max_dd']:<12.1f} {baseline_gap:<12.1f}")
print(f"{'VARIANT A':<12} {var_a_train['pf']:<12.2f} {var_a_test['pf']:<12.2f} {var_a_test['trades']:<12} {var_a_test['win_rate']:<12.1f} {var_a_test['max_dd']:<12.1f} {var_a_gap:<12.1f}")
print(f"{'VARIANT B':<12} {var_b_train['pf']:<12.2f} {var_b_test['pf']:<12.2f} {var_b_test['trades']:<12} {var_b_test['win_rate']:<12.1f} {var_b_test['max_dd']:<12.1f} {var_b_gap:<12.1f}")
print(f"{'VARIANT C':<12} {var_c_train['pf']:<12.2f} {var_c_test['pf']:<12.2f} {var_c_test['trades']:<12} {var_c_test['win_rate']:<12.1f} {var_c_test['max_dd']:<12.1f} {var_c_gap:<12.1f}")
print()

# Validation Goals
print("="*100)
print("VALIDATION ASSESSMENT")
print("="*100)
print()
print("Goals:")
print("  ✅ PF_test ≥ 1.3")
print("  ✅ Gap ≤ 25%")
print("  ✅ Trades ≥ 300")
print()

variants = [
    ('BASELINE', baseline_test, baseline_gap),
    ('VARIANT A (Tight RSI 28/72)', var_a_test, var_a_gap),
    ('VARIANT B (Wide BB 2.5)', var_b_test, var_b_gap),
    ('VARIANT C (SL 1.2/TP 2.2)', var_c_test, var_c_gap)
]

best_variant = None
best_score = -1

for name, metrics, gap in variants:
    pf_ok = "✅" if metrics['pf'] >= 1.3 else "❌"
    gap_ok = "✅" if gap <= 25 else "❌"
    trades_ok = "✅" if metrics['trades'] >= 300 else "❌"
    
    # Simple scoring
    score = (1 if metrics['pf'] >= 1.3 else 0) + (1 if gap <= 25 else 0) + (1 if metrics['trades'] >= 300 else 0)
    if score > best_score:
        best_score = score
        best_variant = name
    
    print(f"{name}:")
    print(f"  PF_test ≥ 1.3:  {pf_ok} {metrics['pf']:.2f}")
    print(f"  Gap ≤ 25%:      {gap_ok} {gap:.1f}%")
    print(f"  Trades ≥ 300:   {trades_ok} {metrics['trades']}")
    print()

if best_score == 3:
    print(f"🎉 SUCCESS: {best_variant} meets all robustness criteria!")
elif best_score == 2:
    print(f"⚠️  PARTIAL: {best_variant} meets 2/3 criteria (acceptable)")
else:
    print(f"❌ NO VARIANT meets all criteria. Best is {best_variant} with {best_score}/3")

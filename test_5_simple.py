#!/usr/bin/env python
"""Simple direct backtest for 5 S001_E configurations using cached ETH data"""

import sys
import os
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from pathlib import Path

# Load cached data directly
print("="*80)
print("S001_E - 5 Configuration Test (Direct Backtest)")
print("="*80)
print("\nLoading ETH 3m cached data...")

eth_3m_path = Path('data_cache/ETH_USDT_3m.csv')
if not eth_3m_path.exists():
    print("ERROR: ETH_USDT_3m.csv not found")
    sys.exit(1)

df = pd.read_csv(eth_3m_path)
if 'timestamp' in df.columns:
    df['datetime'] = pd.to_datetime(df['timestamp'])
elif 'Datetime' in df.columns:
    df['datetime'] = pd.to_datetime(df['Datetime'])
else:
    print("ERROR: Could not find datetime column")
    sys.exit(1)
df = df.sort_values('datetime').reset_index(drop=True)

print(f"Loaded {len(df)} candles")
print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")

# Helper function to calculate RSI
def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Get latest 100 days for faster testing
days_ago = df['datetime'].max() - pd.Timedelta(days=100)
df = df[df['datetime'] >= days_ago].reset_index(drop=True)
print(f"Using last 100 days: {len(df)} candles\n")

# Calculate indicators required by S001
df['EMA_200_3m'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = df[['high', 'low', 'close']].apply(
    lambda x: max(x['high'] - x['low'], 
                  abs(x['high'] - x['close']),
                  abs(x['low'] - x['close'])), axis=1)
df['ATR'] = df['ATR'].rolling(window=14).mean()

# Higher timeframe data: group into 1h candles
df_1h = df.set_index('datetime').resample('1H').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_1h['RSI_14'] = calculate_rsi(df_1h['close'], 14)
df_1h['EMA_200_1h'] = df_1h['close'].ewm(span=200, adjust=False).mean()

print(f"{'SL':<6} {'TP':<6} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

# Configurations to test
configs = [
    {"sl": 1.0, "tp": 3.0},
    {"sl": 1.0, "tp": 4.0},
    {"sl": 0.8, "tp": 3.5},
    {"sl": 1.2, "tp": 4.0},
    {"sl": 1.0, "tp": 2.5},
]

results = []

for config in configs:
    trades = []
    in_trade = False
    entry_price = 0
    entry_idx = 0
    sl = 0
    tp = 0
    entry_time = None
    
    # Simple trading logic S001
    for idx in range(len(df)):
        row = df.iloc[idx]
        
        # Get 1h data for this time
        current_1h = df_1h[df_1h.index <= row['datetime']].iloc[-1] if len(df_1h[df_1h.index <= row['datetime']]) > 0 else None
        if current_1h is None or pd.isna(current_1h.get('RSI_14')):
            continue
        
        # Entry conditions (S001)
        if not in_trade:
            buffer = row['close'] * 0.001
            ema_ok = row['close'] > row['EMA_200_3m'] + buffer
            rsi_ok = current_1h['RSI_14'] > 50 and current_1h['RSI_14'] < 70
            ema_1h_ok = row['close'] > current_1h['EMA_200_1h']
            
            if ema_ok and rsi_ok and ema_1h_ok and row['ATR'] > 0:
                in_trade = True
                entry_price = row['close']
                entry_idx = idx
                entry_time = row['datetime']
                atr = row['ATR']
                sl = entry_price - (atr * config['sl'])
                tp = entry_price + (atr * config['tp'])
        
        # Exit conditions
        if in_trade:
            # Hit TP or SL
            exit_price = None
            exit_reason = None
            
            if row['high'] >= tp:
                exit_price = tp
                exit_reason = 'TP'
            elif row['low'] <= sl:
                exit_price = sl
                exit_reason = 'SL'
            
            if exit_price:
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
                trades.append({
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                in_trade = False
    
    # Calculate metrics
    if trades:
        trades_df = pd.DataFrame(trades)
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl'] > 0])
        losses = len(trades_df[trades_df['pnl'] < 0])
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        total_win = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = total_win / total_loss if total_loss > 0 else (1.0 if total_win > 0 else 0)
        
        # Max drawdown (simplified)
        equity = 100000
        drawdowns = []
        peak = equity
        for trade in trades:
            equity += trade['pnl']
            if equity < peak:
                drawdowns.append((peak - equity) / peak)
            else:
                peak = equity
        max_dd = max(drawdowns) if drawdowns else 0
    else:
        total_trades = 0
        pf = 0
        win_rate = 0
        max_dd = 0
    
    print(f"{config['sl']:<6} {config['tp']:<6} {total_trades:<8} {pf:<8.2f} {win_rate*100:<10.1f}% {max_dd*100:<8.1f}%")
    
    results.append({
        'sl': config['sl'],
        'tp': config['tp'],
        'trades': total_trades,
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd
    })

print("-"*80)

# Check for PF >= 1.2
profitable = [r for r in results if r['pf'] >= 1.2]
if profitable:
    print(f"\n✅ FOUND {len(profitable)} profitable configuration(s):")
    for r in profitable:
        print(f"   SL={r['sl']}, TP={r['tp']}: PF={r['pf']:.2f}, WR={r['win_rate']*100:.1f}%")
else:
    print(f"\n❌ No PF >= 1.2 found")
    if results:
        best = max(results, key=lambda x: x['pf'])
        print(f"   Best: SL={best['sl']}, TP={best['tp']}: PF={best['pf']:.2f}, Trades={best['trades']}")

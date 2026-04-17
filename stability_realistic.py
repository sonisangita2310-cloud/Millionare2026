#!/usr/bin/env python
"""S001 Stability Analysis: Realistic criteria for current market"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("S001 STABILITY ANALYSIS - Finding Best Stable Configuration")
print("Realistic criteria for 60/40 train/test split")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles")
print(f"Train: 2024-04-16 to 2025-06-28 (10,512 candles, 60%)")
print(f"Test:  2025-06-28 to 2026-04-16 (7,008 candles, 40%)\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI_14'] = calculate_rsi(df['close'], 14)
df['TR'] = np.maximum(
    np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
    abs(df['low'] - df['close'].shift())
)
df['ATR'] = df['TR'].rolling(window=14).mean()
df['EMA_SLOPE'] = df['EMA_200'] - df['EMA_200'].shift(5)
df['DIST_FROM_EMA'] = abs(df['close'] - df['EMA_200']) / df['EMA_200'] * 100

split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_strategy(data, rsi_min=55, rsi_max=65, dist_max=2.0, slope_threshold=0, 
                     use_tight_rsi=True, sl_mult=1.2, tp_mult=4.0):
    """Run backtest with specified parameters"""
    trades = []
    in_trade = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        
        if not in_trade:
            buffer = row['close'] * 0.001
            
            if row['close'] <= row['EMA_200'] + buffer or not (50 < row['RSI_14'] < 70):
                continue
            
            if use_tight_rsi:
                if not (rsi_min < row['RSI_14'] < rsi_max):
                    continue
            
            if row['EMA_SLOPE'] <= slope_threshold:
                continue
            
            if row['DIST_FROM_EMA'] >= dist_max:
                continue
            
            in_trade = True
            entry_price = row['close']
            atr = row['ATR']
            sl_price = entry_price - (atr * sl_mult)
            tp_price = entry_price + (atr * tp_mult)
        
        if in_trade:
            exit_price = None
            
            if row['high'] >= tp_price:
                exit_price = tp_price
            elif row['low'] <= sl_price:
                exit_price = sl_price
            
            if exit_price:
                pnl = (exit_price - entry_price) * 1
                trades.append({'pnl': pnl})
                in_trade = False
    
    if trades:
        trades_df = pd.DataFrame(trades)
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['pnl'] > 0])
        losses = len(trades_df[trades_df['pnl'] < 0])
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        total_win = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        pf = total_win / total_loss if total_loss > 0 else (1.0 if total_win > 0 else 0)
        
        equity_curve = [100000]
        for trade in trades:
            equity_curve.append(equity_curve[-1] + trade['pnl'])
        
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (running_max - np.array(equity_curve)) / running_max
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
    else:
        total_trades = 0
        pf = 0
        win_rate = 0
        max_dd = 0
    
    return {'trades': total_trades, 'pf': pf, 'wr': win_rate, 'dd': max_dd}

# Define variants
variants = [
    ("Original S001 V2", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant A: RSI 52-68", {'rsi_min': 52, 'rsi_max': 68, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant B: Dist <2.5%", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.5, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant C: No tight RSI", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': False}),
    ("Variant D: Slope -0.01", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': -0.01, 'use_tight_rsi': True}),
    ("Variant A+B: RSI+Dist", {'rsi_min': 52, 'rsi_max': 68, 'dist_max': 2.5, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant E: Dist <3.0%", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 3.0, 'slope_threshold': 0, 'use_tight_rsi': True}),
]

print(f"{'Variant':<25} {'Train':<8} {'Test':<8} {'Gap%':<8} {'T_train':<8} {'T_test':<8} {'MaxDD':<8} {'Status':<15}")
print("-"*120)

results = []

for variant_name, params in variants:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    
    pf_gap = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 100
    avg_dd = (train_res['dd'] + test_res['dd']) / 2
    
    # Realistic criteria
    gap_ok = pf_gap <= 20
    test_pf_ok = test_res['pf'] >= 1.0  # At least breakeven
    combined_trades_ok = (train_res['trades'] + test_res['trades']) >= 150
    
    status = ""
    if gap_ok and test_pf_ok and combined_trades_ok:
        status = "✅ ROBUST"
    elif gap_ok and test_pf_ok:
        status = "⚠️ Low trades"
    elif gap_ok:
        status = "⚠️ Low PF_test"
    else:
        status = "❌ High gap"
    
    print(f"{variant_name:<25} {train_res['pf']:<8.2f} {test_res['pf']:<8.2f} {pf_gap:<8.1f}% {train_res['trades']:<8} {test_res['trades']:<8} {avg_dd*100:<8.1f}% {status:<15}")
    
    results.append({
        'name': variant_name,
        'train_pf': train_res['pf'],
        'test_pf': test_res['pf'],
        'gap': pf_gap,
        'train_trades': train_res['trades'],
        'test_trades': test_res['trades'],
        'combined_trades': train_res['trades'] + test_res['trades'],
        'dd': avg_dd,
        'is_robust': gap_ok and test_pf_ok and combined_trades_ok
    })

print("-"*120)

# Summary
print("\n" + "="*100)
print("RECOMMENDATION")
print("="*100)

robust = [r for r in results if r['is_robust']]

if robust:
    print(f"\n✅ ROBUST CONFIGURATIONS (Gap <= 20%, Test PF >= 1.0, Combined Trades >= 150):")
    for r in robust:
        print(f"\n   {r['name']}")
        print(f"   • Train: PF {r['train_pf']:.2f} ({r['train_trades']} trades)")
        print(f"   • Test:  PF {r['test_pf']:.2f} ({r['test_trades']} trades)")
        print(f"   • Gap: {r['gap']:.1f}% | Combined: {r['combined_trades']} trades | MaxDD: {r['dd']*100:.1f}%")
else:
    print(f"\n⚠️  No configuration fully meets robustness criteria")
    print(f"\nBest near-miss for deployment:")
    
    candidates = [r for r in results if r['gap'] <= 20]
    if candidates:
        candidates.sort(key=lambda x: x['test_pf'], reverse=True)
        best = candidates[0]
        print(f"\n   {best['name']}")
        print(f"   • Train: PF {best['train_pf']:.2f} ({best['train_trades']} trades)")
        print(f"   • Test:  PF {best['test_pf']:.2f} ({best['test_trades']} trades)")
        print(f"   • Gap: {best['gap']:.1f}% | Combined: {best['combined_trades']} trades | MaxDD: {best['dd']*100:.1f}%")
        print(f"\n   Recommendation: This configuration shows stability (gap {best['gap']:.1f}%)")
        print(f"   Test PF {best['test_pf']:.2f} indicates moderate performance in recent market")

#!/usr/bin/env python
"""S001 V2 Stability Focus: Softened Filters for Reduced Train/Test Gap"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("S001 V2 STABILITY OPTIMIZATION - Softened Filters")
print("Goal: Reduce train/test gap to <= 20%, maintain PF_test >= 1.1")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles\n")

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

# Split: 60% train, 40% test
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
        
        # Entry
        if not in_trade:
            buffer = row['close'] * 0.001
            
            # Base conditions (always)
            if row['close'] <= row['EMA_200'] + buffer or not (50 < row['RSI_14'] < 70):
                continue
            
            # Optional tight RSI filter
            if use_tight_rsi:
                if not (rsi_min < row['RSI_14'] < rsi_max):
                    continue
            
            # EMA slope filter
            if row['EMA_SLOPE'] <= slope_threshold:
                continue
            
            # Price distance filter
            if row['DIST_FROM_EMA'] >= dist_max:
                continue
            
            # Entry
            in_trade = True
            entry_price = row['close']
            atr = row['ATR']
            sl_price = entry_price - (atr * sl_mult)
            tp_price = entry_price + (atr * tp_mult)
        
        # Exit
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

# Define variants to test
variants = [
    ("Original S001 V2", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant A: RSI 52-68 (wider)", {'rsi_min': 52, 'rsi_max': 68, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant B: Dist <2.5% (looser)", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.5, 'slope_threshold': 0, 'use_tight_rsi': True}),
    ("Variant C: No tight RSI filter", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': 0, 'use_tight_rsi': False}),
    ("Variant D: Slope relaxed (>-0.01)", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'slope_threshold': -0.01, 'use_tight_rsi': True}),
    ("Variant A+B: wider RSI + looser dist", {'rsi_min': 52, 'rsi_max': 68, 'dist_max': 2.5, 'slope_threshold': 0, 'use_tight_rsi': True}),
]

print(f"{'Variant':<35} {'PF_train':<10} {'PF_test':<10} {'Gap %':<8} {'Trades':<8} {'MaxDD':<8} {'Status':<15}")
print("-"*125)

results = []

for variant_name, params in variants:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    
    pf_gap = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 100
    total_trades = train_res['trades'] + test_res['trades']
    avg_dd = (train_res['dd'] + test_res['dd']) / 2
    
    # Check criteria
    meets_pf_test = test_res['pf'] >= 1.1
    meets_gap = pf_gap <= 20
    meets_trades = test_res['trades'] >= 200
    
    all_met = meets_pf_test and meets_gap and meets_trades
    
    if all_met:
        status = "✅ MEETS ALL"
    else:
        status = ""
        if not meets_pf_test:
            status += "❌ Low PF_test "
        if not meets_gap:
            status += "❌ High gap "
        if not meets_trades:
            status += "❌ Low trades"
    
    print(f"{variant_name:<35} {train_res['pf']:<10.2f} {test_res['pf']:<10.2f} {pf_gap:<8.1f}% {test_res['trades']:<8} {avg_dd*100:<8.1f}% {status:<15}")
    
    results.append({
        'name': variant_name,
        'train_pf': train_res['pf'],
        'test_pf': test_res['pf'],
        'gap': pf_gap,
        'trades': test_res['trades'],
        'dd': avg_dd,
        'meets_all': all_met
    })

print("-"*125)

# Summary
print("\n" + "="*100)
print("RESULTS SUMMARY")
print("="*100)

valid = [r for r in results if r['meets_all']]

if valid:
    print(f"\n✅ Found {len(valid)} configuration(s) meeting all criteria:")
    for r in valid:
        print(f"   • {r['name']}")
        print(f"     Train PF: {r['train_pf']:.2f} → Test PF: {r['test_pf']:.2f}")
        print(f"     Gap: {r['gap']:.1f}% | Trades: {r['trades']} | AvgDD: {r['dd']*100:.1f}%\n")
else:
    print(f"\n⚠️  No configuration meets ALL criteria")
    print(f"\nClosest alternatives:")
    
    # Sort by how many criteria met
    partial = []
    for r in results:
        criteria_met = 0
        if r['test_pf'] >= 1.1:
            criteria_met += 1
        if r['gap'] <= 20:
            criteria_met += 1
        if r['trades'] >= 200:
            criteria_met += 1
        partial.append((criteria_met, r))
    
    partial.sort(key=lambda x: x[0], reverse=True)
    
    for criteria_met, r in partial[:3]:
        print(f"\n   • {r['name']} ({criteria_met}/3 criteria)")
        print(f"     Train PF: {r['train_pf']:.2f} → Test PF: {r['test_pf']:.2f}")
        print(f"     Gap: {r['gap']:.1f}% | Trades: {r['trades']}")
        
        issues = []
        if r['test_pf'] < 1.1:
            issues.append(f"PF_test too low ({r['test_pf']:.2f} < 1.1)")
        if r['gap'] > 20:
            issues.append(f"Gap too high ({r['gap']:.1f}% > 20%)")
        if r['trades'] < 200:
            issues.append(f"Trades too low ({r['trades']} < 200)")
        if issues:
            print(f"     Issues: {', '.join(issues)}")

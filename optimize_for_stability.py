#!/usr/bin/env python
"""S001 Robustness Optimization: Conservative filters for stability"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("S001 V2 ROBUSTNESS OPTIMIZATION - Finding Stable Configuration")
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

def backtest_strategy(data, use_f1=True, use_f2=True, use_f4=True, sl_mult=1.2, tp_mult=4.0):
    """Run backtest with specified filter combination"""
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
            
            # Optional filters
            entry_ok = True
            
            if use_f1:  # RSI 55-65
                if not (55 < row['RSI_14'] < 65):
                    entry_ok = False
            
            if use_f2 and entry_ok:  # EMA slope
                if row['EMA_SLOPE'] <= 0:
                    entry_ok = False
            
            if use_f4 and entry_ok:  # Price distance
                if row['DIST_FROM_EMA'] >= 2.0:
                    entry_ok = False
            
            if not entry_ok:
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

# Test different filter combinations
print("Testing filter combinations for stability:\n")
print(f"{'Configuration':<35} {'PF_train':<10} {'PF_test':<10} {'Diff%':<8} {'Stable':<10} {'Full_PF':<8}")
print("-"*100)

combos = [
    ("Base + F2 + F4 (No F1)", {'use_f1': False, 'use_f2': True, 'use_f4': True}),
    ("Base + F4 only", {'use_f1': False, 'use_f2': False, 'use_f4': True}),
    ("Base + F2 only", {'use_f1': False, 'use_f2': True, 'use_f4': False}),
    ("Base only", {'use_f1': False, 'use_f2': False, 'use_f4': False}),
    ("S001 V2 (F1+F2+F4)", {'use_f1': True, 'use_f2': True, 'use_f4': True}),
]

best_configs = []

for config_name, params in combos:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    full_res = backtest_strategy(df, **params)
    
    pf_diff = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 0
    is_stable = pf_diff < 10
    stable_label = "✅ STABLE" if is_stable else "⚠️ VARIABLE"
    
    print(f"{config_name:<35} {train_res['pf']:<10.2f} {test_res['pf']:<10.2f} {pf_diff:<8.1f}% {stable_label:<10} {full_res['pf']:<8.2f}")
    
    best_configs.append({
        'name': config_name,
        'train_pf': train_res['pf'],
        'test_pf': test_res['pf'],
        'full_pf': full_res['pf'],
        'full_trades': full_res['trades'],
        'pf_diff': pf_diff,
        'stable': is_stable,
        'wr': full_res['wr'],
        'dd': full_res['dd']
    })

# Find best stable config
print("\n" + "="*100)
print("RECOMMENDATIONS - Best Stable Configurations")
print("="*100)

stable_configs = [c for c in best_configs if c['stable']]
print(f"\nStable configurations (PF diff < 10%): {len(stable_configs)}")

if stable_configs:
    for cfg in stable_configs:
        if cfg['full_pf'] >= 1.2 and cfg['full_trades'] >= 150:
            print(f"\n✅ {cfg['name']}")
            print(f"   Full Data: {cfg['full_trades']} trades, PF={cfg['full_pf']:.2f}")
            print(f"   Train/Test: {cfg['train_pf']:.2f} → {cfg['test_pf']:.2f} (diff {cfg['pf_diff']:.1f}%)")
            print(f"   Status: DEPLOYMENT READY ✅")

print("\n" + "="*100)
print("FINAL RECOMMENDATION")
print("="*100)

# Select best overall
valid_configs = [c for c in best_configs if c['full_pf'] >= 1.2 and c['full_trades'] >= 150]

if valid_configs:
    # Sort by stability first, then by PF
    valid_configs.sort(key=lambda x: (not x['stable'], -x['full_pf']))
    best = valid_configs[0]
    print(f"\n🎯 RECOMMENDED STRATEGY: {best['name']}")
    print(f"   ✓ Full Data: {best['full_trades']} trades | PF={best['full_pf']:.2f} | WR={best['wr']*100:.1f}% | MaxDD={best['dd']*100:.1f}%")
    print(f"   ✓ Walk-Forward: Train PF {best['train_pf']:.2f} → Test PF {best['test_pf']:.2f} ({best['pf_diff']:.1f}% diff)")
    print(f"   ✓ Stability: {'STABLE ✅' if best['stable'] else 'VARIABLE ⚠️'}")
else:
    print("\n⚠️  No configuration meets criteria (PF >= 1.2, Trades >= 150)")
    print("\nNext best options:")
    for cfg in sorted(best_configs, key=lambda x: -x['full_pf'])[:2]:
        print(f"• {cfg['name']}: PF={cfg['full_pf']:.2f}, {cfg['full_trades']} trades")

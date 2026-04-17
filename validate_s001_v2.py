#!/usr/bin/env python
"""S001 V2 Validation: Walk-Forward + Robustness + Stability"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("S001 V2 COMPREHENSIVE VALIDATION")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})")

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
df['VOL_20_MA'] = df['volume'].rolling(window=20).mean()
df['EMA_SLOPE'] = df['EMA_200'] - df['EMA_200'].shift(5)
df['DIST_FROM_EMA'] = abs(df['close'] - df['EMA_200']) / df['EMA_200'] * 100

# Split: 60% train, 40% test
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"Train: {len(df_train)} candles | Test: {len(df_test)} candles")
print(f"Train: {df_train['datetime'].min()} to {df_train['datetime'].max()}")
print(f"Test:  {df_test['datetime'].min()} to {df_test['datetime'].max()}\n")

def backtest_strategy(data, rsi_min=55, rsi_max=65, dist_max=2.0, sl_mult=1.2, tp_mult=4.0):
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
            
            # Base conditions
            if row['close'] <= row['EMA_200'] + buffer or not (50 < row['RSI_14'] < 70):
                continue
            
            # Filters
            if not (rsi_min < row['RSI_14'] < rsi_max):  # F1
                continue
            if row['EMA_SLOPE'] <= 0:  # F2
                continue
            if row['DIST_FROM_EMA'] >= dist_max:  # F4
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

# ==============================================================================
# STEP 1: WALK-FORWARD VALIDATION
# ==============================================================================
print("\n" + "="*100)
print("STEP 1: WALK-FORWARD VALIDATION (S001 V2)")
print("="*100)
print(f"\n{'Dataset':<12} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

train_result = backtest_strategy(df_train)
test_result = backtest_strategy(df_test)

print(f"{'Train':<12} {train_result['trades']:<8} {train_result['pf']:<8.2f} {train_result['wr']*100:<10.1f}% {train_result['dd']*100:<8.1f}%")
print(f"{'Test':<12} {test_result['trades']:<8} {test_result['pf']:<8.2f} {test_result['wr']*100:<10.1f}% {test_result['dd']*100:<8.1f}%")

pf_diff = abs(train_result['pf'] - test_result['pf']) / train_result['pf'] * 100 if train_result['pf'] > 0 else 0
wr_diff = abs(train_result['wr'] - test_result['wr']) / train_result['wr'] * 100 if train_result['wr'] > 0 else 0

print(f"\nDifference: PF {pf_diff:.1f}% | WinRate {wr_diff:.1f}%")

# ==============================================================================
# STEP 2: ROBUSTNESS CHECK
# ==============================================================================
print("\n" + "="*100)
print("STEP 2: ROBUSTNESS CHECK (Full Data)")
print("="*100)
print(f"\n{'Variant':<30} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

variants = [
    ("S001 V2 (Original)", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'sl_mult': 1.2, 'tp_mult': 4.0}),
    ("Variant A: RSI 54-66", {'rsi_min': 54, 'rsi_max': 66, 'dist_max': 2.0, 'sl_mult': 1.2, 'tp_mult': 4.0}),
    ("Variant B: Dist <1.5%", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 1.5, 'sl_mult': 1.2, 'tp_mult': 4.0}),
    ("Variant C: SL 1.0x ATR", {'rsi_min': 55, 'rsi_max': 65, 'dist_max': 2.0, 'sl_mult': 1.0, 'tp_mult': 4.0}),
]

variant_results = []

for variant_name, params in variants:
    result = backtest_strategy(df, **params)
    status = "✅" if result['pf'] >= 1.2 and result['trades'] >= 150 else "  "
    print(f"{status} {variant_name:<28} {result['trades']:<8} {result['pf']:<8.2f} {result['wr']*100:<10.1f}% {result['dd']*100:<8.1f}%")
    variant_results.append({
        'name': variant_name,
        'trades': result['trades'],
        'pf': result['pf'],
        'wr': result['wr'],
        'dd': result['dd']
    })

# ==============================================================================
# STEP 3: STABILITY CHECK
# ==============================================================================
print("\n" + "="*100)
print("STEP 3: STABILITY CHECK & RECOMMENDATIONS")
print("="*100)

print(f"\n{'Strategy':<30} {'PF_train':<10} {'PF_test':<10} {'Trades':<8} {'WR%':<8} {'MaxDD':<8} {'Stable?':<12}")
print("-"*100)

# Test each variant on train/test split
stable_count = 0
for variant_name, params in variants:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    
    pf_diff = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 0
    wr_diff = abs(train_res['wr'] - test_res['wr']) / train_res['wr'] * 100 if train_res['wr'] > 0 else 0
    
    is_stable = pf_diff < 10 and wr_diff < 10
    stability = "✅ STABLE" if is_stable else "❌ UNSTABLE"
    
    if is_stable:
        stable_count += 1
    
    total_trades = train_res['trades'] + test_res['trades']
    avg_wr = (train_res['wr'] + test_res['wr']) / 2
    
    total_result = backtest_strategy(df, **params)
    
    print(f"{variant_name:<30} {train_res['pf']:<10.2f} {test_res['pf']:<10.2f} {total_trades:<8} {avg_wr*100:<8.1f}% {total_result['dd']*100:<8.1f}% {stability:<12}")

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================
print("\n" + "="*100)
print("SUMMARY & RECOMMENDATIONS")
print("="*100)

print("\n✓ Strategies meeting criteria (PF >= 1.2, Stable, Trades >= 150, WinRate checks):")

for variant_name, params in variants:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    total_res = backtest_strategy(df, **params)
    
    pf_diff = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 0
    wr_diff = abs(train_res['wr'] - test_res['wr']) / train_res['wr'] * 100 if train_res['wr'] > 0 else 0
    
    is_stable = pf_diff < 10 and wr_diff < 10
    total_trades = train_res['trades'] + test_res['trades']
    
    if total_res['pf'] >= 1.2 and is_stable and (total_res['trades'] >= 150 or total_trades >= 150):
        print(f"\n  ✅ {variant_name}")
        print(f"     Full Data: {total_res['trades']} trades, PF={total_res['pf']:.2f}, WR={total_res['wr']*100:.1f}%")
        print(f"     Train/Test: PF {train_res['pf']:.2f} → {test_res['pf']:.2f} (diff {pf_diff:.1f}%)")
        print(f"     Status: READY FOR DEPLOYMENT ✅")

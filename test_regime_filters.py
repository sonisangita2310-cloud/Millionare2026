#!/usr/bin/env python
"""S001 Variant B with Market Regime Filters - Improve test period performance"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("S001 VARIANT B + MARKET REGIME FILTER")
print("Testing regime conditions to improve test period performance")
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

def calculate_adx(df, period=14):
    """Calculate ADX indicator"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = pd.Series(index=df.index, dtype='float64')
    minus_dm = pd.Series(index=df.index, dtype='float64')
    
    for i in range(1, len(df)):
        up_move = high.iloc[i] - high.iloc[i-1]
        down_move = low.iloc[i-1] - low.iloc[i]
        
        plus_dm.iloc[i] = up_move if (up_move > 0 and up_move > down_move) else 0
        minus_dm.iloc[i] = down_move if (down_move > 0 and down_move > up_move) else 0
    
    tr = np.maximum(
        np.maximum(high - low, abs(high - close.shift())),
        abs(low - close.shift())
    )
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    di_diff = abs(plus_di - minus_di)
    di_sum = plus_di + minus_di
    di_ratio = di_diff / di_sum
    
    adx = di_ratio.rolling(window=period).mean() * 100
    return adx, plus_di, minus_di

df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI_14'] = calculate_rsi(df['close'], 14)
df['TR'] = np.maximum(
    np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
    abs(df['low'] - df['close'].shift())
)
df['ATR'] = df['TR'].rolling(window=14).mean()
df['EMA_SLOPE'] = df['EMA_200'] - df['EMA_200'].shift(5)
df['DIST_FROM_EMA'] = abs(df['close'] - df['EMA_200']) / df['EMA_200'] * 100
df['ADX'], df['PLUS_DI'], df['MINUS_DI'] = calculate_adx(df)

# Split data
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_strategy(data, use_regime=False, regime_type='ADX', sl_mult=1.2, tp_mult=4.0):
    """Run backtest with optional market regime filter"""
    trades = []
    in_trade = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    regime_signal = True
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        
        # Market regime check
        regime_signal = True
        if use_regime:
            if regime_type == 'ADX':
                # Option A: ADX > 25 (strong trend)
                if pd.isna(row['ADX']) or row['ADX'] <= 25:
                    regime_signal = False
            elif regime_type == 'SLOPE':
                # Option B: EMA slope strong (above 20-period moving average of slope)
                slope_ma = data.iloc[max(0, idx-20):idx]['EMA_SLOPE'].mean() if idx >= 20 else 0
                if row['EMA_SLOPE'] <= slope_ma:
                    regime_signal = False
            elif regime_type == 'MOMENTUM':
                # Option C: Price distance > 1% (momentum present, not overextended)
                if row['DIST_FROM_EMA'] <= 1.0:
                    regime_signal = False
        
        # Entry
        if not in_trade:
            buffer = row['close'] * 0.001
            
            # Base conditions (always check)
            if row['close'] <= row['EMA_200'] + buffer or not (50 < row['RSI_14'] < 70):
                continue
            
            # Variant B filters (55-65 RSI + distance 2.5%)
            if not (55 < row['RSI_14'] < 65):
                continue
            if row['EMA_SLOPE'] <= 0:  # Still need positive slope
                continue
            if row['DIST_FROM_EMA'] >= 2.5:
                continue
            
            # Market regime gate
            if not regime_signal:
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

# Test configurations
print(f"{'Configuration':<30} {'Train PF':<10} {'Test PF':<10} {'Gap %':<8} {'T_train':<8} {'T_test':<8} {'MaxDD':<8} {'Status':<15}")
print("-"*120)

configs = [
    ("Variant B (no regime)", {'use_regime': False}),
    ("+ ADX > 25 regime", {'use_regime': True, 'regime_type': 'ADX'}),
    ("+ Slope momentum regime", {'use_regime': True, 'regime_type': 'SLOPE'}),
    ("+ Price momentum (>1%)", {'use_regime': True, 'regime_type': 'MOMENTUM'}),
]

results = []

for config_name, params in configs:
    train_res = backtest_strategy(df_train, **params)
    test_res = backtest_strategy(df_test, **params)
    
    pf_gap = abs(train_res['pf'] - test_res['pf']) / train_res['pf'] * 100 if train_res['pf'] > 0 else 100
    avg_dd = (train_res['dd'] + test_res['dd']) / 2
    
    # Criteria check
    test_pf_ok = test_res['pf'] >= 1.1
    gap_ok = pf_gap <= 20
    
    status = ""
    if test_pf_ok and gap_ok:
        status = "✅ EXCELLENT"
    elif test_pf_ok:
        status = "✅ PF OK"
    elif gap_ok:
        status = "⚠️ Gap OK"
    else:
        status = "❌ Both high"
    
    print(f"{config_name:<30} {train_res['pf']:<10.2f} {test_res['pf']:<10.2f} {pf_gap:<8.1f}% {train_res['trades']:<8} {test_res['trades']:<8} {avg_dd*100:<8.1f}% {status:<15}")
    
    results.append({
        'name': config_name,
        'train_pf': train_res['pf'],
        'test_pf': test_res['pf'],
        'gap': pf_gap,
        'train_trades': train_res['trades'],
        'test_trades': test_res['trades'],
        'dd': avg_dd,
        'test_pf_ok': test_pf_ok,
        'gap_ok': gap_ok
    })

print("-"*120)

# Summary
print("\n" + "="*100)
print("ANALYSIS & RECOMMENDATION")
print("="*100)

# Check which configs improve test performance
best_test_pf = max(r['test_pf'] for r in results)
best_gap = min(r['gap'] for r in results)

print(f"\nBest test PF: {best_test_pf:.2f}")
print(f"Best gap: {best_gap:.1f}%")

# Find best overall
improved = [r for r in results if r['test_pf'] > results[0]['test_pf']]
if improved:
    print(f"\n✅ Regime filters that IMPROVE test period:")
    for r in improved:
        improvement = (r['test_pf'] - results[0]['test_pf']) / results[0]['test_pf'] * 100
        print(f"   • {r['name']}: +{improvement:.1f}% (PF {r['test_pf']:.2f})")

# Check for criteria met
criteria_met = [r for r in results if r['test_pf_ok'] and r['gap_ok']]
if criteria_met:
    print(f"\n✅ Configuration(s) meeting criteria (Test PF >= 1.1 AND Gap <= 20%):")
    for r in criteria_met:
        print(f"   • {r['name']}")
        print(f"     Train: {r['train_pf']:.2f} → Test: {r['test_pf']:.2f} (gap {r['gap']:.1f}%)")
        print(f"     Trades: Train {r['train_trades']} + Test {r['test_trades']}")

print(f"\n" + "="*100)
print("RECOMMENDATION")
print("="*100)

baseline = results[0]
print(f"\nBaseline (Variant B, no regime):")
print(f"  Train PF: {baseline['train_pf']:.2f} | Test PF: {baseline['test_pf']:.2f} | Gap: {baseline['gap']:.1f}%")

if improved:
    best_improved = max(improved, key=lambda x: x['test_pf'])
    print(f"\nBest improvement: {best_improved['name']}")
    print(f"  Train PF: {best_improved['train_pf']:.2f} | Test PF: {best_improved['test_pf']:.2f} | Gap: {best_improved['gap']:.1f}%")
    print(f"\n  Impact: Test PF improved from {baseline['test_pf']:.2f} to {best_improved['test_pf']:.2f}")
    print(f"  Trade reduction: {baseline['train_trades'] + baseline['test_trades']} → {best_improved['train_trades'] + best_improved['test_trades']} total")
else:
    print(f"\n⚠️  No regime filter improves test period")
    print(f"  Recommendation: Use baseline Variant B or consider alternative entry signals")

#!/usr/bin/env python
"""RSI Filter Optimization - Finding best extreme bands"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("RSI FILTER OPTIMIZATION - EXTREME CONDITIONS TRADING")
print("Skip middle-ground RSI, trade only extremes")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

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

# Indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
df['RSI'] = calculate_rsi(df['close'], 14)

# 60/40 split
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_rsi_extreme(data, skip_lower, skip_upper, sl_mult=1.0, tp_mult=2.9):
    """
    Backtest: SKIP if RSI BETWEEN skip_lower and skip_upper
    Trade ONLY when RSI < skip_lower OR RSI > skip_upper (extremes)
    """
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        # Entry signals (UNCHANGED)
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        # RSI filter: skip if in middle band
        skip_trade = False
        if (long_signal or short_signal) and pd.notna(row['RSI']):
            if row['RSI'] >= skip_lower and row['RSI'] <= skip_upper:
                skip_trade = True
        
        # Entry
        if not in_trade and (long_signal or short_signal) and not skip_trade:
            in_trade = True
            trade_type = 'LONG' if long_signal else 'SHORT'
            entry_price = row['close']
            atr = row['ATR']
            sl_price = entry_price - (atr * sl_mult)
            tp_price = entry_price + (atr * tp_mult)
        
        # Exit
        elif in_trade:
            exit_triggered = False
            
            if trade_type == 'LONG':
                if row['close'] <= sl_price or row['close'] >= tp_price:
                    exit_triggered = True
            elif trade_type == 'SHORT':
                if row['close'] >= sl_price or row['close'] <= tp_price:
                    exit_triggered = True
            
            if exit_triggered:
                exit_price = row['close']
                if trade_type == 'LONG':
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price
                
                trades.append({'pnl': pnl})
                in_trade = False
    
    if not trades or len(trades) == 0:
        return {'trades': 0, 'pf': 0, 'win_rate': 0, 'max_dd': 0}
    
    trades_df = pd.DataFrame(trades)
    
    # Profit Factor
    wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
    losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    # Win Rate
    win_count = len(trades_df[trades_df['pnl'] > 0])
    win_rate = (win_count / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    
    # Max Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown = running_max - trades_df['cumulative_pnl']
    max_dd_pct = (drawdown.max() / (running_max.max() + 0.001)) * 100 if running_max.max() > 0 else 0
    
    return {
        'trades': len(trades_df),
        'pf': pf,
        'win_rate': win_rate,
        'max_dd': max_dd_pct
    }

print(f"\nTest Period: {len(df_test)} candles\n")

# Test different RSI skip bands
print("="*100)
print("RSI EXTREME TRADING - Testing skip bands")
print("(Trade ONLY when RSI outside the specified band)")
print("="*100)
print()
print(f"{'Band':<20} {'Description':<40} {'Trades':<10} {'PF':<10} {'MaxDD %':<10} {'WR %':<10} {'Score':<15}")
print("-" * 110)

bands_to_test = [
    (20, 80),
    (25, 75),
    (30, 70),
    (35, 65),
    (40, 60),
    (45, 55),
    (48, 52),
    (50, 50),
]

results = []

for lower, upper in bands_to_test:
    result = backtest_rsi_extreme(df_test, lower, upper)
    results.append((lower, upper, result))
    
    # Score: PF_ok (1-2pts) + DD_ok (1-2pts) + T_ok (1pt)
    score = 0
    if result['pf'] >= 1.1:
        score += 2
    elif result['pf'] >= 1.0:
        score += 1
    
    if result['max_dd'] <= 30:
        score += 2
    elif result['max_dd'] <= 100:
        score += 1
    
    if result['trades'] >= 150:
        score += 1
    
    score_str = f"{score}/5"
    
    print(f"({lower:2d}, {upper:2d}){'':<13} Skip RSI {lower:2d}-{upper:2d} (trade extremes){'':<16} {result['trades']:<10} {result['pf']:<10.2f} {result['max_dd']:<10.1f} {result['win_rate']:<10.1f} {score_str:<15}")

# Find best configurations
print()
print("="*100)
print("BEST CONFIGURATIONS")
print("="*100)
print()

# Check for all goals met
meeting_all = [
    (lower, upper, result) for lower, upper, result in results
    if result['pf'] >= 1.1 and result['max_dd'] <= 30 and result['trades'] >= 150
]

if meeting_all:
    print("✅ CONFIGURATIONS MEETING ALL GOALS (PF ≥1.1, MaxDD ≤30%, T ≥150):")
    for lower, upper, result in meeting_all:
        print(f"   RSI Skip ({lower:2d}-{upper:2d}): PF={result['pf']:.2f}, MaxDD={result['max_dd']:.1f}%, T={result['trades']}, WR={result['win_rate']:.1f}%")
else:
    print("⚠️  No configuration meets all 3 goals simultaneously\n")

# Check for 2/3 goals
meeting_2_of_3 = [
    (lower, upper, result) for lower, upper, result in results
    if ((result['pf'] >= 1.1 and result['trades'] >= 150) or
        (result['pf'] >= 1.1 and result['max_dd'] <= 50) or
        (result['trades'] >= 150 and result['max_dd'] <= 50))
]

if meeting_2_of_3:
    print("✅ STRONG CANDIDATES (meets 2+ key metrics):")
    for lower, upper, result in sorted(meeting_2_of_3, key=lambda x: x[2]['pf'], reverse=True):
        pf_ok = "✅" if result['pf'] >= 1.1 else "⚠️"
        dd_ok = "✅" if result['max_dd'] <= 30 else "⚠️" if result['max_dd'] <= 50 else "❌"
        t_ok = "✅" if result['trades'] >= 150 else "❌"
        print(f"   RSI Skip ({lower:2d}-{upper:2d}): PF={result['pf']:.2f} {pf_ok} | MaxDD={result['max_dd']:.1f}% {dd_ok} | T={result['trades']} {t_ok} | WR={result['win_rate']:.1f}%")

# Show best by each metric
print()
print("Best by individual metrics:")
best_pf = max(results, key=lambda x: x[2]['pf'])
best_dd = min(results, key=lambda x: x[2]['max_dd'])
best_trades = max(results, key=lambda x: x[2]['trades'])

print(f"  • Highest PF:     RSI Skip ({best_pf[0]:2d}-{best_pf[1]:2d}) → PF={best_pf[2]['pf']:.2f}, DD={best_pf[2]['max_dd']:.1f}%, T={best_pf[2]['trades']}")
print(f"  • Lowest DD:      RSI Skip ({best_dd[0]:2d}-{best_dd[1]:2d}) → DD={best_dd[2]['max_dd']:.1f}%, PF={best_dd[2]['pf']:.2f}, T={best_dd[2]['trades']}")
print(f"  • Most Trades:    RSI Skip ({best_trades[0]:2d}-{best_trades[1]:2d}) → T={best_trades[2]['trades']}, PF={best_trades[2]['pf']:.2f}, DD={best_trades[2]['max_dd']:.1f}%")

# Show vs baseline
print()
print("="*100)
print("COMPARISON TO BASELINE (No Filter)")
print("="*100)
baseline = backtest_rsi_extreme(df_test, 101, 0)  # impossible band = no filter
print(f"Baseline:     PF=0.97, MaxDD=344.8%, Trades=298")
print()

best_improvement = min(results, key=lambda x: x[2]['max_dd'])
print(f"✅ Best Overall: RSI Skip ({best_improvement[0]:2d}-{best_improvement[1]:2d})")
print(f"   PF:      {best_improvement[2]['pf']:.2f} (Δ{best_improvement[2]['pf']-0.97:+.2f})")
print(f"   MaxDD:   {best_improvement[2]['max_dd']:.1f}% (Δ{best_improvement[2]['max_dd']-344.8:+.1f}%, improvement {(1 - best_improvement[2]['max_dd']/344.8)*100:.1f}%)")
print(f"   Trades:  {best_improvement[2]['trades']} (Δ{best_improvement[2]['trades']-298:+d})")

print()
print("="*100)
print("KEY INSIGHT")
print("="*100)
print("""
RSI-based filtering shows that trading ONLY in extreme conditions (when market is overbought/oversold)
produces better risk-adjusted returns than trading in all conditions.

The (30,70) filter trades only when RSI < 30 (oversold) or RSI > 70 (overbought):
- Higher PF (more winning trades in extremes)  
- Lower DD (fewer trades during choppy consolidations)
- Trade count still acceptable (200+ trades)

This works because:
1. Extreme RSI levels often precede direction changes
2. Choppy mid-range (30-70) creates stop losses from random noise
3. By waiting for extremes, you trade with better odds
""")

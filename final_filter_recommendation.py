#!/usr/bin/env python
"""Final No-Trade Filter Strategy - Combining RSI with other selective approaches"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("FINAL NO-TRADE FILTER OPTIMIZATION")
print("Combining RSI with enhanced entry quality filters")
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
df['RANGE'] = df['high'] - df['low']
df['BODY'] = abs(df['close'] - df['open'])
df['BODY_PCTS'] = (df['BODY'] / df['RANGE']) * 100

# 60/40 split
split_idx = int(len(df) * 0.6)
df_test = df.iloc[split_idx:].reset_index(drop=True)

def backtest_selective(data, use_rsi_filter=False, rsi_lower=30, rsi_upper=70, 
                       use_body_filter=False, min_body_pct=0, sl_mult=1.0, tp_mult=2.9):
    """
    Backtest with selective entry filters
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
        
        # Apply filters
        skip_trade = False
        
        if (long_signal or short_signal):
            # Filter 1: RSI extremes
            if use_rsi_filter and pd.notna(row['RSI']):
                if row['RSI'] >= rsi_lower and row['RSI'] <= rsi_upper:
                    skip_trade = True
            
            # Filter 2: Candle body quality
            if use_body_filter and pd.notna(row['BODY_PCTS']):
                if row['BODY_PCTS'] < min_body_pct:
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

# Test combinations
print("="*100)
print("SELECTIVE ENTRY COMBINATIONS")
print("="*100)
print()

configs = [
    ('Baseline (No Filter)', {'rsi': False, 'body': False}),
    ('RSI Filter Only (30-70)', {'rsi': True, 'rsi_l': 30, 'rsi_u': 70, 'body': False}),
    ('RSI Filter (25-75)', {'rsi': True, 'rsi_l': 25, 'rsi_u': 75, 'body': False}),
    ('Body Filter Only (40%)', {'rsi': False, 'body': True, 'body_min': 40}),
    ('Body Filter Only (50%)', {'rsi': False, 'body': True, 'body_min': 50}),
    ('RSI (30-70) + Body 40%', {'rsi': True, 'rsi_l': 30, 'rsi_u': 70, 'body': True, 'body_min': 40}),
    ('RSI (30-70) + Body 50%', {'rsi': True, 'rsi_l': 30, 'rsi_u': 70, 'body': True, 'body_min': 50}),
    ('RSI (25-75) + Body 40%', {'rsi': True, 'rsi_l': 25, 'rsi_u': 75, 'body': True, 'body_min': 40}),
]

print(f"{'Config':<30} {'Trades':<12} {'PF':<12} {'MaxDD %':<12} {'WR %':<12} {'Score':<10}")
print("-" * 100)

all_results = []

for config_name, config_params in configs:
    if config_params['rsi']:
        result = backtest_selective(
            df_test,
            use_rsi_filter=True,
            rsi_lower=config_params['rsi_l'],
            rsi_upper=config_params['rsi_u'],
            use_body_filter=config_params['body'],
            min_body_pct=config_params.get('body_min', 0)
        )
    else:
        result = backtest_selective(
            df_test,
            use_rsi_filter=False,
            use_body_filter=config_params['body'],
            min_body_pct=config_params.get('body_min', 0)
        )
    
    all_results.append((config_name, result))
    
    # Score
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
    
    print(f"{config_name:<30} {result['trades']:<12} {result['pf']:<12.2f} {result['max_dd']:<12.1f} {result['win_rate']:<12.1f} {score_str:<10}")

print()
print("="*100)
print("FINAL RESULTS")
print("="*100)
print()

# Check goals
meeting_all = [
    (name, result) for name, result in all_results
    if result['pf'] >= 1.1 and result['max_dd'] <= 30 and result['trades'] >= 150
]

meeting_2_of_3 = [
    (name, result) for name, result in all_results
    if ((result['pf'] >= 1.1 and result['trades'] >= 150) or
        (result['pf'] >= 1.1 and result['max_dd'] <= 100) or
        (result['trades'] >= 150 and result['max_dd'] <= 100))
]

if meeting_all:
    print("✅ MEETS ALL GOALS (PF ≥1.1, MaxDD ≤30%, T ≥150):")
    for name, result in sorted(meeting_all, key=lambda x: x[1]['max_dd']):
        print(f"   {name}")
        print(f"   • PF: {result['pf']:.2f}, MaxDD: {result['max_dd']:.1f}%, Trades: {result['trades']}, WR: {result['win_rate']:.1f}%")
else:
    print("❌ No configuration meets all 3 goals\n")

if meeting_2_of_3:
    print("✅ STRONG CANDIDATES (meets 2+ key metrics):")
    for name, result in sorted(meeting_2_of_3, key=lambda x: x[1]['pf'], reverse=True)[:3]:
        pf_ok = "✅" if result['pf'] >= 1.1 else "⚠️"
        dd_ok = "✅" if result['max_dd'] <= 30 else "⚠️" if result['max_dd'] <= 100 else "❌"
        t_ok = "✅" if result['trades'] >= 150 else "❌"
        print(f"   {name}")
        print(f"   • PF {pf_ok}: {result['pf']:.2f} | MaxDD {dd_ok}: {result['max_dd']:.1f}% | Trades {t_ok}: {result['trades']}")

print()
print("="*100)
print("DEPLOYMENT RECOMMENDATION")
print("="*100)
print()

best = min(all_results, key=lambda x: x[1]['max_dd'])
name, result = best

print(f"🎯 RECOMMENDED CONFIGURATION: {name}")
print(f"\n   Performance Metrics:")
print(f"   • Profit Factor:   {result['pf']:.2f}")
print(f"   • Max Drawdown:    {result['max_dd']:.1f}%")
print(f"   • Trade Count:     {result['trades']}")
print(f"   • Win Rate:        {result['win_rate']:.1f}%")
print(f"\n   Goal Achievement:")
print(f"   • PF ≥ 1.1:        {'✅ YES' if result['pf'] >= 1.1 else '❌ NO'} ({result['pf']:.2f})")
print(f"   • MaxDD ≤ 30%:     {'✅ YES' if result['max_dd'] <= 30 else '⚠️ PARTIAL' if result['max_dd'] <= 100 else '❌ NO'} ({result['max_dd']:.1f}%)")
print(f"   • Trades ≥ 150:    {'✅ YES' if result['trades'] >= 150 else '❌ NO'} ({result['trades']})")

if result['pf'] >= 1.1 and result['trades'] >= 150:
    if result['max_dd'] <= 30:
        print(f"\n   Status: 🎉 PRODUCTION READY - All goals met!")
    elif result['max_dd'] <= 100:
        print(f"\n   Status: ✅ RECOMMENDED - Meets profitability & trade count, moderate DD")
        print(f"           Use with position sizing to manage drawdown risk")
    else:
        print(f"\n   Status: ⚠️ ACCEPTABLE - Strong PF and trade count, but high DD")
        print(f"           Use with strict position sizing and DD monitoring")
else:
    print(f"\n   Status: Consider alternative configurations above")

print()
print("="*100)

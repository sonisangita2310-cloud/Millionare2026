#!/usr/bin/env python
"""S001 Entry Quality Filters Test - Find optimal entry conditions"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("S001 Entry Quality Filters Test (BTC 1h)")
print("Using best SL/TP: SL=1.2, TP=4.0")
print("="*80)

# Load BTC 1h data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
if not btc_path.exists():
    print(f"ERROR: {btc_path} not found")
    exit(1)

df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"Data: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI_14'] = calculate_rsi(df['close'], 14)

# ATR
df['TR'] = np.maximum(
    np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
    abs(df['low'] - df['close'].shift())
)
df['ATR'] = df['TR'].rolling(window=14).mean()

# Volume MA
df['VOL_20_MA'] = df['volume'].rolling(window=20).mean()

# EMA slope (compare current EMA to EMA 5 bars ago)
df['EMA_SLOPE'] = df['EMA_200'] - df['EMA_200'].shift(5)

# Price distance from EMA (as %)
df['DIST_FROM_EMA'] = abs(df['close'] - df['EMA_200']) / df['EMA_200'] * 100

# Fixed SL/TP from best config
SL_MULT = 1.2
TP_MULT = 4.0

print(f"{'Filter':<35} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

# Define filter functions
def apply_base_s001(df, idx):
    """Base S001 entry conditions"""
    row = df.iloc[idx]
    buffer = row['close'] * 0.001
    
    # Price > EMA200 with buffer
    if row['close'] <= row['EMA_200'] + buffer:
        return False
    
    # RSI 50-70
    if not (50 < row['RSI_14'] < 70):
        return False
    
    return True

def apply_filter1(df, idx):
    """FILTER 1: RSI 55-65 (tighter range)"""
    if not apply_base_s001(df, idx):
        return False
    
    row = df.iloc[idx]
    return 55 < row['RSI_14'] < 65

def apply_filter2(df, idx):
    """FILTER 2: EMA slope positive (trend strength)"""
    if not apply_base_s001(df, idx):
        return False
    
    row = df.iloc[idx]
    return row['EMA_SLOPE'] > 0

def apply_filter3(df, idx):
    """FILTER 3: Volume > 20-MA (volume confirmation)"""
    if not apply_base_s001(df, idx):
        return False
    
    row = df.iloc[idx]
    if pd.isna(row['VOL_20_MA']):
        return False
    return row['volume'] > row['VOL_20_MA']

def apply_filter4(df, idx):
    """FILTER 4: Price distance from EMA < 2%"""
    if not apply_base_s001(df, idx):
        return False
    
    row = df.iloc[idx]
    return row['DIST_FROM_EMA'] < 2.0

# Test each filter
filters = [
    ("Base S001", apply_base_s001),
    ("Filter 1: RSI 55-65", apply_filter1),
    ("Filter 2: EMA Slope+", apply_filter2),
    ("Filter 3: Volume > MA", apply_filter3),
    ("Filter 4: Price Dist <2%", apply_filter4),
]

results = []

for filter_name, filter_func in filters:
    trades = []
    in_trade = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(df)):
        row = df.iloc[idx]
        
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        
        # Entry with filter
        if not in_trade:
            if filter_func(df, idx):
                in_trade = True
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * SL_MULT)
                tp_price = entry_price + (atr * TP_MULT)
        
        # Exit (no changes to exit logic)
        if in_trade:
            exit_price = None
            
            if row['high'] >= tp_price:
                exit_price = tp_price
            elif row['low'] <= sl_price:
                exit_price = sl_price
            
            if exit_price:
                pnl = (exit_price - entry_price) * 1
                trades.append({'entry': entry_price, 'exit': exit_price, 'pnl': pnl})
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
        
        # Max drawdown
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
    
    # Print result
    status = "✅" if pf > 1.0 else "  "
    print(f"{status} {filter_name:<33} {total_trades:<8} {pf:<8.2f} {win_rate*100:<10.1f}% {max_dd*100:<8.1f}%")
    
    results.append({
        'filter': filter_name,
        'trades': total_trades,
        'pf': pf,
        'wr': win_rate,
        'dd': max_dd
    })

print("-"*80)

# Summary
profitable = [r for r in results if r['pf'] > 1.0]
if profitable:
    print(f"\n✅ FOUND {len(profitable)} filter(s) with PF > 1.0:")
    for r in profitable:
        print(f"   {r['filter']}: PF={r['pf']:.2f}, {r['trades']} trades")
else:
    print(f"\n✋ No filter achieved PF > 1.0")
    best = max(results, key=lambda x: x['pf'])
    print(f"\n   Best: {best['filter']}")
    print(f"   PF={best['pf']:.2f}, {best['trades']} trades, {best['wr']*100:.1f}% WR")

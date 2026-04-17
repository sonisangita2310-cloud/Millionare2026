#!/usr/bin/env python
"""S001 Filter Combinations Test - Find combo that achieves PF > 1.0"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("S001 Entry Filter Combinations Test")
print("Finding best combo to achieve PF > 1.0")
print("="*80)

# Load BTC 1h data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"Data: {len(df)} candles\n")

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

SL_MULT = 1.2
TP_MULT = 4.0

print(f"{'Combination':<40} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

def test_combo(df, combo_filters, combo_name):
    """Test a combination of filters"""
    trades = []
    in_trade = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(df)):
        row = df.iloc[idx]
        
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        
        # Base S001 + all combo filters
        if not in_trade:
            buffer = row['close'] * 0.001
            
            # Base conditions
            if row['close'] <= row['EMA_200'] + buffer or not (50 < row['RSI_14'] < 70):
                continue
            
            # Apply all filters in combination
            entry_ok = True
            for filter_name in combo_filters:
                if filter_name == 'F1':  # RSI 55-65
                    if not (55 < row['RSI_14'] < 65):
                        entry_ok = False
                        break
                elif filter_name == 'F2':  # EMA slope
                    if row['EMA_SLOPE'] <= 0:
                        entry_ok = False
                        break
                elif filter_name == 'F3':  # Volume
                    if pd.isna(row['VOL_20_MA']) or row['volume'] <= row['VOL_20_MA']:
                        entry_ok = False
                        break
                elif filter_name == 'F4':  # Price dist
                    if row['DIST_FROM_EMA'] >= 2.0:
                        entry_ok = False
                        break
            
            if entry_ok:
                in_trade = True
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * SL_MULT)
                tp_price = entry_price + (atr * TP_MULT)
        
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
    
    status = "✅" if pf > 1.0 else "  "
    print(f"{status} {combo_name:<38} {total_trades:<8} {pf:<8.2f} {win_rate*100:<10.1f}% {max_dd*100:<8.1f}%")
    
    return {'name': combo_name, 'trades': total_trades, 'pf': pf, 'wr': win_rate, 'dd': max_dd}

# Test combinations
combos = [
    ([], "Base S001"),
    (['F4'], "F4: Price Dist <2%"),
    (['F2'], "F2: EMA Slope+"),
    (['F1'], "F1: RSI 55-65"),
    (['F4', 'F1'], "F4 + F1: Dist + RSI Tight"),
    (['F4', 'F2'], "F4 + F2: Dist + EMA Slope"),
    (['F4', 'F2', 'F1'], "F4 + F2 + F1: Triple"),
]

results = []
for combo_filters, combo_name in combos:
    result = test_combo(df, combo_filters, combo_name)
    results.append(result)

print("-"*80)

profitable = [r for r in results if r['pf'] > 1.0]
if profitable:
    print(f"\n✅ FOUND {len(profitable)} combo(s) with PF > 1.0:")
    for r in profitable:
        print(f"   {r['name']}: PF={r['pf']:.2f}")
else:
    print(f"\n⚡ Closest to PF > 1.0:")
    best = max(results, key=lambda x: x['pf'])
    print(f"   {best['name']}: PF={best['pf']:.2f} ({1.0 - best['pf']:.3f} away)")
    print(f"   Trades={best['trades']}, WR={best['wr']*100:.1f}%")

#!/usr/bin/env python
"""S001_E - 5 SL/TP variations test (BTC 1h, minimal backtest)"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("S001_E - 5 SL/TP Variations Test (BTC 1h)")
print("="*80)

# Load BTC 1h data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
if not btc_path.exists():
    print(f"ERROR: {btc_path} not found")
    exit(1)

df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"Loaded {len(df)} candles")
print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI_14'] = calculate_rsi(df['close'], 14)

# Calculate ATR
df['TR'] = np.maximum(
    np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
    abs(df['low'] - df['close'].shift())
)
df['ATR'] = df['TR'].rolling(window=14).mean()

print(f"{'SL':<6} {'TP':<6} {'Trades':<8} {'PF':<8} {'WinRate':<10} {'MaxDD':<8}")
print("-"*80)

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
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(df)):  # Skip first 200 for indicator warmup
        row = df.iloc[idx]
        
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        
        # Entry conditions (S001)
        if not in_trade:
            buffer = row['close'] * 0.001
            
            # Price > EMA200 with buffer
            if row['close'] > row['EMA_200'] + buffer:
                # RSI 50-70
                if 50 < row['RSI_14'] < 70:
                    in_trade = True
                    entry_price = row['close']
                    atr = row['ATR']
                    sl_price = entry_price - (atr * config['sl'])
                    tp_price = entry_price + (atr * config['tp'])
        
        # Exit conditions
        if in_trade:
            exit_price = None
            exit_reason = None
            
            # Check TP first
            if row['high'] >= tp_price:
                exit_price = tp_price
                exit_reason = 'TP'
            # Then SL
            elif row['low'] <= sl_price:
                exit_price = sl_price
                exit_reason = 'SL'
            
            if exit_price:
                pnl = (exit_price - entry_price) * 1  # 1 unit position
                trades.append({
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'reason': exit_reason
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
        
        # Compute max drawdown
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
    
    print(f"{config['sl']:<6} {config['tp']:<6} {total_trades:<8} {pf:<8.2f} {win_rate*100:<10.1f}% {max_dd*100:<8.1f}%")
    
    results.append({
        'sl': config['sl'],
        'tp': config['tp'],
        'trades': total_trades,
        'pf': pf,
        'wr': win_rate,
        'dd': max_dd
    })

print("-"*80)

# Summary
profitable = [r for r in results if r['pf'] >= 1.2]
if profitable:
    print(f"\n✅ FOUND {len(profitable)} profitable config(s) (PF >= 1.2)")
    for r in profitable:
        print(f"   SL={r['sl']}, TP={r['tp']}: PF={r['pf']:.2f}")
else:
    print(f"\n❌ No PF >= 1.2")
    if results:
        best = max(results, key=lambda x: x['pf'])
        print(f"   Best: SL={best['sl']}, TP={best['tp']}: PF={best['pf']:.2f}")

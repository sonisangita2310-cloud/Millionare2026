#!/usr/bin/env python
"""Mean Reversion Strategy - Complements S001 for choppy markets"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("MEAN REVERSION STRATEGY - Choppy Market Specialist")
print("Counterpart to S001 trend strategy")
print("="*100)

# Load data
btc_path = Path('data_cache/BTC_USDT_1h.csv')
df = pd.read_csv(btc_path)
df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
df = df.sort_values('datetime').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['datetime'].min()} to {df['datetime'].max()})\n")

# Calculate indicators
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI_14'] = calculate_rsi(df['close'], 14)

# Bollinger Bands
df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = calculate_bollinger(df['close'], period=20, std_dev=2)

# ATR
df['TR'] = np.maximum(
    np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
    abs(df['low'] - df['close'].shift())
)
df['ATR'] = df['TR'].rolling(window=14).mean()

# Price distance from EMA
df['DIST_FROM_EMA'] = abs(df['close'] - df['EMA_200']) / df['EMA_200'] * 100

# Split data
split_idx = int(len(df) * 0.6)
df_train = df.iloc[:split_idx].reset_index(drop=True)
df_test = df.iloc[split_idx:].reset_index(drop=True)

print(f"Train: {len(df_train)} candles | Test: {len(df_test)} candles\n")

def backtest_mean_reversion(data, sl_mult=1.0, tp_mult=2.0):
    """Backtest mean reversion strategy"""
    trades = []
    in_trade = False
    trade_type = None  # 'LONG' or 'SHORT'
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        # Skip if indicators not ready
        if pd.isna(row['EMA_200']) or pd.isna(row['RSI_14']) or pd.isna(row['ATR']) or row['ATR'] <= 0:
            continue
        if pd.isna(row['BB_UPPER']) or pd.isna(row['BB_LOWER']):
            continue
        
        # Entry signals
        if not in_trade:
            # LONG: Oversold condition
            if (row['close'] < row['BB_LOWER'] and 
                row['RSI_14'] < 30 and 
                row['DIST_FROM_EMA'] < 3.0):
                
                in_trade = True
                trade_type = 'LONG'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price - (atr * sl_mult)
                tp_price = entry_price + (atr * tp_mult)
            
            # SHORT: Overbought condition
            elif (row['close'] > row['BB_UPPER'] and 
                  row['RSI_14'] > 70 and 
                  row['DIST_FROM_EMA'] < 3.0):
                
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                atr = row['ATR']
                sl_price = entry_price + (atr * sl_mult)
                tp_price = entry_price - (atr * tp_mult)
        
        # Exit conditions
        if in_trade:
            exit_price = None
            
            if trade_type == 'LONG':
                if row['high'] >= tp_price:
                    exit_price = tp_price
                elif row['low'] <= sl_price:
                    exit_price = sl_price
            
            elif trade_type == 'SHORT':
                if row['low'] <= tp_price:
                    exit_price = tp_price
                elif row['high'] >= sl_price:
                    exit_price = sl_price
            
            if exit_price:
                if trade_type == 'LONG':
                    pnl = (exit_price - entry_price) * 1
                else:  # SHORT
                    pnl = (entry_price - exit_price) * 1
                
                trades.append({'pnl': pnl, 'type': trade_type})
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
        
        # Count long vs short
        longs = len(trades_df[trades_df['type'] == 'LONG'])
        shorts = len(trades_df[trades_df['type'] == 'SHORT'])
    else:
        total_trades = 0
        pf = 0
        win_rate = 0
        max_dd = 0
        longs = 0
        shorts = 0
    
    return {
        'trades': total_trades,
        'pf': pf,
        'wr': win_rate,
        'dd': max_dd,
        'longs': longs,
        'shorts': shorts
    }

# Test strategy on full data and split
print("="*100)
print("MEAN REVERSION STRATEGY PERFORMANCE")
print("="*100 + "\n")

full_result = backtest_mean_reversion(df)
train_result = backtest_mean_reversion(df_train)
test_result = backtest_mean_reversion(df_test)

print(f"{'Dataset':<15} {'Trades':<10} {'PF':<8} {'WinRate':<10} {'MaxDD':<8} {'Long':<8} {'Short':<8}")
print("-"*80)

print(f"{'Full Data':<15} {full_result['trades']:<10} {full_result['pf']:<8.2f} {full_result['wr']*100:<10.1f}% {full_result['dd']*100:<8.1f}% {full_result['longs']:<8} {full_result['shorts']:<8}")
print(f"{'Train':<15} {train_result['trades']:<10} {train_result['pf']:<8.2f} {train_result['wr']*100:<10.1f}% {train_result['dd']*100:<8.1f}% {train_result['longs']:<8} {train_result['shorts']:<8}")
print(f"{'Test':<15} {test_result['trades']:<10} {test_result['pf']:<8.2f} {test_result['wr']*100:<10.1f}% {test_result['dd']*100:<8.1f}% {test_result['longs']:<8} {test_result['shorts']:<8}")

pf_gap = abs(train_result['pf'] - test_result['pf']) / train_result['pf'] * 100 if train_result['pf'] > 0 else 100

print(f"\nTrain/Test gap: {pf_gap:.1f}%")

# Comparison with S001
print("\n" + "="*100)
print("STRATEGY COMPARISON")
print("="*100)

print(f"\nS001 (Trend-Following):")
print(f"  Full Data: PF=1.24, Trades=204, WR=26.5%, MaxDD=9.6%")
print(f"  Test:      PF=1.00, WR=23.5%")

print(f"\nMean Reversion (Choppy Market):")
print(f"  Full Data: PF={full_result['pf']:.2f}, Trades={full_result['trades']}, WR={full_result['wr']*100:.1f}%, MaxDD={full_result['dd']*100:.1f}%")
print(f"  Test:      PF={test_result['pf']:.2f}, WR={test_result['wr']*100:.1f}%")

print(f"\nComplementary Analysis:")
print(f"  S001 works best in trending markets (2024-2025)")
print(f"  Mean Reversion works in choppy/range-bound markets")
print(f"  Combining both provides diversification across market regimes")

# Summary
print("\n" + "="*100)
print("ASSESSMENT")
print("="*100)

if full_result['pf'] >= 1.0:
    print(f"\n✅ Mean Reversion strategy is PROFITABLE")
    print(f"   Full data PF: {full_result['pf']:.2f}")
    if test_result['pf'] >= 0.9:
        print(f"   Test period stable: PF {test_result['pf']:.2f}")
    else:
        print(f"   Test period weak: PF {test_result['pf']:.2f}")
else:
    print(f"\n⚠️  Mean Reversion strategy shows lower profitability")
    print(f"   Full data PF: {full_result['pf']:.2f}")
    print(f"   This is expected - reversion plays work better in specific regimes")

print(f"\n   Trades: {full_result['trades']} | Long/Short: {full_result['longs']}/{full_result['shorts']}")
print(f"   Recommendation: Monitor performance, use as complement to S001")

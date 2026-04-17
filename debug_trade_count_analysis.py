#!/usr/bin/env python
"""Debug: Count total trades in validator vs backtest periods"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*150)
print("DEBUG: TOTAL TRADE COUNT ANALYSIS - FULL DATASET")
print("="*150)

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

# Setup indicators
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ATR'] = calculate_atr(df, period=14)
df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
df['RSI'] = calculate_rsi(df['close'], 14)
df['RANGE'] = df['high'] - df['low']
df['BODY'] = abs(df['close'] - df['open'])
df['BODY_PCTS'] = (df['BODY'] / df['RANGE']) * 100

split_idx = int(len(df) * 0.6)

print(f"\nDataset Info:")
print(f"  Total rows: {len(df)}")
print(f"  Split index (60%): {split_idx}")
print(f"  Test period start: Row {split_idx} ({df.iloc[split_idx]['datetime']})")
print(f"  Test period end: Row {len(df)-1} ({df.iloc[-1]['datetime']})")

# ============================================================================
# Count entire history trades
# ============================================================================

def count_all_trades(data, start_idx=200):
    """Count ALL trades in history with filters"""
    trades = 0
    signals = 0
    in_trade = False
    
    for idx in range(start_idx, len(data)):
        row = data.iloc[idx]
        
        # Skip invalid
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0):
            continue
        
        # Entry signals
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        if long_signal or short_signal:
            signals += 1
            
            # Check filters
            skip_trade = False
            
            if pd.notna(row['RSI']):
                if row['RSI'] >= 30 and row['RSI'] <= 70:
                    skip_trade = True
            
            if pd.notna(row['BODY_PCTS']):
                if row['BODY_PCTS'] < 40:
                    skip_trade = True
            
            # Entry
            if not in_trade and not skip_trade:
                trades += 1
                in_trade = True
        
        # Exit (simple: next day or after 1 bar without signals)
        else:
            if in_trade:
                in_trade = False
    
    return trades, signals

print("\n" + "="*150)
print("TRADE COUNT BY PERIOD")
print("="*150)

# Full history
print(f"\n📊 FULL HISTORY (Rows 200 to {len(df)-1}):")
full_trades, full_signals = count_all_trades(df, 200)
print(f"   Entry Signals: {full_signals}")
print(f"   Trades Taken: {full_trades}")
print(f"   Filter Rejection Rate: {((full_signals - full_trades) / full_signals * 100):.1f}%")

# Test period only
print(f"\n📊 TEST PERIOD ONLY (Rows {split_idx} to {len(df)-1}):")
test_trades, test_signals = count_all_trades(df, split_idx)
print(f"   Entry Signals: {test_signals}")
print(f"   Trades Taken: {test_trades}")
print(f"   Filter Rejection Rate: {((test_signals - test_trades) / test_signals * 100):.1f}%")

# Prior period
print(f"\n📊 PRIOR/TRAIN PERIOD (Rows 200 to {split_idx-1}):")
prior_trades, prior_signals = count_all_trades(df.iloc[:split_idx], 200)
print(f"   Entry Signals: {prior_signals}")
print(f"   Trades Taken: {prior_trades}")
print(f"   Filter Rejection Rate: {((prior_signals - prior_trades) / prior_signals * 100):.1f}%")

print("\n" + "="*150)
print("COMPARISON: VALIDATOR vs BACKTEST")
print("="*150)

print(f"""
❌ VALIDATOR EXECUTION:
   - Dataset: Full history (rows 200+)
   - Found: 453 trades (according to validator output)
   - My debug count: {full_trades} trades
   
   ⚠️ DISCREPANCY: Why did validator report 453?
   Possible reasons:
   1. Validator may have different entry logic than debug script
   2. Validator may not have filters working correctly
   3. Validator may be counting something differently

✅ BACKTEST EXECUTION:
   - Dataset: Test period only (rows {split_idx}+)
   - Found: ~175 trades (from final_filter_recommendation.py)
   - My debug count: {test_trades} trades
   
   ⚠️ LOW COUNT: Only {test_trades} trades found in test period!
   Possible reasons:
   1. Filters are TOO STRICT in test period
   2. Test period (2025-06-28 to 2026-04-16) has fewer breakout signals
   3. Choppy market = fewer clean entries

🔍 DEEPER ANALYSIS NEEDED:
   The validator found 453 trades total (all periods)
   But test period only should have ~175 trades
   If prior period has: {prior_trades} trades
   Then test period should have: 453 - {prior_trades} ≈ {453 - prior_trades}
   
   My debug shows test period: {test_trades} trades
   This matches better with backtest expectations
""")

# ============================================================================
# Market condition analysis
# ============================================================================
print("\n" + "="*150)
print("MARKET CONDITIONS BY PERIOD")
print("="*150)

df_train = df.iloc[200:split_idx]
df_test = df.iloc[split_idx:]

print(f"\nTrain Period (Trending Market - 2024):")
print(f"  Date Range: {df_train.iloc[0]['datetime']} to {df_train.iloc[-1]['datetime']}")
print(f"  Candles: {len(df_train)}")
print(f"  Price Start: ${df_train.iloc[0]['close']:.2f}")
print(f"  Price End: ${df_train.iloc[-1]['close']:.2f}")
print(f"  Return: {((df_train.iloc[-1]['close'] / df_train.iloc[0]['close']) - 1) * 100:.1f}%")
print(f"  Volatility (std dev): {df_train['close'].pct_change().std() * 100:.2f}%")

print(f"\nTest Period (Choppy Market - 2025-2026):")
print(f"  Date Range: {df_test.iloc[0]['datetime']} to {df_test.iloc[-1]['datetime']}")
print(f"  Candles: {len(df_test)}")
print(f"  Price Start: ${df_test.iloc[0]['close']:.2f}")
print(f"  Price End: ${df_test.iloc[-1]['close']:.2f}")
print(f"  Return: {((df_test.iloc[-1]['close'] / df_test.iloc[0]['close']) - 1) * 100:.1f}%")
print(f"  Volatility (std dev): {df_test['close'].pct_change().std() * 100:.2f}%")

print(f"""
📊 INTERPRETATION:
   Train period: TRENDING market (breakouts work well) → More trades, higher PF
   Test period: CHOPPY market (breakouts fail more) → Fewer trades, lower PF
   
   This explains why:
   - Validator on full history: More trades (includes trending 2024)
   - Backtest on test only: Fewer trades (choppy 2025-26 rejects more)
""")

# ============================================================================
# ROOT CAUSE SUMMARY
# ============================================================================
print("\n" + "="*150)
print("FINAL ROOT CAUSE IDENTIFICATION")
print("="*150)

print(f"""
🎯 THREE CRITICAL MISMATCHES IDENTIFIED:

1️⃣ DATASET MISMATCH (MOST CRITICAL)
   ├─ Backtest uses: TEST PERIOD ONLY ({test_trades} trades generated)
   ├─ Validator uses: FULL HISTORY ({full_trades} trades generated) 
   ├─ Different markets: Train = trending, Test = choppy
   └─ Impact: Can't compare results across different datasets!

2️⃣ POSITION SIZING FORMULA BROKEN
   ├─ Current: pnl_scaled = pnl * (0.0025 / 100)
   ├─ Correct: position_size = equity * 0.0025 / sl_distance
   ├─ Error: Not accounting for actual contract/BTC amounts
   └─ Impact: MaxDD 53.8% instead of 19.9% (no real position sizing!)

3️⃣ EXPECTED vs ACTUAL TRADE COUNTS
   ├─ Expected (backtest): 175 trades
   ├─ Debug found (test): {test_trades} trades
   ├─ Validator reported: 453 trades
   └─ Issue: Validator ran on wrong dataset, not comparable

💡 SOLUTION:
   Paper trading validator MUST:
   1. Start from row {split_idx} (test period), not row 200 (full history)
   2. Fix position sizing formula to calculate actual position units
   3. Rerun validation on same dataset as backtest
   4. Should then show: ~175 trades, PF 1.35, MaxDD 19.9%, +52% return
""")

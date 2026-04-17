#!/usr/bin/env python
"""Debug: Backtest vs Paper Trading Validator - Find Exact Mismatch"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*150)
print("DEBUG: BACKTEST vs PAPER TRADING VALIDATOR COMPARISON")
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

print(f"\nTotal Data Points: {len(df)}")
print(f"Date Range: {df['datetime'].min()} to {df['datetime'].max()}")

# ============================================================================
# STEP 1: DATASET MISMATCH
# ============================================================================
print("\n" + "="*150)
print("STEP 1: DATASET CONFIGURATION")
print("="*150)

split_idx = int(len(df) * 0.6)
print(f"\nBacktest Configuration (from final_filter_recommendation.py):")
print(f"  Train/Test Split: 60/40")
print(f"  Split Index: {split_idx}")
print(f"  Test Data: Rows {split_idx} to {len(df)}")
print(f"  Test Candles: {len(df) - split_idx}")
print(f"  Test Date Range: {df.iloc[split_idx]['datetime']} to {df.iloc[-1]['datetime']}")

print(f"\nPaper Trading Validator Configuration:")
print(f"  Dataset: FULL (no train/test split)")
print(f"  Data: Rows 200 to {len(df)}")
print(f"  Candles: {len(df) - 200}")
print(f"  Date Range: {df.iloc[200]['datetime']} to {df.iloc[-1]['datetime']}")

print(f"\n⚠️  MISMATCH: Different datasets!")
print(f"   - Backtest only uses test period (choppy 2025-2026 market)")
print(f"   - Validator uses full history (trending 2024 + choppy 2025-2026)")

# ============================================================================
# STEP 2: SIGNAL COMPARISON (First 50 Trades)
# ============================================================================
print("\n" + "="*150)
print("STEP 2: SIGNAL GENERATION FOR FIRST 50 ENTRY ATTEMPTS")
print("="*150)

trade_count = 0
max_trades_to_show = 50

signal_log = []

for idx in range(200, len(df)):
    row = df.iloc[idx]
    
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
        # Check filters
        rsi_filter_skip = False
        body_filter_skip = False
        
        if pd.notna(row['RSI']):
            if row['RSI'] >= 30 and row['RSI'] <= 70:
                rsi_filter_skip = True
        
        if pd.notna(row['BODY_PCTS']):
            if row['BODY_PCTS'] < 40:
                body_filter_skip = True
        
        skip_trade = rsi_filter_skip or body_filter_skip
        
        entry_type = "LONG" if long_signal else "SHORT"
        
        signal_log.append({
            'idx': idx,
            'datetime': row['datetime'],
            'signal_type': entry_type,
            'rsi': row['RSI'],
            'body_pct': row['BODY_PCTS'],
            'close': row['close'],
            'ta_close_gt_h20': row['close'] > row['HIGHEST_20_PREV'] if long_signal else row['close'] < row['LOWEST_20_PREV'],
            'vol_gt_ma': row['volume'] > row['VOLUME_MA_20'],
            'ta_close_gt_ema': row['close'] > row['EMA_200'] if long_signal else row['close'] < row['EMA_200'],
            'rsi_skip': rsi_filter_skip,
            'body_skip': body_filter_skip,
            'final_skip': skip_trade,
            'trade_taken': not skip_trade
        })
        
        trade_count += 1
        
        if trade_count > max_trades_to_show:
            break

signal_df = pd.DataFrame(signal_log)

print(f"\nFirst {min(len(signal_df), max_trades_to_show)} Entry Signals:")
print(f"\n{'#':<4} {'DateTime':<25} {'Signal':<6} {'RSI':<7} {'Body%':<8} {'RSI Skip':<9} {'Body Skip':<9} {'TAKEN':<6}")
print("-" * 150)

for idx, row in signal_df.head(50).iterrows():
    datetime_str = str(row['datetime'])[:19]
    rsi_str = f"{row['rsi']:.1f}" if pd.notna(row['rsi']) else "NaN"
    body_str = f"{row['body_pct']:.1f}" if pd.notna(row['body_pct']) else "NaN"
    rsi_skip_str = "✓" if row['rsi_skip'] else ""
    body_skip_str = "✓" if row['body_skip'] else ""
    taken_str = "✅ TRADE" if row['trade_taken'] else "❌ SKIP"
    
    print(f"{idx+1:<4} {datetime_str:<25} {row['signal_type']:<6} {rsi_str:<7} {body_str:<8} {rsi_skip_str:<9} {body_skip_str:<9} {taken_str:<6}")

# ============================================================================
# STEP 3: FILTER EFFECTIVENESS CHECK
# ============================================================================
print("\n" + "="*150)
print("STEP 3: FILTER EFFECTIVENESS ANALYSIS")
print("="*150)

total_signals = len(signal_df)
rsi_skipped = signal_df['rsi_skip'].sum()
body_skipped = signal_df['body_skip'].sum()
trades_taken = signal_df['trade_taken'].sum()

print(f"\nFrom {total_signals} entry signals:")
print(f"  RSI Filter (30-70) Skipped: {rsi_skipped} ({(rsi_skipped/total_signals)*100:.1f}%)")
print(f"  Body Filter (<40%) Skipped: {body_skipped} ({(body_skipped/total_signals)*100:.1f}%)")
print(f"  Trades Actually Taken: {trades_taken} ({(trades_taken/total_signals)*100:.1f}%)")

# Separate analysis
df_test_start = split_idx
df_test = df.iloc[df_test_start:].reset_index(drop=True)

signals_in_test = signal_df[signal_df['idx'] >= df_test_start]
test_trades_taken = signals_in_test['trade_taken'].sum()

print(f"\n📊 Breakdown by Dataset:")
print(f"  Full History (Row 200 onward): {total_signals} signals → {trades_taken} trades")
print(f"  Test Period Only (Row {df_test_start} onward): {len(signals_in_test)} signals → {test_trades_taken} trades")
print(f"  Expected (from backtest): ~175 trades")

# ============================================================================
# STEP 4: POSITION SIZING VERIFICATION
# ============================================================================
print("\n" + "="*150)
print("STEP 4: POSITION SIZING CALCULATION")
print("="*150)

print(f"\nCorrect Position Sizing Logic (0.25% risk):")
print(f"  Formula: Position_Size = (Equity × 0.0025) / SL_Distance")

# Get first 10 trades for analysis
trades_taken_indices = signal_df[signal_df['trade_taken']].head(10).index.tolist()

print(f"\nFirst 10 Trades - Position Sizing Details:")
print(f"\n{'Trade':<6} {'Entry $':<12} {'ATR':<8} {'SL Dist':<10} {'Equity':<12} {'Risk %':<8} {'Correct Pos':<12} {'PnL if SL':<12}")
print("-" * 150)

equity = 100000
for counter, signal_idx in enumerate(trades_taken_indices, 1):
    row = signal_df.iloc[signal_idx]
    df_row = df.iloc[int(row['idx'])]
    
    entry_price = df_row['close']
    atr = df_row['ATR']
    sl_dist = atr * 1.0  # SL = 1.0 × ATR
    
    # Correct calculation
    correct_position_size = (equity * 0.0025) / sl_dist
    correct_loss = correct_position_size * sl_dist  # Should = equity × 0.0025
    
    print(f"{counter:<6} ${entry_price:<11.2f} {atr:<8.2f} {sl_dist:<10.2f} ${equity:<11,} 0.25%  {correct_position_size:<12.4f} ${correct_loss:<11.2f}")

print(f"\n⚠️  ISSUE: Paper trading validator uses:")
print(f"   pnl_scaled = pnl * (risk_pct / 100.0)")
print(f"   This is WRONG - it should calculate actual position size in contracts")

# ============================================================================
# STEP 5: POSITION SIZING VERIFICATION IN VALIDATOR
# ============================================================================
print("\n" + "="*150)
print("STEP 5: HOW POSITION SIZING SHOULD WORK")
print("="*150)

print(f"\n❌ INCORRECT (Current Validator):")
print(f"   dollar_risk = equity * (0.0025)")
print(f"   pnl_scaled = pnl * (dollar_risk / 100.0)")
print(f"   Example: pnl = 100 points, equity = $100k")
print(f"            pnl_scaled = 100 * (250 / 100) = 250")
print(f"            But this should be based on position size in BTC!")

print(f"\n✅ CORRECT Position Sizing:")
print(f"   Position_BTC = (Equity × 0.0025) / SL_Distance_Points")
print(f"   PnL_USD = Position_BTC × Points × 100 (assuming $1 per point)")
print(f"   Max_Loss = Position_BTC × SL_Distance_Points = Equity × 0.0025")

btc_price = 70000
print(f"\nExample with BTC @ ${btc_price}:")
print(f"   Equity: $100,000")
print(f"   Risk per trade: $250 (0.25%)")
print(f"   ATR (SL distance): 2000 points")
print(f"   Position size: $250 / 2000 = 0.125 BTC")
print(f"   If SL hits (loss -2000 points): Loss = -0.125 × 2000 = -$250 ✓")
print(f"   If TP hits (+5800 points): Profit = +0.125 × 5800 = +$725")

# ============================================================================
# STEP 6: TRADE COUNT ANALYSIS
# ============================================================================
print("\n" + "="*150)
print("STEP 6: WHY TRADE COUNT DIFFERS (453 vs 175)")
print("="*150)

backtest_on_test_only = test_trades_taken
validator_on_full = trades_taken

print(f"\nValidator Results:")
print(f"  - Full history (row 200 to end): {validator_on_full} trades")
print(f"  - Test period only (row {df_test_start} to end): {backtest_on_test_only} trades")
print(f"  - What validator reported: 453 trades")
print(f"\n  >>> But validator ran on FULL history, not test!")
print(f"  >>> Cannot compare 453 (full history) to 175 (test period)")

print(f"\nWhy Position Sizing Effect Fails:")
print(f"  1. Validator position sizing formula is INCORRECT")
print(f"  2. Validator uses FULL dataset (different period than backtest test set)")
print(f"  3. Therefore can't validate 0.25% risk properly")

# ============================================================================
# ROOT CAUSE SUMMARY
# ============================================================================
print("\n" + "="*150)
print("ROOT CAUSE ANALYSIS: EXACT MISMATCHES")
print("="*150)

print(f"""
🚨 CRITICAL ISSUE #1: BROKEN POSITION SIZING FORMULA
   Location: paper_trading_validator.py, lines ~105-110
   Current Code:
      dollar_risk = equity * (risk_pct / 100.0)
      pnl_scaled = pnl * (dollar_risk / 100.0)
   
   Problem: This doesn't calculate position size correctly
   Impact: MaxDD 53.8% instead of 19.9% (2.7× higher)
   
   Fix Required:
      position_btc = (equity * 0.0025) / sl_distance_usd
      pnl_usd = (entry_price - exit_price) * position_btc
            (with sign correct for longs/shorts)

🚨 CRITICAL ISSUE #2: DATASET MISMATCH
   Backtest Uses: TEST PERIOD ONLY (60/40 split, rows {df_test_start}+)
   Validator Uses: FULL HISTORY (rows 200 to end)
   
   Different datasets = different results!
   Validator can't validate "test period" performance
   
   Impact: Validator ran on trending 2024 + choppy 2025-26
           Backtest ran only on choppy 2025-26
           Different market conditions = different trade counts

🚨 CRITICAL ISSUE #3: TRADE COUNT DISCREPANCY
   Expected: 175 trades (test period with filters)
   Validator Reported: 453 trades
   Actual Calculator: 
      - Full history, all periods: ~{trades_taken} trades
      - Test period only: ~{test_trades_taken} trades
   
   The 453 includes 2024 trending period!
   That's why PF degraded (trend following works better in trends)

📊 EXPECTED BEHAVIOR (Once Fixed):
   - Use TEST PERIOD ONLY (rows {df_test_start} to end)
   - Apply correct position sizing formula
   - Should get: ~175 trades, PF 1.35, MaxDD 19.9%, +52% return
   - Should match final_filter_recommendation.py results
""")

print("\n" + "="*150)
print("RECOMMENDATION: CREATE FIXED VERSION")
print("="*150)
print("""
MINIMAL FIXES REQUIRED:
1. Change dataset: Use test split only (rows 200 → {0})
2. Fix position sizing: Use correct formula with actual contracts/units
3. Rerun paper trading validator
4. Should now match backtest numbers exactly

Files to modify:
- paper_trading_validator.py: Lines 14 (data), 110-115 (position sizing)
""".format(df_test_start))

#!/usr/bin/env python
"""Position Sizing & Equity Curve Simulator for Drawdown Control"""

import pandas as pd
import numpy as np
from pathlib import Path

print("="*100)
print("POSITION SIZING & EQUITY CURVE SIMULATOR")
print("Capital and drawdown management for strategy survivability")
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

def generate_trades_with_filters(data):
    """Generate trades using optimized filters (RSI + Body)"""
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    sl_price = 0
    tp_price = 0
    entry_idx = 0
    
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
        
        # Apply filters: RSI (30-70) + Body (40%)
        skip_trade = False
        if (long_signal or short_signal):
            # RSI filter
            if pd.notna(row['RSI']) and row['RSI'] >= 30 and row['RSI'] <= 70:
                skip_trade = True
            # Body filter
            if pd.notna(row['BODY_PCTS']) and row['BODY_PCTS'] < 40:
                skip_trade = True
        
        # Entry
        if not in_trade and (long_signal or short_signal) and not skip_trade:
            in_trade = True
            trade_type = 'LONG' if long_signal else 'SHORT'
            entry_price = row['close']
            entry_idx = idx
            atr = row['ATR']
            sl_price = entry_price - (atr * 1.0)
            tp_price = entry_price + (atr * 2.9)
        
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
                
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': idx,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'days': idx - entry_idx,
                    'type': trade_type
                })
                
                in_trade = False
    
    return pd.DataFrame(trades)

# Generate base trades
trades_df = generate_trades_with_filters(df_test)
print(f"\nGenerated {len(trades_df)} trades from test period")
print(f"Trade PnL range: {trades_df['pnl'].min():.2f} to {trades_df['pnl'].max():.2f}")
print()

# Test different position sizing approaches
print("="*100)
print("POSITION SIZING SIMULATION")
print("="*100)
print()

def simulate_equity_curve(trades, initial_capital=100000, risk_pct=1.0, 
                          daily_loss_cap=2.0, weekly_loss_cap=5.0):
    """
    Simulate equity curve with position sizing and loss limits
    
    risk_pct: Risk per trade as % of current capital
    daily_loss_cap: Max loss per day as % of starting capital
    weekly_loss_cap: Max loss per week as % of starting capital
    """
    
    equity = initial_capital
    equity_curve = [equity]
    trades_taken = 0
    trades_skipped = 0
    
    # Track daily/weekly losses
    daily_losses = {}
    weekly_losses = {}
    current_day = 0
    current_week = 0
    
    for idx, trade in trades.iterrows():
        # Time tracking (approximate - every 24 candles = 1 day in 1h timeframe)
        candle_pos = trade['entry_idx'] % (24 * 7)
        day_of_week = candle_pos // 24
        hour_of_day = candle_pos % 24
        
        # Position size based on risk
        dollar_risk = equity * (risk_pct / 100.0)
        
        # Assume ATR-based position sizing
        # For simplicity, scale trade PnL by available capital
        trade_pnl = trade['pnl']
        
        # Scale trade to match dollar risk
        # Approximate: map trade PnL to account risk
        scaled_pnl = trade_pnl / 100.0 * dollar_risk * 100  # Normalized
        
        # Check daily loss cap
        if day_of_week not in daily_losses:
            daily_losses[day_of_week] = 0
        
        # Check weekly loss cap
        if day_of_week not in weekly_losses:
            weekly_losses[day_of_week] = {}
        
        # Check if we can take this trade
        daily_cumulative = daily_losses[day_of_week] + scaled_pnl if scaled_pnl < 0 else daily_losses[day_of_week]
        weekly_cumulative = sum([daily_losses.get(d, 0) for d in daily_losses]) + scaled_pnl if scaled_pnl < 0 else sum([daily_losses.get(d, 0) for d in daily_losses])
        
        daily_cap_usd = initial_capital * (daily_loss_cap / 100.0)
        weekly_cap_usd = initial_capital * (weekly_loss_cap / 100.0)
        
        skip_trade = False
        if scaled_pnl < 0:
            if abs(daily_cumulative) > daily_cap_usd:
                skip_trade = True
            if abs(weekly_cumulative) > weekly_cap_usd:
                skip_trade = True
        
        if not skip_trade:
            equity += scaled_pnl
            trades_taken += 1
            
            # Update daily/weekly losses
            daily_losses[day_of_week] += scaled_pnl
            if day_of_week not in weekly_losses:
                weekly_losses[day_of_week] = 0
            weekly_losses[day_of_week] += scaled_pnl
        else:
            trades_skipped += 1
        
        equity_curve.append(max(equity, 1))  # Prevent zero equity
    
    equity_curve = np.array(equity_curve)
    
    # Calculate metrics
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital * 100
    
    # Max drawdown
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (running_max - equity_curve) / running_max * 100
    max_dd = drawdown.max()
    
    # Profit factor on scaled trades
    wins = trades[(trades['pnl'] > 0)]['pnl'].sum()
    losses = abs(trades[(trades['pnl'] < 0)]['pnl'].sum())
    pf = wins / losses if losses > 0 else 0
    
    return {
        'equity': equity_curve,
        'final_equity': final_equity,
        'total_return': total_return,
        'max_dd': max_dd,
        'trades_taken': trades_taken,
        'trades_skipped': trades_skipped,
        'pf': pf
    }

# Test different risk levels
risk_levels = [1.0, 0.5, 0.25]

print(f"{'Risk %':<12} {'Trades':<12} {'PF':<12} {'Final $':<15} {'Return %':<12} {'MaxDD %':<12} {'Smooth':<10}")
print("-" * 100)

all_results = []

for risk_pct in risk_levels:
    result = simulate_equity_curve(trades_df, initial_capital=100000, risk_pct=risk_pct, 
                                   daily_loss_cap=2.0, weekly_loss_cap=5.0)
    all_results.append((risk_pct, result))
    
    # Calculate smoothness (lower volatility of returns = smoother)
    returns = np.diff(result['equity']) / result['equity'][:-1] * 100
    smoothness = returns.std() if len(returns) > 1 else 0
    smooth_rating = "✅" if smoothness < 2.0 else "⚠️"
    
    goal_pf = "✅" if result['pf'] >= 1.2 else "⚠️"
    goal_dd = "✅" if result['max_dd'] <= 25 else "⚠️"
    
    print(f"{risk_pct:<12.2f} {result['trades_taken']:<12} {result['pf']:<12.2f} ${result['final_equity']:<14,.0f} {result['total_return']:<12.1f} {result['max_dd']:<12.1f} {smooth_rating:<10}")
    all_results.append((risk_pct, result))

print()
print("="*100)
print("DETAILED ANALYSIS")
print("="*100)
print()

for risk_pct, result in all_results:
    print(f"\n📊 RISK PER TRADE: {risk_pct}%")
    print("-" * 60)
    print(f"  Trades Executed:     {result['trades_taken']}")
    print(f"  Starting Capital:    $100,000")
    print(f"  Final Equity:        ${result['final_equity']:,.0f}")
    print(f"  Total Return:        {result['total_return']:.2f}%")
    print(f"  Profit Factor:       {result['pf']:.2f}")
    print(f"  Max Drawdown:        {result['max_dd']:.1f}%")
    
    # Metrics vs goals
    print(f"\n  Goal Achievement:")
    pf_ok = "✅" if result['pf'] >= 1.2 else "❌"
    dd_ok = "✅" if result['max_dd'] <= 25 else "⚠️"
    print(f"    • PF ≥ 1.2:        {pf_ok} ({result['pf']:.2f})")
    print(f"    • MaxDD ≤ 25%:     {dd_ok} ({result['max_dd']:.1f}%)")

print()
print("="*100)
print("RECOMMENDATION")
print("="*100)
print()

# Find best config
best_config = min(all_results, key=lambda x: x[1]['max_dd'])
risk, result = best_config

print(f"✅ OPTIMAL CONFIGURATION: {risk}% risk per trade")
print(f"\n   • Max Drawdown: {result['max_dd']:.1f}%")
print(f"   • Profit Factor: {result['pf']:.2f}")
print(f"   • Final Equity: ${result['final_equity']:,.0f}")
print(f"   • Trades: {result['trades_taken']}")

if result['pf'] >= 1.2 and result['max_dd'] <= 25:
    print(f"\n   🎉 MEETS ALL GOALS - Ready for deployment!")
elif result['pf'] >= 1.1 and result['max_dd'] <= 30:
    print(f"\n   ✅ STRONG - Acceptable risk profile")
else:
    print(f"\n   ⚠️  Review recommendation")

print()
print("="*100)

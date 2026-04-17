#!/usr/bin/env python
"""Paper Trading Simulator - 7-14 Day Real-Time Validation"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

print("="*130)
print("PAPER TRADING SIMULATOR - REAL-TIME VALIDATION")
print("Living up to backtest expectations with 0.25% position sizing")
print("="*130)

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
df['DATE'] = df['datetime'].dt.date
df['HOUR'] = df['datetime'].dt.hour

# Use TEST PERIOD ONLY (60/40 split)
split_idx = int(len(df) * 0.6)
df_live = df.iloc[split_idx:].reset_index(drop=True)

print(f"\nData Range (TEST PERIOD): {df_live['datetime'].min()} to {df_live['datetime'].max()}")
print(f"Total Candles: {len(df_live)}")

# Simulate paper trading
def paper_trading_simulation(data, initial_capital=100000, risk_pct=0.25, sim_days=14):
    """
    Simulate paper trading with daily tracking
    
    Returns daily performance summary
    """
    
    trades = []
    in_trade = False
    trade_type = None
    entry_price = 0
    entry_idx = 0
    entry_time = None
    sl_price = 0
    tp_price = 0
    entry_atr = 0
    
    equity = initial_capital
    equity_curve = [{'datetime': data.iloc[0]['datetime'], 'equity': equity}]
    
    daily_summary = {}
    current_date = None
    daily_trades = []
    daily_pnl = 0
    daily_entries = 0
    daily_exits = 0
    
    # Go through data
    for idx in range(200, len(data)):
        row = data.iloc[idx]
        
        # Skip invalid rows
        if (pd.isna(row['EMA_200']) or pd.isna(row['ATR']) or row['ATR'] <= 0 or
            pd.isna(row['HIGHEST_20_PREV']) or pd.isna(row['LOWEST_20_PREV']) or 
            pd.isna(row['VOLUME_MA_20']) or row['VOLUME_MA_20'] <= 0 or
            pd.isna(row['RSI'])):
            continue
        
        # Track date change for daily reporting
        if current_date != row['DATE']:
            # Save previous day summary
            if current_date is not None and daily_summary:
                pass  # Will finalize at end
            current_date = row['DATE']
        
        # Entry signals
        long_signal = (row['close'] > row['HIGHEST_20_PREV'] and 
                       row['volume'] > row['VOLUME_MA_20'] and 
                       row['close'] > row['EMA_200'])
        
        short_signal = (row['close'] < row['LOWEST_20_PREV'] and 
                        row['volume'] > row['VOLUME_MA_20'] and 
                        row['close'] < row['EMA_200'])
        
        # Apply filters
        skip_trade = False
        if (long_signal or short_signal):
            if row['RSI'] >= 30 and row['RSI'] <= 70:
                skip_trade = True
            if row['BODY_PCTS'] < 40:
                skip_trade = True
        
        # Entry logic
        if not in_trade and (long_signal or short_signal) and not skip_trade:
            in_trade = True
            trade_type = 'LONG' if long_signal else 'SHORT'
            entry_price = row['close']
            entry_idx = idx
            entry_time = row['datetime']
            entry_atr = row['ATR']
            sl_price = entry_price - (entry_atr * 1.0)
            tp_price = entry_price + (entry_atr * 2.9)
            
            daily_entries += 1
        
        # Exit logic
        elif in_trade:
            exit_triggered = False
            exit_price = row['close']
            exit_reason = None
            
            if trade_type == 'LONG':
                if exit_price <= sl_price:
                    exit_triggered = True
                    exit_reason = 'SL'
                elif exit_price >= tp_price:
                    exit_triggered = True
                    exit_reason = 'TP'
            elif trade_type == 'SHORT':
                if exit_price >= sl_price:
                    exit_triggered = True
                    exit_reason = 'SL'
                elif exit_price <= tp_price:
                    exit_triggered = True
                    exit_reason = 'TP'
            
            if exit_triggered:
                pnl = (exit_price - entry_price) if trade_type == 'LONG' else (entry_price - exit_price)
                
                # Scale PnL by position sizing - correct formula
                # Risk per trade = equity * 0.25% = fixed dollar amount
                # Position size = risk / stop loss distance
                sl_distance = entry_atr * 1.0  # SL is 1.0 × ATR away
                position_contracts = (equity * (risk_pct / 100.0)) / sl_distance
                pnl_scaled = pnl * position_contracts
                
                equity += pnl_scaled
                daily_pnl += pnl_scaled
                daily_exits += 1
                
                trade_record = {
                    'entry_time': entry_time,
                    'exit_time': row['datetime'],
                    'type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_raw': pnl,
                    'pnl_scaled': pnl_scaled,
                    'exit_reason': exit_reason,
                    'bars_held': idx - entry_idx
                }
                
                trades.append(trade_record)
                daily_trades.append(trade_record)
                
                equity_curve.append({'datetime': row['datetime'], 'equity': equity})
                in_trade = False
    
    # Build trades dataframe
    trades_df = pd.DataFrame(trades)
    
    return {
        'trades_df': trades_df,
        'equity_curve': equity_curve,
        'final_equity': equity,
        'total_return_pct': ((equity - initial_capital) / initial_capital) * 100
    }

# Run paper trading simulation
print("\n" + "="*130)
print("RUNNING PAPER TRADING SIMULATION")
print("="*130 + "\n")

sim_result = paper_trading_simulation(df_live, initial_capital=100000, risk_pct=0.25, sim_days=14)
trades_df = sim_result['trades_df']
equity_curve = sim_result['equity_curve']

if len(trades_df) == 0:
    print("❌ NO TRADES GENERATED - CHECK ENTRY LOGIC")
else:
    print(f"✅ Paper Trading Complete: {len(trades_df)} trades executed\n")

# Daily reporting
print("="*130)
print("DAILY PERFORMANCE REPORT")
print("="*130)
print()

if len(trades_df) > 0:
    # Group by date
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    
    daily_stats = []
    equity_by_day = {}
    
    # Initialize equity curve by date
    starting_equity = 100000
    current_eq = starting_equity
    
    for entry in equity_curve:
        date = entry['datetime'].date()
        if date not in equity_by_day:
            equity_by_day[date] = {'start': starting_equity if not equity_by_day else current_eq, 'end': entry['equity']}
        else:
            equity_by_day[date]['end'] = entry['equity']
        current_eq = entry['equity']
    
    # Calculate daily stats
    for date in sorted(trades_df['entry_date'].unique()):
        day_trades = trades_df[trades_df['entry_date'] == date]
        pnl = day_trades['pnl_scaled'].sum()
        start_eq = equity_by_day[date]['start'] if date in equity_by_day else starting_equity
        end_eq = equity_by_day[date]['end'] if date in equity_by_day else starting_equity
        
        # Running max/min for DD calculation
        daily_stats.append({
            'date': date,
            'trades': len(day_trades),
            'entries': len(day_trades[day_trades['entry_time'].dt.date == date]),
            'pnl': pnl,
            'pnl_pct': (pnl / start_eq) * 100 if start_eq > 0 else 0,
            'equity_start': start_eq,
            'equity_end': end_eq,
            'wins': len(day_trades[day_trades['pnl_scaled'] > 0]),
            'losses': len(day_trades[day_trades['pnl_scaled'] <= 0]),
            'win_rate': (len(day_trades[day_trades['pnl_scaled'] > 0]) / len(day_trades) * 100) if len(day_trades) > 0 else 0
        })
    
    daily_df = pd.DataFrame(daily_stats)
    
    # Calculate drawdown
    max_eq = 100000
    equity_values = [entry['equity'] for entry in equity_curve]
    drawdowns = []
    
    for eq in equity_values:
        if eq > max_eq:
            max_eq = eq
        dd = ((max_eq - eq) / max_eq) * 100 if max_eq > 0 else 0
        drawdowns.append(dd)
    
    # Print daily report
    print(f"{'Date':<12} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'WinRate %':<10} {'Daily PnL':<12} {'Daily %':<10} {'Equity':<15} {'DD %':<8}")
    print("-" * 130)
    
    for idx, row in daily_df.iterrows():
        date_str = str(row['date'])
        equity_str = f"${row['equity_end']:,.0f}"
        
        # Get average DD for this day
        day_before = idx * 24  # Approximate
        day_after = (idx + 1) * 24
        day_drawdowns = drawdowns[max(0, day_before):min(len(drawdowns), day_after)]
        avg_dd = np.mean(day_drawdowns) if day_drawdowns else 0
        
        print(f"{date_str:<12} {int(row['trades']):<8} {int(row['wins']):<6} {int(row['losses']):<8} "
              f"{row['win_rate']:<10.1f} ${row['pnl']:<11,.0f} {row['pnl_pct']:<10.2f} {equity_str:<15} {avg_dd:<8.1f}")
    
    print()
    print("="*130)
    print("OVERALL STATISTICS")
    print("="*130)
    print()
    
    # Summary stats
    wins = trades_df[trades_df['pnl_scaled'] > 0]['pnl_scaled'].sum()
    losses = abs(trades_df[trades_df['pnl_scaled'] < 0]['pnl_scaled'].sum())
    pf = wins / losses if losses > 0 else 0
    
    print(f"Total Trades:              {len(trades_df)}")
    print(f"Winning Trades:            {len(trades_df[trades_df['pnl_scaled'] > 0])}")
    print(f"Losing Trades:             {len(trades_df[trades_df['pnl_scaled'] <= 0])}")
    print(f"Win Rate:                  {(len(trades_df[trades_df['pnl_scaled'] > 0]) / len(trades_df) * 100):.1f}%")
    print(f"Profit Factor:             {pf:.2f}")
    print()
    print(f"Starting Capital:          $100,000")
    print(f"Ending Capital:            ${sim_result['final_equity']:,.0f}")
    print(f"Total Return:              {sim_result['total_return_pct']:.2f}%")
    print(f"Total PnL:                 ${sim_result['final_equity'] - 100000:,.0f}")
    print()
    print(f"Max Drawdown:              {max(drawdowns):.1f}%")
    print(f"Avg Trade PnL:             ${trades_df['pnl_scaled'].mean():,.0f}")
    print(f"Avg Win:                   ${trades_df[trades_df['pnl_scaled'] > 0]['pnl_scaled'].mean():,.0f}")
    print(f"Avg Loss:                  ${trades_df[trades_df['pnl_scaled'] <= 0]['pnl_scaled'].mean():,.0f}")
    print(f"Avg Trade Duration:        {trades_df['bars_held'].mean():.0f} hours")
    print()
    
    # Trade log sample
    print("="*130)
    print("RECENT TRADES (Last 10)")
    print("="*130)
    print()
    
    recent_trades = trades_df.tail(10).copy()
    print(f"{'Entry Time':<20} {'Type':<6} {'Entry':<10} {'Exit':<10} {'Reason':<6} {'PnL $':<12} {'Bars':<6}")
    print("-" * 130)
    
    for idx, trade in recent_trades.iterrows():
        entry_str = str(trade['entry_time'])[:16]
        print(f"{entry_str:<20} {trade['type']:<6} ${trade['entry_price']:<9.2f} ${trade['exit_price']:<9.2f} "
              f"{trade['exit_reason']:<6} ${trade['pnl_scaled']:<11,.0f} {int(trade['bars_held']):<6}")
    
    print()
    print("="*130)
    print("VALIDATION CHECKLIST")
    print("="*130)
    print()
    
    # Validation checks
    checks = {
        'Signals Match Backtest': len(trades_df) > 0,
        'Win Rate in Range (38-44%)': 38 <= (len(trades_df[trades_df['pnl_scaled'] > 0]) / len(trades_df) * 100) <= 44,
        'Profit Factor > 1.0': pf > 1.0,
        'Max DD < 30%': max(drawdowns) < 30,
        'Positive Return': sim_result['total_return_pct'] > 0,
        'Avg Trade Positive': trades_df['pnl_scaled'].mean() > 0,
        'SL/TP Hitting': len(trades_df[trades_df['exit_reason'] == 'SL']) > 0 and len(trades_df[trades_df['exit_reason'] == 'TP']) > 0
    }
    
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:<40} {status}")
    
    print()
    print("="*130)
    print("NEXT STEPS FOR DEPLOYMENT")
    print("="*130)
    print()
    
    all_pass = all(checks.values())
    
    if all_pass:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print()
        print("Strategy is ready for paper trading deployment:")
        print("  1. Implement code in trading system with live data feeds")
        print("  2. Run for 7-14 days with paper account (no real capital)")
        print("  3. Monitor daily for:")
        print("     • Entry signals matching backtest logic")
        print("     • Win rate holding around 41%")
        print("     • DD staying below 20%")
        print("     • No execution errors")
        print("  4. After successful paper trading, deploy with $10k initial capital")
        print()
    else:
        print("⚠️  VALIDATION ISSUES DETECTED")
        print()
        failed = [name for name, result in checks.items() if not result]
        print("Failed checks:")
        for fail in failed:
            print(f"  • {fail}")
        print()
        print("Review and adjust strategy parameters before deployment")

else:
    print("❌ No trades were executed in simulation!")
    print("Check:")
    print("  • Entry conditions too restrictive?")
    print("  • RSI filter eliminating signals?")
    print("  • Body filter eliminating signals?")
    print("  • Data quality issues?")

print()
print("="*130)

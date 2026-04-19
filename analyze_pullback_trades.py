"""
ANALYZE PULLBACK TRADES - FIND FAILURE PATTERNS

Goal: Understand why some pullback entries fail vs succeed
Focus: Market conditions, indicator states, pattern recognition

Output: 
  - Win/loss trade examples
  - Pattern analysis
  - Market regime identification
  - Filter recommendations
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

def calculate_indicators(data):
    """Calculate all indicators"""
    # EMA 200
    data['ema_200'] = data['close'].ewm(span=200).mean()
    
    # ATR 14
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    data['atr'] = tr.rolling(window=14).mean()
    
    # RSI 14
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Volume MA 20
    data['vol_ma'] = data['volume'].rolling(window=20).mean()
    
    # Momentum MA 50
    data['mom_ma'] = data['close'].rolling(window=50).mean()
    
    # Trend strength (distance from EMA_200 as % of ATR)
    data['trend_strength'] = abs(data['close'] - data['ema_200']) / data['atr']
    
    return data

def run_trade_analysis(sl_mult=1.2, tp_mult=3.0):
    """Run full backtest tracking trade details"""
    
    print("\n" + "="*100)
    print(f"PULLBACK TRADE ANALYSIS: SL={sl_mult}x ATR, TP={tp_mult}x ATR")
    print("="*100)
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    data = data.reset_index()
    
    # Calculate indicators
    data = calculate_indicators(data)
    
    # Generate signals
    from pullback_signal_generator_v2 import ImprovedPullbackSignalGenerator
    gen = ImprovedPullbackSignalGenerator()
    signals_df = gen.generate_signals(data.set_index('timestamp'))
    
    data['signal'] = signals_df['signal'].values
    
    # Backtest with detailed tracking
    initial_capital = 100000
    position_size = 10000
    fee_pct = 0.001
    slippage_pct = 0.0003
    
    trades = []
    position = None
    
    for idx in range(len(data)):
        candle = data.iloc[idx]
        signal = candle['signal']
        
        if position is None and signal == 1:
            entry_price = candle['close']
            atr = candle['atr']
            
            if pd.isna(atr) or atr == 0:
                continue
            
            entry_fee = position_size * (fee_pct + slippage_pct)
            position = {
                'entry_idx': idx,
                'entry_time': candle['timestamp'],
                'entry_price': entry_price,
                'stop_loss': entry_price - (sl_mult * atr),
                'take_profit': entry_price + (tp_mult * atr),
                'entry_fee': entry_fee,
                'entry_atr': atr,
                'entry_rsi': candle['rsi'],
                'entry_trend_strength': candle['trend_strength'],
                'entry_volatility': atr,
                'entry_volume_ratio': candle['volume'] / candle['vol_ma'] if candle['vol_ma'] > 0 else 0,
                'ema_200': candle['ema_200'],
            }
        
        elif position is not None:
            current_price = candle['close']
            
            if current_price <= position['stop_loss']:
                exit_triggered = True
                exit_price = position['stop_loss']
                exit_type = 'SL'
            elif current_price >= position['take_profit']:
                exit_triggered = True
                exit_price = position['take_profit']
                exit_type = 'TP'
            else:
                exit_triggered = False
            
            if exit_triggered:
                exit_fee = position_size * (fee_pct + slippage_pct)
                gross_pnl = (exit_price - position['entry_price']) * (position_size / position['entry_price'])
                net_pnl = gross_pnl - position['entry_fee'] - exit_fee
                hold_candles = idx - position['entry_idx']
                
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': candle['timestamp'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'pnl': net_pnl,
                    'pnl_pct': (net_pnl / position_size * 100),
                    'winner': 1 if net_pnl > 0 else 0,
                    'hold_hours': hold_candles,
                    'entry_rsi': position['entry_rsi'],
                    'entry_trend_strength': position['entry_trend_strength'],
                    'entry_volatility': position['entry_volatility'],
                    'entry_volume_ratio': position['entry_volume_ratio'],
                }
                trades.append(trade)
                position = None
    
    trades_df = pd.DataFrame(trades)
    
    # Analysis
    winners = trades_df[trades_df['winner'] == 1]
    losers = trades_df[trades_df['winner'] == 0]
    
    print(f"\nOVERALL STATISTICS:")
    print(f"  Total Trades: {len(trades_df)}")
    print(f"  Winners: {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
    print(f"  Losers: {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")
    print(f"  Avg Win: ${winners['pnl'].mean():.2f} ({winners['pnl_pct'].mean():+.2f}%)" if len(winners) > 0 else "  No winners")
    print(f"  Avg Loss: ${losers['pnl'].mean():.2f} ({losers['pnl_pct'].mean():+.2f}%)" if len(losers) > 0 else "  No losers")
    
    # Filter analysis
    print(f"\nENTRY CONDITIONS - WINNERS vs LOSERS:")
    print(f"{'Metric':<30} {'Winners':<20} {'Losers':<20}")
    print("-" * 70)
    
    metrics = ['entry_rsi', 'entry_trend_strength', 'entry_volatility', 'entry_volume_ratio']
    for metric in metrics:
        if len(winners) > 0 and len(losers) > 0:
            w_mean = winners[metric].mean()
            l_mean = losers[metric].mean()
            print(f"{metric:<30} {w_mean:<20.3f} {l_mean:<20.3f}")
    
    # Hold time analysis
    print(f"\nHOLD TIME ANALYSIS:")
    print(f"  Winners avg hold: {winners['hold_hours'].mean():.1f} hours" if len(winners) > 0 else "  No winners")
    print(f"  Losers avg hold: {losers['hold_hours'].mean():.1f} hours" if len(losers) > 0 else "  No losers")
    
    # Exit type distribution
    print(f"\nEXIT DISTRIBUTION:")
    if len(trades_df) > 0:
        exit_types = trades_df['exit_type'].value_counts()
        for exit_type, count in exit_types.items():
            exit_pct = count / len(trades_df) * 100
            print(f"  {exit_type}: {count} trades ({exit_pct:.1f}%)")
    
    # Identify worst trades
    print(f"\nWORST 5 TRADES:")
    if len(losers) > 0:
        worst = losers.nsmallest(5, 'pnl')
        for idx, trade in worst.iterrows():
            print(f"  {trade['entry_time']}: ${trade['pnl']:.2f} ({trade['pnl_pct']:+.2f}%) | "
                  f"RSI={trade['entry_rsi']:.0f}, Trend={trade['entry_trend_strength']:.2f}, "
                  f"Vol={trade['entry_volume_ratio']:.2f}x")
    
    # Identify best trades
    print(f"\nBEST 5 TRADES:")
    if len(winners) > 0:
        best = winners.nlargest(5, 'pnl')
        for idx, trade in best.iterrows():
            print(f"  {trade['entry_time']}: ${trade['pnl']:.2f} ({trade['pnl_pct']:+.2f}%) | "
                  f"RSI={trade['entry_rsi']:.0f}, Trend={trade['entry_trend_strength']:.2f}, "
                  f"Vol={trade['entry_volume_ratio']:.2f}x")
    
    # Time of day analysis
    print(f"\nTIME OF DAY ANALYSIS (UTC Hour):")
    trades_df['hour'] = trades_df['entry_time'].dt.hour
    by_hour = trades_df.groupby('hour').agg({
        'winner': ['count', 'sum', lambda x: x.sum()/len(x)*100]
    }).round(1)
    by_hour.columns = ['Trades', 'Wins', 'WR%']
    print(by_hour[by_hour['Trades'] >= 3])  # Only show hours with 3+ trades
    
    # Day of week analysis
    print(f"\nDAY OF WEEK ANALYSIS:")
    trades_df['day'] = trades_df['entry_time'].dt.day_name()
    by_day = trades_df.groupby('day').agg({
        'winner': ['count', 'sum', lambda x: x.sum()/len(x)*100]
    }).round(1)
    by_day.columns = ['Trades', 'Wins', 'WR%']
    print(by_day)
    
    return trades_df

# Run analysis
trades = run_trade_analysis(sl_mult=1.2, tp_mult=3.0)

# Export for further analysis
trades.to_csv('pullback_trades_detailed.csv', index=False)
print(f"\n✓ Detailed trades exported to pullback_trades_detailed.csv")

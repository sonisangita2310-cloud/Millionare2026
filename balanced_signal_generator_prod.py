#!/usr/bin/env python3
"""
Production Balanced Signal Generator
Configuration: BALANCED (434 trades over 2 years = 18.1/month average)
Status: Ready for deployment
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from datetime import datetime

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    tr = np.maximum(
        np.maximum(data['high'] - data['low'], abs(data['high'] - data['close'].shift())),
        abs(data['low'] - data['close'].shift())
    )
    return tr.rolling(window=period).mean()

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class ProductionBalancedSignalGenerator:
    """
    Production-ready balanced signal generator
    
    CONFIGURATION:
    - Volatility threshold: 0.5% (ATR/price)
    - Breakout strength: 0.2×ATR minimum
    - Expected trades: 434 over 2 years (18.1/month)
    - Quality filters: 7 (original 5 + 2 relaxed quality filters)
    """
    
    def __init__(self):
        self.volatility_threshold = 0.5  # BALANCED config
        self.breakout_strength_multiplier = 0.2  # BALANCED config
        self.config_name = "BALANCED"
        self.expected_trades_2yr = 434
        self.expected_monthly = 18.1
    
    def generate_signals(self, data: pd.DataFrame, warmup: int = 200) -> pd.DataFrame:
        """
        Generate entry signals using balanced filter set
        """
        df = data.copy()
        
        # Calculate indicators
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ATR'] = calculate_atr(df, period=14)
        df['HIGHEST_20_PREV'] = df['high'].shift(1).rolling(window=20).max()
        df['LOWEST_20_PREV'] = df['low'].shift(1).rolling(window=20).min()
        df['VOLUME_MA_20'] = df['volume'].rolling(window=20).mean()
        df['RSI'] = calculate_rsi(df['close'], 14)
        df['RANGE'] = df['high'] - df['low']
        df['BODY'] = abs(df['close'] - df['open'])
        df['BODY_PCTS'] = (df['BODY'] / df['RANGE'].replace(0, 1)) * 100
        df['VOLATILITY_PCT'] = (df['ATR'] / df['close'].fillna(df['close'].mean())) * 100
        
        # Initialize signal columns
        df['SIGNAL'] = 0  # 0=none, 1=LONG, -1=SHORT
        df['STRENGTH'] = 0.0
        df['FILTER_REASON'] = ""
        
        # Apply filters for each candle
        for idx in range(warmup, len(df)):
            row = df.iloc[idx]
            
            # F1: BREAKOUT CHECK
            long_breakout = row['close'] > row['HIGHEST_20_PREV']
            short_breakout = row['close'] < row['LOWEST_20_PREV']
            if not (long_breakout or short_breakout):
                df.loc[idx, 'FILTER_REASON'] = 'F1-No-Breakout'
                continue
            
            # F2: VOLUME CONFIRMATION
            if not (row['volume'] > row['VOLUME_MA_20']):
                df.loc[idx, 'FILTER_REASON'] = 'F2-Low-Volume'
                continue
            
            # F3: TREND DIRECTION
            if long_breakout:
                trend_ok = row['close'] > row['EMA_200']
            else:
                trend_ok = row['close'] < row['EMA_200']
            
            if not trend_ok:
                df.loc[idx, 'FILTER_REASON'] = 'F3-Wrong-Trend'
                continue
            
            # F4: RSI EXTREMES
            if pd.notna(row['RSI']) and 30 <= row['RSI'] <= 70:
                df.loc[idx, 'FILTER_REASON'] = 'F4-RSI-Neutral'
                continue
            
            # F5: BODY QUALITY
            if pd.notna(row['BODY_PCTS']) and row['BODY_PCTS'] < 40:
                df.loc[idx, 'FILTER_REASON'] = 'F5-Weak-Body'
                continue
            
            # F6: VOLATILITY (BALANCED: 0.5%)
            if pd.notna(row['VOLATILITY_PCT']) and row['VOLATILITY_PCT'] < self.volatility_threshold:
                df.loc[idx, 'FILTER_REASON'] = 'F6-Low-Volatility'
                continue
            
            # F7: BREAKOUT STRENGTH (BALANCED: 0.2×ATR)
            atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
            if long_breakout:
                breakout_distance = row['close'] - row['HIGHEST_20_PREV']
            else:
                breakout_distance = row['LOWEST_20_PREV'] - row['close']
            
            if breakout_distance < (atr * self.breakout_strength_multiplier):
                df.loc[idx, 'FILTER_REASON'] = 'F7-Weak-Breakout'
                continue
            
            # ✓ SIGNAL PASSED
            signal_type = 1 if long_breakout else -1
            strength = self._calculate_strength(row, atr, breakout_distance, long_breakout)
            
            df.loc[idx, 'SIGNAL'] = signal_type
            df.loc[idx, 'STRENGTH'] = strength
            df.loc[idx, 'FILTER_REASON'] = 'PASS'
        
        return df
    
    def _calculate_strength(self, row, atr, breakout_distance, long_breakout) -> float:
        """Calculate signal confidence (0.0-1.0)"""
        strength = 0.5
        
        # Breakout strength
        if atr > 0:
            breakout_pct = breakout_distance / atr
            strength += min(0.2, breakout_pct * 0.05)
        
        # RSI extremeness
        if pd.notna(row['RSI']):
            rsi_dist = min(abs(row['RSI'] - 50) - 20, 20)
            strength += min(0.2, rsi_dist / 100)
        
        # Volume strength
        if row['VOLUME_MA_20'] > 0:
            vol_ratio = row['volume'] / row['VOLUME_MA_20']
            strength += min(0.1, (vol_ratio - 1.0) * 0.05)
        
        return min(1.0, strength)


# Test function
def test_balanced_generator():
    """Quick test of balanced generator"""
    print("Testing balanced signal generator...")
    from pathlib import Path
    from datetime import timedelta
    
    # Load data
    df = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # 2-year range
    end_date = pd.Timestamp("2026-04-17")
    start_date = end_date - timedelta(days=730)
    df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
    
    # Generate signals
    gen = ProductionBalancedSignalGenerator()
    signals_df = gen.generate_signals(df_2yr)
    
    signal_rows = signals_df[signals_df['SIGNAL'] != 0]
    print(f"  Total signals: {len(signal_rows)}")
    print(f"  Avg strength: {signal_rows['STRENGTH'].mean():.3f}")
    print(f"  Monthly avg: {len(signal_rows)/24:.1f}")
    
    return signals_df


if __name__ == '__main__':
    test_balanced_generator()

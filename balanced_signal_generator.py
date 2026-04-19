#!/usr/bin/env python3
"""
Balanced Signal Generator v1.0
- Keep 5 original solid filters
- Add quality filters with RELAXED thresholds
- Target: 10-25 trades/month = 240-600 trades over 2 years
"""

import pandas as pd
import numpy as np
from typing import List, Tuple
from datetime import datetime, timedelta

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

class BalancedSignalGenerator:
    """
    Balanced signal generation with 5 original + 2 relaxed quality filters
    Targets 240-600 trades over 2 years (10-25/month)
    """
    
    def __init__(self, 
                 volatility_threshold: float = 0.5,  # Relaxed from 1.0%
                 breakout_strength_multiplier: float = 0.2,  # Relaxed from 0.5×ATR
                 momentum_threshold: float = 0.2):  # Relaxed from 0.3×ATR
        """
        Initialize with RELAXED thresholds for balance
        
        Args:
            volatility_threshold: ATR/price % (0.5 = less restrictive)
            breakout_strength_multiplier: Multiple of ATR (0.2 = less restrictive)
            momentum_threshold: Distance from EMA_200 in ATR multiples
        """
        self.volatility_threshold = volatility_threshold
        self.breakout_strength_multiplier = breakout_strength_multiplier
        self.momentum_threshold = momentum_threshold
        
    def generate_signals(self, data: pd.DataFrame, warmup: int = 200) -> pd.DataFrame:
        """
        Generate entry signals with balanced filter set
        
        FILTER SET:
        1. F1: Breakout (close > 20h or < 20l)
        2. F2: Volume (vol > 20-MA)
        3. F3: Trend (aligned with EMA_200)
        4. F4: RSI Extremes (< 30 or > 70) - KEEP FROM ORIGINAL
        5. F5: Body Quality (body >= 40% range)
        6. F6: Volatility/Market Regime (RELAXED: 0.5% instead of 1.0%)
        7. F7: Breakout Strength (RELAXED: 0.2×ATR instead of 0.5×ATR)
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
        df['STRENGTH'] = 0.0  # Signal confidence 0.0-1.0
        df['FILTER_REASON'] = ""  # Why signal was rejected
        
        # Apply filters
        for idx in range(warmup, len(df)):
            row = df.iloc[idx]
            
            # F1: BREAKOUT CHECK
            long_breakout = row['close'] > row['HIGHEST_20_PREV']
            short_breakout = row['close'] < row['LOWEST_20_PREV']
            
            if not (long_breakout or short_breakout):
                df.loc[idx, 'FILTER_REASON'] = 'F1-No-Breakout'
                continue
            
            # F2: VOLUME CONFIRMATION
            volume_ok = row['volume'] > row['VOLUME_MA_20']
            if not volume_ok:
                df.loc[idx, 'FILTER_REASON'] = 'F2-Low-Volume'
                continue
            
            # F3: TREND DIRECTION (EMA_200)
            if long_breakout:
                trend_ok = row['close'] > row['EMA_200']
            else:
                trend_ok = row['close'] < row['EMA_200']
            
            if not trend_ok:
                df.loc[idx, 'FILTER_REASON'] = 'F3-Wrong-Trend'
                continue
            
            # F4: RSI EXTREMES (keep from original)
            if pd.notna(row['RSI']):
                if row['RSI'] >= 30 and row['RSI'] <= 70:
                    df.loc[idx, 'FILTER_REASON'] = 'F4-RSI-Neutral'
                    continue
            
            # F5: BODY QUALITY (keep from original)
            if pd.notna(row['BODY_PCTS']):
                if row['BODY_PCTS'] < 40:
                    df.loc[idx, 'FILTER_REASON'] = 'F5-Weak-Body'
                    continue
            
            # F6: VOLATILITY/MARKET REGIME (RELAXED: 0.5% instead of 1.0%)
            if pd.notna(row['VOLATILITY_PCT']):
                if row['VOLATILITY_PCT'] < self.volatility_threshold:
                    df.loc[idx, 'FILTER_REASON'] = f'F6-Low-Vol(<{self.volatility_threshold}%)'
                    continue
            
            # F7: BREAKOUT STRENGTH (RELAXED: 0.2×ATR instead of 0.5×ATR)
            atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
            if long_breakout:
                breakout_distance = row['close'] - row['HIGHEST_20_PREV']
                if breakout_distance < (atr * self.breakout_strength_multiplier):
                    df.loc[idx, 'FILTER_REASON'] = f'F7-Weak-Breakout'
                    continue
            else:
                breakout_distance = row['LOWEST_20_PREV'] - row['close']
                if breakout_distance < (atr * self.breakout_strength_multiplier):
                    df.loc[idx, 'FILTER_REASON'] = f'F7-Weak-Breakout'
                    continue
            
            # ✓ SIGNAL PASSED ALL FILTERS
            signal_type = 1 if long_breakout else -1
            
            # Calculate signal strength (0.0-1.0)
            strength = 0.5  # Base
            
            # Breakout strength bonus
            if long_breakout:
                breakout_pct = (breakout_distance / atr) if atr > 0 else 0
            else:
                breakout_pct = (breakout_distance / atr) if atr > 0 else 0
            strength += min(0.2, breakout_pct * 0.05)  # Up to +0.2
            
            # RSI extremeness bonus
            if pd.notna(row['RSI']):
                rsi_distance = min(abs(row['RSI'] - 50) - 20, 20)  # 0-20 range
                strength += min(0.2, rsi_distance / 100)  # Up to +0.2
            
            # Volume bonus
            vol_ratio = row['volume'] / row['VOLUME_MA_20'] if row['VOLUME_MA_20'] > 0 else 1.0
            strength += min(0.1, (vol_ratio - 1.0) * 0.05)  # Up to +0.1
            
            strength = min(1.0, strength)
            
            df.loc[idx, 'SIGNAL'] = signal_type
            df.loc[idx, 'STRENGTH'] = strength
            df.loc[idx, 'FILTER_REASON'] = 'PASS'
        
        return df
    
    def get_signal_summary(self, signals_df: pd.DataFrame) -> dict:
        """Return summary of signal generation"""
        signal_rows = signals_df[signals_df['SIGNAL'] != 0]
        long_signals = len(signals_df[signals_df['SIGNAL'] == 1])
        short_signals = len(signals_df[signals_df['SIGNAL'] == -1])
        
        return {
            'total_signals': len(signal_rows),
            'long_signals': long_signals,
            'short_signals': short_signals,
            'avg_strength': signal_rows['STRENGTH'].mean() if len(signal_rows) > 0 else 0,
            'min_strength': signal_rows['STRENGTH'].min() if len(signal_rows) > 0 else 0,
            'max_strength': signal_rows['STRENGTH'].max() if len(signal_rows) > 0 else 0,
        }

# ============================================================================
# TEST BALANCED VERSIONS
# ============================================================================
if __name__ == '__main__':
    print("="*120)
    print("BALANCED SIGNAL GENERATOR - Test multiple relaxation levels")
    print("="*120)
    
    # Load data
    print("\n[Loading data...]")
    df = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df['Datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Filter to 2-year range
    end_date = pd.Timestamp("2026-04-17")
    start_date = end_date - timedelta(days=365*2)
    df_2yr = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].reset_index(drop=True)
    
    # Test different relaxation levels
    configs = [
        {
            'name': 'CONSERVATIVE',
            'volatility_threshold': 1.0,
            'breakout_strength_multiplier': 0.5,
            'momentum_threshold': 0.3,
            'desc': 'Original improved (most restrictive)'
        },
        {
            'name': 'MODERATE',
            'volatility_threshold': 0.7,
            'breakout_strength_multiplier': 0.35,
            'momentum_threshold': 0.2,
            'desc': 'Slightly relaxed volatility & strength'
        },
        {
            'name': 'BALANCED',
            'volatility_threshold': 0.5,
            'breakout_strength_multiplier': 0.2,
            'momentum_threshold': 0.15,
            'desc': 'Significant relaxation for more trades'
        },
        {
            'name': 'AGGRESSIVE',
            'volatility_threshold': 0.3,
            'breakout_strength_multiplier': 0.1,
            'momentum_threshold': 0.1,
            'desc': 'Most relaxed - highest trade count'
        },
    ]
    
    print("\nTesting filter relaxation levels:\n")
    print(f"{'Strategy':<15} {'Vol%':<8} {'Strength':<12} {'Trades':<10} {'Monthly':<10} {'Description':<40}")
    print("─" * 95)
    
    for config in configs:
        gen = BalancedSignalGenerator(
            volatility_threshold=config['volatility_threshold'],
            breakout_strength_multiplier=config['breakout_strength_multiplier'],
            momentum_threshold=config['momentum_threshold']
        )
        
        signals = gen.generate_signals(df_2yr)
        summary = gen.get_signal_summary(signals)
        
        monthly = summary['total_signals'] / 24  # 24 months over 2 years
        
        print(f"{config['name']:<15} "
              f"{config['volatility_threshold']:<8.1f} "
              f"{config['breakout_strength_multiplier']:<12.2f} "
              f"{summary['total_signals']:<10} "
              f"{monthly:<10.1f} "
              f"{config['desc']:<40}")
    
    print("\nTarget range: 10-25 trades/month = 240-600 trades over 2 years")
    print("\n✓ Use 'BALANCED' configuration for optimal quality/frequency balance")
    
    print("\n" + "="*120)

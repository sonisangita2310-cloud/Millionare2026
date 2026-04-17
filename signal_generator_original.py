"""
Signal Generator - Generates entry signals based on validated strategy
No indicators added. All filters from final_filter_recommendation.py
"""

import pandas as pd
import numpy as np


class SignalGenerator:
    """Generate entry signals with validated filters"""
    
    def __init__(self, df):
        """
        Initialize with indicator data
        
        Args:
            df: DataFrame with all indicators pre-calculated
               Required columns: close, EMA_200, HIGHEST_20_PREV, LOWEST_20_PREV,
                               VOLUME_MA_20, volume, RSI, BODY_PCTS
        """
        self.df = df
    
    def check_entry_signal(self, idx):
        """
        Check if entry signal is valid at given index
        Returns: ('LONG', signal_strength) or ('SHORT', signal_strength) or (None, 0)
        
        ALL FILTERS MUST PASS:
        1. Breakout: Close > 20-candle high (LONG) or < low (SHORT)
        2. Volume: Volume > 20-period MA
        3. Trend: Close > EMA_200 (LONG) or < EMA_200 (SHORT)
        4. RSI Filter: RSI < 30 OR RSI > 70 (skip if 30-70)
        5. Body Quality: Candle body ≥ 40% of range
        """
        
        if idx < 0 or idx >= len(self.df):
            return None, 0
        
        row = self.df.iloc[idx]
        
        # Skip if missing data
        if pd.isna(row['close']) or pd.isna(row['EMA_200']):
            return None, 0
        
        # Entry condition 1: Breakout logic
        long_breakout = row['close'] > row['HIGHEST_20_PREV']
        short_breakout = row['close'] < row['LOWEST_20_PREV']
        
        if not (long_breakout or short_breakout):
            return None, 0  # No breakout
        
        # Entry condition 2: Volume confirmation
        volume_ok = row['volume'] > row['VOLUME_MA_20']
        if not volume_ok:
            return None, 0  # Insufficient volume
        
        # Entry condition 3: Trend direction (EMA_200 filter)
        if long_breakout:
            trend_ok = row['close'] > row['EMA_200']
            signal_type = 'LONG'
        else:  # short_breakout
            trend_ok = row['close'] < row['EMA_200']
            signal_type = 'SHORT'
        
        if not trend_ok:
            return None, 0  # Wrong trend direction
        
        # Entry condition 4: RSI extremes filter (skip if 30-70)
        if pd.notna(row['RSI']):
            if row['RSI'] >= 30 and row['RSI'] <= 70:
                return None, 0  # RSI too neutral, skip trade
        
        # Entry condition 5: Candle body quality
        if pd.notna(row['BODY_PCTS']):
            if row['BODY_PCTS'] < 40:
                return None, 0  # Candle body too small
        
        # All filters passed - entry signal valid
        # Signal strength = how extreme RSI is (0.0 to 1.0)
        rsi = row['RSI']
        if rsi < 30:
            signal_strength = (30 - rsi) / 30  # 0 to 1
        elif rsi > 70:
            signal_strength = (rsi - 70) / 30  # 0 to 1
        else:
            signal_strength = 0
        
        return signal_type, signal_strength
    
    def get_entry_details(self, idx, signal_type):
        """Get entry details (price, RSI, ATR) for logging"""
        
        if idx < 0 or idx >= len(self.df):
            return None
        
        row = self.df.iloc[idx]
        
        return {
            'timestamp': row['datetime'],
            'price': row['close'],
            'rsi': row['RSI'],
            'body_pct': row['BODY_PCTS'],
            'atr': row['ATR'],
            'volume': row['volume']
        }

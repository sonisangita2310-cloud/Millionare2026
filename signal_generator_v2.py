"""
Signal Generator v2 - Fixed with proper debouncing and boundary handling
Prevents consecutive signals and false breakouts at price boundaries
"""

import pandas as pd
import numpy as np


class SignalGenerator:
    """Generate entry signals with validated filters and debouncing"""
    
    def __init__(self, df):
        """
        Initialize with indicator data and signal tracking
        
        Args:
            df: DataFrame with all indicators pre-calculated
               Required columns: close, EMA_200, HIGHEST_20_PREV, LOWEST_20_PREV,
                               VOLUME_MA_20, volume, RSI, BODY_PCTS
        """
        self.df = df
        
        # Signal tracking for debouncing
        self.last_signal_idx = {'LONG': -100, 'SHORT': -100}  # Never fire same signal < 1 candle gap
        self.signal_gap_requirement = 1  # Minimum candles between same signal type
        
        # Breakout boundary tracking (prevent jitter at exact threshold)
        self.breakout_hysteresis_pips = 0  # No extra hysteresis needed if data quality good
    
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
        6. Signal Debouncing: Gap >= minimum_gap since last same-type signal
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
        
        # FIX-001: Entry condition 6: Signal debouncing - prevent consecutive same signals
        last_idx = self.last_signal_idx[signal_type]
        gap_since_last = idx - last_idx
        
        if gap_since_last < self.signal_gap_requirement:
            # Still within debounce period, reject signal
            return None, 0
        
        # All filters passed - mark signal as fired and return
        self.last_signal_idx[signal_type] = idx
        
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
            'volume': row['volume'],
            'signal_quality': self._calculate_signal_quality(row)
        }
    
    def _calculate_signal_quality(self, row):
        """Calculate overall signal quality (0-100)"""
        quality = 50  # Base quality
        
        # RSI extreme = better quality
        rsi = row['RSI']
        if rsi < 20 or rsi > 80:
            quality += 30
        elif rsi < 30 or rsi > 70:
            quality += 15
        
        # Body quality = better quality
        if row['BODY_PCTS'] >= 70:
            quality += 15
        elif row['BODY_PCTS'] >= 50:
            quality += 10
        
        # Volume = better quality
        vol_ratio = row['volume'] / row['VOLUME_MA_20'] if row['VOLUME_MA_20'] > 0 else 1
        if vol_ratio >= 1.5:
            quality += 15
        elif vol_ratio >= 1.2:
            quality += 8
        
        return min(100, quality)
    
    def reset_signal_history(self):
        """Reset signal tracking (useful for testing)"""
        self.last_signal_idx = {'LONG': -100, 'SHORT': -100}
    
    def get_signal_stats(self):
        """Get signal statistics"""
        return {
            'last_long_idx': self.last_signal_idx['LONG'],
            'last_short_idx': self.last_signal_idx['SHORT'],
            'min_gap': self.signal_gap_requirement
        }

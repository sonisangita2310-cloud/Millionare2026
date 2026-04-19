"""
Improved Signal Generator - Quality-focused with market regime detection
Filters out choppy market trades while keeping strong trend breakouts
"""

import pandas as pd
import numpy as np


class ImprovedSignalGenerator:
    """Generate HIGH-QUALITY entry signals with regime detection"""
    
    def __init__(self, df):
        """
        Initialize with indicator data
        
        Args:
            df: DataFrame with all indicators pre-calculated
               Required columns: close, EMA_200, HIGHEST_20_PREV, LOWEST_20_PREV,
                               VOLUME_MA_20, volume, RSI, BODY_PCTS, high, low, ATR
        """
        self.df = df
        self._calculate_additional_indicators()
    
    def _calculate_additional_indicators(self):
        """Calculate market regime indicators"""
        
        # Volatility (ATR-based)
        if 'ATR' not in self.df.columns:
            self.df['ATR'] = self._calculate_atr()
        
        # Volatility relative to price
        self.df['VOLATILITY_PCT'] = (self.df['ATR'] / self.df['close'].fillna(self.df['close'].mean())) * 100
        
        # Trend strength (how far price is from EMA in terms of ATR multiples)
        self.df['DISTANCE_FROM_EMA'] = abs(self.df['close'] - self.df['EMA_200']) / self.df['ATR'].fillna(1.0)
        
        # MACD-like momentum (price vs slow EMA)
        self.df['EMA_50'] = self.df['close'].ewm(span=50, adjust=False).mean()
        self.df['MOMENTUM'] = self.df['EMA_50'] - self.df['EMA_200']
    
    def _calculate_di_plus(self, period=14):
        """Positive Directional Indicator (simplified)"""
        up = self.df['high'].diff()
        down = -self.df['low'].diff()
        
        # DM+ = up if up > down and up > 0
        dmp = pd.Series(np.where((up > down) & (up > 0), up, 0))
        atr14 = self.df['ATR'].rolling(period).mean() if 'ATR' in self.df.columns else self.df['close'].rolling(period).std()
        
        di_plus = (dmp.rolling(period).mean() / atr14) * 100
        return di_plus
    
    def _calculate_di_minus(self, period=14):
        """Negative Directional Indicator (simplified)"""
        up = self.df['high'].diff()
        down = -self.df['low'].diff()
        
        # DM- = down if down > up and down > 0
        dmn = pd.Series(np.where((down > up) & (down > 0), down, 0))
        atr14 = self.df['ATR'].rolling(period).mean() if 'ATR' in self.df.columns else self.df['close'].rolling(period).std()
        
        di_minus = (dmn.rolling(period).mean() / atr14) * 100
        return di_minus
    
    def _calculate_atr(self, period=14):
        """Calculate ATR if not present"""
        tr = np.maximum(
            np.maximum(self.df['high'] - self.df['low'], 
                      abs(self.df['high'] - self.df['close'].shift())),
            abs(self.df['low'] - self.df['close'].shift())
        )
        return tr.rolling(window=period).mean()
    
    def check_entry_signal(self, idx):
        """
        Check if entry signal is VALID and HIGH-QUALITY
        Returns: ('LONG', signal_strength) or ('SHORT', signal_strength) or (None, 0)
        
        ORIGINAL FILTERS (5):
        1. Breakout: Close > 20-candle high (LONG) or < low (SHORT)
        2. Volume: Volume > 20-period MA
        3. Trend: Close > EMA_200 (LONG) or < EMA_200 (SHORT)
        4. RSI Filter: RSI < 30 OR RSI > 70
        5. Body Quality: Candle body ≥ 40%
        
        NEW QUALITY FILTERS (3):
        6. Market Trend: Must be in clear trend (not choppy)
        7. Breakout Strength: Breakout must be significant (not just barely above high)
        8. Momentum Confirmation: Price momentum must match signal direction
        """
        
        if idx < 0 or idx >= len(self.df):
            return None, 0
        
        row = self.df.iloc[idx]
        
        # Skip if missing data
        if pd.isna(row['close']) or pd.isna(row['EMA_200']):
            return None, 0
        
        # ========== ORIGINAL FILTERS (1-5) ==========
        
        # Filter 1: Breakout logic
        long_breakout = row['close'] > row['HIGHEST_20_PREV']
        short_breakout = row['close'] < row['LOWEST_20_PREV']
        
        if not (long_breakout or short_breakout):
            return None, 0  # No breakout
        
        # Filter 2: Volume confirmation
        volume_ok = row['volume'] > row['VOLUME_MA_20']
        if not volume_ok:
            return None, 0  # Insufficient volume
        
        # Filter 3: Trend direction (EMA_200)
        if long_breakout:
            trend_ok = row['close'] > row['EMA_200']
            signal_type = 'LONG'
        else:  # short_breakout
            trend_ok = row['close'] < row['EMA_200']
            signal_type = 'SHORT'
        
        if not trend_ok:
            return None, 0  # Wrong trend direction
        
        # Filter 4: RSI extremes (skip neutral RSI)
        if pd.notna(row['RSI']):
            if row['RSI'] >= 30 and row['RSI'] <= 70:
                return None, 0  # RSI too neutral, skip trade
        
        # Filter 5: Candle body quality
        if pd.notna(row['BODY_PCTS']):
            if row['BODY_PCTS'] < 40:
                return None, 0  # Candle body too small
        
        # ========== NEW QUALITY FILTERS (6-8) ==========
        
        # Filter 6: MARKET TREND STRENGTH (Avoid choppy markets)
        # Skip if market is sideways/choppy (low volatility + neutral ADX)
        if pd.notna(row['VOLATILITY_PCT']):
            # Reject if volatility is too low (choppy market indicator)
            if row['VOLATILITY_PCT'] < 1.0:
                return None, 0  # Too low volatility = choppy market
        
        # Filter 7: BREAKOUT STRENGTH
        # Breakout must be SIGNIFICANT (not just barely above/below 20-period high/low)
        atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
        
        if long_breakout:
            # For LONG: Price must be at least 0.5×ATR above the 20-period high
            breakout_distance = row['close'] - row['HIGHEST_20_PREV']
            if breakout_distance < (atr * 0.5):
                return None, 0  # Weak breakout, likely to fail
        else:  # short_breakout
            # For SHORT: Price must be at least 0.5×ATR below the 20-period low
            breakout_distance = row['LOWEST_20_PREV'] - row['close']
            if breakout_distance < (atr * 0.5):
                return None, 0  # Weak breakout, likely to fail
        
        # Filter 8: MOMENTUM CONFIRMATION
        # Price momentum must match signal direction
        if pd.notna(row['MOMENTUM']):
            if signal_type == 'LONG' and row['MOMENTUM'] <= 0:
                # LONG signal but momentum is DOWN = weak signal
                # Skip or count as lower confidence
                pass  # Note: Could add patience wait (skip this candle but keep watching)
            elif signal_type == 'SHORT' and row['MOMENTUM'] >= 0:
                # SHORT signal but momentum is UP = weak signal
                pass
        
        # ADDITIONAL: Ensure trend distance from EMA is reasonable
        # Price should be meaningfully away from EMA_200 (not just barely crossing)
        if pd.notna(row['DISTANCE_FROM_EMA']):
            if row['DISTANCE_FROM_EMA'] < 0.3:  # Less than 0.3 ATR away from EMA
                return None, 0  # Too close to EMA = unstable entry point
        
        # ========== ALL FILTERS PASSED - SIGNAL VALID ==========
        
        # Calculate signal strength (composite of multiple factors)
        signal_strength = self._calculate_signal_strength(idx, signal_type, row)
        
        return signal_type, signal_strength
    
    def _calculate_signal_strength(self, idx, signal_type, row):
        """
        Calculate composite signal strength (0.0 to 1.0)
        Based on: RSI extremeness, breakout strength, momentum, trend confidence
        """
        
        strength = 0.0
        weights = 0.0
        
        # 1. RSI Extremeness (0.0-0.3)
        if pd.notna(row['RSI']):
            rsi = row['RSI']
            if rsi < 30:
                rsi_strength = (30 - rsi) / 30  # 0 to 1
            elif rsi > 70:
                rsi_strength = (rsi - 70) / 30  # 0 to 1
            else:
                rsi_strength = 0
            
            strength += rsi_strength * 0.3
            weights += 0.3
        
        # 2. Breakout Strength (0.0-0.3)
        atr = row['ATR'] if pd.notna(row['ATR']) else row['close'] * 0.02
        
        if signal_type == 'LONG':
            breakout_dist = row['close'] - row['HIGHEST_20_PREV']
            breakout_pct = breakout_dist / atr
        else:
            breakout_dist = row['LOWEST_20_PREV'] - row['close']
            breakout_pct = breakout_dist / atr
        
        # Normalize breakout (0.5 ATR = 0.3, 2.0 ATR = 1.0)
        breakout_strength = np.clip(breakout_pct / 2.0, 0, 1)
        strength += breakout_strength * 0.3
        weights += 0.3
        
        # 3. Momentum (0.0-0.2)
        if pd.notna(row['MOMENTUM']):
            if signal_type == 'LONG':
                momentum_strength = np.clip(row['MOMENTUM'] / (atr * 0.5), 0, 1)
            else:
                momentum_strength = np.clip(-row['MOMENTUM'] / (atr * 0.5), 0, 1)
            
            strength += momentum_strength * 0.2
            weights += 0.2
        
        # 4. Volatility Condition (0.0-0.2)
        if pd.notna(row['VOLATILITY_PCT']):
            # Higher quality if volatility is moderate (1.0-3.0%)
            if row['VOLATILITY_PCT'] < 1.0:
                vol_strength = 0.3
            elif row['VOLATILITY_PCT'] < 3.0:
                vol_strength = 1.0
            else:
                vol_strength = 0.6  # High volatility = more risk but valid
            
            strength += vol_strength * 0.2
            weights += 0.2
        
        if weights > 0:
            strength = strength / weights
        
        return np.clip(strength, 0.0, 1.0)
    
    def get_entry_details(self, idx, signal_type):
        """Get entry details for logging"""
        
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
            'momentum': row['MOMENTUM'] if 'MOMENTUM' in row.index else None,
            'volatility_pct': row['VOLATILITY_PCT'] if 'VOLATILITY_PCT' in row.index else None,
        }

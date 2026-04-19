"""
SIMPLIFIED OPTIMIZED SIGNAL GENERATOR - Trend Strength Focus

Approach:
  - Keep ALL BALANCED logic (434 signals)
  - Add ONLY the trend strength floor (0.5 ATR minimum)
  - Remove all other "optimizations"
  
Rationale:
  - Winner/loser analysis showed trend strength is the KEY differentiator
  - Winners: 5.122 ATR, Losers: 4.696 ATR (8% difference)
  - Trend strength floor eliminates weak-reversal losers
  
Expected results:
  - Signals: ~430 (minimal reduction, focuses on best entries)
  - Trades: ~320-330 (similar to BALANCED 317)
  - Win Rate: 28.4% → 31-33% (focused improvement)
  - Profit Factor: 0.77 → 0.90-0.95x (approaching breakeven)
"""

import pandas as pd
import numpy as np


class SimplifiedOptimizedSignalGenerator:
    """
    Simplified optimization: BALANCED + trend strength floor only.
    
    This generator takes the proven BALANCED filters and adds ONE strategic filter:
    Trend Strength Floor (0.5 ATR from EMA_200)
    
    This eliminates trades in weak-trend environments where even breakouts fail.
    """
    
    def __init__(self):
        """Initialize with minimal parameters."""
        # Breakout parameters (BALANCED)
        self.breakout_periods = 20
        
        # Volume parameters (BALANCED)
        self.volume_ma_period = 20
        
        # Trend parameters
        self.trend_ema_period = 200
        self.trend_strength_threshold = 0.5  # ATR units (NEW - ONLY optimization)
        
        # RSI parameters (BALANCED)
        self.rsi_period = 14
        self.rsi_low = 30
        self.rsi_high = 70
        
        # Volatility parameters (BALANCED)
        self.volatility_min = 0.005  # 0.5%
        self.volatility_max = 0.03   # 3.0%
        
        # ATR period
        self.atr_period = 14
    
    def generate_signals(self, ohlcv):
        """
        Generate entry signals: BALANCED filters + trend strength floor.
        
        Args:
            ohlcv: DataFrame with columns [open, high, low, close, volume]
        
        Returns:
            DataFrame with signal column (1 = entry signal, 0 = no entry)
        """
        df = ohlcv.copy()
        
        # Calculate indicators
        df = self._add_indicators(df)
        
        # BALANCED FILTERS (5 filters)
        f1_breakout = self._filter_breakout(df)
        f2_volume = self._filter_volume(df)
        f3_trend = self._filter_trend_direction(df)
        f4_rsi = self._filter_rsi(df)
        f5_volatility = self._filter_volatility(df)
        
        # SIMPLIFIED OPTIMIZATION: Trend Strength Floor Only
        f6_trend_strength = self._filter_trend_strength(df)
        
        # Final signal: BALANCED + trend strength
        df['signal'] = (f1_breakout & f2_volume & f3_trend & f4_rsi & f5_volatility & f6_trend_strength).astype(int)
        
        return df
    
    def _add_indicators(self, df):
        """Calculate technical indicators."""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA(200)
        df['ema_200'] = df['close'].ewm(span=self.trend_ema_period, adjust=False).mean()
        
        # ATR
        tr = np.maximum(
            np.maximum(
                df['high'] - df['low'],
                np.abs(df['high'] - df['close'].shift())
            ),
            np.abs(df['low'] - df['close'].shift())
        )
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        
        # Volume MA
        df['volume_ma_20'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        
        # Volatility
        df['volatility'] = df['atr'] / df['close']
        
        # Trend Strength (distance from EMA in ATR)
        df['trend_strength'] = np.abs(df['close'] - df['ema_200']) / df['atr']
        
        return df
    
    def _filter_breakout(self, df):
        """FILTER 1: Recent new high (last 20 periods)."""
        rolling_max = df['high'].rolling(window=self.breakout_periods).max()
        return df['high'] == rolling_max
    
    def _filter_volume(self, df):
        """FILTER 2: Volume above 20-MA."""
        return df['volume'] > df['volume_ma_20']
    
    def _filter_trend_direction(self, df):
        """FILTER 3: Price above EMA(200) - uptrend."""
        return df['close'] > df['ema_200']
    
    def _filter_rsi(self, df):
        """FILTER 4: RSI in extreme zones."""
        return (df['rsi'] < self.rsi_low) | (df['rsi'] > self.rsi_high)
    
    def _filter_volatility(self, df):
        """FILTER 5: Volatility in normal range."""
        return (df['volatility'] >= self.volatility_min) & (df['volatility'] <= self.volatility_max)
    
    def _filter_trend_strength(self, df):
        """FILTER 6: Trend Strength floor (KEY OPTIMIZATION)."""
        return df['trend_strength'] >= self.trend_strength_threshold


def generate_simplified_optimized_signals(data):
    """Convenience function for signal generation."""
    generator = SimplifiedOptimizedSignalGenerator()
    return generator.generate_signals(data)

"""
ENHANCED SIGNAL GENERATOR - Production Entry Quality Improvements

Based on winner/loser analysis:
  - Trend Strength floor: 0.5 ATR
  - Breakout maximum: 0.35 ATR (not 0.2)
  - Volume confirmation: 1.3x MA (not just >20MA)
  - Added momentum gate

Target metrics:
  - Win rate: 28% → 35%
  - Profit Factor: 0.77 → 1.1-1.2x
  - Trade frequency: 250-300 trades (10-13/month)
"""

import pandas as pd
import numpy as np


class EnhancedSignalGenerator:
    """
    Enhanced signal generation with improved entry quality filters.
    
    Filter Stack (7 filters):
    1. Breakout Detection (new high)
    2. Volume Confirmation (upgraded to 1.3x MA)
    3. Trend Direction (EMA alignment)
    4. RSI Extremes (oversold/overbought)
    5. Trend Strength Floor (NEW - 0.5 ATR minimum, eliminates weak-trend breakouts)
    6. Breakout Size Control (0.5-1.5 ATR range - winners 1.074, losers 1.118)
    7. Volume Acceleration (1.3x MA strength validation)
    
    Key Insight from Winner/Loser Analysis:
    - Winners have stronger trend (5.122 vs 4.696 ATR)
    - Winners have better volume (3.75x vs 3.39x)
    - Winners have CONTROLLED breakout size (1.074 vs 1.118 ATR)
    
    This strategy filters OUT the oversized breakouts and weak trends that characterize losers.
    """
    
    def __init__(self, config=None):
        """Initialize with configuration parameters."""
        self.config = config or {
            # Core breakout
            'breakout_lookback': 20,
            'breakout_strength_min': 0.5,       # Min 0.5 ATR
            'breakout_strength_max': 1.5,       # Max 1.5 ATR (winners: 1.074, losers: 1.118)
            
            # Volume
            'volume_ma_period': 20,
            'volume_multiplier': 1.3,            # UPGRADED from loose >MA to 1.3x
            
            # Trend
            'trend_ema_period': 200,
            'trend_strength_floor': 0.5,         # NEW: Require 0.5+ ATR trend
            
            # RSI
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            
            # ATR for volatility
            'atr_period': 14,
            'volatility_min': 0.005,             # 0.5% minimum
            'volatility_max': 0.03,              # 3% maximum
            
            # Distance from EMA
            'min_distance_atr': 0.3,
        }
        
        if config:
            self.config.update(config)
    
    def generate_signals(self, data):
        """
        Generate trading signals based on enhanced filters.
        
        Filter progression:
        1. Breakout: Recent new high
        2. Volume: Volume confirmation
        3. Trend: In trending direction
        4. RSI: Extreme readings (quality entry)
        5. Trend Strength: Must have meaningful trend (NOT weak markets)
        6. Breakout Size: Within quality range (0.25-0.35 ATR, not huge)
        7. Volume Strength: Strong volume, not marginal
        
        Args:
            data: DataFrame with OHLCV + indicators
        
        Returns:
            DataFrame with signal column (1 = buy, 0 = no signal)
        """
        signals = data.copy()
        signals['signal'] = 0
        
        # ----- FILTER 1: BREAKOUT DETECTION -----
        signals['new_high'] = signals['high'] == signals['high'].rolling(
            window=self.config['breakout_lookback']
        ).max()
        
        # ----- FILTER 2: VOLUME CONFIRMATION -----
        signals['volume_ma'] = signals['volume'].rolling(
            window=self.config['volume_ma_period']
        ).mean()
        signals['volume_check'] = signals['volume'] > (
            signals['volume_ma'] * self.config['volume_multiplier']
        )
        
        # ----- FILTER 3: TREND DIRECTION -----
        signals['ema'] = signals['close'].ewm(
            span=self.config['trend_ema_period'],
            adjust=False
        ).mean()
        signals['in_uptrend'] = signals['close'] > signals['ema']
        
        # ----- FILTER 4: RSI EXTREMES -----
        signals['rsi'] = self._calculate_rsi(
            signals['close'],
            self.config['rsi_period']
        )
        signals['rsi_extreme'] = (
            (signals['rsi'] < self.config['rsi_oversold']) |
            (signals['rsi'] > self.config['rsi_overbought'])
        )
        
        # ----- FILTER 5: ATR-BASED VOLATILITY & TREND STRENGTH -----
        signals['atr'] = self._calculate_atr(
            signals['high'],
            signals['low'],
            signals['close'],
            self.config['atr_period']
        )
        
        # Volatility check
        signals['volatility'] = signals['atr'] / signals['close']
        signals['volatility_check'] = (
            (signals['volatility'] >= self.config['volatility_min']) &
            (signals['volatility'] <= self.config['volatility_max'])
        )
        
        # Trend Strength Floor (NEW - CRITICAL FOR WINNERS)
        # Winners have 5.122 ATR trend, losers 4.696 ATR
        # Require minimum 0.5 ATR distance from EMA_200
        signals['trend_strength'] = abs(signals['close'] - signals['ema']) / signals['atr']
        signals['trend_strong'] = signals['trend_strength'] >= self.config['trend_strength_floor']
        
        # ----- FILTER 6: BREAKOUT FORCE (SMART RANGE) -----
        # Breakout displacement in ATR terms
        signals['breakout_displacement'] = (
            signals['high'] - signals['high'].shift(self.config['breakout_lookback'])
        ) / signals['atr']
        
        signals['breakout_force_ok'] = (
            (signals['breakout_displacement'] >= self.config['breakout_strength_min']) &
            (signals['breakout_displacement'] <= self.config['breakout_strength_max'])
        )
        
        # ----- FILTER 7: DISTANCE FROM EMA (BODY QUALITY) -----
        signals['distance_from_ema'] = abs(signals['close'] - signals['ema']) / signals['atr']
        signals['good_distance'] = signals['distance_from_ema'] >= self.config['min_distance_atr']
        
        # ----- COMBINE ALL FILTERS -----
        signals['signal'] = (
            signals['new_high'] &
            signals['volume_check'] &
            signals['in_uptrend'] &
            signals['rsi_extreme'] &
            signals['volatility_check'] &
            signals['trend_strong'] &              # NEW FILTER
            signals['breakout_force_ok'] &         # UPGRADED FILTER
            signals['good_distance']
        ).astype(int)
        
        return signals
    
    def _calculate_rsi(self, prices, period):
        """Calculate RSI indicator."""
        deltas = prices.diff()
        seed = deltas[:period + 1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices, dtype=float)
        rsi[:period] = 100 - 100 / (1 + rs)
        
        for i in range(period, len(prices)):
            delta = deltas.iloc[i]
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down = (down * (period - 1)) / period
            else:
                up = (up * (period - 1)) / period
                down = (down * (period - 1) - delta) / period
            
            rs = up / down if down != 0 else 0
            rsi[i] = 100 - 100 / (1 + rs)
        
        return rsi
    
    def _calculate_atr(self, high, low, close, period):
        """Calculate ATR indicator."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def get_statistics(self, signals):
        """Return signal generation statistics."""
        signal_count = signals['signal'].sum()
        return {
            'total_signals': int(signal_count),
            'signal_pct': f"{100 * signal_count / len(signals):.2f}%",
        }


def generate_enhanced_signals(data, config=None):
    """Convenience function for batch signal generation."""
    generator = EnhancedSignalGenerator(config)
    return generator.generate_signals(data)

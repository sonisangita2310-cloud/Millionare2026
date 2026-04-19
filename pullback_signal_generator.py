"""
PULLBACK STRATEGY - New Entry Edge Design

Architecture:
  Step 1: Trend Identification (EMA 200)
  Step 2: Pullback Detection (price retraces toward EMA)
  Step 3: Momentum Confirmation (RSI + MA divergence)
  Step 4: Entry Signal (continuation + volume)
  Step 5: Exit (fixed ATR SL/TP)

Key Premise:
  - Breakout strategy: enters on highs (exhaustion often follows)
  - Pullback strategy: enters on retracements (higher conviction reversals)
  - Expected edge: Better risk/reward, fewer false breakouts
  
Target Metrics:
  - PF > 1.2x (vs breakout 0.77x)
  - Win rate 35%+ (vs breakout 28%)
  - Trades: 200-300 over 2 years (vs breakout 317)
"""

import pandas as pd
import numpy as np


class PullbackSignalGenerator:
    """
    Pullback-based entry signal generation with momentum confirmation.
    
    Methodology:
    1. Identify uptrend: Price > EMA(200)
    2. Detect pullback: Price pulls within X% of EMA (healthy retracement)
    3. Confirm momentum: RSI recovery + volume
    4. Generate signal on: Pullback completion + bullish confirmation
    
    Advantages over breakout:
    - Enters after confirmation, not on initial break
    - Lower false signal rate (price tested support)
    - Better risk management (SL below pullback)
    """
    
    def __init__(self):
        """Initialize strategy parameters."""
        # Trend identification
        self.trend_ema = 200
        
        # Pullback detection (look for price retracement toward EMA)
        self.pullback_atr_min = 0.3   # Minimum 0.3 ATR from EMA (meaningful move)
        self.pullback_atr_max = 1.2   # Maximum 1.2 ATR from EMA (not oversold)
        
        # Momentum confirmation
        self.rsi_period = 14
        self.rsi_recovery = 35        # RSI should be recovering (not still oversold)
        self.momentum_ma = 50         # MA for momentum calculation
        
        # Volume confirmation
        self.volume_ma = 20
        self.volume_min = 1.0         # Volume should be >= 1x MA
        
        # Volatility filter
        self.atr_period = 14
        self.volatility_min = 0.005   # 0.5% minimum
        self.volatility_max = 0.03    # 3% maximum
        
        # Pullback tracking (lookback for pullback detection)
        self.swing_lookback = 30      # How far back to look for swing high
    
    def generate_signals(self, ohlcv):
        """
        Generate pullback entry signals.
        
        Args:
            ohlcv: DataFrame with [open, high, low, close, volume]
        
        Returns:
            DataFrame with signal column (1 = pullback entry signal)
        """
        df = ohlcv.copy()
        
        # Calculate indicators
        df = self._calculate_indicators(df)
        
        # Step 1: Trend identification
        in_uptrend = df['close'] > df['ema_200']
        
        # Step 2: Pullback detection
        in_pullback = self._detect_pullback(df)
        
        # Step 3: Momentum confirmation
        momentum_confirm = self._confirm_momentum(df)
        
        # Step 4: Volume confirmation
        volume_confirm = df['volume'] > df['volume_ma']
        
        # Step 5: Volatility filter (avoid extremes)
        vol_ok = (df['volatility'] >= self.volatility_min) & (df['volatility'] <= self.volatility_max)
        
        # Combine all filters
        df['signal'] = (in_uptrend & in_pullback & momentum_confirm & volume_confirm & vol_ok).astype(int)
        
        return df
    
    def _calculate_indicators(self, df):
        """Calculate all required technical indicators."""
        
        # EMA 200 (trend)
        df['ema_200'] = df['close'].ewm(span=self.trend_ema, adjust=False).mean()
        
        # ATR (volatility and exit sizing)
        tr = np.maximum(
            np.maximum(df['high'] - df['low'], np.abs(df['high'] - df['close'].shift())),
            np.abs(df['low'] - df['close'].shift())
        )
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        df['volatility'] = df['atr'] / df['close']
        
        # Distance from EMA in ATR units
        df['distance_from_ema'] = (df['close'] - df['ema_200']) / df['atr']
        
        # RSI (momentum confirmation)
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # Momentum MA (rate of change)
        df['momentum_ma'] = df['close'].rolling(window=self.momentum_ma).mean()
        df['momentum'] = df['close'] - df['momentum_ma']
        
        # Volume MA
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma).mean()
        
        # Recent swing high (for pullback identification)
        df['swing_high'] = df['high'].rolling(window=self.swing_lookback).max()
        
        return df
    
    def _detect_pullback(self, df):
        """
        Detect pullback: price is close to EMA but not too close (healthy retracement).
        
        Returns boolean series: True where pullback conditions met
        """
        distance = df['distance_from_ema']
        
        # Pullback condition: price is within retracement zone of EMA
        # Close enough to EMA (retraced) but not too close (not oversold)
        # AND closer to EMA than recent high (retracing, not new high)
        
        in_retracement = (distance > self.pullback_atr_min) & (distance < self.pullback_atr_max)
        
        # Also check: price should be below recent swing high (confirming pullback)
        below_swing = df['close'] < df['swing_high']
        
        return in_retracement & below_swing
    
    def _confirm_momentum(self, df):
        """
        Confirm momentum recovery: price showing strength again after pullback.
        
        Returns boolean series: True where momentum is confirming
        """
        # RSI should be recovering but not yet overbought
        rsi_recovering = (df['rsi'] > self.rsi_recovery) & (df['rsi'] < 65)
        
        # Momentum should be positive (price > momentum MA)
        momentum_positive = df['momentum'] > 0
        
        return rsi_recovering & momentum_positive
    
    def _calculate_rsi(self, prices, period):
        """Calculate RSI indicator."""
        deltas = prices.diff()
        seed = deltas[:period + 1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices, dtype=float)
        rsi[:period] = 100 - 100 / (1 + rs) if rs > 0 else 0
        
        for i in range(period, len(prices)):
            delta = deltas.iloc[i] if i < len(deltas) else 0
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down = (down * (period - 1)) / period
            else:
                up = (up * (period - 1)) / period
                down = (down * (period - 1) - delta) / period
            
            rs = up / down if down != 0 else 0
            rsi[i] = 100 - 100 / (1 + rs) if rs > 0 else 0
        
        return rsi
    
    def get_statistics(self, signals):
        """Return signal generation statistics."""
        signal_count = signals['signal'].sum()
        return {
            'total_signals': int(signal_count),
            'signal_pct': f"{100 * signal_count / len(signals):.2f}%",
        }


def generate_pullback_signals(data):
    """Convenience function for signal generation."""
    generator = PullbackSignalGenerator()
    return generator.generate_signals(data)

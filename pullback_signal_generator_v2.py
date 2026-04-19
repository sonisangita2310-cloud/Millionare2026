"""
IMPROVED PULLBACK STRATEGY - Relaxed Pullback Detection

Changes from v1:
  - Pullback range: 0.3-1.2 ATR → 0.15-1.5 ATR (includes tight pullbacks)
  - Momentum RSI: 35-65 → 30-70 (more entries on reversal)
  - Volume: keep strict (maintain quality confirmation)
  
Expected results:
  - Signals: 136 → 250-350 (+100-150%)
  - Trades: 77 → 150-200 (+50-100%)
  - Maintain or improve PF (if momentum selection is good)
  
Rationale:
  - Smaller retracements are VALID pullback entries
  - They just happened to be filtered out in v1
  - Momentum + volume confirmation still maintains quality
"""

import pandas as pd
import numpy as np


class ImprovedPullbackSignalGenerator:
    """Improved pullback detection with relaxed thresholds."""
    
    def __init__(self):
        """Initialize with relaxed parameters."""
        # Trend identification
        self.trend_ema = 200
        
        # IMPROVED: Relaxed pullback range (include tight retracements)
        self.pullback_atr_min = 0.15   # Lowered from 0.3 (include tight pullbacks)
        self.pullback_atr_max = 1.5    # Raised from 1.2 (wider range)
        
        # Momentum confirmation
        self.rsi_period = 14
        self.rsi_recovery = 30         # Lowered from 35 (more entries)
        self.momentum_ma = 50
        
        # Volume confirmation (keep strict for quality)
        self.volume_ma = 20
        self.volume_min = 1.0
        
        # Volatility
        self.atr_period = 14
        self.volatility_min = 0.005
        self.volatility_max = 0.03
        
        # Pullback tracking
        self.swing_lookback = 30
    
    def generate_signals(self, ohlcv):
        """Generate improved pullback signals."""
        df = ohlcv.copy()
        df = self._calculate_indicators(df)
        
        # Filters
        in_uptrend = df['close'] > df['ema_200']
        in_pullback = self._detect_pullback(df)
        momentum_confirm = self._confirm_momentum(df)
        volume_confirm = df['volume'] > df['volume_ma']
        vol_ok = (df['volatility'] >= self.volatility_min) & (df['volatility'] <= self.volatility_max)
        
        # Combine
        df['signal'] = (in_uptrend & in_pullback & momentum_confirm & volume_confirm & vol_ok).astype(int)
        
        return df
    
    def _calculate_indicators(self, df):
        """Calculate technical indicators."""
        df['ema_200'] = df['close'].ewm(span=self.trend_ema, adjust=False).mean()
        
        tr = np.maximum(
            np.maximum(df['high'] - df['low'], np.abs(df['high'] - df['close'].shift())),
            np.abs(df['low'] - df['close'].shift())
        )
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        df['volatility'] = df['atr'] / df['close']
        df['distance_from_ema'] = (df['close'] - df['ema_200']) / df['atr']
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # Momentum
        df['momentum_ma'] = df['close'].rolling(window=self.momentum_ma).mean()
        df['momentum'] = df['close'] - df['momentum_ma']
        
        # Volume MA
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma).mean()
        
        # Swing high
        df['swing_high'] = df['high'].rolling(window=self.swing_lookback).max()
        
        return df
    
    def _detect_pullback(self, df):
        """Detect pullback (relaxed range)."""
        distance = df['distance_from_ema']
        in_retracement = (distance > self.pullback_atr_min) & (distance < self.pullback_atr_max)
        below_swing = df['close'] < df['swing_high']
        return in_retracement & below_swing
    
    def _confirm_momentum(self, df):
        """Confirm momentum recovery (relaxed RSI)."""
        rsi_recovering = (df['rsi'] > self.rsi_recovery) & (df['rsi'] < 70)
        momentum_positive = df['momentum'] > 0
        return rsi_recovering & momentum_positive
    
    def _calculate_rsi(self, prices, period):
        """Calculate RSI."""
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


def generate_improved_pullback_signals(data):
    """Convenience function."""
    generator = ImprovedPullbackSignalGenerator()
    return generator.generate_signals(data)

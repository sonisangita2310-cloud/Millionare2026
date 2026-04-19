"""
SIGNAL QUALITY ANALYSIS: High Confidence Only

Insight from exit testing:
  - Relaxing SL improves WR but doesn't fix PF
  - This means the market regime has more volatility than expected
  - OR we're entering too many marginal trades

Solution: Filter to ONLY highest confidence entries

Approach:
  - Add RSI extremeness requirement (RSI <20 or >80, not just <30 or >70)
  - This filters to only very oversold/overbought setups
  - Expected: 40-50% fewer signals but much higher quality

Test will show if quality-over-quantity works better than frequency.
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

class HighConfidenceSignalGenerator:
    """Ultra-conservative signal generation: only highest conviction entries."""
    
    def __init__(self):
        self.breakout_periods = 20
        self.volume_ma_period = 20
        self.trend_ema_period = 200
        self.trend_strength_threshold = 0.5
        self.rsi_period = 14
        self.rsi_low = 20      # MORE extreme (was 30)
        self.rsi_high = 80     # MORE extreme (was 70)
        self.volatility_min = 0.005
        self.volatility_max = 0.03
        self.atr_period = 14
    
    def generate_signals(self, ohlcv):
        """Generate only high-confidence signals."""
        df = ohlcv.copy()
        df = self._add_indicators(df)
        
        f1 = self._filter_breakout(df)
        f2 = self._filter_volume(df)
        f3 = self._filter_trend(df)
        f4 = self._filter_rsi_extreme(df)
        f5 = self._filter_volatility(df)
        f6 = self._filter_trend_strength(df)
        
        df['signal'] = (f1 & f2 & f3 & f4 & f5 & f6).astype(int)
        return df
    
    def _add_indicators(self, df):
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMA
        df['ema_200'] = df['close'].ewm(span=self.trend_ema_period, adjust=False).mean()
        
        # ATR
        tr = np.maximum(
            np.maximum(df['high'] - df['low'], np.abs(df['high'] - df['close'].shift())),
            np.abs(df['low'] - df['close'].shift())
        )
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        df['volume_ma_20'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volatility'] = df['atr'] / df['close']
        df['trend_strength'] = np.abs(df['close'] - df['ema_200']) / df['atr']
        
        return df
    
    def _filter_breakout(self, df):
        rolling_max = df['high'].rolling(window=self.breakout_periods).max()
        return df['high'] == rolling_max
    
    def _filter_volume(self, df):
        return df['volume'] > df['volume_ma_20']
    
    def _filter_trend(self, df):
        return df['close'] > df['ema_200']
    
    def _filter_rsi_extreme(self, df):
        return (df['rsi'] < self.rsi_low) | (df['rsi'] > self.rsi_high)
    
    def _filter_volatility(self, df):
        return (df['volatility'] >= self.volatility_min) & (df['volatility'] <= self.volatility_max)
    
    def _filter_trend_strength(self, df):
        return df['trend_strength'] >= self.trend_strength_threshold

# Load and test
data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')

gen = HighConfidenceSignalGenerator()
signals = gen.generate_signals(data)

print("\nHIGH CONFIDENCE SIGNAL ANALYSIS")
print("=" * 100)
print(f"\nRSI Thresholds: <20 or >80 (ultra-extreme, was <30 or >70)")
print(f"\nSignals generated: {int(signals['signal'].sum())}")
print(f"Baseline (Simplified Optimized): 441")
print(f"Reduction: {(1 - signals['signal'].sum() / 441) * 100:.1f}%")
print(f"Monthly frequency estimate: {signals['signal'].sum() / 24 / 12:.1f} trades/month")
print(f"Target: 5-8/month (lower but higher quality)")

# Compare signal distribution
print(f"\nRSI Distribution of filtered signals:")
signal_rows = signals[signals['signal'] == 1]
print(f"  <20: {(signal_rows['rsi'] < 20).sum()}")
print(f"  >80: {(signal_rows['rsi'] > 80).sum()}")
print(f"  Mean RSI: {signal_rows['rsi'].mean():.1f}")
print(f"  Std RSI: {signal_rows['rsi'].std():.1f}")

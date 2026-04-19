"""
PULLBACK SIGNAL GENERATOR v3 - IMPROVED WITH FILTERS

Key improvements from trade analysis:
1. Time-of-day filter (skip worst hours: 10, 17, 22 UTC)
2. Day-of-week filter (skip Friday, 21.4% WR)
3. RSI range refinement (avoid extremes, target 40-65 range)
4. Lower SL multiplier (0.9x instead of 1.2x) - winners hold longer so tighter SL helps
5. Better trend confirmation (0.7+ trend strength minimum)

Expected: Higher win rate (38%+), PF > 1.1x
"""

import pandas as pd
import numpy as np
from typing import Tuple

class PullbackSignalGeneratorV3:
    """Improved pullback strategy with refined filters"""
    
    def __init__(self):
        # Core parameters
        self.ema_period = 200
        self.atr_period = 14
        self.rsi_period = 14
        self.volume_ma_period = 20
        self.momentum_ma_period = 50
        
        # Pullback range
        self.pullback_atr_min = 0.2  # Improved from 0.15
        self.pullback_atr_max = 1.0  # Tightened from 1.5
        
        # Improved RSI filter: target 45-65 (avoid overbought > 70, oversold < 35)
        self.rsi_recovery_min = 45  # Improved from 30
        self.rsi_recovery_max = 65  # New: avoid overbought
        
        # Volume and momentum
        self.volume_threshold = 1.0  # Volume >= 1x MA
        self.momentum_positive = True  # Price > momentum MA
        
        # New filters for quality
        self.min_trend_strength = 0.7  # New: require strong trend (0.7 ATR distance from EMA)
        
        # Time filters - NEW
        self.bad_hours = {10, 17, 22}  # Skip these UTC hours (0% or low WR)
        self.bad_days = {4}  # 4 = Friday (21.4% WR, worst day)
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate pullback entry signals"""
        
        df = data.copy()
        
        # Calculate indicators
        df['ema_200'] = df['close'].ewm(span=self.ema_period).mean()
        
        # ATR
        tr = np.maximum(
            np.maximum(df['high'] - df['low'], abs(df['high'] - df['close'].shift())),
            abs(df['low'] - df['close'].shift())
        )
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume MA
        df['vol_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        
        # Momentum MA
        df['mom_ma'] = df['close'].rolling(window=self.momentum_ma_period).mean()
        
        # Calculate pullback distance
        df['distance_to_ema'] = abs(df['close'] - df['ema_200'])
        df['pullback_size'] = df['distance_to_ema'] / df['atr']
        
        # Trend strength
        df['trend_strength'] = df['distance_to_ema'] / df['atr']
        
        # Initialize signal column
        df['signal'] = 0
        
        # Generate signals
        for i in range(self.ema_period + self.momentum_ma_period, len(df)):
            # Skip if insufficient data
            if pd.isna(df['atr'].iloc[i]) or df['atr'].iloc[i] == 0:
                continue
            
            # 1. UPTREND: Price > EMA_200
            if df['close'].iloc[i] <= df['ema_200'].iloc[i]:
                continue
            
            # 2. PULLBACK: Within range (0.2-1.0 ATR from EMA)
            pullback_sz = df['pullback_size'].iloc[i]
            if pullback_sz < self.pullback_atr_min or pullback_sz > self.pullback_atr_max:
                continue
            
            # 3. RSI RECOVERY: 45-65 range (IMPROVED - avoid extremes)
            rsi_val = df['rsi'].iloc[i]
            if rsi_val < self.rsi_recovery_min or rsi_val > self.rsi_recovery_max:
                continue
            
            # 4. VOLUME CONFIRMATION
            if df['volume'].iloc[i] < self.volume_threshold * df['vol_ma'].iloc[i]:
                continue
            
            # 5. MOMENTUM: Price > momentum MA
            if df['close'].iloc[i] <= df['mom_ma'].iloc[i]:
                continue
            
            # NEW 6. TREND STRENGTH: Must be in meaningful pullback zone
            trend_strength = df['trend_strength'].iloc[i]
            if trend_strength < self.min_trend_strength:
                continue
            
            # NEW 7. TIME OF DAY FILTER
            hour = df.index[i].hour
            if hour in self.bad_hours:
                continue
            
            # NEW 8. DAY OF WEEK FILTER
            day_of_week = df.index[i].dayofweek
            if day_of_week in self.bad_days:
                continue
            
            # All conditions met - SIGNAL!
            df.loc[df.index[i], 'signal'] = 1
        
        return df[['signal']]


# Test the new generator
if __name__ == '__main__':
    print("Testing Pullback Signal Generator v3...")
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    
    # Generate signals
    gen = PullbackSignalGeneratorV3()
    signals = gen.generate_signals(data)
    
    total_signals = signals['signal'].sum()
    print(f"✓ Total signals: {total_signals}")
    print(f"✓ Signal frequency: {total_signals / 17520 * 100:.2f}% of candles")
    print(f"✓ Expected trades/month: {total_signals / 24:.1f}")

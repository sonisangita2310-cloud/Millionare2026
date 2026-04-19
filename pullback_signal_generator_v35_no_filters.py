"""
PULLBACK SIGNAL GENERATOR v3.5-NO-FILTERS (BASELINE WITHOUT TIME FILTERING)

Purpose: Remove time-of-day and day-of-week filters to test if edge is real or just overfitting

Configuration: IDENTICAL to v3.5 except NO time/day filters
- RSI range: 40-70 ✓ (kept)
- Pullback range: 0.15-1.2 ATR ✓ (kept)
- Trend strength: 0.6x ATR ✓ (kept)
- Volume filter: 0.8x MA ✓ (kept)
- Momentum filter: price > MA_50 ✓ (kept)
- **TIME FILTERS: REMOVED** ✗
- **DAY FILTERS: REMOVED** ✗

This shows how much improvement is ONLY from time-based filters
"""

import pandas as pd
import numpy as np
from typing import Tuple

class PullbackSignalGeneratorV35NoFilters:
    """Pullback strategy WITHOUT time/day filters - baseline for robustness test"""
    
    def __init__(self):
        # Core parameters (IDENTICAL to v3.5)
        self.ema_period = 200
        self.atr_period = 14
        self.rsi_period = 14
        self.volume_ma_period = 20
        self.momentum_ma_period = 50
        
        # Pullback range (KEPT from v3.5)
        self.pullback_atr_min = 0.15
        self.pullback_atr_max = 1.2
        
        # RSI filter (KEPT from v3.5)
        self.rsi_recovery_min = 40
        self.rsi_recovery_max = 70
        
        # Volume and momentum (KEPT from v3.5)
        self.volume_threshold = 0.8
        self.momentum_positive = True
        
        # Trend strength (KEPT from v3.5)
        self.min_trend_strength = 0.6
        
        # TIME FILTERS: REMOVED FOR THIS TEST
        # self.bad_hours = {10, 17, 22}  # ← COMMENTED OUT
        # self.bad_days = {4}  # ← COMMENTED OUT
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate pullback entry signals WITHOUT time filtering"""
        
        df = data.copy()
        
        # Calculate indicators (IDENTICAL to v3.5)
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
        
        # Generate signals (IDENTICAL to v3.5 except NO time checks)
        for i in range(self.ema_period + self.momentum_ma_period, len(df)):
            # Skip if insufficient data
            if pd.isna(df['atr'].iloc[i]) or df['atr'].iloc[i] == 0:
                continue
            
            # 1. UPTREND: Price > EMA_200
            if df['close'].iloc[i] <= df['ema_200'].iloc[i]:
                continue
            
            # 2. PULLBACK: Within range
            pullback_sz = df['pullback_size'].iloc[i]
            if pullback_sz < self.pullback_atr_min or pullback_sz > self.pullback_atr_max:
                continue
            
            # 3. RSI RECOVERY: 40-70 range
            rsi_val = df['rsi'].iloc[i]
            if rsi_val < self.rsi_recovery_min or rsi_val > self.rsi_recovery_max:
                continue
            
            # 4. VOLUME CONFIRMATION
            if df['volume'].iloc[i] < self.volume_threshold * df['vol_ma'].iloc[i]:
                continue
            
            # 5. MOMENTUM: Price > momentum MA
            if df['close'].iloc[i] <= df['mom_ma'].iloc[i]:
                continue
            
            # 6. TREND STRENGTH
            trend_strength = df['trend_strength'].iloc[i]
            if trend_strength < self.min_trend_strength:
                continue
            
            # *** NO TIME FILTERS HERE - THAT'S THE DIFFERENCE ***
            # (removed UTC hour check and day-of-week check)
            
            # All conditions met - SIGNAL!
            df.loc[df.index[i], 'signal'] = 1
        
        return df[['signal']]


# Test the new generator
if __name__ == '__main__':
    print("Testing Pullback Signal Generator v3.5-NO-FILTERS...")
    
    # Load data
    data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index('timestamp')
    data = data.iloc[-17520:]
    
    # Generate signals
    gen = PullbackSignalGeneratorV35NoFilters()
    signals = gen.generate_signals(data)
    
    total_signals = signals['signal'].sum()
    print(f"✓ Total signals (NO time filters): {total_signals}")
    print(f"✓ Signal frequency: {total_signals / 17520 * 100:.2f}% of candles")
    print(f"✓ Expected trades/month: {total_signals / 24:.1f}")

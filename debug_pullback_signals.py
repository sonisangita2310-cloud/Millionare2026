"""
PULLBACK SIGNAL DEBUG - Why So Few Signals?

Analysis:
  - Generated 136 signals over 2 years
  - Expected: 200-350
  - Only 56 signals turned into trades (41% conversion)
  
Problem Investigation:
  - Filter 1: In uptrend (trend_ema)
  - Filter 2: In pullback zone (distance from EMA)
  - Filter 3: Momentum recovery (RSI + momentum)
  - Filter 4: Volume confirmation
  - Filter 5: Volatility OK

Which filter is blocking signals?
"""

import pandas as pd
import numpy as np
from pullback_signal_generator import PullbackSignalGenerator

# Load data
data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')

# Last 2 years only
data = data.iloc[-17520:]

print("=" * 100)
print("PULLBACK SIGNAL DEBUG - Filter Analysis")
print("=" * 100)

# Generate signals
gen = PullbackSignalGenerator()
signals = gen.generate_signals(data)

print(f"\nTotal candles: {len(signals):,}")
print(f"Total signals: {signals['signal'].sum():.0f}")

# Check each filter
in_uptrend = signals['close'] > signals['ema_200']
print(f"\n--- FILTER 1: In Uptrend ---")
print(f"Candles in uptrend: {in_uptrend.sum():,} ({in_uptrend.sum()/len(signals)*100:.1f}%)")

# Pullback detection
distance = signals['distance_from_ema']
in_pullback = (distance > 0.3) & (distance < 1.2)
print(f"\n--- FILTER 2: In Pullback Zone (0.3-1.2 ATR) ---")
print(f"In pullback: {in_pullback.sum():,} ({in_pullback.sum()/len(signals)*100:.1f}%)")
print(f"Distance distribution:")
print(f"  <0.3 ATR: {(distance < 0.3).sum():,} (too close to EMA)")
print(f"  0.3-1.2 ATR: {in_pullback.sum():,} (good zone)")
print(f"  >1.2 ATR: {(distance > 1.2).sum():,} (too far from EMA)")

# Momentum
print(f"\n--- FILTER 3: Momentum Recovery ---")
rsi_ok = (signals['rsi'] > 35) & (signals['rsi'] < 65)
momentum_ok = signals['momentum'] > 0
print(f"RSI recovering (35-65): {rsi_ok.sum():,}")
print(f"Momentum positive: {momentum_ok.sum():,}")
print(f"Both: {(rsi_ok & momentum_ok).sum():,}")

# Volume
print(f"\n--- FILTER 4: Volume ---")
vol_ok = signals['volume'] > signals['volume_ma']
print(f"Volume > MA: {vol_ok.sum():,}")

# Volatility
print(f"\n--- FILTER 5: Volatility ---")
vol_range = (signals['volatility'] >= 0.005) & (signals['volatility'] <= 0.03)
print(f"Volatility 0.5%-3%: {vol_range.sum():,}")

# Progressive filtering
print(f"\n--- PROGRESSIVE FILTERING ---")
f1 = in_uptrend
print(f"After F1 (uptrend): {f1.sum():,}")

f2 = f1 & in_pullback
print(f"After F2 (pullback zone): {f2.sum():,}")

f3 = f2 & rsi_ok & momentum_ok
print(f"After F3 (momentum): {f3.sum():,}")

f4 = f3 & vol_ok
print(f"After F4 (volume): {f4.sum():,}")

f5 = f4 & vol_range
print(f"After F5 (volatility): {f5.sum():,}")

print(f"\nFinal signals: {signals['signal'].sum():.0f}")

# Identify the most restrictive filter
print(f"\n--- MOST RESTRICTIVE FILTER ---")
print(f"From uptrend to pullback: {f1.sum():,} → {f2.sum():,} (drop {(1-f2.sum()/f1.sum())*100:.1f}%)")
print(f"From pullback to momentum: {f2.sum():,} → {f3.sum():,} (drop {(1-f3.sum()/f2.sum())*100:.1f}%)")
print(f"From momentum to volume: {f3.sum():,} → {f4.sum():,} (drop {(1-f4.sum()/f3.sum())*100:.1f}%)")
print(f"From volume to volatility: {f4.sum():,} → {f5.sum():,} (drop {(1-f5.sum()/f4.sum())*100:.1f}%)")

print(f"\n{'=' * 100}")
print("RECOMMENDATIONS:")
print(f"{'=' * 100}")

if (1-f2.sum()/f1.sum())*100 > 50:
    print("Problem: Pullback detection too tight")
    print("Solution: Relax pullback_atr range (0.3-1.2 → 0.2-1.5)")
elif (1-f3.sum()/f2.sum())*100 > 50:
    print("Problem: Momentum filter too restrictive")
    print("Solution: Relax RSI range (35-65 → 30-70) or momentum requirement")
elif (1-f4.sum()/f3.sum())*100 > 50:
    print("Problem: Volume filter blocking too many")
    print("Solution: Lower to volume > 0.8x MA")
else:
    print("Filters fairly balanced. Generate fewer but higher quality signals.")

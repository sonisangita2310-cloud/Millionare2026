import pandas as pd
import numpy as np
from enhanced_signal_generator import EnhancedSignalGenerator

# Load data
data = pd.read_csv('data_cache/BTC_USDT_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')

# Generate with debug
gen = EnhancedSignalGenerator()
signals = gen.generate_signals(data)

# Check each filter
print('Filter Analysis (last 100 rows):')
print(f"new_high: {signals['new_high'].tail(100).sum()} / 100")
print(f"volume_check: {signals['volume_check'].tail(100).sum()} / 100")
print(f"in_uptrend: {signals['in_uptrend'].tail(100).sum()} / 100")
print(f"rsi_extreme: {signals['rsi_extreme'].tail(100).sum()} / 100")
print(f"volatility_check: {signals['volatility_check'].tail(100).sum()} / 100")
print(f"trend_strong: {signals['trend_strong'].tail(100).sum()} / 100")
print(f"breakout_force_ok: {signals['breakout_force_ok'].tail(100).sum()} / 100")
print(f"good_distance: {signals['good_distance'].tail(100).sum()} / 100")

# Count across entire dataset
print('\nFull dataset filter counts:')
print(f"new_high: {signals['new_high'].sum()} total")
print(f"volume_check: {signals['volume_check'].sum()} total")
print(f"in_uptrend: {signals['in_uptrend'].sum()} total")
print(f"rsi_extreme: {signals['rsi_extreme'].sum()} total")
print(f"volatility_check: {signals['volatility_check'].sum()} total")
print(f"trend_strong: {signals['trend_strong'].sum()} total")
print(f"breakout_force_ok: {signals['breakout_force_ok'].sum()} total")
print(f"good_distance: {signals['good_distance'].sum()} total")

# Find intersection points
print('\nCombined filter analysis:')
f1 = signals['new_high']
f2 = f1 & signals['volume_check']
f3 = f2 & signals['in_uptrend']
f4 = f3 & signals['rsi_extreme']
f5 = f4 & signals['volatility_check']
f6 = f5 & signals['trend_strong']
f7 = f6 & signals['breakout_force_ok']
f8 = f7 & signals['good_distance']

print(f"After Filter 1 (new_high): {f1.sum()}")
print(f"After Filter 2 (volume_check): {f2.sum()}")
print(f"After Filter 3 (in_uptrend): {f3.sum()}")
print(f"After Filter 4 (rsi_extreme): {f4.sum()}")
print(f"After Filter 5 (volatility_check): {f5.sum()}")
print(f"After Filter 6 (trend_strong): {f6.sum()}")
print(f"After Filter 7 (breakout_force_ok): {f7.sum()}")
print(f"After Filter 8 (good_distance): {f8.sum()}")

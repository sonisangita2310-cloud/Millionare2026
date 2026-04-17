#!/usr/bin/env python3
"""
QUICK TEST: S001 on pre-aligned architecture
Goal: Verify refactor works and if trades trigger
"""
import pandas as pd
import sys
sys.path.insert(0, '.')

from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.backtest_runner import BacktestRunner
from src.backtest_engine import BacktestEngine

print("\n" + "="*70)
print("QUICK TEST: S001 on Pre-Aligned Architecture")
print("="*70)

# Load scenario
print("\n[1] Loading S001...")
sp = ScenarioParser(scenarios_file='scenarios/SCENARIOS_STRUCTURED.json')
s001 = [s for s in sp.get_all_scenarios() if s.id == 'S001'][0]
print(f"    {s001.name}")

# Load & align data (using new architecture)
print("\n[2] Loading multi-timeframe data for alignment...")
runner = BacktestRunner()
runner.scenario_parser = sp

# Load minimal data
from src.backtest_data_engine import DataEngine
data_engine = DataEngine()
data = data_engine.get_all_data(['BTC/USDT'], ['3m', '5m', '15m', '1h', '4h'], force_real_data=False)

print(f"    Data loaded for: {list(data.keys())}")

# Calculate indicators (as backtest does)
print("\n[3] Calculating indicators...")
for symbol, timeframes_data in data.items():
    for timeframe, df in timeframes_data.items():
        if len(df) < 200:
            print(f"    [SKIP] {symbol} {timeframe} ({len(df)} too small)")
            continue
        
        df_with_indicators = IndicatorsEngine.calculate_all_indicators(df)
        runner.indicators.add_timeframe_indicators(symbol, timeframe, df_with_indicators)
        print(f"    ✓ {symbol} {timeframe}: {len(df_with_indicators)} candles")

# Pre-align data (NEW ARCHITECTURE)
print("\n[4] Pre-computing aligned data...")
runner._precompute_aligned_data()

# Test S001 on pre-aligned data
print("\n[5] Running S001 backtest on aligned data...")
symbol = 'BTC/USDT'

if symbol not in runner.aligned_data:
    print(f"    ERROR: {symbol} not in aligned_data")
    sys.exit(1)

df_aligned = runner.aligned_data[symbol]
print(f"    Aligned DataFrame: {len(df_aligned)} rows × {len(df_aligned.columns)} columns")
print(f"    Columns with '_3m': {len([c for c in df_aligned.columns if '_3m' in c])}")
print(f"    Columns with '_1h': {len([c for c in df_aligned.columns if '_1h' in c])}")

# Run backtest
print(f"    [DEBUG] Creating engine...")
engine = BacktestEngine(100000)
print(f"    [DEBUG] Engine created, starting simulation...")

print(f"    [DEBUG] S001 entry conditions: {s001.get_entry_conditions()}")
print(f"    [DEBUG] First 5 rows of aligned_data columns:")
print(f"    Available: {list(df_aligned.columns[:10])}")

trade_count = runner._simulate_scenario(s001, df_aligned, engine)

print(f"\n[6] Results:")
print(f"    Trades: {trade_count}")
metrics = engine.get_backtest_metrics()
print(f"    Profit Factor: {metrics.get('profit_factor', 'N/A')}")
print(f"    Win Rate: {metrics.get('win_rate', 'N/A')}")
print(f"    Max Drawdown: {metrics.get('max_drawdown', 'N/A')}")

print("\n" + "="*70)
if trade_count > 0:
    print(f"✓ SUCCESS: S001 generated {trade_count} trades on aligned data")
    print(f"  → Architecture refactor WORKS")
    print(f"  → Ready for full validation")
else:
    print(f"✗ S001 still 0 trades on aligned data")
    print(f"  → But architecture is fast now")
    print(f"  → Strategy logic issue remains")

print("="*70 + "\n")

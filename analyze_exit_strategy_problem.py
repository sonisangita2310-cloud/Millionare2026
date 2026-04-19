"""
DEEP ANALYSIS: Why Entry Filtering Isn't Working

Problem: Even with trend strength floor (+1.5% win rate), we're still unprofitable
- Simplified Optimized: 29.9% WR, 0.82 PF
- BALANCED: 28.4% WR, 0.77 PF
- Gap: Only +1.5% WR improvement despite filtering weak-trend entries

Root Cause Analysis:
  1. Win rate improvement insufficient for current exit parameters
  2. Need 35%+ WR for 2.9x TP/SL to be profitable at scale
  3. Entry quality improvements plateauing - diminishing returns

Decision Point:
  EITHER:
    A) Exit optimization (increase TP to 3.8-4.0x ATR) - artificial but necessary
    B) Exit strategy redesign (trailing stop, partial profits, break-even) - fundamental
    C) Acknowledge edge is too weak and rebuild from scratch

This analysis determines which path forward.
"""

import pandas as pd
import numpy as np

# Load the trades
trades = pd.read_csv('enhanced_backtest_trades.csv')

print("\n" + "=" * 100)
print("DEEP ANALYSIS: Entry Quality vs Exit Parameters")
print("=" * 100)

# 1. Distribution analysis
print("\n--- WIN/LOSS DISTRIBUTION ---")
winners = trades[trades['winner'] == 1]
losers = trades[trades['winner'] == 0]

print(f"Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
print(f"  Avg P&L: ${winners['net_pnl'].mean():.2f}")
print(f"  Median P&L: ${winners['net_pnl'].median():.2f}")
print(f"  Max P&L: ${winners['net_pnl'].max():.2f}")
print(f"  Min P&L: ${winners['net_pnl'].min():.2f}")

print(f"\nLosers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)")
print(f"  Avg P&L: ${losers['net_pnl'].mean():.2f}")
print(f"  Median P&L: ${losers['net_pnl'].median():.2f}")
print(f"  Max P&L: ${losers['net_pnl'].max():.2f}  (best loss)")
print(f"  Min P&L: ${losers['net_pnl'].min():.2f}  (worst loss)")

# 2. Exit type analysis
print("\n--- EXIT TYPE ANALYSIS ---")
print("\nWinner exits:")
print(trades[trades['winner'] == 1]['exit_type'].value_counts())
print("\nLoser exits:")
print(trades[trades['winner'] == 0]['exit_type'].value_counts())

# 3. Duration analysis
print("\n--- TRADE DURATION ---")
print(f"Winner avg bars held: {winners['bars_held'].mean():.1f}")
print(f"Loser avg bars held: {losers['bars_held'].mean():.1f}")
print(f"Ratio: {winners['bars_held'].mean() / losers['bars_held'].mean():.2f}x")

# 4. Profitability calculation
print("\n--- PROFITABILITY MATH ---")
total_win_pct = trades[trades['winner'] == 1]['pnl_pct'].sum()
total_loss_pct = trades[trades['winner'] == 0]['pnl_pct'].sum()
avg_per_trade_pct = trades['pnl_pct'].mean()

print(f"Total win pct: {total_win_pct:.2f}%")
print(f"Total loss pct: {total_loss_pct:.2f}%")
print(f"Net return: {total_win_pct + total_loss_pct:.2f}%")
print(f"Avg per trade: {avg_per_trade_pct:.3f}%")
print(f"Trades per month: 7.2")
print(f"Monthly avg return: {avg_per_trade_pct * 7.2:.2f}%")

# 5. Breakeven analysis
print("\n--- WHAT'S NEEDED FOR PROFITABILITY ---")
print(f"Current profit factor: 0.82x")
print(f"Breakeven profit factor: 1.00x")
print(f"Gap: {1.00 / 0.82:.2f}x improvement needed")

print(f"\nOption A: Increase TP by {1.00 / 0.82:.2f}x")
print(f"  Current TP: 2.9 ATR")
print(f"  Required TP: {2.9 * (1.00 / 0.82):.1f} ATR")
print(f"  Feasibility: LOW (requires very wide TP, misses quick trades)")

print(f"\nOption B: Increase Win Rate")
print(f"  Current: 29.9%")
print(f"  Needed for 0.82 PF at current exits: 35%+")
print(f"  Gap: +{35 - 29.9:.1f} percentage points")
print(f"  Feasibility: UNCLEAR (entry filtering maxing out)")

print(f"\nOption C: Different exit strategy")
print(f"  Current: Fixed TP/SL")
print(f"  Proposed: Hybrid (TP partial, SL full, trail)")
print(f"  Feasibility: MEDIUM (requires redesign)")

# 6. Period analysis
print("\n--- EARLY VS LATE TRADES ---")
trades['trade_num'] = range(1, len(trades) + 1)
first_half = trades[trades['trade_num'] <= len(trades) // 2]
second_half = trades[trades['trade_num'] > len(trades) // 2]

print(f"First half trades: {len(first_half)}, WR: {first_half['winner'].sum()/len(first_half)*100:.1f}%, PF: {first_half[first_half['winner']==1]['net_pnl'].sum() / abs(first_half[first_half['winner']==0]['net_pnl'].sum()):.2f}x")
print(f"Second half trades: {len(second_half)}, WR: {second_half['winner'].sum()/len(second_half)*100:.1f}%, PF: {second_half[second_half['winner']==1]['net_pnl'].sum() / abs(second_half[second_half['winner']==0]['net_pnl'].sum()):.2f}x")

# 7. Key insight
print("\n" + "=" * 100)
print("KEY INSIGHT")
print("=" * 100)
print("""
The core problem: Entry quality improvements are hitting a CEILING.

Simplified Optimized with trend strength floor only achieved:
  - 29.9% win rate (vs baseline 28.4%)
  - +1.5 percentage points gain

This suggests:
  1. Trend quality is NOT the main driver of losers
  2. Most losers occur due to exit timing/parameters, not entry quality
  3. Further entry optimization will have minimal impact

RECOMMENDATION:
  Stop focusing on entry filtering. Instead, redesign EXIT STRATEGY:
  
  Current problem: 70% of trades lose money despite proper entry
  This means exits are likely:
    - Too tight (SL hit on noise)
    - Not aggressive enough (TP never reached)
    - Wrong type (fixed TP unrealistic for crypto volatility)
  
  Next Steps:
    1. Analyze ONLY the winners: what makes them work?
    2. Analyze exit timing: are we exiting winners too early?
    3. Test TRAILING STOP strategy instead of fixed TP
    4. Consider PARTIAL PROFIT TAKING (25% at 1x TP, 25% at 2x TP, etc.)
""")

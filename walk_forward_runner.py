#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Walk-Forward Validation Runner
Validates trading strategies using chronological train/test split (60/40)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.walk_forward_validator import WalkForwardValidator

if __name__ == "__main__":
    try:
        print("\n" + "="*100)
        print(" "*25 + "WALK-FORWARD VALIDATION SYSTEM")
        print(" "*20 + "Distinguishing Real Edges from Overfitting")
        print("="*100)
        
        validator = WalkForwardValidator(initial_capital=100000.0)
        # ALL 32 strategies require these timeframes (S017 needs Weekly but skip for API compatibility)
        results = validator.run_validation(
            symbols=['BTC/USDT', 'ETH/USDT'],
            timeframes=['1m', '3m', '4h', '5m', '15m', '1h']
        )
        
        if results:
            print("\n" + "="*100)
            print("✅ WALK-FORWARD VALIDATION COMPLETE")
            print("="*100)
            print(f"\n📊 Classification Summary:")
            print(f"   ✅ ROBUST:  {len(results['robust']):2d} strategies (Ready for deployment)")
            print(f"   ⚠️  OVERFIT: {len(results['overfit']):2d} strategies (Need parameter tuning)")
            print(f"   ❌ WEAK:    {len(results['weak']):2d} strategies (No consistent edge)")
            
            if results['robust']:
                print(f"\n🎯 Recommended Action:")
                print(f"   Deploy the {len(results['robust'])} ROBUST strategies")
                print(f"   These have proven edge in both train AND test periods")
            
            print(f"\n📁 Results Files:")
            print(f"   • backtest_results/walk_forward_summary.csv")
            print(f"   • backtest_results/walk_forward_validation.json")
            print(f"   • backtest_results/walk_forward_report.md")
            print("\n" + "="*100)
        else:
            print("\n❌ Validation failed - could not complete analysis")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] User stopped validation")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

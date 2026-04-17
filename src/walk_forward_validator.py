# -*- coding: utf-8 -*-
"""
Walk-Forward Validation System
Validates strategy robustness by testing on train/test split (60/40)
"""

import sys
import os
from datetime import datetime
import pandas as pd
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.backtest_runner import BacktestRunner
from src.backtest_data_engine import DataEngine


class WalkForwardValidator:
    """Validates strategy robustness using walk-forward analysis"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.data_engine = DataEngine()
        self.train_results = {}
        self.test_results = {}
        self.validation_summary = []
    
    def split_data_chronologically(self, data, train_split=0.60):
        """Split data chronologically: first 60% train, last 40% test"""
        print("\n" + "="*70)
        print("DATA SPLIT: TRAIN/TEST (60/40)")
        print("="*70)
        
        train_data = {}
        test_data = {}
        
        for symbol in data:
            train_data[symbol] = {}
            test_data[symbol] = {}
            
            for timeframe in data[symbol]:
                df = data[symbol][timeframe].copy()
                split_idx = int(len(df) * train_split)
                
                train_data[symbol][timeframe] = df.iloc[:split_idx].copy()
                test_data[symbol][timeframe] = df.iloc[split_idx:].copy()
                
                print(f"{symbol} {timeframe}: TRAIN {len(train_data[symbol][timeframe]):,} | TEST {len(test_data[symbol][timeframe]):,}")
        
        return train_data, test_data
    
    def run_backtest_period(self, data, period_name):
        """Run backtest on period with limited data"""
        print(f"\n[Running {period_name} backtest...]")
        
        try:
            runner = BacktestRunner(self.initial_capital)
            runner.data_engine.exchange = self.data_engine.exchange
            
            results = runner.run_full_backtest(
                symbols=list(data.keys()),
                timeframes=list(data[list(data.keys())[0]].keys()),
                use_real_data=True,
                data=data
            )
            
            metrics = {}
            if results and results.get('results'):
                for scenario_id, sr in results['results'].items():
                    metrics[scenario_id] = {
                        'trades': sr.get('trades', 0),
                        'win_rate': sr.get('win_rate', 0),
                        'profit_factor': sr.get('profit_factor', 0),
                        'expectancy': sr.get('expectancy', 0),
                    }
            
            return metrics
        except Exception as e:
            print(f"[ERROR] {period_name} backtest failed: {e}")
            return {}
    
    def validate_consistency(self):
        """Classify strategies by robustness"""
        print("\n" + "="*70)
        print("ROBUSTNESS ANALYSIS")
        print("="*70)
        
        robust = []
        overfit = []
        weak = []
        
        all_strategies = set(self.train_results.keys()) | set(self.test_results.keys())
        
        for strategy_id in all_strategies:
            train_m = self.train_results.get(strategy_id, {})
            test_m = self.test_results.get(strategy_id, {})
            
            train_pf = train_m.get('profit_factor', 0)
            test_pf = test_m.get('profit_factor', 0)
            train_wr = train_m.get('win_rate', 0)
            test_wr = test_m.get('win_rate', 0)
            train_trades = train_m.get('trades', 0)
            test_trades = test_m.get('trades', 0)
            
            # Classification logic
            passes_train = train_pf >= 1.3 and train_trades > 0
            passes_test = test_pf >= 1.3 and test_trades > 0
            wr_stable = abs(test_wr - train_wr) <= 10
            
            if passes_train and passes_test and wr_stable:
                classification = 'ROBUST'
                robust.append(strategy_id)
            elif passes_train and not passes_test:
                classification = 'OVERFIT'
                overfit.append(strategy_id)
            else:
                classification = 'WEAK'
                weak.append(strategy_id)
            
            train_exp = train_m.get('expectancy', 0)
            test_exp = test_m.get('expectancy', 0)
            
            self.validation_summary.append({
                'strategy': strategy_id,
                'classification': classification,
                'train_pf': round(train_pf, 2),
                'test_pf': round(test_pf, 2),
                'train_wr': round(train_wr, 1),
                'test_wr': round(test_wr, 1),
                'wr_diff': round(test_wr - train_wr, 1),
                'train_trades': train_trades,
                'test_trades': test_trades,
                'train_expectancy': round(train_exp, 2),
                'test_expectancy': round(test_exp, 2),
            })
        
        return {
            'robust': robust,
            'overfit': overfit,
            'weak': weak,
            'summary': self.validation_summary
        }
    
    def run_validation(self, symbols=None, timeframes=None):
        """Run complete validation pipeline"""
        if symbols is None:
            symbols = ['BTC/USDT', 'ETH/USDT']
        if timeframes is None:
            # ALL 32 strategies require these timeframes (except S017 which uses Weekly - skip for API compatibility)
            timeframes = ['1m', '3m', '4h', '5m', '15m', '1h']
        
        print("\n" + "="*100)
        print(" "*25 + "WALK-FORWARD VALIDATION SYSTEM")
        print("="*100)
        
        # STARTUP CONFIGURATION LOG
        print("\n[STARTUP] Configuration:")
        print(f"  Symbols: {symbols}")
        print(f"  Timeframes: {timeframes}")
        print(f"  Scenarios file: scenarios/SCENARIOS_STRUCTURED.json (32 strategies, S017 skipped - needs Weekly)")
        print(f"  Status: READY")
        
        # STEP 1: Fetch data
        print("\n[STEP 1/5] Fetching historical data...")
        try:
            data = self.data_engine.get_all_data(symbols, timeframes, force_real_data=False)
        except Exception as e:
            print(f"[ERROR] Cannot fetch data: {e}")
            return None
        
        # STEP 2: Split data
        print("\n[STEP 2/5] Splitting data...")
        train_data, test_data = self.split_data_chronologically(data)
        
        # STEP 3: Test TRAIN period
        print("\n[STEP 3/5] Testing TRAIN period...")
        self.train_results = self.run_backtest_period(train_data, "TRAIN")
        print(f"   TRAIN tested {len(self.train_results)} strategies")
        
        # STEP 4: Test TEST period
        print("\n[STEP 4/5] Testing TEST period...")
        self.test_results = self.run_backtest_period(test_data, "TEST")
        print(f"   TEST tested {len(self.test_results)} strategies")
        
        # STEP 5: Validate
        print("\n[STEP 5/5] Validating consistency...")
        validation = self.validate_consistency()
        
        # Print and export
        self.print_results(validation)
        self.export_results(validation)
        
        return validation
    
    def print_results(self, validation):
        """Print results summary"""
        print("\n" + "="*100)
        print(" "*30 + "VALIDATION RESULTS")
        print("="*100)
        
        robust = validation['robust']
        overfit = validation['overfit']
        weak = validation['weak']
        total = len(robust) + len(overfit) + len(weak)
        
        if total == 0:
            print("\n❌ No strategies tested. Check backtest errors above.")
            return
        
        print(f"\n✅ ROBUST: {len(robust)}/{total} ({len(robust)*100//total}%)")
        for s in sorted(robust)[:5]:
            m = [x for x in validation['summary'] if x['strategy'] == s][0]
            print(f"   {s:45s} │ Train: {m['train_pf']:5.2f} Test: {m['test_pf']:5.2f} │ Δ: {m['wr_diff']:+.1f}%")
        if len(robust) > 5:
            print(f"   ... and {len(robust)-5} more")
        
        print(f"\n⚠️  OVERFIT: {len(overfit)}/{ total} ({len(overfit)*100//total}%)")
        for s in sorted(overfit)[:3]:
            m = [x for x in validation['summary'] if x['strategy'] == s][0]
            print(f"   {s:45s} │ Train: {m['train_pf']:5.2f} → Test: {m['test_pf']:5.2f}")
        
        print(f"\n❌ WEAK: {len(weak)}/{total} ({len(weak)*100//total}%)")
        
        print("\n" + "="*100)
    
    def export_results(self, validation):
        """Export to files"""
        os.makedirs('backtest_results', exist_ok=True)
        
        # CSV
        pd.DataFrame(validation['summary']).to_csv(
            'backtest_results/walk_forward_summary.csv', index=False
        )
        
        # JSON
        with open('backtest_results/walk_forward_validation.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'robust': validation['robust'],
                'overfit': validation['overfit'],
                'weak': validation['weak'],
                'summary': validation['summary'],
            }, f, indent=2, default=str)
        
        # Markdown
        with open('backtest_results/walk_forward_report.md', 'w') as f:
            f.write(f"# Walk-Forward Validation Report\n")
            f.write(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")
            f.write(f"## Results\n")
            f.write(f"- **Robust:** {len(validation['robust'])} strategies\n")
            f.write(f"- **Overfit:** {len(validation['overfit'])} strategies\n")
            f.write(f"- **Weak:** {len(validation['weak'])} strategies\n")
        
        print(f"\n✅ Results exported:")
        print(f"   • backtest_results/walk_forward_summary.csv")
        print(f"   • backtest_results/walk_forward_validation.json")
        print(f"   • backtest_results/walk_forward_report.md")


if __name__ == "__main__":
    validator = WalkForwardValidator(initial_capital=100000.0)
    results = validator.run_validation()

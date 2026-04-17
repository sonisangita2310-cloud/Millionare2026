#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S001 Variants Fast Optimizer - Uses cached data for rapid testing
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.condition_engine import ModularConditionEvaluator
from src.backtest_engine import BacktestEngine, Trade


class FastS001Optimizer:
    """Fast optimizer using cached data and minimal API calls"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.data_engine = DataEngine()
        self.indicators = MultiTimeframeIndicators()
        self.backtest_engine = BacktestEngine(initial_capital)
        self.modular_evaluator = ModularConditionEvaluator(debug=False)
        self.results_summary = []
        
    def load_scenarios(self) -> List[Dict]:
        """Load S001 variants from configuration file"""
        with open("scenarios/S001_RR_OPTIMIZATION.json", 'r') as f:
            config = json.load(f)
        return config.get('scenarios', [])
    
    def run_fast_optimization(self, lookback_days: int = 90) -> Dict:
        """
        Run fast optimization using cached data
        
        Args:
            lookback_days: Number of days of historical data to use
        """
        
        print("\n" + "="*100)
        print(" "*25 + "S001 VARIANTS FAST OPTIMIZATION")
        print(" "*15 + "Using cached data for rapid PF >= 1.2 identification")
        print("="*100)
        print(f"\n📊 Configuration:")
        print(f"   • Initial Capital: ${self.initial_capital:,.0f}")
        print(f"   • Lookback Period: {lookback_days} days")
        print(f"   • Data Source: Cache + Recent Fetch")
        print(f"   • Goal: Identify profitable variants")
        
        # Load scenarios
        scenarios = self.load_scenarios()
        print(f"   • Total Variants: {len(scenarios)}")
        
        # Load data once for all tests
        print(f"\n⏳ Loading market data...")
        try:
            # Try to use cached data, fall back to recent fetch if needed
            data_dict = self._load_optimized_data(lookback_days)
            if not data_dict:
                print("❌ Failed to load data")
                return {}
        except Exception as e:
            print(f"⚠️  Data loading error: {e}")
            return {}
        
        print(f"✅ Data loaded: {len(data_dict)} symbol-timeframe combinations")
        
        # Test each variant
        for i, scenario in enumerate(scenarios, 1):
            variant_id = scenario.get('id', f'Variant_{i}')
            sl_mult = scenario.get('sl_multiplier', 'N/A')
            tp_mult = scenario.get('tp_multiplier', 'N/A')
            
            print(f"\n{'─'*100}")
            print(f"[{i}/{len(scenarios)}] Testing {variant_id}")
            print(f"     SL: {sl_mult}x ATR | TP: {tp_mult}x ATR | R:R: {tp_mult/sl_mult if isinstance(sl_mult, (int, float)) and isinstance(tp_mult, (int, float)) else 'N/A'}")
            
            try:
                # Run backtest on this variant
                metrics = self._run_single_variant_backtest(scenario, data_dict)
                self.results_summary.append(metrics)
                
                # Display results
                self._display_variant_results(metrics)
                
            except Exception as e:
                print(f"     ❌ Error: {str(e)}")
                self.results_summary.append({
                    'variant_id': variant_id,
                    'sl_multiplier': sl_mult,
                    'tp_multiplier': tp_mult,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_profit': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'status': 'ERROR'
                })
        
        # Analyze results
        return self._analyze_results()
    
    def _load_optimized_data(self, lookback_days: int) -> Dict:
        """Load data from cache, fall back to recent fetch"""
        
        data_dict = {}
        symbol = 'BTC/USDT'
        timeframes = ['3m', '1h', '4h']
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        for timeframe in timeframes:
            try:
                # Try cache first
                cache_file = f"data_cache/BTC_USDT_{timeframe}.csv"
                if os.path.exists(cache_file):
                    df = pd.read_csv(cache_file, parse_dates=['timestamp'], index_col='timestamp')
                    # Filter recent data
                    df = df[df.index >= cutoff_date]
                    if len(df) > 0:
                        data_dict[f"{symbol}_{timeframe}"] = df
                        print(f"   ✓ {symbol} {timeframe}: {len(df)} candles from cache")
                    continue
                
                # Fallback: fetch from exchange for this timeframe only
                print(f"   ⏳ Fetching {symbol} {timeframe} (cache miss)...")
                df = self.data_engine.fetch_data(symbol, timeframe, limit=1000)
                if len(df) > 0:
                    data_dict[f"{symbol}_{timeframe}"] = df
                    print(f"   ✓ {symbol} {timeframe}: {len(df)} candles fetched")
                    
            except Exception as e:
                print(f"   ⚠️  {symbol} {timeframe}: {e}")
        
        return data_dict
    
    def _run_single_variant_backtest(self, scenario: Dict, data_dict: Dict) -> Dict:
        """Run backtest for single variant using pre-loaded data"""
        
        variant_id = scenario.get('id', 'Unknown')
        sl_mult = scenario.get('sl_multiplier', 1.0)
        tp_mult = scenario.get('tp_multiplier', 3.0)
        
        # Reset engine
        self.backtest_engine = BacktestEngine(self.initial_capital)
        
        # Get data for this scenario
        primary_tf = scenario.get('timeframe_primary', '3m')
        symbol = 'BTC/USDT'
        data_key = f"{symbol}_{primary_tf}"
        
        if data_key not in data_dict:
            return {
                'variant_id': variant_id,
                'sl_multiplier': sl_mult,
                'tp_multiplier': tp_mult,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_profit': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'status': 'NO_DATA'
            }
        
        df_primary = data_dict[data_key]
        
        # Build all data dict for scenario
        all_tf_data = {}
        for key, df in data_dict.items():
            if symbol in key:
                timeframe = key.split('_')[-1]
                if symbol not in all_tf_data:
                    all_tf_data[symbol] = {}
                all_tf_data[symbol][timeframe] = df
        
        # Calculate indicators for primary timeframe
        df_primary = self.indicators.calculate_all_indicators(
            df_primary,
            scenario.get('indicators', [])
        )
        
        # Simulate backtesting
        trades = []
        for idx, candle_row in df_primary.iterrows():
            candle = candle_row.to_dict()
            candle['_current_time'] = idx
            candle['_symbol'] = symbol
            candle['_all_data'] = all_tf_data
            
            # Evaluate entry conditions
            entry_signal = self._evaluate_entry(scenario, candle)
            
            if entry_signal:
                # Calculate position size
                price = candle.get('close', 0)
                atr = candle.get('ATR_14', 0)
                
                if price > 0 and atr > 0:
                    # SL and TP in dollars
                    sl_distance = atr * sl_mult
                    tp_distance = atr * tp_mult
                    
                    # Simple position sizing: risk 1% per trade
                    risk_amount = self.initial_capital * 0.01
                    qty = risk_amount / sl_distance if sl_distance > 0 else 0
                    
                    if qty > 0:
                        entry_price = price
                        sl_price = entry_price - sl_distance
                        tp_price = entry_price + tp_distance
                        
                        # Simulate trade outcome (simplified)
                        trade = self._simulate_trade_candle(
                            entry_price, sl_price, tp_price, qty, df_primary.loc[idx:].head(20)
                        )
                        if trade:
                            trades.append(trade)
        
        # Calculate metrics
        return self._calculate_metrics(variant_id, sl_mult, tp_mult, trades)
    
    def _evaluate_entry(self, scenario: Dict, candle: Dict) -> bool:
        """Simple entry evaluation"""
        
        conditions = scenario.get('entry', {}).get('conditions', [])
        
        for cond in conditions:
            if cond.get('indicator') == 'price':
                price = candle.get('close', 0)
                ref = cond.get('reference', '')
                ref_value = candle.get(ref, 0)
                comparison = cond.get('comparison', '>')
                
                buffer_pct = cond.get('buffer_pct', 0.0)
                ref_value_buffered = ref_value * (1 + buffer_pct)
                
                if comparison == '>' and price <= ref_value_buffered:
                    return False
                elif comparison == '<' and price >= ref_value_buffered:
                    return False
            
            elif cond.get('indicator') == 'RSI_14':
                rsi = candle.get('RSI_14', 50)
                value = cond.get('value', 50)
                comparison = cond.get('comparison', '>')
                
                if comparison == '>' and rsi <= value:
                    return False
                elif comparison == '<' and rsi >= value:
                    return False
        
        return True
    
    def _simulate_trade_candle(self, entry: float, sl: float, tp: float, qty: float, 
                              future_candles: pd.DataFrame) -> dict:
        """Simulate trade outcome looking forward"""
        
        for idx, candle in future_candles.iterrows():
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            
            # Check if TP hit first
            if high >= tp:
                pnl = (tp - entry) * qty
                return {'entry': entry, 'exit': tp, 'pnl': pnl, 'status': 'TP'}
            
            # Check if SL hit
            if low <= sl:
                pnl = (sl - entry) * qty
                return {'entry': entry, 'exit': sl, 'pnl': pnl, 'status': 'SL'}
        
        # If no exit within lookforward, close at current price (simplified)
        if len(future_candles) > 0:
            last_close = future_candles.iloc[-1].get('close', entry)
            pnl = (last_close - entry) * qty
            return {'entry': entry, 'exit': last_close, 'pnl': pnl, 'status': 'LOOKBACK_END'}
        
        return None
    
    def _calculate_metrics(self, variant_id: str, sl_mult: float, tp_mult: float, 
                          trades: List[Dict]) -> Dict:
        """Calculate backtest metrics from trades"""
        
        if not trades:
            return {
                'variant_id': variant_id,
                'sl_multiplier': sl_mult,
                'tp_multiplier': tp_mult,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_profit': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'status': 'NO_TRADES'
            }
        
        df_trades = pd.DataFrame(trades)
        
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl'] > 0])
        losing_trades = len(df_trades[df_trades['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_wins = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        total_losses = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else (1.0 if total_wins > 0 else 0)
        
        total_profit = df_trades['pnl'].sum()
        avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Status
        if profit_factor >= 1.2:
            status = 'PROFITABLE'
        elif profit_factor >= 1.0:
            status = 'ACCEPTABLE'
        else:
            status = 'UNPROFITABLE'
        
        return {
            'variant_id': variant_id,
            'sl_multiplier': sl_mult,
            'tp_multiplier': tp_mult,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'status': status
        }
    
    def _display_variant_results(self, metrics: Dict):
        """Display results for a single variant"""
        
        pf = metrics['profit_factor']
        status = metrics['status']
        
        emoji = "✅" if status == 'PROFITABLE' else "⚠️ " if status == 'ACCEPTABLE' else "❌"
        
        print(f"     {emoji} PF: {pf:.2f} | Trades: {metrics['total_trades']} | Win%: {metrics['win_rate']*100:.1f}% | P&L: ${metrics['total_profit']:,.0f}")
    
    def _analyze_results(self) -> Dict:
        """Analyze and report results"""
        
        if not self.results_summary:
            print("❌ No results to analyze")
            return {}
        
        df = pd.DataFrame(self.results_summary)
        df_sorted = df.sort_values('profit_factor', ascending=False)
        
        profitable = df_sorted[df_sorted['profit_factor'] >= 1.2]
        acceptable = df_sorted[(df_sorted['profit_factor'] >= 1.0) & (df_sorted['profit_factor'] < 1.2)]
        unprofitable = df_sorted[df_sorted['profit_factor'] < 1.0]
        
        print("\n" + "="*100)
        print(" "*30 + "OPTIMIZATION RESULTS SUMMARY")
        print("="*100)
        
        print(f"\n📊 Classification:")
        print(f"   ✅ PROFITABLE (PF >= 1.2):     {len(profitable):2d} variants")
        print(f"   ⚠️  ACCEPTABLE (1.0 <= PF < 1.2): {len(acceptable):2d} variants")
        print(f"   ❌ UNPROFITABLE (PF < 1.0):    {len(unprofitable):2d} variants")
        
        print(f"\n📈 All Results (sorted by Profit Factor):\n")
        
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            emoji = "✅" if row['status'] == 'PROFITABLE' else "⚠️ " if row['status'] == 'ACCEPTABLE' else "❌"
            print(f"{idx}. {emoji} {row['variant_id']:15s} | PF: {row['profit_factor']:5.2f} | "
                  f"Trades: {row['total_trades']:3d} | Win%: {row['win_rate']*100:5.1f}% | "
                  f"P&L: ${row['total_profit']:10,.0f}")
        
        if len(profitable) > 0:
            print(f"\n🎯 TOP PROFITABLE VARIANTS:")
            for idx, (_, row) in enumerate(profitable.head(3).iterrows(), 1):
                print(f"   {idx}. {row['variant_id']}")
                print(f"      ├─ R:R Ratio: {row['tp_multiplier']/row['sl_multiplier']:.2f}x")
                print(f"      ├─ Profit Factor: {row['profit_factor']:.2f}")
                print(f"      ├─ Win Rate: {row['win_rate']*100:.1f}%")
                print(f"      └─ Total P&L: ${row['total_profit']:,.0f}")
            
            print(f"\n✅ NEXT STEPS:")
            print(f"   1. Validate top variant with walk-forward testing")
            print(f"   2. Expand SL/TP range around top performers")
            print(f"   3. Consider portfolio combining multiple profitable variants")
        else:
            print(f"\n⚠️  No profitable variants found - requires further optimization")
            if len(acceptable) > 0:
                print(f"   • Best candidate: {acceptable.iloc[0]['variant_id']} (PF: {acceptable.iloc[0]['profit_factor']:.2f})")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"backtest_results/s001_fast_optimization_{timestamp}.csv"
        df_sorted.to_csv(csv_file, index=False)
        
        json_file = f"backtest_results/s001_fast_optimization_{timestamp}.json"
        results_dict = {
            'timestamp': datetime.now().isoformat(),
            'profitable': profitable.to_dict(orient='records'),
            'acceptable': acceptable.to_dict(orient='records'),
            'unprofitable': unprofitable.to_dict(orient='records'),
            'summary': {
                'total_variants': len(df),
                'profitable_count': len(profitable),
                'acceptable_count': len(acceptable),
                'unprofitable_count': len(unprofitable)
            }
        }
        
        with open(json_file, 'w') as f:
            json.dump(results_dict, f, indent=2, default=str)
        
        print(f"\n📁 Results saved:")
        print(f"   • {csv_file}")
        print(f"   • {json_file}")
        print("\n" + "="*100 + "\n")
        
        return {
            'profitable_count': len(profitable),
            'results': df_sorted
        }


def main():
    try:
        optimizer = FastS001Optimizer(initial_capital=100000.0)
        results = optimizer.run_fast_optimization(lookback_days=90)
        
        if results and results.get('profitable_count', 0) > 0:
            print(f"✅ Found {results['profitable_count']} profitable variant(s)")
            sys.exit(0)
        else:
            print(f"⚠️  Optimization complete - review results for tuning")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ BUG: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

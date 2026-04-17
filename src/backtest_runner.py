# -*- coding: utf-8 -*-
"""
Main Backtest Execution Runner
Orchestrates the complete backtesting pipeline
"""

import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.backtest_data_engine import DataEngine
from src.backtest_indicators import IndicatorsEngine, MultiTimeframeIndicators
from src.backtest_scenario_parser import ScenarioParser
from src.condition_engine import ModularConditionEvaluator, ConditionRegistry
from src.backtest_engine import BacktestEngine, Trade


class BacktestRunner:
    """Complete backtesting pipeline orchestrator"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.data_engine = DataEngine()
        self.scenario_parser = None
        self.indicators = MultiTimeframeIndicators()
        self.backtest_engine = BacktestEngine(initial_capital)
        self.modular_evaluator = ModularConditionEvaluator(debug=False)
        
        self.results = {}  # {scenario_id: metrics}
        self.all_trades = []
    
    def _evaluate_conditions_hybrid(self, scenario, candle, data_dict):
        """
        Hybrid evaluator: supports both rule-based and modular formats
        REFACTORED: Removed alignment call (data already pre-aligned)
        """
        conditions = scenario.get_entry_conditions()
        
        if not conditions:
            return False
        
        # Check format
        first_condition = conditions[0]
        
        # Format 1: Rule-based (simplified strategies)
        if 'rule' in first_condition:
            from src.backtest_scenario_parser import ConditionEvaluator
            return ConditionEvaluator.evaluate_entry_conditions(scenario, candle, data_dict)
        
        # Format 2: Modular/indicator-based (structured strategies)
        # Data dict already has aligned values, no need to call alignment
        elif 'indicator' in first_condition:
            return self.modular_evaluator.evaluate_entry_conditions(scenario, candle, data_dict, debug=False)
        
        return False
    
    def _apply_timeframe_alignment(self, data_dict: Dict) -> Dict:
        """
        Apply timeframe alignment for multi-timeframe conditions.
        """
        if '_all_data' not in data_dict or '_current_time' not in data_dict:
            return data_dict
        
        all_data = data_dict.get('_all_data', {})
        current_time = data_dict.get('_current_time')
        symbol = data_dict.get('_symbol', '')
        
        if not all_data or not symbol or symbol not in all_data:
            return data_dict
        
        tf_dict = all_data[symbol]
        
        keys_added_count = 0
        # For each available timeframe, find and merge aligned higher TF data
        for tf_name, tf_data in tf_dict.items():
            if not isinstance(tf_data, pd.DataFrame):
                continue
            
            # Find the latest candle in this TF where timestamp <= current_time
            matching_rows = tf_data[tf_data.index <= current_time]
            if len(matching_rows) > 0:
                latest_row = matching_rows.iloc[-1]
                # Add all columns from this timeframe with TF suffix
                for col in latest_row.index:
                    if col not in ['open', 'high', 'low', 'close', 'volume']:
                        col_name = f"{col}_{tf_name}"
                        data_dict[col_name] = latest_row[col]
                        keys_added_count += 1
        
        return data_dict
    
    def run_full_backtest(self, symbols: List[str] = None, timeframes: List[str] = None, use_real_data: bool = True, scenarios_file: str = "scenarios/SCENARIOS_STRUCTURED.json", data: Dict = None) -> Dict:
        """
        Run complete backtest pipeline with REAL DATA ONLY
        
        Args:
            symbols: List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframes: List of timeframes (e.g., ['5m', '15m', '1h'])
            use_real_data: MUST be True - mock data not supported for this run
            scenarios_file: Path to scenarios JSON file (default: full 32 strategies)
            data: Optional pre-fetched data (if provided, skips data fetching step)
            
        Returns:
            Results dictionary with strategy metrics
        """
        
        if data is None and not use_real_data:
            raise Exception("[ERROR] Real data fetching is REQUIRED. Mock data not supported for this phase.")
        
        if symbols is None:
            symbols = ['BTC/USDT', 'ETH/USDT']
        if timeframes is None:
            # ALL 32 strategies require these timeframes (S017 needs Weekly but not API-compatible)
            timeframes = ['1m', '3m', '4h', '5m', '15m', '1h']
        
        print("\n" + "="*70)
        print("INSTITUTIONAL BACKTEST ENGINE - FULL STRATEGY VALIDATION")
        print("="*70)
        
        # Step 1: Fetch real market data (or use pre-fetched data)
        if data is None:
            print("\n[STEP 1/7] Fetching MAXIMUM available historical data from exchange...")
            try:
                data = self.data_engine.get_all_data(symbols, timeframes, force_real_data=True)
            except Exception as e:
                print(f"\n[FATAL] Cannot proceed without market data: {e}")
                return None
        else:
            print("\n[STEP 1/7] Using pre-fetched data...")
        
        # Sync multi-timeframe data
        print("\n[STEP 1b/7] Syncing multi-timeframe data...")
        data = self.data_engine.sync_multiframe_data(data)
        
        if not data or not data.get(symbols[0]):
            print("[ERROR] No data available after syncing")
            return None
        
        # Print data summary
        print("\n" + "="*70)
        print("DATA SUMMARY")
        print("="*70)
        print(self.data_engine.get_data_info(data))
        
        # Step 2: Calculate indicators
        print("\n[STEP 2/7] Calculating technical indicators...")
        self._calculate_indicators(data)
        self.indicators.print_summary()
        
        # Step 2b: PRE-COMPUTE ALIGNED MULTI-TIMEFRAME DATA (ARCHITECTURAL FIX)
        print("\n[STEP 2b/7] Pre-computing aligned multi-timeframe data...")
        self._precompute_aligned_data()
        
        # Step 3: Load scenarios (use full 32-strategy set with modular engine)
        print("\n[STEP 3/7] Loading trading scenarios...")
        print("[INFO] Using Tier 1+2 modular condition engine")
        print("[REGISTERED CONDITIONS]", len(ConditionRegistry.REGISTRY), "handlers available")
        # Use the scenarios_file parameter (default is SCENARIOS_STRUCTURED.json)
        print(f"[SCENARIOS] Loading from: {scenarios_file}")
        self.scenario_parser = ScenarioParser(scenarios_file=scenarios_file)
        self.scenario_parser.print_summary()
        
        # Step 4: Run backtest for each scenario
        print("\n[STEP 4/7] Running backtest simulations...")
        self._run_scenario_backtests(data)
        
        # Step 5: Calculate metrics
        print("\n[STEP 5/7] Computing performance metrics...")
        results = self._calculate_metrics()
        
        # Step 6: Filter and rank
        print("\n[STEP 6/7] Filtering and ranking strategies...")
        filtered_results = self._filter_strategies(results)
        
        # Step 7: Export results
        print("\n[STEP 7/7] Exporting results...")
        self.export_results('backtest_results')
        
        return filtered_results
    
    def _calculate_indicators(self, data: Dict):
        """Calculate all indicators for data"""
        for symbol, timeframes_data in data.items():
            for timeframe, df in timeframes_data.items():
                # Skip if no data
                if len(df) < 200:
                    print(f"[WARNING] Insufficient data for {symbol} {timeframe} ({len(df)} candles)")
                    continue
                
                # Calculate indicators
                df_with_indicators = IndicatorsEngine.calculate_all_indicators(df)
                self.indicators.add_timeframe_indicators(symbol, timeframe, df_with_indicators)
    
    def _precompute_aligned_data(self):
        """
        ARCHITECTURAL FIX: Pre-compute all aligned multi-timeframe data ONCE
        OPTIMIZED: Uses pandas operations instead of loops
        """
        print("\n[PRECOMPUTE] Building pre-aligned multi-timeframe datasets...")
        self.aligned_data = {}
        
        for symbol in self.indicators.data:
            # Use 5m as base timeframe
            if '5m' not in self.indicators.data[symbol]:
                print(f"  [SKIP] {symbol}: no 5m data")
                continue
            
            df_base = self.indicators.get(symbol, '5m').copy()
            print(f"\n  [{symbol}] Base: 5m ({len(df_base)} candles)")
            
            # Attach higher-timeframe values using pandas reindex + forward fill
            for tf in ['3m', '15m', '1h', '4h']:
                if tf not in self.indicators.data[symbol]:
                    continue
                
                df_tf = self.indicators.get(symbol, tf)
                
                # For each indicator column, attach with TF suffix
                for col in df_tf.columns:
                    if col not in ['open', 'high', 'low', 'close', 'volume']:
                        aligned_col = f"{col}_{tf}"
                        # Reindex tf data to base index and forward fill
                        col_reindexed = df_tf[col].reindex(df_base.index, method='ffill')
                        df_base[aligned_col] = col_reindexed
                
                cols_added = len([c for c in df_base.columns if f'_{tf}' in c])
                print(f"     + {tf}: added {cols_added} aligned columns")
            
            # Drop rows with NaN (warmup period)
            df_base = df_base.dropna(how='any')
            self.aligned_data[symbol] = df_base
            print(f"    → Final: {len(df_base)} candles with all TFs aligned")
        
        print(f"\n  Pre-alignment complete: {len(self.aligned_data)} symbols ready\n")
    
    def _run_scenario_backtests(self, data: Dict):
        """Run backtest for each scenario using pre-aligned data"""
        scenarios = self.scenario_parser.get_all_scenarios()
        
        print(f"\nRunning backtest for {len(scenarios)} scenarios...")
        print("-" * 70)
        
        for idx, scenario in enumerate(scenarios):
            print(f"\n[{idx+1}/{len(scenarios)}] {scenario.id}: {scenario.name}")
            
            # Get appropriate data with fallback
            symbol = scenario.asset_pairs[0]  # Use first asset pair
            
            # Use pre-aligned data (has all TFs already attached)
            if symbol not in self.aligned_data:
                print(f"  [WARNING] No aligned data for {symbol}, skipping")
                self.results[scenario.id] = {'total_trades': 0}
                continue
            
            df = self.aligned_data[symbol]
            
            if df is None or len(df) < 200:
                print(f"  [WARNING] Insufficient data, skipping (need {symbol} with >=200 data points)")
                self.results[scenario.id] = {'total_trades': 0}
                continue
            
            # Run scenario backtest
            scenario_engine = BacktestEngine(self.initial_capital)
            trades_count = self._simulate_scenario(scenario, df, scenario_engine)
            
            # Store individual results
            metrics = scenario_engine.get_backtest_metrics()
            metrics['scenario_id'] = scenario.id
            metrics['scenario_name'] = scenario.name
            self.results[scenario.id] = metrics
            
            self.all_trades.extend(scenario_engine.trades)
            
            # Print summary
            if metrics['total_trades'] > 0:
                print(f"  Trades: {metrics['total_trades']} | "
                      f"Win Rate: {metrics['win_rate']:.1%} | "
                      f"Profit Factor: {metrics['profit_factor']:.2f}x | "
                      f"Max DD: {metrics['max_drawdown']:.1%}")
            else:
                print(f"  No trades generated")
    
    def _simulate_scenario(self, scenario, df: pd.DataFrame, engine: BacktestEngine) -> int:
        """
        REFACTORED: Simulate scenario on pre-aligned data
        No per-candle alignment calls (already done in precompute)
        """
        trade_count = 0
        daily_loss = 0.0
        max_daily_loss = engine.daily_loss_limit  # 3% daily loss limit
        
        # Only backtest if we have enough data
        if len(df) < 200:
            return 0
        
        symbol = scenario.asset_pairs[0] if scenario.asset_pairs else 'BTC/USDT'
        
        # DEBUG: Track progress
        total_candles = len(df)
        checkpoints = [200, 1000, 5000, 10000, 50000, 100000, 150000, total_candles]
        last_checkpoint = 200
        print(f"    [BACKTEST] Starting simulation of {total_candles} candles", flush=True)
        
        # DEBUG: Instrument execution layer
        eval_true_count = 0
        create_trade_called = 0
        create_trade_returned_none = 0
        create_trade_success = 0
        sl_calc_failed = 0
        
        # Loop through candles
        for idx in range(200, len(df)):
            candle = df.iloc[idx]
            prev_candle = df.iloc[idx-1]
            
            # DEBUG: Progress check
            if idx in checkpoints:
                print(f"    [BACKTEST] Processed {idx} candles, trades so far: {trade_count}", flush=True)
            
            # Skip if missing key data
            if pd.isna(candle['close']) or pd.isna(candle['ATR_14']):
                continue
            
            # EQUITY PROTECTION: Stop trading if account blown
            if engine.capital <= 0:
                break
            
            # RISK PROTECTION: Stop if daily loss exceeded (3% limit)
            if daily_loss < -max_daily_loss:
                break
            
            # CONCURRENT TRADES PROTECTION: Don't open more than 4 trades
            open_count = len(engine.open_trades)
            if open_count >= engine.max_concurrent_trades:
                continue
            
            # ARCHITECTURAL FIX: Data dict now uses pre-aligned values directly
            # No per-candle alignment call needed
            data_dict = candle.to_dict()
            data_dict['_symbol'] = symbol
            data_dict['_current_time'] = candle.name
            
            try:
                # Evaluate conditions - values like EMA_200_3m, RSI_14_1h already in data_dict
                condition_result = self._evaluate_conditions_hybrid(scenario, candle, data_dict)
                if condition_result:
                    eval_true_count += 1
                
                if condition_result:
                    # DYNAMIC POSITION SIZING (NO notional cap)
                    # Position size = Risk Amount / (Entry Price - Stop Loss)
                    entry_price = candle['close']
                    stop_loss = engine.evaluate_sl_formula(scenario.get_stop_loss_formula(), entry_price, candle['ATR_14'])
                    
                    # Calculate position with NO arbitrary cap
                    raw_position_size = engine.calculate_position_size(entry_price, stop_loss)
                    
                    # Only skip if SL calculation failed
                    if raw_position_size <= 0:
                        sl_calc_failed += 1
                        continue
                    
                    # Create trade with dynamic position sizing
                    create_trade_called += 1
                    trade = engine.create_trade(
                        scenario,
                        entry_price=entry_price,
                        entry_time=candle.name,
                        atr=candle['ATR_14'],
                        symbol=scenario.asset_pairs[0],
                        candle_data=candle
                    )
                    
                    if trade is not None:
                        create_trade_success += 1
                        trade_count += 1
                        engine.open_trades[trade.trade_id] = trade
                        
                        # SIMPLIFIED EXIT: Basic ATR-based SL/TP
                        # SL = entry - (ATR * 1.5)
                        # TP = entry + (ATR * 2.5)
                        # No trailing, no partial, no breakeven
                        simple_sl = entry_price - (candle['ATR_14'] * 1.5)
                        simple_tp = entry_price + (candle['ATR_14'] * 2.5)
                        
                        # Look for exit in next candles
                        for exit_idx in range(idx+1, min(idx+50, len(df))):  # Max 50 candles hold
                            exit_candle = df.iloc[exit_idx]
                            
                            # Check SL hit (loss)
                            if exit_candle['low'] <= simple_sl:
                                pre_close_capital = engine.capital
                                engine.close_trade(trade, simple_sl, exit_candle.name, 'Stop Loss')
                                daily_loss += (engine.capital - pre_close_capital)
                                if trade.trade_id in engine.open_trades:
                                    del engine.open_trades[trade.trade_id]
                                break
                            
                            # Check TP hit (win)
                            if exit_candle['high'] >= simple_tp:
                                pre_close_capital = engine.capital
                                engine.close_trade(trade, simple_tp, exit_candle.name, 'Take Profit')
                                daily_loss += (engine.capital - pre_close_capital)
                                if trade.trade_id in engine.open_trades:
                                    del engine.open_trades[trade.trade_id]
                                break
                        
                        else:
                            # Exit if reached max hold (50 candles)
                            exit_candle = df.iloc[min(idx+50, len(df)-1)]
                            pre_close_capital = engine.capital
                            engine.close_trade(trade, exit_candle['close'], exit_candle.name, 'Time Exit')
                            daily_loss += (engine.capital - pre_close_capital)
                            if trade.trade_id in engine.open_trades:
                                del engine.open_trades[trade.trade_id]
                    else:
                        # Trade creation returned None
                        create_trade_returned_none += 1
            
            except Exception as e:
                # Skip on evaluation error
                pass
        
        # DEBUG: Print execution layer trace
        print(f"\n    [EXECUTION TRACE]")
        print(f"      Evaluator TRUE: {eval_true_count}")
        print(f"      SL calc failed: {sl_calc_failed}")
        print(f"      Trade creation called: {create_trade_called}")
        print(f"      Trade creation success: {create_trade_success}")
        print(f"      Trade creation returned None: {create_trade_called - create_trade_success}")
        print(f"      Final trade count: {trade_count}\n")
        
        return trade_count
    
    def _calculate_metrics(self) -> Dict:
        """Calculate filtered metrics"""
        return self.results.copy()
    
    def _filter_strategies(self, results: Dict) -> Dict:
        """Filter strategies by Phase 4 criteria"""
        
        filtered = {}
        
        for scenario_id, metrics in results.items():
            # Skip scenarios with no trades
            if metrics.get('total_trades', 0) == 0:
                continue
            
            # Apply filters
            win_rate = metrics.get('win_rate', 0)
            profit_factor = metrics.get('profit_factor', 0)
            max_dd = metrics.get('max_drawdown', 0)
            
            # Phase 4 criteria
            if win_rate >= 0.42 and profit_factor >= 1.4 and max_dd <= 0.08:
                filtered[scenario_id] = metrics
        
        # Sort by Sharpe ratio
        sorted_results = sorted(
            filtered.items(),
            key=lambda x: x[1].get('sharpe_ratio', 0),
            reverse=True
        )
        
        return dict(sorted_results)
    
    def print_results_summary(self, results: Dict):
        """Print results summary"""
        print("\n" + "="*70)
        print("BACKTEST RESULTS SUMMARY")
        print("="*70)
        
        if not results:
            print("\n[WARNING] No strategies passed Phase 4 filters")
            print("   (Win Rate >= 42%, Profit Factor >= 1.4, Max DD <= 8%)")
            return
        
        print(f"\n[OK] {len(results)} strategies passed Phase 4 filters\n")
        print("-" * 70)
        print(f"{'Rank':<5} {'Scenario':<8} {'Trades':<8} {'Win %':<8} {'PF':<8} {'Sharpe':<10} {'DD %':<8}")
        print("-" * 70)
        
        for rank, (scenario_id, metrics) in enumerate(results.items(), 1):
            print(f"{rank:<5} {scenario_id:<8} "
                  f"{metrics.get('total_trades', 0):<8} "
                  f"{metrics.get('win_rate', 0)*100:>6.1f}% "
                  f"{metrics.get('profit_factor', 0):>6.2f}x "
                  f"{metrics.get('sharpe_ratio', 0):>8.2f} "
                  f"{metrics.get('max_drawdown', 0)*100:>6.1f}%")
        
        print("-" * 70)
    
    def export_results(self, output_dir: str = "backtest_results"):
        """Export results to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Export filtered results
        with open(os.path.join(output_dir, 'filtered_results.json'), 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Export all trades
        if self.all_trades:
            trades_df = pd.DataFrame([t.to_dict() for t in self.all_trades])
            trades_df.to_csv(os.path.join(output_dir, 'all_trades.csv'), index=False)
        
        print(f"\n[OK] Results exported to {output_dir}/")


def main():
    """Main execution - REAL DATA BACKTEST ONLY"""
    
    # Run backtest with REAL DATA
    runner = BacktestRunner(initial_capital=100000.0)
    
    try:
        print("\n" + "="*70)
        print("[START] STARTING PHASE 5: REAL DATA BACKTESTING")
        print("="*70)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Capital: $100,000")
        print(f"Strategies: 32")
        print("="*70 + "\n")
        
        start_time = datetime.now()
        
        results = runner.run_full_backtest(
            symbols=['BTC/USDT', 'ETH/USDT'],
            timeframes=['5m', '15m', '1h'],
            use_real_data=True
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if results is None:
            print("\n[ERROR] Backtest failed to produce results")
            return {}
        
        # Print summary
        runner.print_results_summary(results)
        
        # Export results
        runner.export_results('backtest_results')
        
        print("\n" + "="*70)
        print(f"[SUCCESS] BACKTEST COMPLETE - {elapsed:.1f} seconds")
        print("="*70)
        
        return results
    
    except Exception as e:
        print(f"\n[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    from datetime import datetime
    results = main()

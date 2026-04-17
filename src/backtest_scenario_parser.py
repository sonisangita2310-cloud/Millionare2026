# -*- coding: utf-8 -*-
"""
Scenario Parser
Loads and validates trading scenarios from SCENARIOS_STRUCTURED.json
"""

import json
import os
from typing import Dict, List, Any, Callable
import pandas as pd
import numpy as np

class ScenarioCondition:
    """Represents a single entry condition"""
    
    def __init__(self, condition_dict: Dict):
        self.indicator = condition_dict.get('indicator')
        self.comparison = condition_dict.get('comparison')
        self.value = condition_dict.get('value')
        self.reference = condition_dict.get('reference')
        self.timeframe = condition_dict.get('timeframe', '1h')
        self.buffer_pct = condition_dict.get('buffer_pct', 0)
        self.definition = condition_dict.get('definition', '')
    
    def evaluate(self, current_price: float, reference_value: float, operator: str) -> bool:
        """Evaluate condition"""
        if operator == '>':
            return current_price > reference_value * (1 + self.buffer_pct)
        elif operator == '<':
            return current_price < reference_value * (1 - self.buffer_pct)
        elif operator == '>=':
            return current_price >= reference_value * (1 + self.buffer_pct)
        elif operator == '<=':
            return current_price <= reference_value * (1 - self.buffer_pct)
        elif operator == '==':
            tolerance = reference_value * 0.001  # 0.1% tolerance
            return abs(current_price - reference_value) < tolerance
        return False


class ScenarioParser:
    """Load and parse trading scenarios from JSON"""
    
    def __init__(self, scenarios_file: str = "scenarios/SCENARIOS_SIMPLIFIED.json"):
        self.scenarios_file = scenarios_file
        self.scenarios = []
        self.scenario_dict = {}
        self.load_scenarios()
    
    def load_scenarios(self):
        """Load scenarios from JSON file"""
        if not os.path.exists(self.scenarios_file):
            raise FileNotFoundError(f"Scenarios file not found: {self.scenarios_file}")
        
        with open(self.scenarios_file, 'r') as f:
            data = json.load(f)
        
        # Handle both direct scenario array and nested structure
        if isinstance(data, dict):
            scenarios_list = data.get('scenarios', [])
        else:
            scenarios_list = data
        
        print(f"\nLoading scenarios from {self.scenarios_file}")
        print(f"Found {len(scenarios_list)} scenarios")
        
        for scenario in scenarios_list:
            scenario_obj = Scenario(scenario)
            self.scenarios.append(scenario_obj)
            self.scenario_dict[scenario_obj.id] = scenario_obj
        
        print(f"[OK] Loaded {len(self.scenarios)} scenarios\n")
    
    def get_scenario(self, scenario_id: str) -> 'Scenario':
        """Get scenario by ID"""
        return self.scenario_dict.get(scenario_id)
    
    def get_all_scenarios(self) -> List['Scenario']:
        """Get all scenarios"""
        return self.scenarios
    
    def get_scenarios_by_category(self, category: str) -> List['Scenario']:
        """Filter scenarios by category"""
        return [s for s in self.scenarios if s.category == category]
    
    def validate_scenarios(self) -> bool:
        """Validate all scenarios are properly formatted"""
        invalid = []
        
        for scenario in self.scenarios:
            if not scenario.validate():
                invalid.append(scenario.id)
        
        if invalid:
            print(f"[WARNING] Invalid scenarios: {invalid}")
            return False
        
        print(f"[OK] All {len(self.scenarios)} scenarios validated")
        return True
    
    def print_summary(self):
        """Print summary of loaded scenarios"""
        print("\nSCENARIO SUMMARY:")
        print("-" * 60)
        
        categories = {}
        for scenario in self.scenarios:
            cat = scenario.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(scenario)
        
        for cat in sorted(categories.keys()):
            scenarios_in_cat = categories[cat]
            print(f"\nCategory {cat}: {len(scenarios_in_cat)} scenarios")
            for s in scenarios_in_cat:
                print(f"  {s.id}: {s.name} ({s.type})")
                print(f"    Win rate: {s.risk_parameters.get('expected_win_rate', 0):.1%}")
                print(f"    RR: {s.risk_parameters.get('expected_rr', 0):.1f}x")
                print(f"    Trades/month: {s.risk_parameters.get('trades_per_month', 0)}")
        
        print("-" * 60)


class Scenario:
    """Represents a single trading scenario"""
    
    def __init__(self, scenario_dict: Dict):
        self.raw = scenario_dict
        
        # Basic info
        self.id = scenario_dict.get('id', '')
        self.name = scenario_dict.get('name', '')
        self.category = scenario_dict.get('category', '')
        self.type = scenario_dict.get('type', 'LONG')  # LONG, SHORT, LONG_or_SHORT
        self.edge_type = scenario_dict.get('edge_type', '')
        
        # Timeframes
        self.timeframe_primary = scenario_dict.get('timeframe_primary', '1h')
        self.timeframes = scenario_dict.get('timeframes', ['1h'])
        
        # Entry conditions
        entry_data = scenario_dict.get('entry', {})
        self.entry_conditions_raw = entry_data.get('conditions', [])
        self.entry_confirmation = entry_data.get('confirmation', 'AND')
        
        # SL/TP
        self.stop_loss_formula = scenario_dict.get('stop_loss', {}).get('formula', '')
        self.take_profit_raw = scenario_dict.get('take_profit', [])
        
        # Trailing stop
        self.trailing_stop = scenario_dict.get('trailing_stop', {})
        
        # Exit conditions
        self.exit_conditions_raw = scenario_dict.get('exit_conditions', [])
        
        # Risk parameters
        self.risk_parameters = scenario_dict.get('risk_parameters', {})
        
        # Other
        self.session_filter = scenario_dict.get('session_filter', 'ALL')
        
        # Normalize asset pairs - accepts both BTC-USD and BTC/USDT formats
        raw_pairs = scenario_dict.get('asset_pairs', ['BTC/USDT', 'ETH/USDT'])
        self.asset_pairs = []
        for pair in raw_pairs:
            if pair.endswith("USDT"):
                # Already in correct format (BTC/USDT or BTC-USDT)
                normalized = pair.replace('-', '/')
            elif pair.endswith("USD"):
                # Convert USD to USDT format (BTC-USD → BTC/USDT)
                normalized = pair.replace('-', '/').replace("USD", "USDT")
            else:
                # Fallback: just normalize slashes
                normalized = pair.replace('-', '/')
            
            self.asset_pairs.append(normalized)
        
        self.notes = scenario_dict.get('notes', '')
    
    def validate(self) -> bool:
        """Validate scenario has required fields"""
        required = ['id', 'name', 'category', 'entry_conditions_raw']
        
        for field in required:
            if not getattr(self, field, None):
                print(f"  ✗ {self.id}: Missing {field}")
                return False
        
        return True
    
    def get_entry_conditions(self) -> List[Dict]:
        """Get entry conditions as list"""
        return self.entry_conditions_raw
    
    def get_stop_loss_formula(self) -> str:
        """Get SL formula string"""
        return self.stop_loss_formula
    
    def get_take_profit_targets(self) -> List[Dict]:
        """Get TP targets"""
        return self.take_profit_raw
    
    def get_exit_conditions(self) -> List[Dict]:
        """Get exit conditions"""
        return self.exit_conditions_raw
    
    def get_expected_win_rate(self) -> float:
        """Get expected win rate"""
        return float(self.risk_parameters.get('expected_win_rate', 0.50))
    
    def get_expected_rr(self) -> float:
        """Get expected risk-reward ratio"""
        return float(self.risk_parameters.get('expected_rr', 2.0))
    
    def get_max_dd_acceptable(self) -> float:
        """Get max drawdown acceptable"""
        return float(self.risk_parameters.get('max_dd_acceptable', 0.10))
    
    def get_risk_per_trade(self) -> float:
        """Get risk per trade as percentage"""
        return float(self.risk_parameters.get('risk_per_trade_pct', 0.015))
    
    def get_trades_per_month(self) -> int:
        """Get expected trades per month"""
        return int(self.risk_parameters.get('trades_per_month', 10))
    
    def __repr__(self):
        return f"Scenario({self.id}: {self.name})"


class ConditionEvaluator:
    """Evaluates entry conditions for trades using text-based rules"""
    
    @staticmethod
    def evaluate_entry_conditions(scenario: Scenario, current_candle: pd.Series, data_dict: Dict) -> bool:
        """
        Evaluate if all entry conditions are met
        
        Args:
            scenario: Scenario object
            current_candle: Current candle data
            data_dict: Dict with all values
            
        Returns:
            bool: True if all conditions are met
        """
        conditions = scenario.get_entry_conditions()
        
        if not conditions:
            return False
        
        # Combine all data into single dict for easy lookup
        values = dict(current_candle)
        values.update(data_dict)
        
        results = []
        
        for condition in conditions:
            rule = condition.get('rule', '')
            result = ConditionEvaluator._evaluate_rule(rule, values)
            results.append(result)
        
        # ALL conditions must be true (AND logic)
        return all(results)
    
    @staticmethod
    def _evaluate_rule(rule: str, values: Dict) -> bool:
        """
        Evaluate a text-based rule like "EMA_12_1h > EMA_21_1h"
        
        Args:
            rule: Text rule to evaluate
            values: Dict of all available values
            
        Returns:
            bool: Result of the rule evaluation
        """
        try:
            # Parse the rule
            for op in ['>=', '<=', '==', '>', '<']:
                if op in rule:
                    parts = rule.split(op)
                    if len(parts) != 2:
                        return False
                    
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Get values
                    left_val = ConditionEvaluator._get_value(left, values)
                    right_val = ConditionEvaluator._get_value(right, values)
                    
                    if left_val is None or right_val is None:
                        return False
                    
                    # Evaluate
                    if op == '>':
                        return float(left_val) > float(right_val)
                    elif op == '<':
                        return float(left_val) < float(right_val)
                    elif op == '>=':
                        return float(left_val) >= float(right_val)
                    elif op == '<=':
                        return float(left_val) <= float(right_val)
                    elif op == '==':
                        return abs(float(left_val) - float(right_val)) < 0.0001
            
            return False
        except Exception as e:
            return False
    
    @staticmethod
    def _get_value(key: str, values: Dict):
        """Get value from dict, handling special cases like 'close_1h' or 'EMA_12_1h'"""
        key = key.strip()
        
        # Direct lookup
        if key in values:
            val = values[key]
            if pd.isna(val):
                return None
            return val
        
        # If key has timeframe suffix (_1h, _15m, _5m, _3m), try without it
        for tf_suffix in ['_1h', '_15m', '_5m', '_3m']:
            if key.endswith(tf_suffix):
                key_without_tf = key[:-len(tf_suffix)]
                if key_without_tf in values:
                    val = values[key_without_tf]
                    if pd.isna(val):
                        return None
                    return val
        
        # Try numeric value
        try:
            return float(key)
        except:
            pass
        
        return None
        
        return None
    
    @staticmethod
    def evaluate_exit_condition(exit_cond: Dict, values: Dict) -> bool:
        """Evaluate exit rule"""
        rule = exit_cond.get('rule', '')
        return ConditionEvaluator._evaluate_rule(rule, values)

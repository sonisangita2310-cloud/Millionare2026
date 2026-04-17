# -*- coding: utf-8 -*-
"""
MODULAR CONDITION ENGINE FRAMEWORK
Scalable, extensible architecture for strategy condition evaluation

Each condition type is an independent, testable function.
Registry pattern ensures clean separation of concerns.
"""

import pandas as pd
import numpy as np
from typing import Dict, Callable, Any, List


class ConditionHandler:
    """
    Individual condition evaluators registered in the engine.
    Each handler is pure and independent.
    """
    
    @staticmethod
    def evaluate_price_comparison(data: Dict, params: Dict) -> bool:
        """
        Simple price vs reference comparison
        Example: price > EMA_200 (with optional buffer)
        """
        price = data.get('close', 0)
        reference_name = params.get('reference', '')
        comparison = params.get('comparison', '>')
        buffer_pct = params.get('buffer_pct', 0)
        
        reference = data.get(reference_name, 0)
        if reference == 0 or pd.isna(reference):
            return False
        
        reference_adjusted = reference * (1 + buffer_pct)
        
        if comparison == '>':
            return price > reference_adjusted
        elif comparison == '>=':
            return price >= reference_adjusted
        elif comparison == '<':
            return price < reference_adjusted * (1 - buffer_pct / (1 + buffer_pct))
        elif comparison == '<=':
            return price <= reference_adjusted
        return False
    
    @staticmethod
    def evaluate_indicator_threshold(data: Dict, params: Dict) -> bool:
        """
        Indicator vs threshold comparison (RSI, ADX, etc.)
        Example: RSI_14 > 50
        """
        indicator_name = params.get('indicator', '')
        value = params.get('value', 0)
        comparison = params.get('comparison', '>')
        
        indicator_value = data.get(indicator_name, None)
        if indicator_value is None or pd.isna(indicator_value):
            return False
        
        if comparison == '>':
            return indicator_value > value
        elif comparison == '>=':
            return indicator_value >= value
        elif comparison == '<':
            return indicator_value < value
        elif comparison == '<=':
            return indicator_value <= value
        elif comparison == '==':
            return abs(indicator_value - value) < 0.01
        return False
    
    @staticmethod
    def evaluate_candle_body_ratio(data: Dict, params: Dict) -> bool:
        """
        Candle body size relative to total range
        body_ratio = abs(close - open) / (high - low)
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        high = data.get('high', 0)
        low = data.get('low', 0)
        threshold = params.get('value', 0.5)
        comparison = params.get('comparison', '>')
        
        range_size = high - low
        if range_size <= 0 or pd.isna(range_size):
            return False
        
        body_size = abs(close - open_price)
        body_ratio = body_size / range_size
        
        if comparison == '>':
            return body_ratio > threshold
        elif comparison == '<':
            return body_ratio < threshold
        elif comparison == '>=':
            return body_ratio >= threshold
        elif comparison == '<=':
            return body_ratio <= threshold
        return False
    
    @staticmethod
    def evaluate_bullish_candle(data: Dict, params: Dict) -> bool:
        """
        Bullish candle: close > open
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        return close > open_price
    
    @staticmethod
    def evaluate_bearish_candle(data: Dict, params: Dict) -> bool:
        """
        Bearish candle: close < open
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        return close < open_price
    
    @staticmethod
    def evaluate_ema_stack(data: Dict, params: Dict) -> bool:
        """
        Bullish EMA stack: EMA_12 > EMA_21 > EMA_50 > EMA_200
        """
        ema_12 = data.get('EMA_12', 0)
        ema_21 = data.get('EMA_21', 0)
        ema_50 = data.get('SMA_50', data.get('EMA_50', 0))
        ema_200 = data.get('SMA_200', data.get('EMA_200', 0))
        
        if any(pd.isna(x) or x == 0 for x in [ema_12, ema_21, ema_50, ema_200]):
            return False
        
        return ema_12 > ema_21 > ema_50 > ema_200
    
    @staticmethod
    def evaluate_bearish_ema_stack(data: Dict, params: Dict) -> bool:
        """
        Bearish EMA stack: EMA_12 < EMA_21 < EMA_50 < EMA_200
        """
        ema_12 = data.get('EMA_12', 0)
        ema_21 = data.get('EMA_21', 0)
        ema_50 = data.get('SMA_50', data.get('EMA_50', 0))
        ema_200 = data.get('SMA_200', data.get('EMA_200', 0))
        
        if any(pd.isna(x) or x == 0 for x in [ema_12, ema_21, ema_50, ema_200]):
            return False
        
        return ema_12 < ema_21 < ema_50 < ema_200
    
    @staticmethod
    def evaluate_volume_spike(data: Dict, params: Dict) -> bool:
        """
        Volume > average volume * multiplier
        """
        volume = data.get('volume', 0)
        volume_sma = data.get('VOLUME_SMA_20', 0)
        multiplier = params.get('value', 1.5)
        
        if volume_sma is None or pd.isna(volume_sma) or volume_sma == 0:
            return False
        
        return volume > volume_sma * multiplier
    
    @staticmethod
    def evaluate_breakout(data: Dict, params: Dict) -> bool:
        """
        Price breaks above 20-period high
        """
        high_20 = data.get('HIGH_20', 0)
        close = data.get('close', 0)
        
        if high_20 is None or pd.isna(high_20) or high_20 == 0:
            return False
        
        return close > high_20
    
    @staticmethod
    def evaluate_breakdown(data: Dict, params: Dict) -> bool:
        """
        Price breaks below 20-period low
        """
        low_20 = data.get('LOW_20', 0)
        close = data.get('close', 0)
        
        if low_20 is None or pd.isna(low_20) or low_20 == 0:
            return False
        
        return close < low_20
    
    @staticmethod
    def evaluate_bollinger_squeeze(data: Dict, params: Dict) -> bool:
        """
        Bollinger Band width is contracting (squeeze)
        BB_WIDTH = (BB_UPPER - BB_LOWER) / SMA_20
        """
        bb_upper = data.get('BB_UPPER_20_2', 0)
        bb_lower = data.get('BB_LOWER_20_2', 0)
        sma_20 = data.get('SMA_20', 0)
        squeeze_ratio = params.get('value', 0.05)
        
        if any(pd.isna(x) or x == 0 for x in [bb_upper, bb_lower, sma_20]):
            return False
        
        width = (bb_upper - bb_lower) / sma_20
        return width < squeeze_ratio
    
    @staticmethod
    def evaluate_adx_rising(data: Dict, params: Dict) -> bool:
        """
        ADX is above threshold (trending market)
        """
        adx = data.get('ADX_14', 0)
        threshold = params.get('value', 25)
        
        if adx is None or pd.isna(adx):
            return False
        
        return adx > threshold
    
    @staticmethod
    def evaluate_atr_expansion(data: Dict, params: Dict) -> bool:
        """
        ATR is expanding (volatility is low/expanding)
        Used for identifying low volatility conditions
        """
        atr = data.get('ATR_14', 0)
        threshold = params.get('value', 100)
        comparison = params.get('comparison', '<')
        
        if atr is None or pd.isna(atr):
            return False
        
        if comparison == '<':
            return atr < threshold
        elif comparison == '<=':
            return atr <= threshold
        elif comparison == '>':
            return atr > threshold
        elif comparison == '>=':
            return atr >= threshold
        return False
    
    @staticmethod
    def evaluate_engulfing_bullish(data: Dict, params: Dict) -> bool:
        """
        Bullish engulfing: current close > prior open AND current open < prior close
        Requires previous candle data in dict
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        prior_close = data.get('prior_close', 0)
        prior_open = data.get('prior_open', 0)
        
        if any(x == 0 or pd.isna(x) for x in [close, open_price, prior_close, prior_open]):
            return False
        
        # Current candle body must engulf prior candle body
        return close > prior_open and open_price < prior_close
    
    @staticmethod
    def evaluate_engulfing_bearish(data: Dict, params: Dict) -> bool:
        """
        Bearish engulfing: current close < prior open AND current open > prior close
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        prior_close = data.get('prior_close', 0)
        prior_open = data.get('prior_open', 0)
        
        if any(x == 0 or pd.isna(x) for x in [close, open_price, prior_close, prior_open]):
            return False
        
        return close < prior_open and open_price > prior_close
    
    @staticmethod
    def evaluate_doji(data: Dict, params: Dict) -> bool:
        """
        DOJI: open ≈ close (within 0.1% of candle range)
        """
        close = data.get('close', 0)
        open_price = data.get('open', 0)
        high = data.get('high', 0)
        low = data.get('low', 0)
        
        range_size = high - low
        if range_size <= 0 or pd.isna(range_size):
            return False
        
        body = abs(close - open_price)
        body_ratio = body / range_size
        
        # DOJI = body < 1% of range
        return body_ratio < 0.01


class ConditionRegistry:
    """
    Central registry of all condition handlers.
    Maps condition type names to their evaluation functions.
    
    PRIORITY IMPLEMENTATION (Tier 1 + 2 only):
    - Tier 1: EMA/SMA, RSI, ATR, Candle Body Ratio
    - Tier 2: Engulfing, Doji, Breakout
    """
    
    REGISTRY: Dict[str, Callable] = {
        # TIER 1 - CORE CONDITIONS
        # ========================
        # Price vs Moving Average
        'price': ConditionHandler.evaluate_price_comparison,
        'price_1h': ConditionHandler.evaluate_price_comparison,
        'price_pullback': ConditionHandler.evaluate_price_comparison,
        
        # Indicator Thresholds (RSI, ADX, MACD)
        'RSI_14': ConditionHandler.evaluate_indicator_threshold,
        'ADX_14': ConditionHandler.evaluate_indicator_threshold,
        'MACD': ConditionHandler.evaluate_indicator_threshold,
        'indicator': ConditionHandler.evaluate_indicator_threshold,
        
        # Candle Patterns
        'candle_body_ratio': ConditionHandler.evaluate_candle_body_ratio,
        'candle_bullish': ConditionHandler.evaluate_bullish_candle,
        'candle_bearish': ConditionHandler.evaluate_bearish_candle,
        
        # Multi-candle Patterns
        'EMA_stack': ConditionHandler.evaluate_ema_stack,
        'EMA_fan': ConditionHandler.evaluate_ema_stack,
        'EMA_stack_break': ConditionHandler.evaluate_ema_stack,
        'downtrend': ConditionHandler.evaluate_bearish_ema_stack,
        
        # ATR (Volatility)
        'ATR_low': ConditionHandler.evaluate_atr_expansion,
        'ADX_rising': ConditionHandler.evaluate_adx_rising,
        
        # TIER 2 - HIGH VALUE CONDITIONS
        # ===============================
        # Engulfing Patterns
        'candle_bullish_engulfing': ConditionHandler.evaluate_engulfing_bullish,
        'candle_bearish_engulfing': ConditionHandler.evaluate_engulfing_bearish,
        'engulfing': ConditionHandler.evaluate_engulfing_bullish,
        'engulfing_bullish': ConditionHandler.evaluate_engulfing_bullish,
        'engulfing_bearish': ConditionHandler.evaluate_engulfing_bearish,
        
        # Doji Pattern
        'doji': ConditionHandler.evaluate_doji,
        'doji_pattern': ConditionHandler.evaluate_doji,
        
        # Breakout/Breakdown
        'breakout': ConditionHandler.evaluate_breakout,
        'breakout_candle': ConditionHandler.evaluate_breakout,
        'range_high': ConditionHandler.evaluate_breakout,
        'breakdown': ConditionHandler.evaluate_breakdown,
        'range_low': ConditionHandler.evaluate_breakdown,
        
        # Volume
        'volume_spike': ConditionHandler.evaluate_volume_spike,
        
        # Volatility
        'bollinger_squeeze': ConditionHandler.evaluate_bollinger_squeeze,
    }
    
    @classmethod
    def get_handler(cls, condition_type: str) -> Callable:
        """Get handler for condition type"""
        return cls.REGISTRY.get(condition_type)
    
    @classmethod
    def register_condition(cls, name: str, handler: Callable):
        """Register custom condition handler"""
        cls.REGISTRY[name] = handler
    
    @classmethod
    def is_registered(cls, condition_type: str) -> bool:
        """Check if condition is registered"""
        return condition_type in cls.REGISTRY


class ModularConditionEvaluator:
    """
    Main evaluator using the condition registry.
    Pure, functional design.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.last_evaluation = {}
    
    def evaluate_condition(self, condition: Dict, data: Dict) -> bool:
        """
        Evaluate a single condition
        Returns True if condition passes, False otherwise
        """
        condition_type = condition.get('indicator', '')
        
        # Get handler from registry
        handler = ConditionRegistry.get_handler(condition_type)
        
        if handler is None:
            if self.debug:
                print(f"[WARNING] No handler for condition type: {condition_type}")
            return False
        
        try:
            result = handler(data, condition)
            
            if self.debug:
                print(f"  Condition '{condition_type}': {result}")
                self.last_evaluation[condition_type] = {
                    'result': result,
                    'data_available': len([k for k, v in data.items() if not pd.isna(v)])
                }
            
            return result
        except Exception as e:
            if self.debug:
                print(f"  [ERROR] Condition '{condition_type}': {e}")
            return False
    
    def evaluate_entry_conditions(self, scenario, candle_data: pd.Series, data_dict: Dict, debug: bool = False) -> bool:
        """
        Evaluate all entry conditions for a scenario.
        Returns True only if all conditions pass (AND logic).
        """
        self.debug = debug
        self.last_evaluation = {}
        
        entry_conditions = scenario.get_entry_conditions()
        
        if self.debug:
            print(f"\n[EVALUATING] {scenario.id}")
            print(f"  Conditions: {len(entry_conditions)}")
        
        # All conditions must be true (AND logic)
        for condition in entry_conditions:
            if not self.evaluate_condition(condition, data_dict):
                return False
        
        if self.debug:
            print(f"  [RESULT] All conditions passed ✅")
        
        return True
    
    def print_condition_summary(self):
        """Print summary of last evaluation"""
        if not self.last_evaluation:
            return
        
        print("\nCondition Evaluation Summary:")
        for condition_type, details in self.last_evaluation.items():
            status = "✅" if details['result'] else "❌"
            print(f"  {status} {condition_type}")

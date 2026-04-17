"""
Configuration management for Millionaire 2026
"""

import json
import os
from typing import Dict, Any


class Config:
    """Configuration handler"""
    
    # Trading Configuration
    TRADING = {
        'initial_capital': 100000,
        'max_position_size': 0.3,
        'max_leverage': 1.0,
        'default_timeframe': '1h',
    }
    
    # Strategy Configuration
    STRATEGIES = {
        'momentum': {
            'lookback_period': 20,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'enabled': True,
        },
        'mean_reversion': {
            'lookback_period': 20,
            'z_score_threshold': 2.0,
            'enabled': True,
        },
        'arbitrage': {
            'min_spread_pct': 0.5,
            'enabled': True,
        }
    }
    
    # Risk Management Configuration
    RISK_MANAGEMENT = {
        'max_daily_loss_pct': 0.05,
        'max_position_loss_pct': 0.02,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.05,
    }
    
    # Market Data Configuration
    MARKET_DATA = {
        'assets': ['bitcoin', 'ethereum'],
        'data_source': 'coingecko',
        'update_frequency': 3600,  # seconds
        'lookback_days': 365,
    }
    
    # API Configuration
    API = {
        'exchange': 'coinbase',
        'mcf_server': 'http://localhost:8000',
        'timeout': 30,
    }
    
    # Backtesting Configuration
    BACKTESTING = {
        'scenarios': ['A', 'B', 'C', 'D', 'E'],
        'initial_capital': 100000,
        'commission': 0.001,  # 0.1%
    }
    
    # Output Configuration
    OUTPUT = {
        'log_file': 'millionaire_2026.log',
        'report_format': 'detailed',
        'report_frequency': 'daily',
    }
    
    @staticmethod
    def load_from_file(filepath: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_to_file(config: Dict[str, Any], filepath: str):
        """Save configuration to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
    
    @staticmethod
    def get_strategy_config(strategy_name: str) -> Dict[str, Any]:
        """Get configuration for specific strategy"""
        return Config.STRATEGIES.get(strategy_name, {})
    
    @staticmethod
    def get_trading_config() -> Dict[str, Any]:
        """Get trading configuration"""
        return Config.TRADING
    
    @staticmethod
    def get_risk_config() -> Dict[str, Any]:
        """Get risk management configuration"""
        return Config.RISK_MANAGEMENT


# Default scenario configurations for Scenario A-E
SCENARIO_CONFIGS = {
    'A': {
        'name': 'Benchmark / Volume Throttle',
        'max_daily_trades': 20,
        'min_volume_threshold': 1000000,
        'strategy_mix': {'momentum': 0.4, 'mean_reversion': 0.3, 'arbitrage': 0.3},
    },
    'B': {
        'name': 'Breakeven / Volume Confirm',
        'max_daily_trades': 15,
        'min_volume_threshold': 2000000,
        'strategy_mix': {'momentum': 0.3, 'mean_reversion': 0.4, 'arbitrage': 0.3},
    },
    'C': {
        'name': 'Build-IT Squeeze',
        'max_daily_trades': 10,
        'min_volume_threshold': 5000000,
        'strategy_mix': {'momentum': 0.2, 'mean_reversion': 0.3, 'arbitrage': 0.5},
    },
    'D': {
        'name': 'Limp-DTY Squeeze',
        'max_daily_trades': 12,
        'min_volume_threshold': 3000000,
        'strategy_mix': {'momentum': 0.35, 'mean_reversion': 0.35, 'arbitrage': 0.3},
    },
    'E': {
        'name': 'Win + Liquidity Pump',
        'max_daily_trades': 25,
        'min_volume_threshold': 500000,
        'strategy_mix': {'momentum': 0.5, 'mean_reversion': 0.25, 'arbitrage': 0.25},
    },
}


def load_config(config_file: str = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults"""
    if config_file and os.path.exists(config_file):
        return Config.load_from_file(config_file)
    return {
        'trading': Config.TRADING,
        'strategies': Config.STRATEGIES,
        'risk': Config.RISK_MANAGEMENT,
        'market_data': Config.MARKET_DATA,
        'api': Config.API,
        'backtesting': Config.BACKTESTING,
    }


__all__ = ['Config', 'SCENARIO_CONFIGS', 'load_config']

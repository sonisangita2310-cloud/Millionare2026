"""
Backtesting framework for strategy validation
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 1.0
    strategy: str = "Unknown"
    
    @property
    def pnl(self) -> float:
        """Profit/Loss of trade"""
        if self.exit_price is None:
            return 0
        return (self.exit_price - self.entry_price) * self.quantity
    
    @property
    def pnl_pct(self) -> float:
        """Profit/Loss percentage"""
        if self.exit_price is None or self.entry_price == 0:
            return 0
        return ((self.exit_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def duration(self) -> Optional[float]:
        """Trade duration in hours"""
        if self.exit_time is None:
            return None
        return (self.exit_time - self.entry_time).total_seconds() / 3600


class BacktestResult:
    """Results from backtesting"""
    
    def __init__(self):
        self.trades: List[Trade] = []
        self.initial_capital: float = 0
        self.final_capital: float = 0
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
    
    @property
    def total_trades(self) -> int:
        """Total number of trades"""
        return len(self.trades)
    
    @property
    def winning_trades(self) -> int:
        """Number of winning trades"""
        return len([t for t in self.trades if t.pnl > 0])
    
    @property
    def losing_trades(self) -> int:
        """Number of losing trades"""
        return len([t for t in self.trades if t.pnl < 0])
    
    @property
    def win_rate(self) -> float:
        """Win rate percentage"""
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def total_pnl(self) -> float:
        """Total profit/loss"""
        return sum(t.pnl for t in self.trades)
    
    @property
    def total_pnl_pct(self) -> float:
        """Total profit/loss percentage"""
        if self.initial_capital == 0:
            return 0
        return (self.total_pnl / self.initial_capital) * 100
    
    @property
    def avg_trade_duration(self) -> float:
        """Average trade duration in hours"""
        durations = [t.duration for t in self.trades if t.duration is not None]
        if not durations:
            return 0
        return sum(durations) / len(durations)
    
    @property
    def sharpe_ratio(self) -> float:
        """Sharpe Ratio (simplified)"""
        if not self.trades or len(self.trades) < 2:
            return 0
        
        returns = [t.pnl_pct for t in self.trades]
        avg_return = sum(returns) / len(returns)
        
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0
        
        return (avg_return / std_dev) * (252 ** 0.5)  # Annualized
    
    @property
    def max_drawdown(self) -> float:
        """Maximum drawdown percentage"""
        if not self.trades:
            return 0
        
        cumulative_pnl = []
        running_pnl = 0
        
        for trade in self.trades:
            running_pnl += trade.pnl
            cumulative_pnl.append(running_pnl)
        
        max_pnl = max(cumulative_pnl)
        if max_pnl == 0:
            return 0
        
        max_dd = min(cumulative_pnl) - max_pnl
        return (max_dd / (self.initial_capital + max_pnl)) * 100
    
    def print_summary(self):
        """Print backtest summary"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS SUMMARY")
        print("="*60)
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${self.final_capital:,.2f}")
        print(f"Total P&L: ${self.total_pnl:,.2f} ({self.total_pnl_pct:.2f}%)")
        print(f"\nTrade Statistics:")
        print(f"Total Trades: {self.total_trades}")
        print(f"Winning Trades: {self.winning_trades}")
        print(f"Losing Trades: {self.losing_trades}")
        print(f"Win Rate: {self.win_rate:.2f}%")
        print(f"Avg Trade Duration: {self.avg_trade_duration:.2f} hours")
        print(f"\nRisk Metrics:")
        print(f"Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {self.max_drawdown:.2f}%")
        print("="*60 + "\n")


class Backtester:
    """Backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.result = BacktestResult()
        self.result.initial_capital = initial_capital
    
    def execute_trade(self, trade: Trade):
        """Execute a trade in backtest"""
        if trade.exit_price and trade.pnl > 0:
            self.current_capital += trade.pnl
        elif trade.exit_price and trade.pnl < 0:
            self.current_capital += trade.pnl
        
        self.result.trades.append(trade)
        logger.info(f"Trade executed: {trade.strategy} - P&L: ${trade.pnl:.2f}")
    
    def run_backtest(self, signals: List[Dict], market_data: List[Dict], start_date: datetime, end_date: datetime) -> BacktestResult:
        """Run backtest with given signals and market data"""
        self.result.start_date = start_date
        self.result.end_date = end_date
        
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        
        # Simplified backtest logic
        for signal in signals:
            # Create a trade from signal
            trade = Trade(
                entry_time=signal.get('timestamp', datetime.now()),
                entry_price=signal.get('entry_price', 0),
                exit_time=signal.get('exit_time'),
                exit_price=signal.get('exit_price'),
                quantity=signal.get('quantity', 1),
                strategy=signal.get('strategy', 'Unknown')
            )
            self.execute_trade(trade)
        
        self.result.final_capital = self.current_capital
        return self.result
    
    def optimize_parameters(self, param_ranges: Dict) -> Dict:
        """Optimize strategy parameters"""
        logger.info("Starting parameter optimization...")
        
        best_params = {}
        best_sharpe = float('-inf')
        
        # Placeholder optimization logic
        for param, values in param_ranges.items():
            for value in values:
                logger.debug(f"Testing {param}={value}")
        
        return best_params


class ScenarioBacktester:
    """Test multiple scenarios (Category A-E)"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.backtester = Backtester(initial_capital)
        self.scenarios = {}
    
    def run_scenario_a(self, market_data, signals):
        """Scenario A: Benchmark / Volume Throttle"""
        logger.info("Running Scenario A: Benchmark / Volume Throttle")
        
        # Extract timestamps from market_data (list of OHLCV objects)
        if market_data and len(market_data) > 0:
            if hasattr(market_data[0], 'timestamp'):
                start_time = market_data[0].timestamp
                end_time = market_data[-1].timestamp
            else:
                start_time = datetime.now()
                end_time = datetime.now()
        else:
            start_time = datetime.now()
            end_time = datetime.now()
        
        return self.backtester.run_backtest(signals, market_data, start_time, end_time)
    
    def run_scenario_b(self, market_data, signals):
        """Scenario B: Breakeven / Volume Confirm"""
        logger.info("Running Scenario B: Breakeven / Volume Confirm")
        return self.backtester.run_backtest(signals, market_data, datetime.now(), datetime.now())
    
    def run_scenario_c(self, market_data, signals):
        """Scenario C: Build-IT Squeeze"""
        logger.info("Running Scenario C: Build-IT Squeeze")
        return self.backtester.run_backtest(signals, market_data, datetime.now(), datetime.now())
    
    def run_scenario_d(self, market_data, signals):
        """Scenario D: Limp-DTY Squeeze"""
        logger.info("Running Scenario D: Limp-DTY Squeeze")
        return self.backtester.run_backtest(signals, market_data, datetime.now(), datetime.now())
    
    def run_scenario_e(self, market_data, signals):
        """Scenario E: Win + Liquidity Pump"""
        logger.info("Running Scenario E: Win + Liquidity Pump")
        return self.backtester.run_backtest(signals, market_data, datetime.now(), datetime.now())
    
    def run_all_scenarios(self, market_data, signals) -> Dict:
        """Run all scenarios and compare results"""
        results = {
            'scenario_a': self.run_scenario_a(market_data, signals),
            'scenario_b': self.run_scenario_b(market_data, signals),
            'scenario_c': self.run_scenario_c(market_data, signals),
            'scenario_d': self.run_scenario_d(market_data, signals),
            'scenario_e': self.run_scenario_e(market_data, signals),
        }
        
        return results

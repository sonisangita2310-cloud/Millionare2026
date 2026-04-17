"""
Portfolio and Risk Management module
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Asset types"""
    BITCOIN = "BTC"
    ETHEREUM = "ETH"
    STABLECOIN = "USDC"


@dataclass
class Position:
    """Represents a position in an asset"""
    asset: AssetType
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    
    @property
    def value(self) -> float:
        """Current value of position"""
        return self.quantity * self.current_price
    
    @property
    def pnl(self) -> float:
        """Unrealized P&L"""
        return self.value - (self.quantity * self.entry_price)
    
    @property
    def pnl_pct(self) -> float:
        """Unrealized P&L percentage"""
        if self.entry_price == 0:
            return 0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100


class Portfolio:
    """Portfolio management"""
    
    def __init__(self, initial_cash: float = 100000):
        self.cash = initial_cash
        self.positions: Dict[AssetType, Position] = {}
        self.trade_history = []
        self.max_position_size = 0.3  # 30% of portfolio per position
        self.max_leverage = 1.0  # No leverage by default
    
    @property
    def total_value(self) -> float:
        """Total portfolio value"""
        position_value = sum(p.value for p in self.positions.values())
        return self.cash + position_value
    
    @property
    def position_count(self) -> int:
        """Number of open positions"""
        return len(self.positions)
    
    @property
    def portfolio_allocation(self) -> Dict[str, float]:
        """Asset allocation percentages"""
        total = self.total_value
        allocation = {
            'cash': (self.cash / total * 100) if total > 0 else 0
        }
        
        for asset, position in self.positions.items():
            allocation[asset.value] = (position.value / total * 100) if total > 0 else 0
        
        return allocation
    
    def can_add_position(self, asset: AssetType, required_value: float) -> bool:
        """Check if position can be added"""
        if required_value > self.cash:
            logger.warning(f"Insufficient cash: need {required_value}, have {self.cash}")
            return False
        
        if required_value > self.total_value * self.max_position_size:
            logger.warning(f"Position too large relative to portfolio")
            return False
        
        return True
    
    def add_position(self, asset: AssetType, quantity: float, price: float) -> bool:
        """Add position to portfolio"""
        cost = quantity * price
        
        if not self.can_add_position(asset, cost):
            return False
        
        position = Position(
            asset=asset,
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.now(),
            current_price=price
        )
        
        self.positions[asset] = position
        self.cash -= cost
        
        logger.info(f"Added position: {quantity} {asset.value} @ {price}")
        return True
    
    def close_position(self, asset: AssetType, price: float) -> Optional[float]:
        """Close position"""
        if asset not in self.positions:
            logger.warning(f"No position to close for {asset.value}")
            return None
        
        position = self.positions[asset]
        proceeds = position.quantity * price
        pnl = proceeds - (position.quantity * position.entry_price)
        
        self.cash += proceeds
        del self.positions[asset]
        
        logger.info(f"Closed position: {asset.value} - P&L: ${pnl:.2f}")
        return pnl
    
    def update_prices(self, prices: Dict[AssetType, float]):
        """Update current prices"""
        for asset, price in prices.items():
            if asset in self.positions:
                self.positions[asset].current_price = price
    
    def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        total_value = self.total_value
        total_pnl = sum(p.pnl for p in self.positions.values())
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / total_value * 100) if total_value > 0 else 0,
            'positions': len(self.positions),
            'allocation': self.portfolio_allocation
        }


class RiskManager:
    """Risk management system"""
    
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.max_daily_loss_pct = 0.05  # 5% max daily loss
        self.max_position_loss_pct = 0.02  # 2% max per position
        self.daily_loss = 0.0
        self.alerts = []
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit exceeded"""
        total_pnl_pct = self.portfolio.get_portfolio_stats()['total_pnl_pct']
        
        if total_pnl_pct < -self.max_daily_loss_pct * 100:
            self.alerts.append(f"Daily loss limit exceeded: {total_pnl_pct:.2f}%")
            logger.warning(f"Daily loss limit exceeded")
            return False
        return True
    
    def check_position_loss(self, asset: AssetType) -> bool:
        """Check if position loss is acceptable"""
        if asset not in self.portfolio.positions:
            return True
        
        position = self.portfolio.positions[asset]
        
        if position.pnl_pct < -self.max_position_loss_pct * 100:
            self.alerts.append(f"Position loss limit exceeded for {asset.value}: {position.pnl_pct:.2f}%")
            return False
        return True
    
    def check_concentration_risk(self) -> Dict[str, bool]:
        """Check concentration risk"""
        allocation = self.portfolio.portfolio_allocation
        max_concentration = 0.4  # 40% max in single asset
        
        risks = {}
        for asset, pct in allocation.items():
            if pct > max_concentration:
                risks[asset] = False
                self.alerts.append(f"Concentration risk: {asset} at {pct:.2f}%")
            else:
                risks[asset] = True
        
        return risks
    
    def calculate_var(self, confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk"""
        positions = list(self.portfolio.positions.values())
        if not positions:
            return 0
        
        position_pnls = [p.pnl for p in positions]
        position_pnls.sort()
        
        index = int(len(position_pnls) * (1 - confidence_level))
        return position_pnls[index] if index < len(position_pnls) else 0
    
    def calculate_cvar(self, confidence_level: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        positions = list(self.portfolio.positions.values())
        if not positions:
            return 0
        
        position_pnls = [p.pnl for p in positions]
        position_pnls.sort()
        
        var_index = int(len(position_pnls) * (1 - confidence_level))
        tail_pnls = position_pnls[:var_index]
        
        return sum(tail_pnls) / len(tail_pnls) if tail_pnls else 0
    
    def get_recommended_position_size(self, account_risk_pct: float = 0.01) -> float:
        """Calculate recommended position size based on Kelly Criterion"""
        # Simplified Kelly formula: f = (win_pct * avg_win - loss_pct * avg_loss) / avg_win
        
        # For now, return based on account risk percentage
        return self.portfolio.total_value * account_risk_pct
    
    def run_stress_test(self, market_scenarios: Dict[str, float]) -> Dict:
        """Run stress test with different market scenarios"""
        scenarios_results = {}
        
        for scenario_name, price_change_pct in market_scenarios.items():
            scenario_total_value = 0
            
            for position in self.portfolio.positions.values():
                adjusted_price = position.current_price * (1 + price_change_pct / 100)
                scenario_total_value += position.quantity * adjusted_price
            
            scenario_total_value += self.portfolio.cash
            scenario_pnl = scenario_total_value - self.portfolio.total_value
            
            scenarios_results[scenario_name] = {
                'portfolio_value': scenario_total_value,
                'pnl': scenario_pnl,
                'pnl_pct': (scenario_pnl / self.portfolio.total_value * 100)
            }
        
        return scenarios_results
    
    def print_risk_report(self):
        """Print risk management report"""
        print("\n" + "="*60)
        print("RISK MANAGEMENT REPORT")
        print("="*60)
        
        stats = self.portfolio.get_portfolio_stats()
        print(f"Portfolio Value: ${stats['total_value']:,.2f}")
        print(f"Total P&L: ${stats['total_pnl']:,.2f} ({stats['total_pnl_pct']:.2f}%)")
        
        print(f"\nValue at Risk (95%): ${self.calculate_var(0.95):,.2f}")
        print(f"Conditional VaR (95%): ${self.calculate_cvar(0.95):,.2f}")
        
        print("\nPosition Risks:")
        for asset in self.portfolio.positions:
            if not self.check_position_loss(asset):
                print(f"  [WARNING] {asset.value}: Loss limit at risk")
        
        print("\nAlerts:")
        if self.alerts:
            for alert in self.alerts:
                print(f"  [WARNING] {alert}")
        else:
            print("  [OK] No alerts")
        
        print("="*60 + "\n")

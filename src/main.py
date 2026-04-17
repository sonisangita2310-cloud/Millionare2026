"""
Main entry point for Millionaire 2026 Trading System

This module orchestrates the entire quantitative trading system including:
- Market data collection and analysis
- Strategy execution
- Portfolio management
- Risk management
- Live trading via API integration
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List

from strategies import StrategyManager, StrategyConfig
from market_data import DataFetcher, MarketDataAnalyzer
from backtesting import Backtester, ScenarioBacktester, BacktestResult
from portfolio import Portfolio, RiskManager, AssetType
from trading_api import TradingAPI, Order, OrderType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('millionaire_2026.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingSystem:
    """Main trading system orchestrator"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital)
        self.risk_manager = RiskManager(self.portfolio)
        self.strategy_manager = StrategyManager(StrategyConfig())
        self.trading_api = TradingAPI()
        self.backtest_results = {}
        
        logger.info(f"Initialized Millionaire 2026 Trading System")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    
    def initialize(self) -> bool:
        """Initialize all system components"""
        logger.info("Initializing trading system...")
        
        # Initialize API connections
        if not self.trading_api.initialize():
            logger.error("Failed to initialize trading API")
            return False
        
        # Verify connections
        connection_status = self.trading_api.verify_connection()
        logger.info(f"Connection Status: {connection_status}")
        
        return True
    
    def fetch_market_data(self, assets: List[str] = None) -> Dict:
        """Fetch market data for specified assets"""
        if assets is None:
            assets = ['bitcoin', 'ethereum']
        
        logger.info(f"Fetching market data for {assets}...")
        fetcher = DataFetcher()
        
        market_data = {}
        for asset in assets:
            data = fetcher.get_market_data(asset, days=365)
            if data:
                market_data[asset] = data
                logger.info(f"Fetched {len(data.data)} candles for {asset}")
        
        return market_data
    
    def analyze_markets(self, market_data: Dict) -> Dict:
        """Analyze markets and generate trading signals"""
        logger.info("Analyzing markets for trading signals...")
        
        signals = {}
        for asset, data in market_data.items():
            analyzer = MarketDataAnalyzer(data)
            indicators = analyzer.calculate_indicators()
            signals[asset] = {
                'indicators': indicators,
                'latest': analyzer.get_latest_indicators()
            }
            logger.info(f"Analyzed {asset}: {analyzer.get_latest_indicators()}")
        
        return signals
    
    def run_backtest(self, market_data: Dict, signals: Dict) -> BacktestResult:
        """Run backtest on strategies"""
        logger.info("Running backtest...")
        
        backtester = Backtester(self.initial_capital)
        
        # Convert data for backtesting
        backtest_signals = []
        for asset, signal_data in signals.items():
            backtest_signals.append({
                'asset': asset,
                'timestamp': datetime.now(),
                'entry_price': signal_data['latest'].get('current_price', 0),
                'quantity': 1.0,
                'strategy': 'Combined'
            })
        
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        
        result = backtester.run_backtest(backtest_signals, [], start_date, end_date)
        self.backtest_results['latest'] = result
        
        return result
    
    def execute_trades(self, signals: Dict) -> List[str]:
        """Execute trades based on signals"""
        logger.info("Executing trades...")
        
        executed_orders = []
        
        for asset, signal_data in signals.items():
            current_price = signal_data['latest'].get('current_price', 0)
            
            if current_price > 0:
                # Create order
                order_id = f"ORD-{asset}-{datetime.now().timestamp()}"
                order = Order(
                    order_id=order_id,
                    asset=asset,
                    quantity=0.01,  # 0.01 BTC or 0.1 ETH
                    price=current_price,
                    order_type=OrderType.MARKET,
                    side='BUY'
                )
                
                # Execute order
                if self.trading_api.execute_order(order):
                    executed_orders.append(order_id)
                    logger.info(f"Executed order: {order_id}")
        
        return executed_orders
    
    def manage_portfolio(self):
        """Manage portfolio and risk"""
        logger.info("Managing portfolio...")
        
        # Check risk limits
        if not self.risk_manager.check_daily_loss_limit():
            logger.warning("Daily loss limit exceeded - stopping trading")
            return False
        
        # Check concentration
        concentration = self.risk_manager.check_concentration_risk()
        logger.info(f"Concentration check: {concentration}")
        
        # Get portfolio stats
        stats = self.portfolio.get_portfolio_stats()
        logger.info(f"Portfolio Stats: {stats}")
        
        return True
    
    def generate_report(self) -> str:
        """Generate trading system report"""
        report = []
        report.append("\n" + "="*80)
        report.append("MILLIONAIRE 2026 - AUTOMATED TRADING SYSTEM REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Portfolio Summary
        stats = self.portfolio.get_portfolio_stats()
        report.append("PORTFOLIO SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Value: ${stats['total_value']:,.2f}")
        report.append(f"Cash: ${stats['cash']:,.2f}")
        report.append(f"Total P&L: ${stats['total_pnl']:,.2f} ({stats['total_pnl_pct']:.2f}%)")
        report.append(f"Open Positions: {stats['positions']}\n")
        
        # Asset Allocation
        report.append("ASSET ALLOCATION")
        report.append("-" * 80)
        for asset, pct in stats['allocation'].items():
            report.append(f"{asset:15s}: {pct:6.2f}%")
        report.append("")
        
        # Risk Metrics
        report.append("RISK METRICS")
        report.append("-" * 80)
        report.append(f"Value at Risk (95%): ${self.risk_manager.calculate_var():.2f}")
        report.append(f"Conditional VaR (95%): ${self.risk_manager.calculate_cvar():.2f}")
        report.append("")
        
        # Backtest Results
        if 'latest' in self.backtest_results:
            result = self.backtest_results['latest']
            report.append("BACKTEST PERFORMANCE")
            report.append("-" * 80)
            report.append(f"Total Trades: {result.total_trades}")
            report.append(f"Win Rate: {result.win_rate:.2f}%")
            report.append(f"Total P&L: ${result.total_pnl:,.2f} ({result.total_pnl_pct:.2f}%)")
            report.append(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
            report.append(f"Max Drawdown: {result.max_drawdown:.2f}%")
            report.append("")
        
        # Trading API Status
        connection = self.trading_api.verify_connection()
        report.append("TRADING API STATUS")
        report.append("-" * 80)
        report.append(f"Exchange Connected: {'YES' if connection['exchange_connected'] else 'NO'}")
        report.append(f"MCF Server Connected: {'YES' if connection['mcf_connected'] else 'NO'}")
        report.append("")
        
        # Active Orders
        open_orders = self.trading_api.get_open_orders()
        report.append("ACTIVE ORDERS")
        report.append("-" * 80)
        if open_orders:
            for order in open_orders:
                report.append(f"  {order.order_id}: {order.side} {order.quantity} {order.asset} @ ${order.price}")
        else:
            report.append("  No active orders")
        report.append("")
        
        report.append("="*80 + "\n")
        
        return "\n".join(report)
    
    def shutdown(self):
        """Shutdown trading system"""
        logger.info("Shutting down trading system...")
        self.trading_api.shutdown()
        logger.info("Trading system shutdown complete")


def main():
    """Main entry point"""
    logger.info("Starting Millionaire 2026 Trading System...")
    
    try:
        # Initialize system
        system = TradingSystem(initial_capital=100000)
        
        if not system.initialize():
            logger.error("Failed to initialize trading system")
            return 1
        
        # Fetch market data
        market_data = system.fetch_market_data(['bitcoin', 'ethereum'])
        
        if not market_data:
            logger.warning("No market data available")
        else:
            # Analyze markets
            signals = system.analyze_markets(market_data)
            
            # Run backtest
            backtest_result = system.run_backtest(market_data, signals)
            backtest_result.print_summary()
            
            # Execute trades
            system.execute_trades(signals)
            
            # Manage portfolio
            system.manage_portfolio()
        
        # Generate and print report
        report = system.generate_report()
        print(report)
        
        # Print risk report
        system.risk_manager.print_risk_report()
        
        # Shutdown
        system.shutdown()
        
        logger.info("Millionaire 2026 Trading System completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

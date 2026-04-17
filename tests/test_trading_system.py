"""
Tests for Millionaire 2026 trading system
"""

import pytest
from datetime import datetime
from src.strategies import StrategyManager, StrategyConfig, StrategyType
from src.market_data import OHLCV, MarketData, TechnicalIndicators
from src.portfolio import Portfolio, Position, AssetType
from src.backtesting import Trade, BacktestResult
from src.trading_api import Order, OrderType, OrderStatus


class TestStrategies:
    """Test trading strategies"""
    
    def test_strategy_config_creation(self):
        """Test strategy configuration"""
        config = StrategyConfig()
        assert config.lookback_period == 20
        assert config.entry_threshold == 0.65
        assert config.max_position_size == 0.1
    
    def test_strategy_manager_initialization(self):
        """Test strategy manager initialization"""
        config = StrategyConfig()
        manager = StrategyManager(config)
        assert len(manager.strategies) == 3
        assert StrategyType.MOMENTUM in manager.strategies
    
    def test_momentum_strategy(self):
        """Test momentum strategy"""
        config = StrategyConfig()
        manager = StrategyManager(config)
        
        signals = manager.generate_signals({
            'asset': 'BTC',
            'rsi': 75,
            'macd': 0.5
        })
        
        assert len(signals) > 0
    
    def test_filter_signals_by_confidence(self):
        """Test signal filtering"""
        config = StrategyConfig()
        manager = StrategyManager(config)
        
        signals = manager.generate_signals({'asset': 'BTC', 'rsi': 75, 'macd': 0.5})
        filtered = manager.filter_signals(signals, min_confidence=0.75)
        
        assert all(s.confidence >= 0.75 for s in filtered)


class TestMarketData:
    """Test market data functions"""
    
    def test_ohlcv_creation(self):
        """Test OHLCV data creation"""
        ohlcv = OHLCV(
            timestamp=datetime.now(),
            open_price=100,
            high=110,
            low=95,
            close=105,
            volume=1000
        )
        
        assert ohlcv.close == 105
        assert ohlcv.volume == 1000
    
    def test_ohlcv_invalid_close(self):
        """Test invalid close price"""
        with pytest.raises(ValueError):
            OHLCV(
                timestamp=datetime.now(),
                open_price=100,
                high=110,
                low=95,
                close=0,
                volume=1000
            )
    
    def test_simple_moving_average(self):
        """Test SMA calculation"""
        data = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        sma = TechnicalIndicators.sma(data, 3)
        
        assert sma[0] is None  # Not enough data
        assert sma[2] is None  # Still not enough data (need index 3)
        assert sma[3] == 102.0  # (100 + 102 + 104) / 3
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        data = [100 + i for i in range(20)]  # Uptrend
        rsi = TechnicalIndicators.rsi(data, 14)
        
        # Should indicate overbought in uptrend
        assert rsi[-1] > 70
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        data = [100 + i * 0.1 for i in range(100)]
        upper, middle, lower = TechnicalIndicators.bollinger_bands(data, 20)
        
        # Upper band should be above middle
        for u, m in zip(upper, middle):
            if u and m:
                assert u >= m


class TestPortfolio:
    """Test portfolio management"""
    
    def test_portfolio_initialization(self):
        """Test portfolio initialization"""
        portfolio = Portfolio(100000)
        assert portfolio.cash == 100000
        assert portfolio.total_value == 100000
    
    def test_add_position(self):
        """Test adding position"""
        portfolio = Portfolio(100000)
        success = portfolio.add_position(AssetType.BITCOIN, 0.5, 50000)
        
        assert success
        assert AssetType.BITCOIN in portfolio.positions
        assert portfolio.positions[AssetType.BITCOIN].quantity == 0.5
    
    def test_position_insufficient_funds(self):
        """Test adding position with insufficient funds"""
        portfolio = Portfolio(100000)
        success = portfolio.add_position(AssetType.BITCOIN, 5, 50000)
        
        assert not success  # Would exceed available cash
    
    def test_position_pnl(self):
        """Test position P&L calculation"""
        position = Position(
            asset=AssetType.BITCOIN,
            quantity=1.0,
            entry_price=50000,
            entry_time=datetime.now(),
            current_price=55000
        )
        
        assert position.pnl == 5000
        assert position.pnl_pct == 10.0
    
    def test_portfolio_allocation(self):
        """Test portfolio allocation calculation"""
        portfolio = Portfolio(100000)
        success = portfolio.add_position(AssetType.BITCOIN, 0.5, 30000)  # $15,000 = 15% of portfolio
        
        assert success  # Position should be added successfully
        allocation = portfolio.portfolio_allocation
        
        assert 'cash' in allocation
        assert 'BTC' in allocation
        assert allocation['cash'] + allocation['BTC'] == 100


class TestBacktesting:
    """Test backtesting framework"""
    
    def test_trade_pnl_calculation(self):
        """Test trade P&L calculation"""
        trade = Trade(
            entry_time=datetime.now(),
            entry_price=100,
            exit_price=110,
            quantity=10,
            strategy='Test'
        )
        
        assert trade.pnl == 100  # (110 - 100) * 10
        assert trade.pnl_pct == 10.0
    
    def test_backtest_result_statistics(self):
        """Test backtest result statistics"""
        result = BacktestResult()
        result.initial_capital = 100000
        result.final_capital = 110000
        
        # Add winning trades
        for i in range(3):
            trade = Trade(
                entry_time=datetime.now(),
                entry_price=100,
                exit_price=110,
                quantity=1,
                strategy='Test'
            )
            result.trades.append(trade)
        
        # Add losing trades
        for i in range(2):
            trade = Trade(
                entry_time=datetime.now(),
                entry_price=100,
                exit_price=95,
                quantity=1,
                strategy='Test'
            )
            result.trades.append(trade)
        
        assert result.total_trades == 5
        assert result.winning_trades == 3
        assert result.losing_trades == 2
        assert result.win_rate == 60.0


class TestTradingAPI:
    """Test trading API"""
    
    def test_order_creation(self):
        """Test order creation"""
        order = Order(
            order_id='ORD-001',
            asset='BTC',
            quantity=0.5,
            price=50000,
            order_type=OrderType.MARKET,
            side='BUY'
        )
        
        assert order.asset == 'BTC'
        assert order.quantity == 0.5
        assert order.status == OrderStatus.PENDING
    
    def test_order_filling(self):
        """Test order filling"""
        order = Order(
            order_id='ORD-001',
            asset='BTC',
            quantity=0.5,
            price=50000,
            order_type=OrderType.MARKET,
            side='BUY'
        )
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = 0.5
        order.average_fill_price = 50000
        
        assert order.is_filled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
API and Server Integration module
MCF Server integration for live trading
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Represents a trading order"""
    order_id: str
    asset: str
    quantity: float
    price: float
    order_type: OrderType
    side: str  # 'BUY' or 'SELL'
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status in [OrderStatus.FILLED, OrderStatus.PARTIAL]


class ExchangeAPI:
    """Base class for exchange API integration"""
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to exchange"""
        logger.info("Connecting to exchange...")
        self.connected = True
        return True
    
    def disconnect(self):
        """Disconnect from exchange"""
        self.connected = False
        logger.info("Disconnected from exchange")
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balance"""
        raise NotImplementedError
    
    def place_order(self, order: Order) -> bool:
        """Place an order"""
        raise NotImplementedError
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        raise NotImplementedError
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status"""
        raise NotImplementedError


class CoinbaseAPI(ExchangeAPI):
    """Coinbase API integration"""
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.coinbase.com/v1"
        self.orders = {}
    
    def connect(self) -> bool:
        """Connect to Coinbase"""
        logger.info("Connecting to Coinbase API...")
        # In production, verify credentials here
        self.connected = True
        return True
    
    def get_balance(self) -> Dict[str, float]:
        """Get Coinbase account balance"""
        if not self.connected:
            logger.error("Not connected to Coinbase")
            return {}
        
        logger.info("Fetching Coinbase account balance")
        # Mock balance
        return {
            'BTC': 0.5,
            'ETH': 10.0,
            'USD': 100000.0
        }
    
    def place_order(self, order: Order) -> bool:
        """Place order on Coinbase"""
        if not self.connected:
            logger.error("Not connected to Coinbase")
            return False
        
        logger.info(f"Placing {order.side} order for {order.quantity} {order.asset} @ {order.price}")
        
        # Mock order placement
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = order.price
        
        self.orders[order.order_id] = order
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Coinbase"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Order {order_id} cancelled")
            return True
        return False
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get Coinbase order status"""
        if order_id in self.orders:
            return self.orders[order_id].status
        return OrderStatus.REJECTED


class MCFServerClient:
    """MCF Server client for live trading"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.connected = False
        self.session = None
    
    def connect(self) -> bool:
        """Connect to MCF server"""
        logger.info(f"Connecting to MCF server at {self.server_url}")
        self.connected = True
        return True
    
    def disconnect(self):
        """Disconnect from MCF server"""
        self.connected = False
        logger.info("Disconnected from MCF server")
    
    def send_signal(self, signal: Dict) -> bool:
        """Send trading signal to MCF server"""
        if not self.connected:
            logger.error("Not connected to MCF server")
            return False
        
        logger.info(f"Sending signal to MCF server: {signal}")
        # In production, send via HTTP/WebSocket
        return True
    
    def receive_signals(self) -> List[Dict]:
        """Receive signals from MCF server"""
        if not self.connected:
            return []
        
        logger.info("Receiving signals from MCF server")
        # In production, listen for WebSocket messages
        return []
    
    def get_market_status(self) -> Dict:
        """Get market status from MCF server"""
        return {
            'status': 'active',
            'timestamp': datetime.now().isoformat(),
            'markets': ['BTC-USD', 'ETH-USD']
        }


class TradingAPI:
    """Unified trading API"""
    
    def __init__(self, exchange: ExchangeAPI = None, mcf_client: MCFServerClient = None):
        self.exchange = exchange or CoinbaseAPI()
        self.mcf_client = mcf_client or MCFServerClient()
        self.orders: Dict[str, Order] = {}
    
    def initialize(self) -> bool:
        """Initialize connections"""
        exchange_ok = self.exchange.connect()
        mcf_ok = self.mcf_client.connect()
        
        return exchange_ok and mcf_ok
    
    def shutdown(self):
        """Shutdown connections"""
        self.exchange.disconnect()
        self.mcf_client.disconnect()
    
    def execute_order(self, order: Order) -> bool:
        """Execute order on exchange"""
        success = self.exchange.place_order(order)
        
        if success:
            self.orders[order.order_id] = order
            logger.info(f"Order {order.order_id} executed")
        
        return success
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        return list(self.orders.values())
    
    def get_open_orders(self) -> List[Order]:
        """Get open orders"""
        return [o for o in self.orders.values() if o.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED]]
    
    def broadcast_signal(self, signal: Dict) -> bool:
        """Broadcast signal to MCF server"""
        return self.mcf_client.send_signal(signal)
    
    def verify_connection(self) -> Dict:
        """Verify all connections"""
        balance = self.exchange.get_balance()
        market_status = self.mcf_client.get_market_status()
        
        return {
            'exchange_connected': len(balance) > 0,
            'mcf_connected': market_status.get('status') == 'active',
            'balance': balance,
            'market_status': market_status
        }


__all__ = [
    'Order',
    'OrderType',
    'OrderStatus',
    'ExchangeAPI',
    'CoinbaseAPI',
    'MCFServerClient',
    'TradingAPI'
]

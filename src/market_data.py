"""
Market data module for handling real-time and historical crypto data
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """Open, High, Low, Close, Volume data"""
    timestamp: datetime
    open_price: float
    high: float
    low: float
    close: float
    volume: float
    
    def __post_init__(self):
        if self.close == 0:
            raise ValueError("Close price cannot be zero")


@dataclass
class MarketData:
    """Market data container"""
    asset: str
    timeframe: str
    data: List[OHLCV]
    last_updated: datetime


class DataFetcher:
    """Fetch market data from various sources"""
    
    def __init__(self):
        self.cache = {}
        self.base_urls = {
            'coingecko': 'https://api.coingecko.com/api/v3',
            'coinbase': 'https://api.coinbase.com/v1',
        }
    
    def fetch_coingecko_data(self, asset: str = 'bitcoin', days: int = 365) -> Optional[List[OHLCV]]:
        """Fetch historical data from CoinGecko"""
        try:
            endpoint = f"{self.base_urls['coingecko']}/coins/{asset}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            }
            
            logger.info(f"Fetching {asset} data from CoinGecko for {days} days")
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            prices = data.get('prices', [])
            
            # Convert to OHLCV format (simplified - using close price only)
            ohlcv_data = []
            for price_data in prices:
                timestamp = datetime.fromtimestamp(price_data[0] / 1000)
                close = price_data[1]
                ohlcv_data.append(OHLCV(
                    timestamp=timestamp,
                    open_price=close,
                    high=close * 1.02,
                    low=close * 0.98,
                    close=close,
                    volume=1000000
                ))
            
            self.cache[asset] = ohlcv_data
            return ohlcv_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {asset} data: {e}")
            return None
    
    def get_market_data(self, asset: str, timeframe: str = '1d', days: int = 365) -> Optional[MarketData]:
        """Get market data for an asset"""
        data = self.fetch_coingecko_data(asset, days)
        if data:
            return MarketData(
                asset=asset,
                timeframe=timeframe,
                data=data,
                last_updated=datetime.now()
            )
        return None


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def sma(data: List[float], period: int) -> List[float]:
        """Simple Moving Average"""
        sma_values = []
        for i in range(len(data)):
            if i < period:
                sma_values.append(None)
            else:
                sma_values.append(sum(data[i-period:i]) / period)
        return sma_values
    
    @staticmethod
    def ema(data: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        ema_values = []
        multiplier = 2 / (period + 1)
        
        for i in range(len(data)):
            if i == 0:
                ema_values.append(data[i])
            else:
                ema = (data[i] * multiplier) + (ema_values[i-1] * (1 - multiplier))
                ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index"""
        rsi_values = []
        
        for i in range(len(data)):
            if i < period:
                rsi_values.append(None)
            else:
                gains = sum(max(data[j] - data[j-1], 0) for j in range(i-period+1, i+1)) / period
                losses = sum(max(data[j-1] - data[j], 0) for j in range(i-period+1, i+1)) / period
                
                if losses == 0:
                    rsi = 100 if gains > 0 else 50
                else:
                    rs = gains / losses
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """MACD - Moving Average Convergence Divergence"""
        fast_ema = TechnicalIndicators.ema(data, fast)
        slow_ema = TechnicalIndicators.ema(data, slow)
        
        macd_line = [f - s if f and s else None for f, s in zip(fast_ema, slow_ema)]
        signal_line = TechnicalIndicators.ema([m for m in macd_line if m is not None], signal)
        
        histogram = [m - s if m and s else None for m, s in zip(macd_line, signal_line)]
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Bollinger Bands"""
        sma_values = TechnicalIndicators.sma(data, period)
        
        upper = []
        middle = []
        lower = []
        
        for i in range(len(data)):
            if sma_values[i] is None:
                upper.append(None)
                middle.append(None)
                lower.append(None)
            else:
                mid = sma_values[i]
                middle.append(mid)
                
                variance = sum((data[j] - mid) ** 2 for j in range(i-period+1, i+1)) / period
                std = variance ** 0.5
                
                upper.append(mid + (std * std_dev))
                lower.append(mid - (std * std_dev))
        
        return upper, middle, lower


class MarketDataAnalyzer:
    """Analyze market data for trading signals"""
    
    def __init__(self, market_data: MarketData):
        self.market_data = market_data
        self.indicators = {}
    
    def calculate_indicators(self) -> Dict:
        """Calculate all technical indicators"""
        closes = [ohlcv.close for ohlcv in self.market_data.data]
        
        self.indicators = {
            'sma_20': TechnicalIndicators.sma(closes, 20),
            'ema_12': TechnicalIndicators.ema(closes, 12),
            'rsi_14': TechnicalIndicators.rsi(closes, 14),
            'bollinger': TechnicalIndicators.bollinger_bands(closes, 20),
        }
        
        return self.indicators
    
    def get_latest_indicators(self) -> Dict:
        """Get current indicator values"""
        if not self.indicators:
            self.calculate_indicators()
        
        return {
            'sma_20': self.indicators['sma_20'][-1] if self.indicators['sma_20'] else None,
            'ema_12': self.indicators['ema_12'][-1] if self.indicators['ema_12'] else None,
            'rsi_14': self.indicators['rsi_14'][-1] if self.indicators['rsi_14'] else None,
            'current_price': self.market_data.data[-1].close,
        }

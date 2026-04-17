"""
Technical Indicators Calculator
Computes all indicators needed for backtesting (EMA, RSI, ATR, MACD, Bollinger Bands)
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class IndicatorsEngine:
    """Calculate technical indicators efficiently"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean()
        
        return atr
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        Returns: (macd_line, signal_line, histogram)
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands
        Returns: (upper_band, middle_band, lower_band)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index (trend strength)
        Simplified version: DX average
        """
        plus_dm = high.diff().fillna(0)
        minus_dm = -low.diff().fillna(0)
        
        plus_dm = plus_dm.where(plus_dm > 0, 0)
        minus_dm = minus_dm.where(minus_dm > 0, 0)
        
        tr = IndicatorsEngine.atr(high, low, high.shift(), period)
        
        di_plus = 100 * (plus_dm.rolling(period).mean() / tr)
        di_minus = 100 * (minus_dm.rolling(period).mean() / tr)
        
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(period).mean()
        
        return adx
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators for a single timeframe
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with all indicators added as columns
        """
        result = df.copy()
        
        # EMAs
        result['EMA_12'] = IndicatorsEngine.ema(result['close'], 12)
        result['EMA_21'] = IndicatorsEngine.ema(result['close'], 21)
        result['EMA_50'] = IndicatorsEngine.ema(result['close'], 50)
        result['EMA_200'] = IndicatorsEngine.ema(result['close'], 200)
        
        # SMAs
        result['SMA_20'] = IndicatorsEngine.sma(result['close'], 20)
        result['SMA_50'] = IndicatorsEngine.sma(result['close'], 50)
        result['SMA_200'] = IndicatorsEngine.sma(result['close'], 200)
        
        # RSI
        result['RSI_14'] = IndicatorsEngine.rsi(result['close'], 14)
        
        # ATR
        result['ATR_14'] = IndicatorsEngine.atr(result['high'], result['low'], result['close'], 14)
        
        # MACD
        macd_line, signal_line, histogram = IndicatorsEngine.macd(result['close'])
        result['MACD_line'] = macd_line
        result['MACD_signal'] = signal_line
        result['MACD_histogram'] = histogram
        
        # Bollinger Bands
        upper, middle, lower = IndicatorsEngine.bollinger_bands(result['close'], 20, 2.0)
        result['BB_upper'] = upper
        result['BB_middle'] = middle
        result['BB_lower'] = lower
        result['BB_width'] = (upper - lower) / middle
        
        # ADX
        result['ADX_14'] = IndicatorsEngine.adx(result['high'], result['low'], 14)
        
        return result
    
    @staticmethod
    def get_indicator_value(df: pd.DataFrame, candle_idx: int, indicator_name: str) -> float:
        """
        Safely get indicator value at specific candle index
        Returns NaN if not available
        """
        try:
            if candle_idx < 0 or candle_idx >= len(df):
                return np.nan
            
            value = df.iloc[candle_idx][indicator_name]
            return float(value) if pd.notna(value) else np.nan
        except:
            return np.nan
    
    @staticmethod
    def validate_indicators_ready(df: pd.DataFrame, required_indicators: list) -> bool:
        """Check if all required indicators are calculated and valid"""
        for indicator in required_indicators:
            if indicator not in df.columns:
                return False
            
            # Check if at least some values are not NaN
            if df[indicator].isna().all():
                return False
        
        return True


class MultiTimeframeIndicators:
    """Manage indicators across multiple timeframes"""
    
    def __init__(self):
        self.data = {}
    
    def add_timeframe_indicators(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """Add indicators for specific timeframe"""
        if symbol not in self.data:
            self.data[symbol] = {}
        
        # Store the dataframe as-is (should already have indicators calculated)
        self.data[symbol][timeframe] = df
    
    def get(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Get data with indicators for specific timeframe"""
        if symbol in self.data and timeframe in self.data[symbol]:
            return self.data[symbol][timeframe]
        return None
    
    def get_value_at_candle(self, symbol: str, timeframe: str, candle_idx: int, indicator: str) -> float:
        """Get specific indicator value at candle"""
        df = self.get(symbol, timeframe)
        if df is None:
            return np.nan
        
        return IndicatorsEngine.get_indicator_value(df, candle_idx, indicator)
    
    def print_summary(self):
        """Print summary of loaded indicators"""
        print("\nINDICATORS CALCULATED:")
        print("-" * 60)
        
        for symbol, timeframes in self.data.items():
            print(f"\n{symbol}:")
            for timeframe, df in timeframes.items():
                indicator_cols = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
                print(f"  {timeframe}: {len(indicator_cols)} indicators")
                print(f"    Candles with data: {df.dropna().shape[0]}/{len(df)}")
        
        print("-" * 60)

"""
Data Engine for Backtesting System
Fetches, caches, and manages OHLCV data from ccxt Delta Exchange
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import ccxt

class DataEngine:
    """Manages OHLCV data fetching and caching"""
    
    def __init__(self, exchange_name: str = "binance", cache_dir: str = "data_cache"):
        """
        Initialize data engine
        
        Args:
            exchange_name: ccxt exchange name (default: binance)
            cache_dir: directory for caching data
        """
        self.exchange_name = exchange_name
        self.cache_dir = cache_dir
        self.exchange = None
        self.data_cache = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize exchange with rate limiting
        try:
            exchange_class = getattr(ccxt, exchange_name)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'rateLimit': 500  # Be respectful to API
            })
            print(f"[OK] Initialized {exchange_name} exchange")
        except Exception as e:
            print(f"[ERROR] Could not initialize {exchange_name}: {e}")
            raise Exception(f"Cannot initialize {exchange_name}. Please check exchange name.")
    
    def _get_cache_path(self, symbol: str, timeframe: str) -> str:
        """Get cache file path - escape forward slashes in symbol"""
        safe_symbol = symbol.replace('/', '_').replace('-', '_')
        return os.path.join(self.cache_dir, f"{safe_symbol}_{timeframe}.csv")
    
    def _load_from_cache(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load data from cache if exists"""
        cache_path = self._get_cache_path(symbol, timeframe)
        if os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
        return None
    
    def _save_to_cache(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """Save data to cache"""
        cache_path = self._get_cache_path(symbol, timeframe)
        df.to_csv(cache_path)
    
    def _generate_mock_data(self, symbol: str, timeframe: str, num_candles: int = 1000) -> pd.DataFrame:
        """Generate synthetic OHLCV data for testing when API unavailable"""
        import random
        
        data = []
        minutes = {'5m': 5, '15m': 15, '1h': 60}
        minutes_per_candle = minutes.get(timeframe, 60)
        
        # Starting price
        if 'BTC' in symbol:
            price = 45000.0
            volatility = 0.008  # 0.8%
        else:  # ETH
            price = 2500.0
            volatility = 0.012  # 1.2%
        
        current_time = datetime.now() - timedelta(minutes=num_candles * minutes_per_candle)
        
        for i in range(num_candles):
            # Generate realistic OHLCV
            daily_change = random.gauss(0, volatility)
            open_price = price
            close_price = price * (1 + daily_change)
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, volatility/2)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, volatility/2)))
            volume = random.uniform(100, 1000)
            
            data.append({
                'timestamp': current_time,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
            
            price = close_price
            current_time += timedelta(minutes=minutes_per_candle)
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, max_days_back: int = 730) -> pd.DataFrame:
        """
        Fetch OHLCV data - 2 years minimum (730 days)
        
        Args:
            symbol: trading pair (e.g., 'BTC/USDT', 'ETH/USDT')
            timeframe: timeframe (e.g., '5m', '15m', '1h')
            max_days_back: maximum days to attempt (default 730 = 2 years)
            
        Returns:
            DataFrame with OHLCV data
        """
        import time
        
        # Try cache first
        cached = self._load_from_cache(symbol, timeframe)
        if cached is not None and len(cached) > 1000:
            print(f"  [OK] Loaded {symbol} {timeframe} from cache ({len(cached)} candles)")
            return cached
        
        # Try ccxt API with pagination
        if self.exchange is None:
            raise Exception("Exchange not initialized")
        
        print(f"  [FETCH] Fetching {symbol} {timeframe} (last {max_days_back} days)...")
        
        try:
            # Get exchange limits
            timeframe_ms = self.exchange.parse_timeframe(timeframe) * 1000
            limit = 1000  # Most exchanges support 1000 limit
            
            # Start from 2+ years ago (or maximum available)
            current_time = int(datetime.now().timestamp() * 1000)
            since = int((datetime.now() - timedelta(days=max_days_back)).timestamp() * 1000)
            
            ohlcv_list = []
            fetch_count = 0
            
            while since < current_time:
                try:
                    # Fetch batch of candles
                    candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                    
                    if not candles or len(candles) == 0:
                        print(f"     Reached end of available data ({len(ohlcv_list)} candles total)")
                        break
                    
                    ohlcv_list.extend(candles)
                    fetch_count += 1
                    
                    # Update since to next batch
                    since = candles[-1][0] + timeframe_ms
                    
                    # Progress indicator
                    if fetch_count % 10 == 0:
                        print(f"     Fetched {len(ohlcv_list):,} candles ({fetch_count} API calls)...")
                    
                    # Rate limiting - be respectful to the API
                    time.sleep(0.05)
                    
                except Exception as e:
                    if 'DDoS' in str(e) or 'rate' in str(e).lower():
                        print(f"     Rate limit, waiting 1 second...")
                        time.sleep(1)
                        continue
                    else:
                        raise
            
            # Convert to DataFrame
            if not ohlcv_list:
                raise Exception(f"No data fetched for {symbol} {timeframe}")
            
            df = pd.DataFrame(
                ohlcv_list,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Validate data integrity
            self._validate_data_integrity(df, timeframe)
            
            # Remove duplicates and sort
            df = df[~df.index.duplicated(keep='first')].sort_index()
            
            # Cache results
            self._save_to_cache(symbol, timeframe, df)
            
            # Calculate stats
            days_span = (df.index[-1] - df.index[0]).days
            data_quality = (len(df) / (days_span * 24 * 60 / self.exchange.parse_timeframe(timeframe))) * 100
            
            print(f"  [OK] Fetched {symbol} {timeframe} ({len(df):,} candles, {days_span} days)")
            
            return df
            
        except Exception as e:
            print(f"  [ERROR] Error fetching {symbol} {timeframe}: {e}")
            raise
    
    def _validate_data_integrity(self, df: pd.DataFrame, timeframe: str):
        """
        Validate data integrity
        - Check for missing candles
        - Validate OHLC values
        - Check timestamp alignment
        """
        timeframe_minutes = {'5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440}.get(timeframe, 60)
        expected_interval = timedelta(minutes=timeframe_minutes)
        
        # Check for gaps
        df_copy = df.copy()
        df_copy['time_diff'] = df_copy.index.to_series().diff()
        
        gaps = df_copy[df_copy['time_diff'] > expected_interval]
        if len(gaps) > 0:
            print(f"  [WARNING] Found {len(gaps)} gaps in {timeframe} data")
        
        # Validate OHLC relationships
        invalid = df[(df['low'] > df['high']) | (df['open'] < df['low']) | (df['open'] > df['high']) |
                      (df['close'] < df['low']) | (df['close'] > df['high'])]
        
        if len(invalid) > 0:
            print(f"  [WARNING] Found {len(invalid)} invalid OHLC candles, removing...")
            df.drop(invalid.index, inplace=True)
    
    def get_all_data(self, symbols: List[str], timeframes: List[str], force_real_data: bool = True) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch all required data
        
        Args:
            symbols: list of symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframes: list of timeframes (e.g., ['5m', '15m', '1h'])
            force_real_data: skip cache and always fetch from exchange
            
        Returns:
            Nested dict: {symbol: {timeframe: DataFrame}}
        """
        if not self.exchange:
            raise Exception("[ERROR] Exchange not initialized. Cannot fetch real data.")
        
        all_data = {}
        
        print("\n" + "="*70)
        print("FETCHING MAXIMUM AVAILABLE HISTORICAL DATA FROM EXCHANGE")
        print("="*70)
        print(f"Exchange: {self.exchange_name.upper()}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Timeframes: {', '.join(timeframes)}")
        print("="*70 + "\n")
        
        # Fetch data for each symbol and timeframe
        for symbol in symbols:
            all_data[symbol] = {}
            for timeframe in timeframes:
                try:
                    # Clear cache if force_real_data
                    if force_real_data:
                        cache_path = self._get_cache_path(symbol, timeframe)
                        if os.path.exists(cache_path):
                            os.remove(cache_path)
                    
                    all_data[symbol][timeframe] = self.fetch_ohlcv(symbol, timeframe)
                    
                except Exception as e:
                    print(f"\n[FATAL] Cannot fetch {symbol} {timeframe}")
                    print(f"   Error: {e}")
                    print(f"   Please check:")
                    print(f"   1. Exchange {self.exchange_name} is accessible")
                    print(f"   2. Pair {symbol} exists on {self.exchange_name}")
                    print(f"   3. Timeframe {timeframe} is supported")
                    raise
        
        print("\n" + "="*70)
        print("DATA FETCHING COMPLETE")
        print("="*70 + "\n")
        
        return all_data
    
    def sync_multiframe_data(self, data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Sync multi-timeframe data to common timestamps
        Ensures all timeframes have matching date ranges
        
        Args:
            data: nested dict of {symbol: {timeframe: DataFrame}}
            
        Returns:
            Synced data with aligned timestamps
        """
        print("\n[SYNCING MULTI-TIMEFRAME DATA]")
        
        synced_data = {}
        
        for symbol in data.keys():
            synced_data[symbol] = {}
            
            # Find common date range
            min_date = None
            max_date = None
            
            for timeframe, df in data[symbol].items():
                if min_date is None or df.index.min() > min_date:
                    min_date = df.index.min()
                if max_date is None or df.index.max() < max_date:
                    max_date = df.index.max()
            
            # Sync all timeframes to common range
            for timeframe, df in data[symbol].items():
                df_sync = df[(df.index >= min_date) & (df.index <= max_date)].copy()
                synced_data[symbol][timeframe] = df_sync
                print(f"  {symbol} {timeframe}: {len(df_sync)} candles | {df_sync.index[0]} to {df_sync.index[-1]}")
        
        return synced_data
    
    def resample_to_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Resample OHLCV data to different timeframe"""
        if target_timeframe == '5m':
            minutes = 5
        elif target_timeframe == '15m':
            minutes = 15
        elif target_timeframe == '1h':
            minutes = 60
        else:
            raise ValueError(f"Unknown timeframe: {target_timeframe}")
        
        # OHLCV resampling rules
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        resampled = df.resample(f'{minutes}min').agg(agg_dict)
        resampled = resampled.dropna()
        
        return resampled
    
    def get_data_info(self, data: Dict[str, Dict[str, pd.DataFrame]]) -> str:
        """Get information about loaded data"""
        info = "\nDATA SUMMARY:\n"
        info += "-" * 60 + "\n"
        
        for symbol, timeframes in data.items():
            info += f"\n{symbol}:\n"
            for timeframe, df in timeframes.items():
                info += f"  {timeframe}: {len(df)} candles"
                if len(df) > 0:
                    info += f" | {df.index[0]} to {df.index[-1]}\n"
                else:
                    info += " | NO DATA\n"
        
        info += "-" * 60 + "\n"
        return info

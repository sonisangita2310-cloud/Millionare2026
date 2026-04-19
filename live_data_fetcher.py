"""
LIVE DATA FETCHER - Real-Time Market Data from Binance API

Fetches live 1-hour candles for BTC/USDT from Binance without requiring
authentication. Only uses closed candles to avoid lookahead bias.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class LiveDataFetcher:
    """Fetch live market data from Binance API"""
    
    def __init__(self, symbol='BTCUSDT', interval='1h', lookback_candles=200):
        """
        Args:
            symbol: Trading pair (default: BTCUSDT for Bitcoin)
            interval: Candle interval (default: 1h for 1-hour candles)
            lookback_candles: Number of historical candles to fetch (default: 200)
        """
        self.symbol = symbol
        self.interval = interval
        self.lookback_candles = lookback_candles
        self.api_url = 'https://api.binance.com/api/v3'
        
        # Track last processed candle
        self.last_candle_timestamp = None
        self.last_fetch_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
    
    def fetch_candles(self, verbose=False):
        """
        Fetch latest closed candles from Binance with ROBUST RETRY LOGIC
        
        Retry Strategy:
        - Max 3 attempts
        - Wait 60 seconds between retries
        - On all failures: return None (skip cycle, do NOT trade)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            None if all retries fail (safe: no partial data, no trading)
        """
        max_retries = 3
        retry_wait_seconds = 60
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            
            try:
                # Fetch latest candles
                params = {
                    'symbol': self.symbol,
                    'interval': self.interval,
                    'limit': self.lookback_candles
                }
                
                response = requests.get(f'{self.api_url}/klines', params=params, timeout=10)
                response.raise_for_status()
                
                if response.status_code != 200:
                    if verbose:
                        print(f"[API ERROR] Status code: {response.status_code} (attempt {attempt}/{max_retries})")
                    
                    # Retry on non-200 status
                    if attempt < max_retries:
                        if verbose:
                            print(f"[API RETRY] Waiting {retry_wait_seconds}s before retry...")
                        time.sleep(retry_wait_seconds)
                        continue
                    else:
                        # All retries exhausted
                        print(f"[API ERROR] All {max_retries} retries failed, skipping cycle (NO TRADE)")
                        return None
                
                data = response.json()
                if not data or len(data) < 10:
                    if verbose:
                        print(f"[API ERROR] Insufficient candle data: {len(data)} (attempt {attempt}/{max_retries})")
                    
                    # Retry on insufficient data
                    if attempt < max_retries:
                        if verbose:
                            print(f"[API RETRY] Waiting {retry_wait_seconds}s before retry...")
                        time.sleep(retry_wait_seconds)
                        continue
                    else:
                        print(f"[API ERROR] All {max_retries} retries failed, skipping cycle (NO TRADE)")
                        return None
                
                # SUCCESS: Validate and return data
                # Reset error counter on successful fetch
                self.consecutive_errors = 0
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                # Convert timestamps to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                
                # Convert prices and volume to float
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # Keep only needed columns (no partial data)
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
                self.last_fetch_time = datetime.now()
                
                if verbose:
                    print(f"[API] Fetched {len(df)} candles (attempt {attempt}/{max_retries})")
                    print(f"[DATA] Latest candle: {df.iloc[-1]['timestamp']} | Close: ${df.iloc[-1]['close']:.2f}")
                
                return df
            
            except requests.exceptions.Timeout as e:
                self.consecutive_errors += 1
                if verbose:
                    print(f"[API ERROR] Request timeout (attempt {attempt}/{max_retries})")
                
                if attempt < max_retries:
                    if verbose:
                        print(f"[API RETRY] Waiting {retry_wait_seconds}s before retry...")
                    time.sleep(retry_wait_seconds)
                else:
                    print(f"[API ERROR] All {max_retries} retries failed (timeout), skipping cycle (NO TRADE)")
                    return None
            
            except requests.exceptions.ConnectionError as e:
                self.consecutive_errors += 1
                if verbose:
                    print(f"[API ERROR] Connection error (attempt {attempt}/{max_retries})")
                
                if attempt < max_retries:
                    if verbose:
                        print(f"[API RETRY] Waiting {retry_wait_seconds}s before retry...")
                    time.sleep(retry_wait_seconds)
                else:
                    print(f"[API ERROR] All {max_retries} retries failed (connection), skipping cycle (NO TRADE)")
                    return None
            
            except Exception as e:
                self.consecutive_errors += 1
                if verbose:
                    print(f"[API ERROR] {str(e)} (attempt {attempt}/{max_retries})")
                
                if attempt < max_retries:
                    if verbose:
                        print(f"[API RETRY] Waiting {retry_wait_seconds}s before retry...")
                    time.sleep(retry_wait_seconds)
                else:
                    print(f"[API ERROR] All {max_retries} retries failed ({type(e).__name__}), skipping cycle (NO TRADE)")
                    return None
        
        # Should not reach here, but just in case
        print(f"[API ERROR] Unexpected: all retries exhausted, skipping cycle (NO TRADE)")
        return None
    
    def is_new_candle(self, df):
        """
        Check if a new candle has formed
        
        Args:
            df: DataFrame with latest candles
        
        Returns:
            True if new candle (latest != last processed), False otherwise
        """
        if df is None or len(df) < 1:
            return False
        
        latest_timestamp = df.iloc[-1]['timestamp']
        
        if self.last_candle_timestamp is None:
            self.last_candle_timestamp = latest_timestamp
            return True
        
        if latest_timestamp > self.last_candle_timestamp:
            self.last_candle_timestamp = latest_timestamp
            return True
        
        return False
    
    def get_time_until_next_candle(self, verbose=False):
        """
        Calculate seconds until next 1-hour candle closes
        
        For 1-hour candles, next close is at top of next hour
        """
        now = datetime.now()
        minutes_until_next = 60 - now.minute
        seconds_until_next = (minutes_until_next * 60) - now.second
        
        # Add buffer (30 seconds) to ensure candle is fully closed
        buffer_seconds = 30
        total_seconds = max(seconds_until_next + buffer_seconds, 5)
        
        if verbose:
            print(f"[WAIT] Time until next 1H candle: {total_seconds} seconds ({int(total_seconds/60)}m {total_seconds%60}s)")
        
        return total_seconds
    
    def wait_for_next_candle(self, check_interval=30, verbose=False):
        """
        Wait for next 1-hour candle to close
        
        Checks every check_interval seconds to detect new candle formation
        
        Args:
            check_interval: How often to check for new candle (seconds)
            verbose: Print wait messages
        """
        start_time = datetime.now()
        last_check_time = start_time
        
        if verbose:
            seconds_until = self.get_time_until_next_candle(verbose=False)
            print(f"[WAIT] Waiting for next candle ({seconds_until}s)...")
        
        while True:
            # Sleep for check interval
            time.sleep(check_interval)
            
            # Try to fetch latest candles
            df = self.fetch_candles(verbose=False)
            
            if df is not None and self.is_new_candle(df):
                elapsed = (datetime.now() - start_time).total_seconds()
                if verbose:
                    print(f"[CANDLE] New candle detected after {int(elapsed)}s")
                break
            
            # Show progress every 60 seconds
            now = datetime.now()
            if (now - last_check_time).total_seconds() >= 60:
                elapsed = (now - start_time).total_seconds()
                remaining = self.get_time_until_next_candle(verbose=False)
                if verbose:
                    print(f"[WAIT] Waiting... {int(elapsed)}s elapsed, ~{int(remaining)}s remaining")
                last_check_time = now
    
    def get_system_status(self, verbose=False):
        """Get current API and connection status"""
        if self.consecutive_errors >= self.max_consecutive_errors:
            status = "CRITICAL"
            message = f"API connection failed {self.consecutive_errors} times"
        elif self.consecutive_errors > 0:
            status = "WARNING"
            message = f"API had {self.consecutive_errors} error(s)"
        else:
            status = "OK"
            message = "API connection healthy"
        
        if verbose:
            print(f"[STATUS] {status}: {message}")
        
        return {
            'status': status,
            'consecutive_errors': self.consecutive_errors,
            'message': message,
            'last_fetch': self.last_fetch_time
        }


def test_live_fetcher():
    """Test live data fetcher"""
    print("="*80)
    print("TESTING LIVE DATA FETCHER")
    print("="*80 + "\n")
    
    fetcher = LiveDataFetcher(symbol='BTCUSDT', interval='1h', lookback_candles=10)
    
    print("[TEST] Fetching live candles from Binance...")
    df = fetcher.fetch_candles(verbose=True)
    
    if df is not None:
        print(f"\n[SUCCESS] Fetched {len(df)} candles")
        print("\nLatest 3 candles:")
        print(df.tail(3).to_string())
        
        print(f"\nSystem status:")
        status = fetcher.get_system_status(verbose=True)
        
        return True
    else:
        print("[FAILED] Could not fetch candles")
        return False


if __name__ == '__main__':
    test_live_fetcher()

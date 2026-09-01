"""
London Strategic Edge (LSE) Market Data Feed
Direct HTTP Vault API client for institutional OHLCV candles across Forex, Gold, and Crypto.
"""
from typing import Optional, Dict, Any
import requests
import pandas as pd
import numpy as np


class LSEDataFeed:
    """
    Client for London Strategic Edge Vault Market Data API.
    Provides tick and candle historical market data.
    """

    BASE_URL = "https://api.londonstrategicedge.com/vault"
    DEFAULT_API_KEY = "lse_live_b89820fd0f3e9e2229eed3829c8e00e3"

    SYMBOL_MAP = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "BTCUSD": "BTC/USD"
    }

    TIMEFRAME_MAP = {
        "15m": "15m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d"
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self.DEFAULT_API_KEY

    def get_vault_usage(self) -> Dict[str, Any]:
        """
        Retrieves account usage statistics and rate limits.
        """
        url = f"{self.BASE_URL}/usage"
        headers = {"x-api-key": self.api_key}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def fetch_candles(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "15m",
        limit: int = 120
    ) -> pd.DataFrame:
        """
        Fetches OHLCV candles from London Strategic Edge Vault API.
        Returns a sorted DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume'].
        """
        lse_symbol = self.SYMBOL_MAP.get(symbol.upper(), symbol)
        lse_tf = self.TIMEFRAME_MAP.get(timeframe.lower(), "15m")

        url = f"{self.BASE_URL}/candles"
        params = {
            "symbol": lse_symbol,
            "timeframe": lse_tf,
            "limit": limit,
            "order": "desc" # Fetch newest candles
        }
        headers = {"x-api-key": self.api_key}

        resp = requests.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        if not data or not isinstance(data, list):
            raise ValueError(f"No candle data returned for symbol {lse_symbol} ({lse_tf})")

        df = pd.DataFrame(data)
        
        # Standardize column naming
        # Expected from LSE: 'ts', 'symbol', 'open', 'high', 'low', 'close', optional 'volume'
        df['time'] = pd.to_datetime(df['ts'])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)

        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0).astype(float)
        else:
            # Forex pairs without volume
            df['volume'] = 1000.0

        # Sort chronological (oldest to newest)
        df = df.sort_values('time').reset_index(drop=True)
        df.index = df['time']

        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

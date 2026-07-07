"""OHLCV data fetching for crypto (Binance via ccxt) and US stocks (yfinance)."""
from __future__ import annotations
import time
import pandas as pd
import ccxt
import yfinance as yf

_BINANCE = ccxt.binance({"enableRateLimit": True})

# timeframe -> (yf_interval, yf_period, ccxt_tf, ccxt_limit)
TIMEFRAMES = {
    "5m":  ("5m",  "5d",  "5m",  500),
    "15m": ("15m", "5d",  "15m", 500),
    "1h":  ("60m", "60d", "1h",  500),
    "4h":  ("60m", "60d", "4h",  500),  # yf no 4h, fallback 1h resample
    "1d":  ("1d",  "1y",  "1d",  365),
    "1w":  ("1wk", "5y",  "1w",  300),
}


def is_crypto(symbol: str) -> bool:
    return "/" in symbol


def fetch_crypto(symbol: str, tf: str = "1h") -> pd.DataFrame:
    yf_int, yf_per, ctf, limit = TIMEFRAMES[tf]
    ohlcv = _BINANCE.fetch_ohlcv(symbol, timeframe=ctf, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)
    return df


def fetch_stock(symbol: str, tf: str = "1h") -> pd.DataFrame:
    yf_int, yf_per, ctf, _ = TIMEFRAMES[tf]
    df = yf.download(
        symbol, period=yf_per, interval=yf_int,
        progress=False, auto_adjust=False, threads=False,
    )
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    if tf == "4h":
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
    return df


def fetch(symbol: str, tf: str = "1h") -> pd.DataFrame:
    if is_crypto(symbol):
        return fetch_crypto(symbol, tf)
    return fetch_stock(symbol, tf)

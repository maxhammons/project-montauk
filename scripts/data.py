"""
TECL data fetcher — CSV fallback + yfinance for fresh data.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT_ROOT, "reference", "TECL Price History (2-23-26).csv")


def load_csv() -> pd.DataFrame:
    """Load the bundled TECL CSV."""
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.columns = [c.lower().strip() for c in df.columns]
    return df


def fetch_yfinance(start: str = "2008-12-01", end: str | None = None) -> pd.DataFrame:
    """Fetch TECL daily OHLCV from yfinance."""
    try:
        import yfinance as yf
        end = end or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        ticker = yf.Ticker("TECL")
        hist = ticker.history(start=start, end=end, auto_adjust=True)
        if hist.empty:
            raise ValueError("yfinance returned empty data")
        df = hist.reset_index()
        df.columns = [c.lower().strip() for c in df.columns]
        df = df.rename(columns={"date": "date"})
        # Ensure tz-naive dates for consistency
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[data] yfinance fetch failed: {e}")
        return pd.DataFrame()


def get_tecl_data(use_yfinance: bool = True) -> pd.DataFrame:
    """
    Get TECL data. Tries yfinance first for freshest data,
    falls back to bundled CSV.
    """
    df = pd.DataFrame()

    if use_yfinance:
        df = fetch_yfinance()

    if df.empty:
        print("[data] Using bundled CSV data")
        df = load_csv()
    else:
        print(f"[data] yfinance: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")

    # Ensure required columns
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"

    return df


if __name__ == "__main__":
    df = get_tecl_data()
    print(f"Loaded {len(df)} bars")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print(df.tail())

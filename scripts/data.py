from __future__ import annotations

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


def fetch_yahoo(start: str = "2008-12-01", end: str | None = None) -> pd.DataFrame:
    """
    Fetch TECL daily OHLCV directly from Yahoo Finance chart API.
    No yfinance dependency — just requests + pandas.
    """
    try:
        import requests

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now() + timedelta(days=1)
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/TECL"
            f"?period1={period1}&period2={period2}&interval=1d"
            f"&includeAdjustedClose=true"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s").normalize(),
            "open": quotes["open"],
            "high": quotes["high"],
            "low": quotes["low"],
            "close": quotes["close"],
            "volume": quotes["volume"],
        })

        # Drop rows with NaN prices
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        # Ensure tz-naive
        df["date"] = df["date"].dt.tz_localize(None)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[data] Yahoo Finance fetch failed: {e}")
        return pd.DataFrame()


def get_tecl_data(use_yfinance: bool = True) -> pd.DataFrame:
    """
    Get TECL data. Loads the bundled CSV as the base, then backfills
    any missing recent bars from yfinance (from CSV's last date to today).
    Falls back to CSV-only if yfinance is unavailable.
    """
    # Always start with the CSV as our base
    csv_df = load_csv()
    csv_last_date = csv_df["date"].max()
    print(f"[data] CSV: {len(csv_df)} bars, ending {csv_last_date.date()}")

    if not use_yfinance:
        print("[data] yfinance disabled, using CSV only")
        return csv_df

    # Fetch new bars from Yahoo starting the day after CSV ends
    fetch_start = (csv_last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    yf_df = fetch_yahoo(start=fetch_start)

    if yf_df.empty:
        print("[data] No new yfinance data (CSV may already be current)")
        return csv_df

    # Filter to only bars after the CSV's last date (avoid overlap)
    yf_df = yf_df[yf_df["date"] > csv_last_date].reset_index(drop=True)

    if yf_df.empty:
        print("[data] yfinance returned data but no new bars after CSV")
        return csv_df

    # Merge: CSV base + yfinance new bars
    # Ensure matching columns
    shared_cols = ["date", "open", "high", "low", "close", "volume"]
    csv_clean = csv_df[shared_cols].copy()
    yf_clean = yf_df[shared_cols].copy()

    df = pd.concat([csv_clean, yf_clean], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)

    print(f"[data] Merged: {len(csv_clean)} CSV + {len(yf_clean)} yfinance = {len(df)} total bars")
    print(f"[data] Date range: {df['date'].min().date()} to {df['date'].max().date()}")

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

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


def _fetch_ticker_yahoo(ticker: str, start: str = "2008-12-01", end: str | None = None) -> pd.DataFrame:
    """
    Fetch daily OHLCV for any ticker from Yahoo Finance chart API.
    Shared helper used by fetch_yahoo, fetch_vix, build_synthetic_tecl.
    """
    try:
        import requests

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now() + timedelta(days=1)
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
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

        df = df.dropna(subset=["close"]).reset_index(drop=True)
        df["date"] = df["date"].dt.tz_localize(None)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[data] Yahoo Finance fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def fetch_vix(start: str = "1990-01-01", end: str | None = None) -> pd.DataFrame:
    """
    Fetch CBOE VIX daily close from Yahoo Finance.
    Returns DataFrame with columns: date, vix_close.
    """
    df = _fetch_ticker_yahoo("^VIX", start=start, end=end)
    if df.empty:
        return pd.DataFrame(columns=["date", "vix_close"])
    return df[["date", "close"]].rename(columns={"close": "vix_close"})


def build_synthetic_tecl(start: str = "1998-01-01", end: str | None = None,
                         anchor_price: float = 10.0) -> pd.DataFrame:
    """
    Build synthetic 3x leveraged TECL data from XLK.

    Uses XLK daily returns scaled by 3x minus daily expense ratio to simulate
    what TECL would have looked like before it existed.

    Parameters
    ----------
    start : start date for XLK fetch
    end : end date for XLK fetch (exclusive — fetch up to this date)
    anchor_price : the price the synthetic series should end at
                   (set to real TECL's first close so they stitch together)

    Returns DataFrame with columns: date, open, high, low, close, volume
    """
    xlk = _fetch_ticker_yahoo("XLK", start=start, end=end)
    if xlk.empty:
        print("[data] WARNING: Could not fetch XLK for synthetic TECL")
        return pd.DataFrame()

    daily_expense = 0.0095 / 252  # TECL expense ratio ~0.95% / trading days

    xlk_close = xlk["close"].values.astype(np.float64)
    xlk_open = xlk["open"].values.astype(np.float64)
    xlk_high = xlk["high"].values.astype(np.float64)
    xlk_low = xlk["low"].values.astype(np.float64)

    n = len(xlk_close)

    # Compute daily returns and synthetic 3x leveraged returns
    daily_ret = np.zeros(n)
    synth_ret = np.zeros(n)
    for i in range(1, n):
        daily_ret[i] = xlk_close[i] / xlk_close[i - 1] - 1
        synth_ret[i] = 3 * daily_ret[i] - daily_expense

    # Build synthetic close series (forward from arbitrary base, then rescale)
    # Start with base=1.0 and compound forward
    synth_close = np.ones(n)
    for i in range(1, n):
        synth_close[i] = synth_close[i - 1] * (1 + synth_ret[i])

    # Rescale so the last synthetic close equals anchor_price
    scale = anchor_price / synth_close[-1] if synth_close[-1] != 0 else 1.0
    synth_close *= scale

    # Synthesize OHLC by scaling XLK OHLC ratios
    xlk_close_safe = np.where(xlk_close > 0, xlk_close, 1.0)
    synth_open = synth_close * (xlk_open / xlk_close_safe)
    synth_high = synth_close * (xlk_high / xlk_close_safe)
    synth_low = synth_close * (xlk_low / xlk_close_safe)

    result = pd.DataFrame({
        "date": xlk["date"].values,
        "open": synth_open,
        "high": synth_high,
        "low": synth_low,
        "close": synth_close,
        "volume": xlk["volume"].values,
    })

    return result


def get_tecl_data(use_yfinance: bool = True) -> pd.DataFrame:
    """
    Get TECL data. The bundled CSV includes synthetic 3x data from XLK
    (1998-2008) stitched to real TECL (2009-present). yfinance only
    appends NEW bars after the CSV's last date — it never overwrites
    the historical/synthetic data.

    Parameters
    ----------
    use_yfinance : fetch fresh bars from Yahoo Finance (appended, never overwrites)
    """
    # Always start with the CSV as our base (includes synthetic 1998-2008 + real 2009+)
    csv_df = load_csv()
    csv_last_date = csv_df["date"].max()
    print(f"[data] CSV: {len(csv_df)} bars, {csv_df['date'].min().date()} to {csv_last_date.date()}")

    if not use_yfinance:
        print("[data] yfinance disabled, using CSV only")
        df = csv_df
    else:
        # Only fetch bars AFTER the CSV ends — never overwrite existing data
        fetch_start = (csv_last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        yf_df = fetch_yahoo(start=fetch_start)

        if yf_df.empty:
            print("[data] No new yfinance data (CSV may already be current)")
            df = csv_df
        else:
            # Strictly append: only bars after CSV's last date
            yf_df = yf_df[yf_df["date"] > csv_last_date].reset_index(drop=True)

            if yf_df.empty:
                print("[data] yfinance returned data but no new bars after CSV")
                df = csv_df
            else:
                shared_cols = ["date", "open", "high", "low", "close", "volume"]
                csv_clean = csv_df[shared_cols].copy()
                yf_clean = yf_df[shared_cols].copy()

                df = pd.concat([csv_clean, yf_clean], ignore_index=True)
                df = df.sort_values("date").reset_index(drop=True)

                print(f"[data] Appended: {len(yf_clean)} new bars from yfinance ({len(df)} total)")

    # ── Fetch and merge VIX ──
    vix_start = df["date"].min().strftime("%Y-%m-%d")
    print(f"[data] Fetching VIX from {vix_start}...")
    vix_df = fetch_vix(start=vix_start)

    if vix_df.empty:
        print("[data] WARNING: VIX fetch failed, filling vix_close with NaN")
        df["vix_close"] = np.nan
    else:
        print(f"[data] VIX: {len(vix_df)} bars")
        df = df.merge(vix_df, on="date", how="left")
        vix_count = df["vix_close"].notna().sum()
        print(f"[data] VIX matched {vix_count}/{len(df)} TECL dates")

    print(f"[data] Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"

    return df


if __name__ == "__main__":
    df = get_tecl_data()
    print(f"Loaded {len(df)} bars")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print(df.tail())

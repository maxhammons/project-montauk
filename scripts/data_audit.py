#!/usr/bin/env python3
"""
Data audit + enrichment for Project Montauk.

1. Audit synthetic TECL data against XLK (verify 3x leverage calculation)
2. Download VIX daily data → CSV
3. Download XLK daily data → CSV (for reference)
4. Download Treasury yield spread data (10Y-2Y) → CSV
5. Build consolidated TECL master CSV with all columns
6. Download additional context: TQQQ, QQQ for cross-asset reference
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add scripts dir to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from data import _fetch_ticker_yahoo, fetch_vix, load_csv

PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
TS_DIR = os.path.join(PROJECT_ROOT, "reference", "time-series data")


def fetch_fred_series(series_id: str, start: str = "1998-01-01") -> pd.DataFrame:
    """
    Fetch a FRED time series via their public API (no key needed for CSV).
    Returns DataFrame with columns: date, value.
    """
    import requests
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"[FRED] Failed to fetch {series_id}: {e}")
        return pd.DataFrame(columns=["date", "value"])


# ─────────────────────────────────────────────────────────────────────
# 1. AUDIT: Verify synthetic TECL against XLK
# ─────────────────────────────────────────────────────────────────────

def audit_synthetic_tecl():
    """
    Compare the synthetic portion of the TECL CSV against fresh XLK data.
    The synthetic TECL should be: 3x daily XLK returns minus daily expense ratio.
    """
    print("\n" + "=" * 70)
    print("AUDIT: Synthetic TECL vs XLK (3x leverage verification)")
    print("=" * 70)

    # Load the existing TECL CSV
    csv_path = os.path.join(TS_DIR, "TECL Price History (2-23-26).csv")
    tecl = pd.read_csv(csv_path, parse_dates=["date"])
    tecl = tecl.sort_values("date").reset_index(drop=True)
    tecl.columns = [c.lower().strip() for c in tecl.columns]

    # TECL IPO was 2008-12-17. Everything before that is synthetic.
    ipo_date = pd.Timestamp("2008-12-17")
    synth = tecl[tecl["date"] < ipo_date].copy()
    real = tecl[tecl["date"] >= ipo_date].copy()
    print(f"  Synthetic bars: {len(synth)} ({synth['date'].min().date()} to {synth['date'].max().date()})")
    print(f"  Real bars:      {len(real)} ({real['date'].min().date()} to {real['date'].max().date()})")

    # Fetch XLK for the synthetic period
    synth_start = synth["date"].min().strftime("%Y-%m-%d")
    synth_end = (ipo_date + timedelta(days=5)).strftime("%Y-%m-%d")
    print(f"\n  Fetching XLK from {synth_start} to {synth_end}...")
    xlk = _fetch_ticker_yahoo("XLK", start=synth_start, end=synth_end)

    if xlk.empty:
        print("  ERROR: Could not fetch XLK data. Skipping audit.")
        return None

    print(f"  XLK bars fetched: {len(xlk)}")

    # Merge on date
    merged = synth.merge(xlk[["date", "close"]], on="date", how="inner", suffixes=("_tecl", "_xlk"))
    print(f"  Matched bars: {len(merged)}")

    if len(merged) < 10:
        print("  ERROR: Too few matched bars for audit.")
        return None

    # Compute XLK daily returns
    xlk_close = merged["close_xlk"].values.astype(np.float64)
    tecl_close = merged["close_tecl"].values.astype(np.float64)

    xlk_ret = np.zeros(len(xlk_close))
    tecl_ret = np.zeros(len(tecl_close))
    for i in range(1, len(xlk_close)):
        if xlk_close[i-1] > 0:
            xlk_ret[i] = xlk_close[i] / xlk_close[i-1] - 1
        if tecl_close[i-1] > 0:
            tecl_ret[i] = tecl_close[i] / tecl_close[i-1] - 1

    # Expected synthetic return: 3x XLK daily return - expense
    daily_expense = 0.0095 / 252
    expected_ret = 3 * xlk_ret - daily_expense

    # Compare (skip first bar which has no return)
    diff = tecl_ret[1:] - expected_ret[1:]

    print(f"\n  --- Return comparison (synthetic TECL vs 3x XLK - expense) ---")
    print(f"  Mean absolute error:   {np.mean(np.abs(diff)):.8f}")
    print(f"  Max absolute error:    {np.max(np.abs(diff)):.8f}")
    print(f"  Std of errors:         {np.std(diff):.8f}")
    print(f"  Correlation:           {np.corrcoef(tecl_ret[1:], expected_ret[1:])[0,1]:.8f}")

    # Check for large discrepancies (> 1% daily return difference)
    large_errors = np.where(np.abs(diff) > 0.01)[0]
    if len(large_errors) > 0:
        print(f"\n  WARNING: {len(large_errors)} bars with >1% return discrepancy:")
        for idx in large_errors[:10]:
            bar_idx = idx + 1  # offset for skip
            d = merged.iloc[bar_idx]["date"]
            print(f"    {d.date()}: TECL ret={tecl_ret[bar_idx]:.4f}, expected={expected_ret[bar_idx]:.4f}, diff={diff[idx]:.4f}")
    else:
        print(f"\n  PASS: No bars with >1% return discrepancy")

    # Also check the stitch point — does the synthetic end match the real start?
    if len(synth) > 0 and len(real) > 0:
        last_synth = synth.iloc[-1]
        first_real = real.iloc[0]
        gap_days = (first_real["date"] - last_synth["date"]).days
        price_gap = abs(first_real["close"] - last_synth["close"]) / last_synth["close"] * 100
        print(f"\n  --- Stitch point ---")
        print(f"  Last synthetic: {last_synth['date'].date()} close=${last_synth['close']:.2f}")
        print(f"  First real:     {first_real['date'].date()} close=${first_real['close']:.2f}")
        print(f"  Gap: {gap_days} calendar days, {price_gap:.2f}% price difference")
        if price_gap > 5:
            print(f"  WARNING: Large price gap at stitch point ({price_gap:.1f}%)")
        else:
            print(f"  PASS: Stitch point looks clean")

    # Check for suspicious values
    print(f"\n  --- Data quality checks ---")
    zero_close = (synth["close"] <= 0).sum()
    nan_close = synth["close"].isna().sum()
    zero_vol = (synth["volume"] <= 0).sum()
    print(f"  Zero/negative closes: {zero_close}")
    print(f"  NaN closes:           {nan_close}")
    print(f"  Zero/negative volume: {zero_vol}")

    # Check OHLC consistency: high >= low, high >= close, low <= close
    bad_hl = (synth["high"] < synth["low"]).sum()
    bad_hc = (synth["high"] < synth["close"]).sum()
    bad_lc = (synth["low"] > synth["close"]).sum()
    print(f"  High < Low:           {bad_hl}")
    print(f"  High < Close:         {bad_hc}")
    print(f"  Low > Close:          {bad_lc}")

    if zero_close == 0 and nan_close == 0 and bad_hl == 0:
        print(f"\n  PASS: Synthetic data quality checks all clean")
    else:
        print(f"\n  WARNING: Data quality issues found above")

    return merged


# ─────────────────────────────────────────────────────────────────────
# 2. DOWNLOAD: VIX
# ─────────────────────────────────────────────────────────────────────

def download_vix():
    print("\n" + "=" * 70)
    print("DOWNLOAD: VIX Daily Close")
    print("=" * 70)

    df = _fetch_ticker_yahoo("^VIX", start="1990-01-01")
    if df.empty:
        print("  ERROR: Could not fetch VIX")
        return None

    vix = df[["date", "open", "high", "low", "close", "volume"]].copy()
    vix.columns = ["date", "vix_open", "vix_high", "vix_low", "vix_close", "vix_volume"]

    out_path = os.path.join(TS_DIR, "VIX Daily.csv")
    vix.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(f"  Bars: {len(vix)}, {vix['date'].min().date()} to {vix['date'].max().date()}")
    return vix


# ─────────────────────────────────────────────────────────────────────
# 3. DOWNLOAD: XLK (TECL underlying)
# ─────────────────────────────────────────────────────────────────────

def download_xlk():
    print("\n" + "=" * 70)
    print("DOWNLOAD: XLK Daily (TECL underlying)")
    print("=" * 70)

    df = _fetch_ticker_yahoo("XLK", start="1998-01-01")
    if df.empty:
        print("  ERROR: Could not fetch XLK")
        return None

    out_path = os.path.join(TS_DIR, "XLK Daily.csv")
    df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(f"  Bars: {len(df)}, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


# ─────────────────────────────────────────────────────────────────────
# 4. DOWNLOAD: Treasury Yield Spread (10Y-2Y) — recession indicator
# ─────────────────────────────────────────────────────────────────────

def download_yield_spread():
    print("\n" + "=" * 70)
    print("DOWNLOAD: Treasury Yield Spread (10Y-2Y)")
    print("=" * 70)

    df = fetch_fred_series("T10Y2Y", start="1998-01-01")
    if df.empty:
        print("  ERROR: Could not fetch yield spread from FRED")
        return None

    df.columns = ["date", "yield_spread_10y2y"]
    out_path = os.path.join(TS_DIR, "Treasury Yield Spread 10Y-2Y.csv")
    df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(f"  Bars: {len(df)}, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


# ─────────────────────────────────────────────────────────────────────
# 5. DOWNLOAD: Cross-asset reference (TQQQ, QQQ)
# ─────────────────────────────────────────────────────────────────────

def download_cross_assets():
    print("\n" + "=" * 70)
    print("DOWNLOAD: Cross-Asset Reference (QQQ, TQQQ)")
    print("=" * 70)

    for ticker in ["QQQ", "TQQQ"]:
        start = "1999-01-01" if ticker == "QQQ" else "2010-02-01"
        df = _fetch_ticker_yahoo(ticker, start=start)
        if df.empty:
            print(f"  ERROR: Could not fetch {ticker}")
            continue
        out_path = os.path.join(TS_DIR, f"{ticker} Daily.csv")
        df.to_csv(out_path, index=False)
        print(f"  Saved: {out_path}")
        print(f"  {ticker}: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")


# ─────────────────────────────────────────────────────────────────────
# 6. DOWNLOAD: Federal Funds Rate — monetary policy regime
# ─────────────────────────────────────────────────────────────────────

def download_fed_funds():
    print("\n" + "=" * 70)
    print("DOWNLOAD: Federal Funds Effective Rate")
    print("=" * 70)

    df = fetch_fred_series("DFF", start="1998-01-01")
    if df.empty:
        print("  ERROR: Could not fetch Fed Funds Rate from FRED")
        return None

    df.columns = ["date", "fed_funds_rate"]
    out_path = os.path.join(TS_DIR, "Fed Funds Rate.csv")
    df.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(f"  Bars: {len(df)}, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


# ─────────────────────────────────────────────────────────────────────
# 7. BUILD: Consolidated TECL Master CSV
# ─────────────────────────────────────────────────────────────────────

def build_master_csv():
    """
    Build a single TECL master CSV with all available enrichment columns:
    - TECL OHLCV (synthetic + real)
    - VIX close
    - XLK close (underlying)
    - Yield spread (10Y-2Y)
    - Fed Funds Rate
    """
    print("\n" + "=" * 70)
    print("BUILD: TECL Master CSV (all enrichment data)")
    print("=" * 70)

    # Start with TECL base
    csv_path = os.path.join(TS_DIR, "TECL Price History (2-23-26).csv")
    tecl = pd.read_csv(csv_path, parse_dates=["date"])
    tecl = tecl.sort_values("date").reset_index(drop=True)
    tecl.columns = [c.lower().strip() for c in tecl.columns]

    # Fetch fresh TECL bars to extend if needed
    last_date = tecl["date"].max()
    fresh = _fetch_ticker_yahoo("TECL", start=(last_date + timedelta(days=1)).strftime("%Y-%m-%d"))
    if not fresh.empty:
        fresh = fresh[fresh["date"] > last_date]
        if not fresh.empty:
            shared = ["date", "open", "high", "low", "close", "volume"]
            tecl = pd.concat([tecl[shared], fresh[shared]], ignore_index=True)
            tecl = tecl.sort_values("date").reset_index(drop=True)
            print(f"  Extended TECL with {len(fresh)} new bars")

    master = tecl[["date", "open", "high", "low", "close", "volume"]].copy()
    print(f"  TECL base: {len(master)} bars")

    # Merge VIX
    vix_path = os.path.join(TS_DIR, "VIX Daily.csv")
    if os.path.exists(vix_path):
        vix = pd.read_csv(vix_path, parse_dates=["date"])
        master = master.merge(vix[["date", "vix_close"]], on="date", how="left")
        matched = master["vix_close"].notna().sum()
        print(f"  VIX merged: {matched}/{len(master)} dates matched")
    else:
        master["vix_close"] = np.nan
        print(f"  VIX: file not found, filled NaN")

    # Merge XLK close
    xlk_path = os.path.join(TS_DIR, "XLK Daily.csv")
    if os.path.exists(xlk_path):
        xlk = pd.read_csv(xlk_path, parse_dates=["date"])
        master = master.merge(xlk[["date", "close"]].rename(columns={"close": "xlk_close"}),
                              on="date", how="left")
        matched = master["xlk_close"].notna().sum()
        print(f"  XLK merged: {matched}/{len(master)} dates matched")
    else:
        master["xlk_close"] = np.nan
        print(f"  XLK: file not found, filled NaN")

    # Merge yield spread (FRED data is daily but not every trading day)
    spread_path = os.path.join(TS_DIR, "Treasury Yield Spread 10Y-2Y.csv")
    if os.path.exists(spread_path):
        spread = pd.read_csv(spread_path, parse_dates=["date"])
        master = master.merge(spread, on="date", how="left")
        # Forward-fill FRED data (published daily but weekends/holidays missing)
        master["yield_spread_10y2y"] = master["yield_spread_10y2y"].ffill()
        matched = master["yield_spread_10y2y"].notna().sum()
        print(f"  Yield spread merged: {matched}/{len(master)} dates (ffill)")
    else:
        master["yield_spread_10y2y"] = np.nan
        print(f"  Yield spread: file not found, filled NaN")

    # Merge Fed Funds
    ff_path = os.path.join(TS_DIR, "Fed Funds Rate.csv")
    if os.path.exists(ff_path):
        ff = pd.read_csv(ff_path, parse_dates=["date"])
        master = master.merge(ff, on="date", how="left")
        master["fed_funds_rate"] = master["fed_funds_rate"].ffill()
        matched = master["fed_funds_rate"].notna().sum()
        print(f"  Fed Funds merged: {matched}/{len(master)} dates (ffill)")
    else:
        master["fed_funds_rate"] = np.nan
        print(f"  Fed Funds: file not found, filled NaN")

    # Add computed columns
    # TECL daily return
    master["tecl_daily_ret"] = master["close"].pct_change()
    # XLK daily return (where available)
    if "xlk_close" in master.columns:
        master["xlk_daily_ret"] = master["xlk_close"].pct_change()
        # Leverage ratio: TECL ret / XLK ret (should be ~3x)
        mask = master["xlk_daily_ret"].abs() > 0.001  # avoid div by tiny numbers
        master.loc[mask, "leverage_ratio"] = master.loc[mask, "tecl_daily_ret"] / master.loc[mask, "xlk_daily_ret"]

    out_path = os.path.join(TS_DIR, "TECL Master.csv")
    master.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    print(f"  Total bars: {len(master)}")
    print(f"  Columns: {list(master.columns)}")
    print(f"  Date range: {master['date'].min().date()} to {master['date'].max().date()}")

    return master


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Project Montauk — Data Audit & Enrichment")
    print("=" * 70)

    # Step 1: Audit synthetic data
    audit_synthetic_tecl()

    # Step 2-6: Download all data
    download_vix()
    download_xlk()
    download_yield_spread()
    download_fed_funds()
    download_cross_assets()

    # Step 7: Build master CSV
    build_master_csv()

    print("\n" + "=" * 70)
    print("DONE. All data saved to:")
    print(f"  {TS_DIR}")
    print("=" * 70)

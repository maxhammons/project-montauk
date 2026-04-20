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
from datetime import timedelta

# Paths (this file lives at scripts/data/audit.py)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))              # scripts/data/
SCRIPTS_DIR = os.path.dirname(_THIS_DIR)                              # scripts/
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)                           # project root
TS_DIR = os.path.join(PROJECT_ROOT, "data")                           # project/data/
sys.path.insert(0, SCRIPTS_DIR)

from data.loader import _fetch_ticker_yahoo


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
# Phase 3e — Synthetic formula re-verification (constants)
# ─────────────────────────────────────────────────────────────────────
#
# Every synthetic row in TECL.csv / TQQQ.csv is built as a first-order
# leveraged-IOPV approximation:
#
#     synth_close[i] = synth_close[i-1] * (1 + 3*src_daily_ret - daily_expense)
#
# where:
#     daily_expense = expense_ratio_yr / 252
#
# Expense ratios (verified against issuer prospectuses):
#     TECL: 0.95%/yr  (ProShares 2024 prospectus)  → 0.0095/252
#     TQQQ: 0.75%/yr  (ProShares prospectus)        → 0.0075/252
#
# Underlying sources:
#     TECL  pre-1998-12-22:  ^SP500-45 (S&P 500 Information Technology Sector index)
#     TECL  1998-12-22 → 2008-12-16:  XLK (Technology Select Sector SPDR ETF)
#     TECL  2008-12-17 →:    real Yahoo TECL bars
#     TQQQ  pre-2010-02-11:  QQQ (Yahoo Finance — pre-1999 backfilled by Yahoo)
#     TQQQ  2010-02-11 →:    real Yahoo TQQQ bars
#
# Leverage decay is modeled IMPLICITLY via daily compounding (a real
# leveraged ETF rebalances daily; this is the same mechanism). It is not
# a separate term in the formula. The decay is regime-dependent — shown
# as a diagnostic in Phase 4 viz, not penalized in fitness.
#
# Re-verification: scripts/data_rebuild_synthetic.py rebuilds from these
# sources deterministically. data_quality.py asserts current CSV matches
# the rebuild row-by-row.

EXPENSE_RATIO_TECL = 0.0095   # /yr — ProShares 2024 prospectus
EXPENSE_RATIO_TQQQ = 0.0075   # /yr — ProShares prospectus
TRADING_DAYS_PER_YEAR = 252


def reverify_formula() -> dict:
    """
    Phase 3e: re-verify the synthetic formula against the source CSVs.
    Returns per-ticker {mean_abs_err, max_abs_err, n} on the daily-return
    residual. This is independent of data_rebuild_synthetic.py — it
    audits the *returns* row-by-row, while the rebuild audits the *bytes*.
    """
    out = {}
    # TECL — verified per-segment so we audit each underlying source separately.
    tecl_path = os.path.join(TS_DIR, "TECL.csv")
    if os.path.exists(tecl_path):
        tecl = pd.read_csv(tecl_path, parse_dates=["date"])
        tecl["date"] = tecl["date"].dt.normalize()
        # Segment 0: ^SP500-45
        sp_path = os.path.join(TS_DIR, "SP500-45.csv")
        if os.path.exists(sp_path):
            src = pd.read_csv(sp_path, parse_dates=["date"])
            src["date"] = src["date"].dt.normalize()
            seg = tecl[tecl["date"] < pd.Timestamp("1998-12-22")]
            m = seg.merge(src[["date", "close"]].rename(columns={"close": "src_close"}), on="date", how="inner")
            m["src_ret"] = m["src_close"].pct_change()
            m["tecl_ret"] = m["close"].pct_change()
            expected = 3 * m["src_ret"] - EXPENSE_RATIO_TECL / TRADING_DAYS_PER_YEAR
            diff = (m["tecl_ret"] - expected).dropna()
            out["TECL_seg0_SP500-45"] = {"n": len(diff), "mean_abs_err": float(diff.abs().mean()), "max_abs_err": float(diff.abs().max())}
        # Segment 1: XLK
        xlk_path = os.path.join(TS_DIR, "XLK.csv")
        if os.path.exists(xlk_path):
            src = pd.read_csv(xlk_path, parse_dates=["date"])
            src["date"] = src["date"].dt.normalize()
            seg = tecl[(tecl["date"] >= pd.Timestamp("1998-12-22")) & (tecl["date"] < pd.Timestamp("2008-12-17"))]
            m = seg.merge(src[["date", "close"]].rename(columns={"close": "src_close"}), on="date", how="inner")
            m["src_ret"] = m["src_close"].pct_change()
            m["tecl_ret"] = m["close"].pct_change()
            expected = 3 * m["src_ret"] - EXPENSE_RATIO_TECL / TRADING_DAYS_PER_YEAR
            diff = (m["tecl_ret"] - expected).dropna()
            out["TECL_seg1_XLK"] = {"n": len(diff), "mean_abs_err": float(diff.abs().mean()), "max_abs_err": float(diff.abs().max())}

    # TQQQ — single segment vs QQQ.
    tqqq_path = os.path.join(TS_DIR, "TQQQ.csv")
    qqq_path = os.path.join(TS_DIR, "QQQ.csv")
    if os.path.exists(tqqq_path) and os.path.exists(qqq_path):
        tqqq = pd.read_csv(tqqq_path, parse_dates=["date"])
        tqqq["date"] = tqqq["date"].dt.normalize()
        qqq = pd.read_csv(qqq_path, parse_dates=["date"])
        qqq["date"] = qqq["date"].dt.normalize()
        seg = tqqq[tqqq["date"] < pd.Timestamp("2010-02-11")]
        m = seg.merge(qqq[["date", "close"]].rename(columns={"close": "src_close"}), on="date", how="inner")
        m["src_ret"] = m["src_close"].pct_change()
        m["tqqq_ret"] = m["close"].pct_change()
        expected = 3 * m["src_ret"] - EXPENSE_RATIO_TQQQ / TRADING_DAYS_PER_YEAR
        diff = (m["tqqq_ret"] - expected).dropna()
        out["TQQQ_seg0_QQQ"] = {"n": len(diff), "mean_abs_err": float(diff.abs().mean()), "max_abs_err": float(diff.abs().max())}

    return out


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

    print("\n  --- Return comparison (synthetic TECL vs 3x XLK - expense) ---")
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
        print("\n  PASS: No bars with >1% return discrepancy")

    # Also check the stitch point — does the synthetic end match the real start?
    if len(synth) > 0 and len(real) > 0:
        last_synth = synth.iloc[-1]
        first_real = real.iloc[0]
        gap_days = (first_real["date"] - last_synth["date"]).days
        price_gap = abs(first_real["close"] - last_synth["close"]) / last_synth["close"] * 100
        print("\n  --- Stitch point ---")
        print(f"  Last synthetic: {last_synth['date'].date()} close=${last_synth['close']:.2f}")
        print(f"  First real:     {first_real['date'].date()} close=${first_real['close']:.2f}")
        print(f"  Gap: {gap_days} calendar days, {price_gap:.2f}% price difference")
        if price_gap > 5:
            print(f"  WARNING: Large price gap at stitch point ({price_gap:.1f}%)")
        else:
            print("  PASS: Stitch point looks clean")

    # Check for suspicious values
    print("\n  --- Data quality checks ---")
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
        print("\n  PASS: Synthetic data quality checks all clean")
    else:
        print("\n  WARNING: Data quality issues found above")

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

    out_path = os.path.join(TS_DIR, "VIX.csv")
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

    out_path = os.path.join(TS_DIR, "XLK.csv")
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
    out_path = os.path.join(TS_DIR, "treasury-spread-10y2y.csv")
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
        out_path = os.path.join(TS_DIR, f"{ticker}.csv")
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
    out_path = os.path.join(TS_DIR, "fed-funds-rate.csv")
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
    vix_path = os.path.join(TS_DIR, "VIX.csv")
    if os.path.exists(vix_path):
        vix = pd.read_csv(vix_path, parse_dates=["date"])
        master = master.merge(vix[["date", "vix_close"]], on="date", how="left")
        matched = master["vix_close"].notna().sum()
        print(f"  VIX merged: {matched}/{len(master)} dates matched")
    else:
        master["vix_close"] = np.nan
        print("  VIX: file not found, filled NaN")

    # Merge XLK close
    xlk_path = os.path.join(TS_DIR, "XLK.csv")
    if os.path.exists(xlk_path):
        xlk = pd.read_csv(xlk_path, parse_dates=["date"])
        master = master.merge(xlk[["date", "close"]].rename(columns={"close": "xlk_close"}),
                              on="date", how="left")
        matched = master["xlk_close"].notna().sum()
        print(f"  XLK merged: {matched}/{len(master)} dates matched")
    else:
        master["xlk_close"] = np.nan
        print("  XLK: file not found, filled NaN")

    # Merge yield spread (FRED data is daily but not every trading day)
    spread_path = os.path.join(TS_DIR, "treasury-spread-10y2y.csv")
    if os.path.exists(spread_path):
        spread = pd.read_csv(spread_path, parse_dates=["date"])
        master = master.merge(spread, on="date", how="left")
        # Forward-fill FRED data (published daily but weekends/holidays missing)
        master["yield_spread_10y2y"] = master["yield_spread_10y2y"].ffill()
        matched = master["yield_spread_10y2y"].notna().sum()
        print(f"  Yield spread merged: {matched}/{len(master)} dates (ffill)")
    else:
        master["yield_spread_10y2y"] = np.nan
        print("  Yield spread: file not found, filled NaN")

    # Merge Fed Funds
    ff_path = os.path.join(TS_DIR, "fed-funds-rate.csv")
    if os.path.exists(ff_path):
        ff = pd.read_csv(ff_path, parse_dates=["date"])
        master = master.merge(ff, on="date", how="left")
        master["fed_funds_rate"] = master["fed_funds_rate"].ffill()
        matched = master["fed_funds_rate"].notna().sum()
        print(f"  Fed Funds merged: {matched}/{len(master)} dates (ffill)")
    else:
        master["fed_funds_rate"] = np.nan
        print("  Fed Funds: file not found, filled NaN")

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

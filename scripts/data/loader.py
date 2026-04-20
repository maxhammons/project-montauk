from __future__ import annotations

"""
TECL data module — local-first with API refresh on /spike invocation.

All data lives in data/ as CSVs. The optimizer reads from local files
and never calls an API during a run. The refresh_all() function is called
once at /spike start to pull any new bars and update every CSV in place.

Files managed:
  TECL.csv                    TECL OHLCV (synthetic 1998-2008 + real 2009+) + vix_close
  VIX.csv                     CBOE VIX OHLCV
  XLK.csv                     TECL underlying
  TQQQ.csv                    Synthetic 1999-2010 + real 2010+
  QQQ.csv                     TQQQ underlying
  SGOV.csv                    iShares 0-3 Month Treasury Bond ETF
  treasury-spread-10y2y.csv   FRED T10Y2Y
  fed-funds-rate.csv          FRED DFF
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Paths (this file lives at scripts/data/loader.py — 3 levels down from project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS_DIR = os.path.join(PROJECT_ROOT, "data")
TECL_CSV = os.path.join(TS_DIR, "TECL.csv")
VIX_CSV = os.path.join(TS_DIR, "VIX.csv")
XLK_CSV = os.path.join(TS_DIR, "XLK.csv")
QQQ_CSV = os.path.join(TS_DIR, "QQQ.csv")
TQQQ_CSV = os.path.join(TS_DIR, "TQQQ.csv")
SGOV_CSV = os.path.join(TS_DIR, "SGOV.csv")
TBILL_3M_CSV = os.path.join(TS_DIR, "tbill-3m.csv")

# Legacy path — migrated to TECL.csv on first load
_LEGACY_CSV = os.path.join(TS_DIR, "TECL Price History (2-23-26).csv")


# ─────────────────────────────────────────────────────────────────────
# Provenance schema (Phase 3b)
# ─────────────────────────────────────────────────────────────────────
#
# Every leveraged-ETF row carries five columns describing where it came
# from and how it was constructed. Stitch segments are ordered chronologically.

PROVENANCE_COLUMNS = (
    "is_synthetic",
    "source_symbol",
    "source_kind",            # "synthetic-leveraged" | "yahoo-real"
    "synthetic_model_version",
    "stitch_segment",         # int — 0 is earliest segment
)

# Per-ticker stitch plan: (segment_id, source_symbol, kind, model_version, end_date_exclusive)
# end_date_exclusive=None means "open-ended" (last segment).
_TECL_STITCH_PLAN = [
    (0, "^SP500-45", "synthetic-leveraged", "v2-3xTechIdx-0.95%ER-daily", "1998-12-22"),
    (1, "XLK",       "synthetic-leveraged", "v2-3xTechIdx-0.95%ER-daily", "2008-12-17"),
    (2, "TECL",      "yahoo-real",          "",                             None),
]
_TQQQ_STITCH_PLAN = [
    (0, "QQQ",  "synthetic-leveraged", "v1-3xQQQ-0.75%ER-daily", "2010-02-11"),
    (1, "TQQQ", "yahoo-real",          "",                         None),
]


def _apply_stitch_plan(df: pd.DataFrame, plan: list) -> pd.DataFrame:
    """Annotate df rows with provenance based on chronological stitch plan."""
    df = df.copy()
    seg_id = pd.Series(index=df.index, dtype="int64")
    src_sym = pd.Series(index=df.index, dtype=object)
    src_kind = pd.Series(index=df.index, dtype=object)
    model_v = pd.Series(index=df.index, dtype=object)

    prev_end = pd.Timestamp("1900-01-01")
    for sid, sym, kind, mv, end in plan:
        end_ts = pd.Timestamp(end) if end else pd.Timestamp("2999-12-31")
        mask = (df["date"] >= prev_end) & (df["date"] < end_ts)
        seg_id[mask] = sid
        src_sym[mask] = sym
        src_kind[mask] = kind
        model_v[mask] = mv
        prev_end = end_ts

    df["is_synthetic"] = (src_kind == "synthetic-leveraged").astype(bool)
    df["source_symbol"] = src_sym
    df["source_kind"] = src_kind
    df["synthetic_model_version"] = model_v
    df["stitch_segment"] = seg_id.astype("Int64")
    return df


def _ensure_provenance_columns(csv_path: str, plan: list) -> bool:
    """
    Idempotently add Phase 3b provenance columns to a ticker CSV.
    Returns True if file was modified.
    """
    if not os.path.exists(csv_path):
        return False
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)

    needs_write = any(c not in df.columns for c in PROVENANCE_COLUMNS)
    df = _apply_stitch_plan(df, plan)
    df.to_csv(csv_path, index=False)
    return needs_write


def migrate_provenance() -> dict:
    """Add provenance columns to TECL.csv and TQQQ.csv. Idempotent."""
    out = {}
    out["TECL"] = _ensure_provenance_columns(TECL_CSV, _TECL_STITCH_PLAN)
    out["TQQQ"] = _ensure_provenance_columns(TQQQ_CSV, _TQQQ_STITCH_PLAN)
    return out


# ─────────────────────────────────────────────────────────────────────
# Date normalization
# ─────────────────────────────────────────────────────────────────────

def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the date column is timezone-naive datetime64 at midnight,
    sorted monotonically. Drops duplicate dates (keeps last).
    Raises ValueError on non-monotonic dates after dedup.
    """
    if "date" not in df.columns or df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    if hasattr(df["date"].dt, "tz") and df["date"].dt.tz is not None:
        df["date"] = df["date"].dt.tz_localize(None)
    df["date"] = df["date"].dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    if not df["date"].is_monotonic_increasing:
        df = df.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
        if not df["date"].is_monotonic_increasing:
            raise ValueError(
                "date column is not monotonic increasing after dedup; "
                f"first violation near index {df['date'].diff().lt(pd.Timedelta(0)).idxmax()}"
            )
    return df


# ─────────────────────────────────────────────────────────────────────
# Yahoo Finance fetcher (shared)
# ─────────────────────────────────────────────────────────────────────

def _fetch_ticker_yahoo(ticker: str, start: str = "2008-12-01", end: str | None = None) -> pd.DataFrame:
    """Fetch daily OHLCV for any ticker from Yahoo Finance chart API."""
    try:
        import requests

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now() + timedelta(days=1)

        # Daily bars need at least one full day of span; same-day/future
        # fetches just create noisy 400s from Yahoo.
        if start_dt.date() >= end_dt.date():
            return pd.DataFrame()
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
        adjclose = (
            result.get("indicators", {})
            .get("adjclose", [{}])[0]
            .get("adjclose")
        )
        if not adjclose:
            adjclose = quotes["close"]

        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s").normalize(),
            "open": quotes["open"],
            "high": quotes["high"],
            "low": quotes["low"],
            "close": quotes["close"],
            "adj_close": adjclose,
            "volume": quotes["volume"],
        })

        df = df.dropna(subset=["close"]).reset_index(drop=True)
        df = _normalize_date_column(df)
        return df

    except Exception as e:
        print(f"[data] Yahoo Finance fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def _fetch_fred_csv(series_id: str, start: str = "1998-01-01") -> pd.DataFrame:
    """Fetch a FRED time series via their public CSV endpoint."""
    try:
        import requests
        from io import StringIO
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).reset_index(drop=True)
        df = _normalize_date_column(df)
        return df
    except Exception as e:
        print(f"[data] FRED fetch failed for {series_id}: {e}")
        return pd.DataFrame(columns=["date", "value"])


# ─────────────────────────────────────────────────────────────────────
# CSV append helper
# ─────────────────────────────────────────────────────────────────────

def _append_new_bars(csv_path: str, ticker: str, start_override: str | None = None) -> int:
    """
    Append new bars to an existing CSV from Yahoo Finance.
    Returns number of new bars appended. Does NOT overwrite existing data.
    """
    if not os.path.exists(csv_path):
        return 0

    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    last_date = df["date"].max()

    fetch_start = start_override or (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    fresh = _fetch_ticker_yahoo(ticker, start=fetch_start)

    if fresh.empty:
        return 0

    fresh = fresh[fresh["date"] > last_date].reset_index(drop=True)
    if fresh.empty:
        return 0

    for col in fresh.columns:
        if col not in df.columns:
            if col == "adj_close" and "close" in df.columns:
                df[col] = df["close"]
            else:
                df[col] = np.nan

    # Only keep columns that exist in the current CSV
    shared = [c for c in df.columns if c in fresh.columns]
    combined = pd.concat([df[shared], fresh[shared]], ignore_index=True)
    combined = _normalize_date_column(combined)
    combined.to_csv(csv_path, index=False)
    return len(fresh)


def _refresh_or_create_ticker_csv(csv_path: str, ticker: str, *, start: str) -> int:
    """
    Create a ticker CSV from scratch if missing, otherwise append new bars.
    Returns number of rows added.
    """
    if not os.path.exists(csv_path):
        df = _fetch_ticker_yahoo(ticker, start=start)
        if df.empty:
            return 0
        df = _normalize_date_column(df)
        df.to_csv(csv_path, index=False)
        return len(df)
    return _append_new_bars(csv_path, ticker)


# ─────────────────────────────────────────────────────────────────────
# refresh_all() — called once at /spike start
# ─────────────────────────────────────────────────────────────────────

def refresh_all():
    """
    Pull latest bars for all local CSVs. Called once at /spike invocation.
    Updates files in place — only appends, never overwrites historical data.
    """
    print("[refresh] Updating all local CSVs...")

    # ── TECL ──
    # Migrate legacy file if needed
    if os.path.exists(_LEGACY_CSV) and not os.path.exists(TECL_CSV):
        _migrate_legacy_tecl()
    elif not os.path.exists(TECL_CSV):
        print("[refresh] ERROR: No TECL CSV found. Run data_audit.py first.")
        return

    # Append fresh TECL bars
    tecl_new = _append_tecl_bars()
    print(f"[refresh] TECL: +{tecl_new} new bars")

    # ── VIX ──
    vix_new = _append_vix_bars()
    print(f"[refresh] VIX: +{vix_new} new bars")

    # ── Re-merge VIX into TECL ──
    if vix_new > 0 or tecl_new > 0:
        _merge_vix_into_tecl()

    # ── XLK ──
    n = _append_new_bars(XLK_CSV, "XLK")
    print(f"[refresh] XLK: +{n} new bars")

    # ── QQQ ──
    n = _append_new_bars(QQQ_CSV, "QQQ")
    print(f"[refresh] QQQ: +{n} new bars")

    # ── TQQQ ──
    n = _append_new_bars(TQQQ_CSV, "TQQQ")
    print(f"[refresh] TQQQ: +{n} new bars")

    # ── SGOV ──
    n = _refresh_or_create_ticker_csv(SGOV_CSV, "SGOV", start="2020-01-01")
    print(f"[refresh] SGOV: +{n} new bars")

    # ── FRED data (yield spread, fed funds) ──
    _refresh_fred("tbill-3m.csv", "DTB3", "rate_3m_tbill")
    _refresh_fred("treasury-spread-10y2y.csv", "T10Y2Y", "yield_spread_10y2y")
    _refresh_fred("fed-funds-rate.csv", "DFF", "fed_funds_rate")

    # Summary
    tecl = pd.read_csv(TECL_CSV, parse_dates=["date"])
    print(f"[refresh] Done. TECL: {len(tecl)} bars through {tecl['date'].max().date()}")


def _append_tecl_bars() -> int:
    """Append new TECL bars from Yahoo and save to TECL.csv."""
    df = pd.read_csv(TECL_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    last_date = df["date"].max()

    fresh = _fetch_ticker_yahoo("TECL", start=(last_date + timedelta(days=1)).strftime("%Y-%m-%d"))
    if fresh.empty:
        return 0

    fresh = fresh[fresh["date"] > last_date].reset_index(drop=True)
    if fresh.empty:
        return 0

    # New rows get OHLCV, vix_close will be filled by _merge_vix_into_tecl
    for col in df.columns:
        if col not in fresh.columns:
            fresh[col] = np.nan

    combined = pd.concat([df, fresh[df.columns]], ignore_index=True)
    combined = _normalize_date_column(combined)
    combined.to_csv(TECL_CSV, index=False)
    return len(fresh)


def _append_vix_bars() -> int:
    """Append new VIX bars from Yahoo and save to VIX.csv."""
    if not os.path.exists(VIX_CSV):
        # Full download
        vix = _fetch_ticker_yahoo("^VIX", start="1990-01-01")
        if vix.empty:
            return 0
        vix.columns = ["date", "vix_open", "vix_high", "vix_low", "vix_close", "vix_volume"]
        vix.to_csv(VIX_CSV, index=False)
        return len(vix)

    df = pd.read_csv(VIX_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    last_date = df["date"].max()

    fresh = _fetch_ticker_yahoo("^VIX", start=(last_date + timedelta(days=1)).strftime("%Y-%m-%d"))
    if fresh.empty:
        return 0

    fresh = fresh[fresh["date"] > last_date].reset_index(drop=True)
    if fresh.empty:
        return 0

    fresh = fresh.rename(columns={
        "open": "vix_open", "high": "vix_high", "low": "vix_low",
        "close": "vix_close", "volume": "vix_volume"
    })
    combined = pd.concat([df, fresh[df.columns]], ignore_index=True)
    combined = _normalize_date_column(combined)
    combined.to_csv(VIX_CSV, index=False)
    return len(fresh)


def _merge_vix_into_tecl():
    """Re-merge vix_close column in TECL.csv from VIX Daily.csv."""
    tecl = pd.read_csv(TECL_CSV, parse_dates=["date"])
    vix = pd.read_csv(VIX_CSV, parse_dates=["date"])

    # Drop old vix_close, re-merge fresh
    if "vix_close" in tecl.columns:
        tecl = tecl.drop(columns=["vix_close"])

    vix_slim = vix[["date", "vix_close"]].copy()
    tecl = tecl.merge(vix_slim, on="date", how="left")
    tecl = _normalize_date_column(tecl)
    tecl.to_csv(TECL_CSV, index=False)


def _refresh_fred(filename: str, series_id: str, col_name: str):
    """Refresh a FRED CSV by appending new observations."""
    path = os.path.join(TS_DIR, filename)
    if not os.path.exists(path):
        df = _fetch_fred_csv(series_id)
        if not df.empty:
            df.columns = ["date", col_name]
            df = _normalize_date_column(df)
            df.to_csv(path, index=False)
            print(f"[refresh] {filename}: downloaded {len(df)} rows")
        return

    existing = pd.read_csv(path, parse_dates=["date"])
    last_date = existing["date"].max()
    fresh = _fetch_fred_csv(series_id, start=(last_date + timedelta(days=1)).strftime("%Y-%m-%d"))
    if fresh.empty or len(fresh) == 0:
        print(f"[refresh] {filename}: up to date")
        return

    fresh.columns = ["date", col_name]
    fresh = fresh[fresh["date"] > last_date]
    if fresh.empty:
        print(f"[refresh] {filename}: up to date")
        return

    combined = pd.concat([existing, fresh], ignore_index=True)
    combined = _normalize_date_column(combined)
    combined.to_csv(path, index=False)
    print(f"[refresh] {filename}: +{len(fresh)} new rows")


def _migrate_legacy_tecl():
    """One-time migration: old TECL Price History CSV → TECL.csv with vix_close."""
    print("[data] Migrating legacy TECL CSV → TECL.csv...")
    df = pd.read_csv(_LEGACY_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)

    # Keep only standard columns
    keep = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in keep if c in df.columns]]

    # Merge VIX if available
    if os.path.exists(VIX_CSV):
        vix = pd.read_csv(VIX_CSV, parse_dates=["date"])
        if "vix_close" in vix.columns:
            df = df.merge(vix[["date", "vix_close"]], on="date", how="left")
    else:
        df["vix_close"] = np.nan

    df.to_csv(TECL_CSV, index=False)
    print(f"[data] Saved {TECL_CSV} ({len(df)} bars)")


# ─────────────────────────────────────────────────────────────────────
# Macro data merge — VIX, Treasury spread, Fed Funds, XLK, SGOV
# Shared across TECL / TQQQ / QQQ so strategies that use macro
# indicators can run unchanged in cross-asset validation.
# ─────────────────────────────────────────────────────────────────────

_TREASURY_CSV = os.path.join(TS_DIR, "treasury-spread-10y2y.csv")
_FED_FUNDS_CSV = os.path.join(TS_DIR, "fed-funds-rate.csv")


def _merge_macro_data(df: pd.DataFrame) -> pd.DataFrame:
    """Merge macro indicators into a price DataFrame by date (left join).

    Adds columns: vix_close, treasury_spread, fed_funds_rate, xlk_close, sgov_close.
    Missing data is NaN — strategies must handle gracefully.
    """
    # VIX (already in TECL but not TQQQ/QQQ)
    if "vix_close" not in df.columns:
        if os.path.exists(VIX_CSV):
            vix = pd.read_csv(VIX_CSV, parse_dates=["date"])
            vix.columns = [c.lower().strip() for c in vix.columns]
            vix = _normalize_date_column(vix)
            # VIX.csv uses "vix_close" column name
            vix_col = "vix_close" if "vix_close" in vix.columns else "close"
            if vix_col in vix.columns:
                vix = vix[["date", vix_col]].rename(columns={vix_col: "vix_close"})
                df = df.merge(vix, on="date", how="left")
        if "vix_close" not in df.columns:
            df["vix_close"] = np.nan

    # Treasury spread (10Y - 2Y)
    if os.path.exists(_TREASURY_CSV):
        ts = pd.read_csv(_TREASURY_CSV, parse_dates=["date"])
        ts.columns = [c.lower().strip() for c in ts.columns]
        ts = _normalize_date_column(ts)
        col = "yield_spread_10y2y" if "yield_spread_10y2y" in ts.columns else ts.columns[1]
        ts = ts[["date", col]].rename(columns={col: "treasury_spread"})
        df = df.merge(ts, on="date", how="left")
        df["treasury_spread"] = df["treasury_spread"].ffill()
    else:
        df["treasury_spread"] = np.nan

    # Fed Funds Rate
    if os.path.exists(_FED_FUNDS_CSV):
        ff = pd.read_csv(_FED_FUNDS_CSV, parse_dates=["date"])
        ff.columns = [c.lower().strip() for c in ff.columns]
        ff = _normalize_date_column(ff)
        col = "fed_funds_rate" if "fed_funds_rate" in ff.columns else ff.columns[1]
        ff = ff[["date", col]].rename(columns={col: "fed_funds_rate"})
        df = df.merge(ff, on="date", how="left")
        df["fed_funds_rate"] = df["fed_funds_rate"].ffill()
    else:
        df["fed_funds_rate"] = np.nan

    # XLK close (TECL underlying)
    if os.path.exists(XLK_CSV):
        xlk = pd.read_csv(XLK_CSV, parse_dates=["date"])
        xlk.columns = [c.lower().strip() for c in xlk.columns]
        xlk = _normalize_date_column(xlk)
        if "close" in xlk.columns:
            xlk = xlk[["date", "close"]].rename(columns={"close": "xlk_close"})
            df = df.merge(xlk, on="date", how="left")
    if "xlk_close" not in df.columns:
        df["xlk_close"] = np.nan

    # SGOV close
    if os.path.exists(SGOV_CSV):
        sgov = pd.read_csv(SGOV_CSV, parse_dates=["date"])
        sgov.columns = [c.lower().strip() for c in sgov.columns]
        sgov = _normalize_date_column(sgov)
        if "close" in sgov.columns:
            sgov_df = sgov[["date", "close"]].rename(columns={"close": "sgov_close"})
            df = df.merge(sgov_df, on="date", how="left")
    if "sgov_close" not in df.columns:
        df["sgov_close"] = np.nan

    return df


# ─────────────────────────────────────────────────────────────────────
# get_tecl_data() — main entry point for the optimizer
# ─────────────────────────────────────────────────────────────────────

def get_tecl_data(use_yfinance: bool = False) -> pd.DataFrame:
    """
    Load TECL data from local CSV. No API calls — all data is local.
    Run refresh_all() before the optimizer to update CSVs.

    The CSV includes synthetic 3x data from XLK (1998-2008) stitched
    to real TECL (2009-present), with vix_close merged in.
    """
    # Migrate legacy file if needed
    if not os.path.exists(TECL_CSV):
        if os.path.exists(_LEGACY_CSV):
            _migrate_legacy_tecl()
        else:
            raise FileNotFoundError(f"No TECL data found. Expected: {TECL_CSV}")

    df = pd.read_csv(TECL_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)
    print(f"[data] TECL: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")

    # Ensure vix_close exists
    if "vix_close" not in df.columns:
        df["vix_close"] = np.nan

    vix_count = df["vix_close"].notna().sum()
    print(f"[data] VIX: {vix_count}/{len(df)} dates matched")

    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"

    df = _merge_macro_data(df)
    return df


# ─────────────────────────────────────────────────────────────────────
# Cross-asset data loaders (for cross-asset validation)
# ─────────────────────────────────────────────────────────────────────

def get_tqqq_data() -> pd.DataFrame:
    """Load TQQQ data from local CSV (synthetic 1999-2010 + real 2010+)."""
    if not os.path.exists(TQQQ_CSV):
        raise FileNotFoundError(f"No TQQQ data. Expected: {TQQQ_CSV}")
    df = pd.read_csv(TQQQ_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"
    df = _merge_macro_data(df)
    print(f"[data] TQQQ: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


def get_qqq_data() -> pd.DataFrame:
    """Load QQQ data from local CSV."""
    if not os.path.exists(QQQ_CSV):
        raise FileNotFoundError(f"No QQQ data. Expected: {QQQ_CSV}")
    df = pd.read_csv(QQQ_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"
    df = _merge_macro_data(df)
    print(f"[data] QQQ: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


def get_sgov_data() -> pd.DataFrame:
    """Load SGOV data from local CSV, downloading an initial local copy if needed."""
    if not os.path.exists(SGOV_CSV):
        n = _refresh_or_create_ticker_csv(SGOV_CSV, "SGOV", start="2020-01-01")
        if n == 0 or not os.path.exists(SGOV_CSV):
            raise FileNotFoundError(f"No SGOV data. Expected: {SGOV_CSV}")
    df = pd.read_csv(SGOV_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)
    for col in ["open", "high", "low", "close", "volume"]:
        assert col in df.columns, f"Missing column: {col}"
    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]
    df["adj_close"] = df["adj_close"].fillna(df["close"])
    print(f"[data] SGOV: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


def get_3m_tbill_rate_data() -> pd.DataFrame:
    """Load the local 3-month Treasury bill rate proxy used for diagnostics/fallbacks."""
    if not os.path.exists(TBILL_3M_CSV):
        _refresh_fred("tbill-3m.csv", "DTB3", "rate_3m_tbill")
        if not os.path.exists(TBILL_3M_CSV):
            raise FileNotFoundError(f"No 3M T-bill rate data. Expected: {TBILL_3M_CSV}")
    df = pd.read_csv(TBILL_3M_CSV, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df = _normalize_date_column(df)
    print(f"[data] 3M T-Bill: {len(df)} rows, {df['date'].min().date()} to {df['date'].max().date()}")
    return df


# ─────────────────────────────────────────────────────────────────────
# Legacy compat — kept for imports in other scripts
# ─────────────────────────────────────────────────────────────────────

# Old CSV_PATH for backwards compat
CSV_PATH = TECL_CSV


def load_csv() -> pd.DataFrame:
    """Legacy wrapper — use get_tecl_data() instead."""
    return get_tecl_data(use_yfinance=False)


def fetch_yahoo(start: str = "2008-12-01", end: str | None = None) -> pd.DataFrame:
    """Fetch TECL from Yahoo Finance."""
    return _fetch_ticker_yahoo("TECL", start=start, end=end)


def fetch_vix(start: str = "1990-01-01", end: str | None = None) -> pd.DataFrame:
    """Fetch VIX from Yahoo Finance. Returns date + vix_close."""
    df = _fetch_ticker_yahoo("^VIX", start=start, end=end)
    if df.empty:
        return pd.DataFrame(columns=["date", "vix_close"])
    return df[["date", "close"]].rename(columns={"close": "vix_close"})


def build_synthetic_tecl(start: str = "1998-01-01", end: str | None = None,
                         anchor_price: float = 10.0) -> pd.DataFrame:
    """Build synthetic 3x leveraged TECL data from XLK."""
    xlk = _fetch_ticker_yahoo("XLK", start=start, end=end)
    if xlk.empty:
        print("[data] WARNING: Could not fetch XLK for synthetic TECL")
        return pd.DataFrame()

    daily_expense = 0.0095 / 252
    xlk_close = xlk["close"].values.astype(np.float64)
    xlk_open = xlk["open"].values.astype(np.float64)
    xlk_high = xlk["high"].values.astype(np.float64)
    xlk_low = xlk["low"].values.astype(np.float64)
    n = len(xlk_close)

    daily_ret = np.zeros(n)
    synth_ret = np.zeros(n)
    for i in range(1, n):
        daily_ret[i] = xlk_close[i] / xlk_close[i - 1] - 1
        synth_ret[i] = 3 * daily_ret[i] - daily_expense

    synth_close = np.ones(n)
    for i in range(1, n):
        synth_close[i] = synth_close[i - 1] * (1 + synth_ret[i])

    scale = anchor_price / synth_close[-1] if synth_close[-1] != 0 else 1.0
    synth_close *= scale

    xlk_close_safe = np.where(xlk_close > 0, xlk_close, 1.0)
    df = pd.DataFrame({
        "date": xlk["date"].values,
        "open": synth_close * (xlk_open / xlk_close_safe),
        "high": synth_close * (xlk_high / xlk_close_safe),
        "low": synth_close * (xlk_low / xlk_close_safe),
        "close": synth_close,
        "volume": xlk["volume"].values,
    })
    return _normalize_date_column(df)


if __name__ == "__main__":
    # When run directly: refresh everything then show summary
    refresh_all()
    df = get_tecl_data()
    print(f"\nLoaded {len(df)} bars")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print(df.tail())

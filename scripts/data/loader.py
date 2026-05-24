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
from io import StringIO

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
TECL_DISTRIBUTIONS_CSV = os.path.join(TS_DIR, "TECL_distributions.csv")
CBOE_VIX_HISTORY_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
TECL_SYNTHETIC_FINANCING_DRAG_ANNUAL = 0.01897

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
        seg_id.loc[mask] = sid
        src_sym.loc[mask] = sym
        src_kind.loc[mask] = kind
        model_v.loc[mask] = mv
        prev_end = end_ts

    df["is_synthetic"] = (src_kind == "synthetic-leveraged").astype(bool)
    df["source_symbol"] = src_sym
    df["source_kind"] = src_kind
    df["synthetic_model_version"] = model_v
    df["stitch_segment"] = seg_id.astype("Int64")
    return df


def _provenance_series_equal(left: pd.Series, right: pd.Series, column: str) -> bool:
    """Compare provenance columns across CSV-read and in-memory dtypes."""
    if column == "is_synthetic":
        return left.astype(bool).equals(right.astype(bool))
    if column == "stitch_segment":
        left_num = pd.to_numeric(left, errors="raise").astype("Int64")
        right_num = pd.to_numeric(right, errors="raise").astype("Int64")
        return left_num.equals(right_num)
    left_text = left.fillna("").astype(str)
    right_text = right.fillna("").astype(str)
    return left_text.equals(right_text)


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

    updated = _apply_stitch_plan(df, plan)
    needs_write = any(c not in df.columns for c in PROVENANCE_COLUMNS)
    if not needs_write:
        needs_write = any(
            not _provenance_series_equal(df[c], updated[c], c)
            for c in PROVENANCE_COLUMNS
        )

    if needs_write:
        updated.to_csv(csv_path, index=False)
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
    df["date"] = pd.to_datetime(df["date"], format="mixed")
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
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        raw_values = df["value"].astype("string").str.strip()
        missing = raw_values.isna() | raw_values.isin(["", "."])
        values = pd.to_numeric(raw_values.mask(missing), errors="coerce")
        invalid = values.isna() & ~missing
        if invalid.any():
            bad_values = raw_values[invalid].head(3).tolist()
            raise ValueError(f"FRED {series_id} contained non-numeric values: {bad_values}")
        df["value"] = values
        df = df.dropna(subset=["value"]).reset_index(drop=True)
        df = _normalize_date_column(df)
        return df
    except Exception as e:
        print(f"[data] FRED fetch failed for {series_id}: {e}")
        return pd.DataFrame(columns=["date", "value"])


def _fetch_vix_cboe() -> pd.DataFrame:
    """Fetch official Cboe VIX history and normalize to local VIX.csv schema."""
    try:
        import requests

        resp = requests.get(CBOE_VIX_HISTORY_URL, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
        df.columns = [c.lower().strip() for c in df.columns]
        _require_columns(df, ["date", "open", "high", "low", "close"], "Cboe VIX history")
        df = df.rename(
            columns={
                "open": "vix_open",
                "high": "vix_high",
                "low": "vix_low",
                "close": "vix_close",
            }
        )
        df["vix_volume"] = 0.0
        df = df[["date", "vix_open", "vix_high", "vix_low", "vix_close", "vix_volume"]]
        df = _normalize_date_column(df)
        return df
    except Exception as e:
        print(f"[data] Cboe VIX fetch failed: {e}")
        return pd.DataFrame(columns=["date", "vix_open", "vix_high", "vix_low", "vix_close", "vix_volume"])


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
    for col in df.columns:
        if col not in fresh.columns:
            fresh[col] = np.nan

    # Preserve the existing CSV schema. Provenance columns are filled by the
    # stitch-plan migration after append, not by Yahoo's raw payload.
    combined = pd.concat([df[df.columns], fresh[df.columns]], ignore_index=True)
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
    Updates files in place. Refreshes append new bars; the one-time legacy
    TECL migration creates TECL.csv from the legacy source if needed.
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
    migrate_provenance()

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
    """Refresh official Cboe VIX history and save to VIX.csv.

    VIX is calculated by Cboe, so the official Cboe history is the canonical
    source. Rewriting the small full file avoids Yahoo-vs-Cboe drift and
    catches historical revisions deterministically.
    """
    fresh = _fetch_vix_cboe()
    if fresh.empty:
        return 0

    if os.path.exists(VIX_CSV):
        existing = pd.read_csv(VIX_CSV, parse_dates=["date"])
        existing.columns = [c.lower().strip() for c in existing.columns]
        existing = _normalize_date_column(existing)
        if existing.equals(fresh):
            return 0
        old_dates = set(existing["date"])
        new_dates = set(fresh["date"])
        changed_dates = old_dates ^ new_dates
        overlap = existing.merge(fresh, on="date", how="inner", suffixes=("_old", "_new"))
        for col in ("vix_open", "vix_high", "vix_low", "vix_close"):
            changed_dates.update(overlap.loc[overlap[f"{col}_old"] != overlap[f"{col}_new"], "date"])
        changed_count = len(changed_dates)
    else:
        changed_count = len(fresh)

    fresh.to_csv(VIX_CSV, index=False)
    return changed_count


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


def _merge_tecl_distributions(df: pd.DataFrame) -> pd.DataFrame:
    """Attach TECL per-share cash distributions by ex-date."""
    out = df.copy()
    if "distribution" in out.columns:
        out = out.drop(columns=["distribution"])
    if not os.path.exists(TECL_DISTRIBUTIONS_CSV):
        out["distribution"] = 0.0
        return out

    dist = pd.read_csv(TECL_DISTRIBUTIONS_CSV, parse_dates=["ex_date"])
    dist.columns = [c.lower().strip() for c in dist.columns]
    if "amount" not in dist.columns:
        out["distribution"] = 0.0
        return out
    dist = dist.rename(columns={"ex_date": "date", "amount": "distribution"})
    dist = _normalize_date_column(dist[["date", "distribution"]])
    dist["distribution"] = pd.to_numeric(dist["distribution"], errors="coerce").fillna(0.0)
    out = out.merge(dist, on="date", how="left")
    out["distribution"] = out["distribution"].fillna(0.0)
    return out


def _apply_tecl_synthetic_financing_drag(
    df: pd.DataFrame,
    annual_drag: float = TECL_SYNTHETIC_FINANCING_DRAG_ANNUAL,
) -> pd.DataFrame:
    """Apply observed real-world financing/tracking drag to synthetic TECL rows.

    The persisted TECL.csv keeps the deterministic ideal 3x construction. At
    load time, default strategy runs use this realism adjustment so synthetic
    returns are not systematically flattered. The last synthetic bar is held
    fixed to preserve the real-data seam; prior synthetic prices are solved
    backward so each forward synthetic return is reduced by the daily drag.
    """
    if "is_synthetic" not in df.columns or annual_drag <= 0:
        return df

    out = df.copy()
    is_synthetic = out["is_synthetic"].astype("string").str.lower().isin(["true", "1"])
    idx = np.flatnonzero(is_synthetic.to_numpy())
    if len(idx) < 2:
        return out

    close = out["close"].astype(float).to_numpy()
    adjusted_close = close.copy()
    daily_drag = annual_drag / 252.0

    for pos in range(len(idx) - 2, -1, -1):
        i = idx[pos]
        j = idx[pos + 1]
        if j != i + 1 or close[i] <= 0:
            continue
        raw_ret = close[j] / close[i] - 1.0
        adjusted_ret = raw_ret - daily_drag
        if adjusted_ret <= -0.99:
            adjusted_ret = -0.99
        adjusted_close[i] = adjusted_close[j] / (1.0 + adjusted_ret)

    ratio = np.ones(len(out))
    valid = (close > 0) & is_synthetic.to_numpy()
    ratio[valid] = adjusted_close[valid] / close[valid]
    for col in ("open", "high", "low", "close"):
        out.loc[is_synthetic, col] = out.loc[is_synthetic, col].astype(float) * ratio[is_synthetic.to_numpy()]
    out["synthetic_financing_drag_bps_annual"] = 0.0
    out.loc[is_synthetic, "synthetic_financing_drag_bps_annual"] = annual_drag * 10_000
    return out


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


def _require_columns(df: pd.DataFrame, columns: list[str], source: str) -> None:
    """Fail fast when a local data file has drifted from its expected schema."""
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{source} missing required column(s): {', '.join(missing)}")


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
            _require_columns(vix, ["date", vix_col], "VIX.csv")
            vix = vix[["date", vix_col]].rename(columns={vix_col: "vix_close"})
            df = df.merge(vix, on="date", how="left")
        if "vix_close" not in df.columns:
            df["vix_close"] = np.nan

    # Treasury spread (10Y - 2Y)
    if os.path.exists(_TREASURY_CSV):
        ts = pd.read_csv(_TREASURY_CSV, parse_dates=["date"])
        ts.columns = [c.lower().strip() for c in ts.columns]
        ts = _normalize_date_column(ts)
        col = "yield_spread_10y2y"
        _require_columns(ts, ["date", col], "treasury-spread-10y2y.csv")
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
        col = "fed_funds_rate"
        _require_columns(ff, ["date", col], "fed-funds-rate.csv")
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
        _require_columns(xlk, ["date", "close"], "XLK.csv")
        xlk = xlk[["date", "close"]].rename(columns={"close": "xlk_close"})
        df = df.merge(xlk, on="date", how="left")
    if "xlk_close" not in df.columns:
        df["xlk_close"] = np.nan

    # SGOV close
    if os.path.exists(SGOV_CSV):
        sgov = pd.read_csv(SGOV_CSV, parse_dates=["date"])
        sgov.columns = [c.lower().strip() for c in sgov.columns]
        sgov = _normalize_date_column(sgov)
        _require_columns(sgov, ["date", "close"], "SGOV.csv")
        sgov_df = sgov[["date", "close"]].rename(columns={"close": "sgov_close"})
        df = df.merge(sgov_df, on="date", how="left")
    if "sgov_close" not in df.columns:
        df["sgov_close"] = np.nan

    return df


# ─────────────────────────────────────────────────────────────────────
# get_tecl_data() — main entry point for the optimizer
# ─────────────────────────────────────────────────────────────────────

def get_tecl_data(
    use_yfinance: bool = False,
    *,
    apply_synthetic_drag: bool = True,
) -> pd.DataFrame:
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

    if apply_synthetic_drag:
        df = _apply_tecl_synthetic_financing_drag(df)
    df = _merge_tecl_distributions(df)
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
    """Fetch VIX from official Cboe history. Returns date + vix_close."""
    df = _fetch_vix_cboe()
    if df.empty:
        return pd.DataFrame(columns=["date", "vix_close"])
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df[["date", "vix_close"]]


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

    if np.any(xlk_close <= 0):
        bad_idx = int(np.where(xlk_close <= 0)[0][0])
        bad_date = pd.Timestamp(xlk["date"].iloc[bad_idx]).date()
        raise ValueError(
            "XLK close must be positive for synthetic TECL build; "
            f"got {xlk_close[bad_idx]} on {bad_date}"
        )

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

    df = pd.DataFrame({
        "date": xlk["date"].values,
        "open": synth_close * (xlk_open / xlk_close),
        "high": synth_close * (xlk_high / xlk_close),
        "low": synth_close * (xlk_low / xlk_close),
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

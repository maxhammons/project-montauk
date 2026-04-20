#!/usr/bin/env python3
"""
Yahoo vs second-source cross-check (Phase 3a).

Fetches daily bars from a second data provider and aligns by date against
the local Yahoo-sourced CSV. Reports per-ticker:
  - bars matched
  - max relative close divergence
  - mean relative close divergence
  - count of days exceeding 0.5% close divergence (per Master Plan threshold)

Source resolution
-----------------
The script auto-selects which provider to query, in this order:

  1. Tiingo  (preferred — generous free tier, stable API, signup at tiingo.com)
       env: TIINGO_APIKEY        keyfile: ~/.tiingokey
  2. Stooq   (fallback — gated behind apikey since 2024)
       env: STOOQ_APIKEY         keyfile: ~/.stooqkey

If neither key is configured, exits with status 2 and prints setup help
(the data_quality runner reports it as SKIP, not FAIL).

CLI
---
  --source {tiingo,stooq,auto}   Override auto-detection (default: auto)
  --ticker NAME                  Specific ticker, or 'all' (default: all)
  --json                         Machine-readable output

Tiingo notes
------------
Tiingo's free tier covers daily EOD for ETFs/equities back decades. The VIX
index (^VIX) is index-class data, not in the free equity tier — for VIX,
Stooq is required. The script transparently falls back to Stooq for any
ticker the primary source can't serve, if a Stooq key is also configured.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/data/ -> scripts/ -> project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

DIVERGENCE_FLAG_PCT = 0.005  # 0.5% per-day flag (Master Plan)
SUMMARY_TARGET_PCT = 0.0001  # <0.01% on real data (Master Plan done criterion)
# Both Yahoo and Tiingo quote to $0.01; sub-cent absolute differences are
# quote-precision ties, not real divergence. Matters for sub-$1 bars (TECL
# 2008-2012 split-adjusted history).
VENDOR_PRECISION_USD = 0.01


# ─────────────────────────────────────────────────────────────────────
# Per-ticker symbol map
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CrossCheckSpec:
    name: str  # local CSV stem (e.g. "TECL")
    tiingo_symbol: str | None
    stooq_symbol: str | None
    real_start: str  # real Yahoo data starts on/after this date


SPECS = [
    CrossCheckSpec("TECL", "TECL", "tecl.us", "2008-12-17"),
    CrossCheckSpec("TQQQ", "TQQQ", "tqqq.us", "2010-02-11"),
    CrossCheckSpec("QQQ", "QQQ", "qqq.us", "1999-03-10"),
    CrossCheckSpec("XLK", "XLK", "xlk.us", "1998-12-22"),
    # ^VIX: index data. Tiingo free tier doesn't cover indices; needs Stooq.
    CrossCheckSpec("VIX", None, "^vix", "1990-01-01"),
]


# ─────────────────────────────────────────────────────────────────────
# Key resolution
# ─────────────────────────────────────────────────────────────────────


def _resolve_key(env_var: str, keyfile_name: str) -> str | None:
    if (k := os.environ.get(env_var)) and k.strip():
        return k.strip()
    keyfile = os.path.expanduser(f"~/{keyfile_name}")
    if os.path.exists(keyfile):
        with open(keyfile) as f:
            v = f.read().strip()
            return v or None
    return None


def _resolve_tiingo() -> str | None:
    return _resolve_key("TIINGO_APIKEY", ".tiingokey")


def _resolve_stooq() -> str | None:
    return _resolve_key("STOOQ_APIKEY", ".stooqkey")


def _print_setup_help() -> None:
    print()
    print("─" * 70)
    print("NO CROSS-CHECK API KEY CONFIGURED — cross-check skipped")
    print("─" * 70)
    print("Configure ONE of the following (Tiingo recommended):")
    print()
    print("  TIINGO  (preferred — 1000 req/day free, 30+ yr EOD coverage)")
    print("    1. Sign up free at https://www.tiingo.com")
    print("    2. Copy your API token from https://www.tiingo.com/account/api/token")
    print("    3. export TIINGO_APIKEY=YOURKEY      (shell env)")
    print("       echo YOURKEY > ~/.tiingokey       (keyfile)")
    print()
    print("  STOOQ   (fallback — required for VIX cross-check)")
    print("    1. Visit https://stooq.com/q/d/?s=tecl.us&get_apikey")
    print("    2. Solve the captcha and copy the apikey from the URL")
    print("    3. export STOOQ_APIKEY=YOURKEY       (shell env)")
    print("       echo YOURKEY > ~/.stooqkey        (keyfile)")
    print("─" * 70)


# ─────────────────────────────────────────────────────────────────────
# Tiingo fetch
# ─────────────────────────────────────────────────────────────────────


def _fetch_tiingo(
    symbol: str, apikey: str, start: str, end: str | None = None
) -> pd.DataFrame:
    import requests

    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    headers = {"Content-Type": "application/json", "Authorization": f"Token {apikey}"}
    url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"
    params = {
        "startDate": start,
        "endDate": end,
        "format": "json",
        "resampleFreq": "daily",
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 404:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    r.raise_for_status()
    payload = r.json()
    if not payload:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(payload)
    # Tiingo returns: date, open, high, low, close, volume, adjClose, adjHigh, adjLow,
    # adjOpen, adjVolume, divCash, splitFactor. We use adjClose (fully adjusted for
    # splits AND dividends) as our "close" for the cross-check — matches Yahoo's
    # adj_close convention, so the comparison works across full history regardless
    # of how many splits/dividends a ticker has had.
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    # Tiingo's `close` is the RAW trading price (never retroactively split-adjusted).
    # Tiingo's `adjClose` is fully-adjusted (splits + dividends).
    # Yahoo's `close` is retroactively SPLIT-adjusted but not dividend-adjusted.
    # To match Yahoo's convention we split-adjust Tiingo's raw close by the product
    # of all splitFactors strictly after each bar.
    if "splitFactor" in df.columns and "close" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)
        sf = df["splitFactor"].fillna(1.0).astype(float).to_numpy()
        # cum_future_splits[i] = product of sf[j] for all j > i
        cum_rev = np.cumprod(sf[::-1])
        # For bar i, future splits are indices i+1..n-1. In the reversed cumprod,
        # cum_rev[n-1-(i+1)] = product of sf[n-1] * sf[n-2] * ... * sf[i+1].
        # Equivalently: shift cum_rev by 1 and fill first position with 1.
        cum_future = np.empty_like(cum_rev)
        cum_future[:-1] = cum_rev[-2::-1]  # drop the last element of reversed cumprod
        cum_future[-1] = 1.0  # most recent bar has no future splits
        # Oops — index correction: we want cum_future[i] = product of sf[j] for j > i.
        # Easier: reverse the array, take cumprod with shift, reverse back.
        rev = sf[::-1].copy()
        rev_cum = np.concatenate(([1.0], np.cumprod(rev[:-1])))
        cum_future = rev_cum[::-1]
        df["close"] = df["close"].astype(float) / cum_future
    keep = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in keep if c in df.columns]]
    return (
        df.sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


# ─────────────────────────────────────────────────────────────────────
# Stooq fetch
# ─────────────────────────────────────────────────────────────────────


def _fetch_stooq(
    symbol: str, apikey: str, start: str, end: str | None = None
) -> pd.DataFrame:
    import requests
    from io import StringIO

    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    d1 = pd.Timestamp(start).strftime("%Y%m%d")
    d2 = pd.Timestamp(end).strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={symbol}&d1={d1}&d2={d2}&i=d&apikey={apikey}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    text = r.text.strip()
    if not text or text.lower().startswith(("get your apikey", "no data")):
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df = pd.read_csv(StringIO(text))
    df.columns = [c.lower().strip() for c in df.columns]
    if "date" not in df.columns or "close" not in df.columns:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    keep = [
        c for c in ("date", "open", "high", "low", "close", "volume") if c in df.columns
    ]
    return (
        df[keep]
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


# ─────────────────────────────────────────────────────────────────────
# Compare
# ─────────────────────────────────────────────────────────────────────


def _load_local(name: str) -> pd.DataFrame:
    """
    Load local CSV and normalize to a `close` column.

    Our local Yahoo `close` is retroactively split-adjusted (Yahoo applies
    splits historically to the close series). Tiingo's fetch is normalized
    to the same convention by _fetch_tiingo(). So here we just use `close`
    (or vix_close for VIX).
    """
    path = os.path.join(DATA_DIR, f"{name}.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df["date"] = df["date"].dt.normalize()
    if "close" in df.columns:
        out = df[["date", "close"]].copy()
    elif "vix_close" in df.columns:
        out = df[["date", "vix_close"]].rename(columns={"vix_close": "close"})
    else:
        raise ValueError(f"{name}: no close/vix_close column")
    return out.sort_values("date").reset_index(drop=True)


def _pick_source_for(
    spec: CrossCheckSpec, prefer: str, tiingo_key: str | None, stooq_key: str | None
) -> tuple[str, str, Callable, str] | None:
    """
    Resolve (source_name, symbol, fetch_fn, apikey) for a ticker, honoring
    the preferred order and per-ticker symbol availability.
    """
    order: list[str]
    if prefer == "tiingo":
        order = ["tiingo", "stooq"]
    elif prefer == "stooq":
        order = ["stooq", "tiingo"]
    else:  # auto
        order = ["tiingo", "stooq"]

    for src in order:
        if src == "tiingo" and tiingo_key and spec.tiingo_symbol:
            return ("tiingo", spec.tiingo_symbol, _fetch_tiingo, tiingo_key)
        if src == "stooq" and stooq_key and spec.stooq_symbol:
            return ("stooq", spec.stooq_symbol, _fetch_stooq, stooq_key)
    return None


def _compare_one(
    spec: CrossCheckSpec, prefer: str, tiingo_key: str | None, stooq_key: str | None
) -> dict:
    chosen = _pick_source_for(spec, prefer, tiingo_key, stooq_key)
    if chosen is None:
        return {
            "ticker": spec.name,
            "source": None,
            "symbol": None,
            "matched": 0,
            "status": "SKIP",
            "reason": "no provider available for this ticker",
            "max_div_pct": None,
            "mean_div_pct": None,
            "exception_days": None,
            "exception_dates": [],
        }
    src_name, symbol, fetch_fn, apikey = chosen

    local = _load_local(spec.name)
    real_start = pd.Timestamp(spec.real_start)
    local = local[local["date"] >= real_start].copy()

    fetch_start = (
        local["date"].min().strftime("%Y-%m-%d") if not local.empty else spec.real_start
    )
    fetch_end = local["date"].max().strftime("%Y-%m-%d") if not local.empty else None

    try:
        ext = fetch_fn(symbol, apikey, fetch_start, fetch_end)
    except Exception as e:
        return {
            "ticker": spec.name,
            "source": src_name,
            "symbol": symbol,
            "matched": 0,
            "status": "FAIL",
            "reason": f"{src_name} fetch failed: {e.__class__.__name__}: {e}",
            "max_div_pct": None,
            "mean_div_pct": None,
            "exception_days": None,
            "exception_dates": [],
        }

    if ext.empty:
        return {
            "ticker": spec.name,
            "source": src_name,
            "symbol": symbol,
            "matched": 0,
            "status": "FAIL",
            "reason": f"{src_name} returned empty",
            "max_div_pct": None,
            "mean_div_pct": None,
            "exception_days": None,
            "exception_dates": [],
        }

    m = local[["date", "close"]].merge(
        ext[["date", "close"]].rename(columns={"close": "ext_close"}),
        on="date",
        how="inner",
    )
    if m.empty:
        return {
            "ticker": spec.name,
            "source": src_name,
            "symbol": symbol,
            "matched": 0,
            "status": "FAIL",
            "reason": "no overlapping dates",
            "max_div_pct": None,
            "mean_div_pct": None,
            "exception_days": None,
            "exception_dates": [],
        }

    # Vendor cent-precision tie: both providers quote prices to $0.01. When the
    # two sources agree to within $0.01, the bars effectively match at quote
    # precision; the relative divergence metric blows up only because the
    # denominator price is tiny (e.g. TECL pre-2012 was sub-$1 split-adjusted,
    # so a $0.01 absolute tick = 3% relative noise). Treat absolute differences
    # ≤ $0.01 as zero divergence so this precision noise stops dominating the
    # summary stats.
    abs_diff = (m["close"] - m["ext_close"]).abs()
    rel_raw = (abs_diff / m["close"]).replace([np.inf, -np.inf], np.nan)
    rel = rel_raw.where(abs_diff > VENDOR_PRECISION_USD, 0.0).dropna()
    max_div = float(rel.max()) if not rel.empty else 0.0
    mean_div = float(rel.mean()) if not rel.empty else 0.0
    excs = m.loc[rel.index].assign(rel=rel)
    exception_mask = excs["rel"] > DIVERGENCE_FLAG_PCT
    exception_dates = excs.loc[exception_mask, "date"].dt.strftime("%Y-%m-%d").tolist()

    # Status logic: mean is the canonical agreement metric (Master Plan target
    # "<0.01% on real data"). Max divergence is hostage to individual outlier
    # bars — and historically TECL 2009's sub-$1 prices produced ~3% noise
    # purely from $0.01 quote precision. The cent-precision filter above
    # absorbs that; remaining divergence is real provider disagreement.
    if max_div > 0.05 or mean_div > 0.002:
        status = "FAIL"
    elif mean_div > SUMMARY_TARGET_PCT:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "ticker": spec.name,
        "source": src_name,
        "symbol": symbol,
        "matched": len(m),
        "status": status,
        "reason": "",
        "max_div_pct": max_div,
        "mean_div_pct": mean_div,
        "exception_days": int(exception_mask.sum()),
        "exception_dates": exception_dates[:20],
    }


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--source",
        choices=["auto", "tiingo", "stooq"],
        default="auto",
        help="Preferred provider (default: auto = tiingo, fallback stooq)",
    )
    ap.add_argument("--ticker", default="all", help="Specific ticker, or 'all'")
    ap.add_argument(
        "--json", action="store_true", help="Print JSON instead of human-readable"
    )
    args = ap.parse_args(argv)

    tiingo_key = _resolve_tiingo()
    stooq_key = _resolve_stooq()

    if not tiingo_key and not stooq_key:
        if args.json:
            print(
                json.dumps(
                    {"status": "SKIP", "reason": "no TIINGO_APIKEY or STOOQ_APIKEY"}
                )
            )
        else:
            _print_setup_help()
        return 2

    specs = (
        SPECS if args.ticker == "all" else [s for s in SPECS if s.name == args.ticker]
    )
    if not specs:
        print(f"Unknown ticker: {args.ticker}")
        return 1

    if not args.json:
        print("=" * 70)
        print(
            f"DATA CROSS-CHECK — Yahoo (local) vs second source (prefer={args.source})"
        )
        print(
            f"  Tiingo key: {'set' if tiingo_key else 'not set'}    "
            f"Stooq key: {'set' if stooq_key else 'not set'}"
        )
        print("=" * 70)

    results = []
    overall_fail = False
    for s in specs:
        r = _compare_one(s, args.source, tiingo_key, stooq_key)
        results.append(r)
        if r["status"] == "FAIL":
            overall_fail = True

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 1 if overall_fail else 0

    for r in results:
        src = f"{r['source']}:{r['symbol']}" if r["source"] else "no-provider"
        print(f"\n  {r['ticker']:<6} ({src})")
        if r["matched"] == 0:
            print(f"    STATUS: {r['status']} — {r['reason']}")
            continue
        print(f"    matched bars:    {r['matched']}")
        print(f"    max divergence:  {r['max_div_pct'] * 100:.4f}%")
        print(f"    mean divergence: {r['mean_div_pct'] * 100:.4f}%")
        print(
            f"    exception days:  {r['exception_days']} (>{DIVERGENCE_FLAG_PCT * 100:.1f}%)"
        )
        if r["exception_dates"]:
            shown = ", ".join(r["exception_dates"][:5])
            extra = (
                f" (+{len(r['exception_dates']) - 5} more)"
                if len(r["exception_dates"]) > 5
                else ""
            )
            print(f"      first dates:   {shown}{extra}")
        print(f"    STATUS: {r['status']}")

    print()
    print("=" * 70)
    print(
        "DONE — "
        + (
            "FAIL: at least one ticker exceeded fail threshold"
            if overall_fail
            else "all checks within tolerance"
        )
    )
    print("=" * 70)
    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main())

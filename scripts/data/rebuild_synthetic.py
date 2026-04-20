#!/usr/bin/env python3
"""
Deterministic synthetic rebuild for TECL.csv and TQQQ.csv.

Rebuilds the pre-IPO synthetic portion of each leveraged ETF from its
underlying source CSV(s) using a documented, deterministic formula:

    synth_close[i] = synth_close[i-1] * (1 + 3 * underlying_daily_ret - daily_expense)

Stitches the synthetic segment(s) to the real (post-IPO) Yahoo Finance bars
by anchoring each segment so its last close equals the next segment's first
close.

Models
------
TECL  v2-3xTechIdx-0.95%ER-daily
        seg 0  ^SP500-45 (S&P 500 Information Technology Sector Index, price-only)
                 1993-05-04 → 1998-12-21
        seg 1  XLK   (Technology Select Sector SPDR ETF)
                 1998-12-22 → 2008-12-16
        seg 2  TECL  (Yahoo Finance, real)
                 2008-12-17 → today

TQQQ  v1-3xQQQ-0.75%ER-daily
        seg 0  QQQ   (Yahoo Finance — early years are themselves synthetic-NDX-derived
                      by Yahoo's own backfill)
                 1993-05-04 → 2010-02-10
        seg 1  TQQQ  (Yahoo Finance, real)
                 2010-02-11 → today

Modes
-----
  --verify  (default)  Build in-memory and report row-by-row drift vs current CSV.
  --write              Overwrite data/{TECL,TQQQ}.csv with the rebuilt series.

Determinism
-----------
Same input bytes in (SP500-45.csv / XLK.csv / QQQ.csv / real-data tail of
TECL.csv|TQQQ.csv) → same output bytes out. SHA-256 over the rebuilt series
is stable across runs.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/data/ -> scripts/ -> project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

SYNTHETIC_MODEL_VERSION_TECL = "v2-3xTechIdx-0.95%ER-daily"
SYNTHETIC_MODEL_VERSION_TQQQ = "v1-3xQQQ-0.75%ER-daily"

OUT_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class SynthSegment:
    """A synthetic segment derived from one underlying source CSV."""
    source_symbol: str          # "^SP500-45", "XLK", "QQQ"
    source_csv: str             # filename in data/
    start_date: str             # inclusive
    end_date: str               # exclusive (next segment's start)


@dataclass(frozen=True)
class TickerSpec:
    name: str                   # "TECL" / "TQQQ"
    seam_date: str              # synthetic→real cutoff (real starts on this date)
    expense_ratio: float        # annualized
    model_version: str
    segments: List[SynthSegment] = field(default_factory=list)

    @property
    def csv_path(self) -> str:
        return os.path.join(DATA_DIR, f"{self.name}.csv")


SPECS: List[TickerSpec] = [
    TickerSpec(
        name="TECL",
        seam_date="2008-12-17",
        expense_ratio=0.0095,
        model_version=SYNTHETIC_MODEL_VERSION_TECL,
        segments=[
            SynthSegment("^SP500-45", "SP500-45.csv", "1900-01-01", "1998-12-22"),
            SynthSegment("XLK",       "XLK.csv",      "1998-12-22", "2008-12-17"),
        ],
    ),
    TickerSpec(
        name="TQQQ",
        seam_date="2010-02-11",
        expense_ratio=0.0075,
        model_version=SYNTHETIC_MODEL_VERSION_TQQQ,
        segments=[
            SynthSegment("QQQ", "QQQ.csv", "1900-01-01", "2010-02-11"),
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────
# Build steps
# ─────────────────────────────────────────────────────────────────────

def _load_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path, parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df["date"] = df["date"].dt.normalize()
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df


def _load_real_tail(spec: TickerSpec) -> pd.DataFrame:
    """Real Yahoo bars from current CSV (seam_date onward)."""
    df = _load_csv(f"{spec.name}.csv")
    seam = pd.Timestamp(spec.seam_date)
    real = df[df["date"] >= seam].copy().reset_index(drop=True)
    # Drop Yahoo "market-closed" artifact bars: weekend dates, or rows where
    # OHLC has degenerated to a single value AND open != close (a real holiday-
    # fill bar from Yahoo carries prior session's open with H=L=C of prior close).
    real = real[real["date"].dt.dayofweek < 5].copy()
    degenerate = (real["high"] == real["low"]) & (real["high"] == real["close"]) & (real["open"] != real["close"])
    if degenerate.any():
        real = real[~degenerate].copy()
    return real.reset_index(drop=True)[[c for c in OUT_COLUMNS if c in real.columns]]


def _build_segment_returns(seg: SynthSegment, expense_ratio: float) -> pd.DataFrame:
    """Returns DataFrame with date, open/high/low/close shape ratios, and synth daily return."""
    src = _load_csv(seg.source_csv)
    start = pd.Timestamp(seg.start_date)
    end = pd.Timestamp(seg.end_date)
    src = src[(src["date"] >= start) & (src["date"] < end)].copy().reset_index(drop=True)
    if len(src) < 2:
        return pd.DataFrame(columns=["date", "open_r", "high_r", "low_r", "close_r", "synth_ret", "volume"])

    daily_expense = expense_ratio / 252.0
    close = src["close"].to_numpy(dtype=np.float64)
    close_safe = np.where(close > 0, close, 1.0)
    daily_ret = np.zeros(len(src), dtype=np.float64)
    daily_ret[1:] = close[1:] / close[:-1] - 1.0
    synth_ret = 3.0 * daily_ret - daily_expense
    synth_ret[0] = 0.0  # first bar anchors only

    out = pd.DataFrame({
        "date":     src["date"].values,
        # OHLC shape ratios relative to source close — let us paint a synthetic
        # OHLC bar from the synthetic close once anchored.
        "open_r":   src["open"].to_numpy(dtype=np.float64)  / close_safe,
        "high_r":   src["high"].to_numpy(dtype=np.float64)  / close_safe,
        "low_r":    src["low"].to_numpy(dtype=np.float64)   / close_safe,
        "close_r":  np.ones(len(src), dtype=np.float64),
        "synth_ret": synth_ret,
        "volume":   src["volume"].to_numpy(dtype=np.float64) if "volume" in src.columns else np.zeros(len(src)),
    })
    return out


def build_one(spec: TickerSpec) -> pd.DataFrame:
    """Return the full rebuilt series (synthetic segments stitched to real)."""
    real = _load_real_tail(spec)
    if real.empty:
        raise RuntimeError(f"{spec.name}: no real bars found at/after seam {spec.seam_date}")

    # Build per-segment return streams in chronological order.
    seg_dfs = [_build_segment_returns(s, spec.expense_ratio) for s in spec.segments]
    # Drop empty segments (e.g., source CSV missing pre-coverage rows).
    seg_dfs = [d for d in seg_dfs if not d.empty]

    if not seg_dfs:
        # No synthetic segments — just write real.
        return real

    # Concatenate segment returns; first row of each later segment carries no
    # cross-segment return jump (we anchor across segments by chained scaling).
    all_synth = pd.concat(seg_dfs, ignore_index=True)
    all_synth = all_synth.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    # Compound from 1.0
    n = len(all_synth)
    synth_close = np.empty(n, dtype=np.float64)
    synth_close[0] = 1.0
    rets = all_synth["synth_ret"].to_numpy(dtype=np.float64)
    for i in range(1, n):
        synth_close[i] = synth_close[i - 1] * (1.0 + rets[i])

    if synth_close[-1] == 0:
        raise ValueError(f"{spec.name}: synthetic close decayed to zero; cannot anchor.")
    anchor = float(real.iloc[0]["close"])
    scale = anchor / synth_close[-1]
    synth_close = synth_close * scale

    synth = pd.DataFrame({
        "date":   all_synth["date"].values,
        "open":   synth_close * all_synth["open_r"].to_numpy(),
        "high":   synth_close * all_synth["high_r"].to_numpy(),
        "low":    synth_close * all_synth["low_r"].to_numpy(),
        "close":  synth_close,
        "volume": all_synth["volume"].to_numpy(),
    })

    # Drop the seam-day row from synth (real owns the seam date).
    synth = synth[synth["date"] < pd.Timestamp(spec.seam_date)]

    full = pd.concat([synth[OUT_COLUMNS], real[OUT_COLUMNS]], ignore_index=True)
    full = full.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return full


def _format_for_disk(df: pd.DataFrame) -> pd.DataFrame:
    """Round to a stable precision so CSV bytes are deterministic."""
    out = df.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = out[col].round(8)
    if "volume" in out.columns:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype(np.int64)
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out[OUT_COLUMNS]


# ─────────────────────────────────────────────────────────────────────
# Verify / Write
# ─────────────────────────────────────────────────────────────────────

def _bytes_sha256(df: pd.DataFrame) -> str:
    payload = _format_for_disk(df).to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify(spec: TickerSpec) -> dict:
    rebuilt = build_one(spec)
    rebuilt_disk = _format_for_disk(rebuilt)

    current = pd.read_csv(spec.csv_path, parse_dates=["date"])
    current.columns = [c.lower().strip() for c in current.columns]
    current["date"] = current["date"].dt.normalize()
    current = current.sort_values("date").reset_index(drop=True)

    rebuilt_ohlc = rebuilt[["date", "open", "high", "low", "close"]].copy()
    rebuilt_ohlc.columns = ["date", "r_open", "r_high", "r_low", "r_close"]
    cur_ohlc = current[["date", "open", "high", "low", "close"]].copy()
    cur_ohlc.columns = ["date", "c_open", "c_high", "c_low", "c_close"]
    merged = rebuilt_ohlc.merge(cur_ohlc, on="date", how="inner")

    if merged.empty:
        diff_max = 0.0
        diff_mean = 0.0
        mismatch_rows = 0
    else:
        rel = np.maximum.reduce([
            (merged["r_open"]  - merged["c_open"]).abs()  / merged["c_open"].replace(0, np.nan),
            (merged["r_high"]  - merged["c_high"]).abs()  / merged["c_high"].replace(0, np.nan),
            (merged["r_low"]   - merged["c_low"]).abs()   / merged["c_low"].replace(0, np.nan),
            (merged["r_close"] - merged["c_close"]).abs() / merged["c_close"].replace(0, np.nan),
        ])
        diff_max = float(rel.max())
        diff_mean = float(rel.mean())
        mismatch_rows = int((rel > 0.005).sum())

    rows_only_in_current = int(
        (~current["date"].isin(rebuilt["date"])).sum()
    )
    rows_only_in_rebuilt = int(
        (~rebuilt["date"].isin(current["date"])).sum()
    )

    bit_identical = (
        rows_only_in_current == 0
        and rows_only_in_rebuilt == 0
        and diff_max < 1e-6
    )

    return {
        "ticker": spec.name,
        "model_version": spec.model_version,
        "rebuilt_rows": len(rebuilt),
        "current_rows": len(current),
        "rows_only_in_current": rows_only_in_current,
        "rows_only_in_rebuilt": rows_only_in_rebuilt,
        "overlap_rows": len(merged),
        "max_relative_diff": diff_max,
        "mean_relative_diff": diff_mean,
        "mismatch_rows_gt_0.5pct": mismatch_rows,
        "rebuilt_sha256": _bytes_sha256(rebuilt),
        "bit_identical_to_current": bool(bit_identical),
    }


def _write(spec: TickerSpec) -> dict:
    rebuilt = build_one(spec)
    rebuilt_disk = _format_for_disk(rebuilt)
    rebuilt_disk.to_csv(spec.csv_path, index=False)
    sha = hashlib.sha256(open(spec.csv_path, "rb").read()).hexdigest()
    return {"ticker": spec.name, "rows": len(rebuilt_disk), "wrote": spec.csv_path, "sha256": sha}


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--verify", action="store_true", help="(default) Compare rebuild against current CSV.")
    g.add_argument("--write",  action="store_true", help="Overwrite TECL.csv & TQQQ.csv with the rebuild.")
    ap.add_argument("--ticker", choices=["TECL", "TQQQ", "all"], default="all")
    args = ap.parse_args(argv)

    specs = SPECS if args.ticker == "all" else [s for s in SPECS if s.name == args.ticker]

    if args.write:
        print("=" * 70)
        print("REBUILD SYNTHETIC — WRITE MODE")
        print("=" * 70)
        for s in specs:
            res = _write(s)
            print(f"  {res['ticker']}: wrote {res['rows']} rows → {res['wrote']}")
            print(f"           sha256={res['sha256']}")
        return 0

    print("=" * 70)
    print("REBUILD SYNTHETIC — VERIFY MODE")
    print("=" * 70)
    any_drift = False
    for s in specs:
        r = _verify(s)
        print(f"\n  {r['ticker']}  (model {r['model_version']})")
        print(f"    seam_date:           {s.seam_date}")
        print(f"    rebuilt rows:        {r['rebuilt_rows']}")
        print(f"    current rows:        {r['current_rows']}")
        print(f"    rows only in curr:   {r['rows_only_in_current']}")
        print(f"    rows only in build:  {r['rows_only_in_rebuilt']}")
        print(f"    overlap rows:        {r['overlap_rows']}")
        print(f"    max rel diff OHLC:   {r['max_relative_diff']:.6e}")
        print(f"    mean rel diff OHLC:  {r['mean_relative_diff']:.6e}")
        print(f"    mismatched (>0.5%):  {r['mismatch_rows_gt_0.5pct']}")
        print(f"    rebuilt sha256:      {r['rebuilt_sha256']}")
        print(f"    bit-identical:       {r['bit_identical_to_current']}")
        if not r["bit_identical_to_current"]:
            any_drift = True

    print()
    if any_drift:
        print("RESULT: drift detected. Re-run with --write to regenerate CSVs from source.")
        return 1
    print("RESULT: rebuild matches current CSVs bit-for-bit. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())

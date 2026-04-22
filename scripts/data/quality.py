#!/usr/bin/env python3
"""
Consolidated data-quality runner (Phase 3f).

Two scopes:

  LOCAL — audit_all() default. No external network. Cheap + deterministic.
          Safe as a per-validation precondition.
  AUDIT — audit_all(include_crosscheck=True), or CLI `--full`. Adds external
          cross-source verification (Tiingo/Stooq). Run as a periodic audit,
          NOT on every validation pass (rate limits → spurious FAILs).

Local tests (always run)
------------------------
  formula_residual           Row-by-row synthetic residual vs deterministic rebuild
  seam_continuity            Synthetic→real boundary continuity (anchor exact)
  manifest_checksum          data/manifest.json sha256 vs disk
  duplicate_dates            Append/merge bug detection
  weekend_holiday_presence   Weekend bars on real data → synthetic-bug signal
  date_gaps                  Gap detection (allow market holidays)
  ohlc_inversion             High<Low / High<Close / Low>Close
  nan_zero_close             Corrupt-bar detection
  split_detection            >50% close change without 5x volume spike
  date_monotonicity          Sort order
  volume_sanity              Zero volume on real ETF dates
  provenance_columns         Synthetic / real provenance fields present
  formula_reverification     Per-segment 3× leverage residual vs source

Audit-only tests (opt-in)
-------------------------
  crosscheck_divergence      Yahoo (local) vs Tiingo/Stooq cross-check

Each check returns: {test, status, scope, summary, details}
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import pandas as pd

# Paths (this file lives at scripts/data/quality.py)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))    # scripts/data/
SCRIPTS_DIR = os.path.dirname(_THIS_DIR)                   # scripts/
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)                # project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")              # project/data/

sys.path.insert(0, SCRIPTS_DIR)
from data.loader import (  # noqa: E402
    PROVENANCE_COLUMNS,
    _TECL_STITCH_PLAN,
    _TQQQ_STITCH_PLAN,
)
from data.audit import reverify_formula  # noqa: E402
from data.manifest import (  # noqa: E402
    MANIFEST_PATH,
    verify_against_disk,
)
from data.rebuild_synthetic import (  # noqa: E402
    SPECS as REBUILD_SPECS,
    _verify as _rebuild_verify,
)

# Tuning thresholds (Master Plan)
SPLIT_PCT = 0.50
SPLIT_VOL_MULT = 5.0
ZERO_VOL_THRESHOLD = 0.05  # >5% zero-volume real ETF bars → WARN
SEAM_CONTINUITY_TOL = 1e-6  # rebuilt synth's last close vs real's first close
RESIDUAL_TOL_BPS_BUILD = 1e-5  # reconstruction residual cap
RESIDUAL_TOL_BPS_FORMULA = 1e-3  # per-segment formula residual cap (1bp)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _result(test: str, status: str, scope: str = "", summary: str = "", details: dict | None = None) -> dict:
    return {"test": test, "status": status, "scope": scope, "summary": summary, "details": details or {}}


def _load(name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, name), parse_dates=["date"])
    df.columns = [c.lower().strip() for c in df.columns]
    df["date"] = df["date"].dt.normalize()
    return df.sort_values("date").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────

def test_formula_residual_vs_rebuild() -> list[dict]:
    """Compare current CSV bytes vs deterministic rebuild."""
    out = []
    for spec in REBUILD_SPECS:
        try:
            r = _rebuild_verify(spec)
        except Exception as e:
            out.append(_result("formula_residual", "FAIL", spec.name, f"rebuild errored: {e}"))
            continue
        if r["bit_identical_to_current"]:
            out.append(_result(
                "formula_residual", "PASS", spec.name,
                f"matches rebuild ({r['overlap_rows']} rows; max rel diff {r['max_relative_diff']:.2e})",
                details=r,
            ))
        elif r["max_relative_diff"] < 1e-3 and r["mismatch_rows_gt_0.5pct"] == 0:
            out.append(_result(
                "formula_residual", "WARN", spec.name,
                f"close to rebuild but bytes differ (max rel {r['max_relative_diff']:.2e})",
                details=r,
            ))
        else:
            out.append(_result(
                "formula_residual", "FAIL", spec.name,
                f"drift from rebuild: max rel diff {r['max_relative_diff']:.2e}, "
                f"{r['mismatch_rows_gt_0.5pct']} rows >0.5%",
                details=r,
            ))
    return out


def test_seam_continuity() -> list[dict]:
    """Last synth close vs first real close at the documented seam."""
    out = []
    seam_for = {"TECL": "2008-12-17", "TQQQ": "2010-02-11"}
    for name, seam in seam_for.items():
        df = _load(f"{name}.csv")
        seam_ts = pd.Timestamp(seam)
        synth = df[df["date"] < seam_ts]
        real = df[df["date"] >= seam_ts]
        if synth.empty or real.empty:
            out.append(_result("seam_continuity", "FAIL", name, "empty synth or real segment"))
            continue
        last_synth = float(synth.iloc[-1]["close"])
        first_real = float(real.iloc[0]["close"])
        rel = abs(last_synth - first_real) / first_real if first_real else float("inf")
        det = {"last_synth_close": last_synth, "first_real_close": first_real, "rel_gap": rel}
        if rel < SEAM_CONTINUITY_TOL:
            out.append(_result("seam_continuity", "PASS", name,
                               f"clean stitch at {seam} (gap {rel:.2e})", det))
        elif rel < 0.05:
            out.append(_result("seam_continuity", "WARN", name,
                               f"non-trivial stitch gap at {seam} ({rel*100:.2f}%)", det))
        else:
            out.append(_result("seam_continuity", "FAIL", name,
                               f"large stitch gap at {seam} ({rel*100:.2f}%)", det))
    return out


def test_manifest_checksum() -> list[dict]:
    out = []
    if not os.path.exists(MANIFEST_PATH):
        return [_result("manifest_checksum", "FAIL", "manifest.json", "missing — run data_manifest.py build")]
    results = verify_against_disk()
    fails = [r for r in results if r["status"] == "FAIL"]
    if fails:
        out.append(_result("manifest_checksum", "FAIL", "all",
                           f"{len(fails)} files drifted from manifest",
                           {"fails": fails}))
    else:
        out.append(_result("manifest_checksum", "PASS", "all",
                           f"{len(results)} files match manifest"))
    return out


def test_duplicate_dates() -> list[dict]:
    out = []
    for name in ("TECL.csv", "TQQQ.csv", "XLK.csv", "QQQ.csv", "VIX.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        dups = df["date"].duplicated().sum()
        if dups == 0:
            out.append(_result("duplicate_dates", "PASS", name, "no duplicates"))
        else:
            out.append(_result("duplicate_dates", "FAIL", name, f"{dups} duplicate dates", {"count": int(dups)}))
    return out


def test_weekend_holiday_presence() -> list[dict]:
    """Real data should have no weekend bars."""
    out = []
    seam_for = {"TECL.csv": "2008-12-17", "TQQQ.csv": "2010-02-11", "XLK.csv": "1998-12-22"}
    for name, seam in seam_for.items():
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        real = df[df["date"] >= pd.Timestamp(seam)]
        weekends = real[real["date"].dt.dayofweek >= 5]
        if len(weekends) == 0:
            out.append(_result("weekend_holiday_presence", "PASS", name, "no weekend bars in real data"))
        else:
            out.append(_result("weekend_holiday_presence", "FAIL", name,
                               f"{len(weekends)} weekend bars in real data",
                               {"sample_dates": weekends["date"].dt.strftime("%Y-%m-%d").head(5).tolist()}))
    return out


# Known historical NYSE/NASDAQ multi-day closures. These produce >5-day gaps
# but are documented market events, not missing data. Add new entries here when
# (rare) future closures occur.
#   2001-09-17: Markets reopened on this date after the Sept 11 attacks closed
#               them Sept 11-14. Gap from 2001-09-10 to 2001-09-17 = 7 days.
KNOWN_LONG_CLOSURES = {
    pd.Timestamp("2001-09-17"),
}


def test_date_gaps() -> list[dict]:
    """Gap detection — allow market holidays (~9-10/yr) and documented closures."""
    out = []
    for name in ("TECL.csv", "TQQQ.csv", "XLK.csv", "QQQ.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        diffs = df["date"].diff().dt.days
        # Big gaps: > 5 calendar days = likely missing data
        big_mask = diffs > 5
        big_dates = df.loc[big_mask, "date"]
        unexplained = [d for d in big_dates if pd.Timestamp(d) not in KNOWN_LONG_CLOSURES]
        if len(unexplained) == 0:
            out.append(_result("date_gaps", "PASS", name,
                               "no unexplained >5-day gaps (known closures allowlisted)"))
        elif len(unexplained) <= 5:
            out.append(_result("date_gaps", "WARN", name,
                               f"{len(unexplained)} unexplained gaps >5d (likely long holidays)"))
        else:
            out.append(_result("date_gaps", "FAIL", name,
                               f"{len(unexplained)} unexplained gaps >5d — investigate"))
    return out


def test_ohlc_inversion() -> list[dict]:
    out = []
    for name in ("TECL.csv", "TQQQ.csv", "XLK.csv", "QQQ.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        bad_hl = (df["high"] < df["low"]).sum()
        bad_hc = (df["high"] < df["close"]).sum()
        bad_lc = (df["low"] > df["close"]).sum()
        bad_ho = (df["high"] < df["open"]).sum()
        bad_lo = (df["low"] > df["open"]).sum()
        total = int(bad_hl + bad_hc + bad_lc + bad_ho + bad_lo)
        det = {"high<low": int(bad_hl), "high<close": int(bad_hc), "low>close": int(bad_lc),
               "high<open": int(bad_ho), "low>open": int(bad_lo)}
        if total == 0:
            out.append(_result("ohlc_inversion", "PASS", name, "OHLC consistent", det))
        else:
            out.append(_result("ohlc_inversion", "FAIL", name, f"{total} OHLC inversions", det))
    return out


def test_nan_zero_close() -> list[dict]:
    out = []
    for name in ("TECL.csv", "TQQQ.csv", "XLK.csv", "QQQ.csv", "VIX.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        close = df["close"] if "close" in df.columns else df.get("vix_close")
        if close is None:
            continue
        nan_close = int(close.isna().sum())
        zero_close = int((close <= 0).sum())
        det = {"nan_close": nan_close, "zero_or_neg_close": zero_close}
        if nan_close == 0 and zero_close == 0:
            out.append(_result("nan_zero_close", "PASS", name, "no NaN/zero closes", det))
        else:
            out.append(_result("nan_zero_close", "FAIL", name,
                               f"{nan_close} NaN, {zero_close} ≤0 closes", det))
    return out


def test_split_detection() -> list[dict]:
    """>50% close change without 5x volume spike → likely unsplit data.

    Only applied to real (non-synthetic) bars. Synthetic bars are computed
    from the underlying with documented multipliers (3x daily for TECL/TQQQ),
    so a 50% synthetic move is just leverage on a ~17% real-underlying move
    (e.g. TQQQ synthetic 2001-01-03 = Fed surprise rate cut +14% NDX rally).
    These cannot be unrecorded splits because we control the calculation.
    """
    out = []
    for name in ("TECL.csv", "TQQQ.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        df["close_pct"] = df["close"].pct_change().abs()
        df["vol_ratio"] = df["volume"] / df["volume"].rolling(20).median()
        if "is_synthetic" in df.columns:
            # Coerce to bool — stored values may be True/False, 0/1, or "True"/"False"
            is_syn = df["is_synthetic"].astype(str).str.lower().isin(("true", "1"))
            real_mask = ~is_syn
        else:
            real_mask = pd.Series(True, index=df.index)
        suspect = df[(df["close_pct"] > SPLIT_PCT) & (df["vol_ratio"] < SPLIT_VOL_MULT) & real_mask]
        if len(suspect) == 0:
            out.append(_result("split_detection", "PASS", name,
                               "no suspicious one-day moves on real bars"))
        else:
            out.append(_result("split_detection", "WARN", name,
                               f"{len(suspect)} suspicious one-day moves on real bars",
                               {"sample_dates": suspect["date"].dt.strftime("%Y-%m-%d").head(5).tolist()}))
    return out


def test_date_monotonicity() -> list[dict]:
    out = []
    for name in ("TECL.csv", "TQQQ.csv", "XLK.csv", "QQQ.csv", "VIX.csv"):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        if df["date"].is_monotonic_increasing:
            out.append(_result("date_monotonicity", "PASS", name, "monotonic increasing"))
        else:
            out.append(_result("date_monotonicity", "FAIL", name, "non-monotonic dates"))
    return out


def test_volume_sanity() -> list[dict]:
    """Real ETF dates should have nonzero volume most of the time."""
    out = []
    seam_for = {"TECL.csv": "2008-12-17", "TQQQ.csv": "2010-02-11", "XLK.csv": "1998-12-22"}
    for name, seam in seam_for.items():
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            continue
        df = _load(name)
        real = df[df["date"] >= pd.Timestamp(seam)]
        if real.empty:
            continue
        zero_vol = int((real["volume"] == 0).sum())
        frac = zero_vol / len(real)
        det = {"zero_vol_rows": zero_vol, "fraction": frac}
        if frac < ZERO_VOL_THRESHOLD:
            out.append(_result("volume_sanity", "PASS", name,
                               f"{zero_vol} zero-vol bars ({frac*100:.2f}%)", det))
        else:
            out.append(_result("volume_sanity", "WARN", name,
                               f"{zero_vol} zero-vol bars ({frac*100:.2f}%)", det))
    return out


def test_provenance_columns() -> list[dict]:
    """Every leveraged-ETF row carries the Phase 3b provenance schema."""
    out = []
    for name, plan in (("TECL.csv", _TECL_STITCH_PLAN), ("TQQQ.csv", _TQQQ_STITCH_PLAN)):
        path = os.path.join(DATA_DIR, name)
        if not os.path.exists(path):
            out.append(_result("provenance_columns", "FAIL", name, "missing CSV"))
            continue
        df = _load(name)
        missing = [c for c in PROVENANCE_COLUMNS if c not in df.columns]
        if missing:
            out.append(_result("provenance_columns", "FAIL", name,
                               f"missing columns: {missing}"))
            continue
        # Spot-check segment ID assignment matches plan.
        expected_segments = sorted({sid for sid, *_ in plan})
        actual_segments = sorted(df["stitch_segment"].dropna().unique().tolist())
        if expected_segments == actual_segments:
            out.append(_result("provenance_columns", "PASS", name,
                               f"all 5 columns present, segments {actual_segments}"))
        else:
            out.append(_result("provenance_columns", "WARN", name,
                               f"segment mismatch: expected {expected_segments}, got {actual_segments}"))
    return out


def test_crosscheck_divergence() -> list[dict]:
    """Phase 3a — Yahoo vs Tiingo (preferred) / Stooq (fallback). SKIP if no API key."""
    cmd = [sys.executable, os.path.join(_THIS_DIR, "crosscheck.py"), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return [_result("stooq_divergence", "FAIL", "all", "subprocess timed out")]
    if proc.returncode == 2:
        return [_result("crosscheck_divergence", "SKIP", "all",
                        "no TIINGO_APIKEY/STOOQ_APIKEY — see scripts/data_crosscheck.py header")]
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return [_result("crosscheck_divergence", "FAIL", "all",
                        f"bad JSON from data_crosscheck.py (rc={proc.returncode})",
                        {"stdout": proc.stdout[:500], "stderr": proc.stderr[:500]})]
    if isinstance(payload, dict) and payload.get("status") == "SKIP":
        return [_result("crosscheck_divergence", "SKIP", "all", payload.get("reason", ""))]
    out = []
    for r in payload:
        src = r.get("source") or "n/a"
        out.append(_result("crosscheck_divergence", r["status"], f"{r['ticker']} via {src}",
                           f"max div {((r['max_div_pct'] or 0) * 100):.4f}%, "
                           f"{r['exception_days'] or 0} exception days",
                           r))
    return out


def test_formula_reverification() -> list[dict]:
    """Phase 3e — per-segment formula residual vs source."""
    res = reverify_formula()
    out = []
    for k, v in res.items():
        if v["max_abs_err"] < RESIDUAL_TOL_BPS_FORMULA:
            out.append(_result("formula_reverification", "PASS", k,
                               f"max abs daily-return residual {v['max_abs_err']:.2e}", v))
        else:
            out.append(_result("formula_reverification", "FAIL", k,
                               f"residual {v['max_abs_err']:.2e} exceeds {RESIDUAL_TOL_BPS_FORMULA:.0e}", v))
    return out


# ─────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────

# Local tests (no external network calls) — safe to run on every validation pass.
LOCAL_TESTS = [
    ("formula_residual_vs_rebuild", test_formula_residual_vs_rebuild),
    ("seam_continuity",             test_seam_continuity),
    ("manifest_checksum",           test_manifest_checksum),
    ("duplicate_dates",             test_duplicate_dates),
    ("weekend_holiday_presence",    test_weekend_holiday_presence),
    ("date_gaps",                   test_date_gaps),
    ("ohlc_inversion",              test_ohlc_inversion),
    ("nan_zero_close",              test_nan_zero_close),
    ("split_detection",             test_split_detection),
    ("date_monotonicity",           test_date_monotonicity),
    ("volume_sanity",               test_volume_sanity),
    ("provenance_columns",          test_provenance_columns),
    ("formula_reverification",      test_formula_reverification),
]

# Audit-only tests — external API calls, run explicitly during periodic audits,
# not on every validation pipeline pass. Keeps validation cheap + deterministic
# and avoids spurious FAILs when external sources rate-limit.
AUDIT_TESTS = [
    ("crosscheck_divergence",       test_crosscheck_divergence),
]

# Backward-compat alias. Equivalent to LOCAL_TESTS + AUDIT_TESTS in declaration
# order. Callers that reference ALL_TESTS still work; prefer LOCAL_TESTS or
# AUDIT_TESTS in new code to make scope explicit.
ALL_TESTS = (
    LOCAL_TESTS[:12]
    + AUDIT_TESTS
    + LOCAL_TESTS[12:]
)


def audit_all(include_crosscheck: bool = False) -> list[dict]:
    """Run data-quality tests and return a flat list of result dicts.

    By default runs only LOCAL_TESTS — no network calls. Pass
    `include_crosscheck=True` to also run AUDIT_TESTS (cross-source verification
    via Tiingo/Stooq). Cross-source audit is a periodic integrity check, not
    a per-validation precondition.
    """
    flat: list[dict] = []
    tests = list(LOCAL_TESTS)
    if include_crosscheck:
        tests = tests + list(AUDIT_TESTS)
    for _name, fn in tests:
        try:
            flat.extend(fn())
        except Exception as e:
            flat.append(_result(_name, "FAIL", "<runner>", f"test errored: {e}"))
    return flat


def summarize(results: list[dict]) -> dict:
    by_status: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {
        "total": len(results),
        "pass": by_status["PASS"],
        "warn": by_status["WARN"],
        "fail": by_status["FAIL"],
        "skip": by_status["SKIP"],
    }


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

_STATUS_COLOR = {"PASS": "\x1b[32m", "WARN": "\x1b[33m", "FAIL": "\x1b[31m", "SKIP": "\x1b[90m"}
_RESET = "\x1b[0m"


def _print(results: list[dict], use_color: bool) -> None:
    print("=" * 78)
    print(f"{'TEST':<32} {'STATUS':<6} {'SCOPE':<22} SUMMARY")
    print("=" * 78)
    last_test = None
    for r in results:
        c = _STATUS_COLOR.get(r["status"], "") if use_color else ""
        end = _RESET if use_color else ""
        sep = "  " if r["test"] == last_test else "\n"
        print(f"{r['test']:<32} {c}{r['status']:<6}{end} {r['scope']:<22} {r['summary']}")
        last_test = r["test"]
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--no-color", action="store_true", help="Disable color")
    ap.add_argument(
        "--full",
        action="store_true",
        help="Run the full audit including external cross-source checks "
             "(Tiingo/Stooq). Off by default — cross-source verification is a "
             "periodic audit, not a per-validation precondition.",
    )
    args = ap.parse_args(argv)

    results = audit_all(include_crosscheck=args.full)
    summary = summarize(results)

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, indent=2, default=str))
    else:
        _print(results, use_color=(not args.no_color and sys.stdout.isatty()))
        print("─" * 78)
        print(f"SUMMARY  pass={summary['pass']}  warn={summary['warn']}  "
              f"fail={summary['fail']}  skip={summary['skip']}  total={summary['total']}")

    return 1 if summary["fail"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

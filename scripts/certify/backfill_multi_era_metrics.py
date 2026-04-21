#!/usr/bin/env python3
"""
Backfill multi-era metrics onto every leaderboard entry.

Problem: The default `fitness` and `share_multiple` on the leaderboard are
computed on the full 1993-2026 history, which includes the synthetic pre-2008
dotcom era. Empirically that period dominates outperformance — all current
leaderboard strategies underperform buy-and-hold on post-2008-12-17 real data.
Max wants a dual view: keep full-history optimization (crash insurance) AND see
how each strategy performs in the modern (real) era where the market looks
different.

Solution: add `multi_era` block to each leaderboard entry with sub-scores on:
  - full:    1993-05-04 → now (current leaderboard metric)
  - real:    2008-12-17 → now (TECL inception; excludes synthetic crash data)
  - modern:  2015-01-01 → now (post-QE, retail-algo era)
  - decayed_fitness: full-history fitness weighted by `exp(-λ * years_ago)`
                     per-trade, so a 2025 trade counts ~3× a 2000 trade.

Nothing is removed; existing `fitness` and `metrics` fields stay the primary
leaderboard key. These are diagnostic columns for the UI to display alongside.

Usage:
    python3 scripts/certify/backfill_multi_era_metrics.py
    python3 scripts/certify/backfill_multi_era_metrics.py --lambda 0.07

Run once to populate the leaderboard. Future promotions can hook into
`enrich_entry_with_multi_era()` to stamp the block at promotion time.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(THIS_DIR)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from data.loader import get_tecl_data  # noqa: E402
from engine.strategy_engine import Indicators, backtest  # noqa: E402
from engine.regime_helpers import score_regime_capture  # noqa: E402
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS  # noqa: E402
from search.evolve import fitness as compute_fitness  # noqa: E402

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")

ERAS = (
    ("full", None, "1993-05-04 → now (includes synthetic pre-2008)"),
    ("real", "2008-12-17", "TECL inception → now (real data only)"),
    ("modern", "2015-01-01", "post-QE retail-algo era → now"),
)

DEFAULT_DECAY_LAMBDA = 0.07  # half-life ≈ 10 years


def _era_metrics(
    df: pd.DataFrame, ind: Indicators, name: str, params: dict, tier: str
) -> dict:
    """Backtest + fitness on a given data slice. Returns {} on error."""
    try:
        fn = STRATEGY_REGISTRY[name]
    except KeyError:
        return {"error": f"strategy {name!r} not in REGISTRY"}
    try:
        entries, exits, labels = fn(ind, params)
        r = backtest(
            df,
            entries,
            exits,
            labels,
            cooldown_bars=params.get("cooldown", 0),
            strategy_name=name,
        )
    except Exception as exc:
        return {"error": f"backtest failed: {exc}"[:200]}
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    try:
        r.regime_score = score_regime_capture(r.trades, close, dates)
    except Exception:
        pass
    fit = compute_fitness(r, tier=tier)
    return {
        "share_multiple": float(r.share_multiple),
        "fitness": float(fit),
        "cagr_pct": float(r.cagr_pct),
        "max_dd_pct": float(r.max_drawdown_pct),
        "trades": int(r.num_trades),
        "trades_per_year": float(r.trades_per_year),
        "bars": int(len(df)),
        "start_date": str(df["date"].iloc[0])[:10],
        "end_date": str(df["date"].iloc[-1])[:10],
    }


def _decayed_fitness(
    df: pd.DataFrame,
    ind: Indicators,
    name: str,
    params: dict,
    tier: str,
    decay_lambda: float,
) -> dict:
    """Compute a fitness variant where each trade's PnL is weighted by
    `exp(-lambda * years_ago)` relative to the terminal bar.

    Approach: run the normal backtest, then synthesize a time-weighted
    share_multiple by replacing each trade's contribution with a decayed
    version. Terminal date = most recent bar in df.
    """
    try:
        fn = STRATEGY_REGISTRY[name]
        entries, exits, labels = fn(ind, params)
        r = backtest(
            df,
            entries,
            exits,
            labels,
            cooldown_bars=params.get("cooldown", 0),
            strategy_name=name,
        )
    except Exception as exc:
        return {"error": f"backtest failed: {exc}"[:200]}

    if not r.trades:
        return {"fitness_decayed": 0.0, "lambda": decay_lambda, "trades": 0}

    terminal = pd.to_datetime(df["date"].iloc[-1])
    # Weighted sum of log-returns: replace trade pnl contribution with
    # exp(-lambda * years_ago) * ln(1 + pnl_pct/100). Then translate back to
    # a compounded share-multiple equivalent.
    weighted_log_return = 0.0
    total_weight = 0.0
    for t in r.trades:
        exit_dt = pd.to_datetime(t.exit_date)
        years_ago = max(0.0, (terminal - exit_dt).days / 365.25)
        w = math.exp(-decay_lambda * years_ago)
        pnl = float(getattr(t, "pnl_pct", 0.0)) / 100.0
        if pnl > -0.999:
            weighted_log_return += w * math.log(1.0 + pnl)
        total_weight += w

    # Normalize: if all weights were 1.0 this equals the raw log return sum.
    # We map back through exp() to get a pseudo-share-multiple, then reuse the
    # full-history fitness penalties (DD, HHI) unweighted.
    pseudo_share = math.exp(weighted_log_return) if total_weight > 0 else 0.0

    # Approximate fitness: use the standard fitness formula with pseudo_share
    # substituted. DD and HHI penalties come from the original full-history
    # backtest (these are population-level characteristics, not time-decayed).
    if r.num_trades < 5 or r.trades_per_year > 5.0 or pseudo_share <= 0:
        fit_decayed = 0.0
    else:
        rs = r.regime_score
        try:
            rs_ok = rs is not None
        except Exception:
            rs_ok = False
        if not rs_ok:
            r.regime_score = score_regime_capture(
                r.trades,
                df["close"].values.astype(np.float64),
                df["date"].values,
            )
            rs = r.regime_score
        hhi = rs.hhi if rs and rs.hhi is not None else 0
        if hhi > 0.35:
            fit_decayed = 0.0
        else:
            hhi_penalty = max(0.5, 1.0 - max(0, hhi - 0.15) * 3)
            dd_penalty = max(0.3, 1.0 - r.max_drawdown_pct / 120.0)
            regime_mult = 1.0
            if rs:
                regime_mult = 0.4 + 0.6 * min(1.0, rs.composite / 0.7)
            fit_decayed = pseudo_share * hhi_penalty * dd_penalty * regime_mult

    return {
        "fitness_decayed": float(fit_decayed),
        "pseudo_share": float(pseudo_share),
        "lambda": float(decay_lambda),
        "half_life_years": float(math.log(2) / decay_lambda)
        if decay_lambda > 0
        else None,
        "trades": int(r.num_trades),
    }


def enrich_entry_with_multi_era(
    entry: dict, df_full: pd.DataFrame, decay_lambda: float = DEFAULT_DECAY_LAMBDA
) -> dict:
    """Compute the multi_era block for a single leaderboard entry.

    Returns the block dict (does not mutate the input entry).
    """
    name = entry.get("strategy")
    params = entry.get("params", {})
    tier = entry.get("tier") or STRATEGY_TIERS.get(name, "T1")

    block: dict = {"computed_at": datetime.utcnow().isoformat() + "Z", "eras": {}}
    for era_key, cutoff, desc in ERAS:
        if cutoff is None:
            df_slice = df_full
        else:
            df_slice = df_full[df_full["date"] >= cutoff].reset_index(drop=True)
        ind_slice = Indicators(df_slice)
        era_block = _era_metrics(df_slice, ind_slice, name, params, tier)
        era_block["description"] = desc
        block["eras"][era_key] = era_block

    # Decayed fitness on the full history
    ind_full = Indicators(df_full)
    block["decayed"] = _decayed_fitness(
        df_full, ind_full, name, params, tier, decay_lambda
    )
    return block


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill multi-era metrics onto every leaderboard entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--lambda",
        dest="decay_lambda",
        type=float,
        default=DEFAULT_DECAY_LAMBDA,
        help=f"Exponential decay rate for decayed_fitness (default: {DEFAULT_DECAY_LAMBDA}, half-life ~10y)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print but do not write back to leaderboard.json",
    )
    args = parser.parse_args()

    print(f"[backfill] Reading {LEADERBOARD_PATH}")
    with open(LEADERBOARD_PATH) as f:
        lb = json.load(f)
    print(f"[backfill] {len(lb)} leaderboard entries")
    print(
        f"[backfill] λ = {args.decay_lambda} (half-life ≈ {math.log(2) / args.decay_lambda:.1f} years)"
    )

    print("[backfill] Loading TECL data...")
    df_full = get_tecl_data()
    print(
        f"[backfill] Full history: {len(df_full)} bars, {df_full['date'].iloc[0]} → {df_full['date'].iloc[-1]}"
    )
    print()

    # Header
    header = f"{'#':<3} {'Strategy':<22} " + " ".join(
        f"{label:>12}"
        for label in ("Full Share", "Real Share", "Modern Sh", "Decayed Fit")
    )
    print(header)
    print("─" * len(header))

    for i, entry in enumerate(lb, 1):
        block = enrich_entry_with_multi_era(
            entry, df_full, decay_lambda=args.decay_lambda
        )
        entry["multi_era"] = block
        eras = block["eras"]

        def fmt_share(era_key: str) -> str:
            s = eras.get(era_key, {}).get("share_multiple")
            return f"{s:.2f}x" if s is not None else "err"

        dec = block.get("decayed", {}).get("fitness_decayed")
        dec_s = f"{dec:.2f}" if dec is not None else "err"
        name = entry.get("strategy", "?")
        print(
            f"#{i:<2} {name:<22} "
            f"{fmt_share('full'):>12} {fmt_share('real'):>12} {fmt_share('modern'):>12} {dec_s:>12}"
        )

    if args.dry_run:
        print()
        print("[backfill] Dry run — no write.")
        return 0

    print()
    print(f"[backfill] Writing enriched leaderboard back to {LEADERBOARD_PATH}")
    with open(LEADERBOARD_PATH, "w") as f:
        json.dump(lb, f, indent=2, default=str)
    print("[backfill] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

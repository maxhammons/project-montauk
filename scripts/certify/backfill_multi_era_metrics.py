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
from datetime import datetime, timezone

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

MARKET_REGIMES = (
    {
        "key": "early_tech_bull",
        "label": "Early tech bull",
        "kind": "bull",
        "start": "1993-05-04",
        "end": "1998-10-07",
        "description": "Pre-dotcom secular tech expansion before the LTCM washout.",
    },
    {
        "key": "dotcom_meltup",
        "label": "Dot-com melt-up",
        "kind": "bull",
        "start": "1998-10-08",
        "end": "2000-03-24",
        "description": "Late-90s internet mania into the Nasdaq blow-off top.",
    },
    {
        "key": "dotcom_bust",
        "label": "Dot-com bust / Y2K fallout",
        "kind": "bear",
        "start": "2000-03-27",
        "end": "2002-10-09",
        "description": "Post-Y2K unwind and tech bust from the 2000 peak to the 2002 trough.",
    },
    {
        "key": "credit_bull",
        "label": "Housing / credit bull",
        "kind": "bull",
        "start": "2002-10-10",
        "end": "2007-10-31",
        "description": "Expansionary pre-GFC bull market after the dot-com reset.",
    },
    {
        "key": "gfc_crash",
        "label": "GFC crash",
        "kind": "crash",
        "start": "2007-11-01",
        "end": "2009-03-09",
        "description": "Global Financial Crisis drawdown from the 2007 peak to the March 2009 low.",
    },
    {
        "key": "qe_recovery",
        "label": "QE recovery",
        "kind": "recovery",
        "start": "2009-03-10",
        "end": "2011-04-29",
        "description": "Post-GFC recovery driven by emergency policy and early QE.",
    },
    {
        "key": "euro_crisis_chop",
        "label": "Euro crisis / downgrade chop",
        "kind": "chop",
        "start": "2011-05-02",
        "end": "2012-11-15",
        "description": "US downgrade, euro-sovereign stress, and high-volatility range behavior.",
    },
    {
        "key": "secular_tech_bull",
        "label": "Secular tech bull",
        "kind": "bull",
        "start": "2012-11-16",
        "end": "2018-09-20",
        "description": "Long low-rate expansion before the 2018 tightening drawdown.",
    },
    {
        "key": "tightening_trade_war",
        "label": "Tightening / trade-war drawdown",
        "kind": "bear",
        "start": "2018-09-21",
        "end": "2018-12-24",
        "description": "Q4 2018 selloff under tightening fears and trade-war pressure.",
    },
    {
        "key": "pre_covid_bull",
        "label": "Pre-COVID melt-up",
        "kind": "bull",
        "start": "2018-12-26",
        "end": "2020-02-19",
        "description": "Late-cycle rally after the 2018 reset and before the pandemic shock.",
    },
    {
        "key": "covid_crash",
        "label": "COVID crash",
        "kind": "crash",
        "start": "2020-02-20",
        "end": "2020-03-23",
        "description": "Pandemic panic drawdown into the March 2020 low.",
    },
    {
        "key": "stimulus_bull",
        "label": "Stimulus / reopening bull",
        "kind": "bull",
        "start": "2020-03-24",
        "end": "2021-11-19",
        "description": "Liquidity-driven rebound and reopening bull market.",
    },
    {
        "key": "inflation_hiking_bear",
        "label": "Inflation / hiking bear",
        "kind": "bear",
        "start": "2021-11-22",
        "end": "2022-10-12",
        "description": "Inflation shock and aggressive rate hikes driving a deep tech drawdown.",
    },
    {
        "key": "ai_bull",
        "label": "AI / disinflation bull",
        "kind": "bull",
        "start": "2022-10-13",
        "end": "2024-07-10",
        "description": "AI-led rebound with easing inflation expectations.",
    },
    {
        "key": "policy_volatility",
        "label": "Late-cycle policy volatility",
        "kind": "policy",
        "start": "2024-07-11",
        "end": None,
        "description": "Recent market shaped more by policy shocks and macro-volatility than a clean trend.",
    },
)

DEFAULT_DECAY_LAMBDA = 0.07  # half-life ≈ 10 years
CRITICAL_REGIME_FLOOR = 0.85
CRITICAL_REGIME_KEYS = {
    "dotcom_bust",
    "gfc_crash",
    "covid_crash",
    "inflation_hiking_bear",
    "tightening_trade_war",
}

REGIME_SCORE_COMPONENTS = {
    "bull_participation": {
        "label": "Bull participation",
        "kinds": {"bull"},
        "anchors": (0.05, 0.20, 0.60),
        "weight": 0.20,
    },
    "recovery_capture": {
        "label": "Recovery capture",
        "kinds": {"recovery"},
        "anchors": (0.10, 0.30, 0.75),
        "weight": 0.15,
    },
    "bear_survival": {
        "label": "Bear survival",
        "kinds": {"bear"},
        "anchors": (0.90, 1.20, 3.00),
        "weight": 0.25,
    },
    "crash_defense": {
        "label": "Crash defense",
        "kinds": {"crash"},
        "anchors": (1.00, 1.50, 4.00),
        "weight": 0.30,
    },
    "policy_resilience": {
        "label": "Policy resilience",
        "kinds": {"policy", "chop"},
        "anchors": (0.85, 1.0, 1.15),
        "weight": 0.10,
    },
}


def _slice_df(
    df: pd.DataFrame,
    start: str | None,
    end: str | None = None,
) -> pd.DataFrame:
    if start is None:
        sliced = df
    else:
        sliced = df[df["date"] >= start]
    if end is not None:
        sliced = sliced[sliced["date"] <= end]
    return sliced.reset_index(drop=True)


def _interp_score(value: float, low: float, mid: float, high: float) -> float:
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    if value <= mid:
        span = max(mid - low, 1e-9)
        return 0.5 * (value - low) / span
    span = max(high - mid, 1e-9)
    return 0.5 + 0.5 * (value - mid) / span


def _geo_mean(values: list[float], floor: float = 0.01) -> float:
    usable = [max(float(v), floor) for v in values if v is not None]
    if not usable:
        return 0.0
    return math.exp(sum(math.log(v) for v in usable) / len(usable))


def _era_metrics(
    df: pd.DataFrame, ind: Indicators, name: str, params: dict, tier: str
) -> dict:
    """Backtest + fitness on a given data slice. Returns {} on error."""
    if len(df) < 2:
        return {"error": "window too short"}
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
    bah_return_pct = ((close[-1] / close[0]) - 1.0) * 100.0 if close[0] > 0 else 0.0
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
        "bah_return_pct": float(bah_return_pct),
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

    block: dict = {
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "eras": {},
    }
    for era_key, cutoff, desc in ERAS:
        df_slice = _slice_df(df_full, cutoff)
        if len(df_slice) < 2:
            era_block = {"error": "window too short"}
        else:
            ind_slice = Indicators(df_slice)
            era_block = _era_metrics(df_slice, ind_slice, name, params, tier)
        era_block["description"] = desc
        block["eras"][era_key] = era_block

    block["regimes"] = []
    for regime in MARKET_REGIMES:
        df_slice = _slice_df(df_full, regime["start"], regime.get("end"))
        if len(df_slice) < 2:
            regime_block = {"error": "window too short"}
        else:
            ind_slice = Indicators(df_slice)
            regime_block = _era_metrics(df_slice, ind_slice, name, params, tier)
        regime_block.update(
            {
                "key": regime["key"],
                "label": regime["label"],
                "kind": regime["kind"],
                "description": regime["description"],
            }
        )
        block["regimes"].append(regime_block)

    block["regime_summary"] = summarize_regime_performance(block["regimes"])

    # Decayed fitness on the full history
    ind_full = Indicators(df_full)
    block["decayed"] = _decayed_fitness(
        df_full, ind_full, name, params, tier, decay_lambda
    )
    return block


def summarize_regime_performance(regimes: list[dict]) -> dict:
    """Aggregate named regime reruns into a compact robustness profile."""
    components = {}
    critical_failures = []
    for regime in regimes:
        key = regime.get("key")
        share = regime.get("share_multiple")
        if key in CRITICAL_REGIME_KEYS and share is not None and float(share) < CRITICAL_REGIME_FLOOR:
            critical_failures.append(
                {
                    "key": key,
                    "label": regime.get("label"),
                    "share_multiple": float(share),
                    "kind": regime.get("kind"),
                }
            )

    weighted_sum = 0.0
    total_weight = 0.0
    for key, spec in REGIME_SCORE_COMPONENTS.items():
        members = [
            regime for regime in regimes
            if regime.get("kind") in spec["kinds"]
            and regime.get("share_multiple") is not None
        ]
        aggregate_share = _geo_mean([float(regime["share_multiple"]) for regime in members])
        score = _interp_score(aggregate_share, *spec["anchors"]) if members else 0.0
        components[key] = {
            "label": spec["label"],
            "score": float(score),
            "aggregate_share_multiple": float(aggregate_share),
            "count": len(members),
            "weight": float(spec["weight"]),
        }
        if members:
            weighted_sum += score * spec["weight"]
            total_weight += spec["weight"]

    overall = 0.0
    if total_weight > 0:
        overall = weighted_sum / total_weight

    weakest = min(
        (
            {
                "key": regime.get("key"),
                "label": regime.get("label"),
                "share_multiple": float(regime.get("share_multiple")),
                "kind": regime.get("kind"),
            }
            for regime in regimes
            if regime.get("share_multiple") is not None
        ),
        key=lambda item: item["share_multiple"],
        default=None,
    )

    return {
        "overall_score": float(overall),
        "critical_floor": float(CRITICAL_REGIME_FLOOR),
        "critical_guardrail_passed": len(critical_failures) == 0,
        "critical_failures": critical_failures,
        "components": components,
        "weakest_regime": weakest,
    }


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

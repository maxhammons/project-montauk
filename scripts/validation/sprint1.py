#!/usr/bin/env python3
"""
Sprint 1 validation: Tier 1 overfitting checks against the leaderboard.

Tests (6 total):
  1.1 Deflated Regime Score — Monte Carlo calibrated Beta-EVT
  1.2 Exit-Boundary Proximity — are strategy exits clustered near regime transitions?
  1.4 Delete-One-Cycle Jackknife — single-cycle dependence with scaled threshold
  1.5 Cycle Concentration (HHI) — separate bull/bear + dominance check
  1.6 Regime Detection Meta-Robustness — wide grid (15-50% thresholds, 5-40 durations)
  1.7 Per-Component Dominance — bull vs bear contribution imbalance

Usage:
    python3 scripts/validate_sprint1.py
    python3 scripts/validate_sprint1.py --top 5 --recalibrate
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

# Add scripts/ to path so we can import core modules
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

from data import get_tecl_data
from strategy_engine import Indicators, backtest
from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
from backtest_engine import score_regime_capture, detect_bear_regimes, detect_bull_regimes
from validation.deflate import (calibrate_null_distribution, deflate_regime_score,
                                estimate_n_eff_heuristic, expected_max_beta)

PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
LEADERBOARD_FILE = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


# ─────────────────────────────────────────────────────────────────────────────
# 1.2 Exit-Boundary Proximity Test
# ─────────────────────────────────────────────────────────────────────────────

def test_exit_boundary_proximity(trades, bears, bulls) -> dict:
    """
    Check whether strategy exits cluster suspiciously close to regime transitions.

    The research (compass...c551.md) warns that with 918K configs and 8-12 params,
    at least one config's exit signal will fire 1-3 bars before every known bear
    peak by pure chance. This test measures that directly.

    For each exit trade, compute distance to nearest bear START (the peak before
    the drop) and bear END (the trough). Exits clustered within 5 bars of bear
    starts indicate potential boundary memorization.
    """
    if not trades:
        return {"flag": False, "n_exits": 0}

    # Collect all regime transition points
    bear_starts = [b.start_idx for b in bears]  # peaks before drops
    bear_ends = [b.end_idx for b in bears]      # troughs
    all_transitions = bear_starts + bear_ends

    # For each exit, compute min distance to any transition
    exit_bars = [t.exit_bar for t in trades if t.exit_bar >= 0]
    if not exit_bars:
        return {"flag": False, "n_exits": 0}

    distances_to_bear_start = []
    distances_to_any_transition = []
    for exit_bar in exit_bars:
        # Distance to nearest bear start (most important — exiting before a crash)
        if bear_starts:
            d_bear_start = min(abs(exit_bar - bs) for bs in bear_starts)
            distances_to_bear_start.append(d_bear_start)

        if all_transitions:
            d_any = min(abs(exit_bar - t) for t in all_transitions)
            distances_to_any_transition.append(d_any)

    # What fraction of exits are within k bars of a bear start?
    n_exits = len(exit_bars)
    within_5_of_bear = sum(1 for d in distances_to_bear_start if d <= 5) / n_exits if n_exits else 0
    within_10_of_bear = sum(1 for d in distances_to_bear_start if d <= 10) / n_exits if n_exits else 0
    within_5_of_any = sum(1 for d in distances_to_any_transition if d <= 5) / n_exits if n_exits else 0

    # Expected by chance: with 13 bear starts across 4340 bars,
    # P(random exit within 5 bars of some bear start) ≈ 13 * 11 / 4340 ≈ 3.3%
    # P(within 10 bars) ≈ 13 * 21 / 4340 ≈ 6.3%
    n_bars = max(max(exit_bars), 4340)
    n_transitions = len(bear_starts)
    expected_within_5 = n_transitions * 11 / n_bars  # window of 11 bars (±5)
    expected_within_10 = n_transitions * 21 / n_bars

    # Enrichment ratio: actual / expected
    enrichment_5 = within_5_of_bear / expected_within_5 if expected_within_5 > 0 else 0
    enrichment_10 = within_10_of_bear / expected_within_10 if expected_within_10 > 0 else 0

    # Flag if exits are >3x enriched near bear starts
    flag = enrichment_5 > 3.0 or enrichment_10 > 3.0

    return {
        "n_exits": n_exits,
        "n_bear_starts": len(bear_starts),
        "pct_within_5_of_bear_start": round(within_5_of_bear * 100, 1),
        "pct_within_10_of_bear_start": round(within_10_of_bear * 100, 1),
        "expected_pct_within_5": round(expected_within_5 * 100, 1),
        "expected_pct_within_10": round(expected_within_10 * 100, 1),
        "enrichment_5": round(enrichment_5, 2),
        "enrichment_10": round(enrichment_10, 2),
        "pct_within_5_of_any_transition": round(within_5_of_any * 100, 1),
        "median_distance_to_bear_start": round(float(np.median(distances_to_bear_start)), 1) if distances_to_bear_start else None,
        "distances_to_bear_start": sorted(distances_to_bear_start)[:10],  # closest 10
        "flag": flag,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1.4 Delete-One-Cycle Jackknife
# ─────────────────────────────────────────────────────────────────────────────

def test_jackknife(trades, close, dates, baseline_composite: float) -> dict:
    """
    Remove each cycle one at a time. A cycle is "dominant" if removing it
    causes >2x the expected impact of an average cycle.
    """
    base_rs = score_regime_capture(trades, close, dates)
    n_bears = base_rs.num_bear_periods
    n_bulls = base_rs.num_bull_periods
    n_total = n_bears + n_bulls
    expected_impact = baseline_composite / max(n_total, 1)

    cycle_impacts = []
    for i in range(n_bears):
        rs = score_regime_capture(trades, close, dates, exclude_bear_idx=i)
        impact = baseline_composite - rs.composite
        ratio = abs(impact) / expected_impact if expected_impact > 0 else 0
        detail = base_rs.bear_detail[i] if i < len(base_rs.bear_detail) else {}
        cycle_impacts.append({
            "type": "bear", "index": i,
            "period": f"{detail.get('start','?')} to {detail.get('end','?')}",
            "score_without": round(rs.composite, 4),
            "impact": round(impact, 4),
            "impact_ratio": round(ratio, 2),
        })

    for i in range(n_bulls):
        rs = score_regime_capture(trades, close, dates, exclude_bull_idx=i)
        impact = baseline_composite - rs.composite
        ratio = abs(impact) / expected_impact if expected_impact > 0 else 0
        detail = base_rs.bull_detail[i] if i < len(base_rs.bull_detail) else {}
        cycle_impacts.append({
            "type": "bull", "index": i,
            "period": f"{detail.get('start','?')} to {detail.get('end','?')}",
            "score_without": round(rs.composite, 4),
            "impact": round(impact, 4),
            "impact_ratio": round(ratio, 2),
        })

    max_ratio = max((c["impact_ratio"] for c in cycle_impacts), default=0)
    dominant = [c for c in cycle_impacts if c["impact_ratio"] > 2.0]

    # Jackknife SE
    if len(cycle_impacts) >= 2:
        theta_dots = [c["score_without"] for c in cycle_impacts]
        n = len(theta_dots)
        jk_se = np.sqrt((n - 1) / n * sum((t - np.mean(theta_dots)) ** 2 for t in theta_dots))
    else:
        jk_se = 0

    return {
        "n_cycles": n_total,
        "max_impact_ratio": round(max_ratio, 2),
        "n_dominant": len(dominant),
        "dominant": dominant,
        "jackknife_se": round(float(jk_se), 4),
        "flag": len(dominant) > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1.5 HHI + Component Dominance
# ─────────────────────────────────────────────────────────────────────────────

def compute_hhi(scores: list[float]) -> float:
    if not scores or sum(scores) == 0:
        return 1.0
    total = sum(scores)
    shares = [s / total for s in scores]
    return sum(s ** 2 for s in shares)


def test_concentration(rs) -> dict:
    """HHI separately for bulls/bears + bull/bear dominance."""
    bull_scores = rs.bull_capture_scores or []
    bear_scores = rs.bear_avoidance_scores or []

    bull_hhi = compute_hhi(bull_scores)
    bear_hhi = compute_hhi(bear_scores)

    n_bull, n_bear = len(bull_scores), len(bear_scores)
    bull_thresh = 1.5 / n_bull if n_bull > 0 else 1.0
    bear_thresh = 1.5 / n_bear if n_bear > 0 else 1.0

    # Component dominance
    bull_avg = np.mean(bull_scores) if bull_scores else 0
    bear_avg = np.mean(bear_scores) if bear_scores else 0
    composite = 0.5 * bull_avg + 0.5 * bear_avg
    if composite > 0 and min(bull_avg, bear_avg) > 0:
        dominance = max(bull_avg, bear_avg) / min(bull_avg, bear_avg)
    else:
        dominance = float('inf') if composite > 0 else 1.0

    bull_flag = bull_hhi > bull_thresh
    bear_flag = bear_hhi > bear_thresh
    dom_flag = dominance > 3.0

    return {
        "bull_hhi": round(bull_hhi, 4), "bear_hhi": round(bear_hhi, 4),
        "bull_thresh": round(bull_thresh, 4), "bear_thresh": round(bear_thresh, 4),
        "bull_flag": bull_flag, "bear_flag": bear_flag,
        "dominance": round(dominance, 2), "dominance_flag": dom_flag,
        "bull_avg": round(float(bull_avg), 3), "bear_avg": round(float(bear_avg), 3),
        "flag": bull_flag or bear_flag or dom_flag,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1.6 Regime Detection Meta-Robustness (wide grid)
# ─────────────────────────────────────────────────────────────────────────────

BEAR_THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
MIN_DURATIONS = [5, 10, 20, 40]

def test_meta_robustness(trades, close, dates, baseline_composite: float) -> dict:
    """
    Test stability across 7x4=28 regime definitions.
    A robust strategy scores consistently regardless of how regimes are defined.
    """
    scores = []
    for bt in BEAR_THRESHOLDS:
        for md in MIN_DURATIONS:
            rs = score_regime_capture(trades, close, dates,
                                     bear_threshold=bt, bull_threshold=bt * 0.67,
                                     min_duration=md)
            scores.append(rs.composite)

    composites = np.array(scores)
    mean_s = float(composites.mean())
    std_s = float(composites.std())
    cv = std_s / mean_s if mean_s > 0 else float('inf')

    # Fraction within 20% of baseline
    if baseline_composite > 0:
        within_20 = float(np.mean(np.abs(composites - baseline_composite) / baseline_composite <= 0.20))
    else:
        within_20 = 0

    return {
        "n_definitions": len(scores),
        "mean": round(mean_s, 4),
        "std": round(std_s, 4),
        "cv": round(cv, 4),
        "min": round(float(composites.min()), 4),
        "max": round(float(composites.max()), 4),
        "pct_within_20pct": round(within_20 * 100, 1),
        "flag": within_20 < 0.60,  # <60% stable = flag
    }


def test_trade_clustering(trades, block_years: int = 4) -> dict:
    """
    Flag candidates whose trades are concentrated in a single 4-year block.
    """
    if not trades:
        return {"flag": True, "max_share": 1.0, "blocks": []}

    years = []
    for trade in trades:
        if getattr(trade, "entry_date", None):
            years.append(pd.Timestamp(trade.entry_date).year)
    if not years:
        return {"flag": True, "max_share": 1.0, "blocks": []}

    start_year = min(years)
    block_counts = {}
    for year in years:
        block_start = start_year + ((year - start_year) // block_years) * block_years
        label = f"{block_start}-{block_start + block_years - 1}"
        block_counts[label] = block_counts.get(label, 0) + 1

    total = sum(block_counts.values())
    blocks = [
        {"window": label, "trades": count, "share": round(count / total, 4)}
        for label, count in sorted(block_counts.items())
    ]
    max_share = max((block["share"] for block in blocks), default=0.0)
    return {
        "flag": max_share > 0.60,
        "max_share": round(max_share, 4),
        "blocks": blocks,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Run strategy and get trades
# ─────────────────────────────────────────────────────────────────────────────

def get_strategy_trades(df, strategy_name, params):
    strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy_fn:
        return None, None
    ind = Indicators(df)
    try:
        entries, exits, labels = strategy_fn(ind, params)
        cooldown = params.get("cooldown", 0)
        result = backtest(df, entries, exits, labels,
                          cooldown_bars=cooldown, strategy_name=strategy_name)
        return result.trades, result
    except Exception:
        return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_sprint1(top_n: int = 20, n_eff_override: int | None = None,
                recalibrate: bool = False, output_json: bool = False):
    start = time.time()

    print("Loading TECL data...")
    df = get_tecl_data(use_yfinance=False)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    print(f"  {len(df)} bars, {df['date'].iloc[0].date()} to {df['date'].iloc[-1].date()}")

    # Detect regimes (for boundary proximity test)
    bears = detect_bear_regimes(close, dates)
    bulls = detect_bull_regimes(close, dates, bears)
    print(f"  {len(bears)} bear periods, {len(bulls)} bull periods")

    # Monte Carlo null calibration
    print("\nCalibrating null distribution...")
    null = calibrate_null_distribution(samples_per_family=40, use_cache=not recalibrate)
    n_eff = n_eff_override or estimate_n_eff_heuristic()
    expected_max = expected_max_beta(null["beta_alpha"], null["beta_beta"], n_eff)

    print(f"  Null: {null['n_valid']} samples → Beta({null['beta_alpha']:.1f}, {null['beta_beta']:.1f})")
    print(f"  RS null: mean={null['rs_mean']:.3f} std={null['rs_std']:.3f} 95th={null['rs_p95']:.3f} 99th={null['rs_p99']:.3f}")
    print(f"  N_eff={n_eff} → expected max RS = {expected_max:.4f}")

    # Load leaderboard
    with open(LEADERBOARD_FILE) as f:
        leaderboard = json.load(f)[:top_n]

    all_results = []
    for i, entry in enumerate(leaderboard):
        name = entry["strategy"]
        params = entry.get("params", {})
        fitness = entry["fitness"]
        print(f"\n[{i+1}/{len(leaderboard)}] {name} (fitness={fitness:.4f})")

        trades, bt_result = get_strategy_trades(df, name, params)
        if trades is None:
            print(f"  SKIP — not in registry")
            all_results.append({**entry, "validation": {"error": "not in registry"}})
            continue

        rs = score_regime_capture(trades, close, dates)
        baseline = rs.composite

        # 1.1 Deflation
        defl = deflate_regime_score(baseline, null, n_eff)

        # 1.2 Exit-boundary proximity
        prox = test_exit_boundary_proximity(trades, bears, bulls)

        # 1.4 Jackknife
        jk = test_jackknife(trades, close, dates, baseline)

        # 1.5 Concentration
        conc = test_concentration(rs)

        # 1.6 Meta-robustness
        meta = test_meta_robustness(trades, close, dates, baseline)

        # Collect flags
        flags = []
        if defl["deflated_probability"] < 0.50:
            flags.append(f"deflated={defl['deflated_probability']:.4f} (noise, null_pctl={defl['null_percentile']:.0f}%)")
        if prox["flag"]:
            flags.append(f"exit_proximity: {prox['enrichment_5']:.1f}x enriched near bear starts (expected {prox['expected_pct_within_5']:.1f}%, actual {prox['pct_within_5_of_bear_start']:.1f}%)")
        if jk["flag"]:
            dom_str = ", ".join(f"{d['type']}#{d['index']}" for d in jk["dominant"][:2])
            flags.append(f"jackknife: {jk['n_dominant']} dominant cycle(s) [{dom_str}] ({jk['max_impact_ratio']:.1f}x)")
        if conc["flag"]:
            parts = []
            if conc["bull_flag"]: parts.append(f"bull_hhi={conc['bull_hhi']:.3f}")
            if conc["bear_flag"]: parts.append(f"bear_hhi={conc['bear_hhi']:.3f}")
            if conc["dominance_flag"]: parts.append(f"dom={conc['dominance']:.1f}x")
            flags.append(f"concentration: {', '.join(parts)}")
        if meta["flag"]:
            flags.append(f"meta: {meta['pct_within_20pct']:.0f}% stable (cv={meta['cv']:.3f})")

        tier = (
            "strong_signal" if defl["deflated_probability"] >= 0.95 and not flags else
            "modest_signal" if defl["deflated_probability"] >= 0.80 and len(flags) <= 1 else
            "fragile" if defl["deflated_probability"] >= 0.50 else
            "noise"
        )

        validation = {
            "regime_score": baseline,
            "deflation": defl,
            "exit_proximity": prox,
            "jackknife": jk,
            "concentration": conc,
            "meta_robustness": meta,
            "tier": tier,
            "flags": flags,
        }

        status = f"{len(flags)} FLAG{'S' if len(flags) != 1 else ''}" if flags else "PASS"
        print(f"  RS={baseline:.3f} pctl={defl['null_percentile']:.0f}% defl={defl['deflated_probability']:.4f} "
              f"prox={prox['enrichment_5']:.1f}x jk={jk['max_impact_ratio']:.1f}x "
              f"dom={conc['dominance']:.1f}x meta={meta['pct_within_20pct']:.0f}% → {tier} ({status})")

        all_results.append({**entry, "validation": validation})

    elapsed = time.time() - start

    if output_json:
        print(json.dumps({"strategies": all_results, "null": null, "n_eff": n_eff}, indent=2, default=str))
        return all_results

    # Summary table
    print(f"\n{'=' * 105}")
    print(f"SPRINT 1 SUMMARY  ({elapsed:.1f}s)  N_eff={n_eff}  Expected max RS={expected_max:.3f}  Null=Beta({null['beta_alpha']:.0f},{null['beta_beta']:.0f})")
    print(f"{'=' * 105}")
    print(f"{'Rk':<4} {'Strategy':<22} {'RS':>6} {'Pctl':>5} {'Defl':>7} {'Prox':>5} {'JK':>5} "
          f"{'Dom':>5} {'Meta':>5} {'#F':>3} {'Tier':<14}")
    print("-" * 105)
    for i, r in enumerate(all_results, 1):
        v = r.get("validation", {})
        if "error" in v:
            print(f"{i:<4} {r['strategy']:<22} {'— ERROR —':>50}")
            continue
        rs_v = v["regime_score"]
        pctl = v["deflation"]["null_percentile"]
        dp = v["deflation"]["deflated_probability"]
        prx = v["exit_proximity"]["enrichment_5"]
        jk_r = v["jackknife"]["max_impact_ratio"]
        dom = v["concentration"]["dominance"]
        meta_s = v["meta_robustness"]["pct_within_20pct"]
        nf = len(v["flags"])
        tier = v["tier"]
        print(f"{i:<4} {r['strategy']:<22} {rs_v:>6.3f} {pctl:>4.0f}% {dp:>7.4f} {prx:>4.1f}x {jk_r:>4.1f}x "
              f"{dom:>4.1f}x {meta_s:>4.0f}% {nf:>3} {tier:<14}")

    # Flag details
    flagged = [r for r in all_results if r.get("validation", {}).get("flags")]
    if flagged:
        print(f"\n  FLAGGED ({len(flagged)}):")
        for r in flagged:
            print(f"    {r['strategy']} (fitness={r['fitness']:.4f}, RS={r['validation']['regime_score']:.3f}):")
            for f in r["validation"]["flags"]:
                print(f"      • {f}")

    clean = [r for r in all_results if not r.get("validation", {}).get("flags") and "error" not in r.get("validation", {})]
    print(f"\n  CLEAN: {len(clean)} | FLAGGED: {len(flagged)} | ERRORS: {len(all_results) - len(clean) - len(flagged)}")

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sprint 1 — Tier 1 overfitting checks")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--n-eff", type=int)
    parser.add_argument("--recalibrate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    run_sprint1(top_n=args.top, n_eff_override=args.n_eff,
                recalibrate=args.recalibrate, output_json=args.json)

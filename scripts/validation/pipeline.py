#!/usr/bin/env python3
"""
Automatic validation pipeline for spike runs.

This module turns raw optimizer rankings into a strict validation funnel:

0. Run integrity
1. Candidate eligibility
2. Search-bias and regime-memorization checks
3. Parameter fragility
4. Time generalization
5. Uncertainty and interaction checks
6. Cross-asset concept generalization
7. Promotion and deployment eligibility

Only PASS candidates are eligible for leaderboard promotion or Pine generation.
WARN and FAIL candidates remain in run artifacts only.
"""

from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from dataclasses import dataclass

import numpy as np

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

from backtest_engine import detect_bear_regimes, detect_bull_regimes, score_regime_capture
from canonical_params import effective_tier as compute_effective_tier
from data import get_tecl_data
from discovery_markers import score_marker_alignment
from pine_generator import generate_pine_script
from strategies import STRATEGY_REGISTRY, STRATEGY_TIERS
from validation.candidate import (
    analyze_four_year_degeneracy,
    analyze_named_windows,
    analyze_walk_forward,
    check_parameter_fragility,
)
from validation.cross_asset import cross_asset_reoptimize, cross_asset_validate
from validation.deflate import (
    calibrate_null_distribution,
    deflate_regime_score,
    estimate_n_eff_heuristic,
    expected_max_beta,
)
from validation.integrity import REQUIRED_PINE_SNIPPETS, validate_run_integrity
from validation.sprint1 import (
    get_strategy_trades,
    test_concentration,
    test_exit_boundary_proximity,
    test_jackknife,
    test_meta_robustness,
    test_trade_clustering,
)
from validation.uncertainty import morris_fragility, stationary_bootstrap_validation


PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
LEADERBOARD_FILE = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_TOP_N = 20


@dataclass
class ValidationContext:
    df: object
    close: np.ndarray
    dates: np.ndarray
    bears: list
    bulls: list
    null: dict
    n_eff: int
    expected_max: float
    regime_transitions: int
    leaderboard: list
    run_integrity: dict


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return float(max(lo, min(hi, value)))


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _build_context(raw_rankings: list[dict]) -> ValidationContext:
    strategy_names = [entry.get("strategy", "") for entry in raw_rankings if entry.get("strategy")]
    run_integrity = validate_run_integrity(strategy_names)
    if run_integrity["verdict"] != "PASS":
        raise RuntimeError("Gate 0 run integrity failed: " + "; ".join(run_integrity["errors"]))

    df = get_tecl_data(use_yfinance=False)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    bears = detect_bear_regimes(close, dates)
    bulls = detect_bull_regimes(close, dates, bears)
    null = calibrate_null_distribution(samples_per_family=40, use_cache=True)
    n_eff = estimate_n_eff_heuristic()
    expected_max = expected_max_beta(null["beta_alpha"], null["beta_beta"], n_eff)

    leaderboard = []
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE) as f:
                leaderboard = json.load(f)
        except Exception:
            leaderboard = []

    return ValidationContext(
        df=df,
        close=close,
        dates=dates,
        bears=bears,
        bulls=bulls,
        null=null,
        n_eff=n_eff,
        expected_max=expected_max,
        regime_transitions=len(bears) + len(bulls),
        leaderboard=leaderboard,
        run_integrity=run_integrity,
    )


def _choose_reopt_budget(hours: float, quick: bool) -> tuple[float, int]:
    if quick or hours <= 0.10:
        return 0.5, 12
    if hours <= 0.50:
        return 1.0, 16
    if hours <= 2.0:
        return 1.5, 20
    return 2.0, 24


def _rank_entries(entries: list[dict], *, by: str = "fitness") -> list[dict]:
    ranked = sorted(entries, key=lambda item: item.get(by, 0), reverse=True)
    for idx, entry in enumerate(ranked, start=1):
        entry["rank"] = idx
    return ranked


def _strategy_history_state(strategy_name: str, leaderboard: list[dict]) -> dict | None:
    matches = [entry for entry in leaderboard if entry.get("strategy") == strategy_name]
    if not matches:
        return None
    return max(matches, key=lambda entry: entry.get("fitness", 0))


def _selection_bias_score(observed_rs: float, expected_max: float) -> float:
    if expected_max <= 0.0:
        return 1.0
    if expected_max >= 1.0:
        return 0.0
    ratio = observed_rs / expected_max
    if ratio >= 1.0:
        return _clamp(0.70 + 0.30 * min((ratio - 1.0) / 0.25, 1.0))
    # Selection-bias adjustment is advisory in the current pipeline, so a
    # below-threshold score should depress confidence without zeroing it out.
    return _clamp(0.35 + 0.35 * max(ratio, 0.0), 0.35, 0.70)


def _trade_sufficiency_score(trades: int) -> float:
    return _clamp((trades - 10.0) / 30.0)


def _geometric_composite(sub_scores: dict) -> float:
    """Weighted geometric mean over present sub-scores.

    A sub-score of None (e.g. a gate skipped due to tier routing) is dropped
    and the remaining weights renormalize. This means T0 and T1 composites are
    computed over their tier-applicable gates only — they don't pay a penalty
    for gates that weren't supposed to run against them.
    """
    weights = {
        "marker_shape":       0.20,   # charter-level first-class gate, every tier
        "walk_forward":       0.20,
        "fragility":          0.20,   # T1/T2 only
        "selection_bias":     0.15,   # T2 only
        "cross_asset":        0.10,   # every tier — the cheap honesty check
        "bootstrap":          0.05,   # T2 only
        "regime_consistency": 0.05,   # T2 only
        "trade_sufficiency":  0.05,
    }
    present = {k: w for k, w in weights.items() if sub_scores.get(k) is not None}
    if not present:
        return 0.0
    total = sum(present.values())
    score = 1.0
    for name, weight in present.items():
        norm_w = weight / total
        score *= _clamp(float(sub_scores[name])) ** norm_w
    return float(score)


def _regime_consistency_score(concentration: dict, meta: dict, clustering: dict) -> float:
    bull_margin = max(0.0, concentration["bull_hhi"] - concentration["bull_thresh"])
    bear_margin = max(0.0, concentration["bear_hhi"] - concentration["bear_thresh"])
    bull_score = _clamp(1.0 - bull_margin / max(1.0 - concentration["bull_thresh"], 1e-6))
    bear_score = _clamp(1.0 - bear_margin / max(1.0 - concentration["bear_thresh"], 1e-6))
    dominance_score = _clamp(1.0 - max(0.0, concentration["dominance"] - 1.0) / 2.0)
    meta_score = _clamp(meta["pct_within_20pct"] / 100.0)
    cluster_score = _clamp(1.0 - max(0.0, clustering["max_share"] - 0.25) / 0.35)
    return float(np.mean([bull_score, bear_score, dominance_score, meta_score, cluster_score]))


def _skip_gate(reason: str) -> dict:
    return {
        "verdict": "SKIPPED",
        "reason": reason,
        "advisories": [],
        "soft_warnings": [],
        "critical_warnings": [],
        "warnings": [],
        "hard_fail_reasons": [],
    }


def _gate1_candidate(entry: dict, ctx: ValidationContext, *, tier: str = "T2") -> dict:
    """Candidate eligibility. Thresholds soften for lower tiers.

    T0 (Hypothesis): trade_count >= 5, no tpp gate (params are canonical, not tuned)
    T1 (Tuned): trade_count >= 10, tpp >= 3.0
    T2 (Discovered): trade_count >= 15, tpp >= 5.0 — the defense against underdetermined GA winners
    """
    metrics = entry.get("metrics") or {}
    strategy_name = entry.get("strategy", "")
    params = entry.get("params") or {}
    trades = entry.get("trades") or []
    trade_count = int(metrics.get("trades", 0))
    trades_per_year = float(metrics.get("trades_yr", 0.0))
    n_params = int(metrics.get("n_params", 0))
    trades_per_param = trade_count / n_params if n_params > 0 else math.inf

    # Per-tier trade-count floor and tpp gate.
    if tier == "T0":
        trade_floor = 5
        tpp_floor = None  # no tpp gate for T0 — canonical params are pre-registered
    elif tier == "T1":
        trade_floor = 10
        tpp_floor = 3.0
    else:  # T2
        trade_floor = 15
        tpp_floor = 5.0

    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []
    history_state = _strategy_history_state(strategy_name, ctx.leaderboard)
    if not trades and strategy_name in STRATEGY_REGISTRY:
        reconstructed, _ = get_strategy_trades(ctx.df, strategy_name, params)
        trades = reconstructed or []
    degeneracy = analyze_four_year_degeneracy(ctx.df, trades)
    strategy_integrity = ctx.run_integrity["strategies"].get(strategy_name, {})

    if trade_count < trade_floor:
        hard_fail_reasons.append(f"[{tier}] trade_count={trade_count} < {trade_floor}")
    if trades_per_year > 5.0:
        hard_fail_reasons.append(f"trades_per_year={trades_per_year:.2f} > 5.0 (charter)")
    if tpp_floor is not None and trades_per_param < tpp_floor:
        hard_fail_reasons.append(f"[{tier}] trades_per_param={trades_per_param:.2f} < {tpp_floor}")
    if degeneracy["verdict"] == "FAIL":
        hard_fail_reasons.extend(f"degeneracy: {reason}" for reason in degeneracy["hard_fail_reasons"])
    soft_warnings.extend(f"degeneracy: {reason}" for reason in degeneracy.get("warnings", []))
    if not strategy_integrity.get("pine_supported", False):
        hard_fail_reasons.append("strategy family is not Pine-deployable")
    if not strategy_integrity.get("charter_compatible", False):
        hard_fail_reasons.append("strategy family is not charter-compatible")

    if tpp_floor is not None and tpp_floor <= trades_per_param < (tpp_floor + 5.0):
        soft_warnings.append(f"trades_per_param={trades_per_param:.2f} in soft-warning band")
    if n_params > ctx.regime_transitions:
        soft_warnings.append(
            f"n_params={n_params} exceeds regime_transitions={ctx.regime_transitions}"
        )
    if history_state and not history_state.get("converged", False):
        advisories.append("strategy family still unconverged in leaderboard history")

    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "tier": tier,
        "trade_count": trade_count,
        "trades_per_year": round(trades_per_year, 4),
        "n_params": n_params,
        "trades_per_param": None if math.isinf(trades_per_param) else round(trades_per_param, 4),
        "regime_transitions": ctx.regime_transitions,
        "degeneracy": degeneracy,
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate2_search_bias(strategy_name: str, params: dict, ctx: ValidationContext) -> tuple[dict, object | None]:
    trades, bt_result = get_strategy_trades(ctx.df, strategy_name, params)
    if trades is None or bt_result is None:
        gate = {
            "verdict": "FAIL",
            "advisories": [],
            "soft_warnings": [],
            "critical_warnings": [],
            "warnings": [],
            "hard_fail_reasons": ["strategy could not be evaluated on full TECL history"],
            "selection_bias_score": 0.0,
            "regime_consistency_score": 0.0,
        }
        return gate, None

    rs = score_regime_capture(trades, ctx.close, ctx.dates)
    observed_rs = float(rs.composite)
    deflation = deflate_regime_score(observed_rs, ctx.null, ctx.n_eff)
    proximity = test_exit_boundary_proximity(trades, ctx.bears, ctx.bulls)
    jackknife = test_jackknife(trades, ctx.close, ctx.dates, observed_rs)
    concentration = test_concentration(rs)
    meta = test_meta_robustness(trades, ctx.close, ctx.dates, observed_rs)
    clustering = test_trade_clustering(trades)

    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []
    if observed_rs <= ctx.expected_max or deflation["deflated_probability"] < 0.50:
        advisories.append(
            f"selection_bias: observed_rs={observed_rs:.4f} expected_max={ctx.expected_max:.4f} "
            f"deflated={deflation['deflated_probability']:.4f}"
        )
    elif deflation["deflated_probability"] < 0.80:
        advisories.append(f"selection_bias: deflated={deflation['deflated_probability']:.4f}")

    if proximity["enrichment_5"] > 3.0 or proximity["enrichment_10"] > 3.0:
        hard_fail_reasons.append(
            f"exit proximity: {proximity['enrichment_5']:.2f}x/{proximity['enrichment_10']:.2f}x near bear starts"
        )

    if jackknife["max_impact_ratio"] > 2.0:
        hard_fail_reasons.append(f"jackknife: dominant cycle {jackknife['max_impact_ratio']:.2f}x")

    if (
        concentration["bull_flag"]
        or concentration["bear_flag"]
        or concentration["dominance"] > 3.0
    ):
        critical_warnings.append(
            f"concentration: bull_hhi={concentration['bull_hhi']:.3f} "
            f"bear_hhi={concentration['bear_hhi']:.3f} dom={concentration['dominance']:.2f}x"
        )
    elif concentration["dominance"] > 2.0:
        soft_warnings.append(f"concentration nearing limit: dom={concentration['dominance']:.2f}x")

    if meta["pct_within_20pct"] < 50.0:
        critical_warnings.append(
            f"meta robustness: only {meta['pct_within_20pct']:.1f}% within 20% of baseline"
        )
    elif meta["pct_within_20pct"] < 75.0:
        soft_warnings.append(
            f"meta robustness soft band: {meta['pct_within_20pct']:.1f}% within 20% of baseline"
        )

    if clustering["max_share"] > 0.60:
        critical_warnings.append(f"trade clustering: max_share={clustering['max_share']:.2f} > 0.60")

    selection_bias_score = _selection_bias_score(observed_rs, ctx.expected_max)
    regime_consistency_score = _regime_consistency_score(concentration, meta, clustering)
    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "observed_regime_score": round(observed_rs, 4),
        "expected_max_regime_score": round(ctx.expected_max, 4),
        "deflation": deflation,
        "exit_proximity": proximity,
        "jackknife": jackknife,
        "concentration": concentration,
        "meta_robustness": meta,
        "trade_clustering": clustering,
        "selection_bias_score": round(selection_bias_score, 4),
        "regime_consistency_score": round(regime_consistency_score, 4),
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }, bt_result


def _gate3_fragility(strategy_name: str, params: dict, ctx: ValidationContext) -> dict:
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    fragility = check_parameter_fragility(ctx.df, strategy_fn, params, strategy_name)
    soft_warnings = [f"fragility: {w}" for w in fragility["warn_params"]]
    critical_warnings = []
    hard_fail_reasons = list(fragility["hard_fail_params"])
    return {
        **fragility,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": soft_warnings + critical_warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate4_time_generalization(strategy_name: str, params: dict, ctx: ValidationContext) -> dict:
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    walk_forward = analyze_walk_forward(ctx.df, strategy_fn, params, strategy_name)
    named_windows = analyze_named_windows(ctx.df, strategy_fn, params, strategy_name)
    soft_warnings = list(walk_forward.get("soft_warnings", [])) + list(named_windows.get("soft_warnings", []))
    critical_warnings = list(walk_forward.get("critical_warnings", [])) + list(named_windows.get("critical_warnings", []))
    warnings = soft_warnings + critical_warnings
    hard_fail_reasons = list(walk_forward["hard_fail_reasons"]) + list(named_windows["hard_fail_reasons"])
    verdict = "FAIL" if hard_fail_reasons else "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "walk_forward": walk_forward,
        "named_windows": named_windows,
        "walk_forward_score": walk_forward["score"],
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate5_uncertainty(strategy_name: str, params: dict, ctx: ValidationContext) -> dict:
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    morris = morris_fragility(ctx.df, strategy_fn, strategy_name, params, trajectories=30)
    bootstrap = stationary_bootstrap_validation(
        ctx.df, strategy_fn, strategy_name, params, resamples=200
    )

    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []
    if morris["interaction_flag"]:
        hard_fail_reasons.append(
            f"morris interaction fragility: max_swing={morris['max_swing']:.2f} "
            f"sigma_ratio={morris['max_sigma_ratio']:.2f}"
        )
    elif morris["warning_flag"]:
        msg = (
            f"morris warning: max_swing={morris['max_swing']:.2f} "
            f"sigma_ratio={morris['max_sigma_ratio']:.2f}"
        )
        if morris["max_swing"] < 0.10:
            pass  # negligible swing — not worth a warning slot
        else:
            critical_warnings.append(msg)

    if bootstrap["hard_fail"]:
        hard_fail_reasons.append(
            f"bootstrap downside probability {bootstrap['downside_prob_vs_bah']:.2f} > 0.50"
        )
    else:
        downside = bootstrap["downside_prob_vs_bah"]
        s_boot = bootstrap["s_boot"]
        if downside > 0.40:
            critical_warnings.append(
                f"bootstrap warning: ci_width={bootstrap['ci_width']:.3f} "
                f"downside_prob={downside:.2f}"
            )
        elif downside > 0.25 or s_boot < 0.20:
            soft_warnings.append(
                f"bootstrap warning: ci_width={bootstrap['ci_width']:.3f} "
                f"downside_prob={downside:.2f}"
            )

    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "morris": morris,
        "bootstrap": bootstrap,
        "fragility_score": morris["s_frag"],
        "bootstrap_score": bootstrap["s_boot"],
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate_marker_shape(strategy_name: str, params: dict, ctx: ValidationContext, *, tier: str = "T2") -> dict:
    """First-class validation gate: does the strategy trade the marker-defined cycle shape?

    The hand-marked TECL cycles in reference/research/chart/TECL-markers.csv are the
    charter's working definition of success. A strategy that beats B&H share count but
    trades a completely different shape is doing something other than what the project
    is trying to do — that's also a fail.

    Thresholds are intentionally loose: we're asking "is the strategy clearly trying to
    trade the same cycles?" not "does it match hindsight-perfect timing?"

    Per tier:
      T0: state_agreement >= 0.75 (hard), missed_cycles == 0 (hard), transition_timing >= 0.50 (soft)
      T1: state_agreement >= 0.70 (hard), missed_cycles <= 3 (soft warning)
      T2: state_agreement >= 0.65 (hard), missed_cycles <= 5 (soft warning)

    `missed_cycles` is a hard fail only at T0 (where the strategy is pre-registered
    as a hypothesis and ought to engage with every marker cycle the data covers).
    At T1/T2 it is a soft warning — a large search will produce candidates with
    high state_agreement that still miss some early-period marker cycles due to
    indicator warm-up, data-availability windows, or genuine regime mismatches,
    and that is informative but not disqualifying when state overlap is strong.
    """
    trades, bt_result = get_strategy_trades(ctx.df, strategy_name, params)
    if trades is None or bt_result is None:
        return {
            "verdict": "FAIL",
            "tier": tier,
            "advisories": [],
            "soft_warnings": [],
            "critical_warnings": [],
            "warnings": [],
            "hard_fail_reasons": ["strategy could not be evaluated for marker shape"],
            "marker_score": 0.0,
        }

    align = score_marker_alignment(ctx.df, trades)
    state_agreement = float(align.get("state_accuracy", 0.0))
    transition_timing = float(align.get("transition_timing_score", 0.0))
    target_buys = int(align.get("target_buy_count", 0))
    candidate_buys = int(align.get("candidate_buy_count", 0))
    # Approximate "missed cycles" as the number of marker buys that have no candidate buy
    # within tolerance. The detail list carries per-target match info.
    buy_matches = align.get("buy_transition_matches", []) or []
    missed_cycles = sum(1 for m in buy_matches if (m.get("score") or 0) < 0.1)

    if tier == "T0":
        state_floor, missed_cap, timing_floor, missed_is_hard = 0.75, 0, 0.50, True
    elif tier == "T1":
        state_floor, missed_cap, timing_floor, missed_is_hard = 0.70, 3, 0.40, False
    else:  # T2
        state_floor, missed_cap, timing_floor, missed_is_hard = 0.65, 5, 0.30, False

    hard_fail_reasons = []
    soft_warnings = []
    advisories = []
    if target_buys == 0:
        advisories.append("marker overlap produced zero target buys — skipping shape gate")
    else:
        if state_agreement < state_floor:
            hard_fail_reasons.append(
                f"[{tier}] marker state_agreement={state_agreement:.3f} < {state_floor:.2f}"
            )
        if missed_cycles > missed_cap:
            msg = f"[{tier}] missed_marker_cycles={missed_cycles} > {missed_cap}"
            if missed_is_hard:
                hard_fail_reasons.append(msg)
            else:
                soft_warnings.append(msg)
        if transition_timing < timing_floor:
            soft_warnings.append(
                f"[{tier}] transition_timing={transition_timing:.3f} < {timing_floor:.2f}"
            )

    warnings = soft_warnings + []
    verdict = "FAIL" if hard_fail_reasons else "PASS"
    return {
        "verdict": verdict,
        "tier": tier,
        "marker_score": round(float(align.get("score", 0.0)), 4),
        "state_agreement": round(state_agreement, 4),
        "transition_timing": round(transition_timing, 4),
        "target_buy_count": target_buys,
        "candidate_buy_count": candidate_buys,
        "missed_cycles": missed_cycles,
        "tolerance_bars": int(align.get("tolerance_bars", 0)),
        "overlap_start": align.get("overlap_start"),
        "overlap_end": align.get("overlap_end"),
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": [],
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate6_cross_asset(strategy_name: str, params: dict, ctx: ValidationContext, *, reopt_minutes: float, reopt_pop_size: int) -> dict:
    cross_asset = cross_asset_validate(strategy_name, params)
    results = cross_asset.get("results", {})
    tqqq = results.get("TQQQ", {})
    qqq = results.get("QQQ", {})

    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []
    if "error" in tqqq:
        hard_fail_reasons.append(f"TQQQ same-param replay error: {tqqq['error']}")
    else:
        tqqq_bah = float(tqqq.get("vs_bah", 0.0))
        if tqqq_bah < 0.50:
            hard_fail_reasons.append(f"TQQQ same-param vs_bah={tqqq_bah:.3f} < 0.50")
        elif tqqq_bah < 1.0:
            soft_warnings.append(f"TQQQ same-param vs_bah={tqqq_bah:.3f} < 1.00")

    if "error" in qqq:
        soft_warnings.append(f"QQQ same-param replay error: {qqq['error']}")
    else:
        qqq_bah = float(qqq.get("vs_bah", 0.0))
        if qqq_bah < 0.50:
            soft_warnings.append(f"QQQ same-param vs_bah={qqq_bah:.3f} < 0.50")

    tier3 = cross_asset_reoptimize(
        strategy_name,
        minutes=reopt_minutes,
        pop_size=reopt_pop_size,
    )
    if tier3.get("verdict") != "PASS":
        hard_fail_reasons.append(tier3.get("reason", "TQQQ re-optimization failed"))

    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "same_params": cross_asset,
        "tier3_reopt": tier3,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate7_synthesis(
    strategy_name: str,
    params: dict,
    entry: dict,
    gates: dict,
    *,
    tier: str = "T2",
) -> dict:
    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []
    for gate_name in ("gate1", "gate_marker", "gate2", "gate3", "gate4", "gate5", "gate6"):
        gate = gates.get(gate_name, {})
        advisories.extend(gate.get("advisories", []))
        soft_warnings.extend(gate.get("soft_warnings", []))
        critical_warnings.extend(gate.get("critical_warnings", []))
        hard_fail_reasons.extend(gate.get("hard_fail_reasons", []))

    trade_count = int((entry.get("metrics") or {}).get("trades", 0))

    # Helper: return None for gates that were skipped due to tier routing,
    # so the composite renormalizes over applicable gates only.
    def _score_if_ran(gate_name: str, field: str, fallback: float | None = None) -> float | None:
        gate = gates.get(gate_name, {})
        if gate.get("verdict") == "SKIPPED":
            return fallback
        value = gate.get(field)
        return float(value) if value is not None else fallback

    # Cross-asset score: same-param TQQQ vs_bah, capped at 1.0 (beating B&H).
    # Uses the already-computed cross-asset result instead of running again.
    def _cross_asset_score() -> float | None:
        g6 = gates.get("gate6", {})
        if g6.get("verdict") == "SKIPPED":
            return None
        same = (g6.get("same_params") or {}).get("results", {}).get("TQQQ", {})
        if "error" in same:
            return 0.0
        tqqq_bah = float(same.get("vs_bah", 0.0))
        return _clamp(tqqq_bah / 1.0)  # 1.0x TQQQ B&H → full credit, 0.5x → 0.5

    # Marker shape sub-score (every tier): prefer state_agreement ramped
    # from the tier's own floor, fallback to marker_score composite.
    def _marker_sub_score() -> float | None:
        gm = gates.get("gate_marker", {})
        if gm.get("verdict") == "SKIPPED":
            return None
        state_agreement = gm.get("state_agreement")
        if state_agreement is None:
            return float(gm.get("marker_score", 0.0))
        return _clamp(float(state_agreement))

    sub_scores: dict = {
        "marker_shape":       _marker_sub_score(),
        "walk_forward":       _score_if_ran("gate4", "walk_forward_score", 0.0),
        "fragility":          _score_if_ran("gate5", "fragility_score",
                                            _score_if_ran("gate3", "score")),
        "selection_bias":     _score_if_ran("gate2", "selection_bias_score"),
        "cross_asset":        _cross_asset_score(),
        "bootstrap":          _score_if_ran("gate5", "bootstrap_score"),
        "regime_consistency": _score_if_ran("gate2", "regime_consistency_score"),
        "trade_sufficiency":  _trade_sufficiency_score(trade_count),
    }
    composite_confidence = _geometric_composite(sub_scores)

    pine_eligible = False
    parity_pass = False
    parity = {
        "mode": "structural_smoke",
        "reference_windows": gates["gate4"].get("named_windows", {}).get("results", []),
        "required_tokens": list(REQUIRED_PINE_SNIPPETS),
    }
    try:
        script = generate_pine_script(strategy_name, params)
        pine_eligible = True
        parity["generated"] = True
        parity["line_count"] = len(script.splitlines())
        parity["settings_ok"] = all(token in script for token in REQUIRED_PINE_SNIPPETS)
        parity_pass = parity["settings_ok"]
        if not parity["settings_ok"]:
            hard_fail_reasons.append("generated Pine candidate missing required strategy settings")
    except Exception as exc:
        parity["generated"] = False
        parity["error"] = str(exc)
        hard_fail_reasons.append(f"Pine generation failed: {exc}")

    if not hard_fail_reasons and composite_confidence < 0.45:
        hard_fail_reasons.append(f"composite_confidence={composite_confidence:.3f} < 0.45")
    elif composite_confidence < 0.70:
        soft_warnings.append(f"composite_confidence={composite_confidence:.3f} < 0.70")

    if not parity_pass and "generated Pine candidate missing required strategy settings" not in hard_fail_reasons:
        critical_warnings.append("Pine parity smoke did not pass")

    # De-duplicate
    advisories = list(dict.fromkeys(advisories))
    soft_warnings = list(dict.fromkeys(soft_warnings))
    critical_warnings = list(dict.fromkeys(critical_warnings))
    hard_fail_reasons = list(dict.fromkeys(hard_fail_reasons))

    # Backward-compat merged list
    warnings = soft_warnings + critical_warnings

    # Verdict: 4-tier taxonomy
    if hard_fail_reasons or composite_confidence < 0.45:
        verdict = "FAIL"
    elif critical_warnings or composite_confidence < 0.70 or len(soft_warnings) >= 4:
        verdict = "WARN"
    else:
        verdict = "PASS"

    clean_pass = verdict == "PASS" and len(soft_warnings) == 0

    return {
        "verdict": verdict,
        "tier": tier,
        "promotion_eligible": verdict == "PASS",
        "clean_pass": clean_pass,
        "pine_eligible": pine_eligible and parity_pass,
        "parity": parity,
        "sub_scores": {k: (round(v, 4) if v is not None else None) for k, v in sub_scores.items()},
        "composite_confidence": round(composite_confidence, 4),
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _resolve_tier(strategy_name: str, params: dict, entry: dict) -> tuple[str, list[str]]:
    """Determine the effective validation tier for a candidate.

    Priority:
      1. Explicit `tier` on the entry (e.g. set by spike_runner when the GA touched it)
      2. Declared STRATEGY_TIERS entry
      3. Default to T2 (safest — full statistical stack)

    Then apply canonical_params.effective_tier() which may auto-promote to a
    stricter tier if params violate canonical/size constraints for the declared tier.
    """
    declared = (entry.get("tier") or STRATEGY_TIERS.get(strategy_name) or "T2").upper()
    effective, reasons = compute_effective_tier(declared, params)
    return effective, reasons


def _validate_entry(
    entry: dict,
    ctx: ValidationContext,
    *,
    reopt_minutes: float,
    reopt_pop_size: int,
) -> dict:
    strategy_name = entry.get("strategy", "")
    params = copy.deepcopy(entry.get("params", {}))
    validation = {
        "verdict": "FAIL",
        "promotion_eligible": False,
        "clean_pass": False,
        "pine_eligible": False,
        "composite_confidence": 0.0,
        "tier": "T2",
        "tier_reasons": [],
        "sub_scores": {},
        "advisories": [],
        "soft_warnings": [],
        "critical_warnings": [],
        "warnings": [],
        "hard_fail_reasons": [],
        "gates": {},
    }

    if strategy_name not in STRATEGY_REGISTRY:
        validation["hard_fail_reasons"].append(f"unknown strategy {strategy_name}")
        validation["gates"]["gate1"] = {
            "verdict": "FAIL",
            "advisories": [],
            "soft_warnings": [],
            "critical_warnings": [],
            "warnings": [],
            "hard_fail_reasons": [f"unknown strategy {strategy_name}"],
        }
        validation["gates"]["gate_marker"] = _skip_gate("unknown strategy")
        validation["gates"]["gate2"] = _skip_gate("unknown strategy")
        validation["gates"]["gate3"] = _skip_gate("unknown strategy")
        validation["gates"]["gate4"] = _skip_gate("unknown strategy")
        validation["gates"]["gate5"] = _skip_gate("unknown strategy")
        validation["gates"]["gate6"] = _skip_gate("unknown strategy")
        validation["gates"]["gate7"] = _skip_gate("unknown strategy")
        entry["validation"] = validation
        return entry

    tier, tier_reasons = _resolve_tier(strategy_name, params, entry)
    validation["tier"] = tier
    validation["tier_reasons"] = tier_reasons
    if tier_reasons:
        validation["advisories"].extend(tier_reasons)

    print(f"[validate] {strategy_name} tier={tier} (fitness={entry.get('fitness', 0):.4f})")

    # ── Gate 1: candidate eligibility (tier-aware thresholds) ──
    gate1 = _gate1_candidate(entry, ctx, tier=tier)
    validation["gates"]["gate1"] = gate1
    hard_stop = bool(gate1["hard_fail_reasons"])

    # ── Marker shape gate: runs for ALL tiers, charter first-class gate ──
    if not hard_stop:
        gate_marker = _gate_marker_shape(strategy_name, params, ctx, tier=tier)
    else:
        gate_marker = _skip_gate("candidate eligibility hard fail")
    validation["gates"]["gate_marker"] = gate_marker
    hard_stop = hard_stop or bool(gate_marker.get("hard_fail_reasons"))

    # ── Gate 2: search-bias / regime memorization — T2 only ──
    if tier == "T2" and not hard_stop:
        gate2, _bt_result = _gate2_search_bias(strategy_name, params, ctx)
    elif tier != "T2":
        gate2 = _skip_gate(f"skipped for {tier} — search-bias stack is T2-only")
    else:
        gate2 = _skip_gate("earlier hard fail")
    validation["gates"]["gate2"] = gate2
    hard_stop = hard_stop or bool(gate2.get("hard_fail_reasons"))

    # ── Gate 3: parameter fragility — T1 + T2 ──
    if tier in {"T1", "T2"} and not hard_stop:
        gate3 = _gate3_fragility(strategy_name, params, ctx)
    elif tier == "T0":
        gate3 = _skip_gate("skipped for T0 — canonical params are pre-registered")
    else:
        gate3 = _skip_gate("earlier hard fail")
    validation["gates"]["gate3"] = gate3
    hard_stop = hard_stop or bool(gate3.get("hard_fail_reasons"))

    # ── Gate 4: walk-forward / named windows — ALL tiers ──
    if not hard_stop:
        gate4 = _gate4_time_generalization(strategy_name, params, ctx)
    else:
        gate4 = _skip_gate("earlier hard fail")
    validation["gates"]["gate4"] = gate4
    hard_stop = hard_stop or bool(gate4.get("hard_fail_reasons"))

    # ── Gate 5: uncertainty (Morris/bootstrap) — T2 only ──
    # ── Gate 6: cross-asset — ALL tiers (highest-power honesty check) ──
    if not hard_stop:
        if tier == "T2":
            gate5 = _gate5_uncertainty(strategy_name, params, ctx)
        else:
            gate5 = _skip_gate(f"skipped for {tier} — uncertainty stack is T2-only")
        gate6 = _gate6_cross_asset(
            strategy_name,
            params,
            ctx,
            reopt_minutes=reopt_minutes,
            reopt_pop_size=reopt_pop_size,
        )
    else:
        gate5 = _skip_gate("earlier hard fail")
        gate6 = _skip_gate("earlier hard fail")
    validation["gates"]["gate5"] = gate5
    validation["gates"]["gate6"] = gate6

    gate7 = _gate7_synthesis(strategy_name, params, entry, validation["gates"], tier=tier)
    validation["gates"]["gate7"] = gate7
    validation["verdict"] = gate7["verdict"]
    validation["promotion_eligible"] = gate7["promotion_eligible"]
    validation["clean_pass"] = gate7["clean_pass"]
    validation["pine_eligible"] = gate7["pine_eligible"]
    validation["composite_confidence"] = gate7["composite_confidence"]
    validation["sub_scores"] = gate7["sub_scores"]
    validation["advisories"] = gate7.get("advisories", [])
    validation["soft_warnings"] = gate7["soft_warnings"]
    validation["critical_warnings"] = gate7["critical_warnings"]
    validation["warnings"] = gate7["warnings"]
    validation["hard_fail_reasons"] = gate7["hard_fail_reasons"]
    entry["validation"] = _json_safe(validation)
    return entry


def run_validation_pipeline(
    results: dict,
    *,
    hours: float,
    quick: bool = False,
    top_n: int = DEFAULT_TOP_N,
) -> dict:
    start = time.time()
    raw_source = copy.deepcopy(results.get("raw_rankings", results.get("rankings", [])))
    raw_rank_field = "discovery_score" if any(
        "discovery_score" in entry for entry in raw_source
    ) else "fitness"
    raw_rankings = _rank_entries(raw_source, by=raw_rank_field)[:top_n]
    ctx = _build_context(raw_rankings)
    print(
        "[validate] TECL context "
        f"{len(ctx.df)} bars | {len(ctx.bears)} bears | {len(ctx.bulls)} bulls | "
        f"N_eff={ctx.n_eff} | expected max RS={ctx.expected_max:.3f}"
    )

    reopt_minutes, reopt_pop_size = _choose_reopt_budget(hours, quick)
    print(f"[validate] Gate 6 re-opt budget: {reopt_minutes:.1f}m @ pop {reopt_pop_size}")

    enriched_rankings = [
        _validate_entry(
            entry,
            ctx,
            reopt_minutes=reopt_minutes,
            reopt_pop_size=reopt_pop_size,
        )
        for entry in raw_rankings
        if entry.get("metrics")
    ]

    final_pass = [entry for entry in enriched_rankings if entry["validation"]["verdict"] == "PASS"]
    final_warn = [entry for entry in enriched_rankings if entry["validation"]["verdict"] == "WARN"]
    final_fail = [entry for entry in enriched_rankings if entry["validation"]["verdict"] == "FAIL"]

    validated_rankings = _rank_entries(final_pass, by="fitness")
    champion = copy.deepcopy(validated_rankings[0]) if validated_rankings else None

    summary = {
        "raw_candidates": len(raw_rankings),
        "evaluated": len(enriched_rankings),
        "pre_tier3_pass": sum(
            1 for entry in enriched_rankings
            if not any(
                entry["validation"]["gates"][gate_name].get("hard_fail_reasons")
                for gate_name in ("gate1", "gate2", "gate3", "gate4")
            )
        ),
        "validated_pass": len(final_pass),
        "validated_warn": len(final_warn),
        "validated_fail": len(final_fail),
        "tier3_minutes": reopt_minutes,
        "tier3_pop_size": reopt_pop_size,
        "elapsed_seconds": round(time.time() - start, 1),
        "run_integrity": ctx.run_integrity,
        "null": {
            "beta_alpha": round(ctx.null["beta_alpha"], 3),
            "beta_beta": round(ctx.null["beta_beta"], 3),
            "expected_max_regime_score": round(ctx.expected_max, 4),
            "n_eff": ctx.n_eff,
        },
    }
    if champion:
        summary["champion"] = {
            "strategy": champion["strategy"],
            "fitness": champion["fitness"],
            "composite_confidence": champion["validation"]["composite_confidence"],
        }

    return {
        "raw_rankings": enriched_rankings,
        "validated_rankings": validated_rankings,
        "champion": champion,
        "validation_summary": summary,
    }

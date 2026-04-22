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
7. Promotion readiness and backtest certification

Only PASS candidates are eligible for leaderboard promotion. Backtest
certification is stricter and also depends on run-integrity checks and
completed run artifacts.
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

from engine.regime_helpers import detect_bear_regimes, detect_bull_regimes, score_regime_capture
from engine.canonical_params import effective_tier as compute_effective_tier
from data.loader import get_tecl_data
from strategies.markers import score_marker_alignment
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
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
from validation.integrity import validate_run_integrity
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


def _interp(value: float, fail: float, soft: float, pass_: float) -> float:
    """Smooth [0,1] interpolation between three anchors.

    fail → 0.0
    soft → 0.5
    pass_ → 1.0

    Linear between anchors; clamped at endpoints. Assumes fail < soft < pass_.
    """
    value = float(value)
    if value >= pass_:
        return 1.0
    if value <= fail:
        return 0.0
    if value < soft:
        denom = soft - fail
        return 0.5 * (value - fail) / denom if denom > 0 else 0.5
    denom = pass_ - soft
    return 0.5 + 0.5 * (value - soft) / denom if denom > 0 else 0.5


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
    """Trade sufficiency sub-score, charter-aligned.

    Charter: trend strategies should not be punished for inactivity.
    A year of holding through new highs is a successful year. Over TECL's
    full history (~18 years at ≤ 5 trades/year = max 90 trades), a good
    long-only trend strategy typically sits between 10 and 25 trades.

    Anchors:
      0 trades → 0.0  (strategy never engaged — no signal to evaluate)
      10 trades → 0.5
      20+ trades → 1.0
    """
    return _interp(float(trades), 0.0, 10.0, 20.0)


def _geometric_composite(sub_scores: dict) -> float:
    """Weighted geometric mean over present sub-scores.

    A sub-score of None (e.g. a gate skipped due to tier routing) is dropped
    and the remaining weights renormalize. This means T0 and T1 composites are
    computed over their tier-applicable gates only — they don't pay a penalty
    for gates that weren't supposed to run against them.

    Weights per validation-thresholds.md (2026-04-21 revision):
      - Marker shape split into state_agreement (marker_shape) and
        magnitude-weighted per-cycle timing (marker_timing).
      - Named-window performance split out of walk_forward as its own
        sub-score.
      - Cross-asset demoted from 0.10 to 0.05.
      - era_consistency added (2026-04-21 late): min(real_share, modern_share)
        → anchor 0.5x/1.0x/1.5x. Catches strategies that pass the weighted-era
        fitness gate but have ONE era that collapsed (fitness can still >= 1.0
        if other eras compensate — era_consistency guards against this).
    """
    weights = {
        "walk_forward":       0.10,   # all tiers
        "marker_shape":       0.10,   # all tiers (state agreement)
        "marker_timing":      0.15,   # all tiers (per-cycle, magnitude-weighted)
        "named_windows":      0.05,   # all tiers
        "era_consistency":    0.20,   # all tiers — primary era-balance signal (raised from 0.15 when cross_asset was removed)
        "fragility":          0.15,   # T1 (Gate 3) / T2 (Gate 5 Morris)
        "selection_bias":     0.10,   # T2 only
        # cross_asset REMOVED 2026-04-21: penalized TECL-specific era winners
        # (gc_vjatr) for non-portability to TQQQ, which contradicts charter intent
        # (TECL-only by design). Sub-score still computed in gate6 for diagnostics
        # but excluded from composite_confidence.
        "bootstrap":          0.05,   # T2 only
        "regime_consistency": 0.05,   # T2 only
        "trade_sufficiency":  0.05,   # all tiers
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


def _cert_check(check: dict | None, *, pending_reason: str | None = None) -> dict:
    payload = dict(check or {})
    payload.setdefault("passed", False)
    if pending_reason is not None:
        payload.setdefault("status", "pending")
        payload.setdefault("reason", pending_reason)
    else:
        payload.setdefault("status", "missing")
    return payload


def _gate1_candidate(entry: dict, ctx: ValidationContext, *, tier: str = "T2") -> dict:
    """Candidate eligibility. Tier-aware trade-count floor; no tpp gate.

    Trade count floors by tier:
      T0 (Hypothesis): >= 5
      T1 (Tuned):      >= 10
      T2 (Discovered): >= 15

    The trades-per-param (tpp) gate was removed in 2026-04-13 (third revision)
    because it was a statistical prior about fit-determinedness that is already
    tested directly and more powerfully by cross-asset, walk-forward, fragility,
    and HHI gates. In Montauk's low-trade-count regime (≤5 trades/year by charter)
    the tpp gate also actively punished legitimate strategies for having more
    than 5 params — counterproductive. Overfit candidates that survive every
    other gate (cross-asset on TQQQ, walk-forward across 4 windows, ±10% param
    perturbation, HHI, Morris) are not meaningfully overfit; the tpp gate added
    only noise.
    """
    metrics = entry.get("metrics") or {}
    strategy_name = entry.get("strategy", "")
    params = entry.get("params") or {}
    trades = entry.get("trades") or []
    trade_count = int(metrics.get("trades", 0))
    trades_per_year = float(metrics.get("trades_yr", 0.0))
    n_params = int(metrics.get("n_params", 0))
    trades_per_param = trade_count / n_params if n_params > 0 else math.inf

    # Per-tier trade-count floor.
    if tier == "T0":
        trade_floor = 5
    elif tier == "T1":
        trade_floor = 10
    else:  # T2
        trade_floor = 15

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

    # Charter-level hard gate: must accumulate more shares than B&H.
    # `share_multiple` is mathematically the share-count multiplier when equity
    # is marked-to-market — see strategy_engine.BacktestResult.share_multiple.
    # This is the project's primary success criterion; failing it disqualifies
    # the candidate at every tier regardless of marker engagement or other gates.
    share_mult = float(metrics.get("share_multiple", 0.0))
    if share_mult < 1.0:
        hard_fail_reasons.append(
            f"share_multiple={share_mult:.3f}x < 1.0 (charter: must beat B&H shares)"
        )
    if trade_count < trade_floor:
        hard_fail_reasons.append(f"[{tier}] trade_count={trade_count} < {trade_floor}")
    if trades_per_year > 5.0:
        hard_fail_reasons.append(f"trades_per_year={trades_per_year:.2f} > 5.0 (charter)")
    if degeneracy["verdict"] == "FAIL":
        hard_fail_reasons.extend(f"degeneracy: {reason}" for reason in degeneracy["hard_fail_reasons"])
    soft_warnings.extend(f"degeneracy: {reason}" for reason in degeneracy.get("warnings", []))
    if not strategy_integrity.get("charter_compatible", False):
        hard_fail_reasons.append("strategy family is not charter-compatible")

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

    # 2026-04-21 revision: these no longer hard-fail. They depress
    # selection_bias / regime_consistency sub-scores via the existing
    # score formulas, which is enough to penalize confidence.
    if proximity["enrichment_5"] > 3.0 or proximity["enrichment_10"] > 3.0:
        critical_warnings.append(
            f"exit proximity: {proximity['enrichment_5']:.2f}x/{proximity['enrichment_10']:.2f}x near bear starts"
        )

    if jackknife["max_impact_ratio"] > 2.0:
        critical_warnings.append(f"jackknife: dominant cycle {jackknife['max_impact_ratio']:.2f}x")

    # Concentration measures whether returns are dominated by a few big trades.
    # For trend-following strategies with few params (≤ 4 signal params), this
    # is the inherent return profile — a few huge bull runs dominate.  That's
    # how regime strategies work, not a sign of overfit.  Downgrade to soft
    # warning for simple strategies.
    from engine.canonical_params import count_tunable_params as _count_tunable
    _n_signal = _count_tunable(params)
    conc_msg = (
        f"concentration: bull_hhi={concentration['bull_hhi']:.3f} "
        f"bear_hhi={concentration['bear_hhi']:.3f} dom={concentration['dominance']:.2f}x"
    )
    if (
        concentration["bull_flag"]
        or concentration["bear_flag"]
        or concentration["dominance"] > 3.0
    ):
        if _n_signal <= 4:
            soft_warnings.append(conc_msg)
        else:
            critical_warnings.append(conc_msg)
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
    # 2026-04-21: former hard_fail_params (swing > 30%) demoted to critical
    # warnings. The fragility sub-score already reflects the high swing, so
    # confidence will drop appropriately without a veto.
    critical_warnings = [f"fragility: {p}" for p in fragility["hard_fail_params"]]
    hard_fail_reasons: list[str] = []
    return {
        **fragility,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": soft_warnings + critical_warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate4_time_generalization(strategy_name: str, params: dict, ctx: ValidationContext, *, tier: str = "T2") -> dict:
    """Walk-forward + named-window checks. Under the 2026-04-21 framework:

    - Named-window performance is split out as its own `named_windows_score`
      sub-score (previously folded into gate4's verdict only).
    - Walk-forward `hard_fail_reasons` are demoted to critical warnings at
      every tier (previously hard-failed at T1/T2). The walk_forward_score
      uses smooth interpolation to reflect degradation without veto.
    - Named-window hard-fails (zero share_multiple, errors) are demoted to
      critical warnings. The score reflects them via a 0.0 anchor.

    Tier still tags the gate output for diagnostic reading but no longer
    alters verdict logic.
    """
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    walk_forward = analyze_walk_forward(ctx.df, strategy_fn, params, strategy_name)
    named_windows = analyze_named_windows(ctx.df, strategy_fn, params, strategy_name)

    # Walk-forward sub-score: smooth interpolation on avg_oos_is_ratio.
    # Anchors per docs/validation-thresholds.md:
    #   avg < 0.50 → 0.0  (hard-fail anchor)
    #   avg = 0.65 → 0.5  (soft-warn anchor)
    #   avg >= 0.80 → 1.0 (pass anchor)
    avg_ratio = float(walk_forward.get("avg_oos_is_ratio", 0.0))
    walk_forward_score = _interp(avg_ratio, 0.50, 0.65, 0.80)

    # Named-windows sub-score: anchor on min share_multiple across windows.
    # Any errored window → 0.0. Any window with share_multiple <= 0 → 0.0.
    #   min <= 0.0 or error → 0.0
    #   min = 0.60 → 0.5
    #   min >= 1.00 → 1.0
    nw_results = named_windows.get("results", [])
    any_error = any((r.get("error") is not None) or (r.get("share_multiple", 1.0) is None) for r in nw_results)
    window_shares = [float(r.get("share_multiple", 0.0)) for r in nw_results if r.get("error") is None]
    if any_error or not window_shares:
        named_windows_score = 0.0
    else:
        min_share = min(window_shares)
        if min_share <= 0.0:
            named_windows_score = 0.0
        else:
            named_windows_score = _interp(min_share, 0.0, 0.60, 1.00)

    # All former hard_fail_reasons from WF and named_windows become critical
    # warnings — they surface in diagnostics but do not veto. Sub-scores
    # carry the penalty into composite_confidence.
    wf_hard_demoted = [f"walk-forward: {r}" for r in walk_forward.get("hard_fail_reasons", [])]
    nw_hard_demoted = [f"named-window: {r}" for r in named_windows.get("hard_fail_reasons", [])]
    soft_warnings = list(walk_forward.get("soft_warnings", [])) + list(named_windows.get("soft_warnings", []))
    critical_warnings = (
        list(walk_forward.get("critical_warnings", []))
        + list(named_windows.get("critical_warnings", []))
        + wf_hard_demoted
        + nw_hard_demoted
    )
    warnings = soft_warnings + critical_warnings
    hard_fail_reasons: list[str] = []  # no hard fails at this gate anymore
    verdict = "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "tier": tier,
        "walk_forward": walk_forward,
        "named_windows": named_windows,
        "walk_forward_score": round(walk_forward_score, 4),
        "named_windows_score": round(named_windows_score, 4),
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
    hard_fail_reasons: list[str] = []
    # 2026-04-21: Morris interaction flag demoted from hard-fail to critical
    # warning. Morris s_frag sub-score already reflects the swing magnitude
    # via _interp-style clamping, which is enough to depress confidence.
    if morris["interaction_flag"]:
        critical_warnings.append(
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
        # 2026-04-21: demoted from hard-fail to critical warning. s_boot
        # sub-score carries the penalty into composite_confidence.
        critical_warnings.append(
            f"bootstrap downside probability {bootstrap['downside_prob_share_multiple']:.2f} > 0.50"
        )
    else:
        downside = bootstrap["downside_prob_share_multiple"]
        s_boot = bootstrap["s_boot"]
        # For simple strategies (≤ 4 signal params), bootstrap uncertainty
        # reflects the inherent variance of trend-following, not overfitting.
        # Only critical-warn above the hard-fail threshold.
        from engine.canonical_params import count_tunable_params as _count_tunable_g5
        _n_sig = _count_tunable_g5(params)
        crit_floor = 0.50 if _n_sig <= 4 else 0.40
        boot_msg = (
            f"bootstrap warning: ci_width={bootstrap['ci_width']:.3f} "
            f"downside_prob={downside:.2f}"
        )
        if downside > crit_floor:
            critical_warnings.append(boot_msg)
        elif downside > 0.25 or s_boot < 0.20:
            soft_warnings.append(boot_msg)

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
    """Marker-shape gate. Emits two sub-score inputs (state_agreement and
    magnitude-weighted per-cycle timing). Under the 2026-04-21 confidence-
    score framework, this gate has no hard fails — warnings are advisory
    and the sub-scores drive confidence.

    Thresholds (informational / diagnostic only):
      state_agreement < 0.30 → critical warning (essentially uncorrelated with markers)
      state_agreement < 0.50 → soft warning (barely above random alignment)
      missed_cycles > tier_cap → soft warning
      transition_timing < tier_floor → soft warning
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
            "state_agreement": 0.0,
            "timing_magnitude_weighted": 0.0,
        }

    # Tier-specific tolerance: tighter for pre-registered T0 hypotheses, looser
    # for large-search T2 discoveries. Applied to both classic transition-timing
    # and magnitude-weighted timing.
    if tier == "T0":
        tolerance_bars, missed_cap, timing_floor = 20, 2, 0.50
    elif tier == "T1":
        tolerance_bars, missed_cap, timing_floor = 30, 3, 0.40
    else:  # T2
        tolerance_bars, missed_cap, timing_floor = 40, 5, 0.30

    align = score_marker_alignment(ctx.df, trades, tolerance_bars=tolerance_bars)
    state_agreement = float(align.get("state_accuracy", 0.0))
    transition_timing = float(align.get("transition_timing_score", 0.0))
    timing_magnitude_weighted = float(align.get("timing_magnitude_weighted", 0.0))
    target_buys = int(align.get("target_buy_count", 0))
    candidate_buys = int(align.get("candidate_buy_count", 0))
    # Approximate "missed cycles" as the number of marker buys that have no candidate buy
    # within tolerance. The detail list carries per-target match info.
    buy_matches = align.get("buy_transition_matches", []) or []
    missed_cycles = sum(1 for m in buy_matches if (m.get("score") or 0) < 0.1)

    # Universal marker thresholds (apply at every tier — diagnostic only):
    #   < 0.30 = critical warning (essentially uncorrelated)
    #   < 0.50 = soft warning (barely above random)
    UNCORRELATED_FLOOR = 0.30
    BARELY_ABOVE_RANDOM_FLOOR = 0.50

    hard_fail_reasons = []
    soft_warnings = []
    critical_warnings = []
    advisories = []
    if target_buys == 0:
        advisories.append("marker overlap produced zero target buys — skipping shape diagnostics")
    else:
        if state_agreement < UNCORRELATED_FLOOR:
            critical_warnings.append(
                f"marker state_agreement={state_agreement:.3f} < {UNCORRELATED_FLOOR:.2f} "
                f"(essentially uncorrelated with markers)"
            )
        elif state_agreement < BARELY_ABOVE_RANDOM_FLOOR:
            soft_warnings.append(
                f"marker state_agreement={state_agreement:.3f} < {BARELY_ABOVE_RANDOM_FLOOR:.2f} "
                f"(barely above random alignment)"
            )
        if missed_cycles > missed_cap:
            soft_warnings.append(
                f"[{tier}] missed_marker_cycles={missed_cycles} > {missed_cap} (informational)"
            )
        if transition_timing < timing_floor:
            soft_warnings.append(
                f"[{tier}] transition_timing={transition_timing:.3f} < {timing_floor:.2f} (informational)"
            )

    warnings = soft_warnings + critical_warnings
    # Verdict always PASS — marker gate is diagnostic, no veto. Warnings are
    # surfaced for UI but do not drive the verdict under the new framework.
    verdict = "PASS"
    return {
        "verdict": verdict,
        "tier": tier,
        "marker_score": round(float(align.get("score", 0.0)), 4),
        "state_agreement": round(state_agreement, 4),
        "transition_timing": round(transition_timing, 4),
        "timing_magnitude_weighted": round(timing_magnitude_weighted, 4),
        "target_buy_count": target_buys,
        "candidate_buy_count": candidate_buys,
        "missed_cycles": missed_cycles,
        "tolerance_bars": int(align.get("tolerance_bars", 0)),
        "overlap_start": align.get("overlap_start"),
        "overlap_end": align.get("overlap_end"),
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def _gate6_cross_asset(strategy_name: str, params: dict, ctx: ValidationContext, *, reopt_minutes: float, reopt_pop_size: int) -> dict:
    """Cross-asset gate. Under the 2026-04-21 framework this gate is demoted:

    - Weight dropped from 0.10 to 0.05 in the composite.
    - No hard fails. Former veto conditions (TQQQ same-param < 0.50, TQQQ
      re-opt failure) become critical warnings.
    - TECL is 3× leveraged and uniquely volatile; cross-asset portability is
      a useful but non-definitive honesty signal, not a bouncer.

    Cross-asset sub-score anchors (on TQQQ same-param share_multiple):
      error or share < 0.20 → 0.0
      share = 0.50 → 0.5
      share >= 1.00 → 1.0
    """
    cross_asset = cross_asset_validate(strategy_name, params)
    results = cross_asset.get("results", {})
    tqqq = results.get("TQQQ", {})
    qqq = results.get("QQQ", {})

    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons: list[str] = []

    if "error" in tqqq:
        critical_warnings.append(f"TQQQ same-param replay error: {tqqq['error']}")
        cross_asset_score = 0.0
    else:
        tqqq_share = float(tqqq.get("share_multiple", 0.0))
        cross_asset_score = _interp(tqqq_share, 0.20, 0.50, 1.00)
        if tqqq_share < 0.50:
            critical_warnings.append(f"TQQQ same-param share_multiple={tqqq_share:.3f} < 0.50")
        elif tqqq_share < 1.0:
            soft_warnings.append(f"TQQQ same-param share_multiple={tqqq_share:.3f} < 1.00")

    if "error" in qqq:
        soft_warnings.append(f"QQQ same-param replay error: {qqq['error']}")
    else:
        qqq_share = float(qqq.get("share_multiple", 0.0))
        if qqq_share < 0.50:
            soft_warnings.append(f"QQQ same-param share_multiple={qqq_share:.3f} < 0.50")

    tier3 = cross_asset_reoptimize(
        strategy_name,
        minutes=reopt_minutes,
        pop_size=reopt_pop_size,
    )
    if tier3.get("verdict") != "PASS":
        # Demoted from hard-fail to critical warning. Re-opt is a re-tuning
        # sanity check — it's informative, not disqualifying.
        critical_warnings.append(tier3.get("reason", "TQQQ re-optimization failed"))

    warnings = soft_warnings + critical_warnings
    verdict = "WARN" if critical_warnings else "PASS"
    return {
        "verdict": verdict,
        "same_params": cross_asset,
        "tier3_reopt": tier3,
        "cross_asset_score": round(float(cross_asset_score), 4),
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
    run_integrity: dict,
    *,
    tier: str = "T2",
) -> dict:
    """Synthesize composite_confidence and emit the final verdict.

    2026-04-21 two-layer model:
      Layer 1 (correctness) — only gate1 can hard-fail; those map to verdict=FAIL.
      Layer 2 (confidence)  — weighted geometric mean of sub-scores drives verdict.

    Verdict rules:
      FAIL: any gate1 hard_fail_reason OR composite_confidence < 0.40
      WARN: 0.40 <= composite_confidence < 0.70
      PASS: composite_confidence >= 0.70  (admitted to leaderboard)
    """
    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []

    # Under the new framework, only gate1 can emit hard_fail_reasons (Layer 1
    # correctness). Collect everything else defensively but drive verdict on
    # gate1 hard-fails + composite.
    for gate_name in ("gate1", "gate_marker", "gate2", "gate3", "gate4", "gate5", "gate6"):
        gate = gates.get(gate_name, {})
        advisories.extend(gate.get("advisories", []))
        soft_warnings.extend(gate.get("soft_warnings", []))
        critical_warnings.extend(gate.get("critical_warnings", []))
        if gate_name == "gate1":
            hard_fail_reasons.extend(gate.get("hard_fail_reasons", []))

    trade_count = int((entry.get("metrics") or {}).get("trades", 0))

    def _score_if_ran(gate_name: str, field: str, fallback: float | None = None) -> float | None:
        gate = gates.get(gate_name, {})
        if gate.get("verdict") == "SKIPPED":
            return fallback
        value = gate.get(field)
        return float(value) if value is not None else fallback

    # Marker shape sub-score — state_agreement via smooth anchors.
    #   < 0.30 → 0.0  (essentially uncorrelated)
    #   = 0.50 → 0.5  (barely above random)
    #   >= 0.80 → 1.0
    def _marker_shape_sub_score() -> float | None:
        gm = gates.get("gate_marker", {})
        if gm.get("verdict") == "SKIPPED":
            return None
        state_agreement = gm.get("state_agreement")
        if state_agreement is None:
            return float(gm.get("marker_score", 0.0))
        return _interp(float(state_agreement), 0.30, 0.50, 0.80)

    # Marker timing sub-score — magnitude-weighted per-cycle timing from markers.py.
    # Already [0,1] where big cycles dominate; pass through unchanged.
    def _marker_timing_sub_score() -> float | None:
        gm = gates.get("gate_marker", {})
        if gm.get("verdict") == "SKIPPED":
            return None
        timing = gm.get("timing_magnitude_weighted")
        if timing is None:
            return None
        return _clamp(float(timing))

    # Era consistency sub-score (2026-04-21, tuned) — min(real, modern) share
    # multiples on smooth anchors (0.0x → 0.0, 0.6x → 0.5, 1.2x → 1.0).
    # Catches strategies that pass weighted-era fitness (one era compensating
    # for another) but have ONE era that fully collapsed.
    # Anchors tuned so the score grades strategies across the full 0-1.2+ range
    # rather than zeroing out everything below 0.5 (which would annihilate
    # composite_confidence via geometric mean for any strategy with real<0.5).
    def _era_consistency_sub_score() -> float | None:
        m = entry.get("metrics") or {}
        real = m.get("real_share_multiple")
        modern = m.get("modern_share_multiple")
        if real is None or modern is None:
            return None
        return _interp(min(float(real), float(modern)), 0.0, 0.6, 1.2)

    sub_scores: dict = {
        "walk_forward":       _score_if_ran("gate4", "walk_forward_score", 0.0),
        "marker_shape":       _marker_shape_sub_score(),
        "marker_timing":      _marker_timing_sub_score(),
        "named_windows":      _score_if_ran("gate4", "named_windows_score", 0.0),
        "era_consistency":    _era_consistency_sub_score(),
        "fragility":          _score_if_ran("gate5", "fragility_score",
                                            _score_if_ran("gate3", "score")),
        "selection_bias":     _score_if_ran("gate2", "selection_bias_score"),
        "cross_asset":        _score_if_ran("gate6", "cross_asset_score"),
        "bootstrap":          _score_if_ran("gate5", "bootstrap_score"),
        "regime_consistency": _score_if_ran("gate2", "regime_consistency_score"),
        "trade_sufficiency":  _trade_sufficiency_score(trade_count),
    }
    composite_confidence = _geometric_composite(sub_scores)

    certification_checks = {
        "engine_integrity": _cert_check(run_integrity.get("engine_integrity")),
        "golden_regression": _cert_check(run_integrity.get("golden_regression")),
        "shadow_comparator": _cert_check(run_integrity.get("shadow_comparator")),
        "data_quality_precheck": _cert_check(run_integrity.get("data_quality")),
        "artifact_completeness": _cert_check(
            None,
            pending_reason="run artifacts are generated after validation",
        ),
    }

    # Composite note as advisory (not veto)
    if composite_confidence < 0.40:
        advisories.append(f"composite_confidence={composite_confidence:.3f} < 0.40 (FAIL threshold)")
    elif composite_confidence < 0.70:
        advisories.append(f"composite_confidence={composite_confidence:.3f} < 0.70 (below admission)")

    if not certification_checks["shadow_comparator"]["passed"]:
        advisories.append(
            "shadow comparator not satisfied: "
            f"{certification_checks['shadow_comparator'].get('status')}"
        )
    if not certification_checks["data_quality_precheck"]["passed"]:
        advisories.append(
            "data-quality precheck not satisfied: "
            f"{certification_checks['data_quality_precheck'].get('status')}"
        )
    if not certification_checks["artifact_completeness"]["passed"]:
        advisories.append("artifact completeness pending")

    # De-duplicate
    advisories = list(dict.fromkeys(advisories))
    soft_warnings = list(dict.fromkeys(soft_warnings))
    critical_warnings = list(dict.fromkeys(critical_warnings))
    hard_fail_reasons = list(dict.fromkeys(hard_fail_reasons))

    warnings = soft_warnings + critical_warnings

    # Verdict (two-layer):
    #   FAIL: Layer 1 correctness violation OR composite < 0.40
    #   WARN: 0.40 <= composite < 0.70
    #   PASS: composite >= 0.70 (admitted)
    # Warnings (soft/critical) no longer drive verdict — they're advisory.
    if hard_fail_reasons or composite_confidence < 0.40:
        verdict = "FAIL"
    elif composite_confidence < 0.70:
        verdict = "WARN"
    else:
        verdict = "PASS"

    clean_pass = verdict == "PASS" and len(critical_warnings) == 0
    promotion_ready = verdict == "PASS"
    backtest_certified = promotion_ready and all(
        check.get("passed", False) for check in certification_checks.values()
    )

    return {
        "verdict": verdict,
        "tier": tier,
        "promotion_ready": promotion_ready,
        "clean_pass": clean_pass,
        "backtest_certified": backtest_certified,
        "certification_checks": certification_checks,
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
        "promotion_ready": False,
        "backtest_certified": False,
        "clean_pass": False,
        "composite_confidence": 0.0,
        "tier": "T2",
        "tier_reasons": [],
        "certification_checks": {},
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
    # Gate2 bundles result-quality checks (HHI, exit-proximity) with search-bias
    # corrections (deflation, selection-bias score). The result-quality checks
    # ARE informative at T1 but the search-bias thresholds are calibrated for
    # 50K+ GA configs and are too strict for T1's small canonical grid (~50 combos).
    # TODO: split gate2 into result-quality (all tiers) vs search-bias (T2 only).
    # For now, gate2 runs at T2 only. T1 relies on walk-forward + cross-asset +
    # fragility for result quality.
    if tier == "T2" and not hard_stop:
        gate2, _bt_result = _gate2_search_bias(strategy_name, params, ctx)
    elif tier != "T2":
        gate2 = _skip_gate(f"skipped for {tier} — gate2 is T2-only (TODO: split result-quality checks out)")
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

    # ── Gate 4: walk-forward / named windows — ALL tiers (tier-aware strictness) ──
    if not hard_stop:
        gate4 = _gate4_time_generalization(strategy_name, params, ctx, tier=tier)
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

    gate7 = _gate7_synthesis(
        strategy_name,
        params,
        entry,
        validation["gates"],
        ctx.run_integrity,
        tier=tier,
    )
    validation["gates"]["gate7"] = gate7
    validation["verdict"] = gate7["verdict"]
    validation["promotion_ready"] = gate7["promotion_ready"]
    validation["backtest_certified"] = gate7["backtest_certified"]
    validation["clean_pass"] = gate7["clean_pass"]
    validation["certification_checks"] = gate7["certification_checks"]
    validation["composite_confidence"] = gate7["composite_confidence"]
    validation["sub_scores"] = gate7["sub_scores"]
    validation["advisories"] = gate7.get("advisories", [])
    validation["soft_warnings"] = gate7["soft_warnings"]
    validation["critical_warnings"] = gate7["critical_warnings"]
    validation["warnings"] = gate7["warnings"]
    validation["hard_fail_reasons"] = gate7["hard_fail_reasons"]
    entry["validation"] = _json_safe(validation)
    return entry


import multiprocessing

# ── Multiprocessing worker infrastructure for validation ──
_val_ctx = None
_val_reopt_minutes = None
_val_reopt_pop_size = None


def _val_worker_init(strategy_names, reopt_minutes, reopt_pop_size):
    """Per-process initializer — builds ValidationContext once per worker."""
    global _val_ctx, _val_reopt_minutes, _val_reopt_pop_size
    _val_reopt_minutes = reopt_minutes
    _val_reopt_pop_size = reopt_pop_size
    run_integrity = validate_run_integrity(strategy_names)
    df = get_tecl_data(use_yfinance=False)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    bears = detect_bear_regimes(close, dates)
    bulls = detect_bull_regimes(close, dates, bears)
    null = calibrate_null_distribution(samples_per_family=40, use_cache=True)
    n_eff = estimate_n_eff_heuristic()
    expected_max = expected_max_beta(null["beta_alpha"], null["beta_beta"], n_eff)
    leaderboard = []
    lb_path = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
    if os.path.exists(lb_path):
        try:
            with open(lb_path) as f:
                leaderboard = json.load(f)
        except Exception:
            leaderboard = []
    _val_ctx = ValidationContext(
        df=df, close=close, dates=dates, bears=bears, bulls=bulls,
        null=null, n_eff=n_eff, expected_max=expected_max,
        regime_transitions=len(bears) + len(bulls),
        leaderboard=leaderboard, run_integrity=run_integrity,
    )


def _val_worker_run(entry):
    """Validate a single entry in a worker process."""
    if not entry.get("metrics"):
        return None
    return _validate_entry(
        entry, _val_ctx,
        reopt_minutes=_val_reopt_minutes,
        reopt_pop_size=_val_reopt_pop_size,
    )


PARALLEL_VALIDATION_THRESHOLD = 4


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

    candidates = [e for e in raw_rankings if e.get("metrics")]
    n_candidates = len(candidates)

    if n_candidates >= PARALLEL_VALIDATION_THRESHOLD:
        strategy_names = [e.get("strategy", "") for e in raw_rankings if e.get("strategy")]
        n_workers = min(multiprocessing.cpu_count() - 1, n_candidates)
        n_workers = max(2, min(n_workers, 8))
        print(f"[validate] Multicore: {n_workers} workers for {n_candidates} candidates...")
        with multiprocessing.Pool(
            processes=n_workers,
            initializer=_val_worker_init,
            initargs=(strategy_names, reopt_minutes, reopt_pop_size),
        ) as pool:
            enriched_rankings = [
                r for r in pool.map(_val_worker_run, candidates) if r is not None
            ]
    else:
        print(f"[validate] Single-core: {n_candidates} candidates...")
        enriched_rankings = [
            _validate_entry(
                entry, ctx,
                reopt_minutes=reopt_minutes,
                reopt_pop_size=reopt_pop_size,
            )
            for entry in candidates
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

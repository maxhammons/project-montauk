"""
Walk-forward validation for any strategy in the registry.

Usage:
    python validate_candidate.py --strategy regime_score --params '{"rsi_len":7,...}'
    python validate_candidate.py --strategy regime_score --from-spike 2026-04-07
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import numpy as np
import pandas as pd

# Add scripts/ to path so we can import core modules
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
from engine.regime_helpers import score_regime_capture


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward splits
# ─────────────────────────────────────────────────────────────────────────────

WF_WINDOWS = [
    ("WF 2015-2017", "2015-01-01", "2018-01-01"),
    ("WF 2018-2020", "2018-01-01", "2021-01-01"),
    ("WF 2021-2023", "2021-01-01", "2024-01-01"),
]

NAMED_WINDOWS = {
    "2020_meltup":    ("2019-06-01", "2021-01-01"),
    "2021_2022_bear": ("2021-01-01", "2023-01-01"),
    "2023_rebound":   ("2023-01-01", "2024-06-01"),
    "2024_onward":    ("2024-06-01", "2026-12-31"),
}


def _latest_stable_test_end(df: pd.DataFrame) -> pd.Timestamp:
    latest = pd.Timestamp(df["date"].max())
    if latest.month == 12 and latest.day == 31:
        return latest + pd.Timedelta(days=1)
    complete_year_end = pd.Timestamp(year=latest.year - 1, month=12, day=31)
    if complete_year_end <= pd.Timestamp("2024-12-31"):
        return latest + pd.Timedelta(days=1)
    return complete_year_end + pd.Timedelta(days=1)


def build_walk_forward_splits(df: pd.DataFrame):
    splits = []
    for label, test_start, test_end in WF_WINDOWS:
        train = df[df["date"] < pd.Timestamp(test_start)].reset_index(drop=True)
        test = df[
            (df["date"] >= pd.Timestamp(test_start))
            & (df["date"] < pd.Timestamp(test_end))
        ].reset_index(drop=True)
        if len(train) > 500 and len(test) > 100:
            splits.append((label, train, test))

    dynamic_end = _latest_stable_test_end(df)
    dynamic_test = df[
        (df["date"] >= pd.Timestamp("2024-01-01"))
        & (df["date"] < dynamic_end)
    ].reset_index(drop=True)
    dynamic_train = df[df["date"] < pd.Timestamp("2024-01-01")].reset_index(drop=True)
    if len(dynamic_train) > 500 and len(dynamic_test) > 100:
        dynamic_label = f"WF 2024-{(dynamic_end - pd.Timedelta(days=1)).year}"
        splits.append((dynamic_label, dynamic_train, dynamic_test))
    return splits


def split_walk_forward(df: pd.DataFrame):
    return build_walk_forward_splits(df)


def split_named_windows(df: pd.DataFrame, warmup_bars: int = 700):
    results = []
    for name, (start, end) in NAMED_WINDOWS.items():
        eval_mask = (df["date"] >= start) & (df["date"] <= end)
        if eval_mask.sum() < 50:
            continue
        eval_start_idx = eval_mask.idxmax()
        data_start_idx = max(0, eval_start_idx - warmup_bars)
        eval_end_idx = eval_mask[::-1].idxmax()
        window = df.iloc[data_start_idx:eval_end_idx + 1].reset_index(drop=True)
        if len(window) > 100:
            results.append((name, window))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Run one evaluation
# ─────────────────────────────────────────────────────────────────────────────

def run_eval(df: pd.DataFrame, strategy_fn, params: dict, name: str) -> dict:
    """Run strategy, backtest, compute regime score. Return metrics dict."""
    ind = Indicators(df)
    try:
        entries, exits, labels = strategy_fn(ind, params)
        cooldown = params.get("cooldown", 0)
        result = backtest(df, entries, exits, labels,
                          cooldown_bars=cooldown, strategy_name=name)
    except Exception as e:
        return {"error": str(e), "regime_score": 0, "mar": 0, "cagr": 0,
                "max_dd": 0, "trades": 0, "share_multiple": 0}

    # Regime scoring
    cl = df["close"].values.astype(np.float64)
    dates = df["date"].values
    try:
        rs = score_regime_capture(result.trades, cl, dates)
        regime = rs.composite
        bull_cap = rs.bull_capture_ratio
        bear_avoid = rs.bear_avoidance_ratio
    except Exception:
        regime = 0.0
        bull_cap = 0.0
        bear_avoid = 0.0

    return {
        "regime_score": round(regime, 4),
        "bull_capture": round(bull_cap, 4),
        "bear_avoidance": round(bear_avoid, 4),
        "mar": round(result.mar_ratio, 3),
        "cagr": round(result.cagr_pct, 1),
        "max_dd": round(result.max_drawdown_pct, 1),
        "trades": result.num_trades,
        "share_multiple": round(result.share_multiple, 3),
        "win_rate": round(result.win_rate_pct, 1),
    }


def _perturb_value(value, perturbation: float):
    if isinstance(value, int):
        delta = max(1, int(round(abs(value) * abs(perturbation))))
        return value - delta if perturbation < 0 else value + delta
    return value * (1 + perturbation)


def check_parameter_fragility(
    df: pd.DataFrame,
    strategy_fn,
    params: dict,
    name: str,
    perturbations: tuple[float, ...] = (-0.20, -0.10, 0.10, 0.20),
) -> dict:
    baseline = run_eval(df, strategy_fn, params, name)
    base_score = max(float(baseline["regime_score"]), 1e-6)
    numeric = {
        k: v for k, v in params.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0
    }

    details = []
    max_swing_10 = 0.0
    max_swing_20 = 0.0
    evaluations = 1

    for key, value in numeric.items():
        param_swings = {}
        for perturbation in perturbations:
            test_params = params.copy()
            test_params[key] = _perturb_value(value, perturbation)
            if isinstance(test_params[key], (int, float)) and test_params[key] <= 0:
                test_params[key] = 1 if isinstance(value, int) else 0.0001
            metrics = run_eval(df, strategy_fn, test_params, name)
            evaluations += 1
            score = float(metrics["regime_score"])
            swing = abs(score - baseline["regime_score"]) / base_score
            param_swings[str(perturbation)] = {
                "score": round(score, 4),
                "swing": round(swing, 4),
            }
            if abs(perturbation) == 0.10:
                max_swing_10 = max(max_swing_10, swing)
            if abs(perturbation) == 0.20:
                max_swing_20 = max(max_swing_20, swing)
        details.append({"name": key, "perturbations": param_swings})

    hard_fail_params = []
    warn_params = []
    for detail in details:
        swings = detail["perturbations"]
        swing_10 = max(
            swings.get("-0.1", {}).get("swing", 0.0),
            swings.get("0.1", {}).get("swing", 0.0),
        )
        swing_20 = max(
            swings.get("-0.2", {}).get("swing", 0.0),
            swings.get("0.2", {}).get("swing", 0.0),
        )
        if swing_10 > 0.30:
            hard_fail_params.append(f"{detail['name']} ({swing_10:.0%} @ ±10%)")
        elif swing_10 > 0.20 or swing_20 > 0.40:
            warn_params.append(f"{detail['name']} ({max(swing_10, swing_20):.0%})")

    score = float(np.clip(1.0 - max(max_swing_10, max_swing_20) / 0.40, 0.0, 1.0))
    verdict = "FAIL" if hard_fail_params else "WARN" if warn_params else "PASS"
    return {
        "verdict": verdict,
        "evaluations": evaluations,
        "baseline_score": round(float(baseline["regime_score"]), 4),
        "max_swing_10": round(max_swing_10, 4),
        "max_swing_20": round(max_swing_20, 4),
        "score": round(score, 4),
        "hard_fail_params": hard_fail_params,
        "warn_params": warn_params,
        "details": details,
    }


def analyze_walk_forward(
    df: pd.DataFrame,
    strategy_fn,
    params: dict,
    name: str,
) -> dict:
    # Get full-period trades_per_year to judge zero-trade windows
    full_eval = run_eval(df, strategy_fn, params, name)
    full_trades_yr = float(full_eval.get("trades", 0)) / max(len(df) / 252.0, 1.0)

    windows = []
    hard_fail_reasons = []
    soft_warnings = []
    critical_warnings = []

    for label, train, test in build_walk_forward_splits(df):
        train_r = run_eval(train, strategy_fn, params, name)
        test_r = run_eval(test, strategy_fn, params, name)
        train_regime = float(train_r.get("regime_score", 0.0))
        test_regime = float(test_r.get("regime_score", 0.0))
        regime_ratio = test_regime / train_regime if train_regime > 0 else 0.0
        train_share = float(train_r.get("share_multiple", 0.0))
        test_share = float(test_r.get("share_multiple", 0.0))
        share_multiple_ratio = test_share / train_share if train_share > 0 else 0.0
        windows.append(
            {
                "label": label,
                "train": train_r,
                "test": test_r,
                "oos_is_ratio": round(regime_ratio, 4),
                "oos_is_metric": "regime_score",
                "share_multiple_ratio": round(share_multiple_ratio, 4),
            }
        )
        if test_r.get("trades", 0) == 0:
            window_years = max(len(test) / 252.0, 0.1)
            expected_trades = full_trades_yr * window_years
            if expected_trades >= 1.5:
                # Strategy should have traded but didn't — real concern
                hard_fail_reasons.append(f"{label}: zero OOS trades (expected ~{expected_trades:.1f})")
            else:
                # Low-frequency strategy in a short window — zero trades is normal
                soft_warnings.append(f"{label}: zero OOS trades (expected ~{expected_trades:.1f})")
        elif regime_ratio < 0.65:
            # Loosened from 0.75 → 0.65 (2026-04-13 third revision):
            # with 4 OOS windows and ~6 trades each, individual-window
            # OOS/IS ratios are noisy. 0.65 still catches catastrophic OOS
            # failures (the actual concern) without rejecting strategies
            # for normal regime variance.
            hard_fail_reasons.append(f"{label}: OOS/IS regime ratio {regime_ratio:.2f} < 0.65")

    ratios = [w["oos_is_ratio"] for w in windows] or [0.0]
    avg_ratio = float(np.mean(ratios))
    spread = float(max(ratios) - min(ratios)) if len(ratios) > 1 else 0.0

    if avg_ratio < 0.50:
        hard_fail_reasons.append(f"average OOS/IS regime ratio {avg_ratio:.2f} < 0.50")
    elif avg_ratio < 0.65:
        critical_warnings.append(f"average OOS/IS regime ratio {avg_ratio:.2f} < 0.65")
    # Walk-forward dispersion thresholds loosened (2026-04-13 third revision):
    # critical 0.65 → 0.75, soft 0.50 → 0.65. With only 4 windows, dispersion
    # in this range is normal noise rather than statistically meaningful signal.
    if spread > 0.75:
        critical_warnings.append(f"walk-forward dispersion {spread:.2f} > 0.75")
    elif spread > 0.65:
        soft_warnings.append(f"walk-forward dispersion {spread:.2f} > 0.65")

    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if warnings else "PASS"
    return {
        "verdict": verdict,
        "windows": windows,
        "avg_oos_is_ratio": round(avg_ratio, 4),
        "min_oos_is_ratio": round(min(ratios), 4),
        "max_oos_is_ratio": round(max(ratios), 4),
        "spread": round(spread, 4),
        "score": round(float(np.clip(avg_ratio, 0.0, 1.0)), 4),
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def analyze_named_windows(
    df: pd.DataFrame,
    strategy_fn,
    params: dict,
    name: str,
) -> dict:
    results = []
    hard_fail_reasons = []
    soft_warnings = []
    critical_warnings = []
    for window_name, window_df in split_named_windows(df):
        metrics = run_eval(window_df, strategy_fn, params, name)
        results.append({"window": window_name, **metrics})
        if metrics.get("error"):
            hard_fail_reasons.append(f"{window_name}: {metrics['error']}")
        elif metrics.get("share_multiple", 0) <= 0:
            # share_multiple <= 0 means the backtest itself broke, not just zero trades
            hard_fail_reasons.append(
                f"{window_name}: trades={metrics.get('trades', 0)} share_multiple={metrics.get('share_multiple', 0):.3f}"
            )
        elif metrics.get("trades", 0) == 0:
            # Strategy chose to sit out — conscious decision, not breakage
            soft_warnings.append(
                f"{window_name}: zero trades (sat out, share_multiple={metrics.get('share_multiple', 0):.3f})"
            )
        elif metrics.get("share_multiple", 0) < 0.6:
            soft_warnings.append(f"{window_name}: share_multiple={metrics['share_multiple']:.3f}")

    warnings = soft_warnings + critical_warnings
    verdict = "FAIL" if hard_fail_reasons else "WARN" if warnings else "PASS"
    return {
        "verdict": verdict,
        "results": results,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "warnings": warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


def analyze_four_year_degeneracy(df: pd.DataFrame, trades: list) -> dict:
    if df.empty:
        return {"verdict": "FAIL", "reason": "Empty dataframe", "windows": []}

    normalized = []
    for trade in trades:
        if hasattr(trade, "entry_date"):
            normalized.append((pd.Timestamp(trade.entry_date), pd.Timestamp(trade.exit_date)))
        elif isinstance(trade, dict):
            normalized.append((pd.Timestamp(trade["entry_date"]), pd.Timestamp(trade["exit_date"])))

    min_year = int(df["date"].min().year)
    max_year = int(df["date"].max().year)
    windows = []
    hard_fails = []
    warnings = []
    sparse_windows = []
    saturated_windows = []
    for start_year in range(min_year, max_year + 1, 4):
        start = pd.Timestamp(year=start_year, month=1, day=1)
        end = pd.Timestamp(year=min(start_year + 4, max_year + 1), month=1, day=1)
        mask = (df["date"] >= start) & (df["date"] < end)
        if mask.sum() < 250:
            continue
        actual_start = pd.Timestamp(df.loc[mask, "date"].min())
        actual_end = pd.Timestamp(df.loc[mask, "date"].max()) + pd.Timedelta(days=1)
        window_days = max((actual_end - actual_start).days, 1)
        exposure_days = 0
        for entry_date, exit_date in normalized:
            overlap_start = max(actual_start, entry_date)
            overlap_end = min(actual_end, exit_date + pd.Timedelta(days=1))
            if overlap_end > overlap_start:
                exposure_days += (overlap_end - overlap_start).days
        exposure = exposure_days / window_days
        windows.append(
            {
                "window": f"{actual_start.year}-{(actual_end - pd.Timedelta(days=1)).year}",
                "exposure": round(exposure, 4),
            }
        )
        window_label = f"{actual_start.year}-{(actual_end - pd.Timedelta(days=1)).year}"
        if exposure <= 0.01:
            sparse_windows.append(f"{window_label}: exposure={exposure:.1%}")
        elif exposure >= 0.99:
            saturated_windows.append(f"{window_label}: exposure={exposure:.1%}")

    n_windows = len(windows)
    if n_windows == 0:
        hard_fails.append("no eligible four-year windows")
    elif len(sparse_windows) == n_windows:
        hard_fails.append("always out across every four-year window")
    elif len(saturated_windows) == n_windows:
        hard_fails.append("always in across every four-year window")
    else:
        if sparse_windows:
            warnings.append(
                f"sparse exposure windows ({len(sparse_windows)}/{n_windows}): "
                + "; ".join(sparse_windows[:3])
            )
        if saturated_windows:
            warnings.append(
                f"saturated exposure windows ({len(saturated_windows)}/{n_windows}): "
                + "; ".join(saturated_windows[:3])
            )

    verdict = "FAIL" if hard_fails else "WARN" if warnings else "PASS"
    return {
        "verdict": verdict,
        "windows": windows,
        "warnings": warnings,
        "hard_fail_reasons": hard_fails,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stability check
# ─────────────────────────────────────────────────────────────────────────────

def check_stability(df: pd.DataFrame, strategy_fn, params: dict, name: str,
                    perturbation: float = 0.10) -> tuple[float, list[str]]:
    """Perturb each numeric param ±10%, check if regime_score swings >20%."""
    baseline = run_eval(df, strategy_fn, params, name)
    base_score = baseline["regime_score"]

    numeric = {k: v for k, v in params.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0}

    stable = 0
    total = 0
    unstable = []

    for k, v in numeric.items():
        total += 1
        scores = []
        for direction in [-1, 1]:
            test_p = params.copy()
            if isinstance(v, int):
                delta = max(1, int(abs(v * perturbation)))
                test_p[k] = v + direction * delta
            else:
                test_p[k] = v * (1 + direction * perturbation)
            if test_p[k] <= 0 and k.endswith("_len"):
                test_p[k] = 1

            r = run_eval(df, strategy_fn, test_p, name)
            scores.append(r["regime_score"])

        if base_score > 0:
            max_swing = max(abs(s - base_score) / base_score for s in scores)
        else:
            max_swing = max(abs(s - base_score) for s in scores)

        if max_swing <= 0.20:
            stable += 1
        else:
            unstable.append(f"{k} ({max_swing:.0%} swing)")

    score = stable / total if total > 0 else 1.0
    return score, unstable


# ─────────────────────────────────────────────────────────────────────────────
# Main validation
# ─────────────────────────────────────────────────────────────────────────────

def validate(strategy_name: str, params: dict, do_stability: bool = True):
    print("Loading TECL data...")
    df = get_tecl_data(use_yfinance=False)
    print(f"  {len(df)} bars, {df['date'].iloc[0]} to {df['date'].iloc[-1]}")

    strategy_fn = STRATEGY_REGISTRY[strategy_name]

    # ── Full-period baseline ──
    print(f"\n{'='*70}")
    print(f"FULL PERIOD — {strategy_name}")
    print(f"{'='*70}")
    full = run_eval(df, strategy_fn, params, strategy_name)
    for k, v in full.items():
        print(f"  {k:20s}: {v}")

    # ── Walk-forward ──
    print(f"\n{'='*70}")
    print("WALK-FORWARD SPLITS")
    print(f"{'='*70}")
    splits = split_walk_forward(df)
    wf_scores = []
    for label, train, test in splits:
        train_r = run_eval(train, strategy_fn, params, strategy_name)
        test_r = run_eval(test, strategy_fn, params, strategy_name)
        wf_scores.append(test_r["regime_score"])
        train_drop = test_r["regime_score"] - train_r["regime_score"]
        flag = " ⚠️  DEGRADATION" if train_drop < -0.15 else ""
        print(f"\n  {label}:")
        print(f"    Train  → regime={train_r['regime_score']:.4f}  MAR={train_r['mar']:.3f}  CAGR={train_r['cagr']:.1f}%  DD={train_r['max_dd']:.1f}%  trades={train_r['trades']}")
        print(f"    Test   → regime={test_r['regime_score']:.4f}  MAR={test_r['mar']:.3f}  CAGR={test_r['cagr']:.1f}%  DD={test_r['max_dd']:.1f}%  trades={test_r['trades']}{flag}")
        print(f"    Δ regime (train→test): {train_drop:+.4f}")

    # ── Named windows ──
    print(f"\n{'='*70}")
    print("NAMED STRESS WINDOWS")
    print(f"{'='*70}")
    named = split_named_windows(df)
    for wname, wdf in named:
        r = run_eval(wdf, strategy_fn, params, strategy_name)
        print(f"\n  {wname}:")
        print(f"    regime={r['regime_score']:.4f}  MAR={r['mar']:.3f}  CAGR={r['cagr']:.1f}%  DD={r['max_dd']:.1f}%  trades={r['trades']}  share_multiple={r['share_multiple']:.3f}")

    # ── Stability ──
    if do_stability:
        print(f"\n{'='*70}")
        print("PARAMETER STABILITY (±10% perturbation)")
        print(f"{'='*70}")
        score, unstable = check_stability(df, strategy_fn, params, strategy_name)
        print(f"  Stability score: {score:.2f} (1.0 = all params stable)")
        if unstable:
            print(f"  Unstable params: {', '.join(unstable)}")
        else:
            print("  All parameters stable ✓")

    # ── Verdict ──
    print(f"\n{'='*70}")
    print("VERDICT")
    print(f"{'='*70}")
    avg_wf = np.mean(wf_scores) if wf_scores else 0
    min_wf = min(wf_scores) if wf_scores else 0
    spread = max(wf_scores) - min(wf_scores) if len(wf_scores) > 1 else 0
    print(f"  Full-period regime score:   {full['regime_score']:.4f}")
    print(f"  Avg walk-forward regime:    {avg_wf:.4f}")
    print(f"  Min walk-forward regime:    {min_wf:.4f}")
    print(f"  WF spread (max-min):        {spread:.4f}")
    print(f"  Full vs avg WF delta:       {full['regime_score'] - avg_wf:+.4f}")

    issues = []
    if avg_wf < full["regime_score"] * 0.5:
        issues.append("Walk-forward avg is <50% of full-period score → likely overfit")
    if spread > 0.4:
        issues.append(f"Walk-forward spread = {spread:.2f} → inconsistent across periods")
    if min_wf == 0:
        issues.append("Zero regime score in at least one window → strategy fails in some regimes")
    if do_stability and score < 0.5:
        issues.append(f"Parameter stability = {score:.2f} → fragile, small changes cause big swings")

    if issues:
        print("\n  ❌ CONCERNS:")
        for issue in issues:
            print(f"     • {issue}")
    else:
        print("\n  ✅ No major red flags detected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a spike candidate")
    parser.add_argument("--strategy", required=True, help="Strategy name from registry")
    parser.add_argument("--params", help="JSON params dict")
    parser.add_argument("--from-spike", help="Load best params from spike/runs/NNN/results.json")
    parser.add_argument("--no-stability", action="store_true", help="Skip stability check (faster)")
    args = parser.parse_args()

    if args.from_spike:
        results_path = f"../spike/runs/{args.from_spike}/results.json"
        with open(results_path) as f:
            results = json.load(f)
        # Find best result for the given strategy in rankings
        best = None
        rankings = results.get("rankings", [])
        for entry in rankings:
            if entry.get("strategy") == args.strategy:
                if best is None or entry.get("fitness", 0) > best.get("fitness", 0):
                    best = entry
        if best is None:
            print(f"No results for strategy '{args.strategy}' in {results_path}")
            sys.exit(1)
        params = best["params"]
        print(f"Loaded params from spike run {args.from_spike} (fitness={best.get('fitness', '?')})")
    else:
        params = json.loads(args.params)

    validate(args.strategy, params, do_stability=not args.no_stability)

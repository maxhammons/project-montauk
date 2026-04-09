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

from data import get_tecl_data
from strategy_engine import Indicators, backtest, BacktestResult
from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
from backtest_engine import score_regime_capture


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward splits
# ─────────────────────────────────────────────────────────────────────────────

WF_BOUNDARIES = [
    ("2018-01-01", "2020-01-01"),
    ("2020-01-01", "2022-01-01"),
    ("2022-01-01", "2024-01-01"),
    ("2024-01-01", "2027-01-01"),
]

NAMED_WINDOWS = {
    "2020_meltup":    ("2019-06-01", "2021-01-01"),
    "2021_2022_bear": ("2021-01-01", "2023-01-01"),
    "2023_rebound":   ("2023-01-01", "2024-06-01"),
    "2024_onward":    ("2024-06-01", "2026-12-31"),
}


def split_walk_forward(df: pd.DataFrame):
    splits = []
    for train_end, test_end in WF_BOUNDARIES:
        train = df[df["date"] < train_end].reset_index(drop=True)
        test = df[df["date"] < test_end].reset_index(drop=True)
        if len(train) > 500 and len(test) > len(train) + 100:
            splits.append((f"WF {train_end[:4]}-{test_end[:4]}", train, test))
    return splits


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
                "max_dd": 0, "trades": 0, "vs_bah": 0}

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
        "vs_bah": round(result.vs_bah_multiple, 3),
        "win_rate": round(result.win_rate_pct, 1),
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
    print(f"Loading TECL data...")
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
    print(f"WALK-FORWARD SPLITS")
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
    print(f"NAMED STRESS WINDOWS")
    print(f"{'='*70}")
    named = split_named_windows(df)
    for wname, wdf in named:
        r = run_eval(wdf, strategy_fn, params, strategy_name)
        print(f"\n  {wname}:")
        print(f"    regime={r['regime_score']:.4f}  MAR={r['mar']:.3f}  CAGR={r['cagr']:.1f}%  DD={r['max_dd']:.1f}%  trades={r['trades']}  vs_bah={r['vs_bah']:.3f}")

    # ── Stability ──
    if do_stability:
        print(f"\n{'='*70}")
        print(f"PARAMETER STABILITY (±10% perturbation)")
        print(f"{'='*70}")
        score, unstable = check_stability(df, strategy_fn, params, strategy_name)
        print(f"  Stability score: {score:.2f} (1.0 = all params stable)")
        if unstable:
            print(f"  Unstable params: {', '.join(unstable)}")
        else:
            print(f"  All parameters stable ✓")

    # ── Verdict ──
    print(f"\n{'='*70}")
    print(f"VERDICT")
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
        print(f"\n  ❌ CONCERNS:")
        for issue in issues:
            print(f"     • {issue}")
    else:
        print(f"\n  ✅ No major red flags detected")


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

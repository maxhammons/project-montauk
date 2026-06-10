"""
TRUE out-of-sample walk-forward: re-optimize on train, evaluate on held-out test.

WHY this exists: the existing gate-4 walk-forward
(`validation/candidate.py::analyze_walk_forward`) replays the SAME
full-history-optimized params on both the train and test slices. That measures
temporal *consistency* of a fixed config — useful, but it is not out-of-sample
validation, because the candidate's params were chosen with knowledge of every
test window. This module adds the real thing: for each anchored walk-forward
split, a fresh randomized param search is run on the TRAIN slice only, and the
train-selected winner is then scored on the held-out TEST slice it never saw.
A candidate whose edge is real should survive being re-discovered from
train-only data; an overfit candidate's re-optimized cousins will collapse OOS.

Conventions shared with the existing gate 4 (so ratios stay comparable to the
sub-score anchors in `docs/validation-thresholds.md`):
  - Splits come from `build_walk_forward_splits` (anchored expanding train,
    disjoint test windows).
  - TEST slices carry NO indicator warmup prefix — indicators warm up inside
    the test window itself, exactly as in `analyze_walk_forward`. Early-window
    NaN bars suppress signals identically for every config, so comparisons
    remain apples-to-apples.
  - Headline per-window ratio is regime_score test/train (candidate.py's
    `oos_is_ratio` convention); share_multiple test/train is reported alongside.

Strategies with an empty STRATEGY_PARAMS space (e.g. chimera ensembles, whose
params are frozen member configs) degenerate gracefully: the only drawable
config is the candidate itself, so the result reduces to a temporal-consistency
measurement with candidate_picked_fraction = 1.0.

Usage:
    python scripts/validation/oos_walk_forward.py            # leaderboard row 0
    python scripts/validation/oos_walk_forward.py --row 1 --evals 150 --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import random as _stdlib_random
import sys
import time

import numpy as np
import pandas as pd

# Add scripts/ to path so we can import core modules
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)
PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)

from data.loader import get_tecl_data
from search.evolve import random_params
from strategies.library import STRATEGY_PARAMS, STRATEGY_REGISTRY
from validation.candidate import build_walk_forward_splits, run_eval


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────

# Verdict anchors deliberately mirror candidate.py's gate-4 average-ratio
# thresholds (WF_AVG_CRITICAL_RATIO / WF_AVG_FAIL_RATIO) so the re-optimized
# OOS/IS ratio reads on the same scale as the existing sub-score.
OOS_WF_PASS_RATIO = 0.65               # avg OOS/IS regime ratio for PASS
OOS_WF_WARN_RATIO = 0.50               # avg OOS/IS regime ratio for WARN; below → FAIL

DEFAULT_EVALS_PER_WINDOW = 150         # ~160 ms/eval × 4 windows ≈ 2 min total
MIN_TRAIN_TRADES = 2                   # configs with < 2 train trades carry no
                                       # selectable signal — skip them
_UNIQUE_DRAW_ATTEMPT_FACTOR = 20       # small discrete spaces exhaust unique
                                       # configs; cap the rejection-sampling loop


def _config_key(params: dict) -> str:
    """Canonical hashable form of a param dict for dedup / identity checks.

    Floats are rounded to 6 dp and ints coerced through float so that a drawn
    `25.0` and a stored `25` compare equal — otherwise candidate-identity
    detection (picked_candidate) would miss numerically identical configs.
    """
    def _norm(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float, np.integer, np.floating)):
            return round(float(v), 6)
        if isinstance(v, dict):
            return {k: _norm(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [_norm(x) for x in v]
        return v

    return json.dumps(_norm(params), sort_keys=True, default=str)


def _draw_configs(space: dict, candidate_params: dict, n: int, window_seed: int) -> list[dict]:
    """Draw up to `n` unique param configs for one window's train search.

    The candidate's own params are always config #0 — the search must be able
    to re-pick the candidate, and its train score anchors picked_candidate.
    Drawn params are merged OVER the candidate so params outside the search
    space (and structural keys like a chimera's `members`) stay fixed.

    `random_params` (search/evolve.py) uses the module-level stdlib RNG, so we
    seed it with a numpy-derived per-window seed and restore the global state
    afterwards — deterministic draws without polluting other callers.
    """
    configs = [dict(candidate_params)]
    seen = {_config_key(candidate_params)}
    if not space or n <= 1:
        return configs

    state = _stdlib_random.getstate()
    try:
        _stdlib_random.seed(window_seed)
        attempts = 0
        max_attempts = n * _UNIQUE_DRAW_ATTEMPT_FACTOR
        while len(configs) < n and attempts < max_attempts:
            attempts += 1
            drawn = random_params(space)
            config = {**candidate_params, **drawn}
            key = _config_key(config)
            if key in seen:
                continue
            seen.add(key)
            configs.append(config)
    finally:
        _stdlib_random.setstate(state)
    return configs


def oos_walk_forward(
    df: pd.DataFrame,
    strategy_name: str,
    candidate_params: dict,
    *,
    evals_per_window: int = DEFAULT_EVALS_PER_WINDOW,
    seed: int = 42,
) -> dict:
    """Re-optimized walk-forward: train-only param search, held-out test eval.

    Per (label, train, test) split from `build_walk_forward_splits(df)`:
      1. Evaluate up to `evals_per_window` unique configs on the TRAIN slice
         (seeded; always including `candidate_params`). Selection metric is
         share_multiple with regime_score as the tie/zero fallback. Configs
         that error or produce < MIN_TRAIN_TRADES train trades are skipped.
      2. Score the train-selected best on the held-out TEST slice. NOTE: test
         slices have no indicator warmup prefix by design — same convention as
         the existing gate 4, see module docstring.
      3. Compute per-window OOS/IS ratios from the train-best's own scores:
         regime_score ratio (headline, matching candidate.py's oos_is_ratio)
         and share_multiple ratio. Zero/negative train score → ratio 0.0.
      4. Record whether the train search re-picked the candidate's own params
         (param-stability signal).

    Determinism: all randomness flows from numpy `default_rng(seed)`; the only
    nondeterministic output field is elapsed_seconds.
    """
    start = time.time()
    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    space = STRATEGY_PARAMS.get(strategy_name, {})
    rng = np.random.default_rng(seed)
    candidate_key = _config_key(candidate_params)

    windows = []
    for label, train, test in build_walk_forward_splits(df):
        window_seed = int(rng.integers(0, 2**32))
        configs = _draw_configs(space, candidate_params, evals_per_window, window_seed)

        best = None  # (sort_key, config, train_metrics)
        skipped = 0
        for config in configs:
            metrics = run_eval(train, strategy_fn, config, strategy_name)
            if metrics.get("error") or metrics.get("trades", 0) < MIN_TRAIN_TRADES:
                skipped += 1
                continue
            sort_key = (
                float(metrics.get("share_multiple", 0.0)),
                float(metrics.get("regime_score", 0.0)),
            )
            if best is None or sort_key > best[0]:
                best = (sort_key, config, metrics)

        fallback_reason = None
        if best is None:
            # Every config errored or under-traded on train. Fall back to the
            # candidate itself so the window still produces a (poor) reading
            # instead of silently vanishing from the average.
            fallback_reason = "no config cleared the train filter; scored candidate as-is"
            fb_metrics = run_eval(train, strategy_fn, dict(candidate_params), strategy_name)
            best = ((0.0, 0.0), dict(candidate_params), fb_metrics)

        _, train_best_params, train_metrics = best
        test_metrics = run_eval(test, strategy_fn, train_best_params, strategy_name)

        train_regime = float(train_metrics.get("regime_score", 0.0))
        test_regime = float(test_metrics.get("regime_score", 0.0))
        regime_ratio = test_regime / train_regime if train_regime > 0 else 0.0
        train_share = float(train_metrics.get("share_multiple", 0.0))
        test_share = float(test_metrics.get("share_multiple", 0.0))
        share_ratio = test_share / train_share if train_share > 0 else 0.0

        window = {
            "label": label,
            "train_best_params": train_best_params,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "oos_is_ratio": round(regime_ratio, 4),
            "oos_is_metric": "regime_score",
            "share_multiple_ratio": round(share_ratio, 4),
            "picked_candidate": _config_key(train_best_params) == candidate_key,
            "configs_evaluated": len(configs),
            "configs_skipped": skipped,
        }
        if fallback_reason:
            window["fallback_reason"] = fallback_reason
        windows.append(window)

    regime_ratios = [w["oos_is_ratio"] for w in windows] or [0.0]
    share_ratios = [w["share_multiple_ratio"] for w in windows] or [0.0]
    avg_ratio = float(np.mean(regime_ratios))
    avg_share = float(np.mean(share_ratios))
    picked_fraction = (
        float(np.mean([w["picked_candidate"] for w in windows])) if windows else 0.0
    )

    verdict = (
        "PASS" if avg_ratio >= OOS_WF_PASS_RATIO
        else "WARN" if avg_ratio >= OOS_WF_WARN_RATIO
        else "FAIL"
    )
    return {
        "method": "reoptimized_walk_forward",
        "evals_per_window": evals_per_window,
        "seed": seed,
        "windows": windows,
        "avg_oos_is_ratio": round(avg_ratio, 4),
        "avg_share_ratio": round(avg_share, 4),
        "candidate_picked_fraction": round(picked_fraction, 4),
        "verdict": verdict,
        "elapsed_seconds": round(time.time() - start, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(strategy_name: str, result: dict) -> None:
    """Pretty-print without the bulky per-window param dicts."""
    print(f"\n{'=' * 70}")
    print(f"RE-OPTIMIZED WALK-FORWARD — {strategy_name}")
    print(f"{'=' * 70}")
    print(f"  evals/window={result['evals_per_window']}  seed={result['seed']}")
    for w in result["windows"]:
        tr, te = w["train_metrics"], w["test_metrics"]
        picked = "candidate" if w["picked_candidate"] else "re-opt    "
        print(f"\n  {w['label']}  [train-best: {picked}]  "
              f"(evaluated {w['configs_evaluated']}, skipped {w['configs_skipped']})")
        print(f"    Train → regime={tr.get('regime_score', 0):.4f}  "
              f"share={tr.get('share_multiple', 0):.3f}  trades={tr.get('trades', 0)}")
        print(f"    Test  → regime={te.get('regime_score', 0):.4f}  "
              f"share={te.get('share_multiple', 0):.3f}  trades={te.get('trades', 0)}")
        print(f"    OOS/IS regime={w['oos_is_ratio']:.4f}  "
              f"share_ratio={w['share_multiple_ratio']:.4f}")
        if w.get("fallback_reason"):
            print(f"    ⚠️  {w['fallback_reason']}")
    print(f"\n  avg_oos_is_ratio (regime):  {result['avg_oos_is_ratio']:.4f}")
    print(f"  avg_share_ratio:            {result['avg_share_ratio']:.4f}")
    print(f"  candidate_picked_fraction:  {result['candidate_picked_fraction']:.2f}")
    print(f"  verdict:                    {result['verdict']}")
    print(f"  elapsed:                    {result['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TRUE out-of-sample walk-forward (re-optimize on train, eval on test)"
    )
    parser.add_argument("--row", type=int, default=0,
                        help="spike/leaderboard.json row to validate (default 0 = champion)")
    parser.add_argument("--evals", type=int, default=DEFAULT_EVALS_PER_WINDOW,
                        help="param configs evaluated per window's train search")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    leaderboard_path = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
    with open(leaderboard_path) as f:
        leaderboard = json.load(f)
    entry = leaderboard[args.row]
    strategy_name = entry["strategy"]
    candidate_params = entry["params"]
    print(f"Leaderboard row {args.row}: {strategy_name} "
          f"(montauk_score={entry.get('montauk_score', '?')})")

    df = get_tecl_data(use_yfinance=False)
    result = oos_walk_forward(
        df, strategy_name, candidate_params,
        evals_per_window=args.evals, seed=args.seed,
    )
    _print_summary(strategy_name, result)

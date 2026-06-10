#!/usr/bin/env python3
"""
CSCV / Probability of Backtest Overfitting (PBO) for Project Montauk.

Implements Combinatorially Symmetric Cross-Validation from Bailey, Borwein,
López de Prado & Zhu, "The Probability of Backtest Overfitting" (Journal of
Computational Finance, 2017).

Idea: take the candidate's parameter NEIGHBORHOOD (the candidate config plus
seeded random draws from its strategy's STRATEGY_PARAMS space), backtest every
variant once over the full history, and build a T×M matrix of per-bar log
returns. Partition the T rows into contiguous blocks; for many random
half-and-half block splits, pick the in-sample (IS) best variant by Sharpe and
ask where it lands out-of-sample (OOS). The relative OOS rank
omega = rank/(M+1) maps to a logit lambda = ln(omega/(1-omega)); PBO is the
fraction of splits where lambda <= 0, i.e. the IS winner falls in the bottom
half OOS.

Anchors (from the paper and common practice):
  - PBO <= 0.20  → acceptable: IS selection carries genuine OOS skill (PASS)
  - PBO  > 0.50  → IS selection is no better than a coin flip; the "edge" is
                   pure selection noise (FAIL)
  - in between   → elevated overfit risk, research artifact only (WARN)

Also reported:
  - median logit lambda (positive = IS winners tend to stay above median OOS)
  - degradation slope: OLS slope of OOS Sharpe of the IS-best on its IS Sharpe
    across splits — a NEGATIVE slope is the classic overfitting signature
    (the harder you optimize IS, the worse you do OOS)
  - candidate_oos_top_half_prob: probability the CANDIDATE itself (not the
    per-split IS winner) ranks in the OOS top half

Determinism: a single numpy default_rng(seed) drives both the variant draws
(via a temporarily re-seeded stdlib `random`, which `random_params` uses) and
the block-split sampling.

Warmup: all return series share a common 700-bar head trim. Every registered
strategy's slowest indicator (EMA-300 / TEMA-200 / Donchian-200 etc.) is fully
warm well before bar 700, so the trim removes the NaN-indicator ramp for the
candidate and every neighbor with one simple, strategy-agnostic rule.

Standalone — not wired into the validation pipeline yet.

Usage:
    python3 scripts/validation/pbo.py            # run on the leaderboard champion
"""

from __future__ import annotations

import json
import math
import os
import random as _stdlib_random
import sys
import time

import numpy as np

# Add scripts/ to path so we can import core modules
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
LEADERBOARD_FILE = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")

WARMUP_BARS = 700  # common indicator-warmup head trim (see module docstring)
MIN_USABLE_VARIANTS = 8  # below this, ranks are too coarse for a meaningful PBO
MIN_TRADES = 2  # variants with < 2 trades carry no selectable signal
_STD_GUARD = 1e-12  # Sharpe denominator guard

# Verdict anchors (Bailey et al. 2017; see module docstring)
PBO_PASS_MAX = 0.20
PBO_WARN_MAX = 0.50


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _rankdata(x: np.ndarray) -> np.ndarray:
    """Ascending ranks 1..M with average ranks for ties (scipy-free)."""
    x = np.asarray(x, dtype=np.float64)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=np.float64)
    ranks[order] = np.arange(1, len(x) + 1, dtype=np.float64)
    # Average ranks across tied values
    sorted_x = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        if j > i:
            avg = (i + j) / 2.0 + 1.0
            ranks[order[i : j + 1]] = avg
        i = j + 1
    return ranks


def _sharpe(rows: np.ndarray) -> np.ndarray:
    """Per-column mean/std Sharpe over the given rows (un-annualized — ranks
    are invariant under the monotone annualization factor)."""
    mean = rows.mean(axis=0)
    std = rows.std(axis=0)
    return mean / np.maximum(std, _STD_GUARD)


def _config_key(params: dict) -> str:
    return json.dumps(params, sort_keys=True, default=str)


def _draw_variant_configs(
    candidate_params: dict, space: dict, n_variants: int, rng: np.random.Generator
) -> list:
    """Candidate + (n_variants-1) seeded, deduplicated draws from the space.

    `random_params` uses the module-level stdlib `random`, so we temporarily
    seed it from our numpy rng (and restore the global state afterwards) to
    keep the draws deterministic without touching evolve.py.
    """
    from search.evolve import random_params

    configs = [candidate_params]
    seen = {_config_key(candidate_params)}
    if not space:
        return configs  # nothing perturbable — neighborhood is the point itself

    state = _stdlib_random.getstate()
    _stdlib_random.seed(int(rng.integers(0, 2**32)))
    try:
        attempts = 0
        # Small spaces can hold fewer than n_variants distinct configs;
        # the attempt cap keeps this loop finite either way.
        while len(configs) < n_variants and attempts < n_variants * 50:
            attempts += 1
            params = random_params(space)
            key = _config_key(params)
            if key in seen:
                continue
            seen.add(key)
            configs.append(params)
    finally:
        _stdlib_random.setstate(state)
    return configs


def _build_return_matrix(df, strategy_name: str, configs: list) -> tuple:
    """Backtest every config once; return (T×M log-return matrix, n_used,
    candidate_usable). Column 0 is always the candidate when usable.

    Per-bar log returns come from BacktestResult.equity_curve — piecewise
    flat (zeros) while out of the market, which is exactly what CSCV needs.
    Variants that raise or produce < MIN_TRADES trades are dropped; exact
    duplicate return columns are collapsed (identical series would only
    distort the rank denominator).
    """
    from engine.strategy_engine import Indicators, backtest
    from strategies.library import STRATEGY_REGISTRY

    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    ind = Indicators(df)  # shared indicator cache across all variants

    columns = []
    seen_series = set()
    candidate_usable = False
    for idx, params in enumerate(configs):
        try:
            entries, exits, labels = strategy_fn(ind, params)
            result = backtest(
                df,
                entries,
                exits,
                labels,
                cooldown_bars=int(params.get("cooldown", 0)),
                strategy_name=strategy_name,
            )
        except Exception:
            continue
        if result.num_trades < MIN_TRADES:
            continue
        equity = np.clip(np.asarray(result.equity_curve, dtype=np.float64), 1e-9, None)
        rets = np.diff(np.log(equity))[WARMUP_BARS:]
        series_key = rets.tobytes()
        if series_key in seen_series:
            continue
        seen_series.add(series_key)
        if idx == 0:
            candidate_usable = True
        columns.append(rets)

    if not columns:
        return np.empty((0, 0)), 0, False
    return np.column_stack(columns), len(columns), candidate_usable


# ─────────────────────────────────────────────────────────────────────────────
# CSCV core
# ─────────────────────────────────────────────────────────────────────────────


def _sample_splits(n_blocks: int, n_splits: int, rng: np.random.Generator) -> list:
    """Distinct random combinations of n_blocks/2 block indices (the IS half).

    The exact CSCV enumerates all C(n_blocks, n_blocks/2) combinations; with
    the 16-block default that is 12,870, so we Monte-Carlo sample n_splits
    distinct ones instead.
    """
    half = n_blocks // 2
    total = math.comb(n_blocks, half)
    target = min(n_splits, total)
    picks, seen = [], set()
    attempts = 0
    while len(picks) < target and attempts < n_splits * 100:
        attempts += 1
        combo = tuple(sorted(rng.choice(n_blocks, size=half, replace=False).tolist()))
        if combo in seen:
            continue
        seen.add(combo)
        picks.append(combo)
    return picks


def cscv_pbo(
    df,
    strategy_name: str,
    candidate_params: dict,
    *,
    n_variants: int = 32,
    n_blocks: int = 16,
    n_splits: int = 200,
    seed: int = 42,
) -> dict:
    """Run CSCV and estimate the Probability of Backtest Overfitting.

    Parameters
    ----------
    df : OHLCV DataFrame (e.g. loader.get_tecl_data())
    strategy_name : key into STRATEGY_REGISTRY / STRATEGY_PARAMS
    candidate_params : the certified config under test (becomes variant 0)
    n_variants : neighborhood size including the candidate
    n_blocks : contiguous time blocks (must be even)
    n_splits : random IS/OOS block combinations to evaluate
    seed : drives variant draws AND split sampling (numpy default_rng)

    Returns a summary dict (see module docstring for verdict anchors).
    """
    if n_blocks % 2 != 0:
        raise ValueError(f"n_blocks must be even, got {n_blocks}")
    t0 = time.time()
    rng = np.random.default_rng(seed)

    from strategies.library import STRATEGY_PARAMS, STRATEGY_REGISTRY

    if strategy_name not in STRATEGY_REGISTRY:
        return {
            "method": "cscv_pbo",
            "status": "unknown_strategy",
            "strategy": strategy_name,
            "elapsed_seconds": round(time.time() - t0, 2),
        }

    space = STRATEGY_PARAMS.get(strategy_name, {})
    configs = _draw_variant_configs(candidate_params, space, n_variants, rng)
    matrix, n_used, candidate_usable = _build_return_matrix(df, strategy_name, configs)

    base = {
        "method": "cscv_pbo",
        "strategy": strategy_name,
        "n_variants_used": n_used,
        "n_blocks": n_blocks,
        "n_splits": n_splits,
        "seed": seed,
    }
    if not candidate_usable:
        base.update(
            {
                "status": "candidate_unusable",
                "elapsed_seconds": round(time.time() - t0, 2),
            }
        )
        return base
    if n_used < MIN_USABLE_VARIANTS:
        base.update(
            {
                "status": "insufficient_variants",
                "min_required": MIN_USABLE_VARIANTS,
                "elapsed_seconds": round(time.time() - t0, 2),
            }
        )
        return base

    T, M = matrix.shape
    blocks = np.array_split(np.arange(T), n_blocks)
    splits = _sample_splits(n_blocks, n_splits, rng)

    lambdas = []
    candidate_top_half = []
    is_best_pairs = []  # (IS Sharpe of IS-best, OOS Sharpe of IS-best)
    all_block_ids = set(range(n_blocks))
    for combo in splits:
        is_rows = np.concatenate([blocks[b] for b in combo])
        oos_rows = np.concatenate(
            [blocks[b] for b in sorted(all_block_ids - set(combo))]
        )

        is_sharpe = _sharpe(matrix[is_rows])
        oos_sharpe = _sharpe(matrix[oos_rows])

        star = int(np.argmax(is_sharpe))  # IS-best variant
        oos_ranks = _rankdata(oos_sharpe)  # ascending: 1 = worst OOS

        omega = oos_ranks[star] / (M + 1)
        lambdas.append(math.log(omega / (1.0 - omega)))
        candidate_top_half.append(oos_ranks[0] / (M + 1) > 0.5)
        is_best_pairs.append((float(is_sharpe[star]), float(oos_sharpe[star])))

    lambdas = np.asarray(lambdas)
    pbo = float(np.mean(lambdas <= 0.0))

    is_vals = np.asarray([p[0] for p in is_best_pairs])
    oos_vals = np.asarray([p[1] for p in is_best_pairs])
    if np.std(is_vals) > _STD_GUARD:
        degradation_slope = float(np.polyfit(is_vals, oos_vals, 1)[0])
    else:
        degradation_slope = 0.0  # no IS spread across splits — slope undefined

    if pbo <= PBO_PASS_MAX:
        verdict = "PASS"
    elif pbo <= PBO_WARN_MAX:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    base.update(
        {
            "n_splits_evaluated": len(splits),
            "n_return_rows": int(T),
            "pbo": pbo,
            "median_logit": float(np.median(lambdas)),
            "degradation_slope": degradation_slope,
            "candidate_oos_top_half_prob": float(np.mean(candidate_top_half)),
            "verdict": verdict,
            "elapsed_seconds": round(time.time() - t0, 2),
            "status": "ok",
        }
    )
    return base


# ─────────────────────────────────────────────────────────────────────────────
# CLI — run against the leaderboard champion
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    from data.loader import get_tecl_data
    from strategies.library import STRATEGY_PARAMS

    with open(LEADERBOARD_FILE) as f:
        leaderboard = json.load(f)
    if not leaderboard:
        print("Leaderboard is empty — nothing to test.")
        return

    # Row 0 is the active champion. Strategies with an empty STRATEGY_PARAMS
    # space (e.g. static certified chimeras) have no parameter neighborhood
    # to perturb, so CSCV cannot apply — fall back to the highest-ranked row
    # whose strategy exposes a perturbable space.
    row = leaderboard[0]
    if not STRATEGY_PARAMS.get(row.get("strategy"), {}):
        for entry in leaderboard:
            if STRATEGY_PARAMS.get(entry.get("strategy"), {}):
                print(
                    f"[pbo] Row 0 ({row.get('strategy')}) has an empty param "
                    f"space — falling back to '{entry.get('strategy')}'."
                )
                row = entry
                break

    strategy_name = row["strategy"]
    candidate_params = row.get("params", {})
    print(f"[pbo] CSCV on champion: {strategy_name}")

    df = get_tecl_data()
    result = cscv_pbo(df, strategy_name, candidate_params)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

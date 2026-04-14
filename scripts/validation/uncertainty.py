"""
Expensive uncertainty checks used by the validation funnel.

These checks are intentionally isolated from the main pipeline so the gate
logic remains readable:
  - Morris-style elementary effects for interaction-aware fragility
  - Stationary bootstrap on daily bars for uncertainty around regime score and
    vs-buy-and-hold performance
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from strategies import STRATEGY_PARAMS
from validation.candidate import run_eval


def _step_param(value, meta, delta_norm: float):
    lo, hi, step, typ = meta
    span = hi - lo
    if span <= 0:
        return value
    target = value + delta_norm * span
    if typ == int:
        steps = round((target - lo) / step)
        target = lo + steps * step
        return int(min(hi, max(lo, target)))
    steps = round((target - lo) / step)
    target = lo + steps * step
    return round(min(hi, max(lo, target)), 4)


def morris_fragility(
    df: pd.DataFrame,
    strategy_fn,
    strategy_name: str,
    params: dict,
    *,
    trajectories: int = 30,
    delta: float = 0.2,
) -> dict:
    space = STRATEGY_PARAMS.get(strategy_name, {})
    numeric = [
        name for name, value in params.items()
        if name in space and isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    # Exclude cooldown from tunable count — it's structural (trade throttling),
    # not signal-generating, so it shouldn't inflate sensitivity thresholds.
    # Matches canonical_params.count_tunable_params behaviour.
    numeric_signal = [n for n in numeric if n != "cooldown"]
    baseline = run_eval(df, strategy_fn, params, strategy_name)
    baseline_rs = max(float(baseline.get("regime_score", 0.0)), 1e-6)
    if not numeric:
        return {
            "method": "morris",
            "trajectories": trajectories,
            "delta": delta,
            "evaluations": 1,
            "max_swing": 0.0,
            "s_frag": 1.0,
            "interaction_flag": False,
            "warning_flag": False,
            "parameters": [],
        }

    rng = np.random.default_rng(42)
    effects = defaultdict(list)
    evaluations = 0
    max_swing = 0.0

    for _ in range(trajectories):
        current = params.copy()
        order = list(rng.permutation(numeric))
        prev = run_eval(df, strategy_fn, current, strategy_name)
        prev_rs = float(prev.get("regime_score", 0.0))
        evaluations += 1
        for name in order:
            meta = space[name]
            test_params = current.copy()
            direction = 1.0 if rng.random() >= 0.5 else -1.0
            test_params[name] = _step_param(current[name], meta, direction * delta)
            curr = run_eval(df, strategy_fn, test_params, strategy_name)
            curr_rs = float(curr.get("regime_score", 0.0))
            effect = (curr_rs - prev_rs) / delta if delta else 0.0
            effects[name].append(effect)
            swing = abs(curr_rs - prev_rs) / max(abs(prev_rs), baseline_rs, 1e-6)
            max_swing = max(max_swing, swing)
            current = test_params
            prev_rs = curr_rs
            evaluations += 1

    parameters = []
    max_sigma_ratio = 0.0
    for name in numeric:
        vals = np.asarray(effects.get(name, [0.0]), dtype=np.float64)
        mu_star = float(np.mean(np.abs(vals)))
        sigma = float(np.std(vals))
        sigma_ratio = sigma / mu_star if mu_star > 1e-9 else math.inf if sigma > 0 else 0.0
        max_sigma_ratio = max(max_sigma_ratio, sigma_ratio if math.isfinite(sigma_ratio) else 10.0)
        parameters.append(
            {
                "name": name,
                "mu_star": round(mu_star, 4),
                "sigma": round(sigma, 4),
                "sigma_ratio": round(float(sigma_ratio), 4) if math.isfinite(sigma_ratio) else 999.0,
            }
        )

    s_frag = float(np.clip(1.0 - max_swing / 0.40, 0.0, 1.0))

    # Scale thresholds by signal-param count (excluding cooldown).  With ≤ 3
    # tunable signal params a strategy has very limited overfitting potential,
    # and sigma_ratio is naturally inflated because each param accounts for a
    # large share of the variance.  The original thresholds were calibrated for
    # complex 6-10 param T2 strategies.
    n_tunable = len(numeric_signal)
    if n_tunable <= 2:
        # Ultra-simple: only hard-fail on extreme swings (> 50% regime-score
        # change from a single 20%-of-range perturbation).
        interaction_flag = max_swing > 0.50
        warning_flag = max_swing > 0.35
    elif n_tunable <= 4:
        interaction_flag = max_swing > 0.40 or (max_sigma_ratio > 2.0 and max_swing > 0.25)
        warning_flag = (0.25 < max_swing <= 0.40) or max_sigma_ratio > 1.5
    else:
        # Original thresholds for complex strategies
        interaction_flag = max_swing > 0.30 or (max_sigma_ratio > 1.5 and max_swing > 0.20)
        warning_flag = (0.20 < max_swing <= 0.30) or max_sigma_ratio > 1.0

    return {
        "method": "morris",
        "trajectories": trajectories,
        "delta": delta,
        "evaluations": evaluations,
        "max_swing": round(max_swing, 4),
        "max_sigma_ratio": round(max_sigma_ratio, 4),
        "s_frag": round(s_frag, 4),
        "interaction_flag": interaction_flag,
        "warning_flag": warning_flag,
        "parameters": parameters,
    }


def _stationary_bootstrap_indices(n: int, *, block_p: float, rng: np.random.Generator) -> np.ndarray:
    indices = np.empty(n, dtype=np.int64)
    indices[0] = rng.integers(0, n)
    for i in range(1, n):
        if rng.random() < block_p:
            indices[i] = rng.integers(0, n)
        else:
            indices[i] = (indices[i - 1] + 1) % n
    return indices


def _bootstrap_df(df: pd.DataFrame, indices: np.ndarray) -> pd.DataFrame:
    base = df.iloc[indices].reset_index(drop=True).copy()
    close = df["close"].values.astype(np.float64)
    returns = np.zeros(len(close), dtype=np.float64)
    returns[1:] = close[1:] / close[:-1] - 1.0
    sampled_returns = returns[indices]

    rebuilt_close = np.empty(len(sampled_returns), dtype=np.float64)
    rebuilt_close[0] = close[0]
    for i in range(1, len(sampled_returns)):
        rebuilt_close[i] = rebuilt_close[i - 1] * (1.0 + sampled_returns[i])

    source_close = base["close"].replace(0, np.nan).ffill().bfill()
    for column in ("open", "high", "low"):
        ratios = (base[column] / source_close).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        base[column] = rebuilt_close * ratios.values
    base["close"] = rebuilt_close
    return base


def stationary_bootstrap_validation(
    df: pd.DataFrame,
    strategy_fn,
    strategy_name: str,
    params: dict,
    *,
    resamples: int = 200,
    expected_block: int = 20,
) -> dict:
    baseline = run_eval(df, strategy_fn, params, strategy_name)
    observed_rs = max(float(baseline.get("regime_score", 0.0)), 1e-6)
    n = len(df)
    rng = np.random.default_rng(43)
    block_p = 1.0 / max(expected_block, 1)

    regime_scores = []
    vs_bah_values = []
    for _ in range(resamples):
        indices = _stationary_bootstrap_indices(n, block_p=block_p, rng=rng)
        boot_df = _bootstrap_df(df, indices)
        metrics = run_eval(boot_df, strategy_fn, params, strategy_name)
        regime_scores.append(float(metrics.get("regime_score", 0.0)))
        vs_bah_values.append(float(metrics.get("vs_bah", 0.0)))

    regime_arr = np.asarray(regime_scores, dtype=np.float64)
    vs_bah_arr = np.asarray(vs_bah_values, dtype=np.float64)
    lo, hi = np.percentile(regime_arr, [5, 95])
    ci_width = float(hi - lo)
    downside_prob = float(np.mean(vs_bah_arr < 1.0))
    s_boot = float(np.clip(1.0 - ci_width / max(observed_rs, 1e-6), 0.0, 1.0))

    return {
        "method": "stationary_bootstrap",
        "resamples": resamples,
        "expected_block": expected_block,
        "observed_regime_score": round(observed_rs, 4),
        "ci_90": [round(float(lo), 4), round(float(hi), 4)],
        "ci_width": round(ci_width, 4),
        "mean_regime_score": round(float(regime_arr.mean()), 4),
        "mean_vs_bah": round(float(vs_bah_arr.mean()), 4),
        "downside_prob_vs_bah": round(downside_prob, 4),
        "s_boot": round(s_boot, 4),
        "hard_fail": downside_prob > 0.5,
        "warning_flag": s_boot < 0.20 or downside_prob > 0.25,
    }

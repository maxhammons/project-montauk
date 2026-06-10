#!/usr/bin/env python3
"""
Selection bias correction for Project Montauk leaderboard.

Deflates Regime Scores using Beta-distribution extreme value theory
with Monte Carlo calibrated null distribution.

The null distribution is computed by running random parameter configs
across all strategy families and measuring their Regime Scores. This
gives the empirical distribution of RS under "no skill" conditions.

Usage:
    python3 scripts/deflate.py                        # Calibrate null + deflate
    python3 scripts/deflate.py --n-eff 500            # Override N_eff estimate
    python3 scripts/deflate.py --samples 200          # More Monte Carlo samples
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.stats import beta as beta_dist

# Add scripts/ to path so we can import core modules
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SCRIPTS_DIR)

PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
HASH_INDEX_FILE = os.path.join(PROJECT_ROOT, "spike", "hash-index.json")
LEADERBOARD_FILE = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
NULL_CACHE_FILE = os.path.join(PROJECT_ROOT, "spike", "null-distribution.json")


# ─────────────────────────────────────────────────────────────────────────────
# N_eff estimation
# ─────────────────────────────────────────────────────────────────────────────


N_EFF_FLOOR = 300  # legacy structural heuristic, kept as an absolute floor
N_EFF_STATE_FILE = os.path.join(PROJECT_ROOT, "spike", "n-eff-state.json")


def estimate_n_eff() -> int:
    """Effective number of search trials, measured from the actual search history.

    Until 2026-06-09 this returned a hardcoded 300 while the hash-index held
    4,116+ deduplicated evaluated configs — understating multiplicity >10x.

    Estimator: the count of deduplicated configs in `spike/hash-index.json`.
    Treating every deduped config as an independent trial is deliberately
    CONSERVATIVE for certification: correlated GA mutations have lower true
    multiplicity, so this upper bound deflates harder than reality, never
    softer. (The eigenvalue-based refinement needs per-config param vectors /
    return series, which the index does not store — tracked in the Phase-2
    backlog.)

    A high-water mark is persisted so pruning or rebuilding the hash-index can
    never quietly relax the deflation bar: N_eff only ratchets upward.
    """
    n_raw = 0
    try:
        with open(HASH_INDEX_FILE) as f:
            index = json.load(f)
        if isinstance(index, dict):
            n_raw = len(index.get("entries", index))
    except (OSError, ValueError):
        n_raw = 0

    high_water = 0
    try:
        with open(N_EFF_STATE_FILE) as f:
            high_water = int(json.load(f).get("high_water", 0))
    except (OSError, ValueError):
        high_water = 0

    n_eff = max(n_raw, high_water, N_EFF_FLOOR)
    if n_eff > high_water:
        try:
            tmp = N_EFF_STATE_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(
                    {
                        "high_water": n_eff,
                        "hash_index_count": n_raw,
                        "updated_utc": time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                        ),
                    },
                    f,
                    indent=2,
                )
            os.replace(tmp, N_EFF_STATE_FILE)
        except OSError:
            pass  # state persistence is best-effort; the live count still rules
    return n_eff


def estimate_n_eff_heuristic(*_args, **_kwargs) -> int:
    """Deprecated alias — use estimate_n_eff(). Kept so stale callers fail soft."""
    return estimate_n_eff()


# ─────────────────────────────────────────────────────────────────────────────
# Monte Carlo null distribution
# ─────────────────────────────────────────────────────────────────────────────


def _calibration_fingerprint() -> dict:
    """Identify the engine + data the null was calibrated on.

    A cached null is only valid for the engine code and dataset that produced
    it. Before 2026-06-09 the cache was reused forever — a strategy could be
    deflated against a null computed on a different engine or stale data.
    """
    import hashlib

    engine_hash = "unknown"
    try:
        from search.evolve import _ENGINE_HASH

        engine_hash = _ENGINE_HASH
    except Exception:
        pass
    data_fingerprint = "unknown"
    manifest_path = os.path.join(PROJECT_ROOT, "data", "manifest.json")
    try:
        with open(manifest_path, "rb") as f:
            data_fingerprint = hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        pass
    return {"engine_hash": engine_hash, "data_fingerprint": data_fingerprint}


def calibrate_null_distribution(
    samples_per_family: int = 40,
    use_cache: bool = True,
    min_valid: int = 5000,
) -> dict:
    """
    Run random parameter configs across all strategy families, compute
    Regime Scores, and fit a Beta distribution to the results.

    This is the empirical null: "what Regime Score would a random
    trend-following strategy achieve on TECL?"

    The cache is keyed on (engine hash, data fingerprint, n_valid): it is
    reused only when calibrated on the same engine + data with at least
    `min_valid` valid samples. The Beta fit has NO silent fallback — an
    infeasible method-of-moments fit raises instead of substituting
    Beta(10,10) (which would silently misstate the null's tails).
    """
    fingerprint = _calibration_fingerprint()
    if use_cache and os.path.exists(NULL_CACHE_FILE):
        with open(NULL_CACHE_FILE) as f:
            cached = json.load(f)
        if (
            cached.get("n_valid", 0) >= min_valid
            and cached.get("engine_hash") == fingerprint["engine_hash"]
            and cached.get("data_fingerprint") == fingerprint["data_fingerprint"]
        ):
            return cached

    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators, backtest
    from strategies.library import STRATEGY_REGISTRY, STRATEGY_PARAMS
    from engine.regime_helpers import score_regime_capture
    from search.evolve import random_params

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values

    t0 = time.time()
    rs_values = []
    per_family = {}
    families = [
        (fam_name, fam_fn, STRATEGY_PARAMS.get(fam_name, {}))
        for fam_name, fam_fn in STRATEGY_REGISTRY.items()
        if STRATEGY_PARAMS.get(fam_name)
    ]

    # Round-robin over families until the valid-sample target is met, so the
    # null is family-balanced at any size. MAX_ROUNDS bounds runaway sampling
    # when most random configs are degenerate (<3 trades).
    MAX_ROUNDS = 50
    rounds = 0
    while len(rs_values) < min_valid and rounds < MAX_ROUNDS:
        rounds += 1
        for fam_name, fam_fn, space in families:
            fam_rs = per_family.setdefault(fam_name, [])
            for _ in range(samples_per_family):
                params = random_params(space)
                try:
                    entries, exits, labels = fam_fn(ind, params)
                    cooldown = params.get("cooldown", 0)
                    result = backtest(
                        df,
                        entries,
                        exits,
                        labels,
                        cooldown_bars=cooldown,
                        strategy_name=fam_name,
                    )
                    if result.num_trades >= 3:
                        rs = score_regime_capture(result.trades, close, dates)
                        rs_values.append(rs.composite)
                        fam_rs.append(rs.composite)
                except (ValueError, RuntimeError, KeyError, IndexError) as e:
                    # MC samples can fail on degenerate random params; log and
                    # continue so the null isn't silently skewed.
                    print(
                        f"  [MC skip] {fam_name}: {type(e).__name__}: {e}",
                        file=sys.stderr,
                    )
            if len(rs_values) >= min_valid:
                break
        print(
            f"  [MC] round {rounds}: {len(rs_values)} valid samples "
            f"(target {min_valid})",
            file=sys.stderr,
        )

    per_family = {
        fam: {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "n": len(vals),
        }
        for fam, vals in per_family.items()
        if vals
    }

    elapsed = time.time() - t0
    v = np.array(rs_values)
    if len(v) < 100:
        raise RuntimeError(
            f"null calibration produced only {len(v)} valid samples — "
            "cannot fit a trustworthy null distribution"
        )

    # Fit Beta via method of moments — fail loud on an infeasible fit.
    mu, var = float(v.mean()), float(v.var())
    if not (var < mu * (1 - mu) and var > 0):
        raise RuntimeError(
            f"Beta method-of-moments fit infeasible (mu={mu:.4f}, var={var:.6f}) — "
            "refusing to substitute a default null"
        )
    common = mu * (1 - mu) / var - 1
    alpha = mu * common
    beta_param = (1 - mu) * common

    result = {
        "samples_per_family": samples_per_family,
        "min_valid_target": min_valid,
        "rounds": rounds,
        "engine_hash": fingerprint["engine_hash"],
        "data_fingerprint": fingerprint["data_fingerprint"],
        "n_valid": len(rs_values),
        "elapsed_seconds": round(elapsed, 1),
        "rs_mean": round(mu, 4),
        "rs_std": round(float(v.std()), 4),
        "rs_min": round(float(v.min()), 4),
        "rs_max": round(float(v.max()), 4),
        "rs_p95": round(float(np.percentile(v, 95)), 4),
        "rs_p99": round(float(np.percentile(v, 99)), 4),
        "beta_alpha": round(alpha, 2),
        "beta_beta": round(beta_param, 2),
        "per_family": per_family,
    }

    # Cache (atomic write: tmp file + os.replace)
    os.makedirs(os.path.dirname(NULL_CACHE_FILE), exist_ok=True)
    tmp_path = NULL_CACHE_FILE + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(result, f, indent=2)
    os.replace(tmp_path, NULL_CACHE_FILE)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Deflation math
# ─────────────────────────────────────────────────────────────────────────────


def expected_max_beta(alpha: float, beta_param: float, n_eff: int) -> float:
    """
    Approximate maximum of N_eff draws from Beta(alpha, beta) via the
    (1 - 1/n_eff)-quantile (ppf). This is a heuristic proxy for the true
    expectation of the maximum order statistic, not its closed-form value.
    """
    if n_eff <= 1:
        return alpha / (alpha + beta_param)
    p = 1.0 - 1.0 / n_eff
    return float(beta_dist.ppf(p, alpha, beta_param))


def deflated_probability(
    observed: float, alpha: float, beta_param: float, n_eff: int
) -> float:
    """
    P(max of N_eff draws from Beta(alpha,beta) < observed) = CDF(observed)^N_eff

    High value = observed score is unlikely to be noise.
    Low value = indistinguishable from luck.
    """
    observed = np.clip(observed, 0.001, 0.999)
    cdf_val = float(beta_dist.cdf(observed, alpha, beta_param))
    return cdf_val**n_eff


def deflate_regime_score(observed_rs: float, null: dict, n_eff: int) -> dict:
    """Deflate a single observed Regime Score against the null distribution."""
    alpha = null["beta_alpha"]
    beta_param = null["beta_beta"]
    expected_max = expected_max_beta(alpha, beta_param, n_eff)
    dp = deflated_probability(observed_rs, alpha, beta_param, n_eff)

    return {
        "observed_rs": round(observed_rs, 4),
        "deflated_probability": round(dp, 6),
        "expected_max_rs": round(expected_max, 4),
        "beats_noise": observed_rs > expected_max,
        "tier": (
            "strong_signal"
            if dp >= 0.95
            else "modest_signal"
            if dp >= 0.80
            else "fragile"
            if dp >= 0.50
            else "noise"
        ),
        # Also report raw percentile vs null (simpler to interpret)
        "null_percentile": round(
            float(beta_dist.cdf(observed_rs, alpha, beta_param)) * 100, 1
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-eff", type=int, help="Override N_eff estimate")
    parser.add_argument(
        "--samples", type=int, default=40, help="Samples per family for MC null"
    )
    parser.add_argument(
        "--recalibrate", action="store_true", help="Force recalibration"
    )
    args = parser.parse_args()

    print("Calibrating null distribution...")
    null = calibrate_null_distribution(
        samples_per_family=args.samples,
        use_cache=not args.recalibrate,
    )
    n_eff = args.n_eff or estimate_n_eff()

    print(
        f"\nNull distribution ({null['n_valid']} samples, {null['elapsed_seconds']}s):"
    )
    print(
        f"  RS: mean={null['rs_mean']:.4f} std={null['rs_std']:.4f} [{null['rs_min']:.3f}, {null['rs_max']:.3f}]"
    )
    print(f"  Beta fit: Beta({null['beta_alpha']:.1f}, {null['beta_beta']:.1f})")
    print(
        f"  Expected max RS at N_eff={n_eff}: {expected_max_beta(null['beta_alpha'], null['beta_beta'], n_eff):.4f}"
    )

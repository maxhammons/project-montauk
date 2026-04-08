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

def estimate_n_eff_heuristic(n_families: int = 15,
                             effective_per_family: int = 20) -> int:
    """
    Structural heuristic: GA mutations are highly correlated (rho ~0.95).
    Each family explores ~10-30 distinct basins. Conservative lower bound.
    Sprint 4 will add eigenvalue-based estimation.
    """
    return n_families * effective_per_family


# ─────────────────────────────────────────────────────────────────────────────
# Monte Carlo null distribution
# ─────────────────────────────────────────────────────────────────────────────

def calibrate_null_distribution(samples_per_family: int = 40,
                                use_cache: bool = True) -> dict:
    """
    Run random parameter configs across all strategy families, compute
    Regime Scores, and fit a Beta distribution to the results.

    This is the empirical null: "what Regime Score would a random
    trend-following strategy achieve on TECL?"

    Caches results to avoid re-running.
    """
    # Check cache
    if use_cache and os.path.exists(NULL_CACHE_FILE):
        with open(NULL_CACHE_FILE) as f:
            cached = json.load(f)
        if cached.get("samples_per_family", 0) >= samples_per_family:
            return cached

    from data import get_tecl_data
    from strategy_engine import Indicators, backtest
    from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
    from backtest_engine import score_regime_capture
    from evolve import random_params

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values

    t0 = time.time()
    rs_values = []
    per_family = {}

    for fam_name, fam_fn in STRATEGY_REGISTRY.items():
        space = STRATEGY_PARAMS.get(fam_name, {})
        if not space:
            continue
        fam_rs = []
        for _ in range(samples_per_family):
            params = random_params(space)
            try:
                entries, exits, labels = fam_fn(ind, params)
                cooldown = params.get("cooldown", 0)
                result = backtest(df, entries, exits, labels,
                                  cooldown_bars=cooldown, strategy_name=fam_name)
                if result.num_trades >= 3:
                    rs = score_regime_capture(result.trades, close, dates)
                    rs_values.append(rs.composite)
                    fam_rs.append(rs.composite)
            except Exception:
                pass
        if fam_rs:
            per_family[fam_name] = {
                "mean": round(float(np.mean(fam_rs)), 4),
                "std": round(float(np.std(fam_rs)), 4),
                "n": len(fam_rs),
            }

    elapsed = time.time() - t0
    v = np.array(rs_values)

    # Fit Beta via method of moments
    mu, var = float(v.mean()), float(v.var())
    if var < mu * (1 - mu) and var > 0:
        common = mu * (1 - mu) / var - 1
        alpha = mu * common
        beta_param = (1 - mu) * common
    else:
        alpha, beta_param = 10.0, 10.0  # fallback

    result = {
        "samples_per_family": samples_per_family,
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

    # Cache
    os.makedirs(os.path.dirname(NULL_CACHE_FILE), exist_ok=True)
    with open(NULL_CACHE_FILE, "w") as f:
        json.dump(result, f, indent=2)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Deflation math
# ─────────────────────────────────────────────────────────────────────────────

def expected_max_beta(alpha: float, beta_param: float, n_eff: int) -> float:
    """Expected maximum of N_eff draws from Beta(alpha, beta)."""
    if n_eff <= 1:
        return alpha / (alpha + beta_param)
    p = 1.0 - 1.0 / n_eff
    return float(beta_dist.ppf(p, alpha, beta_param))


def deflated_probability(observed: float,
                         alpha: float, beta_param: float,
                         n_eff: int) -> float:
    """
    P(max of N_eff draws from Beta(alpha,beta) < observed) = CDF(observed)^N_eff

    High value = observed score is unlikely to be noise.
    Low value = indistinguishable from luck.
    """
    observed = np.clip(observed, 0.001, 0.999)
    cdf_val = float(beta_dist.cdf(observed, alpha, beta_param))
    return cdf_val ** n_eff


def deflate_regime_score(observed_rs: float, null: dict,
                         n_eff: int) -> dict:
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
            "strong_signal" if dp >= 0.95 else
            "modest_signal" if dp >= 0.80 else
            "fragile" if dp >= 0.50 else
            "noise"
        ),
        # Also report raw percentile vs null (simpler to interpret)
        "null_percentile": round(float(beta_dist.cdf(observed_rs, alpha, beta_param)) * 100, 1),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-eff", type=int, help="Override N_eff estimate")
    parser.add_argument("--samples", type=int, default=40, help="Samples per family for MC null")
    parser.add_argument("--recalibrate", action="store_true", help="Force recalibration")
    args = parser.parse_args()

    print("Calibrating null distribution...")
    null = calibrate_null_distribution(
        samples_per_family=args.samples,
        use_cache=not args.recalibrate,
    )
    n_eff = args.n_eff or estimate_n_eff_heuristic()

    print(f"\nNull distribution ({null['n_valid']} samples, {null['elapsed_seconds']}s):")
    print(f"  RS: mean={null['rs_mean']:.4f} std={null['rs_std']:.4f} [{null['rs_min']:.3f}, {null['rs_max']:.3f}]")
    print(f"  Beta fit: Beta({null['beta_alpha']:.1f}, {null['beta_beta']:.1f})")
    print(f"  Expected max RS at N_eff={n_eff}: {expected_max_beta(null['beta_alpha'], null['beta_beta'], n_eff):.4f}")

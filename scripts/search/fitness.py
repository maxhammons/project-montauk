"""Weighted era-based fitness function (2026-04-21).

Replaces raw full-history `share_multiple` as the optimization target because
that metric was dominated by the synthetic 1993-2008 dotcom-crash sidestep —
producing strategies that scored 20x-126x on full history but lost to B&H on
real post-2008 data.

The new fitness is a weighted geometric mean of era-sliced share multiples:

    fitness = full^0.15 × real^0.25 × modern^0.60

Geometric (not arithmetic) mean because share multiples across eras have
wildly different scales (full can be 50x while real/modern are 0.2x-2x).
Arithmetic weighting gets swamped by the largest-magnitude component. Log-space
math is naturally scale-invariant and punishes any era collapse — any era
factor near zero crushes the product regardless of other era values.

Weights:
  0.15 on full        — catastrophe-survival insurance (1993-2008 synthetic)
  0.25 on real        — actual post-2008-12-17 TECL history
  0.60 on modern      — post-2015 regime (the deployment environment)

Floor of 0.01 per component prevents 0^w = 0 from zeroing fitness when a
strategy took no trades in a short era window.
"""

from __future__ import annotations

# Primary weights (2026-04-21 revision). Tune here, not at call sites.
FITNESS_WEIGHT_FULL = 0.15
FITNESS_WEIGHT_REAL = 0.25
FITNESS_WEIGHT_MODERN = 0.60

# Prevent era-specific 0.0 from wiping the product.
FITNESS_ERA_FLOOR = 0.01


def weighted_era_fitness(
    full_share: float,
    real_share: float,
    modern_share: float,
    *,
    weight_full: float = FITNESS_WEIGHT_FULL,
    weight_real: float = FITNESS_WEIGHT_REAL,
    weight_modern: float = FITNESS_WEIGHT_MODERN,
    era_floor: float = FITNESS_ERA_FLOOR,
) -> float:
    """Weighted geometric mean of era share multipliers.

    full_share^0.15 × real_share^0.25 × modern_share^0.60

    Returns 0.0 only if all inputs are non-positive. Otherwise, floors each
    era at `era_floor` before exponentiation.
    """
    f = max(float(full_share or 0.0), era_floor)
    r = max(float(real_share or 0.0), era_floor)
    m = max(float(modern_share or 0.0), era_floor)
    return f**weight_full * r**weight_real * m**weight_modern


def fitness_from_metrics(metrics: dict) -> float:
    """Convenience: pull the three era values from a metrics dict and compute fitness.

    Expects keys `share_multiple`, `real_share_multiple`, `modern_share_multiple`
    (as populated by engine.strategy_engine.backtest() / run_montauk_821()).
    """
    return weighted_era_fitness(
        full_share=metrics.get("share_multiple", 0.0),
        real_share=metrics.get("real_share_multiple", 0.0),
        modern_share=metrics.get("modern_share_multiple", 0.0),
    )


def fitness_from_result(result) -> float:
    """Convenience: pull era values from a BacktestResult object."""
    return weighted_era_fitness(
        full_share=getattr(result, "share_multiple", 0.0),
        real_share=getattr(result, "real_share_multiple", 0.0),
        modern_share=getattr(result, "modern_share_multiple", 0.0),
    )

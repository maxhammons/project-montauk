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

This module also defines the all-era leaderboard score used to rank already-
certified strategies. Unlike the optimizer fitness, that score is intentionally
balanced across full / real / modern eras because the charter leaderboard is
meant to surface the strongest certified strategy across all 30 years of market
conditions, not just the best modern-era specialist.

For leaderboard and viz surfaces, the canonical era metrics are the standalone
era reruns from `multi_era.eras.*.share_multiple` when that block is present.
Those runs restart capital at each era boundary, which makes cross-era
comparisons easier to reason about than slicing the 30-year run forward.
"""

from __future__ import annotations

# Primary weights (2026-04-21 revision). Tune here, not at call sites.
FITNESS_WEIGHT_FULL = 0.15
FITNESS_WEIGHT_REAL = 0.25
FITNESS_WEIGHT_MODERN = 0.60

LEADERBOARD_WEIGHT_FULL = 1 / 3
LEADERBOARD_WEIGHT_REAL = 1 / 3
LEADERBOARD_WEIGHT_MODERN = 1 / 3

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


def canonical_era_shares(
    metrics: dict | None = None,
    *,
    multi_era: dict | None = None,
) -> tuple[float, float, float]:
    """Return the canonical (full, real, modern) share multiples.

    Prefer standalone era reruns from `multi_era` when available. Fall back to
    the legacy metrics dict so search/validation call sites still work before a
    leaderboard row has been enriched.
    """
    metrics = metrics or {}
    eras = (multi_era or {}).get("eras") or {}

    def _pick(metric_key: str, era_key: str) -> float:
        era_value = (eras.get(era_key) or {}).get("share_multiple")
        if era_value is not None:
            return float(era_value)
        return float(metrics.get(metric_key, 0.0) or 0.0)

    return (
        _pick("share_multiple", "full"),
        _pick("real_share_multiple", "real"),
        _pick("modern_share_multiple", "modern"),
    )


def canonicalize_metrics_with_multi_era(
    metrics: dict | None,
    multi_era: dict | None,
) -> dict:
    """Copy canonical era share multiples into a leaderboard metrics dict."""
    normalized = dict(metrics or {})
    full, real, modern = canonical_era_shares(normalized, multi_era=multi_era)
    normalized["share_multiple"] = full
    normalized["real_share_multiple"] = real
    normalized["modern_share_multiple"] = modern
    return normalized


def fitness_from_metrics(metrics: dict, *, multi_era: dict | None = None) -> float:
    """Convenience: pull the three era values from a metrics dict and compute fitness.

    Expects keys `share_multiple`, `real_share_multiple`, `modern_share_multiple`
    (as populated by engine.strategy_engine.backtest() / run_montauk_821()).
    """
    full_share, real_share, modern_share = canonical_era_shares(
        metrics,
        multi_era=multi_era,
    )
    return weighted_era_fitness(
        full_share=full_share,
        real_share=real_share,
        modern_share=modern_share,
    )


def fitness_from_result(result) -> float:
    """Convenience: pull era values from a BacktestResult object."""
    return weighted_era_fitness(
        full_share=getattr(result, "share_multiple", 0.0),
        real_share=getattr(result, "real_share_multiple", 0.0),
        modern_share=getattr(result, "modern_share_multiple", 0.0),
    )


def all_era_performance_score(
    full_share: float,
    real_share: float,
    modern_share: float,
    *,
    era_floor: float = FITNESS_ERA_FLOOR,
) -> float:
    """Balanced geometric mean used for leaderboard ranking.

    This treats full / real / modern eras equally so the trust surface favors
    certified strategies that performed well across the whole 30-year record.
    """
    return weighted_era_fitness(
        full_share=full_share,
        real_share=real_share,
        modern_share=modern_share,
        weight_full=LEADERBOARD_WEIGHT_FULL,
        weight_real=LEADERBOARD_WEIGHT_REAL,
        weight_modern=LEADERBOARD_WEIGHT_MODERN,
        era_floor=era_floor,
    )


def all_era_score_from_metrics(metrics: dict, *, multi_era: dict | None = None) -> float:
    full_share, real_share, modern_share = canonical_era_shares(
        metrics,
        multi_era=multi_era,
    )
    return all_era_performance_score(
        full_share=full_share,
        real_share=real_share,
        modern_share=modern_share,
    )


def all_era_score_from_result(result) -> float:
    return all_era_performance_score(
        full_share=getattr(result, "share_multiple", 0.0),
        real_share=getattr(result, "real_share_multiple", 0.0),
        modern_share=getattr(result, "modern_share_multiple", 0.0),
    )


def all_era_score_from_entry(entry: dict) -> float:
    return all_era_score_from_metrics(
        entry.get("metrics") or {},
        multi_era=entry.get("multi_era"),
    )

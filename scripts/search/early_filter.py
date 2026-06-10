"""Validation-aligned early-filter + successive-halving decision logic (2026-06-09).

WHY a separate module: these are pure functions (no backtests, no I/O), so the
GA loop in `search/evolve.py` stays imperative while the decision rules stay
unit-testable with fake metrics (`tests/test_evolve_search.py`).

The filter thresholds are NOT defined here — they are imported from
`validation/candidate.py`, so the early filter can never drift from the gates
that later zero the corresponding validation sub-scores. A config that breaches
``EXECUTION_DEGRADATION_FAIL`` (close→next-open share collapse) or
``EVENT_COLLAPSE_FAIL`` (edge evaporates without one event window) would be
discarded by the validation pipeline anyway; catching it at chunk end keeps it
out of the run's winner set before any downstream validation cost is spent.
"""

from __future__ import annotations

import math

from validation.candidate import (
    EVENT_COLLAPSE_FAIL,
    EVENT_COLLAPSE_WARN,
    EXECUTION_DEGRADATION_FAIL,
    EXECUTION_DEGRADATION_WARN,
)

# Penalties applied by evolve.py when a chunk-top config breaches the filter.
# HARD: the stored hash-index fitness is multiplied down so history seeding in
# future runs deprioritizes the config without destroying its raw metrics.
# SOFT: the in-run ranking key (discovery score) is demoted, config survives.
HARD_CACHE_FITNESS_PENALTY = 0.25
SOFT_RANK_MULTIPLIER = 0.85

# Successive-halving knobs (modern-era screen before full-history evaluation).
HALVING_MIN_POP = 16  # below this the screen overhead outweighs savings
HALVING_PROMOTE_FRAC = 0.5  # fraction of cache-miss candidates promoted
HALVING_PROMOTE_MIN = 8  # floor so small batches are never over-pruned
SCREEN_WARMUP_BARS = 800  # indicator warmup prefix before the modern slice

# Marker stamped on hash-index entries for screen-pruned candidates.
PRUNED_MARKER = "pruned_modern_screen"


def filter_decision(degradation_pct: float, worst_collapse: float) -> str:
    """Classify execution-realism + event-dependence metrics.

    Returns ``"hard"`` (would zero validation sub-scores — exclude from the
    run's winner set), ``"soft"`` (would WARN at validation — demote ranking),
    or ``"none"``. Pure so the decision table is testable without backtests.
    """
    if (
        degradation_pct <= EXECUTION_DEGRADATION_FAIL
        or worst_collapse >= EVENT_COLLAPSE_FAIL
    ):
        return "hard"
    if (
        degradation_pct <= EXECUTION_DEGRADATION_WARN
        or worst_collapse >= EVENT_COLLAPSE_WARN
    ):
        return "soft"
    return "none"


def halving_active(halving: bool, pop_size: int) -> bool:
    """Halving is opt-out AND auto-disabled for small populations.

    With pop < HALVING_MIN_POP the screen evaluates nearly everything it would
    have promoted anyway (min-8 floor), so the extra ~2,800-bar backtests are
    pure overhead.
    """
    return bool(halving) and pop_size >= HALVING_MIN_POP


def promote_count(
    n_candidates: int,
    frac: float = HALVING_PROMOTE_FRAC,
    floor: int = HALVING_PROMOTE_MIN,
) -> int:
    """How many screened candidates get the full-history evaluation."""
    if n_candidates <= 0:
        return 0
    return min(n_candidates, max(floor, int(math.ceil(n_candidates * frac))))


def select_promoted(
    screen_scores: list[float],
    frac: float = HALVING_PROMOTE_FRAC,
    floor: int = HALVING_PROMOTE_MIN,
) -> set[int]:
    """Indices of the top-``frac`` (min ``floor``) candidates by screen metric.

    Ties break by original index so the same population always promotes the
    same candidates (determinism requirement for parallel == serial results).
    """
    k = promote_count(len(screen_scores), frac, floor)
    order = sorted(range(len(screen_scores)), key=lambda i: (-screen_scores[i], i))
    return set(order[:k])


def pruned_cache_entry(screen_share: float, n_params: int) -> dict:
    """Hash-index entry for a screen-pruned candidate.

    Pruned candidates must be recorded so they are never retried (dedup hit)
    and so deflation's N_eff counts the trial — but they must never outrank a
    fully evaluated config or be picked as a seeding winner. The shape mirrors
    `evolve._cache_entry_from_result`'s v4 keys so every existing reader keeps
    working:

    * ``bah``/``real_bah``/``modern_bah`` present and > 0 (floored) so
      ``_cache_entry_ready`` is True (never re-evaluated) and
      ``save_hash_index`` persists the entry across runs. The modern screen
      share IS the recorded fitness basis for the trial.
    * ``nt: 0`` guarantees ``fitness_from_cache`` returns 0.0 — pruned entries
      rank below every real config and never seed populations as winners.
    * ``dd: None`` makes ``_objectives_from_cache`` return None — the bayesian
      path prunes such trials instead of treating them as feasible.
    * ``pruned`` marks provenance for humans, tests, and the explicit
      pruned-entry guard in ``fitness_from_cache``.
    """
    basis = max(round(float(screen_share), 4), 0.0001)
    return {
        "bah": basis,
        "real_bah": basis,
        "modern_bah": basis,
        "rs": None,
        "dd": None,
        "nt": 0,
        "np": int(n_params),
        "hhi": None,
        "ma": None,
        "pruned": PRUNED_MARKER,
    }

#!/usr/bin/env python3
"""Montauk Score — the single leaderboard ranking and active-strategy score.

Collapses the previous score zoo (``fitness``, ``composite_confidence``,
``overall_performance_score``, ``future_confidence``, ``trust``,
``overall_confidence``) into ONE headline number on ``[0, 1]`` (shown 0-100),
built from three orthogonal pillars that map directly onto the owner's mental
model::

    Montauk Score = Conviction^0.55 × Performance^0.30 × Durability^0.15

  Conviction  (0.55) — "the strategy has my back": evidence the edge is real and
                       will persist out-of-sample (validation quality, robustness,
                       charter fit, search-deflation, optional calibration). This
                       is the number you hold through a scary drawdown — it is
                       about trust, not last week's price.
  Performance (0.30) — era-weighted share accumulation vs B&H, modern > real >
                       synthetic (full^0.15 × real^0.25 × modern^0.60), squashed
                       to [0,1] so it saturates once you clearly beat B&H.
  Durability  (0.15) — "can I live with it": drawdown resilience, parameter
                       parsimony, portfolio non-redundancy, clean artifacts.

Geometric blend: a single broken pillar (e.g. a 98%-drawdown strategy) drags the
whole score down instead of being masked by a strong pillar.

Design notes
------------
* This module reuses the proven sub-score math from
  ``validation.confidence_v2`` so there is exactly one implementation of each
  building block. Conviction is the confidence_v2 "future confidence" recipe
  with the raw-performance term removed (that is now the Performance pillar);
  Durability is the confidence_v2 "trust" recipe with the future-confidence term
  removed (that is now the Conviction pillar). The pillars are therefore
  orthogonal — no double counting.
* It is computable from data already present on a leaderboard row
  (``validation.sub_scores``, ``metrics``, ``family_size``) with graceful
  defaults, so :func:`compute_montauk_score` can be stamped on every row by the
  certification contract without running the confidence_v2 calibration harness.
* Calibration is optional enrichment. Pass a ``context`` built by
  :func:`build_context` (loads hash-index / diversity / calibration artifacts
  once) for the richer score; omit it for a fast, deterministic light score.
"""

from __future__ import annotations

import math
from typing import Any

from search.fitness import canonical_era_shares, weighted_era_fitness
from validation.confidence_v2 import (
    calibration_lookup,
    clamp,
    deflation_score,
    evidence_floor,
    inverse_interp,
    safe_float,
    search_provenance,
    weighted_geomean,
)

# ── Pillar weights (locked 2026-06-07) ──
W_CONVICTION = 0.55
W_PERFORMANCE = 0.30
W_DURABILITY = 0.15

# Performance squash anchors on weighted-era fitness (full^.15 × real^.25 × modern^.60).
# A Gold row ties B&H (era-weighted) at raw=1.0 → 0.5; it takes a strong all-era
# winner (raw≈6) to saturate at 1.0. Below ~0.6 (clearly losing) → 0.0. The
# saturation is intentional: once you clearly beat B&H, more performance should
# not swing the headline number day-to-day — Conviction does the ranking.
PERF_FAIL, PERF_SOFT, PERF_PASS = 0.60, 1.00, 6.00

# Conviction component weights — the confidence_v2 "future confidence" weights
# with the raw-performance term (``forward_edge``) REMOVED, because raw
# performance is now its own Performance pillar. ``weighted_geomean`` renormalizes
# over the keys that are actually present.
_CONVICTION_WEIGHTS = {
    "validation_quality": 0.22,
    "robustness": 0.18,
    "charter_fit": 0.12,
    "search_deflation": 0.13,
    "live_evidence": 0.05,
}

# Durability component weights — the confidence_v2 "trust" weights with the
# ``future_confidence`` term REMOVED (that lives in the Conviction pillar now).
_DURABILITY_WEIGHTS = {
    "drawdown_resilience": 0.22,
    "parameter_parsimony": 0.12,
    "portfolio_redundancy": 0.13,
    "family_crowding": 0.08,
    "artifact_cleanliness": 0.08,
    "live_degradation": 0.07,
}


def _interp(value: float, fail: float, soft: float, pass_: float) -> float:
    """Smooth [0,1] interpolation: fail→0.0, soft→0.5, pass_→1.0 (higher better)."""
    value = float(value)
    if value >= pass_:
        return 1.0
    if value <= fail:
        return 0.0
    if value < soft:
        return 0.5 * (value - fail) / (soft - fail) if soft > fail else 0.5
    return 0.5 + 0.5 * (value - soft) / (pass_ - soft) if pass_ > soft else 0.5


def _family_crowding(family_size: Any) -> float:
    size = int(safe_float(family_size, 1.0))
    if size <= 1:
        return 1.0
    return clamp(1.0 - min(0.15, math.log(size) / math.log(20.0) * 0.15), 0.85, 1.0)


def performance_pillar(
    metrics: dict[str, Any] | None,
    multi_era: dict[str, Any] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Era-weighted share accumulation, squashed to [0,1].

    Recomputed from the canonical era share multiples (not the stored ``fitness``
    field, which may carry a staleness decay) so it is robust and reproducible.
    """
    full, real, modern = canonical_era_shares(metrics or {}, multi_era=multi_era)
    raw = weighted_era_fitness(full, real, modern)
    score = _interp(raw, PERF_FAIL, PERF_SOFT, PERF_PASS)
    return score, {
        "raw_weighted_era_fitness": round(raw, 4),
        "full_share": round(float(full), 4),
        "real_share": round(float(real), 4),
        "modern_share": round(float(modern), 4),
    }


def durability_pillar(
    entry: dict[str, Any],
    *,
    duplicate_score: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """Deployability: drawdown resilience, parsimony, redundancy, clean artifacts."""
    metrics = entry.get("metrics") or {}
    validation = entry.get("validation") or {}
    max_dd = safe_float(metrics.get("max_dd"), 100.0)
    n_params = safe_float(metrics.get("n_params"), 0.0)
    warnings = len(validation.get("soft_warnings") or []) + len(
        validation.get("critical_warnings") or []
    )
    components = {
        "drawdown_resilience": inverse_interp(max_dd, 55.0, 75.0, 95.0),
        "parameter_parsimony": inverse_interp(n_params, 8.0, 24.0, 80.0),
        "portfolio_redundancy": clamp(
            safe_float(duplicate_score, 1.0) if duplicate_score is not None else 1.0,
            0.75,
            1.0,
        ),
        "family_crowding": _family_crowding(entry.get("family_size")),
        "artifact_cleanliness": clamp(1.0 - min(0.25, 0.025 * warnings), 0.75, 1.0),
    }
    score = weighted_geomean(components, _DURABILITY_WEIGHTS)
    return score, {k: round(float(v), 4) for k, v in components.items()}


def conviction_pillar(
    entry: dict[str, Any],
    *,
    hash_summary: dict[str, Any] | None = None,
    calibration_model: dict[str, Any] | None = None,
) -> tuple[float, str, dict[str, Any]]:
    """Trust that the edge is real and will persist out-of-sample.

    Validation quality + robustness + charter fit + search-deflation, then a
    calibration nudge toward observed forward-survival when a calibrated model is
    supplied. Raw performance is deliberately excluded — that is the Performance
    pillar.
    """
    validation = entry.get("validation") or {}
    metrics = entry.get("metrics") or {}
    sub = validation.get("sub_scores") or {}

    composite = safe_float(validation.get("composite_confidence"))
    validation_quality = clamp(0.70 * composite + 0.30 * evidence_floor(sub))

    drawdown_resilience = inverse_interp(
        safe_float(metrics.get("max_dd"), 100.0), 55.0, 75.0, 95.0
    )
    robustness = weighted_geomean(
        {
            "fragility": sub.get("fragility"),
            "bootstrap": sub.get("bootstrap"),
            "selection_bias": sub.get("selection_bias"),
            "drawdown_resilience": drawdown_resilience,
        },
        {
            "fragility": 0.30,
            "bootstrap": 0.20,
            "selection_bias": 0.25,
            "drawdown_resilience": 0.25,
        },
    )
    charter_fit = weighted_geomean(
        {
            "marker_shape": sub.get("marker_shape"),
            "marker_timing": sub.get("marker_timing"),
            "named_windows": sub.get("named_windows"),
            "era_consistency": sub.get("era_consistency"),
            "trade_sufficiency": sub.get("trade_sufficiency"),
        },
        {
            "marker_shape": 0.15,
            "marker_timing": 0.25,
            "named_windows": 0.20,
            "era_consistency": 0.25,
            "trade_sufficiency": 0.15,
        },
    )
    provenance = search_provenance(
        entry,
        hash_summary=hash_summary or {},
        family_size=int(safe_float(entry.get("family_size"), 1.0)),
    )
    search_deflation = deflation_score(entry, provenance, hash_summary or {})

    components = {
        "validation_quality": validation_quality,
        "robustness": robustness,
        "charter_fit": charter_fit,
        "search_deflation": search_deflation,
    }
    raw = weighted_geomean(components, _CONVICTION_WEIGHTS)
    score, calibration_state = calibration_lookup(calibration_model, raw)
    detail = {k: round(float(v), 4) for k, v in components.items()}
    detail["raw_conviction"] = round(raw, 4)
    return score, calibration_state, detail


def _empty_score() -> dict[str, Any]:
    return {
        "montauk_score": None,
        "montauk_score_100": None,
        "conviction": None,
        "conviction_100": None,
        "performance": None,
        "performance_100": None,
        "durability": None,
        "durability_100": None,
        "calibration_state": "unscored",
        "pillars": {},
        "weights": {
            "conviction": W_CONVICTION,
            "performance": W_PERFORMANCE,
            "durability": W_DURABILITY,
        },
    }


def compute_montauk_score(
    entry: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the Montauk Score and its three pillars for one leaderboard row.

    Returns a dict of ``montauk_score`` (+ ``_100``), the three pillar scores,
    the ``calibration_state``, and a ``pillars`` breakdown for the UI detail
    panel. Falls back to a neutral empty score when the row carries no validation
    or metrics block.
    """
    validation = entry.get("validation")
    metrics = entry.get("metrics")
    if not validation or not metrics:
        return _empty_score()

    ctx = context or {}
    duplicate_score = entry.get("duplicate_score")
    if duplicate_score is None and ctx.get("duplicate_scores"):
        duplicate_score = ctx["duplicate_scores"].get(str(entry.get("display_name") or ""))

    performance, perf_detail = performance_pillar(metrics, entry.get("multi_era"))
    durability, dur_detail = durability_pillar(entry, duplicate_score=duplicate_score)
    conviction, calibration_state, conv_detail = conviction_pillar(
        entry,
        hash_summary=ctx.get("hash_summary"),
        calibration_model=ctx.get("calibration_model"),
    )

    montauk = weighted_geomean(
        {
            "conviction": conviction,
            "performance": performance,
            "durability": durability,
        },
        {
            "conviction": W_CONVICTION,
            "performance": W_PERFORMANCE,
            "durability": W_DURABILITY,
        },
    )

    return {
        "montauk_score": round(montauk, 4),
        "montauk_score_100": round(montauk * 100.0, 2),
        "conviction": round(conviction, 4),
        "conviction_100": round(conviction * 100.0, 2),
        "performance": round(performance, 4),
        "performance_100": round(performance * 100.0, 2),
        "durability": round(durability, 4),
        "durability_100": round(durability * 100.0, 2),
        "calibration_state": calibration_state,
        "pillars": {
            "conviction": conv_detail,
            "performance": perf_detail,
            "durability": dur_detail,
        },
        "weights": {
            "conviction": W_CONVICTION,
            "performance": W_PERFORMANCE,
            "durability": W_DURABILITY,
        },
    }


def montauk_score_value(entry: dict[str, Any]) -> float:
    """Read the stamped Montauk Score off a row, recomputing light if absent.

    Convenience for ranking call sites (leaderboard sort, champion pick, viz).
    """
    value = entry.get("montauk_score")
    if value is None:
        value = compute_montauk_score(entry).get("montauk_score")
    return safe_float(value, 0.0)


def build_context() -> dict[str, Any]:
    """Load the optional enrichment artifacts (calibration / diversity / hashes) once.

    Batch callers (leaderboard finalize, recertification) pass the result to
    :func:`compute_montauk_score` for a calibrated score. Per-row hot paths use
    :func:`default_context` (cached) or omit it for the fast light score.
    """
    from validation.confidence_v2 import (
        CALIBRATION_MODEL_PATH,
        hash_index_summary,
        load_duplicate_scores,
        load_json,
    )

    model = load_json(CALIBRATION_MODEL_PATH, None)
    if not isinstance(model, dict) or model.get("status") != "calibrated":
        model = None
    return {
        "hash_summary": hash_index_summary(),
        "duplicate_scores": load_duplicate_scores(),
        "calibration_model": model,
    }


_DEFAULT_CONTEXT: dict[str, Any] | None = None


def default_context() -> dict[str, Any]:
    """Process-cached enrichment context so every stamp is consistent.

    The certification contract stamps every row through this, so the persisted
    Montauk Score is calibrated and identical no matter which call site produced
    it. Artifacts are loaded once per process; missing artifacts degrade
    gracefully to a deterministic light score.
    """
    global _DEFAULT_CONTEXT
    if _DEFAULT_CONTEXT is None:
        try:
            _DEFAULT_CONTEXT = build_context()
        except Exception:
            _DEFAULT_CONTEXT = {}
    return _DEFAULT_CONTEXT

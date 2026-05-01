"""Confidence v2 scoring for Project Montauk.

This module is intentionally diagnostic-only.  It does not decide Gold Status
or leaderboard admission.  It separates:

* validation composite: the existing validation-stack summary
* edge confidence: probability-like estimate of future usefulness
* capital readiness: deployment/sizing suitability after edge is established
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Any

from certify.contract import sync_entry_contract
from engine.canonical_params import count_tunable_params

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
HASH_INDEX_PATH = os.path.join(PROJECT_ROOT, "spike", "hash-index.json")
DIVERSITY_REPORT_PATH = os.path.join(PROJECT_ROOT, "runs", "gold_diversity_report.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "runs", "confidence_v2")
VINTAGE_TRIALS_PATH = os.path.join(OUTPUT_DIR, "vintage_trials.json")
CALIBRATION_MODEL_PATH = os.path.join(OUTPUT_DIR, "calibration_model.json")
LEADERBOARD_SCORES_PATH = os.path.join(OUTPUT_DIR, "leaderboard_scores.json")
LIVE_HOLDOUT_LOG_PATH = os.path.join(OUTPUT_DIR, "live_holdout_log.json")
CONFIDENCE_TIMESERIES_PATH = os.path.join(OUTPUT_DIR, "confidence_timeseries.json")

LIVE_HOLDOUT_START = "2026-05-01"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def inverse_interp(value: float, pass_: float, soft: float, fail: float) -> float:
    """Score where lower values are better."""
    value = float(value)
    if value <= pass_:
        return 1.0
    if value >= fail:
        return 0.0
    if value <= soft:
        return 1.0 - 0.5 * ((value - pass_) / max(soft - pass_, 1e-9))
    return 0.5 - 0.5 * ((value - soft) / max(fail - soft, 1e-9))


def weighted_geomean(values: dict[str, float | None], weights: dict[str, float]) -> float:
    present = {
        key: clamp(value, 1e-6, 1.0)
        for key, value in values.items()
        if value is not None and key in weights
    }
    if not present:
        return 0.0
    total = sum(weights[key] for key in present)
    score = 1.0
    for key, value in present.items():
        score *= value ** (weights[key] / total)
    return clamp(score)


def percentile(values: list[float], q: float) -> float:
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return 0.0
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * clamp(q)
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return clean[lo] * (1.0 - frac) + clean[hi] * frac


def params_key(params: dict[str, Any]) -> str:
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))


def strategy_key(row: dict[str, Any]) -> str:
    return f"{row.get('strategy') or 'unknown'}::{params_key(row.get('params') or {})}"


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def load_gold_rows(path: str = LEADERBOARD_PATH) -> list[dict[str, Any]]:
    rows = load_json(path, [])
    if not isinstance(rows, list):
        return []
    out = []
    for rank, row in enumerate(rows, start=1):
        synced = sync_entry_contract(dict(row))
        if synced.get("gold_status"):
            synced["leaderboard_rank"] = rank
            out.append(synced)
    return out


def load_duplicate_scores(path: str = DIVERSITY_REPORT_PATH) -> dict[str, float]:
    report = load_json(path, {})
    max_redundancy: dict[str, float] = {}
    for pair in report.get("pairs", []) or []:
        names = [str(pair.get("a_name") or ""), str(pair.get("b_name") or "")]
        values = [
            safe_float(pair.get("risk_on_corr")),
            safe_float(pair.get("entry_overlap")),
            safe_float(pair.get("exit_overlap")),
        ]
        redundancy = sum(values) / max(len(values), 1)
        for name in names:
            if name:
                max_redundancy[name] = max(max_redundancy.get(name, 0.0), redundancy)
    scores = {}
    for name, redundancy in max_redundancy.items():
        penalty = clamp((redundancy - 0.90) / 0.10) * 0.25
        scores[name] = round(clamp(1.0 - penalty, 0.75, 1.0), 4)
    return scores


def hash_index_summary(path: str = HASH_INDEX_PATH) -> dict[str, Any]:
    index = load_json(path, {})
    values = []
    if isinstance(index, dict):
        for item in index.values():
            if isinstance(item, dict) and item.get("rs") is not None:
                values.append(safe_float(item.get("rs")))
    values = [v for v in values if v > 0]
    return {
        "n_configs": len(index) if isinstance(index, dict) else 0,
        "rs_mean": round(sum(values) / len(values), 6) if values else None,
        "rs_p95": round(percentile(values, 0.95), 6) if values else None,
        "rs_p99": round(percentile(values, 0.99), 6) if values else None,
    }


def infer_discovery_mode(row: dict[str, Any]) -> str:
    strategy = str(row.get("strategy") or "")
    params = row.get("params") or {}
    if strategy.startswith("gold_hybrid_") or "members" in params:
        return "hybrid"
    tier = str(row.get("tier") or (row.get("validation") or {}).get("tier") or "").upper()
    if tier == "T0":
        return "preregistered"
    if tier == "T1":
        return "grid"
    if tier == "T2":
        return "ga"
    return "unknown"


def search_provenance(row: dict[str, Any], *, hash_summary: dict[str, Any], family_size: int) -> dict[str, Any]:
    n_params = count_tunable_params(row.get("params") or {})
    mode = infer_discovery_mode(row)
    global_configs = int(hash_summary.get("n_configs") or 0)
    if mode == "preregistered":
        n_eff = max(1, n_params * 2)
    elif mode == "grid":
        n_eff = max(50, min(global_configs or 500, family_size * 80 + n_params * 25))
    elif mode == "hybrid":
        n_eff = max(150, min(global_configs or 1000, family_size * 120 + n_params * 35))
    elif mode == "ga":
        n_eff = max(300, min(global_configs or 2000, family_size * 150 + n_params * 60))
    else:
        n_eff = max(300, min(global_configs or 2000, family_size * 150 + n_params * 80))

    pressure = clamp(math.log10(max(n_eff, 1)) / 5.0)
    return {
        "discovery_mode": mode,
        "n_configs_tested": global_configs,
        "n_effective_configs": int(n_eff),
        "n_params": n_params,
        "family_candidates_tested": family_size,
        "selection_pressure": round(pressure, 4),
        "provenance_quality": "partial",
    }


def evidence_floor(sub_scores: dict[str, Any]) -> float:
    values = [
        safe_float(value)
        for key, value in (sub_scores or {}).items()
        if value is not None and key != "cross_asset"
    ]
    if not values:
        return 0.0
    return clamp(0.65 * percentile(values, 0.20) + 0.35 * min(values))


def era_balance(metrics: dict[str, Any]) -> float:
    full = safe_float(metrics.get("share_multiple"))
    real = safe_float(metrics.get("real_share_multiple"))
    modern = safe_float(metrics.get("modern_share_multiple"))
    if real > 0 and modern > 0:
        floor = 0.70 + 0.30 * clamp((min(real, modern) - 1.0) / 0.50)
        symmetry = clamp(min(real, modern) / max(real, modern))
        full_credit = 0.80 + 0.20 * clamp((full - 1.0) / 10.0)
        return clamp(0.60 * floor + 0.25 * symmetry + 0.15 * full_credit)
    values = [v for v in (full, real, modern) if v > 0]
    return clamp(min(values) / max(values)) if values else 0.0


def deflation_score(row: dict[str, Any], provenance: dict[str, Any], hash_summary: dict[str, Any]) -> float:
    metrics = row.get("metrics") or {}
    observed = safe_float(metrics.get("regime_score"))
    p99 = safe_float(hash_summary.get("rs_p99"), 0.0)
    if observed > 0 and p99 > 0:
        signal_margin = clamp((observed - p99 + 0.20) / 0.35)
    else:
        signal_margin = 0.65
    pressure = safe_float(provenance.get("selection_pressure"), 0.5)
    mode = provenance.get("discovery_mode")
    mode_floor = {
        "preregistered": 0.92,
        "grid": 0.78,
        "hybrid": 0.72,
        "ga": 0.68,
        "unknown": 0.62,
    }.get(mode, 0.62)
    return clamp(mode_floor + 0.22 * signal_margin - 0.10 * pressure, 0.45, 1.0)


def calibration_lookup(model: dict[str, Any] | None, raw_score: float) -> tuple[float, str]:
    if not model or model.get("status") != "calibrated":
        return raw_score, "provisional_uncalibrated"
    buckets = model.get("buckets") or []
    if not buckets:
        return raw_score, "provisional_uncalibrated"
    for bucket in buckets:
        lo = safe_float(bucket.get("min_score"), 0.0)
        hi = safe_float(bucket.get("max_score"), 1.0)
        if lo <= raw_score <= hi:
            observed = clamp(safe_float(bucket.get("observed_survival_rate"), raw_score))
            return clamp(0.65 * raw_score + 0.35 * observed), "calibrated"
    nearest = min(buckets, key=lambda b: abs(safe_float(b.get("midpoint"), raw_score) - raw_score))
    observed = clamp(safe_float(nearest.get("observed_survival_rate"), raw_score))
    return clamp(0.65 * raw_score + 0.35 * observed), "calibrated"


def score_entry(
    row: dict[str, Any],
    *,
    family_size: int,
    duplicate_score: float | None,
    hash_summary: dict[str, Any],
    calibration_model: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = row.get("validation") or {}
    metrics = row.get("metrics") or {}
    sub = validation.get("sub_scores") or {}
    val_conf = safe_float(validation.get("composite_confidence"))
    floor = evidence_floor(sub)
    provenance = search_provenance(row, hash_summary=hash_summary, family_size=family_size)

    drawdown = safe_float(metrics.get("max_dd"), 100.0)
    drawdown_resilience = inverse_interp(drawdown, pass_=55.0, soft=75.0, fail=95.0)
    parsimony = inverse_interp(provenance["n_params"], pass_=8.0, soft=24.0, fail=80.0)
    warnings = len(validation.get("soft_warnings") or []) + len(validation.get("critical_warnings") or [])
    warning_cleanliness = clamp(1.0 - min(0.25, 0.025 * warnings), 0.75, 1.0)
    duplicate = clamp(duplicate_score if duplicate_score is not None else 1.0, 0.75, 1.0)
    crowding = clamp(1.0 if family_size <= 1 else 1.0 - min(0.15, math.log(family_size) / math.log(20.0) * 0.15), 0.85, 1.0)

    validation_quality = clamp(0.70 * val_conf + 0.30 * floor)
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
    forward_edge = era_balance(metrics)
    search_deflation = deflation_score(row, provenance, hash_summary)
    live_score = None
    if live_evidence:
        live_score = live_evidence.get("score")

    raw_components = {
        "validation_quality": validation_quality,
        "forward_edge": forward_edge,
        "robustness": robustness,
        "charter_fit": charter_fit,
        "search_deflation": search_deflation,
        "live_evidence": live_score,
    }
    raw_edge = weighted_geomean(
        raw_components,
        {
            "validation_quality": 0.22,
            "forward_edge": 0.30,
            "robustness": 0.18,
            "charter_fit": 0.12,
            "search_deflation": 0.13,
            "live_evidence": 0.05,
        },
    )
    edge, calibration_state = calibration_lookup(calibration_model, raw_edge)

    capital_components = {
        "edge_confidence": edge,
        "drawdown_resilience": drawdown_resilience,
        "parameter_parsimony": parsimony,
        "portfolio_redundancy": duplicate,
        "family_crowding": crowding,
        "artifact_cleanliness": warning_cleanliness,
        "live_degradation": live_score,
    }
    capital = weighted_geomean(
        capital_components,
        {
            "edge_confidence": 0.30,
            "drawdown_resilience": 0.22,
            "parameter_parsimony": 0.12,
            "portfolio_redundancy": 0.13,
            "family_crowding": 0.08,
            "artifact_cleanliness": 0.08,
            "live_degradation": 0.07,
        },
    )

    return {
        "strategy_key": strategy_key(row),
        "display_name": row.get("display_name") or row.get("strategy"),
        "strategy": row.get("strategy"),
        "leaderboard_rank": row.get("leaderboard_rank"),
        "gold_status": bool(row.get("gold_status")),
        "edge_confidence": round(edge, 4),
        "edge_confidence_100": round(edge * 100.0, 2),
        "capital_readiness": round(capital, 4),
        "capital_readiness_100": round(capital * 100.0, 2),
        "calibration_state": calibration_state,
        "edge_confidence_raw": round(raw_edge, 4),
        "edge_confidence_components": {k: round(float(v), 4) for k, v in raw_components.items() if v is not None},
        "capital_readiness_components": {k: round(float(v), 4) for k, v in capital_components.items() if v is not None},
        "search_provenance": provenance,
    }


def build_leaderboard_scores(
    rows: list[dict[str, Any]] | None = None,
    *,
    calibration_model: dict[str, Any] | None = None,
    diversity_report_path: str = DIVERSITY_REPORT_PATH,
) -> dict[str, Any]:
    rows = rows or load_gold_rows()
    hash_summary = hash_index_summary()
    duplicate_scores = load_duplicate_scores(diversity_report_path)
    family_sizes: dict[str, int] = {}
    for row in rows:
        family = str(row.get("strategy") or "unknown")
        family_sizes[family] = family_sizes.get(family, 0) + 1

    scores = []
    for row in rows:
        family = str(row.get("strategy") or "unknown")
        scores.append(
            score_entry(
                row,
                family_size=family_sizes.get(family, 1),
                duplicate_score=duplicate_scores.get(str(row.get("display_name") or "")),
                hash_summary=hash_summary,
                calibration_model=calibration_model,
            )
        )
    scores.sort(
        key=lambda item: (
            safe_float(item.get("edge_confidence")),
            safe_float(item.get("capital_readiness")),
        ),
        reverse=True,
    )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "live_holdout_start": LIVE_HOLDOUT_START,
        "definition": (
            "Edge Confidence estimates future usefulness; Capital Readiness "
            "estimates deployability. Neither changes Gold Status admission."
        ),
        "hash_index_summary": hash_summary,
        "calibration_status": (calibration_model or {}).get("status", "uncalibrated"),
        "scores": scores,
    }


def write_leaderboard_scores(report: dict[str, Any], path: str = LEADERBOARD_SCORES_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


def append_timeseries(report: dict[str, Any], path: str = CONFIDENCE_TIMESERIES_PATH) -> dict[str, Any]:
    existing = load_json(path, {"series": {}})
    if not isinstance(existing, dict):
        existing = {"series": {}}
    series = existing.setdefault("series", {})
    ts = report.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    for score in report.get("scores", []) or []:
        key = score.get("strategy_key")
        if not key:
            continue
        series.setdefault(key, []).append(
            {
                "generated_at": ts,
                "edge_confidence": score.get("edge_confidence"),
                "capital_readiness": score.get("capital_readiness"),
                "calibration_state": score.get("calibration_state"),
            }
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)
    return existing

#!/usr/bin/env python3
"""Collect historical Confidence v2 candidates from existing Montauk artifacts.

The archive is diagnostic input for the vintage calibration harness.  It does
not certify, promote, or rewrite the authority leaderboard.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from engine.canonical_params import count_tunable_params
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
from validation.confidence_v2 import OUTPUT_DIR, params_key, safe_float, strategy_key

DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "candidate_archive.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _iter_json_paths() -> list[str]:
    patterns = [
        "spike/leaderboard.json",
        "spike/archive/*.json",
        "spike/runs/*/dashboard_data.json",
        "spike/runs/*/results.json",
        "spike/runs/*/raw_results.json",
        "runs/*.json",
    ]
    paths: set[str] = set()
    for pattern in patterns:
        paths.update(glob.glob(os.path.join(PROJECT_ROOT, pattern)))
    skipped = {
        os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "candidate_archive.json"),
        os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "vintage_trials.json"),
        os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "leaderboard_scores.json"),
        os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "confidence_timeseries.json"),
    }
    return sorted(p for p in paths if p not in skipped)


def _source_kind(path: str) -> tuple[str, int]:
    rel = os.path.relpath(path, PROJECT_ROOT)
    if rel == "spike/leaderboard.json":
        return ("current_gold_leaderboard", 100)
    if rel.startswith("spike/archive/"):
        return ("archived_leaderboard", 70)
    if rel.endswith("/dashboard_data.json"):
        return ("certified_run_artifact", 90)
    if rel.endswith("/results.json"):
        return ("spike_validated_results", 80)
    if rel.endswith("/raw_results.json"):
        return ("spike_raw_results", 60)
    if rel.startswith("runs/") and "hybrid" in rel:
        return ("hybrid_diagnostic", 78)
    if rel.startswith("runs/") and "grid" in rel:
        return ("grid_diagnostic", 76)
    if rel.startswith("runs/") and "prefilter" in rel:
        return ("prefilter_diagnostic", 58)
    if rel.startswith("runs/") and "near_miss" in rel:
        return ("near_miss_diagnostic", 62)
    return ("diagnostic_artifact", 50)


def _discovery_mode(source_kind: str, strategy: str, row: dict[str, Any]) -> str:
    if strategy.startswith("gold_hybrid_") or "members" in (row.get("params") or {}):
        return "hybrid"
    if "spike_" in source_kind:
        return "ga"
    if "grid" in source_kind or "prefilter" in source_kind:
        return "grid"
    tier = str(row.get("tier") or STRATEGY_TIERS.get(strategy, "")).upper()
    if tier == "T0":
        return "preregistered"
    if tier == "T1":
        return "grid"
    if tier == "T2":
        return "ga"
    return "unknown"


def _candidate_score(row: dict[str, Any], source_priority: int) -> float:
    metrics = row.get("metrics") or {}
    weighted = safe_float(metrics.get("weighted_era_fitness"), safe_float(row.get("fitness")))
    full = safe_float(metrics.get("share_multiple"))
    real = safe_float(metrics.get("real_share_multiple"))
    modern = safe_float(metrics.get("modern_share_multiple"))
    marker = safe_float(row.get("marker_alignment_score"))
    gold_bonus = 1.0 if row.get("gold_status") or (row.get("validation") or {}).get("gold_status") else 0.0
    era_bonus = sum(1 for value in (full, real, modern) if value >= 1.0) / 3.0
    return (
        source_priority
        + 10.0 * gold_bonus
        + 4.0 * min(max(weighted, 0.0), 5.0)
        + 2.0 * era_bonus
        + marker
    )


def _normalize_candidate(
    row: dict[str, Any],
    *,
    path: str,
    source_kind: str,
    source_priority: int,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    strategy = row.get("strategy")
    params = row.get("params")
    if not isinstance(strategy, str) or strategy not in STRATEGY_REGISTRY:
        return None
    if not isinstance(params, dict):
        return None
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    discovery_mode = _discovery_mode(source_kind, strategy, row)
    total_evals = (
        context.get("total_evaluations")
        or context.get("total_combos")
        or row.get("evaluated_grid_combos")
        or context.get("candidate_count")
        or 0
    )
    rel = os.path.relpath(path, PROJECT_ROOT)
    return {
        "strategy_key": f"{strategy}::{params_key(params)}",
        "display_name": row.get("display_name") or row.get("label") or row.get("name") or strategy,
        "strategy": strategy,
        "params": params,
        "tier": row.get("tier") or STRATEGY_TIERS.get(strategy, "T2"),
        "metrics": metrics,
        "fitness": row.get("fitness") or metrics.get("weighted_era_fitness"),
        "marker_alignment_score": row.get("marker_alignment_score") or metrics.get("marker_alignment"),
        "validation": row.get("validation") if isinstance(row.get("validation"), dict) else {},
        "source_priority": source_priority,
        "archive_score": _candidate_score(row, source_priority),
        "search_provenance": {
            "discovery_mode": discovery_mode,
            "n_configs_tested": int(safe_float(total_evals, 0.0)),
            "n_effective_configs": int(max(safe_float(total_evals, 0.0), 1.0)),
            "n_params": count_tunable_params(params),
            "family_candidates_tested": 1,
            "selection_pressure": 0.0,
            "provenance_quality": "artifact_derived",
        },
        "sources": [
            {
                "path": rel,
                "source_kind": source_kind,
                "rank": row.get("rank") or row.get("candidate_rank") or row.get("leaderboard_rank"),
                "total_evaluations": total_evals,
            }
        ],
    }


def _walk_candidates(
    value: Any,
    *,
    path: str,
    source_kind: str,
    source_priority: int,
    context: dict[str, Any],
):
    if isinstance(value, dict):
        candidate = _normalize_candidate(
            value,
            path=path,
            source_kind=source_kind,
            source_priority=source_priority,
            context=context,
        )
        if candidate:
            yield candidate
        child_context = dict(context)
        for key in ("total_evaluations", "total_combos", "candidate_count"):
            if key in value and value[key] is not None:
                child_context[key] = value[key]
        for child in value.values():
            yield from _walk_candidates(
                child,
                path=path,
                source_kind=source_kind,
                source_priority=source_priority,
                context=child_context,
            )
    elif isinstance(value, list):
        for item in value:
            yield from _walk_candidates(
                item,
                path=path,
                source_kind=source_kind,
                source_priority=source_priority,
                context=context,
            )


def build_archive(paths: list[str] | None = None) -> dict[str, Any]:
    paths = paths or _iter_json_paths()
    by_key: dict[str, dict[str, Any]] = {}
    scanned = 0
    parse_errors = []
    for path in paths:
        scanned += 1
        source_kind, source_priority = _source_kind(path)
        try:
            payload = _load_json(path)
        except Exception as exc:
            parse_errors.append({"path": os.path.relpath(path, PROJECT_ROOT), "error": str(exc)})
            continue
        context = {}
        if isinstance(payload, dict):
            for key in ("total_evaluations", "total_combos", "candidate_count"):
                if key in payload:
                    context[key] = payload[key]
        for candidate in _walk_candidates(
            payload,
            path=path,
            source_kind=source_kind,
            source_priority=source_priority,
            context=context,
        ):
            key = candidate["strategy_key"]
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = candidate
                continue
            existing["archive_score"] = max(existing["archive_score"], candidate["archive_score"])
            existing["source_priority"] = max(existing["source_priority"], candidate["source_priority"])
            existing["sources"].extend(candidate["sources"])
            existing["search_provenance"]["n_configs_tested"] = max(
                int(existing["search_provenance"].get("n_configs_tested") or 0),
                int(candidate["search_provenance"].get("n_configs_tested") or 0),
            )
            existing["search_provenance"]["n_effective_configs"] = max(
                int(existing["search_provenance"].get("n_effective_configs") or 0),
                int(candidate["search_provenance"].get("n_effective_configs") or 0),
            )
            if candidate["source_priority"] > existing.get("source_priority", 0):
                for field in ("display_name", "metrics", "fitness", "marker_alignment_score", "validation", "tier"):
                    existing[field] = candidate.get(field)

    candidates = sorted(
        by_key.values(),
        key=lambda row: (
            safe_float(row.get("archive_score")),
            safe_float((row.get("metrics") or {}).get("real_share_multiple")),
            safe_float((row.get("metrics") or {}).get("modern_share_multiple")),
        ),
        reverse=True,
    )
    family_counts: dict[str, int] = {}
    for row in candidates:
        family_counts[row["strategy"]] = family_counts.get(row["strategy"], 0) + 1
    for row in candidates:
        prov = row["search_provenance"]
        prov["family_candidates_tested"] = family_counts.get(row["strategy"], 1)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "diagnostic_only": True,
        "scanned_files": scanned,
        "candidate_count": len(candidates),
        "family_count": len(family_counts),
        "family_counts": dict(sorted(family_counts.items())),
        "parse_errors": parse_errors,
        "selection_rule": "Unique strategy+params candidates sorted by source quality, Gold/era evidence, weighted fitness, and marker score.",
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    archive = build_archive()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(archive, f, indent=2)
    print(
        f"[candidate-archive] files={archive['scanned_files']} "
        f"candidates={archive['candidate_count']} families={archive['family_count']}"
    )
    print(f"[candidate-archive] wrote {args.output}")


if __name__ == "__main__":
    main()

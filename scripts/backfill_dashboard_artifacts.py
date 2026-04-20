#!/usr/bin/env python3
"""Backfill missing dashboard artifacts for leaderboard entries.

This keeps the visualization build path read-only: `viz/build_viz.py` still
only reads precomputed run artifacts, but this helper can materialize missing
`dashboard_data.json` bundles for the current top-N leaderboard entries.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from share_metric import read_share_multiple
from spike_runner import (
    PROJECT_ROOT,
    _emit_run_artifacts,
    _finalize_champion_certification,
    _refresh_final_artifact_views,
    create_run_dir,
)

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
RUNS_DIR = os.path.join(PROJECT_ROOT, "spike", "runs")


def _params_key(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _index_existing_runs() -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    if not os.path.isdir(RUNS_DIR):
        return index

    for entry in sorted(os.listdir(RUNS_DIR)):
        run_path = os.path.join(RUNS_DIR, entry, "dashboard_data.json")
        if not os.path.exists(run_path):
            continue
        try:
            payload = _load_json(run_path)
        except (OSError, json.JSONDecodeError):
            continue

        strategy = payload.get("strategy")
        params = payload.get("params") or {}
        if not strategy:
            continue
        index[(strategy, _params_key(params))] = run_path
    return index


def _normalize_leaderboard_entry(entry: dict[str, Any], rank: int) -> dict[str, Any]:
    normalized = copy.deepcopy(entry)
    normalized["rank"] = rank

    metrics = dict(normalized.get("metrics") or {})
    share_multiple = read_share_multiple(metrics)
    if share_multiple is not None:
        metrics["share_multiple"] = share_multiple
    normalized["metrics"] = metrics

    validation = dict(normalized.get("validation") or {})
    if "promotion_ready" not in validation:
        validation["promotion_ready"] = bool(
            validation.get("promotion_eligible", normalized.get("promotion_ready", False))
        )
    if "backtest_certified" not in validation:
        checks = validation.get("certification_checks") or {}
        validation["backtest_certified"] = bool(checks) and all(
            bool((check or {}).get("passed")) for check in checks.values()
        )
    if "tier" not in validation and normalized.get("tier"):
        validation["tier"] = normalized["tier"]
    normalized["validation"] = validation
    return normalized


def backfill_leaderboard_dashboard_artifacts(*, top_n: int = 20) -> tuple[int, int]:
    if not os.path.exists(LEADERBOARD_PATH):
        raise FileNotFoundError(f"Missing leaderboard: {LEADERBOARD_PATH}")

    leaderboard = _load_json(LEADERBOARD_PATH)
    if not isinstance(leaderboard, list):
        raise ValueError("leaderboard.json must contain a list")

    existing = _index_existing_runs()
    created = 0
    skipped = 0

    for rank, entry in enumerate(leaderboard[:top_n], start=1):
        strategy = entry.get("strategy")
        params = entry.get("params") or {}
        key = (strategy, _params_key(params))
        if key in existing:
            skipped += 1
            continue

        champion = _normalize_leaderboard_entry(entry, rank)
        run_dir = create_run_dir()
        results = {
            "champion": champion,
            "validation_summary": {
                "source": "leaderboard_artifact_backfill",
                "backfilled": True,
                "rank": rank,
                "strategy": strategy,
            },
        }
        artifacts = _emit_run_artifacts(run_dir, results)
        _finalize_champion_certification(results, artifacts)
        _refresh_final_artifact_views(results, artifacts)
        created += 1
        print(
            f"[backfill] created {os.path.relpath(run_dir, PROJECT_ROOT)} "
            f"for #{rank} {strategy}"
        )

    return created, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing dashboard artifacts for leaderboard entries."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Backfill the top N leaderboard entries (default: 20).",
    )
    args = parser.parse_args()

    created, skipped = backfill_leaderboard_dashboard_artifacts(top_n=args.top)
    print(
        f"[backfill] complete: created {created}, already-present {skipped}, "
        f"targeted {min(args.top, created + skipped)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

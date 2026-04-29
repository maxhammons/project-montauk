#!/usr/bin/env python3
"""Sync leaderboard packaging state from existing run artifacts.

For each leaderboard row, find the newest matching `spike/runs/*/dashboard_data.json`
by `(strategy, params)`. If the full five-file bundle exists, copy the run's
artifact-backed validation state onto the leaderboard row so
`backtest_certified` / `artifact_completeness` stay in sync with what is
already on disk.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from certify.contract import REQUIRED_RUN_ARTIFACTS, is_leaderboard_eligible, sync_entry_contract
from certify.backfill_multi_era_metrics import enrich_entry_with_multi_era
from search.fitness import all_era_score_from_entry, canonicalize_metrics_with_multi_era
from data.loader import get_tecl_data

LEADERBOARD_PATH = PROJECT_ROOT / "spike" / "leaderboard.json"
RUNS_DIR = PROJECT_ROOT / "spike" / "runs"


def _params_key(params: dict) -> str:
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def _index_runs() -> dict[tuple[str, str], Path]:
    index: dict[tuple[str, str], Path] = {}
    if not RUNS_DIR.is_dir():
        return index

    for run_dir in RUNS_DIR.iterdir():
        dashboard_path = run_dir / "dashboard_data.json"
        if not dashboard_path.exists():
            continue
        try:
            payload = _load_json(dashboard_path)
        except Exception:
            continue
        strategy = payload.get("strategy")
        params = payload.get("params") or {}
        if not strategy:
            continue
        key = (strategy, _params_key(params))
        previous = index.get(key)
        if previous is None or dashboard_path.stat().st_mtime > previous.stat().st_mtime:
            index[key] = dashboard_path
    return index


def main() -> int:
    if not LEADERBOARD_PATH.exists():
        print(f"[sync-packaged] missing leaderboard: {LEADERBOARD_PATH}")
        return 1

    rows = _load_json(LEADERBOARD_PATH)
    if not isinstance(rows, list):
        print("[sync-packaged] leaderboard.json is not a list")
        return 1

    index = _index_runs()
    df_full = get_tecl_data()
    synced = 0
    missing = 0

    for row in rows:
        key = (row.get("strategy"), _params_key(row.get("params") or {}))
        dashboard_path = index.get(key)
        if dashboard_path is None:
            missing += 1
            continue
        run_dir = dashboard_path.parent
        artifact_paths = {
            name: str(run_dir / f"{name}.json")
            for name in REQUIRED_RUN_ARTIFACTS
        }
        if not all(Path(path).exists() for path in artifact_paths.values()):
            missing += 1
            continue

        try:
            payload = _load_json(dashboard_path)
        except Exception:
            missing += 1
            continue

        if payload.get("validation"):
            row["validation"] = payload["validation"]
        sync_entry_contract(row, artifact_paths=artifact_paths)
        row["multi_era"] = enrich_entry_with_multi_era(row, df_full)
        row["metrics"] = canonicalize_metrics_with_multi_era(
            row.get("metrics"),
            row.get("multi_era"),
        )
        sync_entry_contract(row, artifact_paths=artifact_paths)
        row["overall_performance_score"] = all_era_score_from_entry(row)
        synced += 1

    kept = []
    dropped = 0
    for row in rows:
        sync_entry_contract(row)
        eligible, _reason = is_leaderboard_eligible(row)
        if eligible:
            kept.append(row)
        else:
            dropped += 1
    rows = kept

    rows.sort(
        key=lambda row: (
            float(row.get("overall_performance_score") or 0.0),
            float(row.get("fitness") or 0.0),
            float((row.get("validation") or {}).get("composite_confidence") or 0.0),
        ),
        reverse=True,
    )

    with open(LEADERBOARD_PATH, "w") as f:
        json.dump(rows, f, indent=2)

    print(f"[sync-packaged] synced={synced} missing_or_incomplete={missing} dropped_not_gold={dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prove maintenance artifact generation can run from leaderboard rows alone."""

from __future__ import annotations

import json
import os
import sys
import tempfile


PROJECT_ROOT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "scripts")

sys.path.insert(0, SCRIPTS_ROOT)

import certify.backfill_artifacts as backfill


def main() -> int:
    workdir = None
    with tempfile.TemporaryDirectory(prefix="argus-poc-maintenance-", dir="/tmp") as td:
        workdir = td
        leaderboard_path = os.path.join(td, "leaderboard.json")
        runs_dir = os.path.join(td, "runs")
        os.makedirs(runs_dir, exist_ok=True)

        entry = {
            "strategy": "gc_vjatr",
            "params": {"cooldown": 2},
            "fitness": 1.0,
            "metrics": {"share_multiple": 1.2},
            "tier": "T2",
            "validation": {
                "verdict": "WARN",
                "promotion_ready": False,
                "backtest_certified": False,
                "composite_confidence": 0.65,
                "certification_checks": {
                    "engine_integrity": {"passed": True},
                    "golden_regression": {"passed": True},
                    "shadow_comparator": {"passed": True},
                    "data_quality_precheck": {"passed": True},
                    "artifact_completeness": {"passed": False, "status": "pending"},
                },
            },
        }
        with open(leaderboard_path, "w", encoding="utf-8") as handle:
            json.dump([entry], handle)

        backfill.LEADERBOARD_PATH = leaderboard_path
        backfill.RUNS_DIR = runs_dir

        def fake_create_run_dir() -> str:
            run_dir = os.path.join(runs_dir, "001")
            os.makedirs(run_dir, exist_ok=True)
            return run_dir

        backfill.create_run_dir = fake_create_run_dir

        created, skipped = backfill.backfill_leaderboard_dashboard_artifacts(top_n=1)

        validation_summary_path = os.path.join(runs_dir, "001", "validation_summary.json")
        dashboard_path = os.path.join(runs_dir, "001", "dashboard_data.json")
        with open(validation_summary_path, encoding="utf-8") as handle:
            validation_summary = json.load(handle)
        with open(dashboard_path, encoding="utf-8") as handle:
            dashboard_data = json.load(handle)

        validation = dashboard_data["validation"]
        print(f"workdir={td}")
        print(f"created={created}")
        print(f"skipped={skipped}")
        print(f"source={validation_summary.get('summary', {}).get('source')}")
        print(f"validation_verdict={validation['verdict']}")
        print(f"validation_promotion_ready={validation['promotion_ready']}")
        print(f"validation_backtest_certified={validation['backtest_certified']}")
        print(f"pipeline_imported={'validation.pipeline' in sys.modules}")

    print(f"cleanup_removed={not os.path.exists(workdir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

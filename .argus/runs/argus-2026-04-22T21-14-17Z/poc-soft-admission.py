#!/usr/bin/env python3
"""Prove leaderboard admission of WARN / non-promotion-ready rows."""

from __future__ import annotations

import os
import sys
import tempfile


PROJECT_ROOT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "scripts")

sys.path.insert(0, SCRIPTS_ROOT)

from search.evolve import _is_leaderboard_eligible, update_leaderboard


def main() -> int:
    entry = {
        "strategy": "gc_precross",
        "fitness": 1.23,
        "params": {"cooldown": 2},
        "metrics": {"share_multiple": 1.1},
        "validation": {
            "verdict": "WARN",
            "composite_confidence": 0.65,
            "promotion_ready": False,
            "backtest_certified": False,
            "certification_checks": {
                "engine_integrity": {"passed": True},
                "golden_regression": {"passed": True},
                "shadow_comparator": {"passed": True},
                "data_quality_precheck": {"passed": True},
                "artifact_completeness": {"passed": False, "status": "pending"},
            },
        },
    }

    workdir = None
    with tempfile.TemporaryDirectory(prefix="argus-poc-soft-admission-", dir="/tmp") as td:
        workdir = td
        lb_path = os.path.join(td, "leaderboard.json")
        eligible, reason = _is_leaderboard_eligible(entry)
        saved = update_leaderboard({"rankings": [entry], "date": "2026-04-22"}, lb_path)
        row = saved[0]["validation"]
        print(f"workdir={td}")
        print(f"eligible={eligible}")
        print(f"reason={reason}")
        print(f"saved_rows={len(saved)}")
        print(f"saved_verdict={row['verdict']}")
        print(f"saved_promotion_ready={row['promotion_ready']}")
        print(f"saved_backtest_certified={row['backtest_certified']}")
        print(f"saved_path={lb_path}")

    print(f"cleanup_removed={not os.path.exists(workdir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

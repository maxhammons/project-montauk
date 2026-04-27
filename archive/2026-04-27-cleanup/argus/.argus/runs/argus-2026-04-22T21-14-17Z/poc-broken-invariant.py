#!/usr/bin/env python3
"""Prove post-hoc finalization can set backtest_certified on a WARN row."""

from __future__ import annotations

import os
import sys
import tempfile


PROJECT_ROOT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"
SCRIPTS_ROOT = os.path.join(PROJECT_ROOT, "scripts")

sys.path.insert(0, SCRIPTS_ROOT)

from search.spike_runner import _finalize_champion_certification


def main() -> int:
    workdir = None
    with tempfile.TemporaryDirectory(prefix="argus-poc-broken-invariant-", dir="/tmp") as td:
        workdir = td
        artifacts = {}
        for name in (
            "trade_ledger",
            "signal_series",
            "equity_curve",
            "validation_summary",
            "dashboard_data",
        ):
            path = os.path.join(td, f"{name}.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
            artifacts[name] = path

        results = {
            "champion": {
                "strategy": "gc_precross",
                "validation": {
                    "verdict": "WARN",
                    "promotion_ready": False,
                    "backtest_certified": False,
                    "certification_checks": {
                        "engine_integrity": {"passed": True},
                        "golden_regression": {"passed": True},
                        "shadow_comparator": {"passed": True},
                        "data_quality_precheck": {"passed": True},
                        "artifact_completeness": {"passed": False, "status": "pending"},
                    },
                    "gates": {
                        "gate7": {
                            "promotion_ready": False,
                            "backtest_certified": False,
                            "clean_pass": False,
                            "advisories": ["artifact completeness pending"],
                        }
                    },
                },
            },
            "validation_summary": {"champion": {}},
        }

        _finalize_champion_certification(results, artifacts)
        validation = results["champion"]["validation"]
        gate7 = validation["gates"]["gate7"]
        artifact_check = validation["certification_checks"]["artifact_completeness"]

        print(f"workdir={td}")
        print(f"verdict={validation['verdict']}")
        print(f"promotion_ready={validation['promotion_ready']}")
        print(f"backtest_certified={validation['backtest_certified']}")
        print(f"gate7_backtest_certified={gate7['backtest_certified']}")
        print(f"artifact_status={artifact_check['status']}")
        print(f"artifact_passed={artifact_check['passed']}")
        print(f"gate7_advisories={gate7['advisories']}")

    print(f"cleanup_removed={not os.path.exists(workdir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Certify a single strategy as end-to-end `backtest_certified`.

Given a strategy + params that already cleared the 7-gate validation pipeline
(verdict=PASS, promotion_ready=True), this step:

  1. Creates a new `spike/runs/NNN/` run directory
  2. Emits the five standardized run artifacts (trade_ledger, signal_series,
     equity_curve, validation_summary, dashboard_data)
  3. Runs `_finalize_champion_certification` so `artifact_completeness` flips
     from `pending` → `pass`
  4. Refreshes the on-disk JSON via `_refresh_final_artifact_views` so the
     persisted validation_summary.json reflects the post-finalize state

The strategy becomes `backtest_certified: True` and `clean_pass: True` iff all
five certification checks pass (engine_integrity, golden_regression,
shadow_comparator, data_quality_precheck, artifact_completeness).

Usage:
    # Certify the current #1 leaderboard entry
    python3 scripts/certify/certify_champion.py

    # Certify a specific strategy + params from a prior validation result
    python3 scripts/certify/certify_champion.py \\
        --result /tmp/run_validation.json \\
        --strategy gc_n8 \\
        --params '{"fast_ema": 120, "slow_ema": 150, ...}'

Invoked automatically by `spike_runner.py` at the end of a full run for the
winning champion. This script is the manual entry point for re-certifying a
specific strategy (e.g., after patching the engine or re-running validation).
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _find_champion(
    validation_result: dict, strategy_filter: str | None, params_filter: dict | None
) -> dict | None:
    """Locate the PASS champion matching optional strategy + params filters."""
    validated = validation_result.get("validation", {}).get("validated_rankings", [])
    if not validated:
        return None
    if strategy_filter is None and params_filter is None:
        return validated[0]
    for e in validated:
        if strategy_filter and e.get("strategy") != strategy_filter:
            continue
        if params_filter:
            ep = e.get("params", {})
            if not all(ep.get(k) == v for k, v in params_filter.items()):
                continue
        return e
    return None


def _load_champion_from_leaderboard(
    strategy_filter: str | None, params_filter: dict | None
) -> dict | None:
    """Fallback: pick the top leaderboard entry (or a match) when no validation
    result file is provided."""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    lb_path = os.path.join(project_root, "spike", "leaderboard.json")
    if not os.path.exists(lb_path):
        return None
    with open(lb_path) as f:
        lb = json.load(f)
    if not lb:
        return None
    if strategy_filter is None and params_filter is None:
        return lb[0]
    for e in lb:
        if strategy_filter and e.get("strategy") != strategy_filter:
            continue
        if params_filter:
            ep = e.get("params", {})
            if not all(ep.get(k) == v for k, v in params_filter.items()):
                continue
        return e
    return None


def main():
    # Ensure scripts/ is on sys.path so `from search.spike_runner import ...` works
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--result",
        type=str,
        default=None,
        help="Path to a JSON validation result (default: read top entry from spike/leaderboard.json)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default=None,
        help="Strategy name to certify (default: champion / top entry)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="JSON dict of params to match (default: match first of --strategy)",
    )
    args = parser.parse_args()

    params_filter = json.loads(args.params) if args.params else None

    champion = None
    if args.result:
        with open(args.result) as f:
            result = json.load(f)
        champion = _find_champion(result, args.strategy, params_filter)
        source = args.result
    if champion is None:
        champion = _load_champion_from_leaderboard(args.strategy, params_filter)
        source = "spike/leaderboard.json"

    if champion is None:
        print("[certify] No matching champion found. Aborting.", file=sys.stderr)
        sys.exit(1)

    print(f"[certify] Source: {source}")
    print(f"[certify] Champion: {champion['strategy']} {champion.get('params', {})}")

    from search.spike_runner import (
        _emit_run_artifacts,
        _finalize_champion_certification,
        _refresh_final_artifact_views,
        create_run_dir,
    )

    results = {
        "champion": champion,
        "validation_summary": {},
        "validated_rankings": [champion],
        "rankings": [champion],
        "raw_rankings": [champion],
    }

    run_dir = create_run_dir()
    print(f"[certify] Run dir: {run_dir}")

    artifacts = _emit_run_artifacts(run_dir, results)
    print("[certify] Artifacts emitted:")
    for name, path in artifacts.items():
        size = os.path.getsize(path) if os.path.exists(path) else "MISSING"
        print(f"           {name}: {size} bytes")

    _finalize_champion_certification(results, artifacts)
    _refresh_final_artifact_views(results, artifacts)
    print("[certify] Finalized + refreshed on-disk artifact views")

    # Re-read and report
    with open(artifacts["validation_summary"]) as f:
        vs = json.load(f)
    cv = vs.get("champion_validation", {})
    print("\n=== CERTIFICATION STATUS ===")
    print(f"  verdict:              {cv.get('verdict')}")
    print(f"  promotion_ready:      {cv.get('promotion_ready')}")
    print(f"  backtest_certified:   {cv.get('backtest_certified')}")
    print(f"  clean_pass:           {cv.get('clean_pass')}")
    print(f"  composite_confidence: {cv.get('composite_confidence')}")
    for k, c in (cv.get("certification_checks") or {}).items():
        print(f"  {k}: passed={c.get('passed')}  status={c.get('status', '?')}")


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.set_start_method("fork", force=True)
    main()

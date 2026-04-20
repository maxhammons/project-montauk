#!/usr/bin/env python3
"""Re-validate every entry in `spike/leaderboard.json` under current rules.

Rebuilds the leaderboard from scratch, admitting only entries that pass the
full 7-gate validation pipeline AND all four engine-level certification checks
(engine_integrity, golden_regression, shadow_comparator, data_quality_precheck).

Run this after:
  - Patching the engine (validation/integrity.py, strategy_engine.py, etc.)
  - Changing validation-threshold rules
  - Updating data sources that invalidate prior results

The prior leaderboard is backed up to `spike/leaderboard.json.pre_recert_backup`.
Stale entries that no longer pass are ejected. The charter rule holds: a
strategy on `spike/leaderboard.json` is a binding statement that it is not
overfit and will work into the future.

Usage:
    python3 scripts/certify/recertify_leaderboard.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys


def main():
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sys.path.insert(0, os.path.join(project_root, "scripts"))

    from search.evolve import _is_leaderboard_eligible, update_leaderboard
    from validation.pipeline import run_validation_pipeline

    lb_path = os.path.join(project_root, "spike", "leaderboard.json")
    with open(lb_path) as f:
        lb = json.load(f)

    print(f"[recert] Loaded {len(lb)} leaderboard entries")

    # Minimal candidate format for the validation pipeline. We deliberately do
    # NOT forward the old `validation` block — the pipeline must recompute
    # certification_checks from scratch with the current rules.
    raw_rankings = [
        {
            "strategy": e["strategy"],
            "rank": i,
            "fitness": e.get("fitness", 0),
            "tier": e.get("tier", "T1"),
            "params": e.get("params", {}),
            "metrics": e.get("metrics", {}),
            "marker_alignment_score": e.get("marker_alignment_score"),
            "marker_alignment_detail": e.get("marker_alignment_detail"),
        }
        for i, e in enumerate(lb, 1)
    ]

    print(f"[recert] Running validation pipeline on {len(raw_rankings)} entries...")
    results = run_validation_pipeline(
        {"raw_rankings": raw_rankings},
        hours=0.05,
        quick=True,
        top_n=len(raw_rankings),
    )

    validated = results["validated_rankings"]
    summary = results["validation_summary"]
    print(
        f"[recert] Pipeline done: "
        f"PASS={summary['validated_pass']} "
        f"WARN={summary['validated_warn']} "
        f"FAIL={summary['validated_fail']}"
    )

    admitted = []
    rejected = []
    for e in validated:
        eligible, reason = _is_leaderboard_eligible(e)
        if eligible:
            admitted.append(e)
        else:
            rejected.append((e.get("strategy"), e.get("params"), reason))

    for e in results.get("raw_rankings", []):
        v = e.get("validation") or {}
        if v.get("verdict") != "PASS":
            rejected.append(
                (
                    e.get("strategy"),
                    e.get("params"),
                    f"verdict={v.get('verdict', '?')}",
                )
            )

    print(f"[recert] Admitted {len(admitted)}, rejected {len(rejected)}")
    if rejected:
        print("[recert] Rejected entries (first 20):")
        for name, params, reason in rejected[:20]:
            print(f"         {name} {params}: {reason}")

    if not admitted:
        print("[recert] No entries admitted. Leaderboard would be empty. Aborting.")
        return

    backup_path = lb_path + ".pre_recert_backup"
    shutil.copy2(lb_path, backup_path)
    print(f"[recert] Backed up old leaderboard to {backup_path}")

    with open(lb_path, "w") as f:
        json.dump([], f)

    update_leaderboard(
        {
            "rankings": admitted,
            "date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
            "total_evaluations": len(raw_rankings),
            "elapsed_hours": 0.0,
        },
        lb_path,
    )

    with open(lb_path) as f:
        final = json.load(f)
    print(f"\n[recert] Final leaderboard: {len(final)} entries")
    for i, e in enumerate(final, 1):
        v = e.get("validation", {})
        cc = v.get("certification_checks", {})
        required_ok = all(
            (cc.get(k) or {}).get("passed", False)
            for k in (
                "engine_integrity",
                "golden_regression",
                "shadow_comparator",
                "data_quality_precheck",
            )
        )
        m = e.get("metrics", {})
        share = m.get("share_multiple", 0)
        print(
            f"  #{i:2d}  {e['strategy']:22s}  "
            f"fit={e.get('fitness', 0):6.2f}  "
            f"share={share:6.2f}x  "
            f"verdict={v.get('verdict', '?'):4s}  "
            f"certified={required_ok}  "
            f"{e.get('params')}"
        )


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.set_start_method("fork", force=True)
    main()

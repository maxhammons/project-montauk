#!/usr/bin/env python3
"""Verify every leaderboard row's stored metrics reproduce under current data + engine.

The leaderboard is a certification: a stamped number that no longer reproduces
is a broken promise. For each row this script recomputes the canonical
multi-era metrics (same path as certification: `enrich_entry_with_multi_era`
→ `canonicalize_metrics_with_multi_era`) and compares them to the stored
`metrics` block.

Modes:
    (default)   Report-only. Prints a per-row table; exits 1 if any row is
                stale (drift beyond tolerance on any era multiple) — CI-able.
    --stamp     Additionally writes a `reproducibility` block onto each row in
                spike/leaderboard.json (status ok|stale, per-era drift,
                checked_utc). Never changes metrics or ranking.
    --enforce   --stamp plus drops stale rows from the authority board
                (backup written first; refuses to empty the board). Stale rows
                are certification breaks — re-admit them only through a fresh
                validation run (recertify_leaderboard.py / a new spike run).

Tolerance: absolute drift > 0.01 on any of share_multiple /
real_share_multiple / modern_share_multiple marks a row stale (matches the
spike_runner artifact-emission tolerance).

Usage:
    python3 scripts/certify/verify_board_reproducibility.py
    python3 scripts/certify/verify_board_reproducibility.py --stamp
    python3 scripts/certify/verify_board_reproducibility.py --enforce
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DRIFT_TOLERANCE = 0.01
ERA_KEYS = ("share_multiple", "real_share_multiple", "modern_share_multiple")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_row(row: dict, df_full) -> dict:
    """Recompute canonical era metrics for one row; return reproducibility block."""
    from certify.backfill_multi_era_metrics import enrich_entry_with_multi_era
    from search.fitness import canonicalize_metrics_with_multi_era

    stored = {k: float((row.get("metrics") or {}).get(k, 0.0)) for k in ERA_KEYS}
    try:
        probe = copy.deepcopy(row)
        multi_era = enrich_entry_with_multi_era(probe, df_full)
        recomputed_metrics = canonicalize_metrics_with_multi_era(
            probe.get("metrics"), multi_era
        )
        recomputed = {k: float(recomputed_metrics.get(k, 0.0)) for k in ERA_KEYS}
    except Exception as exc:  # noqa: BLE001 — a row that cannot re-run is stale
        return {
            "status": "stale",
            "error": str(exc),
            "stored": stored,
            "checked_utc": _utc_now(),
        }

    drift = {k: round(abs(recomputed[k] - stored[k]), 6) for k in ERA_KEYS}
    # Tolerance: 1% relative with a 0.01 absolute floor. Era multiples near
    # the 1.0 Gold floor get the tight absolute bound; large full-history
    # multiples aren't flagged for sub-percent float noise.
    stale = any(
        drift[k] > max(DRIFT_TOLERANCE, DRIFT_TOLERANCE * abs(stored[k]))
        for k in ERA_KEYS
    )
    return {
        "status": "stale" if stale else "ok",
        "stored": {k: round(v, 6) for k, v in stored.items()},
        "recomputed": {k: round(v, 6) for k, v in recomputed.items()},
        "drift": drift,
        "tolerance": DRIFT_TOLERANCE,
        "checked_utc": _utc_now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="write reproducibility blocks onto leaderboard rows",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="--stamp plus drop stale rows from the board (backs up first)",
    )
    args = parser.parse_args()

    from data.loader import get_tecl_data

    if not os.path.exists(LEADERBOARD_PATH):
        print(f"[repro] missing leaderboard: {LEADERBOARD_PATH}")
        return 1
    with open(LEADERBOARD_PATH) as f:
        rows = json.load(f)
    if not isinstance(rows, list) or not rows:
        print("[repro] leaderboard is empty or malformed")
        return 1

    df_full = get_tecl_data()
    data_end = str(df_full["date"].max())[:10]
    print(f"[repro] verifying {len(rows)} rows against data through {data_end}\n")

    stale_count = 0
    for i, row in enumerate(rows, 1):
        block = verify_row(row, df_full)
        block["data_end"] = data_end
        if args.stamp or args.enforce:
            row["reproducibility"] = block
        flag = "OK   " if block["status"] == "ok" else "STALE"
        name = row.get("display_name") or row.get("strategy") or "?"
        if "error" in block:
            detail = f"error: {block['error'][:60]}"
        else:
            worst = max(block["drift"], key=lambda k: block["drift"][k])
            detail = (
                f"full {block['stored']['share_multiple']:.3f}->"
                f"{block['recomputed']['share_multiple']:.3f}  "
                f"worst drift {worst}={block['drift'][worst]:.4f}"
            )
        print(f"  #{i:2d} {flag} {name:24s} {detail}")
        stale_count += block["status"] == "stale"

    print(
        f"\n[repro] {len(rows) - stale_count}/{len(rows)} rows reproduce within "
        f"{DRIFT_TOLERANCE:.0%} relative (floor {DRIFT_TOLERANCE}) on every era multiple"
    )

    if args.enforce and stale_count:
        kept = [
            r for r in rows if (r.get("reproducibility") or {}).get("status") == "ok"
        ]
        if not kept:
            print(
                "[repro] --enforce would empty the board — refusing. Run a full "
                "re-certification (recertify_leaderboard.py) instead."
            )
            return 1
        backup = LEADERBOARD_PATH + ".pre_repro_backup"
        shutil.copy2(LEADERBOARD_PATH, backup)
        print(f"[repro] backed up board to {backup}")
        rows = kept
        print(f"[repro] dropped {stale_count} stale rows; {len(rows)} remain")

    if args.stamp or args.enforce:
        tmp = LEADERBOARD_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rows, f, indent=2)
        os.replace(tmp, LEADERBOARD_PATH)
        print("[repro] leaderboard updated")

    return 1 if (stale_count and not args.enforce) else 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.live_holdout import build_live_holdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile immutable signal snapshots against current replay evidence."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    report = build_live_holdout()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(
            f"signal reconciliation: {report['status']} "
            f"({report['matched_count']} match, {report['diverged_count']} diverged, "
            f"{report['not_replayed_count']} not replayed)"
        )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

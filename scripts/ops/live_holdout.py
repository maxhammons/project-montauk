from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.daily import comparable_signal, compute_current_signal, load_active_champion
from ops.events import append_event, utc_now_iso
from ops.paths import LIVE_HOLDOUT_PATH, SIGNALS_DIR, ensure_ops_dirs


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def load_signal_snapshots(signals_dir: Path = SIGNALS_DIR) -> list[dict[str, Any]]:
    if not signals_dir.exists():
        return []
    snapshots = []
    for path in sorted(signals_dir.glob("*.json")):
        payload = _load_json(path)
        payload["_path"] = str(path)
        snapshots.append(payload)
    return snapshots


def compute_replay_by_date(champion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute current replay signal for the latest available date.

    This is deliberately narrow for the first live-holdout slice. It detects
    whether today's point-in-time snapshot still agrees with the current engine
    and champion. Historical full-date replay can be added once the app has more
    live snapshots.
    """

    replay = compute_current_signal(champion)
    return {str(replay["data_end_date"]): replay}


def build_live_holdout(
    *,
    signals_dir: Path = SIGNALS_DIR,
    output_path: Path = LIVE_HOLDOUT_PATH,
) -> dict[str, Any]:
    ensure_ops_dirs()
    snapshots = load_signal_snapshots(signals_dir)
    champion = load_active_champion()
    replay_by_date = compute_replay_by_date(champion)
    comparisons: list[dict[str, Any]] = []

    for snapshot in snapshots:
        date = str(snapshot.get("data_end_date") or "")
        replay = replay_by_date.get(date)
        if not replay:
            comparisons.append({
                "date": date,
                "status": "not_replayed",
                "snapshot_path": snapshot.get("_path"),
            })
            continue
        snapshot_cmp = comparable_signal(snapshot)
        replay_cmp = comparable_signal(replay)
        matches = snapshot_cmp == replay_cmp
        comparisons.append({
            "date": date,
            "status": "match" if matches else "diverged",
            "snapshot_path": snapshot.get("_path"),
            "snapshot": snapshot_cmp,
            "replay": replay_cmp,
            "changed_fields": [
                key for key in sorted(snapshot_cmp) if snapshot_cmp.get(key) != replay_cmp.get(key)
            ],
        })

    matched = sum(1 for item in comparisons if item.get("status") == "match")
    diverged = sum(1 for item in comparisons if item.get("status") == "diverged")
    not_replayed = sum(1 for item in comparisons if item.get("status") == "not_replayed")
    first = snapshots[0] if snapshots else {}
    latest = snapshots[-1] if snapshots else {}
    start_close = float(first.get("close") or 0.0)
    latest_close = float(latest.get("close") or 0.0)
    close_return_pct = None
    if start_close > 0 and latest_close > 0 and len(snapshots) > 1:
        close_return_pct = round((latest_close / start_close - 1.0) * 100.0, 4)

    report = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "status": "attention" if diverged else "ok",
        "snapshot_count": len(snapshots),
        "live_start_date": first.get("data_end_date"),
        "latest_snapshot_date": latest.get("data_end_date"),
        "matched_count": matched,
        "diverged_count": diverged,
        "not_replayed_count": not_replayed,
        "close_return_since_start_pct": close_return_pct,
        "comparisons": comparisons,
    }
    _write_json(output_path, report)
    if diverged:
        append_event(
            "live_holdout_drift",
            "Live holdout replay diverged from a point-in-time signal snapshot.",
            severity="warning",
            payload={"diverged_count": diverged, "output_path": str(output_path)},
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Montauk live holdout report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = build_live_holdout()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(
            f"live holdout: {report['status']} "
            f"({report['matched_count']} match, {report['diverged_count']} diverged)"
        )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())


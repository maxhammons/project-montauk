from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import read_events
from ops.paths import (
    GOVERNANCE_PATH,
    LATEST_PATH,
    LIVE_HOLDOUT_PATH,
    NOTIFICATIONS_PATH,
    RESEARCH_QUEUE_PATH,
    SCHEDULER_CONFIG_PATH,
    SIGNALS_DIR,
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def latest_signal(signals_dir: Path = SIGNALS_DIR) -> dict[str, Any] | None:
    if not signals_dir.exists():
        return None
    files = sorted(signals_dir.glob("*.json"))
    if not files:
        return None
    return _load_json(files[-1])


def build_status(
    *,
    latest_path: Path = LATEST_PATH,
    signals_dir: Path = SIGNALS_DIR,
    event_limit: int = 20,
) -> dict[str, Any]:
    latest = _load_json(latest_path) if latest_path.exists() else None
    signal = latest_signal(signals_dir)
    events = read_events(limit=event_limit)
    return {
        "has_latest_operation": latest is not None,
        "latest_operation": latest,
        "latest_signal": signal,
        "live_holdout": _load_json(LIVE_HOLDOUT_PATH) if LIVE_HOLDOUT_PATH.exists() else None,
        "governance": _load_json(GOVERNANCE_PATH) if GOVERNANCE_PATH.exists() else None,
        "notifications": _load_json(NOTIFICATIONS_PATH) if NOTIFICATIONS_PATH.exists() else None,
        "scheduler": _load_json(SCHEDULER_CONFIG_PATH) if SCHEDULER_CONFIG_PATH.exists() else None,
        "research_queue": _load_json(RESEARCH_QUEUE_PATH) if RESEARCH_QUEUE_PATH.exists() else None,
        "recent_events": events,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show Montauk operations status.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--events", type=int, default=20, help="Recent events to include.")
    args = parser.parse_args(argv)

    status = build_status(event_limit=args.events)
    if args.json:
        print(json.dumps(status, indent=2, default=str))
        return 0

    latest_signal_payload = status.get("latest_signal") or {}
    latest_operation = status.get("latest_operation") or {}
    risk_state = latest_signal_payload.get("risk_state") or "unknown"
    data_end = latest_signal_payload.get("data_end_date") or "unknown"
    op_status = latest_operation.get("status") or "unknown"
    print(f"Montauk status: {op_status}")
    print(f"Latest signal: {risk_state} through {data_end}")
    governance = status.get("governance") or {}
    if governance:
        print(f"Governance: {governance.get('state')}")
    if latest_signal_payload.get("signal_changed"):
        print("Signal changed since prior snapshot.")
    events = status.get("recent_events") or []
    if events:
        print()
        print("Recent events:")
        for event in events[-5:]:
            print(
                f"- {event.get('timestamp_utc')} "
                f"[{event.get('severity')}] {event.get('message')}"
            )
    return 0 if os.path.exists(LATEST_PATH) or latest_signal_payload else 1


if __name__ == "__main__":
    raise SystemExit(main())

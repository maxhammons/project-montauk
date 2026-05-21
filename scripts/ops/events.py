from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops.paths import EVENTS_PATH


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def append_event(
    event_type: str,
    message: str,
    *,
    severity: str = "info",
    payload: dict[str, Any] | None = None,
    events_path: Path = EVENTS_PATH,
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    """Append one structured operations event to the JSONL event log."""

    events_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_utc": timestamp_utc or utc_now_iso(),
        "severity": severity,
        "event_type": event_type,
        "message": message,
        "payload": payload or {},
    }
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=False, default=str))
        f.write("\n")
    return event


def read_events(
    *,
    events_path: Path = EVENTS_PATH,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if not events_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with events_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if limit is not None and limit >= 0:
        return rows[-limit:]
    return rows


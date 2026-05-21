from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import read_events, utc_now_iso
from ops.paths import EVENTS_PATH, NOTIFICATION_STATE_PATH, NOTIFICATIONS_PATH

NOTIFIABLE_EVENT_TYPES = {
    "signal_changed",
    "data_quality_failed",
    "signal_snapshot_conflict",
    "viz_build_failed",
    "job_failed",
    "champion_blocked",
    "replacement_candidate",
    "live_holdout_drift",
}

NOTIFIABLE_SEVERITIES = {"notice", "warning", "error", "critical"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def event_id(event: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "timestamp_utc": event.get("timestamp_utc"),
            "event_type": event.get("event_type"),
            "message": event.get("message"),
            "payload": event.get("payload") or {},
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def is_notifiable(event: dict[str, Any]) -> bool:
    event_type = event.get("event_type")
    severity = event.get("severity")
    return event_type in NOTIFIABLE_EVENT_TYPES or severity in NOTIFIABLE_SEVERITIES


def notification_from_event(event: dict[str, Any]) -> dict[str, Any]:
    severity = str(event.get("severity") or "info")
    title = {
        "notice": "Montauk Notice",
        "warning": "Montauk Warning",
        "error": "Montauk Error",
        "critical": "Montauk Critical",
    }.get(severity, "Montauk")
    return {
        "id": event_id(event),
        "created_utc": utc_now_iso(),
        "title": title,
        "body": event.get("message") or event.get("event_type") or "Montauk event",
        "severity": severity,
        "event_type": event.get("event_type"),
        "event": event,
        "status": "pending",
    }


def build_outbox(
    events: list[dict[str, Any]],
    *,
    sent_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    sent = sent_ids or set()
    out = []
    seen = set()
    for event in events:
        if not is_notifiable(event):
            continue
        nid = event_id(event)
        if nid in sent or nid in seen:
            continue
        note = notification_from_event(event)
        out.append(note)
        seen.add(nid)
    return out


def scan_notifications(
    *,
    events_path: Path = EVENTS_PATH,
    outbox_path: Path = NOTIFICATIONS_PATH,
    state_path: Path = NOTIFICATION_STATE_PATH,
) -> dict[str, Any]:
    state = _load_json(state_path, {"sent_ids": []})
    sent_ids = set(state.get("sent_ids") or [])
    notifications = build_outbox(read_events(events_path=events_path), sent_ids=sent_ids)
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "pending_count": len(notifications),
        "notifications": notifications,
    }
    _write_json(outbox_path, payload)
    return payload


def mark_sent(
    notification_ids: list[str],
    *,
    state_path: Path = NOTIFICATION_STATE_PATH,
) -> dict[str, Any]:
    state = _load_json(state_path, {"sent_ids": []})
    sent_ids = list(dict.fromkeys(list(state.get("sent_ids") or []) + notification_ids))
    payload = {
        "schema_version": 1,
        "updated_utc": utc_now_iso(),
        "sent_ids": sent_ids,
    }
    _write_json(state_path, payload)
    return payload


def send_macos_notification(notification: dict[str, Any]) -> subprocess.CompletedProcess:
    title = str(notification.get("title") or "Montauk")
    body = str(notification.get("body") or "")
    script = f'display notification {json.dumps(body)} with title {json.dumps(title)}'
    return subprocess.run(
        ["osascript", "-e", script],
        text=True,
        capture_output=True,
        check=False,
    )


def send_pending_notifications(
    *,
    events_path: Path = EVENTS_PATH,
    outbox_path: Path = NOTIFICATIONS_PATH,
    state_path: Path = NOTIFICATION_STATE_PATH,
    sender=send_macos_notification,
) -> dict[str, Any]:
    payload = scan_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
    )
    sent = []
    for note in payload.get("notifications") or []:
        result = sender(note)
        if result.returncode == 0:
            note["status"] = "sent"
            note["sent_utc"] = utc_now_iso()
            sent.append(note["id"])
        else:
            note["status"] = "failed"
            note["send_error"] = (result.stderr or result.stdout or "")[-1000:]
    if sent:
        mark_sent(sent, state_path=state_path)
    payload["sent_count"] = len(sent)
    payload["pending_count"] = len([note for note in payload.get("notifications") or [] if note.get("status") != "sent"])
    _write_json(outbox_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or send Montauk notifications.")
    parser.add_argument("--scan", action="store_true", help="Scan events and write pending notification outbox.")
    parser.add_argument("--send", action="store_true", help="Send pending macOS notifications via osascript.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    payload = scan_notifications()
    if args.send:
        payload = send_pending_notifications()
    if args.json or args.scan or args.send:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"pending notifications: {payload['pending_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

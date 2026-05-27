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
from ops.versioning import version_info

NOTIFIABLE_EVENT_TYPES = {
    "signal_changed",
    "data_stale",
    "data_quality_failed",
    "signal_snapshot_conflict",
    "viz_build_failed",
    "job_failed",
    "champion_changed",
    "champion_blocked",
    "manual_review_required",
    "replacement_candidate",
    "live_holdout_drift",
}

NOTIFIABLE_SEVERITIES = {"notice", "warning", "error", "critical"}


def default_preferences() -> dict[str, Any]:
    return {
        "event_types": {event_type: {"enabled": True} for event_type in sorted(NOTIFIABLE_EVENT_TYPES)},
        "severities": {severity: {"enabled": True} for severity in sorted(NOTIFIABLE_SEVERITIES)},
    }


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


def normalize_state(state: dict[str, Any] | None) -> dict[str, Any]:
    state = dict(state or {})
    preferences = state.get("preferences") or {}
    defaults = default_preferences()
    event_types = preferences.get("event_types") or {}
    severities = preferences.get("severities") or {}
    normalized = {
        "schema_version": 1,
        "updated_utc": state.get("updated_utc") or utc_now_iso(),
        "sent_ids": list(dict.fromkeys(state.get("sent_ids") or [])),
        "preferences": {
            "event_types": {
                key: {"enabled": bool((event_types.get(key) or defaults["event_types"][key]).get("enabled", True))}
                for key in defaults["event_types"]
            },
            "severities": {
                key: {"enabled": bool((severities.get(key) or defaults["severities"][key]).get("enabled", True))}
                for key in defaults["severities"]
            },
        },
    }
    return normalized


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


def preferences_allow_event(event: dict[str, Any], preferences: dict[str, Any] | None) -> bool:
    preferences = preferences or default_preferences()
    event_type = str(event.get("event_type") or "")
    severity = str(event.get("severity") or "")
    event_pref = (preferences.get("event_types") or {}).get(event_type)
    if event_pref is not None:
        return bool(event_pref.get("enabled", True))
    severity_pref = (preferences.get("severities") or {}).get(severity)
    if severity_pref is not None:
        return bool(severity_pref.get("enabled", True))
    return True


def target_for_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event_type")
    payload = event.get("payload") or {}
    targets = {
        "signal_changed": ("current", payload.get("snapshot_path") or payload.get("output_path")),
        "data_stale": ("data", "runs/operations/governance.json"),
        "data_quality_failed": ("data", payload.get("output_path") or "runs/operations/latest.json"),
        "signal_snapshot_conflict": ("events", payload.get("path") or payload.get("snapshot_path")),
        "viz_build_failed": ("viz", "viz/montauk-viz.html"),
        "job_failed": ("jobs", payload.get("record_path")),
        "champion_changed": ("champion", "runs/operations/governance.json"),
        "champion_blocked": ("checkup", "runs/operations/governance.json"),
        "manual_review_required": ("checkup", "runs/operations/governance.json"),
        "replacement_candidate": ("champion", "runs/operations/strategy_review.json"),
        "live_holdout_drift": ("checkup", payload.get("output_path") or "runs/operations/live_holdout.json"),
    }
    view, artifact = targets.get(str(event_type), ("events", None))
    return {
        "view": view,
        "artifact_path": artifact,
        "event_id": event_id(event),
    }


def notification_from_event(event: dict[str, Any]) -> dict[str, Any]:
    severity = str(event.get("severity") or "info")
    title = {
        "notice": "Montauk Notice",
        "warning": "Montauk Warning",
        "error": "Montauk Error",
        "critical": "Montauk Critical",
    }.get(severity, "Montauk")
    target = target_for_event(event)
    return {
        "id": event_id(event),
        "created_utc": utc_now_iso(),
        "title": title,
        "body": event.get("message") or event.get("event_type") or "Montauk event",
        "severity": severity,
        "event_type": event.get("event_type"),
        "target": target,
        "target_view": target["view"],
        "artifact_path": target.get("artifact_path"),
        "event": event,
        "status": "pending",
    }


def build_outbox(
    events: list[dict[str, Any]],
    *,
    sent_ids: set[str] | None = None,
    preferences: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    sent = sent_ids or set()
    out = []
    seen = set()
    for event in events:
        if not is_notifiable(event):
            continue
        if not preferences_allow_event(event, preferences):
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
    state = normalize_state(_load_json(state_path, {"sent_ids": []}))
    _write_json(state_path, state)
    sent_ids = set(state.get("sent_ids") or [])
    preferences = state.get("preferences") or default_preferences()
    notifications = build_outbox(
        read_events(events_path=events_path),
        sent_ids=sent_ids,
        preferences=preferences,
    )
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now_iso(),
        "version_info": version_info(),
        "pending_count": len(notifications),
        "preferences": preferences,
        "notifications": notifications,
    }
    _write_json(outbox_path, payload)
    return payload


def mark_sent(
    notification_ids: list[str],
    *,
    state_path: Path = NOTIFICATION_STATE_PATH,
) -> dict[str, Any]:
    state = normalize_state(_load_json(state_path, {"sent_ids": []}))
    sent_ids = list(dict.fromkeys(list(state.get("sent_ids") or []) + notification_ids))
    payload = {
        "schema_version": 1,
        "updated_utc": utc_now_iso(),
        "sent_ids": sent_ids,
        "preferences": state.get("preferences") or default_preferences(),
    }
    _write_json(state_path, payload)
    return payload


def set_notification_preference(
    event_type: str,
    enabled: bool,
    *,
    state_path: Path = NOTIFICATION_STATE_PATH,
) -> dict[str, Any]:
    state = normalize_state(_load_json(state_path, {"sent_ids": []}))
    preferences = state["preferences"]
    if event_type not in preferences["event_types"]:
        raise ValueError(f"unknown notification event type: {event_type}")
    preferences["event_types"][event_type]["enabled"] = bool(enabled)
    state["updated_utc"] = utc_now_iso()
    state["preferences"] = preferences
    _write_json(state_path, state)
    return state


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
    parser.add_argument("--set-event", help="Persist a notification event-type preference.")
    parser.add_argument("--enabled", choices=["true", "false"], help="Enabled value for --set-event.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    if args.set_event:
        if args.enabled is None:
            parser.error("--set-event requires --enabled true|false")
        payload = set_notification_preference(args.set_event, args.enabled == "true")
    else:
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

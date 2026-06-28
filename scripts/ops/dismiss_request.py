"""Dismissal layer for agent-inbox requests.

WHY: the agent inbox is a *work* queue. Some items are genuinely optional
(e.g. "opt-in launch agents not installed") or have been seen and consciously
declined. Without a way to dismiss them, they sit in the inbox forever and
dilute the signal that the inbox means "act on me." This records per-issue
dismissals so the report can suppress them — until the condition gets *worse*
than when it was dismissed, at which point it resurfaces because it now needs a
fresh decision.

Design:
  - Keyed on ``area`` (the stable issue identity, e.g. ``automation.launch_agents``),
    NOT the request title — titles embed volatile counts ("8 agents…"), so an
    area key means dismissing "launch agents not installed" stays dismissed even
    if the count changes from 8 to 7.
  - Stores the *severity at dismissal*. A request is suppressed only while its
    current severity is no worse than when dismissed; an escalation (advisory →
    warning → critical) re-surfaces it, because the situation materially changed.

Storage: ``runs/operations/dismissed_requests.json``::

    {
      "schema_version": 1,
      "dismissals": {
        "automation.launch_agents": {
          "area": "automation.launch_agents",
          "severity": "advisory",
          "note": "Manual use; daily jobs run when I open the app.",
          "dismissed_utc": "2026-06-17T..."
        }
      }
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import OPERATIONS_DIR, ensure_ops_dirs

DISMISSED_REQUESTS_PATH = OPERATIONS_DIR / "dismissed_requests.json"
INBOX_PATH = OPERATIONS_DIR / "agent_inbox.json"

# Must match agent_report.SEVERITY_RANK.
SEVERITY_RANK = {"critical": 3, "warning": 2, "advisory": 1, "info": 0}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)
        f.write("\n")


def load_dismissals(path: Path = DISMISSED_REQUESTS_PATH) -> dict[str, Any]:
    data = _load_json(path, {})
    if not isinstance(data, dict):
        return {"schema_version": 1, "dismissals": {}}
    data.setdefault("schema_version", 1)
    data.setdefault("dismissals", {})
    return data


def is_dismissed(area: str, severity: str, dismissals: dict[str, Any]) -> bool:
    """True if ``area`` is dismissed and its current severity has not escalated.

    Suppressed while ``current severity <= dismissed severity``. An escalation
    beyond the dismissed level re-surfaces the request for a fresh decision.
    """

    entry = (dismissals.get("dismissals") or {}).get(area)
    if not entry:
        return False
    dismissed_rank = SEVERITY_RANK.get(str(entry.get("severity") or "advisory"), 1)
    current_rank = SEVERITY_RANK.get(str(severity or "info"), 0)
    return current_rank <= dismissed_rank


def dismiss(
    area: str,
    severity: str,
    *,
    note: str | None = None,
    path: Path = DISMISSED_REQUESTS_PATH,
) -> dict[str, Any]:
    """Record a dismissal for ``area`` at ``severity`` (idempotent overwrite)."""

    ensure_ops_dirs()
    data = load_dismissals(path)
    entry = {
        "area": area,
        "severity": severity,
        "dismissed_utc": utc_now_iso(),
    }
    if note is not None:
        entry["note"] = note
    data["dismissals"][area] = entry
    _write_json(path, data)
    return entry


def restore(area: str, *, path: Path = DISMISSED_REQUESTS_PATH) -> bool:
    """Remove a dismissal so the issue can surface again. True if one existed."""

    data = load_dismissals(path)
    if area in data["dismissals"]:
        del data["dismissals"][area]
        _write_json(path, data)
        return True
    return False


def _severity_for_area(area: str) -> str | None:
    """Look up an area's current severity from the latest agent inbox."""

    report = _load_json(INBOX_PATH, {})
    for bucket in ("requests", "optional"):
        for item in report.get(bucket) or []:
            if item.get("area") == area:
                return item.get("severity")
    return None


def _cmd_dismiss(args: argparse.Namespace) -> int:
    severity = args.severity or _severity_for_area(args.area)
    if severity is None:
        print(
            f"Could not find area '{args.area}' in the current inbox; "
            "pass --severity to dismiss it explicitly."
        )
        return 1
    dismiss(args.area, severity, note=args.note)
    print(f"Dismissed '{args.area}' (at severity '{severity}'). "
          "It will resurface only if it escalates above that level.")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    data = load_dismissals()
    book = data.get("dismissals") or {}
    if not book:
        print("No dismissed requests on file.")
        return 0
    for area, entry in book.items():
        line = f"{area}  (severity≤{entry.get('severity')}, {entry.get('dismissed_utc')})"
        if entry.get("note"):
            line += f"\n  note: {entry['note']}"
        print(line)
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    ok = restore(args.area)
    print("Restored." if ok else "No dismissal found for that area.")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dismiss / restore agent-inbox requests by area.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dismiss = sub.add_parser("dismiss", help="Dismiss an issue by area (e.g. automation.launch_agents).")
    p_dismiss.add_argument("area")
    p_dismiss.add_argument("--severity", default=None, help="Override; otherwise read from the current inbox.")
    p_dismiss.add_argument("--note", default=None, help="Why it was dismissed.")
    p_dismiss.set_defaults(func=_cmd_dismiss)

    p_list = sub.add_parser("list", help="List active dismissals.")
    p_list.set_defaults(func=_cmd_list)

    p_restore = sub.add_parser("restore", help="Restore (un-dismiss) an area.")
    p_restore.add_argument("area")
    p_restore.set_defaults(func=_cmd_restore)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

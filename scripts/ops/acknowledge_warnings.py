"""Acknowledgment layer for advisory validation warnings.

WHY: Layer-2 validation warnings (e.g. event-dependence, weak cross-asset
portability, parameter parsimony) are honest, *measured* properties of a
strategy — never bugs to silence. But once a human has reviewed and accepted
those known risks for a specific strategy config, re-surfacing them as fresh
"attention" items every day is noise. This module records per-config
acknowledgments so governance can exclude accepted warnings from the active
count WITHOUT ever deleting them from the validation record.

Design:
  - Keyed on ``params_hash`` (the exact config). If a strategy's params change,
    the hash changes and previously-accepted warnings auto-resurface — which is
    correct: a new config has not been reviewed.
  - Matched on a *digit-normalized signature* so a metric drifting from
    "-12.2%" to "-12.4%" does not un-acknowledge an already-accepted warning;
    the underlying disclosure is the same.

Storage: ``runs/operations/acknowledged_warnings.json``::

    {
      "schema_version": 1,
      "acknowledgements": {
        "<params_hash>": {
          "strategy": "chimera_v1_2026_05_26",
          "acknowledged_utc": "2026-06-17T...",
          "note": "Reviewed; accepted known risks.",
          "warnings": [
            {"signature": "event dependence: ...# ...", "example": "<verbatim>"}
          ]
        }
      }
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import ACKNOWLEDGED_WARNINGS_PATH, LATEST_PATH, ensure_ops_dirs

_DIGITS = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def warning_signature(text: str) -> str:
    """Collapse a warning string to a stable identity.

    Lowercases, replaces every run of digits with ``#`` (so changing metric
    values do not change identity), and normalizes whitespace. Two warnings that
    differ only in their measured numbers share one signature.
    """

    if not text:
        return ""
    normalized = _DIGITS.sub("#", str(text).strip().lower())
    return _WS.sub(" ", normalized).strip()


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


def load_acknowledgements(path: Path = ACKNOWLEDGED_WARNINGS_PATH) -> dict[str, Any]:
    data = _load_json(path, {})
    if not isinstance(data, dict):
        return {"schema_version": 1, "acknowledgements": {}}
    data.setdefault("schema_version", 1)
    data.setdefault("acknowledgements", {})
    return data


def acknowledged_signatures_for(
    acknowledgements: dict[str, Any],
    params_hash: str | None,
) -> set[str]:
    """Return the set of acknowledged warning signatures for one config."""

    if not params_hash:
        return set()
    entry = (acknowledgements.get("acknowledgements") or {}).get(params_hash) or {}
    return {
        w.get("signature")
        for w in (entry.get("warnings") or [])
        if isinstance(w, dict) and w.get("signature")
    }


def partition_warnings(
    warnings: list[str],
    acked_signatures: set[str],
) -> tuple[list[str], list[str]]:
    """Split warnings into (active/unacknowledged, acknowledged), preserving order."""

    active: list[str] = []
    acknowledged: list[str] = []
    for warning in warnings or []:
        if warning_signature(warning) in acked_signatures:
            acknowledged.append(warning)
        else:
            active.append(warning)
    return active, acknowledged


def acknowledge(
    params_hash: str,
    warnings: list[str],
    *,
    strategy: str | None = None,
    note: str | None = None,
    path: Path = ACKNOWLEDGED_WARNINGS_PATH,
) -> dict[str, Any]:
    """Record acknowledgment of ``warnings`` for ``params_hash`` (idempotent).

    Merges with any existing acknowledgments for the config; re-acknowledging a
    warning already on file does not duplicate it.
    """

    ensure_ops_dirs()
    data = load_acknowledgements(path)
    book = data["acknowledgements"]
    entry = book.get(params_hash) or {"warnings": []}
    existing = {w.get("signature"): w for w in entry.get("warnings") or [] if isinstance(w, dict)}
    for warning in warnings or []:
        sig = warning_signature(warning)
        if not sig:
            continue
        existing[sig] = {"signature": sig, "example": warning}
    entry["warnings"] = sorted(existing.values(), key=lambda w: w["signature"])
    if strategy:
        entry["strategy"] = strategy
    if note is not None:
        entry["note"] = note
    entry["acknowledged_utc"] = utc_now_iso()
    book[params_hash] = entry
    _write_json(path, data)
    return entry


def clear(params_hash: str, *, path: Path = ACKNOWLEDGED_WARNINGS_PATH) -> bool:
    """Remove all acknowledgments for a config. Returns True if one was removed."""

    data = load_acknowledgements(path)
    if params_hash in data["acknowledgements"]:
        del data["acknowledgements"][params_hash]
        _write_json(path, data)
        return True
    return False


def _active_signal(latest: dict[str, Any]) -> dict[str, Any]:
    return latest.get("active_signal") or latest.get("latest_signal") or {}


def _cmd_list(args: argparse.Namespace) -> int:
    data = load_acknowledgements()
    book = data.get("acknowledgements") or {}
    if not book:
        print("No acknowledged warnings on file.")
        return 0
    for params_hash, entry in book.items():
        print(f"{entry.get('strategy') or '?'}  [{params_hash[:12]}…]  ({entry.get('acknowledged_utc')})")
        if entry.get("note"):
            print(f"  note: {entry['note']}")
        for w in entry.get("warnings") or []:
            print(f"  - {w.get('example')}")
    return 0


def _cmd_active(args: argparse.Namespace) -> int:
    """Acknowledge the active champion's current warnings (the common case)."""

    latest = _load_json(LATEST_PATH, {})
    signal = _active_signal(latest)
    params_hash = (signal.get("active_champion") or {}).get("params_hash")
    strategy = (signal.get("active_champion") or {}).get("strategy")
    warnings = signal.get("warnings") or []
    if not params_hash:
        print("No active champion params_hash in latest.json; nothing to acknowledge.")
        return 1
    if not warnings:
        print(f"Active champion {strategy} has no warnings to acknowledge.")
        return 0
    entry = acknowledge(params_hash, warnings, strategy=strategy, note=args.note)
    print(f"Acknowledged {len(entry['warnings'])} warning signature(s) for {strategy} [{params_hash[:12]}…].")
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    removed = clear(args.params_hash)
    print("Cleared." if removed else "No acknowledgments found for that params_hash.")
    return 0 if removed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acknowledge accepted validation warnings per strategy config.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_active = sub.add_parser("active", help="Acknowledge all current warnings for the active champion.")
    p_active.add_argument("--note", default=None, help="Reviewer note recorded with the acknowledgment.")
    p_active.set_defaults(func=_cmd_active)

    p_list = sub.add_parser("list", help="List all acknowledgments on file.")
    p_list.set_defaults(func=_cmd_list)

    p_clear = sub.add_parser("clear", help="Remove acknowledgments for a params_hash.")
    p_clear.add_argument("params_hash")
    p_clear.set_defaults(func=_cmd_clear)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

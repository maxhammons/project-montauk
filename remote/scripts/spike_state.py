#!/usr/bin/env python3
"""
State management helper for /spike optimization loop.

Avoids inline `python3 -c` commands (which may not match permission patterns).
All state operations go through this script.

Usage:
  python3 scripts/spike_state.py init                    # Initialize fresh state
  python3 scripts/spike_state.py read                    # Print full state as JSON
  python3 scripts/spike_state.py get phase               # Get a single key
  python3 scripts/spike_state.py set phase 2             # Set a scalar value
  python3 scripts/spike_state.py set-json sweep_winners '{"atr_multiplier": {"best_value": 3.0, "best_mar": 0.51}}'
  python3 scripts/spike_state.py merge '{"phase": 3, "baseline": {"mar": 0.5}}'
  python3 scripts/spike_state.py elapsed                 # Print elapsed hours since start
  python3 scripts/spike_state.py append candidates '{"params": {...}, "mar": 0.6}'
"""

import json
import os
import sys
import tempfile
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(PROJECT_ROOT, "remote", "spike-state.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


def _read_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def _write_state(state: dict):
    """Atomic write: write to temp file then rename (crash-safe)."""
    _ensure_dir()
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(STATE_FILE), suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def cmd_init():
    state = {
        "started": datetime.now().isoformat(),
        "phase": 0,
        "iteration": 0,
        "baseline": {},
        "sweep_winners": {},
        "toggle_results": {},
        "candidates": [],
        "validated": [],
        "best_config": {},
        "report_sections_written": [],
        "errors": [],
    }
    _write_state(state)
    print(json.dumps(state, indent=2))


def cmd_read():
    state = _read_state()
    print(json.dumps(state, indent=2))


def cmd_get(key: str):
    state = _read_state()
    val = state.get(key, None)
    if isinstance(val, (dict, list)):
        print(json.dumps(val, indent=2))
    else:
        print(val)


def cmd_set(key: str, value: str):
    state = _read_state()
    # Auto-detect type
    if value.lower() == "true":
        state[key] = True
    elif value.lower() == "false":
        state[key] = False
    else:
        try:
            state[key] = int(value)
        except ValueError:
            try:
                state[key] = float(value)
            except ValueError:
                state[key] = value
    _write_state(state)
    print(f"Set {key} = {state[key]}")


def cmd_set_json(key: str, json_str: str):
    state = _read_state()
    val = json.loads(json_str)
    if key in state and isinstance(state[key], dict) and isinstance(val, dict):
        state[key].update(val)
    else:
        state[key] = val
    _write_state(state)
    print(f"Updated {key}")


def cmd_merge(json_str: str):
    state = _read_state()
    updates = json.loads(json_str)
    for k, v in updates.items():
        if k in state and isinstance(state[k], dict) and isinstance(v, dict):
            state[k].update(v)
        else:
            state[k] = v
    _write_state(state)
    print("State merged")


def cmd_append(key: str, json_str: str):
    state = _read_state()
    val = json.loads(json_str)
    if key not in state:
        state[key] = []
    state[key].append(val)
    _write_state(state)
    print(f"Appended to {key} (now {len(state[key])} items)")


def cmd_elapsed():
    state = _read_state()
    started = datetime.fromisoformat(state.get("started", datetime.now().isoformat()))
    hours = (datetime.now() - started).total_seconds() / 3600
    print(f"{hours:.2f}")


def main():
    if len(sys.argv) < 2:
        print("Usage: spike_state.py <command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()
    elif cmd == "read":
        cmd_read()
    elif cmd == "get":
        cmd_get(sys.argv[2])
    elif cmd == "set":
        cmd_set(sys.argv[2], sys.argv[3])
    elif cmd == "set-json":
        cmd_set_json(sys.argv[2], sys.argv[3])
    elif cmd == "merge":
        cmd_merge(sys.argv[2])
    elif cmd == "append":
        cmd_append(sys.argv[2], sys.argv[3])
    elif cmd == "elapsed":
        cmd_elapsed()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Hash-chained signal-snapshot ledger (Phase 3.1, 2026-06-09).

signals/*.json are immutable daily snapshots. The immutability contract in
ops/daily.py::write_signal_snapshot refuses to overwrite, but nothing stopped
a snapshot file from being edited *after* the fact. This module closes that
gap with `signals/chain.jsonl` — an append-only hash chain over the snapshot
files, so any retroactive edit (or deletion) of a ledgered snapshot is
detectable from the ledger alone.

Ledger format: one JSON line per snapshot date, in date order:

    {"date", "file", "sha256", "prev_sha256", "appended_utc"}

`sha256` is over the snapshot file's raw bytes; `prev_sha256` is the previous
ledger line's sha256 (null for the first line), which is what makes the
ledger a chain — a line can't be silently rewritten without breaking every
line after it.

Backfill note: the 19 snapshots that predate this module (2026-05-08 →
2026-06-09) are covered by the ledger only — their JSON payloads do not carry
the embedded `prev_snapshot_sha256` field. Snapshots written from 2026-06-09
onward by write_signal_snapshot embed `prev_snapshot_sha256` (sha256 of the
previous date's snapshot file) in the payload itself, giving two independent
tamper surfaces: the file-internal back-pointer and this ledger.

Deliberately NOT wired into governance.py — `chain_health()` is the small
pure entry point other systems (governance, doctor) can call later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ops.events import utc_now_iso
from ops.paths import SIGNALS_DIR

CHAIN_PATH = SIGNALS_DIR / "chain.jsonl"

# Only date-stamped snapshots are ledgered — the chain file itself and any
# stray artifacts in signals/ must never enter the chain.
_SNAPSHOT_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def file_sha256(path: Path) -> str:
    """sha256 of a file's raw bytes (the ledger hashes bytes, not parsed JSON,
    so even formatting-only edits break the chain — that is the point)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_files(signals_dir: Path) -> list[Path]:
    if not signals_dir.exists():
        return []
    return sorted(
        p for p in signals_dir.iterdir() if _SNAPSHOT_NAME_RE.match(p.name)
    )


def _read_chain(chain_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse the ledger. Returns (entries, breaks) — unparseable lines are
    breaks, not exceptions, so a corrupted ledger is reported, never masked."""
    entries: list[dict[str, Any]] = []
    breaks: list[dict[str, Any]] = []
    if not chain_path.exists():
        return entries, breaks
    with chain_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                breaks.append({
                    "kind": "unparseable_line",
                    "line": lineno,
                    "detail": str(e),
                })
                continue
            entries.append(entry)
    return entries, breaks


def _verify_entries(
    entries: list[dict[str, Any]],
    signals_dir: Path,
) -> list[dict[str, Any]]:
    """Recompute every ledgered file hash + check line-to-line linkage."""
    breaks: list[dict[str, Any]] = []
    prev_sha: str | None = None
    prev_date: str | None = None
    seen_dates: set[str] = set()
    for i, entry in enumerate(entries):
        date = entry.get("date")
        fname = entry.get("file")
        if date in seen_dates:
            breaks.append({"kind": "duplicate_date", "date": date, "index": i})
        seen_dates.add(date)
        if prev_date is not None and str(date) <= prev_date:
            breaks.append({
                "kind": "date_order",
                "date": date,
                "index": i,
                "detail": f"date {date} not after previous ledgered date {prev_date}",
            })
        if entry.get("prev_sha256") != prev_sha:
            breaks.append({
                "kind": "linkage",
                "date": date,
                "index": i,
                "detail": "prev_sha256 does not match previous line's sha256",
            })
        path = signals_dir / str(fname)
        if not path.exists():
            breaks.append({
                "kind": "missing_file",
                "date": date,
                "file": fname,
                "detail": "ledgered snapshot no longer on disk",
            })
        else:
            actual = file_sha256(path)
            if actual != entry.get("sha256"):
                breaks.append({
                    "kind": "hash_mismatch",
                    "date": date,
                    "file": fname,
                    "detail": (
                        f"file edited after ledgering: ledger {str(entry.get('sha256'))[:12]}…, "
                        f"disk {actual[:12]}…"
                    ),
                })
        prev_sha = entry.get("sha256")
        prev_date = str(date)
    return breaks


def verify_chain(
    signals_dir: Path = SIGNALS_DIR,
    chain_path: Path = CHAIN_PATH,
) -> dict[str, Any]:
    """Recompute every file hash + linkage. {"ok", "entries", "breaks"} plus
    "unledgered" (snapshots on disk the chain hasn't covered yet — build_chain
    work, not a tamper signal)."""
    entries, breaks = _read_chain(chain_path)
    breaks = breaks + _verify_entries(entries, signals_dir)
    ledgered = {str(e.get("date")) for e in entries}
    unledgered = [
        p.stem for p in _snapshot_files(signals_dir) if p.stem not in ledgered
    ]
    return {
        "ok": not breaks,
        "entries": len(entries),
        "breaks": breaks,
        "unledgered": unledgered,
    }


def build_chain(
    signals_dir: Path = SIGNALS_DIR,
    chain_path: Path = CHAIN_PATH,
) -> dict[str, Any]:
    """Idempotently extend the ledger with any not-yet-ledgered snapshots.

    Existing lines are re-verified first (recomputed file hash + linkage) and
    the ledger is NEVER extended on top of a broken chain — appending past a
    break would launder the tamper into a "valid" tail. New dates must sort
    after the last ledgered date: an out-of-order backfill is reported as a
    break instead of silently violating the date-ordered ledger contract.
    """
    entries, breaks = _read_chain(chain_path)
    breaks = breaks + _verify_entries(entries, signals_dir)
    if breaks:
        return {"ok": False, "entries": len(entries), "appended": 0, "breaks": breaks}

    ledgered = {str(e.get("date")) for e in entries}
    last_date = str(entries[-1]["date"]) if entries else None
    prev_sha = str(entries[-1]["sha256"]) if entries else None

    appended = 0
    for path in _snapshot_files(signals_dir):
        date = path.stem
        if date in ledgered:
            continue
        if last_date is not None and date <= last_date:
            breaks.append({
                "kind": "out_of_order_backfill",
                "date": date,
                "file": path.name,
                "detail": (
                    f"snapshot {date} appeared after {last_date} was ledgered; "
                    "append-only ledger cannot insert it in date order"
                ),
            })
            continue
        sha = file_sha256(path)
        entry = {
            "date": date,
            "file": path.name,
            "sha256": sha,
            "prev_sha256": prev_sha,
            "appended_utc": utc_now_iso(),
        }
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        with chain_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=False))
            f.write("\n")
        prev_sha = sha
        last_date = date
        appended += 1

    return {
        "ok": not breaks,
        "entries": len(entries) + appended,
        "appended": appended,
        "breaks": breaks,
    }


def chain_health(
    signals_dir: Path = SIGNALS_DIR,
    chain_path: Path = CHAIN_PATH,
) -> dict[str, Any]:
    """Pure read-only health probe for other systems (governance, doctor) to
    consume later — verifies, never mutates the ledger."""
    return verify_chain(signals_dir=signals_dir, chain_path=chain_path)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help="Verify only (read-only). Default: build (append new dates) then verify.",
    )
    args = ap.parse_args(argv)

    if not args.verify:
        built = build_chain()
        print(f"build: appended={built['appended']} entries={built['entries']}")
        if not built["ok"]:
            for b in built["breaks"]:
                print(f"  BREAK [{b.get('kind')}] {b.get('date', '?')}: {b.get('detail', '')}")
            return 1

    result = verify_chain()
    print(
        f"verify: ok={result['ok']} entries={result['entries']} "
        f"breaks={len(result['breaks'])} unledgered={len(result['unledgered'])}"
    )
    for b in result["breaks"]:
        print(f"  BREAK [{b.get('kind')}] {b.get('date', '?')}: {b.get('detail', '')}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

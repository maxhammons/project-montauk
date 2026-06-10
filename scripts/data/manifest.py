#!/usr/bin/env python3
"""
data/manifest.json builder (Phase 3c).

Captures per-CSV provenance metadata + SHA-256 checksums + build timestamps
so silent tampering or staleness can be detected by data_quality.py.

The manifest is the source of truth for "what each CSV claims to be."
Regenerate after any data refresh or rebuild.

2026-06-09 (Phase 3.4): every build also appends per-CSV historical-bar
checksums to the append-only data/manifest-history.jsonl ledger, and
verify_bar_immutability() proves rows that existed at an earlier build were
never retroactively changed (deep-val D8.1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(SCRIPT_DIR)
)  # scripts/data/ -> scripts/ -> project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")
# Append-only per-build ledger of historical-bar checksums (Phase 3.4,
# 2026-06-09). manifest.json only knows the CURRENT file hash, so a refresh
# that retroactively rewrites old bars looks identical to a legitimate append.
# The history ledger pins the hash of "all rows up to the build-time cutoff"
# so later builds can prove those rows never changed.
HISTORY_PATH = os.path.join(DATA_DIR, "manifest-history.jsonl")

# Per-CSV declared provenance. Build script attaches sha256 + rows + built_utc.
CSV_SPECS = {
    "TECL.csv": {
        "source_real": "Yahoo Finance (TECL)",
        "source_synthetic": "3x ^SP500-45 (1993-1998) + 3x XLK (1998-2008), 0.95%/yr expense, daily compounded; loader applies a 189.7 bps/yr synthetic financing/tracking drag haircut by default",
        "seam_date": "2008-12-17",
        "expense_ratio_source": "Direxion TECL published expense cap/current fact sheet",
        "synthetic_model_version": "v2-3xTechIdx-0.95%ER-daily",
    },
    "TQQQ.csv": {
        "source_real": "Yahoo Finance (TQQQ)",
        "source_synthetic": "3x QQQ, 0.75%/yr expense, daily compounded",
        "seam_date": "2010-02-11",
        "expense_ratio_source": "ProShares prospectus (TQQQ: 0.75%/yr)",
        "synthetic_model_version": "v1-3xQQQ-0.75%ER-daily",
    },
    "XLK.csv": {
        "source_real": "Yahoo Finance (XLK)",
        "seam_date": "1998-12-22",
        "notes": "Underlying ETF for TECL synthetic period (1998-12-22 onward).",
    },
    "QQQ.csv": {
        "source_real": "Yahoo Finance (QQQ; pre-1999 backfilled by Yahoo)",
        "seam_date": "1999-03-10",
        "notes": "Underlying ETF for TQQQ synthetic period (full pre-2010 coverage).",
    },
    "SP500-45.csv": {
        "source_real": "Yahoo Finance (^SP500-45 — S&P 500 Information Technology Sector index)",
        "seam_date": "1993-05-04",
        "notes": "Underlying index for TECL synthetic before XLK existed (1993-05-04 → 1998-12-21). "
        "Price-only index; OHLC degenerates to close.",
    },
    "VIX.csv": {
        "source_real": "Cboe official VIX history",
        "seam_date": "1990-01-02",
        "notes": "CBOE Volatility Index. Merged into TECL.csv as vix_close column.",
    },
    "TECL_distributions.csv": {
        "source_real": "Direxion TECL distribution table plus historical dividend archive for older rows",
        "seam_date": "2021-12-09",
        "notes": "Per-share TECL cash distributions keyed by ex-date. Merged at load time and credited as cash only while the strategy is holding TECL.",
    },
    "SGOV.csv": {
        "source_real": "Yahoo Finance (SGOV)",
        "seam_date": "2020-05-26",
        "notes": "iShares 0-3 Month Treasury Bond ETF. Used by Roth overlay strategies.",
    },
    "treasury-spread-10y2y.csv": {
        "source_real": "FRED (T10Y2Y — 10Y minus 2Y Treasury constant maturity)",
        "seam_date": "1976-06-01",
        "notes": "Recession indicator. Forward-filled into trading calendar.",
    },
    "fed-funds-rate.csv": {
        "source_real": "FRED (DFF — Effective Federal Funds Rate)",
        "seam_date": "1954-07-01",
        "notes": "Monetary policy regime. Forward-filled into trading calendar.",
    },
    "tbill-3m.csv": {
        "source_real": "FRED (DTB3 — 3-Month Treasury Bill: Secondary Market Rate)",
        "seam_date": "1954-01-04",
        "notes": "Risk-free rate proxy.",
    },
}


# ─────────────────────────────────────────────────────────────────────
# Build / verify
# ─────────────────────────────────────────────────────────────────────


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_rows(path: str) -> int | None:
    try:
        df = pd.read_csv(path)
        return int(len(df))
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None


def build_manifest() -> dict:
    """Build manifest dict from current CSVs on disk."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: dict = {"_meta": {"built_utc": now, "schema_version": 1}, "files": {}}
    for fname, spec in CSV_SPECS.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            entry = dict(spec)
            entry["status"] = "MISSING"
            out["files"][fname] = entry
            continue
        entry = dict(spec)
        entry["rows"] = _file_rows(path)
        entry["sha256"] = _file_sha256(path)
        entry["bytes"] = os.path.getsize(path)
        entry["built_utc"] = now
        out["files"][fname] = entry
    return out


def write_manifest(path: str = MANIFEST_PATH) -> dict:
    m = build_manifest()
    with open(path, "w") as f:
        json.dump(m, f, indent=2, sort_keys=False)
        f.write("\n")
    # 2026-06-09 (Phase 3.4): every manifest build also ledgers the
    # historical-bar checksum per CSV so retroactive bar edits are detectable
    # across refreshes (see verify_bar_immutability).
    append_history()
    return m


# ─────────────────────────────────────────────────────────────────────
# Historical-bar immutability ledger (Phase 3.4, 2026-06-09)
# ─────────────────────────────────────────────────────────────────────


def _canonical_history(path: str, cutoff_date: str | None = None) -> dict:
    """Hash the file's historical rows up to a cutoff date.

    Canonical recipe (frozen 2026-06-09 — changing it orphans every existing
    ledger entry, so version it instead of editing it):
      1. Read the CSV as UTF-8 text and split into lines.
      2. The first non-empty line is the header. The date column is the field
         named "date" (case-insensitive, stripped); if absent, field 0 — that
         covers TECL_distributions.csv, whose date key is `ex_date`.
      3. Keep every data line whose date field is <= cutoff_date. Dates are
         ISO YYYY-MM-DD throughout data/, so plain string comparison is
         chronological. cutoff_date=None means "use the max date present"
         (the build-time snapshot of everything currently on disk).
      4. Strip each kept line, join with "\\n", encode UTF-8, sha256.

    Hashing raw row text (not parsed values) means ANY retroactive change is
    flagged — a repriced bar, a re-rounded float, or a schema migration that
    rewrites historical lines. All of those must be deliberate, audited events.
    """
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if not lines:
        return {
            "cutoff_date": None,
            "rows_to_cutoff": 0,
            "history_sha256": None,
            "max_date": None,
        }
    header = [c.strip().lower() for c in lines[0].split(",")]
    date_idx = header.index("date") if "date" in header else 0

    dated_rows: list[tuple[str, str]] = []
    for ln in lines[1:]:
        fields = ln.split(",")
        if date_idx >= len(fields):
            continue
        dated_rows.append((fields[date_idx].strip(), ln.strip()))
    if not dated_rows:
        return {
            "cutoff_date": cutoff_date,
            "rows_to_cutoff": 0,
            "history_sha256": None,
            "max_date": None,
        }

    max_date = max(d for d, _ in dated_rows)
    cutoff = cutoff_date if cutoff_date is not None else max_date
    kept = [row for d, row in dated_rows if d <= cutoff]
    digest = hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()
    return {
        "cutoff_date": cutoff,
        "rows_to_cutoff": len(kept),
        "history_sha256": digest,
        "max_date": max_date,
    }


def load_history(history_path: str = HISTORY_PATH) -> list[dict]:
    if not os.path.exists(history_path):
        return []
    entries = []
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_history(
    *,
    data_dir: str = DATA_DIR,
    history_path: str = HISTORY_PATH,
) -> list[dict]:
    """Append one history entry per existing CSV to the append-only ledger.

    Idempotency: a file whose data state (cutoff/rows/hash) is unchanged from
    its most recent ledger entry is skipped, so repeat write_manifest calls on
    the same data (multiple daily launches) don't bloat the ledger — entries
    mark actual data states, not build invocations.
    """
    last_by_file: dict[str, dict] = {}
    for entry in load_history(history_path):
        last_by_file[entry.get("file", "")] = entry

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    appended: list[dict] = []
    for fname in CSV_SPECS:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            continue
        canon = _canonical_history(path)
        if canon["history_sha256"] is None:
            continue
        prev = last_by_file.get(fname)
        if prev is not None and (
            prev.get("cutoff_date") == canon["cutoff_date"]
            and prev.get("rows_to_cutoff") == canon["rows_to_cutoff"]
            and prev.get("history_sha256") == canon["history_sha256"]
        ):
            continue
        entry = {
            "file": fname,
            "built_utc": now,
            "cutoff_date": canon["cutoff_date"],
            "rows_to_cutoff": canon["rows_to_cutoff"],
            "history_sha256": canon["history_sha256"],
        }
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=False))
            f.write("\n")
        appended.append(entry)
    return appended


def verify_bar_immutability(
    max_entries: int = 20,
    *,
    data_dir: str = DATA_DIR,
    history_path: str = HISTORY_PATH,
) -> dict:
    """Prove historical bars never changed across refreshes (deep-val D8.1).

    For the most recent `max_entries` ledger entries per file, recompute the
    history hash over rows <= that entry's cutoff_date in the CURRENT csv.
    Any mismatch means a bar that existed at ledger time was retroactively
    edited, inserted before, or deleted. A current file whose coverage no
    longer reaches an old cutoff is also a failure — history must never
    shrink silently (a deliberate rebuild must reset the ledger explicitly).
    """
    entries = load_history(history_path)
    if not entries:
        return {
            "ok": True,
            "checked": 0,
            "failures": [],
            "note": "no history yet",
        }

    by_file: dict[str, list[dict]] = {}
    for entry in entries:
        by_file.setdefault(str(entry.get("file")), []).append(entry)

    checked = 0
    failures: list[dict] = []
    for fname, file_entries in by_file.items():
        path = os.path.join(data_dir, fname)
        recent = file_entries[-max_entries:]
        if not os.path.exists(path):
            failures.append(
                {
                    "file": fname,
                    "cutoff_date": recent[-1].get("cutoff_date"),
                    "reason": "file missing on disk but present in history ledger",
                }
            )
            continue
        for entry in recent:
            checked += 1
            cutoff = entry.get("cutoff_date")
            canon = _canonical_history(path, cutoff_date=cutoff)
            if canon["max_date"] is None or str(canon["max_date"]) < str(cutoff):
                failures.append(
                    {
                        "file": fname,
                        "cutoff_date": cutoff,
                        "reason": (
                            f"coverage shrank: current file ends {canon['max_date']}, "
                            f"before ledgered cutoff {cutoff}"
                        ),
                    }
                )
                continue
            if canon["history_sha256"] != entry.get("history_sha256"):
                failures.append(
                    {
                        "file": fname,
                        "cutoff_date": cutoff,
                        "reason": (
                            "retroactive bar change: rows <= cutoff hash "
                            f"{str(canon['history_sha256'])[:12]}…, ledgered "
                            f"{str(entry.get('history_sha256'))[:12]}… "
                            f"(rows now {canon['rows_to_cutoff']}, "
                            f"ledgered {entry.get('rows_to_cutoff')})"
                        ),
                    }
                )
    return {"ok": not failures, "checked": checked, "failures": failures}


def load_manifest(path: str = MANIFEST_PATH) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def verify_against_disk(path: str = MANIFEST_PATH) -> list[dict]:
    """
    Verify each manifest entry's checksum matches the actual file on disk.
    Returns list of {file, status, message} dicts.
    """
    m = load_manifest(path)
    if m is None:
        return [
            {
                "file": "manifest.json",
                "status": "MISSING",
                "message": "manifest not found",
            }
        ]

    results = []
    for fname, entry in m.get("files", {}).items():
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            results.append(
                {"file": fname, "status": "FAIL", "message": "file missing on disk"}
            )
            continue
        if "sha256" not in entry:
            results.append(
                {"file": fname, "status": "WARN", "message": "no sha256 in manifest"}
            )
            continue
        actual = _file_sha256(fpath)
        if actual == entry["sha256"]:
            results.append({"file": fname, "status": "PASS", "message": ""})
        else:
            results.append(
                {
                    "file": fname,
                    "status": "FAIL",
                    "message": f"sha256 drift: expected {entry['sha256'][:12]}…, got {actual[:12]}…",
                }
            )
    return results


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build", help="(default) Build/refresh data/manifest.json")
    sub.add_parser("verify", help="Verify checksums of CSVs vs manifest")
    args = ap.parse_args(argv)

    cmd = args.cmd or "build"

    if cmd == "build":
        m = write_manifest()
        print(f"Wrote {MANIFEST_PATH}")
        for fname, entry in m["files"].items():
            sha = (entry.get("sha256") or "")[:12]
            rows = entry.get("rows", "?")
            status = entry.get("status", "OK")
            print(f"  {fname:<32} rows={rows:<6} sha256={sha}…  status={status}")
        return 0

    if cmd == "verify":
        results = verify_against_disk()
        any_fail = False
        for r in results:
            tag = r["status"]
            extra = f" — {r['message']}" if r["message"] else ""
            print(f"  [{tag}] {r['file']}{extra}")
            if tag == "FAIL":
                any_fail = True
        return 1 if any_fail else 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

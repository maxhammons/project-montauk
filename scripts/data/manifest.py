#!/usr/bin/env python3
"""
data/manifest.json builder (Phase 3c).

Captures per-CSV provenance metadata + SHA-256 checksums + build timestamps
so silent tampering or staleness can be detected by data_quality.py.

The manifest is the source of truth for "what each CSV claims to be."
Regenerate after any data refresh or rebuild.
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
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # scripts/data/ -> scripts/ -> project root
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

# Per-CSV declared provenance. Build script attaches sha256 + rows + built_utc.
CSV_SPECS = {
    "TECL.csv": {
        "source_real": "Yahoo Finance (TECL)",
        "source_synthetic": "3x ^SP500-45 (1993-1998) + 3x XLK (1998-2008), 0.95%/yr expense, daily compounded",
        "seam_date": "2008-12-17",
        "expense_ratio_source": "ProShares 2024 prospectus (TECL: 0.95%/yr)",
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
        "source_real": "Yahoo Finance (^VIX)",
        "seam_date": "1990-01-02",
        "notes": "CBOE Volatility Index. Merged into TECL.csv as vix_close column.",
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
    except Exception:
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
    return m


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

#!/usr/bin/env python3
"""Build one-row-per-family Gold confidence leaderboards.

The authority leaderboard can contain several sibling configs from the same
strategy family. This diagnostic compresses that view into family leaders and
ranks representatives by composite confidence first.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from certify.contract import sync_entry_contract

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "runs", "family_confidence_leaderboard.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence(row: dict[str, Any]) -> float:
    return _safe_float((row.get("validation") or {}).get("composite_confidence"))


def _display_name(row: dict[str, Any]) -> str:
    return str(row.get("display_name") or row.get("strategy") or "unknown")


def _codename_family(row: dict[str, Any]) -> str:
    name = re.sub(r"\s+#\d+$", "", _display_name(row).strip())
    parts = name.split()
    return parts[-1] if parts else "unknown"


def _family_key(row: dict[str, Any], family_key: str) -> str:
    if family_key == "codename":
        return _codename_family(row)
    return str(row.get("strategy") or "unknown")


def _tie_key(row: dict[str, Any]) -> tuple[float, float, float, float, float]:
    metrics = row.get("metrics") or {}
    return (
        _confidence(row),
        _safe_float(row.get("overall_performance_score")),
        _safe_float(row.get("fitness")),
        _safe_float(metrics.get("real_share_multiple")),
        _safe_float(metrics.get("modern_share_multiple")),
    )


def _leader_row(row: dict[str, Any], *, rank: int, family: str, family_size: int) -> dict[str, Any]:
    metrics = row.get("metrics") or {}
    validation = row.get("validation") or {}
    return {
        "rank": rank,
        "family": family,
        "family_size": family_size,
        "leaderboard_rank": row.get("leaderboard_rank"),
        "display_name": _display_name(row),
        "strategy": row.get("strategy"),
        "confidence": round(_confidence(row), 4),
        "confidence_100": round(_confidence(row) * 100.0, 2),
        "overall_performance_score": row.get("overall_performance_score"),
        "fitness": row.get("fitness"),
        "gold_status": bool(row.get("gold_status") or validation.get("gold_status")),
        "gold_status_label": row.get("gold_status_label")
        or validation.get("gold_status_label")
        or "Gold Status",
        "metrics": {
            "share_multiple": metrics.get("share_multiple"),
            "real_share_multiple": metrics.get("real_share_multiple"),
            "modern_share_multiple": metrics.get("modern_share_multiple"),
            "trades": metrics.get("trades"),
            "max_dd": metrics.get("max_dd"),
        },
        "params": row.get("params") or {},
    }


def load_gold_rows(path: str) -> list[dict[str, Any]]:
    rows = []
    for rank, row in enumerate(_load_json(path), start=1):
        synced = sync_entry_contract(dict(row))
        if not synced.get("gold_status"):
            continue
        synced["leaderboard_rank"] = rank
        rows.append(synced)
    return rows


def build_family_board(rows: list[dict[str, Any]], *, family_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(_family_key(row, family_key), []).append(row)

    leaders = []
    for family, family_rows in grouped.items():
        selected = max(family_rows, key=_tie_key)
        leaders.append((family, selected, len(family_rows)))

    leaders.sort(key=lambda item: _tie_key(item[1]), reverse=True)
    return [
        _leader_row(row, rank=idx, family=family, family_size=family_size)
        for idx, (family, row, family_size) in enumerate(leaders, start=1)
    ]


def build_report(path: str) -> dict[str, Any]:
    rows = load_gold_rows(path)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": os.path.relpath(path, PROJECT_ROOT),
        "gold_rows": len(rows),
        "confidence_definition": (
            "composite_confidence estimates robustness into future TECL data; "
            "it is not a raw performance score."
        ),
        "selection_rule": (
            "Gold rows only; one representative per family; choose highest "
            "composite_confidence, tie-break by all-era score, fitness, real "
            "share multiple, then modern share multiple."
        ),
        "strategy_family_leaders": build_family_board(rows, family_key="strategy"),
        "codename_family_leaders": build_family_board(rows, family_key="codename"),
    }


def format_board(report: dict[str, Any], *, family_key: str) -> str:
    key = "codename_family_leaders" if family_key == "codename" else "strategy_family_leaders"
    title = "CODENAME FAMILY CONFIDENCE LEADERBOARD" if family_key == "codename" else "STRATEGY FAMILY CONFIDENCE LEADERBOARD"
    lines = [
        title,
        "=" * 108,
        f"Gold rows: {report['gold_rows']}",
        "rank family                         leader                  conf  overall fit   full  real modern n",
    ]
    for row in report[key]:
        metrics = row["metrics"]
        lines.append(
            f"{row['rank']:>4} {row['family'][:30]:30s} "
            f"{row['display_name'][:22]:22s} "
            f"{row['confidence_100']:>5.1f} "
            f"{_safe_float(row.get('overall_performance_score')):>7.3f} "
            f"{_safe_float(row.get('fitness')):>5.3f} "
            f"{_safe_float(metrics.get('share_multiple')):>6.2f} "
            f"{_safe_float(metrics.get('real_share_multiple')):>5.2f} "
            f"{_safe_float(metrics.get('modern_share_multiple')):>6.2f} "
            f"{row['family_size']:>2}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leaderboard", default=LEADERBOARD_PATH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--family-key", choices=("strategy", "codename"), default="strategy")
    args = parser.parse_args()

    report = build_report(args.leaderboard)
    print(format_board(report, family_key=args.family_key))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[family-confidence] wrote {args.output}")


if __name__ == "__main__":
    main()

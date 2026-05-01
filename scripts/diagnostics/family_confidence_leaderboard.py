#!/usr/bin/env python3
"""Build one-row-per-family Gold confidence leaderboards.

The authority leaderboard can contain several sibling configs from the same
strategy family. This diagnostic compresses that view into family leaders and
ranks representatives by a stricter future-confidence score first.

`validation.composite_confidence` remains the certification score. This report
adds `future_confidence`, a harder-to-game selection score for family-level
strategy choice. It starts from validation confidence and then discounts weak
evidence planks, era imbalance, drawdown, parameter sprawl, family crowding,
and duplicate signals.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from math import log
from typing import Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from certify.contract import sync_entry_contract

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "runs", "family_confidence_leaderboard.json")
DEFAULT_DIVERSITY_REPORT = os.path.join(PROJECT_ROOT, "runs", "gold_diversity_report.json")
DEFAULT_CONFIDENCE_V2 = os.path.join(PROJECT_ROOT, "runs", "confidence_v2", "leaderboard_scores.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _inverse_interp(value: float, pass_: float, soft: float, fail: float) -> float:
    """Inverse smooth score where lower values are better."""
    value = float(value)
    if value <= pass_:
        return 1.0
    if value >= fail:
        return 0.0
    if value <= soft:
        return 1.0 - 0.5 * ((value - pass_) / max(soft - pass_, 1e-9))
    return 0.5 - 0.5 * ((value - soft) / max(fail - soft, 1e-9))


def _weighted_geomean(values: dict[str, float], weights: dict[str, float]) -> float:
    present = {k: _clamp(v, 1e-6, 1.0) for k, v in values.items() if v is not None}
    if not present:
        return 0.0
    total = sum(weights[k] for k in present)
    score = 1.0
    for key, value in present.items():
        score *= value ** (weights[key] / total)
    return _clamp(score)


def _percentile(values: list[float], q: float) -> float:
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return 0.0
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * _clamp(q)
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return clean[lo] * (1.0 - frac) + clean[hi] * frac


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


def _count_leaf_params(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_leaf_params(v) for v in value.values())
    if isinstance(value, list):
        return sum(_count_leaf_params(v) for v in value)
    return 1


def _load_duplicate_scores(path: str | None) -> dict[str, float]:
    """Return duplicate-signal scores by display name.

    Score is 1.0 when no highly redundant neighbor is found, and trends toward
    0.80 when risk-state correlation plus entry/exit overlap are all near 1.0.
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        report = _load_json(path)
    except Exception:
        return {}
    max_redundancy: dict[str, float] = {}
    for pair in report.get("pairs", []) or []:
        a = str(pair.get("a_name") or "")
        b = str(pair.get("b_name") or "")
        values = [
            _safe_float(pair.get("risk_on_corr")),
            _safe_float(pair.get("entry_overlap")),
            _safe_float(pair.get("exit_overlap")),
        ]
        redundancy = sum(values) / len(values)
        for name in (a, b):
            if name:
                max_redundancy[name] = max(max_redundancy.get(name, 0.0), redundancy)
    scores = {}
    for name, redundancy in max_redundancy.items():
        penalty = _clamp((redundancy - 0.90) / 0.10) * 0.20
        scores[name] = round(_clamp(1.0 - penalty, 0.80, 1.0), 4)
    return scores


def _params_key(params: dict[str, Any]) -> str:
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))


def _strategy_key(row: dict[str, Any]) -> str:
    return f"{row.get('strategy') or 'unknown'}::{_params_key(row.get('params') or {})}"


def _load_confidence_v2(path: str | None) -> dict[str, dict[str, Any]]:
    if not path or not os.path.exists(path):
        return {}
    try:
        report = _load_json(path)
    except Exception:
        return {}
    out = {}
    for score in report.get("scores", []) or []:
        key = score.get("strategy_key")
        if key:
            out[str(key)] = score
    return out


def _future_confidence(row: dict[str, Any], *, family_size: int, duplicate_score: float | None) -> tuple[float, dict[str, float]]:
    metrics = row.get("metrics") or {}
    validation = row.get("validation") or {}
    sub_scores = validation.get("sub_scores") or {}
    validation_confidence = _confidence(row)

    evidence_scores = [
        _safe_float(value)
        for key, value in sub_scores.items()
        if value is not None and key != "cross_asset"
    ]
    if evidence_scores:
        evidence_floor = 0.65 * _percentile(evidence_scores, 0.20) + 0.35 * min(evidence_scores)
    else:
        evidence_floor = validation_confidence

    real = _safe_float(metrics.get("real_share_multiple"))
    modern = _safe_float(metrics.get("modern_share_multiple"))
    full = _safe_float(metrics.get("share_multiple"))
    era_values = [v for v in (full, real, modern) if v > 0]
    if real > 0 and modern > 0:
        era_floor = 0.70 + 0.30 * _clamp((min(real, modern) - 1.0) / 0.50)
        era_symmetry = _clamp(min(real, modern) / max(real, modern))
        era_balance = 0.75 * era_floor + 0.25 * era_symmetry
    elif era_values:
        era_balance = _clamp(min(era_values) / max(era_values))
    else:
        era_balance = 0.0

    drawdown = _safe_float(metrics.get("max_dd"), 100.0)
    drawdown_resilience = _inverse_interp(drawdown, pass_=55.0, soft=75.0, fail=95.0)

    n_params = int(_safe_float(metrics.get("n_params"), _count_leaf_params(row.get("params") or {})))
    parsimony = _inverse_interp(n_params, pass_=8.0, soft=24.0, fail=80.0)

    crowding = 1.0 if family_size <= 1 else 1.0 - min(0.12, (log(family_size) / log(20.0)) * 0.12)

    soft = len(validation.get("soft_warnings") or [])
    critical = len(validation.get("critical_warnings") or [])
    warning_cleanliness = _clamp(1.0 - min(0.25, 0.015 * soft + 0.04 * critical), 0.75, 1.0)

    components = {
        "validation_confidence": validation_confidence,
        "evidence_floor": _clamp(evidence_floor),
        "era_balance": _clamp(era_balance),
        "drawdown_resilience": _clamp(drawdown_resilience),
        "parameter_parsimony": _clamp(parsimony),
        "duplicate_signal": _clamp(duplicate_score if duplicate_score is not None else 1.0, 0.80, 1.0),
        "family_crowding": _clamp(crowding, 0.88, 1.0),
        "warning_cleanliness": warning_cleanliness,
    }
    weights = {
        "validation_confidence": 0.35,
        "evidence_floor": 0.18,
        "era_balance": 0.14,
        "drawdown_resilience": 0.10,
        "parameter_parsimony": 0.08,
        "duplicate_signal": 0.07,
        "family_crowding": 0.05,
        "warning_cleanliness": 0.03,
    }
    return _weighted_geomean(components, weights), components


def _tie_key(row: dict[str, Any]) -> tuple[float, float, float, float, float]:
    metrics = row.get("metrics") or {}
    return (
        _safe_float(row.get("edge_confidence"), -1.0),
        _safe_float(row.get("capital_readiness"), -1.0),
        _safe_float(row.get("future_confidence"), _confidence(row)),
        _safe_float(row.get("overall_performance_score")),
        _safe_float(row.get("fitness")),
        _safe_float(metrics.get("real_share_multiple")),
        _safe_float(metrics.get("modern_share_multiple")),
    )


def _leader_row(row: dict[str, Any], *, rank: int, family: str, family_size: int) -> dict[str, Any]:
    metrics = row.get("metrics") or {}
    validation = row.get("validation") or {}
    future_confidence = _safe_float(row.get("future_confidence"), _confidence(row))
    components = row.get("future_confidence_components") or {}
    return {
        "rank": rank,
        "family": family,
        "family_size": family_size,
        "leaderboard_rank": row.get("leaderboard_rank"),
        "display_name": _display_name(row),
        "strategy": row.get("strategy"),
        "confidence": round(future_confidence, 4),
        "confidence_100": round(future_confidence * 100.0, 2),
        "future_confidence": round(future_confidence, 4),
        "future_confidence_100": round(future_confidence * 100.0, 2),
        "edge_confidence": row.get("edge_confidence"),
        "edge_confidence_100": row.get("edge_confidence_100"),
        "capital_readiness": row.get("capital_readiness"),
        "capital_readiness_100": row.get("capital_readiness_100"),
        "calibration_state": row.get("calibration_state"),
        "edge_confidence_components": row.get("edge_confidence_components"),
        "capital_readiness_components": row.get("capital_readiness_components"),
        "search_provenance": row.get("search_provenance"),
        "validation_confidence": round(_confidence(row), 4),
        "validation_confidence_100": round(_confidence(row) * 100.0, 2),
        "confidence_components": {
            key: round(float(value), 4) for key, value in components.items()
        },
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


def build_family_board(
    rows: list[dict[str, Any]],
    *,
    family_key: str,
    duplicate_scores: dict[str, float],
    confidence_v2: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(_family_key(row, family_key), []).append(row)

    leaders = []
    for family, family_rows in grouped.items():
        enriched = []
        for row in family_rows:
            candidate = dict(row)
            v2 = confidence_v2.get(_strategy_key(candidate))
            if v2:
                candidate.update(
                    {
                        "edge_confidence": v2.get("edge_confidence"),
                        "edge_confidence_100": v2.get("edge_confidence_100"),
                        "capital_readiness": v2.get("capital_readiness"),
                        "capital_readiness_100": v2.get("capital_readiness_100"),
                        "calibration_state": v2.get("calibration_state"),
                        "edge_confidence_components": v2.get("edge_confidence_components"),
                        "capital_readiness_components": v2.get("capital_readiness_components"),
                        "search_provenance": v2.get("search_provenance"),
                    }
                )
            future, components = _future_confidence(
                candidate,
                family_size=len(family_rows),
                duplicate_score=duplicate_scores.get(_display_name(candidate)),
            )
            candidate["future_confidence"] = future
            candidate["future_confidence_components"] = components
            enriched.append(candidate)
        selected = max(enriched, key=_tie_key)
        leaders.append((family, selected, len(family_rows)))

    leaders.sort(key=lambda item: _tie_key(item[1]), reverse=True)
    return [
        _leader_row(row, rank=idx, family=family, family_size=family_size)
        for idx, (family, row, family_size) in enumerate(leaders, start=1)
    ]


def build_report(
    path: str,
    *,
    diversity_report: str | None = DEFAULT_DIVERSITY_REPORT,
    confidence_v2_report: str | None = DEFAULT_CONFIDENCE_V2,
) -> dict[str, Any]:
    rows = load_gold_rows(path)
    duplicate_scores = _load_duplicate_scores(diversity_report)
    confidence_v2 = _load_confidence_v2(confidence_v2_report)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": os.path.relpath(path, PROJECT_ROOT),
        "gold_rows": len(rows),
        "confidence_definition": (
            "future_confidence estimates robustness into future TECL data. It "
            "starts from validation composite_confidence, then discounts weak "
            "evidence planks, era imbalance, drawdown, parameter sprawl, "
            "duplicate signals, family crowding, and warning load."
        ),
        "selection_rule": (
            "Gold rows only; one representative per family; choose highest "
            "Edge Confidence when Confidence v2 is available, then Capital "
            "Readiness, then legacy future_confidence, all-era score, fitness, "
            "real share multiple, and modern share multiple."
        ),
        "confidence_components": {
            "validation_confidence": "existing validation composite_confidence",
            "evidence_floor": "blend of weakest and 20th percentile validation sub-scores",
            "era_balance": "all-era outperformance floor plus real/modern symmetry",
            "drawdown_resilience": "max drawdown score; lower drawdown is better",
            "parameter_parsimony": "discount for large parameter surfaces",
            "duplicate_signal": "discount for near-identical risk-state and transition behavior",
            "family_crowding": "small discount for crowded sibling clusters",
            "warning_cleanliness": "small discount for soft/critical validation warnings",
        },
        "diversity_source": (
            os.path.relpath(diversity_report, PROJECT_ROOT)
            if diversity_report and os.path.exists(diversity_report)
            else None
        ),
        "confidence_v2_source": (
            os.path.relpath(confidence_v2_report, PROJECT_ROOT)
            if confidence_v2_report and os.path.exists(confidence_v2_report)
            else None
        ),
        "strategy_family_leaders": build_family_board(
            rows,
            family_key="strategy",
            duplicate_scores=duplicate_scores,
            confidence_v2=confidence_v2,
        ),
        "codename_family_leaders": build_family_board(
            rows,
            family_key="codename",
            duplicate_scores=duplicate_scores,
            confidence_v2=confidence_v2,
        ),
    }


def format_board(report: dict[str, Any], *, family_key: str) -> str:
    key = "codename_family_leaders" if family_key == "codename" else "strategy_family_leaders"
    title = "CODENAME FAMILY CONFIDENCE LEADERBOARD" if family_key == "codename" else "STRATEGY FAMILY CONFIDENCE LEADERBOARD"
    lines = [
        title,
        "=" * 108,
        f"Gold rows: {report['gold_rows']}",
        "rank family                         leader                   edge   cap future valid overall fit   full  real modern n",
    ]
    for row in report[key]:
        metrics = row["metrics"]
        lines.append(
            f"{row['rank']:>4} {row['family'][:30]:30s} "
            f"{row['display_name'][:22]:22s} "
            f"{_safe_float(row.get('edge_confidence_100')):>6.1f} "
            f"{_safe_float(row.get('capital_readiness_100')):>5.1f} "
            f"{row['future_confidence_100']:>6.1f} "
            f"{row['validation_confidence_100']:>5.1f} "
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
    parser.add_argument("--diversity-report", default=DEFAULT_DIVERSITY_REPORT)
    parser.add_argument("--confidence-v2-report", default=DEFAULT_CONFIDENCE_V2)
    parser.add_argument("--family-key", choices=("strategy", "codename"), default="strategy")
    args = parser.parse_args()

    report = build_report(
        args.leaderboard,
        diversity_report=args.diversity_report,
        confidence_v2_report=args.confidence_v2_report,
    )
    print(format_board(report, family_key=args.family_key))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[family-confidence] wrote {args.output}")


if __name__ == "__main__":
    main()

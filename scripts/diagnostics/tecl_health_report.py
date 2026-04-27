#!/usr/bin/env python3
"""Audit TECL Health against named regimes and hand-marked cycles.

The TECL Health model is diagnostic-only. This report checks whether the
score is directionally useful before weights, caps, or smoothing are tuned.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(THIS_DIR)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
VIZ_DIR = os.path.join(PROJECT_ROOT, "viz")

for path in (SCRIPTS_DIR, VIZ_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from build_viz import compute_tecl_health, load_tecl  # noqa: E402
from certify.backfill_multi_era_metrics import MARKET_REGIMES  # noqa: E402
from strategies.regime_map import build_regime_map  # noqa: E402

MARKERS_CSV = os.path.join(PROJECT_ROOT, "data", "markers", "TECL-markers.csv")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "docs", "tecl-health-audit.md")


def _finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(out):
        return None
    return out


def _fmt_num(value: Any, digits: int = 1) -> str:
    value = _finite_float(value)
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _fmt_pct(value: Any, digits: int = 1) -> str:
    value = _finite_float(value)
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f}%"


def _fmt_share_pct(value: Any, digits: int = 0) -> str:
    value = _finite_float(value)
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}%"


def _fmt_int(value: Any) -> str:
    value = _finite_float(value)
    if value is None:
        return "n/a"
    return str(int(round(value)))


def _date_str(value: Any) -> str:
    if value is None or value == "":
        return "open"
    return pd.Timestamp(value).date().isoformat()


def _tecl_price_df(tecl: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(tecl["dates"]).normalize(),
        "close": pd.to_numeric(pd.Series(tecl["close"]), errors="coerce"),
    })


def _health_df(health: dict[str, Any]) -> pd.DataFrame:
    series = health.get("series") or []
    if not series:
        return pd.DataFrame()

    df = pd.DataFrame(series)
    layers = pd.DataFrame((df.pop("layers") if "layers" in df else pd.Series([])).tolist())
    layers = layers.add_prefix("layer_")
    df = pd.concat([df, layers], axis=1)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    numeric_cols = [
        "composite",
        "smooth",
        "cross",
        "confidence",
        "layer_structure",
        "layer_momentum",
        "layer_stress",
        "layer_participation",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    layer_cols = [c for c in df.columns if c.startswith("layer_")]
    df["conflict"] = df[layer_cols].std(axis=1, skipna=True, ddof=0)
    return df


def _window_slice(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def _period_return(price_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float | None:
    window = _window_slice(price_df, start, end).dropna(subset=["close"])
    if len(window) < 2:
        return None
    first = _finite_float(window.iloc[0]["close"])
    last = _finite_float(window.iloc[-1]["close"])
    if first is None or first <= 0 or last is None:
        return None
    return (last / first - 1.0) * 100.0


def _summarize_period(
    health_df: pd.DataFrame,
    price_df: pd.DataFrame,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp | None,
    data_end: pd.Timestamp,
) -> dict[str, Any]:
    start_ts = pd.Timestamp(start).normalize()
    end_ts = data_end if end is None else min(pd.Timestamp(end).normalize(), data_end)
    window = _window_slice(health_df, start_ts, end_ts)
    scored = window.dropna(subset=["composite"])
    if scored.empty:
        return {
            "start": start_ts.date().isoformat(),
            "end": end_ts.date().isoformat(),
            "n": 0,
            "return_pct": _period_return(price_df, start_ts, end_ts),
        }

    first = scored.iloc[0]
    last = scored.iloc[-1]
    return {
        "start": start_ts.date().isoformat(),
        "end": end_ts.date().isoformat(),
        "n": int(len(scored)),
        "return_pct": _period_return(price_df, start_ts, end_ts),
        "score_start": float(first["composite"]),
        "score_end": float(last["composite"]),
        "score_avg": float(scored["composite"].mean()),
        "score_min": float(scored["composite"].min()),
        "score_max": float(scored["composite"].max()),
        "delta": float(last["composite"] - first["composite"]),
        "fast_avg": float(scored["smooth"].mean()) if "smooth" in scored else None,
        "slow_avg": float(scored["cross"].mean()) if "cross" in scored else None,
        "structure_avg": float(scored["layer_structure"].mean()) if "layer_structure" in scored else None,
        "momentum_avg": float(scored["layer_momentum"].mean()) if "layer_momentum" in scored else None,
        "stress_avg": float(scored["layer_stress"].mean()) if "layer_stress" in scored else None,
        "participation_avg": (
            float(scored["layer_participation"].mean())
            if "layer_participation" in scored
            else None
        ),
        "confidence_avg": float(scored["confidence"].mean()) if "confidence" in scored else None,
        "conflict_avg": float(scored["conflict"].mean()) if "conflict" in scored else None,
        "pct_healthy": float((scored["composite"] >= 60.0).mean() * 100.0),
        "pct_fragile": float((scored["composite"] < 50.0).mean() * 100.0),
    }


def _alignment_for_expectation(kind: str, avg_score: float | None) -> str:
    if avg_score is None:
        return "n/a"
    if kind in {"bull", "recovery", "risk_on"}:
        if avg_score >= 55.0:
            return "aligned"
        if avg_score >= 50.0:
            return "borderline"
        return "mismatch"
    if kind in {"bear", "crash", "risk_off"}:
        if avg_score <= 50.0:
            return "aligned"
        if avg_score <= 55.0:
            return "borderline"
        return "mismatch"
    return "neutral"


def _load_marker_rows() -> list[dict[str, Any]]:
    if not os.path.exists(MARKERS_CSV):
        return []
    rows: list[dict[str, Any]] = []
    with open(MARKERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "date": row["date"],
                "price": _finite_float(row.get("price")),
                "type": (row.get("type") or "").strip().lower(),
            })
    return rows


def _marker_cycles(data_end: pd.Timestamp) -> list[dict[str, Any]]:
    markers = _load_marker_rows()
    cycles: list[dict[str, Any]] = []

    for prev, nxt in zip(markers, markers[1:]):
        start_type = prev["type"]
        end_type = nxt["type"]
        if start_type == "buy" and end_type == "sell":
            kind = "risk_on"
        elif start_type == "sell" and end_type == "buy":
            kind = "risk_off"
        else:
            kind = "transition"
        cycles.append({
            "kind": kind,
            "start": prev["date"],
            "end": nxt["date"],
            "start_marker": start_type,
            "end_marker": end_type,
        })

    if markers:
        last = markers[-1]
        open_kind = "risk_on" if last["type"] == "buy" else "risk_off"
        cycles.append({
            "kind": open_kind,
            "start": last["date"],
            "end": data_end.date().isoformat(),
            "start_marker": last["type"],
            "end_marker": "open",
        })

    return cycles


def _named_regime_rows(
    health_df: pd.DataFrame,
    price_df: pd.DataFrame,
    data_end: pd.Timestamp,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for regime in MARKET_REGIMES:
        stats = _summarize_period(health_df, price_df, regime["start"], regime.get("end"), data_end)
        avg = stats.get("score_avg")
        stats.update({
            "key": regime["key"],
            "label": regime["label"],
            "kind": regime["kind"],
            "alignment": _alignment_for_expectation(regime["kind"], avg),
            "description": regime.get("description") or "",
        })
        rows.append(stats)
    return rows


def _marker_cycle_rows(
    health_df: pd.DataFrame,
    price_df: pd.DataFrame,
    data_end: pd.Timestamp,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cycle in _marker_cycles(data_end):
        stats = _summarize_period(health_df, price_df, cycle["start"], cycle["end"], data_end)
        kind = cycle["kind"] if cycle["kind"] in {"risk_on", "risk_off"} else "neutral"
        stats.update({
            "kind": cycle["kind"],
            "start_marker": cycle["start_marker"],
            "end_marker": cycle["end_marker"],
            "alignment": _alignment_for_expectation(kind, stats.get("score_avg")),
        })
        rows.append(stats)
    return rows


def _detected_cycle_rows(
    health_df: pd.DataFrame,
    price_df: pd.DataFrame,
    data_end: pd.Timestamp,
) -> list[dict[str, Any]]:
    regime_df = price_df.rename(columns={"close": "close"}).copy()
    regime_map = build_regime_map(regime_df)
    rows: list[dict[str, Any]] = []
    for cycle in regime_map["cycles"]:
        stats = _summarize_period(health_df, price_df, cycle["start_date"], cycle["end_date"], data_end)
        avg = stats.get("score_avg")
        stats.update({
            "kind": cycle["type"],
            "move_pct": cycle.get("move_pct"),
            "duration_months": cycle.get("duration_months"),
            "alignment": _alignment_for_expectation(cycle["type"], avg),
        })
        rows.append(stats)
    return rows


def _mean_score(rows: list[dict[str, Any]], kinds: set[str]) -> float | None:
    values = [
        r["score_avg"]
        for r in rows
        if r.get("kind") in kinds and _finite_float(r.get("score_avg")) is not None
    ]
    if not values:
        return None
    return float(np.mean(values))


def _fit_summary(rows: list[dict[str, Any]]) -> tuple[int, int]:
    evaluated = [
        r for r in rows
        if r.get("alignment") in {"aligned", "borderline", "mismatch"}
    ]
    fit = [r for r in evaluated if r.get("alignment") in {"aligned", "borderline"}]
    return len(fit), len(evaluated)


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return out


def _build_observations(
    named_rows: list[dict[str, Any]],
    marker_rows: list[dict[str, Any]],
    latest: dict[str, Any],
) -> list[str]:
    observations: list[str] = []
    bull_mean = _mean_score(named_rows, {"bull", "recovery"})
    bear_mean = _mean_score(named_rows, {"bear", "crash"})
    if bull_mean is not None and bear_mean is not None:
        observations.append(
            f"- Named-regime separation: bull/recovery average health is "
            f"{bull_mean:.1f} vs bear/crash {bear_mean:.1f}, a {bull_mean - bear_mean:.1f}-point spread."
        )

    scored_named = [r for r in named_rows if _finite_float(r.get("score_avg")) is not None]
    if scored_named:
        strongest = max(scored_named, key=lambda r: r["score_avg"])
        weakest = min(scored_named, key=lambda r: r["score_avg"])
        observations.append(
            f"- Strongest named regime: {strongest['label']} at {_fmt_num(strongest['score_avg'])} average health."
        )
        observations.append(
            f"- Weakest named regime: {weakest['label']} at {_fmt_num(weakest['score_avg'])} average health."
        )

    fit, total = _fit_summary(marker_rows)
    if total:
        observations.append(f"- Marker-cycle fit: {fit}/{total} evaluated cycles are aligned or borderline.")
        mismatches = [r for r in marker_rows if r.get("alignment") == "mismatch"]
        if mismatches:
            worst = sorted(
                mismatches,
                key=lambda r: abs((r.get("score_avg") or 50.0) - 50.0),
                reverse=True,
            )[:3]
            labels = [
                f"{r['start']} to {r['end']} ({r['kind']}, avg {_fmt_num(r.get('score_avg'))})"
                for r in worst
            ]
            observations.append("- Main marker mismatches: " + "; ".join(labels) + ".")

    conflict_rows = [r for r in named_rows if _finite_float(r.get("conflict_avg")) is not None]
    if conflict_rows:
        conflict = max(conflict_rows, key=lambda r: r["conflict_avg"])
        observations.append(
            f"- Highest layer conflict by named regime: {conflict['label']} "
            f"at {_fmt_num(conflict['conflict_avg'])}."
        )

    if latest:
        observations.append(
            f"- Latest readout: {latest.get('date')} is {latest.get('status')} "
            f"with composite {_fmt_num(latest.get('composite'))}, confidence "
            f"{_fmt_num(latest.get('confidence'))}, and conflict {_fmt_num(latest.get('conflict'))}."
        )

    return observations


def _render_report(
    health: dict[str, Any],
    tecl: dict[str, Any],
    named_rows: list[dict[str, Any]],
    marker_rows: list[dict[str, Any]],
    detected_rows: list[dict[str, Any]],
) -> str:
    data_end = tecl["dates"][-1]
    latest = health.get("latest") or {}
    settings = health.get("settings") or {}
    vix_count = sum(1 for v in (tecl.get("vix") or []) if _finite_float(v) is not None)
    marker_fit, marker_total = _fit_summary(marker_rows)

    lines: list[str] = []
    lines.append("# TECL Health Audit")
    lines.append("")
    lines.append(f"Generated: {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Data through: {data_end}")
    lines.append(f"Model: `{settings.get('model', 'unknown')}`")
    lines.append("")
    lines.append("> Diagnostic-only report. TECL Health is not a buy/sell signal, not a strategy, and not part of leaderboard certification.")
    lines.append("")

    lines.append("## Current Readout")
    lines.extend(_md_table(
        ["Date", "Composite", "Status", "Confidence", "Conflict", "Fast Avg", "Slow Avg"],
        [[
            str(latest.get("date") or "n/a"),
            _fmt_num(latest.get("composite")),
            str(latest.get("status") or "n/a"),
            _fmt_num(latest.get("confidence")),
            _fmt_num(latest.get("conflict")),
            _fmt_num(latest.get("smooth")),
            _fmt_num(latest.get("cross")),
        ]],
    ))
    lines.append("")
    layers = latest.get("layers") or {}
    lines.extend(_md_table(
        ["Structure", "Momentum", "Stress", "Participation"],
        [[
            _fmt_num(layers.get("structure")),
            _fmt_num(layers.get("momentum")),
            _fmt_num(layers.get("stress")),
            _fmt_num(layers.get("participation")),
        ]],
    ))
    lines.append("")

    calibration = settings.get("calibration") or {}
    if calibration:
        lines.append("## Calibration")
        lines.extend(_md_table(
            ["Setting", "Value"],
            [
                ["Layer weights", ", ".join(f"{k} {v:.2f}" for k, v in (settings.get("layer_weights") or {}).items())],
                ["Core blend", f"{_fmt_num(calibration.get('geometric_core_weight'), 2)} geometric / {_fmt_num(calibration.get('arithmetic_core_weight'), 2)} arithmetic"],
                ["Recovery credit", f"{_fmt_num(calibration.get('recovery_credit_weight'), 2)} * max(0, min(momentum, participation) - stress)"],
                ["Stress cap", str(settings.get("stress_cap") or "n/a")],
                ["Basis", str(calibration.get("basis") or "n/a")],
            ],
        ))
        lines.append("")

    lines.append("## Coverage")
    lines.extend(_md_table(
        ["Input", "Coverage"],
        [
            ["TECL rows", str(len(tecl.get("dates") or []))],
            ["VIX matched rows", f"{vix_count}/{len(tecl.get('dates') or [])}"],
            ["Named regimes", str(len(named_rows))],
            ["Marker cycles", str(len(marker_rows))],
            ["Marker-cycle directional fit", f"{marker_fit}/{marker_total}"],
        ],
    ))
    lines.append("")

    lines.append("## Observations")
    lines.extend(_build_observations(named_rows, marker_rows, latest))
    lines.append("")

    lines.append("## Named Regimes")
    lines.extend(_md_table(
        [
            "Regime",
            "Kind",
            "Dates",
            "TECL Return",
            "Avg",
            "Min/Max",
            "End",
            "Struct/Mom/Stress/Part",
            "Conf/Conflict",
            "Fit",
        ],
        [
            [
                r["label"],
                r["kind"],
                f"{r['start']} to {r['end']}",
                _fmt_pct(r.get("return_pct")),
                _fmt_num(r.get("score_avg")),
                f"{_fmt_num(r.get('score_min'))}/{_fmt_num(r.get('score_max'))}",
                _fmt_num(r.get("score_end")),
                (
                    f"{_fmt_int(r.get('structure_avg'))}/"
                    f"{_fmt_int(r.get('momentum_avg'))}/"
                    f"{_fmt_int(r.get('stress_avg'))}/"
                    f"{_fmt_int(r.get('participation_avg'))}"
                ),
                f"{_fmt_int(r.get('confidence_avg'))}/{_fmt_int(r.get('conflict_avg'))}",
                r["alignment"],
            ]
            for r in named_rows
        ],
    ))
    lines.append("")

    lines.append("## Marker Cycles")
    lines.extend(_md_table(
        [
            "Cycle",
            "Markers",
            "TECL Return",
            "Avg",
            "Start/End",
            "Healthy Days",
            "Fragile Days",
            "Fit",
        ],
        [
            [
                f"{r['start']} to {r['end']}",
                f"{r['start_marker']} -> {r['end_marker']}",
                _fmt_pct(r.get("return_pct")),
                _fmt_num(r.get("score_avg")),
                f"{_fmt_num(r.get('score_start'))}/{_fmt_num(r.get('score_end'))}",
                _fmt_share_pct(r.get("pct_healthy")),
                _fmt_share_pct(r.get("pct_fragile")),
                r["alignment"],
            ]
            for r in marker_rows
        ],
    ))
    lines.append("")

    recent_detected = detected_rows[-12:]
    lines.append("## Detected Cycle Snapshot")
    lines.append("Last 12 algorithmic bull/bear cycles from `scripts/strategies/regime_map.py`.")
    lines.extend(_md_table(
        ["Type", "Dates", "Move", "Duration", "Avg Health", "End Health", "Fit"],
        [
            [
                r["kind"],
                f"{r['start']} to {r['end']}",
                _fmt_pct(r.get("move_pct")),
                f"{_fmt_num(r.get('duration_months'))} mo",
                _fmt_num(r.get("score_avg")),
                _fmt_num(r.get("score_end")),
                r["alignment"],
            ]
            for r in recent_detected
        ],
    ))
    lines.append("")

    lines.append("## Calibration Targets")
    lines.append("- Preserve diagnostic-only behavior: no buy/sell calls, no leaderboard rank effect, no certification effect.")
    lines.append("- Use marker-cycle separation as the first tuning target: risk-on windows should average materially above risk-off windows.")
    lines.append("- Use named crash/bear regimes as the stress test: crashes should compress the health score quickly without permanently suppressing recovery regimes.")
    lines.append("- Treat fast and slow averages as readout aids, not the primary truth source, until lag is measured against marker transitions.")
    lines.append("- Review mismatched cycles before changing weights; a mismatch may be a useful warning rather than a model error.")
    lines.append("")

    return "\n".join(lines)


def build_report(output_path: str = DEFAULT_OUTPUT) -> str:
    tecl = load_tecl()
    price_df = _tecl_price_df(tecl)
    health = compute_tecl_health(tecl)
    health_df = _health_df(health)
    if health_df.empty:
        raise RuntimeError("TECL Health produced no series rows")

    data_end = pd.Timestamp(tecl["dates"][-1]).normalize()
    named_rows = _named_regime_rows(health_df, price_df, data_end)
    marker_rows = _marker_cycle_rows(health_df, price_df, data_end)
    detected_rows = _detected_cycle_rows(health_df, price_df, data_end)

    report = _render_report(health, tecl, named_rows, marker_rows, detected_rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
        f.write("\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit TECL Health diagnostic score.")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Markdown output path.",
    )
    args = parser.parse_args()

    try:
        path = build_report(args.output)
    except Exception as exc:  # noqa: BLE001
        print(f"[tecl-health-report] FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"[tecl-health-report] wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

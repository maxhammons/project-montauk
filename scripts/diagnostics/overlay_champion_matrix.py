#!/usr/bin/env python3
"""Overlay-on-Gold-champion matrix.

This diagnostic answers the question:

    Does an overlay module improve a current Gold Bonobo champion without
    breaking full / real / modern share accumulation?

It takes overlay candidates from a grid-search JSON (or explicit params), swaps
their base Bonobo params for each current Gold ``gc_vjatr`` leaderboard row, and
re-runs the overlay strategy against TECL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certify.contract import sync_entry_contract
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import score_marker_alignment


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")

BASE_KEYS = {
    "fast_ema",
    "slow_ema",
    "slope_window",
    "entry_bars",
    "cooldown",
    "atr_period",
    "atr_look",
    "atr_expand",
    "atr_confirm",
}


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    validation = payload.get("validation") or {}
    rows = validation.get("validated_rankings") or validation.get("raw_rankings")
    if rows:
        return list(rows)
    return list(payload.get("raw_rankings") or payload.get("rankings") or [])


def _overlay_signature(params: dict[str, Any]) -> str:
    overlay_params = {k: v for k, v in (params or {}).items() if k not in BASE_KEYS}
    return json.dumps(overlay_params, sort_keys=True, separators=(",", ":"))


def load_overlay_candidates(
    *,
    overlay_strategy: str,
    grid_path: str | None,
    params_json: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if params_json:
        return [
            {
                "strategy": overlay_strategy,
                "params": json.loads(params_json),
                "source_rank": 1,
            }
        ]
    if not grid_path:
        raise ValueError("provide --grid or --params-json")

    payload = _load_json(grid_path)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _candidate_rows(payload):
        if row.get("strategy") != overlay_strategy:
            continue
        params = row.get("params") or {}
        sig = _overlay_signature(params)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(
            {
                "strategy": overlay_strategy,
                "params": params,
                "source_rank": row.get("rank", len(out) + 1),
                "source_fitness": row.get("fitness"),
                "source_marker": row.get("marker_alignment_score"),
            }
        )
        if len(out) >= limit:
            break
    return out


def load_gold_bases(*, family: str, top_n: int) -> list[dict[str, Any]]:
    leaderboard = _load_json(LEADERBOARD_PATH)
    bases = []
    for row in leaderboard:
        synced = sync_entry_contract(dict(row))
        if synced.get("strategy") != family:
            continue
        if not synced.get("gold_status"):
            continue
        bases.append(synced)
        if len(bases) >= top_n:
            break
    return bases


def merge_base_overlay(base_params: dict[str, Any], overlay_params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(overlay_params or {})
    for key in BASE_KEYS:
        if key in base_params:
            merged[key] = base_params[key]
    return merged


def _slice_df(df: pd.DataFrame, start: str | None) -> pd.DataFrame:
    if start is None:
        return df.reset_index(drop=True)
    return df[df["date"] >= start].reset_index(drop=True)


def _standalone_share_multiple(
    df: pd.DataFrame,
    strategy: str,
    params: dict[str, Any],
    start: str | None,
) -> float:
    df_slice = _slice_df(df, start)
    if len(df_slice) < 2:
        return 0.0
    ind = Indicators(df_slice)
    entries, exits, labels = STRATEGY_REGISTRY[strategy](ind, params)
    result = backtest(
        df_slice,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy,
    )
    return round(float(result.share_multiple), 4)


def _run_strategy(df: pd.DataFrame, strategy: str, params: dict[str, Any]) -> dict[str, Any]:
    if strategy not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {strategy}")
    ind = Indicators(df)
    entries, exits, labels = STRATEGY_REGISTRY[strategy](ind, params)
    result = backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy,
    )
    marker = score_marker_alignment(df, result.trades)
    raw_engine = {
        "share_multiple": round(float(result.share_multiple), 4),
        "real_share_multiple": round(float(result.real_share_multiple), 4),
        "modern_share_multiple": round(float(result.modern_share_multiple), 4),
    }
    return {
        "share_multiple": _standalone_share_multiple(df, strategy, params, None),
        "real_share_multiple": _standalone_share_multiple(df, strategy, params, "2008-12-17"),
        "modern_share_multiple": _standalone_share_multiple(df, strategy, params, "2015-01-01"),
        "raw_engine": raw_engine,
        "metrics_view": "canonical_standalone",
        "trades": int(result.num_trades),
        "trades_per_year": round(float(result.trades_per_year), 4),
        "max_drawdown_pct": round(float(result.max_drawdown_pct), 4),
        "marker_score": marker.get("score"),
        "marker_timing": marker.get("timing_magnitude_weighted"),
    }


def build_matrix(
    *,
    overlay_strategy: str,
    candidates: list[dict[str, Any]],
    bases: list[dict[str, Any]],
    min_real_retention: float,
    min_modern_retention: float,
    min_full_retention: float,
) -> dict[str, Any]:
    df = get_tecl_data()
    rows = []
    for base_idx, base in enumerate(bases, start=1):
        base_strategy = base["strategy"]
        base_params = base.get("params") or {}
        base_metrics = _run_strategy(df, base_strategy, base_params)
        for cand_idx, candidate in enumerate(candidates, start=1):
            overlay_params = merge_base_overlay(base_params, candidate.get("params") or {})
            overlay_metrics = _run_strategy(df, overlay_strategy, overlay_params)
            full_ratio = (
                overlay_metrics["share_multiple"] / base_metrics["share_multiple"]
                if base_metrics["share_multiple"]
                else 0.0
            )
            real_ratio = (
                overlay_metrics["real_share_multiple"] / base_metrics["real_share_multiple"]
                if base_metrics["real_share_multiple"]
                else 0.0
            )
            modern_ratio = (
                overlay_metrics["modern_share_multiple"] / base_metrics["modern_share_multiple"]
                if base_metrics["modern_share_multiple"]
                else 0.0
            )
            timing_delta = (
                float(overlay_metrics["marker_timing"] or 0.0)
                - float(base_metrics["marker_timing"] or 0.0)
            )
            score_delta = (
                float(overlay_metrics["marker_score"] or 0.0)
                - float(base_metrics["marker_score"] or 0.0)
            )
            survives = bool(
                overlay_metrics["share_multiple"] >= 1.0
                and overlay_metrics["real_share_multiple"] >= 1.0
                and overlay_metrics["modern_share_multiple"] >= 1.0
                and full_ratio >= min_full_retention
                and real_ratio >= min_real_retention
                and modern_ratio >= min_modern_retention
            )
            rows.append(
                {
                    "base_rank": base_idx,
                    "base_name": base.get("display_name") or base_strategy,
                    "base_strategy": base_strategy,
                    "candidate_rank": cand_idx,
                    "overlay_strategy": overlay_strategy,
                    "source_rank": candidate.get("source_rank"),
                    "survives": survives,
                    "marker_timing_delta": round(timing_delta, 4),
                    "marker_score_delta": round(score_delta, 4),
                    "full_ratio": round(full_ratio, 4),
                    "real_ratio": round(real_ratio, 4),
                    "modern_ratio": round(modern_ratio, 4),
                    "base_metrics": base_metrics,
                    "overlay_metrics": overlay_metrics,
                    "overlay_params": overlay_params,
                }
            )
    rows.sort(
        key=lambda r: (
            bool(r["survives"]),
            r["marker_timing_delta"],
            r["real_ratio"],
            r["modern_ratio"],
            r["full_ratio"],
        ),
        reverse=True,
    )
    return {
        "overlay_strategy": overlay_strategy,
        "base_family": bases[0]["strategy"] if bases else None,
        "base_count": len(bases),
        "candidate_count": len(candidates),
        "thresholds": {
            "min_full_retention": min_full_retention,
            "min_real_retention": min_real_retention,
            "min_modern_retention": min_modern_retention,
        },
        "rows": rows,
    }


def _format_table(matrix: dict[str, Any], *, top_n: int) -> str:
    lines = [
        f"OVERLAY MATRIX: {matrix['overlay_strategy']}",
        "=" * 96,
        "base | cand | pass | dTiming | dMarker | fullR | realR | modernR | overlay full/real/modern",
    ]
    for row in matrix["rows"][:top_n]:
        om = row["overlay_metrics"]
        lines.append(
            f"{row['base_name'][:22]:22s} | "
            f"{row['candidate_rank']:>4} | "
            f"{'yes' if row['survives'] else 'no ':3s} | "
            f"{row['marker_timing_delta']:>7.4f} | "
            f"{row['marker_score_delta']:>7.4f} | "
            f"{row['full_ratio']:>5.2f} | "
            f"{row['real_ratio']:>5.2f} | "
            f"{row['modern_ratio']:>7.2f} | "
            f"{om['share_multiple']:.2f}/{om['real_share_multiple']:.2f}/{om['modern_share_multiple']:.2f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, help="overlay strategy, e.g. gc_vjatr_reclaimer")
    parser.add_argument("--grid", default=None, help="grid_search JSON to source overlay candidates")
    parser.add_argument("--params-json", default=None, help="explicit overlay params JSON")
    parser.add_argument("--base-family", default="gc_vjatr")
    parser.add_argument("--top-bases", type=int, default=6)
    parser.add_argument("--top-candidates", type=int, default=8)
    parser.add_argument("--min-full-retention", type=float, default=0.80)
    parser.add_argument("--min-real-retention", type=float, default=0.95)
    parser.add_argument("--min-modern-retention", type=float, default=0.95)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    bases = load_gold_bases(family=args.base_family, top_n=args.top_bases)
    candidates = load_overlay_candidates(
        overlay_strategy=args.overlay,
        grid_path=args.grid,
        params_json=args.params_json,
        limit=args.top_candidates,
    )
    matrix = build_matrix(
        overlay_strategy=args.overlay,
        candidates=candidates,
        bases=bases,
        min_real_retention=args.min_real_retention,
        min_modern_retention=args.min_modern_retention,
        min_full_retention=args.min_full_retention,
    )
    print(_format_table(matrix, top_n=min(30, len(matrix["rows"]))))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(matrix, f, indent=2)
        print(f"\n[overlay-matrix] wrote {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Autopsy near-miss strategy families that fail the Gold economic contract.

This is a research diagnostic. It answers why a family is not Gold-ready by
showing all-era economics, named-window damage, annual damage, marker misses,
and timing diversity versus current Gold anchors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import get_tecl_data
from diagnostics.champion_error_atlas import build_error_atlas
from diagnostics.diversity_prefilter_search import (
    build_anchor_profiles,
    diversity_against_anchors,
    load_anchor_rows,
)
from engine.strategy_engine import Indicators, backtest
from search.fitness import weighted_era_fitness
from search.grid_search import GRIDS, _grid_combos, _is_valid_combo
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import candidate_risk_state_from_trades, marker_target_from_df, score_marker_alignment
from validation.candidate import analyze_named_windows


DEFAULT_TARGETS = [
    "vol_calm_regime",
    "vj_or_slope_meta",
    "rsi_regime_canonical",
    "atr_ratio_vix",
]


def _run_strategy(df: pd.DataFrame, ind: Indicators, strategy: str, params: dict[str, Any]):
    fn = STRATEGY_REGISTRY[strategy]
    entries, exits, labels = fn(ind, params)
    return backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy,
    )


def _best_grid_candidate(df: pd.DataFrame, ind: Indicators, strategy: str) -> dict[str, Any]:
    if strategy not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {strategy}")
    grid = GRIDS.get(strategy)
    if not grid:
        raise KeyError(f"no grid for strategy: {strategy}")

    best = None
    evaluated = 0
    for params in _grid_combos(grid):
        if not _is_valid_combo(strategy, params):
            continue
        evaluated += 1
        result = _run_strategy(df, ind, strategy, params)
        wfit = weighted_era_fitness(
            result.share_multiple,
            result.real_share_multiple,
            result.modern_share_multiple,
        )
        row = {
            "strategy": strategy,
            "params": params,
            "weighted_era_fitness": float(wfit),
            "result": result,
        }
        if best is None or row["weighted_era_fitness"] > best["weighted_era_fitness"]:
            best = row
    if best is None:
        raise ValueError(f"no valid grid combos for {strategy}")
    best["evaluated_grid_combos"] = evaluated
    return best


def _date_at(df: pd.DataFrame, bar: int | None) -> str | None:
    if bar is None or bar < 0 or bar >= len(df):
        return None
    return str(pd.to_datetime(df["date"].iloc[int(bar)]).date())


def _annual_damage(df: pd.DataFrame, result, state: np.ndarray, *, min_year: int = 2009) -> list[dict[str, Any]]:
    dates = pd.to_datetime(df["date"])
    close = df["close"].values.astype(float)
    rows = []
    for year in sorted(set(int(y) for y in dates.dt.year)):
        if year < min_year:
            continue
        idx = np.where(dates.dt.year.values == year)[0]
        if len(idx) < 30:
            continue
        start = int(idx[0])
        end = int(idx[-1])
        eq0 = float(result.equity_curve[start])
        eq1 = float(result.equity_curve[end])
        p0 = float(close[start])
        p1 = float(close[end])
        if eq0 <= 0 or p0 <= 0:
            continue
        strategy_return = eq1 / eq0 - 1.0
        bah_return = p1 / p0 - 1.0
        share_multiple = (eq1 / eq0) / (p1 / p0) if p1 > 0 else 0.0
        rows.append(
            {
                "year": year,
                "share_multiple": round(float(share_multiple), 4),
                "strategy_return_pct": round(float(strategy_return * 100), 2),
                "bah_return_pct": round(float(bah_return * 100), 2),
                "risk_on_exposure": round(float(np.mean(state[start : end + 1])), 4),
            }
        )
    return sorted(rows, key=lambda row: row["share_multiple"])


def _trade_preview(trades: list, *, limit: int = 8) -> dict[str, Any]:
    worst = sorted(trades, key=lambda trade: float(trade.pnl_pct))[:limit]
    recent = sorted(trades, key=lambda trade: int(trade.entry_bar), reverse=True)[:limit]
    return {
        "worst_trades": [
            {
                "entry_date": trade.entry_date,
                "exit_date": trade.exit_date,
                "pnl_pct": round(float(trade.pnl_pct), 2),
                "bars_held": int(trade.bars_held),
                "exit_reason": trade.exit_reason,
            }
            for trade in worst
        ],
        "recent_trades": [
            {
                "entry_date": trade.entry_date,
                "exit_date": trade.exit_date,
                "pnl_pct": round(float(trade.pnl_pct), 2),
                "bars_held": int(trade.bars_held),
                "exit_reason": trade.exit_reason,
            }
            for trade in recent
        ],
    }


def _gold_contract_failures(result) -> list[str]:
    failures = []
    if result.share_multiple < 1.0:
        failures.append("full_history_below_bh")
    if result.real_share_multiple < 1.0:
        failures.append("real_era_below_bh")
    if result.modern_share_multiple < 1.0:
        failures.append("modern_era_below_bh")
    return failures


def _compact_named_windows(named: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for row in named.get("results", []):
        out.append(
            {
                "window": row.get("window"),
                "share_multiple": row.get("share_multiple"),
                "trades": row.get("trades"),
                "max_dd": row.get("max_dd"),
                "cagr": row.get("cagr"),
                "regime_score": row.get("regime_score"),
                "warning": bool(row.get("share_multiple", 0) < 1.0) if not row.get("error") else True,
                "error": row.get("error"),
            }
        )
    return sorted(out, key=lambda item: float(item.get("share_multiple") or 0.0))


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def build_autopsy(strategy: str, df: pd.DataFrame, ind: Indicators, anchors: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = _best_grid_candidate(df, ind, strategy)
    params = candidate["params"]
    result = candidate["result"]
    state = candidate_risk_state_from_trades(len(df), result.trades)
    marker_target = marker_target_from_df(df)
    marker = score_marker_alignment(df, result.trades, target=marker_target)
    anchor_profiles = build_anchor_profiles(df, ind, anchors)
    diversity = diversity_against_anchors(
        result,
        n_bars=len(df),
        anchors=anchor_profiles,
        tolerance=5,
    )
    named = analyze_named_windows(df, STRATEGY_REGISTRY[strategy], params, strategy)
    atlas = build_error_atlas(strategy, params, df, tolerance_bars=30, min_mismatch_bars=20)

    return {
        "strategy": strategy,
        "params": params,
        "evaluated_grid_combos": candidate["evaluated_grid_combos"],
        "gold_contract_failures": _gold_contract_failures(result),
        "metrics": {
            "weighted_era_fitness": round(float(candidate["weighted_era_fitness"]), 4),
            "share_multiple": round(float(result.share_multiple), 4),
            "real_share_multiple": round(float(result.real_share_multiple), 4),
            "modern_share_multiple": round(float(result.modern_share_multiple), 4),
            "trades": int(result.num_trades),
            "trades_per_year": float(result.trades_per_year),
            "max_drawdown_pct": round(float(result.max_drawdown_pct), 2),
            "cagr_pct": round(float(result.cagr_pct), 2),
            "exposure_pct": round(float(result.exposure_pct), 2),
            "exit_reasons": result.exit_reasons,
        },
        "named_windows": {
            "verdict": named.get("verdict"),
            "warnings": named.get("warnings", []),
            "results": _compact_named_windows(named),
        },
        "worst_years": _annual_damage(df, result, state)[:10],
        "marker": {
            "score": marker.get("score"),
            "state_accuracy": marker.get("state_accuracy"),
            "timing_magnitude_weighted": marker.get("timing_magnitude_weighted"),
            "transition_timing_score": marker.get("transition_timing_score"),
            "candidate_buy_count": marker.get("candidate_buy_count"),
            "candidate_sell_count": marker.get("candidate_sell_count"),
            "target_buy_count": marker.get("target_buy_count"),
            "target_sell_count": marker.get("target_sell_count"),
        },
        "worst_transition_misses": atlas["worst_transition_misses"][:10],
        "worst_state_mismatches": atlas["worst_state_mismatches"][:10],
        "diversity_vs_gold": diversity,
        "trade_preview": _trade_preview(result.trades),
    }


def build_report(targets: list[str]) -> dict[str, Any]:
    start = time.time()
    df = get_tecl_data()
    ind = Indicators(df)
    anchors = load_anchor_rows(None)
    rows = [build_autopsy(strategy, df, ind, anchors) for strategy in targets]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "targets": targets,
        "anchors": [
            {
                "name": row.get("display_name") or row.get("strategy"),
                "strategy": row.get("strategy"),
                "rank": row.get("leaderboard_rank"),
            }
            for row in anchors
        ],
        "elapsed_seconds": round(time.time() - start, 2),
        "autopsies": rows,
    }


def format_report(payload: dict[str, Any]) -> str:
    lines = [
        "NEAR-MISS AUTOPSY",
        "=" * 112,
        "Anchors: " + ", ".join(f"{a['name']} ({a['strategy']})" for a in payload["anchors"]),
        f"Targets: {', '.join(payload['targets'])}",
        "",
    ]
    for row in payload["autopsies"]:
        m = row["metrics"]
        d = row["diversity_vs_gold"]
        marker = row["marker"]
        lines.extend(
            [
                row["strategy"].upper(),
                "-" * 112,
                (
                    f"wfit={m['weighted_era_fitness']:.4f} full={m['share_multiple']:.4f} "
                    f"real={m['real_share_multiple']:.4f} modern={m['modern_share_multiple']:.4f} "
                    f"trades={m['trades']} tpy={m['trades_per_year']:.1f} "
                    f"maxDD={m['max_drawdown_pct']:.1f}%"
                ),
                f"Gold failures: {', '.join(row['gold_contract_failures']) or 'none'}",
                (
                    f"diversity={d['diversity_score']:.4f} max_corr={d['max_anchor_corr']:.4f} "
                    f"entry_overlap={d['max_entry_overlap']:.4f} exit_overlap={d['max_exit_overlap']:.4f}"
                ),
                (
                    f"marker={marker['score']:.4f} state={marker['state_accuracy']:.4f} "
                    f"timing_mag={marker['timing_magnitude_weighted']:.4f}"
                ),
                "params=" + json.dumps(row["params"], sort_keys=True),
                "",
                "Worst named windows:",
            ]
        )
        for window in row["named_windows"]["results"][:4]:
            lines.append(
                f"  {window['window']:<16} share={float(window.get('share_multiple') or 0):>6.3f} "
                f"trades={int(window.get('trades') or 0):>3} maxDD={float(window.get('max_dd') or 0):>5.1f}% "
                f"regime={float(window.get('regime_score') or 0):>5.3f}"
            )
        lines.append("Worst calendar years:")
        for year in row["worst_years"][:5]:
            lines.append(
                f"  {year['year']} share={year['share_multiple']:>6.3f} "
                f"strategy={year['strategy_return_pct']:>7.2f}% bh={year['bah_return_pct']:>7.2f}% "
                f"exposure={year['risk_on_exposure']:>5.1%}"
            )
        lines.append("Worst marker misses:")
        for miss in row["worst_transition_misses"][:5]:
            lines.append(
                f"  {miss['kind']:<4} {miss['target_date']} nearest={miss['nearest_date']} "
                f"dist={miss['distance_bars']} mag={miss['magnitude']} score={miss['score']}"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    parser.add_argument("--output", default="runs/near_miss_autopsy.json")
    args = parser.parse_args()

    targets = [item.strip() for item in args.targets.split(",") if item.strip()]
    payload = build_report(targets)
    print(format_report(payload))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(payload, f, indent=2, default=_json_default)
        print(f"\n[near-miss-autopsy] wrote {args.output}")


if __name__ == "__main__":
    main()

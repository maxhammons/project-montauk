#!/usr/bin/env python3
"""
Champion Error Atlas — marker-transition misses for a strategy.

This diagnostic is intentionally read-only. It runs a registered strategy,
scores it against TECL-markers.csv, and prints the largest timing misses and
state-mismatch windows so new hypotheses can target actual failure modes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import (
    candidate_risk_state_from_trades,
    marker_target_from_df,
    score_marker_alignment,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


def _default_candidate() -> tuple[str, dict]:
    with open(LEADERBOARD_PATH) as f:
        leaderboard = json.load(f)
    if not leaderboard:
        raise ValueError("leaderboard is empty")
    top = leaderboard[0]
    return top["strategy"], top.get("params", {})


def _date_at(df: pd.DataFrame, bar: int | None) -> str | None:
    if bar is None or bar < 0 or bar >= len(df):
        return None
    return str(pd.to_datetime(df["date"].iloc[bar]).date())


def _transition_kind(target: dict, bar: int) -> str:
    if bar in set(target["buy_bars"]):
        return "buy"
    if bar in set(target["sell_bars"]):
        return "sell"
    return "transition"


def _mismatch_windows(
    df: pd.DataFrame,
    target_state: np.ndarray,
    candidate_state: np.ndarray,
    overlap_start: int,
    overlap_end: int,
    *,
    min_bars: int,
) -> list[dict]:
    close = df["close"].values.astype(float)
    out = []
    i = overlap_start
    while i <= overlap_end:
        mismatch = bool(target_state[i]) != bool(candidate_state[i])
        if not mismatch:
            i += 1
            continue
        start = i
        while i <= overlap_end and bool(target_state[i]) != bool(candidate_state[i]):
            i += 1
        end = i - 1
        bars = end - start + 1
        if bars < min_bars:
            continue
        p0 = close[start]
        p1 = close[end]
        move_pct = (p1 / p0 - 1.0) * 100 if p0 > 0 else 0.0
        if target_state[start] and not candidate_state[start]:
            label = "missed_risk_on"
        elif candidate_state[start] and not target_state[start]:
            label = "exposed_risk_off"
        else:
            label = "state_mismatch"
        out.append(
            {
                "start_bar": int(start),
                "end_bar": int(end),
                "start_date": _date_at(df, start),
                "end_date": _date_at(df, end),
                "bars": int(bars),
                "type": label,
                "move_pct": round(float(move_pct), 2),
            }
        )
    return sorted(out, key=lambda x: (abs(x["move_pct"]), x["bars"]), reverse=True)


def build_error_atlas(
    strategy_name: str,
    params: dict,
    df: pd.DataFrame,
    *,
    tolerance_bars: int = 30,
    min_mismatch_bars: int = 10,
) -> dict:
    if strategy_name not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {strategy_name}")

    ind = Indicators(df)
    entries, exits, labels = STRATEGY_REGISTRY[strategy_name](ind, params)
    result = backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy_name,
    )
    alignment = score_marker_alignment(df, result.trades, tolerance_bars=tolerance_bars)
    target = marker_target_from_df(df)
    candidate_state = candidate_risk_state_from_trades(len(df), result.trades)

    transition_misses = []
    for match in alignment["magnitude_weighted_matches"]:
        target_bar = int(match["target_bar"])
        nearest_bar = match.get("nearest_bar")
        transition_misses.append(
            {
                "kind": _transition_kind(target, target_bar),
                "target_bar": target_bar,
                "target_date": _date_at(df, target_bar),
                "nearest_bar": nearest_bar,
                "nearest_date": _date_at(df, nearest_bar),
                "distance_bars": match.get("distance_bars"),
                "magnitude": match.get("magnitude"),
                "score": match.get("score"),
            }
        )
    transition_misses = sorted(
        transition_misses,
        key=lambda x: (
            float(x["score"] or 0.0),
            -float(x["magnitude"] or 0.0),
        ),
    )

    overlap_start = target["overlap_start"]
    overlap_end = target["overlap_end"]
    mismatches = []
    if overlap_start is not None and overlap_end is not None:
        mismatches = _mismatch_windows(
            df,
            target["state"],
            candidate_state,
            int(overlap_start),
            int(overlap_end),
            min_bars=min_mismatch_bars,
        )

    return {
        "strategy": strategy_name,
        "params": params,
        "summary": {
            "share_multiple": result.share_multiple,
            "real_share_multiple": result.real_share_multiple,
            "modern_share_multiple": result.modern_share_multiple,
            "trades": result.num_trades,
            "trades_per_year": result.trades_per_year,
            "max_drawdown_pct": result.max_drawdown_pct,
            "exit_reasons": result.exit_reasons,
        },
        "marker": {
            "score": alignment["score"],
            "state_accuracy": alignment["state_accuracy"],
            "timing_magnitude_weighted": alignment["timing_magnitude_weighted"],
            "transition_timing_score": alignment["transition_timing_score"],
            "target_buy_count": alignment["target_buy_count"],
            "target_sell_count": alignment["target_sell_count"],
            "candidate_buy_count": alignment["candidate_buy_count"],
            "candidate_sell_count": alignment["candidate_sell_count"],
        },
        "worst_transition_misses": transition_misses,
        "worst_state_mismatches": mismatches,
    }


def format_error_atlas(atlas: dict, *, top_n: int) -> str:
    s = atlas["summary"]
    m = atlas["marker"]
    lines = [
        f"ERROR ATLAS: {atlas['strategy']}",
        "=" * 72,
        (
            f"share={s['share_multiple']} real={s['real_share_multiple']} "
            f"modern={s['modern_share_multiple']} trades={s['trades']} "
            f"maxDD={s['max_drawdown_pct']}%"
        ),
        (
            f"marker_score={m['score']} state={m['state_accuracy']} "
            f"timing_mag={m['timing_magnitude_weighted']} "
            f"timing_raw={m['transition_timing_score']}"
        ),
        "",
        "WORST MARKER TRANSITION MISSES",
    ]
    for row in atlas["worst_transition_misses"][:top_n]:
        lines.append(
            f"  {row['kind']:4s} {row['target_date']} -> nearest {row['nearest_date']} "
            f"dist={row['distance_bars']} bars mag={row['magnitude']} score={row['score']}"
        )

    lines.extend(["", "WORST STATE MISMATCH WINDOWS"])
    for row in atlas["worst_state_mismatches"][:top_n]:
        lines.append(
            f"  {row['type']:16s} {row['start_date']} -> {row['end_date']} "
            f"bars={row['bars']} move={row['move_pct']:+.2f}%"
        )

    lines.extend(["", f"exit_reasons={s['exit_reasons']}"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", help="registered strategy name; defaults to leaderboard #1")
    parser.add_argument("--params-json", help="JSON object overriding/defaulting params")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()

    strategy_name, params = _default_candidate()
    if args.strategy:
        strategy_name = args.strategy
        params = {}
    if args.params_json:
        params.update(json.loads(args.params_json))

    df = get_tecl_data()
    atlas = build_error_atlas(strategy_name, params, df)
    if args.json:
        print(json.dumps(atlas, indent=2))
    else:
        print(format_error_atlas(atlas, top_n=args.top))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Profile why grid concepts fail the authority prefilter.

This is for research modules such as airbag/state-filter overlays where "0
charter-pass" hides whether the module is close, too trade-heavy, or simply
economically destructive.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import get_tecl_data
from engine.regime_helpers import score_regime_capture
from engine.strategy_engine import Indicators, backtest
from search.fitness import weighted_era_fitness
from search.grid_search import GRIDS, _grid_combos, _is_valid_combo
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import marker_target_from_df, score_marker_alignment


def _reasons(result, weighted_fit: float) -> list[str]:
    reasons = []
    if weighted_fit < 1.0:
        reasons.append("weighted_era_fitness<1")
    if result.share_multiple < 1.0:
        reasons.append("full<1")
    if result.real_share_multiple < 1.0:
        reasons.append("real<1")
    if result.modern_share_multiple < 1.0:
        reasons.append("modern<1")
    if result.num_trades < 5:
        reasons.append("trades<5")
    if result.trades_per_year > 5.0:
        reasons.append("trades_per_year>5")
    return reasons or ["authority_pass"]


def profile_concept(concept: str, *, limit: int) -> dict[str, Any]:
    if concept not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {concept}")
    grid = GRIDS.get(concept)
    if not grid:
        raise KeyError(f"no grid registered for: {concept}")

    df = get_tecl_data()
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    marker_target = marker_target_from_df(df)
    fn = STRATEGY_REGISTRY[concept]
    combos = [c for c in _grid_combos(grid) if _is_valid_combo(concept, c)]
    reason_counts: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    top_marker = []
    top_weighted = []

    for idx, params in enumerate(combos, start=1):
        if limit and idx > limit:
            break
        try:
            entries, exits, labels = fn(ind, params)
            result = backtest(
                df,
                entries,
                exits,
                labels,
                cooldown_bars=int(params.get("cooldown", 0)),
                strategy_name=concept,
            )
        except Exception as exc:  # noqa: BLE001
            reason_counts[f"exception:{type(exc).__name__}"] += 1
            continue
        wfit = weighted_era_fitness(
            result.share_multiple,
            result.real_share_multiple,
            result.modern_share_multiple,
        )
        reasons = _reasons(result, wfit)
        reason_counts.update(reasons)
        for a in reasons:
            for b in reasons:
                if a < b:
                    pairs[(a, b)] += 1
        result.regime_score = score_regime_capture(result.trades, close, dates)
        marker = score_marker_alignment(df, result.trades, target=marker_target)
        row = {
            "strategy": concept,
            "params": params,
            "reasons": reasons,
            "weighted_era_fitness": round(float(wfit), 4),
            "marker_score": marker.get("score"),
            "marker_timing": marker.get("timing_magnitude_weighted"),
            "metrics": {
                "share_multiple": round(float(result.share_multiple), 4),
                "real_share_multiple": round(float(result.real_share_multiple), 4),
                "modern_share_multiple": round(float(result.modern_share_multiple), 4),
                "trades": int(result.num_trades),
                "trades_per_year": round(float(result.trades_per_year), 4),
                "max_drawdown_pct": round(float(result.max_drawdown_pct), 4),
            },
        }
        top_marker.append(row)
        top_marker.sort(key=lambda x: float(x.get("marker_timing") or 0.0), reverse=True)
        del top_marker[20:]
        top_weighted.append(row)
        top_weighted.sort(key=lambda x: float(x["weighted_era_fitness"]), reverse=True)
        del top_weighted[20:]

    checked = min(len(combos), limit) if limit else len(combos)
    return {
        "concept": concept,
        "grid_combos": len(combos),
        "checked": checked,
        "reason_counts": dict(reason_counts.most_common()),
        "reason_pairs": {
            f"{a}+{b}": count
            for (a, b), count in pairs.most_common(20)
        },
        "top_by_marker_timing": top_marker,
        "top_by_weighted_era": top_weighted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concepts", required=True, help="comma-separated strategy names")
    parser.add_argument("--limit", type=int, default=0, help="max combos per concept; 0=all")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    results = [
        profile_concept(concept.strip(), limit=args.limit)
        for concept in args.concepts.split(",")
        if concept.strip()
    ]
    for item in results:
        print(f"\n{item['concept']} checked={item['checked']} / {item['grid_combos']}")
        for reason, count in item["reason_counts"].items():
            print(f"  {reason:<24} {count}")
        top = item["top_by_weighted_era"][:3]
        for row in top:
            m = row["metrics"]
            print(
                "  best_wfit "
                f"w={row['weighted_era_fitness']:.3f} "
                f"full={m['share_multiple']:.2f} real={m['real_share_multiple']:.2f} "
                f"modern={m['modern_share_multiple']:.2f} trades={m['trades']} "
                f"marker_timing={row['marker_timing']}"
            )
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump({"profiles": results}, f, indent=2)
        print(f"\n[rejection-profile] wrote {args.output}")


if __name__ == "__main__":
    main()

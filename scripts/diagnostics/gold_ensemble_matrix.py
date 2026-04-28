#!/usr/bin/env python3
"""Gold-only ensemble matrix.

This diagnostic builds simple vote ensembles from the current Gold leaderboard
rows. It does not admit anything to the leaderboard; it answers whether a
Gold-only ensemble is worth formalizing as a registered strategy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import combinations
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certify.contract import sync_entry_contract
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from search.fitness import weighted_era_fitness
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import candidate_risk_state_from_trades, score_marker_alignment


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def load_gold_rows() -> list[dict[str, Any]]:
    rows = []
    for rank, row in enumerate(_load_json(LEADERBOARD_PATH), start=1):
        synced = sync_entry_contract(dict(row))
        if synced.get("gold_status"):
            synced["leaderboard_rank"] = rank
            rows.append(synced)
    return rows


def select_default_shortlist(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Top row per family plus the strongest full-history Bonobo alternate."""
    selected: list[dict[str, Any]] = []
    seen_families: set[str] = set()
    for row in rows:
        family = row.get("strategy")
        if family not in seen_families:
            selected.append(row)
            seen_families.add(family)
    bonobos = [row for row in rows if row.get("strategy") == "gc_vjatr"]
    if bonobos:
        best_full = max(
            bonobos,
            key=lambda row: float((row.get("metrics") or {}).get("share_multiple") or 0.0),
        )
        if best_full not in selected:
            selected.append(best_full)
    return selected


def _run_row(df, row: dict[str, Any]) -> dict[str, Any]:
    strategy = row["strategy"]
    params = row.get("params") or {}
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
    return {
        "row": row,
        "state": candidate_risk_state_from_trades(len(df), result.trades),
        "result": result,
    }


def _events_from_state(state: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    entries = np.zeros(len(state), dtype=bool)
    exits = np.zeros(len(state), dtype=bool)
    labels = np.array([""] * len(state))
    for i in range(1, len(state)):
        if state[i] and not state[i - 1]:
            entries[i] = True
        elif state[i - 1] and not state[i]:
            exits[i] = True
            labels[i] = "VOTE"
    return entries, exits, labels


def _ensemble_state(
    member_runs: list[dict[str, Any]],
    *,
    mode: str,
    threshold: float,
) -> np.ndarray:
    states = np.asarray([run["state"].astype(float) for run in member_runs])
    if mode == "equal":
        scores = np.sum(states, axis=0)
        return scores >= threshold
    if mode == "confidence":
        weights = np.asarray(
            [
                float((run["row"].get("validation") or {}).get("composite_confidence") or 0.0)
                for run in member_runs
            ]
        )
    elif mode == "performance":
        weights = np.asarray(
            [float(run["row"].get("overall_performance_score") or run["row"].get("fitness") or 0.0) for run in member_runs]
        )
    else:
        raise ValueError(f"unknown ensemble mode: {mode}")
    if float(np.sum(weights)) <= 0.0:
        weights = np.ones(len(member_runs))
    weighted = np.sum(states * weights[:, None], axis=0) / float(np.sum(weights))
    return weighted >= threshold


def _metrics_from_result(result, marker: dict[str, Any]) -> dict[str, Any]:
    wfit = weighted_era_fitness(
        result.share_multiple,
        result.real_share_multiple,
        result.modern_share_multiple,
    )
    return {
        "fitness": round(float(wfit), 4),
        "share_multiple": round(float(result.share_multiple), 4),
        "real_share_multiple": round(float(result.real_share_multiple), 4),
        "modern_share_multiple": round(float(result.modern_share_multiple), 4),
        "trades": int(result.num_trades),
        "trades_per_year": round(float(result.trades_per_year), 4),
        "max_drawdown_pct": round(float(result.max_drawdown_pct), 4),
        "marker_score": marker.get("score"),
        "marker_timing": marker.get("timing_magnitude_weighted"),
    }


def build_matrix(*, shortlist_names: list[str] | None = None) -> dict[str, Any]:
    leaderboard = load_gold_rows()
    if not leaderboard:
        raise ValueError("no Gold rows found")
    if shortlist_names:
        wanted = {name.lower() for name in shortlist_names}
        shortlist = [
            row
            for row in leaderboard
            if str(row.get("display_name", "")).lower() in wanted
            or str(row.get("strategy", "")).lower() in wanted
        ]
    else:
        shortlist = select_default_shortlist(leaderboard)
    if len(shortlist) < 3:
        raise ValueError("need at least 3 Gold rows for an ensemble")

    df = get_tecl_data()
    runs = [_run_row(df, row) for row in shortlist]
    champion = leaderboard[0]
    champion_metrics = champion.get("metrics") or {}
    candidate_rows = []

    specs = []
    for size in (3, 4):
        if len(runs) < size:
            continue
        for combo in combinations(runs, size):
            specs.append((list(combo), "equal", 2.0 if size == 3 else 2.0, "2of3" if size == 3 else "2of4"))
            if size == 4:
                specs.append((list(combo), "equal", 3.0, "3of4"))
            for threshold in (0.50, 0.60, 0.67):
                specs.append((list(combo), "confidence", threshold, f"conf{threshold:.2f}"))
                specs.append((list(combo), "performance", threshold, f"perf{threshold:.2f}"))

    seen_specs: set[str] = set()
    for members, mode, threshold, label in specs:
        member_names = [run["row"].get("display_name") or run["row"].get("strategy") for run in members]
        sig = json.dumps([member_names, mode, threshold], sort_keys=True)
        if sig in seen_specs:
            continue
        seen_specs.add(sig)
        state = _ensemble_state(members, mode=mode, threshold=threshold)
        entries, exits, labels = _events_from_state(state)
        result = backtest(df, entries, exits, labels, strategy_name=f"gold_ensemble_{label}")
        marker = score_marker_alignment(df, result.trades)
        metrics = _metrics_from_result(result, marker)
        all_era_ok = (
            metrics["share_multiple"] >= 1.0
            and metrics["real_share_multiple"] >= 1.0
            and metrics["modern_share_multiple"] >= 1.0
        )
        candidate_rows.append(
            {
                "label": label,
                "mode": mode,
                "threshold": threshold,
                "members": member_names,
                "all_era_ok": all_era_ok,
                "metrics": metrics,
                "vs_champion": {
                    "full_ratio": round(
                        metrics["share_multiple"] / float(champion_metrics.get("share_multiple") or 1.0),
                        4,
                    ),
                    "real_ratio": round(
                        metrics["real_share_multiple"] / float(champion_metrics.get("real_share_multiple") or 1.0),
                        4,
                    ),
                    "modern_ratio": round(
                        metrics["modern_share_multiple"] / float(champion_metrics.get("modern_share_multiple") or 1.0),
                        4,
                    ),
                },
            }
        )

    candidate_rows.sort(
        key=lambda row: (
            row["all_era_ok"],
            row["metrics"]["fitness"],
            row["metrics"]["marker_timing"] or 0.0,
            -row["metrics"]["max_drawdown_pct"],
        ),
        reverse=True,
    )
    return {
        "champion": {
            "display_name": champion.get("display_name") or champion.get("strategy"),
            "strategy": champion.get("strategy"),
            "metrics": champion_metrics,
        },
        "shortlist": [
            {
                "rank": row.get("leaderboard_rank"),
                "display_name": row.get("display_name") or row.get("strategy"),
                "strategy": row.get("strategy"),
                "metrics": row.get("metrics"),
            }
            for row in shortlist
        ],
        "rows": candidate_rows,
    }


def format_matrix(matrix: dict[str, Any], *, top_n: int) -> str:
    champion = matrix["champion"]
    lines = [
        "GOLD ENSEMBLE MATRIX",
        "=" * 104,
        (
            f"Champion: {champion['display_name']} "
            f"full={float(champion['metrics'].get('share_multiple') or 0):.2f} "
            f"real={float(champion['metrics'].get('real_share_multiple') or 0):.2f} "
            f"modern={float(champion['metrics'].get('modern_share_multiple') or 0):.2f}"
        ),
        "Shortlist: " + ", ".join(row["display_name"] for row in matrix["shortlist"]),
        "",
        "label      mode        ok  fit    full  real modern trades marker  vsChamp full/real/modern  members",
    ]
    for row in matrix["rows"][:top_n]:
        m = row["metrics"]
        v = row["vs_champion"]
        lines.append(
            f"{row['label']:<10} {row['mode']:<11} {'yes' if row['all_era_ok'] else 'no ':3s} "
            f"{m['fitness']:>5.3f} {m['share_multiple']:>6.2f} {m['real_share_multiple']:>5.2f} "
            f"{m['modern_share_multiple']:>6.2f} {m['trades']:>6} "
            f"{float(m.get('marker_timing') or 0):>6.3f} "
            f"{v['full_ratio']:>5.2f}/{v['real_ratio']:>4.2f}/{v['modern_ratio']:>4.2f}  "
            f"{', '.join(row['members'])}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", default=None, help="comma-separated display names/strategy names")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    shortlist_names = [item.strip() for item in args.shortlist.split(",")] if args.shortlist else None
    matrix = build_matrix(shortlist_names=shortlist_names)
    print(format_matrix(matrix, top_n=args.top))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(matrix, f, indent=2)
        print(f"\n[gold-ensemble] wrote {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Diversity-first search over existing strategy grids.

This is a research search, not an admission path. It reuses `grid_search.GRIDS`
and the strategy registry, applies the normal all-era charter prefilter, then
ranks survivors by how different their risk-on/trade timing is from selected
Gold anchors.

Default anchors:
  - current #1 Gold row
  - `Ivory Hare`
  - top `gc_vjatr` row
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certify.contract import sync_entry_contract
from data.loader import get_tecl_data
from engine.regime_helpers import score_regime_capture
from engine.strategy_engine import Indicators, backtest
from search.evolve import _count_tunable_params, fitness as compute_fitness
from search.fitness import weighted_era_fitness
from search.grid_search import GRIDS, _grid_combos, _is_valid_combo
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
from strategies.markers import (
    candidate_risk_state_from_trades,
    marker_target_from_df,
    score_marker_alignment,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


DEFAULT_CONCEPTS = [
    "drawdown_recovery",
    "multi_tf_momentum",
    "rsi_mean_revert_trend",
    "vol_compression_breakout",
    "price_position_regime",
    "treasury_regime",
    "xlk_relative_momentum",
    "vix_regime_entry",
    "donchian_vix",
    "fed_macro_primary",
    "sgov_flight_switch",
    "vol_calm_regime",
    "keltner_squeeze_breakout",
    "vix_term_proxy",
    "macd_qqq_bull",
    "ensemble_vote_3of5",
]


DEFAULT_WEIGHTED_REJECT = "weighted_era_fitness_below_min"


_worker_df = None
_worker_ind = None
_worker_close = None
_worker_dates = None
_worker_marker_target = None
_worker_anchor_profiles = None
_worker_thresholds = None


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _trade_bars(trades: list, attr: str) -> list[int]:
    out = []
    for trade in trades:
        value = getattr(trade, attr, None)
        if value is not None and int(value) >= 0:
            out.append(int(value))
    return out


def _overlap(a: list[int], b: list[int], *, tolerance: int) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    def matched(source: list[int], target: list[int]) -> float:
        hits = 0
        arr = np.asarray(target, dtype=int)
        for bar in source:
            if np.any(np.abs(arr - int(bar)) <= tolerance):
                hits += 1
        return hits / len(source)

    return float((matched(a, b) + matched(b, a)) / 2.0)


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    af = a.astype(float)
    bf = b.astype(float)
    if np.std(af) == 0 or np.std(bf) == 0:
        return 0.0
    return float(np.corrcoef(af, bf)[0, 1])


def load_anchor_rows(anchor_names: list[str] | None = None) -> list[dict[str, Any]]:
    leaderboard = _load_json(LEADERBOARD_PATH)
    gold_rows = []
    for rank, row in enumerate(leaderboard, start=1):
        synced = sync_entry_contract(dict(row))
        if synced.get("gold_status"):
            synced["leaderboard_rank"] = rank
            gold_rows.append(synced)
    if anchor_names:
        wanted = [name.lower() for name in anchor_names]
        anchors = []
        for name in wanted:
            for row in gold_rows:
                if name == str(row.get("display_name", "")).lower() or name == str(row.get("strategy", "")).lower():
                    anchors.append(row)
                    break
        if anchors:
            return anchors

    anchors = [gold_rows[0]]
    for row in gold_rows:
        if str(row.get("display_name", "")).lower() == "ivory hare":
            anchors.append(row)
            break
    for row in gold_rows:
        if row.get("strategy") == "gc_vjatr":
            anchors.append(row)
            break
    seen = set()
    unique = []
    for row in anchors:
        key = (row.get("strategy"), json.dumps(row.get("params", {}), sort_keys=True))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _run_strategy(df, ind, strategy: str, params: dict[str, Any]):
    fn = STRATEGY_REGISTRY.get(strategy)
    if fn is None:
        raise KeyError(f"unknown strategy: {strategy}")
    entries, exits, labels = fn(ind, params)
    result = backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy,
    )
    return result


def _worker_init(
    anchor_rows: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> None:
    global _worker_df, _worker_ind, _worker_close, _worker_dates
    global _worker_marker_target, _worker_anchor_profiles, _worker_thresholds
    _worker_df = get_tecl_data()
    _worker_ind = Indicators(_worker_df)
    _worker_close = _worker_df["close"].values.astype(np.float64)
    _worker_dates = _worker_df["date"].values
    _worker_marker_target = marker_target_from_df(_worker_df)
    _worker_anchor_profiles = build_anchor_profiles(_worker_df, _worker_ind, anchor_rows)
    _worker_thresholds = thresholds


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def select_concepts(
    *,
    concepts: list[str],
    all_grids: bool,
    exclude_prefixes: list[str],
    exclude_concepts: list[str],
    max_combos_per_concept: int,
) -> list[str]:
    if all_grids:
        selected = sorted(GRIDS)
    else:
        selected = concepts

    excluded = set(exclude_concepts)
    out = []
    for concept in selected:
        if concept in excluded:
            continue
        if any(concept.startswith(prefix) for prefix in exclude_prefixes):
            continue
        grid = GRIDS.get(concept)
        if max_combos_per_concept > 0 and grid:
            combos = sum(1 for params in _grid_combos(grid) if _is_valid_combo(concept, params))
            if combos > max_combos_per_concept:
                continue
        out.append(concept)
    return out


def _near_miss_row(concept: str, params: dict[str, Any], result, wfit: float) -> dict[str, Any]:
    return {
        "strategy": concept,
        "weighted_era_fitness": round(float(wfit), 4),
        "params": params,
        "metrics": {
            "trades": int(result.num_trades),
            "trades_yr": float(result.trades_per_year),
            "share_multiple": round(float(result.share_multiple), 4),
            "real_share_multiple": round(float(result.real_share_multiple), 4),
            "modern_share_multiple": round(float(result.modern_share_multiple), 4),
            "max_dd": round(float(result.max_drawdown_pct), 4),
        },
    }


def _evaluate_job(job: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    concept, params = job
    try:
        result = _run_strategy(_worker_df, _worker_ind, concept, params)
    except Exception:
        return {"status": "reject", "reason": "exception", "concept": concept}
    wfit = weighted_era_fitness(
        result.share_multiple,
        result.real_share_multiple,
        result.modern_share_multiple,
    )
    if wfit < _worker_thresholds["min_weighted_era_fitness"]:
        return {
            "status": "reject",
            "reason": DEFAULT_WEIGHTED_REJECT,
            "concept": concept,
            "wfit": float(wfit),
            "near_miss": _near_miss_row(concept, params, result, wfit),
        }
    if result.num_trades < 5:
        return {"status": "reject", "reason": "trades<5", "concept": concept, "wfit": float(wfit)}
    if result.trades_per_year > 5.0:
        return {"status": "reject", "reason": "trades_per_year>5", "concept": concept, "wfit": float(wfit)}
    diversity = diversity_against_anchors(
        result,
        n_bars=len(_worker_df),
        anchors=_worker_anchor_profiles,
        tolerance=_worker_thresholds["tolerance"],
    )
    if (
        diversity["max_anchor_corr"] > _worker_thresholds["max_anchor_corr"]
        or diversity["max_entry_overlap"] > _worker_thresholds["max_entry_overlap"]
        or diversity["max_exit_overlap"] > _worker_thresholds["max_exit_overlap"]
        or diversity["diversity_score"] < _worker_thresholds["min_diversity_score"]
    ):
        return {"status": "reject", "reason": "diversity", "concept": concept, "wfit": float(wfit)}
    result.regime_score = score_regime_capture(result.trades, _worker_close, _worker_dates)
    align = score_marker_alignment(_worker_df, result.trades, target=_worker_marker_target)
    return {
        "status": "pass",
        "concept": concept,
        "wfit": float(wfit),
        "row": _candidate_entry(
            concept=concept,
            params=params,
            result=result,
            align=align,
            diversity=diversity,
        ),
    }


def build_anchor_profiles(df, ind, anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = []
    for row in anchors:
        result = _run_strategy(df, ind, row["strategy"], row.get("params") or {})
        profiles.append(
            {
                "name": row.get("display_name") or row["strategy"],
                "strategy": row["strategy"],
                "state": candidate_risk_state_from_trades(len(df), result.trades),
                "entry_bars": _trade_bars(result.trades, "entry_bar"),
                "exit_bars": _trade_bars(result.trades, "exit_bar"),
            }
        )
    return profiles


def diversity_against_anchors(
    result,
    *,
    n_bars: int,
    anchors: list[dict[str, Any]],
    tolerance: int,
) -> dict[str, Any]:
    state = candidate_risk_state_from_trades(n_bars, result.trades)
    entry_bars = _trade_bars(result.trades, "entry_bar")
    exit_bars = _trade_bars(result.trades, "exit_bar")
    rows = []
    for anchor in anchors:
        corr = _corr(state, anchor["state"])
        entry_overlap = _overlap(entry_bars, anchor["entry_bars"], tolerance=tolerance)
        exit_overlap = _overlap(exit_bars, anchor["exit_bars"], tolerance=tolerance)
        rows.append(
            {
                "anchor": anchor["name"],
                "risk_on_corr": round(corr, 4),
                "entry_overlap": round(entry_overlap, 4),
                "exit_overlap": round(exit_overlap, 4),
            }
        )
    max_corr = max((max(0.0, row["risk_on_corr"]) for row in rows), default=0.0)
    max_entry = max((row["entry_overlap"] for row in rows), default=0.0)
    max_exit = max((row["exit_overlap"] for row in rows), default=0.0)
    penalty = 0.60 * max_corr + 0.20 * max_entry + 0.20 * max_exit
    return {
        "diversity_score": round(max(0.0, 1.0 - penalty), 4),
        "max_anchor_corr": round(max_corr, 4),
        "max_entry_overlap": round(max_entry, 4),
        "max_exit_overlap": round(max_exit, 4),
        "anchors": rows,
    }


def _candidate_entry(
    *,
    concept: str,
    params: dict[str, Any],
    result,
    align: dict[str, Any],
    diversity: dict[str, Any],
) -> dict[str, Any]:
    result.regime_score = getattr(result, "regime_score", None)
    tier = STRATEGY_TIERS.get(concept, "T1")
    fit = compute_fitness(result, tier=tier)
    wfit = weighted_era_fitness(
        result.share_multiple,
        result.real_share_multiple,
        result.modern_share_multiple,
    )
    diversity_score = float(diversity["diversity_score"])
    return {
        "strategy": concept,
        "rank": 0,
        "fitness": fit,
        "weighted_era_fitness": round(float(wfit), 4),
        "diversity_adjusted_score": round(float(wfit) * (1.0 + diversity_score), 4),
        "tier": tier,
        "params": params,
        "marker_alignment_score": align["score"],
        "marker_alignment_detail": align,
        "diversity": diversity,
        "metrics": {
            "trades": int(result.num_trades),
            "trades_yr": float(result.trades_per_year),
            "n_params": _count_tunable_params(params),
            "share_multiple": round(float(result.share_multiple), 4),
            "real_share_multiple": round(float(result.real_share_multiple), 4),
            "modern_share_multiple": round(float(result.modern_share_multiple), 4),
            "max_dd": round(float(result.max_drawdown_pct), 4),
            "regime_score": result.regime_score.composite if result.regime_score else 0,
            "exit_reasons": result.exit_reasons,
        },
    }


def run_search(
    *,
    concepts: list[str],
    anchors: list[str] | None,
    min_weighted_era_fitness: float,
    max_anchor_corr: float,
    max_entry_overlap: float,
    max_exit_overlap: float,
    min_diversity_score: float,
    tolerance: int,
    top_n: int,
    progress_every: int,
    workers: int,
) -> dict[str, Any]:
    df = get_tecl_data()
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    marker_target = marker_target_from_df(df)
    anchor_rows = load_anchor_rows(anchors)
    anchor_profiles = build_anchor_profiles(df, ind, anchor_rows)

    jobs = []
    concept_counts: dict[str, int] = {}
    for concept in concepts:
        grid = GRIDS.get(concept)
        if not grid:
            print(f"[diversity-search] skip {concept}: no grid")
            continue
        if concept not in STRATEGY_REGISTRY:
            print(f"[diversity-search] skip {concept}: not in registry")
            continue
        combos = [params for params in _grid_combos(grid) if _is_valid_combo(concept, params)]
        concept_counts[concept] = len(combos)
        print(f"  {concept:<28} {len(combos):>5} combos")
        jobs.extend((concept, params) for params in combos)

    start = time.time()
    rows = []
    rejects = {
        "exception": 0,
        DEFAULT_WEIGHTED_REJECT: 0,
        "trades<5": 0,
        "trades_per_year>5": 0,
        "diversity": 0,
    }
    concept_survivors: dict[str, int] = {}
    concept_best_wfit: dict[str, float] = {}
    near_misses: list[dict[str, Any]] = []
    thresholds = {
        "min_weighted_era_fitness": min_weighted_era_fitness,
        "max_anchor_corr": max_anchor_corr,
        "max_entry_overlap": max_entry_overlap,
        "max_exit_overlap": max_exit_overlap,
        "min_diversity_score": min_diversity_score,
        "tolerance": tolerance,
    }

    def _consume(idx: int, payload: dict[str, Any]) -> None:
        concept = payload.get("concept", "?")
        wfit = float(payload.get("wfit") or 0.0)
        concept_best_wfit[concept] = max(concept_best_wfit.get(concept, 0.0), float(wfit))
        if payload.get("status") == "pass":
            rows.append(payload["row"])
            concept_survivors[concept] = concept_survivors.get(concept, 0) + 1
        else:
            reason = str(payload.get("reason") or "exception")
            rejects[reason] = rejects.get(reason, 0) + 1
        if payload.get("near_miss"):
            near_misses.append(payload["near_miss"])
            near_misses.sort(key=lambda row: row["weighted_era_fitness"], reverse=True)
            del near_misses[50:]
        if progress_every > 0 and idx % progress_every == 0:
            elapsed = time.time() - start
            print(
                f"[diversity-search] progress {idx}/{len(jobs)} "
                f"pass={len(rows)} elapsed={elapsed:.1f}s",
                flush=True,
            )

    if workers > 1 and len(jobs) > 1:
        n_workers = max(2, min(workers, multiprocessing.cpu_count(), len(jobs)))
        chunksize = max(4, min(64, len(jobs) // max(n_workers * 20, 1)))
        print(f"[diversity-search] Multicore: {n_workers} workers, chunksize={chunksize}")
        with multiprocessing.Pool(
            processes=n_workers,
            initializer=_worker_init,
            initargs=(anchor_rows, thresholds),
        ) as pool:
            for idx, payload in enumerate(pool.imap_unordered(_evaluate_job, jobs, chunksize=chunksize), start=1):
                _consume(idx, payload)
    else:
        global _worker_df, _worker_ind, _worker_close, _worker_dates
        global _worker_marker_target, _worker_anchor_profiles, _worker_thresholds
        _worker_df = df
        _worker_ind = ind
        _worker_close = close
        _worker_dates = dates
        _worker_marker_target = marker_target
        _worker_anchor_profiles = anchor_profiles
        _worker_thresholds = thresholds
        for idx, job in enumerate(jobs, start=1):
            _consume(idx, _evaluate_job(job))

    rows.sort(
        key=lambda row: (
            row["diversity_adjusted_score"],
            row["weighted_era_fitness"],
            row["diversity"]["diversity_score"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return {
        "concepts": concepts,
        "anchors": [
            {
                "name": row.get("display_name") or row.get("strategy"),
                "strategy": row.get("strategy"),
                "rank": row.get("leaderboard_rank"),
            }
            for row in anchor_rows
        ],
        "thresholds": {
            "min_weighted_era_fitness": min_weighted_era_fitness,
            "max_anchor_corr": max_anchor_corr,
            "max_entry_overlap": max_entry_overlap,
            "max_exit_overlap": max_exit_overlap,
            "min_diversity_score": min_diversity_score,
            "trade_overlap_tolerance_bars": tolerance,
        },
        "total_combos": len(jobs),
        "workers": workers,
        "survivors": len(rows),
        "rejects": rejects,
        "concept_summary": [
            {
                "strategy": concept,
                "combos": concept_counts.get(concept, 0),
                "survivors": concept_survivors.get(concept, 0),
                "best_weighted_era_fitness": round(concept_best_wfit.get(concept, 0.0), 4),
            }
            for concept in sorted(concept_counts)
        ],
        "near_misses": near_misses[:30],
        "rankings": rows[:top_n],
        "elapsed_seconds": round(time.time() - start, 2),
    }


def format_report(payload: dict[str, Any]) -> str:
    lines = [
        "DIVERSITY PREFILTER SEARCH",
        "=" * 104,
        "Anchors: " + ", ".join(f"{a['name']} ({a['strategy']})" for a in payload["anchors"]),
        f"Combos={payload['total_combos']} survivors={payload['survivors']} rejects={payload['rejects']}",
        "",
        "rank strategy                    score  wfit  div  corr entry exit  full real modern trades marker",
    ]
    for row in payload["rankings"][:30]:
        m = row["metrics"]
        d = row["diversity"]
        detail = row.get("marker_alignment_detail") or {}
        lines.append(
            f"{row['rank']:>4} {row['strategy']:<27} "
            f"{row['diversity_adjusted_score']:>5.3f} {row['weighted_era_fitness']:>5.3f} "
            f"{d['diversity_score']:>4.2f} {d['max_anchor_corr']:>5.2f} "
            f"{d['max_entry_overlap']:>5.2f} {d['max_exit_overlap']:>4.2f} "
            f"{m['share_multiple']:>5.2f} {m['real_share_multiple']:>4.2f} "
            f"{m['modern_share_multiple']:>6.2f} {m['trades']:>6} "
            f"{float(detail.get('timing_magnitude_weighted') or 0.0):>6.3f}"
        )
    if not payload["rankings"] and payload.get("near_misses"):
        lines.extend(["", "TOP ECONOMIC NEAR MISSES"])
        for row in payload["near_misses"][:15]:
            m = row["metrics"]
            lines.append(
                f"  {row['strategy']:<27} wfit={row['weighted_era_fitness']:>5.3f} "
                f"full={m['share_multiple']:>5.2f} real={m['real_share_multiple']:>4.2f} "
                f"modern={m['modern_share_multiple']:>5.2f} trades={m['trades']:>4}"
            )
    if payload.get("concept_summary"):
        lines.extend(["", "BEST BY CONCEPT"])
        for row in sorted(
            payload["concept_summary"],
            key=lambda item: item["best_weighted_era_fitness"],
            reverse=True,
        )[:20]:
            lines.append(
                f"  {row['strategy']:<27} best_wfit={row['best_weighted_era_fitness']:>5.3f} "
                f"survivors={row['survivors']:>4}/{row['combos']}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concepts", default=",".join(DEFAULT_CONCEPTS))
    parser.add_argument("--all-grids", action="store_true", help="search all grids instead of --concepts")
    parser.add_argument("--exclude-prefix", default="", help="comma-separated strategy prefixes to skip")
    parser.add_argument("--exclude-concepts", default="", help="comma-separated exact strategy names to skip")
    parser.add_argument(
        "--max-combos-per-concept",
        type=int,
        default=0,
        help="skip concepts with more valid grid combos than this; 0 disables",
    )
    parser.add_argument("--anchors", default=None, help="comma-separated anchor display or strategy names")
    parser.add_argument("--min-weighted-era-fitness", type=float, default=1.0)
    parser.add_argument("--max-anchor-corr", type=float, default=0.85)
    parser.add_argument("--max-entry-overlap", type=float, default=0.85)
    parser.add_argument("--max-exit-overlap", type=float, default=0.85)
    parser.add_argument("--min-diversity-score", type=float, default=0.10)
    parser.add_argument("--trade-tolerance", type=int, default=5)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--progress-every", type=int, default=250)
    parser.add_argument("--workers", type=int, default=max(1, min(8, multiprocessing.cpu_count() - 1)))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    concepts = select_concepts(
        concepts=_split_csv(args.concepts),
        all_grids=args.all_grids,
        exclude_prefixes=_split_csv(args.exclude_prefix),
        exclude_concepts=_split_csv(args.exclude_concepts),
        max_combos_per_concept=args.max_combos_per_concept,
    )
    anchors = _split_csv(args.anchors) if args.anchors else None
    payload = run_search(
        concepts=concepts,
        anchors=anchors,
        min_weighted_era_fitness=args.min_weighted_era_fitness,
        max_anchor_corr=args.max_anchor_corr,
        max_entry_overlap=args.max_entry_overlap,
        max_exit_overlap=args.max_exit_overlap,
        min_diversity_score=args.min_diversity_score,
        tolerance=args.trade_tolerance,
        top_n=args.top,
        progress_every=args.progress_every,
        workers=args.workers,
    )
    print(format_report(payload))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[diversity-search] wrote {args.output}")


if __name__ == "__main__":
    main()

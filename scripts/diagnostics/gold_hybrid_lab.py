#!/usr/bin/env python3
"""Gold hybrid lab: rank entry/exit specialists and test hybrids.

This diagnostic keeps the hybrid research honest:

  * Only current Gold leaderboard rows are eligible as members.
  * Entry skill and exit skill are scored separately from marker transitions.
  * Hybrid params freeze the selected members explicitly; no strategy reads the
    leaderboard at runtime.

It does not admit anything to the leaderboard. Promising rows should be passed
through the normal validation/certification path before promotion.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certify.contract import sync_entry_contract
from data.loader import get_tecl_data
from engine.regime_helpers import score_regime_capture
from engine.strategy_engine import Indicators, backtest
from search.evolve import fitness as compute_fitness
from search.fitness import all_era_performance_score, weighted_era_fitness
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
from strategies.markers import score_marker_alignment
from validation.pipeline import run_validation_pipeline


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "runs", "gold_hybrid_lab.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def _mean_match_score(matches: list[dict[str, Any]]) -> float:
    if not matches:
        return 0.0
    return float(np.mean([_safe_float(match.get("score")) for match in matches]))


def load_gold_rows(*, top_n: int | None = None) -> list[dict[str, Any]]:
    rows = []
    for rank, row in enumerate(_load_json(LEADERBOARD_PATH), start=1):
        synced = sync_entry_contract(dict(row))
        if not synced.get("gold_status"):
            continue
        synced["leaderboard_rank"] = rank
        rows.append(synced)
        if top_n and len(rows) >= top_n:
            break
    return rows


def _slice_df(df: pd.DataFrame, start: str | None) -> pd.DataFrame:
    if start is None:
        return df.reset_index(drop=True)
    return df[df["date"] >= start].reset_index(drop=True)


def _run_signals(df: pd.DataFrame, strategy: str, params: dict[str, Any]):
    if strategy not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {strategy}")
    ind = Indicators(df)
    return STRATEGY_REGISTRY[strategy](ind, params)


def _run_backtest(df: pd.DataFrame, strategy: str, params: dict[str, Any]):
    entries, exits, labels = _run_signals(df, strategy, params)
    return backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0) or 0),
        strategy_name=strategy,
    )


def _canonical_metrics(df: pd.DataFrame, strategy: str, params: dict[str, Any]) -> dict[str, Any]:
    full = _run_backtest(_slice_df(df, None), strategy, params)
    real = _run_backtest(_slice_df(df, "2008-12-17"), strategy, params)
    modern = _run_backtest(_slice_df(df, "2015-01-01"), strategy, params)
    marker = score_marker_alignment(df, full.trades)
    fitness = weighted_era_fitness(
        full.share_multiple,
        real.share_multiple,
        modern.share_multiple,
    )
    overall = all_era_performance_score(
        full.share_multiple,
        real.share_multiple,
        modern.share_multiple,
    )
    return {
        "fitness": round(float(fitness), 4),
        "overall_performance_score": round(float(overall), 4),
        "share_multiple": round(float(full.share_multiple), 4),
        "real_share_multiple": round(float(real.share_multiple), 4),
        "modern_share_multiple": round(float(modern.share_multiple), 4),
        "trades": int(full.num_trades),
        "trades_per_year": round(float(full.trades_per_year), 4),
        "max_drawdown_pct": round(float(full.max_drawdown_pct), 4),
        "marker_score": marker.get("score"),
        "marker_timing": marker.get("timing_magnitude_weighted"),
        "entry_timing": _mean_match_score(marker.get("buy_transition_matches") or []),
        "exit_timing": _mean_match_score(marker.get("sell_transition_matches") or []),
    }


def _count_leaf_params(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_leaf_params(v) for v in value.values())
    if isinstance(value, list):
        return sum(_count_leaf_params(v) for v in value)
    return 1


def _serialize_trades(trades) -> list[dict[str, Any]]:
    return [
        {
            "entry_bar": int(t.entry_bar),
            "exit_bar": int(t.exit_bar),
            "entry_date": t.entry_date,
            "exit_date": t.exit_date,
            "entry_price": float(t.entry_price),
            "exit_price": float(t.exit_price),
            "pnl_pct": float(t.pnl_pct),
            "bars_held": int(t.bars_held),
            "exit_reason": t.exit_reason,
        }
        for t in trades
    ]


def _raw_entry(df: pd.DataFrame, strategy: str, params: dict[str, Any], rank: int) -> dict[str, Any]:
    result = _run_backtest(df, strategy, params)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    result.params = params
    result.regime_score = score_regime_capture(result.trades, close, dates)
    marker = score_marker_alignment(df, result.trades)
    tier = STRATEGY_TIERS.get(strategy, "T2")
    fit = compute_fitness(result, tier=tier)
    return {
        "strategy": strategy,
        "rank": rank,
        "fitness": round(float(fit), 4),
        "tier": tier,
        "params": params,
        "marker_alignment_score": marker["score"],
        "marker_alignment_detail": marker,
        "metrics": {
            "trades": result.num_trades,
            "trades_yr": result.trades_per_year,
            "n_params": _count_leaf_params(params),
            "share_multiple": result.share_multiple,
            "real_share_multiple": result.real_share_multiple,
            "modern_share_multiple": result.modern_share_multiple,
            "cagr": result.cagr_pct,
            "max_dd": result.max_drawdown_pct,
            "mar": result.mar_ratio,
            "regime_score": result.regime_score.composite if result.regime_score else 0,
            "hhi": (result.regime_score.hhi or 0) if result.regime_score else 0,
            "bull_capture": result.regime_score.bull_capture_ratio if result.regime_score else 0,
            "bear_avoidance": result.regime_score.bear_avoidance_ratio if result.regime_score else 0,
            "win_rate": result.win_rate_pct,
            "exit_reasons": result.exit_reasons,
        },
        "trades": _serialize_trades(result.trades),
    }


def score_gold_row(df: pd.DataFrame, row: dict[str, Any]) -> dict[str, Any]:
    strategy = row["strategy"]
    params = row.get("params") or {}
    result = _run_backtest(df, strategy, params)
    marker = score_marker_alignment(df, result.trades)
    confidence = _safe_float((row.get("validation") or {}).get("composite_confidence"))
    metrics = row.get("metrics") or {}
    overall = _safe_float(row.get("overall_performance_score") or row.get("fitness"))
    drawdown = _safe_float(metrics.get("max_dd") or result.max_drawdown_pct, 100.0)
    drawdown_score = max(0.0, min(1.0, 1.0 - drawdown / 80.0))
    econ_score = max(0.0, min(1.0, overall / 4.0))
    entry_timing = _mean_match_score(marker.get("buy_transition_matches") or [])
    exit_timing = _mean_match_score(marker.get("sell_transition_matches") or [])
    entry_score = (
        0.55 * entry_timing
        + 0.20 * _safe_float(marker.get("recall"))
        + 0.15 * confidence
        + 0.10 * econ_score
    )
    exit_score = (
        0.55 * exit_timing
        + 0.20 * _safe_float(marker.get("precision"))
        + 0.15 * confidence
        + 0.10 * drawdown_score
    )
    return {
        "leaderboard_rank": row.get("leaderboard_rank"),
        "display_name": row.get("display_name") or strategy,
        "strategy": strategy,
        "params": params,
        "confidence": round(confidence, 4),
        "overall_performance_score": round(overall, 4),
        "metrics": metrics,
        "entry_score": round(float(entry_score), 4),
        "exit_score": round(float(exit_score), 4),
        "entry_timing": round(float(entry_timing), 4),
        "exit_timing": round(float(exit_timing), 4),
        "marker_score": marker.get("score"),
        "marker_timing": marker.get("timing_magnitude_weighted"),
        "candidate_buy_count": marker.get("candidate_buy_count"),
        "candidate_sell_count": marker.get("candidate_sell_count"),
    }


def _member_config(row: dict[str, Any], *, weight: float | None = None) -> dict[str, Any]:
    out = {
        "display_name": row.get("display_name"),
        "strategy": row["strategy"],
        "params": row.get("params") or {},
    }
    if weight is not None:
        out["weight"] = round(float(weight), 6)
    return out


def _row_weight(row: dict[str, Any]) -> float:
    confidence = _safe_float((row.get("validation") or {}).get("composite_confidence"), 0.5)
    performance = _safe_float(row.get("overall_performance_score") or row.get("fitness"), 1.0)
    return max(0.01, confidence * performance)


def _family_leaders(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    selected = []
    seen = set()
    for row in rows:
        family = row.get("strategy")
        if family in seen:
            continue
        seen.add(family)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _candidate(
    label: str,
    strategy: str,
    params: dict[str, Any],
    df: pd.DataFrame,
    champion: dict[str, Any],
) -> dict[str, Any]:
    metrics = _canonical_metrics(df, strategy, params)
    champ_metrics = champion.get("metrics") or {}
    all_era_ok = (
        metrics["share_multiple"] >= 1.0
        and metrics["real_share_multiple"] >= 1.0
        and metrics["modern_share_multiple"] >= 1.0
    )
    return {
        "label": label,
        "strategy": strategy,
        "params": params,
        "all_era_ok": all_era_ok,
        "metrics": metrics,
        "vs_champion": {
            "full_ratio": round(
                metrics["share_multiple"] / _safe_float(champ_metrics.get("share_multiple"), 1.0),
                4,
            ),
            "real_ratio": round(
                metrics["real_share_multiple"] / _safe_float(champ_metrics.get("real_share_multiple"), 1.0),
                4,
            ),
            "modern_ratio": round(
                metrics["modern_share_multiple"] / _safe_float(champ_metrics.get("modern_share_multiple"), 1.0),
                4,
            ),
        },
    }


def build_lab(*, top_n: int = 20, family_limit: int = 5) -> dict[str, Any]:
    rows = load_gold_rows(top_n=top_n)
    if len(rows) < 2:
        raise ValueError("need at least two Gold rows")

    df = get_tecl_data()
    skills = [score_gold_row(df, row) for row in rows]
    entry_board = sorted(skills, key=lambda row: row["entry_score"], reverse=True)
    exit_board = sorted(skills, key=lambda row: row["exit_score"], reverse=True)

    by_name = {row.get("display_name") or row["strategy"]: row for row in rows}
    entry_row = by_name[entry_board[0]["display_name"]]
    exit_row = by_name[exit_board[0]["display_name"]]
    champion = rows[0]
    families = _family_leaders(rows, limit=family_limit)

    switchboard_params = {
        "entry_strategy": entry_row["strategy"],
        "entry_params": entry_row.get("params") or {},
        "exit_strategy": exit_row["strategy"],
        "exit_params": exit_row.get("params") or {},
    }
    overlay_params = {
        "base_strategy": champion["strategy"],
        "base_params": champion.get("params") or {},
        "entry_strategy": entry_row["strategy"],
        "entry_params": entry_row.get("params") or {},
        "exit_strategy": exit_row["strategy"],
        "exit_params": exit_row.get("params") or {},
    }
    members = [_member_config(row, weight=_row_weight(row)) for row in families]

    candidates = [
        _candidate(
            "switchboard_top_entry_exit",
            "gold_hybrid_switchboard",
            switchboard_params,
            df,
            champion,
        ),
        _candidate(
            "champion_overlay_top_entry_exit",
            "gold_hybrid_champion_overlay",
            overlay_params,
            df,
            champion,
        ),
    ]
    for threshold in (0.50, 0.60, 0.67):
        candidates.append(
            _candidate(
                f"family_committee_{threshold:.2f}",
                "gold_hybrid_committee",
                {"members": members, "threshold": threshold},
                df,
                champion,
            )
        )

    candidates.sort(
        key=lambda row: (
            row["all_era_ok"],
            row["metrics"]["overall_performance_score"],
            row["metrics"]["fitness"],
            row["metrics"]["marker_timing"] or 0.0,
            -row["metrics"]["max_drawdown_pct"],
        ),
        reverse=True,
    )

    raw_rankings = [
        _raw_entry(df, row["strategy"], row["params"], rank)
        for rank, row in enumerate(candidates, start=1)
    ]

    return {
        "champion": {
            "display_name": champion.get("display_name") or champion.get("strategy"),
            "strategy": champion.get("strategy"),
            "metrics": champion.get("metrics") or {},
        },
        "entry_leaderboard": entry_board,
        "exit_leaderboard": exit_board,
        "family_members": members,
        "candidates": candidates,
        "raw_rankings": raw_rankings,
    }


def format_lab(lab: dict[str, Any], *, top_n: int) -> str:
    champion = lab["champion"]
    lines = [
        "GOLD HYBRID LAB",
        "=" * 112,
        (
            f"Champion: {champion['display_name']} "
            f"full={_safe_float(champion['metrics'].get('share_multiple')):.2f} "
            f"real={_safe_float(champion['metrics'].get('real_share_multiple')):.2f} "
            f"modern={_safe_float(champion['metrics'].get('modern_share_multiple')):.2f}"
        ),
        "",
        "ENTRY SPECIALISTS",
        "rank name                     entry  timing conf  full/real/modern",
    ]
    for idx, row in enumerate(lab["entry_leaderboard"][:top_n], start=1):
        m = row["metrics"]
        lines.append(
            f"{idx:>4} {row['display_name'][:24]:24s} "
            f"{row['entry_score']:.3f}  {row['entry_timing']:.3f}  {row['confidence']:.3f} "
            f"{_safe_float(m.get('share_multiple')):.2f}/"
            f"{_safe_float(m.get('real_share_multiple')):.2f}/"
            f"{_safe_float(m.get('modern_share_multiple')):.2f}"
        )
    lines.extend([
        "",
        "EXIT SPECIALISTS",
        "rank name                     exit   timing conf  full/real/modern",
    ])
    for idx, row in enumerate(lab["exit_leaderboard"][:top_n], start=1):
        m = row["metrics"]
        lines.append(
            f"{idx:>4} {row['display_name'][:24]:24s} "
            f"{row['exit_score']:.3f}  {row['exit_timing']:.3f}  {row['confidence']:.3f} "
            f"{_safe_float(m.get('share_multiple')):.2f}/"
            f"{_safe_float(m.get('real_share_multiple')):.2f}/"
            f"{_safe_float(m.get('modern_share_multiple')):.2f}"
        )
    lines.extend([
        "",
        "HYBRID CANDIDATES",
        "label                              ok  overall fit   full  real modern trades dd    marker vsChamp full/real/modern",
    ])
    for row in lab["candidates"]:
        m = row["metrics"]
        v = row["vs_champion"]
        lines.append(
            f"{row['label'][:34]:34s} {'yes' if row['all_era_ok'] else 'no ':3s} "
            f"{m['overall_performance_score']:>6.3f} {m['fitness']:>5.3f} "
            f"{m['share_multiple']:>6.2f} {m['real_share_multiple']:>5.2f} "
            f"{m['modern_share_multiple']:>6.2f} {m['trades']:>6} "
            f"{m['max_drawdown_pct']:>5.1f} {float(m.get('marker_timing') or 0):>6.3f} "
            f"{v['full_ratio']:>5.2f}/{v['real_ratio']:>4.2f}/{v['modern_ratio']:>4.2f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=8, help="Rows to show in entry/exit tables")
    parser.add_argument("--top-gold", type=int, default=20, help="Gold rows to evaluate")
    parser.add_argument("--family-limit", type=int, default=5, help="Top family leaders in committee")
    parser.add_argument("--validate", action="store_true", help="Run the quick validation pipeline on hybrid candidates")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    lab = build_lab(top_n=args.top_gold, family_limit=args.family_limit)
    if args.validate:
        validation = run_validation_pipeline(
            {"raw_rankings": lab["raw_rankings"]},
            hours=0.05,
            quick=True,
            top_n=len(lab["raw_rankings"]),
        )
        lab["validation"] = validation
        summary = validation.get("validation_summary") or {}
        print(
            "[gold-hybrid-lab] validation "
            f"PASS={summary.get('validated_pass')} "
            f"WARN={summary.get('validated_warn')} "
            f"FAIL={summary.get('validated_fail')}"
        )
    print(format_lab(lab, top_n=args.top))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(lab, f, indent=2)
        print(f"\n[gold-hybrid-lab] wrote {args.output}")


if __name__ == "__main__":
    main()

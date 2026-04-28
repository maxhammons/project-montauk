#!/usr/bin/env python3
"""Gold leaderboard diversity report.

This diagnostic treats `spike/leaderboard.json` as the authority set and asks
whether the Gold rows are genuinely different signals or mostly duplicates:

  - family concentration
  - risk-on state correlation / agreement
  - entry and exit overlap within a small bar tolerance
  - era-by-era strengths
  - direct comparison of a focus row, by default the newest timing-repair row
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
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import candidate_risk_state_from_trades, score_marker_alignment


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def load_gold_entries() -> list[dict[str, Any]]:
    entries = []
    for rank, row in enumerate(_load_json(LEADERBOARD_PATH), start=1):
        synced = sync_entry_contract(dict(row))
        if synced.get("gold_status"):
            synced["leaderboard_rank"] = rank
            entries.append(synced)
    return entries


def _trade_bars(trades: list, attr: str) -> list[int]:
    bars = []
    for trade in trades:
        value = getattr(trade, attr, None)
        if value is not None and int(value) >= 0:
            bars.append(int(value))
    return bars


def _overlap(a: list[int], b: list[int], *, tolerance: int) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    def matched(source: list[int], target: list[int]) -> float:
        hits = 0
        target_arr = np.asarray(target, dtype=int)
        for bar in source:
            if np.any(np.abs(target_arr - int(bar)) <= tolerance):
                hits += 1
        return hits / len(source)

    return round(float((matched(a, b) + matched(b, a)) / 2.0), 4)


def _risk_corr(a: np.ndarray, b: np.ndarray) -> float:
    af = a.astype(float)
    bf = b.astype(float)
    if np.std(af) == 0 or np.std(bf) == 0:
        return 0.0
    return round(float(np.corrcoef(af, bf)[0, 1]), 4)


def _run_entry(df, entry: dict[str, Any]) -> dict[str, Any]:
    strategy = entry["strategy"]
    params = entry.get("params") or {}
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
    state = candidate_risk_state_from_trades(len(df), result.trades)
    return {
        "entry": entry,
        "result": result,
        "state": state,
        "entry_bars": _trade_bars(result.trades, "entry_bar"),
        "exit_bars": _trade_bars(result.trades, "exit_bar"),
        "marker": marker,
    }


def _summary_for(run: dict[str, Any]) -> dict[str, Any]:
    entry = run["entry"]
    result = run["result"]
    metrics = entry.get("metrics") or {}
    validation = entry.get("validation") or {}
    marker = run["marker"]
    return {
        "rank": entry.get("leaderboard_rank"),
        "display_name": entry.get("display_name") or entry.get("strategy"),
        "strategy": entry.get("strategy"),
        "family_rank": entry.get("family_rank"),
        "confidence": validation.get("composite_confidence"),
        "fitness": entry.get("fitness"),
        "metrics": {
            "share_multiple": round(float(metrics.get("share_multiple", result.share_multiple)), 4),
            "real_share_multiple": round(float(metrics.get("real_share_multiple", result.real_share_multiple)), 4),
            "modern_share_multiple": round(float(metrics.get("modern_share_multiple", result.modern_share_multiple)), 4),
            "trades": int(metrics.get("trades", result.num_trades)),
            "max_drawdown_pct": round(float(metrics.get("max_dd", result.max_drawdown_pct)), 4),
            "recomputed_share_multiple": round(float(result.share_multiple), 4),
            "recomputed_real_share_multiple": round(float(result.real_share_multiple), 4),
            "recomputed_modern_share_multiple": round(float(result.modern_share_multiple), 4),
        },
        "marker": {
            "score": marker.get("score"),
            "timing_magnitude_weighted": marker.get("timing_magnitude_weighted"),
            "state_accuracy": marker.get("state_accuracy"),
        },
    }


def _pair_row(a: dict[str, Any], b: dict[str, Any], *, tolerance: int) -> dict[str, Any]:
    a_entry = a["entry"]
    b_entry = b["entry"]
    agreement = float(np.mean(a["state"] == b["state"]))
    both_on = int(np.sum(a["state"] & b["state"]))
    either_on = int(np.sum(a["state"] | b["state"]))
    return {
        "a_rank": a_entry.get("leaderboard_rank"),
        "a_name": a_entry.get("display_name") or a_entry.get("strategy"),
        "a_strategy": a_entry.get("strategy"),
        "b_rank": b_entry.get("leaderboard_rank"),
        "b_name": b_entry.get("display_name") or b_entry.get("strategy"),
        "b_strategy": b_entry.get("strategy"),
        "risk_on_corr": _risk_corr(a["state"], b["state"]),
        "state_agreement": round(agreement, 4),
        "jaccard_risk_on": round(both_on / either_on, 4) if either_on else 1.0,
        "entry_overlap": _overlap(a["entry_bars"], b["entry_bars"], tolerance=tolerance),
        "exit_overlap": _overlap(a["exit_bars"], b["exit_bars"], tolerance=tolerance),
        "trade_count_delta": abs(len(a["entry_bars"]) - len(b["entry_bars"])),
    }


def build_report(*, focus: str | None, tolerance: int) -> dict[str, Any]:
    entries = load_gold_entries()
    if not entries:
        raise ValueError("no Gold leaderboard entries found")

    df = get_tecl_data()
    runs = [_run_entry(df, entry) for entry in entries]
    summaries = [_summary_for(run) for run in runs]

    family_counts: dict[str, int] = {}
    for entry in entries:
        family = entry.get("strategy", "?")
        family_counts[family] = family_counts.get(family, 0) + 1
    total = len(entries)
    family_shares = {k: round(v / total, 4) for k, v in sorted(family_counts.items())}
    hhi = sum((v / total) ** 2 for v in family_counts.values())

    pairs = [
        _pair_row(a, b, tolerance=tolerance)
        for a, b in combinations(runs, 2)
    ]
    redundant_pairs = sorted(
        [
            pair
            for pair in pairs
            if pair["risk_on_corr"] >= 0.95
            and pair["entry_overlap"] >= 0.80
            and pair["exit_overlap"] >= 0.80
        ],
        key=lambda x: (x["risk_on_corr"], x["entry_overlap"], x["exit_overlap"]),
        reverse=True,
    )
    most_diverse_pairs = sorted(
        pairs,
        key=lambda x: (x["risk_on_corr"], x["entry_overlap"], x["exit_overlap"]),
    )

    focus_rows = []
    if focus:
        focus_lower = focus.lower()
        focus_runs = [
            run
            for run in runs
            if focus_lower in str(run["entry"].get("display_name", "")).lower()
            or focus_lower in str(run["entry"].get("strategy", "")).lower()
        ]
        if focus_runs:
            focus_run = focus_runs[0]
            focus_rows = sorted(
                [
                    _pair_row(focus_run, other, tolerance=tolerance)
                    for other in runs
                    if other is not focus_run
                ],
                key=lambda x: (x["risk_on_corr"], x["entry_overlap"], x["exit_overlap"]),
            )

    era_leaders = {}
    for key in ("share_multiple", "real_share_multiple", "modern_share_multiple"):
        era_leaders[key] = sorted(
            summaries,
            key=lambda row: float(row["metrics"].get(key) or 0.0),
            reverse=True,
        )[:3]

    return {
        "gold_rows": total,
        "family_concentration": {
            "counts": dict(sorted(family_counts.items())),
            "shares": family_shares,
            "hhi": round(float(hhi), 4),
            "effective_families": round(float(1.0 / hhi), 2) if hhi else 0.0,
        },
        "rows": summaries,
        "pairs": pairs,
        "redundant_pairs": redundant_pairs,
        "most_diverse_pairs": most_diverse_pairs[:10],
        "focus": focus,
        "focus_pairs": focus_rows,
        "era_leaders": era_leaders,
        "settings": {
            "trade_overlap_tolerance_bars": tolerance,
        },
    }


def format_report(report: dict[str, Any], *, top_pairs: int) -> str:
    fc = report["family_concentration"]
    lines = [
        "GOLD DIVERSITY REPORT",
        "=" * 88,
        f"Gold rows: {report['gold_rows']}",
        (
            "Family concentration: "
            f"HHI={fc['hhi']} effective_families={fc['effective_families']} "
            f"counts={fc['counts']}"
        ),
        "",
        "ROWS",
    ]
    for row in report["rows"]:
        m = row["metrics"]
        marker = row["marker"]
        lines.append(
            f"  #{row['rank']:>2} {row['display_name']:<20} {row['strategy']:<24} "
            f"full={m['share_multiple']:>6.2f} real={m['real_share_multiple']:>5.2f} "
            f"modern={m['modern_share_multiple']:>5.2f} trades={m['trades']:>3} "
            f"marker={float(marker.get('timing_magnitude_weighted') or 0):.3f}"
        )

    if report.get("focus_pairs"):
        lines.extend(["", f"FOCUS PAIRS: {report.get('focus')}"])
        for row in report["focus_pairs"][:top_pairs]:
            other = row["b_name"] if report["focus"].lower() in row["a_name"].lower() else row["a_name"]
            lines.append(
                f"  vs {other:<20} corr={row['risk_on_corr']:>6.3f} "
                f"agree={row['state_agreement']:>6.3f} entry={row['entry_overlap']:>5.2f} "
                f"exit={row['exit_overlap']:>5.2f}"
            )

    lines.extend(["", "MOST REDUNDANT PAIRS"])
    if report["redundant_pairs"]:
        rows = report["redundant_pairs"][:top_pairs]
    else:
        rows = sorted(
            report["pairs"],
            key=lambda x: (x["risk_on_corr"], x["entry_overlap"], x["exit_overlap"]),
            reverse=True,
        )[:top_pairs]
    for row in rows:
        lines.append(
            f"  {row['a_name']:<20} <> {row['b_name']:<20} "
            f"corr={row['risk_on_corr']:>6.3f} entry={row['entry_overlap']:>5.2f} "
            f"exit={row['exit_overlap']:>5.2f}"
        )

    lines.extend(["", "MOST DIVERSE PAIRS"])
    for row in report["most_diverse_pairs"][:top_pairs]:
        lines.append(
            f"  {row['a_name']:<20} <> {row['b_name']:<20} "
            f"corr={row['risk_on_corr']:>6.3f} entry={row['entry_overlap']:>5.2f} "
            f"exit={row['exit_overlap']:>5.2f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus", default="Ivory Hare")
    parser.add_argument("--trade-tolerance", type=int, default=5)
    parser.add_argument("--top-pairs", type=int, default=8)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    report = build_report(focus=args.focus, tolerance=args.trade_tolerance)
    print(format_report(report, top_pairs=args.top_pairs))
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[gold-diversity] wrote {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Chimera weight-grid sweep.

The Chimera committee (`chimera_v1_2026_05_26` :: `_static_gold_committee`) is a
weighted long/flat vote over a set of Gold member strategies: each member casts
its daily long/flat state, votes are weighted and summed, and the committee goes
long when the weighted share crosses ``threshold``.

This diagnostic asks: *are there better weight allocations than the certified
Chimera?* It holds the member set fixed and sweeps a grid of per-member weights
(including 0 = drop the member) and committee thresholds, backtests every
distinct resulting signal, and ranks the variants.

It is a **research diagnostic only** — it does not admit anything to the
leaderboard. A promising weight vector must still be frozen into a registered
Chimera snapshot and pushed through the normal validation/certification path
before it can become the active strategy.

Speed: each member's daily state is computed once and cached; many weight ratios
collapse to the same committee signal, so variants are deduped by their state
signature and only distinct signals are backtested.

Examples
--------
    # Sweep the current Chimera's 3 members over default weight levels.
    python scripts/diagnostics/chimera_weight_grid.py

    # Coarser/finer weight levels + thresholds, show top 30.
    python scripts/diagnostics/chimera_weight_grid.py \
        --weights 0,1,2,3,4 --thresholds 0.4,0.45,0.5,0.55,0.6 --top 30

    # Build the member set from the top-5 Gold family leaders instead.
    python scripts/diagnostics/chimera_weight_grid.py --from-gold 5
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from itertools import product
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from search.fitness import weighted_era_fitness
from strategies.library import (
    _events_to_state,
    _member_signals,
    _state_to_events,
)
from strategies.markers import score_marker_alignment

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "runs", "chimera_weight_grid.json")
CHIMERA_STRATEGY = "chimera_v1_2026_05_26"


def _load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def _params_key(strategy: str, params: dict[str, Any]) -> str:
    return strategy + "|" + json.dumps(params or {}, sort_keys=True, default=str)


def current_chimera_members() -> tuple[list[dict[str, Any]], float]:
    """Return (members, threshold) of the certified Chimera leaderboard row."""
    lb = _load_json(LEADERBOARD_PATH)
    rows = [e for e in lb if e.get("strategy") == CHIMERA_STRATEGY]
    if not rows:
        raise SystemExit(
            f"No {CHIMERA_STRATEGY} row found on the leaderboard — "
            "pass --from-gold N to build a member set instead."
        )
    params = rows[0].get("params") or {}
    members = list(params.get("members") or [])
    threshold = float(params.get("threshold", 0.5))
    return members, threshold


def gold_leader_members(n: int) -> list[dict[str, Any]]:
    """Build a member set from the top-N Gold family leaders (one per family)."""
    lb = _load_json(LEADERBOARD_PATH)
    leaders = [
        e
        for e in lb
        if e.get("family_leader") and e.get("strategy") != CHIMERA_STRATEGY
    ]
    leaders.sort(key=lambda e: float(e.get("montauk_score") or 0.0), reverse=True)
    members = []
    for e in leaders[:n]:
        members.append(
            {
                "display_name": e.get("display_name") or e.get("strategy"),
                "strategy": e["strategy"],
                "params": e.get("params") or {},
                "weight": 1.0,
            }
        )
    return members


def member_state(ind: Indicators, member: dict[str, Any]) -> np.ndarray:
    """Daily long/flat state for one member (cached by caller)."""
    entries, exits, _labels = _member_signals(
        ind, member["strategy"], member.get("params", {})
    )
    return _events_to_state(entries, exits).astype(float)


def committee_signal(
    states: np.ndarray, weights: np.ndarray, threshold: float
) -> np.ndarray:
    """Replicates `_static_gold_committee`: weighted long share >= threshold."""
    wsum = float(np.sum(weights))
    if wsum <= 0.0:
        return np.zeros(states.shape[1], dtype=bool)
    scores = np.sum(states * weights[:, None], axis=0) / wsum
    return scores >= threshold


def _normalize_weights(weights: tuple[float, ...]) -> tuple[int, ...]:
    """Integer-normalize a weight vector so equivalent ratios share one key."""
    nz = [w for w in weights if w > 0]
    if not nz:
        return tuple(0 for _ in weights)
    g = 0
    for w in nz:
        g = math.gcd(g, int(round(w)))
    g = g or 1
    return tuple(int(round(w)) // g for w in weights)


def evaluate_signal(df, state: np.ndarray) -> dict[str, Any]:
    entries, exits, labels = _state_to_events(state, "COM")
    result = backtest(
        df, entries, exits, labels, cooldown_bars=0, strategy_name=CHIMERA_STRATEGY
    )
    marker = score_marker_alignment(df, result.trades)
    fit = weighted_era_fitness(
        result.share_multiple,
        result.real_share_multiple,
        result.modern_share_multiple,
    )
    return {
        "fitness": round(float(fit), 4),
        "share_multiple": round(float(result.share_multiple), 4),
        "real_share_multiple": round(float(result.real_share_multiple), 4),
        "modern_share_multiple": round(float(result.modern_share_multiple), 4),
        "trades": int(result.num_trades),
        "trades_per_year": round(float(result.trades_per_year), 4),
        "max_drawdown_pct": round(float(result.max_drawdown_pct), 4),
        "marker_score": round(float(marker.get("score") or 0.0), 4),
        "marker_timing": round(float(marker.get("timing_magnitude_weighted") or 0.0), 4),
    }


def run_grid(
    members: list[dict[str, Any]],
    weight_levels: list[float],
    thresholds: list[float],
    *,
    baseline_threshold: float,
) -> dict[str, Any]:
    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)

    # Cache each distinct member's state array once.
    state_cache: dict[str, np.ndarray] = {}
    member_states = []
    for m in members:
        key = _params_key(m["strategy"], m.get("params", {}))
        if key not in state_cache:
            state_cache[key] = member_state(ind, m)
        member_states.append(state_cache[key])
    states = np.asarray(member_states)
    names = [m.get("display_name") or m["strategy"] for m in members]

    # Backtest cache keyed by the committee signal signature, so equivalent
    # weight ratios / thresholds that yield the same signal are scored once.
    signal_cache: dict[bytes, dict[str, Any]] = {}
    variants: list[dict[str, Any]] = []
    seen_configs: set[tuple] = set()

    for weights in product(weight_levels, repeat=len(members)):
        if not any(w > 0 for w in weights):
            continue
        norm = _normalize_weights(weights)
        warr = np.asarray(norm, dtype=float)
        for threshold in thresholds:
            cfg = (norm, round(float(threshold), 4))
            if cfg in seen_configs:
                continue
            seen_configs.add(cfg)
            state = committee_signal(states, warr, threshold)
            sig = np.packbits(state.astype(bool)).tobytes()
            metrics = signal_cache.get(sig)
            if metrics is None:
                if not state.any():
                    metrics = {"degenerate": "always_flat"}
                elif state.all():
                    metrics = {"degenerate": "always_long"}
                else:
                    metrics = evaluate_signal(df, state)
                signal_cache[sig] = metrics
            if "degenerate" in metrics:
                continue
            variants.append(
                {
                    "weights": list(norm),
                    "threshold": round(float(threshold), 4),
                    "metrics": metrics,
                }
            )

    # Certified baseline (the live Chimera weights) for comparison.
    base_weights = np.asarray(
        [float(m.get("weight", 1.0)) for m in members], dtype=float
    )
    base_state = committee_signal(states, base_weights, baseline_threshold)
    baseline = {
        "weights": [round(float(w), 4) for w in base_weights],
        "threshold": round(float(baseline_threshold), 4),
        "metrics": (
            evaluate_signal(df, base_state)
            if base_state.any() and not base_state.all()
            else {"degenerate": True}
        ),
    }

    variants.sort(key=lambda v: v["metrics"]["fitness"], reverse=True)
    return {
        "members": names,
        "member_strategies": [m["strategy"] for m in members],
        "weight_levels": weight_levels,
        "thresholds": thresholds,
        "configs_evaluated": len(seen_configs),
        "distinct_signals": len(signal_cache),
        "variants": variants,
        "baseline": baseline,
    }


def format_report(result: dict[str, Any], *, top_n: int) -> str:
    lines = []
    names = result["members"]
    lines.append("Chimera weight-grid sweep")
    lines.append(f"  members: {', '.join(names)}")
    lines.append(
        f"  configs={result['configs_evaluated']} "
        f"distinct_signals={result['distinct_signals']} "
        f"non_degenerate_variants={len(result['variants'])}"
    )
    b = result["baseline"]
    bm = b["metrics"]
    if "degenerate" not in bm:
        lines.append(
            f"  certified baseline: w={b['weights']} thr={b['threshold']} "
            f"-> fit={bm['fitness']} full={bm['share_multiple']} "
            f"real={bm['real_share_multiple']} modern={bm['modern_share_multiple']} "
            f"maxDD={bm['max_drawdown_pct']}% trades={bm['trades']}"
        )
    lines.append("")
    wcols = " ".join(f"w{i}" for i in range(len(names)))
    lines.append(
        f"  rank  {wcols:>{max(8, len(wcols))}}  thr   fit    full   real  modern "
        f"maxDD% trd  mark"
    )
    for i, v in enumerate(result["variants"][:top_n], start=1):
        m = v["metrics"]
        wstr = " ".join(f"{w:>2d}" for w in v["weights"])
        lines.append(
            f"  {i:>4d}  {wstr:>{max(8, len(wcols))}}  {v['threshold']:.2f}  "
            f"{m['fitness']:>5.3f} {m['share_multiple']:>6.2f} "
            f"{m['real_share_multiple']:>5.2f} {m['modern_share_multiple']:>6.2f} "
            f"{m['max_drawdown_pct']:>6.1f} {m['trades']:>3d} {m['marker_score']:>5.3f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--weights",
        default="0,1,2,3",
        help="Comma-separated per-member weight levels to sweep (default 0,1,2,3; 0 drops the member).",
    )
    parser.add_argument(
        "--thresholds",
        default="0.4,0.5,0.6",
        help="Comma-separated committee thresholds to sweep (default 0.4,0.5,0.6).",
    )
    parser.add_argument(
        "--from-gold",
        type=int,
        default=0,
        metavar="N",
        help="Build the member set from the top-N Gold family leaders instead of the certified Chimera members.",
    )
    parser.add_argument("--top", type=int, default=20, help="How many top variants to print.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Where to write the full results JSON.")
    parser.add_argument("--json", action="store_true", help="Print full JSON to stdout.")
    args = parser.parse_args(argv)

    weight_levels = [float(x) for x in args.weights.split(",") if x.strip() != ""]
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip() != ""]

    if args.from_gold > 0:
        members = gold_leader_members(args.from_gold)
        baseline_threshold = 0.5
        if not members:
            raise SystemExit("No Gold family leaders found to build a member set.")
    else:
        members, baseline_threshold = current_chimera_members()

    result = run_grid(
        members, weight_levels, thresholds, baseline_threshold=baseline_threshold
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result, top_n=args.top))
        print(f"\n[chimera-grid] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

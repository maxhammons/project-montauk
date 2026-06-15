#!/usr/bin/env python3
"""Chimera aggregation lab — experiment with how the committee combines votes.

The live Chimera (`chimera_v1_2026_05_26`) aggregates its members with a single
symmetric threshold on a weighted long-share. With three comparably-weighted
members and threshold 0.5 that reduces to a plain **2-of-3 majority vote**, and
the exact weights don't change any decision. This lab asks whether a *different
aggregation rule* over the same members does better — without touching the
leaderboard.

Mechanisms tested
-----------------
* **Symmetric threshold** — vary the long-share threshold (1-of-3 / 2-of-3 / 3-of-3).
* **Hysteresis (asymmetric)** — enter on one threshold, exit on a lower one, so
  the committee is "sticky" and resists whipsaws (or the reverse). This is the
  one mechanism that genuinely bites with correlated members.
* **Lopsided weights** — lean hard on one member so weights actually matter.

Each scheme is backtested and scored by the same era-weighted fitness the GA
uses, alongside drawdown / trades / marker, and compared to the live baseline.

Research only — emits no leaderboard changes.

Usage:
    python scripts/diagnostics/chimera_aggregation_lab.py
    python scripts/diagnostics/chimera_aggregation_lab.py --hysteresis-grid --top 25
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from data.loader import get_tecl_data  # noqa: E402
from engine.strategy_engine import Indicators  # noqa: E402
from diagnostics.chimera_weight_grid import (  # noqa: E402
    current_chimera_members,
    evaluate_signal,
    member_state,
)

DEFAULT_OUT = os.path.join(PROJECT_ROOT, "runs", "chimera_aggregation_lab.json")


def aggregate(states: np.ndarray, weights: np.ndarray, enter_thr: float, exit_thr: float) -> np.ndarray:
    """Hysteresis committee. enter_thr == exit_thr recovers a simple threshold.

    Daily weighted long-share crosses `enter_thr` to go long, and must fall to
    `exit_thr` (<= enter_thr) to go flat again. In between, the state holds.
    """
    wsum = float(np.sum(weights))
    if wsum <= 0.0:
        return np.zeros(states.shape[1], dtype=bool)
    score = np.sum(states * weights[:, None], axis=0) / wsum
    n = score.shape[0]
    out = np.zeros(n, dtype=bool)
    pos = False
    for i in range(n):
        if not pos and score[i] >= enter_thr:
            pos = True
        elif pos and score[i] <= exit_thr:
            pos = False
        out[i] = pos
    return out


# Count-boundary thresholds for an n-member equal-weight committee.
# Long-share == (#members long)/n, so a midpoint threshold cleanly maps to a
# member count: enter when count >= E uses (E-0.5)/n; exit when count <= X uses
# (X+0.5)/n. For n=3: {>=1: 0.167, >=2: 0.5, >=3: 0.833}.
def _enter_thr(count: int, n: int) -> float:
    return (count - 0.5) / n


def _exit_thr(count: int, n: int) -> float:
    return (count + 0.5) / n


def build_schemes(n_members: int, base_weights: np.ndarray, base_threshold: float) -> list[dict]:
    """Named aggregation schemes, parameterized by member counts (bug-proof)."""
    n = n_members
    eq = np.ones(n)
    E = lambda c: _enter_thr(c, n)  # noqa: E731 — terse local helpers
    X = lambda c: _exit_thr(c, n)   # noqa: E731
    schemes = [
        {"name": "LIVE baseline (weighted, thr 0.5)", "weights": base_weights, "enter": base_threshold, "exit": base_threshold},
        {"name": "equal majority (>=2)",  "weights": eq, "enter": E(2), "exit": X(1)},
        {"name": "any-long (>=1)",        "weights": eq, "enter": E(1), "exit": X(0)},
        {"name": "unanimous (>=3)",       "weights": eq, "enter": E(3), "exit": X(2)},
        # Hysteresis — sticky long (resist whipsaw): enter on agreement, exit late
        {"name": "sticky: enter>=2, exit on all-flat", "weights": eq, "enter": E(2), "exit": X(0)},
        {"name": "sticky: enter>=3, exit on all-flat", "weights": eq, "enter": E(3), "exit": X(0)},
        {"name": "sticky: enter>=3, exit on <=1",      "weights": eq, "enter": E(3), "exit": X(1)},
        # Hysteresis — twitchy (enter easily, exit fast): the opposite end
        {"name": "twitchy: enter>=1, exit on <=1",     "weights": eq, "enter": E(1), "exit": X(1)},
    ]
    return schemes


def lopsided_schemes(names: list[str], n_members: int) -> list[dict]:
    """Lean hard on each member in turn (dominant weight = sum of others + 1)."""
    out = []
    for i in range(n_members):
        w = np.ones(n_members)
        w[i] = float(n_members)  # dominates: its vote alone clears thr 0.5
        out.append({"name": f"lean on {names[i]} (dominant)", "weights": w, "enter": 0.5, "exit": 0.5})
    return out


def run(out_path: str, *, hysteresis_grid: bool, top: int) -> dict:
    members, base_threshold = current_chimera_members()
    base_weights = np.asarray([float(m.get("weight", 1.0)) for m in members], dtype=float)
    names = [m.get("display_name") or m["strategy"] for m in members]

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    states = np.asarray([member_state(ind, m) for m in members])

    schemes = build_schemes(len(members), base_weights, base_threshold)
    schemes += lopsided_schemes(names, len(members))

    if hysteresis_grid:
        n = len(members)
        # enter when count >= E, exit when count <= X, for all E>=1, X<E.
        for E in range(1, n + 1):
            for X in range(0, E):
                schemes.append({
                    "name": f"grid: enter>={E}, exit<={X}",
                    "weights": np.ones(n), "enter": _enter_thr(E, n), "exit": _exit_thr(X, n),
                })

    results = []
    baseline_fit = None
    for sc in schemes:
        state = aggregate(states, np.asarray(sc["weights"], dtype=float), sc["enter"], sc["exit"])
        if not state.any() or state.all():
            metrics = {"degenerate": "always_long" if state.all() else "always_flat"}
        else:
            metrics = evaluate_signal(df, state)
        row = {"name": sc["name"], "enter": sc["enter"], "exit": sc["exit"],
               "weights": [round(float(w), 3) for w in sc["weights"]], "metrics": metrics}
        results.append(row)
        if sc["name"].startswith("LIVE") and "fitness" in metrics:
            baseline_fit = metrics["fitness"]

    def sortkey(r):
        m = r["metrics"]
        return m.get("fitness", -1) if "degenerate" not in m else -1
    ranked = sorted(results, key=sortkey, reverse=True)

    out = {
        "members": names,
        "baseline_fitness": baseline_fit,
        "scheme_count": len(results),
        "results": ranked,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Chimera aggregation lab — members: {', '.join(names)}")
    print(f"baseline (LIVE) fitness = {baseline_fit}\n")
    hdr = f"  {'fit':>5} {'full':>7} {'real':>5} {'modern':>6} {'maxDD':>6} {'trd':>4}  Δfit   scheme"
    print(hdr)
    for r in ranked[:top]:
        m = r["metrics"]
        if "degenerate" in m:
            print(f"  {'--':>5} {'':>7} {'':>5} {'':>6} {'':>6} {'':>4}        {r['name']}  [{m['degenerate']}]")
            continue
        dfit = (m["fitness"] - baseline_fit) if baseline_fit is not None else 0.0
        flag = "+" if dfit > 0.0005 else (" " if abs(dfit) <= 0.0005 else "-")
        print(
            f"  {m['fitness']:>5.3f} {m['share_multiple']:>7.2f} {m['real_share_multiple']:>5.2f} "
            f"{m['modern_share_multiple']:>6.2f} {m['max_drawdown_pct']:>6.1f} {m['trades']:>4d} "
            f" {flag}{abs(dfit):.3f} {r['name']}"
        )
    print(f"\n[chimera-agg] wrote {out_path}  (research only — no leaderboard change)")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hysteresis-grid", action="store_true", help="Also sweep a full enter/exit threshold grid.")
    p.add_argument("--top", type=int, default=20, help="How many schemes to print.")
    p.add_argument("--out", default=DEFAULT_OUT)
    args = p.parse_args(argv)
    run(args.out, hysteresis_grid=args.hysteresis_grid, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

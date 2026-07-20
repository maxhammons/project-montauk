#!/usr/bin/env python3
"""Chimera v2 lab — two-stage full-Gold weighted index with hysteresis.

Chimera v1 (`chimera_v1_2026_05_26`) is a 3-member majority vote where the
weights are decorative (see `chimera_aggregation_lab.py`). This lab searches
the v2 design: an **index of every Gold row**, structured to respect the
board's family redundancy:

  Stage 1 (within family)  — each Gold family's variants vote; the family
      emits a fractional long-share (3 of 4 Bonobos long -> 0.75). Variant
      disagreement acts as a live parameter-sensitivity meter.
  Stage 2 (across families) — index score = sum(family_weight * family_share),
      with family weights proportional to the family's best Montauk Score
      (formula-derived, never free-fit). An equal-weight control runs beside it.
  Execution — hysteresis threshold pair on the continuous score: go long when
      score >= enter, flat again only when score <= exit. A small principled
      grid of enter/exit pairs is searched (~22 per weight scheme).

Every evaluated config is logged to `spike/hash-index.json` so selection-bias
deflation (N_eff) stays honest about this search.

Research only — emits no leaderboard changes. The winning config must be
frozen into a registered `chimera_v2_YYYY_MM_DD` snapshot and pushed through
the full validation/certification path before it can board.

Usage:
    python scripts/diagnostics/chimera_v2_lab.py
    python scripts/diagnostics/chimera_v2_lab.py --top 30 --no-hash-log
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from data.loader import get_tecl_data  # noqa: E402
from engine.strategy_engine import Indicators  # noqa: E402
from search.evolve import config_hash, load_hash_index, save_hash_index  # noqa: E402
from diagnostics.chimera_weight_grid import (  # noqa: E402
    _load_json,
    _params_key,
    committee_signal,
    current_chimera_members,
    evaluate_signal,
    member_state,
)

LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "runs", "chimera_v2_lab.json")
LAB_STRATEGY = "chimera_v2_two_stage"

# Small principled hysteresis grid: enter/exit pairs at 0.1 steps. exit == enter
# recovers a plain symmetric threshold; exit < enter is sticky-long hysteresis.
ENTER_LEVELS = [0.5, 0.6, 0.7, 0.8]
EXIT_LEVELS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def gold_families() -> list[dict[str, Any]]:
    """Group current non-Chimera Gold rows into families with Montauk weights."""
    lb = _load_json(LEADERBOARD_PATH)
    by_family: dict[str, list[dict[str, Any]]] = {}
    for e in lb:
        strategy = e.get("strategy") or ""
        if strategy.startswith("chimera"):
            continue
        if not e.get("gold_status"):
            continue
        by_family.setdefault(strategy, []).append(e)
    families = []
    for strategy, rows in sorted(by_family.items()):
        rows.sort(key=lambda e: float(e.get("montauk_score") or 0.0), reverse=True)
        families.append(
            {
                "family": strategy,
                "best_montauk": float(rows[0].get("montauk_score") or 0.0),
                "members": [
                    {
                        "display_name": e.get("display_name") or strategy,
                        "strategy": strategy,
                        "params": e.get("params") or {},
                    }
                    for e in rows
                ],
            }
        )
    if not families:
        raise SystemExit("No non-Chimera Gold rows found on the leaderboard.")
    return families


def family_shares(ind: Indicators, families: list[dict[str, Any]]) -> np.ndarray:
    """Stage 1: per-family fractional long-share series (families x bars)."""
    cache: dict[str, np.ndarray] = {}
    shares = []
    for fam in families:
        states = []
        for m in fam["members"]:
            key = _params_key(m["strategy"], m.get("params", {}))
            if key not in cache:
                cache[key] = member_state(ind, m)
            states.append(cache[key])
        shares.append(np.mean(np.asarray(states), axis=0))
    return np.asarray(shares)


def index_score(shares: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Stage 2: weighted index score in [0, 1]."""
    w = np.asarray(weights, dtype=float)
    return np.sum(shares * (w / float(np.sum(w)))[:, None], axis=0)


def hysteresis_state(score: np.ndarray, enter_thr: float, exit_thr: float) -> np.ndarray:
    """Long when score crosses `enter_thr`; flat again only at `exit_thr`."""
    out = np.zeros(score.shape[0], dtype=bool)
    pos = False
    for i in range(score.shape[0]):
        if not pos and score[i] >= enter_thr:
            pos = True
        elif pos and score[i] <= exit_thr:
            pos = False
        out[i] = pos
    return out


def frozen_params(
    families: list[dict[str, Any]],
    weights: np.ndarray,
    enter_thr: float,
    exit_thr: float,
) -> dict[str, Any]:
    """The literal params blob a `chimera_v2` library snapshot would freeze."""
    w = np.asarray(weights, dtype=float)
    w = w / float(np.sum(w))
    return {
        "families": [
            {
                "family": fam["family"],
                "weight": round(float(w[i]), 6),
                "members": [
                    {"strategy": m["strategy"], "params": m["params"]}
                    for m in fam["members"]
                ],
            }
            for i, fam in enumerate(families)
        ],
        "enter_threshold": enter_thr,
        "exit_threshold": exit_thr,
    }


def run(out_path: str, *, top: int, log_hashes: bool) -> dict:
    families = gold_families()
    fam_names = [f["family"] for f in families]
    montauk_w = np.asarray([f["best_montauk"] for f in families], dtype=float)
    equal_w = np.ones(len(families))

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    shares = family_shares(ind, families)

    schemes = [
        ("montauk", montauk_w),
        ("equal", equal_w),
    ]
    pairs = [(e, x) for e in ENTER_LEVELS for x in EXIT_LEVELS if x <= e]

    signal_cache: dict[bytes, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    hash_entries: dict[str, dict[str, Any]] = {}
    for scheme_name, weights in schemes:
        score = index_score(shares, weights)
        for enter_thr, exit_thr in pairs:
            state = hysteresis_state(score, enter_thr, exit_thr)
            sig = np.packbits(state).tobytes()
            metrics = signal_cache.get(sig)
            if metrics is None:
                if not state.any():
                    metrics = {"degenerate": "always_flat"}
                elif state.all():
                    metrics = {"degenerate": "always_long"}
                else:
                    metrics = evaluate_signal(df, state)
                signal_cache[sig] = metrics
            results.append(
                {
                    "scheme": scheme_name,
                    "enter": enter_thr,
                    "exit": exit_thr,
                    "metrics": metrics,
                }
            )
            if log_hashes and "degenerate" not in metrics:
                h = config_hash(
                    LAB_STRATEGY,
                    {"scheme": scheme_name, "enter": enter_thr, "exit": exit_thr},
                )
                hash_entries[h] = {
                    "bah": metrics["share_multiple"],
                    "real_bah": metrics["real_share_multiple"],
                    "modern_bah": metrics["modern_share_multiple"],
                    "rs": None,
                    "dd": metrics["max_drawdown_pct"],
                    "nt": metrics["trades"],
                    "np": 3,  # scheme + enter + exit
                }

    # Baseline: the certified Chimera v1 signal on current data.
    v1_members, v1_threshold = current_chimera_members()
    v1_states = np.asarray([member_state(ind, m) for m in v1_members])
    v1_weights = np.asarray([float(m.get("weight", 1.0)) for m in v1_members])
    v1_state = committee_signal(v1_states, v1_weights, v1_threshold)
    v1_metrics = (
        evaluate_signal(df, v1_state)
        if v1_state.any() and not v1_state.all()
        else {"degenerate": True}
    )

    def sortkey(r):
        m = r["metrics"]
        if "degenerate" in m:
            return (-1.0, 0.0)
        # Fitness first; lower drawdown breaks ties.
        return (m["fitness"], -m["max_drawdown_pct"])

    ranked = sorted(results, key=sortkey, reverse=True)
    best = ranked[0] if ranked and "degenerate" not in ranked[0]["metrics"] else None
    best_frozen = None
    if best is not None:
        best_w = montauk_w if best["scheme"] == "montauk" else equal_w
        best_frozen = frozen_params(families, best_w, best["enter"], best["exit"])

    if log_hashes and hash_entries:
        index = load_hash_index()
        new = {h: v for h, v in hash_entries.items() if h not in index}
        if new:
            index.update(new)
            save_hash_index(index)
        print(f"[chimera-v2] logged {len(new)} new configs to hash-index "
              f"({len(hash_entries) - len(new)} already present)")

    out = {
        "families": [
            {
                "family": f["family"],
                "rows": len(f["members"]),
                "best_montauk": round(f["best_montauk"], 4),
                "montauk_weight": round(float(montauk_w[i] / montauk_w.sum()), 4),
            }
            for i, f in enumerate(families)
        ],
        "grid": {"enter_levels": ENTER_LEVELS, "exit_levels": EXIT_LEVELS,
                 "pairs_per_scheme": len(pairs), "schemes": [s for s, _ in schemes]},
        "baseline_chimera_v1": v1_metrics,
        "configs_evaluated": len(results),
        "distinct_signals": len(signal_cache),
        "results": ranked,
        "best_frozen_params": best_frozen,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print("Chimera v2 lab — two-stage full-Gold weighted index")
    for row in out["families"]:
        print(f"  {row['family']}: {row['rows']} rows, best Montauk {row['best_montauk']}, "
              f"weight {row['montauk_weight']}")
    if "degenerate" not in v1_metrics:
        print(f"\n  Chimera v1 baseline: fit={v1_metrics['fitness']} "
              f"full={v1_metrics['share_multiple']} real={v1_metrics['real_share_multiple']} "
              f"modern={v1_metrics['modern_share_multiple']} "
              f"maxDD={v1_metrics['max_drawdown_pct']}% trades={v1_metrics['trades']}")
    base_fit = v1_metrics.get("fitness")
    print(f"\n  {'fit':>5} {'full':>7} {'real':>5} {'modern':>6} {'maxDD':>6} "
          f"{'trd':>4} {'t/yr':>5}  Δv1    scheme  enter/exit")
    for r in ranked[:top]:
        m = r["metrics"]
        if "degenerate" in m:
            print(f"  {'--':>5}  [{m['degenerate']}]  {r['scheme']} {r['enter']}/{r['exit']}")
            continue
        dfit = (m["fitness"] - base_fit) if base_fit is not None else 0.0
        flag = "+" if dfit > 0.0005 else (" " if abs(dfit) <= 0.0005 else "-")
        charter = "" if m["trades_per_year"] <= 5.0 else "  [!] >5 trades/yr"
        print(f"  {m['fitness']:>5.3f} {m['share_multiple']:>7.2f} "
              f"{m['real_share_multiple']:>5.2f} {m['modern_share_multiple']:>6.2f} "
              f"{m['max_drawdown_pct']:>6.1f} {m['trades']:>4d} {m['trades_per_year']:>5.2f} "
              f" {flag}{abs(dfit):.3f} {r['scheme']:>7}  {r['enter']:.1f}/{r['exit']:.1f}{charter}")
    print(f"\n[chimera-v2] wrote {out_path}  (research only — no leaderboard change)")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--top", type=int, default=25, help="How many configs to print.")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--no-hash-log", action="store_true",
                   help="Skip logging evaluated configs to spike/hash-index.json.")
    args = p.parse_args(argv)
    run(args.out, top=args.top, log_hashes=not args.no_hash_log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

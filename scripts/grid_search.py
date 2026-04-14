#!/usr/bin/env python3
"""
Grid Search — Exhaustive canonical-param search for T1 strategy concepts.

Instead of running a GA (which spends hours on random mutation/crossover),
this module backtests EVERY combo in a discrete canonical grid in seconds,
pre-filters by charter gates, then validates survivors through the full
tier-routed pipeline.

Usage:
    python3 scripts/grid_search.py                    # all concepts, all grids
    python3 scripts/grid_search.py --concepts golden_cross_slope,ema_slope_above
    python3 scripts/grid_search.py --dry-run           # just show combos + smoke test
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import score_regime_capture
from data import get_tecl_data
from discovery_markers import score_marker_alignment
from evolve import fitness as compute_fitness, _count_tunable_params, update_leaderboard, _Enc
from pine_generator import supports_pine_strategy
from strategies import STRATEGY_REGISTRY, STRATEGY_TIERS
from strategy_engine import Indicators, backtest
from validation.pipeline import run_validation_pipeline

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# Canonical grids — discrete canonical values to test for each concept.
# Every value must be from the strict canonical set (canonical_params.py).
# Total combos per concept shown in comments.
# ─────────────────────────────────────────────────────────────────────────────

GRIDS = {
    "golden_cross_slope": {                         # 4 × 3 × 2 × 2 = 48 combos
        "fast_ema":     [20, 30, 50, 100],
        "slow_ema":     [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "ema_slope_above": {                            # 4 × 2 × 2 = 16 combos
        "ema_len":      [50, 100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "rsi_recovery_ema": {                           # 3 × 4 = 12 combos
        "rsi_len":      [7, 14, 21],
        "trend_len":    [50, 100, 150, 200],
        "cooldown":     [5],
    },
    "rsi_50_above_trend": {                         # 2 × 3 × 2 = 12 combos
        "rsi_len":      [7, 14],
        "trend_len":    [100, 150, 200],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "triple_ema_stack": {                           # 3 × 2 × 2 × 2 = 24 combos
        "short_ema":    [20, 30, 50],
        "med_ema":      [100, 150],
        "long_ema":     [200, 300],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "dual_ema_stack": {                             # 4 × 3 × 2 = 24 combos
        "short_ema":    [20, 30, 50, 100],
        "long_ema":     [100, 150, 200],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "donchian_filter": {                            # 4 × 3 × 3 = 36 combos
        "entry_len":    [50, 100, 150, 200],
        "exit_len":     [20, 50, 100],
        "trend_len":    [50, 100, 200],
        "cooldown":     [5],
    },
    "macd_above_zero_trend": {                      # 3 = 3 combos
        "trend_len":    [100, 150, 200],
        "cooldown":     [5],
    },
    "ema_pure_slope": {                             # 4 × 2 × 2 = 16 combos
        "ema_len":      [50, 100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars":   [2, 3],
        "cooldown":     [5],
    },
    "ema_200_confirm": {                            # 3 × 3 = 9 combos
        "ema_len":      [100, 150, 200],
        "entry_bars":   [2, 3, 5],
        "cooldown":     [5],
    },
    "ema_200_regime": {                             # 3 × 2 = 6 combos
        "ema_len":      [100, 150, 200],
        "cooldown":     [2, 5],
    },
}


def _grid_combos(grid: dict) -> list[dict]:
    """Expand a grid dict into all parameter combos (Cartesian product)."""
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _is_valid_combo(concept: str, params: dict) -> bool:
    """Reject obviously invalid combos (e.g., fast_ema >= slow_ema)."""
    fast = params.get("fast_ema") or params.get("short_ema")
    slow = params.get("slow_ema") or params.get("long_ema")
    if fast is not None and slow is not None and fast >= slow:
        return False
    # For triple stack: short < med < long
    short = params.get("short_ema")
    med = params.get("med_ema")
    long_ = params.get("long_ema")
    if short is not None and med is not None and long_ is not None:
        if not (short < med < long_):
            return False
    # For donchian: exit_len < entry_len
    entry = params.get("entry_len")
    exit_ = params.get("exit_len")
    if entry is not None and exit_ is not None and exit_ >= entry:
        return False
    return True


def run_grid_search(
    concepts: list[str] | None = None,
    dry_run: bool = False,
    top_n: int = 20,
    validate: bool = True,
) -> dict:
    """Run exhaustive grid search over all (or specified) concepts.

    Returns dict with raw results + validated rankings + leaderboard state.
    """
    if concepts is None:
        concepts = list(GRIDS.keys())

    # Load data once
    print("[grid] Loading TECL data...")
    df = get_tecl_data()
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    print(f"[grid] {len(df)} bars, {len(concepts)} concepts")

    # Count total combos
    total_combos = 0
    for concept in concepts:
        grid = GRIDS.get(concept, {})
        combos = [c for c in _grid_combos(grid) if _is_valid_combo(concept, c)]
        total_combos += len(combos)
        print(f"  {concept:<28} {len(combos):>4} combos")
    print(f"  {'TOTAL':<28} {total_combos:>4} combos")

    if dry_run:
        print("\n[grid] Dry run — no backtests. Exiting.")
        return {"total_combos": total_combos}

    # ── Phase 1: Exhaustive backtest + pre-filter ──
    start = time.time()
    all_results = []
    charter_rejects = 0
    for concept in concepts:
        fn = STRATEGY_REGISTRY.get(concept)
        if fn is None:
            print(f"  SKIP {concept}: not in STRATEGY_REGISTRY")
            continue
        grid = GRIDS.get(concept, {})
        combos = [c for c in _grid_combos(grid) if _is_valid_combo(concept, c)]
        best_share = 0.0
        concept_pass = 0
        for params in combos:
            try:
                entries, exits, labels = fn(ind, params)
                result = backtest(df, entries, exits, labels,
                                  cooldown_bars=params.get("cooldown", 0),
                                  strategy_name=concept)
                result.params = params
            except Exception:
                continue

            # Charter pre-filter
            if result.vs_bah_multiple < 1.0:
                charter_rejects += 1
                continue
            if result.num_trades < 5:
                charter_rejects += 1
                continue
            if result.trades_per_year > 5.0:
                charter_rejects += 1
                continue

            # Compute regime score + marker alignment
            result.regime_score = score_regime_capture(result.trades, close, dates)
            align = score_marker_alignment(df, result.trades)
            tier = STRATEGY_TIERS.get(concept, "T1")
            fit = compute_fitness(result, tier=tier)

            entry = {
                "strategy": concept,
                "rank": 0,
                "fitness": fit,
                "tier": tier,
                "params": params,
                "marker_alignment_score": align["score"],
                "marker_alignment_detail": align,
                "metrics": {
                    "trades": result.num_trades,
                    "trades_yr": result.trades_per_year,
                    "n_params": _count_tunable_params(params),
                    "vs_bah": result.vs_bah_multiple,
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
                "trades": [
                    {"entry_bar": t.entry_bar, "exit_bar": t.exit_bar,
                     "entry_date": t.entry_date, "exit_date": t.exit_date,
                     "entry_price": t.entry_price, "exit_price": t.exit_price,
                     "pnl_pct": t.pnl_pct, "bars_held": t.bars_held,
                     "exit_reason": t.exit_reason}
                    for t in result.trades
                ],
            }
            all_results.append(entry)
            concept_pass += 1
            if result.vs_bah_multiple > best_share:
                best_share = result.vs_bah_multiple

        print(f"  {concept:<28} {concept_pass:>3} pass charter  best_share={best_share:.2f}x")

    elapsed_search = time.time() - start
    # Rank by share_multiple (primary metric)
    all_results.sort(key=lambda e: e["metrics"]["vs_bah"], reverse=True)
    for i, e in enumerate(all_results, 1):
        e["rank"] = i

    print(f"\n[grid] Search done: {total_combos} combos → {len(all_results)} pass charter "
          f"({charter_rejects} rejected) in {elapsed_search:.1f}s")

    if not all_results:
        print("[grid] No candidates passed charter pre-filter. Nothing to validate.")
        return {"total_combos": total_combos, "charter_pass": 0}

    # Show top 10 raw
    print(f"\n[grid] Top 10 raw (by share_multiple):")
    for e in all_results[:10]:
        m = e["metrics"]
        print(f"  {e['strategy']:<28} share={m['vs_bah']:.2f}x  trades={m['trades']}  "
              f"tpy={m['trades_yr']:.2f}  marker={e['marker_alignment_score']:.3f}  "
              f"params={e['params']}")

    if not validate:
        return {"total_combos": total_combos, "charter_pass": len(all_results),
                "raw_rankings": all_results[:top_n]}

    # ── Phase 2: Validate top-N through the pipeline ──
    print(f"\n[grid] Validating top {min(top_n, len(all_results))} candidates...")
    val_input = {"raw_rankings": all_results[:top_n]}
    validation = run_validation_pipeline(val_input, hours=0.05, quick=True)

    summary = validation["validation_summary"]
    print(f"\n[grid] Validation: PASS={summary['validated_pass']}  "
          f"WARN={summary['validated_warn']}  FAIL={summary['validated_fail']}")

    # ── Phase 3: Update leaderboard ──
    validated = validation["validated_rankings"]
    lb_path = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
    if validated:
        # Reset leaderboard for clean state
        with open(lb_path, "w") as f:
            json.dump([], f)
        lb = update_leaderboard(
            {"rankings": validated, "date": datetime.now().strftime("%Y-%m-%d"),
             "total_evaluations": total_combos, "elapsed_hours": elapsed_search / 3600},
            lb_path,
        )
        print(f"\n[grid] Leaderboard updated: {len(lb)} entries")
        for i, e in enumerate(lb[:20], 1):
            m = e.get("metrics", {})
            t = (e.get("validation") or {}).get("tier") or e.get("tier") or "?"
            print(f"  #{i} {e['strategy']:<28} [{t}]  share={m.get('vs_bah',0):.2f}x  "
                  f"fitness={e.get('fitness',0):.4f}  params={e.get('params',{})}")
    else:
        print("[grid] No strategies passed validation. Leaderboard unchanged.")

    return {
        "total_combos": total_combos,
        "charter_pass": len(all_results),
        "raw_rankings": all_results[:top_n],
        "validation": validation,
        "leaderboard_entries": len(validated),
    }


def main():
    parser = argparse.ArgumentParser(description="Grid Search — exhaustive canonical param testing")
    parser.add_argument("--concepts", type=str, default=None,
                        help="Comma-separated concept names (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Just show combo counts, don't backtest")
    parser.add_argument("--top-n", type=int, default=20,
                        help="Validate top N candidates (default: 20)")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip validation (just pre-test)")
    args = parser.parse_args()

    concepts = args.concepts.split(",") if args.concepts else None
    run_grid_search(
        concepts=concepts,
        dry_run=args.dry_run,
        top_n=args.top_n,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()

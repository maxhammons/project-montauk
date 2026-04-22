#!/usr/bin/env python3
"""Focus-spike: hardened grid search around a known-good strategy.

Long-run reliability via GridRunner harness (see safe_runner.py):
  - heartbeat every 60s (visible even under stdout buffering)
  - checkpoints every 100k combos (survive any crash)
  - crash rate auto-abort if >50% of backtests fail
  - top-K kept globally, not just charter-passers
  - validation wrapped in try/except with recovery-file dump

Usage:
    python scripts/search/focus_spike.py --strategy gc_vjatr [--top-n 100]

Grid is loaded from `scripts/search/focus_grids.py` keyed by strategy.
Results:
  - Admitted to `spike/leaderboard.json` if confidence >= 0.60
  - Checkpoint/recovery files under `spike/focus_spikes/<strategy>_<ts>/`
  - No bulk persistence of raw grid results (only top-K heap survives)
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Per-strategy grids (extend as new strategies get focus spikes)
# ─────────────────────────────────────────────────────────────────────────────

FOCUS_GRIDS: dict[str, dict[str, list]] = {
    # gc_vjatr — Jade Bonobo neighborhood (2026-04-21). Broad integer-step
    # on EMAs, wide ATR mechanism coverage.
    "gc_vjatr": {
        "fast_ema":     [100, 120, 130, 140, 150, 160, 170, 180, 200],
        "slow_ema":     [150, 160, 170, 175, 180, 190, 200, 220, 250, 275, 300],
        "slope_window": [1, 3, 5],
        "entry_bars":   [1, 2, 3],
        "cooldown":     [0, 2, 5],
        "atr_period":   [7, 10, 14, 20, 30],
        "atr_look":     [20, 30, 50, 75, 100],
        "atr_expand":   [1.5, 1.75, 1.9, 2.0, 2.1, 2.25, 2.5],
        "atr_confirm":  [1, 2, 3, 5],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Worker functions (top-level so Pool can pickle them)
# ─────────────────────────────────────────────────────────────────────────────

_WORKER_STRATEGY: str | None = None


def _worker_init_factory(strategy_name: str):
    """Return a closure-free initializer. The strategy name is picked up from
    a module-level global that the parent sets before Pool creation."""
    def _init():
        global _df, _ind, _fn
        from data.loader import get_tecl_data
        from engine.strategy_engine import Indicators
        from strategies.library import STRATEGY_REGISTRY
        _df = get_tecl_data()
        _ind = Indicators(_df)
        _fn = STRATEGY_REGISTRY[strategy_name]
    return _init


def _worker_init():
    """Actual initializer — reads strategy from module-level _WORKER_STRATEGY
    (set in each worker via fork inheritance from parent)."""
    global _df, _ind, _fn
    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators
    from strategies.library import STRATEGY_REGISTRY
    _df = get_tecl_data()
    _ind = Indicators(_df)
    _fn = STRATEGY_REGISTRY[_WORKER_STRATEGY]


def _worker_eval(params: dict):
    """Backtest one combo. Returns tuple on charter-pass, None on reject,
    {"_error": str} on crash."""
    from engine.strategy_engine import backtest
    from search.fitness import weighted_era_fitness

    try:
        e, x, l = _fn(_ind, params)
        r = backtest(_df, e, x, l, cooldown_bars=params.get("cooldown", 0), strategy_name=_WORKER_STRATEGY)
        if r.num_trades < 5 or r.trades_per_year > 5.0:
            return None
        wef = weighted_era_fitness(r.share_multiple, r.real_share_multiple, r.modern_share_multiple)
        if wef < 1.0:
            return None
        return (
            float(wef),
            float(r.share_multiple),
            float(r.real_share_multiple),
            float(r.modern_share_multiple),
            int(r.num_trades),
            float(r.trades_per_year),
            float(r.max_drawdown_pct),
            float(r.cagr_pct),
            params,
        )
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    global _WORKER_STRATEGY

    parser = argparse.ArgumentParser(description="Focus-spike grid search.")
    parser.add_argument("--strategy", required=True, help="Strategy name (must be a key in FOCUS_GRIDS).")
    parser.add_argument("--top-n", type=int, default=100, help="Validate top N candidates (default 100).")
    parser.add_argument("--workers", type=int, default=None, help="Pool size (default cpu-1 capped at 12).")
    parser.add_argument("--checkpoint-every", type=int, default=100_000, help="Combos between checkpoints.")
    parser.add_argument("--heartbeat-secs", type=float, default=60.0, help="Heartbeat interval (seconds).")
    args = parser.parse_args()

    if args.strategy not in FOCUS_GRIDS:
        print(f"ERROR: unknown strategy '{args.strategy}'. Available: {list(FOCUS_GRIDS.keys())}")
        sys.exit(2)

    _WORKER_STRATEGY = args.strategy
    grid = FOCUS_GRIDS[args.strategy]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_dir = os.path.join(PROJECT_ROOT, "spike", "focus_spikes", f"{args.strategy}_{ts}")

    from search.safe_runner import GridRunner, run_validation_safely

    runner = GridRunner(
        strategy_name=args.strategy,
        grid=grid,
        worker_eval=_worker_eval,
        worker_init=_worker_init,
        filter_fn=lambda p: p.get("slow_ema", 1) > p.get("fast_ema", 0),
        fitness_key=0,
        top_n_keep=1000,
        n_workers=args.workers,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every=args.checkpoint_every,
        heartbeat_secs=args.heartbeat_secs,
        fail_fast_crash_pct=0.50,
        chunksize=100,
    )

    out = runner.run()
    stats = out["stats"]
    top_k = out["top_k"]

    # Summary
    print("\n" + "=" * 70)
    print(f"FOCUS-SPIKE COMPLETE — {args.strategy}")
    print("=" * 70)
    print(f"Combos: total={stats.combos_total:,}  passed={stats.combos_passed:,}")
    print(f"Skipped (charter-reject): {stats.combos_skipped:,}")
    print(f"Crashed: {stats.combos_crashed:,}  ({100*stats.crash_rate():.2f}%)")
    print(f"Elapsed: {stats.elapsed_sec()/60:.1f} min")
    print(f"Top-K heap captured: {len(top_k)}")
    if not top_k:
        print("No charter-passing configs found. Exiting.")
        return

    # Dual-era winner tally
    dual = [r for r in top_k if len(r) >= 4 and r[2] >= 1.0 and r[3] >= 1.0]
    print(f"\nDual-era winners (real >= 1.0 AND modern >= 1.0): {len(dual)}")
    for fit, full, real, modern, nt, tpy, dd, cagr, p in dual[:10]:
        print(f"  fit={fit:.3f} full={full:6.2f}x real={real:.2f}x modern={modern:.2f}x trades={nt} dd={dd:.1f}%")

    # Validate top N through the pipeline (with crash recovery)
    to_validate = top_k[: args.top_n]
    print(f"\nValidating top {len(to_validate)} through pipeline...")

    raw_rankings = _build_raw_rankings(args.strategy, to_validate)
    recovery_path = os.path.join(checkpoint_dir, "pre_validation_rankings.json")
    val_results = run_validation_safely(raw_rankings, recovery_path=recovery_path)

    if val_results is None:
        print(f"  [!] Validation failed. Grid data preserved at {recovery_path}.")
        return

    summary = val_results["validation_summary"]
    print(f"Validation: PASS={summary['validated_pass']} WARN={summary['validated_warn']} FAIL={summary['validated_fail']}")

    # Admit to leaderboard
    admit = [
        e for e in val_results["raw_rankings"]
        if (e.get("validation") or {}).get("composite_confidence", 0.0) >= 0.60
    ]
    if admit:
        from search.evolve import update_leaderboard
        update_leaderboard(
            {
                "rankings": admit,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_evaluations": stats.combos_total,
                "elapsed_hours": stats.elapsed_sec() / 3600,
            },
            os.path.join(PROJECT_ROOT, "spike", "leaderboard.json"),
        )
        print(f"Admitted {len(admit)} entries to leaderboard (top-20 cap applied).")
    else:
        print("No entries reached admission threshold (0.60 confidence).")


def _build_raw_rankings(strategy: str, top_k: list) -> list[dict]:
    """Convert GridRunner top-K results into raw_rankings for run_validation_pipeline.

    Re-runs the backtest to get full metadata (trades, regime_score, marker alignment)
    that wasn't stored in the compact top-K tuples.
    """
    import numpy as np
    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators, backtest
    from strategies.library import STRATEGY_REGISTRY
    from engine.regime_helpers import score_regime_capture
    from strategies.markers import score_marker_alignment
    from engine.canonical_params import count_tunable_params

    df = get_tecl_data()
    ind = Indicators(df)
    fn = STRATEGY_REGISTRY[strategy]
    cl = df["close"].values.astype(np.float64)
    dates = df["date"].values

    raw = []
    for rec in top_k:
        fit = rec[0]
        params = rec[-1]
        e, x, l = fn(ind, params)
        r = backtest(df, e, x, l, cooldown_bars=params.get("cooldown", 0), strategy_name=strategy)
        rs = score_regime_capture(r.trades, cl, dates)
        align = score_marker_alignment(df, r.trades)
        raw.append({
            "strategy": strategy,
            "rank": 0,
            "fitness": round(float(fit), 4),
            "tier": "T2",
            "params": params,
            "marker_alignment_score": align["score"],
            "marker_alignment_detail": align,
            "metrics": {
                "trades": r.num_trades,
                "trades_yr": r.trades_per_year,
                "n_params": count_tunable_params(params),
                "share_multiple": r.share_multiple,
                "real_share_multiple": r.real_share_multiple,
                "modern_share_multiple": r.modern_share_multiple,
                "cagr": r.cagr_pct,
                "max_dd": r.max_drawdown_pct,
                "mar": r.mar_ratio,
                "regime_score": rs.composite,
                "hhi": rs.hhi or 0,
                "bull_capture": rs.bull_capture_ratio,
                "bear_avoidance": rs.bear_avoidance_ratio,
                "win_rate": r.win_rate_pct,
                "exit_reasons": r.exit_reasons,
            },
        })
    return raw


if __name__ == "__main__":
    multiprocessing.set_start_method("fork", force=True)
    main()

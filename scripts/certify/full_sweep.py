#!/usr/bin/env python3
"""Full-registry rescoring sweep under the 2026-04-21 confidence-score framework.

Runs exhaustive canonical grid search across all 138 grid-searchable strategies,
then validates the 23 fixed-param strategies directly. Writes results to
`spike/historical_rescore.json` and updates `spike/leaderboard.json` (top-20 by
confidence).

Purpose: the new validation framework removed non-correctness hard-fails and
added per-cycle magnitude-weighted marker timing. Strategies previously killed
by cross-asset, walk-forward, named-window, Morris, or bootstrap hard-fails may
now score competitively. This sweep surfaces those.

Checkpointing: writes progress to `spike/.full_sweep_checkpoint.json` after each
phase so interrupted runs can resume.

Usage:
    python3 scripts/certify/full_sweep.py
    python3 scripts/certify/full_sweep.py --phase grid     # only grid search
    python3 scripts/certify/full_sweep.py --phase fixed    # only fixed-param
    python3 scripts/certify/full_sweep.py --phase report   # rebuild summary only
"""

from __future__ import annotations

import argparse
import glob
import json
import multiprocessing
import os
import sys
import time
from datetime import datetime


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

SPIKE_DIR = os.path.join(PROJECT_ROOT, "spike")
LEADERBOARD_PATH = os.path.join(SPIKE_DIR, "leaderboard.json")
RESCORE_PATH = os.path.join(SPIKE_DIR, "historical_rescore.json")
CHECKPOINT_PATH = os.path.join(SPIKE_DIR, ".full_sweep_checkpoint.json")


def _load_checkpoint() -> dict:
    if not os.path.exists(CHECKPOINT_PATH):
        return {}
    try:
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_checkpoint(data: dict) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _best_historical_params(strategy_name: str) -> dict | None:
    """Scan past spike runs for the highest-fitness config of a given strategy.

    Returns the params dict or None if the strategy was never run.
    """
    best_fitness = -1.0
    best_params = None
    for rf in glob.glob(os.path.join(SPIKE_DIR, "runs", "*", "results.json")):
        try:
            with open(rf) as f:
                r = json.load(f)
        except Exception:
            continue
        for entry in r.get("raw_rankings") or r.get("rankings") or []:
            if entry.get("strategy") != strategy_name:
                continue
            fitness = float(entry.get("fitness") or 0.0)
            params = entry.get("params") or {}
            if not params:
                continue
            if fitness > best_fitness:
                best_fitness = fitness
                best_params = params
    return best_params


def run_grid_phase(top_n: int = 200) -> dict:
    """Phase 1 — run exhaustive canonical grid across all grid-searchable strategies."""
    from search.grid_search import GRIDS, run_grid_search

    concepts = sorted(GRIDS.keys())
    print(f"[sweep] Phase 1: grid-search across {len(concepts)} strategies")
    print(
        f"[sweep]   top_n={top_n} (per-concept-best guaranteed; remaining fill by share_multiple)"
    )

    start = time.time()
    result = run_grid_search(
        concepts=concepts,
        dry_run=False,
        top_n=top_n,
        validate=True,
    )
    elapsed = time.time() - start
    print(f"[sweep] Phase 1 done in {elapsed / 60:.1f} min")
    return {
        "phase": "grid",
        "elapsed_seconds": round(elapsed, 1),
        "total_combos": result.get("total_combos", 0),
        "charter_pass": result.get("charter_pass", 0),
        "leaderboard_entries": result.get("leaderboard_entries", 0),
    }


def _backtest_fixed_param(strategy_name: str, params: dict):
    """Backtest a single strategy with given params, return (metrics_dict, trades, bt_result)."""
    from data.loader import get_tecl_data
    from engine.strategy_engine import Indicators, backtest
    from engine.regime_helpers import score_regime_capture
    from strategies.library import STRATEGY_REGISTRY
    from strategies.markers import score_marker_alignment
    import numpy as np

    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    try:
        entries, exits, labels = strategy_fn(ind, params)
    except Exception as exc:
        return None, None, f"strategy raise: {exc}"
    cooldown = int(params.get("cooldown", 0))
    try:
        bt = backtest(
            df,
            entries,
            exits,
            labels,
            cooldown_bars=cooldown,
            strategy_name=strategy_name,
        )
    except Exception as exc:
        return None, None, f"backtest raise: {exc}"
    if bt.num_trades == 0:
        return None, None, "zero trades"

    cl = df["close"].values.astype(np.float64)
    dates = df["date"].values
    try:
        rs = score_regime_capture(bt.trades, cl, dates)
        regime_score = float(rs.composite)
    except Exception:
        regime_score = 0.0

    marker = score_marker_alignment(df, bt.trades)

    # Signal-param count for tier auto-promotion
    from engine.canonical_params import count_tunable_params

    n_params = count_tunable_params(params)

    # Compute trades_yr
    years = max(len(df) / 252.0, 1.0)

    metrics = {
        "share_multiple": round(bt.share_multiple, 4),
        "real_share_multiple": round(bt.real_share_multiple, 4),
        "modern_share_multiple": round(bt.modern_share_multiple, 4),
        "cagr": round(bt.cagr_pct, 2),
        "max_dd": round(bt.max_drawdown_pct, 2),
        "mar": round(bt.mar_ratio, 3),
        "trades": bt.num_trades,
        "trades_yr": round(bt.num_trades / years, 3),
        "win_rate": round(bt.win_rate_pct, 1),
        "regime_score": round(regime_score, 4),
        "n_params": n_params,
    }
    return metrics, bt.trades, marker


def run_fixed_param_phase() -> dict:
    """Phase 2 — validate the 23 fixed-param strategies (no GRID) under the new rubric."""
    from search.evolve import update_leaderboard
    from search.grid_search import GRIDS
    from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
    from validation.pipeline import run_validation_pipeline

    fixed = sorted(s for s in STRATEGY_REGISTRY if s not in GRIDS)
    print(f"[sweep] Phase 2: validating {len(fixed)} fixed-param strategies")

    raw_rankings = []
    for name in fixed:
        params = _best_historical_params(name) or {}
        source = "historical" if params else "defaults"
        print(f"  [fixed] {name:30s} params={source}")
        metrics, trades, marker_or_err = _backtest_fixed_param(name, params)
        if metrics is None:
            print(f"    SKIP {name}: {marker_or_err}")
            continue
        # Fitness = weighted-era geometric mean (2026-04-21 revision). Same
        # scheme the GA/grid-search uses: full^0.15 * real^0.25 * modern^0.60.
        from search.fitness import fitness_from_metrics

        fit = fitness_from_metrics(metrics)
        raw_rankings.append(
            {
                "strategy": name,
                "rank": 0,
                "fitness": round(fit, 4),
                "tier": STRATEGY_TIERS.get(name, "T2"),
                "params": params,
                "metrics": metrics,
                "marker_alignment_score": float(marker_or_err.get("score", 0.5))
                if isinstance(marker_or_err, dict)
                else 0.5,
            }
        )

    print(f"[sweep]   {len(raw_rankings)} fixed-param candidates charter-compatible")

    if not raw_rankings:
        return {"phase": "fixed", "validated": 0}

    start = time.time()
    results = run_validation_pipeline(
        {"raw_rankings": raw_rankings},
        hours=0.05,
        quick=True,
        top_n=len(raw_rankings),
    )
    elapsed = time.time() - start
    summary = results["validation_summary"]
    print(
        f"[sweep] Phase 2 validation done in {elapsed / 60:.1f} min: "
        f"PASS={summary['validated_pass']} WARN={summary['validated_warn']} FAIL={summary['validated_fail']}"
    )

    # Feed every validated row through the canonical leaderboard authority path.
    validated = results.get("raw_rankings", [])
    if validated:
        update_leaderboard(
            {
                "rankings": validated,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_evaluations": len(raw_rankings),
                "elapsed_hours": elapsed / 3600,
            },
            LEADERBOARD_PATH,
        )
        print("[sweep] Submitted fixed-param validation rows to leaderboard authority")

    # Persist ALL fixed-param validation results (admitted or not) so Phase 3
    # can pull from the full new-rubric set without re-running validation.
    fixed_out_path = os.path.join(SPIKE_DIR, "fixed_param_sweep_output.json")
    with open(fixed_out_path, "w") as f:
        json.dump(
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rankings": results.get("raw_rankings", []),
            },
            f,
            indent=2,
            default=str,
        )
    print(f"[sweep] Wrote {fixed_out_path}")

    return {
        "phase": "fixed",
        "evaluated": len(raw_rankings),
        "validated_pass": summary["validated_pass"],
        "validated_warn": summary["validated_warn"],
        "validated_fail": summary["validated_fail"],
        "admitted": len(validated),
        "fixed_output_path": fixed_out_path,
        "elapsed_seconds": round(elapsed, 1),
    }


def build_rescore_report(new_rubric_cutoff_ts: float | None = None) -> dict:
    """Phase 3 — assemble NEW-rubric confidence scores per strategy.

    Sources (all guaranteed to be new-rubric):
      1. Current `spike/leaderboard.json` (rescored under new framework)
      2. Run files created after `new_rubric_cutoff_ts` (Phase 1 grid output)
      3. `spike/fixed_param_sweep_output.json` (Phase 2 output)

    Fall back: strategies not covered by any of the above are marked
    `status: "not_evaluated_in_sweep"` with no confidence score. Older run
    files (pre-cutoff) are ignored — their composite_confidence was computed
    under the old rubric and would mislead.
    """
    from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS

    print("[sweep] Phase 3: building rescore report (new-rubric only)")

    best_per_strategy: dict[str, dict] = {}

    def _ingest(entry: dict, source: str) -> None:
        name = entry.get("strategy")
        if not name:
            return
        val = entry.get("validation") or {}
        conf = float(val.get("composite_confidence") or 0.0)
        prev = best_per_strategy.get(name)
        if prev is None or conf > prev["composite_confidence"]:
            best_per_strategy[name] = {
                "strategy": name,
                "composite_confidence": conf,
                "verdict": val.get("verdict", "?"),
                "tier": val.get("tier", STRATEGY_TIERS.get(name, "T2")),
                "params": entry.get("params") or {},
                "share_multiple": float(
                    (entry.get("metrics") or {}).get("share_multiple", 0.0)
                ),
                "trades": int((entry.get("metrics") or {}).get("trades", 0)),
                "fitness": float(entry.get("fitness") or 0.0),
                "source": source,
                "sub_scores": val.get("sub_scores", {}),
                "hard_fail_reasons": val.get("hard_fail_reasons", []),
            }

    # 1. Leaderboard (always new-rubric post-sweep)
    if os.path.exists(LEADERBOARD_PATH):
        with open(LEADERBOARD_PATH) as f:
            lb = json.load(f)
        for entry in lb:
            _ingest(entry, source="leaderboard")
        print(f"[sweep]   ingested {len(lb)} leaderboard entries")

    # 2. Run files created after the new-rubric cutoff (Phase 1 output)
    run_files = sorted(glob.glob(os.path.join(SPIKE_DIR, "runs", "*", "results.json")))
    fresh_runs = 0
    for rf in run_files:
        if (
            new_rubric_cutoff_ts is not None
            and os.path.getmtime(rf) < new_rubric_cutoff_ts
        ):
            continue
        fresh_runs += 1
        try:
            with open(rf) as f:
                r = json.load(f)
        except Exception:
            continue
        for entry in r.get("raw_rankings") or r.get("rankings") or []:
            _ingest(entry, source=os.path.relpath(rf, PROJECT_ROOT))
    print(f"[sweep]   ingested {fresh_runs} fresh run files")

    # 3. Phase 2 fixed-param output
    fixed_out_path = os.path.join(SPIKE_DIR, "fixed_param_sweep_output.json")
    if os.path.exists(fixed_out_path):
        with open(fixed_out_path) as f:
            fo = json.load(f)
        for entry in fo.get("rankings", []):
            _ingest(entry, source="fixed_param_sweep_output.json")
        print(f"[sweep]   ingested {len(fo.get('rankings', []))} fixed-param entries")

    # Strategies that were never evaluated
    missing = sorted(s for s in STRATEGY_REGISTRY if s not in best_per_strategy)

    # Sort by confidence
    ranked = sorted(
        best_per_strategy.values(),
        key=lambda e: e["composite_confidence"],
        reverse=True,
    )

    admission_counts = {"admitted": 0, "watchlist": 0, "research": 0, "rejected": 0}
    for e in ranked:
        c = e["composite_confidence"]
        if c >= 0.70:
            admission_counts["admitted"] += 1
        elif c >= 0.60:
            admission_counts["watchlist"] += 1
        elif c >= 0.40:
            admission_counts["research"] += 1
        else:
            admission_counts["rejected"] += 1

    report = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "framework": "2026-04-21 confidence-score",
        "total_strategies_registered": len(STRATEGY_REGISTRY),
        "total_strategies_evaluated": len(best_per_strategy),
        "strategies_never_evaluated": missing,
        "admission_counts": admission_counts,
        "rankings": ranked,
    }

    with open(RESCORE_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"[sweep] Wrote {RESCORE_PATH}")
    print("\n[sweep] Top 25 by confidence:")
    for i, e in enumerate(ranked[:25], 1):
        c = e["composite_confidence"] * 100
        label = (
            "ADMIT"
            if c >= 70
            else "WATCH"
            if c >= 60
            else "RSRCH"
            if c >= 40
            else "REJCT"
        )
        print(
            f"  #{i:2d} {e['strategy']:30s} conf={c:5.1f} [{label}] "
            f"share={e['share_multiple']:6.2f}x  tier={e['tier']}"
        )
    if missing:
        print(
            f"\n[sweep] {len(missing)} strategies had no evaluated runs (registered but never searched):"
        )
        for m in missing[:20]:
            print(f"    {m}")
        if len(missing) > 20:
            print(f"    ... and {len(missing) - 20} more")

    return report


def main():
    parser = argparse.ArgumentParser(description="Full-registry rescoring sweep")
    parser.add_argument(
        "--phase",
        choices=["all", "grid", "fixed", "report"],
        default="all",
        help="Which phase to run (default: all)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=200,
        help="Validate this many grid candidates (per-concept-best guaranteed; default 200)",
    )
    args = parser.parse_args()

    checkpoint = _load_checkpoint()
    print(f"[sweep] Checkpoint state: {list(checkpoint.keys())}")

    # Record the sweep start timestamp so Phase 3 can filter fresh runs.
    # If we're resuming (checkpoint has a prior sweep_start), keep it so the
    # report considers the original run window.
    if "sweep_start_ts" not in checkpoint:
        checkpoint["sweep_start_ts"] = time.time()
        _save_checkpoint(checkpoint)
    sweep_start_ts = float(checkpoint["sweep_start_ts"])

    if args.phase in {"all", "grid"}:
        if checkpoint.get("grid_done") and args.phase == "all":
            print(
                "[sweep] Phase 1 already completed — skipping. Delete checkpoint to rerun."
            )
        else:
            result = run_grid_phase(top_n=args.top_n)
            checkpoint["grid_done"] = True
            checkpoint["grid_result"] = result
            _save_checkpoint(checkpoint)

    if args.phase in {"all", "fixed"}:
        if checkpoint.get("fixed_done") and args.phase == "all":
            print(
                "[sweep] Phase 2 already completed — skipping. Delete checkpoint to rerun."
            )
        else:
            result = run_fixed_param_phase()
            checkpoint["fixed_done"] = True
            checkpoint["fixed_result"] = result
            _save_checkpoint(checkpoint)

    if args.phase in {"all", "report"}:
        report = build_rescore_report(new_rubric_cutoff_ts=sweep_start_ts)
        checkpoint["report_done"] = True
        checkpoint["report_summary"] = {
            "total_evaluated": report["total_strategies_evaluated"],
            "admission_counts": report["admission_counts"],
        }
        _save_checkpoint(checkpoint)

    # Phase 4 — backfill dashboard_data.json artifacts for every leaderboard
    # entry so viz/build_viz.py can render all charts without manual follow-up.
    if args.phase in {"all", "report"}:
        from certify.backfill_artifacts import backfill_leaderboard_dashboard_artifacts

        print("[sweep] Phase 4: backfilling dashboard artifacts for leaderboard")
        created, present = backfill_leaderboard_dashboard_artifacts(top_n=20)
        print(f"[sweep]   created {created}, already-present {present}")
        checkpoint["backfill_done"] = True
        checkpoint["backfill_created"] = created
        _save_checkpoint(checkpoint)

    print("\n[sweep] Complete.")


if __name__ == "__main__":
    multiprocessing.set_start_method("fork", force=True)
    main()

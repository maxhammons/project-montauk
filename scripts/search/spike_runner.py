#!/usr/bin/env python3
"""
Spike Runner — single command, fully autonomous optimization.

This is the main entry point for /spike. It:
  1. Creates a sequentially numbered run directory
  2. Runs the evolutionary optimizer (with history seeding + dedup)
  3. Generates a markdown report with top-10 table
  4. Updates the all-time leaderboard (top 20)
  5. Saves everything to spike/runs/NNN/

Usage:
  python3 scripts/spike_runner.py --hours 4
  python3 scripts/spike_runner.py --hours 8 --pop-size 60

All output goes to spike/runs/<N>/. The active strategy is never modified.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from certify.contract import sync_entry_contract


def _load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _write_json(path: str, payload, *, encoder_cls=None):
    with open(path, "w") as f:
        if encoder_cls is not None:
            json.dump(payload, f, indent=2, cls=encoder_cls)
        else:
            json.dump(payload, f, indent=2)


def _risk_state_from_trades(
    n_bars: int, trades: list
) -> tuple[list[bool], list[bool], list[bool]]:
    risk_on = [False] * n_bars
    buy_events = [False] * n_bars
    sell_events = [False] * n_bars
    for trade in trades or []:
        entry_bar = max(0, int(trade.entry_bar))
        exit_bar = (
            int(trade.exit_bar) if getattr(trade, "exit_bar", -1) >= 0 else (n_bars - 1)
        )
        exit_bar = min(n_bars - 1, max(entry_bar, exit_bar))
        for idx in range(entry_bar, exit_bar + 1):
            risk_on[idx] = True
        buy_events[entry_bar] = True
        sell_events[exit_bar] = True
    return risk_on, buy_events, sell_events


def _compute_drawdown_series(values) -> list[float]:
    import numpy as np

    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return []
    peak = np.maximum.accumulate(arr)
    dd = np.where(peak > 0, (arr - peak) / peak * 100, 0.0)
    return [round(float(v), 4) for v in dd]


def _refresh_final_artifact_views(results: dict, artifacts: dict, *, encoder_cls=None):
    validation_summary_path = artifacts.get("validation_summary")
    if validation_summary_path and os.path.exists(validation_summary_path):
        payload = _load_json(validation_summary_path) or {}
        payload["summary"] = results.get("validation_summary", {})
        payload["champion_validation"] = (results.get("champion") or {}).get(
            "validation", {}
        )
        _write_json(validation_summary_path, payload, encoder_cls=encoder_cls)

    dashboard_data_path = artifacts.get("dashboard_data")
    if dashboard_data_path and os.path.exists(dashboard_data_path):
        payload = _load_json(dashboard_data_path) or {}
        payload["validation"] = (results.get("champion") or {}).get("validation", {})
        payload["validation_summary"] = results.get("validation_summary", {})
        _write_json(dashboard_data_path, payload, encoder_cls=encoder_cls)


def _finalize_champion_certification(results: dict, artifacts: dict):
    champion = results.get("champion")
    if not champion:
        return

    targets = [champion]
    if results.get("validated_rankings"):
        targets.append(results["validated_rankings"][0])
    if results.get("rankings"):
        targets.append(results["rankings"][0])

    for target in targets:
        sync_entry_contract(target, artifact_paths=artifacts)

    summary = results.get("validation_summary") or {}
    if summary.get("champion"):
        summary["champion"]["backtest_certified"] = champion["validation"][
            "backtest_certified"
        ]
        summary["champion"]["promotion_ready"] = champion["validation"][
            "promotion_ready"
        ]


def _emit_run_artifacts(
    run_dir: str, results: dict, *, encoder_cls=None, overlay=None
) -> dict:
    generated_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    champion = results.get("champion")
    artifacts = {}

    validation_summary_payload = {
        "generated_utc": generated_utc,
        "run_id": os.path.basename(run_dir),
        "summary": results.get("validation_summary", {}),
        "champion_validation": (champion or {}).get("validation", {}),
    }
    validation_summary_path = os.path.join(run_dir, "validation_summary.json")
    _write_json(
        validation_summary_path, validation_summary_payload, encoder_cls=encoder_cls
    )
    artifacts["validation_summary"] = validation_summary_path

    if not champion:
        trade_ledger_path = os.path.join(run_dir, "trade_ledger.json")
        signal_series_path = os.path.join(run_dir, "signal_series.json")
        equity_curve_path = os.path.join(run_dir, "equity_curve.json")
        dashboard_data_path = os.path.join(run_dir, "dashboard_data.json")
        _write_json(trade_ledger_path, [], encoder_cls=encoder_cls)
        _write_json(signal_series_path, [], encoder_cls=encoder_cls)
        _write_json(equity_curve_path, [], encoder_cls=encoder_cls)
        _write_json(
            dashboard_data_path,
            {
                "generated_utc": generated_utc,
                "run_id": os.path.basename(run_dir),
                "champion": None,
                "validation_summary": results.get("validation_summary", {}),
            },
            encoder_cls=encoder_cls,
        )
        artifacts.update(
            {
                "trade_ledger": trade_ledger_path,
                "signal_series": signal_series_path,
                "equity_curve": equity_curve_path,
                "dashboard_data": dashboard_data_path,
            }
        )
        return artifacts

    import numpy as np
    import pandas as pd

    from data.loader import get_tecl_data
    from strategies.library import STRATEGY_REGISTRY
    from engine.strategy_engine import Indicators, backtest

    strategy_name = champion["strategy"]
    params = champion["params"]
    strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
    if strategy_fn is None:
        raise KeyError(f"{strategy_name} missing from STRATEGY_REGISTRY")

    df = get_tecl_data(use_yfinance=False)
    indicators = Indicators(df)
    entries, exits, labels = strategy_fn(indicators, params)
    backtest_result = backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=params.get("cooldown", 0),
        strategy_name=strategy_name,
    )

    dates = [str(pd.Timestamp(value).date()) for value in df["date"]]
    close = df["close"].astype(float).to_numpy()
    equity_curve = np.asarray(backtest_result.equity_curve, dtype=float)
    initial_capital = 1000.0
    if len(close) == 0 or close[0] <= 0:
        bah_curve = np.zeros(len(close), dtype=float)
    else:
        bah_curve = initial_capital * (close / close[0])

    risk_on, buy_events, sell_events = _risk_state_from_trades(
        len(df), backtest_result.trades
    )
    drawdown = _compute_drawdown_series(equity_curve)
    bah_drawdown = _compute_drawdown_series(bah_curve)

    trade_ledger = [
        {
            "entry_bar": int(trade.entry_bar),
            "entry_date": trade.entry_date,
            "entry_price": round(float(trade.entry_price), 6),
            "exit_bar": int(trade.exit_bar),
            "exit_date": trade.exit_date,
            "exit_price": round(float(trade.exit_price), 6),
            "exit_reason": trade.exit_reason,
            "pnl_pct": round(float(trade.pnl_pct), 6),
            "bars_held": int(trade.bars_held),
        }
        for trade in backtest_result.trades
    ]

    signal_series = [
        {
            "date": dates[i],
            "risk_state": "risk_on" if risk_on[i] else "risk_off",
            "risk_on": bool(risk_on[i]),
            "entry_signal": bool(entries[i]),
            "exit_signal": bool(exits[i]),
            "buy_event": bool(buy_events[i]),
            "sell_event": bool(sell_events[i]),
            "close": round(float(close[i]), 6),
        }
        for i in range(len(df))
    ]

    equity_curve_payload = [
        {
            "date": dates[i],
            "equity": round(float(equity_curve[i]), 6),
            "bah_equity": round(float(bah_curve[i]), 6),
            "drawdown_pct": drawdown[i],
            "bah_drawdown_pct": bah_drawdown[i],
        }
        for i in range(len(df))
    ]

    stored_share_multiple = float(
        (champion.get("metrics") or {}).get("share_multiple", 0.0)
    )
    recomputed_share_multiple = float(backtest_result.share_multiple)
    drift = abs(recomputed_share_multiple - stored_share_multiple)
    if drift > 0.01:
        print(
            "[artifacts] Warning: recomputed share_multiple diverged from stored metrics "
            f"({recomputed_share_multiple:.4f} vs {stored_share_multiple:.4f})"
        )

    trade_ledger_path = os.path.join(run_dir, "trade_ledger.json")
    signal_series_path = os.path.join(run_dir, "signal_series.json")
    equity_curve_path = os.path.join(run_dir, "equity_curve.json")
    dashboard_data_path = os.path.join(run_dir, "dashboard_data.json")
    _write_json(trade_ledger_path, trade_ledger, encoder_cls=encoder_cls)
    _write_json(signal_series_path, signal_series, encoder_cls=encoder_cls)
    _write_json(equity_curve_path, equity_curve_payload, encoder_cls=encoder_cls)

    dashboard_data = {
        "generated_utc": generated_utc,
        "run_id": os.path.basename(run_dir),
        "strategy": strategy_name,
        "rank": champion.get("rank", 1),
        "fitness": champion.get("fitness"),
        "params": params,
        "metrics": champion.get("metrics", {}),
        "marker_alignment_score": champion.get("marker_alignment_score"),
        "marker_alignment_detail": champion.get("marker_alignment_detail"),
        "validation": champion.get("validation", {}),
        "share_multiple_recomputed": round(recomputed_share_multiple, 6),
        "share_multiple_drift": round(drift, 6),
        "trade_ledger": trade_ledger,
        "signal_series": signal_series,
        "equity_curve": equity_curve_payload,
        "overlay": overlay,
        "validation_summary": results.get("validation_summary", {}),
    }
    _write_json(dashboard_data_path, dashboard_data, encoder_cls=encoder_cls)

    artifacts.update(
        {
            "trade_ledger": trade_ledger_path,
            "signal_series": signal_series_path,
            "equity_curve": equity_curve_path,
            "dashboard_data": dashboard_data_path,
        }
    )
    return artifacts


def create_run_dir() -> str:
    """Create the next sequentially numbered run directory: spike/runs/NNN."""
    base = os.path.join(PROJECT_ROOT, "spike", "runs")
    os.makedirs(base, exist_ok=True)

    # Find the highest existing run number
    existing = [
        d
        for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d)) and d.isdigit()
    ]
    next_num = max((int(d) for d in existing), default=0) + 1
    run_dir = os.path.join(base, f"{next_num:03d}")

    os.makedirs(run_dir, exist_ok=True)
    return run_dir


class TeeWriter:
    """Write to both stdout and a log file simultaneously."""

    def __init__(self, log_path: str):
        self.terminal = sys.stdout
        self.log_file = open(log_path, "w")

    def write(self, text):
        self.terminal.write(text)
        self.log_file.write(text)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()


def main():
    parser = argparse.ArgumentParser(
        description="Spike Runner — fully autonomous TECL strategy optimization"
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=None,
        help="How long to run the optimizer (required unless --chunk)",
    )
    parser.add_argument(
        "--pop-size",
        type=int,
        default=40,
        help="Population per strategy per generation (default: 40)",
    )
    parser.add_argument(
        "--quick", action="store_true", help="Shorter progress report intervals"
    )
    parser.add_argument(
        "--strategies",
        type=str,
        default=None,
        help="Comma-separated list of strategy names to run (default: all)",
    )
    parser.add_argument(
        "--bayesian",
        action="store_true",
        help="Use Bayesian optimization (Optuna TPE) instead of GA",
    )
    parser.add_argument(
        "--chunk",
        action="store_true",
        help="Run a single timed chunk (for /spike v2 iterative loop)",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=20.0,
        help="Chunk duration in minutes (default: 20, requires --chunk)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=None,
        help="Path to state JSON from previous chunk (requires --chunk)",
    )
    args = parser.parse_args()

    # Parse strategy filter
    strategy_filter = None
    if args.strategies:
        strategy_filter = [s.strip() for s in args.strategies.split(",")]

    if args.chunk:
        _run_chunk(args, strategy_filter)
    else:
        _run_full(args, strategy_filter)


def _run_chunk(args, strategy_filter):
    """Run a single optimizer chunk (for /spike v2 iterative loop)."""
    import json

    # Load state from previous chunk if provided
    state = None
    if args.state_file and os.path.exists(args.state_file):
        with open(args.state_file) as f:
            state = json.load(f)

    # Create run dir (reuse existing if resuming)
    run_dir = create_run_dir()

    from search.evolve import evolve_chunk

    result = evolve_chunk(
        minutes=args.minutes,
        pop_size=args.pop_size,
        strategies=strategy_filter,
        state=state,
        run_dir=run_dir,
    )

    # Save state for next chunk
    state_path = os.path.join(run_dir, "chunk_state.json")

    class _Enc(json.JSONEncoder):
        def default(self, o):
            if hasattr(o, "item"):
                return o.item()
            return super().default(o)

    with open(state_path, "w") as f:
        json.dump(result["state"], f, cls=_Enc)

    # Save chunk results
    results_path = os.path.join(run_dir, "chunk_results.json")
    with open(results_path, "w") as f:
        json.dump(
            {k: v for k, v in result.items() if k != "state"}, f, cls=_Enc, indent=2
        )

    print(f"\nState saved: {state_path}")
    print(f"Results saved: {results_path}")

    # Print JSON for Claude to parse
    print(
        f"\n###CHUNK_RESULT### {json.dumps({k: v for k, v in result.items() if k != 'state'}, cls=_Enc)}"
    )


def _run_full(args, strategy_filter):
    """Run the full optimizer (original /spike behavior)."""
    if args.hours is None:
        print("ERROR: --hours is required for full runs (or use --chunk)")
        sys.exit(1)
    # Create run directory
    run_dir = create_run_dir()
    print(f"Run directory: {run_dir}")

    # Tee output to log file
    log_path = os.path.join(run_dir, "log.txt")
    tee = TeeWriter(log_path)
    sys.stdout = tee

    try:
        print(f"Spike Runner started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {args.hours}h | Pop: {args.pop_size} | Run dir: {run_dir}\n")

        # Refresh all local CSVs with latest data before optimizing
        from data.loader import refresh_all

        refresh_all()
        print()

        # Run the optimizer first, then validate before promoting anything.
        from search.evolve import _Enc, evolve, update_leaderboard
        from diagnostics.report import generate_report
        from diagnostics.roth_overlay import build_champion_overlay
        from validation.pipeline import run_validation_pipeline

        results = evolve(
            hours=args.hours,
            pop_size=args.pop_size,
            quick=args.quick,
            run_dir=run_dir,
            strategies=strategy_filter,
            bayesian=args.bayesian,
            publish_leaderboard=False,
            write_report=False,
        )

        raw_results_path = os.path.join(run_dir, "raw_results.json")
        with open(raw_results_path, "w") as f:
            json.dump(results, f, indent=2, cls=_Enc)
        print(f"[validate] Raw optimizer results saved: {raw_results_path}")

        validation = run_validation_pipeline(
            results,
            hours=args.hours,
            quick=args.quick,
        )
        results["raw_rankings"] = validation["raw_rankings"]
        results["validated_rankings"] = validation["validated_rankings"]
        results["rankings"] = validation["validated_rankings"]
        results["champion"] = validation["champion"]
        results["validation_summary"] = validation["validation_summary"]

        artifacts = {}
        champion = validation["champion"]
        overlay = None
        if champion:
            try:
                overlay = build_champion_overlay(
                    champion["strategy"],
                    champion["params"],
                )
                champion["overlay"] = overlay
                if results["validated_rankings"]:
                    results["validated_rankings"][0]["overlay"] = overlay
                overlay_path = os.path.join(run_dir, "overlay_report.json")
                with open(overlay_path, "w") as f:
                    json.dump(overlay, f, indent=2, cls=_Enc)
                artifacts["overlay_report"] = overlay_path
                print(f"[validate] Roth overlay: {overlay_path}")
            except Exception as exc:
                print(f"[validate] Warning: overlay simulation failed: {exc}")
            champ_tier = (
                (champion.get("validation") or {}).get("tier")
                or champion.get("tier")
                or "T2"
            )
            champ_share = (champion.get("metrics") or {}).get("share_multiple", 0.0)
            print(
                f"[validate] Champion: {champion['strategy']} "
                f"tier={champ_tier} share={champ_share:.3f}x "
                f"(fitness={champion['fitness']:.4f})"
            )
        else:
            print(
                "[validate] No fully validated champion. Emitting empty artifact bundle."
            )

        artifacts.update(
            _emit_run_artifacts(
                run_dir,
                results,
                encoder_cls=_Enc,
                overlay=overlay,
            )
        )
        _finalize_champion_certification(results, artifacts)
        _refresh_final_artifact_views(results, artifacts, encoder_cls=_Enc)
        results["artifacts"] = artifacts
        print(f"[artifacts] Trade ledger:       {artifacts['trade_ledger']}")
        print(f"[artifacts] Signal series:      {artifacts['signal_series']}")
        print(f"[artifacts] Equity curve:       {artifacts['equity_curve']}")
        print(f"[artifacts] Validation summary: {artifacts['validation_summary']}")
        print(f"[artifacts] Dashboard data:     {artifacts['dashboard_data']}")

        leaderboard_path = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
        previous_best = results.get("best_ever")
        if results["validated_rankings"]:
            leaderboard = update_leaderboard(
                {**results, "rankings": results["validated_rankings"]},
                leaderboard_path,
            )
            print(
                f"[validate] Leaderboard updated with {len(results['validated_rankings'])} "
                "fully validated entries"
            )
        else:
            leaderboard = _load_json(leaderboard_path) or []
            print(
                "[validate] Leaderboard unchanged because no entry passed full validation."
            )

        results_path = os.path.join(run_dir, "results.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, cls=_Enc)
        print(f"[validate] Validated results saved: {results_path}")

        report_text = generate_report(
            results,
            run_dir,
            leaderboard=leaderboard,
            previous_best=previous_best,
            history_stats=results.get("history_stats"),
        )
        report_path = os.path.join(run_dir, "report.md")
        with open(report_path, "w") as f:
            f.write(report_text)

        print(f"\n{'=' * 60}")
        print("SPIKE COMPLETE")
        print(f"{'=' * 60}")
        print(f"Report:      {report_path}")
        print(f"Results:     {results_path}")
        print(f"Raw results: {raw_results_path}")
        print(f"Log:         {log_path}")
        print(f"Leaderboard: {leaderboard_path}")
        print(f"Trades:      {artifacts['trade_ledger']}")
        print(f"Signals:     {artifacts['signal_series']}")
        print(f"Equity:      {artifacts['equity_curve']}")
        print(f"Validate:    {artifacts['validation_summary']}")
        print(f"Dashboard:   {artifacts['dashboard_data']}")
        if artifacts.get("overlay_report"):
            print(f"Overlay:     {artifacts['overlay_report']}")

        # Rebuild the HTML viz from the freshly updated leaderboard +
        # per-run dashboard_data.json files. Non-blocking: failures here
        # never abort the run — viz can always be rebuilt manually.
        try:
            backfill_script = os.path.join(
                PROJECT_ROOT, "scripts", "backfill_dashboard_artifacts.py"
            )
            if os.path.exists(backfill_script):
                rc = subprocess.call([sys.executable, backfill_script, "--top", "20"])
                if rc != 0:
                    print(
                        "[viz] backfill_dashboard_artifacts.py exited with "
                        f"code {rc} (non-fatal)"
                    )
            else:
                print(f"[viz] {backfill_script} not found; skipping artifact backfill")

            build_script = os.path.join(PROJECT_ROOT, "viz", "build_viz.py")
            if os.path.exists(build_script):
                rc = subprocess.call([sys.executable, build_script])
                if rc == 0:
                    viz_html = os.path.join(PROJECT_ROOT, "viz", "montauk-viz.html")
                    print(f"Viz:         {viz_html}")
                else:
                    print(f"[viz] build_viz.py exited with code {rc} (non-fatal)")
            else:
                print(f"[viz] {build_script} not found; skipping viz build")
        except Exception as exc:  # noqa: BLE001
            print(f"[viz] build_viz.py raised {exc} (non-fatal)")

    finally:
        sys.stdout = tee.terminal
        tee.close()

    print(f"\nDone. Report at: {os.path.join(run_dir, 'report.md')}")


if __name__ == "__main__":
    main()

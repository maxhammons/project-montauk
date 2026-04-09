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
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_run_dir() -> str:
    """Create the next sequentially numbered run directory: spike/runs/NNN."""
    base = os.path.join(PROJECT_ROOT, "spike", "runs")
    os.makedirs(base, exist_ok=True)

    # Find the highest existing run number
    existing = [
        d for d in os.listdir(base)
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
    parser.add_argument("--hours", type=float, required=True,
                        help="How long to run the optimizer")
    parser.add_argument("--pop-size", type=int, default=40,
                        help="Population per strategy per generation (default: 40)")
    parser.add_argument("--quick", action="store_true",
                        help="Shorter progress report intervals")
    parser.add_argument("--strategies", type=str, default=None,
                        help="Comma-separated list of strategy names to run (default: all)")
    parser.add_argument("--bayesian", action="store_true",
                        help="Use Bayesian optimization (Optuna TPE) instead of GA")
    parser.add_argument("--chunk", action="store_true",
                        help="Run a single timed chunk (for /spike v2 iterative loop)")
    parser.add_argument("--minutes", type=float, default=20.0,
                        help="Chunk duration in minutes (default: 20, requires --chunk)")
    parser.add_argument("--state-file", type=str, default=None,
                        help="Path to state JSON from previous chunk (requires --chunk)")
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

    from evolve import evolve_chunk
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
            if hasattr(o, 'item'):
                return o.item()
            return super().default(o)

    with open(state_path, "w") as f:
        json.dump(result["state"], f, cls=_Enc)

    # Save chunk results
    results_path = os.path.join(run_dir, "chunk_results.json")
    with open(results_path, "w") as f:
        json.dump({k: v for k, v in result.items() if k != "state"}, f, cls=_Enc, indent=2)

    print(f"\nState saved: {state_path}")
    print(f"Results saved: {results_path}")

    # Print JSON for Claude to parse
    print(f"\n###CHUNK_RESULT### {json.dumps({k: v for k, v in result.items() if k != 'state'}, cls=_Enc)}")


def _run_full(args, strategy_filter):
    """Run the full optimizer (original /spike behavior)."""
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
        from data import refresh_all
        refresh_all()
        print()

        # Run the optimizer
        from evolve import evolve
        results = evolve(
            hours=args.hours,
            pop_size=args.pop_size,
            quick=args.quick,
            run_dir=run_dir,
            strategies=strategy_filter,
            bayesian=args.bayesian,
        )

        print(f"\n{'='*60}")
        print(f"SPIKE COMPLETE")
        print(f"{'='*60}")
        print(f"Report:      {os.path.join(run_dir, 'report.md')}")
        print(f"Results:     {os.path.join(run_dir, 'results.json')}")
        print(f"Log:         {log_path}")
        print(f"Leaderboard: {os.path.join(PROJECT_ROOT, 'spike', 'leaderboard.json')}")

    finally:
        sys.stdout = tee.terminal
        tee.close()

    print(f"\nDone. Report at: {os.path.join(run_dir, 'report.md')}")


if __name__ == "__main__":
    main()

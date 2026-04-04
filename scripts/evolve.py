#!/usr/bin/env python3
"""
Multi-strategy evolutionary optimizer for Project Montauk.

Tests ALL registered strategies, evolves parameters for each, and
compares everything against the current best. The goal is simple:
beat buy-and-hold on TECL with ≤3 trades per year.

Usage:
  python3 scripts/evolve.py --hours 8               # Full overnight run
  python3 scripts/evolve.py --hours 1 --quick        # Quick test
  python3 scripts/evolve.py --list                    # Show registered strategies
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import random
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import get_tecl_data
from strategy_engine import Indicators, backtest, BacktestResult

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(PROJECT_ROOT, "remote", "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "tested-configs.jsonl")


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        if isinstance(o, np.ndarray): return o.tolist()
        return super().default(o)


# ─────────────────────────────────────────────────────────────────────────────
# Config hashing & history — don't repeat yourself across runs
# ─────────────────────────────────────────────────────────────────────────────

def config_hash(strategy_name: str, params: dict) -> str:
    """Deterministic hash for a strategy + params combo."""
    # Sort params, round floats to avoid floating point noise
    clean = {}
    for k, v in sorted(params.items()):
        if isinstance(v, float):
            clean[k] = round(v, 4)
        else:
            clean[k] = v
    key = f"{strategy_name}:{json.dumps(clean, sort_keys=True)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_history() -> dict:
    """
    Load tested configs from JSONL history file.
    Returns dict: {config_hash: {strategy, params, fitness, metrics, date}}
    """
    history = {}
    if not os.path.exists(HISTORY_FILE):
        return history
    try:
        with open(HISTORY_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                h = entry.get("hash", "")
                # Keep the best result for each hash
                if h not in history or entry.get("fitness", 0) > history[h].get("fitness", 0):
                    history[h] = entry
    except Exception as e:
        print(f"[history] Warning: failed to load history: {e}")
    return history


def save_history_batch(entries: list):
    """Append a batch of tested configs to the JSONL history file."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, "a") as f:
            for entry in entries:
                f.write(json.dumps(entry, cls=_Enc) + "\n")
    except Exception as e:
        print(f"[history] Warning: failed to save history: {e}")


def get_top_from_history(history: dict, strategy_name: str, n: int = 8) -> list:
    """Get top N param sets for a strategy from history."""
    candidates = [
        entry for entry in history.values()
        if entry.get("strategy") == strategy_name and entry.get("fitness", 0) > 0
    ]
    candidates.sort(key=lambda x: x.get("fitness", 0), reverse=True)
    return [c["params"] for c in candidates[:n]]


def update_leaderboard(results: dict, leaderboard_path: str) -> list:
    """
    Update the all-time top-20 leaderboard.
    Returns the updated leaderboard list.
    """
    # Load strategy descriptions for context
    try:
        from strategies import STRATEGY_DESCRIPTIONS
    except ImportError:
        STRATEGY_DESCRIPTIONS = {}

    # Load existing
    leaderboard = []
    if os.path.exists(leaderboard_path):
        try:
            with open(leaderboard_path) as f:
                leaderboard = json.load(f)
        except Exception:
            pass

    # Add this run's rankings
    date = results.get("date", datetime.now().strftime("%Y-%m-%d"))
    for entry in results.get("rankings", []):
        if not entry.get("metrics"):
            continue
        lb_entry = {
            "strategy": entry["strategy"],
            "fitness": entry["fitness"],
            "params": entry.get("params", {}),
            "metrics": entry["metrics"],
            "date": date,
        }
        # Include description so Claude can understand the strategy from leaderboard alone
        desc = STRATEGY_DESCRIPTIONS.get(entry["strategy"])
        if desc:
            lb_entry["description"] = desc
        leaderboard.append(lb_entry)

    # Deduplicate: keep best per config hash
    seen = {}
    for entry in leaderboard:
        h = config_hash(entry["strategy"], entry.get("params", {}))
        if h not in seen or entry["fitness"] > seen[h]["fitness"]:
            seen[h] = entry
    leaderboard = sorted(seen.values(), key=lambda x: x["fitness"], reverse=True)[:20]

    # Save
    os.makedirs(os.path.dirname(leaderboard_path), exist_ok=True)
    with open(leaderboard_path, "w") as f:
        json.dump(leaderboard, f, indent=2, cls=_Enc)

    return leaderboard


# ─────────────────────────────────────────────────────────────────────────────
# Fitness — directly targets what you want
# ─────────────────────────────────────────────────────────────────────────────

MAX_TRADES_PER_YEAR = 3.0

def fitness(result: BacktestResult) -> float:
    """
    Score a strategy result. Higher = better.

    Primary: vs_bah_multiple (beat buy-and-hold)
    Guard: max 3 trades/year, drawdown penalty, min trade count
    """
    if result is None or result.num_trades < 3:
        return 0.0

    bah = max(result.vs_bah_multiple, 0.001)

    # Drawdown penalty: 50% DD → 0.75x, 80% DD → 0.60x
    dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)

    # Trade frequency penalty: hard cap at 3/yr, soft penalty above 2/yr
    if result.trades_per_year > MAX_TRADES_PER_YEAR:
        freq_penalty = max(0.1, 1.0 - (result.trades_per_year - MAX_TRADES_PER_YEAR) * 0.3)
    else:
        freq_penalty = 1.0

    return bah * dd_penalty * freq_penalty


# ─────────────────────────────────────────────────────────────────────────────
# Parameter generation
# ─────────────────────────────────────────────────────────────────────────────

def random_params(space: dict) -> dict:
    """Generate random parameters within a strategy's search space."""
    params = {}
    for name, (lo, hi, step, typ) in space.items():
        n_steps = int(round((hi - lo) / step))
        val = lo + random.randint(0, max(1, n_steps)) * step
        params[name] = int(round(val)) if typ == int else round(val, 4)
    return params


def mutate_params(params: dict, space: dict, rate: float = 0.2) -> dict:
    result = params.copy()
    for name, (lo, hi, step, typ) in space.items():
        if random.random() >= rate:
            continue
        current = result.get(name, (lo + hi) / 2)
        delta = random.choice([-2, -1, 1, 2]) * step
        val = max(lo, min(hi, current + delta))
        result[name] = int(round(val)) if typ == int else round(val, 4)
    return result


def crossover_params(p1: dict, p2: dict) -> dict:
    child = {}
    for key in set(list(p1.keys()) + list(p2.keys())):
        child[key] = random.choice([p1, p2]).get(key, p1.get(key))
    return child


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(ind: Indicators, df, strategy_fn, params: dict, name: str) -> tuple:
    """Run one strategy config, return (fitness_score, BacktestResult)."""
    try:
        entries, exits, labels = strategy_fn(ind, params)
        cooldown = params.get("cooldown", 0)
        result = backtest(df, entries, exits, labels,
                          cooldown_bars=cooldown, strategy_name=name)
        return fitness(result), result
    except Exception:
        return 0.0, None


def evolve(hours: float = 8.0, pop_size: int = 40, quick: bool = False,
           run_dir: str | None = None) -> dict:
    """
    Run the evolutionary optimizer. Returns the results dict.

    Parameters
    ----------
    hours : how long to run
    pop_size : population per strategy per generation
    quick : shorter report intervals
    run_dir : directory to save results (optional, for spike_runner)
    """
    # Late import to pick up any new strategies added between runs
    from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS

    start_time = time.time()
    end_time = start_time + hours * 3600

    print(f"=== Montauk Multi-Strategy Optimizer ===")
    print(f"Duration: {hours}h | Pop: {pop_size}/strategy | Strategies: {len(STRATEGY_REGISTRY)}")
    print(f"Constraint: ≤{MAX_TRADES_PER_YEAR} trades/year")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    # ── Load history for seeding & dedup ──
    history = load_history()
    dedup_cache = {}  # hash -> fitness (skip re-evaluation)
    for h, entry in history.items():
        if entry.get("fitness", 0) > 0:
            dedup_cache[h] = entry["fitness"]
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0}
    new_history_entries = []  # batch-save at end

    if history:
        print(f"[history] Loaded {len(history):,} configs from previous runs")
        print(f"[history] Dedup cache: {len(dedup_cache):,} configs with known fitness\n")

    # ── Baseline: run each strategy with default (midpoint) params ──
    print("── Baselines ──")
    baselines = {}
    for name, fn in STRATEGY_REGISTRY.items():
        space = STRATEGY_PARAMS.get(name, {})
        default_params = {k: (lo + hi) / 2 for k, (lo, hi, step, typ) in space.items()}
        # Round ints
        for k, (lo, hi, step, typ) in space.items():
            if typ == int:
                default_params[k] = int(round(default_params[k]))
        score, result = evaluate(ind, df, fn, default_params, name)
        baselines[name] = {"score": score, "result": result, "params": default_params}
        if result:
            print(f"  {name:<22} score={score:.4f}  bah={result.vs_bah_multiple:.3f}x  "
                  f"trades/yr={result.trades_per_year:.1f}  CAGR={result.cagr_pct:.1f}%  "
                  f"DD={result.max_drawdown_pct:.1f}%")
        else:
            print(f"  {name:<22} FAILED")

    # ── Initialize populations (one per strategy) ──
    # Seed with historical winners + defaults + random
    populations = {}
    max_seed = max(2, int(pop_size * 0.2))  # 20% from history
    for name in STRATEGY_REGISTRY:
        space = STRATEGY_PARAMS.get(name, {})
        pop = [baselines[name]["params"].copy()]

        # Seed from history
        hist_winners = get_top_from_history(history, name, n=max_seed)
        for hw in hist_winners:
            if len(pop) < pop_size:
                pop.append(hw)
        if hist_winners:
            history_stats["seeded_per_strategy"] = max(
                history_stats["seeded_per_strategy"], len(hist_winners))

        # Fill rest with random
        while len(pop) < pop_size:
            pop.append(random_params(space))
        populations[name] = pop

    # ── Evolution ──
    best_ever_score = 0.0
    best_ever_name = ""
    best_ever_params = {}
    best_ever_result = None

    # Load previous best
    best_path = os.path.join(PROJECT_ROOT, "remote", "best-ever.json")
    if os.path.exists(best_path):
        try:
            with open(best_path) as f:
                prev = json.load(f)
            if prev.get("fitness", 0) > best_ever_score:
                best_ever_score = prev["fitness"]
                best_ever_name = prev.get("strategy", "")
                best_ever_params = prev.get("params", {})
                print(f"\nLoaded best-ever: {best_ever_name} fitness={best_ever_score:.4f}")
        except Exception:
            pass

    generation = 0
    total_evals = 0
    last_report = start_time
    report_interval = 60 if quick else 300
    strategy_bests = {name: (0.0, {}, None) for name in STRATEGY_REGISTRY}
    convergence_history = []

    print(f"\n── Evolving ──")

    while time.time() < end_time:
        generation += 1

        for strat_name, fn in STRATEGY_REGISTRY.items():
            space = STRATEGY_PARAMS.get(strat_name, {})
            pop = populations[strat_name]

            # Evaluate with dedup cache
            scored = []
            for params in pop:
                h = config_hash(strat_name, params)
                if h in dedup_cache:
                    # Reuse cached fitness (no result object — just score)
                    scored.append((dedup_cache[h], params, None))
                    history_stats["cached_configs"] += 1
                else:
                    score, result = evaluate(ind, df, fn, params, strat_name)
                    total_evals += 1
                    scored.append((score, params, result))
                    dedup_cache[h] = score
                    history_stats["new_configs"] += 1
                    # Queue for history save
                    if result:
                        new_history_entries.append({
                            "hash": h,
                            "strategy": strat_name,
                            "params": params,
                            "fitness": round(score, 4),
                            "metrics": {
                                "vs_bah": round(result.vs_bah_multiple, 4),
                                "cagr": round(result.cagr_pct, 2),
                                "max_dd": round(result.max_drawdown_pct, 1),
                                "mar": round(result.mar_ratio, 3),
                                "trades_yr": round(result.trades_per_year, 1),
                            },
                            "date": datetime.now().strftime("%Y-%m-%d"),
                        })
            scored.sort(key=lambda x: x[0], reverse=True)

            # Update strategy best
            if scored[0][0] > strategy_bests[strat_name][0]:
                strategy_bests[strat_name] = (scored[0][0], scored[0][1], scored[0][2])

            # Update global best
            if scored[0][0] > best_ever_score:
                best_ever_score = scored[0][0]
                best_ever_name = strat_name
                best_ever_params = scored[0][1].copy()
                best_ever_result = scored[0][2]
                save_best(best_path, best_ever_score, best_ever_name,
                          best_ever_params, best_ever_result)

            # Selection + reproduction
            n_elite = max(2, int(pop_size * 0.2))
            elites = [s[1] for s in scored[:n_elite]]
            new_pop = list(elites)

            # Crossover
            for _ in range(pop_size // 3):
                p1, p2 = random.sample(elites, min(2, len(elites)))
                new_pop.append(crossover_params(p1, p2))

            # Mutation
            stag = generation - getattr(evolve, '_last_improve', {}).get(strat_name, 0)
            mut_rate = 0.15 if stag < 30 else 0.30 if stag < 80 else 0.50
            while len(new_pop) < pop_size:
                parent = random.choice(elites)
                new_pop.append(mutate_params(parent, space, rate=mut_rate))

            # Wild card injection
            if generation % 15 == 0:
                new_pop[-1] = random_params(space)

            populations[strat_name] = new_pop[:pop_size]

        # Track convergence
        gen_best = max(strategy_bests[s][0] for s in strategy_bests)
        convergence_history.append((generation, round(gen_best, 4)))

        # Progress report
        now = time.time()
        if now - last_report >= report_interval:
            remaining = (end_time - now) / 3600
            per_sec = total_evals / (now - start_time)
            print(f"Gen {generation:>5}: BEST={best_ever_score:.4f} ({best_ever_name})  "
                  f"evals={total_evals:,} ({per_sec:.0f}/s)  {remaining:.1f}h left")
            for s, (sc, _, res) in sorted(strategy_bests.items(), key=lambda x: -x[1][0]):
                if res:
                    print(f"    {s:<22} {sc:.4f}  bah={res.vs_bah_multiple:.3f}x  "
                          f"t/yr={res.trades_per_year:.1f}  DD={res.max_drawdown_pct:.1f}%")
            last_report = now

    # ── Final report ──
    elapsed = (time.time() - start_time) / 3600

    # Rank all strategies
    rankings = sorted(strategy_bests.items(), key=lambda x: -x[1][0])

    # Always show 8.2.1 baseline for comparison
    baseline_821 = baselines.get("montauk_821", {})
    bl_result = baseline_821.get("result")

    print(f"\n{'='*60}")
    print(f"DONE — {elapsed:.1f}h, {total_evals:,} evals, {generation} generations")
    print(f"{'='*60}")

    if bl_result:
        print(f"\n── 8.2.1 Baseline (the strategy to beat) ──")
        print(f"  vs B&H={bl_result.vs_bah_multiple:.3f}x  CAGR={bl_result.cagr_pct:.1f}%  "
              f"DD={bl_result.max_drawdown_pct:.1f}%  trades/yr={bl_result.trades_per_year:.1f}")

    print(f"\n── Strategy Rankings (vs 8.2.1) ──")
    for rank, (name, (score, params, result)) in enumerate(rankings, 1):
        if result:
            beat_str = ""
            if bl_result and bl_result.vs_bah_multiple > 0:
                improvement = (result.vs_bah_multiple / bl_result.vs_bah_multiple - 1) * 100
                beat_str = f"  {'BEATS' if result.vs_bah_multiple > bl_result.vs_bah_multiple else 'loses to'} 8.2.1 by {improvement:+.0f}%"
            print(f"  #{rank} {name:<22} fitness={score:.4f}  bah={result.vs_bah_multiple:.3f}x  "
                  f"t/yr={result.trades_per_year:.1f}  CAGR={result.cagr_pct:.1f}%  "
                  f"DD={result.max_drawdown_pct:.1f}%  MAR={result.mar_ratio:.2f}{beat_str}")
            print(f"     params: {json.dumps({k: v for k, v in params.items() if k != 'cooldown'}, cls=_Enc)}")
            if result.trades:
                print(f"     trades: {result.num_trades} ({result.trades_per_year:.1f}/yr)")
                for t in result.trades[:5]:
                    print(f"       {t.entry_date} → {t.exit_date}  {t.pnl_pct:+.1f}%  {t.exit_reason}")
                if len(result.trades) > 5:
                    print(f"       ... +{len(result.trades)-5} more")

    # ── Re-evaluate strategy bests that were cached (no result object) ──
    # Needed for full metrics in the final report
    for strat_name in list(strategy_bests.keys()):
        score, params, result = strategy_bests[strat_name]
        if result is None and score > 0 and strat_name in STRATEGY_REGISTRY:
            _, result = evaluate(ind, df, STRATEGY_REGISTRY[strat_name], params, strat_name)
            strategy_bests[strat_name] = (score, params, result)

    # Re-sort after re-evaluation
    rankings = sorted(strategy_bests.items(), key=lambda x: -x[1][0])

    # ── Save history ──
    if new_history_entries:
        save_history_batch(new_history_entries)
        print(f"\n[history] Saved {len(new_history_entries):,} new configs to history")

    history_stats["total_history"] = len(dedup_cache)

    # ── Update leaderboard ──
    leaderboard_path = os.path.join(HISTORY_DIR, "leaderboard.json")

    # Save results
    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "elapsed_hours": round(elapsed, 2),
        "total_evaluations": total_evals,
        "generations": generation,
        "constraint": f"<={MAX_TRADES_PER_YEAR} trades/yr",
        "history_stats": history_stats,
        "rankings": [
            {
                "rank": i + 1,
                "strategy": name,
                "fitness": round(score, 4),
                "params": params,
                "metrics": {
                    "vs_bah": round(result.vs_bah_multiple, 4),
                    "cagr": round(result.cagr_pct, 2),
                    "max_dd": round(result.max_drawdown_pct, 1),
                    "mar": round(result.mar_ratio, 3),
                    "trades": result.num_trades,
                    "trades_yr": round(result.trades_per_year, 1),
                    "win_rate": round(result.win_rate_pct, 1),
                    "exit_reasons": result.exit_reasons,
                } if result else None,
                "trades": [
                    {
                        "entry_date": t.entry_date,
                        "exit_date": t.exit_date,
                        "pnl_pct": round(t.pnl_pct, 1),
                        "exit_reason": t.exit_reason,
                        "bars_held": t.bars_held,
                    }
                    for t in (result.trades if result else [])
                ],
            }
            for i, (name, (score, params, result)) in enumerate(rankings)
        ],
        "best_ever": {
            "strategy": best_ever_name,
            "fitness": round(best_ever_score, 4),
            "params": best_ever_params,
        },
    }

    leaderboard = update_leaderboard(results, leaderboard_path)

    # Save results JSON
    date_str = datetime.now().strftime("%Y-%m-%d")
    if run_dir:
        out_path = os.path.join(run_dir, "results.json")
    else:
        out_path = os.path.join(PROJECT_ROOT, "remote", f"evolve-results-{date_str}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, cls=_Enc)
    print(f"\nResults: {out_path}")

    # Generate markdown report
    try:
        from report import generate_report
        prev_best_snapshot = {
            "strategy": best_ever_name,
            "fitness": best_ever_score,
        } if best_ever_score > 0 else None
        report_dir = run_dir or os.path.join(PROJECT_ROOT, "remote", "runs", date_str)
        report_text = generate_report(
            results, report_dir,
            leaderboard=leaderboard,
            previous_best=prev_best_snapshot,
            history_stats=history_stats,
        )
        print(f"Report: {os.path.join(report_dir, 'report.md')}")
    except Exception as e:
        print(f"[report] Warning: report generation failed: {e}")

    print(f"\n###JSON### {json.dumps(results, cls=_Enc)}")

    return results


def save_best(path, score, name, params, result):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "fitness": round(score, 4),
        "strategy": name,
        "params": params,
        "vs_bah": round(result.vs_bah_multiple, 4) if result else 0,
        "cagr": round(result.cagr_pct, 2) if result else 0,
        "max_dd": round(result.max_drawdown_pct, 1) if result else 0,
        "trades_yr": round(result.trades_per_year, 1) if result else 0,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_Enc)


def main():
    parser = argparse.ArgumentParser(description="Montauk Multi-Strategy Optimizer")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--pop-size", type=int, default=40)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--list", action="store_true", help="List strategies and exit")
    args = parser.parse_args()

    if args.list:
        from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
        for name in STRATEGY_REGISTRY:
            space = STRATEGY_PARAMS.get(name, {})
            print(f"  {name:<22} {len(space)} params")
        return

    evolve(hours=args.hours, pop_size=args.pop_size, quick=args.quick)


if __name__ == "__main__":
    main()

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
import signal
import sys
import time
import random
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import get_tecl_data
from strategy_engine import Indicators, backtest, BacktestResult

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR = os.path.join(PROJECT_ROOT, "spike")
HISTORY_FILE = os.path.join(HISTORY_DIR, "tested-configs.jsonl")  # legacy, no longer written
HASH_INDEX_FILE = os.path.join(HISTORY_DIR, "hash-index.json")   # compact: {hash: fitness}


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


def load_hash_index() -> dict:
    """
    Load the compact hash index: {config_hash: fitness}.
    Falls back to migrating from legacy JSONL if the index doesn't exist yet.
    """
    # Try compact index first
    if os.path.exists(HASH_INDEX_FILE):
        try:
            with open(HASH_INDEX_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"[history] Warning: failed to load hash index: {e}")
            return {}

    # Migrate from legacy JSONL if it exists
    if os.path.exists(HISTORY_FILE):
        print("[history] Migrating legacy JSONL to compact hash index...")
        index = {}
        try:
            with open(HISTORY_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    h = entry.get("hash", "")
                    fit = entry.get("fitness", 0)
                    if h and (h not in index or fit > index[h]):
                        index[h] = round(fit, 4)
            save_hash_index(index)
            print(f"[history] Migrated {len(index):,} unique configs to hash-index.json")
            return index
        except Exception as e:
            print(f"[history] Warning: migration failed: {e}")
            return {}

    return {}


def save_hash_index(index: dict):
    """Save the compact hash index to disk. Prunes zero-fitness entries to control size."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    # Only keep configs that actually produced results (fitness > 0).
    # Zero-fitness configs failed fast (< 3 trades) and are cheap to re-evaluate.
    # This keeps the index under ~20 MB even after many runs.
    pruned = {h: f for h, f in index.items() if f > 0}
    dropped = len(index) - len(pruned)
    if dropped > 0:
        print(f"[history] Pruned {dropped:,} zero-fitness entries from hash index")
    try:
        with open(HASH_INDEX_FILE, "w") as f:
            json.dump(pruned, f, cls=_Enc)
    except Exception as e:
        print(f"[history] Warning: failed to save hash index: {e}")


def get_top_from_leaderboard(leaderboard_path: str, strategy_name: str, n: int = 8) -> list:
    """Get top N param sets for a strategy from the leaderboard."""
    if not os.path.exists(leaderboard_path):
        return []
    try:
        with open(leaderboard_path) as f:
            lb = json.load(f)
        candidates = [
            entry for entry in lb
            if entry.get("strategy") == strategy_name and entry.get("fitness", 0) > 0
        ]
        candidates.sort(key=lambda x: x.get("fitness", 0), reverse=True)
        return [c["params"] for c in candidates[:n]]
    except Exception:
        return []


CONVERGE_RUNS = 3  # auto-flag as converged after this many runs with no improvement
PRUNE_RUNS = 2     # skip strategies below baseline after this many runs
BASELINE_FLOOR = 0.05  # minimum fitness to survive pruning (approx montauk_821 default)


def update_leaderboard(results: dict, leaderboard_path: str) -> list:
    """
    Update the all-time top-20 leaderboard with convergence tracking.

    Each strategy (by name) tracks:
    - best_fitness: highest fitness ever seen for this strategy name
    - runs_without_improvement: consecutive runs where this strategy didn't beat its best
    - converged: True when runs_without_improvement >= CONVERGE_RUNS

    Convergence is per-strategy-name (not per-config). Once a strategy is converged,
    Claude should skip optimizing it and focus effort elsewhere.

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

    # Build per-strategy convergence state from existing leaderboard
    # Track the best entry per strategy name (highest fitness)
    strategy_state = {}  # strategy_name -> {best_fitness, runs_without_improvement, converged}
    for entry in leaderboard:
        name = entry["strategy"]
        if name not in strategy_state:
            strategy_state[name] = {
                "best_fitness": entry.get("fitness", 0),
                "runs_without_improvement": entry.get("runs_without_improvement", 0),
                "converged": entry.get("converged", False),
            }
        else:
            # Keep highest fitness
            if entry.get("fitness", 0) > strategy_state[name]["best_fitness"]:
                strategy_state[name]["best_fitness"] = entry["fitness"]

    # Check this run's results against previous bests
    date = results.get("date", datetime.now().strftime("%Y-%m-%d"))
    strategies_in_run = set()
    for entry in results.get("rankings", []):
        if not entry.get("metrics"):
            continue
        name = entry["strategy"]
        strategies_in_run.add(name)
        new_fitness = entry["fitness"]

        if name not in strategy_state:
            strategy_state[name] = {
                "best_fitness": new_fitness,
                "runs_without_improvement": 0,
                "converged": False,
            }
        else:
            prev_best = strategy_state[name]["best_fitness"]
            # Improvement threshold: must beat previous best by >0.1% to count
            if new_fitness > prev_best * 1.001:
                strategy_state[name]["best_fitness"] = new_fitness
                strategy_state[name]["runs_without_improvement"] = 0
                strategy_state[name]["converged"] = False
            else:
                strategy_state[name]["runs_without_improvement"] += 1

        # Auto-converge check (only if not manually unconverged)
        rwi = strategy_state[name]["runs_without_improvement"]
        if rwi >= CONVERGE_RUNS and not strategy_state[name].get("manual_unconverge"):
            if not strategy_state[name]["converged"]:
                strategy_state[name]["converged"] = True
                print(f"[leaderboard] {name} auto-converged after {rwi} runs with no improvement")

        # Build leaderboard entry
        lb_entry = {
            "strategy": name,
            "fitness": new_fitness,
            "params": entry.get("params", {}),
            "metrics": entry["metrics"],
            "date": date,
            "converged": strategy_state[name]["converged"],
            "runs_without_improvement": strategy_state[name]["runs_without_improvement"],
        }
        desc = STRATEGY_DESCRIPTIONS.get(name)
        if desc:
            lb_entry["description"] = desc
        leaderboard.append(lb_entry)

    # Increment runs_without_improvement for strategies NOT in this run
    # (they were registered but produced no results — still counts as no improvement)
    for name in strategy_state:
        if name not in strategies_in_run:
            strategy_state[name]["runs_without_improvement"] += 1
            if strategy_state[name]["runs_without_improvement"] >= CONVERGE_RUNS:
                strategy_state[name]["converged"] = True

    # Propagate convergence state to existing leaderboard entries
    for entry in leaderboard:
        name = entry["strategy"]
        if name in strategy_state:
            entry["converged"] = strategy_state[name]["converged"]
            entry["runs_without_improvement"] = strategy_state[name]["runs_without_improvement"]

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


def set_converged(leaderboard_path: str, strategy_name: str, converged: bool) -> bool:
    """Manually flag/unflag a strategy as converged. Returns True on success."""
    if not os.path.exists(leaderboard_path):
        return False
    with open(leaderboard_path) as f:
        leaderboard = json.load(f)
    found = False
    for entry in leaderboard:
        if entry["strategy"] == strategy_name:
            entry["converged"] = converged
            if not converged:
                entry["runs_without_improvement"] = 0
                entry["manual_unconverge"] = True
            found = True
    if found:
        with open(leaderboard_path, "w") as f:
            json.dump(leaderboard, f, indent=2, cls=_Enc)
    return found


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
    print(f"Duration: {hours}h | Pop: {pop_size}/strategy | Registered: {len(STRATEGY_REGISTRY)}")
    print(f"Constraint: ≤{MAX_TRADES_PER_YEAR} trades/year")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    # ── Load hash index for dedup ──
    dedup_cache = load_hash_index()  # hash -> fitness
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0}

    if dedup_cache:
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

    # ── Auto-prune underperformers ──
    # Skip strategies that have been in 2+ runs and never cracked the fitness floor
    leaderboard_path = os.path.join(HISTORY_DIR, "leaderboard.json")
    prune_info = {}  # strategy -> {runs, best_fitness}
    if os.path.exists(leaderboard_path):
        try:
            with open(leaderboard_path) as f:
                lb = json.load(f)
            for entry in lb:
                name = entry["strategy"]
                rwi = entry.get("runs_without_improvement", 0)
                fit = entry.get("fitness", 0)
                if name not in prune_info or fit > prune_info[name]["best_fitness"]:
                    prune_info[name] = {
                        "total_runs": rwi + 1,  # rwi=0 means at least 1 run
                        "best_fitness": fit,
                    }
        except Exception:
            pass

    skipped_strategies = set()
    # Always keep montauk_821 (baseline) and never skip strategies not yet on leaderboard
    for name in list(STRATEGY_REGISTRY.keys()):
        if name == "montauk_821":
            continue
        info = prune_info.get(name)
        if info and info["total_runs"] >= PRUNE_RUNS and info["best_fitness"] < BASELINE_FLOOR:
            skipped_strategies.add(name)

    if skipped_strategies:
        print(f"\n── Auto-pruned ({len(skipped_strategies)} strategies below fitness floor {BASELINE_FLOOR} after {PRUNE_RUNS}+ runs) ──")
        for name in sorted(skipped_strategies):
            best = prune_info[name]["best_fitness"]
            print(f"  SKIP {name:<22} best={best:.4f} (below {BASELINE_FLOOR})")
        print()

    active_strategies = {k: v for k, v in STRATEGY_REGISTRY.items() if k not in skipped_strategies}
    print(f"Active strategies: {len(active_strategies)}/{len(STRATEGY_REGISTRY)}")

    # ── Initialize populations (one per strategy) ──
    # Seed with historical winners + defaults + random
    populations = {}
    max_seed = max(2, int(pop_size * 0.2))  # 20% from history
    for name in active_strategies:
        space = STRATEGY_PARAMS.get(name, {})
        pop = [baselines[name]["params"].copy()]

        # Seed from leaderboard (top configs from previous runs)
        lb_winners = get_top_from_leaderboard(leaderboard_path, name, n=max_seed)
        for lw in lb_winners:
            if len(pop) < pop_size:
                pop.append(lw)
        if lb_winners:
            history_stats["seeded_per_strategy"] = max(
                history_stats["seeded_per_strategy"], len(lb_winners))

        # Fill rest with random
        while len(pop) < pop_size:
            pop.append(random_params(space))
        populations[name] = pop

    # ── Evolution ──
    best_ever_score = 0.0
    best_ever_name = ""
    best_ever_params = {}
    best_ever_result = None

    # Load previous best from leaderboard (sorted by fitness, [0] = best)
    if os.path.exists(leaderboard_path):
        try:
            with open(leaderboard_path) as f:
                lb = json.load(f)
            if lb and lb[0].get("fitness", 0) > best_ever_score:
                best_ever_score = lb[0]["fitness"]
                best_ever_name = lb[0].get("strategy", "")
                best_ever_params = lb[0].get("params", {})
                print(f"\nLoaded best-ever: {best_ever_name} fitness={best_ever_score:.4f}")
        except Exception:
            pass

    generation = 0
    total_evals = 0
    last_report = start_time
    report_interval = 60 if quick else 300
    strategy_bests = {name: (0.0, {}, None) for name in active_strategies}
    convergence_history = []

    # Allow Ctrl+C or kill to save results gracefully
    _interrupted = [False]
    def _handle_signal(sig, frame):
        print(f"\n[interrupted — saving results...]")
        _interrupted[0] = True
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    print(f"\n── Evolving ──")

    while time.time() < end_time and not _interrupted[0]:
        generation += 1

        for strat_name, fn in active_strategies.items():
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
        if result is None and score > 0 and strat_name in active_strategies:
            _, result = evaluate(ind, df, active_strategies[strat_name], params, strat_name)
            strategy_bests[strat_name] = (score, params, result)

    # Re-sort after re-evaluation
    rankings = sorted(strategy_bests.items(), key=lambda x: -x[1][0])

    # ── Save hash index ──
    save_hash_index(dedup_cache)
    print(f"\n[history] Saved hash index: {len(dedup_cache):,} unique configs")

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
        # Even without spike_runner, save into the runs/ structure
        fallback_dir = os.path.join(PROJECT_ROOT, "spike", "runs", date_str)
        os.makedirs(fallback_dir, exist_ok=True)
        out_path = os.path.join(fallback_dir, "results.json")
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
        report_dir = run_dir or os.path.join(PROJECT_ROOT, "spike", "runs", date_str)
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



def main():
    parser = argparse.ArgumentParser(description="Montauk Multi-Strategy Optimizer")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--pop-size", type=int, default=40)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--list", action="store_true", help="List strategies and exit")
    parser.add_argument("--converge", type=str, help="Flag strategy as converged")
    parser.add_argument("--unconverge", type=str, help="Unflag strategy (resume optimization)")
    args = parser.parse_args()

    if args.converge:
        lb_path = os.path.join(HISTORY_DIR, "leaderboard.json")
        if set_converged(lb_path, args.converge, True):
            print(f"Flagged '{args.converge}' as converged")
        else:
            print(f"Strategy '{args.converge}' not found on leaderboard")
        return

    if args.unconverge:
        lb_path = os.path.join(HISTORY_DIR, "leaderboard.json")
        if set_converged(lb_path, args.unconverge, False):
            print(f"Unflagged '{args.unconverge}' — will be optimized again")
        else:
            print(f"Strategy '{args.unconverge}' not found on leaderboard")
        return

    if args.list:
        from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
        for name in STRATEGY_REGISTRY:
            space = STRATEGY_PARAMS.get(name, {})
            print(f"  {name:<22} {len(space)} params")
        return

    evolve(hours=args.hours, pop_size=args.pop_size, quick=args.quick)


if __name__ == "__main__":
    main()

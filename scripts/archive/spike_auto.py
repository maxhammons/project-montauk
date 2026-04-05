#!/usr/bin/env python3
"""
Autonomous evolutionary strategy optimizer for Project Montauk.

Runs for a configurable duration, testing thousands of parameter combinations
using an evolutionary algorithm (selection, crossover, mutation). All optimization
logic lives here — Claude just launches this and reads the results.

Usage:
  python3 scripts/spike_auto.py --hours 8                    # Full overnight run
  python3 scripts/spike_auto.py --hours 1 --pop-size 30      # Quick test
  python3 scripts/spike_auto.py --hours 8 --no-sweep          # Skip initial sweep phase
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import random
from datetime import datetime

import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    """Handle numpy types in JSON output."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import get_tecl_data
from backtest_engine import StrategyParams, run_backtest
from validation import validate_candidate

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# Search space: (min, max, step, type)
# ─────────────────────────────────────────────────────────────────────────────

SEARCH_SPACE = {
    "short_ema_len":           (5, 25, 2, int),
    "med_ema_len":             (15, 60, 5, int),
    "long_ema_len":            (200, 800, 50, int),
    "trend_ema_len":           (30, 120, 10, int),
    "slope_lookback":          (3, 20, 2, int),
    "min_trend_slope":         (-0.5, 0.5, 0.1, float),
    "triple_ema_len":          (100, 400, 50, int),
    "triple_slope_lookback":   (1, 5, 1, int),
    "range_len":               (20, 100, 10, int),
    "max_range_pct":           (10.0, 50.0, 5.0, float),
    "sell_confirm_bars":       (1, 5, 1, int),
    "sell_buffer_pct":         (0.0, 1.0, 0.1, float),
    "sell_cooldown_bars":      (0, 10, 1, int),
    "atr_period":              (10, 60, 5, int),
    "atr_multiplier":          (1.5, 5.0, 0.5, float),
    "quick_ema_len":           (3, 25, 2, int),
    "quick_lookback_bars":     (2, 10, 1, int),
    "quick_delta_pct_thresh":  (-15.0, -3.0, 1.0, float),
    "trail_drop_pct":          (10.0, 40.0, 5.0, float),
    "tema_exit_lookback":      (3, 20, 2, int),
    "atr_ratio_len":           (50, 200, 25, int),
    "atr_ratio_max":           (1.0, 3.0, 0.25, float),
    "adx_len":                 (10, 30, 5, int),
    "adx_min":                 (15.0, 30.0, 5.0, float),
    "roc_len":                 (10, 40, 5, int),
    "bear_guard_pct":          (10.0, 30.0, 5.0, float),
    "bear_guard_lookback":     (30, 120, 15, int),
    "asym_atr_ratio_threshold":(1.0, 2.5, 0.25, float),
    "asym_exit_multiplier":    (1.0, 3.0, 0.5, float),
    "vol_spike_len":           (10, 40, 5, int),
    "vol_spike_mult":          (1.5, 4.0, 0.25, float),
}

TOGGLE_PARAMS = [
    # Core (previously locked — now the optimizer can disable them)
    "enable_trend", "enable_atr_exit", "enable_quick_exit",
    "enable_sell_confirm", "enable_sell_cooldown", "enable_sideways_filter",
    # Optional signals
    "enable_slope_filter", "enable_below_filter", "enable_trail_stop",
    "enable_tema_exit", "enable_atr_ratio_filter", "enable_adx_filter",
    "enable_roc_filter", "enable_bear_guard", "enable_asymmetric_exit",
    "enable_vol_exit",
]

# Only truly fixed params — everything else is fair game for the optimizer
FIXED_PARAMS = {
    "initial_capital", "commission_pct",
}


# ─────────────────────────────────────────────────────────────────────────────
# Evolutionary operators
# ─────────────────────────────────────────────────────────────────────────────

def random_value(name):
    """Generate a random valid value for a parameter."""
    if name in TOGGLE_PARAMS:
        return random.choice([True, False])
    if name not in SEARCH_SPACE:
        return None
    lo, hi, step, typ = SEARCH_SPACE[name]
    if typ == int:
        n_steps = (hi - lo) // step
        return lo + random.randint(0, n_steps) * step
    else:
        n_steps = int(round((hi - lo) / step))
        return round(lo + random.randint(0, n_steps) * step, 4)


def enforce_constraints(config):
    """Fix parameter relationships that must hold."""
    # short EMA must be < med EMA
    if config.get("short_ema_len", 15) >= config.get("med_ema_len", 30):
        config["med_ema_len"] = config["short_ema_len"] + 5
    # If a toggle is off, don't waste search on its numeric params
    toggle_deps = {
        "enable_trend": ["trend_ema_len", "slope_lookback", "min_trend_slope"],
        "enable_atr_exit": ["atr_period", "atr_multiplier"],
        "enable_quick_exit": ["quick_ema_len", "quick_lookback_bars", "quick_delta_pct_thresh"],
        "enable_sell_confirm": ["sell_confirm_bars", "sell_buffer_pct"],
        "enable_sell_cooldown": ["sell_cooldown_bars"],
        "enable_sideways_filter": ["range_len", "max_range_pct"],
        "enable_slope_filter": ["triple_ema_len", "triple_slope_lookback"],
        "enable_below_filter": ["triple_ema_len"],
        "enable_trail_stop": ["trail_drop_pct"],
        "enable_tema_exit": ["tema_exit_lookback"],
        "enable_atr_ratio_filter": ["atr_ratio_len", "atr_ratio_max"],
        "enable_adx_filter": ["adx_len", "adx_min"],
        "enable_roc_filter": ["roc_len"],
        "enable_bear_guard": ["bear_guard_pct", "bear_guard_lookback"],
        "enable_asymmetric_exit": ["asym_atr_ratio_threshold", "asym_exit_multiplier"],
        "enable_vol_exit": ["vol_spike_len", "vol_spike_mult"],
    }
    defaults = StrategyParams().to_dict()
    for toggle, deps in toggle_deps.items():
        if not config.get(toggle, False):
            for dep in deps:
                config[dep] = defaults[dep]
    return config


def mutate(config, rate=0.15):
    """Mutate a config. Each mutable param has `rate` chance of changing."""
    result = config.copy()
    mutable = [k for k in list(SEARCH_SPACE.keys()) + TOGGLE_PARAMS if k not in FIXED_PARAMS]
    for name in mutable:
        if random.random() >= rate:
            continue
        if name in TOGGLE_PARAMS:
            result[name] = not result.get(name, False)
        elif name in SEARCH_SPACE:
            lo, hi, step, typ = SEARCH_SPACE[name]
            current = result.get(name, (lo + hi) / 2)
            delta = random.choice([-3, -2, -1, 1, 2, 3]) * step
            new_val = max(lo, min(hi, current + delta))
            result[name] = int(round(new_val)) if typ == int else round(new_val, 4)
    return enforce_constraints(result)


def crossover(p1, p2):
    """Uniform crossover: each param randomly from either parent."""
    child = {}
    for key in set(list(p1.keys()) + list(p2.keys())):
        if key in FIXED_PARAMS:
            child[key] = p1.get(key, p2.get(key))
        elif key in SEARCH_SPACE or key in TOGGLE_PARAMS:
            child[key] = random.choice([p1, p2]).get(key, p1.get(key))
        else:
            child[key] = p1.get(key, p2.get(key))
    return enforce_constraints(child)


# ─────────────────────────────────────────────────────────────────────────────
# Fitness evaluation
# ─────────────────────────────────────────────────────────────────────────────

def get_rs(result):
    return result.regime_score.composite if result.regime_score else 0.0


def fitness(df, config):
    """
    Evaluate a config. Returns (score, result) or (0.0, None) on error.

    Fitness = vs_bah_multiple × drawdown_penalty × quality_guards

    This directly targets the real goal: beat buy-and-hold on TECL
    while keeping drawdowns manageable and avoiding degenerate strategies.
    """
    try:
        params = StrategyParams.from_dict(config)
        result = run_backtest(df, params)

        # Primary: how much of buy-and-hold do we capture?
        # vs_bah_multiple: >1.0 = beating B&H, <1.0 = losing
        bah = max(result.vs_bah_multiple, 0.001)

        # Drawdown penalty: reward lower drawdowns
        # A strategy with 50% DD gets 0.75x, 80% DD gets 0.60x, 30% DD gets 0.85x
        dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)

        # Regime score bonus: strategies that time regimes well tend to be robust
        # This is a secondary signal, not the primary target
        rs = get_rs(result)
        regime_bonus = 1.0 + (rs - 0.5) * 0.3  # RS=0.7 → 1.06x, RS=0.5 → 1.0x

        score = bah * dd_penalty * regime_bonus

        # Quality guards (hard penalties for degenerate strategies)
        if result.num_trades < 5:
            score *= 0.3
        if result.trades_per_year > 6:
            score *= 0.5
        if result.avg_bars_held < 20:
            score *= 0.5
        if result.false_signal_rate_pct > 30:
            score *= 0.7
        # Extremely high drawdown is unacceptable
        if result.max_drawdown_pct > 85:
            score *= 0.3

        return score, result
    except Exception:
        return 0.0, None


def compact_metrics(r):
    """Compact dict of key metrics from a BacktestResult."""
    if r is None:
        return {}
    return {
        "rs": round(get_rs(r), 4),
        "bull": round(r.regime_score.bull_capture_ratio, 4) if r.regime_score else 0,
        "bear": round(r.regime_score.bear_avoidance_ratio, 4) if r.regime_score else 0,
        "cagr": round(r.cagr_pct, 2),
        "dd": round(r.max_drawdown_pct, 1),
        "mar": round(r.mar_ratio, 3),
        "bah": round(r.vs_bah_multiple, 3),
        "trades": r.num_trades,
        "t_yr": round(r.trades_per_year, 1),
        "bars": round(r.avg_bars_held, 0),
        "win": round(r.win_rate_pct, 1),
    }


def diff_params(config, baseline):
    """Return only params that differ from baseline."""
    return {k: v for k, v in config.items() if k in baseline and v != baseline[k]}


# ─────────────────────────────────────────────────────────────────────────────
# Sweep phase — quick single-param exploration to seed population
# ─────────────────────────────────────────────────────────────────────────────

def sweep_phase(df, baseline_dict, baseline_score):
    """Sweep each parameter individually. Returns dict of {param: best_value, delta}."""
    print("── Sweep Phase ──")
    winners = {}
    for name, (lo, hi, step, typ) in SEARCH_SPACE.items():
        if name in FIXED_PARAMS:
            continue
        n_steps = int(round((hi - lo) / step))
        test_points = max(5, min(n_steps + 1, 10))
        values = np.linspace(lo, hi, test_points)
        if typ == int:
            values = sorted(set(int(round(v)) for v in values))
        else:
            values = [round(v, 4) for v in values]

        best_val = baseline_dict.get(name)
        best_score = baseline_score
        for v in values:
            config = baseline_dict.copy()
            config[name] = v
            config = enforce_constraints(config)
            score, _ = fitness(df, config)
            if score > best_score:
                best_score = score
                best_val = v
        delta = best_score - baseline_score
        if delta > 0.001:
            winners[name] = {"value": best_val, "delta": round(delta, 4)}
    ranked = sorted(winners.items(), key=lambda x: -x[1]["delta"])
    summary = ", ".join(f"{k}={v['value']}(+{v['delta']:.3f})" for k, v in ranked)
    print(f"  {len(winners)} winners: {summary}")

    # Also sweep toggles
    for toggle in TOGGLE_PARAMS:
        config = baseline_dict.copy()
        config[toggle] = not config.get(toggle, False)
        config = enforce_constraints(config)
        score, _ = fitness(df, config)
        delta = score - baseline_score
        if delta > 0.001:
            winners[toggle] = {"value": not baseline_dict.get(toggle, False), "delta": round(delta, 4)}
            print(f"  Toggle {toggle}={not baseline_dict.get(toggle, False)}: +{delta:.4f}")

    return winners


# ─────────────────────────────────────────────────────────────────────────────
# Main evolutionary loop
# ─────────────────────────────────────────────────────────────────────────────

def evolve(df, hours=8.0, pop_size=50, elite_pct=0.2, report_interval=300,
           skip_sweep=False):
    start_time = time.time()
    end_time = start_time + hours * 3600
    baseline_dict = StrategyParams().to_dict()

    # ── Baseline ──
    baseline_score, baseline_result = fitness(df, baseline_dict)
    bm = compact_metrics(baseline_result)
    print(f"Baseline: RS={baseline_score:.4f} CAGR={bm['cagr']}% MAR={bm['mar']} vs_bah={bm['bah']}x")

    best_ever_score = baseline_score
    best_ever_config = baseline_dict.copy()
    best_ever_metrics = bm

    # Load previous best-ever
    best_path = os.path.join(PROJECT_ROOT, "remote", "best-ever.json")
    if os.path.exists(best_path):
        try:
            with open(best_path) as f:
                prev = json.load(f)
            if prev.get("regime_score", 0) > best_ever_score:
                best_ever_score = prev["regime_score"]
                if "params" in prev:
                    best_ever_config = {**baseline_dict, **prev["params"]}
                print(f"Loaded best-ever: RS={best_ever_score:.4f}")
        except Exception:
            pass

    # ── Sweep phase ──
    sweep_winners = {}
    if not skip_sweep:
        sweep_winners = sweep_phase(df, baseline_dict, baseline_score)

    # ── Initialize population ──
    population = [baseline_dict.copy(), best_ever_config.copy()]

    # Seed from sweep winners
    if sweep_winners:
        # Config with all sweep winners applied
        all_winners = baseline_dict.copy()
        for name, info in sweep_winners.items():
            all_winners[name] = info["value"]
        population.append(enforce_constraints(all_winners))

        # Individual sweep winners
        for name, info in sweep_winners.items():
            config = baseline_dict.copy()
            config[name] = info["value"]
            population.append(enforce_constraints(config))

    # Fill rest with mutations
    while len(population) < pop_size:
        base = random.choice(population[:max(3, len(population))])
        population.append(mutate(base, rate=0.3))
    population = population[:pop_size]

    # ── Evolutionary loop ──
    generation = 0
    total_evals = 0
    stagnation = 0
    last_improvement = 0
    last_report = start_time
    history = []
    progress_path = os.path.join(PROJECT_ROOT, "remote", "spike-progress.json")

    print(f"\n── Evolutionary Loop (pop={pop_size}, {hours}h) ──")

    while time.time() < end_time:
        generation += 1

        # Evaluate
        scored = []
        for config in population:
            score, result = fitness(df, config)
            total_evals += 1
            scored.append((score, config, result))
        scored.sort(key=lambda x: x[0], reverse=True)

        gen_best = scored[0][0]
        gen_avg = sum(s[0] for s in scored) / len(scored)
        history.append((generation, round(gen_best, 4), round(gen_avg, 4)))

        # Track best-ever
        if scored[0][0] > best_ever_score:
            best_ever_score = scored[0][0]
            best_ever_config = scored[0][1].copy()
            best_ever_metrics = compact_metrics(scored[0][2])
            last_improvement = generation
            stagnation = 0
            save_best_ever(best_path, best_ever_score, best_ever_config,
                           best_ever_metrics, baseline_dict)
        else:
            stagnation += 1

        # Progress report
        now = time.time()
        if now - last_report >= report_interval:
            remaining = (end_time - now) / 3600
            print(f"Gen {generation:>5}: best={gen_best:.4f} avg={gen_avg:.4f} | "
                  f"BEST={best_ever_score:.4f} | evals={total_evals:,} | "
                  f"{remaining:.1f}h left | stag={stagnation}")
            save_progress(progress_path, generation, total_evals, best_ever_score,
                          diff_params(best_ever_config, baseline_dict),
                          best_ever_metrics, history, now - start_time)
            last_report = now

        # ── Selection ──
        n_elite = max(2, int(pop_size * elite_pct))
        elites = [s[1] for s in scored[:n_elite]]

        # ── Adaptive mutation rate ──
        # Higher mutation when stagnating
        mut_rate = 0.15 if stagnation < 50 else 0.30 if stagnation < 150 else 0.50

        # ── Build next generation ──
        new_pop = list(elites)  # Elites survive

        # Crossover children
        n_children = pop_size // 3
        for _ in range(n_children):
            p1, p2 = random.sample(elites, min(2, len(elites)))
            new_pop.append(crossover(p1, p2))

        # Mutants
        while len(new_pop) < pop_size:
            parent = random.choice(elites)
            new_pop.append(mutate(parent, rate=mut_rate))

        # Inject wild card every 20 generations to escape local optima
        if generation % 20 == 0:
            wild = baseline_dict.copy()
            mutable = [k for k in list(SEARCH_SPACE.keys()) + TOGGLE_PARAMS if k not in FIXED_PARAMS]
            for name in random.sample(mutable, random.randint(4, 8)):
                val = random_value(name)
                if val is not None:
                    wild[name] = val
            new_pop[-1] = enforce_constraints(wild)

        population = new_pop[:pop_size]

    # ── Validate top candidates ──
    elapsed_hours = (time.time() - start_time) / 3600
    print(f"\n── Validating top candidates ({total_evals:,} evals in {elapsed_hours:.1f}h) ──")

    # If no generations ran, evaluate population once for final ranking
    if generation == 0:
        scored = []
        for config in population:
            score, result = fitness(df, config)
            total_evals += 1
            scored.append((score, config, result))
        scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate top configs
    seen = set()
    top_configs = []
    for score, config, result in scored:
        key = json.dumps(diff_params(config, baseline_dict), sort_keys=True)
        if key not in seen and key != "{}":
            seen.add(key)
            top_configs.append((score, config, result))
        if len(top_configs) >= 5:
            break

    validated = []
    for i, (score, config, result) in enumerate(top_configs):
        params = StrategyParams.from_dict(config)
        v = validate_candidate(df, params, check_stability=False)
        status = "PASS" if v.passes_validation else "FAIL"
        print(f"  #{i+1}: RS={score:.4f} {status} "
              f"regime={v.regime_score_improvement_pct:+.1f}% "
              f"mar={v.mar_improvement_pct:+.1f}%")
        validated.append({
            "rank": i + 1,
            "regime_score": round(score, 4),
            "params_diff": diff_params(config, baseline_dict),
            "metrics": compact_metrics(result),
            "validation": {
                "passes": v.passes_validation,
                "consistent": v.consistent_improvement,
                "regime_improve_pct": round(v.regime_score_improvement_pct, 1),
                "mar_improve_pct": round(v.mar_improvement_pct, 1),
                "rejections": v.rejection_reasons,
            }
        })

    # ── Final results ──
    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "elapsed_hours": round(elapsed_hours, 2),
        "total_evaluations": total_evals,
        "generations": generation,
        "baseline": {"regime_score": round(baseline_score, 4), "metrics": bm},
        "best_ever": {
            "regime_score": round(best_ever_score, 4),
            "params_diff": diff_params(best_ever_config, baseline_dict),
            "metrics": best_ever_metrics,
        },
        "sweep_winners": sweep_winners,
        "validated_candidates": validated,
        "convergence_tail": history[-20:],
    }

    date_str = datetime.now().strftime("%Y-%m-%d")
    results_path = os.path.join(PROJECT_ROOT, "remote", f"spike-results-{date_str}.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, cls=_NumpyEncoder)

    print(f"\n{'='*50}")
    print(f"DONE — {elapsed_hours:.1f}h, {total_evals:,} evals, {generation} generations")
    print(f"Baseline RS:  {baseline_score:.4f}")
    print(f"Best-ever RS: {best_ever_score:.4f} ({(best_ever_score/baseline_score - 1)*100:+.1f}%)")
    if validated:
        passing = [v for v in validated if v["validation"]["passes"]]
        print(f"Validated:    {len(passing)}/{len(validated)} pass")
    print(f"Results:      {results_path}")
    print(f"{'='*50}")

    print(f"\n###JSON### {json.dumps(results, cls=_NumpyEncoder)}")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# File I/O
# ─────────────────────────────────────────────────────────────────────────────

def save_best_ever(path, score, config, metrics, baseline_dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "regime_score": round(score, 4),
        "params": diff_params(config, baseline_dict),
        "full_params": config,
        **metrics,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_NumpyEncoder)


def save_progress(path, gen, evals, best_score, best_diff, best_metrics, history, elapsed):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generation": gen,
        "total_evaluations": evals,
        "elapsed_hours": round(elapsed / 3600, 2),
        "best_ever_score": round(best_score, 4),
        "best_ever_diff": best_diff,
        "best_ever_metrics": best_metrics,
        "recent_history": history[-10:],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_NumpyEncoder)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Montauk Evolutionary Optimizer")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--pop-size", type=int, default=50)
    parser.add_argument("--elite-pct", type=float, default=0.2)
    parser.add_argument("--report-interval", type=int, default=300,
                        help="Seconds between progress reports (default 300)")
    parser.add_argument("--no-sweep", action="store_true",
                        help="Skip initial parameter sweep phase")
    args = parser.parse_args()

    print(f"=== Montauk Evolutionary Optimizer ===")
    print(f"Duration: {args.hours}h | Pop: {args.pop_size} | Elite: {args.elite_pct*100:.0f}%")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    df = get_tecl_data(use_yfinance=False)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    evolve(df, hours=args.hours, pop_size=args.pop_size,
           elite_pct=args.elite_pct, report_interval=args.report_interval,
           skip_sweep=args.no_sweep)


if __name__ == "__main__":
    main()

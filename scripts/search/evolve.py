#!/usr/bin/env python3
"""
Multi-strategy evolutionary optimizer for Project Montauk.

Tests ALL registered strategies, evolves parameters for each, and
compares everything against the current best. The goal is simple:
beat buy-and-hold on TECL with ≤5 trades per year.

Usage:
  python3 scripts/evolve.py --hours 8               # Full overnight run
  python3 scripts/evolve.py --hours 1 --quick        # Quick test
  python3 scripts/evolve.py --list                    # Show registered strategies
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import signal
import sys
import time
import random
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from certify.contract import (
    is_leaderboard_eligible as _is_leaderboard_eligible,
    sync_entry_contract,
)
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest, BacktestResult
from engine.regime_helpers import score_regime_capture
from search.early_filter import (
    HARD_CACHE_FITNESS_PENALTY,
    SCREEN_WARMUP_BARS,
    SOFT_RANK_MULTIPLIER,
    filter_decision,
    halving_active,
    pruned_cache_entry,
    select_promoted,
)
from search.fitness import (
    all_era_score_from_entry,
    canonicalize_metrics_with_multi_era,
    fitness_from_metrics,
    fitness_from_result,
    weighted_era_fitness,
)
from strategies.markers import NEUTRAL_MARKER_SCORE, score_marker_alignment
from strategies.library import STRATEGY_TIERS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_DIR = os.path.join(PROJECT_ROOT, "spike")
HISTORY_FILE = os.path.join(HISTORY_DIR, "tested-configs.jsonl")  # legacy, no longer written
HASH_INDEX_FILE = os.path.join(HISTORY_DIR, "hash-index.json")   # compact raw-metrics cache


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.bool_,)): return bool(o)
        if isinstance(o, np.ndarray): return o.tolist()
        return super().default(o)


def _compute_engine_hash() -> str:
    """Hash core optimizer files AND the data manifest so both engine fixes
    and data refreshes invalidate stale cache keys. Without the manifest
    (added 2026-06-09), a TECL data refresh let the GA reuse metrics computed
    on old data via hash-index hits. Files moved to subfolders by the
    2026-04-20 restructure."""
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/
    project_root = os.path.dirname(scripts_dir)
    digest = hashlib.sha256()
    for rel_path in (
        os.path.join("engine", "strategy_engine.py"),
        os.path.join("search", "evolve.py"),
        os.path.join("search", "fitness.py"),
        os.path.join("strategies", "library.py"),
    ):
        path = os.path.join(scripts_dir, rel_path)
        with open(path, "rb") as f:
            digest.update(rel_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(f.read())
            digest.update(b"\0")
    manifest_path = os.path.join(project_root, "data", "manifest.json")
    try:
        with open(manifest_path, "rb") as f:
            digest.update(b"data/manifest.json\0")
            digest.update(f.read())
    except OSError:
        digest.update(b"data/manifest.json:missing\0")
    return digest.hexdigest()[:12]


_ENGINE_HASH = _compute_engine_hash()


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
    key = f"{_ENGINE_HASH}:{strategy_name}:{json.dumps(clean, sort_keys=True)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_hash_index() -> dict:
    """
    Load the compact hash index.

    Format v4 (current):
      {config_hash: {
          "bah": share_multiple,
          "real_bah": real_share_multiple,
          "modern_bah": modern_share_multiple,
          "rs": regime_score,
          "dd": max_dd,
          "nt": num_trades,
          "np": n_params,
          "hhi": hhi
      }}
    Format v2 (old): {config_hash: {"f": fitness, "rs": regime_score}}
    Format v1 (old): {config_hash: fitness}

    v1-v3 entries are stale under the era-weighted objective if they don't store
    all three era share-multipliers. They're migrated with bah=None so they are
    re-evaluated when encountered.
    """
    if os.path.exists(HASH_INDEX_FILE):
        try:
            with open(HASH_INDEX_FILE) as f:
                raw = json.load(f)
            if raw:
                sample = next(iter(raw.values()))
                if isinstance(sample, (int, float)):
                    # v1 → migrate: mark all as stale (bah=None)
                    n = len(raw)
                    migrated = {
                        h: {
                            "bah": None,
                            "real_bah": None,
                            "modern_bah": None,
                            "rs": None,
                            "dd": None,
                            "nt": 0,
                            "np": 0,
                            "hhi": None,
                        }
                        for h in raw
                    }
                    print(f"[history] Migrated {n:,} v1 entries to v4 format (stale, will re-evaluate)")
                    return migrated
                # Check for v2 entries (have "f" key but no "bah" key)
                if isinstance(sample, dict) and "f" in sample and "bah" not in sample:
                    n = len(raw)
                    migrated = {
                        h: {
                            "bah": None,
                            "real_bah": None,
                            "modern_bah": None,
                            "rs": v.get("rs"),
                            "dd": None,
                            "nt": 0,
                            "np": 0,
                            "hhi": None,
                        }
                        for h, v in raw.items()
                    }
                    print(f"[history] Migrated {n:,} v2 entries to v4 format (stale, will re-evaluate)")
                    return migrated
                if isinstance(sample, dict) and (
                    "real_bah" not in sample or "modern_bah" not in sample
                ):
                    n = len(raw)
                    migrated = {
                        h: {
                            "bah": None,
                            "real_bah": None,
                            "modern_bah": None,
                            "rs": v.get("rs"),
                            "dd": v.get("dd"),
                            "nt": v.get("nt", 0),
                            "np": v.get("np", 0),
                            "hhi": v.get("hhi"),
                            "ma": v.get("ma"),
                        }
                        for h, v in raw.items()
                    }
                    print(f"[history] Migrated {n:,} v3 entries to v4 format (missing era metrics, will re-evaluate)")
                    return migrated
            return raw
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
                    if h and h not in index:
                        index[h] = {
                            "bah": None,
                            "real_bah": None,
                            "modern_bah": None,
                            "rs": None,
                            "dd": None,
                            "nt": 0,
                            "np": 0,
                            "hhi": None,
                        }
            save_hash_index(index)
            print(f"[history] Migrated {len(index):,} unique configs to hash-index.json")
            return index
        except Exception as e:
            print(f"[history] Warning: migration failed: {e}")
            return {}

    return {}


def save_hash_index(index: dict):
    """Save the hash index to disk. Prunes stale/empty entries to control size.

    v4 format stores the full/real/modern era share multipliers so the
    era-weighted objective can be recomputed without rerunning the backtest.
    Entries missing any era multiplier are pruned because they must be
    re-evaluated anyway.
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    pruned = {}
    for h, v in index.items():
        if (
            isinstance(v, dict)
            and v.get("bah")
            and v.get("real_bah") is not None
            and v.get("modern_bah") is not None
        ):
            pruned[h] = v
    dropped = len(index) - len(pruned)
    if dropped > 0:
        print(f"[history] Pruned {dropped:,} stale/empty entries from hash index")
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

    **Leaderboard guard:** entries are only admitted if they have Gold Status:
    certified not overfit, artifact-backed / backtest-certified, and beating
    B&H in full, real, and modern eras. Performance does not affect eligibility;
    it only ranks already-Gold rows and trims the surface to the top 20.
    Ranking uses a balanced all-era score so the leaderboard surfaces the
    strongest certified strategy across full / real / modern history.
    `backtest_certified` remains champion-only because artifact completeness is
    a post-validation deployment concern, not an anti-overfit admission rule.

    Returns the updated leaderboard list.
    """
    # Load strategy descriptions for context
    try:
        from strategies.library import STRATEGY_DESCRIPTIONS
    except ImportError:
        STRATEGY_DESCRIPTIONS = {}

    # Display-name registry sits next to the leaderboard: spike/name_registry.json

    name_registry_path = os.path.join(
        os.path.dirname(leaderboard_path) or ".", "name_registry.json"
    )

    # Load existing
    leaderboard = []
    if os.path.exists(leaderboard_path):
        try:
            with open(leaderboard_path) as f:
                leaderboard = json.load(f)
        except Exception:
            pass

    normalized_existing = []
    for entry in leaderboard:
        if not isinstance(entry, dict):
            continue
        sync_entry_contract(entry)
        eligible, reason = _is_leaderboard_eligible(entry)
        if eligible:
            normalized_existing.append(entry)
        else:
            print(
                f"[leaderboard] dropped existing {entry.get('strategy')} "
                f"from authority view: {reason}"
            )
    leaderboard = normalized_existing

    # Backfill display_name on legacy entries that predate the naming rule.
    from strategies.naming import assign_display_name as _assign_name
    for _e in leaderboard:
        if not _e.get("display_name") and _e.get("strategy"):
            _e["display_name"] = _assign_name(
                _e["strategy"], _e.get("params", {}), name_registry_path
            )

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
    rejected_count = 0
    # Lazy multi-era enrichment: load TECL once on first admitted entry so the
    # backfill cost stays scoped to promotions. See certify/backfill_multi_era_metrics.py.
    _multi_era_df = None
    _multi_era_fn = None
    def _enrich_multi_era(lb_entry_obj):
        nonlocal _multi_era_df, _multi_era_fn
        try:
            if _multi_era_fn is None:
                from certify.backfill_multi_era_metrics import enrich_entry_with_multi_era
                _multi_era_fn = enrich_entry_with_multi_era
            if _multi_era_df is None:
                from data.loader import get_tecl_data
                _multi_era_df = get_tecl_data()
            lb_entry_obj["multi_era"] = _multi_era_fn(lb_entry_obj, _multi_era_df)
        except Exception as _exc:
            # Enrichment must never block promotion — log and move on.
            print(f"[leaderboard] multi_era enrichment skipped for {lb_entry_obj.get('strategy')}: {_exc}")
    for entry in results.get("rankings", []):
        if not entry.get("metrics"):
            continue
        sync_entry_contract(entry)
        # Leaderboard guard: admit only Gold Status rows.
        eligible, reason = _is_leaderboard_eligible(entry)
        if not eligible:
            rejected_count += 1
            print(
                f"[leaderboard] rejected {entry.get('strategy')} "
                f"(fit={entry.get('fitness', 0):.2f}): {reason}"
            )
            continue
        name = entry["strategy"]
        strategies_in_run.add(name)

        # Build leaderboard entry. Display names are assigned only after the
        # canonical multi-era Gold check so rejected rows do not pollute the
        # name registry.
        lb_entry = {
            "strategy": name,
            "fitness": entry["fitness"],
            "params": entry.get("params", {}),
            "metrics": entry["metrics"],
            "date": date,
        }
        # Preserve marker alignment fields — these are first-class charter
        # signals, not optional decoration. Reports/dashboards rely on
        # `marker_alignment_score` being present at the top level.
        if entry.get("marker_alignment_score") is not None:
            lb_entry["marker_alignment_score"] = entry["marker_alignment_score"]
        if entry.get("marker_alignment_detail") is not None:
            lb_entry["marker_alignment_detail"] = entry["marker_alignment_detail"]
        # Preserve declared tier (validation tier may differ if auto-promoted)
        if entry.get("tier") is not None:
            lb_entry["tier"] = entry["tier"]
        if entry.get("validation") is not None:
            lb_entry["validation"] = entry["validation"]
        desc = STRATEGY_DESCRIPTIONS.get(name)
        if desc:
            lb_entry["description"] = desc
        _enrich_multi_era(lb_entry)
        lb_entry["metrics"] = canonicalize_metrics_with_multi_era(
            lb_entry.get("metrics"),
            lb_entry.get("multi_era"),
        )
        lb_entry["fitness"] = fitness_from_metrics(
            lb_entry.get("metrics") or {},
            multi_era=lb_entry.get("multi_era"),
        )
        sync_entry_contract(lb_entry)
        eligible, reason = _is_leaderboard_eligible(lb_entry)
        if not eligible:
            rejected_count += 1
            print(
                f"[leaderboard] rejected {name} after multi-era canonicalization "
                f"(fit={lb_entry.get('fitness', 0):.2f}): {reason}"
            )
            continue
        new_fitness = lb_entry["fitness"]
        if name not in strategy_state:
            strategy_state[name] = {
                "best_fitness": new_fitness,
                "runs_without_improvement": 0,
                "converged": False,
            }
        else:
            prev_best = strategy_state[name]["best_fitness"]
            # Improvement threshold: must beat previous best by >0.1% to count.
            if new_fitness > prev_best * 1.001:
                strategy_state[name]["best_fitness"] = new_fitness
                strategy_state[name]["runs_without_improvement"] = 0
                strategy_state[name]["converged"] = False
            else:
                strategy_state[name]["runs_without_improvement"] += 1

        # Auto-converge check (only if not manually unconverged).
        rwi = strategy_state[name]["runs_without_improvement"]
        if rwi >= CONVERGE_RUNS and not strategy_state[name].get("manual_unconverge"):
            if not strategy_state[name]["converged"]:
                strategy_state[name]["converged"] = True
                print(f"[leaderboard] {name} auto-converged after {rwi} runs with no improvement")
        lb_entry["converged"] = strategy_state[name]["converged"]
        lb_entry["runs_without_improvement"] = strategy_state[name]["runs_without_improvement"]
        from strategies.naming import assign_display_name
        lb_entry["display_name"] = assign_display_name(
            name, entry.get("params", {}), name_registry_path
        )
        lb_entry["overall_performance_score"] = all_era_score_from_entry(lb_entry)
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

    # Deduplicate: keep strongest certified entry per config hash (Montauk-first).
    def _entry_montauk(entry: dict) -> float:
        # Stamped on every row by sync_entry_contract (calibrated, consistent).
        return float(entry.get("montauk_score") or 0.0)
    def _entry_overall_score(entry: dict) -> float:
        value = entry.get("overall_performance_score")
        if value is not None:
            return float(value)
        return all_era_score_from_entry(entry)
    def _entry_fitness(entry: dict) -> float:
        return float(entry.get("fitness") or 0.0)

    seen = {}
    for entry in leaderboard:
        h = config_hash(entry["strategy"], entry.get("params", {}))
        if h not in seen or (
            _entry_montauk(entry), _entry_overall_score(entry), _entry_fitness(entry)
        ) > (
            _entry_montauk(seen[h]), _entry_overall_score(seen[h]), _entry_fitness(seen[h])
        ):
            seen[h] = entry
    # Leaderboard order is Montauk-Score-first among already-certified rows:
    # confidence-led ranking (Conviction 0.55 × Performance 0.30 × Durability
    # 0.15), with all-era performance and fitness as tiebreaks. The top row is
    # the active strategy.
    leaderboard = sorted(
        seen.values(),
        key=lambda x: (
            _entry_montauk(x),
            _entry_overall_score(x),
            _entry_fitness(x),
        ),
        reverse=True,
    )

    # Diversity floor (2026-06-09): at most MAX_ROWS_PER_STRATEGY rows per
    # strategy name. Twelve param-variants of one strategy are one idea, not
    # twelve discoveries — a board that is 19/20 a single lineage can fool
    # itself into thinking it has diversity (project-status §5 risk). The
    # montauk family_crowding penalty stays as the soft signal; this is the
    # hard cap. Top-Montauk rows per strategy survive.
    MAX_ROWS_PER_STRATEGY = 4
    per_strategy: dict = {}
    capped = []
    for entry in leaderboard:
        name = entry.get("strategy") or "?"
        per_strategy[name] = per_strategy.get(name, 0) + 1
        if per_strategy[name] <= MAX_ROWS_PER_STRATEGY:
            capped.append(entry)
        else:
            print(
                f"[leaderboard] diversity cap: dropped {name} variant "
                f"(montauk={_entry_montauk(entry):.4f}) beyond {MAX_ROWS_PER_STRATEGY}/strategy"
            )
    leaderboard = capped[:20]

    # Surface family concentration explicitly and disambiguate duplicate
    # display names within the authority leaderboard. This is intentionally
    # non-destructive: Gold siblings remain visible, but the UI no longer makes
    # same-family variants look like independent discoveries.
    family_counts: dict[str, int] = {}
    for entry in leaderboard:
        family = entry.get("strategy", "?")
        family_counts[family] = family_counts.get(family, 0) + 1

    family_seen: dict[str, int] = {}
    name_counts: dict[str, int] = {}
    for entry in leaderboard:
        base_name = entry.get("display_name") or entry.get("strategy", "?")
        entry["display_name_base"] = base_name
        name_counts[base_name] = name_counts.get(base_name, 0) + 1

    name_seen: dict[str, int] = {}
    for entry in leaderboard:
        family = entry.get("strategy", "?")
        family_seen[family] = family_seen.get(family, 0) + 1
        entry["family_rank"] = family_seen[family]
        entry["family_size"] = family_counts[family]
        entry["family_leader"] = entry["family_rank"] == 1
        entry["family_concentration"] = (
            round(family_counts[family] / len(leaderboard), 4) if leaderboard else 0.0
        )

        base_name = entry["display_name_base"]
        name_seen[base_name] = name_seen.get(base_name, 0) + 1
        if name_counts[base_name] > 1:
            entry["display_name"] = f"{base_name} #{name_seen[base_name]}"

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
# Fitness — share-count accumulation × robustness guards
# ─────────────────────────────────────────────────────────────────────────────
#
# Charter (2026-04-13): the primary metric is share-count multiplier vs B&H.
# `BacktestResult.share_multiple` is the only Python attribute name —
# the legacy Python alias was retired in Phase 7. Older
# leaderboard JSON entries persisted under a legacy key
# are still readable via `report.py::_share_mult`.
#
# What changed from the previous revision:
#   * REMOVED the `trade_scale = min(1.0, num_trades / 10)` soft ramp that
#     punished strategies for trading fewer than 10 times. Low trade
#     frequency is a feature for a regime strategy, not a bug. A year of
#     holding through new highs is a successful year.
#   * KEPT the `num_trades < 5` hard floor — this is a structural "did the
#     strategy actually engage" check, not a frequency punishment.
#   * KEPT `MAX_TRADES_PER_YEAR = 5.0` — this is the charter's regime-vs-scalper
#     boundary (raised from 3.0 on 2026-04-13 for practical flexibility — a
#     200-EMA regime filter on TECL naturally does ~3-4 round trips/yr). It
#     punishes HIGH frequency (churn), not low frequency.
#   * KEPT drawdown, HHI, and complexity penalties — all robustness-driven,
#     not frequency-driven.
#   * RETIRED `discovery_score_value` as a ranking nudge — raw rankings now
#     use fitness directly, with share_multiple as the primary driver. Marker
#     shape alignment became a first-class validation gate (not a ±5% nudge).
#
# Cache format v4 stores raw backtest metrics plus the real/modern era
# share-multipliers so fitness/objectives can be recomputed on the fly when the
# formula changes, without re-running backtests.

MAX_TRADES_PER_YEAR = 5.0  # charter boundary: regime strategy, not scalper (was 3.0 pre-2026-04-13)


def fitness_from_cache(entry: dict, *, tier: str = "T2") -> float:
    """Compute fitness from cached raw metrics (v4 cache entry).

    Same formula as fitness() but operates on stored metrics dict.
    Returns 0.0 if any required field is None.
    Note: trades_per_year gate can't be applied from cache (no years info) —
    cached entries already passed through full fitness() once.

    Tier-aware: T0 skips the trades-per-param gate (canonical pre-registration
    is the structural defense; see fitness() docstring).

    2026-06-09: entries carry two optional early-filter fields. `pruned` marks
    a successive-halving screen prune — the config never got a full-history
    evaluation, so it must rank at 0.0 (dedup-skip only, never a winner or a
    seed). `pen` is the hard-breach penalty multiplier (×0.25) stamped by the
    post-chunk early filter so history seeding deprioritizes configs that
    would fail execution-realism / event-dependence at validation anyway.
    """
    if entry.get("pruned"):
        return 0.0
    share_mult = entry.get("bah")
    real_share = entry.get("real_bah")
    modern_share = entry.get("modern_bah")
    if (
        share_mult is None
        or real_share is None
        or modern_share is None
        or share_mult <= 0
    ):
        return 0.0
    num_trades = entry.get("nt") or 0
    if num_trades < 5:
        return 0.0  # structural: did the strategy actually engage?
    n_params = entry.get("np") or 0
    hhi = entry.get("hhi") or 0
    if hhi > 0.35:
        return 0.0
    dd = entry.get("dd")
    if dd is None:
        return 0.0

    share_mult = weighted_era_fitness(
        full_share=share_mult,
        real_share=real_share,
        modern_share=modern_share,
    )

    # HHI penalty
    hhi_penalty = max(0.5, 1.0 - max(0, hhi - 0.15) * 3)

    # Drawdown penalty
    dd_penalty = max(0.3, 1.0 - dd / 120.0)

    # Complexity penalty REMOVED (2026-04-13 third revision) — see fitness().
    complexity_penalty = 1.0

    # Regime quality multiplier
    rs = entry.get("rs") or 0
    regime_mult = 0.4 + 0.6 * min(1.0, rs / 0.7)

    base = share_mult * hhi_penalty * dd_penalty * complexity_penalty * regime_mult
    # Early-filter hard-breach penalty (see docstring) — raw metrics stay intact.
    return base * float(entry.get("pen") or 1.0)


def discovery_score_value(fitness_score: float, marker_alignment_score: float | None) -> float:
    """Retired as a nudge. Kept as a back-compat alias for fitness.

    Previous behavior: fitness * (0.95 + 0.10 * marker). That ±5% nudge is
    retired per the 2026-04-13 charter revision — marker shape alignment is
    now a first-class validation gate, not a ranking adjustment. Callers that
    still reference `discovery_score` will see it equal `fitness`.
    """
    del marker_alignment_score  # deliberately unused — see docstring
    return float(fitness_score)


def discovery_score_from_cache(entry: dict, *, tier: str = "T2") -> float:
    return discovery_score_value(fitness_from_cache(entry, tier=tier),
                                 entry.get("ma", NEUTRAL_MARKER_SCORE))


def fitness(result: BacktestResult, *, tier: str = "T2") -> float:
    """
    Weighted-era share-count fitness (2026-04-21 revision).

    PRIMARY: `weighted_era_fitness` = full^0.15 × real^0.25 × modern^0.60
       — a weighted geometric mean of era-sliced share multipliers. See
       `scripts/search/fitness.py` for the full rationale. Previously primary
       was raw `share_multiple` on full 1993-now history; that was dominated
       by the synthetic 1993-2008 dotcom crash, producing strategies that
       crushed full-history but failed on real post-2008 data.

    Guards: drawdown, cycle concentration (HHI), trade count floor, charter
       trade-frequency limit. Regime score still used as a quality multiplier.
    """
    if result is None or result.num_trades < 5:
        return 0.0

    # ── Primary: weighted geometric mean over era share multipliers ──
    share_mult = weighted_era_fitness(
        full_share=result.share_multiple,
        real_share=result.real_share_multiple,
        modern_share=result.modern_share_multiple,
    )

    # ── Charter boundary: regime strategy, not scalper ──
    if result.trades_per_year > MAX_TRADES_PER_YEAR:
        return 0.0
    if share_mult <= 0:
        return 0.0

    # ── Cycle concentration penalty (HHI) ──
    rs = result.regime_score
    hhi = rs.hhi if rs and rs.hhi is not None else 0
    if hhi > 0.35:
        return 0.0  # single cycle carries everything — reject
    hhi_penalty = max(0.5, 1.0 - max(0, hhi - 0.15) * 3)  # ramp 0.15→0.35

    # ── Drawdown penalty — penalize strategies with huge drawdowns ──
    # Max DD of 80%+ → 0.3x, 40% → 0.65x, 20% → 0.83x
    dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 120.0)

    # ── Complexity penalty REMOVED (2026-04-13 third revision) ──
    # The trades-per-param (tpp) gate it implemented is a statistical prior
    # that's already tested directly and more powerfully by cross-asset,
    # walk-forward, fragility, and HHI gates. In Montauk's low-trade-count
    # charter (≤5 trades/year), it also actively punished legitimate strategies
    # with more than 5 params. Overfit candidates that survive every other
    # gate are not meaningfully overfit; this penalty added only noise.
    complexity_penalty = 1.0

    # ── Regime quality multiplier (rewards good timing, but share_mult drives ranking) ──
    # Regime score 0.7 → 1.0x (full credit), 0.5 → 0.8x, 0.3 → 0.6x
    regime_mult = 1.0
    if rs:
        regime_mult = 0.4 + 0.6 * min(1.0, rs.composite / 0.7)

    return share_mult * hhi_penalty * dd_penalty * complexity_penalty * regime_mult


def _count_tunable_params(params: dict) -> int:
    return sum(
        1
        for k, v in params.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "cooldown"
    )


def _cache_entry_from_result(
    params: dict,
    result: BacktestResult | None,
    marker_alignment_score: float | None = None,
) -> dict:
    """Store raw metrics so ranking formulas can evolve without rerunning backtests."""
    regime_score = result.regime_score if result else None
    hhi = None
    if regime_score and regime_score.hhi is not None:
        hhi = round(regime_score.hhi, 4)
    return {
        "bah": round(result.share_multiple, 4) if result else None,
        "real_bah": round(result.real_share_multiple, 4) if result else None,
        "modern_bah": round(result.modern_share_multiple, 4) if result else None,
        "rs": round(regime_score.composite, 4) if regime_score else None,
        "dd": round(result.max_drawdown_pct, 1) if result else None,
        "nt": result.num_trades if result else 0,
        "np": _count_tunable_params(params),
        "hhi": hhi,
        "ma": round(float(marker_alignment_score), 4)
        if marker_alignment_score is not None else None,
    }


def _cache_entry_ready(entry: dict | None) -> bool:
    return bool(
        isinstance(entry, dict)
        and entry.get("bah") is not None
        and entry.get("real_bah") is not None
        and entry.get("modern_bah") is not None
    )


def _dataset_years(df) -> float:
    if df is None or len(df) < 2:
        return 0.0
    start = np.datetime64(df["date"].iloc[0])
    end = np.datetime64(df["date"].iloc[-1])
    days = float((end - start) / np.timedelta64(1, "D"))
    return days / 365.25 if days > 0 else 0.0


def _passes_pareto_hard_gates(num_trades: int, trades_per_year: float, n_params: int, hhi: float) -> bool:
    if num_trades < 5:
        return False
    if trades_per_year > MAX_TRADES_PER_YEAR:
        return False
    if hhi > 0.35:
        return False
    if n_params > 0 and (num_trades / n_params) < 5:
        return False
    return True


def _objectives_from_cache(entry: dict, dataset_years: float) -> tuple[float, float, float] | None:
    if entry.get("pruned"):
        # Screen-pruned trial: no full-history metrics exist (dd is None
        # anyway), so the bayesian path must prune rather than rank it.
        return None
    share_mult = entry.get("bah")
    real_share = entry.get("real_bah")
    modern_share = entry.get("modern_bah")
    dd = entry.get("dd")
    num_trades = entry.get("nt") or 0
    n_params = entry.get("np") or 0
    hhi = entry.get("hhi")
    if hhi is None:
        hhi = 0.0
    if share_mult is None or real_share is None or modern_share is None or dd is None:
        return None
    trades_per_year = (num_trades / dataset_years) if dataset_years > 0 else 0.0
    if not _passes_pareto_hard_gates(num_trades, trades_per_year, n_params, float(hhi)):
        return None
    return (
        weighted_era_fitness(
            full_share=float(share_mult),
            real_share=float(real_share),
            modern_share=float(modern_share),
        ),
        float(dd),
        float(hhi),
    )


def _objectives_from_result(result: BacktestResult | None) -> tuple[float, float, float] | None:
    if result is None:
        return None
    hhi = 0.0
    if result.regime_score and result.regime_score.hhi is not None:
        hhi = float(result.regime_score.hhi)
    n_params = _count_tunable_params(result.params)
    if not _passes_pareto_hard_gates(result.num_trades, result.trades_per_year, n_params, hhi):
        return None
    return fitness_from_result(result), float(result.max_drawdown_pct), hhi


def _require_optuna():
    try:
        import optuna
        from optuna.samplers import NSGAIISampler
    except ImportError as exc:
        raise SystemExit(
            "Optuna is required for Bayesian mode. Install `optuna` in the active Python environment."
        ) from exc
    return optuna, NSGAIISampler


# ─────────────────────────────────────────────────────────────────────────────
# Parameter generation
# ─────────────────────────────────────────────────────────────────────────────

def random_params(space: dict) -> dict:
    """Generate random parameters within a strategy's search space.

    Degenerate ranges (hi == lo, used by T0 pre-registered strategies) always
    return the committed value — without this clamp, the fallback
    `max(1, n_steps)` would let randint produce `lo + 1*step`, drifting the
    param off-canonical.
    """
    params = {}
    for name, (lo, hi, step, typ) in space.items():
        if hi <= lo:
            val = lo
        else:
            n_steps = int(round((hi - lo) / step))
            val = lo + random.randint(0, max(1, n_steps)) * step
            val = min(val, hi)
        params[name] = int(round(val)) if typ == int else round(val, 4)
    return params


def mutate_params(params: dict, space: dict, rate: float = 0.2,
                   magnitude: int = 2) -> dict:
    """Mutate parameters. magnitude controls step size (1=fine, 2=normal, 4=burst)."""
    result = params.copy()
    for name, (lo, hi, step, typ) in space.items():
        if random.random() >= rate:
            continue
        current = result.get(name, (lo + hi) / 2)
        delta = random.choice(list(range(-magnitude, 0)) + list(range(1, magnitude + 1))) * step
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
    """Run one strategy config and return discovery + fitness context.

    Fitness is evaluated at the strategy's declared tier so T0 hypothesis
    strategies (canonical pre-registered) bypass the T2-only tpp gate
    rather than being silently zeroed during the GA loop.
    """
    try:
        entries, exits, labels = strategy_fn(ind, params)
        cooldown = params.get("cooldown", 0)
        result = backtest(df, entries, exits, labels,
                          cooldown_bars=cooldown, strategy_name=name)
        # Attach params for complexity penalty calculation
        result.params = params
        # Compute regime score (needed by fitness function)
        if result.num_trades >= 3:
            cl = df["close"].values.astype(np.float64)
            dates = df["date"].values
            result.regime_score = score_regime_capture(result.trades, cl, dates)
        else:
            result.regime_score = None
        tier = STRATEGY_TIERS.get(name, "T2")
        fitness_score = fitness(result, tier=tier)
        marker_alignment = score_marker_alignment(df, result.trades)
        marker_score = float(marker_alignment["score"])
        discovery_score = discovery_score_value(fitness_score, marker_score)
        return fitness_score, discovery_score, marker_score, marker_alignment, result
    except Exception:
        return 0.0, 0.0, NEUTRAL_MARKER_SCORE, {
            "score": NEUTRAL_MARKER_SCORE,
            "error": "evaluation_failed",
        }, None


# ─────────────────────────────────────────────────────────────────────────────
# Parallel population evaluation + successive halving (2026-06-09)
# ─────────────────────────────────────────────────────────────────────────────
#
# WHY a module-level holder + fork: a generation's population is evaluated by a
# worker pool, and the df / Indicators cache are far too heavy to pickle per
# task. With the fork start method (set per-pool via get_context, the scoped
# cousin of recertify_leaderboard's global set_start_method("fork")), workers
# inherit _PARALLEL_CTX as a copy-on-write snapshot: the parent warms its
# Indicators cache during baseline/seed evaluation, the fork copies that
# snapshot, and each worker keeps filling its own copy lazily. The dedup-cache
# lookup stays in the parent (cheap dict hit) — only cache-miss candidates
# reach the pool.

_PARALLEL_CTX: dict = {"df": None, "ind": None, "screen_df": None, "screen_from": None}


def _set_parallel_context(df, ind, screen_df=None, screen_from=None) -> None:
    """Stage the fork-inherited globals. MUST run before pool creation."""
    _PARALLEL_CTX["df"] = df
    _PARALLEL_CTX["ind"] = ind
    _PARALLEL_CTX["screen_df"] = screen_df
    _PARALLEL_CTX["screen_from"] = screen_from


def _ctx_indicators() -> Indicators:
    ind = _PARALLEL_CTX.get("ind")
    if ind is None:  # built lazily on first use in each worker
        ind = Indicators(_PARALLEL_CTX["df"])
        _PARALLEL_CTX["ind"] = ind
    return ind


def _worker_eval_full(task: tuple) -> tuple:
    """Pool worker: full-history evaluation of one (strategy_name, params)."""
    strat_name, params = task
    from strategies.library import STRATEGY_REGISTRY

    fn = STRATEGY_REGISTRY[strat_name]
    return evaluate(_ctx_indicators(), _PARALLEL_CTX["df"], fn, params, strat_name)


def _worker_eval_screen(task: tuple) -> float:
    """Pool worker: modern-era screen metric for one (strategy_name, params)."""
    strat_name, params = task
    from strategies.library import STRATEGY_REGISTRY

    fn = STRATEGY_REGISTRY[strat_name]
    return _screen_share(
        _PARALLEL_CTX["screen_df"], fn, params, strat_name, _PARALLEL_CTX["screen_from"]
    )


def _screen_share(screen_df, strategy_fn, params: dict, name: str, eval_from) -> float:
    """Successive-halving screen metric: modern-era share_multiple.

    Reuses validation.candidate.run_eval's eval_from path, which already
    implements the era growth-ratio convention (warmup prefix feeds indicators
    only; the scored share_multiple starts at the modern boundary).
    """
    from validation.candidate import run_eval

    metrics = run_eval(screen_df, strategy_fn, params, name, eval_from=eval_from)
    if metrics.get("error"):
        return 0.0
    return float(metrics.get("share_multiple", 0.0) or 0.0)


def _resolve_workers(workers: int | None) -> int:
    if workers is not None:
        return max(1, int(workers))
    return max(1, (os.cpu_count() or 2) - 2)


def _create_eval_pool(workers: int | None):
    """Create the once-per-chunk fork pool, or None to run serial.

    Never raises: platforms without fork (or sandboxed environments that
    refuse subprocesses) silently degrade to the serial path so parallelism
    can never crash a run.
    """
    n_workers = _resolve_workers(workers)
    if n_workers <= 1:
        return None
    try:
        ctx = multiprocessing.get_context("fork")
        return ctx.Pool(processes=n_workers)
    except Exception as e:
        print(f"[parallel] fork pool unavailable ({e}) — running serial")
        return None


def _close_eval_pool(pool_state: dict) -> None:
    pool = pool_state.get("pool")
    if pool is None:
        return
    try:
        pool.close()
        pool.join()
    except Exception:
        try:
            pool.terminate()
        except Exception:
            pass
    pool_state["pool"] = None


def _pool_map(pool_state: dict | None, worker_fn, tasks: list, serial_fn) -> list:
    """Order-preserving map with automatic serial fallback.

    pool.map preserves task order, so parallel results are positionally
    identical to serial ones. Any pool failure permanently downgrades the
    chunk to serial (pool_state["pool"] = None) instead of crashing the run.
    """
    pool = pool_state.get("pool") if pool_state else None
    if pool is not None and len(tasks) > 1:
        try:
            return pool.map(worker_fn, tasks)
        except Exception as e:
            print(f"[parallel] pool map failed ({e}) — serial for the rest of this chunk")
            try:
                pool.terminate()
            except Exception:
                pass
            pool_state["pool"] = None
    return [serial_fn(t) for t in tasks]


def _build_screen_frame(df):
    """Build the successive-halving screen slice: warmup prefix + modern era.

    Returns (screen_df, eval_from) or (None, None) when screening is pointless
    — no modern bars, or the slice covers ~the whole frame (e.g. a cross-asset
    df that already starts post-2015), where a screen backtest would cost as
    much as the full evaluation it is supposed to avoid.

    The boundary is the canonical MODERN_ERA_START (the same date behind
    `modern_share_multiple` and the fitness modern-era weight) — never a new
    ad-hoc date.
    """
    from engine.strategy_engine import MODERN_ERA_START

    if df is None or "date" not in df:
        return None, None
    mask = (df["date"] >= MODERN_ERA_START).values
    if not mask.any():
        return None, None
    first = int(np.argmax(mask))
    start = max(0, first - SCREEN_WARMUP_BARS)
    screen_df = df.iloc[start:].reset_index(drop=True)
    if len(screen_df) >= 0.9 * len(df):
        return None, None
    return screen_df, MODERN_ERA_START


def _evaluate_population(
    pop: list,
    strat_name: str,
    fn,
    ind: Indicators,
    df,
    dedup_cache: dict,
    history_stats: dict,
    strat_tier: str,
    *,
    pool_state: dict | None = None,
    screen_df=None,
    screen_from=None,
    halving_on: bool = False,
) -> tuple[list, int]:
    """Evaluate one strategy's population for one generation.

    Returns (scored, n_new_full_evals); `scored` preserves population order so
    the caller's sort produces identical rankings whether the work ran serial
    or pooled. Stages:

      1. dedup — parent-only dict lookups; duplicate configs inside the same
         population resolve to a single evaluation (the serial loop got this
         for free because the cache filled mid-loop)
      2. optional modern-era screen of ALL cache-miss candidates (halving);
         non-promoted candidates are pruned with a hash-index tombstone so
         they are never retried and still count toward N_eff
      3. full-history evaluation of the promoted candidates (pool or serial)
    """
    slots: list = [None] * len(pop)
    pending: dict = {}  # config_hash -> {"params": dict, "indices": [int]}
    miss_order: list = []  # hashes in first-seen order (determinism)
    for i, params in enumerate(pop):
        h = config_hash(strat_name, params)
        cached = dedup_cache.get(h)
        if _cache_entry_ready(cached):
            fitness_score = fitness_from_cache(cached, tier=strat_tier)
            marker_score = cached.get("ma", NEUTRAL_MARKER_SCORE)
            if marker_score is None:
                marker_score = NEUTRAL_MARKER_SCORE
            discovery_score = discovery_score_from_cache(cached, tier=strat_tier)
            slots[i] = (discovery_score, fitness_score, params, None, marker_score, None)
            history_stats["cached_configs"] += 1
        elif h in pending:
            pending[h]["indices"].append(i)
            history_stats["cached_configs"] += 1  # in-pop duplicate, as before
        else:
            pending[h] = {"params": params, "indices": [i]}
            miss_order.append(h)

    # ── Successive halving: screen misses on the modern slice, prune losers ──
    pruned_hashes: set = set()
    if halving_on and screen_df is not None and miss_order:
        tasks = [(strat_name, pending[h]["params"]) for h in miss_order]
        screen_scores = _pool_map(
            pool_state, _worker_eval_screen, tasks,
            serial_fn=lambda t: _screen_share(screen_df, fn, t[1], strat_name, screen_from),
        )
        promoted_idx = select_promoted([float(s) for s in screen_scores])
        for j, h in enumerate(miss_order):
            if j in promoted_idx:
                continue
            info = pending[h]
            pruned_hashes.add(h)
            dedup_cache[h] = pruned_cache_entry(
                screen_scores[j], _count_tunable_params(info["params"])
            )
            for i in info["indices"]:
                slots[i] = (0.0, 0.0, info["params"], None, NEUTRAL_MARKER_SCORE, None)
        history_stats["screen_evals"] = history_stats.get("screen_evals", 0) + len(tasks)
        history_stats["pruned_screen"] = (
            history_stats.get("pruned_screen", 0) + len(pruned_hashes)
        )

    # ── Full-history evaluation of the surviving cache misses ──
    eval_hashes = [h for h in miss_order if h not in pruned_hashes]
    tasks = [(strat_name, pending[h]["params"]) for h in eval_hashes]
    outputs = _pool_map(
        pool_state, _worker_eval_full, tasks,
        serial_fn=lambda t: evaluate(ind, df, fn, t[1], strat_name),
    )
    n_new = 0
    for h, out in zip(eval_hashes, outputs):
        fitness_score, discovery_score, marker_score, marker_detail, result = out
        info = pending[h]
        dedup_cache[h] = _cache_entry_from_result(info["params"], result, marker_score)
        for i in info["indices"]:
            slots[i] = (
                discovery_score, fitness_score, info["params"],
                result, marker_score, marker_detail,
            )
        history_stats["new_configs"] += 1
        n_new += 1
    return slots, n_new


def _apply_early_filter_to_bests(
    df, reg: dict, strategy_bests: dict, dedup_cache: dict, top_k: int = 5
) -> list:
    """Post-chunk validation-aligned early filter (2026-06-09).

    Runs analyze_execution_realism + analyze_event_dependence (≈5 extra
    backtests per config, once per chunk) on the chunk's top-K distinct
    configs and applies the early_filter.filter_decision verdicts:

      hard → exclude from strategy_bests / best-run tracking / leaderboard
             submission for this run, and stamp `pen`=0.25 on the hash-index
             entry so future history seeding deprioritizes it
      soft → keep, but demote the in-run ranking key by ×0.85

    Mutates `strategy_bests` in place and returns the annotation list for the
    results dict. Tuple layouts differ between evolve() (6 slots) and
    evolve_chunk() (4 slots): only slots 0..2 (discovery, fitness, params) are
    interpreted; trailing slots are blanked positionally on exclusion (floats
    → NEUTRAL_MARKER_SCORE, objects → None) so both layouts survive.
    """
    from validation.candidate import analyze_event_dependence, analyze_execution_realism

    ranked = sorted(
        (
            (name, tup) for name, tup in strategy_bests.items()
            if tup[1] > 0 and tup[2] and name in reg
        ),
        key=lambda x: -x[1][1],
    )
    selected = []
    seen_hashes = set()
    for name, tup in ranked:
        h = config_hash(name, tup[2])
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        selected.append((name, tup, h))
        if len(selected) >= top_k:
            break
    if not selected:
        return []

    annotations = []
    print(f"\n── Early filter (validation-aligned, top {len(selected)} configs) ──")
    for name, tup, h in selected:
        realism = analyze_execution_realism(df, reg[name], tup[2], name)
        events = analyze_event_dependence(df, reg[name], tup[2], name)
        degradation = float(realism.get("degradation_pct", 0.0))
        collapse = float(events.get("worst_collapse", 0.0))
        decision = filter_decision(degradation, collapse)
        if decision == "hard":
            action = "exclude"
            blanked = (0.0, 0.0, {}) + tuple(
                NEUTRAL_MARKER_SCORE if isinstance(v, (int, float)) else None
                for v in tup[3:]
            )
            strategy_bests[name] = blanked
            cached = dedup_cache.get(h)
            if isinstance(cached, dict):
                cached["pen"] = HARD_CACHE_FITNESS_PENALTY
        elif decision == "soft":
            action = "demote"
            strategy_bests[name] = (tup[0] * SOFT_RANK_MULTIPLIER,) + tuple(tup[1:])
            print(
                f"  WARNING {name}: soft breach — ranking key demoted "
                f"×{SOFT_RANK_MULTIPLIER}"
            )
        else:
            action = "keep"
        print(
            f"  {action.upper():7s} {name:<22} "
            f"next-open degradation={degradation:+.1f}% "
            f"event collapse={collapse:.2f} ({events.get('worst_event') or '-'})"
        )
        annotations.append({
            "strategy": name,
            "config_hash": h,
            "params": tup[2],
            "degradation_pct": round(degradation, 2),
            "worst_collapse": round(collapse, 4),
            "worst_event": events.get("worst_event"),
            "decision": decision,
            "action": action,
        })
    return annotations


def evolve_bayesian(ind, df, strategy_name, strategy_fn, space, hours, dedup_cache, history_stats):
    """
    Multi-objective Bayesian optimization for a single strategy using Optuna NSGA-II.
    Returns discovery-aware best candidate while keeping Pareto objectives unchanged.
    """
    optuna, NSGAIISampler = _require_optuna()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    dataset_years = _dataset_years(df)

    def params_from_trial(trial) -> dict:
        params = {}
        for name, (lo, hi, step, typ) in space.items():
            if typ == int:
                params[name] = trial.params.get(name, int((lo + hi) / 2))
            else:
                idx = trial.params.get(f"_idx_{name}", 0)
                params[name] = round(lo + idx * step, 4)
        return params

    def objective(trial):
        params = {}
        for name, (lo, hi, step, typ) in space.items():
            if typ == int:
                params[name] = trial.suggest_int(name, int(lo), int(hi), step=int(step))
            else:
                # For float params, discretize to match GA's step resolution
                n_steps = int(round((hi - lo) / step))
                idx = trial.suggest_int(f"_idx_{name}", 0, n_steps)
                params[name] = round(lo + idx * step, 4)

        # Check dedup cache
        h = config_hash(strategy_name, params)
        cached = dedup_cache.get(h)
        if _cache_entry_ready(cached):
            history_stats["cached_configs"] += 1
            objectives = _objectives_from_cache(cached, dataset_years)
            if objectives is None:
                raise optuna.TrialPruned()
            return objectives

        fitness_score, _discovery_score, marker_score, _marker_detail, result = evaluate(
            ind, df, strategy_fn, params, strategy_name
        )
        history_stats["new_configs"] += 1

        # Store to cache (v4 format)
        dedup_cache[h] = _cache_entry_from_result(params, result, marker_score)

        objectives = _objectives_from_result(result)
        if objectives is None:
            raise optuna.TrialPruned()
        return objectives

    study = optuna.create_study(
        directions=["maximize", "minimize", "minimize"],
        sampler=NSGAIISampler(seed=42),
    )

    # Seed with leaderboard winners if available
    leaderboard_path = os.path.join(HISTORY_DIR, "leaderboard.json")
    seeds = get_top_from_leaderboard(leaderboard_path, strategy_name, n=5)
    for seed_params in seeds:
        try:
            trial_params = {}
            for name, (lo, hi, step, typ) in space.items():
                val = seed_params.get(name, (lo + hi) / 2)
                if typ == int:
                    n_steps = int(round((hi - lo) / step))
                    idx = int(round((val - lo) / step))
                    idx = max(0, min(n_steps, idx))
                    trial_params[name] = int(lo + idx * step)
                else:
                    n_steps = int(round((hi - lo) / step))
                    idx = int(round((val - lo) / step))
                    idx = max(0, min(n_steps, idx))
                    trial_params[f"_idx_{name}"] = idx
            study.enqueue_trial(trial_params)
        except Exception:
            pass

    timeout = hours * 3600
    study.optimize(objective, timeout=timeout, n_trials=100000, show_progress_bar=False)

    pareto = [trial for trial in study.best_trials if trial.values is not None]
    if not pareto:
        print("    Pareto front: 0 feasible trials after pruning")
        return (
            0.0,
            0.0,
            {},
            None,
            None,
            len(study.trials),
            NEUTRAL_MARKER_SCORE,
            {"score": NEUTRAL_MARKER_SCORE, "error": "no_feasible_trials"},
        )

    candidates = [trial for trial in pareto if trial.values[1] < 70 and trial.values[2] < 0.35]
    used_fallback = False
    if not candidates:
        candidates = pareto
        used_fallback = True

    best_trial = None
    best_trial_discovery = -1.0
    best_trial_marker_score = NEUTRAL_MARKER_SCORE
    strategy_tier = STRATEGY_TIERS.get(strategy_name, "T2")
    for trial in candidates:
        params = params_from_trial(trial)
        cached = dedup_cache.get(config_hash(strategy_name, params), {})
        discovery = discovery_score_from_cache(cached, tier=strategy_tier)
        if discovery > best_trial_discovery:
            best_trial = trial
            best_trial_discovery = discovery
            best_trial_marker_score = cached.get("ma", NEUTRAL_MARKER_SCORE)

    if best_trial is None:
        best_trial = max(candidates, key=lambda trial: trial.values[0])
    screen_label = "fallback to full front" if used_fallback else "DD/HHI-screened"
    print(
        f"    Pareto front: {len(pareto)} feasible trials, "
        f"{len(candidates)} in selection pool ({screen_label})"
    )
    print(
        f"    Selected objectives: share={best_trial.values[0]:.3f}x "
        f"DD={best_trial.values[1]:.1f}% HHI={best_trial.values[2]:.3f} "
        f"marker={best_trial_marker_score:.3f} fitness={best_trial_discovery:.4f}"
    )

    best_params = params_from_trial(best_trial)

    # Re-evaluate best to get full result
    best_fitness, best_discovery, best_marker_score, best_marker_detail, best_result = evaluate(
        ind, df, strategy_fn, best_params, strategy_name
    )

    return (
        best_discovery,
        best_fitness,
        best_params,
        best_result,
        tuple(best_trial.values),
        len(study.trials),
        best_marker_score,
        best_marker_detail,
    )


SEARCH_ROSTER_FILE = os.path.join(PROJECT_ROOT, "spike", "search-roster.json")


def _load_retired_roster() -> set:
    """Families retired from default search (spike/search-roster.json)."""
    try:
        with open(SEARCH_ROSTER_FILE) as f:
            roster = json.load(f)
        return set(roster.get("retired") or [])
    except (OSError, ValueError):
        return set()


def evolve(hours: float = 8.0, pop_size: int = 40, quick: bool = False,
           run_dir: str | None = None, strategies: list[str] | None = None,
           bayesian: bool = False, publish_leaderboard: bool = True,
           write_report: bool = True, early_filter: bool = True,
           workers: int | None = None, halving: bool = True) -> dict:
    """
    Run the evolutionary optimizer. Returns the results dict.

    Parameters
    ----------
    hours : how long to run
    pop_size : population per strategy per generation
    quick : shorter report intervals
    run_dir : directory to save results (optional, for spike_runner)
    strategies : optional list of strategy names to run (default: all)
    early_filter : run the validation-aligned execution-realism +
        event-dependence filter on the run's top configs at the end
        (a full `evolve` run is one chunk for filtering purposes)
    workers : fork-pool size for population evaluation (None → cpu_count-2;
        <=1 → serial). GA path only — the bayesian path stays serial.
    halving : successive-halving modern-era screen before full-history
        evaluation (auto-disabled below pop 16)
    """
    # Late import to pick up any new strategies added between runs
    from strategies.library import STRATEGY_REGISTRY, STRATEGY_PARAMS

    # Filter to requested strategies if specified
    if strategies:
        unknown = [s for s in strategies if s not in STRATEGY_REGISTRY]
        if unknown:
            print(f"WARNING: Unknown strategies: {unknown}")
        STRATEGY_REGISTRY_FILTERED = {k: v for k, v in STRATEGY_REGISTRY.items() if k in strategies}
        STRATEGY_PARAMS_FILTERED = {k: v for k, v in STRATEGY_PARAMS.items() if k in strategies}
    else:
        # Search-roster curation (2026-06-09): families listed as retired in
        # spike/search-roster.json are excluded from DEFAULT search. They stay
        # registered (board rows / null calibration / explicit --strategies
        # still work) — retirement only stops the GA spending default compute
        # on families the project's own scans showed cannot clear the Gold
        # economics floor. Edit the roster file to retire/revive.
        retired = _load_retired_roster()
        STRATEGY_REGISTRY_FILTERED = {
            k: v for k, v in STRATEGY_REGISTRY.items() if k not in retired
        }
        STRATEGY_PARAMS_FILTERED = {
            k: v for k, v in STRATEGY_PARAMS.items() if k not in retired
        }
        if retired:
            active = sum(1 for k in STRATEGY_PARAMS_FILTERED)
            print(f"[roster] {len(retired)} families retired from default search; "
                  f"{active} searchable families active")

    if bayesian:
        _require_optuna()

    start_time = time.time()
    end_time = start_time + hours * 3600

    print("=== Montauk Multi-Strategy Optimizer ===")
    print(f"Duration: {hours}h | Pop: {pop_size}/strategy | Registered: {len(STRATEGY_REGISTRY_FILTERED)}")
    print(f"Constraint: ≤{MAX_TRADES_PER_YEAR} trades/year")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)
    print(f"Data: {len(df)} bars, {df['date'].min().date()} to {df['date'].max().date()}\n")

    # ── Load hash index for dedup ──
    dedup_cache = load_hash_index()  # hash -> fitness
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0,
                     "screen_evals": 0, "pruned_screen": 0}

    if dedup_cache:
        print(f"[history] Dedup cache: {len(dedup_cache):,} configs with known fitness\n")

    # ── Baseline: run each strategy with default (midpoint) params ──
    print("── Baselines ──")
    baselines = {}
    for name, fn in STRATEGY_REGISTRY_FILTERED.items():
        space = STRATEGY_PARAMS_FILTERED.get(name, {})
        default_params = {k: (lo + hi) / 2 for k, (lo, hi, step, typ) in space.items()}
        # Round ints
        for k, (lo, hi, step, typ) in space.items():
            if typ == int:
                default_params[k] = int(round(default_params[k]))
        fitness_score, discovery_score, marker_score, marker_detail, result = evaluate(
            ind, df, fn, default_params, name
        )
        baselines[name] = {
            "fitness": fitness_score,
            "discovery_score": discovery_score,
            "marker_alignment_score": marker_score,
            "marker_alignment_detail": marker_detail,
            "result": result,
            "params": default_params,
        }
        if result:
            print(f"  {name:<22} discovery={discovery_score:.4f}  fitness={fitness_score:.4f}  "
                  f"marker={marker_score:.3f}  share={result.share_multiple:.3f}x  "
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
    for name in list(STRATEGY_REGISTRY_FILTERED.keys()):
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

    active_strategies = {k: v for k, v in STRATEGY_REGISTRY_FILTERED.items() if k not in skipped_strategies}
    print(f"Active strategies: {len(active_strategies)}/{len(STRATEGY_REGISTRY_FILTERED)}")

    # ── Initialize populations (one per strategy) ──
    # Seed with historical winners + defaults + random
    populations = {}
    max_seed = max(2, int(pop_size * 0.2))  # 20% from history
    for name in active_strategies:
        space = STRATEGY_PARAMS_FILTERED.get(name, {})
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
    historical_best_fitness = 0.0
    historical_best_name = ""
    historical_best_params = {}
    best_run_discovery = 0.0
    best_run_name = ""
    best_run_params = {}

    # Load previous best from leaderboard (sorted by fitness, [0] = best)
    if os.path.exists(leaderboard_path):
        try:
            with open(leaderboard_path) as f:
                lb = json.load(f)
            if lb and lb[0].get("fitness", 0) > historical_best_fitness:
                historical_best_fitness = lb[0]["fitness"]
                historical_best_name = lb[0].get("strategy", "")
                historical_best_params = lb[0].get("params", {})
                print(f"\nLoaded best-ever: {historical_best_name} fitness={historical_best_fitness:.4f}")
        except Exception:
            pass

    generation = 0
    total_evals = 0
    last_report = start_time
    report_interval = 30 if quick else 60
    strategy_bests = {
        name: (0.0, 0.0, {}, None, NEUTRAL_MARKER_SCORE, None)
        for name in active_strategies
    }
    convergence_history = []

    # Allow Ctrl+C or kill to save results gracefully
    _interrupted = [False]
    def _handle_signal(sig, frame):
        print("\n[interrupted — saving results...]")
        _interrupted[0] = True
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    print("\n── Evolving ──")

    # ── Parallel + halving setup (GA path only; bayesian stays serial) ──
    # The pool is created ONCE per run, after the baselines warmed the
    # parent's Indicators cache, so the fork snapshot ships warm caches.
    screen_df, screen_from = _build_screen_frame(df) if halving else (None, None)
    halving_on = halving_active(halving, pop_size) and screen_df is not None
    pool_state = {"pool": None}
    if not bayesian:
        _set_parallel_context(df, ind, screen_df, screen_from)
        pool_state["pool"] = _create_eval_pool(workers)
        if pool_state["pool"] is not None:
            print(f"[parallel] fork pool: {_resolve_workers(workers)} workers")
        if halving_on:
            print(f"[halving] modern-era screen: {len(screen_df)} bars "
                  f"(eval from {str(screen_from)[:10]})")

    if bayesian:
        # Optuna's NSGA-II evaluates trials one-at-a-time through study
        # .optimize() (ask/tell), not as a batched population — there is no
        # generation-shaped map to parallelize or screen, so this path stays
        # serial and unscreened by design.
        print("Mode: Bayesian (Optuna NSGA-II Pareto)\n")
        per_strategy_hours = hours / max(1, len(active_strategies))
        for strat_name, fn in active_strategies.items():
            space = STRATEGY_PARAMS_FILTERED.get(strat_name, {})
            if not space:
                continue
            print(f"  Optimizing {strat_name} ({per_strategy_hours:.1f}h)...")
            discovery_score, fitness_score, params, result, best_val, n_trials, marker_score, marker_detail = evolve_bayesian(
                ind, df, strat_name, fn, space, per_strategy_hours, dedup_cache, history_stats)
            total_evals += n_trials
            strategy_bests[strat_name] = (
                discovery_score, fitness_score, params, result, marker_score, marker_detail
            )
            if discovery_score > best_run_discovery:
                best_run_discovery = discovery_score
                best_run_name = strat_name
                best_run_params = params.copy()
            if result:
                pareto_str = ""
                if isinstance(best_val, tuple) and len(best_val) == 3:
                    pareto_str = (
                        f" Pareto={best_val[0]:.3f}x/"
                        f"{best_val[1]:.1f}%/{best_val[2]:.3f}"
                    )
                print(f"    Best: discovery={discovery_score:.4f} fitness={fitness_score:.4f} "
                      f"marker={marker_score:.3f} share={result.share_multiple:.3f}x "
                      f"CAGR={result.cagr_pct:.1f}% DD={result.max_drawdown_pct:.1f}% "
                      f"{pareto_str} ({n_trials} trials)")
            generation = n_trials  # for report
    else:
        while time.time() < end_time and not _interrupted[0]:
            generation += 1

            for strat_name, fn in active_strategies.items():
                space = STRATEGY_PARAMS_FILTERED.get(strat_name, {})
                pop = populations[strat_name]
                strat_tier = STRATEGY_TIERS.get(strat_name, "T2")

                # Evaluate with dedup cache (v4: era metrics, fitness on the fly),
                # optional halving screen, and the once-per-run fork pool.
                scored, n_new = _evaluate_population(
                    pop, strat_name, fn, ind, df, dedup_cache, history_stats,
                    strat_tier, pool_state=pool_state, screen_df=screen_df,
                    screen_from=screen_from, halving_on=halving_on,
                )
                total_evals += n_new
                scored.sort(key=lambda x: x[0], reverse=True)

                # Update strategy best
                if scored[0][0] > strategy_bests[strat_name][0]:
                    strategy_bests[strat_name] = scored[0]

                # Update global best run candidate
                if scored[0][0] > best_run_discovery:
                    best_run_discovery = scored[0][0]
                    best_run_name = strat_name
                    best_run_params = scored[0][2].copy()

                # ── Diversity measurement (research: track normalized parameter variance) ──
                # Compute population diversity as mean normalized variance across params
                if space and len(scored) >= 4:
                    param_arrays = {}
                    for _, _, p, *_rest in scored:
                        for k, v in p.items():
                            if k in space:
                                param_arrays.setdefault(k, []).append(float(v))
                    diversities = []
                    for k, vals in param_arrays.items():
                        lo, hi = space[k][0], space[k][1]
                        rng = hi - lo
                        if rng > 0 and len(vals) >= 2:
                            diversities.append(np.std(vals) / rng)
                    pop_diversity = float(np.mean(diversities)) if diversities else 0.0
                else:
                    pop_diversity = 0.5  # assume moderate diversity when unmeasurable

                # Track initial diversity for DGEA comparison
                if generation == 1:
                    if not hasattr(evolve, '_initial_diversity'):
                        evolve._initial_diversity = {}
                    evolve._initial_diversity[strat_name] = max(pop_diversity, 0.01)

                initial_div = getattr(evolve, '_initial_diversity', {}).get(strat_name, 0.1)
                relative_diversity = pop_diversity / initial_div if initial_div > 0 else 0

                # ── Mutation survival rate (free convergence diagnostic) ──
                # Fraction of offspring retaining >90% of parent fitness
                if hasattr(evolve, '_prev_scored') and strat_name in evolve._prev_scored:
                    prev_best = evolve._prev_scored[strat_name]
                    survivors = sum(1 for s, *_rest in scored if s >= prev_best * 0.9)
                    mut_survival = survivors / len(scored) if scored else 0
                else:
                    mut_survival = 0.5  # unknown first gen
                if not hasattr(evolve, '_prev_scored'):
                    evolve._prev_scored = {}
                evolve._prev_scored[strat_name] = scored[0][0] if scored else 0

                # ── Adaptive mutation rate (research: diversity-driven, not time-based) ──
                # DGEA switching: low diversity → burst mode, high diversity → exploitation
                D_LOW = 0.15   # below 15% of initial diversity → burst
                D_HIGH = 0.60  # above 60% of initial → normal exploitation

                if relative_diversity < D_LOW:
                    # Diversity collapsed — burst mode (research: 30%+ mutation, large steps)
                    mut_rate = 0.40
                    mut_magnitude = 4  # ±1-4 steps
                elif relative_diversity < D_HIGH:
                    # Moderate diversity — balanced exploration
                    mut_rate = 0.20
                    mut_magnitude = 2  # ±1-2 steps
                else:
                    # High diversity — fine exploitation
                    mut_rate = 0.10
                    mut_magnitude = 1  # ±1 step

                # Selection + reproduction
                n_elite = max(2, int(pop_size * 0.2))
                elites = [s[2] for s in scored[:n_elite]]
                new_pop = list(elites)

                # Crossover
                for _ in range(pop_size // 3):
                    p1, p2 = random.sample(elites, min(2, len(elites)))
                    new_pop.append(crossover_params(p1, p2))

                # Mutation (adaptive rate + magnitude)
                while len(new_pop) < pop_size:
                    parent = random.choice(elites)
                    new_pop.append(mutate_params(parent, space, rate=mut_rate,
                                                 magnitude=mut_magnitude))

                # ── Diversity injection: 5% random individuals every generation ──
                # Research: 5-10% per gen (was 0.17%/gen = 1 individual every 15 gens)
                n_inject = max(1, int(pop_size * 0.05))  # 5% of pop = 2 individuals at pop=40
                for j in range(n_inject):
                    idx = len(new_pop) - 1 - j
                    if idx >= n_elite:  # don't overwrite elites
                        new_pop[idx] = random_params(space)

                populations[strat_name] = new_pop[:pop_size]

            # Track convergence
            gen_best = max(strategy_bests[s][0] for s in strategy_bests)
            convergence_history.append((generation, round(gen_best, 4)))

            # Progress report
            now = time.time()
            if now - last_report >= report_interval:
                remaining = (end_time - now) / 3600
                per_sec = total_evals / (now - start_time)
                print(f"Gen {generation:>5}: BEST_DISC={best_run_discovery:.4f} ({best_run_name})  "
                      f"evals={total_evals:,} ({per_sec:.0f}/s)  {remaining:.1f}h left")
                for s, (disc, fit, _params, res, marker_score, _marker_detail) in sorted(strategy_bests.items(), key=lambda x: -x[1][0]):
                    if res:
                        rs_str = f"RS={res.regime_score.composite:.3f}" if res.regime_score else "RS=?"
                        print(f"    {s:<22} disc={disc:.4f} fit={fit:.4f} marker={marker_score:.3f}  "
                              f"{rs_str}  share={res.share_multiple:.3f}x  "
                              f"t/yr={res.trades_per_year:.1f}  DD={res.max_drawdown_pct:.1f}%")
                last_report = now

    _close_eval_pool(pool_state)

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
        print("\n── 8.2.1 Baseline (the strategy to beat) ──")
        print(f"  share={bl_result.share_multiple:.3f}x  CAGR={bl_result.cagr_pct:.1f}%  "
              f"DD={bl_result.max_drawdown_pct:.1f}%  trades/yr={bl_result.trades_per_year:.1f}")

    print("\n── Strategy Rankings (vs 8.2.1) ──")
    for rank, (name, (discovery_score, fitness_score, params, result, marker_score, _marker_detail)) in enumerate(rankings, 1):
        if result:
            beat_str = ""
            if bl_result and bl_result.share_multiple > 0:
                improvement = (result.share_multiple / bl_result.share_multiple - 1) * 100
                beat_str = f"  {'BEATS' if result.share_multiple > bl_result.share_multiple else 'loses to'} 8.2.1 by {improvement:+.0f}%"
            print(f"  #{rank} {name:<22} discovery={discovery_score:.4f}  fitness={fitness_score:.4f}  "
                  f"marker={marker_score:.3f}  share={result.share_multiple:.3f}x  "
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
        discovery_score, fitness_score, params, result, marker_score, marker_detail = strategy_bests[strat_name]
        if (result is None or marker_detail is None) and discovery_score > 0 and strat_name in active_strategies:
            fitness_score, discovery_score, marker_score, marker_detail, result = evaluate(
                ind, df, active_strategies[strat_name], params, strat_name
            )
            strategy_bests[strat_name] = (
                discovery_score, fitness_score, params, result, marker_score, marker_detail
            )

    # ── Early filter: validation-aligned post-run gate (2026-06-09) ──
    # A full evolve() run is one "chunk"; both GA and bayesian paths land
    # here. Runs AFTER the cached-best re-evaluation so soft demotions are
    # not overwritten, and BEFORE save_hash_index so `pen` stamps persist.
    early_filter_report = []
    if early_filter:
        early_filter_report = _apply_early_filter_to_bests(
            df, active_strategies, strategy_bests, dedup_cache
        )
        if any(a["action"] == "exclude" for a in early_filter_report):
            # Recompute the run winner from the surviving bests.
            best_run_discovery, best_run_name, best_run_params = 0.0, "", {}
            for s_name, tup in strategy_bests.items():
                if tup[0] > best_run_discovery:
                    best_run_discovery = tup[0]
                    best_run_name = s_name
                    best_run_params = dict(tup[2])

    # Re-sort after re-evaluation + filtering
    rankings = sorted(strategy_bests.items(), key=lambda x: -x[1][0])

    # ── Save hash index ──
    save_hash_index(dedup_cache)
    print(f"\n[history] Saved hash index: {len(dedup_cache):,} unique configs")

    history_stats["total_history"] = len(dedup_cache)

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
                "fitness": round(fitness_score, 4),
                "params": params,
                "metrics": {
                    "share_multiple": round(result.share_multiple, 4),
                    "real_share_multiple": round(result.real_share_multiple, 4),
                    "modern_share_multiple": round(result.modern_share_multiple, 4),
                    "cagr": round(result.cagr_pct, 2),
                    "max_dd": round(result.max_drawdown_pct, 1),
                    "mar": round(result.mar_ratio, 3),
                    "trades": result.num_trades,
                    "trades_yr": round(result.trades_per_year, 1),
                    "win_rate": round(result.win_rate_pct, 1),
                    "exit_reasons": result.exit_reasons,
                    # Regime score metrics (new — research-aligned)
                    "regime_score": round(result.regime_score.composite, 4) if result.regime_score else 0,
                    "bull_capture": round(result.regime_score.bull_capture_ratio, 4) if result.regime_score else 0,
                    "bear_avoidance": round(result.regime_score.bear_avoidance_ratio, 4) if result.regime_score else 0,
                    "hhi": round(result.regime_score.hhi, 4)
                    if result.regime_score and result.regime_score.hhi is not None else 0,
                    "n_params": _count_tunable_params(params),
                } if result else None,
                "discovery_score": round(discovery_score, 4),
                "marker_alignment_score": round(marker_score, 4),
                "marker_alignment_detail": marker_detail,
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
            for i, (name, (discovery_score, fitness_score, params, result, marker_score, marker_detail)) in enumerate(rankings)
        ],
        "best_ever": {
            "strategy": historical_best_name,
            "fitness": round(historical_best_fitness, 4),
            "params": historical_best_params,
        },
        # Why each chunk-top config was kept/demoted/excluded (2026-06-09).
        "early_filter": early_filter_report,
    }

    leaderboard_path = os.path.join(HISTORY_DIR, "leaderboard.json")
    leaderboard = None
    if publish_leaderboard:
        leaderboard = update_leaderboard(results, leaderboard_path)

    # Save results JSON
    if run_dir:
        out_path = os.path.join(run_dir, "results.json")
    else:
        # Even without spike_runner, save into the runs/ structure
        runs_base = os.path.join(PROJECT_ROOT, "spike", "runs")
        os.makedirs(runs_base, exist_ok=True)
        existing = [
            d for d in os.listdir(runs_base)
            if os.path.isdir(os.path.join(runs_base, d)) and d.isdigit()
        ]
        next_num = max((int(d) for d in existing), default=0) + 1
        fallback_dir = os.path.join(runs_base, f"{next_num:03d}")
        os.makedirs(fallback_dir, exist_ok=True)
        out_path = os.path.join(fallback_dir, "results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, cls=_Enc)
    print(f"\nResults: {out_path}")

    # Generate markdown report
    if write_report:
        try:
            from diagnostics.report import generate_report
            prev_best_snapshot = {
                "strategy": historical_best_name,
                "fitness": historical_best_fitness,
            } if historical_best_fitness > 0 else None
            report_dir = run_dir or fallback_dir
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



# ─────────────────────────────────────────────────────────────────────
# evolve_chunk() — pause/resume optimizer for /spike v2
# ─────────────────────────────────────────────────────────────────────

def detect_boundary_hits(best_params: dict, space: dict, threshold: float = 0.1) -> dict:
    """
    Check if any best param values are near the edge of their search space.
    Returns {param_name: "high" | "low" | None}.
    """
    hits = {}
    for name, (lo, hi, step, typ) in space.items():
        val = best_params.get(name)
        if val is None:
            hits[name] = None
            continue
        rng = hi - lo
        if rng == 0:
            hits[name] = None
            continue
        if (val - lo) / rng < threshold:
            hits[name] = "low"
        elif (hi - val) / rng < threshold:
            hits[name] = "high"
        else:
            hits[name] = None
    return hits


def evolve_chunk(
    minutes: float = 20.0,
    pop_size: int = 40,
    run_dir: str | None = None,
    strategies: list[str] | None = None,
    state: dict | None = None,
    df: object = None,
    early_filter: bool = True,
    workers: int | None = None,
    halving: bool = True,
) -> dict:
    """
    Run the optimizer for a fixed number of minutes, then return results + state.

    This is the building block for /spike v2's iterative loop. Call with
    state=None to start fresh; pass the returned state dict to resume.

    Parameters
    ----------
    df : optional DataFrame to use instead of TECL. Pass TQQQ/QQQ data
         for cross-asset re-optimization (Tier 3 validation).
    early_filter : post-chunk validation-aligned filter on the chunk's top
         configs (execution realism + event dependence; 2026-06-09)
    workers : fork-pool size for population evaluation (None → cpu_count-2;
         <=1 → serial)
    halving : successive-halving modern-era screen (off below pop 16)

    Returns dict with:
      rankings: sorted strategy results
      state: serializable dict to pass to the next chunk
      diagnostics: per-strategy boundary hits, diversity, improvement
      best_ever: {strategy, fitness, params}
      early_filter: per-config filter annotations (why kept/demoted/excluded)
    """
    from strategies.library import STRATEGY_REGISTRY, STRATEGY_PARAMS

    # Filter strategies
    if strategies:
        REG = {k: v for k, v in STRATEGY_REGISTRY.items() if k in strategies}
        PAR = {k: v for k, v in STRATEGY_PARAMS.items() if k in strategies}
    else:
        REG = STRATEGY_REGISTRY
        PAR = STRATEGY_PARAMS

    start_time = time.time()
    end_time = start_time + minutes * 60

    if df is None:
        df = get_tecl_data(use_yfinance=False)
    ind = Indicators(df)

    dedup_cache = load_hash_index()
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0,
                     "screen_evals": 0, "pruned_screen": 0}

    leaderboard_path = os.path.join(HISTORY_DIR, "leaderboard.json")

    if state is None:
        # ── Fresh start ──
        print(f"[chunk] Fresh start — {minutes:.0f}m, {len(REG)} strategies, pop={pop_size}")

        # Baselines
        baselines = {}
        for name, fn in REG.items():
            space = PAR.get(name, {})
            default_params = {k: (lo + hi) / 2 for k, (lo, hi, step, typ) in space.items()}
            for k, (lo, hi, step, typ) in space.items():
                if typ == int:
                    default_params[k] = int(round(default_params[k]))
            fitness_score, discovery_score, marker_score, _marker_detail, _result = evaluate(
                ind, df, fn, default_params, name
            )
            baselines[name] = {
                "fitness": fitness_score,
                "discovery_score": discovery_score,
                "marker_alignment_score": marker_score,
                "params": default_params,
            }

        # Initialize populations
        populations = {}
        max_seed = max(2, int(pop_size * 0.2))
        for name in REG:
            space = PAR.get(name, {})
            pop = [baselines[name]["params"].copy()]
            lb_winners = get_top_from_leaderboard(leaderboard_path, name, n=max_seed)
            for lw in lb_winners:
                if len(pop) < pop_size:
                    pop.append(lw)
            while len(pop) < pop_size:
                pop.append(random_params(space))
            populations[name] = pop

        # Load best-ever from leaderboard
        best_ever_score = 0.0
        best_ever_name = ""
        best_ever_params = {}
        if os.path.exists(leaderboard_path):
            try:
                with open(leaderboard_path) as f:
                    lb = json.load(f)
                if lb and lb[0].get("fitness", 0) > best_ever_score:
                    best_ever_score = lb[0]["fitness"]
                    best_ever_name = lb[0].get("strategy", "")
                    best_ever_params = lb[0].get("params", {})
            except Exception:
                pass

        generation = 0
        total_evals = 0
        strategy_bests = {
            name: (0.0, 0.0, {}, NEUTRAL_MARKER_SCORE)
            for name in REG
        }
        convergence_history = []
        initial_diversity = {}
        prev_scored = {}
    else:
        # ── Resume from state ──
        print(f"[chunk] Resuming from gen {state['generation']} — {minutes:.0f}m")
        populations = state["populations"]
        best_ever_score = state["best_ever_score"]
        best_ever_name = state["best_ever_name"]
        best_ever_params = state["best_ever_params"]
        generation = state["generation"]
        total_evals = state["total_evals"]
        strategy_bests = {
            k: (
                v.get("discovery_score", v.get("score", 0.0)),
                v.get("fitness_score", v.get("score", 0.0)),
                v.get("params", {}),
                v.get("marker_alignment_score", NEUTRAL_MARKER_SCORE),
            )
            for k, v in state["strategy_bests"].items()
        }
        convergence_history = state.get("convergence_history", [])
        initial_diversity = state.get("initial_diversity", {})
        prev_scored = state.get("prev_scored", {})

        # Handle strategy registry drift (strategies added/removed between chunks)
        for name in list(populations.keys()):
            if name not in REG:
                del populations[name]
                if name in strategy_bests:
                    del strategy_bests[name]
        for name in REG:
            if name not in populations:
                space = PAR.get(name, {})
                populations[name] = [random_params(space) for _ in range(pop_size)]
                strategy_bests[name] = (0.0, 0.0, {}, NEUTRAL_MARKER_SCORE)

    # ── GA loop ──
    _interrupted = [False]
    def _handle_signal(sig, frame):
        _interrupted[0] = True
    old_sigint = signal.signal(signal.SIGINT, _handle_signal)
    old_sigterm = signal.signal(signal.SIGTERM, _handle_signal)

    last_report = start_time
    gen_start = generation

    # Once-per-chunk fork pool + halving screen frame (2026-06-09). The
    # parent's Indicators cache (warmed by baselines on fresh starts) rides
    # into the workers via the fork snapshot of _PARALLEL_CTX.
    screen_df, screen_from = _build_screen_frame(df) if halving else (None, None)
    halving_on = halving_active(halving, pop_size) and screen_df is not None
    _set_parallel_context(df, ind, screen_df, screen_from)
    pool_state = {"pool": _create_eval_pool(workers)}
    if pool_state["pool"] is not None:
        print(f"[parallel] fork pool: {_resolve_workers(workers)} workers")
    if halving_on:
        print(f"[halving] modern-era screen: {len(screen_df)} bars "
              f"(eval from {str(screen_from)[:10]})")

    try:
        while time.time() < end_time and not _interrupted[0]:
            generation += 1

            for strat_name, fn in REG.items():
                space = PAR.get(strat_name, {})
                pop = populations[strat_name]
                strat_tier = STRATEGY_TIERS.get(strat_name, "T2")

                # Evaluate (dedup in parent, screen + full evals via pool)
                scored, n_new = _evaluate_population(
                    pop, strat_name, fn, ind, df, dedup_cache, history_stats,
                    strat_tier, pool_state=pool_state, screen_df=screen_df,
                    screen_from=screen_from, halving_on=halving_on,
                )
                total_evals += n_new
                scored.sort(key=lambda x: x[0], reverse=True)

                # Update bests
                if scored[0][0] > strategy_bests.get(strat_name, (0.0,))[0]:
                    strategy_bests[strat_name] = (
                        scored[0][0],
                        scored[0][1],
                        scored[0][2],
                        scored[0][4],
                    )
                if scored[0][0] > best_ever_score:
                    best_ever_score = scored[0][0]
                    best_ever_name = strat_name
                    best_ever_params = scored[0][2].copy()

                # Diversity measurement
                if space and len(scored) >= 4:
                    param_arrays = {}
                    for _, _, p, *_rest in scored:
                        for k, v in p.items():
                            if k in space:
                                param_arrays.setdefault(k, []).append(float(v))
                    diversities = []
                    for k, vals in param_arrays.items():
                        lo, hi = space[k][0], space[k][1]
                        rng = hi - lo
                        if rng > 0 and len(vals) >= 2:
                            diversities.append(np.std(vals) / rng)
                    pop_diversity = float(np.mean(diversities)) if diversities else 0.0
                else:
                    pop_diversity = 0.5

                if generation == gen_start + 1:
                    initial_diversity[strat_name] = max(pop_diversity, 0.01)

                init_div = initial_diversity.get(strat_name, 0.1)
                relative_diversity = pop_diversity / init_div if init_div > 0 else 0

                # Mutation survival rate
                if strat_name in prev_scored:
                    prev_best = prev_scored[strat_name]
                    survivors = sum(1 for s, *_rest in scored if s >= prev_best * 0.9)
                    mut_survival = survivors / len(scored) if scored else 0
                else:
                    mut_survival = 0.5
                prev_scored[strat_name] = scored[0][0] if scored else 0

                # DGEA mutation
                D_LOW, D_HIGH = 0.15, 0.60
                if relative_diversity < D_LOW:
                    mut_rate, mut_magnitude = 0.40, 4
                elif relative_diversity < D_HIGH:
                    mut_rate, mut_magnitude = 0.20, 2
                else:
                    mut_rate, mut_magnitude = 0.10, 1

                # Reproduction
                n_elite = max(2, int(pop_size * 0.2))
                elites = [s[2] for s in scored[:n_elite]]
                new_pop = list(elites)
                for _ in range(pop_size // 3):
                    p1, p2 = random.sample(elites, min(2, len(elites)))
                    new_pop.append(crossover_params(p1, p2))
                while len(new_pop) < pop_size:
                    parent = random.choice(elites)
                    new_pop.append(mutate_params(parent, space, rate=mut_rate, magnitude=mut_magnitude))

                n_inject = max(1, int(pop_size * 0.05))
                for j in range(n_inject):
                    idx = len(new_pop) - 1 - j
                    if idx >= n_elite:
                        new_pop[idx] = random_params(space)

                populations[strat_name] = new_pop[:pop_size]

            gen_best = max(strategy_bests[s][0] for s in strategy_bests)
            convergence_history.append((generation, round(gen_best, 4)))

            # Progress
            now = time.time()
            if now - last_report >= 30:
                remaining = (end_time - now) / 60
                print(f"  Gen {generation}: BEST={best_ever_score:.4f} ({best_ever_name}) "
                      f"evals={total_evals:,} {remaining:.0f}m left")
                last_report = now

    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)
        _close_eval_pool(pool_state)

    # ── Early filter: validation-aligned post-chunk gate (2026-06-09) ──
    # Runs before save_hash_index so hard-breach `pen` stamps persist.
    early_filter_report = []
    if early_filter:
        early_filter_report = _apply_early_filter_to_bests(
            df, REG, strategy_bests, dedup_cache
        )
        excluded_hashes = {
            a["config_hash"] for a in early_filter_report if a["action"] == "exclude"
        }
        if excluded_hashes and config_hash(best_ever_name, best_ever_params) in excluded_hashes:
            # The chunk champion itself breached — fall back to the best
            # surviving config (prior-chunk bests live in strategy_bests too).
            best_ever_score, best_ever_name, best_ever_params = 0.0, "", {}
            for s_name, tup in strategy_bests.items():
                if tup[0] > best_ever_score:
                    best_ever_score = tup[0]
                    best_ever_name = s_name
                    best_ever_params = dict(tup[2])

    # Save dedup cache
    save_hash_index(dedup_cache)

    # Build diagnostics
    diagnostics = {}
    for strat_name in REG:
        space = PAR.get(strat_name, {})
        best_discovery, best_fitness, best_params, best_marker = strategy_bests.get(
            strat_name, (0.0, 0.0, {}, NEUTRAL_MARKER_SCORE)
        )
        diagnostics[strat_name] = {
            "best_discovery_score": round(best_discovery, 4),
            "best_fitness_score": round(best_fitness, 4),
            "best_marker_alignment_score": round(best_marker, 4),
            "best_params": best_params,
            "boundary_hits": detect_boundary_hits(best_params, space),
            "diversity": round(initial_diversity.get(strat_name, 0), 4),
        }

    # Re-evaluate bests that were cached (no full result)
    rankings = []
    for strat_name, (discovery_score, fitness_score, params, marker_score, ) in sorted(
        strategy_bests.items(), key=lambda x: -x[1][0]
    ):
        fitness_score, discovery_score, marker_score, marker_detail, result = evaluate(
            ind, df, REG[strat_name], params, strat_name
        )
        rankings.append({
            "strategy": strat_name,
            "fitness": round(fitness_score, 4),
            "discovery_score": round(discovery_score, 4),
            "marker_alignment_score": round(marker_score, 4),
            "marker_alignment_detail": marker_detail,
            "params": params,
            "metrics": {
                "share_multiple": round(result.share_multiple, 4) if result else 0,
                "real_share_multiple": round(result.real_share_multiple, 4) if result else 0,
                "modern_share_multiple": round(result.modern_share_multiple, 4) if result else 0,
                "cagr": round(result.cagr_pct, 1) if result else 0,
                "max_dd": round(result.max_drawdown_pct, 1) if result else 0,
                "trades": result.num_trades if result else 0,
                "trades_yr": round(result.trades_per_year, 1) if result else 0,
            },
        })

    elapsed = (time.time() - start_time) / 60
    gens_this_chunk = generation - gen_start
    print(f"[chunk] Done — {elapsed:.1f}m, {gens_this_chunk} generations, {total_evals:,} evals")

    # Serializable state for next chunk
    out_state = {
        "populations": populations,
        "best_ever_score": best_ever_score,
        "best_ever_name": best_ever_name,
        "best_ever_params": best_ever_params,
        "generation": generation,
        "total_evals": total_evals,
        "strategy_bests": {
            k: {
                "discovery_score": v[0],
                "fitness_score": v[1],
                "params": v[2],
                "marker_alignment_score": v[3],
            }
            for k, v in strategy_bests.items()
        },
        "convergence_history": convergence_history,
        "initial_diversity": initial_diversity,
        "prev_scored": prev_scored,
    }

    return {
        "rankings": rankings,
        "state": out_state,
        "diagnostics": diagnostics,
        "best_ever": {
            "strategy": best_ever_name,
            "fitness": round(best_ever_score, 4),
            "params": best_ever_params,
        },
        "elapsed_minutes": round(elapsed, 1),
        "generations": gens_this_chunk,
        "total_evals": total_evals,
        # Why each chunk-top config was kept/demoted/excluded (2026-06-09).
        "early_filter": early_filter_report,
    }


def main():
    parser = argparse.ArgumentParser(description="Montauk Multi-Strategy Optimizer")
    parser.add_argument("--hours", type=float, default=5.0)
    parser.add_argument("--pop-size", type=int, default=40)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--bayesian", action="store_true",
                        help="Use Optuna NSGA-II multi-objective search")
    parser.add_argument("--workers", type=int, default=None,
                        help="Fork-pool size for population eval (default cpu_count-2; 1=serial)")
    parser.add_argument("--no-early-filter", action="store_true",
                        help="Skip the post-run validation-aligned early filter")
    parser.add_argument("--no-halving", action="store_true",
                        help="Skip the successive-halving modern-era screen")
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
        from strategies.library import STRATEGY_REGISTRY, STRATEGY_PARAMS
        for name in STRATEGY_REGISTRY:
            space = STRATEGY_PARAMS.get(name, {})
            print(f"  {name:<22} {len(space)} params")
        return

    evolve(hours=args.hours, pop_size=args.pop_size, quick=args.quick,
           bayesian=args.bayesian, workers=args.workers,
           early_filter=not args.no_early_filter, halving=not args.no_halving)


if __name__ == "__main__":
    main()

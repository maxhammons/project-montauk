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
import os
import signal
import sys
import time
import random
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest, BacktestResult
from engine.regime_helpers import score_regime_capture
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
    """Hash core optimizer files so engine fixes invalidate stale cache keys.
    Files moved to subfolders by the 2026-04-20 restructure."""
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/
    digest = hashlib.sha256()
    for rel_path in (
        os.path.join("engine", "strategy_engine.py"),
        os.path.join("search", "evolve.py"),
        os.path.join("strategies", "library.py"),
    ):
        path = os.path.join(scripts_dir, rel_path)
        with open(path, "rb") as f:
            digest.update(rel_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(f.read())
            digest.update(b"\0")
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

    Format v3 (current): {config_hash: {"bah": share_multiple, "rs": regime_score, "dd": max_dd, "nt": num_trades, "np": n_params, "hhi": hhi}}
    Format v2 (old): {config_hash: {"f": fitness, "rs": regime_score}}
    Format v1 (old): {config_hash: fitness}

    v1 and v2 entries are stale — they don't store raw metrics, so fitness
    can't be recomputed. They're migrated with bah=None and will be
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
                    migrated = {h: {"bah": None, "rs": None, "dd": None, "nt": 0, "np": 0, "hhi": None} for h in raw}
                    print(f"[history] Migrated {n:,} v1 entries to v3 format (bah=None, will re-evaluate)")
                    return migrated
                # Check for v2 entries (have "f" key but no "bah" key)
                if isinstance(sample, dict) and "f" in sample and "bah" not in sample:
                    n = len(raw)
                    migrated = {h: {"bah": None, "rs": v.get("rs"), "dd": None, "nt": 0, "np": 0, "hhi": None} for h, v in raw.items()}
                    print(f"[history] Migrated {n:,} v2 entries to v3 format (bah=None, will re-evaluate)")
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
                        index[h] = {"bah": None, "rs": None, "dd": None, "nt": 0, "np": 0, "hhi": None}
            save_hash_index(index)
            print(f"[history] Migrated {len(index):,} unique configs to hash-index.json")
            return index
        except Exception as e:
            print(f"[history] Warning: migration failed: {e}")
            return {}

    return {}


def save_hash_index(index: dict):
    """Save the hash index to disk. Prunes stale/empty entries to control size.

    v3 format: {hash: {"bah": share_multiple, "rs": regime_score, "dd": max_dd, "nt": num_trades, "np": n_params, "hhi": hhi}}
    Entries with bah=None or bah=0 are pruned (they need re-evaluation anyway).
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    pruned = {}
    for h, v in index.items():
        if isinstance(v, dict) and v.get("bah"):
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

# Engine-level certification checks that must pass for a strategy to be admitted
# to the leaderboard. Excludes `artifact_completeness` (a deployment-only check
# that is champion-specific; fixed up by spike_runner._finalize_champion_certification).
# Per the charter (see docs/charter.md and project-status.md): the leaderboard is a
# statement of "not overfit, will generalize into the future" — it requires the
# full 7-gate validation pipeline (promotion_ready) AND the engine-level integrity
# checks (engine_integrity, golden_regression, shadow_comparator, data_quality).
REQUIRED_CERTIFICATION_CHECKS = (
    "engine_integrity",
    "golden_regression",
    "shadow_comparator",
    "data_quality_precheck",
)


LEADERBOARD_WATCHLIST_CONFIDENCE = 0.60
LEADERBOARD_ADMIT_CONFIDENCE = 0.70


def _is_leaderboard_eligible(entry: dict) -> tuple[bool, str]:
    """Return (eligible, reason) — whether an entry may be admitted to the leaderboard.

    Under the 2026-04-21 confidence-score framework:
      - Entries with `composite_confidence >= 0.70` are admitted (PASS verdict).
      - Entries with 0.60 <= composite < 0.70 are visible as "watchlist" (WARN).
      - Entries below 0.60 are hidden (FAIL or research-only).
      - All admitted/watchlist entries must still pass REQUIRED_CERTIFICATION_CHECKS
        (engine integrity, golden regression, shadow comparator, data quality).

    Legacy leaderboard entries without a `validation` block are grandfathered in.
    """
    validation = entry.get("validation") or {}
    if not validation:
        return True, "legacy_entry"
    composite = float(validation.get("composite_confidence") or 0.0)
    if composite < LEADERBOARD_WATCHLIST_CONFIDENCE:
        return False, f"composite_confidence={composite:.3f} < {LEADERBOARD_WATCHLIST_CONFIDENCE:.2f}"
    checks = validation.get("certification_checks") or {}
    failing = [
        name for name in REQUIRED_CERTIFICATION_CHECKS
        if not (checks.get(name) or {}).get("passed", False)
    ]
    if failing:
        return False, f"certification checks failing: {', '.join(failing)}"
    return True, "ok"


def update_leaderboard(results: dict, leaderboard_path: str) -> list:
    """
    Update the all-time top-20 leaderboard with convergence tracking.

    Each strategy (by name) tracks:
    - best_fitness: highest fitness ever seen for this strategy name
    - runs_without_improvement: consecutive runs where this strategy didn't beat its best
    - converged: True when runs_without_improvement >= CONVERGE_RUNS

    Convergence is per-strategy-name (not per-config). Once a strategy is converged,
    Claude should skip optimizing it and focus effort elsewhere.

    **Leaderboard guard (2026-04-20):** entries are only admitted if they are
    promotion_ready AND pass every required engine-level certification check
    (see REQUIRED_CERTIFICATION_CHECKS). This enforces the charter rule that a
    leaderboard entry is a certification of "not overfit, will work into the
    future" — no candidate that hasn't cleared the full validation + engine
    integrity stack can be on the board.

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
        # Leaderboard guard: admit only promotion_ready + engine-certified entries.
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
        from strategies.naming import assign_display_name

        lb_entry = {
            "strategy": name,
            "display_name": assign_display_name(
                name, entry.get("params", {}), name_registry_path
            ),
            "fitness": new_fitness,
            "params": entry.get("params", {}),
            "metrics": entry["metrics"],
            "date": date,
            "converged": strategy_state[name]["converged"],
            "runs_without_improvement": strategy_state[name]["runs_without_improvement"],
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

    # Deduplicate: keep highest-confidence entry per config hash.
    def _entry_confidence(entry: dict) -> float:
        return float((entry.get("validation") or {}).get("composite_confidence") or 0.0)

    seen = {}
    for entry in leaderboard:
        h = config_hash(entry["strategy"], entry.get("params", {}))
        if h not in seen or _entry_confidence(entry) > _entry_confidence(seen[h]):
            seen[h] = entry
    # Leaderboard order is confidence-first (primary metric under the 2026-04-21
    # framework), fitness as tie-breaker.
    leaderboard = sorted(
        seen.values(),
        key=lambda x: (_entry_confidence(x), x.get("fitness", 0)),
        reverse=True,
    )[:20]

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
# Cache format v3: stores raw backtest metrics {bah, rs, dd, nt, np, hhi, ma}
# so fitness can be recomputed on the fly when the formula changes,
# without re-running backtests.

MAX_TRADES_PER_YEAR = 5.0  # charter boundary: regime strategy, not scalper (was 3.0 pre-2026-04-13)


def fitness_from_cache(entry: dict, *, tier: str = "T2") -> float:
    """Compute fitness from cached raw metrics (v3 cache entry).

    Same formula as fitness() but operates on stored metrics dict.
    Returns 0.0 if any required field is None.
    Note: trades_per_year gate can't be applied from cache (no years info) —
    cached entries already passed through full fitness() once.

    Tier-aware: T0 skips the trades-per-param gate (canonical pre-registration
    is the structural defense; see fitness() docstring).
    """
    share_mult = entry.get("bah")
    if share_mult is None or share_mult <= 0:
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

    # HHI penalty
    hhi_penalty = max(0.5, 1.0 - max(0, hhi - 0.15) * 3)

    # Drawdown penalty
    dd_penalty = max(0.3, 1.0 - dd / 120.0)

    # Complexity penalty REMOVED (2026-04-13 third revision) — see fitness().
    complexity_penalty = 1.0

    # Regime quality multiplier
    rs = entry.get("rs") or 0
    regime_mult = 0.4 + 0.6 * min(1.0, rs / 0.7)

    return share_mult * hhi_penalty * dd_penalty * complexity_penalty * regime_mult


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
    from search.fitness import weighted_era_fitness

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
        "rs": round(regime_score.composite, 4) if regime_score else None,
        "dd": round(result.max_drawdown_pct, 1) if result else None,
        "nt": result.num_trades if result else 0,
        "np": _count_tunable_params(params),
        "hhi": hhi,
        "ma": round(float(marker_alignment_score), 4)
        if marker_alignment_score is not None else None,
    }


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
    share_mult = entry.get("bah")
    dd = entry.get("dd")
    num_trades = entry.get("nt") or 0
    n_params = entry.get("np") or 0
    hhi = entry.get("hhi")
    if hhi is None:
        hhi = 0.0
    if share_mult is None or dd is None:
        return None
    trades_per_year = (num_trades / dataset_years) if dataset_years > 0 else 0.0
    if not _passes_pareto_hard_gates(num_trades, trades_per_year, n_params, float(hhi)):
        return None
    return float(share_mult), float(dd), float(hhi)


def _objectives_from_result(result: BacktestResult | None) -> tuple[float, float, float] | None:
    if result is None:
        return None
    hhi = 0.0
    if result.regime_score and result.regime_score.hhi is not None:
        hhi = float(result.regime_score.hhi)
    n_params = _count_tunable_params(result.params)
    if not _passes_pareto_hard_gates(result.num_trades, result.trades_per_year, n_params, hhi):
        return None
    return float(result.share_multiple), float(result.max_drawdown_pct), hhi


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
        if cached and isinstance(cached, dict) and cached.get("bah") is not None:
            history_stats["cached_configs"] += 1
            objectives = _objectives_from_cache(cached, dataset_years)
            if objectives is None:
                raise optuna.TrialPruned()
            return objectives

        fitness_score, _discovery_score, marker_score, _marker_detail, result = evaluate(
            ind, df, strategy_fn, params, strategy_name
        )
        history_stats["new_configs"] += 1

        # Store to cache (v3 format)
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


def evolve(hours: float = 8.0, pop_size: int = 40, quick: bool = False,
           run_dir: str | None = None, strategies: list[str] | None = None,
           bayesian: bool = False, publish_leaderboard: bool = True,
           write_report: bool = True) -> dict:
    """
    Run the evolutionary optimizer. Returns the results dict.

    Parameters
    ----------
    hours : how long to run
    pop_size : population per strategy per generation
    quick : shorter report intervals
    run_dir : directory to save results (optional, for spike_runner)
    strategies : optional list of strategy names to run (default: all)
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
        STRATEGY_REGISTRY_FILTERED = STRATEGY_REGISTRY
        STRATEGY_PARAMS_FILTERED = STRATEGY_PARAMS

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
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0}

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

    if bayesian:
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

                # Evaluate with dedup cache (v3: stores raw metrics, fitness computed on the fly)
                scored = []
                for params in pop:
                    h = config_hash(strat_name, params)
                    cached = dedup_cache.get(h)
                    if cached and isinstance(cached, dict) and cached.get("bah") is not None:
                        # v3 cache hit — recompute fitness from raw metrics
                        fitness_score = fitness_from_cache(cached, tier=strat_tier)
                        marker_score = cached.get("ma", NEUTRAL_MARKER_SCORE)
                        discovery_score = discovery_score_from_cache(cached, tier=strat_tier)
                        scored.append((discovery_score, fitness_score, params, None, marker_score, None))
                        history_stats["cached_configs"] += 1
                    else:
                        # New config or stale entry (bah=None) — must evaluate
                        fitness_score, discovery_score, marker_score, marker_detail, result = evaluate(
                            ind, df, fn, params, strat_name
                        )
                        total_evals += 1
                        scored.append((discovery_score, fitness_score, params, result, marker_score, marker_detail))
                        dedup_cache[h] = _cache_entry_from_result(params, result, marker_score)
                        history_stats["new_configs"] += 1
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

    # Re-sort after re-evaluation
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
) -> dict:
    """
    Run the optimizer for a fixed number of minutes, then return results + state.

    This is the building block for /spike v2's iterative loop. Call with
    state=None to start fresh; pass the returned state dict to resume.

    Parameters
    ----------
    df : optional DataFrame to use instead of TECL. Pass TQQQ/QQQ data
         for cross-asset re-optimization (Tier 3 validation).

    Returns dict with:
      rankings: sorted strategy results
      state: serializable dict to pass to the next chunk
      diagnostics: per-strategy boundary hits, diversity, improvement
      best_ever: {strategy, fitness, params}
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
    history_stats = {"cached_configs": 0, "new_configs": 0, "seeded_per_strategy": 0}

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

    try:
        while time.time() < end_time and not _interrupted[0]:
            generation += 1

            for strat_name, fn in REG.items():
                space = PAR.get(strat_name, {})
                pop = populations[strat_name]
                strat_tier = STRATEGY_TIERS.get(strat_name, "T2")

                # Evaluate
                scored = []
                for params in pop:
                    h = config_hash(strat_name, params)
                    cached = dedup_cache.get(h)
                    if cached and isinstance(cached, dict) and cached.get("bah") is not None:
                        fitness_score = fitness_from_cache(cached, tier=strat_tier)
                        marker_score = cached.get("ma", NEUTRAL_MARKER_SCORE)
                        discovery_score = discovery_score_from_cache(cached, tier=strat_tier)
                        scored.append((discovery_score, fitness_score, params, None, marker_score, None))
                        history_stats["cached_configs"] += 1
                    else:
                        fitness_score, discovery_score, marker_score, marker_detail, result = evaluate(
                            ind, df, fn, params, strat_name
                        )
                        total_evals += 1
                        scored.append((discovery_score, fitness_score, params, result, marker_score, marker_detail))
                        dedup_cache[h] = _cache_entry_from_result(params, result, marker_score)
                        history_stats["new_configs"] += 1
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
    }


def main():
    parser = argparse.ArgumentParser(description="Montauk Multi-Strategy Optimizer")
    parser.add_argument("--hours", type=float, default=5.0)
    parser.add_argument("--pop-size", type=int, default=40)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--bayesian", action="store_true",
                        help="Use Optuna NSGA-II multi-objective search")
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

    evolve(hours=args.hours, pop_size=args.pop_size, quick=args.quick, bayesian=args.bayesian)


if __name__ == "__main__":
    main()

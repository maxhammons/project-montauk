"""Unit tests for the 2026-06-09 evolve.py search upgrades.

Covers the pure decision logic behind the three features added to
`scripts/search/evolve.py` — none of these tests run a backtest:

* validation-aligned early filter (hard / soft / none decisions)
* successive-halving promotion math (top-frac, min-8 floor, off-below-16)
* pruned hash-index entry shape (dedup-skips, never ranks, never seeds)
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

import validation.candidate as candidate
from search import early_filter as ef
from search.evolve import (
    HASH_INDEX_FILE,  # noqa: F401  (documents what save_hash_index targets)
    _build_screen_frame,
    _cache_entry_from_result,
    _cache_entry_ready,
    _objectives_from_cache,
    discovery_score_from_cache,
    fitness_from_cache,
    save_hash_index,
)


# ─────────────────────────────────────────────────────────────────────────────
# Early-filter decision logic (feature A)
# ─────────────────────────────────────────────────────────────────────────────


class TestFilterDecision:
    def test_hard_breach_by_degradation(self):
        assert ef.filter_decision(-30.0, 0.0) == "hard"
        assert ef.filter_decision(-45.0, 0.0) == "hard"
        assert ef.filter_decision(-100.0, 0.0) == "hard"

    def test_hard_breach_by_collapse(self):
        assert ef.filter_decision(0.0, 0.95) == "hard"
        assert ef.filter_decision(0.0, 1.0) == "hard"

    def test_hard_wins_over_soft_when_both_breach(self):
        assert ef.filter_decision(-31.0, 0.85) == "hard"
        assert ef.filter_decision(-16.0, 0.96) == "hard"

    def test_soft_breach_by_degradation(self):
        assert ef.filter_decision(-15.0, 0.0) == "soft"
        assert ef.filter_decision(-29.9, 0.0) == "soft"

    def test_soft_breach_by_collapse(self):
        assert ef.filter_decision(0.0, 0.80) == "soft"
        assert ef.filter_decision(0.0, 0.94) == "soft"

    def test_no_breach(self):
        assert ef.filter_decision(-14.9, 0.79) == "none"
        assert ef.filter_decision(0.0, 0.0) == "none"
        assert ef.filter_decision(5.0, 0.5) == "none"

    def test_thresholds_are_the_validation_gates(self):
        # The early filter must never drift from validation/candidate.py —
        # it imports the gate constants rather than redefining them.
        assert ef.filter_decision(candidate.EXECUTION_DEGRADATION_FAIL, 0.0) == "hard"
        assert ef.filter_decision(0.0, candidate.EVENT_COLLAPSE_FAIL) == "hard"
        assert ef.filter_decision(candidate.EXECUTION_DEGRADATION_WARN, 0.0) == "soft"
        assert ef.filter_decision(0.0, candidate.EVENT_COLLAPSE_WARN) == "soft"

    def test_penalty_constants(self):
        assert 0.0 < ef.HARD_CACHE_FITNESS_PENALTY < 1.0
        assert 0.0 < ef.SOFT_RANK_MULTIPLIER < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Successive-halving promotion math (feature C)
# ─────────────────────────────────────────────────────────────────────────────


class TestPromoteCount:
    @pytest.mark.parametrize(
        "n,expected",
        [(40, 20), (20, 10), (17, 9), (16, 8), (10, 8), (8, 8), (5, 5), (1, 1), (0, 0)],
    )
    def test_top_frac_with_min_floor(self, n, expected):
        assert ef.promote_count(n) == expected

    def test_never_exceeds_candidate_count(self):
        for n in range(0, 50):
            assert 0 <= ef.promote_count(n) <= n


class TestSelectPromoted:
    def test_promotes_top_half_by_score(self):
        scores = [float(i) for i in range(20)]  # 0..19, best are highest
        promoted = ef.select_promoted(scores)
        assert promoted == set(range(10, 20))

    def test_min_floor_applies(self):
        scores = [float(i) for i in range(10)]
        promoted = ef.select_promoted(scores)
        assert len(promoted) == 8  # 0.5 * 10 = 5 < floor 8

    def test_ties_break_by_index_for_determinism(self):
        scores = [1.0] * 20
        promoted = ef.select_promoted(scores)
        assert promoted == set(range(10))

    def test_deterministic_given_same_input(self):
        scores = [
            3.0,
            1.0,
            4.0,
            1.0,
            5.0,
            9.0,
            2.0,
            6.0,
            5.0,
            3.0,
            5.0,
            8.0,
            9.0,
            7.0,
            9.0,
            3.0,
            2.0,
            3.0,
            8.0,
            4.0,
        ]
        assert ef.select_promoted(scores) == ef.select_promoted(list(scores))


class TestHalvingActive:
    def test_off_below_min_pop(self):
        assert ef.halving_active(True, ef.HALVING_MIN_POP - 1) is False

    def test_on_at_min_pop(self):
        assert ef.halving_active(True, ef.HALVING_MIN_POP) is True
        assert ef.halving_active(True, 40) is True

    def test_flag_off_wins(self):
        assert ef.halving_active(False, 100) is False


class TestBuildScreenFrame:
    def _frame(self, start: str, end: str) -> pd.DataFrame:
        dates = pd.bdate_range(start, end)
        return pd.DataFrame({"date": dates, "close": [1.0] * len(dates)})

    def test_warmup_prefix_plus_modern_slice(self):
        from engine.strategy_engine import MODERN_ERA_START

        df = self._frame("2005-01-03", "2020-12-31")
        screen_df, eval_from = _build_screen_frame(df)
        assert eval_from == MODERN_ERA_START
        first_modern = int((df["date"] >= MODERN_ERA_START).values.argmax())
        expected_start = first_modern - ef.SCREEN_WARMUP_BARS
        assert screen_df["date"].iloc[0] == df["date"].iloc[expected_start]
        assert len(screen_df) == len(df) - expected_start
        # Index must be reset so position-based engine math works.
        assert screen_df.index[0] == 0

    def test_modern_only_frame_disables_screen(self):
        # Screen ≈ full frame → no savings → halving must opt out.
        screen_df, eval_from = _build_screen_frame(
            self._frame("2016-01-04", "2020-12-31")
        )
        assert screen_df is None and eval_from is None

    def test_pre_modern_frame_disables_screen(self):
        screen_df, eval_from = _build_screen_frame(
            self._frame("2000-01-03", "2010-12-31")
        )
        assert screen_df is None and eval_from is None


# ─────────────────────────────────────────────────────────────────────────────
# Pruned cache-entry shape (feature C ↔ hash-index contract)
# ─────────────────────────────────────────────────────────────────────────────


def _good_v4_entry() -> dict:
    """A healthy fully-evaluated v4 cache entry (fake metrics)."""
    return {
        "bah": 2.0,
        "real_bah": 1.5,
        "modern_bah": 1.2,
        "rs": 0.7,
        "dd": 30.0,
        "nt": 20,
        "np": 4,
        "hhi": 0.10,
        "ma": 0.6,
    }


class TestPrunedCacheEntry:
    def test_schema_matches_v4_plus_marker(self):
        # Same keys as _cache_entry_from_result plus the provenance marker —
        # existing readers (fitness_from_cache, _objectives_from_cache,
        # confidence_v2.hash_index_summary) must keep working untouched.
        v4_keys = set(_cache_entry_from_result({}, None))
        pruned = ef.pruned_cache_entry(1.23, n_params=4)
        assert set(pruned) == v4_keys | {"pruned"}
        assert pruned["pruned"] == ef.PRUNED_MARKER
        assert pruned["np"] == 4

    def test_dedup_treats_pruned_as_ready(self):
        # "Never retried": _cache_entry_ready must be True so the GA skips
        # re-evaluating a pruned config on every future encounter.
        assert _cache_entry_ready(ef.pruned_cache_entry(1.23, 4)) is True

    def test_pruned_entry_never_ranks_or_seeds(self):
        # fitness 0.0 means a pruned entry can never become a strategy best,
        # a run winner, or a history-seeded leaderboard candidate.
        entry = ef.pruned_cache_entry(99.0, 4)  # even a huge screen metric
        assert fitness_from_cache(entry) == 0.0
        assert discovery_score_from_cache(entry) == 0.0

    def test_bayesian_objectives_prune_the_trial(self):
        assert _objectives_from_cache(ef.pruned_cache_entry(1.5, 4), 30.0) is None

    def test_screen_metric_recorded_and_floored_for_persistence(self):
        entry = ef.pruned_cache_entry(1.234567, 2)
        assert entry["modern_bah"] == pytest.approx(1.2346)
        # screen share of 0.0 still persists (save_hash_index drops falsy bah)
        zero = ef.pruned_cache_entry(0.0, 2)
        assert zero["bah"] > 0

    def test_save_hash_index_persists_pruned_entries(self, tmp_path, monkeypatch):
        import search.evolve as ev

        path = tmp_path / "hash-index.json"
        monkeypatch.setattr(ev, "HASH_INDEX_FILE", str(path))
        monkeypatch.setattr(ev, "HISTORY_DIR", str(tmp_path))
        index = {
            "aaaa": ef.pruned_cache_entry(0.8, 3),
            "bbbb": _good_v4_entry(),
            "cccc": _cache_entry_from_result({}, None),  # stale → dropped
        }
        save_hash_index(index)
        on_disk = json.loads(path.read_text())
        assert set(on_disk) == {"aaaa", "bbbb"}
        assert on_disk["aaaa"]["pruned"] == ef.PRUNED_MARKER


# ─────────────────────────────────────────────────────────────────────────────
# Hard-breach cache penalty (feature A ↔ hash-index contract)
# ─────────────────────────────────────────────────────────────────────────────


class TestCachePenalty:
    def test_pen_multiplies_cached_fitness(self):
        entry = _good_v4_entry()
        base = fitness_from_cache(entry)
        assert base > 0
        penalized = {**entry, "pen": ef.HARD_CACHE_FITNESS_PENALTY}
        assert fitness_from_cache(penalized) == pytest.approx(
            base * ef.HARD_CACHE_FITNESS_PENALTY
        )

    def test_missing_pen_means_no_penalty(self):
        entry = _good_v4_entry()
        assert fitness_from_cache({**entry, "pen": None}) == pytest.approx(
            fitness_from_cache(entry)
        )

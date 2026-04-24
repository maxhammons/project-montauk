"""Phase 1b — golden-trade regression (LOAD-BEARING regression net).

Re-runs `strategy_engine.run_montauk_821()` with default 8.2.1
`StrategyParams` on the current `data/TECL.csv` and asserts every trade
matches the ledger stored in `tests/golden_trades_821.json` within
±0.001% PnL tolerance.

This is the regression anchor that lets us delete the legacy Pine bridge with
confidence: if the Python engine silently changes behavior (slippage, EMA
seeding, exit priority, etc.), this test fails loudly.

Refreshing the golden:
    python tests/generate_golden_trades.py
Only do this when the change is intentional — document the reason in the
commit message, and treat it as a breaking change.
"""

from __future__ import annotations

import builtins
import io
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from certify.contract import is_leaderboard_eligible, sync_validation_contract
from certify.backfill_multi_era_metrics import summarize_regime_performance
from engine.regime_helpers import run_backtest
from engine.strategy_engine import StrategyParams, run_montauk_821
from data.loader import get_tecl_data
from search.evolve import (
    _compute_engine_hash,
    _objectives_from_cache,
    _objectives_from_result,
    update_leaderboard,
)
from search.fitness import (
    all_era_score_from_metrics,
    canonicalize_metrics_with_multi_era,
    fitness_from_result,
    weighted_era_fitness,
)
from search.share_metric import LEGACY_SHARE_MULTIPLE_KEY
from search.spike_runner import _finalize_champion_certification

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_trades_821.json"
PNL_TOLERANCE_PCT = 0.001  # ±0.001 percentage points on pnl_pct per trade
PRICE_TOLERANCE = 1e-4  # fill prices compared in dollars


@pytest.fixture(scope="module")
def golden() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.skip(f"missing {GOLDEN_PATH.name}; run tests/generate_golden_trades.py")
    with open(GOLDEN_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fresh_result():
    df = get_tecl_data(use_yfinance=False)
    return run_montauk_821(df, StrategyParams(), score_regimes=False)


def test_trade_count_matches_golden(golden, fresh_result):
    expected = len(golden["trades"])
    actual = len(fresh_result.trades)
    assert actual == expected, (
        f"trade count drifted: golden={expected} actual={actual}. "
        "If intentional, re-run tests/generate_golden_trades.py."
    )


def test_every_trade_matches_golden_within_tolerance(golden, fresh_result):
    """Each trade must agree on entry/exit date, exit reason, and pnl_pct."""
    golden_trades = golden["trades"]
    fresh_trades = fresh_result.trades

    assert len(fresh_trades) == len(golden_trades)

    mismatches: list[str] = []
    for i, (g, t) in enumerate(zip(golden_trades, fresh_trades)):
        if t.entry_date != g["entry_date"]:
            mismatches.append(
                f"trade {i}: entry_date {t.entry_date} != golden {g['entry_date']}"
            )
            continue
        if t.exit_date != g["exit_date"]:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_date {t.exit_date} != golden {g['exit_date']}"
            )
            continue
        if t.exit_reason != g["exit_reason"]:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_reason {t.exit_reason!r} != golden {g['exit_reason']!r}"
            )
            continue
        if abs(float(t.pnl_pct) - g["pnl_pct"]) > PNL_TOLERANCE_PCT:
            mismatches.append(
                f"trade {i} ({t.entry_date}): pnl_pct {t.pnl_pct:.6f} vs golden {g['pnl_pct']:.6f} "
                f"(Δ={t.pnl_pct - g['pnl_pct']:+.6f} > ±{PNL_TOLERANCE_PCT})"
            )
            continue
        if abs(float(t.entry_price) - g["entry_price"]) > PRICE_TOLERANCE:
            mismatches.append(
                f"trade {i} ({t.entry_date}): entry_price {t.entry_price:.6f} != golden {g['entry_price']:.6f}"
            )
        if abs(float(t.exit_price) - g["exit_price"]) > PRICE_TOLERANCE:
            mismatches.append(
                f"trade {i} ({t.entry_date}): exit_price {t.exit_price:.6f} != golden {g['exit_price']:.6f}"
            )

    if mismatches:
        header = (
            f"{len(mismatches)} trade(s) diverged from golden_trades_821.json — "
            "engine behavior changed. If intentional, re-run generate_golden_trades.py."
        )
        pytest.fail(header + "\n  " + "\n  ".join(mismatches[:10]))


def test_summary_metrics_match_golden(golden, fresh_result):
    """Terminal metrics (share_multiple, CAGR, max_dd) must match."""
    meta = golden["metadata"]
    assert abs(float(fresh_result.share_multiple) - meta["share_multiple"]) < 1e-3, (
        f"share_multiple drift: {fresh_result.share_multiple} vs golden {meta['share_multiple']}"
    )
    assert abs(float(fresh_result.cagr_pct) - meta["cagr_pct"]) < 1e-2, (
        f"CAGR drift: {fresh_result.cagr_pct} vs golden {meta['cagr_pct']}"
    )
    assert (
        abs(float(fresh_result.max_drawdown_pct) - meta["max_drawdown_pct"]) < 1e-1
    ), (
        f"max_drawdown_pct drift: {fresh_result.max_drawdown_pct} vs golden {meta['max_drawdown_pct']}"
    )


def test_slippage_is_unified_per_phase1c(golden):
    """Sanity: golden was generated with slippage_pct=0.05 (Phase 1c unification)."""
    assert golden["metadata"]["slippage_pct"] == 0.05, (
        "golden_trades_821.json was generated with a non-unified slippage value — "
        "regenerate after Phase 1c."
    )


def test_compat_run_backtest_matches_strategy_engine(fresh_result):
    """The backtest_engine compatibility façade must mirror the canonical run."""
    df = get_tecl_data(use_yfinance=False)
    compat_result = run_backtest(df, StrategyParams(), score_regimes=False)

    assert compat_result.share_multiple == fresh_result.share_multiple
    assert compat_result.num_trades == fresh_result.num_trades
    assert [
        (t.entry_date, t.exit_date, t.exit_reason, round(float(t.pnl_pct), 6))
        for t in compat_result.trades
    ] == [
        (t.entry_date, t.exit_date, t.exit_reason, round(float(t.pnl_pct), 6))
        for t in fresh_result.trades
    ]


def test_legacy_leaderboard_entries_still_readable():
    """Phase 1d / Phase 7: report.py must still read old leaderboard entries.

    The old Python alias was retired in Phase 7, but older
    `spike/leaderboard.json` entries still need to load. This test pins the
    JSON-side back-compat shim in `report.py::_share_mult`.
    """
    from diagnostics.report import _share_mult  # noqa: WPS433 — test-local import is intentional

    # New format (Phase 1d onward)
    assert _share_mult({"share_multiple": 2.5}) == 2.5
    # Legacy format (pre-Phase 1d entries)
    assert _share_mult({LEGACY_SHARE_MULTIPLE_KEY: 3.14}) == 3.14
    # New format wins when both present
    assert _share_mult({"share_multiple": 2.5, LEGACY_SHARE_MULTIPLE_KEY: 9.0}) == 2.5
    # Missing both → zero fallback
    assert _share_mult({}) == 0.0


def test_engine_hash_changes_when_fitness_module_changes(monkeypatch):
    real_open = builtins.open
    fitness_bytes = {"value": b"fitness-v1"}

    def fake_open(path, mode="r", *args, **kwargs):
        path_str = os.fspath(path)
        if path_str.endswith(os.path.join("search", "fitness.py")) and "b" in mode:
            return io.BytesIO(fitness_bytes["value"])
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    hash_before = _compute_engine_hash()
    fitness_bytes["value"] = b"fitness-v2"
    hash_after = _compute_engine_hash()
    assert hash_before != hash_after


def test_optuna_objective_uses_weighted_era_fitness():
    result = SimpleNamespace(
        share_multiple=8.0,
        real_share_multiple=0.4,
        modern_share_multiple=0.5,
        max_drawdown_pct=18.0,
        num_trades=12,
        trades_per_year=1.2,
        params={"fast_ema": 120, "slow_ema": 180},
        regime_score=SimpleNamespace(hhi=0.2),
    )

    objectives = _objectives_from_result(result)
    assert objectives is not None
    assert objectives[0] == pytest.approx(fitness_from_result(result))
    assert objectives[0] != pytest.approx(result.share_multiple)


def test_cached_optuna_objective_uses_weighted_era_fitness():
    entry = {
        "bah": 9.0,
        "real_bah": 0.3,
        "modern_bah": 0.45,
        "dd": 12.0,
        "nt": 14,
        "np": 2,
        "hhi": 0.2,
    }

    objectives = _objectives_from_cache(entry, dataset_years=10.0)
    assert objectives is not None
    assert objectives[0] == pytest.approx(weighted_era_fitness(9.0, 0.3, 0.45))
    assert objectives[0] != pytest.approx(entry["bah"])


def test_warn_row_is_not_leaderboard_eligible():
    entry = {
        "strategy": "gc_precross",
        "fitness": 1.2,
        "params": {"cooldown": 2},
        "metrics": {"share_multiple": 1.1},
        "validation": {
            "verdict": "WARN",
            "promotion_ready": False,
            "backtest_certified": False,
            "certification_checks": {
                "engine_integrity": {"passed": True},
                "golden_regression": {"passed": True},
                "shadow_comparator": {"passed": True},
                "data_quality_precheck": {"passed": True},
                "artifact_completeness": {"passed": False, "status": "pending"},
            },
        },
    }

    eligible, reason = is_leaderboard_eligible(entry)
    assert eligible is False
    assert "promotion_ready=False" in reason
    assert sync_validation_contract(entry["validation"])["certified_not_overfit"] is False

    with tempfile.TemporaryDirectory() as td:
        leaderboard = update_leaderboard(
            {"rankings": [entry], "date": "2026-04-23"},
            os.path.join(td, "leaderboard.json"),
        )
    assert leaderboard == []


def test_promotion_ready_row_can_be_admitted_before_artifact_completion():
    entry = {
        "strategy": "gc_precross",
        "fitness": 1.2,
        "params": {"cooldown": 2},
        "metrics": {"share_multiple": 1.1},
        "validation": {
            "verdict": "PASS",
            "promotion_ready": True,
            "backtest_certified": False,
            "certification_checks": {
                "engine_integrity": {"passed": True},
                "golden_regression": {"passed": True},
                "shadow_comparator": {"passed": True},
                "data_quality_precheck": {"passed": True},
                "artifact_completeness": {"passed": False, "status": "pending"},
            },
        },
    }

    eligible, reason = is_leaderboard_eligible(entry)
    assert eligible is True
    assert reason == "ok"
    normalized = sync_validation_contract(entry["validation"])
    assert normalized["certified_not_overfit"] is True
    assert normalized["backtest_certified"] is False


def test_leaderboard_ranks_by_all_era_score_after_certification():
    def make_entry(
        strategy: str,
        fitness: float,
        confidence: float,
        *,
        full: float,
        real: float,
        modern: float,
    ) -> dict:
        return {
            "strategy": strategy,
            "fitness": fitness,
            "params": {"cooldown": 2},
            "metrics": {
                "share_multiple": full,
                "real_share_multiple": real,
                "modern_share_multiple": modern,
            },
            "validation": {
                "verdict": "PASS",
                "promotion_ready": True,
                "backtest_certified": False,
                "composite_confidence": confidence,
                "certification_checks": {
                    "engine_integrity": {"passed": True},
                    "golden_regression": {"passed": True},
                    "shadow_comparator": {"passed": True},
                    "data_quality_precheck": {"passed": True},
                    "artifact_completeness": {"passed": False, "status": "pending"},
                },
            },
        }

    modern_skewed = make_entry(
        "gc_a",
        2.7744,
        0.7293,
        full=11.9639,
        real=1.0430,
        modern=2.8942,
    )
    stronger_all_era = make_entry(
        "gc_b",
        2.6511,
        0.7345,
        full=13.1308,
        real=1.7353,
        modern=2.1203,
    )

    with tempfile.TemporaryDirectory() as td:
        leaderboard = update_leaderboard(
            {"rankings": [modern_skewed, stronger_all_era], "date": "2026-04-23"},
            os.path.join(td, "leaderboard.json"),
        )

    assert all_era_score_from_metrics(stronger_all_era["metrics"]) > all_era_score_from_metrics(modern_skewed["metrics"])
    assert [row["strategy"] for row in leaderboard[:2]] == ["gc_b", "gc_a"]


def test_multi_era_reruns_override_legacy_sliced_era_metrics_for_leaderboard():
    metrics = {
        "share_multiple": 17.4652,
        "real_share_multiple": 1.4741,
        "modern_share_multiple": 2.0084,
    }
    multi_era = {
        "eras": {
            "full": {"share_multiple": 17.4652},
            "real": {"share_multiple": 0.9609},
            "modern": {"share_multiple": 2.5711},
        }
    }

    normalized = canonicalize_metrics_with_multi_era(metrics, multi_era)

    assert normalized["share_multiple"] == pytest.approx(17.4652)
    assert normalized["real_share_multiple"] == pytest.approx(0.9609)
    assert normalized["modern_share_multiple"] == pytest.approx(2.5711)
    assert all_era_score_from_metrics(normalized) == pytest.approx(
        all_era_score_from_metrics(metrics, multi_era=multi_era)
    )


def test_regime_summary_aggregates_components_and_flags_critical_breaches():
    summary = summarize_regime_performance(
        [
            {"key": "dotcom_bust", "label": "Dot-com bust / Y2K fallout", "kind": "bear", "share_multiple": 0.72},
            {"key": "gfc_crash", "label": "GFC crash", "kind": "crash", "share_multiple": 1.41},
            {"key": "covid_crash", "label": "COVID crash", "kind": "crash", "share_multiple": 1.18},
            {"key": "stimulus_bull", "label": "Stimulus / reopening bull", "kind": "bull", "share_multiple": 1.09},
            {"key": "qe_recovery", "label": "QE recovery", "kind": "recovery", "share_multiple": 1.04},
            {"key": "policy_volatility", "label": "Late-cycle policy volatility", "kind": "policy", "share_multiple": 0.97},
        ]
    )

    assert summary["overall_score"] > 0
    assert summary["components"]["crash_defense"]["score"] > summary["components"]["bear_survival"]["score"]
    assert summary["critical_guardrail_passed"] is False
    assert [item["key"] for item in summary["critical_failures"]] == ["dotcom_bust"]


def test_finalization_cannot_certify_warn_row():
    with tempfile.TemporaryDirectory() as td:
        artifacts = {}
        for name in (
            "trade_ledger",
            "signal_series",
            "equity_curve",
            "validation_summary",
            "dashboard_data",
        ):
            path = os.path.join(td, f"{name}.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
            artifacts[name] = path

        results = {
            "champion": {
                "strategy": "gc_precross",
                "validation": {
                    "verdict": "WARN",
                    "promotion_ready": False,
                    "backtest_certified": False,
                    "clean_pass": False,
                    "certification_checks": {
                        "engine_integrity": {"passed": True},
                        "golden_regression": {"passed": True},
                        "shadow_comparator": {"passed": True},
                        "data_quality_precheck": {"passed": True},
                        "artifact_completeness": {"passed": False, "status": "pending"},
                    },
                    "gates": {
                        "gate7": {
                            "promotion_ready": False,
                            "backtest_certified": False,
                            "clean_pass": False,
                            "advisories": ["artifact completeness pending"],
                        }
                    },
                },
            },
            "validation_summary": {"champion": {}},
        }

        _finalize_champion_certification(results, artifacts)
        validation = results["champion"]["validation"]

    assert validation["promotion_ready"] is False
    assert validation["certified_not_overfit"] is False
    assert validation["backtest_certified"] is False
    assert validation["gates"]["gate7"]["backtest_certified"] is False

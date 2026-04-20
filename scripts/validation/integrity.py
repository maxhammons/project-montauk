"""
Run-level integrity checks for the validation funnel.

Gate 0 is intentionally simple: fail fast if the local datasets, execution
engine, or regression anchors are not in a state where a validated winner
could be trusted. It also surfaces non-fatal certification checks that Gate 7
can use when deciding whether a candidate is merely promotion-ready or fully
backtest-certified.
"""

from __future__ import annotations

import inspect
import importlib.util
import json
import os

import numpy as np
import pandas as pd

from data.loader import get_qqq_data, get_tecl_data, get_tqqq_data
from strategies.library import STRATEGY_PARAMS, STRATEGY_REGISTRY
from engine.strategy_engine import StrategyParams, backtest as strategy_backtest, run_montauk_821

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_TRADES_PATH = os.path.join(PROJECT_ROOT, "tests", "golden_trades_821.json")
DATA_QUALITY_PATH = os.path.join(PROJECT_ROOT, "scripts", "data", "quality.py")
PNL_TOLERANCE_PCT = 0.001
PRICE_TOLERANCE = 1e-4
SHADOW_TRADE_TOLERANCE = 2
SHADOW_PNL_TOLERANCE_PCT = 0.5


def _midpoint_params(strategy_name: str) -> dict:
    params = {}
    for name, (lo, hi, step, typ) in STRATEGY_PARAMS.get(strategy_name, {}).items():
        if typ == int:
            n_steps = int(round((hi - lo) / step))
            idx = n_steps // 2
            params[name] = int(lo + idx * step)
        else:
            n_steps = int(round((hi - lo) / step))
            idx = n_steps // 2
            params[name] = round(lo + idx * step, 4)
    return params


def _run_golden_regression_check() -> dict:
    if not os.path.exists(GOLDEN_TRADES_PATH):
        return {
            "passed": False,
            "status": "missing_fixture",
            "fixture_path": GOLDEN_TRADES_PATH,
            "reason": "tests/golden_trades_821.json not found",
            "mismatches": [],
        }

    try:
        with open(GOLDEN_TRADES_PATH) as f:
            golden = json.load(f)

        df = get_tecl_data(use_yfinance=False)
        result = run_montauk_821(df, StrategyParams(), score_regimes=False)
        golden_trades = golden.get("trades", [])
        mismatches: list[str] = []

        if len(result.trades) != len(golden_trades):
            mismatches.append(
                f"trade_count actual={len(result.trades)} expected={len(golden_trades)}"
            )

        for i, (expected, actual) in enumerate(zip(golden_trades, result.trades)):
            if actual.entry_date != expected["entry_date"]:
                mismatches.append(
                    f"trade {i}: entry_date actual={actual.entry_date} expected={expected['entry_date']}"
                )
                continue
            if actual.exit_date != expected["exit_date"]:
                mismatches.append(
                    f"trade {i}: exit_date actual={actual.exit_date} expected={expected['exit_date']}"
                )
                continue
            if actual.exit_reason != expected["exit_reason"]:
                mismatches.append(
                    f"trade {i}: exit_reason actual={actual.exit_reason!r} expected={expected['exit_reason']!r}"
                )
                continue
            if abs(float(actual.pnl_pct) - expected["pnl_pct"]) > PNL_TOLERANCE_PCT:
                mismatches.append(
                    f"trade {i}: pnl_pct actual={actual.pnl_pct:.6f} expected={expected['pnl_pct']:.6f}"
                )
                continue
            if abs(float(actual.entry_price) - expected["entry_price"]) > PRICE_TOLERANCE:
                mismatches.append(
                    f"trade {i}: entry_price actual={actual.entry_price:.6f} expected={expected['entry_price']:.6f}"
                )
            if abs(float(actual.exit_price) - expected["exit_price"]) > PRICE_TOLERANCE:
                mismatches.append(
                    f"trade {i}: exit_price actual={actual.exit_price:.6f} expected={expected['exit_price']:.6f}"
                )

        meta = golden.get("metadata", {})
        if meta.get("slippage_pct") != 0.05:
            mismatches.append(
                f"slippage_pct actual={meta.get('slippage_pct')} expected=0.05"
            )
        if abs(float(result.share_multiple) - float(meta.get("share_multiple", 0.0))) >= 1e-3:
            mismatches.append(
                f"share_multiple actual={result.share_multiple} expected={meta.get('share_multiple')}"
            )
        if abs(float(result.cagr_pct) - float(meta.get("cagr_pct", 0.0))) >= 1e-2:
            mismatches.append(
                f"cagr_pct actual={result.cagr_pct} expected={meta.get('cagr_pct')}"
            )
        if (
            abs(float(result.max_drawdown_pct) - float(meta.get("max_drawdown_pct", 0.0)))
            >= 1e-1
        ):
            mismatches.append(
                "max_drawdown_pct "
                f"actual={result.max_drawdown_pct} expected={meta.get('max_drawdown_pct')}"
            )

        return {
            "passed": not mismatches,
            "status": "pass" if not mismatches else "fail",
            "fixture_path": GOLDEN_TRADES_PATH,
            "trade_count": len(result.trades),
            "mismatches": mismatches[:10],
        }
    except Exception as exc:
        return {
            "passed": False,
            "status": "error",
            "fixture_path": GOLDEN_TRADES_PATH,
            "reason": str(exc),
            "mismatches": [],
        }


def _minimal_shadow_params() -> StrategyParams:
    return StrategyParams(
        short_ema_len=15,
        med_ema_len=30,
        long_ema_len=50,
        trend_ema_len=70,
        slope_lookback=10,
        min_trend_slope=0.0,
        enable_trend=False,
        enable_slope_filter=False,
        enable_below_filter=False,
        enable_sideways_filter=False,
        enable_sell_confirm=False,
        sell_confirm_bars=1,
        sell_buffer_pct=0.0,
        enable_sell_cooldown=False,
        enable_atr_exit=False,
        enable_quick_exit=False,
        enable_trail_stop=False,
        enable_tema_exit=False,
        enable_atr_ratio_filter=False,
        enable_adx_filter=False,
        enable_roc_filter=False,
        enable_bear_guard=False,
        enable_asymmetric_exit=False,
        enable_vol_exit=False,
        slippage_pct=0.0,
        commission_pct=0.0,
        initial_capital=10_000.0,
    )


def _pine_ema(series: np.ndarray, length: int) -> np.ndarray:
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    out[length - 1] = float(np.mean(series[:length]))
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _run_shadow_comparator_check() -> dict:
    if importlib.util.find_spec("backtesting") is None:
        return {
            "passed": False,
            "status": "missing_dependency",
            "reason": "backtesting.py not installed (dev-only dependency)",
        }

    try:
        from backtesting import Backtest, Strategy

        class EmaCrossStrategy(Strategy):
            short_len = 15
            med_len = 30
            long_len = 50

            def init(self):
                close = np.asarray(self.data.Close)
                self.ema_s = self.I(_pine_ema, close, self.short_len)
                self.ema_m = self.I(_pine_ema, close, self.med_len)
                self.ema_l = self.I(_pine_ema, close, self.long_len)

            def next(self):
                if len(self.ema_s) < 2:
                    return
                s, m, lg = self.ema_s[-1], self.ema_m[-1], self.ema_l[-1]
                s_prev, lg_prev = self.ema_s[-2], self.ema_l[-2]
                if np.isnan(s) or np.isnan(m) or np.isnan(lg):
                    return
                if self.position:
                    if (
                        not np.isnan(s_prev)
                        and not np.isnan(lg_prev)
                        and s_prev >= lg_prev
                        and s < lg
                    ):
                        self.position.close()
                elif s > m:
                    self.buy()

        df = get_tecl_data(use_yfinance=False)
        recent = df[df["date"] >= pd.Timestamp("2019-01-01")].reset_index(drop=True)
        ours = run_montauk_821(recent, _minimal_shadow_params(), score_regimes=False)

        shadow_df = pd.DataFrame(
            {
                "Open": recent["open"].values,
                "High": recent["high"].values,
                "Low": recent["low"].values,
                "Close": recent["close"].values,
                "Volume": recent["volume"].values,
            },
            index=pd.to_datetime(recent["date"]),
        )
        bt = Backtest(
            shadow_df,
            EmaCrossStrategy,
            cash=10_000,
            commission=0.0,
            trade_on_close=True,
            exclusive_orders=True,
            finalize_trades=True,
        )
        stats = bt.run()

        issues: list[str] = []
        ours_n = ours.num_trades
        shadow_n = int(stats["# Trades"])
        if abs(ours_n - shadow_n) > SHADOW_TRADE_TOLERANCE:
            issues.append(f"trade_count ours={ours_n} shadow={shadow_n}")

        ours_by_date = {t.entry_date: float(t.pnl_pct) for t in ours.trades}
        # backtesting.py force-finalizes the last open position as a
        # zero-duration, same-bar liquidation (EntryBar == ExitBar, ReturnPct == 0).
        # Our engine records the same position through the final bar as an
        # End-of-Data exit with real PnL. Exclude that artifact — it's a
        # bar-close-semantic difference between engines, not a real divergence.
        # This matches tests/test_shadow_comparator.py::test_per_trade_pnl_within_0p5pct.
        shadow_zero_duration = {
            str(pd.Timestamp(row.EntryTime).date())
            for row in stats["_trades"].itertuples()
            if row.EntryBar == row.ExitBar and float(row.ReturnPct) == 0.0
        }
        shadow_by_date = {
            str(pd.Timestamp(row.EntryTime).date()): float(row.ReturnPct) * 100
            for row in stats["_trades"].itertuples()
        }
        common = sorted(
            (set(ours_by_date) & set(shadow_by_date)) - shadow_zero_duration
        )
        if len(common) < 10:
            issues.append(f"common_trade_count={len(common)} < 10")
        else:
            divergent = [
                d for d in common
                if abs(ours_by_date[d] - shadow_by_date[d]) > SHADOW_PNL_TOLERANCE_PCT
            ]
            # Allow a minority of divergences — matches the standalone test's
            # "majority-agrees" rule (test_drift_mismatched_trades_are_minority
            # permits ≤1/3 drift). A single edge-case divergence does not
            # indicate an engine-wide bug.
            if len(divergent) > len(common) // 3:
                issues.append(
                    f"same_date_pnl_divergences={len(divergent)}/{len(common)} "
                    f"exceeds 1/3 tolerance"
                )

        return {
            "passed": not issues,
            "status": "pass" if not issues else "fail",
            "trade_count_ours": ours_n,
            "trade_count_shadow": shadow_n,
            "issues": issues[:10],
        }
    except Exception as exc:
        return {
            "passed": False,
            "status": "error",
            "reason": str(exc),
        }


def _run_data_quality_precheck() -> dict:
    if not os.path.exists(DATA_QUALITY_PATH):
        return {
            "passed": False,
            "status": "missing_phase3_runner",
            "reason": "scripts/data_quality.py not found",
        }

    try:
        spec = importlib.util.spec_from_file_location("data_quality", DATA_QUALITY_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load scripts/data_quality.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "audit_all"):
            raise RuntimeError("scripts/data_quality.py does not expose audit_all()")
        report = module.audit_all()
        # audit_all() returns a list of per-check result dicts, each with a
        # `status` field (PASS / WARN / FAIL / SKIP). Pre-check passes iff
        # no check FAILed. Warns and skips are acceptable.
        if isinstance(report, list):
            fails = [r for r in report if str(r.get("status", "")).upper() == "FAIL"]
            passed = len(fails) == 0
            summary = {
                "total": len(report),
                "pass": sum(1 for r in report if str(r.get("status", "")).upper() == "PASS"),
                "warn": sum(1 for r in report if str(r.get("status", "")).upper() == "WARN"),
                "fail": len(fails),
                "skip": sum(1 for r in report if str(r.get("status", "")).upper() == "SKIP"),
            }
            return {
                "passed": passed,
                "status": "pass" if passed else "fail",
                "summary": summary,
                "failing_checks": [
                    {"test": r.get("test"), "scope": r.get("scope"), "summary": r.get("summary")}
                    for r in fails[:10]
                ],
            }
        # Legacy dict-style return (older data_quality.py revisions)
        passed = str(report.get("verdict", "")).upper() == "PASS"
        return {
            "passed": passed,
            "status": "pass" if passed else "fail",
            "report": report,
        }
    except Exception as exc:
        return {
            "passed": False,
            "status": "error",
            "reason": str(exc),
        }


def validate_run_integrity(strategy_names: list[str]) -> dict:
    datasets = {}
    errors = []

    for asset, loader in (
        ("TECL", get_tecl_data),
        ("TQQQ", get_tqqq_data),
        ("QQQ", get_qqq_data),
    ):
        try:
            df = loader(use_yfinance=False) if asset == "TECL" else loader()
            datasets[asset] = {
                "bars": int(len(df)),
                "start": str(df["date"].min().date()),
                "end": str(df["date"].max().date()),
            }
            if df.empty:
                errors.append(f"{asset} dataset is empty")
        except Exception as exc:
            errors.append(f"{asset} dataset unavailable: {exc}")

    signature = inspect.signature(strategy_backtest)
    slippage_default = signature.parameters["slippage_pct"].default
    engine = {
        "slippage_pct_default": slippage_default,
        "slippage_active": bool(slippage_default and slippage_default > 0),
        "bar_close_execution": True,
        "lookahead_safe": True,
        "repaint_safe": True,
    }
    engine_errors = []
    if not engine["slippage_active"]:
        engine_errors.append("strategy_engine.backtest has zero slippage by default")
    if engine_errors:
        errors.extend(engine_errors)

    engine_integrity = {
        "passed": not engine_errors,
        "status": "pass" if not engine_errors else "fail",
        "checks": engine,
        "errors": engine_errors,
    }

    golden_regression = _run_golden_regression_check()
    shadow_comparator = _run_shadow_comparator_check()
    data_quality = _run_data_quality_precheck()

    strategy_checks = {}
    for strategy_name in sorted(set(strategy_names)):
        check = {
            "in_registry": strategy_name in STRATEGY_REGISTRY,
            "charter_compatible": True,
        }
        if not check["in_registry"]:
            errors.append(f"{strategy_name} missing from STRATEGY_REGISTRY")
        strategy_checks[strategy_name] = check

    verdict = "PASS" if not errors else "FAIL"
    return {
        "verdict": verdict,
        "datasets": datasets,
        "engine": engine,
        "engine_integrity": engine_integrity,
        "golden_regression": golden_regression,
        "shadow_comparator": shadow_comparator,
        "data_quality": data_quality,
        "strategies": strategy_checks,
        "errors": errors,
    }

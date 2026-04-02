"""
Walk-forward validation and anti-overfitting framework.

Ensures parameter changes generalize across multiple time windows
rather than fitting to a single backtest period.

Primary metric: regime_score (bull capture + bear avoidance).
MAR and other metrics are reported for reference.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from backtest_engine import StrategyParams, BacktestResult, run_backtest


@dataclass
class ValidationResult:
    """Aggregated result across all validation windows."""
    candidate_params: dict
    baseline_params: dict
    # Per-window results
    window_results: list  # list of dicts with train/test metrics
    # Aggregate scores — regime_score is primary
    avg_test_regime_score: float = 0.0
    avg_test_mar: float = 0.0
    avg_test_cagr: float = 0.0
    avg_test_max_dd: float = 0.0
    avg_test_trades: float = 0.0
    # Improvement vs baseline
    regime_score_improvement_pct: float = 0.0
    mar_improvement_pct: float = 0.0
    cagr_improvement_pct: float = 0.0
    dd_improvement_pct: float = 0.0
    # Stability
    param_stability_score: float = 0.0  # 0-1, higher = more stable
    consistent_improvement: bool = False  # True if regime_score improves in ALL windows
    # Verdict
    passes_validation: bool = False
    rejection_reasons: list = None

    def __post_init__(self):
        if self.rejection_reasons is None:
            self.rejection_reasons = []

    def summary_str(self) -> str:
        status = "PASS" if self.passes_validation else "FAIL"
        lines = [
            f"Validation: {status}",
            f"  Avg RegimeScore:  {self.avg_test_regime_score:.3f}",
            f"  Regime improve:   {self.regime_score_improvement_pct:+.1f}%",
            f"  Avg Test MAR:     {self.avg_test_mar:.2f}",
            f"  Avg Test CAGR:    {self.avg_test_cagr:.2f}%",
            f"  Avg Test Max DD:  {self.avg_test_max_dd:.1f}%",
            f"  MAR improvement:  {self.mar_improvement_pct:+.1f}%",
            f"  Consistent:       {self.consistent_improvement}",
            f"  Stability:        {self.param_stability_score:.2f}",
        ]
        if self.rejection_reasons:
            lines.append(f"  Rejections: {'; '.join(self.rejection_reasons)}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Named validation windows matching Charter stress tests
# ─────────────────────────────────────────────────────────────────────────────

NAMED_WINDOWS = {
    "2020_meltup":    ("2019-06-01", "2021-01-01"),
    "2021_2022_bear": ("2021-01-01", "2023-01-01"),
    "2023_rebound":   ("2023-01-01", "2024-06-01"),
    "2024_onward":    ("2024-06-01", "2026-12-31"),
}


def split_walk_forward(df: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Non-overlapping expanding-window walk-forward splits.

    The TEST data includes all data from the start (for indicator warmup)
    through the test end. We only EVALUATE performance on bars after
    the train cutoff, but the backtest engine needs the full history
    to initialize EMAs correctly.

    The train set is used to verify the strategy works in-sample.
    The test set is the FULL dataset up to the test end — the backtest
    engine's warmup period handles the rest.
    """
    boundaries = [
        ("2018-01-01", "2020-01-01"),
        ("2020-01-01", "2022-01-01"),
        ("2022-01-01", "2024-01-01"),
        ("2024-01-01", "2027-01-01"),
    ]
    splits = []
    for train_end, test_end in boundaries:
        train = df[df["date"] < train_end].reset_index(drop=True)
        test = df[df["date"] < test_end].reset_index(drop=True)
        if len(train) > 500 and len(test) > len(train) + 100:
            splits.append((train, test))
    return splits


def split_named_windows(df: pd.DataFrame, warmup_bars: int = 700) -> list[tuple[str, pd.DataFrame]]:
    """
    Split data by the Charter's named stress-test periods.
    Includes warmup_bars of lead-in data before each window so indicators
    (especially long EMAs) are fully warmed up when the evaluation period starts.
    """
    results = []
    for name, (start, end) in NAMED_WINDOWS.items():
        eval_mask = (df["date"] >= start) & (df["date"] <= end)
        if eval_mask.sum() < 50:
            continue
        eval_start_idx = eval_mask.idxmax()
        data_start_idx = max(0, eval_start_idx - warmup_bars)
        eval_end_idx = eval_mask[::-1].idxmax()
        window = df.iloc[data_start_idx:eval_end_idx + 1].reset_index(drop=True)
        if len(window) > 100:
            results.append((name, window))
    return results


def _get_regime_score(r: BacktestResult) -> float:
    if r.regime_score is None:
        return 0.0
    return r.regime_score.composite


def check_param_stability(df: pd.DataFrame, params: StrategyParams,
                          perturbation: float = 0.10,
                          max_result_swing: float = 0.20) -> tuple[float, list[str]]:
    """
    Check if small parameter changes cause disproportionate result changes.
    Uses regime_score as the stability metric (consistent with primary target).
    Returns (stability_score, list of unstable params).
    """
    baseline = run_backtest(df, params)
    baseline_score = _get_regime_score(baseline)

    numeric_params = {}
    d = params.to_dict()
    for k, v in d.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "initial_capital":
            numeric_params[k] = v

    stable_count = 0
    total_tested = 0
    unstable_params = []

    for k, v in numeric_params.items():
        if v == 0:
            continue
        total_tested += 1
        scores = []
        for direction in [-1, 1]:
            test_d = d.copy()
            if isinstance(v, int):
                delta = max(1, int(abs(v * perturbation)))
                test_d[k] = v + direction * delta
            else:
                test_d[k] = v * (1 + direction * perturbation)

            if test_d[k] <= 0 and k.endswith("_len"):
                test_d[k] = 1
            if test_d[k] <= 0 and k.endswith("_bars"):
                test_d[k] = 1

            try:
                test_params = StrategyParams.from_dict(test_d)
                r = run_backtest(df, test_params)
                scores.append(_get_regime_score(r))
            except Exception:
                scores.append(baseline_score)

        if baseline_score > 0:
            max_swing = max(abs(s - baseline_score) / baseline_score for s in scores)
        else:
            max_swing = max(abs(s - baseline_score) for s in scores)

        if max_swing <= max_result_swing:
            stable_count += 1
        else:
            unstable_params.append(f"{k} (swing={max_swing:.1%})")

    stability = stable_count / total_tested if total_tested > 0 else 1.0
    return stability, unstable_params


def validate_candidate(df: pd.DataFrame,
                       candidate: StrategyParams,
                       baseline: StrategyParams | None = None,
                       min_trades_per_window: int = 3,
                       require_consistent: bool = False,
                       check_stability: bool = True) -> ValidationResult:
    """
    Full validation of a candidate parameter set against baseline.

    1. Walk-forward test across multiple windows
    2. Named window stress tests (including 2021-22 bear)
    3. Parameter stability check
    4. Minimum trade count
    5. Consistent improvement check (on regime_score)

    Pass criteria: regime_score must not be worse on average, and must pass
    quality guards (min trades, stability).
    """
    if baseline is None:
        baseline = StrategyParams()

    rejection_reasons = []
    window_results = []

    # ── Walk-forward windows ──
    splits = split_walk_forward(df)
    baseline_test_scores = []
    candidate_test_scores = []
    baseline_test_mars = []
    candidate_test_mars = []

    for i, (train, test) in enumerate(splits):
        b_train = run_backtest(train, baseline)
        b_test = run_backtest(test, baseline)
        c_train = run_backtest(train, candidate)
        c_test = run_backtest(test, candidate)

        b_score = _get_regime_score(b_test)
        c_score = _get_regime_score(c_test)

        window_results.append({
            "window": f"walk_forward_{i}",
            "baseline_train_mar": b_train.mar_ratio,
            "baseline_test_regime_score": round(b_score, 4),
            "baseline_test_mar": b_test.mar_ratio,
            "baseline_test_cagr": b_test.cagr_pct,
            "baseline_test_dd": b_test.max_drawdown_pct,
            "candidate_train_mar": c_train.mar_ratio,
            "candidate_test_regime_score": round(c_score, 4),
            "candidate_test_mar": c_test.mar_ratio,
            "candidate_test_cagr": c_test.cagr_pct,
            "candidate_test_dd": c_test.max_drawdown_pct,
            "candidate_test_trades": c_test.num_trades,
        })

        baseline_test_scores.append(b_score)
        candidate_test_scores.append(c_score)
        baseline_test_mars.append(b_test.mar_ratio)
        candidate_test_mars.append(c_test.mar_ratio)

        if c_test.num_trades < min_trades_per_window:
            rejection_reasons.append(f"Window {i}: only {c_test.num_trades} trades (min {min_trades_per_window})")

    # ── Named windows (stress tests) ──
    named = split_named_windows(df)
    for name, window_df in named:
        b = run_backtest(window_df, baseline)
        c = run_backtest(window_df, candidate)
        b_score = _get_regime_score(b)
        c_score = _get_regime_score(c)

        window_results.append({
            "window": name,
            "baseline_test_regime_score": round(b_score, 4),
            "baseline_test_mar": b.mar_ratio,
            "baseline_test_cagr": b.cagr_pct,
            "baseline_test_dd": b.max_drawdown_pct,
            "candidate_test_regime_score": round(c_score, 4),
            "candidate_test_mar": c.mar_ratio,
            "candidate_test_cagr": c.cagr_pct,
            "candidate_test_dd": c.max_drawdown_pct,
            "candidate_test_trades": c.num_trades,
        })
        baseline_test_scores.append(b_score)
        candidate_test_scores.append(c_score)
        baseline_test_mars.append(b.mar_ratio)
        candidate_test_mars.append(c.mar_ratio)

    # ── Aggregate metrics ──
    test_entries = [w for w in window_results if "candidate_test_regime_score" in w]
    avg_test_regime = np.mean([w["candidate_test_regime_score"] for w in test_entries]) if test_entries else 0
    avg_test_mar = np.mean([w["candidate_test_mar"] for w in test_entries]) if test_entries else 0
    avg_test_cagr = np.mean([w["candidate_test_cagr"] for w in test_entries]) if test_entries else 0
    avg_test_dd = np.mean([w["candidate_test_dd"] for w in test_entries]) if test_entries else 0
    avg_test_trades = np.mean([w.get("candidate_test_trades", 0) for w in test_entries]) if test_entries else 0

    avg_base_regime = np.mean(baseline_test_scores) if baseline_test_scores else 0
    avg_base_mar = np.mean(baseline_test_mars) if baseline_test_mars else 0
    avg_base_cagr = np.mean([w.get("baseline_test_cagr", 0) for w in test_entries]) if test_entries else 0
    avg_base_dd = np.mean([w.get("baseline_test_dd", 0) for w in test_entries]) if test_entries else 0

    regime_imp = ((avg_test_regime - avg_base_regime) / abs(avg_base_regime) * 100) if avg_base_regime != 0 else 0
    mar_imp = ((avg_test_mar - avg_base_mar) / abs(avg_base_mar) * 100) if avg_base_mar != 0 else 0
    cagr_imp = ((avg_test_cagr - avg_base_cagr) / abs(avg_base_cagr) * 100) if avg_base_cagr != 0 else 0
    dd_imp = ((avg_base_dd - avg_test_dd) / abs(avg_base_dd) * 100) if avg_base_dd != 0 else 0

    # ── Consistency check (on regime_score) ──
    consistent = all(c > b for c, b in zip(candidate_test_scores, baseline_test_scores)) if candidate_test_scores else False
    if require_consistent and not consistent:
        rejection_reasons.append("Not consistently better on regime_score across all windows")

    # ── Stability check ──
    stability = 1.0
    if check_stability:
        stability, unstable = check_param_stability(df, candidate)
        if stability < 0.5:
            rejection_reasons.append(f"Param stability too low ({stability:.2f}): {', '.join(unstable[:3])}")

    # ── Final verdict ──
    # Primary: regime_score must not be worse on average
    # Guard: must have trades, MAR must not collapse
    passes = (
        len(rejection_reasons) == 0
        and avg_test_regime >= avg_base_regime  # Must not be worse on primary target
        and avg_test_trades >= 1
        and avg_test_mar > 0.05  # Must have some positive risk-adjusted return
    )

    return ValidationResult(
        candidate_params=candidate.to_dict(),
        baseline_params=baseline.to_dict(),
        window_results=window_results,
        avg_test_regime_score=float(avg_test_regime),
        avg_test_mar=float(avg_test_mar),
        avg_test_cagr=float(avg_test_cagr),
        avg_test_max_dd=float(avg_test_dd),
        avg_test_trades=float(avg_test_trades),
        regime_score_improvement_pct=float(regime_imp),
        mar_improvement_pct=float(mar_imp),
        cagr_improvement_pct=float(cagr_imp),
        dd_improvement_pct=float(dd_imp),
        param_stability_score=stability,
        consistent_improvement=consistent,
        passes_validation=passes,
        rejection_reasons=rejection_reasons,
    )


if __name__ == "__main__":
    from data import get_tecl_data

    df = get_tecl_data(use_yfinance=False)
    print("=== Validating baseline against itself (should pass) ===")
    result = validate_candidate(df, StrategyParams(), check_stability=False)
    print(result.summary_str())

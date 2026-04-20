from __future__ import annotations

"""
Regime detection and capture-quality scoring helpers.

Post-Phase-7 (engine consolidation), this module is a *helpers-only* module:
the canonical Montauk 8.2.1 execution loop, the `StrategyParams` dataclass,
the `Trade` / `BacktestResult` dataclasses, and every indicator implementation
all live in `scripts/strategy_engine.py` — the single source of truth.

What stays here:
  - `Regime` / `RegimeScore` dataclasses
  - `detect_bear_regimes()` / `detect_bull_regimes()` (cycle segmentation)
  - `score_regime_capture()` (bull capture + bear avoidance + HHI per cycle)

These are used by:
  - `strategy_engine.run_montauk_821()` (canonical 8.2.1 path)
  - `scripts/evolve.py` (attaches `regime_score` to evolved BacktestResults)
  - `scripts/grid_search.py` (same)
  - `scripts/validation/{pipeline,sprint1,walk_forward,candidate,deflate}.py`

Compatibility note:
  - this module still re-exports thin wrappers for `run_backtest`,
    `StrategyParams`, `Trade`, `BacktestResult`, and the core indicators so
    older callers and verification harnesses can compare against the canonical
    `strategy_engine` implementation without reviving a second execution loop
"""

from dataclasses import dataclass

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Regime detection and scoring
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Regime:
    """A single bear or bull market period."""
    kind: str           # "bear" or "bull"
    start_idx: int
    end_idx: int
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    move_pct: float     # negative for bear, positive for bull


@dataclass
class RegimeScore:
    """Regime capture quality metrics."""
    bull_capture_ratio: float   # 0.0–1.0: fraction of each bull leg participated in (avg)
    bear_avoidance_ratio: float # 0.0–1.0: fraction of each bear leg avoided (avg)
    composite: float            # 0.5 * bull + 0.5 * bear
    num_bull_periods: int
    num_bear_periods: int
    bull_detail: list           # per-bull: {start, end, move_pct, captured_pct}
    bear_detail: list           # per-bear: {start, end, move_pct, avoided_pct}
    # Per-cycle scores for HHI/jackknife (added Sprint 1)
    bull_capture_scores: list | None = None   # per-bull capture ratios
    bear_avoidance_scores: list | None = None # per-bear avoidance ratios
    hhi: float | None = None                  # Herfindahl-Hirschman Index on cycle contributions

    def summary_str(self) -> str:
        lines = [
            f"Regime Score:    {self.composite:>8.3f}",
            f"  Bull Capture:  {self.bull_capture_ratio:>8.3f}  ({self.num_bull_periods} periods)",
            f"  Bear Avoidance:{self.bear_avoidance_ratio:>8.3f}  ({self.num_bear_periods} periods)",
        ]
        if self.hhi is not None:
            lines.append(f"  Cycle HHI:     {self.hhi:>8.3f}  ({'concentrated' if self.hhi > 0.25 else 'diversified'})")
        return "\n".join(lines)


def detect_bear_regimes(
    close: np.ndarray,
    dates: np.ndarray,
    bear_threshold: float = 0.30,
    min_duration: int = 20,
) -> list[Regime]:
    """
    Algorithmically detect bear market periods from a price series.

    A bear period starts when price drops bear_threshold% from a rolling peak,
    and ends when price recovers above a new local peak (or the series ends).
    Requires min_duration bars to count as a real bear.

    Parameters
    ----------
    close : price series
    dates : date array (same length as close)
    bear_threshold : minimum peak-to-trough drawdown to qualify (default 0.30 = 30%)
    min_duration : minimum bars between bear start and trough to qualify

    Returns
    -------
    List of Regime objects with kind="bear"
    """
    n = len(close)
    bears = []

    peak_idx = 0
    peak_price = close[0]
    in_bear = False
    bear_start_idx = 0
    trough_idx = 0
    trough_price = close[0]

    for i in range(1, n):
        if in_bear:
            if close[i] < trough_price:
                trough_idx = i
                trough_price = close[i]
            # Bear ends when price recovers above the peak that started it
            # (or recovers enough — use peak_price as the target)
            if close[i] >= peak_price:
                duration = trough_idx - bear_start_idx
                if duration >= min_duration:
                    bears.append(Regime(
                        kind="bear",
                        start_idx=bear_start_idx,
                        end_idx=trough_idx,
                        start_date=str(dates[bear_start_idx])[:10],
                        end_date=str(dates[trough_idx])[:10],
                        start_price=peak_price,
                        end_price=trough_price,
                        move_pct=(trough_price / peak_price - 1) * 100,
                    ))
                # Reset — new peak
                in_bear = False
                peak_idx = i
                peak_price = close[i]
        else:
            if close[i] > peak_price:
                peak_idx = i
                peak_price = close[i]
            else:
                drawdown = (peak_price - close[i]) / peak_price
                if drawdown >= bear_threshold:
                    in_bear = True
                    bear_start_idx = peak_idx
                    trough_idx = i
                    trough_price = close[i]

    # If still in bear at end of data, record it
    if in_bear:
        duration = trough_idx - bear_start_idx
        if duration >= min_duration:
            bears.append(Regime(
                kind="bear",
                start_idx=bear_start_idx,
                end_idx=trough_idx,
                start_date=str(dates[bear_start_idx])[:10],
                end_date=str(dates[trough_idx])[:10],
                start_price=peak_price,
                end_price=trough_price,
                move_pct=(trough_price / peak_price - 1) * 100,
            ))

    return bears


def detect_bull_regimes(
    close: np.ndarray,
    dates: np.ndarray,
    bear_regimes: list[Regime],
    bull_threshold: float = 0.20,
) -> list[Regime]:
    """
    Infer bull market periods as the gaps between bear periods.
    A bull period runs from the trough of one bear to the peak of the next.
    Only includes bull periods with move_pct >= bull_threshold.
    """
    n = len(close)
    bulls = []

    # Start of first bull: beginning of data
    # Each bear gives us a trough; the bull runs trough → next bear start
    prior_end_idx = 0

    for bear in bear_regimes:
        bull_start = prior_end_idx
        bull_end = bear.start_idx

        if bull_end <= bull_start:
            prior_end_idx = bear.end_idx
            continue

        # Find the actual peak in this window
        peak_idx_local = bull_start + int(np.argmax(close[bull_start:bull_end + 1]))
        start_price = close[bull_start]
        peak_price = close[peak_idx_local]
        move_pct = (peak_price / start_price - 1) * 100

        if move_pct >= bull_threshold * 100:
            bulls.append(Regime(
                kind="bull",
                start_idx=bull_start,
                end_idx=peak_idx_local,
                start_date=str(dates[bull_start])[:10],
                end_date=str(dates[peak_idx_local])[:10],
                start_price=start_price,
                end_price=peak_price,
                move_pct=move_pct,
            ))

        prior_end_idx = bear.end_idx

    # Final bull after last bear
    if prior_end_idx < n - 1:
        bull_start = prior_end_idx
        bull_end = n - 1
        peak_idx_local = bull_start + int(np.argmax(close[bull_start:bull_end + 1]))
        start_price = close[bull_start]
        peak_price = close[peak_idx_local]
        move_pct = (peak_price / start_price - 1) * 100
        if move_pct >= bull_threshold * 100:
            bulls.append(Regime(
                kind="bull",
                start_idx=bull_start,
                end_idx=peak_idx_local,
                start_date=str(dates[bull_start])[:10],
                end_date=str(dates[peak_idx_local])[:10],
                start_price=start_price,
                end_price=peak_price,
                move_pct=move_pct,
            ))

    return bulls


def score_regime_capture(
    trades: list,
    close: np.ndarray,
    dates: np.ndarray,
    bear_threshold: float = 0.30,
    bull_threshold: float = 0.20,
    min_duration: int = 20,
    boundary_shift: int = 0,
    exclude_bear_idx: int | None = None,
    exclude_bull_idx: int | None = None,
) -> RegimeScore:
    """
    Score how well the strategy captures bull markets and avoids bear markets.

    For each bull period: compute what fraction of the price gain (trough to peak)
    the strategy participated in based on bars held within that period.

    For each bear period: compute what fraction of the price loss the strategy
    avoided by being out of the market.

    Parameters
    ----------
    boundary_shift : shift all regime boundaries by this many bars (for perturbation testing)
    exclude_bear_idx : skip the bear period at this index (for jackknife)
    exclude_bull_idx : skip the bull period at this index (for jackknife)

    Returns a RegimeScore with composite = 0.5 * bull_capture + 0.5 * bear_avoidance.
    """
    n = len(close)

    # Build a bar-by-bar "in market" array from the trade log
    in_market = np.zeros(n, dtype=bool)
    for t in trades:
        entry = t.entry_bar
        exit_b = t.exit_bar if t.exit_bar >= 0 else n - 1
        in_market[entry:exit_b + 1] = True

    # Detect regimes
    bears = detect_bear_regimes(close, dates, bear_threshold=bear_threshold, min_duration=min_duration)
    bulls = detect_bull_regimes(close, dates, bears, bull_threshold=bull_threshold)

    # Apply boundary shift if requested (perturbation test)
    if boundary_shift != 0:
        shifted_bears = []
        for bear in bears:
            new_start = max(0, min(n - 1, bear.start_idx + boundary_shift))
            new_end = max(0, min(n - 1, bear.end_idx + boundary_shift))
            if new_end > new_start:
                shifted_bears.append(Regime(
                    kind=bear.kind, start_idx=new_start, end_idx=new_end,
                    start_date=bear.start_date, end_date=bear.end_date,
                    start_price=bear.start_price, end_price=bear.end_price,
                    move_pct=bear.move_pct,
                ))
        bears = shifted_bears

        shifted_bulls = []
        for bull in bulls:
            new_start = max(0, min(n - 1, bull.start_idx + boundary_shift))
            new_end = max(0, min(n - 1, bull.end_idx + boundary_shift))
            if new_end > new_start:
                shifted_bulls.append(Regime(
                    kind=bull.kind, start_idx=new_start, end_idx=new_end,
                    start_date=bull.start_date, end_date=bull.end_date,
                    start_price=bull.start_price, end_price=bull.end_price,
                    move_pct=bull.move_pct,
                ))
        bulls = shifted_bulls

    # ── Score bear avoidance ──
    bear_detail = []
    bear_avoidance_scores_list = []
    for i, bear in enumerate(bears):
        if exclude_bear_idx is not None and i == exclude_bear_idx:
            continue
        s, e = bear.start_idx, bear.end_idx
        if e <= s:
            continue
        bear_bars = e - s
        bars_out = np.sum(~in_market[s:e])
        avoidance = bars_out / bear_bars if bear_bars > 0 else 1.0
        bear_avoidance_scores_list.append(avoidance)
        bear_detail.append({
            "start": bear.start_date,
            "end": bear.end_date,
            "move_pct": round(bear.move_pct, 1),
            "avoided_pct": round(avoidance * 100, 1),
        })

    # ── Score bull capture ──
    bull_detail = []
    bull_capture_scores_list = []
    for i, bull in enumerate(bulls):
        if exclude_bull_idx is not None and i == exclude_bull_idx:
            continue
        s, e = bull.start_idx, bull.end_idx
        if e <= s:
            continue
        bull_bars = e - s
        bars_in = np.sum(in_market[s:e])
        capture = bars_in / bull_bars if bull_bars > 0 else 0.0
        bull_capture_scores_list.append(capture)
        bull_detail.append({
            "start": bull.start_date,
            "end": bull.end_date,
            "move_pct": round(bull.move_pct, 1),
            "captured_pct": round(capture * 100, 1),
        })

    bull_capture = float(np.mean(bull_capture_scores_list)) if bull_capture_scores_list else 0.0
    bear_avoidance = float(np.mean(bear_avoidance_scores_list)) if bear_avoidance_scores_list else 1.0
    composite = 0.5 * bull_capture + 0.5 * bear_avoidance

    # ── Compute HHI on cycle contributions ──
    all_scores = bull_capture_scores_list + bear_avoidance_scores_list
    if len(all_scores) >= 2:
        total = sum(all_scores)
        if total > 0:
            shares = [s / total for s in all_scores]
            hhi = sum(s ** 2 for s in shares)
        else:
            hhi = 1.0
    else:
        hhi = 1.0  # single cycle = maximally concentrated

    return RegimeScore(
        bull_capture_ratio=round(bull_capture, 4),
        bear_avoidance_ratio=round(bear_avoidance, 4),
        composite=round(composite, 4),
        num_bull_periods=len([b for i, b in enumerate(bulls) if exclude_bull_idx is None or i != exclude_bull_idx]),
        num_bear_periods=len([b for i, b in enumerate(bears) if exclude_bear_idx is None or i != exclude_bear_idx]),
        bull_detail=bull_detail,
        bear_detail=bear_detail,
        bull_capture_scores=bull_capture_scores_list,
        bear_avoidance_scores=bear_avoidance_scores_list,
        hhi=round(hhi, 4),
    )


from strategy_engine import (  # noqa: E402
    BacktestResult,
    StrategyParams,
    Trade,
    _adx as adx,
    _atr as atr,
    _ema as ema,
    _highest as highest,
    _lowest as lowest,
    _sma as sma,
    _tema as tema,
    run_montauk_821,
)


def run_backtest(df, params: StrategyParams | None = None, *, score_regimes: bool = False):
    """Compatibility wrapper that delegates to the canonical engine."""
    return run_montauk_821(
        df,
        StrategyParams() if params is None else params,
        score_regimes=score_regimes,
    )


if __name__ == "__main__":
    # Smoke test the regime helpers against current TECL data.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from data import get_tecl_data
    from strategy_engine import run_montauk_821

    df = get_tecl_data(use_yfinance=False)
    result = run_montauk_821(df)
    print("=== Montauk 8.2.1 (regime helpers smoke-test) ===")
    print(result.summary_str())
    if result.regime_score:
        print("\nBear periods detected:")
        for b in result.regime_score.bear_detail:
            print(f"  {b['start']} → {b['end']}  move={b['move_pct']:+.1f}%  avoided={b['avoided_pct']:.1f}%")
        print("\nBull periods detected:")
        for b in result.regime_score.bull_detail:
            print(f"  {b['start']} → {b['end']}  move={b['move_pct']:+.1f}%  captured={b['captured_pct']:.1f}%")

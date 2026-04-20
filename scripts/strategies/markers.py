#!/usr/bin/env python3
"""
Discovery-stage marker prior for Project Montauk.

The hand-marked TECL cycles are a soft discovery prior only. They should help
the optimizer prefer low-frequency big-cycle behavior without becoming a hard
optimization target or a validation gate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER_CSV = os.path.join(PROJECT_ROOT, "data", "markers", "TECL-markers.csv")
DEFAULT_TRANSITION_TOLERANCE_BARS = 30
NEUTRAL_MARKER_SCORE = 0.5


@dataclass
class MarkerCycle:
    buy_date: pd.Timestamp
    sell_date: pd.Timestamp | None


def _normalize_dates(series) -> np.ndarray:
    return pd.to_datetime(series).dt.normalize().values.astype("datetime64[ns]")


def load_marker_cycles(path: str = MARKER_CSV) -> list[MarkerCycle]:
    if not os.path.exists(path):
        return []

    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"date", "type"}
    if not required.issubset(df.columns):
        raise ValueError(f"Marker CSV missing required columns: {required - set(df.columns)}")
    if df.empty:
        return []

    marker_types = df["type"].astype(str).str.strip().str.lower().tolist()
    if marker_types[0] != "buy":
        raise ValueError("Marker CSV must start with a buy marker")

    cycles: list[MarkerCycle] = []
    open_buy: pd.Timestamp | None = None
    last_type = None
    for row in df.itertuples(index=False):
        marker_type = str(row.type).strip().lower()
        if marker_type not in {"buy", "sell"}:
            raise ValueError(f"Unsupported marker type: {row.type}")
        if marker_type == last_type:
            raise ValueError(f"Marker CSV contains consecutive {marker_type} markers")

        marker_date = pd.Timestamp(row.date).normalize()
        if marker_type == "buy":
            open_buy = marker_date
        else:
            if open_buy is None:
                raise ValueError("Encountered sell marker without an open buy marker")
            cycles.append(MarkerCycle(buy_date=open_buy, sell_date=marker_date))
            open_buy = None
        last_type = marker_type

    if open_buy is not None:
        cycles.append(MarkerCycle(buy_date=open_buy, sell_date=None))

    return cycles


def _date_to_bar(dates: np.ndarray, when: pd.Timestamp) -> int | None:
    idx = int(np.searchsorted(dates, np.datetime64(when), side="left"))
    if idx >= len(dates):
        return None
    return idx


def candidate_risk_state_from_trades(n_bars: int, trades: list) -> np.ndarray:
    state = np.zeros(n_bars, dtype=bool)
    for trade in trades or []:
        entry_bar = max(0, int(trade.entry_bar))
        exit_bar = int(trade.exit_bar) if getattr(trade, "exit_bar", -1) >= 0 else (n_bars - 1)
        exit_bar = min(n_bars - 1, max(entry_bar, exit_bar))
        state[entry_bar:exit_bar + 1] = True
    return state


def marker_target_from_df(df: pd.DataFrame, cycles: list[MarkerCycle] | None = None) -> dict:
    cycles = cycles if cycles is not None else load_marker_cycles()
    if not cycles:
        return {
            "state": np.zeros(len(df), dtype=bool),
            "buy_bars": [],
            "sell_bars": [],
            "overlap_start": None,
            "overlap_end": None,
        }

    dates = _normalize_dates(df["date"])
    state = np.zeros(len(df), dtype=bool)
    buy_bars: list[int] = []
    sell_bars: list[int] = []

    for cycle in cycles:
        buy_bar = _date_to_bar(dates, cycle.buy_date)
        if buy_bar is None:
            continue
        buy_bars.append(buy_bar)
        if cycle.sell_date is None:
            state[buy_bar:] = True
            continue
        sell_bar = _date_to_bar(dates, cycle.sell_date)
        if sell_bar is None:
            state[buy_bar:] = True
            continue
        if sell_bar <= buy_bar:
            continue
        state[buy_bar:sell_bar] = True
        sell_bars.append(sell_bar)

    all_points = buy_bars + sell_bars
    if not all_points:
        overlap_start = None
        overlap_end = None
    else:
        overlap_start = min(all_points)
        overlap_end = max(all_points)

    return {
        "state": state,
        "buy_bars": sorted(buy_bars),
        "sell_bars": sorted(sell_bars),
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
    }


def _transition_bars_from_state(state: np.ndarray) -> tuple[list[int], list[int]]:
    buys = []
    sells = []
    prev = False
    for idx, value in enumerate(state):
        curr = bool(value)
        if curr and not prev:
            buys.append(idx)
        elif prev and not curr:
            sells.append(idx)
        prev = curr
    return buys, sells


def _precision_recall_f1(target_state: np.ndarray, candidate_state: np.ndarray) -> tuple[float, float, float]:
    tp = int(np.sum(target_state & candidate_state))
    candidate_on = int(np.sum(candidate_state))
    target_on = int(np.sum(target_state))

    precision = tp / candidate_on if candidate_on > 0 else 0.0
    recall = tp / target_on if target_on > 0 else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _transition_timing_score(target_bars: list[int], candidate_bars: list[int], tolerance_bars: int) -> tuple[float, list[dict]]:
    if not target_bars:
        return 1.0, []
    if not candidate_bars:
        return 0.0, [{"target_bar": int(target), "nearest_bar": None, "distance_bars": None, "score": 0.0} for target in target_bars]

    details = []
    scores = []
    for target in target_bars:
        nearest = min(candidate_bars, key=lambda bar: abs(bar - target))
        distance = abs(nearest - target)
        score = max(0.0, 1.0 - distance / max(tolerance_bars, 1))
        details.append({
            "target_bar": int(target),
            "nearest_bar": int(nearest),
            "distance_bars": int(distance),
            "score": round(score, 4),
        })
        scores.append(score)
    return float(np.mean(scores)), details


def score_marker_alignment(
    df: pd.DataFrame,
    trades: list,
    *,
    tolerance_bars: int = DEFAULT_TRANSITION_TOLERANCE_BARS,
) -> dict:
    target = marker_target_from_df(df)
    overlap_start = target["overlap_start"]
    overlap_end = target["overlap_end"]
    if overlap_start is None or overlap_end is None or overlap_end <= overlap_start:
        return {
            "score": NEUTRAL_MARKER_SCORE,
            "state_accuracy": NEUTRAL_MARKER_SCORE,
            "precision": NEUTRAL_MARKER_SCORE,
            "recall": NEUTRAL_MARKER_SCORE,
            "f1": NEUTRAL_MARKER_SCORE,
            "transition_timing_score": NEUTRAL_MARKER_SCORE,
            "transition_count_score": NEUTRAL_MARKER_SCORE,
            "tolerance_bars": tolerance_bars,
            "overlap_start": None,
            "overlap_end": None,
            "target_buy_count": 0,
            "target_sell_count": 0,
            "candidate_buy_count": 0,
            "candidate_sell_count": 0,
            "buy_transition_matches": [],
            "sell_transition_matches": [],
        }

    candidate_state = candidate_risk_state_from_trades(len(df), trades)
    target_window = target["state"][overlap_start:overlap_end + 1]
    candidate_window = candidate_state[overlap_start:overlap_end + 1]

    state_accuracy = float(np.mean(target_window == candidate_window))
    precision, recall, f1 = _precision_recall_f1(target_window, candidate_window)

    candidate_buys, candidate_sells = _transition_bars_from_state(candidate_state)
    target_buys = [bar for bar in target["buy_bars"] if overlap_start <= bar <= overlap_end]
    target_sells = [bar for bar in target["sell_bars"] if overlap_start <= bar <= overlap_end]
    candidate_buys = [bar for bar in candidate_buys if overlap_start <= bar <= overlap_end]
    candidate_sells = [bar for bar in candidate_sells if overlap_start <= bar <= overlap_end]

    buy_timing, buy_matches = _transition_timing_score(target_buys, candidate_buys, tolerance_bars)
    sell_timing, sell_matches = _transition_timing_score(target_sells, candidate_sells, tolerance_bars)
    transition_timing_score = float(np.mean([buy_timing, sell_timing]))

    buy_count_score = max(0.0, 1.0 - abs(len(candidate_buys) - len(target_buys)) / max(len(target_buys), 1))
    sell_count_score = max(0.0, 1.0 - abs(len(candidate_sells) - len(target_sells)) / max(len(target_sells), 1))
    transition_count_score = float(np.mean([buy_count_score, sell_count_score]))

    score = float(np.mean([state_accuracy, f1, transition_timing_score, transition_count_score]))
    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    return {
        "score": round(score, 4),
        "state_accuracy": round(state_accuracy, 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "transition_timing_score": round(transition_timing_score, 4),
        "transition_count_score": round(transition_count_score, 4),
        "tolerance_bars": int(tolerance_bars),
        "overlap_start": dates.iloc[overlap_start],
        "overlap_end": dates.iloc[overlap_end],
        "target_buy_count": len(target_buys),
        "target_sell_count": len(target_sells),
        "candidate_buy_count": len(candidate_buys),
        "candidate_sell_count": len(candidate_sells),
        "buy_transition_matches": buy_matches,
        "sell_transition_matches": sell_matches,
    }

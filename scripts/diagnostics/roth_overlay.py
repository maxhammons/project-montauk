#!/usr/bin/env python3
"""
Binary Roth overlay simulation for validated Project Montauk winners.

The core TECL signal remains binary in/out. This module simulates how regular
Roth contributions are routed between SGOV and TECL on top of that signal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from data.loader import get_sgov_data, get_tecl_data
from validation.sprint1 import get_strategy_trades


DEFAULT_ANNUAL_CONTRIBUTION = 7500.0


@dataclass
class ContributionLot:
    contribution_date: pd.Timestamp
    amount: float
    shares: float


def _align_overlay_frames(tecl_df: pd.DataFrame, sgov_df: pd.DataFrame) -> pd.DataFrame:
    start = max(pd.Timestamp(tecl_df["date"].min()), pd.Timestamp(sgov_df["date"].min()))
    end = min(pd.Timestamp(tecl_df["date"].max()), pd.Timestamp(sgov_df["date"].max()))

    tecl = tecl_df.loc[(tecl_df["date"] >= start) & (tecl_df["date"] <= end), ["date", "close"]].copy()
    sgov_price_col = "adj_close" if "adj_close" in sgov_df.columns else "close"
    sgov = sgov_df.loc[
        (sgov_df["date"] >= start) & (sgov_df["date"] <= end),
        ["date", sgov_price_col],
    ].copy()
    sgov = sgov.rename(columns={sgov_price_col: "sgov_close"})
    frame = tecl.merge(sgov, on="date", how="left")
    frame["sgov_close"] = frame["sgov_close"].ffill().bfill()
    frame = frame.dropna(subset=["close", "sgov_close"]).reset_index(drop=True)
    return frame


def _monthly_contribution_flags(dates: pd.Series) -> np.ndarray:
    month_key = dates.dt.strftime("%Y-%m")
    first_indices = month_key.drop_duplicates().index
    flags = np.zeros(len(dates), dtype=bool)
    flags[first_indices] = True
    return flags


def _risk_state_from_trades(n_bars: int, trades: list) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    risk_on = np.zeros(n_bars, dtype=bool)
    buy_events = np.zeros(n_bars, dtype=bool)
    sell_events = np.zeros(n_bars, dtype=bool)
    for trade in trades or []:
        entry_bar = max(0, int(trade.entry_bar))
        exit_bar = int(trade.exit_bar) if getattr(trade, "exit_bar", -1) >= 0 else (n_bars - 1)
        exit_bar = min(n_bars - 1, max(entry_bar, exit_bar))
        risk_on[entry_bar:exit_bar + 1] = True
        buy_events[entry_bar] = True
        sell_events[exit_bar] = True
    return risk_on, buy_events, sell_events


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    arr = np.asarray(values, dtype=np.float64)
    peak = np.maximum.accumulate(arr)
    dd = np.where(peak > 0, (arr - peak) / peak, 0.0)
    return round(abs(float(dd.min())) * 100.0, 2)


def _average_lag_days(lag_events: list[tuple[float, int]]) -> float:
    if not lag_events:
        return 0.0
    total_weight = sum(weight for weight, _days in lag_events)
    if total_weight <= 0:
        return 0.0
    return round(sum(weight * days for weight, days in lag_events) / total_weight, 1)


def simulate_binary_roth_overlay(
    strategy_name: str,
    params: dict,
    *,
    annual_contribution: float = DEFAULT_ANNUAL_CONTRIBUTION,
) -> dict:
    tecl_df = get_tecl_data(use_yfinance=False)
    sgov_df = get_sgov_data()
    trades, _ = get_strategy_trades(tecl_df, strategy_name, params)
    if trades is None:
        raise ValueError(f"Could not evaluate strategy for overlay: {strategy_name}")

    frame = _align_overlay_frames(tecl_df, sgov_df)
    if frame.empty:
        raise ValueError("No overlapping TECL/SGOV data available for overlay")

    start_date = pd.Timestamp(frame["date"].iloc[0])
    end_date = pd.Timestamp(frame["date"].iloc[-1])
    n = len(frame)
    monthly_contribution = annual_contribution / 12.0

    risk_on_full, buy_events_full, sell_events_full = _risk_state_from_trades(len(tecl_df), trades)
    lookup = {pd.Timestamp(date): idx for idx, date in enumerate(pd.to_datetime(tecl_df["date"]))}
    risk_on = np.zeros(n, dtype=bool)
    buy_events = np.zeros(n, dtype=bool)
    sell_events = np.zeros(n, dtype=bool)
    for i, when in enumerate(pd.to_datetime(frame["date"])):
        src_idx = lookup.get(pd.Timestamp(when))
        if src_idx is None:
            continue
        risk_on[i] = risk_on_full[src_idx]
        buy_events[i] = buy_events_full[src_idx]
        sell_events[i] = sell_events_full[src_idx]

    contribution_flags = _monthly_contribution_flags(pd.to_datetime(frame["date"]))

    tecl_shares = 0.0
    sgov_shares = 0.0
    contribution_lots: list[ContributionLot] = []
    lag_events: list[tuple[float, int]] = []
    total_contributions = 0.0
    total_account_values = []
    sweep_count = 0
    risk_on_contribution_count = 0
    risk_off_contribution_count = 0

    for i, row in frame.iterrows():
        when = pd.Timestamp(row["date"])
        tecl_close = float(row["close"])
        sgov_close = float(row["sgov_close"])

        if sell_events[i] and tecl_shares > 0:
            proceeds = tecl_shares * tecl_close
            if sgov_close > 0:
                sgov_shares += proceeds / sgov_close
            tecl_shares = 0.0

        if buy_events[i] and sgov_shares > 0:
            sweep_value = sgov_shares * sgov_close
            if tecl_close > 0:
                tecl_shares += sweep_value / tecl_close
            sgov_shares = 0.0
            sweep_count += 1
            for lot in contribution_lots:
                lag_days = int((when - lot.contribution_date).days)
                lag_events.append((lot.amount, max(0, lag_days)))
            contribution_lots = []

        if contribution_flags[i]:
            total_contributions += monthly_contribution
            if risk_on[i]:
                if tecl_close > 0:
                    tecl_shares += monthly_contribution / tecl_close
                lag_events.append((monthly_contribution, 0))
                risk_on_contribution_count += 1
            else:
                if sgov_close > 0:
                    shares = monthly_contribution / sgov_close
                    sgov_shares += shares
                    contribution_lots.append(
                        ContributionLot(
                            contribution_date=when,
                            amount=monthly_contribution,
                            shares=shares,
                        )
                    )
                risk_off_contribution_count += 1

        total_account_values.append(tecl_shares * tecl_close + sgov_shares * sgov_close)

    final_tecl_value = tecl_shares * float(frame["close"].iloc[-1])
    final_sgov_value = sgov_shares * float(frame["sgov_close"].iloc[-1])
    final_total_value = final_tecl_value + final_sgov_value

    for lot in contribution_lots:
        lag_days = int((end_date - lot.contribution_date).days)
        lag_events.append((lot.amount, max(0, lag_days)))

    return {
        "assumptions": {
            "annual_contribution": round(annual_contribution, 2),
            "monthly_contribution": round(monthly_contribution, 2),
            "contribution_schedule": "first_trading_day_of_month",
            "risk_off_sleeve": "SGOV",
            "allocation_policy": "binary_tecl_or_sgov",
            "simulation_start": start_date.strftime("%Y-%m-%d"),
            "simulation_end": end_date.strftime("%Y-%m-%d"),
        },
        "total_contributions": round(total_contributions, 2),
        "final_tecl_value": round(final_tecl_value, 2),
        "final_sgov_value": round(final_sgov_value, 2),
        "final_total_value": round(final_total_value, 2),
        "max_drawdown_pct": _max_drawdown(total_account_values),
        "sweep_count": int(sweep_count),
        "avg_cash_deployment_lag_days": _average_lag_days(lag_events),
        "risk_on_contribution_count": int(risk_on_contribution_count),
        "risk_off_contribution_count": int(risk_off_contribution_count),
    }


def simulate_tecl_dca_baseline(
    *,
    annual_contribution: float = DEFAULT_ANNUAL_CONTRIBUTION,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    tecl_df = get_tecl_data(use_yfinance=False).copy()
    if start_date:
        tecl_df = tecl_df.loc[tecl_df["date"] >= pd.Timestamp(start_date)].copy()
    if end_date:
        tecl_df = tecl_df.loc[tecl_df["date"] <= pd.Timestamp(end_date)].copy()
    tecl_df = tecl_df.reset_index(drop=True)
    monthly_contribution = annual_contribution / 12.0
    contribution_flags = _monthly_contribution_flags(pd.to_datetime(tecl_df["date"]))

    shares = 0.0
    total_contributions = 0.0
    account_values = []

    for i, row in tecl_df.iterrows():
        close = float(row["close"])
        if contribution_flags[i] and close > 0:
            total_contributions += monthly_contribution
            shares += monthly_contribution / close
        account_values.append(shares * close)

    return {
        "annual_contribution": round(annual_contribution, 2),
        "monthly_contribution": round(monthly_contribution, 2),
        "simulation_start": pd.Timestamp(tecl_df["date"].iloc[0]).strftime("%Y-%m-%d"),
        "simulation_end": pd.Timestamp(tecl_df["date"].iloc[-1]).strftime("%Y-%m-%d"),
        "total_contributions": round(total_contributions, 2),
        "final_total_value": round(account_values[-1] if account_values else 0.0, 2),
        "max_drawdown_pct": _max_drawdown(account_values),
    }


def build_champion_overlay(
    strategy_name: str,
    params: dict,
    *,
    annual_contribution: float = DEFAULT_ANNUAL_CONTRIBUTION,
) -> dict:
    overlay = simulate_binary_roth_overlay(
        strategy_name,
        params,
        annual_contribution=annual_contribution,
    )
    baseline = simulate_tecl_dca_baseline(
        annual_contribution=annual_contribution,
        start_date=overlay["assumptions"]["simulation_start"],
        end_date=overlay["assumptions"]["simulation_end"],
    )
    overlay["vs_tecl_dca"] = {
        "baseline_final_total_value": baseline["final_total_value"],
        "baseline_max_drawdown_pct": baseline["max_drawdown_pct"],
        "difference_value": round(overlay["final_total_value"] - baseline["final_total_value"], 2),
        "difference_pct": round(
            ((overlay["final_total_value"] / baseline["final_total_value"]) - 1) * 100,
            2,
        ) if baseline["final_total_value"] > 0 else 0.0,
    }
    overlay["baseline"] = baseline
    return overlay

#!/usr/bin/env python3
"""
Signal Diversity — compare strategy risk-state overlap.

Use this after Spike/grid runs to answer whether a candidate is genuinely
different from Bonobo or just another timing-near-duplicate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loader import get_tecl_data
from engine.strategy_engine import Indicators, backtest
from strategies.library import STRATEGY_REGISTRY
from strategies.markers import candidate_risk_state_from_trades


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEADERBOARD_PATH = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")


def _load_entry(strategy: str | None, params_json: str | None) -> tuple[str, dict]:
    if strategy:
        params = json.loads(params_json) if params_json else {}
        return strategy, params
    with open(LEADERBOARD_PATH) as f:
        leaderboard = json.load(f)
    if not leaderboard:
        raise ValueError("leaderboard is empty")
    top = leaderboard[0]
    return top["strategy"], top.get("params", {})


def _state_for(strategy: str, params: dict, df) -> tuple[np.ndarray, object]:
    if strategy not in STRATEGY_REGISTRY:
        raise KeyError(f"unknown strategy: {strategy}")
    ind = Indicators(df)
    entries, exits, labels = STRATEGY_REGISTRY[strategy](ind, params)
    result = backtest(
        df,
        entries,
        exits,
        labels,
        cooldown_bars=int(params.get("cooldown", 0)),
        strategy_name=strategy,
    )
    return candidate_risk_state_from_trades(len(df), result.trades), result


def compare(a_state: np.ndarray, b_state: np.ndarray) -> dict:
    both_on = int(np.sum(a_state & b_state))
    either_on = int(np.sum(a_state | b_state))
    both_off = int(np.sum((~a_state) & (~b_state)))
    disagree = int(np.sum(a_state != b_state))
    n = len(a_state)
    corr = 0.0
    if np.std(a_state.astype(float)) > 0 and np.std(b_state.astype(float)) > 0:
        corr = float(np.corrcoef(a_state.astype(float), b_state.astype(float))[0, 1])
    return {
        "bars": n,
        "state_agreement": round(float(np.mean(a_state == b_state)), 4),
        "disagreement_bars": disagree,
        "disagreement_pct": round(disagree / n * 100, 2) if n else 0.0,
        "jaccard_risk_on": round(both_on / either_on, 4) if either_on else 1.0,
        "risk_on_corr": round(corr, 4),
        "both_on_pct": round(both_on / n * 100, 2) if n else 0.0,
        "both_off_pct": round(both_off / n * 100, 2) if n else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="base strategy; default leaderboard #1")
    parser.add_argument("--base-params-json", default=None)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-params-json", default=None)
    args = parser.parse_args()

    base_name, base_params = _load_entry(args.base, args.base_params_json)
    cand_name, cand_params = _load_entry(args.candidate, args.candidate_params_json)
    df = get_tecl_data()
    base_state, base_result = _state_for(base_name, base_params, df)
    cand_state, cand_result = _state_for(cand_name, cand_params, df)
    payload = {
        "base": {
            "strategy": base_name,
            "share_multiple": base_result.share_multiple,
            "real_share_multiple": base_result.real_share_multiple,
            "modern_share_multiple": base_result.modern_share_multiple,
            "trades": base_result.num_trades,
        },
        "candidate": {
            "strategy": cand_name,
            "share_multiple": cand_result.share_multiple,
            "real_share_multiple": cand_result.real_share_multiple,
            "modern_share_multiple": cand_result.modern_share_multiple,
            "trades": cand_result.num_trades,
        },
        "diversity": compare(base_state, cand_state),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

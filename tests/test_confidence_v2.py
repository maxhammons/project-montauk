from __future__ import annotations

import pytest

from validation.confidence_v2 import calibration_lookup, score_entry


def _row(max_dd: float = 60.0, strategy: str = "gc_vjatr") -> dict:
    return {
        "strategy": strategy,
        "display_name": "Test Strategy",
        "tier": "T2",
        "gold_status": True,
        "params": {
            "fast_ema": 140,
            "slow_ema": 160,
            "slope_window": 1,
            "entry_bars": 2,
            "atr_period": 7,
        },
        "metrics": {
            "share_multiple": 12.0,
            "real_share_multiple": 1.2,
            "modern_share_multiple": 2.5,
            "max_dd": max_dd,
            "regime_score": 0.72,
        },
        "validation": {
            "composite_confidence": 0.75,
            "sub_scores": {
                "walk_forward": 1.0,
                "marker_shape": 0.95,
                "marker_timing": 0.45,
                "named_windows": 0.50,
                "era_consistency": 1.0,
                "fragility": 0.90,
                "selection_bias": 0.70,
                "bootstrap": 0.80,
                "trade_sufficiency": 1.0,
            },
            "soft_warnings": [],
            "critical_warnings": [],
        },
    }


def test_calibrated_lookup_blends_bucket_survival_without_flattening_raw_score():
    model = {
        "status": "calibrated",
        "buckets": [
            {
                "min_score": 0.0,
                "max_score": 1.0,
                "midpoint": 0.5,
                "observed_survival_rate": 0.40,
            }
        ],
    }

    low, low_state = calibration_lookup(model, 0.50)
    high, high_state = calibration_lookup(model, 0.80)

    assert low_state == "calibrated"
    assert high_state == "calibrated"
    assert low == pytest.approx(0.465)
    assert high == pytest.approx(0.66)
    assert high > low


def test_score_entry_separates_edge_confidence_from_capital_readiness_drawdown():
    hash_summary = {"n_configs": 1000, "rs_p99": 0.65}
    model = {
        "status": "calibrated",
        "buckets": [
            {
                "min_score": 0.0,
                "max_score": 1.0,
                "midpoint": 0.5,
                "observed_survival_rate": 0.50,
            }
        ],
    }

    normal = score_entry(
        _row(max_dd=60.0),
        family_size=1,
        duplicate_score=1.0,
        hash_summary=hash_summary,
        calibration_model=model,
    )
    fragile = score_entry(
        _row(max_dd=98.0),
        family_size=1,
        duplicate_score=1.0,
        hash_summary=hash_summary,
        calibration_model=model,
    )

    assert normal["edge_confidence"] > fragile["edge_confidence"]
    assert normal["capital_readiness"] > fragile["capital_readiness"]
    assert fragile["capital_readiness_components"]["drawdown_resilience"] == 0.0
    assert normal["calibration_state"] == "calibrated"

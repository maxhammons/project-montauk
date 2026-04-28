import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from diagnostics.overlay_champion_matrix import (
    load_overlay_candidates,
    merge_base_overlay,
)


def test_merge_base_overlay_preserves_overlay_keys_and_replaces_base_keys():
    base = {
        "fast_ema": 140,
        "slow_ema": 160,
        "atr_period": 7,
        "cooldown": 0,
    }
    overlay = {
        "fast_ema": 130,
        "slow_ema": 150,
        "atr_period": 16,
        "rsi_len": 14,
        "vol_ratio_max": 0.85,
    }

    merged = merge_base_overlay(base, overlay)

    assert merged["fast_ema"] == 140
    assert merged["slow_ema"] == 160
    assert merged["atr_period"] == 7
    assert merged["cooldown"] == 0
    assert merged["rsi_len"] == 14
    assert merged["vol_ratio_max"] == 0.85


def test_load_overlay_candidates_deduplicates_overlay_signature(tmp_path):
    payload = {
        "validation": {
            "validated_rankings": [
                {
                    "strategy": "gc_vjatr_reclaimer",
                    "rank": 1,
                    "params": {
                        "fast_ema": 140,
                        "slow_ema": 160,
                        "rsi_len": 14,
                        "vol_ratio_max": 0.85,
                    },
                },
                {
                    "strategy": "gc_vjatr_reclaimer",
                    "rank": 2,
                    "params": {
                        "fast_ema": 130,
                        "slow_ema": 150,
                        "rsi_len": 14,
                        "vol_ratio_max": 0.85,
                    },
                },
                {
                    "strategy": "gc_vjatr_reclaimer",
                    "rank": 3,
                    "params": {
                        "fast_ema": 140,
                        "slow_ema": 160,
                        "rsi_len": 21,
                        "vol_ratio_max": 0.85,
                    },
                },
            ]
        }
    }
    path = tmp_path / "grid.json"
    path.write_text(__import__("json").dumps(payload))

    candidates = load_overlay_candidates(
        overlay_strategy="gc_vjatr_reclaimer",
        grid_path=str(path),
        params_json=None,
        limit=10,
    )

    assert [c["source_rank"] for c in candidates] == [1, 3]

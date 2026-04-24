#!/usr/bin/env python3
"""
Grid Search — Exhaustive canonical-param search for T1 strategy concepts.

Instead of running a GA (which spends hours on random mutation/crossover),
this module backtests EVERY combo in a discrete canonical grid in seconds,
pre-filters by charter gates, then validates survivors through the full
tier-routed pipeline.

Usage:
    python3 scripts/grid_search.py                    # all concepts, all grids
    python3 scripts/grid_search.py --concepts golden_cross_slope,ema_slope_above
    python3 scripts/grid_search.py --dry-run           # just show combos + smoke test
"""

from __future__ import annotations

import argparse
import itertools
import multiprocessing
import os
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.regime_helpers import score_regime_capture
from data.loader import get_tecl_data
from strategies.markers import score_marker_alignment
from search.evolve import (
    fitness as compute_fitness,
    _count_tunable_params,
    update_leaderboard,
)
from strategies.library import STRATEGY_REGISTRY, STRATEGY_TIERS
from engine.strategy_engine import Indicators, backtest
from validation.pipeline import run_validation_pipeline

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


# ─────────────────────────────────────────────────────────────────────────────
# Canonical grids — discrete canonical values to test for each concept.
# Every value must be from the strict canonical set (canonical_params.py).
# Total combos per concept shown in comments.
# ─────────────────────────────────────────────────────────────────────────────

GRIDS = {
    "golden_cross_slope": {  # 4 × 3 × 2 × 2 = 48 combos
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "ema_slope_above": {  # 4 × 2 × 2 = 16 combos
        "ema_len": [50, 100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "rsi_recovery_ema": {  # 3 × 4 = 12 combos
        "rsi_len": [7, 14, 21],
        "trend_len": [50, 100, 150, 200],
        "cooldown": [5],
    },
    "rsi_50_above_trend": {  # 2 × 3 × 2 = 12 combos
        "rsi_len": [7, 14],
        "trend_len": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "triple_ema_stack": {  # 3 × 2 × 2 × 2 = 24 combos
        "short_ema": [20, 30, 50],
        "med_ema": [100, 150],
        "long_ema": [200, 300],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "dual_ema_stack": {  # 4 × 3 × 2 = 24 combos
        "short_ema": [20, 30, 50, 100],
        "long_ema": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "donchian_filter": {  # 4 × 3 × 3 = 36 combos
        "entry_len": [50, 100, 150, 200],
        "exit_len": [20, 50, 100],
        "trend_len": [50, 100, 200],
        "cooldown": [5],
    },
    "macd_above_zero_trend": {  # 3 = 3 combos
        "trend_len": [100, 150, 200],
        "cooldown": [5],
    },
    "ema_pure_slope": {  # 4 × 2 × 2 = 16 combos
        "ema_len": [50, 100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "ema_200_confirm": {  # 3 × 3 = 9 combos
        "ema_len": [100, 150, 200],
        "entry_bars": [2, 3, 5],
        "cooldown": [5],
    },
    "ema_200_regime": {  # 3 × 2 = 6 combos
        "ema_len": [100, 150, 200],
        "cooldown": [2, 5],
    },
    # ── Spike batch 2026-04-14: new signal families ──
    "roc_above_trend": {  # 3 × 3 × 2 = 18 combos
        "roc_len": [10, 20, 50],
        "trend_len": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "stoch_recovery_trend": {  # 3 × 3 = 9 combos
        "stoch_len": [7, 14, 21],
        "trend_len": [100, 150, 200],
        "cooldown": [5],
    },
    "adx_di_trend": {  # 3 × 3 × 2 = 18 combos
        "adx_len": [7, 14, 21],
        "trend_len": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "keltner_breakout": {  # 2 × 3 × 2 = 12 combos
        "kc_ema_len": [20, 50],
        "kc_atr_mult": [1.5, 2.0, 2.5],
        "trend_len": [100, 200],
        "cooldown": [5],
    },
    "vol_calm_regime": {  # 3 × 3 = 9 combos
        "vol_short": [10, 20, 50],
        "vol_long": [100, 150, 200],
        "cooldown": [5],
    },
    "macd_hist_trend": {  # 3 × 3 = 9 combos
        "trend_len": [100, 150, 200],
        "entry_bars": [2, 3, 5],
        "cooldown": [5],
    },
    "roc_ema_slope": {  # 3 × 2 × 2 × 2 = 24 combos
        "roc_len": [10, 20, 50],
        "ema_len": [100, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "stoch_cross_trend": {  # 3 × 3 × 2 = 18 combos
        "stoch_len": [7, 14, 21],
        "trend_len": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "double_ema_slope": {  # 3 × 3 × 2 × 2 = 36 combos
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "rsi_roc_combo": {  # 2 × 3 × 2 = 12 combos
        "rsi_len": [7, 14],
        "roc_len": [10, 20, 50],
        "trend_len": [100, 200],
        "cooldown": [5],
    },
    # ── Spike batch 2026-04-14b: oscillator-filtered golden cross ──
    "cci_regime_trend": {  # 2 × 2 × 2 × 2 = 16 combos
        "cci_len": [14, 20],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "willr_recovery_trend": {  # 3 × 2 × 2 × 2 = 24 combos
        "willr_len": [7, 14, 21],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "mfi_above_trend": {  # 3 × 2 × 2 × 2 = 24 combos
        "mfi_len": [7, 14, 21],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "obv_slope_trend": {  # N7 extended 2026-04-20: added 120/150 VJ-pair
        "obv_ema_len": [20, 50, 100],
        "fast_ema": [30, 50, 100, 120],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "bb_width_regime": {  # 2 × 2 × 2 × 2 = 16 combos
        "bb_len": [20, 50],
        "bb_avg_len": [50, 100],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    "tema_short_slope": {  # 3 × 2 × 2 × 2 × 2 = 48 combos
        "tema_len": [20, 30, 50],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "cci_willr_combo": {  # 2 × 3 × 2 × 2 = 24 combos
        "cci_len": [14, 20],
        "willr_len": [7, 14, 21],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    "mfi_obv_trend": {  # 3 × 2 × 2 × 2 × 2 = 48 combos
        "mfi_len": [7, 14, 21],
        "obv_ema_len": [20, 50],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "slope_window": [3, 5],
        "cooldown": [5],
    },
    "atr_ratio_trend": {  # 3 × 3 × 2 × 2 = 36 combos
        "atr_short": [7, 14, 20],
        "atr_long": [50, 100, 200],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    "bb_cci_combo": {  # 2 × 2 × 2 × 2 × 2 = 32 combos
        "cci_len": [14, 20],
        "bb_len": [20, 50],
        "bb_avg_len": [50, 100],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    # ── Spike batch 2026-04-14c: macro + cross-asset + advanced ──
    "vix_gc_filter": {  # 3 × 2 × 2 = 12 combos
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 200],
        "vix_threshold": [20, 50],
        "cooldown": [5],
    },
    "treasury_curve_trend": {  # 3 × 2 × 2 × 2 = 24 combos
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "xlk_relative_strength": {  # 3 × 2 × 2 = 12 combos
        "xlk_fast": [20, 50, 100],
        "xlk_slow": [100, 200],
        "slope_window": [3, 5],
        "cooldown": [5],
    },
    "fed_funds_pivot": {  # 3 × 4 = 12 combos
        "rsi_len": [7, 14, 21],
        "trend_len": [50, 100, 150, 200],
        "cooldown": [5],
    },
    "keltner_squeeze_breakout": {  # 2 × 3 × 3 = 18 combos
        "kc_ema_len": [20, 50],
        "kc_atr_mult": [1.5, 2.0, 2.5],
        "kc_avg_len": [20, 50, 100],
        "cooldown": [5],
    },
    "vix_term_proxy": {  # 3 × 2 × 3 = 18 combos
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 200],
        "vix_sma_len": [20, 30, 50],
        "cooldown": [5],
    },
    "macd_qqq_bull": {  # 3 = 3 combos
        "trend_len": [100, 150, 200],
        "cooldown": [5],
    },
    "dual_tema_breakout": {  # 3 × 2 × 2 × 2 × 2 = 48 combos
        "tema_len": [20, 30, 50],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "vol_donchian_breakout": {  # 3 × 3 = 9 combos (filtered by exit < entry)
        "entry_len": [50, 100, 200],
        "exit_len": [10, 20, 50],
        "cooldown": [5],
    },
    "sgov_flight_switch": {  # 3 × 2 = 6 combos
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    # ── Spike batch 2026-04-14d: golden cross hybrids ──
    "gc_precross": {  # 4 × 2 × 2 = 16 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_asym_fast_entry": {  # 3 × 2 × 2 = 12 combos (filtered entry_fast < entry_slow < exit_slow)
        "entry_fast": [14, 20, 30],
        "entry_slow": [50, 100],
        "exit_fast": [30, 50],
        "exit_slow": [100, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_tema_asym": {  # 3 × 2 × 2 × 2 × 2 = 48 combos (filtered by fast < slow, tema < slow)
        "tema_len": [20, 30, 50],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_spread_momentum": {  # 4 × 2 × 2 = 16 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_precross_roc": {  # 3 × 2 × 3 × 2 = 36 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50],
        "slow_ema": [100, 200],
        "roc_len": [10, 20, 50],
        "slope_window": [3, 5],
        "cooldown": [5],
    },
    "gc_asym_triple": {  # 2 × 2 × 2 = 8 combos (filtered entry_fast < entry_mid < exit_slow)
        "entry_fast": [14, 20],
        "entry_mid": [50, 100],
        "exit_fast": [30, 50],
        "exit_slow": [100, 200],
        "cooldown": [5],
    },
    "gc_spread_band": {  # 4 × 2 × 2 = 16 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_precross_vol": {  # 4 × 2 × 2 × 2 = 32 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_asym_slope": {  # 2 × 2 × 2 × 2 = 16 combos (filtered entry_fast < entry_slow, exit_fast < exit_slow)
        "entry_fast": [14, 20],
        "entry_slow": [50, 100],
        "exit_fast": [30, 50],
        "exit_slow": [100, 200],
        "slope_window": [5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_precross_strict": {  # 4 × 2 × 2 × 2 = 32 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    # ── gc-pre-VIX: pre-cross + VIX panic circuit breaker ──
    "gc_pre_vix": {  # 4 × 3 × 2 × 2 = 48 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "gc_strict_vix": {  # 4 × 3 × 2 × 2 = 48 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "cooldown": [5],
    },
    "atr_ratio_vix": {  # 3 × 3 × 2 × 2 = 36 combos (filtered atr_short < atr_long, fast < slow)
        "atr_short": [7, 14, 20],
        "atr_long": [50, 100, 200],
        "fast_ema": [30, 50],
        "slow_ema": [100, 200],
        "cooldown": [5],
    },
    # ── Spike batch 2026-04-15: diversity strategies (non-crossover) ──
    "drawdown_recovery": {  # 2 × 3 × 3 × 3 × 3 = 162 combos
        "trend_len": [100, 200],
        "lookback": [50, 100, 200],
        "thresh_pct": [15.0, 20.0, 25.0],
        "recover_pct": [25.0, 50.0, 75.0],
        "exit_dd_pct": [15.0, 20.0, 25.0],
    },
    "multi_tf_momentum": {  # 3 × 2 × 2 × 2 = 24 combos
        "short_lb": [20, 30, 50],
        "med_lb": [50, 100],
        "long_lb": [100, 200],
        "confirm_bars": [2, 3],
        "cooldown": [5],
    },
    "rsi_mean_revert_trend": {  # 3 × 2 × 3 × 3 = 54 combos
        "rsi_len": [7, 14, 21],
        "trend_len": [100, 200],
        "oversold": [20.0, 30.0, 40.0],
        "overbought": [70.0, 75.0, 80.0],
        "cooldown": [5],
    },
    "vol_compression_breakout": {  # 3 × 3 × 3 × 3 × 3 = 243 combos
        "atr_period": [7, 14, 20],
        "trend_len": [50, 100, 200],
        "lookback": [20, 50, 100],
        "compress_pct": [2.0, 3.0, 5.0],
        "expand_pct": [6.0, 8.0, 10.0],
    },
    "price_position_regime": {  # 2 × 3 × 2 × 3 = 36 combos
        "high_lb": [100, 200],
        "low_lb": [20, 50, 100],
        "exit_lb": [50, 200],
        "pct_of_high": [85.0, 90.0, 95.0],
        "cooldown": [5],
    },
    "treasury_regime": {  # 3 × 2 × 2 = 12 combos
        "trend_len": [50, 100, 200],
        "slope_window": [3, 5],
        "exit_bars": [2, 3],
        "cooldown": [5],
    },
    "xlk_relative_momentum": {  # 3 × 3 × 2 = 18 combos
        "lookback": [20, 50, 100],
        "trend_len": [20, 50, 100],
        "confirm_bars": [2, 3],
        "cooldown": [5],
    },
    "consecutive_strength": {  # 3 × 3 × 3 × 3 = 81 combos
        "atr_period": [7, 14, 20],
        "entry_streak": [3, 5],
        "exit_streak": [2, 3, 5],
        "atr_mult": [2.0, 2.5, 3.0],
        "cooldown": [5],
    },
    # ── Spike batch 2026-04-15b: diagnostic-informed (fix gc_* weaknesses) ──
    "gc_atr_trail": {  # 4 × 3 × 3 × 2 × 2 × 3 = 432 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "atr_period": [7, 14, 20],
        "slope_window": [3, 5],
        "entry_bars": [2, 3],
        "atr_mult": [2.0, 2.5, 3.0],
    },
    "fast_ema_atr_trail": {  # 3 × 3 × 3 × 2 × 2 × 3 = 324 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50],
        "slow_ema": [50, 100, 150],
        "atr_period": [7, 14, 20],
        "slope_window": [3, 5],
        "confirm_bars": [2, 3],
        "atr_mult": [2.0, 2.5, 3.0],
    },
    "vix_regime_entry": {  # 3 × 3 × 3 = 27 combos
        "trend_len": [50, 100, 200],
        "entry_vix": [15.0, 20.0, 25.0],
        "exit_vix": [25.0, 30.0, 35.0],
        "cooldown": [5],
    },
    "rsi_bull_regime": {  # 3 × 2 × 4 = 24 combos
        "rsi_len": [7, 14, 21],
        "confirm_bars": [2, 3],
        "exit_level": [30.0, 35.0, 40.0, 45.0],
        "cooldown": [5],
    },
    "donchian_vix": {  # 4 × 5 = 20 combos
        "entry_len": [50, 100, 150, 200],
        "exit_len": [20, 30, 50, 70, 100],
        "cooldown": [5],
    },
    "gc_slope_no_death": {  # 4 × 3 × 3 × 2 × 2 × 3 = 432 combos (filtered fast < slow)
        "fast_ema": [20, 30, 50, 100],
        "slow_ema": [100, 150, 200],
        "atr_period": [7, 14, 20],
        "slope_window": [3, 5],
        "confirm_bars": [2, 3],
        "atr_mult": [2.0, 2.5, 3.0],
    },
    # ── GC Enhancement Matrix 2026-04-20 — addons on top of champion gc_strict_vix base ──
    # Base fixed at canonical-near-champion: fast=100, slow=200, slope=3, entry_bars=2, cooldown=2.
    # Addon param sweeps as defined in docs/*NEXT/gc-enhancement-matrix.md.
    "gc_e1": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "xlk_ema_len": [50, 100, 200],
    },
    "gc_e2": {  # 3 × 3 = 9 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "rsi_len": [7, 14, 21],
        "rsi_exit_threshold": [40, 45, 50],
    },
    "gc_e3": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vol_mult": [1.5, 2.0, 2.5],
        "vol_ema_len": [20, 50],
    },
    "gc_e4": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "atr_buffer_mult": [0.5, 1.0, 1.5],
        "atr_period": [14, 20],
    },
    "gc_e5": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "accel_threshold": [0.1, 0.5, 1.0],
    },
    "gc_e6": {  # 3 × 3 = 9 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "atr_period": [7, 14, 20],
        "atr_mult": [2.0, 2.5, 3.0],
    },
    "gc_e7": {  # 2 × 3 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "curve_mode": ["A", "B"],
        "lookback": [5, 10, 20],
    },
    "gc_e8": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "rate_lookback": [20, 50, 100],
    },
    "gc_e9": {  # 2 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "sgov_lookback": [20, 50],
    },
    "gc_e10": {  # 2 × 2 × 3 = 12 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "atr_short": [7, 14],
        "atr_long": [50, 100],
        "vol_ratio_threshold": [1.5, 2.0, 2.5],
    },
    "gc_e11": {  # 4 × 3 = 12 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "dd_pct": [15.0, 20.0, 25.0, 30.0],
        "dd_lookback": [50, 100, 200],
    },
    "gc_e12": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "macd_exit_bars": [2, 3, 5],
    },
    "gc_e13": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "slope_exit_window": [5, 10, 20],
        "slope_threshold": [0.0, -0.001],
    },
    "gc_e14": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "bear_bars": [3, 5, 7],
    },
    "gc_e15": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "gap_down_pct": [3.0, 5.0, 8.0],
    },
    "gc_e16": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "ratio_lookback": [10, 20, 50],
        "ratio_ema": [20, 50],
    },
    "gc_e17": {  # 3 × 3 = 9 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "profit_lock_pct": [50.0, 100.0, 200.0],
        "tight_atr_mult": [1.0, 1.5, 2.0],
    },
    "gc_e18": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "max_bars": [200, 300, 500],
    },
    "gc_e19": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vix_ema_len": [20, 50, 100],
        "vix_above_pct": [10.0, 20.0],
    },
    "gc_n1": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "entry_vix_max": [20.0, 25.0, 30.0],
    },
    "gc_n2": {  # 3 × 3 = 9 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "adx_len": [7, 14, 20],
        "adx_threshold": [15.0, 20.0, 25.0],
    },
    "gc_n3": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "xlk_ema_len": [50, 100, 200],
    },
    "gc_n4": {  # 3 × 3 = 9 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "min_recovery_pct": [15.0, 20.0, 30.0],
        "crash_threshold": [30.0, 40.0, 50.0],
    },
    "gc_n5": {  # 1 combo (no new params)
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
    },
    "gc_n6": {  # 2 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "seasonal_months_off": ["May-Sep", "Jun-Sep"],
    },
    "gc_n7": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vol_entry_mult": [1.2, 1.5, 2.0],
        "vol_ema_len": [20, 50],
    },
    "gc_n8": {  # 1 combo (no new params)
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
    },
    "gc_n9": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "bb_len": [14, 20, 50],
        "squeeze_lookback": [50, 100],
    },
    "gc_n10": {  # 1 combo
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
    },
    "gc_n11": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vix_slope_window": [3, 5, 10],
    },
    "gc_n12": {  # 1 combo
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
    },
    "gc_n13": {  # 2 × 2 = 4 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "short_ret_lb": [10, 20],
        "med_ret_lb": [50, 100],
    },
    "gc_n14": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "high_proximity_pct": [85.0, 90.0, 95.0],
        "high_lookback": [50, 100],
    },
    "gc_s1": {  # 2 × 3 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "base_cooldown": [2, 5],
        "vol_cooldown_mult": [1.0, 2.0, 3.0],
    },
    "gc_s2": {  # 3 × 2 = 6 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "bear_memory_bars": [50, 100, 200],
        "bear_threshold_pct": [40.0, 50.0],
    },
    "gc_s3": {  # 3 combos
        "fast_ema": [100],
        "slow_ema": [200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vix_reentry_below": [20.0, 25.0, 30.0],
    },
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 1): addons on VJ (gc_n8) base ──
    # Base sweeps BOTH canonical 100/200 AND the 120/150 champion pair so each
    # overlay is tested against (a) strict-canonical VJ and (b) actual Velvet
    # Jaguar. _is_valid_combo keeps fast_ema < slow_ema; all 4 cross pairs valid.
    "gc_vjx": {  # 4 × 3 × 3 × 2 = 72 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "shock_look": [5, 10, 20],
        "shock_vix_roc": [1.3, 1.5, 2.0],
        "shock_price_drop": [5.0, 8.0],
    },
    "gc_vjxr": {  # 4 × 2 × 2 × 2 × 2 = 64 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "shock_look": [5, 10],
        "shock_drop": [10.0, 15.0],
        "rsi_bounce": [30.0, 35.0],
        "watch_bars": [20, 50],
        "rsi_len": [14],
        "bounce_ema": [50],
    },
    "gc_vjv": {  # 4 × 2 × 2 × 3 = 48 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "vol_short": [10, 20],
        "vol_long": [50, 100],
        "vol_entry_ratio": [0.8, 0.9, 1.0],
    },
    "gc_vjatr": {  # 4 × 3 × 2 × 3 × 2 = 144 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "atr_period": [7, 14, 20],
        "atr_look": [20, 50],
        "atr_expand": [1.5, 2.0, 2.5],
        "atr_confirm": [3, 5],
    },
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 2) ──
    "gc_vjrsi": {  # 4 × 2 × 2 × 3 = 48 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "rsi_len": [7, 14],
        "rsi_oversold": [25.0, 30.0],
        "rsi_bounce": [30.0, 35.0, 40.0],
        "rsi_trend_ema": [100],
    },
    "gc_vjsgov": {  # 4 × 3 × 2 = 24 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "rs_lookback": [20, 50, 100],
        "rs_persistence": [10, 20],
    },
    "gc_vjtimer": {  # 4 × 2 × 2 × 2 = 32 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "time_stop_bars": [100, 150],
        "below_ema": [100, 150],
        "below_persist": [5, 10],
    },
    "pullback_in_trend": {  # 3 × 2 × 3 × 2 × 2 = 72 combos (trend_len, pullback_look, pullback_pct, exit_ema, exit_persist)
        "trend_len": [100, 150, 200],
        "pullback_look": [20, 50],
        "pullback_pct": [10.0, 15.0, 20.0],
        "exit_ema": [30, 50],
        "exit_persist": [3, 5],
        "cooldown": [10],
    },
    # ── Velvet Jaguar Overlays 2026-04-20 (Round 3) ──
    "rsi_regime_canonical": {  # 2 × 3 × 3 × 2 × 1 = 36 combos
        "rsi_len": [7, 14],
        "trend_len": [50, 100, 200],
        "entry_rsi": [30.0, 35.0, 40.0],
        "exit_rsi": [70.0, 75.0],
        "panic_rsi": [15.0],
        "cooldown": [10],
    },
    "dual_tf_gc": {  # 2 × 2 × 2 × 2 × 2 = 32 combos (filtered fast<slow, outer_fast<outer_slow)
        "fast_ema": [30, 50],
        "slow_ema": [150, 200],
        "outer_fast": [100, 150],
        "outer_slow": [200, 300],
        "slope_window": [2, 3],
        "entry_bars": [2],
        "cooldown": [5],
    },
    "tecl_sgov_rs": {  # 3 × 2 × 2 × 2 = 24 combos
        "rs_look": [20, 50, 100],
        "rs_exit": [-5.0, -10.0],
        "trend_ema": [100, 200],
        "exit_ema": [30, 50],
        "cooldown": [5],
    },
    # ── Circuit breakers on VJ (Round 4, Bucket C) ──
    # Base fixed at actual VJ params (fast=120, slow=150).
    "gc_n8_ddbreaker": {  # 4 × 3 = 12 combos
        "fast_ema": [120],
        "slow_ema": [150],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "pause_dd_pct": [20.0, 25.0, 30.0, 40.0],
        "resume_dd_pct": [10.0, 15.0, 20.0],
    },
    "gc_n8_timelimit": {  # 3 × 3 = 9 combos
        "fast_ema": [120],
        "slow_ema": [150],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "max_hold": [300, 500, 750],
        "tl_ema": [100, 150, 200],
    },
    "gc_n8_panic_flat": {  # 3 × 2 × 3 = 18 combos
        "fast_ema": [120],
        "slow_ema": [150],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "panic_vix": [35.0, 40.0, 50.0],
        "panic_roc": [1.3, 1.5],
        "flat_bars": [5, 10, 20],
    },
    # ── Final batch 2026-04-20 (deferred A5/A7/A9 + B2/B3/B5/B6/B8/B10/B11/B12/B13/B16) ──
    "gc_vjmac": {  # 4 × 3 = 12 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "ff_lookback": [100, 150, 200],
    },
    "gc_vjbb": {  # 4 × 2 × 2 × 3 = 48 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "bb_len": [20, 50],
        "bb_mult": [2.0],
        "bb_width_look": [50, 100],
        "bb_pct": [20.0, 30.0, 40.0],
    },
    "gc_vjdd": {  # 4 × 3 = 12 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "dd_pct": [15.0, 20.0, 25.0],
    },
    "vol_regime_canonical": {  # 2 × 2 × 2 × 3 × 2 = 48 combos
        "vol_short": [10, 20],
        "vol_long": [50, 100],
        "trend_len": [100, 200],
        "vol_entry_ratio": [0.8, 0.9, 1.0],
        "vol_exit_ratio": [1.3, 1.5],
        "cooldown": [5],
    },
    "composite_osc_canonical": {  # 3 × 2 × 2 = 12 combos
        "tema_len": [100, 150, 200],
        "quick_len": [7, 14],
        "adx_len": [14, 20],
        "cooldown": [5],
    },
    "bounce_breakout": {  # 3 × 2 × 2 × 2 × 2 = 48 combos
        "entry_len": [50, 100, 150],
        "exit_len": [20, 50],
        "trend_len": [100, 200],
        "reclaim_ema": [30, 50],
        "watch_bars": [20, 50],
        "cooldown": [5],
    },
    "tri_filter_macd": {  # 2 × 2 × 2 × 2 × 2 = 32 combos
        "trend_len": [100, 200],
        "rsi_len": [7, 14],
        "rsi_entry_floor": [40.0, 45.0],
        "rsi_panic": [25.0, 30.0],
        "exit_confirm": [2, 3],
        "cooldown": [3],
    },
    "momentum_roc_canonical": {  # 3 × 2 × 2 × 2 = 24 combos
        "roc_len": [20, 50, 100],
        "trend_ema": [100, 200],
        "exit_ema": [30, 50],
        "panic_roc": [-5.0, -8.0],
        "cooldown": [5],
    },
    "adaptive_ema_vol": {  # 2 × 2 × 2 × 2 = 16 combos (vol bands fixed; slope-side fixed)
        "vix_low": [20.0],
        "vix_high": [30.0],
        "fast1": [50],
        "slow1": [200],
        "fast2": [30, 50],
        "slow2": [100, 150],
        "fast3": [20],
        "slow3": [50, 100],
        "dwell": [5, 10],
        "entry_bars": [2],
        "cooldown": [3],
    },
    "regime_state_machine": {  # 1 combo (structural — no tunables)
        "cooldown": [5],
    },
    "ensemble_vote_3of5": {  # 2 × 3 × 3 = 18 combos
        "trend_len": [100, 150, 200],
        "entry_vote": [2, 3, 4],
        "exit_vote": [-1, 0],
        "cooldown": [5],
    },
    "fed_macro_primary": {  # 3 × 2 × 2 × 2 = 24 combos
        "ff_long": [100, 150, 200],
        "ff_short": [20, 50],
        "ff_exit": [50, 100],
        "spread_floor": [-0.3, 0.0],
        "cooldown": [0],
    },
    "slope_only_200": {  # 2 × 2 = 4 combos
        "ema_len": [150, 200],
        "slope_look": [10, 20],
        "cooldown": [5],
    },
    # ── Next-Frontier 2026-04-20 (Lane 2: VJ cross-asset rescue) ──
    "gc_vj_decay_gate": {  # 4 × 2 × 3 = 24 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "decay_look": [20, 50],
        "decay_threshold": [-0.10, -0.05, 0.0],
    },
    "gc_vj_xlk_relative_trend": {  # 4 × 2 × 2 × 2 = 32 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "xlk_fast": [30, 50],
        "xlk_slow": [150, 200],
        "xlk_slope": [2, 3],
    },
    "gc_vj_dual_regime": {  # 4 × 2 × 2 = 16 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "reg_fast": [30, 50],
        "reg_slow": [150, 200],
    },
    # ── Next-Frontier 2026-04-20 (Lane 1: generalization-first) ──
    "rank_slope_regime": {  # 2 × 2 × 2 × 3 × 2 = 48 combos
        "trend_len": [100, 200],
        "slope_look": [10, 20],
        "rank_window": [100, 200],
        "entry_pct": [40.0, 50.0, 60.0],
        "exit_pct": [20.0, 30.0],
        "cooldown": [5],
    },
    "zscore_return_reversion": {  # 2 × 2 × 3 × 2 × 2 = 48 combos
        "ret_n": [10, 20],
        "window": [100, 200],
        "entry_z": [-2.0, -1.5, -1.0],
        "exit_z": [0.5, 1.0],
        "trend_len": [100, 200],
        "cooldown": [5],
    },
    # ── Next-Frontier 2026-04-20 (Lane 3: unused data) ──
    "breadth_decay_composite": {  # 2 × 2 × 3 × 3 = 36 combos
        "trend_len": [100, 200],
        "exit_ema": [30, 50],
        "breadth_look": [10, 20, 50],
        "narrow_threshold": [0.95, 1.00, 1.05],
        "cooldown": [5],
    },
    # ── Next-Frontier 2026-04-20 (Lane 4: meta + infrastructure) ──
    "vj_or_slope_meta": {  # 4 × 2 × 2 = 16 combos
        "fast_ema": [100, 120],
        "slow_ema": [150, 200],
        "slope_window": [3],
        "entry_bars": [2],
        "cooldown": [2],
        "slope_ema_len": [150, 200],
        "slope_look": [10, 20],
    },
}


def _grid_combos(grid: dict) -> list[dict]:
    """Expand a grid dict into all parameter combos (Cartesian product)."""
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _is_valid_combo(concept: str, params: dict) -> bool:
    """Reject obviously invalid combos (e.g., fast_ema >= slow_ema)."""
    fast = params.get("fast_ema") or params.get("short_ema")
    slow = params.get("slow_ema") or params.get("long_ema")
    if fast is not None and slow is not None and fast >= slow:
        return False
    # For triple stack: short < med < long
    short = params.get("short_ema")
    med = params.get("med_ema")
    long_ = params.get("long_ema")
    if short is not None and med is not None and long_ is not None:
        if not (short < med < long_):
            return False
    # For donchian: exit_len < entry_len
    entry = params.get("entry_len")
    exit_ = params.get("exit_len")
    if entry is not None and exit_ is not None and exit_ >= entry:
        return False
    # For ATR ratio: short < long
    atr_s = params.get("atr_short")
    atr_l = params.get("atr_long")
    if atr_s is not None and atr_l is not None and atr_s >= atr_l:
        return False
    # For BB width: bb_len < bb_avg_len
    bb = params.get("bb_len")
    bb_avg = params.get("bb_avg_len")
    if bb is not None and bb_avg is not None and bb >= bb_avg:
        return False
    # For XLK relative strength: xlk_fast < xlk_slow
    xlk_f = params.get("xlk_fast")
    xlk_s = params.get("xlk_slow")
    if xlk_f is not None and xlk_s is not None and xlk_f >= xlk_s:
        return False
    # For Keltner squeeze: kc_avg_len > kc_ema_len (averaging window wider than channel)
    kc_ema = params.get("kc_ema_len")
    kc_avg = params.get("kc_avg_len")
    if kc_ema is not None and kc_avg is not None and kc_avg <= kc_ema:
        return False
    # For asymmetric entry/exit pairs: entry_fast < entry_slow, exit_fast < exit_slow,
    # and entry_fast < exit_slow (faster entry than exit)
    ef = params.get("entry_fast")
    es = params.get("entry_slow")
    xf = params.get("exit_fast")
    xs = params.get("exit_slow")
    if ef is not None and es is not None and ef >= es:
        return False
    if xf is not None and xs is not None and xf >= xs:
        return False
    if ef is not None and xs is not None and ef >= xs:
        return False
    # For triple-pair asymmetric: entry_fast < entry_mid < exit_slow
    em = params.get("entry_mid")
    if ef is not None and em is not None and ef >= em:
        return False
    if em is not None and xs is not None and em >= xs:
        return False
    return True


# ── Multiprocessing worker infrastructure ──
# Each worker process gets its own copy of data + indicators (avoids pickling).
_worker_df = None
_worker_ind = None
_worker_close = None
_worker_dates = None


def _worker_init():
    """Per-process initializer — loads data once per worker."""
    global _worker_df, _worker_ind, _worker_close, _worker_dates
    _worker_df = get_tecl_data()
    _worker_ind = Indicators(_worker_df)
    _worker_close = _worker_df["close"].values.astype(np.float64)
    _worker_dates = _worker_df["date"].values


def _worker_backtest(job: tuple[str, dict]) -> dict | None:
    """Backtest a single (concept, params) combo in a worker process.

    Returns a result dict if the combo passes charter pre-filter, else None.
    """
    concept, params = job
    fn = STRATEGY_REGISTRY.get(concept)
    if fn is None:
        return None
    try:
        entries, exits, labels = fn(_worker_ind, params)
        result = backtest(
            _worker_df,
            entries,
            exits,
            labels,
            cooldown_bars=params.get("cooldown", 0),
            strategy_name=concept,
        )
        result.params = params
    except Exception:
        return None

    # Charter pre-filter — uses weighted-era fitness (2026-04-21 revision).
    # Previously required full share_multiple >= 1.0, which rewarded synthetic
    # dotcom sidestepping and produced strategies that failed on real data.
    # The new gate is `weighted_era_fitness >= 1.0` which requires combined
    # era performance to beat B&H. See scripts/search/fitness.py.
    from search.fitness import weighted_era_fitness as _wef

    _w = _wef(
        result.share_multiple, result.real_share_multiple, result.modern_share_multiple
    )
    if _w < 1.0:
        return {"_rejected": True}
    if result.num_trades < 5:
        return {"_rejected": True}
    if result.trades_per_year > 5.0:
        return {"_rejected": True}

    # Compute regime score + marker alignment
    result.regime_score = score_regime_capture(
        result.trades, _worker_close, _worker_dates
    )
    align = score_marker_alignment(_worker_df, result.trades)
    tier = STRATEGY_TIERS.get(concept, "T1")
    fit = compute_fitness(result, tier=tier)

    return {
        "strategy": concept,
        "rank": 0,
        "fitness": fit,
        "tier": tier,
        "params": params,
        "marker_alignment_score": align["score"],
        "marker_alignment_detail": align,
        "metrics": {
            "trades": result.num_trades,
            "trades_yr": result.trades_per_year,
            "n_params": _count_tunable_params(params),
            "share_multiple": result.share_multiple,
            "real_share_multiple": result.real_share_multiple,
            "modern_share_multiple": result.modern_share_multiple,
            "cagr": result.cagr_pct,
            "max_dd": result.max_drawdown_pct,
            "mar": result.mar_ratio,
            "regime_score": result.regime_score.composite if result.regime_score else 0,
            "hhi": (result.regime_score.hhi or 0) if result.regime_score else 0,
            "bull_capture": result.regime_score.bull_capture_ratio
            if result.regime_score
            else 0,
            "bear_avoidance": result.regime_score.bear_avoidance_ratio
            if result.regime_score
            else 0,
            "win_rate": result.win_rate_pct,
            "exit_reasons": result.exit_reasons,
        },
        "trades": [
            {
                "entry_bar": t.entry_bar,
                "exit_bar": t.exit_bar,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl_pct": t.pnl_pct,
                "bars_held": t.bars_held,
                "exit_reason": t.exit_reason,
            }
            for t in result.trades
        ],
    }


def _backtest_single(concept, params, ind, df, close, dates):
    """Single-thread backtest for small workloads (no pickling overhead)."""
    fn = STRATEGY_REGISTRY.get(concept)
    if fn is None:
        return None
    try:
        entries, exits, labels = fn(ind, params)
        result = backtest(
            df,
            entries,
            exits,
            labels,
            cooldown_bars=params.get("cooldown", 0),
            strategy_name=concept,
        )
        result.params = params
    except Exception:
        return None
    # Charter pre-filter — weighted-era fitness (2026-04-21 revision).
    from search.fitness import weighted_era_fitness as _wef

    _w = _wef(
        result.share_multiple, result.real_share_multiple, result.modern_share_multiple
    )
    if _w < 1.0:
        return {"_rejected": True}
    if result.num_trades < 5:
        return {"_rejected": True}
    if result.trades_per_year > 5.0:
        return {"_rejected": True}
    result.regime_score = score_regime_capture(result.trades, close, dates)
    align = score_marker_alignment(df, result.trades)
    tier = STRATEGY_TIERS.get(concept, "T1")
    fit = compute_fitness(result, tier=tier)
    return {
        "strategy": concept,
        "rank": 0,
        "fitness": fit,
        "tier": tier,
        "params": params,
        "marker_alignment_score": align["score"],
        "marker_alignment_detail": align,
        "metrics": {
            "trades": result.num_trades,
            "trades_yr": result.trades_per_year,
            "n_params": _count_tunable_params(params),
            "share_multiple": result.share_multiple,
            "real_share_multiple": result.real_share_multiple,
            "modern_share_multiple": result.modern_share_multiple,
            "cagr": result.cagr_pct,
            "max_dd": result.max_drawdown_pct,
            "mar": result.mar_ratio,
            "regime_score": result.regime_score.composite if result.regime_score else 0,
            "hhi": (result.regime_score.hhi or 0) if result.regime_score else 0,
            "bull_capture": result.regime_score.bull_capture_ratio
            if result.regime_score
            else 0,
            "bear_avoidance": result.regime_score.bear_avoidance_ratio
            if result.regime_score
            else 0,
            "win_rate": result.win_rate_pct,
            "exit_reasons": result.exit_reasons,
        },
        "trades": [
            {
                "entry_bar": t.entry_bar,
                "exit_bar": t.exit_bar,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl_pct": t.pnl_pct,
                "bars_held": t.bars_held,
                "exit_reason": t.exit_reason,
            }
            for t in result.trades
        ],
    }


def run_grid_search(
    concepts: list[str] | None = None,
    dry_run: bool = False,
    top_n: int = 20,
    validate: bool = True,
) -> dict:
    """Run exhaustive grid search over all (or specified) concepts.

    Returns dict with raw results + validated rankings + leaderboard state.
    """
    if concepts is None:
        concepts = list(GRIDS.keys())

    # Load data once (main process — for combo counting + post-search use)
    print("[grid] Loading TECL data...")
    df = get_tecl_data()
    ind = Indicators(df)
    close = df["close"].values.astype(np.float64)
    dates = df["date"].values
    print(f"[grid] {len(df)} bars, {len(concepts)} concepts")

    # Build flat job list: [(concept, params), ...]
    jobs = []
    for concept in concepts:
        fn = STRATEGY_REGISTRY.get(concept)
        if fn is None:
            print(f"  SKIP {concept}: not in STRATEGY_REGISTRY")
            continue
        grid = GRIDS.get(concept, {})
        combos = [c for c in _grid_combos(grid) if _is_valid_combo(concept, c)]
        print(f"  {concept:<28} {len(combos):>4} combos")
        for params in combos:
            jobs.append((concept, params))
    total_combos = len(jobs)
    print(f"  {'TOTAL':<28} {total_combos:>4} combos")

    if dry_run:
        print("\n[grid] Dry run — no backtests. Exiting.")
        return {"total_combos": total_combos}

    # ── Phase 1: Exhaustive backtest + pre-filter ──
    # For small job counts, single-thread is faster (avoids process spawn overhead).
    MULTICORE_THRESHOLD = 150
    start = time.time()
    all_results = []
    charter_rejects = 0

    if total_combos >= MULTICORE_THRESHOLD:
        n_workers = min(multiprocessing.cpu_count() - 1, total_combos // 10) or 1
        n_workers = max(2, min(n_workers, 12))
        print(f"\n[grid] Multicore: {n_workers} workers for {total_combos} combos...")
        with multiprocessing.Pool(
            processes=n_workers, initializer=_worker_init
        ) as pool:
            for result in pool.imap_unordered(_worker_backtest, jobs, chunksize=8):
                if result is None:
                    continue
                if result.get("_rejected"):
                    charter_rejects += 1
                    continue
                all_results.append(result)
    else:
        print(
            f"\n[grid] Single-core: {total_combos} combos (below multicore threshold)..."
        )
        for concept, params in jobs:
            result = _backtest_single(concept, params, ind, df, close, dates)
            if result is None:
                continue
            if result.get("_rejected"):
                charter_rejects += 1
                continue
            all_results.append(result)

    # Per-concept summary (fitness = weighted-era; share = full-history for context)
    concept_stats: dict[str, tuple[int, float, float]] = {}
    for e in all_results:
        c = e["strategy"]
        prev_count, prev_best_fit, prev_best_share = concept_stats.get(c, (0, 0.0, 0.0))
        concept_stats[c] = (
            prev_count + 1,
            max(prev_best_fit, e.get("fitness", 0)),
            max(prev_best_share, e["metrics"]["share_multiple"]),
        )
    for concept in concepts:
        count, best_fit, best_share = concept_stats.get(concept, (0, 0.0, 0.0))
        print(
            f"  {concept:<28} {count:>3} pass charter  best_fit={best_fit:.2f}  best_share={best_share:.2f}x"
        )

    elapsed_search = time.time() - start
    # Rank by fitness (weighted-era geometric mean of share multipliers —
    # 2026-04-21 revision). Previously ranked by raw full-history share_multiple,
    # which was dominated by the synthetic pre-2008 dotcom sidestep.
    all_results.sort(key=lambda e: e.get("fitness", 0), reverse=True)
    for i, e in enumerate(all_results, 1):
        e["rank"] = i

    print(
        f"\n[grid] Search done: {total_combos} combos → {len(all_results)} pass charter "
        f"({charter_rejects} rejected) in {elapsed_search:.1f}s"
    )

    if not all_results:
        print("[grid] No candidates passed charter pre-filter. Nothing to validate.")
        return {"total_combos": total_combos, "charter_pass": 0}

    # Show top 10 raw
    print("\n[grid] Top 10 raw (by weighted-era fitness):")
    for e in all_results[:10]:
        m = e["metrics"]
        print(
            f"  {e['strategy']:<28} fit={e.get('fitness', 0):.2f}  "
            f"full={m['share_multiple']:.2f}x  real={m.get('real_share_multiple', 0):.2f}x  "
            f"modern={m.get('modern_share_multiple', 0):.2f}x  trades={m['trades']}  "
            f"marker={e['marker_alignment_score']:.3f}"
        )

    if not validate:
        return {
            "total_combos": total_combos,
            "charter_pass": len(all_results),
            "raw_rankings": all_results[:top_n],
        }

    # ── Phase 2: Validate top-N through the pipeline ──
    # Ensure per-concept representation: best combo from each concept first,
    # then fill remaining slots with global best (by weighted-era fitness).
    seen_concepts = set()
    per_concept_best = []
    remaining = []
    for e in all_results:
        if e["strategy"] not in seen_concepts:
            per_concept_best.append(e)
            seen_concepts.add(e["strategy"])
        else:
            remaining.append(e)
    val_candidates = per_concept_best + remaining
    val_candidates = val_candidates[:top_n]
    n_concepts_repr = len(per_concept_best)
    print(
        f"\n[grid] Validating top {len(val_candidates)} candidates "
        f"({n_concepts_repr} concepts guaranteed a slot)..."
    )
    val_input = {"raw_rankings": val_candidates}
    validation = run_validation_pipeline(
        val_input, hours=0.05, quick=True, top_n=len(val_candidates)
    )

    summary = validation["validation_summary"]
    print(
        f"\n[grid] Validation: PASS={summary['validated_pass']}  "
        f"WARN={summary['validated_warn']}  FAIL={summary['validated_fail']}"
    )

    # ── Phase 3: Update leaderboard ──
    # Feed all validated rankings into the canonical admission path. It alone
    # decides whether a row is authoritative enough for leaderboard persistence.
    lb_path = os.path.join(PROJECT_ROOT, "spike", "leaderboard.json")
    admit_candidates = validation.get("raw_rankings", [])
    if admit_candidates:
        lb = update_leaderboard(
            {
                "rankings": admit_candidates,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_evaluations": total_combos,
                "elapsed_hours": elapsed_search / 3600,
            },
            lb_path,
        )
        print(f"\n[grid] Leaderboard updated: {len(lb)} entries")
        for i, e in enumerate(lb[:20], 1):
            m = e.get("metrics", {})
            v = e.get("validation") or {}
            t = v.get("tier") or e.get("tier") or "?"
            c = float(v.get("composite_confidence") or 0.0) * 100.0
            label = "ADMIT" if c >= 70 else "WATCH" if c >= 60 else "—"
            print(
                f"  #{i} {e['strategy']:<28} [{t}] conf={c:5.1f}[{label}] "
                f"share={m.get('share_multiple', 0):.2f}x  params={e.get('params', {})}"
            )
    else:
        print("[grid] No validated candidates produced authority-eligible rows.")

    return {
        "total_combos": total_combos,
        "charter_pass": len(all_results),
        "raw_rankings": all_results[:top_n],
        "validation": validation,
        "leaderboard_entries": len(admit_candidates),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Grid Search — exhaustive canonical param testing"
    )
    parser.add_argument(
        "--concepts",
        type=str,
        default=None,
        help="Comma-separated concept names (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Just show combo counts, don't backtest"
    )
    parser.add_argument(
        "--top-n", type=int, default=20, help="Validate top N candidates (default: 20)"
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation (just pre-test)"
    )
    args = parser.parse_args()

    concepts = args.concepts.split(",") if args.concepts else None
    run_grid_search(
        concepts=concepts,
        dry_run=args.dry_run,
        top_n=args.top_n,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()

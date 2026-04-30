#!/usr/bin/env python3
"""Assemble the Montauk visualization HTML.

Reads:
  - data/TECL.csv         (price + provenance columns, vix_close)
  - data/manifest.json    (provenance hash + build timestamp)
  - data/markers/TECL-markers.csv  (north-star buy/sell markers)
  - spike/leaderboard.json (top-20 strategy entries)
  - spike/runs/*/dashboard_data.json  (per-strategy artifacts; matched to leaderboard
                                      entries by strategy + params)

Writes:
  - viz/montauk-viz.html  (fully self-contained; embeds Lightweight Charts +
                          all data via window.__MONTAUK_DATA__)

Behavior:
  - Never re-runs any backtest. Reads precomputed artifacts only.
  - If no run dir matches a leaderboard entry, embeds metadata only and
    flags the entry as `stale`.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from typing import Any

import numpy as np
import pandas as pd

VIZ_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(VIZ_DIR)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from certify.contract import compute_gold_status, sync_validation_contract
from engine.strategy_engine import Indicators, _sma
from search.share_metric import read_share_multiple

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SPIKE_DIR = os.path.join(PROJECT_ROOT, "spike")
TEMPLATE_DIR = os.path.join(VIZ_DIR, "templates")

LEADERBOARD_PATH = os.path.join(SPIKE_DIR, "leaderboard.json")
FAMILY_CONFIDENCE_PATH = os.path.join(PROJECT_ROOT, "runs", "family_confidence_leaderboard.json")
RUNS_DIR = os.path.join(SPIKE_DIR, "runs")
TECL_CSV = os.path.join(DATA_DIR, "TECL.csv")
MARKERS_CSV = os.path.join(DATA_DIR, "markers", "TECL-markers.csv")
MANIFEST_JSON = os.path.join(DATA_DIR, "manifest.json")
LIB_JS = os.path.join(VIZ_DIR, "lightweight-charts.js")
SHELL_HTML = os.path.join(TEMPLATE_DIR, "shell.html")
APP_JS = os.path.join(TEMPLATE_DIR, "app.js")
OUTPUT_HTML = os.path.join(VIZ_DIR, "montauk-viz.html")


# --------------------------------------------------------------------------- #
# Data loaders
# --------------------------------------------------------------------------- #

def _safe_float(x: str) -> float | None:
    try:
        if x == "" or x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def load_tecl() -> dict[str, Any]:
    """Read TECL.csv and return arrays plus synthetic_end_index."""
    dates: list[str] = []
    o, h, l, c, v, vix = [], [], [], [], [], []
    is_synthetic: list[bool] = []
    synthetic_end_index = -1

    with open(TECL_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            dates.append(row["date"])
            o.append(_safe_float(row.get("open", "")))
            h.append(_safe_float(row.get("high", "")))
            l.append(_safe_float(row.get("low", "")))
            c.append(_safe_float(row.get("close", "")))
            v.append(_safe_float(row.get("volume", "")) or 0.0)
            vix.append(_safe_float(row.get("vix_close", "")))
            synth = (row.get("is_synthetic", "False") == "True")
            is_synthetic.append(synth)
            if synth:
                synthetic_end_index = i

    return {
        "dates": dates,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "vix": vix,
        "is_synthetic": is_synthetic,
        "synthetic_end_index": synthetic_end_index,
    }


def load_manifest() -> dict[str, Any]:
    if not os.path.exists(MANIFEST_JSON):
        return {}
    with open(MANIFEST_JSON) as f:
        m = json.load(f)
    tecl = (m.get("files") or {}).get("TECL.csv") or {}
    return {
        "sha256": tecl.get("sha256"),
        "built_utc": tecl.get("built_utc"),
        "rows": tecl.get("rows"),
        "seam_date": tecl.get("seam_date"),
    }


def load_north_star_markers() -> list[dict[str, Any]]:
    if not os.path.exists(MARKERS_CSV):
        return []
    out = []
    with open(MARKERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            out.append({
                "date": row["date"],
                "price": _safe_float(row.get("price", "")),
                "type": (row.get("type") or "").strip().lower(),
            })
    return out


def _json_float(value: Any, ndigits: int = 4) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    return round(v, ndigits)


def _shift(arr: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    if n <= 0:
        return arr.astype(np.float64)
    out[n:] = arr[:-n]
    return out


def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    for i in range(window - 1, len(arr)):
        values = arr[i - window + 1:i + 1]
        values = values[np.isfinite(values)]
        if len(values) >= max(5, window // 4):
            out[i] = np.std(values, ddof=0)
    return out


def _rolling_max(arr: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    for i in range(window - 1, len(arr)):
        values = arr[i - window + 1:i + 1]
        values = values[np.isfinite(values)]
        if len(values):
            out[i] = np.max(values)
    return out


def _pct_change(arr: np.ndarray, lookback: int) -> np.ndarray:
    prev = _shift(arr, lookback)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(prev > 0, arr / prev - 1.0, np.nan)


def _rolling_percentile(arr: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    for i in range(window - 1, len(arr)):
        value = arr[i]
        if not np.isfinite(value):
            continue
        values = arr[i - window + 1:i + 1]
        values = values[np.isfinite(values)]
        if len(values) < max(20, window // 5):
            continue
        out[i] = float(np.mean(values <= value))
    return out


def _efficiency_ratio(arr: np.ndarray, lookback: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    diffs = np.abs(np.diff(arr, prepend=np.nan))
    for i in range(lookback, len(arr)):
        if not np.isfinite(arr[i]) or not np.isfinite(arr[i - lookback]):
            continue
        path = diffs[i - lookback + 1:i + 1]
        path = path[np.isfinite(path)]
        path_sum = np.sum(path)
        if path_sum > 0:
            out[i] = abs(arr[i] - arr[i - lookback]) / path_sum
    return out


def _ewma(arr: np.ndarray, half_life: float) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=np.float64)
    alpha = 1.0 - np.exp(np.log(0.5) / half_life)
    last = np.nan
    for i, value in enumerate(arr):
        if not np.isfinite(value):
            if np.isfinite(last):
                out[i] = last
            continue
        last = value if not np.isfinite(last) else alpha * value + (1 - alpha) * last
        out[i] = last
    return out


def _signed_score(value: np.ndarray, scale: float) -> np.ndarray:
    return 50.0 + 50.0 * np.tanh(value / scale)


def _inverse_percentile_score(percentile: np.ndarray) -> np.ndarray:
    return 100.0 * (1.0 - np.clip(percentile, 0.0, 1.0))


def _weighted_geo_score(items: list[tuple[np.ndarray, float]], n: int) -> np.ndarray:
    total = np.zeros(n, dtype=np.float64)
    weights = np.zeros(n, dtype=np.float64)
    for values, weight in items:
        mask = np.isfinite(values)
        clipped = np.clip(values[mask], 1.0, 100.0) / 100.0
        total[mask] += np.log(clipped) * weight
        weights[mask] += weight
    out = np.full(n, np.nan, dtype=np.float64)
    mask = weights > 0
    out[mask] = np.exp(total[mask] / weights[mask]) * 100.0
    return out


def _weighted_arith_score(items: list[tuple[np.ndarray, float]], n: int) -> np.ndarray:
    total = np.zeros(n, dtype=np.float64)
    weights = np.zeros(n, dtype=np.float64)
    for values, weight in items:
        mask = np.isfinite(values)
        total[mask] += np.clip(values[mask], 0.0, 100.0) * weight
        weights[mask] += weight
    out = np.full(n, np.nan, dtype=np.float64)
    mask = weights > 0
    out[mask] = total[mask] / weights[mask]
    return out


def _read_close_by_date(filename: str) -> dict[str, float]:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    out: dict[str, float] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = _safe_float(row.get("close", ""))
            if value is not None:
                out[row["date"]] = value
    return out


def _aligned_close(dates: list[str], filename: str) -> np.ndarray:
    by_date = _read_close_by_date(filename)
    return np.asarray([by_date.get(date, np.nan) for date in dates], dtype=np.float64)


def compute_tecl_health(tecl: dict[str, Any]) -> dict[str, Any]:
    """Compute diagnostic-only TECL Health.

    This evolves the legacy composite oscillator into a layered 0-100 health
    model. It remains deliberately non-authoritative: no buy/sell signals, no
    certification effect, and no leaderboard ranking effect.
    """

    settings = {
        "model": "tecl-health-v3-calibrated-diagnostic",
        "layer_weights": {"structure": 0.25, "momentum": 0.35, "stress": 0.20, "participation": 0.20},
        "calibration": {
            "geometric_core_weight": 0.65,
            "arithmetic_core_weight": 0.35,
            "recovery_credit_weight": 0.20,
            "stress_cap_floor": 55.0,
            "stress_cap_multiplier": 0.85,
            "stress_cap_recovery_share": 0.50,
            "basis": "marker-cycle directional fit, named-regime separation, and crash compression",
        },
        "averaging": {"fast_ewma_half_life_days": 5, "slow_ewma_half_life_days": 63},
        "stress_cap": "final score capped at 55 + 0.85 * stress score + 0.5 * recovery credit",
        "legacy_inputs": {
            "tema_length": 300,
            "tema_slope_lookback": 2,
            "tema_slope_threshold_pct": 0.30,
            "quick_ema_length": 7,
            "quick_ema_slope_lookback": 5,
            "quick_ema_slope_threshold_pct": -0.15,
            "macd_fast": 30,
            "macd_slow": 180,
            "macd_signal": 20,
            "macd_hist_threshold": 0.03,
            "dmi_length": 60,
            "dmi_scale": 0.18,
        },
    }

    dates = tecl.get("dates") or []
    if not dates:
        return {"settings": settings, "bands": {}, "series": [], "latest": {}}

    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": tecl.get("open") or [],
        "high": tecl.get("high") or [],
        "low": tecl.get("low") or [],
        "close": tecl.get("close") or [],
        "volume": tecl.get("volume") or [],
    })
    ind = Indicators(df)
    close = ind.close
    high = ind.high
    low = ind.low
    vix = np.asarray(tecl.get("vix") or [np.nan] * len(dates), dtype=np.float64)
    n = len(close)
    legacy = settings["legacy_inputs"]

    tema = ind.tema(legacy["tema_length"])
    tema_prev = _shift(tema, legacy["tema_slope_lookback"])
    with np.errstate(divide="ignore", invalid="ignore"):
        tema_slope_pct = np.where(tema != 0, (tema - tema_prev) / tema, np.nan)
        norm_tema = np.tanh(tema_slope_pct / (legacy["tema_slope_threshold_pct"] * 0.01))

    quick = ind.ema(legacy["quick_ema_length"])
    quick_prev = _shift(quick, legacy["quick_ema_slope_lookback"])
    quick_slope = (quick - quick_prev) / legacy["quick_ema_slope_lookback"]
    norm_quick = np.tanh(quick_slope / abs(legacy["quick_ema_slope_threshold_pct"] * 0.01))

    macd_hist = ind.macd_hist(
        legacy["macd_fast"],
        legacy["macd_slow"],
        legacy["macd_signal"],
    )
    norm_macd = np.tanh(macd_hist / legacy["macd_hist_threshold"])

    plus_di = ind.di_plus(legacy["dmi_length"])
    minus_di = ind.di_minus(legacy["dmi_length"])
    with np.errstate(divide="ignore", invalid="ignore"):
        dmi_raw = (plus_di - minus_di) / np.maximum(plus_di + minus_di, 0.0001)
        norm_dmi = np.tanh(dmi_raw / legacy["dmi_scale"])

    ma50 = _sma(close, 50)
    ma100 = _sma(close, 100)
    ma200 = _sma(close, 200)
    with np.errstate(divide="ignore", invalid="ignore"):
        price_vs_200 = np.where(ma200 > 0, close / ma200 - 1.0, np.nan)
        slope50 = np.where(_shift(ma50, 20) > 0, ma50 / _shift(ma50, 20) - 1.0, np.nan)
        slope200 = np.where(_shift(ma200, 20) > 0, ma200 / _shift(ma200, 20) - 1.0, np.nan)
        distance_50 = np.where(ma50 > 0, close / ma50 - 1.0, np.nan)

    er63 = _efficiency_ratio(close, 63)
    structure_score = _weighted_geo_score([
        (_signed_score(price_vs_200, 0.12), 0.30),
        (_signed_score(slope50, 0.035), 0.20),
        (_signed_score(slope200, 0.025), 0.15),
        (50.0 + 50.0 * norm_dmi, 0.20),
        (np.clip(er63, 0.0, 1.0) * 100.0, 0.15),
    ], n)

    ret21 = _pct_change(close, 21)
    ret63 = _pct_change(close, 63)
    ret126 = _pct_change(close, 126)
    ret252 = _pct_change(close, 252)
    extension_balance = 100.0 - 40.0 * np.abs(np.tanh(distance_50 / 0.45))
    momentum_score = _weighted_geo_score([
        (_signed_score(ret21, 0.12), 0.18),
        (_signed_score(ret63, 0.25), 0.22),
        (_signed_score(ret126, 0.45), 0.16),
        (_signed_score(ret252, 0.70), 0.12),
        (50.0 + 50.0 * norm_quick, 0.14),
        (50.0 + 50.0 * norm_macd, 0.14),
        (extension_balance, 0.04),
    ], n)

    log_ret = np.diff(np.log(close), prepend=np.nan)
    rv20 = _rolling_std(log_ret, 20) * np.sqrt(252.0)
    rv60 = _rolling_std(log_ret, 60) * np.sqrt(252.0)
    atr20 = ind.atr(20)
    with np.errstate(divide="ignore", invalid="ignore"):
        atr_pct = np.where(close > 0, atr20 / close, np.nan)
        high_252 = _rolling_max(high, 252)
        drawdown_252 = np.where(high_252 > 0, close / high_252 - 1.0, np.nan)
        vix_ret10 = _pct_change(vix, 10)

    rv_score = _inverse_percentile_score(_rolling_percentile(rv20, 756))
    atr_score = _inverse_percentile_score(_rolling_percentile(atr_pct, 756))
    vix_level_score = _inverse_percentile_score(_rolling_percentile(vix, 756))
    vix_change_score = _signed_score(-vix_ret10, 0.20)
    drawdown_score = np.clip(100.0 * (1.0 + drawdown_252 / 0.45), 0.0, 100.0)
    stress_score = _weighted_geo_score([
        (rv_score, 0.25),
        (atr_score, 0.20),
        (vix_level_score, 0.20),
        (vix_change_score, 0.15),
        (drawdown_score, 0.20),
    ], n)

    qqq = _aligned_close(dates, "QQQ.csv")
    xlk = _aligned_close(dates, "XLK.csv")
    qqq_ma200 = _sma(qqq, 200)
    xlk_ma200 = _sma(xlk, 200)
    with np.errstate(divide="ignore", invalid="ignore"):
        qqq_vs_200 = np.where(qqq_ma200 > 0, qqq / qqq_ma200 - 1.0, np.nan)
        xlk_vs_200 = np.where(xlk_ma200 > 0, xlk / xlk_ma200 - 1.0, np.nan)
        qqq_ret63 = _pct_change(qqq, 63)
        xlk_ret63 = _pct_change(xlk, 63)
        tecl_ret63 = _pct_change(close, 63)
        xlk_vs_qqq_63 = xlk_ret63 - qqq_ret63
        tecl_vs_qqq_63 = tecl_ret63 - qqq_ret63

    participation_score = _weighted_geo_score([
        (_signed_score(qqq_vs_200, 0.10), 0.30),
        (_signed_score(xlk_vs_200, 0.10), 0.25),
        (_signed_score(qqq_ret63, 0.18), 0.20),
        (_signed_score(xlk_vs_qqq_63, 0.08), 0.15),
        (_signed_score(tecl_vs_qqq_63, 0.20), 0.10),
    ], n)

    layer_weights = settings["layer_weights"]
    layer_items = [
        (structure_score, layer_weights["structure"]),
        (momentum_score, layer_weights["momentum"]),
        (stress_score, layer_weights["stress"]),
        (participation_score, layer_weights["participation"]),
    ]
    calibration = settings["calibration"]
    geo_core = _weighted_geo_score(layer_items, n)
    arith_core = _weighted_arith_score(layer_items, n)
    core_score = (
        calibration["geometric_core_weight"] * geo_core
        + calibration["arithmetic_core_weight"] * arith_core
    )
    recovery_credit = (
        np.maximum(0.0, np.minimum(momentum_score, participation_score) - stress_score)
        * calibration["recovery_credit_weight"]
    )
    stress_cap = (
        calibration["stress_cap_floor"]
        + calibration["stress_cap_multiplier"] * stress_score
        + calibration["stress_cap_recovery_share"] * recovery_credit
    )
    final_score = np.minimum(
        core_score + recovery_credit,
        np.where(np.isfinite(stress_cap), stress_cap, 100.0),
    )
    final_score = np.clip(final_score, 0.0, 100.0)
    fast = _ewma(final_score, settings["averaging"]["fast_ewma_half_life_days"])
    slow = _ewma(final_score, settings["averaging"]["slow_ewma_half_life_days"])

    layer_arrays = [structure_score, momentum_score, stress_score, participation_score]
    layer_stack = np.vstack(layer_arrays)
    valid_counts = np.sum(np.isfinite(layer_stack), axis=0)
    dispersion = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        values = layer_stack[:, i]
        values = values[np.isfinite(values)]
        if len(values):
            dispersion[i] = np.std(values, ddof=0)
    coverage = valid_counts / len(layer_arrays)
    confidence = np.clip((100.0 - 1.7 * dispersion) * coverage, 0.0, 100.0)

    series = []
    for i, date in enumerate(dates):
        series.append({
            "date": date,
            "composite": _json_float(final_score[i], 2),
            "smooth": _json_float(fast[i], 2),
            "cross": _json_float(slow[i], 2),
            "layers": {
                "structure": _json_float(structure_score[i], 2),
                "momentum": _json_float(momentum_score[i], 2),
                "stress": _json_float(stress_score[i], 2),
                "participation": _json_float(participation_score[i], 2),
            },
            "confidence": _json_float(confidence[i], 2),
        })

    latest_idx = len(dates) - 1
    latest_score = final_score[latest_idx]
    latest_conflict = dispersion[latest_idx]
    if latest_score >= 75 and latest_conflict < 25:
        status = "healthy"
    elif latest_score >= 60:
        status = "constructive"
    elif latest_conflict >= 25:
        status = "mixed"
    elif latest_score >= 40:
        status = "fragile"
    else:
        status = "stressed"
    latest = {
        "date": dates[latest_idx],
        "close": _json_float(close[latest_idx], 2),
        "composite": _json_float(final_score[latest_idx], 2),
        "smooth": _json_float(fast[latest_idx], 2),
        "cross": _json_float(slow[latest_idx], 2),
        "status": status,
        "confidence": _json_float(confidence[latest_idx], 1),
        "conflict": _json_float(latest_conflict, 1),
        "layers": {
            "structure": _json_float(structure_score[latest_idx], 1),
            "momentum": _json_float(momentum_score[latest_idx], 1),
            "stress": _json_float(stress_score[latest_idx], 1),
            "participation": _json_float(participation_score[latest_idx], 1),
        },
        "components": {
            "price_vs_200": _json_float(price_vs_200[latest_idx] * 100.0, 1),
            "ma50_slope_20d": _json_float(slope50[latest_idx] * 100.0, 1),
            "trend_efficiency": _json_float(er63[latest_idx] * 100.0, 1),
            "quick_ema": _json_float(50.0 + 50.0 * norm_quick[latest_idx], 1),
            "macd_hist": _json_float(50.0 + 50.0 * norm_macd[latest_idx], 1),
            "realized_vol_pctile": _json_float(_rolling_percentile(rv20, 756)[latest_idx] * 100.0, 1),
            "vix_pctile": _json_float(_rolling_percentile(vix, 756)[latest_idx] * 100.0, 1),
            "drawdown_252": _json_float(drawdown_252[latest_idx] * 100.0, 1),
            "qqq_trend": _json_float(_signed_score(qqq_vs_200, 0.10)[latest_idx], 1),
            "xlk_vs_qqq_63d": _json_float(xlk_vs_qqq_63[latest_idx] * 100.0, 1),
            "recovery_credit": _json_float(recovery_credit[latest_idx], 1),
        },
    }

    return {
        "source": "Layered diagnostic evolved from legacy Montauk Composite Oscillator 1.3",
        "diagnostic_only": True,
        "settings": settings,
        "bands": {
            "healthy": 75,
            "constructive": 60,
            "mixed": 40,
            "stressed": 0,
        },
        "series": series,
        "latest": latest,
    }


def load_leaderboard() -> list[dict[str, Any]]:
    if not os.path.exists(LEADERBOARD_PATH):
        print(f"[build_viz] WARNING: leaderboard not found at {LEADERBOARD_PATH}")
        return []
    with open(LEADERBOARD_PATH) as f:
        d = json.load(f)
    if not isinstance(d, list):
        print("[build_viz] WARNING: leaderboard.json is not a list; skipping")
        return []
    return d


def load_family_confidence() -> dict[str, Any] | None:
    if not os.path.exists(FAMILY_CONFIDENCE_PATH):
        print(f"[build_viz] Family confidence report not found at {FAMILY_CONFIDENCE_PATH}")
        return None
    try:
        with open(FAMILY_CONFIDENCE_PATH) as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[build_viz] WARNING: failed to load family confidence report: {exc}")
        return None
    if not isinstance(data, dict):
        print("[build_viz] WARNING: family confidence report is not an object; skipping")
        return None
    return data


def index_run_artifacts() -> dict[tuple[str, str], dict[str, Any]]:
    """Index every spike/runs/*/dashboard_data.json by (strategy_name, params_key).

    Returns a dict mapping (strategy, params_key) -> {path, payload, mtime}.
    Newer runs win when keys collide.
    """
    if not os.path.isdir(RUNS_DIR):
        return {}

    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in sorted(os.listdir(RUNS_DIR)):
        run_path = os.path.join(RUNS_DIR, entry, "dashboard_data.json")
        if not os.path.exists(run_path):
            continue
        try:
            with open(run_path) as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[build_viz] skipping {run_path}: {exc}")
            continue

        strat = payload.get("strategy")
        params = payload.get("params") or {}
        if not strat:
            continue
        key = (strat, params_key(params))
        mtime = os.path.getmtime(run_path)
        prev = index.get(key)
        if prev is None or mtime > prev["mtime"]:
            index[key] = {"path": run_path, "payload": payload, "mtime": mtime}
    return index


def params_key(params: dict[str, Any]) -> str:
    """Stable string key for a params dict."""
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


# --------------------------------------------------------------------------- #
# Recent scorecards (compute from equity_curve)
# --------------------------------------------------------------------------- #

def compute_recent_scorecards(equity_curve: list[dict[str, Any]],
                              trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute 1Y/3Y/5Y diagnostic scorecards from the equity curve."""
    if not equity_curve:
        return {}

    # Index curve by date for fast lookup
    curve_dates = [p["date"] for p in equity_curve]
    last_date_str = curve_dates[-1]
    try:
        last_date = dt.date.fromisoformat(last_date_str)
    except ValueError:
        return {}

    out: dict[str, dict[str, Any]] = {}
    for label, years in (("1y", 1), ("3y", 3), ("5y", 5)):
        cutoff = last_date.replace(year=last_date.year - years)
        # find index of first curve date >= cutoff
        start_idx = None
        for i, d in enumerate(curve_dates):
            if d >= cutoff.isoformat():
                start_idx = i
                break
        if start_idx is None or start_idx >= len(equity_curve) - 1:
            out[label] = {"share_multiple": None, "max_dd": None, "trades": 0}
            continue

        start = equity_curve[start_idx]
        end = equity_curve[-1]

        # Share-multiple proxy: (strategy_growth) / (bah_growth) over the window
        s_start = start.get("equity") or 0.0
        s_end = end.get("equity") or 0.0
        b_start = start.get("bah_equity") or 0.0
        b_end = end.get("bah_equity") or 0.0
        share_mult: float | None = None
        if s_start > 0 and b_start > 0 and b_end > 0:
            strat_g = s_end / s_start
            bah_g = b_end / b_start
            share_mult = strat_g / bah_g if bah_g else None

        # Max drawdown over window (drawdown_pct already absolute; recompute peak-to-trough)
        peak = -float("inf")
        max_dd = 0.0
        for p in equity_curve[start_idx:]:
            eq = p.get("equity") or 0.0
            if eq > peak:
                peak = eq
            if peak > 0:
                dd = (peak - eq) / peak * 100.0
                if dd > max_dd:
                    max_dd = dd

        # Trade count in window (use entry_date)
        cutoff_iso = cutoff.isoformat()
        n_trades = sum(
            1 for t in (trades or [])
            if (t.get("entry_date") or "") >= cutoff_iso
        )

        out[label] = {
            "share_multiple": round(share_mult, 3) if share_mult is not None else None,
            "max_dd": round(max_dd, 1),
            "trades": n_trades,
        }
    return out


# --------------------------------------------------------------------------- #
# Validation summary flattening
# --------------------------------------------------------------------------- #

def flatten_gates(validation: dict[str, Any]) -> dict[str, str]:
    """Pull a flat gate→verdict map from the validation block."""
    if not validation:
        return {}
    gates = validation.get("gates") or {}
    flat: dict[str, str] = {}
    for k, v in gates.items():
        if isinstance(v, dict):
            flat[k] = v.get("verdict", "—")
        else:
            flat[k] = str(v)
    # certification_checks → also surface as gates
    certs = validation.get("certification_checks") or {}
    for k, v in certs.items():
        verdict = "PASS" if (isinstance(v, dict) and v.get("passed")) else (
            "FAIL" if isinstance(v, dict) and v.get("status") == "fail" else
            (v.get("status", "—").upper() if isinstance(v, dict) else "—")
        )
        flat[f"cert.{k}"] = verdict
    return flat


# --------------------------------------------------------------------------- #
# Strategy bundle assembly
# --------------------------------------------------------------------------- #

def build_strategy_entry(rank: int,
                         entry: dict[str, Any],
                         run: dict[str, Any] | None) -> dict[str, Any]:
    """Build one strategy bundle entry from a leaderboard row + matching run."""
    codename = entry.get("strategy", "?")
    name = entry.get("display_name") or codename
    params = entry.get("params") or {}
    base_metrics = entry.get("metrics") or {}

    share_multiple = read_share_multiple(base_metrics)

    # Marker alignment: top-level field on leaderboard
    marker_alignment = entry.get("marker_alignment_score")

    metrics = {
        "share_multiple": share_multiple,
        "real_share_multiple": base_metrics.get("real_share_multiple"),
        "modern_share_multiple": base_metrics.get("modern_share_multiple"),
        "cagr": base_metrics.get("cagr"),
        "max_dd": base_metrics.get("max_dd"),
        "mar": base_metrics.get("mar"),
        "trades": base_metrics.get("trades"),
        "trades_yr": base_metrics.get("trades_yr"),
        "win_rate": base_metrics.get("win_rate"),
        "regime_score": base_metrics.get("regime_score"),
        "bull_capture": base_metrics.get("bull_capture"),
        "bear_avoidance": base_metrics.get("bear_avoidance"),
        "marker_alignment": marker_alignment,
        "hhi": base_metrics.get("hhi"),
    }

    entry_validation = entry.get("validation")
    validation = (
        sync_validation_contract(entry_validation) if entry_validation else {}
    )
    backtest_certified = bool(validation.get("backtest_certified"))
    certified_not_overfit = bool(validation.get("certified_not_overfit"))
    promotion_ready = bool(validation.get("promotion_ready"))
    gold = compute_gold_status(validation, base_metrics)
    gold_status = bool(entry.get("gold_status") or gold.get("gold_status"))
    tier = entry.get("tier") or validation.get("tier") or "T0"

    out: dict[str, Any] = {
        "id": f"s{rank:02d}",
        "rank": rank,
        "name": name,
        "display_name_base": entry.get("display_name_base") or name,
        "codename": codename,
        "family_rank": entry.get("family_rank"),
        "family_size": entry.get("family_size"),
        "family_leader": bool(entry.get("family_leader", False)),
        "family_concentration": entry.get("family_concentration"),
        "fitness": entry.get("fitness"),
        "overall_performance_score": entry.get("overall_performance_score"),
        "composite_confidence": validation.get("composite_confidence"),
        "tier": tier,
        "certified_not_overfit": certified_not_overfit,
        "backtest_certified": backtest_certified,
        "promotion_ready": promotion_ready,
        "gold_status": gold_status,
        "gold_status_label": "Gold Status" if gold_status else "Not Gold",
        "all_eras_beat_bh": bool(gold.get("all_eras_beat_bh")),
        "gold_status_blockers": gold.get("gold_status_blockers", []),
        "params": params,
        "metrics": metrics,
        "multi_era": entry.get("multi_era"),
        "manually_admitted": bool(entry.get("manually_admitted")),
        "manual_admission": entry.get("manual_admission"),
        "validation_summary": flatten_gates(validation),
        "trades": [],
        "equity_curve": [],
        "recent_scorecards": {},
        "stale": run is None,
    }

    if run is None:
        return out

    payload = run["payload"]
    out["run_path"] = os.path.relpath(run["path"], PROJECT_ROOT)
    out["trades"] = payload.get("trade_ledger") or []

    # Equity curve — strip drawdown_pct + drawdown_curve (panel removed 2026-04-21)
    eq = []
    for p in payload.get("equity_curve") or []:
        eq.append({
            "date": p["date"],
            "equity": p.get("equity"),
            "bah_equity": p.get("bah_equity"),
        })
    out["equity_curve"] = eq

    # Recent scorecards (1Y/3Y/5Y)
    out["recent_scorecards"] = compute_recent_scorecards(eq, out["trades"])

    # If the run has richer metric values than leaderboard, prefer them
    run_metrics = payload.get("metrics") or {}
    for k in ("share_multiple", "cagr", "max_dd", "mar", "trades", "trades_yr",
              "win_rate", "regime_score", "bull_capture", "bear_avoidance", "hhi"):
        v = run_metrics.get(k)
        if v is not None and out["metrics"].get(k) is None:
            out["metrics"][k] = v

    # If the run carries a richer validation block, fold it in
    payload_validation = payload.get("validation")
    run_validation = (
        sync_validation_contract(payload_validation) if payload_validation else {}
    )
    if run_validation:
        run_gates = flatten_gates(run_validation)
        if run_gates:
            out["validation_summary"] = run_gates
        if run_validation.get("tier"):
            out["tier"] = run_validation["tier"]

    return out


# --------------------------------------------------------------------------- #
# Top-level assembly
# --------------------------------------------------------------------------- #

def build_bundle() -> dict[str, Any]:
    print("[build_viz] Loading TECL price data…")
    tecl = load_tecl()
    print(f"[build_viz]   {len(tecl['dates'])} bars; synthetic ends at index {tecl['synthetic_end_index']}")
    health = compute_tecl_health(tecl)
    latest_health = health.get("latest") or {}
    if latest_health:
        print(
            "[build_viz] TECL Health: "
            f"{latest_health.get('composite')} on {latest_health.get('date')} "
            "(diagnostic only)"
        )

    manifest = load_manifest()
    if manifest:
        print(f"[build_viz] Manifest: sha256={manifest.get('sha256','?')[:12]}… built {manifest.get('built_utc')}")
    else:
        print("[build_viz] Manifest missing — provenance badge will warn.")

    markers = load_north_star_markers()
    print(f"[build_viz] North-star markers: {len(markers)}")

    leaderboard = load_leaderboard()
    print(f"[build_viz] Leaderboard entries: {len(leaderboard)}")
    family_confidence = load_family_confidence()
    if family_confidence:
        leaders = family_confidence.get("strategy_family_leaders") or []
        print(f"[build_viz] Family confidence leaders: {len(leaders)}")

    runs = index_run_artifacts()
    print(f"[build_viz] Indexed {len(runs)} run-dir dashboard_data.json files")

    strategies: list[dict[str, Any]] = []
    matched = 0
    for i, entry in enumerate(leaderboard, start=1):
        key = (entry.get("strategy"), params_key(entry.get("params") or {}))
        run = runs.get(key)
        if run:
            matched += 1
        strategies.append(build_strategy_entry(i, entry, run))
    print(f"[build_viz] Matched {matched}/{len(leaderboard)} leaderboard entries to run artifacts")

    tecl_out = dict(tecl)
    tecl_out["manifest"] = manifest

    bundle = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tecl": tecl_out,
        "tecl_health": health,
        "markers": {"north_star": markers},
        "strategies": strategies,
        "family_confidence": family_confidence,
    }
    return bundle


# --------------------------------------------------------------------------- #
# HTML emission
# --------------------------------------------------------------------------- #

def emit_html(bundle: dict[str, Any]) -> None:
    if not os.path.exists(SHELL_HTML):
        raise FileNotFoundError(f"Missing template: {SHELL_HTML}")
    if not os.path.exists(APP_JS):
        raise FileNotFoundError(f"Missing app.js: {APP_JS}")
    if not os.path.exists(LIB_JS):
        raise FileNotFoundError(
            f"Missing Lightweight Charts library at {LIB_JS}.\n"
            f"Re-vendor by placing the local lightweight-charts standalone bundle at that path."
        )

    with open(SHELL_HTML) as f:
        shell = f.read()
    with open(APP_JS) as f:
        app_js = f.read()
    with open(LIB_JS) as f:
        lib_js = f.read()

    data_json = json.dumps(bundle, separators=(",", ":"), default=str)

    # Guard against accidental script-tag breakouts inside JSON.
    # JSON spec forbids raw `<` so we escape `</` to be safe inside <script>.
    safe_data_json = data_json.replace("</", "<\\/")

    # Use replace (not format) since the template contains many braces.
    # The payload placeholder is the unique sentinel /*__MONTAUK_PAYLOAD__*/null
    # so that the literal token "__MONTAUK_DATA__" elsewhere in the template
    # (e.g. inside app.js error strings) is left untouched.
    html = (shell
            .replace("__LIGHTWEIGHT_CHARTS__", lib_js)
            .replace("/*__MONTAUK_PAYLOAD__*/null", safe_data_json)
            .replace("__MONTAUK_APP__", app_js))

    with open(OUTPUT_HTML, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(OUTPUT_HTML) / (1024 * 1024)
    print(f"[build_viz] Wrote {OUTPUT_HTML} ({size_mb:.2f} MB)")


def main() -> int:
    try:
        bundle = build_bundle()
        emit_html(bundle)
        print(f"[build_viz] Done. Open with: open '{OUTPUT_HTML}'")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[build_viz] FAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

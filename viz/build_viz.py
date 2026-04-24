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

VIZ_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(VIZ_DIR)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from certify.contract import sync_validation_contract
from search.share_metric import read_share_multiple

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SPIKE_DIR = os.path.join(PROJECT_ROOT, "spike")
TEMPLATE_DIR = os.path.join(VIZ_DIR, "templates")

LEADERBOARD_PATH = os.path.join(SPIKE_DIR, "leaderboard.json")
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
    tier = entry.get("tier") or validation.get("tier") or "T0"

    out: dict[str, Any] = {
        "id": f"s{rank:02d}",
        "rank": rank,
        "name": name,
        "codename": codename,
        "fitness": entry.get("fitness"),
        "overall_performance_score": entry.get("overall_performance_score"),
        "composite_confidence": validation.get("composite_confidence"),
        "tier": tier,
        "certified_not_overfit": certified_not_overfit,
        "backtest_certified": backtest_certified,
        "promotion_ready": promotion_ready,
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
        out["certified_not_overfit"] = bool(run_validation.get("certified_not_overfit"))
        out["backtest_certified"] = bool(run_validation.get("backtest_certified"))
        out["promotion_ready"] = bool(run_validation.get("promotion_ready"))
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

    manifest = load_manifest()
    if manifest:
        print(f"[build_viz] Manifest: sha256={manifest.get('sha256','?')[:12]}… built {manifest.get('built_utc')}")
    else:
        print("[build_viz] Manifest missing — provenance badge will warn.")

    markers = load_north_star_markers()
    print(f"[build_viz] North-star markers: {len(markers)}")

    leaderboard = load_leaderboard()
    print(f"[build_viz] Leaderboard entries: {len(leaderboard)}")

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
        "markers": {"north_star": markers},
        "strategies": strategies,
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

#!/usr/bin/env python3
from __future__ import annotations

"""
Generate a parameter diff report for a Montauk strategy candidate.

Compares proposed parameter values against the 8.2.1 defaults and outputs a
compact text report to spike/runs/. Does NOT write Pine Script files.

Usage:
  python3 scripts/generate_pine.py '{"short_ema_len": 12, "atr_multiplier": 2.5}' "9.0-candidate-A"
  python3 scripts/generate_pine.py '{"short_ema_len": 12}' "9.0-candidate-1" --output spike/runs/my-diff.txt
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_engine import StrategyParams

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Maps Python param names to Pine Script input variable names
PARAM_MAP = {
    "short_ema_len":         ("shortEmaLen",         "int"),
    "med_ema_len":           ("medEmaLen",           "int"),
    "long_ema_len":          ("longEmaLen",          "int"),
    "enable_trend":          ("enableTrend",         "bool"),
    "trend_ema_len":         ("trendEmaLen",         "int"),
    "slope_lookback":        ("slopeLookback",       "int"),
    "min_trend_slope":       ("minTrendSlope",       "float"),
    "enable_slope_filter":   ("enableSlopeFilter",   "bool"),
    "enable_below_filter":   ("enableBelowFilter",   "bool"),
    "triple_ema_len":        ("tripleEmaLen",        "int"),
    "triple_slope_lookback": ("tripleSlopeLookback", "int"),
    "enable_sideways_filter":("enableSidewaysFilter","bool"),
    "range_len":             ("rangeLen",            "int"),
    "max_range_pct":         ("maxRangePct",         "float"),
    "enable_sell_confirm":   ("enableSellConfirm",   "bool"),
    "sell_confirm_bars":     ("sellConfirmBars",     "int"),
    "sell_buffer_pct":       ("sellBufferPct",       "float"),
    "enable_sell_cooldown":  ("enableSellCooldown",  "bool"),
    "sell_cooldown_bars":    ("sellCooldownBars",    "int"),
    "enable_atr_exit":       ("enableATRExit",       "bool"),
    "atr_period":            ("atrPeriod",           "int"),
    "atr_multiplier":        ("atrMultiplier",       "float"),
    "enable_quick_exit":     ("enableQuickExit",     "bool"),
    "quick_ema_len":         ("quickEmaLen",         "int"),
    "quick_lookback_bars":   ("quickLookbackBars",   "int"),
    "quick_delta_pct_thresh":("quickDeltaPctThresh", "float"),
    "enable_trail_stop":     ("enableTrailStop",     "bool"),
    "trail_drop_pct":        ("trailDropPct",        "float"),
    "enable_tema_exit":      ("enableTemaExit",      "bool"),
    "tema_exit_lookback":    ("temaExitLookback",    "int"),
}


def generate_diff(params: dict, version_name: str, output_path: str | None = None) -> str:
    defaults = StrategyParams().to_dict()
    date_str = datetime.now().strftime("%Y-%m-%d")

    changes = []      # (pine_var, default_val, new_val, py_key)
    new_params = []   # keys not in PARAM_MAP

    for py_key, new_val in params.items():
        if py_key not in PARAM_MAP:
            new_params.append((py_key, new_val))
            continue

        pine_var, _ = PARAM_MAP[py_key]
        default_val = defaults.get(py_key)
        if new_val != default_val:
            changes.append((pine_var, default_val, new_val, py_key))

    # Build report
    lines = [
        f"=== Montauk {version_name} — Parameter diff vs 8.2.1 ===",
        f"Generated: {date_str}",
        "",
    ]

    if changes:
        lines.append("CHANGED:")
        for pine_var, old_val, new_val, py_key in changes:
            lines.append(f"  {pine_var:<24} {str(old_val):<8} → {str(new_val):<8}  ({py_key})")
    else:
        lines.append("CHANGED: (none — all values match 8.2.1 defaults)")

    if new_params:
        lines.append("")
        lines.append("NEW (not in 8.2.1 — add manually):")
        for py_key, val in new_params:
            lines.append(f"  {py_key:<24} {str(val):<8}")

    lines.append("")
    lines.append("All other parameters: unchanged from 8.2.1 defaults.")
    lines.append("Apply to: src/strategy/active/Project Montauk 8.2.1.txt")

    report = "\n".join(lines)

    if output_path is None:
        safe_version = version_name.replace(" ", "-").replace("/", "-")
        output_path = os.path.join(PROJECT_ROOT, "spike", "runs", f"diff-{date_str}-{safe_version}.txt")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report + "\n")

    print(report)
    print(f"\nWritten to: {output_path}")

    return report, changes, new_params, output_path


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_pine.py '<json params>' '<version name>' [--output <path>]")
        sys.exit(1)

    params = json.loads(sys.argv[1])
    version_name = sys.argv[2]

    output_path = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_path = sys.argv[idx + 1]

    report, changes, new_params, out_file = generate_diff(params, version_name, output_path)

    change_list = [
        {"pine_var": c[0], "py_key": c[3], "old": c[1], "new": c[2]}
        for c in changes
    ]
    new_list = [{"py_key": k, "value": v} for k, v in new_params]

    print(f"\n###JSON### {__import__('json').dumps({'command': 'generate', 'version': version_name, 'changes': change_list, 'new_params': new_list, 'output': out_file})}")


if __name__ == "__main__":
    main()

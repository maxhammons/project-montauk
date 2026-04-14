#!/usr/bin/env python3
"""
Python-vs-Pine Script parity checking for Project Montauk.

Three tiers of checking:
  Tier 1 — Structural parity (automated, no TradingView needed)
  Tier 2 — Signal replay (automated prep, produces diagnostic Pine + reference CSV)
  Tier 3 — Trade-list comparison (semi-automated, needs TradingView export)

Usage:
    python parity.py structural --strategy montauk_821 --params '{...}'
    python parity.py batch
    python parity.py replay --strategy montauk_821 --params '{...}' --output-dir spike/runs/042/
    python parity.py trade-compare --strategy montauk_821 --params '{...}' --tv-trades export.csv
"""

from __future__ import annotations

import argparse
import csv
import inspect
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd

from pine_generator import generate_pine_script, supports_pine_strategy, _BUILDERS
from strategies import STRATEGY_REGISTRY, STRATEGY_PARAMS
from strategy_engine import Indicators, backtest


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParamMatch:
    python_key: str
    python_value: object
    pine_var: str
    pine_type: str
    pine_default: object
    matched: bool
    note: str = ""


@dataclass
class TradeComparison:
    trade_num: int
    entry_date_py: str
    entry_date_pine: str
    exit_date_py: str
    exit_date_pine: str
    entry_price_py: float
    entry_price_pine: float
    exit_price_py: float
    exit_price_pine: float
    pnl_pct_py: float
    pnl_pct_pine: float
    entry_date_match: bool
    exit_date_match: bool
    price_divergence_pct: float
    pnl_divergence_pct: float
    status: str  # "match", "warn", "fail"


# ─────────────────────────────────────────────────────────────────────────────
# Pine Script parser functions
# ─────────────────────────────────────────────────────────────────────────────

def parse_pine_inputs(script: str) -> list[dict]:
    """Extract all input.*() declarations from generated Pine."""
    results = []
    # Match: varName = input.type(default, "label", ...)
    pattern = re.compile(
        r'(\w+)\s*=\s*input\.(int|float|bool)\s*\('
        r'\s*(-?[\d.]+|true|false)\s*,'
        r'\s*"([^"]*)"'
    )
    for m in pattern.finditer(script):
        var_name, input_type, default_str, label = m.groups()
        if input_type == "bool":
            default = default_str == "true"
        elif input_type == "int":
            default = int(float(default_str))
        else:
            default = float(default_str)
        results.append({
            "var_name": var_name,
            "type": input_type,
            "default": default,
            "label": label,
        })
    return results


def parse_pine_settings(script: str) -> dict:
    """Extract strategy() header settings from generated Pine."""
    settings = {}
    # Find the strategy() call block. Can't use simple regex because the
    # title string may contain parentheses like "(T0)". Instead, find
    # "strategy(" and count balanced parens to find the matching close.
    start = script.find("strategy(")
    if start < 0:
        return settings
    depth = 0
    end = start
    for i in range(start, len(script)):
        if script[i] == "(":
            depth += 1
        elif script[i] == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = script[start:end]

    kv_patterns = {
        "initial_capital": (r'initial_capital\s*=\s*(\d+)', int),
        "default_qty_value": (r'default_qty_value\s*=\s*(\d+)', int),
        "pyramiding": (r'pyramiding\s*=\s*(\d+)', int),
        "commission_value": (r'commission_value\s*=\s*([\d.]+)', float),
        "slippage": (r'slippage\s*=\s*(\d+)', int),
    }
    for key, (pat, typ) in kv_patterns.items():
        m = re.search(pat, block)
        if m:
            settings[key] = typ(m.group(1))

    bool_patterns = {
        "process_orders_on_close": r'process_orders_on_close\s*=\s*(true|false)',
        "calc_on_every_tick": r'calc_on_every_tick\s*=\s*(true|false)',
    }
    for key, pat in bool_patterns.items():
        m = re.search(pat, block)
        if m:
            settings[key] = m.group(1) == "true"

    str_patterns = {
        "default_qty_type": r'default_qty_type\s*=\s*(strategy\.\w+)',
        "commission_type": r'commission_type\s*=\s*(strategy\.\w+\.\w+)',
    }
    for key, pat in str_patterns.items():
        m = re.search(pat, block)
        if m:
            settings[key] = m.group(1)

    return settings


def parse_pine_indicators(script: str) -> list[dict]:
    """Extract all ta.*() calls from generated Pine."""
    results = []
    pattern = re.compile(r'(\w+)\s*=\s*ta\.(\w+)\s*\(([^)]*)\)')
    for m in pattern.finditer(script):
        var_name, func, args_str = m.groups()
        args = [a.strip() for a in args_str.split(",")]
        results.append({
            "var_name": var_name,
            "function": f"ta.{func}",
            "args": args,
        })
    return results


def parse_pine_conditions(script: str) -> dict:
    """Extract entry/exit condition structure from generated Pine."""
    entry_count = len(re.findall(r'strategy\.entry\s*\(', script))
    exit_count = len(re.findall(r'strategy\.close\s*\(', script))

    # Count is*Exit variables
    exit_vars = re.findall(r'(is\w*Exit)\s*=', script)

    # Check for exitCond compound
    exit_cond_match = re.search(r'exitCond\s*=\s*(.+)', script)
    exit_cond_expr = exit_cond_match.group(1).strip() if exit_cond_match else ""

    # Check for cooldown pattern
    has_cooldown = bool(re.search(r'lastSellBar|cooldownBars|cooldown', script, re.IGNORECASE))
    has_can_enter = bool(re.search(r'canEnter', script))

    # Check for entry signal
    entry_signal_match = re.search(r'entrySignal\s*=\s*(.+)', script)
    entry_signal_expr = entry_signal_match.group(1).strip() if entry_signal_match else ""

    # Check exit-first priority: entry guarded by `not exitCond` or exit block before entry block
    exit_before_entry = False
    exit_pos = script.find('strategy.close(')
    entry_pos = script.find('strategy.entry(')
    if exit_pos >= 0 and entry_pos >= 0:
        exit_before_entry = exit_pos < entry_pos

    return {
        "entry_count": entry_count,
        "exit_count": exit_count,
        "exit_vars": exit_vars,
        "exit_cond_expr": exit_cond_expr,
        "entry_signal_expr": entry_signal_expr,
        "has_cooldown": has_cooldown,
        "has_can_enter": has_can_enter,
        "exit_before_entry": exit_before_entry,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Builder source introspection — extract Python param → Pine var mapping
# ─────────────────────────────────────────────────────────────────────────────

def _extract_param_mapping(strategy_name: str) -> dict[str, str]:
    """Parse a Pine builder's source to extract params.get("key") → Pine var mapping.

    Returns dict of {python_param_key: pine_var_name}.
    Falls back to empty dict if source is not inspectable (e.g. lambdas).
    """
    builder = _BUILDERS.get(strategy_name)
    if builder is None:
        return {}

    try:
        source = inspect.getsource(builder)
    except (OSError, TypeError):
        return {}

    mapping = {}
    # Pattern: pineVar = input.*(... params.get("python_key", default) ...)
    # Works for both direct builders and template functions
    lines = source.split("\n")
    for line in lines:
        # Match: varName = input.type({_pine_number(params.get("key", default)...)
        m = re.search(
            r'(\w+)\s*=\s*input\.\w+\s*\(\s*\{_pine_number\(\s*'
            r'(?:params|p)\.get\(\s*"(\w+)"',
            line,
        )
        if m:
            pine_var, python_key = m.groups()
            mapping[python_key] = pine_var
            continue

        # Also match lambda wrappers that pass params through
        # e.g., params.get("ema_len", ...) used as positional arg to template
        m2 = re.search(r'(?:params|p)\.get\(\s*"(\w+)"', line)
        if m2 and "input." not in line:
            # Template arg, can't determine Pine var name from this line alone
            pass

    return mapping


def _extract_param_mapping_from_pine(params: dict, pine_inputs: list[dict]) -> dict[str, str]:
    """Fallback: match Python params to Pine inputs by value.

    For each Python param, find a Pine input with the same default value.
    Returns dict of {python_param_key: pine_var_name}.
    """
    mapping = {}
    used_pine_vars = set()

    for py_key, py_val in params.items():
        for inp in pine_inputs:
            if inp["var_name"] in used_pine_vars:
                continue
            pine_val = inp["default"]
            # Compare with type coercion
            if isinstance(py_val, bool):
                if pine_val == py_val:
                    mapping[py_key] = inp["var_name"]
                    used_pine_vars.add(inp["var_name"])
                    break
            elif isinstance(py_val, int) and isinstance(pine_val, int):
                if pine_val == py_val:
                    mapping[py_key] = inp["var_name"]
                    used_pine_vars.add(inp["var_name"])
                    break
            elif isinstance(py_val, (int, float)) and isinstance(pine_val, (int, float)):
                if abs(float(pine_val) - float(py_val)) < 1e-6:
                    mapping[py_key] = inp["var_name"]
                    used_pine_vars.add(inp["var_name"])
                    break

    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1: Structural parity
# ─────────────────────────────────────────────────────────────────────────────

_EXPECTED_SETTINGS = {
    "initial_capital": 1000,
    "default_qty_value": 100,
    "default_qty_type": "strategy.percent_of_equity",
    "pyramiding": 0,
    "commission_value": 0.05,
    "slippage": 0,
    "process_orders_on_close": True,
    "calc_on_every_tick": False,
}

# Python indicator method → Pine function name
_INDICATOR_MAP = {
    "ema": "ta.ema",
    "sma": "ta.sma",
    "rsi": "ta.rsi",
    "atr": "ta.atr",
    "tema": "ta.ema",  # TEMA is 3x EMA
    "highest": "ta.highest",
    "lowest": "ta.lowest",
    "stddev": "ta.stdev",
    "adx": "ta.dmi",
    "stoch_k": "ta.stoch",
    "macd_line": "ta.ema",  # MACD uses EMA internally
    "bb_upper": "ta.sma",   # BB uses SMA
    "bb_lower": "ta.sma",
    "pct_change": None,      # computed manually in Pine
    "slope": None,           # computed manually in Pine
    "vol_ema": "ta.ema",
}


def check_param_parity(strategy_name: str, params: dict, pine_inputs: list[dict]) -> dict:
    """Verify every Python param appears in Pine with matching default value."""
    advisories = []
    hard_fails = []
    matches = []

    # Try source-based mapping first, fall back to value matching
    source_mapping = _extract_param_mapping(strategy_name)
    value_mapping = _extract_param_mapping_from_pine(params, pine_inputs)

    # Merge: source-based takes priority
    mapping = {**value_mapping, **source_mapping}

    pine_by_var = {inp["var_name"]: inp for inp in pine_inputs}
    matched_pine_vars = set()

    for py_key, py_val in params.items():
        pine_var = mapping.get(py_key)
        if pine_var and pine_var in pine_by_var:
            inp = pine_by_var[pine_var]
            matched_pine_vars.add(pine_var)
            # Check value match
            pine_val = inp["default"]
            val_match = False
            if isinstance(py_val, bool):
                val_match = pine_val == py_val
            elif isinstance(py_val, int):
                val_match = pine_val == py_val
            else:
                val_match = abs(float(pine_val) - float(py_val)) < 1e-6

            matches.append(ParamMatch(
                python_key=py_key, python_value=py_val,
                pine_var=pine_var, pine_type=inp["type"],
                pine_default=pine_val, matched=val_match,
            ))
            if not val_match:
                hard_fails.append(
                    f"param '{py_key}': Python={py_val} but Pine {pine_var}={pine_val}"
                )
        else:
            matches.append(ParamMatch(
                python_key=py_key, python_value=py_val,
                pine_var="?", pine_type="?",
                pine_default=None, matched=False,
                note="no matching Pine input found",
            ))
            advisories.append(f"param '{py_key}' has no mapped Pine input")

    # Check for unmapped Pine inputs
    unmatched_pine = [inp["var_name"] for inp in pine_inputs if inp["var_name"] not in matched_pine_vars]
    if unmatched_pine:
        advisories.append(f"Pine inputs not mapped to Python params: {unmatched_pine}")

    matched_count = sum(1 for m in matches if m.matched)
    verdict = "FAIL" if hard_fails else ("WARN" if advisories else "PASS")

    return {
        "verdict": verdict,
        "matched": matched_count,
        "total_python": len(params),
        "total_pine": len(pine_inputs),
        "unmatched_python": [m.python_key for m in matches if not m.matched],
        "unmatched_pine": unmatched_pine,
        "value_mismatches": hard_fails,
        "advisories": advisories,
        "details": [
            {"py": m.python_key, "pine": m.pine_var, "py_val": m.python_value,
             "pine_val": m.pine_default, "ok": m.matched, "note": m.note}
            for m in matches
        ],
    }


def check_settings_parity(pine_settings: dict) -> dict:
    """Verify strategy header settings match expected values."""
    mismatches = []
    for key, expected in _EXPECTED_SETTINGS.items():
        actual = pine_settings.get(key)
        if actual is None:
            mismatches.append({"key": key, "expected": expected, "actual": "MISSING"})
        elif actual != expected:
            mismatches.append({"key": key, "expected": expected, "actual": actual})

    verdict = "FAIL" if mismatches else "PASS"
    return {
        "verdict": verdict,
        "all_match": not mismatches,
        "mismatches": mismatches,
        "hard_fail_reasons": [
            f"setting '{m['key']}': expected {m['expected']}, got {m['actual']}"
            for m in mismatches
        ],
    }


def check_indicator_parity(strategy_name: str, params: dict, pine_indicators: list[dict],
                           df: pd.DataFrame | None = None) -> dict:
    """Verify Python indicator calls have Pine equivalents."""
    advisories = []

    # Determine which indicators the Python strategy uses via cache inspection
    used_indicators = []
    if df is not None and strategy_name in STRATEGY_REGISTRY:
        ind = Indicators(df)
        ind._cache.clear()
        try:
            STRATEGY_REGISTRY[strategy_name](ind, params)
        except Exception:
            advisories.append("could not run strategy to inspect indicator cache")
        used_indicators = list(ind._cache.keys())

    # Map to expected Pine calls
    pine_funcs = {pi["function"] for pi in pine_indicators}
    missing = []
    for cache_key in used_indicators:
        ind_name = cache_key[0] if isinstance(cache_key, tuple) else cache_key
        expected_pine = _INDICATOR_MAP.get(ind_name)
        if expected_pine is None:
            # Manually computed in Pine, no ta.* call expected
            continue
        if expected_pine not in pine_funcs:
            missing.append({"python": ind_name, "expected_pine": expected_pine})

    verdict = "WARN" if missing else "PASS"
    return {
        "verdict": verdict,
        "python_indicators": len(used_indicators),
        "pine_indicators": len(pine_indicators),
        "missing_in_pine": missing,
        "advisories": advisories,
    }


def check_condition_parity(strategy_name: str, pine_conditions: dict,
                           params: dict) -> dict:
    """Verify structural properties of entry/exit logic in Pine."""
    hard_fails = []
    advisories = []

    # Exactly one entry and one exit call
    if pine_conditions["entry_count"] != 1:
        hard_fails.append(f"expected 1 strategy.entry(), found {pine_conditions['entry_count']}")
    if pine_conditions["exit_count"] < 1:
        hard_fails.append(f"expected >= 1 strategy.close(), found {pine_conditions['exit_count']}")

    # Cooldown check
    cooldown_val = params.get("cooldown", 0)
    if cooldown_val > 0 and not pine_conditions["has_cooldown"]:
        hard_fails.append("cooldown > 0 in params but no cooldown logic in Pine")
    elif cooldown_val == 0 and pine_conditions["has_cooldown"]:
        advisories.append("cooldown=0 but Pine has cooldown logic (harmless, no-op)")

    # canEnter guard
    if not pine_conditions["has_can_enter"]:
        advisories.append("no canEnter guard found (may re-enter while in position)")

    # Exit before entry (priority order)
    if not pine_conditions["exit_before_entry"]:
        advisories.append("strategy.entry() appears before strategy.close() in source order")

    verdict = "FAIL" if hard_fails else ("WARN" if advisories else "PASS")
    return {
        "verdict": verdict,
        "entry_count": pine_conditions["entry_count"],
        "exit_count": pine_conditions["exit_count"],
        "exit_branch_count": len(pine_conditions["exit_vars"]),
        "cooldown_expected": cooldown_val > 0,
        "cooldown_present": pine_conditions["has_cooldown"],
        "has_can_enter": pine_conditions["has_can_enter"],
        "exit_before_entry": pine_conditions["exit_before_entry"],
        "hard_fail_reasons": hard_fails,
        "advisories": advisories,
    }


def structural_parity_check(strategy_name: str, params: dict,
                            df: pd.DataFrame | None = None) -> dict:
    """Tier 1 entry point: full structural parity check."""
    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []

    if not supports_pine_strategy(strategy_name):
        return {
            "verdict": "SKIPPED",
            "mode": "structural",
            "reason": f"no Pine builder for {strategy_name}",
            "generated": False,
            "advisories": [],
            "soft_warnings": [],
            "critical_warnings": [],
            "hard_fail_reasons": [],
        }

    try:
        script = generate_pine_script(strategy_name, params)
    except Exception as exc:
        return {
            "verdict": "FAIL",
            "mode": "structural",
            "generated": False,
            "error": str(exc),
            "advisories": [],
            "soft_warnings": [],
            "critical_warnings": [],
            "hard_fail_reasons": [f"Pine generation failed: {exc}"],
        }

    # Parse
    pine_inputs = parse_pine_inputs(script)
    pine_settings = parse_pine_settings(script)
    pine_indicators = parse_pine_indicators(script)
    pine_conditions = parse_pine_conditions(script)

    # Sub-checks
    param_result = check_param_parity(strategy_name, params, pine_inputs)
    settings_result = check_settings_parity(pine_settings)
    indicator_result = check_indicator_parity(strategy_name, params, pine_indicators, df)
    condition_result = check_condition_parity(strategy_name, pine_conditions, params)

    # Aggregate
    for r in (param_result, settings_result, indicator_result, condition_result):
        advisories.extend(r.get("advisories", []))
        hard_fail_reasons.extend(r.get("hard_fail_reasons", []))

    if settings_result["verdict"] == "FAIL":
        critical_warnings.append("Pine strategy settings do not match expected values")
    if param_result["verdict"] == "FAIL":
        critical_warnings.append("Pine input defaults do not match Python params")
    if condition_result["verdict"] == "FAIL":
        critical_warnings.append("Pine condition structure has issues")

    if indicator_result.get("missing_in_pine"):
        soft_warnings.append(
            f"Pine missing indicators: {[m['python'] for m in indicator_result['missing_in_pine']]}"
        )

    # Commission vs slippage advisory (always present)
    advisories.append(
        "Python uses 0.05% slippage on fill price; Pine uses 0.05% commission. "
        "Expected PnL divergence: <0.15% per trade."
    )

    # Overall verdict
    if hard_fail_reasons:
        verdict = "FAIL"
    elif critical_warnings:
        verdict = "FAIL"
    elif soft_warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "mode": "structural",
        "generated": True,
        "line_count": len(script.splitlines()),
        "param_parity": param_result,
        "settings_parity": settings_result,
        "indicator_parity": indicator_result,
        "condition_parity": condition_result,
        "settings_ok": settings_result["verdict"] == "PASS",
        "advisories": list(dict.fromkeys(advisories)),
        "soft_warnings": list(dict.fromkeys(soft_warnings)),
        "critical_warnings": list(dict.fromkeys(critical_warnings)),
        "hard_fail_reasons": list(dict.fromkeys(hard_fail_reasons)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2: Signal replay
# ─────────────────────────────────────────────────────────────────────────────

def generate_indicator_reference(strategy_name: str, params: dict,
                                 df: pd.DataFrame) -> dict:
    """Run Python strategy and capture bar-by-bar indicator values + trades."""
    ind = Indicators(df)
    ind._cache.clear()

    entries, exits, labels = STRATEGY_REGISTRY[strategy_name](ind, params)
    cooldown = params.get("cooldown", 0)
    result = backtest(df, entries, exits, labels, cooldown_bars=cooldown,
                      strategy_name=strategy_name)

    # Extract cached indicator arrays
    indicators = {}
    for cache_key, arr in ind._cache.items():
        if isinstance(arr, np.ndarray):
            name = "_".join(str(x) for x in cache_key) if isinstance(cache_key, tuple) else str(cache_key)
            indicators[name] = arr

    dates = df["date"].values
    close = df["close"].values.astype(np.float64)

    return {
        "dates": [str(d)[:10] for d in dates],
        "close": close,
        "indicators": indicators,
        "entries": entries,
        "exits": exits,
        "exit_labels": labels,
        "trades": result.trades,
        "backtest_result": result,
    }


def generate_diagnostic_pine(strategy_name: str, params: dict) -> str:
    """Generate Pine Script with extra diagnostic plots for visual comparison."""
    base_script = generate_pine_script(strategy_name, params)

    # Find the riskState footer to insert diagnostics before it
    footer_marker = "riskState = strategy.position_size > 0 ? 1 : 0"

    diag_lines = [
        "",
        "// ═══════════════════════════════════════════════════════════════",
        "// DIAGNOSTIC SECTION — auto-generated by parity.py",
        "// Paste into TradingView and compare indicator traces against",
        "// the Python reference CSV for signal-level parity checking.",
        "// ═══════════════════════════════════════════════════════════════",
        "",
        "// Entry/exit signal highlighting",
        "bgcolor(strategy.position_size > 0 and strategy.position_size[1] == 0 ? color.new(color.green, 85) : na)",
        "bgcolor(strategy.position_size == 0 and strategy.position_size[1] > 0 ? color.new(color.red, 85) : na)",
        "",
        "// Data-window exports for every indicator (invisible on chart, visible in data window)",
    ]

    # Parse the base script to find what indicators exist
    pine_indicators = parse_pine_indicators(base_script)
    for pi in pine_indicators:
        var_name = pi["var_name"]
        diag_lines.append(
            f'plot({var_name}, "Diag: {var_name}", color=color.new(color.gray, 100), '
            f'display=display.data_window)'
        )

    # Also export entry/exit signals as 0/1
    pine_conditions = parse_pine_conditions(base_script)
    if pine_conditions["entry_signal_expr"]:
        diag_lines.append(
            'plot(entrySignal ? 1 : 0, "Diag: entrySignal", '
            'color=color.new(color.gray, 100), display=display.data_window)'
        )
    for ev in pine_conditions["exit_vars"]:
        diag_lines.append(
            f'plot({ev} ? 1 : 0, "Diag: {ev}", '
            f'color=color.new(color.gray, 100), display=display.data_window)'
        )

    diag_block = "\n".join(diag_lines) + "\n\n"

    if footer_marker in base_script:
        return base_script.replace(footer_marker, diag_block + footer_marker)
    else:
        return base_script.rstrip() + "\n" + diag_block


def export_reference_csv(reference: dict, output_path: Path) -> str:
    """Write bar-by-bar indicator reference to CSV for comparison against TradingView."""
    rows = []
    n = len(reference["dates"])
    for i in range(n):
        row = {
            "date": reference["dates"][i],
            "close": f"{reference['close'][i]:.4f}",
            "entry": int(reference["entries"][i]),
            "exit": int(reference["exits"][i]),
        }
        for name, arr in reference["indicators"].items():
            val = arr[i] if i < len(arr) else float("nan")
            row[name] = f"{val:.6f}" if not np.isnan(val) else ""
        rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return str(output_path)


def signal_replay_check(strategy_name: str, params: dict, df: pd.DataFrame,
                        output_dir: Path | None = None) -> dict:
    """Tier 2 entry point: produce diagnostic Pine + reference data."""
    advisories = []

    if strategy_name not in STRATEGY_REGISTRY:
        return {"verdict": "FAIL", "mode": "signal_replay",
                "error": f"{strategy_name} not in STRATEGY_REGISTRY"}

    reference = generate_indicator_reference(strategy_name, params, df)
    diagnostic_pine = generate_diagnostic_pine(strategy_name, params)

    csv_path = None
    pine_path = None
    if output_dir:
        output_dir = Path(output_dir)
        csv_path = export_reference_csv(reference, output_dir / "parity_reference.csv")
        pine_path = output_dir / "diagnostic_strategy.txt"
        pine_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pine_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(diagnostic_pine)
        pine_path = str(pine_path)

    trade_summary = []
    for t in reference["trades"]:
        trade_summary.append({
            "entry_date": t.entry_date,
            "exit_date": t.exit_date,
            "entry_price": round(t.entry_price, 4),
            "exit_price": round(t.exit_price, 4),
            "pnl_pct": round(t.pnl_pct, 4),
            "exit_reason": t.exit_reason,
        })

    return {
        "verdict": "READY",
        "mode": "signal_replay",
        "python_trade_count": len(reference["trades"]),
        "indicator_count": len(reference["indicators"]),
        "bar_count": len(reference["dates"]),
        "reference_csv_path": csv_path,
        "diagnostic_pine_path": pine_path,
        "reference_trades": trade_summary,
        "advisories": advisories,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3: Trade-list comparison
# ─────────────────────────────────────────────────────────────────────────────

def parse_tv_trade_list(text: str) -> list[dict]:
    """Parse TradingView Strategy Tester trade list export.

    Handles both tab-separated (copy-paste from TV) and CSV formats.
    TV exports paired Entry/Exit rows per trade number.
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return []

    # Detect delimiter
    if "\t" in lines[0]:
        delimiter = "\t"
    else:
        delimiter = ","

    reader = csv.reader(io.StringIO(text.strip()), delimiter=delimiter)
    rows = list(reader)

    if len(rows) < 2:
        return []

    # Normalize header
    header = [h.strip().lower().replace(" ", "_").replace("/", "_") for h in rows[0]]

    # Find column indices
    def _col(names):
        for name in names:
            for i, h in enumerate(header):
                if name in h:
                    return i
        return None

    trade_col = _col(["trade_#", "trade"])
    type_col = _col(["type"])
    signal_col = _col(["signal"])
    date_col = _col(["date", "date_time"])
    price_col = _col(["price"])
    profit_col = _col(["profit"])
    pct_col = _col(["profit_%", "profit_pct", "pct"])
    contracts_col = _col(["contracts", "qty"])

    if date_col is None or price_col is None:
        return []

    # Parse rows into entry/exit pairs
    pending_entries = {}  # trade_num -> entry_row
    trades = []

    for row in rows[1:]:
        if len(row) <= max(c for c in [date_col, price_col] if c is not None):
            continue

        # Determine if entry or exit
        signal = row[signal_col].strip().lower() if signal_col is not None and signal_col < len(row) else ""
        row_type = row[type_col].strip().lower() if type_col is not None and type_col < len(row) else ""

        is_entry = "entry" in signal or "entry" in row_type
        is_exit = "exit" in signal or "exit" in row_type or "close" in signal or "close" in row_type

        trade_num_str = row[trade_col].strip() if trade_col is not None and trade_col < len(row) else ""
        try:
            trade_num = int(trade_num_str)
        except (ValueError, IndexError):
            trade_num = len(trades) + len(pending_entries) + 1

        date_str = row[date_col].strip() if date_col < len(row) else ""
        # Normalize date: "2020-03-24 00:00" → "2020-03-24"
        date_str = date_str[:10]

        try:
            price = float(row[price_col].strip().replace(",", "")) if price_col < len(row) else 0.0
        except (ValueError, IndexError):
            price = 0.0

        profit = 0.0
        if profit_col is not None and profit_col < len(row):
            try:
                profit = float(row[profit_col].strip().replace(",", ""))
            except (ValueError, IndexError):
                pass

        profit_pct = 0.0
        if pct_col is not None and pct_col < len(row):
            try:
                profit_pct = float(row[pct_col].strip().replace(",", "").replace("%", ""))
            except (ValueError, IndexError):
                pass

        if is_entry:
            pending_entries[trade_num] = {
                "trade_num": trade_num,
                "entry_date": date_str,
                "entry_price": price,
            }
        elif is_exit and trade_num in pending_entries:
            entry = pending_entries.pop(trade_num)
            entry.update({
                "exit_date": date_str,
                "exit_price": price,
                "profit": profit,
                "profit_pct": profit_pct,
            })
            trades.append(entry)

    return trades


def estimate_commission_slippage_divergence(python_trades: list) -> dict:
    """Estimate expected PnL divergence from commission-vs-slippage modeling."""
    divergences = []
    for t in python_trades:
        if t.entry_price > 0 and t.exit_price > 0:
            # Python model: entry at close * 1.0005, exit at close * 0.9995
            # Approximate the "true close" by reversing slippage
            true_entry = t.entry_price / 1.0005
            true_exit = t.exit_price / 0.9995
            py_return = t.exit_price / t.entry_price - 1
            # Pine model: fills at true close, then 0.05% commission each side
            pine_return = (true_exit / true_entry - 1) - 0.001  # ~0.10% total commission
            divergences.append(abs(py_return - pine_return) * 100)

    return {
        "max_expected_pct": max(divergences) if divergences else 0.0,
        "mean_expected_pct": sum(divergences) / len(divergences) if divergences else 0.0,
        "trade_count": len(divergences),
    }


def match_trades(python_trades: list, pine_trades: list[dict], *,
                 date_tolerance_days: int = 1,
                 price_tol_pct: float = 0.15,
                 pnl_tol_pct: float = 0.20) -> list[TradeComparison]:
    """Match Python backtest trades against TV trades and compute divergences."""
    comparisons = []

    # Build lookup by entry date for Pine trades
    pine_by_date = {}
    for pt in pine_trades:
        pine_by_date.setdefault(pt["entry_date"], []).append(pt)
    pine_used = set()

    for i, py_trade in enumerate(python_trades):
        py_entry_date = py_trade.entry_date
        py_exit_date = py_trade.exit_date

        # Try exact date match first, then +/- tolerance
        matched_pine = None
        for offset in range(date_tolerance_days + 1):
            for delta in ([0] if offset == 0 else [-offset, offset]):
                try:
                    check_date = str(
                        (pd.Timestamp(py_entry_date) + pd.Timedelta(days=delta)).date()
                    )
                except Exception:
                    continue
                candidates = pine_by_date.get(check_date, [])
                for pt in candidates:
                    pt_id = id(pt)
                    if pt_id not in pine_used:
                        matched_pine = pt
                        pine_used.add(pt_id)
                        break
                if matched_pine:
                    break
            if matched_pine:
                break

        if matched_pine is None:
            comparisons.append(TradeComparison(
                trade_num=i + 1,
                entry_date_py=py_entry_date, entry_date_pine="UNMATCHED",
                exit_date_py=py_exit_date, exit_date_pine="",
                entry_price_py=py_trade.entry_price, entry_price_pine=0,
                exit_price_py=py_trade.exit_price, exit_price_pine=0,
                pnl_pct_py=py_trade.pnl_pct, pnl_pct_pine=0,
                entry_date_match=False, exit_date_match=False,
                price_divergence_pct=float("inf"),
                pnl_divergence_pct=float("inf"),
                status="fail",
            ))
            continue

        # Compute divergences
        entry_price_div = (
            abs(py_trade.entry_price - matched_pine["entry_price"]) /
            py_trade.entry_price * 100
        ) if py_trade.entry_price > 0 else 0

        exit_price_div = (
            abs(py_trade.exit_price - matched_pine["exit_price"]) /
            py_trade.exit_price * 100
        ) if py_trade.exit_price > 0 else 0

        pine_pnl = matched_pine.get("profit_pct", 0)
        pnl_div = abs(py_trade.pnl_pct - pine_pnl)

        exit_date_match = py_exit_date == matched_pine.get("exit_date", "")

        price_div = max(entry_price_div, exit_price_div)
        status = "match"
        if pnl_div > pnl_tol_pct or price_div > price_tol_pct:
            status = "warn"
        if pnl_div > 1.0 or not exit_date_match:
            status = "fail"

        comparisons.append(TradeComparison(
            trade_num=i + 1,
            entry_date_py=py_entry_date,
            entry_date_pine=matched_pine["entry_date"],
            exit_date_py=py_exit_date,
            exit_date_pine=matched_pine.get("exit_date", ""),
            entry_price_py=py_trade.entry_price,
            entry_price_pine=matched_pine["entry_price"],
            exit_price_py=py_trade.exit_price,
            exit_price_pine=matched_pine["exit_price"],
            pnl_pct_py=py_trade.pnl_pct,
            pnl_pct_pine=pine_pnl,
            entry_date_match=py_entry_date == matched_pine["entry_date"],
            exit_date_match=exit_date_match,
            price_divergence_pct=round(price_div, 4),
            pnl_divergence_pct=round(pnl_div, 4),
            status=status,
        ))

    return comparisons


def trade_list_parity_check(strategy_name: str, params: dict,
                            df: pd.DataFrame, tv_trade_text: str, *,
                            price_tol_pct: float = 0.15,
                            pnl_tol_pct: float = 0.20) -> dict:
    """Tier 3 entry point: compare Python backtest trades vs TradingView export."""
    advisories = []
    soft_warnings = []
    critical_warnings = []
    hard_fail_reasons = []

    # Run Python backtest
    ind = Indicators(df)
    entries, exits, labels = STRATEGY_REGISTRY[strategy_name](ind, params)
    cooldown = params.get("cooldown", 0)
    result = backtest(df, entries, exits, labels, cooldown_bars=cooldown,
                      strategy_name=strategy_name)
    python_trades = result.trades

    # Parse TV export
    pine_trades = parse_tv_trade_list(tv_trade_text)
    if not pine_trades:
        return {
            "verdict": "FAIL", "mode": "trade_list",
            "hard_fail_reasons": ["could not parse TradingView trade list"],
            "advisories": [], "soft_warnings": [], "critical_warnings": [],
        }

    # Match
    comparisons = match_trades(python_trades, pine_trades,
                               price_tol_pct=price_tol_pct, pnl_tol_pct=pnl_tol_pct)

    # Stats
    matched_count = sum(1 for c in comparisons if c.status != "fail" or c.entry_date_pine != "UNMATCHED")
    unmatched_py = sum(1 for c in comparisons if c.entry_date_pine == "UNMATCHED")
    unmatched_pine = len(pine_trades) - (len(comparisons) - unmatched_py)

    pnl_divs = [c.pnl_divergence_pct for c in comparisons if c.status != "fail" or c.entry_date_pine != "UNMATCHED"]
    price_divs = [c.price_divergence_pct for c in comparisons if c.price_divergence_pct < float("inf")]

    max_pnl_div = max(pnl_divs) if pnl_divs else 0
    mean_pnl_div = sum(pnl_divs) / len(pnl_divs) if pnl_divs else 0
    max_price_div = max(price_divs) if price_divs else 0

    # Expected divergence from commission vs slippage
    expected = estimate_commission_slippage_divergence(python_trades)

    # Verdict
    count_diff_pct = abs(len(python_trades) - len(pine_trades)) / max(len(python_trades), 1) * 100
    if count_diff_pct > 10:
        hard_fail_reasons.append(
            f"trade count diverges: Python={len(python_trades)}, Pine={len(pine_trades)} ({count_diff_pct:.0f}%)"
        )
    if max_pnl_div > 1.0:
        hard_fail_reasons.append(f"max PnL divergence {max_pnl_div:.2f}% > 1.0% (likely logic error)")
    if max_pnl_div > 0.5:
        soft_warnings.append(f"max PnL divergence {max_pnl_div:.2f}% > 0.5%")
    if mean_pnl_div > 0.2:
        soft_warnings.append(f"mean PnL divergence {mean_pnl_div:.2f}% > 0.2%")
    if unmatched_py > 2:
        soft_warnings.append(f"{unmatched_py} Python trades unmatched in TV export")
    if unmatched_pine > 2:
        soft_warnings.append(f"{unmatched_pine} TV trades unmatched in Python backtest")

    advisories.append(
        f"Expected commission-vs-slippage divergence: "
        f"max {expected['max_expected_pct']:.3f}%, mean {expected['mean_expected_pct']:.3f}%"
    )

    first_diverging = None
    for c in comparisons:
        if c.status == "fail":
            first_diverging = c.trade_num
            break

    if hard_fail_reasons:
        verdict = "FAIL"
    elif soft_warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "mode": "trade_list",
        "python_trade_count": len(python_trades),
        "pine_trade_count": len(pine_trades),
        "matched_count": matched_count,
        "unmatched_python": unmatched_py,
        "unmatched_pine": max(0, unmatched_pine),
        "max_price_divergence_pct": round(max_price_div, 4),
        "max_pnl_divergence_pct": round(max_pnl_div, 4),
        "mean_pnl_divergence_pct": round(mean_pnl_div, 4),
        "first_diverging_trade": first_diverging,
        "expected_divergence": expected,
        "divergent_trades": [
            {
                "trade": c.trade_num,
                "entry_py": c.entry_date_py, "entry_pine": c.entry_date_pine,
                "exit_py": c.exit_date_py, "exit_pine": c.exit_date_pine,
                "pnl_py": round(c.pnl_pct_py, 2), "pnl_pine": round(c.pnl_pct_pine, 2),
                "pnl_div": c.pnl_divergence_pct,
                "status": c.status,
            }
            for c in comparisons if c.status != "match"
        ],
        "advisories": advisories,
        "soft_warnings": soft_warnings,
        "critical_warnings": critical_warnings,
        "hard_fail_reasons": hard_fail_reasons,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Midpoint params helper (shared with integrity.py)
# ─────────────────────────────────────────────────────────────────────────────

def _midpoint_params(strategy_name: str) -> dict:
    """Generate midpoint params for a strategy from STRATEGY_PARAMS."""
    params = {}
    for name, (lo, hi, step, typ) in STRATEGY_PARAMS.get(strategy_name, {}).items():
        n_steps = int(round((hi - lo) / step))
        idx = n_steps // 2
        if typ == int:
            params[name] = int(lo + idx * step)
        else:
            params[name] = round(lo + idx * step, 4)
    return params


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_report(report: dict, verbose: bool = False):
    """Pretty-print a parity report."""
    verdict = report.get("verdict", "?")
    mode = report.get("mode", "?")
    icon = {"PASS": "+", "WARN": "~", "FAIL": "!", "SKIPPED": "-", "READY": "*"}.get(verdict, "?")
    print(f"[{icon}] {verdict} — {mode}")

    if report.get("generated") is False:
        print(f"    error: {report.get('error', report.get('reason', '?'))}")
        return

    if mode == "structural":
        pp = report.get("param_parity", {})
        sp = report.get("settings_parity", {})
        ip = report.get("indicator_parity", {})
        cp = report.get("condition_parity", {})
        print(f"    params: {pp.get('matched', 0)}/{pp.get('total_python', 0)} matched, "
              f"{len(pp.get('value_mismatches', []))} mismatches")
        print(f"    settings: {'OK' if sp.get('all_match') else 'MISMATCH'}")
        print(f"    indicators: {ip.get('python_indicators', '?')} Python, "
              f"{ip.get('pine_indicators', '?')} Pine, "
              f"{len(ip.get('missing_in_pine', []))} missing")
        print(f"    conditions: entry={cp.get('entry_count', '?')}, "
              f"exit_branches={cp.get('exit_branch_count', '?')}, "
              f"cooldown={'yes' if cp.get('cooldown_present') else 'no'}")

    elif mode == "signal_replay":
        print(f"    trades: {report.get('python_trade_count', '?')}")
        print(f"    indicators: {report.get('indicator_count', '?')}")
        print(f"    bars: {report.get('bar_count', '?')}")
        if report.get("reference_csv_path"):
            print(f"    reference CSV: {report['reference_csv_path']}")
        if report.get("diagnostic_pine_path"):
            print(f"    diagnostic Pine: {report['diagnostic_pine_path']}")

    elif mode == "trade_list":
        print(f"    Python trades: {report.get('python_trade_count', '?')}")
        print(f"    Pine trades: {report.get('pine_trade_count', '?')}")
        print(f"    matched: {report.get('matched_count', '?')}")
        print(f"    max PnL divergence: {report.get('max_pnl_divergence_pct', 0):.3f}%")
        print(f"    mean PnL divergence: {report.get('mean_pnl_divergence_pct', 0):.3f}%")

    if verbose:
        for category in ("hard_fail_reasons", "critical_warnings", "soft_warnings", "advisories"):
            items = report.get(category, [])
            if items:
                print(f"    {category}:")
                for item in items:
                    print(f"      - {item}")


def main():
    parser = argparse.ArgumentParser(
        description="Python-vs-Pine parity checking for Project Montauk"
    )
    sub = parser.add_subparsers(dest="command")

    # Tier 1: structural
    t1 = sub.add_parser("structural", help="Tier 1 structural parity check")
    t1.add_argument("--strategy", required=True)
    t1.add_argument("--params", type=json.loads, default={})
    t1.add_argument("--verbose", "-v", action="store_true")

    # Tier 2: signal replay
    t2 = sub.add_parser("replay", help="Tier 2 signal replay + diagnostic Pine")
    t2.add_argument("--strategy", required=True)
    t2.add_argument("--params", type=json.loads, default={})
    t2.add_argument("--output-dir", default=".")
    t2.add_argument("--verbose", "-v", action="store_true")

    # Tier 3: trade-list compare
    t3 = sub.add_parser("trade-compare", help="Tier 3 trade-list comparison")
    t3.add_argument("--strategy", required=True)
    t3.add_argument("--params", type=json.loads, default={})
    t3.add_argument("--tv-trades", required=True, help="Path to TV export file or '-' for stdin")
    t3.add_argument("--price-tol", type=float, default=0.15)
    t3.add_argument("--pnl-tol", type=float, default=0.20)
    t3.add_argument("--verbose", "-v", action="store_true")

    # Batch: run Tier 1 on all strategies
    batch = sub.add_parser("batch", help="Run Tier 1 on all strategies in _BUILDERS")
    batch.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if args.command == "structural":
        params = args.params or _midpoint_params(args.strategy)
        report = structural_parity_check(args.strategy, params)
        _print_report(report, args.verbose)
        sys.exit(0 if report["verdict"] in ("PASS", "WARN") else 1)

    elif args.command == "replay":
        from data import get_tecl_data
        df = get_tecl_data(use_yfinance=False)
        params = args.params or _midpoint_params(args.strategy)
        report = signal_replay_check(args.strategy, params, df,
                                     output_dir=Path(args.output_dir))
        _print_report(report, args.verbose)

    elif args.command == "trade-compare":
        from data import get_tecl_data
        df = get_tecl_data(use_yfinance=False)
        params = args.params or _midpoint_params(args.strategy)
        if args.tv_trades == "-":
            tv_text = sys.stdin.read()
        else:
            with open(args.tv_trades, "r") as f:
                tv_text = f.read()
        report = trade_list_parity_check(args.strategy, params, df, tv_text,
                                         price_tol_pct=args.price_tol,
                                         pnl_tol_pct=args.pnl_tol)
        _print_report(report, args.verbose)
        sys.exit(0 if report["verdict"] in ("PASS", "WARN") else 1)

    elif args.command == "batch":
        from data import get_tecl_data
        df = get_tecl_data(use_yfinance=False)
        results = {}
        pass_count = 0
        warn_count = 0
        fail_count = 0
        skip_count = 0

        for strategy_name in sorted(_BUILDERS.keys()):
            params = _midpoint_params(strategy_name)
            report = structural_parity_check(strategy_name, params, df)
            results[strategy_name] = report
            v = report["verdict"]
            if v == "PASS":
                pass_count += 1
            elif v == "WARN":
                warn_count += 1
            elif v == "SKIPPED":
                skip_count += 1
            else:
                fail_count += 1
            print(f"  {strategy_name}: ", end="")
            _print_report(report, args.verbose)

        print(f"\n{'='*60}")
        print(f"Batch: {len(results)} strategies — "
              f"{pass_count} PASS, {warn_count} WARN, {fail_count} FAIL, {skip_count} SKIP")
        sys.exit(0 if fail_count == 0 else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

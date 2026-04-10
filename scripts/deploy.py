#!/usr/bin/env python3
"""
Patch the active Montauk Pine Script with optimizer output.

Usage:
  python scripts/deploy.py spike/runs/013
  python scripts/deploy.py spike/runs/013/results.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PINE_PATH = PROJECT_ROOT / "src/strategy/active/Project Montauk 8.2.1.txt"

PARAM_MAP = {
    "short_ema": "shortEmaLen",
    "med_ema": "medEmaLen",
    "trend_ema": "trendEmaLen",
    "slope_lookback": "slopeLookback",
    "atr_period": "atrPeriod",
    "atr_mult": "atrMultiplier",
    "quick_ema": "quickEmaLen",
    "quick_lookback": "quickLookbackBars",
    "quick_thresh": "quickDeltaPctThresh",
    "sell_buffer": "sellBufferPct",
    "cooldown": "sellCooldownBars",
}


def resolve_results_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    search_paths = [candidate] if candidate.is_absolute() else [Path.cwd() / candidate, PROJECT_ROOT / candidate]

    for path in search_paths:
        resolved = path.resolve()
        if resolved.is_dir():
            results_path = resolved / "results.json"
            if results_path.exists():
                return results_path
        elif resolved.exists():
            return resolved

    missing = search_paths[0].resolve()
    raise FileNotFoundError(f"Could not find run directory or results file: {missing}")


def format_pine_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.10f}".rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
        return text
    raise TypeError(f"Unsupported Pine value type: {type(value).__name__}")


def patch_pine_script(pine_text: str, params: dict) -> tuple[str, list[dict], list[str]]:
    patched = pine_text
    changes: list[dict] = []
    matched: set[str] = set()

    for param_name, pine_var in PARAM_MAP.items():
        if param_name not in params:
            continue

        new_value = format_pine_value(params[param_name])
        pattern = re.compile(
            rf"(?m)^(\s*{re.escape(pine_var)}\s*=\s*input\.\w+\()([^,]+)(,.*)$"
        )

        def _replace(match: re.Match[str]) -> str:
            old_value = match.group(2).strip()
            changes.append(
                {
                    "param": param_name,
                    "pine_var": pine_var,
                    "old": old_value,
                    "new": new_value,
                }
            )
            matched.add(param_name)
            return f"{match.group(1)}{new_value}{match.group(3)}"

        patched, _ = pattern.subn(_replace, patched, count=1)

    unmatched = sorted(name for name in params if name in PARAM_MAP and name not in matched)
    return patched, changes, unmatched


def load_winner(results_path: Path) -> dict:
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    rankings = results.get("rankings")
    if not isinstance(rankings, list) or not rankings:
        raise ValueError(f"No rankings found in {results_path}")

    return results


def select_ranking_entry(results: dict, strategy_name: str | None = None,
                         rank: int | None = None) -> dict:
    rankings = results.get("rankings")
    if not isinstance(rankings, list) or not rankings:
        raise ValueError("No rankings found in results")

    if rank is not None:
        if rank < 1 or rank > len(rankings):
            raise ValueError(f"Requested rank {rank} is outside available rankings (1-{len(rankings)})")
        entry = rankings[rank - 1]
        if strategy_name and entry.get("strategy") != strategy_name:
            raise ValueError(
                f"Rank {rank} is {entry.get('strategy')}, not requested strategy {strategy_name}"
            )
        if not isinstance(entry.get("params"), dict):
            raise ValueError(f"Ranking entry #{rank} has no params dict")
        return entry

    target_strategy = strategy_name or "montauk_821"
    matches = [entry for entry in rankings if entry.get("strategy") == target_strategy]
    if not matches:
        if strategy_name:
            raise ValueError(f"No ranking entry found for strategy {strategy_name}")
        raise ValueError(
            "No montauk_821 result found in rankings. Pass --strategy or --rank explicitly "
            "if you really want to deploy something else."
        )

    entry = matches[0]
    if not isinstance(entry.get("params"), dict):
        raise ValueError(f"Selected ranking entry for {target_strategy} has no params dict")
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Run directory or results.json path")
    parser.add_argument("--strategy", help="Deploy a specific strategy from rankings")
    parser.add_argument("--rank", type=int, help="Deploy a specific overall rank from rankings")
    args = parser.parse_args(argv)

    results_path = resolve_results_path(args.path)
    run_dir = results_path.parent
    results = load_winner(results_path)
    winner = select_ranking_entry(results, strategy_name=args.strategy, rank=args.rank)
    params = winner["params"]

    with open(ACTIVE_PINE_PATH, "r", encoding="utf-8", newline="") as f:
        pine_text = f.read()

    patched_text, changes, unmatched = patch_pine_script(pine_text, params)
    output_path = run_dir / "patched_strategy.txt"
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write(patched_text)

    strategy_name = winner.get("strategy", "unknown")
    missing_params = sorted(name for name in PARAM_MAP if name not in params)
    unmapped_params = sorted(name for name in params if name not in PARAM_MAP)

    print(f"Loaded winner: {strategy_name}")
    print(f"Source results: {results_path}")
    print(f"Patched output: {output_path}")

    if strategy_name != "montauk_821":
        print("WARNING: winner is not montauk_821; only mapped Montauk params were patched.")

    if changes:
        print("\nPatched defaults:")
        for change in changes:
            print(
                f"  {change['param']} -> {change['pine_var']}: "
                f"{change['old']} -> {change['new']}"
            )
    else:
        print("\nPatched defaults: none")

    if missing_params:
        print(f"\nWARNING: results missing mapped params: {', '.join(missing_params)}")
    if unmatched:
        print(f"WARNING: Pine inputs not found for params: {', '.join(unmatched)}")
    if unmapped_params:
        print(f"NOTE: ignored params with no Pine mapping: {', '.join(unmapped_params)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

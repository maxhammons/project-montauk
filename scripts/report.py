#!/usr/bin/env python3
"""
Auto-generate markdown reports from spike optimization results.

Called by spike_runner.py at the end of each run. No Claude tokens needed.

Usage:
    from report import generate_report
    generate_report(results_dict, run_dir, leaderboard_path)
"""

from __future__ import annotations

import json
import os
from datetime import datetime


def _fmt_pct(val: float) -> str:
    return f"{val:.1f}%"


def _fmt_mult(val: float) -> str:
    return f"{val:.3f}x"


def _fmt_fitness(val: float) -> str:
    return f"{val:.4f}"


def _top_n_table(rankings: list, n: int = 10) -> str:
    """Generate a markdown table of the top N results."""
    lines = []
    lines.append("| # | Strategy | vs B&H | CAGR | Max DD | MAR | Trades/Yr | Fitness |")
    lines.append("|---|----------|--------|------|--------|-----|-----------|---------|")

    for entry in rankings[:n]:
        m = entry.get("metrics")
        if not m:
            continue
        lines.append(
            f"| {entry['rank']} "
            f"| {entry['strategy']} "
            f"| {_fmt_mult(m['vs_bah'])} "
            f"| {_fmt_pct(m['cagr'])} "
            f"| {_fmt_pct(m['max_dd'])} "
            f"| {m['mar']:.3f} "
            f"| {m['trades_yr']:.1f} "
            f"| {_fmt_fitness(entry['fitness'])} |"
        )
    return "\n".join(lines)


def _detail_block(entry: dict) -> str:
    """Generate a detail section for a single ranked entry."""
    m = entry.get("metrics")
    if not m:
        return ""

    params = entry.get("params", {})
    # Filter out cooldown for display (it's a meta-param)
    display_params = {k: v for k, v in params.items() if k != "cooldown"}

    lines = [
        f"### #{entry['rank']}: {entry['strategy']}",
        "",
        f"**Fitness:** {_fmt_fitness(entry['fitness'])} | "
        f"**vs B&H:** {_fmt_mult(m['vs_bah'])} | "
        f"**CAGR:** {_fmt_pct(m['cagr'])} | "
        f"**Max DD:** {_fmt_pct(m['max_dd'])} | "
        f"**MAR:** {m['mar']:.3f}",
        "",
        f"**Parameters:**",
        f"```json",
        json.dumps(display_params, indent=2),
        f"```",
        "",
        f"**Trades:** {m['trades']} total ({m['trades_yr']:.1f}/yr) | "
        f"**Win rate:** {_fmt_pct(m['win_rate'])}",
        "",
    ]

    # Exit reason breakdown
    reasons = m.get("exit_reasons", {})
    if reasons:
        lines.append("**Exit reasons:** " + ", ".join(f"{k}: {v}" for k, v in reasons.items()))
        lines.append("")

    # Trade list if available
    trade_list = entry.get("trades", [])
    if trade_list:
        lines.append("| Entry | Exit | PnL | Reason |")
        lines.append("|-------|------|-----|--------|")
        for t in trade_list[:10]:
            lines.append(f"| {t['entry_date']} | {t['exit_date']} | {t['pnl_pct']:+.1f}% | {t['exit_reason']} |")
        if len(trade_list) > 10:
            lines.append(f"| ... | +{len(trade_list) - 10} more | | |")
        lines.append("")

    return "\n".join(lines)


def _leaderboard_table(leaderboard: list) -> str:
    """Generate the all-time leaderboard table (top 20) with convergence status."""
    if not leaderboard:
        return "*No historical data yet.*"

    lines = []
    lines.append("| # | Strategy | vs B&H | CAGR | Max DD | MAR | Fitness | Status | Date |")
    lines.append("|---|----------|--------|------|--------|-----|---------|--------|------|")

    for i, entry in enumerate(leaderboard[:20], 1):
        m = entry.get("metrics", {})
        converged = entry.get("converged", False)
        rwi = entry.get("runs_without_improvement", 0)
        if converged:
            status = "CONVERGED"
        elif rwi > 0:
            status = f"{rwi} runs flat"
        else:
            status = "active"
        lines.append(
            f"| {i} "
            f"| {entry.get('strategy', '?')} "
            f"| {_fmt_mult(m.get('vs_bah', 0))} "
            f"| {_fmt_pct(m.get('cagr', 0))} "
            f"| {_fmt_pct(m.get('max_dd', 0))} "
            f"| {m.get('mar', 0):.3f} "
            f"| {_fmt_fitness(entry.get('fitness', 0))} "
            f"| {status} "
            f"| {entry.get('date', '?')} |"
        )
    return "\n".join(lines)


def generate_report(
    results: dict,
    run_dir: str,
    leaderboard: list | None = None,
    previous_best: dict | None = None,
    history_stats: dict | None = None,
) -> str:
    """
    Generate a full markdown report and save it to run_dir/report.md.

    Parameters
    ----------
    results : dict from evolve() — rankings, metadata, etc.
    run_dir : path to save report.md
    leaderboard : all-time top 20 list
    previous_best : best-ever before this run started
    history_stats : dict with reuse/new counts

    Returns the report text.
    """
    date = results.get("date", datetime.now().strftime("%Y-%m-%d"))
    rankings = results.get("rankings", [])
    elapsed = results.get("elapsed_hours", 0)
    total_evals = results.get("total_evaluations", 0)
    generations = results.get("generations", 0)
    n_strategies = len(set(r["strategy"] for r in rankings if r.get("metrics")))

    lines = []

    # Header
    lines.append(f"# Spike Report — {date}")
    lines.append("")
    lines.append(
        f"**Run:** {elapsed:.1f}h | "
        f"{total_evals:,} evals | "
        f"{generations:,} generations | "
        f"{n_strategies} strategies"
    )
    lines.append("")

    # Top 10 table
    lines.append("## Top 10")
    lines.append("")
    lines.append(_top_n_table(rankings, 10))
    lines.append("")

    # Detail blocks for top 3
    lines.append("## Top 3 — Details")
    lines.append("")
    for entry in rankings[:3]:
        if entry.get("metrics"):
            lines.append(_detail_block(entry))

    # vs Previous Best
    if previous_best and previous_best.get("fitness", 0) > 0:
        lines.append("## vs Previous Best")
        lines.append("")
        prev_name = previous_best.get("strategy", "?")
        prev_fitness = previous_best.get("fitness", 0)
        curr_best = rankings[0] if rankings else {}
        curr_fitness = curr_best.get("fitness", 0)
        curr_name = curr_best.get("strategy", "?")

        lines.append(f"- **Previous best:** {prev_name} (fitness {prev_fitness:.4f})")
        lines.append(f"- **This run's best:** {curr_name} (fitness {curr_fitness:.4f})")

        if curr_fitness > prev_fitness:
            delta = (curr_fitness / prev_fitness - 1) * 100
            lines.append(f"- **Improved by {delta:+.1f}%**")
        elif curr_fitness == prev_fitness:
            lines.append(f"- No change")
        else:
            delta = (curr_fitness / prev_fitness - 1) * 100
            lines.append(f"- No improvement ({delta:+.1f}%)")
        lines.append("")

    # All-time leaderboard
    if leaderboard:
        lines.append("## All-Time Leaderboard (Top 20)")
        lines.append("")
        lines.append(_leaderboard_table(leaderboard))
        lines.append("")

    # History stats
    if history_stats:
        lines.append("## Session Stats")
        lines.append("")
        lines.append(f"- New unique configs tested: {history_stats.get('new_configs', 0):,}")
        lines.append(f"- Configs reused from cache: {history_stats.get('cached_configs', 0):,}")
        lines.append(f"- Total configs in history: {history_stats.get('total_history', 0):,}")
        seeded = history_stats.get('seeded_per_strategy', 0)
        if seeded:
            lines.append(f"- Population seeded with {seeded} historical winners per strategy")
        lines.append("")

    report_text = "\n".join(lines)

    # Save
    os.makedirs(run_dir, exist_ok=True)
    report_path = os.path.join(run_dir, "report.md")
    with open(report_path, "w") as f:
        f.write(report_text)

    return report_text


if __name__ == "__main__":
    # Quick test: read most recent evolve results and generate a report
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if len(sys.argv) > 1:
        results_path = sys.argv[1]
    else:
        # Find most recent results.json in spike/runs/
        runs_dir = os.path.join(project_root, "spike", "runs")
        if not os.path.isdir(runs_dir):
            print("No runs directory found")
            sys.exit(1)
        run_dirs = sorted([d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))])
        if not run_dirs:
            print("No run directories found")
            sys.exit(1)
        latest = os.path.join(runs_dir, run_dirs[-1], "results.json")
        if not os.path.exists(latest):
            print(f"No results.json in {run_dirs[-1]}")
            sys.exit(1)
        results_path = latest

    with open(results_path) as f:
        results = json.load(f)

    run_dir = os.path.dirname(results_path)
    report = generate_report(results, run_dir)
    print(report)
    print(f"\nSaved to: {os.path.join(run_dir, 'report.md')}")

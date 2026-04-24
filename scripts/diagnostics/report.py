#!/usr/bin/env python3
"""
Auto-generate markdown reports from spike optimization results.

Called by spike_runner.py at the end of each run. No Claude tokens needed.

Usage:
    from diagnostics.report import generate_report
    generate_report(results_dict, run_dir, leaderboard_path)
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from search.share_metric import read_share_multiple


def _fmt_pct(val: float) -> str:
    return f"{val:.1f}%"


def _fmt_mult(val: float) -> str:
    return f"{val:.3f}x"


def _fmt_fitness(val: float) -> str:
    return f"{val:.4f}"


def _fmt_money(val: float) -> str:
    return f"${val:,.2f}"


def _share_mult(m: dict) -> float:
    """Back-compat wrapper for share-count metric reads."""
    return read_share_multiple(m)


def _top_n_table(rankings: list, n: int = 10) -> str:
    """Generate a markdown table of the top N results.

    Primary metric: `Share Mult.` — share-count multiplier vs B&H. Per charter
    (2026-04-13), this is the ranking metric. Tier column shows the effective
    validation tier (T0 / T1 / T2) the candidate was evaluated under.
    """
    lines = []
    lines.append(
        "| # | Strategy | Tier | Share Mult. | Marker | RS | CAGR | Max DD | MAR | Trades | Params | Fitness |"
    )
    lines.append(
        "|---|----------|------|-------------|--------|----|------|--------|-----|--------|--------|---------|"
    )

    for entry in rankings[:n]:
        m = entry.get("metrics")
        if not m:
            continue
        rs = m.get("regime_score", 0)
        n_params = m.get("n_params", "?")
        n_trades = m.get("trades", 0)
        tier = (entry.get("validation") or {}).get("tier") or entry.get("tier") or "T2"
        marker = entry.get("marker_alignment_score", 0.0)
        lines.append(
            f"| {entry['rank']} "
            f"| {entry['strategy']} "
            f"| {tier} "
            f"| {_fmt_mult(_share_mult(m))}"
            f"| {marker:.3f} "
            f"| {rs:.3f} "
            f"| {_fmt_pct(m['cagr'])} "
            f"| {_fmt_pct(m['max_dd'])} "
            f"| {m['mar']:.3f} "
            f"| {n_trades} "
            f"| {n_params} "
            f"| {_fmt_fitness(entry['fitness'])} |"
        )
    return "\n".join(lines)


def _raw_discovery_table(rankings: list, n: int = 10) -> str:
    lines = []
    lines.append("| # | Strategy | Tier | Share Mult. | Marker | Fitness | Trades |")
    lines.append("|---|----------|------|-------------|--------|---------|--------|")

    for entry in rankings[:n]:
        m = entry.get("metrics")
        if not m:
            continue
        tier = (entry.get("validation") or {}).get("tier") or entry.get("tier") or "T2"
        lines.append(
            f"| {entry['rank']} "
            f"| {entry['strategy']} "
            f"| {tier} "
            f"| {_fmt_mult(_share_mult(m))}"
            f"| {entry.get('marker_alignment_score', 0.0):.3f} "
            f"| {_fmt_fitness(entry.get('fitness', 0.0))} "
            f"| {m.get('trades', 0)} |"
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

    rs = m.get("regime_score", 0)
    hhi = m.get("hhi", 0)
    bull_cap = m.get("bull_capture", 0)
    bear_avoid = m.get("bear_avoidance", 0)
    n_params = m.get("n_params", "?")

    tier = (entry.get("validation") or {}).get("tier") or entry.get("tier") or "T2"
    lines = [
        f"### #{entry['rank']}: {entry['strategy']}  [`{tier}`]",
        "",
        f"**Share Mult. vs B&H:** {_fmt_mult(_share_mult(m))} | "
        f"**Marker alignment:** {entry.get('marker_alignment_score', 0.0):.3f} | "
        f"**Fitness:** {_fmt_fitness(entry['fitness'])}",
        "",
        f"**Regime Score:** {rs:.3f} (bull={bull_cap:.3f}, bear={bear_avoid:.3f}) | "
        f"**HHI:** {hhi:.3f} | "
        f"**Params:** {n_params}",
        "",
        f"**CAGR:** {_fmt_pct(m['cagr'])} | "
        f"**Max DD:** {_fmt_pct(m['max_dd'])} | "
        f"**MAR:** {m['mar']:.3f}",
        "",
        "**Parameters:**",
        "```json",
        json.dumps(display_params, indent=2),
        "```",
        "",
        f"**Trades:** {m['trades']} total ({m['trades_yr']:.1f}/yr) | "
        f"**Win rate:** {_fmt_pct(m['win_rate'])}",
        "",
    ]

    validation = entry.get("validation") or {}
    if validation:
        lines.append(
            f"**Validation:** {validation.get('verdict', '?')} | "
            f"**Composite:** {validation.get('composite_confidence', 0):.3f} | "
            f"**Verified Not Overfit:** {validation.get('certified_not_overfit', False)} | "
            f"**Backtest Certified:** {validation.get('backtest_certified', False)} | "
            f"**Promotion Ready:** "
            f"{validation.get('promotion_ready', validation.get('promotion_eligible', False))}"
        )
        if validation.get("critical_warnings"):
            lines.append(
                "**Critical warnings:** " + "; ".join(validation["critical_warnings"])
            )
        if validation.get("soft_warnings"):
            lines.append("**Soft warnings:** " + "; ".join(validation["soft_warnings"]))
        elif validation.get("warnings") and not validation.get("critical_warnings"):
            # Backward compat: old results without soft/critical split
            lines.append("**Warnings:** " + "; ".join(validation["warnings"]))
        if validation.get("hard_fail_reasons"):
            lines.append(
                "**Hard fails:** " + "; ".join(validation["hard_fail_reasons"])
            )
        lines.append("")

    marker_detail = entry.get("marker_alignment_detail") or {}
    if marker_detail:
        lines.append(
            f"**Marker detail:** accuracy={marker_detail.get('state_accuracy', 0):.3f} | "
            f"f1={marker_detail.get('f1', 0):.3f} | "
            f"transition_timing={marker_detail.get('transition_timing_score', 0):.3f} | "
            f"window={marker_detail.get('overlap_start', '?')} -> {marker_detail.get('overlap_end', '?')}"
        )
        lines.append("")

    # Exit reason breakdown
    reasons = m.get("exit_reasons", {})
    if reasons:
        lines.append(
            "**Exit reasons:** " + ", ".join(f"{k}: {v}" for k, v in reasons.items())
        )
        lines.append("")

    # Trade list if available
    trade_list = entry.get("trades", [])
    if trade_list:
        lines.append("| Entry | Exit | PnL | Reason |")
        lines.append("|-------|------|-----|--------|")
        for t in trade_list[:10]:
            lines.append(
                f"| {t['entry_date']} | {t['exit_date']} | {t['pnl_pct']:+.1f}% | {t['exit_reason']} |"
            )
        if len(trade_list) > 10:
            lines.append(f"| ... | +{len(trade_list) - 10} more | | |")
        lines.append("")

    return "\n".join(lines)


def _leaderboard_table(leaderboard: list) -> str:
    """Generate the all-time leaderboard table (top 20) with convergence status."""
    if not leaderboard:
        return "*No historical data yet.*"

    lines = []
    lines.append(
        "| # | Strategy | Tier | Share Mult. | RS | CAGR | Max DD | MAR | Fitness | Status | Date |"
    )
    lines.append(
        "|---|----------|------|-------------|----|------|--------|-----|---------|--------|------|"
    )

    for i, entry in enumerate(leaderboard[:20], 1):
        m = entry.get("metrics", {})
        converged = entry.get("converged", False)
        rwi = entry.get("runs_without_improvement", 0)
        if converged:
            status = "CONVERGED"
        elif rwi > 0:
            status = f"{rwi} flat"
        else:
            status = "active"
        rs = m.get("regime_score", 0)
        tier = (entry.get("validation") or {}).get("tier") or entry.get("tier") or "T2"
        lines.append(
            f"| {i} "
            f"| {entry.get('strategy', '?')} "
            f"| {tier} "
            f"| {_fmt_mult(_share_mult(m))}"
            f"| {rs:.3f} "
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
    previous_best : leaderboard #1 before this run started
    history_stats : dict with reuse/new counts

    Returns the report text.
    """
    date = results.get("date", datetime.now().strftime("%Y-%m-%d"))
    validated_rankings = results.get("validated_rankings", results.get("rankings", []))
    raw_rankings = results.get("raw_rankings", [])
    rankings = validated_rankings
    display_rankings = rankings if rankings else raw_rankings
    elapsed = results.get("elapsed_hours", 0)
    total_evals = results.get("total_evaluations", 0)
    generations = results.get("generations", 0)
    n_strategies = len(
        set(
            r["strategy"]
            for r in (raw_rankings or display_rankings)
            if r.get("metrics")
        )
    )
    validation_summary = results.get("validation_summary")
    champion = results.get("champion")
    artifacts = results.get("artifacts", {})

    # Derive run number from directory name
    run_num = os.path.basename(run_dir.rstrip("/"))

    lines = []

    # Header
    lines.append(f"# Spike Report — Run {run_num} ({date})")
    lines.append("")
    lines.append(
        f"**Run:** {elapsed:.1f}h | "
        f"{total_evals:,} evals | "
        f"{generations:,} generations | "
        f"{n_strategies} strategies"
    )
    lines.append("")

    if validation_summary:
        lines.append("## Validation Summary")
        lines.append("")
        lines.append(f"- Raw candidates: {validation_summary.get('raw_candidates', 0)}")
        lines.append(f"- Pre-tier3 pass: {validation_summary.get('pre_tier3_pass', 0)}")
        lines.append(
            f"- Fully validated pass: {validation_summary.get('validated_pass', 0)}"
        )
        lines.append(f"- Tier3 warns: {validation_summary.get('validated_warn', 0)}")
        lines.append(
            f"- Failed validation: {validation_summary.get('validated_fail', 0)}"
        )
        lines.append(
            f"- Tier3 budget: {validation_summary.get('tier3_minutes', 0)}m "
            f"@ pop {validation_summary.get('tier3_pop_size', 0)} "
            f"| N_eff: {validation_summary.get('null', {}).get('n_eff', 'n/a')}"
        )
        if champion:
            lines.append(
                f"- Champion: {champion.get('strategy', '?')} "
                f"(fitness {_fmt_fitness(champion.get('fitness', 0))}, "
                f"composite {champion.get('validation', {}).get('composite_confidence', 0):.3f})"
            )
        else:
            lines.append("- Champion: none - no entry passed full validation")
        if artifacts.get("trade_ledger"):
            lines.append(f"- Trade ledger: {artifacts['trade_ledger']}")
        if artifacts.get("signal_series"):
            lines.append(f"- Signal series: {artifacts['signal_series']}")
        if artifacts.get("equity_curve"):
            lines.append(f"- Equity curve: {artifacts['equity_curve']}")
        if artifacts.get("validation_summary"):
            lines.append(f"- Validation summary: {artifacts['validation_summary']}")
        if artifacts.get("dashboard_data"):
            lines.append(f"- Dashboard data: {artifacts['dashboard_data']}")
        if artifacts.get("overlay_report"):
            lines.append(f"- Overlay report: {artifacts['overlay_report']}")
        lines.append("")

    # Top 10 tables
    if validation_summary:
        lines.append("## Validated Top 10")
        lines.append("")
        if rankings:
            lines.append(_top_n_table(rankings, 10))
        else:
            lines.append("*No entries passed full validation. See raw results below.*")
        lines.append("")

        if raw_rankings:
            lines.append("## Discovery Top 10 (Pre-Validation)")
            lines.append("")
            lines.append(_raw_discovery_table(raw_rankings, 10))
            lines.append("")
    else:
        lines.append("## Top 10")
        lines.append("")
        lines.append(_top_n_table(rankings, 10))
        lines.append("")

    # Detail blocks for top 3
    lines.append("## Top 3 — Details")
    lines.append("")
    for entry in display_rankings[:3]:
        if entry.get("metrics"):
            lines.append(_detail_block(entry))

    overlay = champion.get("overlay") if champion else None
    if overlay:
        baseline = overlay.get("baseline", {})
        comparison = overlay.get("vs_tecl_dca", {})
        assumptions = overlay.get("assumptions", {})
        lines.append("## Roth Overlay")
        lines.append("")
        lines.append(
            f"- Contribution schedule: {assumptions.get('contribution_schedule', '?')} "
            f"at {_fmt_money(assumptions.get('monthly_contribution', 0.0))}/month "
            f"({_fmt_money(assumptions.get('annual_contribution', 0.0))}/year)"
        )
        lines.append(f"- Risk-off sleeve: {assumptions.get('risk_off_sleeve', 'SGOV')}")
        lines.append(
            f"- Simulation window: {assumptions.get('simulation_start', '?')} -> "
            f"{assumptions.get('simulation_end', '?')}"
        )
        lines.append(
            f"- Total contributions: {_fmt_money(overlay.get('total_contributions', 0.0))}"
        )
        lines.append(
            f"- Final account value: {_fmt_money(overlay.get('final_total_value', 0.0))} "
            f"(TECL {_fmt_money(overlay.get('final_tecl_value', 0.0))}, "
            f"SGOV {_fmt_money(overlay.get('final_sgov_value', 0.0))})"
        )
        lines.append(
            f"- Max drawdown: {_fmt_pct(overlay.get('max_drawdown_pct', 0.0))} | "
            f"Sweeps: {overlay.get('sweep_count', 0)} | "
            f"Avg cash lag: {overlay.get('avg_cash_deployment_lag_days', 0.0)} days"
        )
        lines.append(
            f"- vs TECL DCA: {_fmt_money(comparison.get('difference_value', 0.0))} "
            f"({comparison.get('difference_pct', 0.0):+.2f}%) "
            f"against baseline {_fmt_money(baseline.get('final_total_value', 0.0))}"
        )
        lines.append("")

    # vs Previous Best
    if previous_best and previous_best.get("fitness", 0) > 0:
        lines.append("## vs Previous Best")
        lines.append("")
        prev_name = previous_best.get("strategy", "?")
        prev_fitness = previous_best.get("fitness", 0)
        curr_best = display_rankings[0] if display_rankings else {}
        curr_fitness = curr_best.get("fitness", 0)
        curr_name = curr_best.get("strategy", "?")

        lines.append(f"- **Previous best:** {prev_name} (fitness {prev_fitness:.4f})")
        lines.append(f"- **This run's best:** {curr_name} (fitness {curr_fitness:.4f})")

        if curr_fitness > prev_fitness:
            delta = (curr_fitness / prev_fitness - 1) * 100
            lines.append(f"- **Improved by {delta:+.1f}%**")
        elif curr_fitness == prev_fitness:
            lines.append("- No change")
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
        lines.append(
            f"- New unique configs tested: {history_stats.get('new_configs', 0):,}"
        )
        lines.append(
            f"- Configs reused from cache: {history_stats.get('cached_configs', 0):,}"
        )
        lines.append(
            f"- Total configs in history: {history_stats.get('total_history', 0):,}"
        )
        seeded = history_stats.get("seeded_per_strategy", 0)
        if seeded:
            lines.append(
                f"- Population seeded with {seeded} historical winners per strategy"
            )
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
        run_dirs = sorted(
            [
                d
                for d in os.listdir(runs_dir)
                if os.path.isdir(os.path.join(runs_dir, d))
            ],
            key=lambda d: int(d) if d.isdigit() else d,
        )
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

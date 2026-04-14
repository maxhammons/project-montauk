# /spike Skill — About

## What it does

The Spike skill launches and runs the **Montauk Engine** — Project Montauk's autonomous evolutionary strategy optimizer + tier-routed validator + Pine generator. It tests hundreds of thousands of parameter combinations across multiple TECL strategies using a genetic algorithm, with the goal of accumulating more shares of TECL than buy-and-hold while matching the hand-marked cycle shape in `data/markers/TECL-markers.csv`.

> Spike = the entrypoint / command surface (`/spike`, `/spike-focus`, `/spike-results`).
> Montauk Engine = the underlying machinery (search + tier-routed validation + Pine emission).

## Architecture

```
Claude (pre-run)              GitHub Actions (autonomous)
────────────────              ──────────────────────────
Study leaderboard             spike_runner.py
Write/prune strategies  →       └─ evolve.py
Commit & push                      ├─ Load hash index (dedup)
Trigger workflow                   ├─ Baseline eval all strategies
                                   ├─ Auto-prune underperformers
                                   ├─ Evolutionary loop per strategy:
                                   │    ├─ Evaluate population (60 configs)
                                   │    ├─ Select top performers
                                   │    ├─ Crossover + mutate
                                   │    └─ Repeat for hours
                                   ├─ Update leaderboard + hash index
                                   └─ Generate report
                              Commit results to spike/runs/ & push

Claude (post-run)
─────────────────
git pull
Read report
Generate Pine Script for #1 winner
```

## Why evolutionary?

Each backtest takes ~0.03ms. Over 5 hours that's ~600,000 evaluations. An evolutionary algorithm naturally converges on good parameter regions while adaptive mutation prevents local optima. Zero Claude tokens spent during optimization.

## Files

| File | Role |
|------|------|
| `scripts/strategies.py` | Strategy library — all strategy functions + registry |
| `scripts/strategy_engine.py` | Backtest engine + indicator cache |
| `scripts/evolve.py` | Evolutionary optimizer + convergence tracking |
| `scripts/spike_runner.py` | Main entry point — creates run dir, tees output |
| `scripts/report.py` | Auto-generates markdown reports |
| `spike/leaderboard.json` | All-time top 20 strategies |
| `spike/hash-index.json` | Compact dedup index: {hash: fitness} |
| `spike/runs/NNN/` | Per-session output (report.md, results.json, log.txt) |

## Anti-overfitting

The Montauk Engine's defense against overfitting is **tier-routed validation** — validation difficulty scales with how the candidate was selected (T0 hypothesis vs T1 tuned vs T2 discovered). See `docs/validation-philosophy.md` for the framework.

Existing in-engine defenses:

- Fitness penalizes high drawdown
- Hash-based dedup prevents re-testing identical configs
- Auto-pruning removes strategies that can't beat baseline after 2 runs
- Convergence tracking flags strategies that plateau after 3 runs
- Cross-asset validation runs at every tier as the cheapest, highest-power honesty check

> **Note (2026-04-13):** The "excessive trade frequency" penalty in the current fitness function is being removed — low trade frequency is a feature for a regime strategy, not a flaw. Tier routing has not yet been implemented in code.

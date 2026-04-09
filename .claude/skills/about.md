# /spike Skill — About

## What it does

The spike skill runs an autonomous evolutionary strategy optimizer for Project Montauk. It tests hundreds of thousands of parameter combinations across multiple trading strategies for TECL, using a genetic algorithm to converge on configurations that maximize fitness (beat buy-and-hold with low trade frequency).

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

- Fitness penalizes high drawdown and excessive trade frequency
- Strategies must produce 3+ trades to score above zero
- Hash-based dedup prevents re-testing identical configs
- Auto-pruning removes strategies that can't beat baseline after 2 runs
- Convergence tracking flags strategies that plateau after 3 runs

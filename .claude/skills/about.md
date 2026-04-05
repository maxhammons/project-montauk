# /spike Skill — About

## What it does

The spike skill runs an autonomous evolutionary strategy optimizer for Project Montauk. It tests thousands of parameter combinations for the Montauk 8.2.1 TECL trading strategy, using a genetic algorithm to converge on configurations that maximize regime score (how well the strategy captures bull markets and avoids bear markets).

## Architecture

```
Claude (orchestrator)          Python (compute)
─────────────────────          ─────────────────
Launch spike_auto.py    →      Baseline evaluation
                               Parameter sweeps (seed population)
Wait / monitor progress        Evolutionary loop:
                                 ├─ Evaluate population (~50 configs)
                                 ├─ Select top performers
                                 ├─ Crossover (combine winners)
                                 ├─ Mutate (random perturbations)
                                 ├─ Enforce constraints
                                 └─ Repeat for hours
                               Walk-forward validation of top 5
Read results            ←      Write results JSON + best-ever
Generate Pine diffs
Write report
Commit & push
```

## Why evolutionary?

The previous spike skill (v3) had Claude run one parameter test at a time — each test cost tokens for the command, output parsing, state management, and decision-making. Even with Sonnet, this limited throughput to ~100 tests per 8-hour session.

By moving the optimization loop into Python:
- Each backtest takes ~50ms (not minutes of Claude overhead)
- 8 hours = 500,000+ evaluations (vs ~100 with Claude orchestration)
- Zero tokens spent on per-test decisions
- Evolutionary algorithm naturally converges on good parameter regions
- Adaptive mutation prevents getting stuck in local optima

## Files

| File | Role |
|------|------|
| `scripts/spike_auto.py` | Autonomous evolutionary optimizer |
| `scripts/backtest_engine.py` | Python replica of Montauk 8.2.1 strategy |
| `scripts/validation.py` | Walk-forward validation framework |
| `scripts/run_optimization.py` | Manual CLI for individual tests |
| `scripts/generate_pine.py` | Convert winning params to Pine Script diffs |
| `scripts/spike_state.py` | Legacy state management (v3 skill) |
| `remote/best-ever.json` | Best config found across all sessions |
| `remote/spike-results-*.json` | Per-session detailed results |
| `remote/spike-progress.json` | Live progress during a run |

## Signal queue (`scripts/signal_queue.json`)

A pre-built queue of 20 signal proposals, each with:
- Toggle name, parameter ranges, default values
- Logic pseudocode and implementation sketch
- Which part of the engine it wires into (entry gate or exit condition)
- Status: `implemented` (IDs 1-8) or `queued` (IDs 9-20)

Queued signals cover: Bollinger width gate, EMA fan alignment, MACD histogram gate, min-move re-entry filter, higher-lows structure gate, distance-from-mean guard, realized vol exit, EMA slope deceleration exit, RSI overbought exit, volume dry-up gate, breakout proximity gate, consecutive down-bar exit.

Claude's job during Phase 2 is to pick the next queued signal, implement it (~30 lines in backtest_engine.py), add its params to spike_auto.py's search space, mark it implemented, and re-launch the optimizer.

## Search space

The optimizer explores ~30 numeric parameters and 10 boolean toggles across the Montauk strategy's entry/exit filters. Core architecture (EMA cross entry, trend filter, primary exits) stays fixed. Optional features (trailing stop, TEMA exit, volume spike exit, ADX filter, bear depth guard, etc.) are toggled on/off and their thresholds optimized. The search space grows each time a queued signal is implemented.

Constraints are enforced automatically (e.g., short EMA < medium EMA, disabled toggles reset their numeric params to defaults).

## Anti-overfitting

- Quality penalties in fitness: too few trades, excessive churn, high false signal rate
- Walk-forward validation of top candidates across 4 time windows
- Stability check: small param changes shouldn't cause large result swings
- The optimizer targets regime score (structurally robust metric) not raw returns

# Project Montauk — Project Status

> As of 2026-04-13

---

## 1. Current Project Identity

The project is no longer best described as "an EMA strategy with some optimizer scripts around it."

The correct framing is:

> Project Montauk is a TECL share-accumulation factory: discover long-only TECL strategies that match the hand-marked cycle shape, validate them at the tier appropriate to how they were selected, and generate Pine for the best PASS winner.

That is now the standard the codebase should be measured against.

---

## 2. What Is True Today

### Discovery is real

The repo can search across multiple TECL strategy families rather than only tuning `montauk_821`. The optimizer (Spike → Montauk Engine) is operational with a reusable hash index, leaderboard, and chunked iterative mode.

### Promotion gating exists in the canonical full-run path

The local full-run flow distinguishes between:

- raw optimizer output
- validated output

Only validated PASS entries are intended to become promotable memory.

### Pine generation exists

The repo can generate Pine candidates for validated winners, with a Montauk-specific patch path for `montauk_821`.

### Deployment-context modeling exists as a separate concern

The Roth overlay model can sit on top of a validated binary TECL signal without changing the identity of the strategy.

---

## 3. What Just Changed (2026-04-13 charter revision)

The spirit-guide was revised to address a structural mismatch: the validation framework was calibrated for high-DOF GA winners and was being applied uniformly to all candidates, including simple human-authored hypotheses. This punished the wrong thing and effectively closed the door on small, conceptually motivated strategies.

The revision introduces:

- **Share-count multiplier vs B&H** as the primary metric (replacing dollar `vs_bah` as the optimization target)
- **Marker shape alignment** as a first-class validation gate (replacing the ±5% soft-prior nudge)
- **Three validation tiers**: T0 (Hypothesis), T1 (Tuned), T2 (Discovered) with strict canonical parameter set for T0
- **Tier routing**: validation difficulty matches selection bias
- **Removal of trade-frequency punishment** for low-trade strategies
- **Naming**: Spike is the skill; Spike launches and runs the Montauk Engine

The existing T2 statistical stack stays intact. It is not wrong — it is just being scoped to its actual job (large-search-budget candidates).

---

## 4. What Is Still Incomplete

### Tier routing — implemented (2026-04-13)

`canonical_params.py` defines the strict canonical set plus `effective_tier()`. `strategies.STRATEGY_TIERS` carries the declared tier per strategy (all current entries default to T2). `validation/pipeline.py` routes by tier in `_validate_entry`: T0 skips gates 2/3/5, T1 skips gates 2/5, T2 runs the full stack. All three tiers run gate 1 (tier-aware thresholds), the marker gate, gate 4 (walk-forward), and gate 6 (cross-asset). The composite confidence renormalizes over present gates.

### Marker shape gate — implemented (2026-04-13)

`_gate_marker_shape` in `validation/pipeline.py` runs for every tier. Reuses `discovery_markers.score_marker_alignment`. Thresholds: T0 state_agreement ≥ 0.75 + 0 missed cycles; T1 ≥ 0.70 + ≤ 1; T2 ≥ 0.65 + ≤ 2. Failure is a hard fail at gate level, not a nudge.

### Share-count metric — implemented (2026-04-13)

Math identity established: `vs_bah_multiple` equals share-count multiplier when equity is marked-to-market. `strategy_engine.BacktestResult` now exposes `share_multiple` as the primary name. Fitness formula renamed and reframed. `trade_scale` low-trade penalty removed. `discovery_score_value` retired as a nudge — now an alias for fitness so the marker operates at the gate level instead.

### Python-to-Pine trust is not fully closed

Pine candidates are generated, but the project still needs formal parity confidence between Python strategy logic, emitted Pine logic, and actual TradingView compile / runtime behavior.

### Final deployment is still manual

Acceptable for now. The factory ends at validated champion → Pine candidate → manual TradingView review, not autonomous live deployment.

---

## 5. Current Strategic Risks

### Validation gates that don't fit the candidate

Until tier routing lands in code, the project will continue to over-validate simple hypotheses and under-validate large-search winners. The new spirit-guide defines the right structure; the scripts don't yet enforce it.

### Strategy-family concentration is still a real risk

If too much of the validated memory depends on one idea cluster, the project can fool itself into thinking it has diversity when it only has variants.

### Documentation / code drift

The next implementation sprint must close the gap between what the spirit-guide now requires and what the scripts actually do. Until then, the docs lead the code.

---

## 6. Immediate Priorities

1. ~~Implement T0 / T1 / T2 tier routing in the validation pipeline.~~ ✓ 2026-04-13
2. ~~Implement strict canonical parameter set check for T0.~~ ✓ 2026-04-13 (`canonical_params.py`)
3. ~~Add share-count multiplier as the primary metric.~~ ✓ 2026-04-13 (math identity — already computed as `vs_bah_multiple`, renamed and reframed)
4. ~~Promote marker shape alignment to a first-class validation gate at every tier.~~ ✓ 2026-04-13 (`_gate_marker_shape`)
5. ~~Remove low-trade-frequency punishment from fitness and gates.~~ ✓ 2026-04-13 (`trade_scale` removed; gate1 tier-aware)
6. Author a real T0 hypothesis strategy (e.g. EMA-200 crossover with canonical params) to exercise the T0 pipeline end-to-end.
7. Update the `VALIDATION-THRESHOLDS.md` doc to split per tier now that the code supports it.
8. Add formal Python-vs-Pine parity checks.
9. Keep the leaderboard PASS-only, with tier tags.

---

## 7. Plain-English Summary

Project Montauk already behaves like a promising strategy factory.

What it still needs is to become a **trustworthy and productive** strategy factory:

- broad discovery (search) AND fast hypothesis iteration (T0)
- tier-routed validation that matches selection bias
- the marker chart as the working definition of success
- share-count accumulation as the goal
- PASS-only promotion across all tiers
- Pine output for the real winner
- deployment analysis that sits downstream of validation instead of corrupting it

That is the line between "interesting research repo" and "rock-solid guiding system."

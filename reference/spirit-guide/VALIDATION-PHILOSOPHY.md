# Project Montauk — Validation Philosophy

> Raw optimizer output is research. Validation decides what is real.

---

## 1. Why Validation Exists

Project Montauk is trying to discover robust long-only TECL strategies from a large search space. That means overfitting is the default failure mode.

The optimizer is good at finding historical winners. The validation system exists to answer a harder question:

> Is this strategy probably real, or is it just the luckiest thing we found on one historical path?

If the project cannot answer that question honestly, the rest of the factory does not matter.

Discovery may use soft priors to express project taste. Validation exists to keep those priors from becoming promotion bias.

---

## 2. The Core Rule

A raw optimizer winner is **not** a winner.

A strategy only becomes real when it receives a final **PASS** verdict from the validation pipeline.

That rule has operational consequences:

- **PASS**: eligible for leaderboard promotion, champion selection, and Pine generation
- **WARN**: useful research output, but not promotable
- **FAIL**: archive only, keep searching

The leaderboard is therefore a memory of validated PASS results, not a scrapbook of impressive raw backtests.

---

## 3. What Validation Must Prove

Validation is trying to prove four things:

1. The strategy is not obviously underdetermined or degenerate.
2. The strategy still works when time period and regime context change.
3. The strategy logic is not TECL-noise cosplay.
4. The strategy is stable enough to deserve a Pine deployment artifact.

If any of those fail, the project should not promote the strategy.

---

## 4. Canonical Validation Stack

The intended validation stack for Project Montauk is:

### Stage 0 — Run and search integrity

Before the project reasons about a candidate, it must make sure the run itself is valid and the search is not garbage-in:

- canonical datasets are present
- backtest realism settings are active
- candidate families stay inside charter guardrails
- obvious junk is rejected cheaply during search

This stage exists to protect the rest of the pipeline from invalid context.

### Stage 1 — Candidate eligibility

Cheap structural rejection before deeper analysis:

- trade sufficiency
- trade frequency discipline
- complexity vs evidence
- obvious degeneracy checks

These checks stop weak candidates from wasting validation time, but they do **not** prove robustness.

### Stage 2 — Statistical overfit checks

The first serious screen:

- deflation / selection-bias correction
- exit-boundary proximity
- delete-one-cycle jackknife
- concentration and dominance checks
- regime-definition meta-robustness
- temporal clustering checks

This is the first place the project asks whether a high score is distinguishable from search noise.

### Stage 3 — Parameter and time robustness

The strategy must survive changed market windows:

- parameter fragility analysis
- walk-forward validation
- named stress windows

The point is not perfection. The point is avoiding “worked once, on that exact slice, for reasons we do not trust.”

### Stage 4 — Uncertainty and concept generalization

The strategy logic must be stronger than one lucky path or one set of TECL-tuned parameters:

- uncertainty and interaction checks
- same-parameter cross-asset checks
- re-optimization of the winning strategy family on TQQQ

Cross-asset work is for validation only. Production scope remains TECL.

### Stage 5 — Deployment eligibility

A strategy is only deployment-eligible when:

- it still satisfies the charter guardrails: TECL-only, long-only, single-position, Pine-expressible
- final verdict is **PASS**
- it is allowed onto the validated leaderboard
- it can be emitted as a Pine Script candidate for TradingView

If the project cannot generate Pine for the winner, the factory is incomplete.

The spirit-guide defines the stack and its purpose. The exact thresholds, formulas, budgets, and implementation details belong in the validation scripts.

After a strategy clears validation, the project may run deployment-context analysis such as the Roth cashflow overlay. That happens after the PASS decision. It does not create PASS by itself.

---

## 5. Principles

1. **Validation is mandatory.** It is not a post-hoc extra.
2. **PASS only gets promoted.** A high raw score does not outrank a failed validation.
3. **Research is the spec.** Validation rules should move toward the strongest defensible statistical standard the repo can support.
4. **Honesty beats excitement.** A strategy that looks great but fails validation is not “almost ready.” It is rejected.
5. **The output must be deployable.** The end product is not a JSON blob. It is a Pine candidate for the best PASS winner.
6. **Deployment overlays are downstream.** They may inform how a validated winner is used, but they do not replace validation.

---

## 6. Current Direction

The project already has the beginnings of the right validation culture:

- integrity checks
- candidate gating
- a statistical validation suite
- fragility and time-robustness checks
- cross-asset validation work
- full-run promotion gating in the local `spike_runner` flow

What still matters is finishing the job:

- tighter parity confidence between Python and Pine
- continued hardening of the statistical governor
- continued refinement of validation confidence signals
- formal Python-vs-Pine parity tests

Those are improvements to the same principle, not a change in philosophy.

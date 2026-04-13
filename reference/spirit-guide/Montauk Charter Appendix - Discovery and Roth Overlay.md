# Project Montauk Charter Appendix — Discovery and Roth Overlay

This appendix defines two approved supporting layers around the core charter:

- the marker-aligned discovery north star (formalization of Section 3 of the charter)
- the post-validation Roth cashflow overlay

Neither layer changes the core identity of Project Montauk. The project remains a TECL signal factory whose real winners are validated PASS strategies with Pine artifacts.

---

## 1. Marker-Aligned Discovery

The hand-marked TECL cycle file [`reference/research/chart/TECL-markers.csv`](../research/chart/TECL-markers.csv) is the **north star** for discovery, ranking, and validation.

It is no longer a soft prior. The earlier framing (a ±5% nudge on raw fitness) understated the role the marker chart should play. The marker chart is the project's working definition of what "good cycle timing" looks like.

### How the marker chart is used

1. **Target series construction.** The marker buy / sell points are converted into a bar-level `risk_on` / `risk_off` target series across the full TECL history.
2. **Shape alignment metric.** Every candidate's bar-level state series is compared to the marker target. Three numbers are recorded:
   - `state_agreement` — fraction of bars where candidate state equals marker state
   - `median_transition_lag` — median absolute distance between candidate and marker transitions, measured in bars
   - `missed_cycles` — count of marker cycles the candidate did not engage with at all
3. **Validation gate.** Marker shape alignment is a first-class **validation gate at every tier** (T0, T1, T2). Threshold values live in the validation scripts.
4. **Discovery ranking.** Raw discovery ranking uses share-count multiplier as the primary signal and marker shape alignment as a strong tie-breaker. The earlier `0.95 + 0.10 * marker_alignment` formula is retired.

### What the marker chart is not

- it is not a source of truth about exact trade dates (hindsight-perfect cycle calls are not realistic)
- it is not a substitute for the validation pipeline
- it is not a reason to promote a strategy that fails its tier gates

A strategy that nails the marker shape but fails on cross-asset is not real. A strategy that fails marker alignment but beats `vs_bah` is doing something other than what the project is trying to do — it is also not promotable.

---

## 2. Roth Cashflow Overlay

The approved Roth overlay is an **account-management layer**, not the identity of the strategy.

The core signal remains binary:

- risk-on: TECL is allowed
- risk-off: TECL is not allowed

The Roth overlay applies fixed contribution timing on top of that binary signal:

- contributions continue on schedule
- when risk-off, contributions go to the approved cash sleeve
- when risk-on, contributions go to TECL
- when the signal flips back to risk-on, accumulated sleeve capital may be swept into TECL

The default risk-off sleeve is `SGOV`.

This overlay is approved because it fits the real operating context of a Roth account while preserving the integrity of the core signal engine.

---

## 3. What The Overlay Is Not

The Roth overlay is not:

- a change to the charter's signal scope
- partial-position strategy logic
- variable legal contribution logic
- a replacement for validation
- a reason to weaken Pine or signal discipline

The strategy still needs to stand on its own as a binary TECL signal before any overlay is applied.

---

## 4. Pine Boundary

Pine remains the signal execution artifact.

That means:

- Pine should expose the normalized risk state
- Pine should not encode Roth contribution scheduling
- account-level cashflow allocation stays in Python / account simulation, not in Pine

This preserves a clean separation between:

- signal generation
- validation
- account deployment analysis

---

## 5. Governance Rule

If there is ever tension between:

- making the signal look better by using the overlay
- keeping the signal honest and validation-clean

the honest signal wins.

The overlay exists to model deployment context, not to rescue a weak strategy.

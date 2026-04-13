# Project Montauk Charter Appendix — Discovery and Roth Overlay

This appendix defines two approved supporting layers around the core charter:

- the marker-aligned discovery north star (formalization of Section 3 of the charter)
- the post-validation Roth cashflow overlay

Neither layer changes the core identity of Project Montauk. The project remains a TECL signal factory whose real winners are validated PASS strategies with Pine artifacts.

---

## 1. Marker-Aligned Discovery

The hand-marked TECL cycle file [`reference/research/chart/TECL-markers.csv`](../research/chart/TECL-markers.csv) is a **north star for hypothesis design and a diagnostic for ranking** — not a hard validation gate.

History note: an earlier revision (first 2026-04-13 charter rewrite) made marker alignment a first-class hard gate at every tier. That overcorrected — it caused strategies that maximize share count via different but valid cycle shapes to fail solely on "doesn't match Max's drawing." Per the second 2026-04-13 revision, the marker is back to being directional guidance plus a diagnostic, not the bouncer at the door.

### How the marker chart is used

1. **Target series construction.** The marker buy / sell points are converted into a bar-level `risk_on` / `risk_off` target series across the full TECL history.
2. **Shape diagnostic metrics.** Every candidate's bar-level state series is compared to the marker target. The following are recorded for ranking and reports:
   - `state_agreement` — fraction of bars where candidate state equals marker state
   - `transition_timing` — how close candidate transitions are to marker transitions
   - `missed_cycles` — count of marker cycles the candidate did not engage with
   - `marker_score` — composite of the above
3. **Soft / critical warnings (not hard fails).**
   - `state_agreement < 0.30` → critical warning (essentially uncorrelated with markers)
   - `state_agreement < 0.50` → soft warning (barely above random)
   - other thresholds → informational
4. **Hypothesis design prior.** When authoring a new T0 strategy, Claude reads `T0-DESIGN-GUIDE.md` which uses marker engagement as a design heuristic. This is upstream of validation — it shapes what gets *proposed*, not what gets *promoted*.
5. **Composite confidence.** Marker score still contributes to the geometric composite that drives ranking and the WARN/PASS threshold.

### What the marker chart is not

- it is not a source of truth about exact trade dates
- it is not a substitute for the charter share-multiplier and trades-per-year gates
- it is not a reason to reject a strategy that maximizes share count within charter constraints

A strategy that beats B&H share count, holds trades ≤5/yr, survives cross-asset and walk-forward, and has reasonable marker alignment (state_agreement ≥ 0.30) is a valid winner — even if it trades a different cycle shape than the markers describe.

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

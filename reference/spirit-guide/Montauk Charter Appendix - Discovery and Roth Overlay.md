# Project Montauk Charter Appendix — Discovery and Roth Overlay

This appendix defines two approved supporting layers around the core charter:

- a discovery-stage marker prior
- a post-validation Roth cashflow overlay

Neither layer changes the core identity of Project Montauk. The project remains a TECL signal factory whose real winners are validated PASS strategies with Pine artifacts.

---

## 1. Discovery-Stage Marker Prior

The hand-marked TECL cycle file is an approved **soft prior** for discovery.

Its purpose is to lightly steer search toward the kind of low-frequency bull/bear regime capture the project is trying to find:

- major bull-leg participation
- major bear-phase avoidance
- infrequent, high-conviction transitions

The marker prior is allowed to influence raw discovery ranking and search preference.

It is **not**:

- a validation gate
- a promotion rule
- a source of truth about exact trade dates
- a reason to promote a weak strategy

The optimizer may prefer marker-aligned strategies, but only validation decides what is real.

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

- a change to the charter’s signal scope
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
- account-level cashflow allocation stays in Python/account simulation, not in Pine

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

# Project Montauk Discovery + Roth Overlay Plan

> **Status (2026-04-13):** The marker-prior section of this plan is **superseded** by the 2026-04-13 charter revision. Marker alignment is now a first-class validation gate at every tier, not a ±5% soft-prior nudge on raw fitness. See `validation-philosophy.md` and `charter-appendix.md` for the current framing. The Roth overlay sections below remain the active plan.

## Summary

Keep the core Montauk mission unchanged: discover robust long-only TECL signals, validate them at the tier appropriate to how they were selected, and emit a `backtest_certified` signal bundle for the best PASS winner. Two supporting layers sit around that core:

- a **marker-aligned discovery north star** — the hand-marked TECL cycles in [TECL-markers.csv](../data/markers/TECL-markers.csv) define the working shape of success, and shape alignment is a validation gate
- a **post-validation Roth account overlay** that routes ongoing Roth cash into `SGOV` when risk-off and into `TECL` when risk-on

The core strategy remains a binary TECL in/out engine. The Roth cashflow layer is an approved deployment overlay on top of any charter-compatible PASS winner.

## Key Changes

### 1. Marker as north star (supersedes earlier soft-prior plan)

- Parse the marker buy/sell points into a bar-level `risk_on` / `risk_off` target series across the full TECL history.
- For every candidate, compute and persist:
  - `state_agreement` — fraction of bars where candidate state matches marker state
  - `median_transition_lag` — median absolute distance between candidate and marker transitions, in bars
  - `missed_cycles` — count of marker cycles the candidate did not engage with at all
- Use these as a **first-class validation gate at every tier (T0 / T1 / T2)**. Threshold values live in the validation scripts.
- Use share-count multiplier vs B&H as the **primary** raw discovery ranking signal. Use marker shape alignment as a strong tie-breaker in raw ranking.
- The earlier `discovery_score = fitness * (0.95 + 0.10 * marker_alignment_score)` formula is retired.

### 2. Add a binary Roth cashflow overlay after validation

- Treat Roth cashflow as an **account overlay**, not part of the core signal definition.
- Apply the overlay only to validated winners, starting with the champion.
- Model a fixed contribution schedule with variable allocation:
  - contributions continue on schedule regardless of risk state
  - when risk-off, contributions go into `SGOV`
  - when risk-on, contributions go directly into `TECL`
  - on a buy transition, sweep the full `SGOV` sleeve into `TECL`
  - on a sell transition, liquidate `TECL` and move proceeds into `SGOV`
- Make the overlay binary in v1:
  - no risk bands
  - no partial scaling
  - no accelerated contribution multipliers
  - no “slow buy” mode
- Default overlay assumptions:
  - annual contribution default: `$7,500`
  - monthly schedule
  - contribution date: first trading day of each month
  - risk-off sleeve: `SGOV`
  - signal-triggered reallocations execute on the same bar-close convention as the core signal engine
- Add a dedicated account-level simulator rather than forcing this into the core backtest engine.
- Require overlay compatibility only for charter-compatible single-position binary strategies; that should cover all promotable winners.

### 3. Pipeline placement and outputs

- Update the canonical flow to:
  - discover with marker prior
  - validate the core TECL signal
  - simulate the Roth overlay for the validated champion
  - emit the `backtest_certified` signal bundle (five JSON artifacts + native HTML viewer) for the validated champion
  - manually execute from the daily risk_on / risk_off signal
- Do not make overlay results a validation gate in v1. Validation stays about signal honesty and robustness; the overlay is a deployment/account analysis layer.
- Extend `results.json` with:
  - `raw_rankings[*].marker_alignment_score`
  - `raw_rankings[*].discovery_score`
  - `raw_rankings[*].marker_alignment_detail`
  - `champion.overlay`
  - `artifacts.overlay_report` if a separate overlay artifact is produced
- Extend `report.md` with:
  - a discovery section showing marker alignment on top raw candidates
  - an overlay section for the validated champion
  - comparison against a baseline `TECL DCA` account
- Add a standard `risk_state` output to the emitted signal bundle:
  - `risk_on` means TECL is allowed
  - `risk_off` means SGOV holding-tank state
- Do not encode Roth contribution mechanics inside the signal engine. The signal engine exposes state only (via `signal_series.json`); the contribution allocator remains an account-overlay concept (`scripts/roth_overlay.py`).

### 4. Data and docs

- Generalize the data layer to support `SGOV` as a first-class local dataset with refresh behavior matching the other validation/deployment assets.
- Add a charter appendix and spirit-guide updates that say:
  - the core charter remains TECL signal discovery
  - hand-marked TECL cycles are an approved soft discovery prior
  - Roth contributions continue on schedule
  - `SGOV` is the approved risk-off holding tank in the deployment overlay
  - the overlay is account management, not strategy identity
- Keep the main charter summary unchanged.

## Public Interfaces / Contracts

- Raw discovery results gain:
  - `marker_alignment_score: float`
  - `discovery_score: float`
  - `marker_alignment_detail: object`
- Add an account overlay result object for the champion:
  - contribution assumptions
  - total contributions
  - final TECL value
  - final SGOV value
  - final total account value
  - max drawdown
  - sweep count
  - average cash deployment lag
  - comparison vs `TECL DCA`
- Signal-bundle contract stays strategy-signal-only — every emitted `signal_series.json` exposes a normalized `risk_state` series.

## Test Plan

- Marker parsing:
  - marker CSV loads into alternating buy/sell cycles without ambiguity
  - bar-level target `risk_on` state is correct across the full overlap window
- Discovery behavior:
  - two otherwise similar candidates with different marker alignment get appropriately different `discovery_score`
  - marker prior cannot rescue a zero-fitness or clearly poor strategy
  - raw rankings sort by `discovery_score`, while validation/leaderboard rules remain PASS-only
- Overlay simulation:
  - risk-off contributions route to `SGOV`
  - buy transitions sweep the full `SGOV` sleeve into `TECL`
  - in-position contributions route directly to `TECL`
  - sell transitions move proceeds back to `SGOV`
  - overlay works unchanged for at least two different binary strategy families
- Reporting and artifacts:
  - `results.json` contains discovery and overlay sections
  - `report.md` shows marker-alignment diagnostics and champion overlay metrics
  - the emitted `signal_series.json` exposes `risk_state` without embedding account-specific contribution logic
- Governance:
  - spirit-guide and charter appendix describe the marker prior and Roth overlay consistently
  - validation gates remain about core strategy robustness, not account cashflow

## Assumptions and Defaults

- Marker alignment is a **soft prior only**.
- Cashflow overlay is a **charter appendix**, not a main-charter rewrite.
- Contributions are fixed on schedule; allocation varies by risk state.
- `SGOV` is the canonical risk-off holding tank.
- v1 overlay is binary only; no partial risk bands, no accelerated buying multipliers, no slow-buy mode.
- Overlay simulation runs for the validated champion, not for every raw candidate.
- Validation stays signal-first; overlay results are informative and deployment-facing, not a PASS gate in v1.

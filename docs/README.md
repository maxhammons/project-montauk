# docs/ — map

**North star**: discover long-only TECL strategies that accumulate more shares
than buy-and-hold, certify only what survives honest anti-overfit statistics
(Gold = fit to trade, beats B&H in every era, full falsifiable system
confidence), and execute manually from the daily risk_on/risk_off signal.

Reorganized 2026-06-09 (audit: grouped app docs, archived one-time reports,
fixed stale links). Keep this map accurate when adding files.

## Governance (change only by explicit decision — never by code drift)
- `charter.md` — mission, guardrails, success definition
- `charter-appendix.md` — discovery north star + Roth overlay extensions

## Active reference (how the system judges)
- `validation-thresholds.md` — **authoritative** gates, weights, anchors, Gold contract, live-demotion rule
- `validation-philosophy.md` — why the framework is shaped this way (where it disagrees with thresholds, thresholds wins)
- `design-guide.md` — strategy-authoring pre-flight (banner marks sections describing the retired framework)
- `pipeline.md` — visual source of truth for the whole flow (2026-06-09 addendum covers the search-engine upgrades)

## Status
- `project-status.md` — current implementation state; §2b is the 2026-06-09 remediation record

## Backlog — `*NEXT/`
Canonical outstanding work.
- `Montauk 3.0/` — **the forward vision**: a TECL-only always-on *appliance* server
  that runs the deterministic idea→Gold pipeline 24/7 behind a **bulletproof
  validation engine** (the north star), refreshes its own data, hosts the app,
  watches for signal flips, and breeds chimeras. Start at `Montauk 3.0/README.md`;
  governing draft `Montauk 3.0/charter.md`; resolved calls `Montauk 3.0/decisions.md`;
  the validation hardening plan `Montauk 3.0/validation-engine-hardening.md`. Pillars:
  idea-to-gold conveyor, meta-strategy chimeras, iOS companion.
- `Montauk 4.0/` — **the next release after 3.0**: trading beyond TECL long/flat — a
  wider action space (SGOV leg / sizing / shorts) and a multi-sector rotation fleet.
  Deferred until 3.0 is real.
- `archive/` — executed plans (incl. the completed 2026-06-09 gold-standard remediation plan and the adjudicated deep-validation audit)

## App — `app/`
- `app-charter.md`, `app-reference.md`, `app-packaging.md`

## Research
- `ai-research-playbook.md` — how LLM sessions restock the hypothesis queue
- `research/` — synthesis, sources, reports

## Historical — read only when needed
- `Montauk 2.0/` — Pine-excision record + `deep-validation-report.md` (deep-validation adjudication; owner sign-off line in §3)
- `archive/` — one-time reports superseded by current docs (e.g. tecl-health-audit)
- `Legacy/` — pre-2.0 material; do not read unless asked

# Montauk 3.0 — The Always-On TECL Research Appliance

**Status: VISION / OPERATING CONTRACT (updated 2026-07-17).** This folder
defines the next TECL-only iteration of Project Montauk. The governing draft is
[charter.md](charter.md); settled decisions and superseded decisions are recorded
in [decisions.md](decisions.md). Existing questionnaire answers are source
material, not the final specification.

## Questionnaire promotion rule

After Max completes each questionnaire round, the reviewing agent must read the
entire answer set and update this README, [charter.md](charter.md),
[decisions.md](decisions.md), and every affected pillar document **before**
drafting another round or preparing a coding handoff. The completed questionnaire
is preserved unchanged as source evidence; the reconciled Markdown documents
become the current planning truth. Contradictions are resolved explicitly and
older decisions remain visible as superseded history. A questionnaire round is
not complete merely because an answered file exists.

> **Montauk 3.0 is a personal, always-on TECL research appliance where a
> model-agnostic frontier agent continuously invents executable strategy
> candidates, a protected deterministic pipeline backtests and validates them,
> every qualifying Gold configuration automatically joins the leaderboard, and
> Montauk recommends—but does not normally activate—a new leader without Max's
> approval.**

The purpose of all of this machinery is simple: make the most defensible
available TECL `risk_on` / `risk_off` call, explain why it deserves trust, and
keep challenging it in the background.

## The operating contract

- **TECL only.** Multi-asset work is Montauk 4.x or later.
- **Single user.** Montauk 3.0 is built for Max, not as a general product.
- **Always on.** The server refreshes data, recertifies trusted strategies,
  generates research, drains the experiment queue, and reports changes without
  daily supervision.
- **AI proposes; deterministic code decides.** A remote frontier model may author
  isolated strategy candidates, study the failure ledger, choose what to explore
  next, and attempt bounded repairs. It never decides backtest passage, Gold,
  rank, or the trusted signal.
- **Rust is fixed, not agent-selected.** The production strategy/evaluation path
  uses a prebuilt Rust engine and primitive library. The normal agent output is a
  schema-constrained declarative **family specification**, never a hand-written
  list of configurations. It declares logic, parameter domains, and constraints;
  Rust validates and compiles the logic graph once, generates valid exact
  configurations, and batch-evaluates them. An isolated agent-authored Rust
  family module is a later escape hatch only for mechanisms the specification
  language cannot express.
- **The core is protected.** The autonomous agent may not change the data
  contract, execution semantics, backtest engine, validation suite, Gold
  thresholds, score/ranking formula, operations safety layer, or authority rules.
  Those changes require explicit owner-directed work and versioned
  recertification consequences.
- **Gold goes directly to the leaderboard.** There is no staging board and no
  Trade Roster. Each Gold configuration is a row; the interface may collapse
  near-identical rows by family.
- **Recommended is not active.** Montauk can name a new recommended leader, but a
  normal active-strategy change requires Max's approval. Manual brokerage
  execution remains the rule throughout 3.x.
- **Quiet by default.** The normal experience is a daily digest and
  change/failure notifications, with a mostly read-only “Montauk at a glance”
  application and a conversational Slack/agent surface.

## What Gold means

The current owner-intent wording is:

> **Gold means a frozen strategy configuration beats TECL buy-and-hold across
> every required real-data evaluation period, passes Montauk's complete
> versioned correctness and anti-overfitting contract, and is certified fit to
> trade to the strongest extent Montauk can establish from available evidence.**

Gold means **no disqualifying overfit or correctness failure was detected**. It
does not make future returns certain. New market evidence, a data correction, or
a methodology/version change can make a Gold result stale or revoke it. Synthetic
history adds diagnostic confidence but is not a substitute for real-market
evidence. Exact real-period gates, synthetic red-flag rules, execution timing,
and breadth-aware statistical correction remain specification work.

## Read in this order

1. **[charter.md](charter.md)** — the complete product and operating contract,
   including authority boundaries, funnel states, steady-state behavior, and the
   remaining decisions.
2. **[decisions.md](decisions.md)** — the append-only decision ledger. Historical
   decisions remain visible when superseded.
3. **[validation-engine-hardening.md](validation-engine-hardening.md)** — the
   correctness and anti-overfitting work needed before high-volume autonomous
   search can make defensible Gold claims.
4. **[2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md)** —
   the candidate contract and deterministic conveyor.
5. **[2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md)** —
   Chimera research, gated until several materially independent Gold strategies
   exist.

## Supporting plans and scope boundaries

| Document | 3.0 role | Current status |
|---|---|---|
| [validation-engine-hardening.md](validation-engine-hardening.md) | Establish a statistically honest, reproducible Gold contract that remains defensible under massive search breadth. | Required 3.0 foundation |
| [2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md) | Turn ready candidate families and parameter spaces into screened, backtested, validated, reproducible results. | Requires revision and implementation |
| [2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md) | Test whether independent Gold strategies can combine into a superior voting/confidence strategy. | Deferred inside 3.x until prerequisites exist |
| [2026-06-10-ios-companion-app.md](2026-06-10-ios-companion-app.md) | Historical mobile-app proposal. | Deferred to 4.x/5.x; not a 3.0 completion requirement |
| [_RUST CONVERSION.txt](_RUST%20CONVERSION.txt) | Rust strategy/evaluator architecture and performance policy. | Rust fixed; declarative families plus isolated Rust-module escape hatch |

The multi-asset expansion lives in
[`../Montauk 4.0/`](../Montauk%204.0/). Beginning it is an explicit human
decision; no uptime duration or soak test automatically advances the project.

## The most important unresolved contracts

The remaining questions are not about the vision. They are the small number of
places where an implementation would otherwise invent policy:

- executable signal timing and B&H comparison semantics;
- the exact real-data, recent-performance, synthetic-stress, and rolling-demotion
  rules for Gold;
- search-breadth accounting and board-level false-discovery control;
- the safe candidate representation and pre-execution sandbox;
- emergency behavior when the active strategy loses Gold;
- forward-evidence waiting/staleness rules and recertification triggers;
- the protected-core enforcement mechanism and Slack command authority; and
- measurable 3.0 acceptance criteria, while preserving Max's sole authority to
  begin 4.x.

These are collected in
[Questionnaire 3 — Final Operating Contract](Questionnaires/Questionnaire%203%20-%20Final%20Operating%20Contract.rtf)
rather than scattered through new planning files.

# Montauk 3.0 — The Always-On TECL Research Appliance

**Status: RATIFIED VISION / IMPLEMENTATION CONTRACT (updated 2026-07-21).** This folder
defines the next TECL-only iteration of Project Montauk. The governing contract is
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

- **TECL is the only traded asset.** Multi-asset selection, sizing, and rotation
  are later work. Strategies may use point-in-time, provenance-verified external
  inputs such as VIX, volume, options-derived data, macro series, related assets,
  or an idiosyncratic TECL component while still emitting only TECL
  `risk_on`/`risk_off`.
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
  language cannot express. Once the escape-hatch acceptance suite is approved,
  isolated modules may enter deterministic intake automatically; Max does not
  approve each generated module.
- **The core is protected.** The autonomous agent may not change the data
  contract, execution semantics, backtest engine, validation suite, Gold
  thresholds, score/ranking formula, operations safety layer, or authority rules.
  Those changes require explicit owner-directed work and versioned
  recertification consequences. A human-held signing key seals an exact core
  release; autonomous startup and evaluation fail closed if its signed manifest,
  permissions, or protected hashes do not verify.
- **Pending Gold is a deterministic certification state, not a Trade Roster.**
  Historical-suite survivors enter `Pending Gold` while they accumulate the
  required cooling-off/forward evidence. Graduation to current Gold is automatic
  after the current contract passes again. Each current Gold configuration is a
  leaderboard row; the interface may collapse related rows by family.
- **Recommended is not active.** Montauk can name a new recommended leader, but a
  normal active-strategy change requires Max's approval. Manual brokerage
  execution remains the rule throughout 3.x.
- **Quiet by default.** The normal experience is a daily digest and
  change/failure notifications, with a mostly read-only “Montauk at a glance”
  application and a conversational Slack/agent surface.
- **Current contract only.** There are no grandfathered Gold rows. A material
  data, execution, engine, or validation change makes every incompatible
  certificate stale and queues urgent recertification.
- **Everything durable has an off-machine GitHub path.** Code, specifications,
  manifests, authority state, Gold artifacts, and partitioned database snapshots
  are backed up without forcing high-volume live databases into ordinary Git
  blobs. No acknowledged durable result may be silently lost.

## What Gold means

The current owner-intent wording is:

> **Gold means a frozen strategy configuration beats TECL buy-and-hold across
> every required real-data evaluation period, passes Montauk's complete
> versioned correctness and anti-overfitting contract, and is certified fit to
> trade to the strongest extent Montauk can establish from available evidence.**

Gold means **no disqualifying overfit or correctness failure was detected**. It
does not make future returns certain. New market evidence, a data correction, or
a methodology/version change can make a Gold result stale or revoke it. Synthetic
history adds diagnostic/stress confidence but is not a substitute for real-market
evidence. No test may be skipped, silently renormalized, or replaced by a high
composite score. A configuration with missing required data or insufficient
evidence cannot be Gold.

The owner-facing confidence number remains **Validation Score** until a frozen
calibration target, controls, sample size, and genuine forward outcomes justify
a probability interpretation. Performance and confidence thresholds are
versioned contracts; they never auto-ratchet merely because the search found
more winners.

## Read in this order

1. **[charter.md](charter.md)** — the complete product and operating contract,
   including authority boundaries, funnel states, steady-state behavior, and the
   bounded calibration studies that remain.
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
| [2026-06-09-idea-to-gold-pipeline.md](2026-06-09-idea-to-gold-pipeline.md) | Turn ready candidate families and parameter spaces into screened, backtested, validated, reproducible results. | Ratified operating plan; Phase A ready |
| [2026-04-23-meta-strategy-design.md](2026-04-23-meta-strategy-design.md) | Test whether independent Gold strategies can combine into a superior voting/confidence strategy. | Deferred inside 3.x until prerequisites exist |
| [2026-06-10-ios-companion-app.md](2026-06-10-ios-companion-app.md) | Historical mobile-app proposal. | Deferred to 4.x/5.x; not a 3.0 completion requirement |
| [_RUST CONVERSION.txt](_RUST%20CONVERSION.txt) | Rust strategy/evaluator architecture and performance policy. | Rust fixed; declarative families plus isolated Rust-module escape hatch |

The multi-asset expansion lives in
[`../Montauk 4.0/`](../Montauk%204.0/). Beginning it is an explicit human
decision; no uptime duration or soak test automatically advances the project.

## Ratified policy; calibration work remains

[Questionnaire 3 — Final Operating Contract](Questionnaires/Questionnaire%203%20-%20Final%20Operating%20Contract.rtf)
is complete and preserved as owner evidence. It resolved agent authority,
candidate isolation, Pending Gold, recommendation/fallback behavior,
recertification, current-contract-only Gold, storage, GitHub backup, Slack
authority, and acceptance ownership.

The remaining work is **methodology and engineering calibration**, not permission
for a coding agent to choose policy. Phase A must produce evidence for:

- the executable notification-to-fill model, tested against conservative OHLC
  stress assumptions and later Max's recorded manual fills;
- a small, fixed real-data horizon/rolling-window contract that realizes “beats
  B&H however reasonably sliced” without creating a tunable exam;
- the initial real-era performance margin (owner intuition: begin around 1.10),
  lower-bound test, and recent/stress weighting;
- independent recalibration of the XLK/technology-index synthetic series and its
  diagnostic/catastrophic-stress role;
- board/lifetime search correction that recognizes correlated configurations
  without punishing a legitimate nearby configuration merely for similarity;
- the meaning and forward calibration of Validation Score; and
- false-positive **and false-negative** behavior of every anti-overfit gate so a
  strict but invalid grader cannot reject sound controls.

Those studies must be reviewed and frozen into a signed contract before the
autonomous conveyor can certify Gold. Only Max declares 3.0 complete. Work on a
later major version begins only when Max separately says so; acceptance tests,
elapsed time, or a soak never make that decision.

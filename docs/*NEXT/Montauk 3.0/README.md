# Montauk 3.0 — The Always-On TECL Research Appliance

**Status: RATIFIED VISION / IMPLEMENTATION CONTRACT (updated 2026-07-21).** This folder
defines the next TECL-only iteration of Project Montauk. The governing contract is
[charter.md](charter.md); settled decisions and superseded decisions are recorded
in [decisions.md](decisions.md). Existing questionnaire answers are source
material, not the final specification.

**3.0 rewrite boundary.** This folder is the self-contained planning authority
for the rewrite. Existing scripts, tests, scores, folder layouts, dashboards,
and documentation elsewhere in the repository are migration evidence—not 3.0
requirements—unless an active document in this folder explicitly adopts them.
No coding agent may fill a gap by copying a contradictory legacy behavior. In
particular, legacy rules such as synthetic-inclusive Gold, family row caps,
automatic activation of the top row, author-tier shortcuts, and the old Python
pipeline do not survive unless restated here.

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

### The testing-pipeline guiding light

> **A Gold certificate exists to give Max the strongest honest assurance
> Montauk can produce—from current scholarship, market expertise, AI-assisted
> research, independent review, reproducible evidence, and its own calibrated
> controls—that an exact strategy is not detectably overfit and that actually
> following it under obtainable execution should outperform matched TECL
> buy-and-hold.**

Everything in the backtest and validation design must trace to that promise.
Expert or model opinion can identify risks and methods, but it is not itself
evidence and cannot award Gold. “Strongest honest assurance” is deliberately not
absolute certainty: future markets can invalidate a sound historical result.

## Montauk 3.0 on one slide

```text
Model or Max generates a typed strategy family
                       |
                       v
       protected Rust libraries validate the definition
       and expand its parameter space
                       |
                       v
      logical bucket of configuration work
         (streamed data, not scripts/files)
                       |
                       v
              VALIDATION PIPELINE
       backtest against matched TECL B&H
          (resolves economic passage)
                       |
                       v
       correctness + anti-overfit validation
          (resolves four remaining planks)
                       |
                    if pass
                       v
               Gold leaderboard
                       |
                       v
                    ranking
                       |
                       v
             Max chooses the Active row

All day in the background: verified data, recertification, recovery,
research feedback, and a quiet daily digest.
```

That is the product. One family definition may yield millions of configuration
records; compiling a separate script for each configuration would be slower,
harder to reproduce, and unnecessary. A genuinely new mechanism that the shared
library cannot express may use one isolated Rust module for its whole family.
At very large scales, the bucket is logical: Rust can expand a family in
deterministic shards/batches just before evaluation instead of first writing
billions of tiny files or database jobs. Every configuration actually evaluated
still receives an exact identity and compact durable result.

The backtest and validation stages together answer the five Gold questions. The
economic-passage plank is decided by the backtest; validation completes
correctness, generalization, search honesty, and reproducibility/currentness.
“Five planks” does not mean five more pipeline stages or a second performance
test.

Sandboxing, databases, Rust optimization, statistical methods, backup, and the
conversation channel are supporting implementation—not additional product
stages. If an implementation cannot be traced to one box above or to protecting
one of those boxes, it needs explicit justification or removal.

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
- **Native Debian deployment.** The preferred 3.0 appliance is the dedicated
  tower running minimal Debian Stable without a desktop, supervised by
  `systemd`, with live data on SSD, private Tailscale/SSH administration, and
  trusted work able to preempt research. This is a deployment baseline, not a
  Gold or hardware-purchase gate.
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
- **Pending Gold is an activation status, not a second certification board.** A
  configuration that clears every candidate-local historical requirement enters
  the next daily frozen certification epoch. The epoch adds the cohort-wide
  search correction, assembles the final five-plank verdict, and automatically
  publishes passing rows to the Gold leaderboard with a `Pending Gold` badge.
  It is not eligible to become Recommended or Active until the cooling/forward-
  evidence rule and a fresh certification pass. There is still one leaderboard
  and no Trade Roster.
  Every exact row remains queryable, while the normal view starts with families
  collapsed so near-identical variants do not bury unrelated strategies.
- **Recommended is not active.** Montauk can name a new recommended leader, but a
  normal active-strategy change requires Max's approval. Manual brokerage
  execution remains the rule throughout 3.x.
- **Execution is after-close to next-open.** Max manually submits a position-
  change order after the verified close for execution at the next regular-
  session market open. Gold models that workflow plus calibrated costs across a
  fixed $10,000–$100,000 notional order band. Personal fill logging, actual
  order-size/account tracking, and brokerage-position tracking are outside 3.0.
- **The economic scope is intentionally narrow.** The primary account is tax-
  advantaged, so tax modeling is out of scope. Risk-off cash earns zero; an
  active SGOV leg is later work.
- **Quiet by default.** The normal experience is a daily digest and
  change/failure notifications, with a mostly read-only “Montauk at a glance”
  application and one conversational private channel/agent surface. Slack is the
  conservative commissioning default; Buzz is evaluated against the same
  adapter contract before the final channel choice. Only one primary channel is
  deployed. The interaction can feel OpenClaw/Buzz-like, but a deterministic
  Montauk controller—not the channel, model, or gateway—authorizes every state
  change.
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

The primary performance claim is deliberately literal: under a signal formed
after a verified daily close and a modeled fill at the next regular-session open
plus calibrated costs, the strategy's terminal TECL-equivalent wealth/share
multiple must beat a matched B&H investment on the required real-data horizons.
The leaderboard shows that simple relative result alongside Validation Score (or
calibrated Confidence only if the evidence later earns that word).

The owner-facing confidence number remains **Validation Score** until a frozen
calibration target, controls, sample size, and genuine forward outcomes justify
a probability interpretation. Performance and confidence thresholds are
versioned contracts; they never auto-ratchet merely because the search found
more winners.

Gold is intended to earn **operational trust**: Max should not have to re-litigate
the pipeline before following a Gold strategy through an uncomfortable period.
It cannot earn certainty that the next call is correct. The reason to trust it is
that the exact strategy passed a small, complete, independently tested contract
and remains current—not that Montauk accumulated the largest possible number of
tests or scores.

No existing or legacy “Gold” label is presumed to satisfy this 3.0 promise. At
cutover, every row starts outside the current 3.0 board until it passes the final
3.0 contract from scratch.

## Read in this order

1. **[charter.md](charter.md)** — the complete product and operating contract,
   including authority boundaries, funnel states, steady-state behavior, and the
   bounded calibration studies that remain.
2. **[implementation-plan.md](implementation-plan.md)** —
   the implementation sequence for the conveyor.
3. **[validation-engine-hardening.md](validation-engine-hardening.md)** — the
   correctness and anti-overfitting work needed before high-volume autonomous
   search can make defensible Gold claims.
4. **[rust-strategy-and-evaluation-policy.md](rust-strategy-and-evaluation-policy.md)** —
   the subordinate technical representation/performance policy.
5. **[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md)** —
   the dedicated-host, service, provider-agent, private remote-access, channel
   selection, and OpenClaw-pattern deployment contract.
6. **[decisions.md](decisions.md)** — historical rationale and superseded calls.
   A coding agent must not reconstruct requirements from this ledger when the
   charter already states current policy.
7. **[chimera-research-design.md](chimera-research-design.md)** —
   Chimera research, gated until several materially independent Gold strategies
   exist.

### Documentation authority

There is one owner for each kind of truth:

| Question | Owning document |
|---|---|
| What Montauk is, what Gold means, and who has authority | `charter.md` |
| In what order it is built and accepted | `implementation-plan.md` |
| How the host, services, remote agent, conversation channel, and private access operate | Debian/agent/channel operations policy |
| Which validation methods are admissible and still need proof | validation hardening plan |
| How normal strategies are represented and accelerated | Rust policy |
| Why a decision changed | decision log only |

Pillar documents reference the charter; they do not create parallel product,
Gold, or authority rules. If duplication disagrees, the charter wins and the
duplicate is a documentation defect.

## Supporting plans and scope boundaries

| Document | 3.0 role | Current status |
|---|---|---|
| [validation-engine-hardening.md](validation-engine-hardening.md) | Establish a statistically honest, reproducible Gold contract that remains defensible under massive search breadth. | Required 3.0 foundation |
| [implementation-plan.md](implementation-plan.md) | Turn ready candidate families and parameter spaces into screened, backtested, validated, reproducible results in the required build order. | Required coding handoff; Phase 1 ready |
| [debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md) | Run the appliance on minimal Debian with `systemd`, low-priority Rust research, a bounded model adapter, one selected private channel, and Tailscale/SSH; compare Slack and Buzz and define what is borrowed from OpenClaw. | Deployment baseline; channel bake-off and commissioning values pending |
| [rust-strategy-and-evaluation-policy.md](rust-strategy-and-evaluation-policy.md) | Define Rust strategy representation, compilation, parity, containment, and performance policy. | Required implementation pillar |
| [chimera-research-design.md](chimera-research-design.md) | Test whether independent Gold strategies can combine into a superior voting/confidence strategy. | Deferred/conditional inside 3.x |
| [validation-audit-findings.md](validation-audit-findings.md) | Preserve defects found in legacy validation code so they are not repeated. | Reference evidence only; not an architecture or threshold source |
| [decisions.md](decisions.md) | Explain how the current policy emerged, including superseded calls. | Historical rationale only; never implement directly |
| `Questionnaires/` | Preserve Max's answers and the wording that produced them. | Frozen source evidence; do not edit or implement directly |
| [2026-06-10-ios-companion-app.md](../Montauk%204.0/2026-06-10-ios-companion-app.md) | Historical mobile-app proposal. | Deferred to 4.x/5.x; not a 3.0 completion requirement |

OS/editor/session metadata—including `.DS_Store` and
`Questionnaires/_chat.txt`—is excluded from the planning handoff and has no
authority.

The multi-asset expansion lives in
[`../Montauk 4.0/`](../Montauk%204.0/). Beginning it is an explicit human
decision; no uptime duration or soak test automatically advances the project.

## Ratified policy; calibration work remains

[Questionnaire 1](Questionnaires/Questionnaire%201_Answered.rtf),
[Questionnaire 2](Questionnaires/Questionnaire%202.txt),
[Questionnaire 3 — Final Operating Contract](Questionnaires/Questionnaire%203%20-%20Final%20Operating%20Contract.rtf),
[Questionnaire 4 — Backtest and Validation Contract](Questionnaires/Questionnaire%204%20-%20Backtest%20and%20Validation%20Contract.rtf)
and
[Questionnaire 5 — Remaining 3.0 Decisions and Research Mandate](Questionnaires/Questionnaire%205%20-%20Remaining%203.0%20Decisions%20and%20Research%20Mandate.rtf)
are complete and preserved as owner evidence. They resolve agent authority,
candidate isolation, Pending Gold, recommendation/fallback behavior,
recertification, current-contract-only Gold, storage, GitHub backup, channel
authority, acceptance ownership, the deployable performance target, historical
validation structure, daily certification cohorts, the owner's testing-pipeline
guiding light, practical execution/account scope, and the Phase 1 research
mandate.

Max noted that much of Questionnaire 4's statistical language was not clear to
him. The plain-language guiding light therefore governs every technical answer.
Accepted suggestions fix owner-visible outcomes; unanswered or tentative method
details remain evidence-driven Phase 1 design work and may not be represented as
personal statistical judgments by Max. Questionnaire 5 leaves its Gold-first
priority confirmation and final open-ended product check blank, so the prior
Gold-first plan remains and no new product requirement is inferred.

The remaining work is **methodology and engineering calibration**, not permission
for a coding agent to choose policy. Phase 1 must produce evidence for:

- calibrated slippage/fees from market evidence for the fixed
  signal-after-verified-close, next-regular-session-open execution contract and
  $10,000–$100,000 modeled order band;
- the aggregate rolling-window passage rule and catastrophic-window veto around
  the fixed complete-history and trailing-five-year hard gates;
- a predeclared, source-labelled named-moment suite, separating observed TECL
  episodes from reconstructed pre-inception episodes;
- explicit evidence labels separating frozen historical replay, nested rolling-
  origin reconstruction, spent/reused holdouts, and genuinely post-freeze
  per-row forward data;
- the exact expanding-versus-rolling design for required nested rolling-origin
  reconstruction, plus whether CPCV has adequate assumptions, power, and
  incremental protection to be a hard applicable gate; purge/embargo derives
  from actual information/outcome overlap, never a copied percentage;
- the final economic margin, beginning with a 1.10 point-estimate hypothesis,
  and the one-sided uncertainty rule above no edge;
- a time-separated overlap study that extends the XLK-based synthetic
  transformation through real TECL history, calibrates on earlier blocks, tests
  later blocks without refitting, and then fixes its diagnostic/catastrophic-
  stress role;
- board/lifetime search correction that recognizes correlated configurations
  and adaptive holdout reuse without punishing a legitimate nearby configuration
  merely for similarity;
- the achievable annual appliance-level false-Gold/false-reject frontier, using
  1% probability of any false Gold as an aspirational reference rather than an
  unexamined cutoff;
- the meaning and forward calibration of Validation Score;
- the simplest Montauk Score/ranking formula that gives evidentiary strength
  priority over marginal performance and admits no extra pillar without measured
  incremental value, plus a calibrated “leader not clearly separated” status;
  and
- false-positive **and false-negative** behavior of every anti-overfit gate so a
  strict but invalid grader cannot reject sound controls.

Those studies must be reviewed and frozen into a signed contract before the
autonomous conveyor can certify Gold. Only Max declares 3.0 complete. Work on a
later major version begins only when Max separately says so; acceptance tests,
elapsed time, or a soak never make that decision.

Phase 1 brings consequential decisions back in simple terms with a simple
example, recommendation, measured tradeoff, and technical appendix. Mandatory
personal fill recording, tax modeling, paid outside-human review, hardware/
provider procurement, and a throughput acceptance target are not 3.0 work.

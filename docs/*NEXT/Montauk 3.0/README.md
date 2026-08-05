# Montauk 3.0 — The Always-On TECL Research Appliance

**Status: RATIFIED VISION / IMPLEMENTATION CONTRACT (updated 2026-07-25).** This folder
defines the next TECL-only iteration of Project Montauk. The governing contract is
[charter.md](charter.md); settled decisions and superseded decisions are recorded
in [decisions.md](decisions.md). Existing questionnaire answers are source
material, not the final specification.

**3.0 rewrite boundary.** This folder is the self-contained planning authority
for the rewrite. Existing scripts, tests, scores, folder layouts,
and documentation elsewhere in the repository are migration evidence—not 3.0
requirements—unless an active document in this folder explicitly adopts them.

**Two things elsewhere in the repository ARE adopted, explicitly.** The Mac Tauri
app in `app/` is retrofitted as the 3.0 read-only visual surface rather than
replaced (D122) — "dashboards" was removed from the superseded list above for that
reason. And Montauk 2.0 stays runnable in place, emitting its frozen daily signal
and preserving its Gold artifacts as parity fixtures, until 3.0 replaces it
(D111/D112/D121).
No coding agent may fill a gap by copying a contradictory legacy behavior. In
particular, legacy rules such as synthetic-inclusive Gold, family row caps,
author-tier shortcuts, and the old Python pipeline do not survive unless
restated here.

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
> Montauk publishes the top-ranked row's daily signal as the leader.**

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
          Montauk emits the leader's signal

All day in the background: verified data, recertification, recovery,
research feedback, and a quiet daily digest.
```

That is the product. One family definition may yield millions of configuration
records; compiling a separate script for each configuration would be slower,
harder to reproduce, and unnecessary. A mechanism the shared library cannot
express is reached by proposing a new building block for Max's approval (D96),
never by the agent writing its own module.
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
- **Native Debian deployment.** The 3.0 appliance is the dedicated tower running
  minimal **Debian 13 `trixie`** on wired Ethernet (D82), supervised by
  `systemd`, with live data on SSD, private Tailscale/SSH administration, an
  on-demand tailnet-only XFCE/RDP desktop for graphical administration (D83), and
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
  configurations, and batch-evaluates them. **Free composition from existing
  blocks; a new block needs approval first** (D96, the Lego principle): the agent
  builds, wires, declares ranges, smoke-tests, and submits with no owner approval
  at any step, but creating a *new custom primitive* requires Max's approval
  **before** it is created, plus acceptance tests and the D108 signed release.
  Block breadth and an idea-starvation report are therefore hard requirements
  (D98).
- **The core is protected.** The autonomous agent may not change the data
  contract, execution semantics, backtest engine, validation suite, Gold
  thresholds, score/ranking formula, operations safety layer, or authority rules.
  Those changes require explicit owner-directed work and versioned
  recertification consequences. A human-held signing key seals an exact core
  release; autonomous startup and evaluation fail closed if its signed manifest,
  permissions, or protected hashes do not verify.
- **Pending Gold is a cooling status, not a second certification board.** A
  configuration that clears every candidate-local historical requirement enters
  the next daily frozen certification epoch. The epoch adds the cohort-wide
  search correction, assembles the final five-plank verdict, and automatically
  publishes passing rows to the Gold leaderboard with a `Pending Gold` badge.
  A Pending row may rank anywhere on the board, but its signal is not published
  as the leader's until it clears the cooling/forward-evidence rule and a fresh
  certification pass (D125). There is still one leaderboard and no Trade Roster.
  Every exact row remains queryable, while the normal view starts with families
  collapsed so near-identical variants do not bury unrelated strategies.
- **Montauk ranks and emits the leader (D125).** There are no authority states —
  no Recommended, no Active, no Manual Override. The leader is the top-ranked
  Gold row, and a leader change applies five-bar hysteresis. Publishing that
  signal is an operational fact requiring no approval, and Montauk does not
  model whether real money is following it (D124). Manual brokerage execution
  remains the rule throughout 3.x.
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
  blobs. No acknowledged durable result may be silently lost. The promise is
  scoped honestly: zero loss against ordinary process/disk failure via a local
  journal plus a second local device, and an explicitly accepted
  physical-disaster recovery point equal to the last verified GitHub sync.
- **A backup outage is not a trading rule.** If everything is healthy except
  off-machine replication, Montauk journals locally, shows `degraded_backup`,
  alerts Max, and still delivers the valid signal on time — while blocking Gold
  publication, leader changes, and other non-essential authority mutations.
- **TECL is a product, not just a price series.** Observed history spans a TYH
  era (2008-12-17 → 2012-06-28, Russell 1000 Technology) and the current
  Technology Select Sector era; both seams are labelled. A material product
  change — benchmark, leverage objective, ticker/CUSIP, closure, prolonged halt —
  alerts Max immediately, suspends new trusted signals, and stales affected
  certificates.

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

No existing or legacy “Gold” label is presumed to satisfy this 3.0 promise.
Every row starts outside the 3.0 board until it passes the final 3.0 contract
from scratch.

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
| [debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md) | Run the appliance on minimal Debian 13 with `systemd`, low-priority Rust research, a bounded model adapter, one selected private channel, and Tailscale/SSH plus an on-demand graphical desktop; record why Slack was selected over Buzz and email, and define what is borrowed from OpenClaw. | Deployment baseline; channel selected (Slack, D81, owner-confirmed 2026-08-02), host and remote-access settled (D82/D83), commissioning values pending |
| [channel-gateway-and-agent-runtime.md](channel-gateway-and-agent-runtime.md) | Fill in *how* the channel is built: subscription-first agent runtime (Agent SDK), the build/rent line, and the three-path design that keeps digests and mutations model-free. | Design contract; subordinate to the operations document. Command schema and steering contract still open |
| [rust-strategy-and-evaluation-policy.md](rust-strategy-and-evaluation-policy.md) | Define Rust strategy representation, compilation, parity, containment, and performance policy. | Required implementation pillar |
| [chimera-research-design.md](chimera-research-design.md) | Test whether independent Gold strategies can combine into a superior voting/confidence strategy. | Deferred/conditional inside 3.x |
| [validation-audit-findings.md](validation-audit-findings.md) | Preserve defects found in legacy validation code so they are not repeated. | Reference evidence only; not an architecture or threshold source |
| [decisions.md](decisions.md) | Explain how the current policy emerged, including superseded calls. | Historical rationale only; never implement directly |
| `Questionnaires/` | Preserve Max's answers and the wording that produced them. | Frozen source evidence; do not edit or implement directly |
| `research/rd1/` | Ten-stream Phase 1 evidence package plus the research lead's conclusion. | Reference evidence and hypothesis inventory; **not** a requirements source. Nothing here is policy until the charter adopts it |
| `research/rd2/` | Independent review of the rd1 package; eleven follow-up research prompts. | Open research backlog. R3/R5 (TECL-TYH data, distributions, synthetic overlap), R1/R4 (search honesty, low-sample inference), and R2 (null worlds) are live; R6/R9's broker and dead-man portions are out of scope per the charter |
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
[Questionnaire 5 — Remaining 3.0 Decisions and Research Mandate](Questionnaires/Questionnaire%205%20-%20Remaining%203.0%20Decisions%20and%20Research%20Mandate.rtf),
[Questionnaire 6 — Operational Edge Cases and Owner Decisions](Questionnaires/Questionnaire%206%20-%20Operational%20Edge%20Cases%20and%20Owner%20Decisions.txt)
and
[Questionnaire 7 — Research Reconciliation Decisions](Questionnaires/Questionnaire%207%20-%20Research%20Reconciliation%20Decisions.txt)
(Part A only)
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

Questionnaire 6 and Questionnaire 7 Part A were promoted on 2026-07-25
(decisions D65–D78). Two answers required interpretation and are flagged in the
decision log rather than transcribed: Questionnaire 6 question 2 reads
“off-machine replication” as “off-machine testing” and is superseded by
Questionnaire 7 question 3; Questionnaire 6 question 1 gave an alert-severity
answer rather than the state-machine choice it was asked for, and was reasked as
Questionnaire 8 A8 (now closed by D90).

[Questionnaire 8 — Intent Alignment and Remaining Technical Decisions](Questionnaires/Questionnaire%208%20-%20Intent%20Alignment%20and%20Remaining%20Technical%20Decisions.txt)
restated Questionnaire 7 Part B in plain language with worked examples (Part B),
added eight alignment items found when auditing the plan against Max's stated
intent (Part A), and closed four older un-carried-forward blanks plus four
never-asked decisions from the 2026-07-25 completeness audit (Part C).
[Questionnaire 9 — Final Build Readiness Clarifications](Questionnaires/Questionnaire%209%20-%20Final%20Build%20Readiness%20Clarifications.txt)
then corrected four answers that were blank or did not answer the question asked,
bounded three answers that needed an exact implementation boundary, and confirmed
the final decision boundary.

**Both are answered and promoted (2026-08-02, decisions D84–D110). Every open
owner decision is closed.** The open-owner-authority table in
[decisions.md](decisions.md) is retained only as an audit trail of what closed
each row. Questionnaire 8 A4 was the single blank and is answered by
Questionnaire 9 item 1.

**Five of those decisions changed prior plan text rather than filling a gap** —
read them before relying on older passages:

| Decision | Change |
|---|---|
| **D96** | The escape hatch is **replaced by a per-block approval gate**. Composing from existing blocks is unrestricted; creating a *new* primitive needs Max's approval before it is built. |
| **D97** | **No catastrophic-loss veto.** Near-ruin penalizes leaderboard rank instead. Amends D77. |
| **D99** | A sealed historical holdout is **spent on reveal**, not permanently sealed. Gives charter §4.2 an owner mandate and a mechanism. |
| **D106** | Synthetic pre-2009 history moves from **zero weight** to a limited, empirically calibrated weight — never able to rescue or sink a strategy on its own. |
| **D108** | The core is sealed by a **password-controlled privileged ceremony**, not a hardware signing key. |

Two more ratify readings the plan had already adopted without authority: **D109**
(a material TECL product change suspends trusted signals) and **D110** (the
$10,000–$100,000 modeled order band).

**The questionnaire process is closed (D107).** Questionnaire 10 was written at
Max's own request on 2026-08-03 as an accounting of what the reconciliation left
open — six genuine items and two interpretations, all now answered and promoted as
**D111–D118**. It did not reopen the finality rule, which binds an implementation
agent from generating a broad clarification round unprompted.

Of those eight, two existed only because Max retired Montauk 2.0 on 2026-08-02:
**D111/D121** keep 2.0 running as it does today on its own data pipeline, and
**D112** preserves it runnable with its artifacts and archived code — and makes
testing the 2.0 Gold strategies against the rebuilt pipeline the *first* thing 3.0
does.

**D124 then removed the 2.0→3.0 cutover concept entirely.** There is no
signal-authority handover, no condition checklist, no approval ceremony, and no
`approve_active_switch` mutation. That apparatus was invented by the planning
process rather than requested, and Max struck it: Montauk emits the top-ranked
Gold strategy's signal as an operational fact and **does not model whether real
money is following it**. He decides separately, outside Montauk, what he trusts.
**D123** likewise removed restore drills and the completion declaration from
planning scope. Four owner approvals remain, not seven.

Later owner involvement is the four named approvals in D107 as amended by D123
and D124, requested as focused evidence reports or approval cards. An
implementation agent that hits an unforeseen
issue asks one focused question — never a new questionnaire — and only when
owner-visible behavior, the Gold promise, protected-core authority, real-money
safety, external spending, or credentials would materially change.

What remains is the measured Phase 1 values Max ratifies from plain-language
reports under Questionnaire 5 items 15–19 and D107 item 1.

The remaining work is **methodology and engineering calibration**, not permission
for a coding agent to choose policy. Phase 1 must produce evidence for:

- calibrated slippage/fees from market evidence for the fixed
  signal-after-verified-close, next-regular-session-open execution contract and
  the $10,000–$100,000 modeled order band (band now owner-selected, D110);
- the aggregate rolling-window reporting rule around the two hard gates —
  complete observed history and trailing five years (D86). Rolling windows, named
  moments, the TYH era, and synthetic stress are **diagnostics**, not gates,
  unless Phase 1 proves a specific one catches failures the two hard gates miss.
  There is no catastrophic-window veto (D97);
- the causal-eligibility start date for the $1,000 strategy-versus-B&H comparison
  — first date every required input and warm-up is available, not first trade
  (D86) — and the "insufficient evidence" display that must never read as a pass
  (D92);
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
  later blocks without refitting, and then proposes the **limited empirical
  weight** synthetic history carries in Validation Score and ranking (D106) —
  bounded so it can never substitute for real-data passage, rescue a failing
  strategy, or independently deny Gold;
- board/lifetime search correction that recognizes correlated configurations
  and adaptive holdout reuse without punishing a legitimate nearby configuration
  merely for similarity;
- the false-Gold/false-reject frontier measured by running the **complete
  conveyor on known-worthless and planted-good control worlds**, reported under
  annual, 5-year, 10-year, *and* lifetime interpretations so Max can choose the
  operating policy from the real tradeoff (D91). 1% probability of any false Gold
  is an aspirational reference, never an unexamined cutoff, and no method may be
  described as guaranteeing a false Gold cannot occur;
- a primary-source TECL distribution ledger and the symmetric
  ex-date-entitlement / pay-date-availability reinvestment convention for both
  the strategy and matched B&H;
- whether the TYH product era (2008-12-17 → 2012-06-28) earns promotion from
  diagnostic to required stress gate under D86, and whether the 2018 GICS
  reconstitution is a further seam;
- explicit RPO/RTO per failure scope, the `degraded_backup` signal path, and the
  owner-approved non-authoritative restore drill;
- the **forward calibration** of Validation Score. Its meaning is already fixed
  by D105 — evidence strength, no percent sign, no probability claim — and
  probability language is unlocked only by frozen forward results plus an
  owner-approved contract change;
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

# Project Montauk 3.0 Charter — The Always-On TECL Research Appliance

**Status: RATIFIED OPERATING POLICY THROUGH QUESTIONNAIRE 5; CALIBRATION PENDING
(updated 2026-07-21).** This document captures the owner's clarified intent and
is the governing 3.0 planning contract. It defines a rewrite target and
**supersedes conflicting behavior in current code, documentation outside this
folder, and legacy Gold artifacts**. Those sources remain migration evidence
only. A behavior becomes a 3.0 requirement only when this charter or an active
charter-subordinate pillar in this folder states it; the rewrite must reconcile
tests and implementation to this contract before cutover.

Terms marked **DECIDED** are owner decisions. Terms marked **POLICY DECIDED,
CALIBRATION PENDING** have a fixed safety/authority outcome but still require a
measured, versioned implementation rule. A coding agent may implement only the
approved experiment and acceptance criteria; it may not choose the eventual
threshold or reinterpret the owner policy.

**DECIDED — questionnaire promotion rule.** After Max completes a questionnaire
round, the reviewing agent must process the entire answer set into this charter,
the decision log, README, and every affected pillar plan before drafting another
round or a coding handoff. The answered questionnaire remains unchanged as source
evidence; the reconciled active docs become project truth. Conflicts are resolved
explicitly and prior decisions are marked superseded rather than erased.

---

## 0. Purpose

Montauk exists to answer one practical question for TECL:

> **Should the current trusted state be risk-on or risk-off, and why is this the
> most defensible call Montauk can make today?**

Montauk 3.0 replaces a manually driven research loop with a personal, always-on
appliance. It continuously challenges the current strategy, turns human- or
agent-authored ideas into reproducible experiments, rejects candidates that do
not survive the contract, maintains a Gold-only leaderboard, and surfaces only
the decisions or failures that deserve Max's attention.

Its success is not “a large number of features” or “a large number of tests.”
Success is a trustworthy end-to-end research and signal system whose methods are
clear enough that Max can understand why a signal has earned authority.

### 0.1 Testing-pipeline guiding light

**DECIDED.**

> **A Gold certificate exists to give Max the strongest honest assurance
> Montauk can produce—from current scholarship, market expertise, AI-assisted
> research, independent review, reproducible evidence, and its own calibrated
> controls—that an exact strategy is not detectably overfit and that actually
> following it under obtainable execution should outperform matched TECL
> buy-and-hold.**

This is the governing requirement for every backtest, walk-forward, search-
correction, and anti-overfit choice. A method stays only when it helps establish
one part of that promise without creating misleading certainty or needless
complexity. AI or expert agreement may direct research; neither can substitute
for causal, reproducible, calibrated evidence.

## 1. Product definition and completion target

**DECIDED.** Montauk 3.0 is:

> A personal, always-on TECL research appliance where a model-agnostic frontier
> agent continuously invents executable strategy candidates, a protected
> deterministic pipeline backtests and validates them, every qualifying Gold
> configuration automatically joins the leaderboard, and Montauk
> recommends—but does not normally activate—a new leader without Max's
> approval.

A complete 3.0 must be able to run unattended through the whole loop:

1. acquire and verify current data;
2. protect the last trusted signal when current data or operations fail;
3. recertify the active strategy with priority;
4. generate or accept executable strategy ideas;
5. perform pre-execution safety and correctness checks;
6. cheaply screen exact parameter configurations;
7. fully backtest survivors under frozen execution semantics;
8. run the complete versioned validation suite;
9. publish every Gold configuration to the current leaderboard;
10. update the Montauk recommendation without silently changing the active
    strategy;
11. generate the current trusted TECL state;
12. retain enough evidence to reproduce every important verdict; and
13. send concise digests, change notifications, and actionable failures.

No daily supervision is part of the target. A normal week may require no action.
The intended steady state is quiet: the machine works, Max receives a useful
daily digest, and stronger attention is requested only for a meaningful change
or fault.

## 2. Scope and priorities

### 2.1 In scope

- TECL, with the existing long/flat or risk-on/risk-off action space.
- Point-in-time, provenance-verified explanatory inputs from other markets or
  data streams—including VIX, TECL/underlying volume, options-derived measures,
  macro series, related assets, and an idiosyncratic TECL component—provided the
  strategy still trades only TECL and every input passes the same causal/data
  contract.
- A single user: Max.
- An always-on dedicated host. The deployment baseline is native current Debian
  Stable on the dedicated tower, installed minimally without a desktop and
  supervised by `systemd`; hot state lives on SSD and trusted work preempts
  research. Hardware procurement, model-provider choice, spending policy, and a
  numerical throughput target remain deployment concerns rather than Gold or
  completion gates.
- A model-agnostic remote frontier agent invoked on a schedule. “No local AI”
  means no locally hosted foundation model; it does not prohibit Claude, Codex,
  or another remote agent from operating through a subscription or API.
- Automated strategy authoring, experiment scheduling, result analysis, bounded
  candidate repair, backtesting, validation, Gold publication, recertification,
  ranking, signal generation, and reporting.
- Manual owner approval for normal active-strategy changes.
- Manual brokerage execution for all of 3.x.
- A tax-advantaged primary trading account. Gold is net of modeled trading costs
  but does not include an after-tax performance model.
- A mostly read-only Montauk application plus one private conversational
  notification/command adapter. Slack is the conservative commissioning default;
  Buzz is a bounded candidate evaluated before the final channel choice.

### 2.2 Explicitly out of scope

- Multi-asset selection, allocation, sizing, or rotation. External features do
  not broaden the traded action space; multi-asset trading belongs to later work.
- Autonomous brokerage execution.
- Tax modeling, tax optimization, wash-sale/lot accounting, and multiple account
  profiles.
- Recording or reconciling Max's personal brokerage fills, account balance, or
  actual order sizes. Montauk 3.0 reports its signal and modeled execution but
  does not claim to know the brokerage position.
- An active risk-off asset such as SGOV. Risk-off earns zero in the 3.0 Gold
  comparison.
- Mandatory review by an outside human expert. Independent implementation,
  adversarial review, primary-source audit, and control evidence remain required,
  but a paid/credentialed external reviewer is not a 3.0 gate.
- Hardware procurement, provider/budget selection, and a strategies-per-hour or
  throughput acceptance target. Rust correctness and efficient implementation
  remain in scope; these deployment choices do not define completion.
- A general multi-user or commercial product.
- iOS as a 3.0 completion requirement. The companion is a 4.x/5.x convenience.
- Automatic progression to 4.x. Only Max decides when 3.0 is sufficiently proven
  to begin 4.x; no calendar interval makes that decision.

### 2.3 Priority order

**DECIDED.** When priorities conflict:

1. correctness and data integrity;
2. honest validation and protection against false Gold;
3. dependable trusted-signal operation and recovery;
4. auditability and clarity;
5. throughput and the number of configurations tested;
6. convenience and presentation.

A false Gold admission is considered slightly worse than rejecting a strategy
that might have been good.

## 3. Authority and sources of truth

Montauk must have one explicit authority path. Parallel scripts, duplicate
boards, undocumented score variants, silent fallbacks, and contradictory
artifacts are defects.

| Concern | Authority |
|---|---|
| Data fit for trusted use | Versioned deterministic data-verification contract |
| Candidate definition | Frozen source/definition plus exact parameters |
| Backtest result | Versioned deterministic engine and execution contract |
| Gold eligibility | Versioned deterministic validation contract |
| Rank and recommendation | Versioned deterministic Montauk Score/ranking contract |
| Active strategy | Explicit owner selection, except a separately specified emergency rule |
| Current trusted signal | Active Gold strategy evaluated on last verified data |
| Autonomous research priorities | Agent/scheduler policy, never certification authority |
| Core methodology changes | Explicit owner-directed, signed core release |
| Durable recovery state | Transactional authority record plus verified off-machine backup |

The AI agent may influence **what is proposed and what enters the queue**. It may
not influence a deterministic verdict after observing the answer, reinterpret a
failed gate, soften a threshold, or choose which evidence “counts.”

### 3.1 Simplicity is a safety requirement

The minimum conceptual system is:

- one untrusted idea intake;
- one deterministic backtest contract;
- one deterministic Gold exam;
- one Gold leaderboard;
- one Recommended configuration;
- one owner-controlled Active configuration; and
- one trusted signal/outbox.

Implementation details may scale each component, but may not create parallel
versions of it. A new score, state, store, scheduler, approval layer, or fallback
is permitted only when an existing concept cannot express a required safety or
operating distinction. It must have one owner, one-sentence purpose, and a tested
retirement/migration path. “More comprehensive” is not sufficient justification.

The charter owns product, Gold, and authority policy. Pillar plans own only their
implementation domain. The decision log is historical evidence, not a second
requirements specification.

## 4. The Gold contract

### 4.1 Meaning

**DECIDED; statistical and execution calibration pending.**

> **Gold means a frozen strategy configuration beats TECL buy-and-hold across
> every required real-data evaluation period, passes Montauk's complete
> versioned correctness and anti-overfitting contract, and is certified fit to
> trade to the strongest extent Montauk can establish from available evidence.**

“No detected overfitting” is the strongest honest claim. Gold is not a promise
that every trade will be correct or that future returns are certain. Markets can
change, evidence can accumulate, and a previously Gold strategy can lose Gold.
“To the best of current knowledge” therefore means the best defensible process
Montauk can assemble and independently test—not a claim that humanity can remove
market uncertainty.

Gold is binary eligibility, not rank. A Gold strategy may have disclosed
weaknesses, high drawdown, few trades, or regime dependence and still qualify if
it satisfies every hard gate. Those weaknesses affect confidence, score, rank,
and the owner's decision; they are not silently hidden.

There is no obligation to keep the board populated. An empty current Gold board
means Montauk has not found a configuration that earns certification; it never
authorizes lowering the standard.

No certificate produced by an earlier Montauk contract is automatically 3.0
Gold. During cutover, legacy rows are evidence inputs only; each exact row must
pass the final 3.0 contract from scratch before entering the current board.

### 4.2 Evidence roles

- **Real market data determines economic eligibility.** Gold must beat the
  frozen B&H comparator over complete observed TECL history and a fixed
  trailing-five-year horizon as hard gates. A small predeclared rolling-window
  contract uses a calibrated aggregate passage rule plus a calibrated
  catastrophic-window veto; it does not require every arbitrary slice to win and
  cannot grow candidate by candidate.
- **The economic margin is greater than 1.0.** The owner's provisional intuition
  is to begin with 1.10 as the unrounded full/recent point-estimate hypothesis.
  Separately, an uncertainty-aware lower bound must exceed no edge (1.0), or the
  result is insufficient evidence. Phase 1 calibrates the final margin and bound
  from controls rather than whether a favored strategy survives. No threshold
  auto-ratchets after seeing winners; changing it creates a new owner-approved
  Gold-contract version and recertification.
- **Modern/recent evidence has three explicit jobs.** It is a hard eligibility
  horizon, a ranking input through its margin of passage, and a live warning/
  revocation input under a persistent sequential rule. A single bad trade or
  week does not revoke Gold.
- **Synthetic history is diagnostic and stress evidence.** The present series is
  deterministically derived from 3x daily S&P technology-index returns
  (1993–1998), 3x daily XLK returns (1998–2008), expenses, and a loader-time
  financing/tracking-drag haircut before the real TECL seam. It reproduces from
  checked-in sources, but prior overlap audits found structural tracking and
  volatility differences from real TECL. It may influence diagnostics and
  confidence only under a separately audited weighting/stress contract; it never
  substitutes for real TECL passage. Repeated ruin, invalid behavior, or a
  predeclared catastrophic safety breach may veto Gold only after the synthetic
  model and veto rule are independently recalibrated.
- **Named moments remain visible and source-labelled.** The fixed diagnostic
  suite includes the owner's examples—2001/dot-com, 2008, 2020, 2022, tariff
  announcements—and future events added only through a methodology version.
  Pre-TECL episodes such as 2001 and most of 2008 are reconstructed/synthetic
  stress evidence, never “real TECL” passage; episodes within observed TECL
  history use verified real data. A predeclared catastrophic veto may become
  hard only after Phase 1 calibrates it on controls.
- **Untouched forward evidence is distinct.** Bars occurring after a strategy was
  frozen and certified could not have been used to design that frozen version.
  Montauk must track this evidence separately from historical validation.
  Historical replay and rolling-origin reconstruction must be labeled
  retrospective or pseudo-OOS when the family, parameter space, or selection
  policy was designed using later history; they do not become untouched evidence
  merely because the engine partitions old dates.
- **There is no permanently untouched historical lockbox.** A sealed campaign
  block supplies one-time evidence; after any metric, rank, or verdict is
  revealed, that block is marked spent/reused and the disclosure enters lifetime
  adaptive-search accounting. Only post-freeze bars in the exact row's immutable
  live-forward ledger are untouched for that row. A reusable-holdout mechanism
  may be added only after independent review proves that Montauk needs and
  implements it correctly.
- **One bad call is not revocation.** Gold is judged by the contract over
  meaningful evidence, not by demanding perfect trades.
- **Gold uses one deployable fill contract.** The signal forms only after the
  official daily bar is verified; certification fills at the next regular-
  session open plus calibrated slippage and fees. Max will submit the manual
  order after the close for execution at the next market open. Same-close and
  other OHLC fills are diagnostics/stresses only. Phase 1 calibrates costs from
  market evidence; it does not collect Max's personal fills or reopen causal fill
  timing merely because another convention produces a better backtest. The
  fixed backtesting assumption is a $10,000–$100,000 notional order band. Cost
  calibration must be defensible across that range and conservative where the
  range matters; Montauk does not collect or infer actual account or order size.
- **B&H is matched and reproducible.** It uses adjusted total-return TECL, the
  same eligible start and initial capital, the same first obtainable purchase
  timing, explicit costs, and unrounded decisions. Risk-off cash receives zero
  return in the 3.0 Gold comparison. SGOV or another active cash substitute is
  later-version work.
- **Taxes are out of scope.** The primary account is tax-advantaged. Gold
  therefore compares pre-tax returns net of the frozen execution costs and does
  not model tax lots, holding-period rates, or wash sales.

The primary economic number is the exact terminal deployable TECL wealth/share
multiple versus matched B&H. Daily net log-wealth differences support inference;
CAGR, maximum drawdown, Sharpe, and trade statistics explain the path but cannot
replace the primary Gold target.

### 4.3 The Gold exam has five planks

Every required method belongs to exactly one of these questions. The backtest
stage resolves economic passage; the later correctness/anti-overfit validation
stage resolves the other four. The five planks are the final Gold report, not
five additional stages after backtesting.

1. **Correctness:** Did causal, verified data and the frozen execution engine
   produce the claimed signals, fills, trades, and artifacts without lookahead,
   repaint, corruption, or implementation divergence?
2. **Economic passage:** Under the matched deployable contract, does the
   configuration beat TECL B&H by the required uncertainty-aware margin on the
   fixed complete/recent real-data horizons with sufficient observations?
3. **Generalization:** Does the same frozen logic remain useful outside the exact
   parameter point and historical slice that selected it—across predeclared
   temporal, parameter-neighborhood, event-concentration, and execution stresses?
4. **Search honesty:** After the complete adaptive family/configuration search is
   considered with dependence, is the result still distinguishable from the best
   outcome expected by chance?
5. **Reproducibility and currency:** Can a clean environment reproduce the row
   from immutable inputs and is its certificate current under live monitoring and
   the latest compatible contract?

Each plank has a hard pass/fail/insufficient-evidence result. Montauk Score cannot
offset one. The UI may show one light per plank and plain-English reasons; the
technical report expands the methods beneath it.

Gold has no universal minimum-trade cliff. Every method reports trades, distinct
state transitions/exposure episodes, effective observations, uncertainty width,
and power; inadequate evidence returns `insufficient` whether there are 9,
49, or 500 nominal trades.

This is deliberately **not** “run every statistical test anyone can name.” A
method enters the Gold contract only if Phase 1 demonstrates all of the
following:

- the exact failure mode it detects is relevant and not already covered;
- its assumptions and sample-size requirements fit Montauk's data;
- its implementation matches the cited method or an independently reviewed
  specification;
- positive, negative, null, and seeded-defect controls establish useful power
  without an unacceptable false-rejection rate; and
- its verdict has one predeclared decision role.

A method that fails those conditions is repaired, diagnostic-only, or removed.
Adding gates, warnings, and weighted scores without proving incremental value is
itself validation overfitting.

Hindsight annotations, hand-marked market cycles, and metrics optimized directly
during discovery may guide ideation and appear as diagnostics. They are not
independent Gold evidence and cannot enter Validation Score unless a genuinely
separate-data design and selection correction earns that role.

### 4.4 Universal rigor and search breadth

**DECIDED.** Human-authored and AI-authored candidates face the same mandatory
evidence planks and rigor. A predeclared test may have a valid equivalent or
`not_applicable` result when it is structurally inapplicable, but origin does
not earn skipped evidence, a lighter route, or silent score renormalization.

Every mandatory test must actually execute on complete required data. Compute
cost, apparent simplicity, or an upstream opinion that a test is unnecessary is
never evidence. Missing, skipped, underpowered, or unverifiable required evidence
blocks Gold. Montauk Score ranks only configurations that have already cleared
every Gold plank.

This does **not** make search history irrelevant. A simple rule discovered after
millions of adaptive attempts has a different false-discovery context from the
same rule genuinely frozen before any observation. Montauk must record the
complete observable search process and apply a defensible multiplicity or
selection-bias correction at the appropriate family, campaign, and board level.
The exact statistical mechanism remains a hard prerequisite for high-volume
autonomous search.

Dependence must be modeled honestly. A nearby configuration is not rejected or
“punished” merely because a similar configuration also works, but thousands of
near-identical rows do not count as thousands of independent discoveries or
Chimera votes. Board/lifetime correction uses effective dependence, not a naive
raw row count, while each exact configuration keeps its own evidence and row.

The validation suite itself must be validated. Before its thresholds are frozen,
Montauk must measure false-Gold detection **and** false-rejection behavior using
null/adversarial controls, simple fixed structural controls, seeded defects,
simulation, and genuine forward outcomes. Simple EMA/RSI strategies are useful
controls, not ground-truth examples of “definitely not overfit.” Until forward
calibration supports a probability interpretation, the headline is Validation
Score—not “Confidence %.”

Phase 1 reports an appliance-level frontier: the probability that at least one
null strategy becomes Gold during a simulated year of continual Montauk search
versus the recovery rate for planted economically meaningful signals. A 1%
annual probability of any false Gold is the aspirational reference, not an
already-ratified cutoff; Max approves the final achievable operating point after
seeing its false-rejection cost.

Historical generalization uses nested rolling-origin reconstruction as its
required chronological spine. Phase 1 compares expanding and fixed rolling
training variants on the same controls. It must also evaluate CPCV alongside
rolling-origin and should retain both where CPCV has a defined selection target,
adequate power, and measured incremental protection. CPCV cannot become a
ceremonial hard gate when its assumptions do not apply; such a family needs a
predeclared valid equivalent or `not_applicable` result. Purge and embargo
lengths derive from actual feature, label, and holding-outcome information
intervals, use zero when no overlap path exists, and fail candidate intake when a
required interval cannot be established.

Parameter robustness records both numeric distance and behavioral distance.
Signal, position, and trade paths are hashed so identical sparse behavior is not
counted as independent confirmation. Family/campaign/epoch search-honesty
evidence may be computed once and referenced immutably by many exact Gold rows;
that shared certificate never makes sibling rows independent Chimera votes.

### 4.5 Reproducibility

Every Gold row must be reproducible from:

- frozen strategy source or declarative definition;
- exact parameter configuration;
- data snapshot/fingerprint and comparator definition;
- feature and execution semantics;
- engine, validator, threshold, and ranking versions;
- random seeds and search/campaign provenance;
- complete gate results and retained artifacts; and
- certification and forward-evidence timestamps.

If any required component is missing, the row is not Gold.

## 5. The research funnel

### 5.1 Vocabulary

- **Idea:** a written hypothesis.
- **Family:** an organizational/statistical grouping whose configurations share
  the same trigger logic and parameter schema. It helps batching, display,
  search accounting, and Chimera dependence control; it is not a certification
  or owner-facing authority unit.
- **Configuration:** one family plus one exact parameter set.
- **Strategy candidate:** one configuration that completed a backtest.
- **Strategy:** in owner-facing summaries, a configuration; technical views must
  retain the more precise terms above.

Counts must name their funnel stage. “Strategies tested” alone is too ambiguous
at scale. A digest should distinguish, at minimum, configurations generated,
cheap-screened, fully backtested, validated, and newly Gold, plus family counts.

The configuration bucket is a logical queue, not a directory of scripts or a
requirement to materialize the whole Cartesian product. A durable family/search
shard may generate deterministic batches just in time. Each configuration that
actually executes receives an exact identity and compact result record.

### 5.2 Candidate-ready contract

Before a family can enter executable research it must include:

- executable logic or a valid declarative strategy definition;
- declared parameter domains and constraints;
- a one- or two-sentence economic or behavioral rationale;
- expected failure modes;
- required inputs, warm-up, and signal timing;
- point-in-time source, publication-lag, missingness, and provenance requirements
  for every non-TECL input;
- deterministic smoke tests;
- static/lookahead/safety-check results; and
- immutable identity and version metadata.

### 5.3 Ordered gates

The implementation preserves the one-slide conveyor while ordering work by cost:

1. validate, deduplicate, and safely compile one family definition;
2. expand exact configurations as data and run cheap screens;
3. run the matched-B&H backtest;
4. run the remaining four correctness/anti-overfit planks, including artifact
   reproduction;
5. publish every passing row to the Gold leaderboard; and
6. rank it without changing Active authority.

Failure is terminal for that exact attempt at that version; later expensive
stages do not run. A simple two-EMA family may pass correctness and anti-overfit
checks but fail economic performance, and therefore never reach Gold.

No autonomous candidate is trusted merely because a frontier model authored it.
The pipeline has to execute code before it can backtest it, so safety gates must
precede candidate execution rather than being treated as a benefit of eventual
Gold validation.

## 6. Continual ideation and search

### 6.1 Two cooperating loops

The always-on system contains two parallel loops:

- **Research intelligence loop:** read recent aggregate outcomes, leaderboard
  weaknesses, failure reasons, retired-family samples, and unused mechanisms;
  then propose ready families, repair a bounded number of invalid candidates,
  and restock prioritized queues.
- **Deterministic experiment loop:** consume queued work according to protected
  resource priorities, evaluate configurations, persist outcomes, validate
  survivors, publish Gold, and expose structured feedback.

The frontier provider is replaceable. Prompts, candidate schemas, tool
capabilities, and output contracts should not make “Claude” a system dependency.
One model at a time is sufficient. A durable OS timer invokes a bounded fresh
agent run; a provider's interactive session loop is not the scheduler or task
ledger.

### 6.2 Search policy

**DECIDED operating policy; adaptive-yield calibration pending.**

- Keep enough queued work to use available research compute without requiring
  every generated configuration to run immediately.
- Favor promising mechanisms and deliberate responses to champion weaknesses,
  while reserving a permanent exploration lane for unusual ideas.
- Initial planning allocation: approximately 70% exploitation/promising
  families, up to 20% champion-weakness work when needed, and 10% unusual
  exploration. The actual allocation should adapt to survivor yield, Gold yield,
  novelty, and operational priorities.
- Ten percent is the autonomous steady-state exploration floor, not a permanent
  owner restriction. Max may explicitly launch a named campaign with 100%
  exploration, 0% exploration, or another allocation; the override is bounded,
  visible, and audited.
- Recertification and trusted-signal work always preempt discovery research.
- Cheaply sample broad or retired families before committing deep search.
- Do not permanently condemn an indicator or mechanism merely because one
  implementation failed. Record what exact logic, region, data, and gate failed;
  preserve the indicator/data stream as available material; and keep testing
  tuned, complementary, or redesigned versions when evidence earns compute.
- Review aggregate results before generating the next batch so the agent does not
  repeat rejected configurations or get trapped in one mechanism.
- Retest exact prior configurations only when a versioned reason exists, such as
  meaningful new market data, a changed engine/validator, or a deliberate audit.

There is no fixed “one family per hour” completion target. Throughput should be
measured empirically after correctness, resource isolation, and representative
workloads exist.

A compile, timeout, memory, or other resource failure describes an implementation
attempt, not the economic configuration. Resource-bound work enters a dedicated
quarantine/repair lane with its original hypothesis intact. Limits must protect
trusted deadlines without being so tight that legitimate strategies are silently
classified as bad ideas.

## 7. System architecture

```text
MODEL OR MAX -> typed family definition using protected Rust primitives
                                |
                                v
               Rust expands exact configurations as data
                                |
                                v
                         research bucket
                                |
                                v
                       VALIDATION PIPELINE
           matched-B&H backtest -> remaining Gold validation
                                |
                             if pass
                                v
                         Gold leaderboard
                                |
                                v
                              rank
                                |
                                v
                    Max normally chooses Active
                                |
                                v
              protected signal -> manual brokerage action
```

The architecture has three trust zones:

1. **Untrusted research:** the model, generated specifications/modules, and their
   disposable sandbox. It may propose work and read bounded feedback.
2. **Sealed Montauk core:** verified data, causal execution, backtesting, the
   five-plank Gold exam, leaderboard, recertification, and trusted signal
   generation.
3. **Max authority:** Recommended/Active decisions, manual brokerage actions,
   maintenance release approval, and the read-only/chat surfaces that carry exact
   authenticated commands.

Information may flow from protected results back to ideation, but ideation's
write authority never flows into the protected core or Active state.

The high-volume experiment ledger belongs in a queryable local database, not in
millions of committed JSON files. Every durable data class nevertheless has a
GitHub-hosted off-machine recovery path: ordinary Git for protected
infrastructure, definitions, migrations, compact manifests, and human-readable
snapshots; partitioned/compressed logical snapshots, releases, or Git LFS where
appropriate for bulk artifacts. Ordinary Git blobs stay below GitHub's 100 MiB
hard limit (with an earlier internal warning). Split repositories only when a
measured size, access-control, or recovery requirement demands it. A live mutable
database is never treated as a normal Git file.

The target is no silent loss of acknowledged durable state. Authority, current
signal, approvals, and Gold lifecycle mutations are durably journaled and
replicated before acknowledgement. Each batch has a pre-batch recovery point and
an end-of-batch commit/snapshot; the maximum background sync interval is one
hour. In-flight computations may be rerun after a crash, but completed durable
results cannot disappear without an integrity failure and immediate alert.

The operational shell around these three trust zones is deliberately small:

```text
systemd timers/services -> deterministic Montauk controller
                                  |             \
                                  |              -> bounded provider adapter
                                  |                    -> candidate workspace
                                  v
                    protected Rust conveyor and authority state
                                  ^
                                  |
                   private typed channel adapter <-> Max

Max reaches the host privately through Tailscale/SSH; an optional provider
Remote Control session is for deliberate maintenance, not scheduling or
authority.
```

The complete deployment contract, service identities, acceptance drills,
Slack/Buzz selection, and OpenClaw comparison live in
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md).

## 8. Autonomous-agent authority and containment

### 8.1 Allowed

The scheduled agent may:

- author new isolated strategy families and parameter spaces;
- write rationale, failure hypotheses, tests, and metadata;
- read the leaderboard and complete failure ledger;
- submit valid candidates to intake without human review;
- analyze aggregate research outcomes and recommend the next search;
- make frequent commits in the generated-research area;
- try the original invalid candidate plus at most two immediate repairs; and
- place unresolved candidates in a lower-priority repair queue.

### 8.2 Prohibited without explicit owner-directed work

The agent may not change:

- the data pipeline or data-quality contract;
- execution timing, fills, fees, or comparator semantics;
- the backtest/search engine;
- the validation suite or Gold thresholds;
- Montauk Score, confidence, performance, or ranking formulas;
- recertification, demotion, active-strategy, or signal-authority rules;
- operations safety, sandbox policy, notification authority, or recovery rules;
- protected tests, fixtures, golden artifacts, or audit logs; or
- permissions that enforce these boundaries.

This is the highest-priority autonomy rule. It must be mechanically enforced,
not merely stated in a prompt. The smallest acceptable enforcement design is:

1. the resident agent runs as an OS identity with no core-write credential;
2. the deployed core is one read-only, content-addressed release;
3. Max's offline/human-held key signs its manifest;
4. generated research lives outside that release; and
5. startup and every Gold/signal job verify the signature, hashes, and
   permissions and fail closed on mismatch.

Repository count, branch layout, and backup tooling may support this boundary but
are not additional trust concepts. A password prompt, clean Git history, or later
rollback alone is not the seal.

Commits are rollback points, not a sandbox. Candidate execution still requires
capability denial, process isolation, resource/time limits, deterministic inputs,
and explicit output schemas. Network, arbitrary filesystem writes, subprocess
spawning, credential access, and protected-repository mutation should be denied
by default.

The agent's generated-research area is deliberately a “pool of chaos”: it may
write arbitrary candidate specifications or isolated modules there. Nothing in
that area becomes trusted because it exists or compiles. Deterministic intake,
causal access, containment, full backtesting, validation, and certification are
the only route out.

The 3.0 core keeps a provider-neutral adapter and never exposes provider
credentials to candidate workers. Whichever account, subscription/API, and
spending limit Max supplies at deployment is environment configuration outside
the 3.0 product contract; the system does not autonomously register providers or
invent a cost/failover policy. Each autonomous invocation is a bounded one-shot
job under the no-core-write agent identity. `systemd`, not a Claude `/loop`,
interactive Remote Control session, conversation thread, or another provider-
specific session feature, owns durable scheduling and restart behavior.

### 8.3 Candidate representation

Rust is the fixed production strategy/evaluation language; the agent does not
choose among Python, Go, and Rust. **DECIDED:** the normal and first production
path is a schema-constrained declarative family specification over a protected,
prebuilt Rust primitive library. The agent declares one mechanism, its typed
logic graph, parameter domains, and constraints. It does not enumerate exact
configurations. Rust performs schema/type/causality validation, canonicalizes and
hashes the graph, generates only valid parameter combinations, compiles an
execution plan once, and batch-evaluates configurations as data.

This minimizes the two errors automation can actually prevent: malformed or
unsafe strategy implementations and invalid parameter combinations. It cannot
make the economic hypothesis correct; backtesting and validation still decide
that.

A genuinely novel mechanism may eventually use one isolated Rust module compiled
once for that immutable family version, then sweep its parameter space without
recompilation. That escape hatch is disabled until its containment, causality,
determinism, resource, and parity acceptance tests pass. After Max approves the
escape-hatch policy and signed core release, individual generated modules do not
need case-by-case approval: conforming modules automatically enter untrusted
intake, and the unchanged deterministic pipeline decides their outcome. Adding a
new shared primitive still changes protected core and therefore requires a signed
owner release. Python may remain a readable
reference/parity oracle, but it is not a production strategy format or an
independent source of trading truth.

## 9. Leaderboard, recommendation, and active authority

### 9.1 Leaderboard

**DECIDED.**

- Discovery and backtesting run continuously. Once per day, Montauk freezes the
  complete eligible survivor cohort and lifetime search-ledger snapshot,
  completes the cohort-dependent search-honesty correction, assembles the final
  five-plank verdict from immutable candidate and shared artifacts, and publishes
  every passing configuration automatically with activation status **Pending
  Gold**. Candidate-local validation is not rerun under another name. The daily
  epoch does not reset prior disclosures or search history. This is automatic
  publication, not a second board, weaker exam, staging approval, or Trade
  Roster.
- Pending Gold normally accumulates 20 verified trading bars, maintains every
  required gate, and receives a fresh certification before becoming eligible to
  be Recommended or Active. Bars, trades/signals, regimes, and relative
  performance are shown separately; elapsed bars are never described as strong
  forward proof when no relevant event occurred. Max may explicitly override the
  activation delay, and that exception is conspicuous and audited.
- There is one current Gold leaderboard, not a staging board or Trade Roster.
- Every current Gold configuration is eligible for its own row.
- Rows are collapsed by family by default, showing the leading row and the count
  of hidden siblings. Every exact configuration remains queryable and pageable;
  near-identical variants do not occupy the default screen.
- The board has no conceptual maximum size; storage and views must be
  database-backed, paginated, filtered, and indexed rather than represented as
  one giant file.
- A strategy that loses Gold leaves the current board and remains in a historical
  Gold archive with the reason and versions.
- The board reranks after relevant certification, recertification, data, or score
  updates.

Every compact leaderboard row shows exactly four things: **Montauk Score,
Validation Score** (or calibrated Confidence only when calibration supports that
word), **terminal deployable TECL wealth/share multiple versus matched B&H**, and
**forward-evidence status/age**. The performance field includes a simple relative
expression such as “1.14× B&H”; the fourth field is a status, not another score.
Any additional headline metric must have one clear definition and earn its place.
Plain-English weaknesses and simple gate-state indicators should be available
without exposing a zoo of loosely related scores.

The board keeps one exact deterministic rank. When calibrated uncertainty cannot
meaningfully distinguish the leading group, it also displays **leader not
clearly separated**. That warning does not create another score or prevent
Montauk from naming one recommendation; it makes rank precision honest.

### 9.2 Recommended versus active

- **Montauk Recommended:** the highest-ranked activation-eligible Gold strategy
  under the current recommendation/switch contract. A Pending Gold row may rank
  highly on the board but cannot yet hold this authority state.
- **Active Strategy:** the owner-authorized strategy currently allowed to produce
  the trusted signal.
- **Manual Override:** an explicit persistent state showing that Active differs
  from Recommended.

A normal recommendation change does not change Active. Max may approve or
decline it; ignoring it leaves the incumbent active. The interface must make a
manual override impossible to mistake for the recommendation.

Confidence gains matter more than equally sized performance gains. A small score
improvement should not create churn. The initial versioned recommendation rule
flags owner review when any one of these holds while every Gold and secondary
non-degradation floor remains satisfied:

- Validation Score improves by at least 10 absolute points without a material
  deployable-performance loss;
- the lower-bound deployable-performance estimate improves by at least 10%
  relative without a Validation Score decline; or
- Montauk Score improves by at least 5 absolute points with neither component
  materially worse.

The candidate must remain above the entry threshold for five new verified
trading bars; a lower exit threshold supplies hysteresis. These are provisional
operating values to calibrate against recommendation churn, not permission for
the agent to tune the rule after seeing a preferred candidate.

Phase 1 must freeze the simplest Montauk Score formula that ranks already-Gold
rows from Validation Score and deployable Performance while giving validation
strength greater influence. A third pillar is admitted only if controls show
distinct, incremental decision value; relabeling or recombining existing inputs
does not qualify. The score cannot double-count a Gold method or hide a weakness.

### 9.3 Emergency loss of Gold

**DECIDED.** A normal leaderboard/recommendation change never activates a
strategy. When Active or a manual override loses Gold:

1. revoke its Active authority and any manual override immediately;
2. if the highest-ranked compatible Gold fallback emits the **same** current
   risk state as the last verified Montauk instruction, transfer the Active
   pointer automatically as a named emergency fallback, preserve the instruction,
   and send a critical alert;
3. if the fallback disagrees, preserve the last issued instruction, leave no
   strategy labeled Active, enter `human_decision_required`, display both states,
   and alert Max immediately; and
4. if no Gold fallback exists, display `no_certified_strategy`, recommend
   risk-off for Max's consideration, preserve the last instruction until Max
   decides, and perform no brokerage action.

Montauk never claims to know the actual brokerage position in 3.0 because
personal fill acknowledgement and reconciliation are out of scope. It displays
the current trusted strategy state and last issued instruction, clearly labelled
as such, and performs no brokerage action.

## 10. Data, live evidence, and recertification

### 10.1 Data failure

If current data fails verification:

- do not produce a new trusted signal;
- do not certify, recertify, demote, or mutate the current leaderboard from the
  failed/partial dataset;
- keep displaying the last verified signal with an explicit stale timestamp;
- preserve current authority state;
- raise an actionable failure for human intervention; and
- permit only low-priority deterministic research against the immutable,
  content-addressed last-good snapshot when it cannot delay recovery. Label every
  result `stale_data_research`; it cannot recertify, promote, demote, mutate the
  leaderboard, or emit a trusted signal. No survivor may enter current Gold
  until replayed through the complete pipeline on repaired, verified data.

On recovery after downtime: catch up and verify data first, then recertify the
active strategy before trusting a new signal; only then resume lower-priority
research and board maintenance.

### 10.2 Forward evidence and recertification

Montauk must track, per Gold row:

- certification/freeze date;
- untouched forward bars and elapsed market time;
- forward performance versus the frozen comparator;
- observed drawdown and trade count;
- last recertification data/version; and
- current, stale, or revoked state.

The initial scheduling contract is:

- replay Active after every verified daily bar;
- formally renew Active after 20 new verified bars, any new signal/trade event,
  any live-warning threshold, or before an activation/fallback decision;
- renew Recommended and the top cohort weekly or before activation eligibility;
- renew the remaining board after 63 new verified bars, with spare compute
  permitted to pull work forward; and
- preempt discovery whenever verification, renewal, or recovery needs resources.

These values are versioned commissioning defaults and may be recalibrated only
through an owner-approved core release. Repeating unchanged data proves replay,
not new evidence.

A core data, engine, execution, validator, threshold, or eligibility change
creates a new methodology version and immediately makes every incompatible
certificate stale. Data/correctness changes receive urgent full-board
recertification; no legacy or grandfathered configuration remains current Gold.
A genuinely ranking-only change may preserve compatible Gold evidence while the
board reranks under a named ranking version. Montauk minimizes the stale interval
but never represents stale evidence as current confidence.

Rolling recent underperformance uses a predeclared one-sided sequential rule. A
first meaningful trailing-five-year bound breach creates a warning and priority
renewal; persistence across two formal renewals separated by sufficient new
evidence revokes Gold. Correctness, causality, data, replay, or artifact failures
bypass hysteresis and stale/revoke immediately.

## 11. Storage, audit, and failure memory

The experiment database retains a compact permanent record for every attempted
configuration:

- identity, family, parameters, and campaign;
- generation and evaluation timestamps;
- data/engine/validator versions;
- funnel stage reached;
- key metrics;
- terminal failure code and plain-English reason; and
- references to retained artifacts.

Full artifacts are retained permanently for current/historical Gold and a
stratified audit sample, and for at least one year for near-Gold. For an exhausted
region with near-zero measured chance of Gold, bulky per-configuration traces may
expire after a compact lossless-enough summary records the exact tested space,
versions, aggregate results, representative failures, and deduplication keys.
The archive must be sufficient to avoid unknowingly repeating the same failed
work. Generated strategy source is retained even after retirement so later agents
can study or redesign it.

The failure ledger is part of the research intelligence, not a trash pile. The
agent should read it to avoid exact repetition, distinguish implementation
failure from mechanism failure, identify complementary mechanisms, and sample
retired families when new data or a material redesign justifies it.

Silent fallback and swallowed error behavior are prohibited. Every operational
failure has a structured code, ownership, safe state, retry policy, escalation
policy, and durable audit event.

Every durable class has local integrity protection and an off-machine GitHub
copy. Use multiple repositories by responsibility when needed; keep regular Git
objects below platform limits; and use partitioned snapshots/LFS/releases for
large immutable artifacts rather than committing a changing database file. A
pre-batch recovery point and end-of-batch or hourly sync—whichever comes first—
bound exposure. Authority/Gold mutations are replicated before acknowledgement.
Backup corruption, GitHub sync failure past its bound, or any lost acknowledged
state is a critical alert. Restore drills must prove the copies, not merely prove
that a push command ran.

## 12. User experience

The primary experience should answer:

1. What is the current trusted TECL state?
2. Which strategy is active, is it still Gold, and is it a manual override?
3. Why is it still the most defensible active choice?
4. Is a materially better recommendation waiting?
5. Is anything broken or stale?
6. Is research making useful progress?

The app is primarily read-only. Validation gates should appear as simple,
traceable pass/fail lights with plain-English explanations such as “most of the
historical advantage came from one event,” with detailed evidence available on
demand.

The notification surface begins with one daily digest because Montauk does not
trade intraday. The digest includes the trusted state and any change, Active
Gold/override status, Pending Gold and recommendation changes, honest funnel
counts, new Gold rows, important board movement, forward-evidence/
recertification status, and actionable failures.

Within five minutes of detection, attempt immediate delivery for verified-data
failure, a missed required-signal deadline, Active losing Gold, no compatible
fallback, authority/control-store corruption, artifact-integrity failure, or a
sandbox escape attempt. Three consecutive research-cycle failures or one systemic
pipeline defect also alert; isolated candidate failures remain in the digest.
Max may route these classes into separate rooms in the selected channel.

The selected private channel supports conversation plus exactly these state-
changing 3.0 commands:

- request a named ideation/research campaign;
- trigger recertification;
- approve one exact pending Active-strategy switch.

Status/explanation queries are read-only. Every mutation requires Max's
allowlisted identity, an immutable request/strategy ID, explicit confirmation,
expiry, idempotency, replay protection, and a durable audit event. The channel
adapter cannot acknowledge alerts, enter/exit maintenance mode, modify
methodology, or infer approval or execution from free-form conversation. Channel history is never the
audit log; the control database and notification outbox remain authoritative.

Montauk has one provider-neutral typed channel-adapter contract and deploys only
one primary provider at a time. Slack Socket Mode is the conservative
commissioning default because it already supplies mature phone clients and push
delivery without a public webhook. Before committing to it, a bounded bake-off
may select Buzz if Buzz proves equally reliable for Max's phone/digest workflow,
passes the identical identity/confirmation/replay/recovery tests, and earns its
greater self-hosting and operations cost through materially better agent/thread
continuity. Max makes that final UX choice from measured evidence; the rejected
adapter does not remain as a parallel command path.

Buzz's signed events, agent identities, searchable rooms, and JSON/ACP surface
are useful outer-channel features, not Montauk authority. Buzz's relay/audit
history cannot become a second command truth, and its shell/file agent receives
no protected credentials or writes. Direct Claude-in-Slack is likewise not the
Montauk control plane because it does not authorize the local appliance.

Tailscale plus SSH is the independent administration and recovery path; it is not
replaced by a channel or model. A provider's Remote Control feature may expose a
deliberately started local repair session, but it inherits that Linux identity's
permissions and never changes the core boundary.

Montauk borrows OpenClaw's and Buzz's useful **interaction patterns**: one long-
lived gateway boundary, typed messages, stable thread/session routing, per-session FIFO
and global backpressure, exact scheduled jobs separated from health checks,
durable task/audit state, immediate run status, idempotent side effects, private
remote access, and health/doctor probes. It does not adopt OpenClaw as Gold,
queue, audit, signal, or Active authority; nor does it import broad computer
control, plugin breadth, inferred conversational authority, or host-level agent
execution. Neither OpenClaw nor Buzz is trusted as Montauk's authority; OpenClaw
is not a required 3.0 dependency, while Buzz is only the bounded Slack
alternative described above.

## 13. Chimera

Chimera is a candidate family in which several strong strategies vote or
contribute confidence to a system-level risk estimate. It receives no special
Gold treatment and no shortcut.

Chimera work waits until several materially independent Gold strategies exist
and independence can be measured. If no ensemble beats the best single strategy
under the same contract, keeping the single strategy is a valid result.

## 14. Performance implementation

Accuracy is more important than speed; speed matters because it determines how
many honest experiments the available host can evaluate. Profiling and efficient
Rust implementation remain normal engineering, but hardware selection, provider
budget, and a numerical throughput target do not gate Gold or 3.0 completion.

The preferred direction is:

- a legible reference implementation and frozen behavioral fixtures;
- a prebuilt high-performance Rust evaluator and reusable primitive library;
- a coverage matrix proving exact reproduction of the legacy Active strategy
  needed for safe shadow/cutover, the matched B&H/execution reference, every
  final validation control/benchmark, and any legacy strategy Max explicitly
  selects for migration;
- compact strategy definitions for normal composition;
- at most one isolated compiled Rust module per genuinely novel family, not a
  newly compiled program for every parameter configuration;
- profiling on representative workloads;
- shared/vectorized/precomputed indicator work where semantics allow;
- optimized Rust kernels and evaluator paths only for measured bottlenecks; and
- parity tests with bit-for-bit equality where possible and explicit,
  tolerance-pinned equivalence otherwise.

The deployment baseline supports that work with release-mode Rust builds, live
data/control state on SSD, matched-channel RAM, wired networking, controlled
updates/reboots, no sleep, stable cooling, and preferably a UPS. Research uses
all spare resources through bounded batches and lower OS/controller priority;
physical versus logical thread count, memory cap, batch size, and thermal ceiling
are measured on the actual tower. A small emergency swap area may prevent an
instant crash, but sustained swapping is an alert and load-shedding condition.
Kernel, governor, filesystem, and low-level tuning occur only after profiling.

Compilation proves syntax/type properties, not trading correctness, absence of
lookahead, or validity of the edge. No optimized path may become an independent,
unreconciled source of trading truth.

The first primitive vocabulary covers typed arithmetic/boolean composition,
lags/rolling values, TECL OHLCV and approved external inputs, SMA/EMA/WMA,
momentum/ROC, RSI/MACD, ATR/volatility/bands, crossover/threshold events, and
explicit entry/exit/hold/cooldown/position state. Primitives remain small,
independently fixture-tested, causal, and protected. Missing expressiveness
creates a module or primitive proposal; it never silently kills an idea.

## 15. Definition of done

Montauk 3.0 is ready for Max to call complete when:

- the full loop in §1 operates automatically on the dedicated host;
- the protected-core boundary is mechanically enforced;
- the Gold contract and search-breadth correction are versioned, tested, and
  defensible;
- every published Gold row is reproducible;
- data failure, restart, offline recovery, stale evidence, and active-Gold loss
  enter explicit safe states and escalate correctly;
- the recommendation/active distinction and owner authority are unambiguous;
- the system can continuously generate, test, learn from, and revisit strategy
  research without queue starvation or silent failure;
- the minimal Debian host, `systemd` supervision, service identities, SSD/hot-
  storage policy, private Tailscale/SSH recovery path, bounded provider adapter,
  and the one selected private channel adapter pass their operational and
  authority drills;
- the current signal and its justification are legible at a glance;
- the system has passed representative end-to-end, recovery, security, parity,
  and unattended-soak acceptance tests; and
- Max decides the evidence is sufficient.

An unattended soak test is evidence for Max's decision, not an automatic project
transition. Only Max declares 3.0 complete, and later-version work begins only
after a separate explicit instruction from Max.

## 16. Required calibration and design evidence

Questionnaires 3–5 settled the owner-visible policy. Max explicitly noted that
technical language was often unclear; §0.1 therefore governs all interpretation.
Every decision report starts with a simple explanation and a simple example,
then states the recommendation, measured false-Gold/false-reject consequences,
and known limits. Formulas, papers, and implementation details belong in an
appendix. The following are bounded Phase 1 studies—not open invitations for a
coding agent to optimize around a current winner or attribute unstated
statistical opinions to Max:

1. **Execution study:** implement the fixed signal-after-verified-close,
   next-regular-session-open contract; calibrate slippage/fees and OHLC stress
   diagnostics from market evidence across the fixed $10,000–$100,000 modeled
   order band; and freeze the matched B&H comparator. Personal fill, balance,
   and actual-order-size capture or reconciliation are out of scope.
2. **Economic-gate study:** retain complete observed TECL history and trailing
   five years as hard gates; calibrate the small rolling-window aggregate and
   catastrophic-veto rules, the provisional 1.10 point-estimate margin, and the
   one-sided lower bound above 1.0; and show both missed-good and admitted-bad
   behavior. The primary estimand is terminal deployable TECL wealth/share
   multiple versus matched B&H.
3. **Synthetic-data study:** independently reproduce and overlap-calibrate the
   technology-index/XLK construction, financing drag, volatility/tracking error,
   weights, and any catastrophic veto. Extend the XLK-based synthetic
   transformation through the observed TECL era, calibrate only on earlier
   overlap blocks, and evaluate later blocks without refitting. Compare modeled
   and actual daily returns, terminal path, volatility, drawdowns, tracking
   error, and named-event behavior. Build a predeclared named-moment suite and
   label every result observed-real or reconstructed/synthetic; pre-inception
   episodes never count as real TECL passage.
4. **Validation-of-validation study:** audit every final admitted method and
   threshold; distinguish frozen historical replay, nested rolling-origin
   reconstruction, spent/reused holdouts, and genuinely post-freeze forward
   evidence; require nested rolling-origin and compare expanding/rolling
   variants; evaluate CPCV alongside it and make CPCV hard only where a defined
   target, causal purge/embargo interval, adequate power, and incremental control
   value justify it; test null, adversarial, simple structural, seeded-defect,
   planted-signal, and forward controls; report Type-I/false-Gold and Type-II/
   false-rejection behavior; map the annual appliance-level risk/recovery
   frontier around the aspirational 1% any-false-Gold reference; and define what
   Validation Score measures and whether it can ever be calibrated as a
   probability. No permanent historical block is described as untouched after
   its result is revealed.
5. **Multiplicity study:** preserve lifetime hierarchical search provenance and
   every holdout reveal; seal one immutable shared correction artifact per
   family/campaign/daily certification cohort; separate numeric parameter
   neighbors from identical signal/trade behavior using behavioral hashes; and
   select an independently reviewed within-family plus board/lifetime method that
   handles correlated configurations and continuous adaptive feedback without
   treating raw row count as independence.
6. **Containment/seal study:** demonstrate the resident identity has no core-write
   credential, the signed read-only core fails closed, causal workers remain
   contained, resource failures quarantine/repair safely, and the acceptance
   suite can enable automatic isolated-module intake.
7. **Recovery/storage study:** prove no loss of acknowledged authority/Gold state,
   bounded batch recovery, measured artifact-size/restore topology, corruption
   detection, and clean GitHub-hosted restore.
8. **Ranking study:** freeze the smallest Montauk Score formula from Validation
   Score and deployable Performance, prove any additional input is independently
   useful, calibrate recommendation churn, and define when the board shows
   `leader not clearly separated` without creating another headline score.
9. **Acceptance matrix:** attach a stable test ID, invariant, fixture, threshold,
   artifact, safe failure state, rollback, and Max sign-off field to every phase
   exit and safety-critical operating invariant.

The performance margin, false-Gold operating point, validation package,
activation/renewal schedule, ranking ambiguity, and switch thresholds remain
provisional until these reports exist. Max approves the recommended package in
plain language. Later fine-tuning requires a new versioned control study and
owner approval; it is never an autonomous adjustment to preserve or remove a
particular strategy.

The completed questionnaire remains unchanged as source evidence. The decision
log records the resulting calls; this charter and its pillar plans are the
current planning truth.

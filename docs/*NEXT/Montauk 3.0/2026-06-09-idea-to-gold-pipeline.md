# Montauk 3.0 Idea-to-Gold Pipeline

**Status: RATIFIED OPERATING PLAN; CALIBRATION PHASE READY (2026-07-21).** This
replaces the earlier rare-authoring/nightly-drain plan. It implements the
Questionnaire 3 operating contract in
[charter.md](charter.md) and [decisions.md](decisions.md): continuous
model-agnostic ideation, untrusted candidate containment, deterministic
evaluation, automatic Gold-to-leaderboard publication, and human authority over
normal active-strategy changes.

This is a safe handoff for **Phase A contract research and protected-boundary
prototyping**, not blanket permission to build the autonomous appliance around
guesses. Phase A must turn the ratified policies into empirically calibrated,
versioned, Max-approved executable contracts before downstream implementation.

## 1. Goal

Accept a human idea or continuously generate new strategy families, turn their
parameter spaces into exact configurations, cheaply reject weak work, fully
backtest and validate survivors, and publish every reproducible Gold
configuration without human research maintenance.

The pipeline optimizes for:

1. false-Gold prevention;
2. correct and reproducible trusted signals;
3. legibility and recovery;
4. maximum useful throughput on available hardware.

“More configurations tested” is useful only when every attempt remains inside the
same honest accounting and methodology contract.

## 2. Four planes and one-way authority

Montauk 3.0 separates four planes:

1. **Untrusted ideation plane.** A scheduled, model-agnostic frontier agent reads
   permitted research summaries, authors new families, and repairs its own
   candidate artifacts.
2. **Sandboxed strategy-execution plane.** Candidate definitions are parsed,
   statically checked, capability-restricted, smoke-tested, and evaluated without
   credentials or write access to the core.
3. **Protected deterministic plane.** Verified data, backtest semantics,
   validation, Gold, scoring, ranking, recertification, and signal generation.
4. **Human-authorized operating plane.** Recommended strategy, active strategy,
   last verified instruction, owner approvals, alerts, and audited commands.

Information may flow from deterministic results back to ideation. Write authority
never flows from ideation or candidate code into the protected or active-authority
planes.

The agent decides what to propose. The scheduler decides what receives compute.
The protected pipeline decides what the evidence says. Max decides normal active
strategy changes.

## 3. Canonical terms and counts

| Term | Meaning |
|---|---|
| Idea | Written hypothesis about a possible signal mechanism |
| Family | One trigger/decision graph plus one parameter schema; an organizational and batching unit, not a certification unit |
| Configuration | One family version plus one exact parameter set |
| Candidate | A configuration that completed the required backtest |
| Pending Gold | A candidate that passed the historical suite and is accumulating its required untouched forward evidence |
| Gold row | One exact configuration that passed every current Gold requirement, including any Pending Gold requirement |

Owner-facing copy may call a configuration a “strategy.” Operational metrics must
name the stage:

- families proposed and accepted;
- configurations expanded;
- configurations cheap-screened;
- configurations fully backtested;
- candidates fully validated;
- Pending Gold configurations and forward bars accrued; and
- new/current/revoked Gold rows.

A generated combination that never ran is not “tested.”

## 4. Candidate-ready contract

A family cannot enter executable intake until it is submitted through the
versioned structured StrategySpec contract. The agent authors one family/search
space; it does not enumerate exact configurations. The specification contains:

- immutable family and version identity;
- executable logic or a valid typed/declarative definition;
- parameter names, types, domains, constraints, and intended search method;
- a one- or two-sentence economic/behavioral rationale;
- expected failure modes;
- required inputs and warm-up;
- for every non-TECL input: source identity, point-in-time availability,
  publication/revision lag, missing-data behavior, and causal-access declaration;
- explicit signal timing;
- deterministic smoke tests and expected results;
- static lookahead/capability-check results;
- author/provider and generation-run provenance; and
- content hash plus parent/redesign lineage.

Rust is the fixed production authoring/evaluation target; the agent never chooses
the implementation language. The high-throughput distinction is:

- **normal family:** the agent submits a compact schema-constrained definition
  over a versioned prebuilt Rust primitive registry. The definition is
  declarative data, not Python code. Unknown primitives, invalid types, causal
  violations, and malformed constraints fail before evaluation;
- **novel family:** the agent may emit one isolated Rust module, compiled once for
  that immutable family version; and
- **configuration:** the trusted evaluator supplies exact parameters to the
  already-built family evaluator. It never compiles a new program per
  configuration.

This is how millions or billions of configurations can share one compiled
execution plan, precomputed indicators, memory layouts, and batched execution.
Python may remain a reference/parity oracle and test harness, but not a production
family or configuration representation. The isolated Rust-module route is staged
and disabled until its signed containment, causality, determinism, resource, and
reference-parity acceptance suite passes. Once Max approves that **policy**, each
conforming module may enter untrusted intake automatically; Max does not approve
modules one by one. Shared primitives and the module SDK remain protected core.

Illustrative manifest only—the final schema remains to be chosen:

```yaml
family_id: vivid_otter
version: 1
definition_hash: sha256:...
representation: composition_v1
author:
  kind: frontier_agent
  provider: replaceable
mechanism: >
  Reduce exposure when medium-term trend weakens under elevated volatility.
expected_failure: >
  Rapid whipsaw in low-volatility sideways markets.
inputs: [tecl_ohlcv]
signal_timing: pending_contract
parameters:
  fast_window: {type: int, min: 5, max: 80}
  slow_window: {type: int, min: 40, max: 400}
  vol_window: {type: int, values: [10, 20, 30, 60]}
constraints:
  - fast_window < slow_window
smoke_fixture: fixtures/strategy_contract_v1
```

Names should follow the owner's adjective-animal convention. Names are labels,
not statistical identities.

## 5. The cost-ordered funnel

```text
verified data + frozen methodology
              |
              v
family proposal -> schema/policy/dedup -> isolated smoke
              |
              v
configuration expansion + cheap screen
              |
              v
full required backtest and B&H performance gates
              |
              v
complete correctness / anti-overfit / robustness validation
              |
              v
artifact and reproducibility verification
              |
              v
Pending Gold -> untouched forward evidence + fresh certification
              |
              v
Gold certification -> leaderboard row -> recommendation evaluation
              |
              v
structured results and failures -> next ideation cycle
```

### Stage 0 — operational preconditions

Before trusted work:

- the control database is healthy;
- the last committed methodology/version set is internally consistent;
- the deployed protected-core manifest has a valid signature from Max's
  human-held release key, all protected hashes and permissions match, and the
  resident agent cannot access that key;
- required market data is complete, verified, and fingerprinted;
- active-strategy signal and recertification deadlines have resource priority;
- the most recent durable recovery point is healthy and its off-machine GitHub
  replication is inside the allowed window; and
- the experiment worker has enforced CPU, memory, temperature, and disk limits.

Research may be preempted at any point by data, trusted-signal, active
recertification, recovery, or notification work.

### Stage 1 — agent ideation and bounded repair

On a tunable schedule, initially imagined as roughly hourly:

1. read aggregate results from the last completed interval;
2. read exact-duplicate summaries, family histories, failure-reason aggregates,
   leaderboard composition, and active-champion weaknesses;
3. choose work across promising, weakness-repair, and exploratory lanes;
4. author one or more ready families/search spaces;
5. run local schema/static/smoke tooling;
6. try the original artifact plus at most two immediate repairs; and
7. submit valid artifacts or enqueue unresolved ones for low-priority repair.

The agent may predict which work is promising for queue ordering. That adaptive
selection must be logged as part of search provenance; it cannot be treated as
free evidence.

### Stage 2 — untrusted intake

Intake is deterministic and fail-closed:

- parse and validate the manifest;
- content-address and version the family;
- reject exact duplicates under the same data/engine/validator fingerprint;
- reject prohibited capabilities and imports;
- deny network, secrets, arbitrary filesystem writes, subprocesses, and core
  mutation;
- run in a disposable worker behind a causal feature API or equivalent
  prefix-replay-enforced input boundary—read-only access to a full future array is
  not sufficient;
- enforce time/CPU/memory/output limits;
- verify deterministic output under repeated seeded runs;
- run lookahead/static checks and golden smoke fixtures; and
- persist a structured failure or admit the family to configuration expansion.

A compile failure, timeout, OOM, or resource-limit hit protects the appliance; it
does **not** establish that the underlying idea is bad. It enters the quarantine/
repair lane with a precise reason. Candidate code cannot raise its own limits.

Git commits are useful history and rollback. They are not a substitute for this
boundary.

### Stage 3 — configuration expansion and cheap screening

The trusted engine, not the model, expands parameter spaces. It should:

- type-check and canonicalize the family graph against the exact primitive
  registry version;
- apply declared constraints before evaluation;
- generate canonical configuration identities;
- use version-aware exact deduplication;
- reuse safe precomputed indicators where semantics permit;
- compile/optimize one internal execution plan per family version rather than per
  exact configuration;
- record every configuration actually evaluated;
- run the cheapest correctness and economic screens first; and
- promote only survivors to full backtesting.

Related variants are legitimate configurations. Family-level “near twin”
similarity may help presentation or compute allocation, but must not silently
erase exact configurations the owner wants tested.

### Stage 4 — full backtest and economic eligibility

Every survivor runs the required real-data backtests under one frozen executable
contract:

- signal observation timestamp and earliest genuinely obtainable manual fill;
- matched B&H start, first purchase, costs, distributions, and unrounded values;
- fees, spreads/slippage, zero initial risk-off cash return, and missing-bar
  behavior;
- warm-up and boundary rules;
- complete real history, a recent horizon initially centered on trailing five
  years, and a small predeclared rolling/window robustness design; and
- a one-sided or equivalently uncertainty-aware superiority margin, calibrated
  around Max's provisional 1.10 starting intuition.

Configurations that fail required B&H/performance gates stop here. The exact
fill estimator, horizon/window design, uncertainty floor, and margin are bounded
Phase A calibration studies; the implementation agent may not choose convenient
values. Same-close certification is prohibited when the strategy consumed that
close. OHLC average/high/low and close-fill results are diagnostics unless their
availability and executability are proven.

Synthetic history runs as a diagnostic/confidence input, not as real passage. Its
present construction uses 3x daily S&P technology-sector-index returns
(1993–1998), 3x daily XLK returns (1998–2008), expenses, daily compounding, a
real-TECL seam, and a loader-time 189.7 bps/year financing/tracking haircut. The
builder is reproducible, but prior audits found material volatility/tracking
differences from actual TECL. Phase A must independently recalibrate any weight or
catastrophic veto on overlap and model-error controls before either can affect
Gold.

### Stage 5 — complete validation

Every remaining candidate, regardless of human or AI origin, must satisfy the
same mandatory versioned evidence planks and rigor. Structurally inapplicable
algorithms require a predeclared equivalent or valid `not_applicable` outcome;
they do not disappear through silent score renormalization. At minimum the target
contract covers:

- engine/data/integrity correctness;
- no lookahead, overlap, or repaint;
- independent comparator/golden regression;
- complete search-path and family/campaign provenance plus dependence-aware
  selection-bias accounting; raw counts of highly related configurations are not
  automatically independent trials;
- parameter-neighborhood and walk-forward behavior;
- PBO and performance deflation;
- stationary-bootstrap uncertainty and minimum evidence;
- parameter sensitivity and fragility;
- event, regime, and return concentration;
- execution degradation;
- board-level multiple-testing control;
- artifact completeness and independent reproduction; and
- explicit confidence limits and data-scarcity disclosure.

No mandatory result may be missing, skipped, underpowered, or unverifiable and
still receive Gold. Montauk Score ranks configurations only after all hard planks
pass. Until forward calibration supports a probability interpretation, the
headline is **Validation Score**, not “confidence percent.”

The validator is itself under test. Phase A must measure both false-Gold and
false-rejection behavior using null/randomized controls, seeded leakage and
overfit defects, simple frozen structural controls, simulation, and later
per-row forward outcomes. More gates or a lower pass rate do not by themselves
prove rigor.

The pipeline does not “give everything its due diligence” by wasting full
validation compute on candidates that already failed. It does so by applying the
correct decisive test at every stage and recording why work stopped.

### Stage 6 — Pending Gold, Gold, leaderboard, and recommendation

A historical-suite survivor enters deterministic `Pending Gold`; this is not a
human Trade Roster. Publication is transactional:

1. freeze the strategy definition and exact parameters;
2. finalize complete artifacts and fingerprints;
3. create the Pending Gold certification record;
4. atomically expose its state in the evidence/leaderboard surface;
5. accrue 20 verified trading bars under that exact frozen identity;
6. run a fresh complete certification;
7. if it still passes, automatically graduate it to current Gold, calculate its
   score/rank, and evaluate Recommended; and
8. emit the appropriate digest/event.

Pending Gold cannot be Active. Max may explicitly override the waiting delay,
but the exception is conspicuous and audited. Only the latest compatible
validation contract appears on the current Gold board; incompatible older rows
become stale and must recertify rather than remain grandfathered.

Gold publication and recommendation changes never alter Active. Normal
activation requires Max's audited approval of one exact configuration. Initial
review thresholds are +10 absolute Validation Score points with no material
performance loss, +10% relative lower-bound deployable performance with no
Validation decline, or +5 Montauk Score points with neither component materially
worse; the advantage persists for five verified bars with hysteresis. These are
versioned calibration defaults, not agent-tunable values.

If Active loses Gold, its authority and any override end immediately. A same-
state top Gold fallback may take the Active pointer automatically without
authorizing a new trade. An opposing-state fallback leaves no Active, preserves
the last verified instruction, enters `human_decision_required`, and alerts Max.
If no Gold remains, Montauk enters `no_certified_strategy`, recommends risk-off
for human consideration, and takes no brokerage action.

### Stage 7 — feedback and memory

Every terminal result writes a structured record:

- exact identity and versions;
- stage reached and compute used;
- metrics measured at that stage;
- pass/fail code and plain-English reason;
- source campaign and queue lane;
- parent/revision lineage; and
- artifact references.

The next ideation cycle receives aggregates and representative examples—not an
unbounded raw dump. It should learn:

- which implementations failed to compile or violated safety rules;
- which parameter regions lack economic traction;
- which mechanisms repeatedly fail specific gates;
- which champion weaknesses remain unaddressed;
- which families are overrepresented;
- which retired families deserve a small resample; and
- which novel combinations have not been explored.

“Retired” means low priority under current evidence, not permanently forbidden.
A family may be revisited with meaningful new data, a complementary primitive, a
champion weakness, periodic sampling, or a material redesign.
No indicator, external input, or broad mechanism is condemned because one family
or parameter region failed. The ledger distinguishes a failed exact
configuration, a weak searched region, an implementation problem, and an
unpromising trigger graph so the agent can tune, combine, or redesign without
repeating the same work.

## 6. Scheduling and resource allocation

Priority order:

1. **P0:** verified-data refresh, active-signal generation, active-strategy
   forward replay/recertification;
2. **P1:** recovery, integrity failures, critical notifications;
3. **P2:** recommendation/top-cohort and rolling full-board recertification;
4. **P3:** candidate validation and Gold finalization;
5. **P4:** preemptible discovery research and low-priority repair.

Initial discovery planning uses approximately:

- 70% promising families/regions;
- up to 20% active-champion weakness work when useful; and
- at least 10% unusual exploration.

These are adaptive allocations, not scientific facts. In autonomous steady
state the scheduler changes them from observed useful yield while preserving the
10% exploration default. Max may explicitly launch a bounded campaign with any
allocation, including 0% or 100% exploration. Queue backlog is acceptable. Queue
starvation should wake the ideation loop rather than ask Max for routine
maintenance.

## 7. Persistence model

The target scale requires more than Markdown and JSON queues. The operational
design should include:

- a transactional control database for families, versions, configurations, jobs,
  certifications, recommendation/active state, recertification state, and a
  notification outbox;
- append-only, compressed, partitioned experiment results for high-volume
  screens;
- content-addressed immutable artifacts for Gold and near-Gold candidates;
- compact reproducible Gold manifests/snapshots plus protected code, strategy
  source/specs, schemas, and signed manifests on GitHub-hosted recovery paths;
- pre-batch recovery points, end-of-batch commits/snapshots, and a maximum
  one-hour background replication interval; and
- tested database backup, restore, and corruption-recovery procedures.

The leaderboard is a query/materialized view over current Gold certifications,
not a manually edited file. The historical Gold archive is an immutable status
history, not a deletion pile.

Storage volume must be benchmarked. At extreme claimed throughput, even a tiny
record per configuration can exceed local-disk capacity; retention and
aggregation tiers must be derived from measured bytes/configuration and recovery
needs.

The durability contract is zero **silent** loss of acknowledged completed state,
not preservation of every CPU instruction in flight. Authority, signal,
approval, and Gold mutations replicate before acknowledgement. In-flight compute
may rerun. Every evaluated configuration keeps a compact permanent identity,
version, parameter, verdict, reason, and dedup record. Full Gold/historical-Gold
and audit-sample artifacts are permanent; near-Gold is retained at least one
year. Bulky hopeless-region traces may expire only after an archive precisely
describes the tested region and prevents wasteful accidental retesting.

Do not commit a live mutable database as an ordinary Git file. Ordinary Git
blobs stay below GitHub's 100 MiB hard block and should be kept well below it;
use partitioned immutable snapshots, releases, LFS where appropriate, and
separate repositories by responsibility. The transactional database/outbox is
the operating authority; GitHub is its tested off-machine recovery path.

## 8. Protected-core rules

The autonomous agent's write credentials must be incapable of changing:

- data acquisition/verification;
- backtest/execution/comparator semantics;
- search accounting;
- validation and Gold thresholds;
- score/ranking;
- board/active authority;
- signal generation;
- operations safety and recovery;
- protected tests/golden fixtures; and
- the permissions themselves.

Enforce this with separate protected-core and generated-research repositories or
workspaces, distinct OS identities/credentials, read-only deployed core,
protected remote branches, and a content-addressed release manifest signed by a
human-held key unavailable to the resident agent. Startup, testing, publication,
and trusted signals fail closed if the signature, hash set, or permissions do not
verify. A password alone, clean Git history, or rollback after mutation is not a
seal.

Core changes occur only in an explicit Max-authorized maintenance/release mode
with reviewed diff, protected tests, a newly signed manifest, audit record, and
credential revocation on exit. A material methodology change stales incompatible
Gold rows and starts urgent recertification; a ranking-only change may preserve
compatible certificates under a new rank version. Generated strategies remain
isolated and immutable by family version; the agent does not append autonomous
work into one shared monolithic strategy file.

## 9. Delivery sequence for a coding agent

Do not build the hourly agent first. Build the truth and containment boundaries
it will depend on. Every phase needs named artifacts, tests, rollback/cutover
instructions, and a blocking exit review; a phase title is not permission to
invent the empirical calibration values inside it.

### Phase A — freeze and test the contracts

- Run a timestamped execution study and freeze the manual workflow, earliest
  obtainable fill, slippage/spread stresses, and exactly matched B&H semantics;
  same-close certification is permitted only if causally executable.
- Calibrate and freeze the complete-real, trailing-five-year-centered, small
  rolling/window design; the provisional ~1.10 superiority margin; one-sided
  uncertainty floor; minimum trades/track record; and persistent rolling
  warning/demotion behavior. Avoid retrospective “reasonable slice” invention.
- Independently audit the synthetic TECL model against its real overlap and
  model-error controls. Freeze its construction/version and decide from evidence
  whether it has a diagnostic weight or catastrophic veto; it never substitutes
  for real passage.
- Complete the line-by-line validation correctness audit. Add a validation-of-
  validation harness measuring false-Gold **and** false-rejection behavior with
  randomized nulls, seeded lookahead/overfit defects, simple frozen controls,
  simulations, and an ongoing per-row forward calibration dataset.
- Define Validation Score as an evidence-strength index; do not display it as a
  probability until a frozen outcome target and forward reliability study
  support that interpretation.
- Specify multiplicity as a formal statistical design: tested universe,
  within-family versus board/lifetime scope, online versus batch behavior,
  dependency clustering, alpha/sequential policy, and whether a new search can
  change an existing certificate. Calibrate it with simulation and independent
  review. Do not equate a raw count of correlated variants with independent
  hypotheses or erase legitimate exact rows.
- Write transition tables and invariants for jobs/candidates, certifications,
  Pending Gold/current Gold, Recommended/Active/override, the five-bar switch
  persistence rule, stale data, same/opposing-state fallback, no Gold,
  `human_decision_required`, and the exact states permitted to emit a trusted
  instruction.
- Design the cryptographic protected-core release seal, human-held-key ceremony,
  repository/OS credential split, module acceptance policy, and fail-closed
  startup checks. Candidate code receives no core or provider credentials.
- Freeze recertification triggers: Active replay each verified bar and formal
  renewal every 20 new bars/event/warning/pre-activation; top cohort weekly; rest
  after 63 new bars; incompatible contract change stales rows immediately.
- Reconcile the resulting truth into canonical repository docs and tests,
  including `CLAUDE.md`, `docs/charter.md`,
  `docs/validation-thresholds.md`, and
  `docs/validation-philosophy.md`; publish one version/hash manifest so these
  3.0 planning files do not become a parallel authority.
- Turn every contract into versioned schemas, fixtures, decision tables, and
  acceptance tests.

**Exit:** Max ratifies the calibrated contract package; the validation audit,
false-positive/false-negative study, synthetic/execution studies, multiplicity
design, core-seal threat model, and state tables have review evidence; no
canonical doc/test says “top row is automatically active,” labels an
uncalibrated score as probability, permits a skipped Gold plank, or preserves an
incompatible validation route.

### Phase B — representation, causality, containment, and scale prototypes

- Prototype the prebuilt Rust evaluator and primitive library with typed
  strategy definitions on representative current and novel families.
- Build a primitive coverage matrix and reproduce every current production,
  current/historical Gold, benchmark, and simple validation-control strategy.
  The initial small fixture-tested registry covers arithmetic/boolean operations,
  lag/rolling access, moving averages, momentum, RSI/MACD, ATR/volatility/bands,
  crossover/threshold events, approved external inputs, and explicit position
  state.
- Implement a structured StrategySpec submission tool exposing the exact
  primitive registry/schema; prove malformed types, invented primitives, invalid
  constraints, and causal violations fail before configuration generation.
- Compile each accepted declarative family graph into one optimized internal Rust
  execution plan, then reuse it across the full parameter sweep.
- Separately prototype one isolated agent-authored Rust family module to measure
  compile/repair cost and containment burden, but keep the module route disabled
  in autonomous operation until its signed containment, causal-access,
  determinism, resource, and reference-parity acceptance suite passes. After Max
  approves that policy, conforming modules graduate to untrusted intake without
  per-module owner approval.
- Provide a causal feature/signal API or prove prefix-replay invariance so
  read-only access to a full historical array cannot create future-data leakage.
- Prototype disposable workers, capability denial, static checks, core
  read-only mounts, and CPU/memory/time/output limits.
- Prove compile/time/OOM failures enter quarantine with one original plus two
  immediate repair attempts and cannot be mislabeled as economic rejection or
  raise their own resource limits.
- Measure representative throughput, latency, bytes retained per configuration,
  result-compression ratios, and trusted-work preemption on target-class
  hardware.

**Exit:** all required current strategies are expressible with signal/trade
parity; lookahead/prefix and sandbox escape suites pass; the signed module policy
has an explicit Max approval record before it is enabled; candidate failure
cannot mutate core or miss a trusted deadline; scale measurements are sufficient
to design storage honestly.

### Phase C — canonical persistence, identities, and migration

- Introduce the control database and migrations.
- Define immutable family/configuration/campaign/certification identities.
- Import or reference existing queues, hash history, leaderboard, active pointer,
  and artifacts without creating dual authorities.
- Add transactional jobs, leases, idempotent transitions, and notification
  outbox.
- Derive retention/partitioning from Phase B bytes-per-configuration results;
  identify which store is authoritative after recovery.
- Implement compact permanent verdict/dedup records, permanent Gold/historical-
  Gold artifacts, at-least-one-year near-Gold retention, and summarized
  hopeless-region archives.
- Implement pre-batch and end-of-batch recovery points, at-most-hourly background
  replication, replication-before-acknowledgement for authority/Gold/signal
  mutations, and a GitHub-hosted recovery layout using ordinary Git, immutable
  snapshots/releases, or LFS according to artifact size.
- Implement backup/restore, reconciliation, legacy rollback, backup-overdue
  alerts, and corruption/loss reports.

**Exit:** a dry-run migration preserves every authoritative identity; kill-at-
every-transition and machine-loss restores recover every acknowledged Gold/
authority state while rerunning only declared in-flight work; GitHub recovery is
proven from a clean machine; rollback to the legacy read path is tested; there is
exactly one operational source for each concern.

### Phase D — deterministic funnel

- Implement cost-ordered stages and durable state transitions.
- Run global engine/data/golden-comparator attestation before screening; run
  candidate-specific causality, determinism, and safety checks before/during
  candidate evaluation rather than deferring integrity to final validation.
- Record honest stage-specific counts and failure codes.
- Connect existing search/backtest/validation capabilities behind versioned
  adapters rather than copying them.
- Make Pending Gold entry, forward-bar attribution, fresh graduation, current
  Gold publication, revocation, and historical archive transitions atomic and
  fully reproducible.

**Exit:** every stage has deterministic replay, no missing/skipped mandatory
plank, fail-closed behavior, fault injection, durable provenance, and clean-
environment Pending Gold/Gold reproduction under the latest contract only.

### Phase E — authority, forward evidence, recovery, and minimum alerts

- Separate Pending Gold, current Gold, Recommended, Active, last-verified-
  instruction, and acknowledged-manual-fill identities.
- Implement the 20-bar Pending Gold cooling period, owner delay override,
  recommendation thresholds, five-bar persistence/hysteresis, manual override,
  and audited exact-switch approval.
- Implement current/stale/revoked/archive certification states and the latest-
  compatible-contract-only current board.
- Implement data-failure, restart, offline catch-up, recertification, and
  active-Gold-loss state machines, including automatic same-state pointer
  fallback, opposing-state `human_decision_required`, and no-Gold risk-off
  recommendation without brokerage action.
- Implement Active-per-bar replay, formal renewal triggers, weekly top-cohort and
  63-bar remainder renewal, two-renewal rolling-underperformance demotion, and
  immediate stale/revoke rules for integrity failures.
- Pause discovery during data recovery until control-store verification, data
  catch-up, Active recertification, current signal, and top-cohort refresh finish.
- Implement the minimum critical alert path, dead-man/health indication,
  kill/disable control, and notification outbox before unattended research is
  possible.

**Exit:** exhaustive state-transition tests prove that only the allowed Active
state can emit a trusted instruction; same-state fallback cannot create a trade;
opposing-state and no-Gold cases require Max; fault, stale-data, restart,
notification, Pending Gold, recertification, and owner-override drills reach the
specified safe state.

### Phase F — resident agent and feedback loop

- Add a provider-neutral agent adapter and scheduled trigger.
- Let Max configure provider/subscription/API credentials and cost policy outside
  candidate workers; the system does not autonomously choose providers or invent
  spending limits.
- Generate arbitrary candidate specs/modules only inside the untrusted “pool of
  chaos”; only schema- or module-policy-conforming artifacts cross intake.
- Add one original plus two immediate candidate-repair attempts and a deferred
  repair queue.
- Feed bounded structured result/failure summaries into subsequent cycles.
- Validate queue allocation and diversity/exploration behavior.

**Exit:** a provider mock plus Max's configured provider satisfy the same adapter
contract; replacement does not alter deterministic semantics; malicious/invalid
outputs cannot cross the sandbox or protected-core boundary; queue starvation,
runaway backlog, and provider failure are visible and safe.

### Phase G — read-mostly surfaces

- Build the daily digest and critical alerts.
- Expose Montauk Score, Validation Score (or calibrated Confidence only when
  justified), deployable Performance, current signal,
  active/override/recommendation status, gate lights, and plain-English weakness
  explanations.
- Add Slack chat in read-only mode first; add authenticated structured mutations
  only after their authority contract is tested.
- Slack mutations are limited to: request a named research campaign, trigger
  recertification, and approve one exact pending Active switch. They require
  Max's allowlisted identity, immutable ID, confirmation, expiry, idempotency,
  replay protection, and durable audit. Free-form text never changes authority.
- Do not permit Slack to acknowledge alerts or manual brokerage fills, enter or
  exit maintenance, or modify methodology/core. Put manual-fill acknowledgement
  in a dedicated authenticated app/operations action.
- Support multiple notification channels, but treat the durable local outbox and
  audit ledger—not Slack history—as authoritative.

**Exit:** every headline value traces to one authoritative record; stale,
override, Recommended/Active disagreement, and actionable failures are
unmistakable; privileged Slack commands pass identity, confirmation,
idempotency, replay, and audit tests; every forbidden command fails visibly.

### Phase H — measured performance work

- Profile representative family and parameter workloads.
- Optimize shared computation and data layout first.
- Port only demonstrated bottlenecks behind exact/tolerance-pinned parity tests.
- Set throughput and hardware targets from benchmarks, not aspirations.

**Exit:** optimized and reference paths satisfy frozen signal/trade/fill/metric
parity; discovery load cannot violate data/signal/recertification deadlines;
hardware targets and sustainable thermal/storage envelopes are measured.

### Phase I — commissioning and authority cutover

- Provision the target always-on host from a documented clean build.
- Run the new system in shadow without changing legacy Active authority.
- Rehearse database restore, data divergence, candidate escape, agent/provider
  outage, active-Gold loss, no-Gold, and notification failure.
- Compare shadow signals/artifacts to the frozen reference and investigate every
  divergence.
- Perform an explicit reversible legacy-authority cutover.
- Run an unattended soak long enough to exercise the acceptance matrix and
  produce an owner-review package. Its duration and results inform Max; neither a
  timer nor a passing suite declares the release complete.

**Exit:** every acceptance-matrix row has evidence and rollback instructions;
Max alone explicitly approves autonomous 3.0 operation. This approval does not
begin 4.x; only a separate later instruction from Max may do that.

## 10. End-to-end acceptance evidence

The implemented conveyor must demonstrate:

- deterministic replay from the same inputs and versions;
- exact rejection at every funnel stage with durable reasons;
- complete search accounting across adaptive agent cycles;
- no candidate ability to read secrets, use the network, mutate core, escape
  limits, or forge a verdict;
- signed-core verification and fail-closed behavior under tamper, stale manifest,
  wrong OS identity, lost signature, and attempted resident-agent escalation;
- atomic recovery from termination at each job transition;
- Gold reproduction from a clean environment;
- Pending Gold graduation, latest-contract board publication, and recommendation
  changes without active-strategy mutation;
- owner approval/override behavior with audit and replay protection;
- same-state, opposing-state, and empty-board fallback behavior without an
  unauthorized brokerage instruction;
- safe current-data failure and offline recovery;
- active recertification preemption under full research load;
- bounded storage growth, zero-silent-loss acknowledgement semantics, GitHub-
  hosted off-machine recovery, and clean-machine restore;
- provider replacement at the agent seam; and
- measured validator false-Gold/false-rejection behavior and ongoing forward
  calibration; and
- an unattended soak showing that failures become visible rather than silent.

Before coding handoff, convert this list into an acceptance matrix with a stable
test ID, invariant, fixture/workload, measurable threshold or SLA, expected
artifact, failure severity/safe state, rollback procedure, and owner-sign-off
field. Keep three decisions distinct:

1. objective operational acceptance evidence is complete;
2. Max declares Montauk 3.0 complete; and
3. Max separately authorizes work on 4.x.

## 11. Ratified policy versus calibration work

Questionnaire 3 resolves the operating-policy questions. A coding agent may not
reopen the Rust representation, origin-neutral complete gate, one current Gold
board, Pending Gold concept, human normal activation, emergency state machine,
signed-core boundary, Slack allowlist, durability semantics, provider authority,
or Max-only release authority.

Implementation beyond Phase A is blocked only on evidence-derived contract
values and mechanisms:

- executable manual-fill and matched-B&H semantics;
- fixed real/recent/rolling horizons, the provisional ~1.10 margin, minimum
  evidence, and rolling-demotion calibration;
- synthetic-model validation and any diagnostic weight/veto;
- hierarchy/dependence-aware lifetime multiplicity correction;
- Validation Score construction and measured false-positive/false-negative
  operating characteristics;
- exact signed-core/module-sandbox implementation and recovery topology; and
- benchmark-derived Rust execution/storage/hardware targets.

Each item produces a reviewable study, fixtures, a versioned contract proposal,
and a Max decision. “Whatever is easiest to code” is not an admissible answer.

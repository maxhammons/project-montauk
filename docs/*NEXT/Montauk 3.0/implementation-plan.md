# Montauk 3.0 Idea-to-Gold Pipeline

**Status: REQUIRED CODING HANDOFF PLAN / CHARTER-SUBORDINATE; CALIBRATION PHASE
READY (updated 2026-07-21).** This replaces the earlier rare-authoring/nightly-
drain plan. It implements the
Questionnaires 3–5 operating contract in
[charter.md](charter.md) and [decisions.md](decisions.md): continuous
model-agnostic ideation, untrusted candidate containment, deterministic
evaluation, automatic Gold-to-leaderboard publication, and human authority over
normal active-strategy changes.

The appliance shell around this conveyor is specified separately in
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md):
minimal Debian, `systemd`, resource preemption, private Tailscale/SSH, a bounded
provider adapter, one selected typed conversation channel, the Slack/Buzz
bake-off, and the intentionally limited interaction patterns Montauk borrows.

This is a safe handoff for **Phase 1 contract research and protected-boundary
prototyping**, not blanket permission to build the autonomous appliance around
guesses. Phase 1 must turn the ratified policies into empirically calibrated,
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

Its governing test is simpler than the implementation: Gold must provide the
strongest honest assurance Montauk can earn from current research, expert
scrutiny, independent reasoning, reproducible evidence, and calibrated controls
that an exact strategy is not detectably overfit and should outperform matched
TECL B&H when actually followed. A stage or method that does not help earn or
protect that promise does not belong in the conveyor.

## 2. Three trust zones and one-way authority

Montauk 3.0 has three trust zones:

1. **Untrusted research.** The scheduled model, generated specs/modules, and
   disposable candidate sandbox. It proposes work, attempts bounded repairs, and
   receives structured feedback.
2. **Sealed Montauk core.** Verified data, execution/backtest semantics, the
   five-plank Gold exam, scoring/ranking, leaderboard, recertification, and
   trusted signal generation.
3. **Max authority.** Recommended/Active state, exact approvals, maintenance
   releases, alerts, and manual brokerage action.

Information may flow from deterministic results back to ideation. Write authority
never flows from ideation or candidate code into the protected or active-authority
zones.

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
| Gold row | One exact configuration that passed the complete historical Gold contract and joined the leaderboard |
| Pending Gold | The activation status of a Gold row still inside its cooling/forward-evidence period |

Owner-facing copy may call a configuration a “strategy.” Operational metrics must
name the stage:

- families proposed and accepted;
- configurations expanded;
- configurations cheap-screened;
- configurations fully backtested;
- candidates fully validated;
- Pending Gold rows and forward bars accrued; and
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
Model or Max -> typed family definition -> protected Rust library
                                             |
                                             v
                              exact configurations as data
                                             |
                                             v
                                      research bucket
                                             |
                                             v
                                   VALIDATION PIPELINE
                              matched-B&H backtest
                            (economic passage plank)
                                             |
                                             v
                         remaining correctness/anti-overfit
                              validation (four planks)
                                             |
                                          if pass
                                             v
                                      Gold leaderboard
                                             |
                                             v
                                           ranking
                                             |
                                             v
                                  Max normally chooses Active
```

Schema checks, sandboxing, deduplication, artifact verification, forward
monitoring, and feedback protect this flow. They are not separate product
pipelines and must not create parallel verdicts.

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

During a current-data failure, spare capacity may continue deterministic
low-priority work only against the content-addressed last-good snapshot. Every
result is labeled `stale_data_research` and is barred from current Gold, board
mutation, and trusted signals until it is replayed on repaired verified data.

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
- partition very large spaces into deterministic resumable shards and stream
  bounded batches to evaluation instead of pre-materializing billions of jobs;
- use version-aware exact deduplication;
- reuse safe precomputed indicators where semantics permit;
- compile/optimize one internal execution plan per family version rather than per
  exact configuration;
- record every configuration actually evaluated, even when its work item was
  generated just in time;
- run the cheapest correctness and economic screens first; and
- promote only survivors to full backtesting.

Related variants are legitimate configurations. Family-level “near twin”
similarity may help presentation or compute allocation, but must not silently
erase exact configurations the owner wants tested.

### Stage 4 — full backtest and economic eligibility

Every survivor runs the required real-data backtests under one frozen executable
contract:

- signal only after the official daily bar verifies, with certification at the
  next regular-session open plus calibrated slippage and fees; Max submits the
  manual order after close for that opening execution;
- matched B&H start, first purchase, costs, distributions, and unrounded values;
- fees, spreads/slippage, zero initial risk-off cash return, and missing-bar
  behavior;
- tax-advantaged-account/pre-tax treatment; tax modeling and an active SGOV leg
  are excluded;
- warm-up and boundary rules;
- exact terminal deployable TECL wealth/share multiple versus matched B&H as the
  primary target, with daily net log-wealth differences retained for inference;
- complete observed TECL history and trailing five years as hard gates;
- a small predeclared rolling-window design with a calibrated aggregate passage
  rule plus calibrated catastrophic-window veto; and
- a provisional 1.10 point-estimate hypothesis plus an uncertainty-aware lower
  bound above no edge (1.0), with insufficient evidence as an explicit result.

Configurations that fail required B&H/performance gates stop here. The exact
slippage/fees, rolling aggregate/veto rule, uncertainty floor, and final margin
are bounded Phase 1 calibration studies; the implementation agent may not choose
convenient values. The fixed backtesting assumption is a $10,000–$100,000
notional order band; costs come from market evidence and use conservative values
where the range materially changes them. The system does not infer or track
actual account or order size. Same-close and alternative OHLC results are
diagnostics/stresses only. CAGR, drawdown, Sharpe, and trade statistics explain
performance; they cannot replace the primary Gold target.

Synthetic history runs as a diagnostic/confidence input, not as real passage. Its
present construction uses 3x daily S&P technology-sector-index returns
(1993–1998), 3x daily XLK returns (1998–2008), expenses, daily compounding, a
real-TECL seam, and a loader-time 189.7 bps/year financing/tracking haircut. The
builder is reproducible, but prior audits found material volatility/tracking
differences from actual TECL. Phase 1 must independently recalibrate any weight or
catastrophic veto on overlap and model-error controls before either can affect
Gold.

The synthetic study must extend the XLK-based transformation through observed
TECL. It calibrates only on earlier overlap blocks and evaluates later blocks
without refitting, comparing daily-return bias, tracking error, volatility,
terminal path, drawdowns, financing/expense error, and named-event behavior.

A predeclared named-moment suite includes 2001/dot-com, 2008, 2020, 2022,
tariff announcements, and later events added only through a methodology version.
Every result is source-labelled. Pre-TECL episodes are reconstructed/synthetic
diagnostics; observed TECL episodes use verified real data. The suite cannot be
expanded or reweighted candidate by candidate.

### Stage 5 — candidate-local validation and cohort eligibility

Every remaining candidate, regardless of human or AI origin, must satisfy the
same mandatory versioned evidence planks and rigor. The backtest stage has
already resolved economic passage; this stage resolves candidate-local
correctness, generalization, reproducibility/currentness, and any family/campaign
search evidence that does not depend on the full daily cohort. Stage 6 completes
the cohort-dependent part of search honesty and assembles the final five-plank
verdict. No economic or candidate-local test is rerun under another label.
Structurally inapplicable algorithms require a predeclared equivalent or valid
`not_applicable` outcome; they do not disappear through silent score
renormalization. Named methods such as PBO, SPA, bootstrap, walk-forward, and
sensitivity analysis are used only after Phase 1 proves their assumptions,
power, control behavior, and incremental role. They are tools beneath a
plank—not extra funnel stages or independently weighted excuses to pass.

No mandatory result may be missing, skipped, underpowered, or unverifiable and
still receive Gold. Montauk Score ranks configurations only after all hard planks
pass. Until forward calibration supports a probability interpretation, the
headline is **Validation Score**, not “confidence percent.”

The validator is itself under test. Phase 1 must measure both false-Gold and
false-rejection behavior using null/randomized controls, seeded leakage and
overfit defects, simple frozen structural controls, simulation, and later
per-row forward outcomes. More gates or a lower pass rate do not by themselves
prove rigor.

Nested rolling-origin reconstruction is the required chronological spine; Phase
1 chooses between expanding and fixed rolling training designs. CPCV is
evaluated alongside it and should become a hard applicable gate when its target,
assumptions, power, and incremental defect detection are proven. Otherwise use a
predeclared valid equivalent or `not_applicable`, not a ceremonial pass. Purge
and embargo derive from actual information/label/holding-outcome intervals, use
zero where no overlap path exists, and cannot be guessed.

A revealed historical holdout is permanently labelled spent/reused and enters
lifetime adaptive-search accounting; only post-freeze bars in an exact row's
live-forward ledger are untouched for that row. Parameter robustness records
both numeric and behavioral distance by hashing signal, position, and trade
paths. No fixed trade-count cliff substitutes for effective observations,
uncertainty, regimes, and method power.

The pipeline does not “give everything its due diligence” by wasting full
validation compute on candidates that already failed. It does so by applying the
correct decisive test at every stage and recording why work stopped.

### Stage 6 — Gold publication, Pending activation, and recommendation

A historical-suite survivor becomes eligible for the next daily frozen Gold
epoch; this is not a human Trade Roster or a second certification tier.
Discovery/backtesting continue between epochs. Once per day, publication is
transactional:

1. freeze the complete eligible survivor cohort and lifetime search-ledger
   snapshot;
2. run the cohort-dependent shared multiplicity/search-honesty correction
   against that coherent universe;
3. combine each survivor's immutable candidate-local artifacts with the shared
   artifact and emit one final five-plank verdict, without rerunning prior gates;
4. freeze every passing definition, exact parameters, artifact, fingerprint, and
   shared family/campaign/epoch search-honesty certificate;
5. atomically create each Gold certificate with
   `activation_status=pending`, publish it, and rerank the board;
6. carry all disclosures into later epochs rather than resetting search history;
7. accrue 20 verified trading bars under each exact frozen identity;
8. run a fresh complete certification;
9. if it still passes, mark it activation-eligible and evaluate Recommended; and
10. emit the appropriate digest/event.

Pending Gold cannot be Recommended or Active. Max may explicitly override the
waiting delay, but the exception is conspicuous and audited. Only the latest compatible
validation contract appears on the current Gold board; incompatible older rows
become stale and must recertify rather than remain grandfathered.

Each compact row exposes Montauk Score, Validation Score (or calibrated
Confidence only after it earns that name), a simple terminal deployable
wealth/share expression such as “1.14× B&H,” and forward-evidence status. Exact
rank remains deterministic, with `leader not clearly separated` when calibrated
uncertainty cannot distinguish the leading group.

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

The controller supplies the global concurrency cap and per-lane FIFO queues.
`systemd` owns durable timers and process supervision. Provider session loops,
Conversation threads, Buzz, and OpenClaw are never schedulers or queue authorities. Research
workers run at lower CPU/I/O priority and shed load before trusted deadlines,
memory pressure, sustained swapping, thermal throttling, or storage pressure can
harm P0–P3 work.

## 7. Persistence model

The target scale requires more than Markdown and JSON queues. The operational
design should begin with one logical authority and as few physical stores as
measured scale permits. It should include:

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

No second database, file tree, or snapshot may become a parallel source of
authority. Partitioning and content-addressed blobs are storage optimizations
behind the control database; split them physically only when a measured size,
access-control, or recovery requirement demands it.

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
use partitioned immutable snapshots, releases, or LFS where appropriate. Split
repositories only when a measured size, access-control, or recovery requirement
demands it. The transactional database/outbox is the operating authority;
GitHub is its tested off-machine recovery path.

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

The minimum enforcement is one resident-agent OS identity with no core-write
credential, one read-only content-addressed core release, generated work outside
that release, and one manifest signed by a human-held key unavailable to the
agent. Startup and every Gold/signal job fail closed if the signature, hash set,
or permissions do not verify. Repository/branch topology may support this but is
not another trust layer. A password alone, clean Git history, or rollback after
mutation is not a seal.

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

The build has five phases:

| Phase | Outcome |
|---|---|
| 1. Prove the exam | Max approves the executable Gold, execution, and authority contracts |
| 2. Build the sealed evaluator | Rust families/configurations run causally and durable state restores cleanly |
| 3. Build the conveyor | Backtest → remaining Gold validation → leaderboard → ranking → Active authority works deterministically |
| 4. Add autonomy | The model restocks the bucket and one selected private channel reports/accepts only narrow commands |
| 5. Optimize and cut over | Measured speed work, shadow operation, recovery drills, and Max's final approval |

### Phase 1 — prove the exam and authority contract

- Implement the fixed signal-after-verified-close, next-regular-session-open
  workflow; calibrate slippage/fees and conservative OHLC diagnostics; freeze
  exactly matched B&H semantics; use the fixed $10,000–$100,000 modeled order
  band; and do not require personal fill, balance, or actual-order-size capture
  or reconciliation.
- Freeze terminal deployable TECL wealth/share multiple versus matched B&H as the
  primary estimand and daily net log-wealth difference as the inference series.
  Keep complete observed TECL history and trailing five years as hard gates;
  calibrate the small rolling aggregate/catastrophic-veto design, provisional
  1.10 point-estimate margin, lower bound above 1.0, evidence sufficiency, and
  persistent warning/demotion behavior. Do not install a universal trade-count
  cliff or invent retrospective “reasonable slices.”
- Independently audit the synthetic TECL model against its real overlap and
  model-error controls. Freeze its construction/version and decide from evidence
  whether it has a diagnostic weight or catastrophic veto; it never substitutes
  for real passage. Extend the XLK transformation through actual TECL; calibrate
  only on earlier overlap blocks and test later blocks without refitting against
  return bias, tracking error, volatility, terminal path, drawdown, financing/
  expense, and named-event measures. Freeze a source-labelled named-moment suite
  in which pre-inception 2001/2008 evidence is reconstructed and observed-TECL
  events such as 2020/2022/tariff announcements remain distinguishable.
- Select the smallest complete method set, then independently audit every final
  retained or rewritten implementation against its frozen specification and
  primary literature. Add a validation-of-validation harness measuring
  false-Gold **and** false-rejection behavior with randomized nulls, seeded
  lookahead/overfit defects, simple frozen controls, simulations, and an ongoing
  per-row forward calibration dataset. Finishing an audit of discarded legacy
  files is not required.
- Define Validation Score as an evidence-strength index; do not display it as a
  probability until a frozen outcome target and forward reliability study
  support that interpretation.
- Require nested rolling-origin reconstruction and compare expanding with fixed
  rolling training windows. Evaluate CPCV alongside it; retain CPCV as a hard
  applicable gate only after proving a defined target, interval-derived
  purge/embargo, adequate power, and incremental control value. Freeze explicit
  evidence labels and mark every revealed historical holdout spent/reused.
- Report an appliance-level frontier between annual probability of any false
  Gold and recovery of planted meaningful signals, with 1% annual false Gold as
  an aspirational reference for Max's later choice.
- Freeze the simplest Montauk Score formula from Validation Score and deployable
  Performance, with validation strength taking priority. Admit no third pillar
  unless controls prove distinct incremental value; prevent double-counting of
  a Gold method.
- Specify multiplicity as a formal statistical design: tested universe,
  within-family versus board/lifetime scope, online versus batch behavior,
  dependency clustering, alpha/sequential policy, and whether a new search can
  change an existing certificate. Calibrate it with simulation and independent
  review. Do not equate a raw count of correlated variants with independent
  hypotheses or erase legitimate exact rows. Define daily frozen certification
  epochs, shared immutable cohort artifacts, lifetime disclosure carry-forward,
  and signal/position/trade-path hashes.
- Write transition tables and invariants for jobs/candidates, certifications,
  Gold activation status (Pending/eligible), Recommended/Active/override, the five-bar switch
  persistence rule, stale data, same/opposing-state fallback, no Gold,
  `human_decision_required`, and the exact states permitted to emit a trusted
  instruction.
- Design the minimum cryptographic protected-core seal: resident-agent OS
  identity without core-write access, read-only content-addressed release,
  generated work outside it, Max-held signing key, and fail-closed startup/Gold/
  signal checks. Choose repository topology only if the threat/recovery tests
  require it. Candidate code receives no core or provider credentials.
- Freeze recertification triggers: Active replay each verified bar and formal
  renewal every 20 new bars/event/warning/pre-activation; top cohort weekly; rest
  after 63 new bars; incompatible contract change stales rows immediately.
- Calibrate when exact rank must carry `leader not clearly separated`; expose
  that status without adding a headline score.
- Reconcile the resulting truth into canonical repository docs and tests,
  including `CLAUDE.md`, `docs/charter.md`,
  `docs/validation-thresholds.md`, and
  `docs/validation-philosophy.md`; publish one version/hash manifest so these
  3.0 planning files do not become a parallel authority.
- Turn every contract into versioned schemas, fixtures, decision tables, and
  acceptance tests.
- Give every safety- or evidence-critical step its own positive fixture,
  negative/seeded-defect fixture, deterministic expected result, and retained
  acceptance artifact. A passing end-to-end run cannot substitute for proof of
  an internal step.
- Return each decision to Max in simple language with a simple example,
  recommendation, measured false-Gold/false-reject tradeoff, and known limits;
  put formulas, sources, and implementation detail in an appendix.

**Exit:** Max ratifies the calibrated contract package; the validation audit,
false-positive/false-negative study, synthetic/execution studies, multiplicity
design, core-seal threat model, and state tables have review evidence; no
canonical doc/test says “top row is automatically active,” labels an
uncalibrated score as probability, permits a skipped Gold plank, or preserves an
incompatible validation route.

### Phase 2 — build the sealed evaluator and durable state

#### Workstream 2A — representation, causality, containment, and scale

- Prototype the prebuilt Rust evaluator and primitive library with typed
  strategy definitions on representative current and novel families.
- Build a primitive coverage matrix and reproduce the legacy Active strategy
  needed for shadow/cutover safety, matched B&H/execution references, every
  final validation control/benchmark, and any legacy strategy Max explicitly
  selects as a migration candidate. Do not rebuild the historical board as a
  compatibility exercise.
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

**Checkpoint:** all required current strategies are expressible with signal/trade
parity; lookahead/prefix and sandbox escape suites pass; the signed module policy
has an explicit Max approval record before it is enabled; candidate failure
cannot mutate core or miss a trusted deadline; scale measurements are sufficient
to design storage honestly.

#### Workstream 2B — canonical persistence, identities, and migration

- Introduce the control database and migrations.
- Define immutable family/configuration/campaign/certification identities.
- Import or reference existing queues, hash history, leaderboard, active pointer,
  and artifacts without creating dual authorities.
- Add transactional jobs, leases, idempotent transitions, and notification
  outbox.
- Derive retention/partitioning from Workstream 2A bytes-per-configuration
  results;
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

**Checkpoint:** a dry-run migration preserves every authoritative identity; kill-at-
every-transition and machine-loss restores recover every acknowledged Gold/
authority state while rerunning only declared in-flight work; GitHub recovery is
proven from a clean machine; rollback to the legacy read path is tested; there is
exactly one operational source for each concern.

### Phase 3 — build the deterministic conveyor and authority states

#### Workstream 3A — deterministic funnel

- Implement cost-ordered stages and durable state transitions.
- Run global engine/data/golden-comparator attestation before screening; run
  candidate-specific causality, determinism, and safety checks before/during
  candidate evaluation rather than deferring integrity to final validation.
- Record honest stage-specific counts and failure codes.
- Reuse an existing search/backtest/validation capability only when Phase 1
  accepts its semantics and audit evidence; otherwise rewrite it. Do not preserve
  legacy gates, weights, tiers, scores, or file boundaries merely for continuity.
- Implement daily frozen certification cohorts with complete search-ledger
  snapshots, shared multiplicity artifacts, lifetime disclosure carry-forward,
  and transactional multi-row publication.
- Make Gold publication with Pending activation, row-specific forward-bar
  attribution, fresh activation eligibility, revocation, and historical archive
  transitions atomic and fully reproducible.

**Checkpoint:** every stage has deterministic replay, no missing/skipped mandatory
plank, fail-closed behavior, fault injection, durable provenance, and clean-
environment Gold/activation-status reproduction under the latest contract only.

#### Workstream 3B — authority, forward evidence, recovery, and minimum alerts

- Separate Gold certification, activation status, Recommended, Active, last-
  verified instruction, and modeled execution identities. Do not create a
  brokerage-position or personal-fill authority record in 3.0.
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
- Give recovery absolute priority. Permit only explicitly labeled low-priority
  research against the immutable last-good snapshot when it cannot delay
  control-store verification, data catch-up, Active recertification, the current
  signal, and top-cohort refresh; replay any survivor on repaired verified data
  before it may affect current Gold.
- Implement the minimum critical alert path, dead-man/health indication,
  kill/disable control, and notification outbox before unattended research is
  possible.

**Checkpoint:** exhaustive state-transition tests prove that only the allowed Active
state can emit a trusted instruction; same-state fallback cannot create a trade;
opposing-state and no-Gold cases require Max; fault, stale-data, restart,
notification, Pending Gold, recertification, and owner-override drills reach the
specified safe state.

### Phase 4 — add the resident agent and quiet control surfaces

#### Workstream 4A — resident agent and feedback loop

- Add a provider-neutral agent adapter and a no-overlap `systemd` timer/one-shot
  trigger. Each call has bounded turns/tokens, wall time, candidate-only working
  paths, structured input/output, and a durable run ID; a provider's interactive
  loop is not durable scheduling.
- Accept externally supplied provider/subscription/API credentials and limits
  outside candidate workers. Provider procurement, budget, and comparative
  selection are deployment concerns; the system does not choose providers or
  invent spending limits.
- Generate arbitrary candidate specs/modules only inside the untrusted “pool of
  chaos”; only schema- or module-policy-conforming artifacts cross intake.
- Add one original plus two immediate candidate-repair attempts and a deferred
  repair queue.
- Feed bounded structured result/failure summaries into subsequent cycles.
- Validate queue allocation and diversity/exploration behavior.
- Run the adapter under the no-core-write `montauk-agent` identity and prove that
  provider credentials never reach candidate workers. Treat optional provider
  Remote Control as a deliberately launched maintenance surface, not an
  autonomous service.

**Checkpoint:** a provider mock plus Max's configured provider satisfy the same adapter
contract; replacement does not alter deterministic semantics; malicious/invalid
outputs cannot cross the sandbox or protected-core boundary; queue starvation,
runaway backlog, and provider failure are visible and safe.

#### Workstream 4B — read-mostly surfaces

- Build the daily digest and critical alerts.
- Expose Montauk Score, Validation Score (or calibrated Confidence only when
  justified), terminal deployable wealth/share multiple as a simple
  strategy-versus-B&H expression, forward-evidence status/age, exact rank plus
  `leader not clearly separated` when warranted, current signal,
  active/override/recommendation status, gate lights, and plain-English weakness
  explanations.
- Define and test one provider-neutral channel adapter against a fake controller
  and notification outbox. It owns transport only; the controller owns command
  schemas, task state, authority, and audit.
- Before building a full provider integration, run the time-boxed Slack/Buzz
  bake-off from the operations policy. Compare phone/push reliability, thread
  continuity, identity and mutation safety, restart reconciliation, Debian
  resource cost, install/TLS/backup/update burden, and provider-neutral agent
  continuity. Max chooses from the evidence. Build and deploy only the winner;
  do not preserve a second live command path.
- Slack Socket Mode is the conservative default if Buzz does not pass in time or
  does not clearly earn its heavier self-hosted stack. If Buzz wins, its signed
  relay events and agent rooms remain transport receipts—not Montauk audit or
  authority—and its shell/file agent has no protected credentials or writes.
- Channel mutations are limited to: request a named research campaign, trigger
  recertification, and approve one exact pending Active switch. They require
  Max's stable allowlisted identity, immutable ID, confirmation, expiry,
  idempotency, replay protection, and durable audit. Free-form text never changes
  authority.
- Do not permit the channel to acknowledge alerts, enter or exit maintenance,
  modify methodology/core, or run arbitrary host commands.
- Support multiple rooms within the selected provider when useful, but treat the
  durable local outbox and audit ledger—not conversation history—as authoritative.
- Route by stable Max/room IDs, serialize each thread/session, enforce a global
  agent concurrency cap, acknowledge inbound delivery promptly, and show
  accepted/queued/running/completed/failed status in the same thread.
- Route free-form chat to a bounded advisory agent task with read-only status,
  redacted logs, failure-ledger context, and candidate-workspace access. It may
  explain, diagnose within that boundary, or author research; it cannot silently
  escalate into protected maintenance or unrestricted host control.
- Provide private Tailscale/SSH administration as the independent recovery path.
  Direct Claude-in-Slack, Buzz's relay/agent runtime, and OpenClaw are not Montauk
  authority paths. Borrow useful typed-gateway, task-state, queuing, identity,
  idempotency, and health patterns without importing broad host tools, plugins,
  multiple gateways/agents, or conversationally inferred mutations.

**Checkpoint:** every headline value traces to one authoritative record; stale,
override, Recommended/Active disagreement, and actionable failures are
unmistakable; privileged channel commands pass identity, confirmation,
idempotency, replay, restart-reconciliation, and audit tests; every forbidden
command fails visibly.

### Phase 5 — optimize, commission, and cut over

#### Workstream 5A — measured performance work

- Profile representative family and parameter workloads.
- Optimize shared computation and data layout first.
- Port only demonstrated bottlenecks behind exact/tolerance-pinned parity tests.
- Record profiling evidence for future optimization; do not create a hardware-
  procurement or strategies-per-hour acceptance gate.
- On the actual Debian tower, use release builds and benchmark physical versus
  logical worker counts, bounded batch sizes, shared-indicator caching, RAM/
  memory pressure, SSD I/O, and sustained thermal behavior. Keep a trusted-work
  reserve/preemption path; do not normalize sustained swap or tune kernels,
  governors, and filesystems without measured evidence.

**Checkpoint:** optimized and reference paths satisfy frozen signal/trade/fill/metric
parity; discovery load cannot violate data/signal/recertification deadlines;
the available host remains stable under sustained load. No numerical discovery-
throughput target gates completion.

#### Workstream 5B — commissioning and authority cutover

- Provision current Debian Stable minimally on the target always-on host from a
  documented clean build. Put live state on SSD, configure no-sleep/power-loss
  recovery, controlled updates/reboots, wired networking and UPS behavior where
  available, separated service identities, `systemd` supervision, Tailscale/SSH,
  the selected channel adapter, health/doctor checks, and off-machine backup.
- Run the new system in shadow without changing legacy Active authority.
- Rehearse database restore, data divergence, candidate escape, agent/provider
  outage, channel/Tailscale outage, service kill/restart, resource exhaustion,
  thermal throttling, disk pressure/failure, active-Gold loss, no-Gold, and
  notification failure.
- Compare shadow signals/artifacts to the frozen reference and investigate every
  divergence.
- Perform an explicit reversible legacy-authority cutover.
- Run an unattended soak long enough to exercise the acceptance matrix and
  produce an owner-review package. Its duration and results inform Max; neither a
  timer nor a passing suite declares the release complete.

**Phase 5 exit:** every acceptance-matrix row has evidence and rollback instructions;
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
- Pending-to-eligible activation transition, latest-contract board publication,
  and recommendation changes without active-strategy mutation;
- owner approval/override behavior with audit and replay protection;
- same-state, opposing-state, and empty-board fallback behavior without an
  unauthorized brokerage instruction;
- safe current-data failure and offline recovery;
- active recertification preemption under full research load;
- bounded storage growth, zero-silent-loss acknowledgement semantics, GitHub-
  hosted off-machine recovery, and clean-machine restore;
- provider replacement at the agent seam;
- boot/power-loss recovery, `systemd` restart/no-overlap behavior, private
  Tailscale/SSH recovery, selected-channel identity/confirmation/replay defenses,
  and reconciliation of conversation state with the durable ledger;
- proof that neither the selected channel adapter nor any optional Buzz,
  OpenClaw, or provider remote session can execute a core mutation outside the
  controller contract;
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

Questionnaires 3–5 resolve the owner-visible operating policy. Max's
plain-language Gold guiding light controls any technical ambiguity. A coding
agent may not reopen the Rust representation, origin-neutral complete gate,
next-open execution timing, primary terminal relative-wealth target, complete/
trailing-five-year hard periods, required rolling-origin spine, daily
certification epochs, one current Gold board, Pending Gold concept, human normal
activation, emergency state machine, signed-core boundary, channel allowlist,
durability semantics, provider authority, or Max-only release authority.

Implementation beyond Phase 1 is blocked only on evidence-derived contract
values and mechanisms:

- calibrated slippage/fees and matched-B&H fixtures inside the fixed next-open
  and $10,000–$100,000 modeled-order contract;
- rolling aggregate/catastrophic rules, the provisional 1.10 point margin,
  uncertainty/evidence sufficiency, and rolling-demotion calibration;
- expanding versus fixed rolling training windows, CPCV's scientifically
  applicable role, and interval-derived purge/embargo rules;
- the source-labelled named-moment suite;
- synthetic-model validation and any diagnostic weight/veto;
- hierarchy/dependence-aware lifetime multiplicity correction and shared daily-
  epoch artifact;
- the achievable any-false-Gold/planted-signal-recovery frontier around the
  aspirational 1% annual reference;
- Validation Score construction and measured false-positive/false-negative
  operating characteristics;
- the `leader not clearly separated` rule;
- exact signed-core/module-sandbox implementation and recovery topology.

Each item produces a reviewable study, fixtures, a versioned contract proposal,
and a Max decision. “Whatever is easiest to code” is not an admissible answer.
Tax modeling, personal fill logging/reconciliation, mandatory outside-human
review, an active SGOV leg, hardware/provider procurement, and a numerical
throughput target are explicitly outside this list and outside 3.0.

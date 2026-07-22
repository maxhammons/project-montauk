# Montauk 3.0 Follow-up Research Prompts

These prompts target unresolved or incorrectly resolved issues found during the
independent review of the Montauk 3.0 research package. Run each prompt as a
separate research assignment so one agent's conclusions do not silently become the
premises of another.

## Instructions to prepend to every research assignment

> Act as an independent, skeptical researcher. Read the governing Montauk 3.0
> charter, decisions, validation hardening plan, completed questionnaires, relevant
> code, data manifests, and existing research report before forming a conclusion.
> Use primary sources wherever possible and link directly to them. Distinguish
> theorem, measured Montauk evidence, external empirical evidence, and inference.
> Map every external method's assumptions to Montauk explicitly; do not import a
> conventional threshold from another population. State what would falsify your
> recommendation. Produce one recommended minimal design, its strongest
> alternative, known limits, required fixtures, stopping rules, retained artifacts,
> and unresolved owner decisions. Do not edit project files or present simulation
> as proof of a theorem. End with an adversarial self-review identifying how your
> own recommendation could fail.

## R1 — Continual search and the correct false-Gold error target

> Design a continual-search policy for Montauk whose target is the probability of
> at least one false Gold, rather than FDR or mFDR. Compare online FWER,
> alpha-spending, closed daily-cohort FWER, e-value/e-process approaches, and any
> valid hybrid for an a-priori unbounded sequence of searches over repeatedly reused,
> serially dependent TECL history. Explain whether and when Tian–Ramdas online FWER,
> dependent online FWER, Romano–Wolf, SPA, Reality Check, or other primary methods
> apply. Prove or reject composition of the daily cohort test with the lifetime
> procedure. Analyze dependence across days, family renaming, optimizer changes,
> external-feature fishing, holdout reuse, behavioral near-twins, and signed core
> releases. A core release must not be assumed to erase past searching. Produce
> annual, five-year, ten-year, and lifetime interpretations plus planted-signal
> recovery, but label simulation as generator-specific operating evidence. Explain
> exactly when a newly discovered search-accounting defect should stale prior Gold.

## R2 — Null worlds with genuinely known absence of edge

> Design at least four materially different TECL-like null-world generators whose
> absence of exploitable long/cash timing edge is known by construction. Do not call
> a stationary/bootstrap resample of real TECL a zero-edge world unless you prove
> that it destroys the relevant predictability. For each generator, specify the
> joint process for TECL OHLC, volume, VIX, macro features, calendar, distributions,
> and product seams; which marginal, volatility-clustering, cross-series, and regime
> properties it preserves; and which forms of predictability it deliberately
> destroys. Red-team each world with trend, volatility timing, mean reversion,
> calendar/event memorization, rare-event rules, and high-dimensional feature
> searches. Include planted signals of known size and multiple mechanism shapes.
> Recommend a diverse control battery and show how false-Gold estimates change
> across null models rather than relying on one convenient generator.

## R3 — TECL/TYH data, corporate actions, and total-return accounting

> Perform a forensic, primary-source reconstruction of TECL/TYH from inception to
> the current date. Verify ticker/CUSIP and benchmark changes, every split, every
> ordinary-income and capital-gain distribution, ex/record/pay dates, expense
> disclosures, and material prospectus/index changes. Audit every row and omission
> in `data/TECL_distributions.csv`, every relevant manifest claim, and the current
> runtime's distribution treatment. Define three non-overlapping views: raw
> tradable OHLC, causally split-adjusted feature data, and total-return wealth
> accounting. Specify entitlement, cash availability, reinvestment price, costs,
> and behavior when a strategy enters/exits around ex- and pay-dates. Prove that
> strategies and matched B&H use the same eligible start, first obtainable fill,
> initial capital, transaction costs, and distribution convention. Provide tests
> that detect missing distributions, early cash availability, future-action leakage,
> and double-counting between adjusted prices and cash credits.

## R4 — Low-sample economic inference and hard-horizon sufficiency

> Evaluate uncertainty methods for the exact terminal deployable wealth multiple
> versus matched TECL B&H when strategies are selected adaptively, path-dependent,
> and may have fewer than twenty trades across only three or four plausible regimes.
> Test stationary-bootstrap full-path resimulation, alternative block bootstraps,
> regime-aware generative methods, subsampling, HAC diagnostics, and any defensible
> alternative on known data-generating processes with stationarity and regime
> breaks. Preserve joint TECL/VIX/macro/OHLC validity and rerun causal strategy logic
> for every draw. Measure interval coverage after selection, not only before it.
> Determine whether `bars / block_length`, regime count, trade count, or a MinTRL
> cross-walk can validly act as an evidence floor for terminal relative wealth;
> reject invented effective-sample-size formulas. Compare complete-history and
> trailing-five-year hard gates, and return the false-Gold/false-rejection effect of
> treating an insufficient required horizon as non-passing.

## R5 — Synthetic TECL reconstruction and holdout exhaustion

> Reassess the pre-inception TECL reconstruction using verified product history.
> Separate the 2008-2012 TYH/Russell 1000 Technology era from the post-2012 TECL/
> Technology Select Sector era, and determine whether the 2018 GICS reconstitution
> is a product-contract seam, a composition/regime event, or both. Audit the current
> 3x underlying-return, expense, financing, distribution, and stitching formulas.
> Determine whether XLK is an adequate proxy in each period and whether using XLK
> blends its own expenses, tracking, and distributions into the inferred TECL drag.
> Design a calibrate-earlier/test-later study that explicitly accounts for having
> only one credible held-out block. State what happens after that block has been
> inspected and a model is revised—do not reuse it as untouched evidence. Evaluate
> rate-conditioned financing only if it improves genuinely held-out behavior and
> stress extrapolation into rate regimes outside the calibration range. Preserve
> synthetic evidence as diagnostic-only.

## R6 — Obtainable opening-auction execution

> For Max's actual broker, account type, and interface, determine whether an order
> submitted after the verified close can participate in the NYSE Arca Core Open
> Auction for TECL. Use current exchange rules and broker/account documentation or a
> bounded direct account test. Document exact order type, time-in-force, submission
> cutoff, routing, cancellation, rejection, partial-fill, delayed-open, LULD/halt,
> and unfilled-remainder behavior. Distinguish auction price from first continuous
> print. Design a finite execution state machine and conservative backtest outcome
> for every unresolved state. Determine what daily source can honestly verify the
> official close, what periodic primary audit is sufficient, and what remains
> insufficient without SIP/auction/quote data. For the $10,000-$100,000 band,
> specify the evidence needed for a point cost estimate versus a conservative range
> and identify any paid dataset only with exact cost, coverage, and decision value.

## R7 — Exact independent reproduction and numerical determinism

> Design the complete independent-reproduction contract for every Gold certificate,
> including independent data parsing, calendars, corporate actions, feature
> calculation, signals, positions, fills, distributions, daily wealth, B&H,
> validation statistics, and final verdict. Compare freezing exact bootstrap/
> Monte-Carlo index arrays as certificate artifacts with specifying a versioned
> cross-language RNG and golden test vectors. Exact certificate reproduction must
> not be replaced by overlapping confidence intervals or qualitative ranking
> agreement; distributional tests should validate the sampler separately. Define
> exact fields, tolerance fields, forbidden categorical boundary tolerance, stable
> operation order, and non-finite behavior. Calibrate tolerances across Rust/Python,
> platforms, compilers, CPU features, transcendental libraries, adversarial numeric
> ranges, and threshold-near cases—not merely two modes of the same Rust build.
> Specify the organizational/source-visibility boundary that makes the reference
> implementation meaningfully independent and the hand-derived fixtures that catch
> shared specification errors.

## R8 — Declarative and custom-Rust containment

> Threat-model both the normal declarative StrategySpec path and the disabled custom
> Rust-module escape hatch. For StrategySpec, cover parser recursion, oversized
> documents, constraint/combination explosions, integer overflow, algorithmic
> complexity, malformed numeric inputs, and resource starvation. For custom Rust,
> cover the compile phase separately from runtime: compiler resource exhaustion,
> file reads/writes, environment/secrets, network, build scripts, proc macros,
> dependencies, `unsafe`, FFI, subprocesses, linker behavior, and generated output.
> Compare direct `rustc` plus a frozen SDK, a vetted crate allowlist, seccomp/
> namespaces/cgroups, gVisor/Wasm, and microVM containment. Do not describe an
> adversarial test suite as proof of containment. Produce a minimal default-disabled
> design, binary acceptance fixtures with expected failure reasons, reproducible
> build/signing requirements, and the owner ceremony required to enable one exact
> signed escape-hatch version.

## R9 — Transactional durability, recovery, and independent dead-man monitoring

> Design a crash-consistent durability protocol for authority, approval, Active/
> Recommended, signal, Gold lifecycle, compact research ledger, and bulk artifacts.
> Do not equate `fsync`, a copied SQLite/WAL file, a successful push, or a cached
> read-back with a transactionally valid replica. Specify transaction/log sequence
> numbers, atomic snapshot or SQLite backup APIs, acknowledgement boundaries,
> idempotent replay, divergence detection, queued GitHub replication, and recovery
> ordering. Model process kill, one-disk loss, whole-tower loss, shared-power/fire/
> theft, GitHub-only outage, stale remote, corruption, and total internet outage.
> Return explicit RPO/RTO per failure scope. Design a non-authoritative clean-machine
> restore drill and one outbound-only heartbeat service whose alert route is outside
> Montauk's Slack/Buzz authority path. Reconcile the design with “GitHub for now”
> and identify exactly what zero-data-loss promise is and is not physically possible.

## R10 — Ranking, score redundancy, and owner decision quality

> Audit Montauk Score and the recommendation/switch surface without changing Gold
> eligibility. Replace the proposed pairwise `R² > 0.6` shortcut with a method able
> to detect exact, monotonic, nonlinear, and multivariable redundancy: rank
> correlation, conditional ablation, multicollinearity, mutual information where
> justified, and genuinely out-of-sample incremental ranking/switch value. Ensure a
> third pillar cannot become a hidden Gold gate. Evaluate leader-separation methods
> after adaptive selection and shared market dependence; do not reduce confidence
> from 90% to 75% merely to make the warning appear less often. Calibrate false-clear
> and false-ambiguity rates on known equal and separated leaders. Design and test one
> complete review card plus one explicit confirmation button for pointer-only and
> opposite-state changes, deferral/dismissal retriggers, immutable audit history,
> drawdown/catastrophe visibility, and recommendation churn.

## R11 — Phase 1 integration and adversarial contract audit

> Rebuild the Phase 1 dependency and acceptance matrix across all ten research
> streams. Ensure data/execution and economic contracts freeze before statistical
> grading; known-answer control generators freeze before validator calibration;
> calibration and sealed audit batteries are genuinely disjoint; retrospective
> holdout logging never restores validity to already-revealed data; and sandbox,
> independent reproduction, durability, notification, ranking, and recovery each
> have explicit Phase 1 gates rather than appearing only in a summary diagram.
> Correct broken links, inconsistent TECL-history figures, unsafe expected control
> verdicts, and owner recommendations presented as ratified decisions. Build a
> requirement-traceability table from every charter/decision/questionnaire promise
> to one study, positive fixture, seeded negative, expected result, retained
> artifact, responsible reviewer, and ratification step. Have a final adversarial
> reviewer who did not see calibration results attempt to invalidate the complete
> package. Output a blocking-issues list rather than declaring readiness when a
> mandatory claim remains unsupported.


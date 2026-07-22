# Montauk 3.0 Research — Stream 1: Phase 1 program design

**Scope.** This report converts the Phase 1 mandate in `implementation-plan.md`
("Phase 1 — prove the exam and authority contract") and the Phase 1 obligations
in `validation-engine-hardening.md` §§1b, 2a–2b, 3e and `decisions.md`
(D43, D45–D50, D57) into a dependency-ordered, preregistered research program: a
set of study IDs with inputs, outputs, acceptance gates, review roles,
parallelism rules, and a ratification sequence. It does not propose new Gold
thresholds, weights, or product policy — those remain charter- and
decision-log-owned. It specifies **how Phase 1 itself must be run** so Phase 1
does not become the first thing Montauk overfits.

---

## 1. One-page plain-English conclusion

**What Phase 1 actually is.** Before Montauk can certify a single Gold
strategy, someone has to design and freeze the exam itself — the fill model,
the benchmark, the statistical tests, the multiple-testing correction — using
methods chosen *before* anyone looks at how Montauk's own candidates score on
them. Tune-then-peek design work makes Phase 1 an overfit **validator** that
happens to pass whatever is currently running, one level up from an overfit
strategy.

**The core discipline** (a clinical-trial standard applied to the exam itself):
1. **Write the exact question and stopping rule before collecting evidence**
   (preregistration — Nosek et al. 2018 [Evidence: primary]).
2. **Never let the same data both tune a method and grade it** (Cawley &
   Talbot 2010's selection-bias result [Evidence: primary]).
3. **Test the validator on cases with a known right answer** — planted noise
   that should fail, planted signal that should pass, known defects that
   should be caught — before trusting it on real candidates
   (validation-of-validation, per `validation-engine-hardening.md` G14).
4. **Never spend the same holdout evidence twice without accounting for it**
   (Dwork et al. 2015's reusable-holdout problem [Evidence: primary], with the
   transfer caveat in §6).

**A concrete example.** If Phase 1 is deciding whether CPCV should be a hard
Gold gate, the wrong way is: run CPCV on today's leaderboard, see the current
champion pass, and ship it — grading the exam using the answer you already
like. The right way (Study P1-04): build **control worlds** first — pure
noise, a random long/cash rule, a strategy that memorizes 2020/2022 dates —
with known correct verdicts ("should fail" for all three). Freeze CPCV's exact
configuration against those controls *before* it ever sees a real candidate.
Only if it rejects the known-bad controls and passes the planted-good control
does it earn a role in the real contract, and its config is never retuned
against real candidates afterward.

**What Max should decide and do.**
- Approve the ten study IDs (§3) and dependency order (§3.10) as the Phase 1
  work plan.
- Personally hold the "unblind" step in every study that has one: nobody
  (including an AI agent) sees how a real candidate scores against a newly
  calibrated method until that method's config is frozen and hash-logged.
- Expect "insufficient evidence" or "this method does not earn a hard-gate
  role at Montauk's sample size" as legitimate outcomes, per the charter's
  priority order (false Gold is worse than a missed good strategy).
- Reserve the final ratification meeting (§3.10 step 6) to review the whole
  package at once — later studies can reveal that an earlier one needs
  revision.

---

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Preregistering hypotheses, design, and analysis plan before data collection reduces researcher degrees of freedom and distinguishes confirmatory from exploratory findings | Primary paper | Nosek, Ebersole, DeHaven, Mellor, "The preregistration revolution," *PNAS* 115(11), 2018. https://www.pnas.org/doi/10.1073/pnas.1708274114 | Strong (well-established methodology paper; broad adoption across psychology/medicine, cited here for the mechanism, not for an external consensus claim about Montauk's domain) | **Partially.** The freeze-before-look mechanism is domain-agnostic and directly usable for Phase 1's method-selection process. The population (behavioral/clinical studies) does not transfer any numeric threshold — only the discipline transfers. | Use for *process design* (§3, §4); never to import an effect-size or p-value convention into TECL backtesting. |
| Many defensible analytic choices exist even for one honestly pre-specified hypothesis; the resulting "garden of forking paths" inflates false positives without deliberate p-hacking | Primary paper | Gelman & Loken, "The garden of forking paths," 2013 (Columbia working paper; condensed in *American Scientist*, 2014). https://sites.stat.columbia.edu/gelman/research/unpublished/Forking_paths.pdf | Strong (mechanism is a mathematical/logical argument, not an empirical claim tied to one population) | **Yes, directly.** Applies to any adaptive analyst, including an AI agent iterating strategy families against a fixed dataset — the mechanism, not the population, is what matters. | Motivates P1-01 (control worlds) and the requirement that Phase 1's own method comparisons be logged as a forking-paths ledger, not just a final report. |
| Optimizing a model-selection criterion over finite data has non-negligible variance; selection bias from this can be comparable in magnitude to real differences between algorithms | Primary paper | Cawley & Talbot, "On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation," *JMLR* 11, 2010, pp. 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html | Strong (JMLR; the abstract itself states the selection-bias-magnitude finding directly, confirmed by direct fetch) | **Yes, structurally.** Montauk's search-then-validate process shares the same variance/selection-bias mechanism, independent of asset class. The paper's own numeric bias magnitudes are on UCI-style benchmarks and do **not** transfer as TECL numbers. | The nested (double) cross-validation remedy is the paper's broader prescription (its full argument and citation history), not a sentence quoted from the abstract — cited here as an accurate characterization, not an abstract-level quote. Grounds P1-02's nested-holdout design. |
| Repeated adaptive querying of a fixed holdout invalidates naive statistical guarantees; a "reusable holdout" mechanism can preserve validity across many adaptive queries within a bounded budget | Primary paper | Dwork, Feldman, Hardt, Pitassi, Reingold, Roth, "The reusable holdout: Preserving validity in adaptive data analysis," *Science* 349(6248), 2015. https://pubmed.ncbi.nlm.nih.gov/26250683/ | Strong (Science; formal guarantee with stated assumptions, confirmed by direct abstract fetch) | **Partially — [Inference] for the non-transfer half.** The core warning (holdouts get "spent" by adaptive reveal) transfers exactly. The abstract does not itself state the i.i.d.-sampling/bounded-query-budget assumptions; that the guarantee likely does not extend to Montauk's serially dependent bars is this report's own inference, not a claim independently verified against the primary source (§6). | Use to justify P1-03 (holdout-reveal ledger); do **not** cite this paper as license to claim a Montauk holdout is "safe to reuse indefinitely." |
| A sequential "Ladder" algorithm can maintain an accurate leaderboard under fully adaptive, repeated resubmission using minimal disclosure | Primary paper (preprint / ICML 2015) | Blum & Hardt, "The Ladder: A Reliable Leaderboard for Machine Learning Competitions," arXiv:1502.04585. https://arxiv.org/abs/1502.04585 | Moderate (single paper, theoretical guarantees under an adversarial model, less empirically stress-tested than Cawley/Dwork) | **Conceptually, not numerically.** Montauk's Gold leaderboard is this exact problem, but the paper's model does not include serial dependence or non-i.i.d. daily bars. | Treat as an architectural pattern to test in P1-03/P1-06, not an adopted, pre-proven algorithm. |
| CSCV/PBO estimates the probability that the best-performing configuration in a search is overfit, using symmetric partitions of the same trials tried; targets the search/selection process, not one strategy in isolation | Primary paper | Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting," *Journal of Computational Finance* 20(4), 2017, pp. 39–70 (SSRN preprint 2014, id 2326253). https://doi.org/10.21314/JCF.2016.322 | Strong (peer-reviewed, directly on backtest overfitting) | **Yes for the target, no for any fixed threshold.** Matches the repo's own G7 finding: the legacy PBO used M=32 draws/16 blocks that did not represent Montauk's actual searched universe. Method validity transfers; any specific PBO cutoff does not — it is a function of the actual selection matrix. | Central to P1-04; must be run on Montauk's actual predeclared family/campaign selection matrix, never a convenient random neighborhood. |
| CPCV shows lower probability of backtest overfitting and better rank stability than K-Fold, Purged K-Fold, and Walk-Forward in a synthetic controlled environment built to compare validation schemes | Primary paper | Arian, Norouzi Mobarekeh & Seco, "Backtest overfitting in the machine learning era: A comparison of out-of-sample testing methods in a synthetic controlled environment," *Knowledge-Based Systems* 305, 2024, art. 112477. https://doi.org/10.1016/j.knosys.2024.112477 | Strong as a peer-reviewed methods comparison | **No, not directly.** The paper's population is a synthetic controlled environment built for the comparison, not TECL's own low-trade regime (typically <20 trades for a champion strategy). Its CPCV-superiority ranking is a different population's result. | Cited only to explain why P1-02 runs its own bake-off on Montauk's actual controls (§3) rather than importing this paper's ranking as if it applied to TECL. |
| No single cross-validation scheme (blocked, purged, walk-forward, combinatorial) dominates across all conditions on non-stationary, financial-style time series; scheme choice is context-dependent | Working paper | Schnaubelt, "A comparison of machine learning model validation schemes for non-stationary time series data," FAU Discussion Papers in Economics No. 11/2019. https://www.econstor.eu/handle/10419/209136 | Moderate (working paper, not journal-refereed at time of citation) | **No, not directly.** Same reasoning as the Arian et al. row — a different, non-TECL population. | Cited only as the second population Phase 1 should *not* import a ranking from; P1-02 generates Montauk-specific evidence instead. |

---

## 3. Recommended Montauk experiments

Each study has a **study ID**, a **preregistered estimand** (fixed before
results are seen), an explicit **stopping rule**, and what must be **frozen
before looking at results**. These make executable the obligations already
stated in `implementation-plan.md`'s Phase 1 bullets and
`validation-engine-hardening.md` §3e.

### P1-00 — Freeze the exam's own preregistration document
- **Inputs:** charter.md Gold definition; decisions D43/D45–D50; the candidate
  method list in `validation-engine-hardening.md` §3b/§3d.
- **Estimand:** N/A — this study produces the preregistration artifact itself.
- **Stopping rule:** complete when every candidate method (nested rolling-
  origin, CPCV, CSCV/PBO, SPA/Reality Check/Romano-Wolf, stationary bootstrap,
  Morris sensitivity, MinTRL, synthetic-overlap weight) has a named target
  question, a predeclared pass/fail rule, and an owning study, logged in one
  version-hashed document before any control world is built.
- **Frozen before results:** the entire list — no method added or dropped
  after P1-01 begins without a logged amendment and rationale.
- **Output:** `phase1-preregistration-v1.md` (hash-stamped).

### P1-01 — Build the control worlds (the "known answer key")
- **Inputs:** TECL/TQQQ/QQQ/synthetic history from `data/`; the engine's
  causal replay contract.
- **Estimand:** for each control world, the known ground-truth verdict (e.g.,
  "a dependence-preserving null-return world contains no exploitable edge; any
  strategy passing Gold on it is a false Gold by construction").
- **Stopping rule:** all seven control classes from
  `validation-engine-hardening.md` §3e-2 exist and are independently reviewed
  before any real candidate touches them: (1) dependence-preserving null
  returns, (2) exposure/trade-count-matched random long/cash rules, (3)
  high-dimensional noise families searched over many configurations, (4)
  event/date memorizers, (5) intentional lookahead/repaint/fill defects, (6)
  frozen structural controls (static B&H, static cash), (7) synthetic worlds
  with a planted, recoverable signal of known size.
- **Frozen before results:** the expected verdict for every control
  (pass/fail/insufficient), written down before any validator method runs on
  it.
- **Output:** `control-worlds-v1/` fixture set + `expected-verdicts.json`.

### P1-02 — Rolling-origin vs. CPCV method bake-off
- **Inputs:** P1-01 controls, split into a "calibration slice" and a disjoint
  "final-check slice" (Cawley & Talbot's nested structure).
- **Estimand:** for each of {expanding nested rolling-origin, fixed-window
  rolling-origin, CPCV-with-derived-purge/embargo}, measured on the
  calibration slice only: false-Gold rate on known-null controls,
  correct-rejection rate on planted defects, recovery rate of the
  planted-signal control, rank stability, compute cost.
- **Stopping rule:** each method's configuration is frozen once its
  calibration-slice metrics are recorded — no further tuning after that
  freeze.
- **Frozen before results:** the calibration/final-check assignment (by
  control-ID hash, not cherry-picked); the metric formulas; the decision rule
  for "CPCV earns hard-gate status" (per D48: defined target + adequate power
  + measured incremental defect detection beyond rolling-origin alone,
  evaluated only on the final-check slice).
- **Output:** `method-bakeoff-v1-report.md` + frozen validator-method configs.
  This answers the open "is CPCV better than walk-forward" question (§2b) on
  Montauk's own low-trade regime directly, rather than importing the
  Arian–Norouzi Mobarekeh–Seco or Schnaubelt papers' populations (see §2 —
  both are peer-reviewed/working papers on unrelated environments, not
  evidence about TECL).

### P1-03 — Holdout-reveal ledger and adaptive-reuse accounting
- **Inputs:** every P1-01/P1-02 control result; every real historical data
  slice ever shown to a human or agent during Phase 1.
- **Estimand:** a complete, append-only log of every holdout reveal — what,
  to whom, when, and what decision it influenced.
- **Stopping rule:** the ledger schema exists and is populated retroactively
  for every P1-01–P1-02 reveal before P1-04 begins.
- **Frozen before results:** the ledger schema (fields, immutability
  guarantee, hash-chaining).
- **Output:** `holdout-ledger-schema-v1.md` + populated ledger. Since Dwork et
  al.'s formal guarantee likely does not transfer to Montauk's serially
  dependent bars and unbounded query budget (§6), complete disclosure
  accounting is the honest fallback, stated as such rather than silently
  assumed.

### P1-04 — Board-level search-honesty correction
- **Inputs:** P1-01 controls (especially the high-dimensional noise-family and
  event-memorizer controls); P1-03 ledger; a reconstructed "actual searched
  universe" reflecting Montauk's real family/campaign structure (not a
  convenient random neighborhood — answers the repo's own G7 finding); Stream
  4's frozen economic-passage rule (cross-stream dependency — §3.10).
- **Estimand:** for each of {CSCV/PBO on the actual selection matrix, White's
  Reality Check, Hansen's SPA, Romano-Wolf step-down}: board-level false-Gold
  rate under the correlated-noise control, power to still pass the
  planted-signal control, compute cost.
- **Stopping rule:** freeze the method (or minimal combination) that controls
  false-Gold under the correlated-noise control without rejecting the
  planted-signal control, evaluated once on a final-check subset disjoint
  from whatever was used to pick the method.
- **Frozen before results:** the definition of "the actual searched universe"
  (exact configuration? behavioral cluster after G19 fingerprinting?) —
  decided from the charter's dependence language, not backed into after
  seeing which definition preserves a particular candidate.
- **Output:** `search-honesty-method-v1.md`, frozen correction formula.

### P1-05 — Execution/comparator truth calibration: cross-stream dependency (owned by Stream 5)
- **Inputs:** Stream 5's own calibration of the next-regular-session-open fill
  model, slippage/fee functions across the $10,000–$100,000 notional band, and
  the matched-B&H construction.
- **Estimand:** owned by Stream 5 — not restated here.
- **Stopping rule:** owned by Stream 5; **this stream only requires** that the
  fill/comparator contract be frozen (version-hashed) before P1-02/P1-04 run
  their final-check slice, since every backtest verdict downstream depends on
  it.
- **Frozen before results:** the fill/comparator formula itself, before any
  control-world or real-candidate backtest is scored under it.
- **Output:** cross-reference to Stream 5's artifact; this stream records only
  the dependency edge (§3.10).

### P1-06 — Validation-of-validation harness (G14) end-to-end dry run
- **Inputs:** P1-00–P1-04 frozen methods; P1-01 controls; P1-03 ledger;
  Stream 5's and Stream 4's frozen contracts (§3.10).
- **Estimand:** whole-validator sensitivity (fraction of seeded
  defects/known-bad controls correctly rejected) and specificity (fraction of
  known-good controls, including the planted-signal world, correctly
  passed), reported with the control sample size.
- **Stopping rule:** run once, end-to-end, through the entire author → search
  → select → backtest → validate pipeline on every control, not just the
  final method stack in isolation (per §3e item 3 — testing only a
  preselected winner understates the false-discovery problem).
- **Frozen before results:** the full pipeline configuration (every method
  frozen in P1-00–P1-05) before this run starts; a failure here returns to
  the relevant upstream study with a logged amendment, not a silent patch.
- **Output:** `validator-of-validator-report-v1.md`: sensitivity/specificity
  point estimates + CIs, per-control breakdown, known limitations.

### P1-07 — Whole-appliance false-Gold/false-reject frontier
- **Inputs:** P1-06 output; a simulated year of continuous adaptive search
  against P1-01 controls (per D50 / charter §2.3 priority order).
- **Estimand:** the appliance-level curve of P(≥1 false Gold in a simulated
  year of continuous search) vs. recovery rate of planted meaningful signals,
  at several operating points around the 1% aspirational annual reference.
- **Stopping rule:** frontier reported at a predeclared grid of operating
  points; Max reviews it once and chooses an operating point.
- **Frozen before results:** the grid of operating points (chosen for
  interpretability, not to land near a convenient number).
- **Output:** `false-gold-frontier-v1.md` + the plotted curve.

### P1-08 — Montauk Score formula freeze
- **Inputs:** P1-04/P1-06/P1-07 outputs; the charter's requirement that
  Validation Score take priority and no third pillar be admitted without
  proven incremental value.
- **Estimand:** whether a proposed third pillar adds measurably distinct
  information on the P1-01 controls (does it change rank-ordering of
  known-good vs. known-bad controls beyond the two existing pillars?).
- **Stopping rule:** admit a pillar only if it changes at least one control's
  correct classification that the two-pillar formula got wrong; otherwise
  reject it.
- **Frozen before results:** the definition of "measurably distinct
  information" — a predeclared statistical test on the controls, not an
  eyeball comparison after seeing real leaderboard rows.
- **Output:** `montauk-score-formula-v1.md`.

### P1-09 — Synthetic-TECL overlap study: cross-stream dependency (owned by Stream 6)
- **Inputs:** Stream 6's calibrate-earlier/score-later overlap design
  (`6-Synthetic TECL reconstruction`), which is itself the recalibration
  design for the pre-2008 synthetic series.
- **Estimand:** owned by Stream 6 — not restated here, to avoid two documents
  defining the same estimand. (Stream 6 calibrates the reconstruction's
  assumptions on earlier overlap blocks only, then scores later blocks
  without refitting, split at the June 2012 index-target seam and September
  2018 GICS reshuffle it identifies.)
- **Stopping rule:** owned by Stream 6. This stream's own requirement:
  Stream 6's frozen calibrate/score boundary and diagnostic-weight
  recommendation must be locked before P1-08 sets the Montauk Score formula,
  since a synthetic-history diagnostic weight is one of charter §4.2's
  inputs.
- **Frozen before results:** N/A here. Phase 1 freezes only that it will
  treat Stream 6's output as diagnostic-only (per D30/D56), never a
  substitute for real-TECL passage.
- **Output:** `p1-09-stream6-dependency-note-v1.md` recording the edge and
  confirming no duplicate estimand exists between this document and Stream
  6's report. The substantive experiment output remains Stream 6's own
  artifact set.

### 3.10 Dependency order, acceptance gates, review roles, and ratification sequence

**Dependency graph.** Arrows mean "must be frozen before the next study's
final-check phase begins." Studies with no arrow between them may run in
parallel.

```
P1-00 (preregister)
   |
   v
P1-01 (control worlds) --+------------------> P1-03 (holdout ledger,
   |                     |                     populated retroactively)
   |                     +------------------> P1-09 (cross-ref only:
   |                                          Stream 6's own study; no
   v                                          in-house duplicate)
P1-02 (rolling/CPCV bake-off)
   |
   +--------------------------> P1-04 (search-honesty correction)
   |                                   |
   |   Stream 5 (fill/comparator, cross-referenced) and Stream 4
   |   (economic-passage rule, cross-referenced) must each freeze
   |   before P1-02 and P1-04 grade their final-check slices.
   v                                   v
P1-06 (validator-of-validator, full pipeline dry run — needs P1-02,
        P1-04, Stream 5, and Stream 4 all frozen)
   |
   v
P1-07 (false-Gold/false-reject frontier)
   |
   v
P1-08 (Montauk Score formula freeze — needs P1-09/Stream 6 frozen too)
   |
   v
RATIFICATION (Max reviews the complete package)
```

**Parallelism rule.** P1-00/P1-01 are strictly sequential prerequisites for
everything else. Once P1-01 is frozen, P1-02 and P1-04's control construction
run in parallel (disjoint control-set slices). P1-09 is a cross-stream
dependency edge onto Stream 6, not an in-house experiment — it needs only
P1-01/P1-03 and Stream 6's own frozen report, independent of P1-02/P1-04/P1-06.
Stream 5 (fill/comparator) and Stream 4 (economic-passage calibration — the
rolling-aggregate/catastrophic-veto design, the provisional 1.10× margin, the
evidence-sufficiency floor) are both cross-stream inputs of the same shape:
each must freeze before P1-02/P1-04 grade final-check passes and before §4's
controls (e.g., "all-cash must FAIL economic passage") can be graded, but each
stream's own calibration proceeds in parallel with P1-00–P1-03. P1-06 waits on
P1-02, P1-04, Stream 5, and Stream 4. P1-07/P1-08 are sequential after P1-06;
P1-08 also needs Stream 6 frozen via P1-09. Phase 2 Workstream 2A
(validator-agnostic prototyping) may start in parallel with P1-02–P1-09; Phase
3 (the conveyor) waits for full ratification.

**Acceptance gates.**

| Study | Acceptance gate |
|---|---|
| P1-00 | Every candidate method has a named target, a predeclared decision rule, and an owning study, logged in a version-hashed document. |
| P1-01 | All seven control classes exist with independently reviewed, predeclared expected verdicts logged before any method touches them. |
| P1-02 | The chosen window design's calibration-slice metrics are frozen and its final-check-slice metrics (disjoint control subset) are reported without further tuning. |
| P1-03 | The ledger schema is populated retroactively for every prior reveal; no un-logged reveal exists before P1-04 begins. |
| P1-04 | The chosen correction method controls false-Gold on the correlated-noise control on a disjoint final-check subset while still passing the planted-signal control at a stated rate, and Stream 4's frozen economic-passage rule exists so §4's controls can be graded consistently. |
| P1-05 | Stream 5 delivers a version-hashed fill/comparator contract before P1-02/P1-04 grade their final-check slices. |
| P1-06 | The full author→search→select→backtest→validate pipeline is dry-run on every P1-01 control, once, with every upstream method (including Stream 5/Stream 4) already frozen. |
| P1-07 | The frontier is reported at a predeclared grid of operating points; Max has reviewed it and chosen an operating point. |
| P1-08 | Any proposed third pillar is rejected unless it changes at least one control's classification that the two-pillar formula got wrong, per a predeclared test; Stream 6's synthetic-weight recommendation is frozen. |
| P1-09 | Stream 6 delivers its frozen calibrate-earlier/score-later report; this stream's dependency note confirms no duplicate estimand exists between the two documents. |

**Review roles.** Per the charter's rule that a paid/credentialed external
reviewer is not a 3.0 gate (§2.2), roles are filled by Max and AI agent
invocations under a structural-independence rule:

- **Method designer** (may be an AI agent): proposes/configures a candidate
  method (e.g., a CPCV purge/embargo formula in P1-02).
- **Control-verdict author** (logged before the designer's method runs, per
  P1-01): declares the expected verdict for each control, timestamped and
  hash-chained in the P1-03 ledger *before* the method designer's config runs
  against it — separating the roles in time even under the same overall agent.
- **Adversarial reviewer** (fresh agent invocation or Max, no visibility into
  calibration-slice results): audits the final-check pass in
  P1-02/P1-04/P1-06 for the failure modes in G1–G19.
- **Owner-ratifier** (Max only): holds the single sign-off below; no study is
  "accepted" merely because an agent's own report says pass.

**Final ratification sequence.**
1. All ten studies reach their acceptance gate (table above).
2. The AI agent assembles one consolidated package:
   `phase1-preregistration-v1.md`, every study's frozen artifact, the complete
   P1-03 ledger, and the P1-06 report with its sensitivity/specificity CIs.
3. An adversarial-reviewer pass (fresh agent invocation, no prior visibility
   into calibration-slice results) checks the package against G1–G19 and
   confirms no method was tuned after seeing its own final-check result
   (auditable via P1-03's timestamps).
4. Max reviews the P1-07 frontier and chooses an operating point.
5. Max reviews the plain-language decision reports (per D57) for every
   provisional value this stream touches: rolling-window design,
   search-honesty correction, Montauk Score formula.
6. Max ratifies the whole package as one signed, versioned contract. Per
   `implementation-plan.md`'s Phase 1 exit criterion, this requires that no
   canonical doc or test say "top row is automatically active," label an
   uncalibrated score as a probability, permit a skipped Gold plank, or
   preserve an incompatible validation route.
7. Only after step 6 does Phase 3 (the conveyor) begin wiring in the frozen
   methods; Phase 2's validator-agnostic engineering work may already be
   underway per the parallelism rule above.

---

## 4. Null, defect, and planted-signal controls

What P1-01 must contain, restated as falsifiable pass/fail expectations:

| Control | What it is | Must pass or fail? | What a failure here indicates |
|---|---|---|---|
| Dependence-preserving null returns | Reshuffled/resampled returns preserving autocorrelation/volatility clustering but destroying any real signal | **Must FAIL Gold** | If any strategy searched over this world reaches Gold, P1-04's correction is too weak — a direct false-Gold detection. |
| Exposure/trade-count-matched random long/cash rule | Same position-change count and average holding period as a typical candidate, but the on/off decision is randomized | **Must FAIL Gold** | Tests whether the validator secretly rewards "being in the market often" rather than a real timing edge. |
| High-dimensional noise family searched over many configurations | A sterile parameter grid with no causal connection to price, searched exhaustively like a real family | **Must FAIL Gold even at the top of the search** | The sharpest test of the multiplicity correction (P1-04) and G1/G2. |
| Event/date memorizer | A rule keyed to specific calendar dates rather than any general signal | **Must FAIL generalization plank**, even if it passes economic passage on history including that date | Tests event-concentration/regime-consistency diagnostics; a memorizer should collapse under out-of-sample stress. |
| Intentional lookahead/repaint/fill defect | A strategy using next-bar information, or a fill model filling at a better-than-obtainable price | **Must FAIL correctness plank** | Direct test of causal-replay/prefix-invariance checks; if this passes, the correctness plank is broken. |
| Simple frozen structural control (static B&H, static all-cash) | The comparator itself and its trivial complement | **B&H must exactly match its own definition (tautological pass); all-cash must FAIL economic passage** (graded against Stream 4's frozen rule) | Sanity check on comparator math and terminal-wealth/share-multiple accounting. |
| Synthetic world with a planted, recoverable signal | A constructed price series with a known, moderate genuine edge inserted into otherwise realistic noise | **Must PASS Gold, at a chosen minimum recovery rate** | The power check — exposes an over-strict validator (fails everything) or one that never recovers real signal. |
| Amended/duplicate near-twin parameter cluster (G19) | Many parameter points producing an identical or near-identical trade path | **Must be counted as ONE effective trial for multiplicity, not many** | Tests that P1-04 uses behavioral-cluster dependence rather than raw parameter counts. |

**How this detects silent cheating.** Every control's expected verdict is
written down in P1-00/P1-01 before any method touches it. If a method's
config is later adjusted specifically to make a known-null control pass or a
known-good control fail more comfortably after seeing the result, that is
data-dependent method tuning — Cawley & Talbot's failure mode, at the
meta-level of choosing the exam. The P1-03 ledger exists to make any such
after-the-fact adjustment visible rather than silently absorbed into a
"final" report.

---

## 5. False-Gold and false-rejection consequences

The charter treats a false Gold as slightly worse than a false rejection
(§2.3), and Phase 1's own strictness choices sit on exactly this tradeoff:

- **False Gold cost.** Max manually executes a real position change based on
  a strategy that is not actually better than TECL B&H. Because execution is
  manual and TECL is 3x-levered, a false-Gold drawdown compounds real capital
  loss with erosion of trust in the whole appliance — surfacing during a real
  drawdown, it is the scenario most likely to make Max stop trusting Montauk
  altogether: a whole-program cost.
- **False rejection cost.** A genuinely good strategy sits at "no Gold," and
  Montauk continues with an inferior or no signal. Because an empty board
  never authorizes lowering the standard (charter §4.1), the cost is forgone,
  recoverable performance — not symmetric with false Gold's capital-and-trust
  risk.
- **Where Phase 1 lands.** Every stopping rule above (P1-02, P1-04, P1-06)
  prefers freezing a method that clears the known-null controls even at some
  cost to planted-signal power. P1-07's frontier makes this tradeoff visible
  and numeric rather than an implicit design choice.
- **Asymmetric review.** P1-06's harness weights its review more toward
  sensitivity to known-null/noise-family controls (can a bad strategy sneak
  through) than toward planted-signal recovery, while still reporting both.

---

## 6. Assumptions and power/limits

- **Sample-size ceiling is structural, not fixable by better statistics**
  (G3). Real TECL history is **~17.5 years** (inception 2008-12-17; verified
  directly against 4,401 real-labeled rows in `data/TECL.csv`, spanning
  2008-12-17 through the current data pull — not "roughly 15 years"),
  containing on the order of **3** materially independent real
  macro/volatility regimes (the 2008 GFC aftermath at/near inception, the
  2020 COVID crash/recovery, and the 2022 rate-hike bear). D47's four-item
  named-moment diagnostic suite additionally lists dot-com (2001–2003), but
  that moment predates TECL's 2008-12-17 real inception entirely and exists
  only as reconstructed/synthetic history — D47 itself states "no
  reconstructed episode can satisfy a real-data Gold gate," so dot-com must
  not be counted toward the real-regime tally this ceiling argument depends
  on, even though it remains a legitimate synthetic-diagnostic panel entry.
  Every study above reporting a "final-check" statistic on real TECL history
  inherits this ceiling: no resampling or cross-validation design manufactures
  independent regimes the data do not contain. Phase 1's job is to **report**
  this ceiling honestly, not to paper over it with an impressive composite
  score.
- **Control worlds are not real markets.** P1-01's synthetic null/noise/
  planted-signal worlds test the validator's mechanics, not whether TECL
  specifically contains an exploitable edge. P1-06/P1-07 measure the exam's
  honesty; separately, Stream 6 (via P1-09's dependency edge) measures how
  much pre-inception synthetic history can be trusted as diagnostic evidence
  — these are different questions and must not be conflated. This report
  resolves a prior ambiguity about whether P1-09 duplicates Stream 6's work:
  it does not — P1-09 is a dependency edge only, and Stream 6 is the sole
  owner of that estimand and stopping rule (§3, P1-09).
- **The Dwork et al. reusable-holdout formal guarantee likely does not
  transfer cleanly** [Inference — this report's own reasoning, not verified
  against the paper's full text]. Their guarantee assumes i.i.d.-sampled
  queries against a fixed-size holdout within a bounded adaptive budget.
  Montauk's daily bars are serially dependent, a strategy's informative
  "trials" are trades/regime-transitions rather than daily rows, and the
  agent's query budget is effectively unbounded and continuous. Phase 1
  should not claim a Montauk holdout is "provably safe to reuse" on this
  paper's strength; P1-03's ledger is the honest fallback.
- **Blum & Hardt's Ladder is a pattern, not a proof for Montauk.** Its
  adversarial-adaptive model excludes serial dependence and multi-year
  evaluation horizons; any adopted mechanism requires its own control-world
  validation (P1-06), not inherited theoretical guarantees.
- **Nested cross-validation (Cawley & Talbot) transfers as a structural
  requirement, not a specific k-fold recipe.** Their result concerns any
  selection process optimized over finite data with non-negligible estimator
  variance; TECL-appropriate window lengths remain Phase 1's own calibration
  work (P1-02), constrained by the small independent-regime count above.
- **The Arian–Norouzi Mobarekeh–Seco and Schnaubelt papers are cited only to
  explain a methodological choice, not as evidence about TECL** (§2). Neither
  paper's population is Montauk's low-trade regime; P1-02 exists precisely so
  Phase 1 does not import either paper's CPCV-vs-walk-forward ranking as if
  it applied here.
- **This report does not resolve** the exact purge/embargo formula, the
  specific slippage/fee numbers, the final 1.10-vs-calibrated economic
  margin, or the exact Montauk Score weighting — Streams 2, 4, 5, and 10's
  substantive work. This stream only specifies the process by which those
  streams must freeze and test their answers.

---

## 7. Required fixtures and durable artifacts

| Fixture / artifact | Type | Expected result | Retention |
|---|---|---|---|
| `control-worlds-v1/` (7 classes from P1-01) | Deterministic positive + seeded-negative fixtures | Each control's expected verdict logged in `expected-verdicts.json` before any method runs | Permanent — re-run on every validator version bump |
| `phase1-preregistration-v1.md` | Preregistration document (P1-00) | N/A — this *is* the frozen plan | Permanent, version-hashed, amendments logged not silently edited |
| `holdout-ledger-schema-v1.md` + populated ledger (P1-03) | Durable disclosure record | Every reveal timestamped, hash-chained, attributed | Permanent, append-only |
| `method-bakeoff-v1-report.md` (P1-02) | Acceptance artifact | Frozen window-design config + calibration/final-check split identifiers | Permanent |
| `search-honesty-method-v1.md` (P1-04) | Acceptance artifact | Frozen correction method + its false-Gold/power numbers on controls | Permanent |
| `validator-of-validator-report-v1.md` (P1-06) | Acceptance artifact | Sensitivity/specificity point estimates + CIs, full pipeline run | Permanent, re-run required on every core-release version bump |
| `false-gold-frontier-v1.md` (P1-07) | Decision artifact for Max | The frontier curve + Max's chosen operating point, dated and signed | Permanent |
| `montauk-score-formula-v1.md` (P1-08) | Frozen formula spec | Two-pillar formula unless a third pillar's incremental value is proven on controls | Permanent, versioned |
| `p1-09-stream6-dependency-note-v1.md` (P1-09) | Dependency-edge record | Confirms no duplicate estimand vs. Stream 6's `synthetic-tecl-reconstruction.md`; records the freeze date this stream depends on | Permanent |
| Seeded-defect fixtures (lookahead, repaint, wrong fill, non-finite arithmetic) | Negative fixtures | Correctness plank fails closed on each, with a produced artifact | Permanent regression suite, run pre-merge on every engine change |

Every safety- or evidence-critical step gets one positive fixture, one
negative/seeded-defect fixture, a deterministic expected result, and a
retained acceptance artifact. "The complete pipeline passed once" is never
accepted as proof of an individual internal step.

---

## 8. Unresolved owner decisions

1. **How many controls are "enough" for P1-01/P1-06's sensitivity/specificity
   estimate to be trustworthy, given TECL's own small independent-regime
   count?**
   *Default:* report the estimate with an explicit sample size and confidence
   interval rather than fixing a control count in advance; accept a wide
   interval as an honest limit. *Tradeoff:* more synthetic controls tighten
   validator-quality estimates but buy no more real TECL evidence — do not
   let a precise validator-quality number imply a precise strategy-quality
   number.

2. **Who plays "adversarial reviewer" in P1-04/P1-06 — must it be a person
   distinct from whoever configured the method, or can the same AI agent
   self-review under a different prompt?**
   *Default:* the charter requires independent reimplementation/adversarial
   review but rules out a mandatory paid external reviewer (§2.2). Practical
   default: Max personally reviews the final P1-06/P1-07 artifacts before
   ratification, and any AI adversarial review runs from an agent invocation
   that did not see the calibration-slice results — structural, not merely
   social, separation. *Tradeoff:* weaker than a fully independent human
   reviewer, but that option was already explicitly descoped by Max.

3. **Should the ten studies gate sequentially, or can Phase 2's
   non-validation engineering proceed in parallel while P1-04–P1-09 are still
   running?**
   *Default:* per §3.10, allow Phase 2 Workstream 2A (validator-agnostic
   prototyping) to start once P1-00/P1-01/P1-03 are frozen. Phase 3 (the
   conveyor) waits for full ratification. *Tradeoff:* parallelism saves
   calendar time but risks Phase 2 assuming a validator shape Phase 1 later
   changes; mitigated by keeping 2A method-agnostic.

4. **What counts as large-enough "measured incremental value" for a proposed
   third Montauk Score pillar (P1-08)?**
   *Default:* require the pillar to change the correct/incorrect
   classification of at least one P1-01 control the two-pillar formula got
   wrong, via a predeclared test — not a subjective post-hoc judgment.
   *Tradeoff:* may reject a pillar that would genuinely help on live data but
   that no synthetic control exposes; the alternative risks the exact
   forking-paths/selection-bias problem this report exists to avoid.

5. **Does Stream 1 or Stream 6 hold the pen on the synthetic-overlap
   calibrate/score experiment?**
   *Default (adopted in this revision):* Stream 6 owns the estimand,
   stopping rule, and artifact in full; P1-09 is a dependency-edge record
   only (§3, §6). *Tradeoff:* this removes the prior ambiguity between
   "own-and-run" and "cross-reference-and-defer" patterns, matching how
   P1-05 already treats Stream 5 — but Max should confirm Stream 6's owner
   agrees P1-08 may block on their freeze date, since that is a new
   cross-stream commitment this revision introduces.

---

## References

Primary sources first; every secondary source is explicitly labeled.

1. **[Primary]** Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T.
   (2018). "The preregistration revolution." *Proceedings of the National
   Academy of Sciences*, 115(11), 2600–2606.
   https://www.pnas.org/doi/10.1073/pnas.1708274114
2. **[Primary]** Gelman, A., & Loken, E. (2013). "The garden of forking paths:
   Why multiple comparisons can be a problem, even when there is no 'fishing
   expedition' or 'p-hacking' and the research hypothesis was posited ahead of
   time." Columbia University working paper (condensed in *American
   Scientist*, 2014).
   https://sites.stat.columbia.edu/gelman/research/unpublished/Forking_paths.pdf
3. **[Primary]** Cawley, G. C., & Talbot, N. L. C. (2010). "On Over-fitting in
   Model Selection and Subsequent Selection Bias in Performance Evaluation."
   *Journal of Machine Learning Research*, 11, 2079–2107.
   https://www.jmlr.org/papers/v11/cawley10a.html
4. **[Primary]** Dwork, C., Feldman, V., Hardt, M., Pitassi, T., Reingold, O.,
   & Roth, A. (2015). "The reusable holdout: Preserving validity in adaptive
   data analysis." *Science*, 349(6248), 636–638.
   https://pubmed.ncbi.nlm.nih.gov/26250683/
5. **[Primary]** Blum, A., & Hardt, M. (2015). "The Ladder: A Reliable
   Leaderboard for Machine Learning Competitions." *ICML 2015* /
   arXiv:1502.04585. https://arxiv.org/abs/1502.04585
6. **[Primary]** Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J.
   (2017). "The Probability of Backtest Overfitting." *Journal of
   Computational Finance*, 20(4), 39–70 (SSRN preprint 2014, id 2326253).
   https://doi.org/10.21314/JCF.2016.322 ;
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
7. **[Primary]** Arian, H. R., Norouzi Mobarekeh, D., & Seco, L. A. (2024).
   "Backtest overfitting in the machine learning era: A comparison of
   out-of-sample testing methods in a synthetic controlled environment."
   *Knowledge-Based Systems*, 305, art. 112477.
   https://doi.org/10.1016/j.knosys.2024.112477
8. **[Primary, working paper]** Schnaubelt, M. (2019). "A comparison of
   machine learning model validation schemes for non-stationary time series
   data." FAU Discussion Papers in Economics, No. 11/2019.
   https://www.econstor.eu/handle/10419/209136
9. **[Primary, repo-internal]** `docs/*NEXT/Montauk 3.0/validation-engine-
   hardening.md`, §§1b, 2a–2b, 3d–3e (Phase 1 mandate, G1–G19 gap register,
   Phase 1 validation-stack experiment design).
10. **[Primary, repo-internal]** `docs/*NEXT/Montauk 3.0/implementation-
    plan.md`, "Phase 1 — prove the exam and authority contract."
11. **[Primary, repo-internal]** `docs/*NEXT/Montauk 3.0/decisions.md`, D43,
    D45–D50, D57 (five-plank contract, guiding light, rolling/named-moment
    design, evidence sufficiency, false-Gold frontier, simple-language
    ratification protocol).
12. **[Primary, repo-internal]** `docs/*NEXT/Montauk 3.0/charter.md`, §2.3
    (priority order and false-Gold/false-reject asymmetry), §4.1–4.2 (Gold
    meaning and evidence roles).
13. **[Primary, repo-internal]** `data/TECL.csv`, `data/manifest.json` —
    verified directly: 4,401 of 8,338 rows real-labeled, spanning
    2008-12-17 to the current data pull (~17.5 years).
14. **[Primary, repo-internal]** `docs/*NEXT/Montauk 3.0/research/6-Synthetic
    TECL reconstruction/synthetic-tecl-reconstruction.md` — owning document
    for P1-09's dependency edge.
15. **[Secondary, cited only to locate primaries]** Search-result summaries
    and abstract-fetch tools used to confirm bibliographic details above; no
    numeric claim in this report rests on a secondary summary alone.

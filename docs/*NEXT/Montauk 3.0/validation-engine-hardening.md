# Montauk 3.0 — The Validation Engine (North Star) + Hardening Plan

**Status: REQUIRED PHASE 1 IMPLEMENTATION PILLAR / CHARTER-SUBORDINATE (opened
2026-06-17; owner contract updated 2026-07-21).** This document owns the research,
control experiments, and evidence needed to freeze the five-plank Gold exam. It
cannot change the product, Gold promise, or authority policy in
[charter.md](charter.md). The audit below is
**design-level** (what is covered, what is missing, measured against the
anti-overfitting literature). Existing-script findings are logged in
[validation-audit-findings.md](validation-audit-findings.md), but completing a
line-by-line audit of code that will be discarded is not a 3.0 prerequisite. G10
applies to every validation method and implementation actually retained or
rewritten for the final five-plank exam.

---

## 1. Why this is the north star

Owner's intended outcome: by the end, any Gold strategy is **defensible,
auditable, testable**, and trustworthy enough to use without re-litigating the
pipeline. In Max's governing plain language, Gold should provide the strongest
honest assurance available from current scholarship, market expertise,
AI-assisted research, independent review, reproducible evidence, and Montauk's
own calibrated controls that the exact strategy is not detectably overfit and
should outperform matched TECL B&H when actually followed. This does **not** mean
“every validation we can think of.” It means the smallest complete set of
independently justified checks that covers Montauk's actual failure modes.

The bucket and the search exist to **feed** the validation engine. The whole
machine's credibility reduces to that engine's rigor: if it lets one overfit
strategy through, the leaderboard stops being a certification and becomes a
watchlist. So the validation engine—not the optimizer or the number of
configurations—is the thing that has to be bulletproof. Bulletproof means
correct, calibrated, and understandable; it does not mean long.

**The standing standard.** A Gold strategy must survive the scrutiny of a
skeptical quant professional or an academic referee: frozen and versioned logic,
full adaptive-search accounting, selection correction wherever adaptive choice
can inflate evidence,
chronology-respecting reconstructed evidence, correctly attributed untouched
live-forward evidence, reproducible artifacts, independent re-implementation,
and honestly stated uncertainty—including what the data cannot support.

### 1a. The complete Gold exam fits on one slide

| Plank | One question |
|---|---|
| Correctness | Are the data, signals, fills, trades, and artifacts causal and reproduced correctly? |
| Economic passage | Does the strategy beat matched TECL B&H by the required real-data margin with sufficient evidence? |
| Generalization | Does the frozen logic survive time, parameter, event-concentration, and execution stresses that were not chosen to flatter it? |
| Search honesty | Is the result still exceptional after Montauk's complete adaptive search and dependence are counted? |
| Reproducibility/currentness | Can the exact row be rebuilt cleanly, and is it still current under forward monitoring? |

Every Gold configuration passes all five. Each plank emits one verdict and one
plain-English explanation. Technical methods sit beneath a plank; they are not
additional product stages or owner-facing scores.

A proposed method is mandatory only after Phase 1 proves its relevance,
assumptions, implementation parity, incremental information, power, and false-
rejection behavior on controls. A fashionable method that is invalid at
Montauk's sample size is worse than omitting it honestly. PBO/CSCV, SPA/Reality
Check, bootstrap, walk-forward, sensitivity analysis, and every other named
technique are candidate instruments—not articles of faith.

### 1b. Owner contract ratified through Questionnaire 5 on 2026-07-21

Max reported that technical language was often unclear. His plain-language goal
therefore outranks an inferred preference for any named statistical method.
Accepted owner-visible outcomes are fixed below; blank or tentative method
answers do not create new policy and must earn any role through Phase 1 controls.

- Gold is Montauk's highest **versioned process and evidence certification**, not
  a guarantee of any future call or return. An empty Gold board is an honest
  result.
- Every configuration faces every mandatory evidence plank regardless of author,
  simplicity, compute cost, or expected result. Missing, skipped, underpowered,
  incomplete, or unverifiable required evidence blocks Gold. A structurally
  inapplicable algorithm needs a predeclared equivalent or valid
  `not_applicable` treatment; no origin-based tier or silent renormalization
  remains.
- Montauk Score ranks only configurations that passed all hard planks. The
  evidence-strength composite is named **Validation Score**, not a confidence
  percentage, until a frozen forward outcome and reliability study justify a
  probability interpretation.
- Universal gates do not erase adaptive selection. The agent's proposals,
  cheap-screen rejects, configurations, campaigns, feedback cycles, and
  board/lifetime comparisons remain observable. Correction must model effective
  dependence; it may neither treat every near-twin as independent nor erase
  legitimate exact configurations.
- Economic eligibility uses matched TECL B&H across complete real history, a
  fixed trailing-five-year horizon, and a small predeclared rolling/window
  design. Complete history and trailing five years are hard gates; Phase 1
  calibrates an aggregate rolling rule plus a catastrophic-window veto. The
  point-estimate margin begins from Max's provisional 1.10 intuition, while an
  uncertainty-aware lower bound must exceed 1.0 or return insufficient evidence.
- The primary economic result is terminal deployable TECL wealth/share multiple
  versus matched B&H. Daily net log-wealth differences support inference; path,
  risk, and trade metrics remain explanations.
- Synthetic history is diagnostic and never substitutes for real passage. Its
  current model and any weight/catastrophic veto require independent overlap and
  model-error calibration. Extend the XLK-based transformation through observed
  TECL, calibrate only on earlier overlap blocks, and test later blocks without
  refitting so the model is not graded on the same full period that tuned it.
- Gold observes the verified official daily close and models execution at the
  next regular-session open plus calibrated slippage and fees. Max will submit
  the manual order after close for that opening execution. Same-close and other
  OHLC fills are stress/diagnostic outputs. Costs come from market evidence and
  are calibrated across a fixed $10,000–$100,000 modeled order band. 3.0 does
  not collect Max's actual fills, balance, or order sizes.
- The primary account is tax-advantaged, tax modeling is out of scope, risk-off
  cash earns zero, and SGOV is not a 3.0 strategy leg.
- Nested rolling-origin reconstruction is required. Phase 1 selects expanding or
  fixed rolling training windows and evaluates CPCV alongside the chronological
  spine; CPCV becomes a hard applicable gate only if its target, assumptions,
  power, and incremental protection are established.
- Purge/embargo lengths derive from actual information, label, and holding-
  outcome intervals. A revealed historical holdout is spent/reused evidence,
  never a permanent untouched lockbox; only post-freeze row-specific bars are
  untouched for that exact row.
- Backtest/B&H passage precedes the expensive validation suite. Candidate-code
  containment and correctness preflight precede execution.
- A historical-suite survivor joins the one Gold leaderboard with activation
  status `Pending Gold`, normally accumulates 20 verified bars, and must pass a
  fresh certification before it can be Recommended or Active. Only the latest
  compatible contract appears on the current board; no legacy grandfathering.
- The validator must measure both false-Gold and false-rejection behavior. A
  validator that rejects everything is not robust merely because it is strict.
- There is no universal minimum trade-count cliff. Evidence sufficiency follows
  effective decisions/regimes, uncertainty, and method power.
- Gold decisions publish automatically once per day from a frozen survivor
  cohort plus complete search-ledger snapshot. Epochs inherit lifetime
  disclosures and may share one immutable search-honesty artifact across rows.
- The false-Gold control study reports a whole-appliance annual risk/recovery
  frontier; 1% probability of any false Gold is an aspirational reference that
  Max will ratify or revise after seeing the false-rejection cost.
- Exact ranks remain visible, with a calibrated `leader not clearly separated`
  status when the leading evidence is indistinguishable.
- Automation cannot change the validator, thresholds, weights, data/execution
  contract, or evidence rules. A signed Max-authorized core release creates new
  version identities and immediately stales incompatible certifications for
  urgent recertification.
- Independent reimplementation, adversarial review, primary-source verification,
  and controls are mandatory; an outside paid/credentialed human reviewer is not
  a 3.0 gate.

**Trust boundary.** No existing legacy Gold label earns this promise. Complete
trust in a future call is impossible; operational trust in the 3.0 process is the
goal. That trust is not justified until the five-plank contract, the validator's
own control study, clean reproduction, and forward monitoring have all passed and
no legacy row has been admitted without recertification from scratch. Rebuilding
every old row is not a 3.0 prerequisite.

---

## 2. Where the exam sits

```
 ideas/specifications -> cheap screen -> full backtest -> remaining validation
                                           |                   |
                                  economic passage       other four planks
                                           +---------+---------+
                                                     v
                                      Gold board + forward monitoring
```

The final certificate reports all five planks. The drawing separates when they
are decided so “backtest” and “Gold exam” do not become duplicate performance
tests.

**The asymmetry that matters:** Ideation and backtesting *generate* (and Montauk
3.0 makes them enormously more powerful—auto-enter, continuous feedback,
billions of configurations). The Gold exam is the **adversary**. As the number of
effectively independent opportunities to get lucky rises, the multiplicity
burden must rise with it. Raw counts of highly dependent near-twins do not
automatically equal independent trials, and unrelated evidence planks do not
become arbitrarily stricter merely because throughput improved. A more powerful
search without honest dependence-aware correction manufactures false Gold; a
naïve raw-count penalty can manufacture false rejection. This balance is the
central design law of the machine.

### 2a. Backtest truth comes before anti-overfit statistics

No resampling method can rescue a backtest whose chronology, comparator, or fill
is wrong. Before Phase 1 compares statistical methods, one small executable
contract must freeze:

| Contract item | Required truth |
|---|---|
| Information clock | Every feature value has a point-in-time source and the engine can replay any historical prefix without later bars changing an earlier decision. |
| Signal and fill | Form the signal only after the official daily bar is verified; Max submits the manual order after close; certify at the next regular-session open plus calibrated slippage/fees derived from market evidence across a fixed $10,000–$100,000 modeled order band. Same-close and other OHLC conventions are diagnostic stresses. Actual account balance and order size are neither inferred nor tracked. |
| Matched comparator | Adjusted total-return TECL B&H uses the same eligible start, initial capital, first obtainable purchase timing, cost convention, and unrounded arithmetic. |
| Account/risk-off scope | The primary account is tax-advantaged; no tax model enters Gold. Risk-off cash earns zero and no SGOV leg is traded in 3.0. |
| Primary outcome | Exact terminal deployable TECL wealth/share multiple versus matched B&H. Retain daily net log-wealth differences for inference; CAGR, drawdown, Sharpe, and trade statistics are supporting views, never substitute Gold targets. |
| Reproduction | A second implementation reproduces signals, fills, daily P&L, trades, and the final verdict from immutable inputs and version stamps. |
| Failure behavior | Missing data, impossible prices, non-finite arithmetic, nondeterminism, and parity differences fail closed and produce an artifact, never a silent fallback. |

The leading economic representation is an exact terminal wealth/share multiple
versus matched B&H, with the daily net log-wealth difference retained for
inference and diagnosis. A ratio of two rounded CAGRs should not decide Gold.
Where path uncertainty is simulated, Phase 1 should reconstruct price paths and
rerun the full causal strategy—not merely resample already-realized strategy
trades or daily P&L when doing so would break the indicator and position logic.

Daily observations are not automatically independent observations. A strategy
that holds one position for months may have thousands of daily rows but only a
small number of distinct decisions, trades, or regimes. Every inferential method
must use a dependence model and report the effective evidence it actually has.

### 2b. “Walk-forward” names four different experiments

Calling all historical partitions “out of sample” creates confidence the data do
not support. Montauk must store and display the evidence type, not only a generic
`walk_forward_pass` flag.

| Evidence type | Construction | What it can show | What it cannot honestly claim |
|---|---|---|---|
| **Frozen historical replay** | Run today's exact frozen configuration on predeclared old eras/windows with no refit. | Time/event concentration, historical degradation, and dependence on a particular interval. | Untouched evidence, if the family or parameters were invented after seeing any of those dates. |
| **Nested rolling-origin reconstruction** | At each historical origin, define/search/select using only the prefix, freeze the winner, then evaluate the next block; repeat. | Whether the **family plus selection procedure** would have generalized when operated through time; expanding and rolling training windows can be compared. | Proof about today's exact row, or untouched evidence for a family designed using the later full history. |
| **Sealed or reused certification period** | Withhold a final block from a campaign and reveal it only after selection. | A one-time check before the result is revealed. | A permanent lockbox. Pass/fail, rank, and metrics become adaptive feedback once the agent or owner sees them; repeated querying spends the holdout. |
| **Per-row live forward ledger** | Accumulate bars only after exact code, parameters, data contract, and certification identity were frozen. | The only genuinely untouched market evidence for that exact row. | A fast guarantee: twenty quiet bars with no signal transition may contain almost no evidence about the mechanism. |

**Purging and embargo are conditional leakage controls, not ritual gaps.** Purge
training observations whose label/outcome intervals overlap a test interval.
Add an embargo only for a specified residual information path or dependence
horizon. A feature lookback crossing a fold boundary is not itself leakage when
those past values would really have been available at the decision time; using a
future outcome, revised value, or overlapping holding-period label is. The gap
must therefore derive from each feature/label contract rather than a copied
percentage. Use a zero gap when no overlap path exists. If a family requires an
interval that intake cannot calculate exactly, that family is invalid rather
than eligible for a guessed safety gap.

**CPCV is not “better walk-forward” in every sense.** Combinatorial purged cross-
validation can create many purged train/test combinations and a useful
distribution of results, particularly for trained models with overlapping
labels. Some combinations train on blocks that occur after an earlier test
block, however, so CPCV is not a replay of what Montauk could have known at that
date and it does not manufacture new regimes. The 2024
[Arian–Norouzi–Seco study](https://doi.org/10.1016/j.knosys.2024.112477) found
CPCV superior to walk-forward under its synthetic/ML experiment and S&P
500 application; [Schnaubelt's 2019 study](https://www.iwf.rw.fau.de/files/2019/11/11_2019.pdf)
found chronology-preserving forward validation preferable under several kinds
of non-stationary evolution and also showed that the result changes with the
data-generating dynamics. Phase 1 must therefore compare them on Montauk's own
low-trade controls rather than crown either method from one paper.

**Ratified direction; exact design pending calibration.** Nested rolling-origin
reconstruction is the required chronological spine because it matches the
intended live research process. Phase 1 compares expanding and fixed rolling
training windows and evaluates CPCV alongside that spine. The preferred outcome
is to retain both, but CPCV becomes a hard applicable gate only when Montauk can
define what it tests, derive any necessary purge/embargo, demonstrate adequate
power, and show incremental false-Gold protection on controls. Otherwise a
predeclared equivalent or valid `not_applicable` result is more honest than a
ceremonial “pass.” Neither method substitutes for the immutable per-row live-
forward ledger.

---

## 3. Legacy lessons—not a required 3.0 architecture

The current scripts may be rewritten. Their value here is evidence about failure
modes, tests worth investigating, and complexity not to carry forward. 3.0 does
not have to preserve their gates, weights, tiers, scores, or file boundaries.

**Legacy headline:** the engine contains an advanced set of anti-overfitting methods and
maps to serious literature (López de Prado / Bailey et al., Politis-Romano,
Morris), but its certification claim is **provisional**. The correctness audit is
incomplete, breadth and board-level multiplicity gaps are structural, the
validator's own weights need governance, and live-forward attribution must be
per frozen row. “Professional-grade” is an acceptance target, not a current
finding.

### 3a. Research-corpus quality verdict

The material under `docs/research`, the Elicit PDF, the separate eight-row Elicit
CSV, `docs/research/research_rd2/sources.rtf`, and its ten-item APA export were
reviewed as leads, not accepted as specifications.

| Artifact | Audit finding | Proper use |
|---|---|---|
| Elicit overfitting report | It says 50 papers were screened, 10 included, and only five had full text; an LLM extracted the comparison fields. Its prose turns context-specific study choices into recommendations too readily. | Search index and terminology map. Verify every consequential claim in the underlying paper. |
| Eight-row Elicit CSV | Four rows are relevant research summaries; one is the attached report and three are credential websites. It does not support a complete validation design. | Provenance for the narrow initial scan only. FRM/CQF/CMT are unrelated to strategy certification. |
| Round-2 RTF source dump and APA export | The RTF's 50 results mix directly relevant quant papers with generic ML, clinical, vulnerability-detection, and broad survey material. The APA export narrows that to ten algorithmic-trading papers but still mixes established evidence, context-specific applications, and 2026 low-evidence proposals. Neither documents an applicability or quality screen. | Candidate bibliography to triage by failure mode, evidence quality, and TECL applicability. |
| Earlier AI reports | Several reports reuse the same small group of papers and then propose different thresholds, weights, and composite scores. Repetition across AI summaries is not independent corroboration. | Problem inventory. Do not import a number merely because several generated reports repeat it. |

The corpus is directionally right about chronology, multiple testing, parameter
fragility, costs, and live deterioration. It does **not** justify universal
cutoffs such as 50 trades, PBO at either 0.05 or 0.40, a fixed walk-forward
efficiency, fixed degradation percentages, fixed fragility/HHI values, or a
particular composite weight. For example, the 2026
[GT-Score paper](https://doi.org/10.3390/jrfm19010060) calls its 50-trade rule a
practical default for stabilizing its own heuristic Z-score; it is not a theorem
that 49-trade TECL evidence is invalid and 50 trades is sound. Likewise, the
reported 73% median Sharpe deterioration in 215
[bank-marketed alternative-beta strategies](https://doi.org/10.3905/jpm.2017.43.2.090)
and the weak Sharpe prediction in 888
[Quantopian algorithms](https://doi.org/10.3905/joi.2016.25.3.069) are important
warnings from different populations—not Montauk Gold thresholds.

The 2026 [Kac Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6827500)
and [AlgoXpert](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6303279)
papers are new research leads, not foundations for Gold. The former is a novel
Sharpe-times-equity-linearity ranking tested on 600 futures strategy
combinations; the latter is a recent preprint demonstrated on one intraday
USDJPY case and four variants. Covariance-penalty and Bayesian methods deserve
control-study candidates, but their regression/Sharpe/model assumptions do not
automatically cover arbitrary TECL rule families. The two-month 2022
cryptocurrency reinforcement-learning test and FX/intraday studies are too
context-specific to set Montauk policy.

No numerical rule from this corpus enters the contract until the Phase 1 control
study measures its false-Gold, false-reject, power, and incremental behavior for
Montauk. The source lists remain a hypothesis inventory; primary papers and
reproducible controls are the evidence.

### 3b. Candidate-method adjudication

The literature does support a **stack of distinct protections**. “Stack” means
orthogonal failure modes under the five planks, not a serial parade of every
named test.

| Method or evidence | Potential Montauk role | Current disposition |
|---|---|---|
| Causal prefix replay, engine parity, obtainable fills, matched B&H | Establish that the claimed backtest is real. | **Mandatory correctness/economic foundation.** |
| Nested rolling-origin reconstruction | Test the family plus search/selection procedure under production chronology. | **Required chronological method; Phase 1 calibrates expanding versus fixed rolling windows and power.** |
| Purged K-fold / CPCV / embargo | Remove actual label overlap and measure selection stability across multiple partitions. | **Required Phase 1 evaluation; hard Gold role only when scientifically applicable and incremental.** Purge/embargo comes from declared intervals; use a valid equivalent/N/A rather than a ritual gap or invalid CPCV pass. |
| White Reality Check, Hansen SPA, Romano–Wolf step-down | Test performance versus the benchmark after a broad, dependent search. | **Leading search-honesty candidates.** Select the smallest valid campaign/board design. |
| CSCV/PBO | Estimate rank reversal/overfit behavior of a predeclared selection universe. | **Supplementary candidate.** It must use the actual searched alternatives/selection rule, not a convenient random neighborhood or only the final top rows. |
| DSR/PSR/Minimum Track Record Length | Adjust or qualify Sharpe-ratio evidence. | **Conditional only if Sharpe has a declared decision role.** They cannot be relabeled as a deflated Montauk Score or a general probability of Gold. |
| Stationary/block bootstrap | Put uncertainty around a statistic under an explicit dependence/stationarity approximation. | **Candidate uncertainty instrument, not regime proof.** Resampling returns cannot create new market regimes and may break level-dependent indicator mechanics. |
| Parameter perturbation plus signal/trade fingerprints | Detect isolated optima and whether nearby parameters express genuinely similar behavior. | **Required evidence representation; Phase 1 calibrates the hard robustness rule.** Many parameter points producing the identical trade path count as redundancy, not independent robustness. |
| Morris/Sobol sensitivity | Identify which inputs drive output variance and reduce search dimensions. | **Research/search diagnostic, not a probability of overfitting.** |
| Event concentration and regime views | Expose reliance on a crash, rally, or hand-labeled interval. | **Plain-English diagnostic; veto only if a predeclared calibrated catastrophic rule earns it.** |
| Synthetic TECL and other assets | Stress mechanisms outside observed TECL history. | **Diagnostic only in 3.0.** Correlated assets and modeled history are not independent TECL evidence. |
| Model Confidence Set | Express when several leaders may be statistically indistinguishable. | **Ranking diagnostic candidate, not the board-wide multiplicity fix.** Published financial simulations warn it may need very high signal-to-noise and is not robust to multiple testing. |
| Twenty post-certification bars | Operational cooling, replay monitoring, and time for obvious defects to surface. | **Activation policy, not statistical proof by itself.** Report state transitions/trades/regimes separately from elapsed bars. |

At scale, search honesty is necessarily **cohort evidence**, not a billion copies
of a row-local test. An exact Gold row should reference an immutable shared
family/campaign/board correction artifact plus its own correctness, economic,
generalization, and forward artifacts. Behaviorally identical siblings may all
remain rows, as Max requested, without pretending each is an independent
discovery or rerunning the same expensive correction thousands of times.

### 3c. What's already strong (mapped to the literature)

| Capability | File | Literature anchor |
|---|---|---|
| Engine integrity — executed lookahead / repaint / overlap / bar-close-fill checks (not self-reported flags) | `validation/integrity.py` | no-lookahead correctness |
| Golden-regression net + shadow comparator vs `backtesting.py` / `vectorbt` | `tests/test_regression.py`, `test_shadow_comparator.py` | independent re-implementation cross-check |
| **CSCV / Probability of Backtest Overfitting** (logit λ, degradation slope, candidate OOS-top-half prob) | `validation/pbo.py` | Bailey, Borwein, López de Prado & Zhu (2017) |
| Selection-bias **deflation** — expected-max Beta EVT + Monte-Carlo null + **measured N_eff** (ratcheted) | `validation/deflate.py` | López de Prado expected-max-Sharpe / deflated performance |
| Historical rolling-origin re-optimization, kept distinct from frozen replay | `validation/oos_walk_forward.py` | candidate reconstruction method; it is not untouched evidence if the family was designed with later history |
| **Stationary bootstrap** confidence intervals | `validation/uncertainty.py` | Politis & Romano (1994) |
| **Morris elementary-effects** global parameter sensitivity | `validation/uncertainty.py` | Morris (1991) |
| Execution realism (next-open fills, −15% budget) | `validation/reality_check.py`, gate_realism | implementation-shortfall realism |
| Event-dependence splicing (single-event edge collapse) | gate_realism | robustness to one-regime edges |
| Regime / return concentration (HHI, clustering) | `validation/sprint1.py` | Herfindahl-Hirschman concentration |
| **Active-system live-forward holdout + demotion/calibration scaffolding** | `ops/live_holdout.py`, `validation/confidence_v2.py` | valuable foundation; per-frozen-row attribution and sufficiency rules remain G11 |

The live-forward layer can become the most valuable evidence in the system, but
only after each observation is attributed to the exact frozen code, parameters,
and certification vintage that generated it.

### 3d. Method/research backlog—not nineteen Gold gates

The register below decomposes research risk so nothing is forgotten. It must not
be implemented as nineteen sequential services, nineteen UI lights, or a score
for every row. Phase 1 resolves each item into one of four outcomes: part of one
of the five planks, diagnostic-only, fixed outside the validator, or removed.

| # | Gap | Why it matters | Severity | Fix direction |
|---|---|---|:-:|---|
| **G1** | **Generation-breadth multiplicity.** Current N_eff accounting is blind to some authored families, cheap-screen rejects, adaptive batches, and board/lifetime selection. With continuous feedback-driven generation, P(some family reaches Gold by luck) rises even when individual rules look simple. | This is the price of the whole “huge bucket” vision. Unfixed, scaling generation silently manufactures false Gold. | **Critical** | Record every observable selection event and configuration actually evaluated; specify within-family, campaign, and board/lifetime correction. |
| **G2** | **No board-level multiple-testing test.** Legacy PBO covers a random candidate neighborhood; nothing asks "is the best-of-the-whole-board genuinely better than benchmark, given the full set tried?" (`reality_check.py` is fills, not the test of the same name.) | Each row is deflated for *its* search; the *board* is the max over thousands of pipeline runs and is not FWER/FDR-controlled. | **High** | Compare White's Reality Check, Hansen's SPA, Romano-Wolf step-down, or another dependence-aware design on Montauk controls; select the smallest valid approach rather than stacking named tests. |
| **G3** | **Data-scarcity ceiling.** ~3–4 independent macro regimes, <20 trades, ~53 params on the champion; real-era multiple ~1.0–1.3×. No statistical method manufactures degrees of freedom that are not in the data. | The validator can be flawless and forward uncertainty can still be wide. Pretending otherwise is the dishonest failure mode. | **Structural (unfixable by math)** | Surface CIs, trade count, independent-regime count, and minimum track record. More elapsed untouched TECL history is the direct cure; other assets may add context but are not equivalent TECL forward evidence. |
| **G4** | **The validator's own free parameters.** 14 sub-score weights + every anchor are hand-set, and some were tuned to the *current* candidate pool (the `era_consistency` anchor note says so explicitly). | A validator fit to today's candidates is itself overfit — it grades the test it wrote. | **High** | Freeze + version the validator config; sensitivity-test verdicts against weight/anchor perturbation; **never** tune anchors toward the current pool. |
| **G5** | **Calibration thinness.** Live holdout began 2026-05-01 (~6 weeks); the confidence→forward-survival model trains mostly on *simulated* vintages. | The calibration that makes Conviction "honest" is not yet itself validated forward. | **Medium (time-healing)** | Keep accumulating; label calibration provisional; report calibration sample size alongside every Gold claim. |
| **G6** | **Small-sample power.** Bootstrap / regime / PBO computed on 15–19 trades have wide CIs and low power. | Many sub-scores are noisier than their single number implies; a universal 50-trade rule would only hide the issue. | **Medium** | Report uncertainty width, effective observations, power, and insufficiency explicitly. Evaluate Sharpe-specific Minimum Track Record Length only if its assumptions and decision role fit; do not install an imported trade-count cliff. |
| **G7** | **PBO scale + selection universe.** M=32 random parameter draws and 16 blocks do not represent the configurations or adaptive rule that produced the candidate. | PBO is about selection/rank reversal across a model universe; a convenient neighborhood can answer the wrong question. | **Medium** | Reconstruct the actual predeclared family/campaign selection matrix and test whether PBO adds information beyond the search-wide method at Montauk's sample size. Do not run it only on an already-selected top subset. |
| **G8** | **Point-in-time macro data.** FRED series (T10Y2Y, DFF, 3m T-bill) are *revised*; if revised values stand in for what was knowable historically, that's subtle lookahead. | A defensible-to-academics claim must rule out revision lookahead. | **Verify** | Confirm vintage / as-released macro data, or document the assumption explicitly. |
| **G9** | **Minimum Track Record Length** not computed. | It may provide a compact statement of how much history an estimated edge would require, but it must not become another impressive number without a valid role. | **Candidate method** | Evaluate MinTRL against Montauk's objective and sample size; keep it only if assumptions and incremental decision value pass Phase 1. |
| **G10** | **Final retained-method correctness audit not yet possible.** The legacy `deflate.py` review found real issues, but auditing files that will be discarded does not prove the rewritten exam. | "Auditable" requires every method that actually affects Gold to have been checked against its frozen specification and controls. | **Process** | After Phase 1 selects methods, independently audit each final implementation and parity fixture; use the legacy findings log only where relevant. |
| **G11** | **Forward evidence is not yet an immutable per-row record.** An active-system stream can be relabeled when the champion changes, and repeated recertification on unchanged data can be mistaken for new evidence. | Evidence after one frozen version's certification belongs only to that version; reproducibility reruns do not create new market evidence. | **Critical contract** | Key observations by frozen strategy/configuration/certification ID; separate replay, renewal on new bars, and re-optimization; define sequential/hysteresis rules. |
| **G12** | **Gold execution policy and modeled scale are decided; numerical costs and comparator fixtures are not yet calibrated.** Signal-after-verified-close/manual-next-open and the $10,000–$100,000 modeled order band are fixed, but slippage, fees, B&H dates/distributions, and parity artifacts still need proof. | A statistically strong result under an impossible fill is not fit to trade. A rounded point estimate barely above 1.0 is weak evidence of superiority. | **Critical implementation** | Implement the fixed next-open workflow net of market-calibrated costs across the modeled band, matched B&H, terminal relative wealth/share multiple, and a lower bound above 1.0; keep close-fill as diagnostic. Do not require personal fill, balance, or actual-order-size logging. |
| **G13** | **Composite/gate semantics may not match “passes every validation.”** Skipped/missing dimensions can be renormalized, warnings may not affect verdicts, and weighted strength can offset a failed plank. | A score is not a probability and cannot rescue absent mandatory evidence. | **High** | Define mandatory minima and explicit `not_applicable` equivalents; fail Gold on missing/unverifiable required evidence; label uncalibrated composite values as scores, not probabilities. |
| **G14** | **The validator's false-positive and false-negative operating characteristics are unmeasured.** Passing known defects and rejecting valid controls are both possible. | “Stricter” can hide a powerless or biased grader just as easily as a permissive one. | **Critical evidence** | Build a validation-of-validation harness with randomized nulls, seeded leakage/overfit defects, simple frozen controls, simulation, power reporting, and per-row forward outcomes. Freeze expected sensitivity/specificity ranges per contract version. |
| **G15** | **Synthetic TECL diagnostic validity is not independently calibrated.** The builder is reproducible, but its index/ETF proxies, leverage model, expenses, seam, and financing haircut are not equivalent to observed TECL behavior. | An uncalibrated synthetic vote or veto can create false confidence or reject a sound real-era strategy. | **High** | Extend the frozen XLK transformation through observed TECL; calibrate assumptions on earlier overlap blocks and test later blocks without refitting; quantify daily-return bias, tracking error, volatility, terminal path, drawdowns, expenses/financing error, and event behavior; version every assumption; permit a weight/veto only after this time-separated review. |
| **G16** | **Recent/rolling structure is decided; its aggregate, veto, and demotion rules remain uncalibrated.** Complete observed history and trailing five years are hard gates, but a hand-picked rolling exam can still manufacture passage or rejection. | Retrospective windows manufacture robustness; excessively many correlated windows can make Gold impossible without adding independent evidence. | **Critical calibration** | Freeze a small rolling design; calibrate its aggregate/catastrophic rules, provisional 1.10 point margin, lower bound above 1.0, and two-renewal warning/demotion behavior on controls. |
| **G17** | **External-input point-in-time contracts are incomplete.** 3.0 may use VIX, volume, options, related assets, macro series, and idiosyncratic components while trading TECL only. | Revision, publication-lag, same-bar, survivorship, timezone, and missing-data mistakes can create invisible lookahead. | **High** | Require a versioned source registry with provenance, publication/market timestamp, revision policy, missing semantics, and causal feature APIs; verify with prefix replay and as-of fixtures. |
| **G18** | **Adaptive-reuse policy is decided; its lifetime accounting still needs a proven implementation.** The agent studies prior failures and verdicts, so every revealed holdout result can shape later families even when later code never reads the holdout directly. | Repeated pass/fail queries eventually fit the examiner. A permanent static lockbox is incompatible with an unlimited feedback loop. | **Critical implementation** | Store the four evidence types in §2b; log every reveal; publish from daily frozen certification cohorts; carry lifetime history forward; evaluate a formally reviewed reusable-holdout design only if needed; call only post-freeze per-row bars untouched. |
| **G19** | **Parameter plateaus can be behavioral duplicates.** Wide numeric neighborhoods may all emit the same sparse TECL signals/trades. | Counting identical behavior as many corroborating variants inflates both apparent robustness and search breadth. | **High** | Hash signal, position, and trade paths; report numeric coverage separately from behavioral diversity; use behavioral clusters when estimating dependence and robustness. |

### 3e. Phase 1 experiment that chooses the validation stack

Phase 1 must test the validator as an end-to-end **selection system**, not tune a
list of thresholds against the current leaderboard.

1. Freeze the decided terminal relative-wealth objective, next-open execution/
   comparator contract, candidate methods, decision roles, and target operating
   characteristics before looking at evaluation results. Max must ultimately
   choose the acceptable whole-appliance false-Gold/false-reject tradeoff after
   seeing the frontier; plot the aspirational 1% annual any-false-Gold reference.
2. Build several control worlds rather than pretending one simulator is truth:
   dependence-preserving null returns; exposure/trade-count-matched random
   long/cash rules; high-dimensional noise families searched over many
   configurations; event/date memorizers; intentional lookahead/repaint and fill
   defects; simple frozen structural controls; and synthetic worlds with a
   planted, recoverable signal.
3. Run the **entire** author/search/select/backtest/validation procedure on those
   controls. Testing only a preselected winner understates the false-discovery
   problem Montauk actually creates.
4. Compare an expanding nested rolling-origin spine with a fixed rolling-window
   variant. Evaluate CPCV alongside them wherever it has a defined target; derive
   purge/embargo from actual intervals and include a no-overlap/equivalent path.
   Judge alternatives by board-level false Gold, false rejection of planted
   signals, bias/variance of future-performance estimates, rank stability,
   useful power, and compute—not by whichever preserves the current champion.
5. Compare White/SPA/Romano–Wolf-style search-wide correction and any PBO/DSR
   supplement on the same controls. Explicitly test massive correlated near-
   twins, diverse families, and adaptive feedback across campaigns.
6. Ablate one method at a time. A method stays only if it catches a relevant
   defect missed elsewhere or materially improves calibration without an
   unacceptable false-reject or complexity cost.
7. Tune provisional values on calibration controls, lock a validator version,
   and evaluate it once on separate control worlds. Current and historical
   leaderboard rows are not threshold-training data.
8. After launch, compare every frozen verdict with its immutable live-forward
   ledger. Recalibration is a Max-authorized new contract version, never an
   autonomous reaction to an inconvenient outcome.

Separately, run the owner-required synthetic overlap experiment: extend the
XLK-based transformation through real TECL history, calibrate on earlier rolling
overlap blocks, and score later blocks without refitting. The report must compare
modeled and actual return paths, bias, tracking error, volatility, drawdowns,
financing/expense error, and named moments, with uncertainty stated plainly.

Every safety- or evidence-critical step receives at least one positive fixture,
one negative/seeded-defect fixture, a deterministic expected result, and a
retained acceptance artifact. “The complete pipeline passed” cannot hide an
untested internal step.

Future literature work begins with a named Montauk gap and ends with a testable
consequence. A broad source list or another named method is not a deliverable.
Every decision returned to Max starts with simple language and a simple example,
then gives the recommendation, false-Gold/false-reject consequences, and known
limits; technical material belongs in an appendix.

A ratified operating rule lets discovery run continuously but makes Gold
certification occur once per day in frozen **certification epochs**. Each epoch seals the
eligible survivor cohort, complete search-ledger snapshot, method versions, and
shared multiplicity artifact before publishing rows. This makes the examined
universe coherent without slowing cheap research. It does not reset history:
later epochs still inherit prior result disclosures and must satisfy the chosen
lifetime/adaptive policy.

This protocol may end with fewer methods than the legacy suite. That is success
if the retained set covers the five planks with measured operating behavior and
clear failure explanations.

---

## 4. What a skeptical reviewer receives for one Gold row

| Plank | Required review package |
|---|---|
| Correctness | Frozen identity and inputs; point-in-time data proof; execution/fill contract; independent signal/trade reproduction; artifact hashes |
| Economic passage | Matched B&H definition; terminal deployable TECL wealth/share multiple and daily log-relative inference series; unrounded complete/recent real-horizon results; uncertainty margin; trade/regime/evidence sufficiency |
| Generalization | Explicit evidence-type labels; nested rolling-origin results; predeclared time/parameter/named-moment/execution stresses; behavioral-path clusters; assumptions and power for each method; observed-real versus reconstructed/synthetic labels |
| Search honesty | Complete family/campaign/lifetime search provenance; dependence model; independently reviewed search-wide correction and its controls |
| Reproducibility/currentness | Clean-machine replay; latest contract version; immutable per-row forward record; warnings/renewal state; no grandfathering |

The package also includes the validator-version control report: seeded defects it
caught, stable controls it retained, null behavior, false-Gold and false-reject
estimates, and every known limitation. That report validates the exam; it is not
another per-strategy score.

`Pending Gold` appears on the Gold leaderboard automatically when the next
daily frozen certification epoch publishes its passing cohort. It describes
activation eligibility, not weaker certification. Its forward counters remain
explicit, and it cannot be Recommended or Active until the cooling rule and
fresh certification pass.

---

## 5. Hardening backlog (prioritized)

1. **Prove the exam itself (G4/G10/G14).** Audit each retained method against its
   specification, remove duplicate/unpowered methods, freeze every free
   parameter, and measure false-Gold and false-rejection behavior. The
   [legacy findings log](validation-audit-findings.md) supplies prior evidence;
   it is not a substitute for auditing the final implementation.
2. **Implement and calibrate correctness and economic truth
   (G8/G12/G16/G17).** Prove causal point-in-time inputs; implement the fixed
   next-open fill and matched B&H contracts; calibrate costs, the rolling
   aggregate/catastrophic rules, provisional 1.10 point margin, lower bound above
   1.0, and warning/demotion behavior; and freeze a source-labelled named-moment
   suite.
3. **Prove generalization with the data Montauk actually has
   (G3/G5/G6/G9/G15/G19).** Choose only methods with adequate power; adjudicate
   the expanding-versus-rolling design, CPCV's applicable role, PBO, bootstrap,
   and synthetic evidence; execute the time-separated XLK-model-versus-real-TECL
   overlap study; report the remaining TECL data ceiling plainly.
4. **Solve search honesty once (G1/G2/G7/G18/G19).** Preserve the complete
   adaptive ledger and every holdout reveal, estimate effective behavioral
   dependence, and compare SPA/Reality Check/step-down or another reviewed
   design inside daily certification cohorts. Select the smallest method that
   controls the stated appliance-level error without making related valid
   configurations impossible.
5. **Make evidence fail-closed and current (G11/G13).** Implement immutable
   per-row forward records, Pending Gold activation status, clean reproduction,
   no missing required evidence, and latest-contract-only current Gold.

---

## 6. What does NOT change

This is evidence-led correction, never threshold shopping for a desired winner.
It may strengthen a permissive test **or** repair/remove an invalid over-strict
test when the audit and control studies justify that change. The autonomous agent
cannot alter the Gold planks, admitted methods, thresholds, scores, or decision
semantics. Those elements may change only through an explicit Max-authorized,
signed and versioned core release with documented rationale, tests, and
consequences for existing certifications. Incompatible rows immediately leave
the current board pending urgent recertification; they are not grandfathered.
No release may tune the grader toward the current candidate pool or compare mixed
contract versions as though they were identical. When a hardening item lands, it
is reconciled into the authoritative validation docs by explicit decision, never
by drift.

## 7. Primary research anchors

These sources establish the search-selection problem and candidate tools; citing
one does not automatically admit its method to Montauk:

- Halbert White, [“A Reality Check for Data Snooping”](https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152)
  (best encountered model versus a benchmark after specification search).
- Peter R. Hansen, [“A Test for Superior Predictive Ability”](https://www.tandfonline.com/doi/abs/10.1198/073500105000000063)
  (a more powerful alternative designed to reduce sensitivity to poor/irrelevant
  alternatives).
- Joseph P. Romano and Michael Wolf,
  [“Stepwise Multiple Testing as Formalized Data Snooping”](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x)
  (dependence-aware familywise error control for multiple comparisons).
- Campbell Harvey, Yan Liu, and Heqing Zhu,
  [“… and the Cross-Section of Expected Returns”](https://www.nber.org/papers/w20592)
  (multiple testing with correlated tests and selection breadth).
- David H. Bailey, Jonathan Borwein, Marcos López de Prado, and Qiji Jim Zhu,
  [“The Probability of Backtest Overfitting”](https://doi.org/10.21314/JCF.2016.322)
  (CSCV/PBO as one candidate instrument for configuration-selection risk).
- David H. Bailey and Marcos López de Prado,
  [“The Deflated Sharpe Ratio”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
  (Sharpe-specific adjustment for selection bias and non-normal returns, not a
  general deflator for arbitrary scores).
- Leonard Tashman,
  [“Out-of-sample tests of forecasting accuracy”](https://doi.org/10.1016/S0169-2070(00)00065-0)
  (series splits, rolling origins/windows, recalibration, and multiple test
  periods; no universal walk-forward-efficiency cutoff).
- Matthias Schnaubelt,
  [“A comparison of machine learning model validation schemes for non-stationary time series data”](https://www.iwf.rw.fau.de/files/2019/11/11_2019.pdf)
  (validation-scheme performance changes with stationarity/evolution; rolling-
  origin methods perform well in several non-periodic settings).
- Hamidreza Arian, Daniel Norouzi Mobarekeh, and Luis Seco,
  [“Backtest overfitting in the machine learning era”](https://doi.org/10.1016/j.knosys.2024.112477)
  (evidence favoring CPCV within a particular synthetic/ML comparison, to be
  tested rather than generalized automatically to Montauk).
- Cynthia Dwork et al.,
  [“The reusable holdout: Preserving validity in adaptive data analysis”](https://pubmed.ncbi.nlm.nih.gov/26250683/)
  (repeated adaptive feedback can overfit a holdout even without direct training
  access).
- Dimitris Politis and Joseph Romano,
  [“The Stationary Bootstrap”](https://www.tandfonline.com/doi/abs/10.1080/01621459.1994.10476870)
  (resampling inference for weakly dependent stationary observations under
  explicit assumptions).
- Max Morris,
  [“Factorial Sampling Plans for Preliminary Computational Experiments”](https://doi.org/10.1080/00401706.1991.10484804)
  (input-sensitivity screening, not an overfit probability).
- Andrew Lo,
  [“The Statistics of Sharpe Ratios”](https://doi.org/10.2469/faj.v58.n4.2453)
  (Sharpe inference and annualization depend on the return process and serial
  correlation).
- Diego Aparicio and Marcos López de Prado,
  [“How Hard Is It to Pick the Right Model?”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3044740)
  (financial simulation warning about Model Confidence Set power and multiple
  testing).

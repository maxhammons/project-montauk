# Montauk 3.0 — The Validation Engine (North Star) + Hardening Plan

**Status: LIVING DOC (opened 2026-06-17; owner contract updated 2026-07-21).**
This is the guiding-light workstream of Montauk 3.0. The audit below is
**design-level** (what is covered, what is missing, measured against the
anti-overfitting literature). The **line-by-line correctness audit** (G10) is
underway — findings logged in
[validation-audit-findings.md](validation-audit-findings.md) (`deflate.py` done; top
finding: parametric tail extrapolation in the deflation null).

---

## 1. Why this is the north star

Owner's framing (2026-06-17): *full walk-through and walk-forward, every validation
we can think of, so that by the end any Gold strategy is **defensible, auditable,
testable**, with **very little doubt of its ability to work into the future.***

The bucket and the search exist to **feed** the validation engine. The whole
machine's credibility reduces to that engine's rigor: if it lets one overfit
strategy through, the leaderboard stops being a certification and becomes a
watchlist. So the validation engine — not the optimizer, not the bucket — is the
thing that has to be bulletproof.

**The standing standard.** A Gold strategy must survive the scrutiny of a
skeptical quant professional or an academic referee: frozen and versioned logic,
full adaptive-search accounting, multiple-testing correction at every level,
true out-of-sample and correctly attributed live-forward evidence, reproducible
artifacts, independent re-implementation, and honestly stated uncertainty—
including what the data cannot support.

### 1a. Owner contract ratified through Questionnaire 3 on 2026-07-21

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
  fixed recent horizon initially centered on trailing five years, and a small
  predeclared rolling/window design. The exact uncertainty-aware margin starts
  from Max's provisional ~1.10 intuition and requires calibration.
- Synthetic history is diagnostic and never substitutes for real passage. Its
  current model and any weight/catastrophic veto require independent overlap and
  model-error calibration.
- Gold must use a timestamped, obtainable manual-execution model. Same-close
  fills cannot certify a signal that consumed that close. OHLC alternatives and
  close fills are stress/diagnostic outputs unless their availability and
  execution are proven.
- Backtest/B&H passage precedes the expensive validation suite. Candidate-code
  containment and correctness preflight precede execution.
- A historical-suite survivor is `Pending Gold`, normally accumulates 20 verified
  bars, and must pass a fresh certification before current Gold. Only the latest
  compatible contract appears on the current board; no legacy grandfathering.
- The validator must measure both false-Gold and false-rejection behavior. A
  validator that rejects everything is not robust merely because it is strict.
- Automation cannot change the validator, thresholds, weights, data/execution
  contract, or evidence rules. A signed Max-authorized core release creates new
  version identities and immediately stales incompatible certifications for
  urgent recertification.

---

## 2. The three-step pipeline (the architecture this lives in)

```
 STEP 1 — THE BUCKET            STEP 2 — BACKTEST + TUNE         STEP 3 — VALIDATION ENGINE
 (authoring / ideas)            (find valid parameters)          (overfit detection + robustness)
 ───────────────────            ─────────────────────            ──────────────────────────────
 implemented strategy   ──▶     GA / grid over the         ──▶   "did this REALLY work, and
 families, auto-entered          billion-combo param space        will it keep working?"
 (generate freely)               (cheap screen → mine)            the adversary that assumes
                                                                  everything upstream is overfit
                                                                  until proven otherwise
```

**The asymmetry that matters:** Steps 1–2 *generate* (and Montauk 3.0 makes them
enormously more powerful—auto-enter, continuous feedback, billions of
configurations). Step 3 is the **adversary**. As the number of effectively
independent opportunities to get lucky rises, the multiplicity burden must rise
with it. Raw counts of highly dependent near-twins do not automatically equal
independent trials, and unrelated evidence planks do not become arbitrarily
stricter merely because throughput improved. A more powerful search without
honest dependence-aware correction manufactures false Gold; a naïve raw-count
penalty can manufacture false rejection. This balance is the central design law
of the machine.

---

## 3. Current state — honest audit (2026-06-17)

**Headline:** the engine contains an advanced set of anti-overfitting methods and
maps to serious literature (López de Prado / Bailey et al., Politis-Romano,
Morris), but its certification claim is **provisional**. The correctness audit is
incomplete, breadth and board-level multiplicity gaps are structural, the
validator's own weights need governance, and live-forward attribution must be
per frozen row. “Professional-grade” is an acceptance target, not a current
finding.

### 3a. What's already strong (mapped to the literature)

| Capability | File | Literature anchor |
|---|---|---|
| Engine integrity — executed lookahead / repaint / overlap / bar-close-fill checks (not self-reported flags) | `validation/integrity.py` | no-lookahead correctness |
| Golden-regression net + shadow comparator vs `backtesting.py` / `vectorbt` | `tests/test_regression.py`, `test_shadow_comparator.py` | independent re-implementation cross-check |
| **CSCV / Probability of Backtest Overfitting** (logit λ, degradation slope, candidate OOS-top-half prob) | `validation/pbo.py` | Bailey, Borwein, López de Prado & Zhu (2017) |
| Selection-bias **deflation** — expected-max Beta EVT + Monte-Carlo null + **measured N_eff** (ratcheted) | `validation/deflate.py` | López de Prado expected-max-Sharpe / deflated performance |
| **True re-optimized OOS walk-forward**, kept distinct from replay-consistency WF | `validation/oos_walk_forward.py` | walk-forward analysis (Pardo) |
| **Stationary bootstrap** confidence intervals | `validation/uncertainty.py` | Politis & Romano (1994) |
| **Morris elementary-effects** global parameter sensitivity | `validation/uncertainty.py` | Morris (1991) |
| Execution realism (next-open fills, −15% budget) | `validation/reality_check.py`, gate_realism | implementation-shortfall realism |
| Event-dependence splicing (single-event edge collapse) | gate_realism | robustness to one-regime edges |
| Regime / return concentration (HHI, clustering) | `validation/sprint1.py` | Herfindahl-Hirschman concentration |
| **Active-system live-forward holdout + demotion/calibration scaffolding** | `ops/live_holdout.py`, `validation/confidence_v2.py` | valuable foundation; per-frozen-row attribution and sufficiency rules remain G11 |

The live-forward layer can become the most valuable evidence in the system, but
only after each observation is attributed to the exact frozen code, parameters,
and certification vintage that generated it.

### 3b. The gap register (what a skeptic would raise)

| # | Gap | Why it matters | Severity | Fix direction |
|---|---|---|:-:|---|
| **G1** | **Generation-breadth multiplicity.** Current N_eff accounting is blind to some authored families, cheap-screen rejects, adaptive batches, and board/lifetime selection. With continuous feedback-driven generation, P(some family reaches Gold by luck) rises even when individual rules look simple. | This is the price of the whole “huge bucket” vision. Unfixed, scaling generation silently manufactures false Gold. | **Critical** | Record every observable selection event and configuration actually evaluated; specify within-family, campaign, and board/lifetime correction. |
| **G2** | **No board-level multiple-testing test.** PBO covers a candidate's *own* param neighborhood; nothing asks "is the best-of-the-whole-board genuinely better than benchmark, given the full set tried?" (`reality_check.py` is fills, not the test of the same name.) | Each row is deflated for *its* search; the *board* is the max over thousands of pipeline runs and is not FWER/FDR-controlled. | **High** | Add White's Reality Check (2000) / Hansen's SPA (2005) / Romano-Wolf step-down across the family/board set. |
| **G3** | **Data-scarcity ceiling.** ~3–4 independent macro regimes, <20 trades, ~53 params on the champion; real-era multiple ~1.0–1.3×. No statistical method manufactures degrees of freedom that are not in the data. | The validator can be flawless and forward uncertainty can still be wide. Pretending otherwise is the dishonest failure mode. | **Structural (unfixable by math)** | Surface CIs, trade count, independent-regime count, and minimum track record. More elapsed untouched TECL history is the direct cure; other assets may add context but are not equivalent TECL forward evidence. |
| **G4** | **The validator's own free parameters.** 14 sub-score weights + every anchor are hand-set, and some were tuned to the *current* candidate pool (the `era_consistency` anchor note says so explicitly). | A validator fit to today's candidates is itself overfit — it grades the test it wrote. | **High** | Freeze + version the validator config; sensitivity-test verdicts against weight/anchor perturbation; **never** tune anchors toward the current pool. |
| **G5** | **Calibration thinness.** Live holdout began 2026-05-01 (~6 weeks); the confidence→forward-survival model trains mostly on *simulated* vintages. | The calibration that makes Conviction "honest" is not yet itself validated forward. | **Medium (time-healing)** | Keep accumulating; label calibration provisional; report calibration sample size alongside every Gold claim. |
| **G6** | **Small-sample power.** Bootstrap / regime / PBO computed on 15–19 trades have wide CIs and low power. | Many sub-scores are noisier than their single number implies. | **Medium** | Report CI width / power; add **Minimum Track Record Length** (Bailey & López de Prado 2014) as an explicit floor. |
| **G7** | **PBO scale + neighborhood.** M=32 variants, 16 blocks; the neighborhood is *random* param draws, not the configs the GA actually searched. | Measures overfit risk in the *neighborhood*, not the *search path* that produced the candidate. | **Low–Med** | Larger M / blocks; seed the neighborhood from actually-searched configs. |
| **G8** | **Point-in-time macro data.** FRED series (T10Y2Y, DFF, 3m T-bill) are *revised*; if revised values stand in for what was knowable historically, that's subtle lookahead. | A defensible-to-academics claim must rule out revision lookahead. | **Verify** | Confirm vintage / as-released macro data, or document the assumption explicitly. |
| **G9** | **Minimum Track Record Length** not computed. | A clean, standard, cheap statement of "how long a record is needed to trust this edge." | **Cheap add** | Implement MinTRL; surface per candidate. |
| **G10** | **No line-by-line correctness audit yet.** This document is a *design* gap analysis; the implementations themselves (is the PBO math right, the bootstrap stationary-block length sane, the null fit valid) are unaudited. | "Auditable" requires the audit to have actually happened. | **Process** | Read every `scripts/validation/*.py` against its cited method; record findings here. |
| **G11** | **Forward evidence is not yet an immutable per-row record.** An active-system stream can be relabeled when the champion changes, and repeated recertification on unchanged data can be mistaken for new evidence. | Evidence after one frozen version's certification belongs only to that version; reproducibility reruns do not create new market evidence. | **Critical contract** | Key observations by frozen strategy/configuration/certification ID; separate replay, renewal on new bars, and re-optimization; define sequential/hysteresis rules. |
| **G12** | **Gold execution and comparator semantics are unsettled.** Same-close fills are not deployable when the signal uses that close; B&H dates, distributions, cash return, costs, and unrounded comparison margin must be frozen. | A statistically strong result under an impossible fill is not fit to trade. A rounded point estimate barely above 1.0 is weak evidence of superiority. | **Critical contract** | Certify on the actual next-available execution workflow net of costs; keep close-fill as diagnostic. Decide whether the hard economic gate uses a one-sided lower confidence bound. |
| **G13** | **Composite/gate semantics may not match “passes every validation.”** Skipped/missing dimensions can be renormalized, warnings may not affect verdicts, and weighted strength can offset a failed plank. | A score is not a probability and cannot rescue absent mandatory evidence. | **High** | Define mandatory minima and explicit `not_applicable` equivalents; fail Gold on missing/unverifiable required evidence; label uncalibrated composite values as scores, not probabilities. |
| **G14** | **The validator's false-positive and false-negative operating characteristics are unmeasured.** Passing known defects and rejecting valid controls are both possible. | “Stricter” can hide a powerless or biased grader just as easily as a permissive one. | **Critical evidence** | Build a validation-of-validation harness with randomized nulls, seeded leakage/overfit defects, simple frozen controls, simulation, power reporting, and per-row forward outcomes. Freeze expected sensitivity/specificity ranges per contract version. |
| **G15** | **Synthetic TECL diagnostic validity is not independently calibrated.** The builder is reproducible, but its index/ETF proxies, leverage model, expenses, seam, and financing haircut are not equivalent to observed TECL behavior. | An uncalibrated synthetic vote or veto can create false confidence or reject a sound real-era strategy. | **High** | Validate on real-TECL overlap and model-error controls; version every assumption; quantify volatility/tracking differences; permit a weight/veto only after out-of-model review. |
| **G16** | **Recent/rolling passage and demotion can themselves become a hand-picked exam.** “Beat B&H however reasonably sliced” is not executable until the slices and persistence rule are frozen. | Retrospective windows manufacture robustness; excessively many correlated windows can make Gold impossible without adding independent evidence. | **Critical contract** | Predeclare a small complete-real/recent/rolling design, calibrate the provisional ~1.10 margin and uncertainty floor, and test the two-renewal warning/demotion rule under simulation and controls. |
| **G17** | **External-input point-in-time contracts are incomplete.** 3.0 may use VIX, volume, options, related assets, macro series, and idiosyncratic components while trading TECL only. | Revision, publication-lag, same-bar, survivorship, timezone, and missing-data mistakes can create invisible lookahead. | **High** | Require a versioned source registry with provenance, publication/market timestamp, revision policy, missing semantics, and causal feature APIs; verify with prefix replay and as-of fixtures. |

---

## 4. What "academically defensible Gold" means (the checklist a critic could run)

A Gold row should be able to answer all of these on demand:

1. **Frozen identity** — exact strategy logic, parameters, inputs, execution
   semantics, data vintage, and validator version are immutable for the verdict.
   Re-optimization creates a new candidate rather than rewriting forward history.
2. **Full search accounting** — the total observable families, adaptive batches,
   configurations evaluated, and rejects are recorded, and the selection
   correction uses them (G1).
3. **Multiple-testing controlled at every level** — per-candidate (PBO + deflation,
   present) *and* board-level (SPA / Reality Check, G2).
4. **True OOS + live forward** — re-optimized walk-forward plus evidence attributed
   to each frozen row, with bars, time, trades/signals, regimes, and calibration
   sample size stated (G5/G11). Historical-suite survivors remain Pending Gold
   until the required untouched forward record and fresh certification complete.
5. **Reproducible** — recomputable from the five artifacts; era metrics re-derivable
   (`certify/verify_board_reproducibility.py`); no trust in stale stamps.
6. **Independently re-implementable** — shadow comparator agrees (present; make it CI,
   not dev-only).
7. **Honest confidence** — stated CIs plus independent-regime/trade-count context
   and explicit acknowledgement of the data-scarcity ceiling (G3). An
   uncalibrated weighted composite is labeled a score, not a probability.
8. **Deployable economics** — every named real-data horizon beats the frozen B&H
   contract under the actual execution workflow and unrounded decision values
   (G12/G16).
9. **Mandatory evidence** — skipped, missing, insufficient, or unverifiable
   required gates cannot disappear through weight renormalization (G13).
10. **Validator operating characteristics** — frozen defect/control suites report
    measured false-Gold, false-rejection, power, and uncertainty behavior; pass
    scarcity is not used as proof of rigor (G14).
11. **Synthetic honesty** — the exact proxy/leverage/expense/seam/financing model
    and overlap error are disclosed; synthetic results are diagnostic and have no
    uncalibrated vote or veto (G15).
12. **Point-in-time inputs** — every external feature traces to an as-of source,
    publication/revision policy, missing-data rule, and causal fixture (G8/G17).
13. **Current contract only** — a material methodology change stales incompatible
    rows; older certificates are archived rather than grandfathered onto the
    current Gold board.

---

## 5. Hardening backlog (prioritized)

1. **G10 + G14 — audit and validate the validator.** Finish the line-by-line
   method audit, then prove the full suite against defect, null, structural-
   control, simulation, and forward datasets. **Underway** —
   [validation-audit-findings.md](validation-audit-findings.md).
2. **G12 + G16 — freeze deployable economic truth.** Calibrate timestamp/fill and
   matched-B&H semantics, complete-real/recent/rolling passage, provisional
   ~1.10 superiority margin, uncertainty floor, and warning/demotion behavior.
3. **G1 + G2 — dependence-aware breadth and board/lifetime correction.** Count
   the complete observable adaptive search while estimating effective—not raw—
   independent breadth; choose and independently review the hierarchical online
   SPA/Reality-Check/step-down design.
4. **G11 + G13 — fail-closed evidence and immutable forward identity.** Implement
   Pending Gold, per-row forward bars, hard mandatory planks, and latest-contract-
   only current Gold.
5. **G15 — independently recalibrate synthetic TECL.** Quantify overlap/model
   error before allowing any diagnostic weight or veto.
6. **G4 — freeze + sensitivity-test validator parameters.** Never tune anchors to
   the current candidate pool; define Validation Score without probability
   language until G14 supports it.
7. **G8 + G17 — point-in-time external data registry and causal API.** Cover macro,
   VIX, volume, options, related assets, and idiosyncratic inputs.
8. **G9 + G6 — Minimum Track Record Length + small-sample CI/power reporting.**
9. **G7 — strengthen PBO** with actual searched neighborhoods and calibrated
   scale.
10. **G5 + G3 — bank and expose untouched evidence.** Report calibration sample,
    trade/regime counts, and the TECL data-scarcity ceiling on every current claim.

---

## 6. What does NOT change

This is evidence-led correction, never threshold shopping for a desired winner.
It may strengthen a permissive test **or** repair/remove an invalid over-strict
test when the audit and control studies justify that change. The autonomous agent
cannot alter the Gold contract, binary correctness layer, composite, or deflation
machinery. Those elements may change only through an explicit Max-authorized,
signed and versioned core release with documented rationale, tests, and
consequences for existing certifications. Incompatible rows immediately leave
the current board pending urgent recertification; they are not grandfathered.
No release may tune the grader toward the current candidate pool or compare mixed
contract versions as though they were identical. When a hardening item lands, it
is reconciled into the authoritative validation docs by explicit decision, never
by drift.

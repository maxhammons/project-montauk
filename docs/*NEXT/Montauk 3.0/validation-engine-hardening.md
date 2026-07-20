# Montauk 3.0 — The Validation Engine (North Star) + Hardening Plan

**Status: LIVING DOC (opened 2026-06-17; owner contract updated 2026-07-17).**
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

### 1a. Owner contract clarified on 2026-07-17

- Gold is Montauk's highest **process and evidence certification**, not a
  guarantee of any future call or return.
- Every candidate faces the same mandatory evidence planks and rigor regardless
  of whether a human or an AI authored it. A structurally inapplicable test may
  have a predeclared equivalent or valid `not_applicable` result;
  origin-based T0/T1/T2 skipping and silent renormalization are not the target
  3.0 contract.
- Universal gates do not erase selection bias. The adaptive agent's family
  proposals, cheap-screen rejects, parameter configurations, feedback cycles,
  and board-wide comparisons must all be represented in the correction.
- Required real-data horizons determine economic eligibility. Synthetic history
  is diagnostic; a possible catastrophic synthetic veto is still an open
  predeclared rule.
- Backtest/B&H passage precedes the expensive validation suite. Candidate-code
  containment and correctness preflight precede execution.
- Automation cannot change the validator, thresholds, weights, or evidence rules.
  Max-authorized hardening may create a new contract version; affected
  certifications then follow an explicit stale/recertification policy.

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
enormously more powerful — auto-enter, grind-constantly, billions of combos). Step 3
is the **adversary**. The more powerful generation gets, the *harder* Step 3 must
work — **the bar rises with the search, it never falls.** A more powerful search
without a correspondingly harder validator just manufactures false Gold faster.
This is the single most important design law of the whole machine.

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
   sample size stated (G5/G11).
5. **Reproducible** — recomputable from the five artifacts; era metrics re-derivable
   (`certify/verify_board_reproducibility.py`); no trust in stale stamps.
6. **Independently re-implementable** — shadow comparator agrees (present; make it CI,
   not dev-only).
7. **Honest confidence** — stated CIs plus independent-regime/trade-count context
   and explicit acknowledgement of the data-scarcity ceiling (G3). An
   uncalibrated weighted composite is labeled a score, not a probability.
8. **Deployable economics** — every named real-data horizon beats the frozen B&H
   contract under the actual execution workflow and unrounded decision values
   (G12).
9. **Mandatory evidence** — skipped, missing, insufficient, or unverifiable
   required gates cannot disappear through weight renormalization (G13).

---

## 5. Hardening backlog (prioritized)

1. **G1 — breadth deflation.** The big rock; prerequisite for safe high-volume
   auto-enter. Count observable family proposals, adaptive batches,
   configurations evaluated, and rejects; feed the relevant levels into
   within-family and board/lifetime correction.
2. **G10 — line-by-line correctness audit** of `scripts/validation/`. Cheap insurance
   that the strong design is also a correct implementation. **Underway** —
   [validation-audit-findings.md](validation-audit-findings.md).
3. **G11–G13 — freeze the forward-evidence identity, deployable execution/B&H
   contract, and mandatory gate semantics** before calling the suite complete.
4. **G2 — board-level SPA / Reality Check** test across the family set.
5. **G4 — freeze + sensitivity-test the validator's own parameters.** Stop the
   validator from being overfit to today's pool.
6. **G8 — verify point-in-time macro data** (rule out revision lookahead).
7. **G9 + G6 — Minimum Track Record Length + small-sample CI/power reporting.**
8. **G7 — strengthen PBO** (scale + search-path neighborhood).
9. **G5 — keep banking live-forward evidence**; report calibration sample size on
   every claim (passive, time-healing).
10. **G3 — surface the data-scarcity ceiling** on every Gold claim now; the structural
   cure for TECL is more untouched TECL market evidence.

---

## 6. What does NOT change

This is hardening, never opportunistic softening. The autonomous agent cannot
alter the Gold contract, binary correctness layer, composite, or deflation
machinery. Those elements may change only through an explicit Max-authorized,
versioned core release with documented rationale, tests, and consequences for
existing certifications. No release may tune the grader toward the current
candidate pool or compare mixed contract versions as though they were identical.
When a hardening item lands, it is reconciled into the authoritative validation
docs by explicit decision, never by drift.

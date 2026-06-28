# Montauk 3.0 — The Validation Engine (North Star) + Hardening Plan

**Status: LIVING DOC (opened 2026-06-17).** This is the guiding-light workstream of
Montauk 3.0. The audit below is **design-level** (what is covered, what is missing,
measured against the anti-overfitting literature). The **line-by-line correctness
audit** (G10) is now **underway** — findings logged in
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

**The standing standard.** A Gold strategy must survive the scrutiny of a skeptical
quant professional or an academic referee: pre-registered selection, full
search-count accounting, multiple-testing correction at every level, true
out-of-sample *and* live-forward evidence, reproducible from artifacts, independently
re-implementable, with **honestly stated confidence intervals** — including honesty
about what the data cannot support.

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

**Headline:** the engine is already **professional-grade** and maps directly to the
serious anti-overfitting toolkit (López de Prado / Bailey et al., Politis-Romano,
Morris). It is well beyond typical independent-quant practice. The gaps below are
real, but most are *refinements* — except **G1**, which is structural and gets worse
exactly as Montauk 3.0 scales generation.

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
| **Live forward holdout + auto-demotion + calibration model** | `ops/live_holdout.py`, `validation/confidence_v2.py` | true out-of-sample forward evidence — *the rarest and most valuable layer* |

That live-forward layer is the crown jewel: most systems never collect honest
forward evidence at all, let alone auto-demote on it.

### 3b. The gap register (what a skeptic would raise)

| # | Gap | Why it matters | Severity | Fix direction |
|---|---|---|:-:|---|
| **G1** | **Generation-breadth multiplicity.** N_eff is counted from the hash-index (configs that got *mined*), blind to families *authored and screened out*. With auto-enter + grind-constantly, P(some family reaches Gold by luck) → 1 over time, and the deflation never sees the denominator. | This is the price of the whole "huge bucket" vision. Unfixed, scaling generation **silently manufactures false Gold** — the #1 risk in Montauk 3.0. | **Critical** | Count *generated* families (not just mined configs); feed authoring breadth into the multiplicity correction. Ties to decisions D6 + charter Q6. |
| **G2** | **No board-level multiple-testing test.** PBO covers a candidate's *own* param neighborhood; nothing asks "is the best-of-the-whole-board genuinely better than benchmark, given the full set tried?" (`reality_check.py` is fills, not the test of the same name.) | Each row is deflated for *its* search; the *board* is the max over thousands of pipeline runs and is not FWER/FDR-controlled. | **High** | Add White's Reality Check (2000) / Hansen's SPA (2005) / Romano-Wolf step-down across the family/board set. |
| **G3** | **Data-scarcity ceiling.** ~3–4 independent macro regimes, <20 trades, ~53 params on the champion; real-era multiple ~1.0–1.3×. No statistical method manufactures degrees of freedom that aren't in the data. | The validator can be flawless and forward confidence intervals are *still* wide. Pretending otherwise is the dishonest failure mode. | **Structural (unfixable by math)** | Quantify + *surface* the ceiling (state CIs, sample size, independent-regime count on every Gold claim). The real cure is more independent data → the multi-asset expansion (**Montauk 4.0**, `../Montauk 4.0/`). |
| **G4** | **The validator's own free parameters.** 14 sub-score weights + every anchor are hand-set, and some were tuned to the *current* candidate pool (the `era_consistency` anchor note says so explicitly). | A validator fit to today's candidates is itself overfit — it grades the test it wrote. | **High** | Freeze + version the validator config; sensitivity-test verdicts against weight/anchor perturbation; **never** tune anchors toward the current pool. |
| **G5** | **Calibration thinness.** Live holdout began 2026-05-01 (~6 weeks); the confidence→forward-survival model trains mostly on *simulated* vintages. | The calibration that makes Conviction "honest" is not yet itself validated forward. | **Medium (time-healing)** | Keep accumulating; label calibration provisional; report calibration sample size alongside every Gold claim. |
| **G6** | **Small-sample power.** Bootstrap / regime / PBO computed on 15–19 trades have wide CIs and low power. | Many sub-scores are noisier than their single number implies. | **Medium** | Report CI width / power; add **Minimum Track Record Length** (Bailey & López de Prado 2014) as an explicit floor. |
| **G7** | **PBO scale + neighborhood.** M=32 variants, 16 blocks; the neighborhood is *random* param draws, not the configs the GA actually searched. | Measures overfit risk in the *neighborhood*, not the *search path* that produced the candidate. | **Low–Med** | Larger M / blocks; seed the neighborhood from actually-searched configs. |
| **G8** | **Point-in-time macro data.** FRED series (T10Y2Y, DFF, 3m T-bill) are *revised*; if revised values stand in for what was knowable historically, that's subtle lookahead. | A defensible-to-academics claim must rule out revision lookahead. | **Verify** | Confirm vintage / as-released macro data, or document the assumption explicitly. |
| **G9** | **Minimum Track Record Length** not computed. | A clean, standard, cheap statement of "how long a record is needed to trust this edge." | **Cheap add** | Implement MinTRL; surface per candidate. |
| **G10** | **No line-by-line correctness audit yet.** This document is a *design* gap analysis; the implementations themselves (is the PBO math right, the bootstrap stationary-block length sane, the null fit valid) are unaudited. | "Auditable" requires the audit to have actually happened. | **Process** | Read every `scripts/validation/*.py` against its cited method; record findings here. |

---

## 4. What "academically defensible Gold" means (the checklist a critic could run)

A Gold row should be able to answer all of these on demand:

1. **Pre-registration** — the strategy + its tier were fixed before the backtest; the
   tier matches how it was selected (T0/T1/T2). No laundering a discovered strategy as a hypothesis.
2. **Full search accounting** — the *total* number of families and configs tried (not
   just survivors) is recorded, and the deflation uses it (G1).
3. **Multiple-testing controlled at every level** — per-candidate (PBO + deflation,
   present) *and* board-level (SPA / Reality Check, G2).
4. **True OOS + live forward** — re-optimized walk-forward (present) *and* accumulating
   live-holdout evidence with auto-demotion (present), with sample size stated (G5).
5. **Reproducible** — recomputable from the five artifacts; era metrics re-derivable
   (`certify/verify_board_reproducibility.py`); no trust in stale stamps.
6. **Independently re-implementable** — shadow comparator agrees (present; make it CI,
   not dev-only).
7. **Honest confidence** — stated CIs + the independent-regime / trade-count context,
   including explicit acknowledgement of the data-scarcity ceiling (G3). A defensible
   Gold says *"here is how confident, and here is exactly why it isn't more."*

---

## 5. Hardening backlog (prioritized)

1. **G1 — breadth deflation.** The big rock; prerequisite for safe high-volume
   auto-enter. Count generated families; feed into the multiplicity correction.
2. **G10 — line-by-line correctness audit** of `scripts/validation/`. Cheap insurance
   that the strong design is also a correct implementation. **Underway** —
   [validation-audit-findings.md](validation-audit-findings.md).
3. **G2 — board-level SPA / Reality Check** test across the family set.
4. **G4 — freeze + sensitivity-test the validator's own parameters.** Stop the
   validator from being overfit to today's pool.
5. **G8 — verify point-in-time macro data** (rule out revision lookahead).
6. **G9 + G6 — Minimum Track Record Length + small-sample CI/power reporting.**
7. **G7 — strengthen PBO** (scale + search-path neighborhood).
8. **G5 — keep banking live-forward evidence**; report calibration sample size on
   every claim (passive, time-healing).
9. **G3 — surface the data-scarcity ceiling** on every Gold claim now; the structural
   cure (more independent data) is the multi-asset expansion (Montauk 4.0).

---

## 6. What does NOT change

This is hardening, never softening. The frozen Gold contract, the binary correctness
layer, the composite weights *as currently locked*, and the deflation machinery stay
exactly as authoritative in `docs/validation-thresholds.md`. Every item here either
**adds** a check, **accounts for more breadth**, or **surfaces honesty** — none
relaxes the bar. When a hardening item lands, it is promoted into the authoritative
validation docs by explicit decision (never by drift).

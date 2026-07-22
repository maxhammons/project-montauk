# Montauk 3.0 Research — Stream 2: Continuous adaptive multiple testing

*Scope: statistically valid search-honesty policy for an indefinitely-running, agent-driven strategy factory — hierarchical families, agent feedback, daily certification cohorts, parameter neighbors, behavioral duplicates, family renaming/splitting, optimizer/stopping-rule changes, revealed holdouts, external-feature attempts. Maps to charter.md §4.4 ("search honesty"), the fifth Gold plank, and validation-engine-hardening.md gaps G1, G2, G7, G18, G19.*

---

## 1. One-page plain-English conclusion

**The problem:** Montauk never stops testing. Every day it looks at a fresh batch of candidates, indefinitely. Without accounting for *how many looks have been taken over the machine's whole life*, something with zero real edge will eventually look "significant" purely by chance — and look exactly as convincing as a real discovery.

**Recommended two-layer design:**

1. **Inside each daily certification epoch** — run a *batch* dependence-aware test (Romano–Wolf step-down or Hansen's SPA) asking whether today's best survivor beats buy-and-hold once today's candidate correlations are bootstrapped directly, rather than guessed at as an "effective number of tests."
2. **Across the appliance's whole lifetime** — run an **online alpha-investing / e-value wealth ledger** (Foster–Stine; Javanmard–Montanari's LORD; Ramdas's SAFFRON/ADDIS; e-BH). Montauk starts with one fixed error budget; each day's outer-test result spends a sliver, topped up only when a real discovery is banked. This is the only method family built for a search that never closes — White/SPA/Romano–Wolf assume a fixed, closed hypothesis set decided in advance.

**What's proven versus what's inferred.** The cited literature proves these ledgers control **mFDR** — expected false discoveries ÷ expected total discoveries — at or below the starting rate, under stated dependence assumptions. That is a *ratio* bound, not by itself a bound on the *absolute expected count* of false Golds over an unbounded horizon. An absolute-count cap additionally requires the total number of tests the ledger ever funds to be controlled — and Montauk's design lets the budget (and thus fundable tests) grow every time a true discovery is banked. So "expected false Golds stay ≤ the starting budget forever" is this stream's **[Inference]** about how the pieces compose, not a theorem taken directly from any cited paper. Experiment 2B (§3) exists to check that inference empirically before it is frozen into the validator.

**Does a future search ever change an already-issued Gold certificate? No, not through this mechanism.** The ledger and batch tests control the *rate of new certifications going forward*; they never re-adjudicate a certificate already granted. Later ledger depletion, a newly-noticed family relationship, or heavier-than-realized historical search intensity does not revoke, downgrade, or destabilize a prior Gold row under this design. The only thing that can change an already-issued Gold's standing is the separate, existing forward-performance system (the per-row forward ledger, Pending Gold's cooling window, Active/Recommended review per charter §9) — which reacts to how the strategy trades going forward, not to search accounting. The two systems must never be conflated.

**Correcting the record on the "1%" reference.** charter.md and validation-engine-hardening.md §4 both state the aspirational figure as **"a 1% annual probability of any false Gold"** — annual, repeated, with no "lifetime" or "ever" language anywhere. An earlier draft of this report quoted "1% probability of any false Gold, ever" as if lifted from the charter; it was not. Converting that annual aspiration into a single **lifetime** budget (recommended below) is *this stream's proposed departure*, not existing ratified policy — treated honestly as an open decision in §8(a).

**Why the choice isn't cosmetic — illustrative quantification** (placeholders pending Experiment 2B's real simulation; not validated Montauk numbers):

| Horizon | Naive "reset 1% every year" † | Single lifetime budget (W₀ = 0.01, never reset) |
|---|---|---|
| 1 year | 1.0% | ≤ 1.0% |
| 5 years | ≈ 4.9% (1 − 0.99⁵) | ≤ 1.0% (unchanged) |
| 10 years | ≈ 9.6% (1 − 0.99¹⁰) | ≤ 1.0% (unchanged) |
| 50 years | ≈ 39.5% (1 − 0.99⁵⁰) | ≤ 1.0% (unchanged, contingent on §6's composition caveat) |

† Independence-across-years illustration only, not how Montauk or any cited method actually behaves — included solely to show quantitatively why "1% per year forever" and "1% once, ever" are different promises.

**Recommended default (pending Max's sign-off, §8a):** a single lifetime wealth budget, W₀ = 0.01, spent once, refunded only by verified true discoveries, reset only by a signed new core-version release. Phase 1 turns the table above into a real frontier (Experiment 2B) so Max picks the operating point against actual numbers.

---

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Adaptive re-analysis of the same data inflates false-discovery risk unless leakage is bounded | Primary | Dwork et al., ["The reusable holdout"](https://www.science.org/doi/10.1126/science.aaa9375), *Science* 349(6248), 2015 | Strong | Yes — theoretical, population-agnostic | Supports the charter's "no permanent lockbox; every reveal is spent" rule. |
| An adaptively-fed leaderboard can overfit its holdout; "only update if meaningfully better" (the Ladder) bounds it | Primary | Blum & Hardt, ["The Ladder"](https://arxiv.org/abs/1502.04585), NeurIPS 2015 | Strong | Partial — mechanism transfers; Montauk's board is a certification gate, not a score contest | Relevant to Experiment 2D, §8(c). |
| A fixed error budget can be spent across an unbounded test stream so that **mFDR** never exceeds the start rate | Primary | Foster & Stine, ["α-investing"](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2007.00643.x), *JRSS-B* 70(2), 2008 | Strong | Yes | Foundational to the ledger. **mFDR is a ratio, not FDR, and not itself an absolute-count cap** — §1, §6. |
| LOND/LORD generalize alpha-investing with online FDR/mFDR control under independence and some dependence | Primary | Javanmard & Montanari, ["Online Rules for Control of FDR/FDX"](https://projecteuclid.org/journals/annals-of-statistics/volume-46/issue-2/Online-rules-for-control-of-false-discovery-rate-and-false/10.1214/17-AOS1559.full), *AoS* 46(2), 2018; arXiv companion: [1603.09000](https://arxiv.org/abs/1603.09000) | Strong | Yes | **Correction:** arXiv:1502.06197, previously cited as the "precursor," is a distinct earlier paper (introduces LOND/LORD), not a preprint of this AoS paper — 1603.09000 is the real companion. Dependence assumptions still need checking against market history (§6). |
| SAFFRON improves power via adaptive null-fraction estimation; ADDIS further improves it under conservative nulls | Primary | Ramdas et al., ["SAFFRON"](https://arxiv.org/abs/1802.09098), ICML 2018; Tian & Ramdas, ["ADDIS"](https://arxiv.org/abs/1905.11465), NeurIPS 2019 | Strong | Yes | ADDIS is the power-robust default for Montauk's likely conservative-null regime. |
| e-values merge validly under arbitrary dependence by averaging; e-BH controls FDR under arbitrary dependence | Primary | Vovk & Wang, ["E-values"](https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-3/E-values-Calibration-combination-and-applications/10.1214/20-AOS2020.full), *AoS* 49(3), 2021; Wang & Ramdas, "FDR control with e-values," *JRSS-B* 84(3), 2022 | Strong | Yes | Best reason to prefer e-values for the outer ledger. Note: "arbitrary dependence" is proved *among e-values*, conditional on each being individually valid — not a certification that the within-epoch test modeled market dependence correctly (§6). |
| "Testing/safe by betting" reframes tests as betting strategies valid under optional stopping (anytime-valid) | Primary | Shafer, ["Testing by betting"](https://doi.org/10.1111/rssa.12647), *JRSS-A* 184, 2021; Grünwald et al., ["Safe testing"](https://academic.oup.com/jrsssb/article/86/5/1091), *JRSS-B* 86(5), 2024 | Strong | Yes | Matches campaigns with no pre-declared fixed duration. |
| The best model from a specification search needs a joint bootstrapped max-statistic null, not a per-model p-value | Primary | White, ["Reality Check"](https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152), *Econometrica* 68(5), 2000 | Strong | Yes, for a fixed closed universe, not an unbounded stream | Correct for the within-epoch test, not the lifetime ledger; conflating the two is G2. |
| SPA is less conservative than the Reality Check, reducing sensitivity to weak/irrelevant alternatives | Primary | Hansen, ["SPA"](https://www.tandfonline.com/doi/abs/10.1198/073500105000000063), *JBES* 23(4), 2005 | Strong | Same caveat | Preferred given daily-cohort breadth from cheap screens. |
| Romano–Wolf stepwise testing controls FWER using bootstrapped actual dependence among test statistics | Primary | Romano & Wolf, ["Stepwise Multiple Testing"](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x), *Econometrica* 73(4), 2005 | Strong | Yes | Answers behavioral-duplicate/parameter-neighbor dependence without hand-estimating "effective tests" (contrast PBO's fixed M=32, G7). |
| Correlated-test multiplicity materially changes which asset-pricing anomalies survive; naive per-test significance overstates discoveries | Primary (empirical) | Harvey, Liu & Zhu, NBER WP [20592](https://www.nber.org/papers/w20592) | Strong (warning) / Moderate (numeric anchor) | Partial — warning transfers; equity-factor t-stat cutoffs must **not** be imported as Montauk thresholds | Population mismatch flagged. |
| CSCV/PBO estimates rank-reversal risk of a predeclared selection universe | Primary | Bailey, Borwein, López de Prado & Zhu, ["PBO"](https://doi.org/10.21314/JCF.2016.322), *JCF* 20(4), 2017 | Strong (method) / Moderate (applicability) | Partial — valid only if the selection matrix reflects the actual search, not a convenient neighborhood (G7) | Complementary diagnostic, not a substitute for §1's two layers. |
| Deflated Sharpe Ratio adjusts Sharpe inference for selection bias and non-normality | Primary | Bailey & López de Prado, ["DSR"](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551), 2014 | Strong | Conditional — only if Sharpe is a declared input; not Montauk's share-multiple target | Charter §4.3 already restricts this. |
| Anytime-valid e-value backtests exist for financial risk-measure calibration (VaR/ES) | Primary (adjacent) | Wang, Wang & Ziegel, ["E-backtesting"](https://arxiv.org/abs/2209.00991) | Moderate | Weak-to-moderate — risk calibration, not discovery multiplicity | Shows the toolset is finance-adjacent already; not evidence for a Montauk threshold. |
| An LLM-authored synthesis can cite fixed cutoffs as domain-general | Secondary (repo-internal) | `validation-engine-hardening.md` §3a | N/A | N/A | Montauk's own caution against importing numbers uncritically — the standard this stream holds itself to. |

---

## 3. Recommended Montauk experiment(s)

Each is a control-world simulation run **before** any threshold or method is frozen into the validator. None may be re-run with an expanded grid after seeing an inconvenient result.

### Experiment 2A — Within-epoch batch method bake-off
- **Preregistered estimand:** for a simulated daily cohort of size *k* from five generators (dependence-preserving block-bootstrapped null TECL/B&H; exposure/trade-matched random rules; a high-dimensional noise-parameter family swept as the GA would; an event/date-memorizer; a planted-signal world), estimate epoch-level Type-I rate and power for no correction, Bonferroni, BH, Reality Check, SPA, Romano–Wolf, and e-BH.
- **Stopping rule:** 2,000 simulated epochs per world, fixed in advance. Report exact Clopper–Pearson CIs. No additional batches regardless of outcome.
- **Frozen in advance:** generator code, cohort-size distribution, planted-signal magnitude, method list.

### Experiment 2B — Lifetime online-ledger simulation
- **Preregistered estimand:** cumulative false Golds (mFDR) *and* true-signal recovery over simulated 1/5/10-year horizons, for LOND, LORD, SAFFRON, ADDIS, e-value GAI, across W₀ ∈ {0.001, 0.01, 0.05, 0.10}, feeding 2A's actual generator output plus a scripted near-twin-flooding agent and a shared-regime common random effect. Must report the realized **absolute** false-Gold count against total tests funded, separately from mFDR, as the direct empirical check of §1's inference.
- **Stopping rule:** 5,000 lifetime realizations per (rule, W₀) cell, fixed in advance. Full frontier at 1/5/10 years, every cell. No new values added after seeing results.
- **Deliverable:** the frontier plot (charter §4.4), annotated against both the charter's literal annual reference and the lifetime alternative — replacing §1's illustrative table with real numbers.

### Experiment 2C — Behavioral-duplicate / effective-breadth calibration
- **Preregistered estimand:** ratio of raw generated configurations to behaviorally-distinct clusters (exact hash, G19) across the existing spike/leaderboard history.
- **Stopping rule:** one-time, retrospective, descriptive analysis of the complete existing record; no new search, no tuning against the result.

### Experiment 2D — Reusable-holdout (Ladder/Thresholdout) feasibility pilot
- **Preregistered estimand:** whether Thresholdout/Ladder against a historical block with known planted SNR yields materially tighter, better-calibrated generalization than Montauk's "spent on first reveal" policy, under a fixed sequence of simulated adaptive queries.
- **Stopping rule:** query budget and 1,000-query sequence length fixed in advance; single frozen evaluation.

---

## 4. Null, defect, and planted-signal controls

| Control | Construction | Required outcome |
|---|---|---|
| Dependence-preserving null world | Circular block bootstrap of real TECL/B&H returns, no embedded edge | Both layers reject at ≈ declared rate |
| Exposure/trade-matched random rule | Random switching matched to a real candidate's exposure/trade count | Must not pass above declared Type-I rate |
| High-dimensional noise-parameter family | Large swept family, no economic rationale, searched as the GA would | Board test rejects best survivor at declared rate despite size |
| Event/date memorizer | Rule keyed to specific dates | Fails generalization *and* flagged as exceptional-by-luck |
| Intentional lookahead/repaint/fill defect | Seeded correctness bugs (G14 harness) | Caught by the correctness plank before reaching multiplicity; a leak is that plank's defect, not this stream's |
| Frozen structural control (plain EMA cross) | Known, non-tuned baseline | Consistent across repeated runs; canary for ledger implementation drift |
| Planted, recoverable signal world | Injected edge, predeclared magnitude | Both layers recover it at acceptable power; failure implies over-conservatism (§5) |
| Wealth-gaming adversarial fixture | Scripted rename / near-twin flood / "new campaign" restart after a bad epoch | **No reduction** in charged wealth from any maneuver; identity keys off the canonicalized hashed logic graph (charter §8.3), never the agent-supplied name |
| Optimizer/stopping-rule-change fixture | Mid-lifetime optimizer swap, no signed new core version | Treated as continuation, not reset; reset observable only after a signed core-version bump |
| Revealed-holdout replay | Repeated queries against one sealed historical block | Marginal informativeness decays with each reveal (Dwork et al.), confirming "spent/reused" is implemented, not just declared |
| Already-issued-Gold non-interference fixture | Freeze a Gold row; run 2B-style search for a further simulated year, including scripted ledger depletion | The frozen row's status is provably untouched by any subsequent ledger event — direct test of §1's "no backward revocation" claim |

Each control needs a deterministic expected result and retained artifact (§7); "the pipeline passed" is insufficient without independently checked seeded-defect detection (G10, G14).

---

## 5. False-Gold and false-rejection consequences and asymmetry

- **False Gold cost:** Max manually executes real trades ($10,000–$100,000 notional) against a configuration with no real edge — eroding the premise that Gold exists so Max doesn't re-litigate the pipeline during a scary drawdown. A false Gold failing *during* a real drawdown looks identical, in the moment, to a real edge having a bad month.
- **False rejection cost:** a genuinely good configuration is denied or delayed behind Pending Gold's 20-bar window — **structurally cheaper**, since the agent keeps searching and can re-propose a similar family later. It is a one-time opportunity cost, not a standing liability.
- **The asymmetry:** false rejections self-heal; false Golds do not until the forward ledger eventually reveals the problem, likely after capital is at risk. The appliance should lean conservative on Experiment 2B's frontier rather than a "50/50" framing — but not arbitrarily strict, since G14 warns a validator rejecting everything is unmeasurable, not robust. The deliverable to Max is the quantified trade-off curve, not a qualitative "be careful."
- **Timing matters.** A false Gold caught within the 20-bar window costs little; one surviving to become Active for months compounds risk. Per §1, that forward-ledger/cooling mechanism is the *only* thing that acts on an already-issued certificate — a separate risk-control system from the multiplicity correction, reported to Max as distinct.

---

## 6. Assumptions and power/limits

- **Data ceiling is structural, not a multiplicity problem.** TECL has ~15 years of history and ~3–4 materially independent macro regimes (G3). No multiplicity method manufactures more; this stream only makes the accounting of what was tried honest.
- **Two distinct dependence sources, easy to conflate.** (1) *Search-generated* — near-twins correlated by shared logic; Romano–Wolf/SPA's bootstrap handles this within an epoch. (2) *Market-generated* — every epoch tests against the same ~15-year history, so consecutive epochs' statistics are not independent even for unrelated families. "Valid under arbitrary dependence" for e-BH/ADDIS is a proof about dependence *among* e-values, conditional on individual validity — it does not certify the within-epoch test modeled market dependence correctly. Experiment 2B feeds 2A's real output into the ledger for this reason; proving each layer valid in isolation and assuming automatic composition would be a mistake.
- **mFDR vs. FDR vs. absolute count — the honest gap.** Alpha-investing guarantees are proven for mFDR, not FDR, and not directly for the absolute expected count of false Golds over an unbounded horizon. §1's "≤ W₀ forever" framing is this stream's own composition, flagged **[Inference] not [Primary evidence]**; it holds only if total funded tests don't outpace the ratio guarantee, and Montauk's design lets the budget (and fundable tests) grow whenever a true discovery is banked. Experiment 2B must report the absolute count directly.
- **Behavioral-duplicate clustering is itself uncertain.** Exact hashing (G19) is simple and hard to game but may under-cluster near-duplicates differing on one rare bar (§8d).
- **Power is genuinely limited by evidence, not just correction choice.** With single-digit independent regimes, even a well-calibrated combination has wide uncertainty bands; "leader not clearly separated" (charter §9) should be the normal state for close competitors.
- **This stream does not address engine correctness.** Lookahead/repaint/fill defects are a precondition, not a consequence, of multiplicity accounting (G10, G14 own that boundary).
- **This stream does not, and should not, re-adjudicate already-issued Gold certificates.** Per §1, scope is the rate of new certifications; making search-honesty findings retroactively touch a prior Gold row would need its own separate charter change and is out of scope here.

---

## 7. Required fixtures and durable artifacts

- **Deterministic positive fixture:** a frozen structural control (plain EMA-cross) through the full pipeline, exact expected pass/fail and wealth-ledger delta retained as regression.
- **Deterministic seeded-negative fixture:** a memorized-date rule, expected to fail the outer test at or below its declared rate — canary for silent over-permissiveness.
- **Planted-signal fixture:** injected edge of predeclared, versioned magnitude; expected recovery rate as the power baseline.
- **Wealth-ledger replay fixture:** a frozen, hand-verifiable sequence of reveals with exact expected wealth balance after each step — the ledger's own unit test.
- **Adversarial lineage fixture:** the §4 rename/flood/restart attack, with an artifact proving charged wealth was unaffected.
- **Already-issued-Gold non-interference fixture:** the §4 fixture proving a frozen row's status survives further ledger activity — regression test for §1's "no backward revocation" claim.
- **Control-world generator code and parameters**, version-pinned, for Experiments 2A/2B — reproducible exactly, never silently re-simulated later.
- **The frontier plot itself** (false-Gold vs. power, 1/5/10-year horizons, W₀ grid) — a durable, dated artifact, regenerated only under an explicit new contract version.
- **A validator-version control report** (hardening-doc §4 pattern): seeded defects caught, stable controls retained, estimated false-Gold/reject rates, known limitations — versioned per contract release.

---

## 8. Unresolved owner decisions

**(a) Is the aspirational reference a lifetime budget, or should Montauk keep the charter's literal annual framing?**
The charter's text is **annual**, not lifetime — a prior draft misquoted it as "ever." Recommended default: a **lifetime** wealth budget (W₀ = 0.01, spent once, refunded only by verified true discoveries, reset only by a signed core-version release) — a deliberate, disclosed *change*, since §1's table shows a naive annual-reset drifting toward ~40% cumulative false-Gold probability over 50 years, while a lifetime budget holds ≤1% by construction (subject to §6's composition caveat). Tradeoff: the relative bar for new certification rises quietly as prior discoveries consume the budget. A periodic partial refresh is possible but reintroduces a quantifiable erosion Experiment 2B must price out first. **Requires Max's explicit sign-off — a policy change, not a restatement.**

**(b) Does a new optimizer, fitness function, or named "campaign" ever justify a fresh wealth sub-ledger?**
Recommended default: **no** — every change inherits the lifetime ledger unless accompanied by a signed new core-version release, consistent with the charter's existing versioning rule. A softer rule creates a low-effort gaming vector: relabeling to "restart the counter." (Governs *new* certifications only — per §1, has no bearing on certificates already issued.)

**(c) Is a reusable-holdout mechanism worth building, given the charter already treats every reveal as spent?**
Recommended default: **decline for v1**; revisit only if Experiment 2D shows materially tighter calibration than spent-on-reveal, given the added governance/validation burden (G10/G14).

**(d) How should "behavioral duplicate" be defined — exact trade-path hash, or fuzzier overlap tolerance?**
Recommended default: **exact hash only**, for simplicity and gaming-resistance; revisit only if Experiment 2C shows material under-clustering in practice.

**(e) Should external-feature "fishing" draw against the same wealth ledger as strategy-logic search, or a separate one?**
Recommended default: **the same ledger** — a new feature is a new configuration attempt like any other; a separate "free" ledger is a direct loophole (G17's point-in-time contract still applies).

---

## References

*Primary sources first, each tagged. Citations verified by direct fetch of the arXiv/publisher record; one correction noted inline (#2).*

1. **[Primary]** Foster, D. & Stine, R. (2008). "α-investing: a procedure for sequential control of expected false discoveries." *JRSS-B* 70(2), 429–444. https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2007.00643.x
2. **[Primary]** Javanmard, A. & Montanari, A. (2018). "Online Rules for Control of False Discovery Rate and False Discovery Exceedance." *Annals of Statistics* 46(2), 526–554. https://projecteuclid.org/journals/annals-of-statistics/volume-46/issue-2/Online-rules-for-control-of-false-discovery-rate-and-false/10.1214/17-AOS1559.full — arXiv companion: https://arxiv.org/abs/1603.09000. *Correction: arXiv:1502.06197, previously cited as the "precursor," is a distinct earlier paper by the same authors (introduces LOND/LORD) — related, not a preprint of this AoS paper.*
3. **[Primary]** Ramdas, A., Zrnic, T., Wainwright, M. & Jordan, M. (2018). "SAFFRON." *ICML* PMLR 80, 4286–4294. https://arxiv.org/abs/1802.09098
4. **[Primary]** Tian, J. & Ramdas, A. (2019). "ADDIS." *NeurIPS 2019*. https://arxiv.org/abs/1905.11465
5. **[Primary]** Vovk, V. & Wang, R. (2021). "E-values: Calibration, combination and applications." *Annals of Statistics* 49(3), 1736–1754. https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-3/E-values-Calibration-combination-and-applications/10.1214/20-AOS2020.full
6. **[Primary]** Wang, R. & Ramdas, A. (2022). "False discovery rate control with e-values." *JRSS-B* 84(3), 822–852. https://academic.oup.com/jrsssb/article-abstract/84/3/822
7. **[Primary]** Shafer, G. (2021). "Testing by betting." *JRSS-A* 184, 407–431. https://doi.org/10.1111/rssa.12647
8. **[Primary]** Grünwald, P., de Heide, R. & Koolen, W. (2024). "Safe testing." *JRSS-B* 86(5), 1091–1128. https://academic.oup.com/jrsssb/article/86/5/1091
9. **[Primary]** White, H. (2000). "A Reality Check for Data Snooping." *Econometrica* 68(5), 1097–1126. https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152
10. **[Primary]** Hansen, P. R. (2005). "A Test for Superior Predictive Ability." *JBES* 23(4), 365–380. https://www.tandfonline.com/doi/abs/10.1198/073500105000000063
11. **[Primary]** Romano, J. & Wolf, M. (2005). "Stepwise Multiple Testing as Formalized Data Snooping." *Econometrica* 73(4), 1237–1282. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x
12. **[Primary]** Harvey, C., Liu, Y. & Zhu, H. "… and the Cross-Section of Expected Returns." NBER WP 20592. https://www.nber.org/papers/w20592
13. **[Primary]** Bailey, D. H., Borwein, J., López de Prado, M. & Zhu, Q. J. (2017). "The Probability of Backtest Overfitting." *J. Computational Finance* 20(4), 39–69. https://doi.org/10.21314/JCF.2016.322
14. **[Primary]** Bailey, D. H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio." *J. Portfolio Management*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
15. **[Primary]** Dwork, C., Feldman, V., Hardt, M., Pitassi, T., Reingold, O. & Roth, A. (2015). "The reusable holdout." *Science* 349(6248), 636–638. https://www.science.org/doi/10.1126/science.aaa9375
16. **[Primary]** Blum, A. & Hardt, M. (2015). "The Ladder." https://arxiv.org/abs/1502.04585
17. **[Primary, adjacent domain]** Wang, Q., Wang, R. & Ziegel, J. "E-backtesting." Working paper. https://arxiv.org/abs/2209.00991
18. **[Secondary, repo-internal]** `docs/*NEXT/Montauk 3.0/validation-engine-hardening.md` — Montauk's audit and gap register (G1, G2, G3, G7, G10, G14, G17, G18, G19); also the source verified for the charter's exact "1% annual" wording (§1, §6).
19. **[Secondary, repo-internal]** `docs/*NEXT/Montauk 3.0/charter.md` §§4.3–4.5, 5, 9 — operating contract for the Gold exam, certification epochs, and leaderboard/activation authority. Governing product context, not statistical evidence.

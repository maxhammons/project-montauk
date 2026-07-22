# Montauk 3.0 Research — Stream 3: Validator-of-validator laboratory

**Scope note.** This report designs the control-world laboratory testing the *whole* Montauk 3.0 loop — author → search → select → backtest → validate → certify — not one validation function in isolation. It satisfies G14 (unmeasured false-positive/negative rates), G19 (behavioral duplicates), G1/G2 (multiplicity), and the D55/D40 research mandate. It does not choose thresholds or which named method (PBO, SPA, CPCV, bootstrap…) survives Phase 1 — that is Streams 1, 2, and 4's job. It answers one question: **how would Montauk ever know if its own examiner were lying to it, in either direction?**

Every recommendation is method-first and champion-agnostic: no experiment or fixture is built around, or presumes the outcome for, any specific registered strategy (D43: "no legacy Gold row is presumed to meet 3.0 — every row must pass the final contract from scratch").

---

## 1. One-page plain-English conclusion

**Bottom line: build a "fake evidence factory" before trusting the real one.**

The validator is the only thing between "this looks good" and "Max risks real money." Code can be wrong invisibly — too gullible (Gold on noise) or too paranoid (rejects something real). The only way to know which failure you have is to feed the validator things whose true answer you already know, because you built them.

- **Fake markets with no real edge** (dependence-preserving nulls) — run the full discovery loop against these. Any Gold here is a **false Gold**, by construction.
- **Fake markets with a real, moderate, hidden edge** — if the pipeline fails to certify it, that's a **false rejection**: the bar is too high, or a gate is broken.
- **Fake markets with a genuine regime break** — a stale edge that only worked before the break must be caught, not extrapolated across it.
- **Fake strategies that cheat** — peeking at tomorrow's close, a hard-coded memorized crash date, an unobtainable fill, 200 near-identical copies of one trade sequence. Each must be caught deterministically.
- **Fake strategies that are genuinely good but trade rarely** — the honest verdict may be `insufficient` (D50), not a false pass or fail.

**Worked example.** A control strategy: "risk_on if bar-index falls within [2020-03-20, 2020-04-15], else risk_off," dressed with a plausible "recovery window length" parameter. Backtested honestly it looks spectacular — it *is* the one crash-recovery window in TECL's history. A validator with no calendar-literal detection or event-concentration check certifies it Gold. The lab plants exactly this, confirms rejection (event-dependence diagnostic + type-system refusal of date literals), and keeps it as a permanent regression fixture.

This is a laboratory, not a one-time test — it reruns every time the validator's contract version changes (D42/D43).

**Max should decide now:** (1) approve building this battery before autonomous search runs at scale — an unmeasured validator is "unknown," not "strict"; (2) set the compute budget, since full-length control draws compete with discovery for the same host cycles (Section 8); (3) decide who plays "the cheater" in adversarial review — a separate AI session with no validator-internals access is the recommended default, since a paid human reviewer is out of scope (D54).

---

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Block/stationary resampling preserves marginal distribution and short-range dependence, giving a principled null against which structural rules can be tested | Primary | Künsch (1989), Ann. Statist. 17(3):1217–1241 | Strong (foundational) | Partial — assumes weak stationarity; TECL/VIX carry regime shifts a resampled null does not manufacture new instances of | Block length is itself a tuned parameter; "passes the null" means no edge *under this model*, not that none exists |
| Stationary bootstrap (geometric random block lengths) improves on fixed-block Künsch resampling for weakly-dependent series | Primary | Politis & Romano (1994), JASA 89(428):1303–1313 | Strong | Partial — same stationarity caveat | Candidate instrument per §3c; reused here to *build null worlds*, not compute a strategy's own CI |
| CSCV/PBO estimates probability of backtest overfitting for a predeclared trial universe via symmetric partitioning | Primary | Bailey, Borwein, López de Prado & Zhu (2015/16), J. Computational Finance | Strong for stated scope | Partial — needs the actual searched-and-selected universe, not a convenient neighborhood (G7) | A candidate false-Gold detector *to be validated* here, not ground truth |
| Leakage has a formal taxonomy (legitimate vs. illegitimate features, contamination, learn-predict separation) generalizing beyond its original setting | Primary | Shachar Kaufman, Saharon Rosset, Claudia Perlich & Ori Stitelman (2012), ACM TKDD 6(4), Art. 15 | Strong | Strong — maps onto point-in-time feature contracts (G8, G17) | The checklist for enumerating leakage subtypes in Section 7, not a source of numeric thresholds |
| Metamorphic testing checks correctness without a ground-truth oracle via relations between related inputs/outputs | Primary + survey | Chen, Cheung & Yiu (1998), HKUST-CS98-01 (located via secondary citation); surveyed in Chen et al. (2018), ACM Comput. Surv. 51(1) | Strong (survey); Moderate (locating 1998 original) | Strong — directly usable for engine correctness checks (e.g., shifting all prices by a constant should not change signal timing) | Software-QA technique, not a statistical control; complements Section 4's mutation-testing framing |
| Mutation testing (seeding known defects, checking the suite kills them) measures whether tests would catch a real bug | Primary survey | Jia & Harman (2011), IEEE TSE 37(5):649–678 | Strong | Strong — the design pattern for the seeded-defect fixture library | Borrowed for validator logic, not arbitrary source code |
| Repeated adaptive querying of a held-out set invalidates its guarantee even without direct training on it; a reusable holdout needs an explicit mechanism to stay valid | Primary | Dwork, Feldman, Hardt, Pitassi, Reingold & Roth (2015), Science 349(6248):636–638 | Strong | Strong — motivates a sealed, never-revealed blind battery (Section 4) | Its fix (thresholdout) is a candidate for Streams 1/2 on market-data holdouts; here only the warning is borrowed |
| Herding/"expert consensus" repetition across AI-generated literature is not independent corroboration and does not establish a threshold applies to TECL | Secondary (repo-internal) | `validation-engine-hardening.md` §3a | Strong as a project finding | N/A | Why this report measures acceptance bars on Montauk's own controls rather than importing convention (Section 8) |
| A validator can be simultaneously "strict" and "wrong" — strictness and correctness are different axes | **Inference** | Derived from Jia & Harman (2011) + repo D40/G14 | Moderate — reasoned, not published for finance validators | Full — organizing principle of this stream | Labeled Inference deliberately; not cited as an established external result |

---

## 3. Recommended Montauk experiments

Each is **preregistered**: estimand, construction, and stopping rule frozen before any result is inspected (§3e item 7). None choose a threshold — they produce operating-characteristic curves Streams 1/2/4 and Max use to set them.

**V1 — Null-world false-Gold rate.** *Estimand:* probability at least one configuration reaches Gold during a simulated year of continuous discovery against synthetic TECL-like paths (stationary-bootstrap resampled real TECL/VIX log-returns) with no genuine tradeable structure by construction. *Construction:* full-length (~15-year-equivalent) resampled paths, not 252-bar single-year worlds — a shorter world can't be scored against era_consistency/named_windows and would confound "rejected for insufficient history" with "correctly no edge." A cheap 252-bar variant is retained only as a pre-screen, not for the reported rate. Run at 2–3 block-length settings to bound Politis-Romano tuning sensitivity. *Stopping rule:* the naive floor is K=500; binomial-CI math (n≈z²p(1−p)/margin²) shows a ±0.5-point half-width near the policy reference p≈1% (D50) actually needs n≈1,521 — so K=500 is a screening budget, and Max should budget compute against ~1,500 as the realistic ceiling (Section 8). Reserve one independently-seeded battery (V6) for the sign-off number.

**V2 — Planted-signal recovery across mechanism shapes.** *Estimand:* recall — probability of Gold — for markets with a known, moderate edge over a null-matched noise floor, at several strength tiers across ≥3 mechanism shapes (trend, volatility-timing, mean-reversion). Tiers (illustrative: ~1.05×–1.60× terminal share-multiple) are self-generated scaffolding, not imported from any market — re-anchor once Streams 1/2/4 report the empirical share-multiple distribution among plausible TECL strategies. *Construction:* N draws per cell, signal planted before resampling; plant formula and expected effect frozen and verified before the pipeline sees it. *Stopping rule:* N=100/cell (≥12 cells) as an initial screen; CI half-widths near p=0.5 can approach ±10 points, possibly too wide to resolve a candidate bar — escalate N for the tier nearest the eventual bar. **No acceptance number is proposed.** An earlier "≥80% recall" bar was an unjustified import of the clinical-trial 80%-power convention with no transfer argument for Montauk's ~3–4-regime ceiling (G3); removed. Max sets the bar after reviewing the curve (Section 8).

**V3 — Behavioral-duplicate multiplicity sensitivity.** *Estimand:* does N_eff grow when search adds parameter points hashing to an *identical* trade path as an already-counted configuration, versus growing proportionally when it adds genuinely distinct clusters? *Construction:* a generic, arbitrarily-parameterized structural family built solely for this fixture — e.g., a two-lookback crossover with values chosen for reproducibility only, **not** matched to any registered or historically certified strategy, so the check is validated against a family-agnostic instrument rather than the incumbent's shape. Build 1×/10×/100× density batteries of near-identical-hash neighbors, plus a control battery of genuinely-distinct neighbors crossing known regime-sensitive thresholds. *Stopping rule:* one deterministic run per density level (hashing is exact); N_eff must not increase under identical-behavior densification and should increase with cluster count under genuinely-distinct densification. Any violation is a G19 defect, not a weight to retune.

**V4 — Seeded-defect detection.** *Estimand:* for each Section 7 defect class, probability the correctness/generalization planks reject it versus a known-clean control. *Construction:* exhaustive enumeration (small, deterministic library); run each variant repeatedly to confirm determinism. *Stopping rule:* every defect attempted, no early stop; a single miss on an "obvious" defect is an automatic audit failure requiring a fix — no CI softens a deterministic miss.

**V5 — Adversarial red-team frontier.** *Estimand:* minimum documented effort to produce one false Gold against the frozen contract, given the plain-English Gold contract but denied validator source and battery contents. *Construction:* a separate agent session (or Max) targets suspected blind spots. *Stopping rule:* fixed budget (500 attempts or 8 hours); any success becomes a new permanent fixture; repeat once per contract version.

**V6 — Blind/held-out battery replication.** *Estimand:* whether rates from the open, tuning-visible battery (V1–V5) replicate on an independently-seeded, never-inspected "sealed" battery. *Construction:* Battery A (open) and Battery B (sealed) from one shared seed registry; B opened only once, at sign-off. *Stopping rule:* run once per contract version; material divergence is itself a finding (simulator overfitting, Section 4) that blocks sign-off.

**V7 — Regime-change transition control.** *Estimand:* does the pipeline distinguish a genuine regime break from stable structure — refusing to certify a pre-change-only edge as durable, while still certifying an edge that holds on both sides? Distinct from fixture #15 (regime *concentration*), which is not a genuine break. *Construction:* concatenate two block-bootstrap segments with different volatility/dependence parameters (drawn from TECL's own calmest vs. most turbulent multi-year windows) at a known changepoint. Family (a) stale-edge (planted pre-change only) should reject or fail era-consistency; family (b) durable-edge (planted both sides) should stay Gold-eligible. *Stopping rule:* N=100 draws/family; report the fraction receiving the pre-declared correct verdict.

**V8 — Low-trade-count sufficiency control.** *Estimand:* is a genuinely good but sparsely-trading strategy correctly returned `insufficient` (D50) when trade count/regime coverage is too thin, and correctly Gold-eligible when sparse trades span adequate independent regimes? *Construction:* 3–5 synthetic strategies with sparse, well-spaced trades (roughly one per detected regime, per G3's ~3–4-regime ceiling) and a known planted edge: (a) too concentrated → `insufficient`; (b) adequate coverage → Gold-eligible. *Stopping rule:* deterministic, each run once; any mismatch is a D50-implementation defect, not a statistical near-miss.

---

## 4. Null, defect, and planted-signal controls

**Must pass.** Buy-and-hold TECL, a plain 200-day trend filter, and an exposure-matched coin-flip must receive predictable verdicts: buy-and-hold/coin-flip should almost never clear economic-passage (no edge beyond beta); the trend filter should show a modest, explainable edge and not be rejected for simplicity (D40).

**Must fail.** Every Section 7 defect (lookahead, impossible fill, date memorization, revised-vintage substitution, contamination) must be rejected deterministically, every time. The date-memorizer specifically tests the event-dependence diagnostic and the type system's refusal of literal date primitives — if "bar-index modulo N" smuggles a date lookup past the type system, that's a primitive-registry defect, not just a validator one.

**Planted signals must be recovered "often enough."** Montauk's mission is finding real edges, not rejecting everything doubtful. V2 must show the pipeline *can* certify a genuine, moderate edge across more than one mechanism shape — otherwise the lab silently calibrates toward maximum strictness, the same "invalid grader in the opposite direction" D40 warns against.

**Simulator overfitting — the method cheating on itself.** The risk is that tuning against these worlds teaches the validator their specific shape rather than general correctness. Four defenses: (1) **blind/sealed audit worlds (V6)**, the direct analogue of Dwork et al.'s reusable-holdout warning; (2) **ablation** — remove one candidate method at a time, rerun V1–V4; a method earns its keep only if removing it worsens rates on the *sealed* battery; (3) **adversarial review (V5)** — finds blind spots passive generation is unlikely to think of; (4) **frozen evaluation code** — the harness is versioned and content-addressed alongside the validator it tests, mirroring the protected-core seal, so a harness change is distinguishable from a validator change.

---

## 5. False-Gold and false-rejection consequences

The two error types are not symmetric. **False Gold is silent, delayed, and compounds:** a falsely-certified edge came from noise, search luck, or an undetected defect; because Max acts on the signal without re-litigating the pipeline, false Gold converts directly into real capital risk. The 20-bar Pending-Gold cooling window is a weak filter here — a noise-driven strategy's near-term forward behavior is also noise, so it can "look fine" through cooling into Active status before enough live bars reveal the problem. **False rejection is visible, immediate, and correctable:** the cost is legible (thin leaderboard; Max understands TECL's ~15-year, ~3–4-regime ceiling, G3, and waits). "An empty Gold board is an honest result" — false rejection degrades toward honest-empty; false Gold degrades toward dishonest-full.

**[Inference, not measured evidence]** Because false Gold is more expensive and hidden, the default operating point should plausibly sit closer to "accept some false rejection to suppress false Gold" than a naive symmetric error-cost analysis suggests. This is reasoned judgment, flagged as such rather than stated in the declarative register of Section 2's sourced claims — it is *not* empirically derived. It is consistent with the repo's asymmetric framing (D50's 1% annual aspirational false-Gold reference, with no analogous cap on false rejection), but this stream does not choose the operating point — that is Max's call (Section 8) — and recommends the false-reject rate always be reported alongside the false-Gold rate, never alone.

---

## 6. Assumptions and power/limits

- **Null worlds are models, not proof of "no edge."** Stationary-bootstrap nulls assume weak stationarity and short-range dependence; TECL's real history includes genuine regime shifts (2008, 2020, 2022) a resampled null does not manufacture new instances of. Passing V1 is evidence against false Gold *under this null model*, not proof no generative process could fool it.
- **The 252-bar confound is resolved, not eliminated.** An earlier V1 construction used single-year null worlds, which can't be scored against era_consistency/named_windows/G3's regime-count expectations — the real validator would reject nearly every draw for insufficient history, confounding "too short" with "correctly no-edge." V1 now runs full-length paths for its headline number; the residual limit is that even a full-length synthetic path encodes only as many distinct regimes as the block structure permits (~3–4, matching G3) — no resampling manufactures independent regime evidence the real market lacks.
- **Compute is real.** Every full-length V1/V2/V7 draw competes with live discovery for the same spare, preemptible cycles. The corrected V1 ceiling (~1,500 replicates, not 500) is materially more expensive than earlier drafts implied; Section 8 asks Max to set the budget, likely via a tiered screen-then-confirm approach.
- **No acceptance bar is imported from outside Montauk.** V2's recall bar and V1's false-Gold ceiling are left to Max, calibrated to Montauk's own ~3–4-regime ceiling, not clinical-trial or industry convention.
- **Fixtures are deliberately champion-agnostic.** No experiment or fixture presumes the outcome for any registered strategy's exact parameters; where a frozen structural control is needed (V3), it uses an arbitrary family invented for that purpose only, never a certification precedent.
- **Adversarial review has no completeness proof.** A red team that fails (V5) shows absence of an *easy* attack within budget and that team's creativity, not a guarantee no attack exists.
- **Behavioral-duplicate hashing (V3) assumes exact trade-path equality is the right proxy.** Slightly different timing but near-identical outcomes won't hash identically and could be under-counted; a fuzzy behavioral-distance metric is a harder, open question this stream flags but does not solve.

---

## 7. Required fixtures and durable artifacts

**Deterministic positive fixtures (must always pass; none reference a specific registered strategy).**
1. Matched TECL buy-and-hold, full history — no spurious edge beyond the comparator.
2. Plain 200-day-SMA trend filter — clears cleanly with a modest, explainable result; the "simple ≠ overfit" control.
3. A frozen, arbitrarily-parameterized synthetic dual-lookback crossover invented solely for this library (not any current/historical Active strategy) — confirms the harness executes deterministically end-to-end; explicitly **not** a stand-in for "known good" under 3.0 (D43).

**Deterministic negative (seeded-defect) fixtures — target 15–20, each with a name, expected-fail plank, version-pinned content hash:**

| # | Defect | Mechanism | Caught by |
|---|---|---|---|
| 1 | Same-bar close read | Signal uses same day's close, not verified close | Point-in-time contract |
| 2 | One-bar lookahead | Feature computed with `t+1` data | Causal prefix replay |
| 3 | Same-close fill | Filled at signal bar's close, not next-open | Execution/fill contract |
| 4 | Optimistic intraday fill | Entry at day's low, exit at day's high | Impossible-fill check |
| 5 | Revised-vintage substitution | T10Y2Y/DFF/3m-bill fed final-revision, not as-published | Point-in-time source contract (G8) |
| 6 | Literal date memorizer | Risk-on window hard-coded to a crash-recovery range | Event-dependence / date-literal ban |
| 7 | Disguised date memorizer | Same via "bar-index modulo N" | Event-dependence (must catch disguised) |
| 8 | Train/test contamination | Fold trains over its own test fold's label interval | Purge/embargo check |
| 9 | Future-outcome label leak | Feature uses the trade's own outcome | Leakage taxonomy (target-leak class) |
| 10 | Duplicate-behavior flood | 200 neighbors hashing to one trade path | Behavioral-duplicate / N_eff (G19) |
| 11 | Noise-feature soup | 100 noise indicators over 10,000 configs | Multiplicity / search-honesty |
| 12 | Non-finite arithmetic | NaN/Inf mid-backtest | Fail-closed correctness |
| 13 | Nondeterminism injection | Output differs across identical reruns | Determinism / reproducibility |
| 14 | Nested-CV false-independence | Post-test-block training misrepresented as OOS | CPCV applicability (D48) |
| 15 | Regime-narrow structural control | Entire edge is one hand-picked bull run | Regime/event-concentration diagnostic |

**Structural/behavioral controls (support V7/V8; not defects — correct verdicts are non-obvious):**

| # | Control | Mechanism | Correct verdict |
|---|---|---|---|
| 16 | Regime-change stale edge | Genuine changepoint; edge pre-change only | Reject / era-consistency failure |
| 17 | Regime-change durable edge | Same changepoint; edge both sides | Gold-eligible if valid |
| 18 | Sparse-trade insufficient evidence | 3–5 trades, too concentrated | `insufficient` (D50) |
| 19 | Sparse-trade adequate coverage | 3–5 trades, one per regime, adequate effect | Gold-eligible |

**Retained artifacts.** Every V1–V8 run against a frozen contract version produces one immutable, content-addressed report: seeds, K/N run, per-fixture pass/fail with hashes, false-Gold rate with CI, recall curve, V3 N_eff table, V5 red-team log — retained permanently (mirroring D37) and referenced in every future Gold certificate's control-report package. A contract version without a currently-attached report is not exam-complete.

---

## 8. Unresolved owner decisions

1. **How many full-length draws can the host afford, with discovery the only other consumer of spare cycles?** *Default:* budget ~1,500 full-length V1 replicates (the corrected CI ceiling near p≈1%, not the 500-draw floor) via a tiered screen (252-bar pre-filter) then confirm (full-length); treat further scale-up as deliberate. *Tradeoff:* tighter CIs compete with discovery throughput on one shared host.
2. **Who plays the adversarial red team (V5), and how often?** *Default:* a separate Claude Code session, given only the plain-English contract, denied validator source/battery contents, once per contract version. *Tradeoff:* cheap and repeatable but may share blind spots with the strategy-authoring AI; a paid human reviewer is out of scope (D54).
3. **How is sealed Battery B (V6) protected during tuning, and how often refreshed?** *Default:* generate once at project start from a separate seed registry; open once per sign-off; refresh only with a signed core-release bump (D42/D43's recert trigger). *Tradeoff:* too-rare refresh risks familiarity over years; too-frequent reduces replication value.
4. **Full ablation matrix every version, or only on changed methods?** *Default:* full matrix at major bumps; incremental at minor bumps. *Tradeoff:* only full reruns catch interaction effects between unchanged methods, but they are the most expensive item here.
5. **Minimum planted-signal recall rate (V2), and does it differ by mechanism/control type?** *Default:* Max reviews the empirical power curve once it exists rather than pre-committing. No number is proposed here — an earlier "≥80%" was an unjustified clinical-trial import with no argument for Montauk's regime ceiling, and is removed. Any bar Max sets should cite G3, not outside convention, and should be revisited once V7/V8 show whether regime-change and low-trade-count controls need a different bar than the mechanism-shape cells.

---

## References

**Primary sources (cited above with page/DOI where available):**

- Hans R. Künsch (1989), "The Jackknife and the Bootstrap for General Stationary Observations," *Annals of Statistics* 17(3):1217–1241.
- Dimitris N. Politis and Joseph P. Romano (1994), "The Stationary Bootstrap," *JASA* 89(428):1303–1313.
- David H. Bailey, Jonathan Borwein, Marcos López de Prado, and Qiji Jim Zhu (2015/2016), "The Probability of Backtest Overfitting," *Journal of Computational Finance*.
- Shachar Kaufman, Saharon Rosset, Claudia Perlich, and Ori Stitelman (2012), "Leakage in Data Mining: Formulation, Detection, and Avoidance," *ACM TKDD* 6(4), Art. 15. DOI: 10.1145/2382577.2382579.
- Tsong Yueh Chen, S. C. Cheung, and S. M. Yiu (1998), "Metamorphic Testing: A New Approach for Generating Next Test Cases," Tech. Report HKUST-CS98-01 (located via secondary citation, not independently retrieved); surveyed in Chen et al. (2018), "Metamorphic Testing: A Review of Challenges and Opportunities," *ACM Comput. Surv.* 51(1).
- Yue Jia and Mark Harman (2011), "An Analysis and Survey of the Development of Mutation Testing," *IEEE TSE* 37(5):649–678.
- Cynthia Dwork, Vitaly Feldman, Moritz Hardt, Toniann Pitassi, Omer Reingold, and Aaron Roth (2015), "The Reusable Holdout: Preserving Validity in Adaptive Data Analysis," *Science* 349(6248):636–638.

**Secondary / project-internal (grounding only; not external evidence):** `validation-engine-hardening.md` (G1–G19 gap register, Phase 1 mandate) · `validation-audit-findings.md` (legacy `deflate.py` audit, D-1–D-5) · `decisions.md` (D40, D42–D55) · `rust-strategy-and-evaluation-policy.md` (typed primitive registry, protected-core seal) · `implementation-plan.md` (Stage 5–6, cohort certification).

Not cited: White (1995) Reality Check, Hansen (2005) SPA, Romano-Wolf (2005) step-down, and Morris (1991) sensitivity — already verified in `validation-engine-hardening.md` §7 and Streams 1/2's subject, not this stream's; named only, not re-verified here.

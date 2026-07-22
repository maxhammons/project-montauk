# Montauk 3.0 — Research Lead Conclusion (Phase 1 Evidence Package)

**Role:** Independent, skeptical research lead.
**Scope:** Montauk 3.0 — a single-user, TECL-only, long/flat, daily strategy appliance.
**Date:** 2026-07-22.
**Mandate:** Establish what *Gold* must mean — the strongest **honest** evidence that an *exact, frozen* strategy configuration (a) is not detectably overfit and (b) should beat *matched TECL buy‑and‑hold* under obtainable execution (signal formed after a verified daily close, filled at the next regular‑session open plus calibrated costs, $10,000–$100,000 notional) — and lay out the research program that earns that word.

> **Bottom line up front.** Montauk 3.0's Gold promise is achievable, but only as a *contract that validates itself before it is trusted*. The binding constraint on everything is **data scarcity**: ~17.5 years of real TECL history (inception **2008‑12‑17**; ~4,401 real‑labeled rows in `data/TECL.csv`) containing on the order of **3–4 materially independent macro regimes**. No statistical method widens that ceiling. The correct posture is therefore not "run more tests," but "run a *small, complete, self‑audited* contract, freeze it before looking at results, prove it catches planted defects and clears known nulls, and be willing — often — to say *insufficient evidence* rather than manufacture confidence." The single most important design principle that emerged independently across streams: **do not import thresholds from unrelated markets, and never let the same evidence both tune and certify a method.**

---

## How this package was produced (provenance & integrity)

Ten specialist research streams were run, each as a three‑stage pipeline: (1) a researcher drafted with primary sources, (2) an **independent adversarial skeptic** tried to refute the draft and did targeted web spot‑checks, (3) a finalizer folded valid critiques in. Orchestration was Opus 4.8; **all 30 subagents were Sonnet 5**. Every stream returned `needs_revision` from its skeptic except Stream 7 (`major_gaps`); all revisions were applied. The adversarial layer caught, and the finalizers fixed, real defects — imported thresholds, citation/venue errors, inference presented as evidence, and internal contradictions (see the per‑stream *Residual risks* and the **Integrity ledger** at the end).

**This document distinguishes evidence from inference explicitly.** Tags: `[Evidence: primary]`, `[Evidence: secondary]`, `[Inference]`. Expert or model opinion is *not* evidence and cannot award Gold.

### The ten stream reports

| # | Stream | File | Skeptic verdict (pre‑fix) |
|---|--------|------|---------------------------|
| 1 | Phase 1 program design | [`1-Phase 1 program design/phase-1-program-design.md`](1-Phase%201%20program%20design/phase-1-program-design.md) | needs_revision |
| 2 | Continuous adaptive multiple testing | [`2-Continuous adaptive multiple testing/continuous-adaptive-multiple-testing.md`](2-Continuous%20adaptive%20multiple%20testing/continuous-adaptive-multiple-testing.md) | needs_revision |
| 3 | Validator‑of‑validator laboratory | [`3-Validator-of-validator laboratory/validator-of-validator-laboratory.md`](3-Validator-of-validator%20laboratory/validator-of-validator-laboratory.md) | needs_revision |
| 4 | Economic gate & low‑sample inference | [`4-Economic gate and low-sample inference/economic-gate-and-low-sample-inference.md`](4-Economic%20gate%20and%20low-sample%20inference/economic-gate-and-low-sample-inference.md) | needs_revision |
| 5 | TECL data, B&H & opening execution | [`5-TECL data, B&H, and opening execution/tecl-data-bah-and-opening-execution.md`](5-TECL%20data%2C%20B%26H%2C%20and%20opening%20execution/tecl-data-bah-and-opening-execution.md) | needs_revision |
| 6 | Synthetic TECL reconstruction | [`6-Synthetic TECL reconstruction/synthetic-tecl-reconstruction.md`](6-Synthetic%20TECL%20reconstruction/synthetic-tecl-reconstruction.md) | needs_revision |
| 7 | Rust sandbox & software supply chain | [`7-Rust sandbox and software supply chain/rust-sandbox-and-software-supply-chain.md`](7-Rust%20sandbox%20and%20software%20supply%20chain/rust-sandbox-and-software-supply-chain.md) | **major_gaps** |
| 8 | Independent reproduction & numerical determinism | [`8-Independent reproduction and numerical determinism/independent-reproduction-and-numerical-determinism.md`](8-Independent%20reproduction%20and%20numerical%20determinism/independent-reproduction-and-numerical-determinism.md) | needs_revision |
| 9 | Durability, availability & dead‑man monitoring | [`9-Durability, availability, and dead-man monitoring/durability-availability-and-dead-man-monitoring.md`](9-Durability%2C%20availability%2C%20and%20dead-man%20monitoring/durability-availability-and-dead-man-monitoring.md) | needs_revision |
| 10 | Ranking & human decision quality | [`10-Ranking and human decision quality/ranking-and-human-decision-quality.md`](10-Ranking%20and%20human%20decision%20quality/ranking-and-human-decision-quality.md) | needs_revision |

---

## 1. One‑page plain‑English conclusion

Montauk 3.0 wants one thing: **the most defensible daily TECL `risk_on`/`risk_off` call, with an honest account of why it deserves trust.** Gold is the certificate that says "we looked hard and found no disqualifying overfit or correctness failure, and on real data this exact strategy beat just holding TECL." It is *not* a promise about tomorrow.

Six things must be true for that certificate to be worth anything, and the research says how to get each:

1. **Prove the exam before you trust the grade.** Before certifying any strategy, build a *"fake‑evidence factory"* — control worlds with **known** answers (pure‑noise strategies that should fail; a planted, recoverable signal that should pass; strategies with deliberate cheating like look‑ahead or impossible fills that should be caught). Run Montauk's *entire* author→search→select→certify loop on them. Measure how often it wrongly awards Gold and how often it wrongly rejects a real edge. Freeze the method **first**, then test it on a **sealed** set of worlds it never saw. (Streams 1, 3.)

2. **Count the searching, honestly and forever.** An always‑on factory that invents strategies indefinitely will *eventually* find something that looks great by luck. Control this with two layers: a within‑day batch test that accounts for how similar the day's candidates are to each other, plus a **lifetime "betting budget"** that gets spent as certificates are issued and never resets (except on an explicit, signed core change). Critically: **a future search never retroactively cancels an already‑issued Gold certificate** — only live forward performance can. (Stream 2.)

3. **Measure "beats B&H" with a ruler that respects the calendar.** A 1.10× terminal result over 17 years and a 1.10× over 5 years are *not* the same evidence. Keep the terminal share/wealth multiple as the headline (Max‑facing), but always show it next to a horizon‑normalized rate and a **one‑sided lower bound** computed by resampling the *price path* and re‑running the whole strategy from scratch. When the trailing‑5‑year window is effectively one regime, the honest verdict will often be **insufficient evidence** — and that is a correct answer, not a failure. (Stream 4.)

4. **Nail down the data and the trade.** Gold's literal claim — "verified close → next‑open fill → beats matched B&H" — collapses if the close is wrong, the B&H benchmark isn't total‑return, or Max's broker can't actually reach the opening auction. Build an **executable source registry** and a **failure‑state table**, verify the official close, and treat *"can this broker submit an opening‑auction order?"* as a **hard live‑deployment gate.** (Note: `data/TECL.csv` is split‑adjusted but **not** confirmed total‑return‑adjusted.) (Stream 5.)

5. **Keep the machine honest and alive.** The engine must be **deterministic and independently reproducible** (two implementations against one frozen spec, plus hand‑derived fixtures — because two coders can share the same misreading). The autonomous agent must be **contained** (it proposes typed specs; a protected Rust core decides; the risky "escape hatch" that compiles agent Rust stays disabled until it passes a containment suite). And nothing durable may be **silently lost** — authority/Gold/signal state replicates synchronously to a second local device, GitHub is a monitored async backup that never blocks the signal, and an **independent, read‑only dead‑man alert** fires if Montauk goes quiet. (Streams 7, 8, 9.)

6. **Make the human decision small and unambiguous.** On top of the Gold board, add only the minimum: a *disclosure‑only* "leader not clearly separated" flag (which must **not** block the recommendation itself), and a switch‑confirmation card that visibly distinguishes a *pointer‑only* rank change from an *immediate opposite‑state trade instruction.* Audit the ranking score so a passed Gold gate isn't also silently inflating the score (no double‑counting). (Stream 10.)

**The unifying discipline:** preregister the estimand and stopping rule; generate operating points from Montauk's *own* controls, never borrowed numbers; label evidence vs. inference; and prefer an honest null to a confident guess. Because Montauk trades a **3×‑levered** ETF with **manual** execution, a false Gold is not one bad trade — it compounds real capital loss with loss of trust in the whole appliance. That asymmetry should tilt every ambiguous call toward *not* certifying.

---

## 2. Cross‑stream evidence‑quality table

Load‑bearing claims behind the recommendations, with honest strength labels. "Transfers?" asks whether a result derived elsewhere applies to a single 3×‑levered daily tech ETF with ~17.5 yr of real history.

| # | Claim | Evidence type | Source (primary unless noted) | Strength | Transfers to TECL? |
|---|-------|---------------|-------------------------------|----------|--------------------|
| 1 | Many defensible analytic choices inflate false positives even without deliberate p‑hacking ("garden of forking paths") | Primary paper | Gelman & Loken 2013/2014 | Strong (logical argument, not population‑tied) | Yes — mechanism applies to any adaptive analyst |
| 2 | Model‑selection variance creates selection bias of a magnitude comparable to real method differences; nested CV is the remedy | Primary paper | Cawley & Talbot, *JMLR* 11 (2010) | Strong (abstract fetch‑verified) | Structurally yes; benchmark magnitudes do **not** transfer numerically |
| 3 | The probability that the *best‑of‑many* searched config is overfit can be estimated (CSCV/PBO) | Primary paper | Bailey, Borwein, López de Prado & Zhu, *J. Computational Finance* 20(4) (2017) | Strong, peer‑reviewed | Target transfers; **no fixed numeric cutoff transfers** |
| 4 | Online/adaptive testing can control error over an unbounded stream (alpha‑investing / LORD / SAFFRON / e‑values) | Primary papers | Foster & Stine 2008; Javanmard & Montanari 2015/2018; Ramdas et al. 2018/2019; Vovk & Wang 2021 | Strong for the *ratio* (mFDR) bound | Mechanism transfers; **absolute** false‑Gold count must be measured, not assumed |
| 5 | Batch data‑snooping correction for a whole search (Reality Check / SPA / step‑down) | Primary papers | White 2000; Hansen 2005; Romano & Wolf 2005 | Strong | Method transfers; operating point must be re‑derived on Montauk controls |
| 6 | A "reusable holdout" can preserve validity across many adaptive queries **under i.i.d. sampling** | Primary paper | Dwork et al., *Science* 349 (2015); Blum & Hardt 2015 | Strong (mechanism); **i.i.d./bounded‑budget applicability to TECL is [Inference]** | Warning transfers; formal guarantee likely does **not** (serial dependence) |
| 7 | Sharpe/performance inference must correct for serial dependence; daily counts overstate effective N | Primary paper | Lo 2002, *FAJ* | Strong | Yes — mechanism applies to any daily log‑wealth‑difference statistic |
| 8 | Dependence‑preserving resampling for dependent returns (stationary/block bootstrap; automatic block length) | Primary papers | Politis & Romano 1994; Politis & White 2004 / Patton‑Politis‑White 2009 | Moderate* (*Politis‑Romano 1994 paywalled 403; not re‑verified against primary text this pass) | Yes for the resampling target; block length must be data‑derived, never copied |
| 9 | Leveraged daily‑rebalanced ETF returns are path‑dependent ("volatility decay") | Primary papers | Cheng & Madhavan 2009; Avellaneda & Zhang 2010 | Strong | Yes — TECL is exactly this product class |
| 10 | Real TECL is **not** one continuous index series: traded as TYH vs. Russell 1000 Tech until ~2012‑06‑29; Tech Select Sector Index reconstituted by the Sept‑2018 GICS Comm‑Services split | Product‑primary | Select Sector SPDR Form 497 (2018‑06‑19); S&P/GICS methodology | Strong (directly fetched) | Directly — both seams are currently **unrecorded** in `data/manifest.json` |
| 11 | Normal declarative StrategySpec path has **no** build‑time supply chain (no `Cargo.toml`/`build.rs`/proc‑macros); compilers/crates/`unsafe` enter **only** via the escape hatch | Product‑primary (project docs) + inference | `rust-strategy-and-evaluation-policy.md`; RustSec advisory DB | Strong for the architecture; "compile threat absent on normal path" scoped as [Inference] | Directly |
| 12 | Independent teams implementing one spec still share correlated bugs (N‑version independence is not free) | Primary paper | Knight & Leveson 1986, *IEEE TSE* | Strong (PDF‑verified; corrected from a misquote) | Qualitative lesson transfers; the 1986 failure **rate** does not |
| 13 | Floating‑point summation is order‑dependent; parallel reductions are nondeterministic without pinned order | Primary | IEEE 754‑2019; Goldberg 1991; Ahrens/Demmel/Nguyen reproducible summation | Strong | Yes |
| 14 | 3‑2‑1 backups, RPO/RTO, WORM/object‑lock, append‑only repos are standard durability primitives; GitHub file/LFS limits make it unsuitable for high‑volume DB blobs | Product‑primary | GitHub docs (file‑size/LFS); restic/Borg; S3 Object Lock; (CISA 3‑2‑1 — **fetch failed 403, unverified**) | Strong except CISA row | Yes |
| 15 | Human‑factors effect sizes (risk communication, alert fatigue, decision noise) are medicine/general‑judgment research | Secondary/primary | Gigerenzer & Edwards 2003; Kahneman et al. 2021; alert‑fatigue lit | Moderate | **Only qualitative mechanisms transfer; numeric effect sizes do not** |

\* Unverified/weak‑sourced rows are flagged in the **Integrity ledger**. They are honestly downgraded rather than presented as settled.

---

## 3. Recommended Montauk experiment — the Phase 1 program (preregistered)

The correct deliverable is **not** one experiment but a **dependency‑ordered, preregistered program** that ends in a single signed contract. Below is the master estimand, the dependency order, and the stopping/ratification rule. Each stream report holds the detailed per‑study estimand and stopping rule; this is the spine that connects them.

### 3.1 The master estimand

> **For a validator version `V` and a frozen operating point, estimate the appliance‑level annual probability of a *false Gold* (certifying a configuration whose true forward edge over matched TECL B&H is ≤ 0) and the probability of *false rejection* (failing to certify a configuration with a genuine, recoverable planted edge), as measured by running Montauk's complete author→search→select→certify loop over predeclared control worlds.**

The owner‑facing performance result remains the **terminal TECL‑equivalent wealth/share multiple vs. matched B&H** on each required real horizon (per charter/D46), always paired with a horizon‑normalized rate and a one‑sided lower bound. The 1% annual any‑false‑Gold figure is an **aspirational reference point to plot the frontier against, not an imported cutoff.**

### 3.2 Dependency order (what freezes before what)

```
FREEZE FIRST (no results peeking):
  P1-00  Preregistration: objective, estimand, decision roles, target operating characteristics
  S5     Data + execution contract: official-close verification, total-return B&H,
         next-open fill model, broker opening-auction obtainability (HARD live gate)
  S4     Economic-passage estimand: terminal-ratio headline + horizon-normalized rate
         + one-sided lower bound method (full causal path resimulation)
        │
        ▼
BUILD THE EXAM (calibration worlds; method still tunable here, on CALIBRATION controls only):
  S3/P1-01  Control-world battery A (calibration): dependence-preserving nulls,
            trade/exposure-matched random rules, noise families, event/date memorizers,
            seeded look-ahead/repaint/fill defects, frozen structural controls,
            planted recoverable signals, regime-change + low-trade-count controls
  S2        Search-honesty method bake-off: within-epoch batch (Reality Check/SPA/
            Romano-Wolf) + lifetime online wealth ledger (LORD/SAFFRON/e-values)
  S6        Synthetic overlap study (PARALLEL, diagnostic-only): calibrate builder on
            Block 2 (2012-06-29..2018-09-20), test ONCE on Block 3 (2018-09-21..present),
            Block 1 read-only contamination diagnostic
        │
        ▼
ENGINEERING GATES (must pass before autonomous scale; PARALLEL with the above):
  S8   Determinism + independent-reproduction parity matrix (tolerance ladder from data)
  S7   Sandbox containment suite + StrategySpec parser hardening + reproducible builds/signing
  S9   Durability tiers + independent read-only dead-man alert (drilled)
        │
        ▼
LOCK + TEST ONCE (no more tuning):
  Freeze validator version V; run the FULL loop once on a SEALED audit battery (Battery B)
  the method never saw. Plot the false-Gold / false-rejection FRONTIER.
        │
        ▼
RATIFY:
  Max chooses the operating point on the frontier; S10 ranking/switch surface is set;
  the contract is signed. Only Max declares Phase 1 complete.
```

### 3.3 Stopping rule (program‑level)

- **Calibration → lock:** method parameters may be tuned **only** against calibration controls (Battery A) and Montauk's own search ledger. When the plots stabilize, **lock the validator version.** Current and historical leaderboard rows are **never** threshold‑training data.
- **Sealed evaluation → one shot:** run once on Battery B (worlds generated at project start, opened once). No re‑tuning after opening. A method survives only if it **catches a relevant seeded defect missed elsewhere** *or* **materially improves calibration** without an unacceptable false‑reject or complexity cost (ablate one method at a time).
- **Sample‑size honesty:** report the estimate **with its confidence interval**; a wide interval near the policy‑relevant region (e.g., p≈1% false Gold) is an **honest** result. Do not manufacture controls to narrow it artificially; disclose the compute‑limited replicate ceiling (Stream 3 estimates ~1,500 full‑length synthetic replicates near p≈1%, **not** a 500‑draw floor).
- **Forward, not retroactive:** after launch, every frozen verdict is compared to its immutable live‑forward ledger. Recalibration is a Max‑authorized *new signed contract version*, never an autonomous reaction to an inconvenient outcome. **A new search never edits an issued Gold certificate.**

---

## 4. Null, defect, and planted‑signal controls

Consolidated from Streams 1, 2, 3, 7, 8 (each stream owns the detailed fixtures). A validator that cannot post the *expected* verdict on every one of these is not ready.

**Null worlds (must NOT earn Gold):**
- Dependence‑preserving null returns (stationary/block bootstrap of TECL that destroys any edge but preserves autocorrelation/vol‑clustering).
- Exposure‑ and trade‑count‑matched random long/cash rules.
- High‑dimensional **noise families** searched over many configurations (the pure‑multiplicity trap).
- **Event/date memorizers** (strategies that encode specific calendar dates rather than a mechanism).
- Static all‑cash (must **fail** economic passage tautologically — a sanity check that the gate has teeth).

**Seeded‑defect worlds (must be CAUGHT and classed as correctness failures, not economic verdicts):**
- Look‑ahead / repaint; impossible or too‑good fills; data leakage/contamination.
- Nondeterminism injection (off‑by‑one bar; flush‑to‑zero/denormals; stale tzdata; shuffled/duplicated rows; silently reduced Monte‑Carlo resample count).
- CPCV false‑independence; behavioral‑duplicate flood (thousands of near‑twins that must not count as independent hypotheses).
- StrategySpec DoS (over‑depth graph, over‑large expansion, integer‑overflow) — an **availability** failure, distinct severity class.
- Escape‑hatch containment breaches (network egress, credential access, writes outside the output path, resource‑limit evasion, future‑leak canary).

**Planted‑signal worlds (a genuine, recoverable edge that SHOULD earn Gold):**
- Several mechanism *shapes* (trend, mean‑reversion, volatility‑state) with a known true edge, to measure recall/power — deliberately **not** the current champion's family, to stay champion‑agnostic.

**Structural / positive controls:**
- Static buy‑and‑hold (must tautologically pass economic passage as the reference).
- Frozen simple structural strategies (e.g., 200‑day SMA) with fixed expected verdicts for drift detection.

**Anti‑simulator‑overfitting defenses (so the lab doesn't teach the validator to pass its own tests):**
sealed/blind Battery B opened once; one‑method‑at‑a‑time ablation; adversarial red‑team (a separate agent invocation denied the validator source and battery contents); and a **frozen evaluation harness** whose acceptance artifacts are content‑addressed and retained permanently. Adversarial review demonstrates *absence of an easy attack within a budget*, **not** a completeness proof — state that limit plainly.

---

## 5. False‑Gold and false‑rejection consequences

Every stream converged on the same asymmetry, and it should govern the operating point:

| Error | What it costs | Character |
|-------|---------------|-----------|
| **False Gold** (certify a non‑edge) | Max manually executes a real position change on a **3×‑levered** ETF that isn't actually better than holding. Drawdown compounds real capital loss **and** erodes trust in the whole appliance. | **Whole‑program**, hard to reverse. |
| **False rejection** (miss a real edge) | Board sits at "no Gold"; Montauk runs an inferior or no signal. An empty board never lowers the standard (charter). | Forgone but **recoverable** performance; asymmetrically cheaper. |

**Therefore, bias every ambiguous call toward *not* certifying** — accept some loss of planted‑signal power to keep known‑null false‑Gold low.

**A second, worse class of error is correlated.** Streams 7–9 identify failures that don't hurt one row but **every** row at once: a leaky sandbox/escape hatch that manufactures a false Gold via a data leak; a compromised or non‑reproducible core build that every downstream verdict inherits; silent state loss or a silently‑failed dead‑man monitor. These deserve **stricter** gates than any per‑strategy threshold, because a single failure invalidates the entire leaderboard simultaneously. Missed‑heartbeat **false negatives** (Montauk dies quietly) are the single most severe operational failure in a single‑user system with no team backstop; missed‑heartbeat **false positives** (alert fatigue) are dangerous because they train Max to ignore the alarm exactly when it matters.

---

## 6. Assumptions and power/limits

- **The data ceiling is the master limit.** ~17.5 years of real TECL (inception 2008‑12‑17), on the order of **3–4 independent macro regimes**. The trailing‑5‑year window is plausibly **one** dominant regime for evidentiary purposes. No bootstrap, HAC correction, or resampling scheme manufactures independent‑regime evidence the data don't contain. Expect frequent, **honest "insufficient evidence"** verdicts — especially on the 5‑year gate. (Streams 1, 3, 4, 6.)
- **Daily observation counts overstate effective sample size** (serial dependence; Lo 2002). Champion‑scale strategies make **<20 trades**, so trade‑level inference (bootstrap, minimum‑track‑record‑length) yields wide bounds that must be reported wide, not narrowed. (Stream 4.)
- **Synthetic history is diagnostic‑only** and, once the pre‑2012 TYH/Russell index‑mismatch block is correctly excluded from calibration, the overlap study has **exactly one genuine held‑out block** (Block 3, <8 years) against one calibration block (Block 2, ~6 years) — a fragile, single‑split design. Financing costs are excluded from TECL's capped expense table, so the financing haircut must be **back‑solved from realized NAV drag**, not fit to a disclosed rate. (Stream 6.)
- **Stationarity across TECL's regime‑shifting span is an assumption, not a fact** — block‑bootstrap validity rests on it; disclose a sensitivity check. (Stream 4.)
- **Correlation/effect sizes from other domains do not transfer numerically** — only mechanisms do. This applies to clinical/financial statistical conventions *and* to human‑factors research. Any operating number must be generated from Montauk's own controls. (Streams 3, 4, 10.)
- **Independent reproduction bounds confidence but does not replace spec review** — two implementations can share a misreading of the prose spec and pass every parity fixture; hand‑derived fixtures are required. RNG parity across Python (PCG64) and Rust (ChaCha12) cannot be bit‑exact; the right target is **distributional** parity, and this remains **unresolved** until a second implementation of the validation math exists. (Stream 8.)
- **Adversarial review is bounded, not a proof.** Absence of an easy attack within one red team's budget is evidence, not a guarantee. (Streams 3, 7.)

---

## 7. Required fixtures and durable artifacts

Every safety‑ or evidence‑critical step gets **at least one positive fixture, one seeded‑negative fixture, a deterministic expected result, and a retained acceptance artifact.** "The whole pipeline passed" must never hide an untested internal step. Consolidated:

- **Preregistration & method records:** `phase1-preregistration-v1.md`; frozen control‑world battery + `expected-verdicts.json`; holdout/reveal ledger schema + ledger; method‑bakeoff report; search‑honesty method spec; **validator‑of‑validator report** (seeded defects caught, nulls cleared, false‑Gold/false‑reject estimates, known limits) — this report *validates the exam*; it is **not** another per‑strategy score.
- **Economic gate:** constant‑edge horizon‑invariance fixture; hindsight‑collapse fixture (the lower bound must actually collapse a hindsight point estimate); path‑resimulation‑vs‑trade‑resampling parity artifact (audit against silent downgrade to the cheaper wrong method); per‑row retained bootstrap replicate distributions.
- **Data/execution:** an **executable source registry** (data type → primary endpoint → fallback → cadence → verification) and a **failure‑state table** (failure → detection → system state → recovery); golden split/distribution files; seeded negatives for split‑blindness, vendor staleness, auction mislabeling, vendor revision, delayed open.
- **Synthetic overlap:** frozen block boundaries + fitted parameters + held‑out metrics tied to a bumped `synthetic_model_version`; structural‑break fixtures for 2012‑06‑29 and 2018‑09‑21; a hand‑computed toy fixture cross‑checked against the Avellaneda‑Zhang closed form.
- **Determinism/parity:** the 7‑class parity fixture matrix (signals, fills, trades, daily wealth, B&H, verdicts, + an RNG‑dependent statistical‑parity class); the data‑derived **tolerance ladder** (bit‑exact for categorical outputs, measured tolerance for floats, tightest on the primary Gold number); pinned toolchain/CPU flags + tzdata version.
- **Sandbox/supply chain:** escape‑hatch containment battery (six binary checks incl. future‑leak canary); StrategySpec parser adversarial battery; reproducible‑build artifact (two independent build hashes + diff per release); dependency‑audit + SBOM + signing/revocation runbook (drilled).
- **Durability:** golden control‑DB fixture + manifest; restore‑drill ledger; **second‑device read‑back verification log** (on every synchronous write); dead‑man fire‑drill log; key‑recovery ceremony record; PAR2 parity sidecars for cold archives.
- **Ranking:** synthetic leaderboard ground‑truth panel; historical churn‑replay; switch‑confirmation copy matrix (ambiguity‑flag × pointer‑only/opposite‑state); double‑counting seeded‑defect fixture; drawdown/catastrophe disclosure‑completeness fixture.

---

## 8. Unresolved owner decisions

These require Max. Ordered by leverage. Each carries a recommended default from the streams; the default is a starting point, not a foregone conclusion.

**A. Economic gate & sample size (highest leverage).**
1. **Confidence level for the one‑sided lower bound** (Stream 4). Recommended default **one‑sided 90%** — explicitly a business‑continuity judgment, *not* statistically derived. 95% would return "insufficient evidence" for nearly every candidate at TECL's data ceiling. *Only Max can set the false‑Gold/false‑reject operating point.*
2. **Does the trailing‑5‑year gate get its own uncertainty‑aware lower bound**, or stay a disclosed point‑estimate diagnostic subordinate to the full‑history gate? (Stream 4.)
3. **How is "insufficient evidence" on one window (clean on the other) represented for Gold eligibility** — non‑passing but visually distinct from a hard fail (recommended), or a soft pass? (Stream 4.)

**B. Search‑honesty policy (whole‑program risk).**
4. **Is the aspirational 1% a *lifetime* wealth budget or *annual*?** The charter's literal wording is **annual**; a lifetime budget is a genuine, disclosed **policy departure** requiring Max's explicit sign‑off. (Stream 2.)
5. **Does a new optimizer/fitness/campaign ever justify a fresh wealth sub‑ledger?** Recommended **no** — inherits the lifetime ledger unless a signed core‑version release. (Stream 2.)
6. **Does external‑feature "fishing" draw against the same wealth ledger as strategy‑logic search?** Recommended **yes, same ledger** — a separate one is a gaming loophole. (Stream 2.)

**C. Data & execution (hard live‑deployment gate).**
7. **Which broker will actually submit the after‑close order, and does it demonstrably reach the NYSE Arca opening auction?** This is a **hard gate** on any Gold row being treated as live‑tradeable. Schwab opening‑auction support is currently **undocumented** (the top live blocker). (Stream 5.)
8. **Resolve the expense‑ratio ambiguity** (0.95% cap vs. 0.87% disclosed net) and version‑stamp it. (Stream 5.)
9. **Acquire intraday/quote data, or formally accept a documented conservative cost *range*** rather than a TECL‑specific point estimate for the $10k–$100k band? (Stream 5.)
10. **Confirm/record the two synthetic seams** (TYH/Russell‑1000‑Tech pre‑2012; GICS 2018 index reconstitution) in `data/manifest.json`, and confirm whether TECL.csv should carry a **total‑return** series for B&H. (Streams 5, 6.)

**D. Engineering & operations.**
11. **Sandbox posture:** ban all third‑party crates in the escape hatch (recommended, until shown too restrictive) vs. a vetted allowlist; OS sandboxing first (seccomp+namespaces+cgroups) vs. adding a microVM layer; hardware‑backed offline signing key (recommended). Set concrete StrategySpec parser caps (recursion depth, expansion count). (Stream 7.)
12. **Determinism:** primary‑metric tolerance and safety factor (derive empirically, not a round number); allow transcendental primitives with wider tolerance vs. exclude; pin/disable SIMD on the wealth‑path summation (recommended); **RNG parity = distributional vs. bit‑exact** (recommended distributional — unresolved until a second implementation exists). (Stream 8.)
13. **Durability:** which independent read‑only heartbeat provider + receive‑only alert channel; whether to add a WORM off‑machine copy beyond GitHub; concrete RPO/RTO per state class (RPO=0 holds only for process/software failure — the physical‑disaster case is up to ~1 hr via GitHub; is that residual acceptable?); real second local device vs. application‑level dual‑write (recommended real device — dual‑write has an unresolved atomicity gap). (Stream 9.)

**E. Ranking & human decision.**
14. **Confidence level for "leader not clearly separated"** (default pre‑registered 90% with a mechanical fallback to 75%, decided *before* fixtures run) — and confirm the flag is **disclosure‑only** and does **not** gate the Recommended pointer (charter §9.1). (Stream 10.)
15. **Friction for an opposite‑state switch** (default: mandatory two‑step confirmation with inline drawdown/catastrophe evidence) and re‑trigger delta for a dismissed recommendation. (Stream 10.)

**F. Governance / cross‑stream.**
16. **What counts as "measurably distinct information" to admit a third Montauk Score pillar?** Recommended: it must flip at least one control's classification via a predeclared test, not a post‑hoc leaderboard judgment. (Stream 1.)
17. **Who plays the adversarial reviewer**, and how are calibration slices kept blind from it? Recommended: Max reviews final artifacts personally; AI adversarial review comes from an invocation blind to calibration results. (Streams 1, 3.)

---

## Integrity ledger (what remains unverified — read before trusting a citation)

In the spirit of "distinguish evidence from inference," these are the honest gaps the streams disclosed. None invalidate a recommendation, but each should be closed before the cited claim is treated as settled primary evidence:

- **Stream 4:** Politis & Romano (1994) and Newey & West (1987) returned 403/paywalled; no open‑access mirror found this pass. Both are textbook‑standard methods, but their evidence rows are honestly downgraded to Moderate/secondary‑sourced. The exact paper‑of‑origin for the "~3.26 expected‑max Sharpe at 1,000 trials" figure (DSR vs. companion) could not be confirmed by primary quote.
- **Stream 5:** Delayed‑open rule mechanics sourced via search, not a re‑verified primary fetch (SEC EDGAR rate‑limited). CRSP field‑level total‑return formula is a reconstruction, not a verbatim quote. Vendor OHLC revision/backfill history never audited.
- **Stream 9:** The CISA 3‑2‑1 primary page failed to fetch (403) across HTML/PDF/archive; the OpenZFS admin page was bot‑blocked. The 3‑2‑1 principle is uncontroversial, but the specific citation is unverified.
- **Stream 10:** The OECD/JRC composite‑indicator handbook passage on double‑counting/correlation remains unverified via primary text after two attempts; Experiment C's own statistic is self‑contained and can proceed regardless. The Model Confidence Set's multiple‑testing limitation is sourced only to the repo's own hardening notes.
- **Cross‑stream figure reconciliation:** the verified real‑TECL history is **~17.5 years / ~4,401 real rows** (Streams 1, 4 corrected an understated "~15 years"). Some stream bodies still say "~15 years"; where they do, read **~17.5**. The independent‑regime count is **~3–4** and is the operative constraint regardless of the exact year figure.

---

*Prepared as an independent research package for Montauk 3.0 Phase 1. It identifies risks and methods and lays out the program that would produce Gold‑worthy evidence; it does not itself award Gold. Per the charter, the studies above must be reviewed and frozen into a signed contract before the autonomous conveyor can certify, and only Max declares Phase 1 complete.*

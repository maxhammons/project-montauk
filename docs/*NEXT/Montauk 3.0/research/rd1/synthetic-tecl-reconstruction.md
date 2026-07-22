# Montauk 3.0 Research — Stream 6: Synthetic TECL reconstruction

## 1. One-page plain-English conclusion

Montauk needs a pre-2008 TECL series because real TECL has traded only since
December 17, 2008 [Evidence: product-primary — Direxion 497 filing history, see
References #3–4]. The repo already builds one: 3x daily S&P Information
Technology index returns (1993–1998), then 3x daily XLK returns (1998–2008),
minus a 0.95%/yr expense drag, minus a flat 189.7 bps/yr "financing/tracking"
haircut applied at load time [Evidence: repo-internal —
`data/manifest.json`, `scripts/data/rebuild_synthetic.py`,
`scripts/data/loader.py`]. Charter policy already treats this series as
**diagnostic only, never a substitute for real passage**, and requires
calibration only on earlier overlap blocks with later blocks tested without
refitting [Evidence: repo-internal — `charter.md`, decision D56, gap G15].
This report is that recalibration design, plus one material finding the prior
audits missed.

**The finding:** real TECL itself is not one continuous, single-index series.
It launched under the ticker **TYH**, targeting **300% of the Russell 1000
Technology Index**, and only became "TECL" tracking the **Technology Select
Sector Index** (the same index XLK tracks) effective on or about **June 29,
2012** — nearly 3.5 years after inception [Evidence: product-primary —
Direxion's April 30, 2012 prospectus supplement, Reference #4]. Separately, the
Technology Select Sector Index itself was reconstituted in September 2018 when
GICS moved Alphabet/Google, Meta/Facebook-class names out of Technology into a
newly created Communication Services sector — a restructuring both XLK's own
trust (Reference #7) and the sector-index provider (Reference #8) disclosed
directly [Evidence: product-primary, corroborated by two independently
fetched primary filings]. Neither seam is currently represented in
`data/manifest.json` or the `is_synthetic` column — the pipeline only knows
about one seam (2008-12-17, synthetic vs. real).

**Concrete example.** Suppose on some day in 2010 XLK returns +2%. The current
model says synthetic-style TECL "should" have returned roughly 3×2% minus
costs ≈ +5.7–5.8%. But the real fund trading that day (TYH) was not exposed to
XLK's index at all — it was exposed to the Russell 1000 Technology Index, a
differently-constructed basket [Evidence: product-primary — Reference #3, #4].
If real TYH returned, say, +5.2% that day, that gap is not evidence the
*reconstruction formula* is wrong — it is a different-underlying-index gap
masquerading as a model-tracking-error gap. Any overlap-calibration block that
spans Dec 2008–Jun 2012 conflates these two error sources unless it is split
at the June 2012 seam and, per Section 8 Decision #1, never used to fit the
model.

**What Max should do.** Keep synthetic evidence diagnostic-only, as charter
already requires. Before any recalibration is trusted for even a diagnostic
weight: (a) add the June 2012 index-target seam and the September 2018
GICS-reshuffle seam as recorded provenance events, not just the 2008 seam;
(b) fit the overlap model on the one structurally clean, single-index real
block (2012-06-29–2018-09-20) and test it, without refitting, on the one
later block (2018-09-21–present) — never on the 2008–2012 TYH block, which
Decision #1 (Section 8) excludes from calibration; (c) treat any
rate-conditioned financing-haircut refinement as an empirically-backed-out
NAV-drag model, not a fit against a disclosed rate schedule, since no such
schedule is published [Evidence: product-primary — swap financing costs are
disclosed only as a distinct, excluded-from-the-fee-cap risk category, not a
quantified rate; see Section 2, row 3]. Do not let this work upgrade synthetic
evidence beyond diagnostic status; that ceiling is a charter decision
(D30/D56), not something this stream can move.

## 2. Evidence-quality table

| Claim | Evidence type | Source (URL) | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Daily leveraged-fund return ≈ β·R − c − ½β(β−1)·RV, where RV is realized variance of the underlying over the horizon (the "volatility decay" formula) | Primary paper | Avellaneda & Zhang, SIAM J. Financial Math., 2010. https://math.nyu.edu/inmemoriam/avellaneda/SIAMLETFS.pdf | Strong | Yes — general result for any daily-reset β-multiple product | Empirically validated on 56 real 2×/3× funds post-2008, not on a 1993–2008 index-proxy reconstruction. The ½β(β−1)RV term is what a naive "3× minus flat expense" spreadsheet misses; the builder captures compounding bar-by-bar but should be checked against this closed form as a fixture (Section 7). |
| Daily rebalancing by leveraged/inverse ETFs creates end-of-day flow and can affect underlying-market microstructure/volatility | Primary paper (core claims corroborated via secondary abstract; full text paywalled) | Cheng & Madhavan, J. Investment Management, Winter 2009. SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1393995 | Moderate | Indirect — informs *why* financing/rebalancing costs are not flat over time | Downgraded a notch versus Avellaneda-Zhang since the full derivation could not be fetched (SSRN blocked retrieval); treat cited specifics as tentative. |
| TECL's disclosed prospectus separates a stated, capped expense ratio (~0.94–0.95%/yr at launch and by contractual cap, 0.87% net per recent fee tables) from swap-based **financing costs**, which are a distinct cost of obtaining leveraged notional exposure | Product-primary for the category split; [Inference] for fittability | Direxion 497 prospectus (Oct 2008/suppl. Apr 2009), SEC EDGAR: https://www.sec.gov/Archives/edgar/data/1424958/000089843209000516/a497.htm; SEC N-CSR FY2024 expense tables | Moderate | Partially — the *category split* is disclosed; the *rate* is not | Financing costs are explicitly **excluded** from the capped "Total Annual Fund Operating Expenses" figure and disclosed only qualitatively as a risk factor — no rate or schedule is published. [Inference]: the two-layer expense/haircut split is structurally right-shaped, but Experiment C's target variable must be *empirically backed out from realized NAV tracking drag*, not read off a disclosed source. |
| TECL launched 2008-12-17 as **TYH**, target index = **Russell 1000 Technology Index** (Russell-methodology cap-weighted); renamed to **TECL** and target index switched to **Technology Select Sector Index** (S&P modified-cap-weighted, concentration-capped) effective on or about **June 29, 2012** | Product-primary (SEC 497 filings) | Direxion 497, Oct 2008/Apr 2009 supplement, Reference above; Direxion 497 supplement dated Apr 30, 2012, SEC EDGAR: https://www.sec.gov/Archives/edgar/data/1424958/000089418912002411/drxnshrs-etftrst_497e.htm | Strong | Directly — this *is* TECL's own corporate history | This is the report's central finding, independently corroborated via web search (Benzinga, ETFtrends, ETF Strategy). It is not represented anywhere in `data/manifest.json` or `TECL.csv`'s `is_synthetic`/`source_symbol` columns, which imply real TECL has always tracked the same index XLK does. It did not, for ~42 months. |
| GICS reclassified major "Technology" names (Alphabet, Meta) into a new Communication Services sector, restructuring the Technology Select Sector Index / XLK composition, with reconstitution effective after close **September 21, 2018** | Product-primary — both XLK's own trust and the index provider directly | (1) Select Sector SPDR Trust Form 497 supplement, June 19, 2018, SEC EDGAR: https://www.sec.gov/Archives/edgar/data/1064641/000119312518196887/d578872d497.htm; (2) S&P Dow Jones Indices/MSCI joint announcement, Nov 15, 2017: https://press.spglobal.com/2017-11-15-S-P-Dow-Jones-Indices-And-MSCI-Announce-Revisions-To-The-Global-Industry-Classification-Standard-GICS-R-Structure-In-2018 | Strong | Directly — affects both XLK (the synthetic proxy, 1998–2008) and post-2012 real TECL | Both a primary XLK-trust filing and the index provider's own release were located and fetched directly this pass; ETFtrends/CNBC (Reference #9) now serve only as secondary corroboration. Three distinct dates exist here — Nov 15, 2017 announcement, Sept 21, 2018 index/fund reconstitution (used throughout this report), Sept 28, 2018 GICS Direct data-feed implementation — flagged to avoid the conflation this report otherwise criticizes. |
| A 2026 internal Montauk 2.0 audit measured synthetic-era tracking error at 8.96%/yr against an imported "<3%" threshold, and found full-history share multiples 6–12× the real-era multiples | Repo-internal measurement; Inference on threshold applicability | `docs/Montauk 2.0/deep-validation-report.md`, D2.1/D2.2, D2.9 (legacy, historical context only) | Moderate — the 8.96%/yr and 6–12× numbers are real; the "<3%" bar's population is undocumented | Not applicable as-is: per the rule against importing thresholds from unrelated populations, "<3%" must not be reused without knowing what it was calibrated against. 8.96%/yr and 6–12× are useful priors, not pass/fail bars. |
| Technology Select Sector Index uses "modified market capitalization" weighting with single-name capping, vs. the Russell-methodology cap-weighting of the pre-2012 real-TECL target index | Product-primary (SEC 497 New Index Description text) | Direxion 497 supplement, Apr 30, 2012 | Strong | Directly | Explains why splicing XLK-driven synthetic history onto real TECL, or comparing the two pre-2012, mixes two index-construction philosophies, not just two variance realizations. |

## 3. Recommended Montauk experiment(s)

Each experiment below is scoped to what the current repo can execute with data
already checked in (`data/manifest.json` inventory), or explicitly flags where
it cannot. All four share the same three structural blocks: **Block 1** =
2008-12-17 to 2012-06-28 (TYH/Russell-1000-Tech era), **Block 2** = 2012-06-29
to 2018-09-20 (TECL/pre-GICS-reshuffle Technology-Select-Sector era), **Block
3** = 2018-09-21 to present (post-reshuffle era).

### Experiment A — Time-separated overlap calibration (charter-mandated, D56/G15)

**Estimand.** Using only the frozen builder and haircut/expense parameters
fit **exclusively on Block 2** — the one structurally clean, single-index
real-TECL era — compute, without refitting: (i) mean daily log-return bias
(synthetic-formula output vs. observed real TECL); (ii) annualized tracking
error (stdev of that daily difference); (iii) terminal cumulative-return ratio
at block end; (iv) max-drawdown gap; (v) day-level return gap on the fixed
named-moment dates that fall inside the block (2020, 2022, tariff-announcement
days — 2001 and most of 2008 remain outside any real-data block and are
excluded from this estimand). These five metrics are computed once on **Block
3** (the true held-out OOS block).

**Block 1 is never a calibration target.** Per Owner Decision #1 (Section 8),
2008-12-17–2012-06-28 is real, tradeable TECL/TYH NAV but tracked a different
index than the synthetic builder assumes — fitting the haircut/expense
parameters to it would conflate index-substitution error with model error,
which is exactly the contamination the report's Section 1 example describes.
Block 1 is instead run once, read-only, using the Block-2-fit parameters
(never fit to Block 1 itself), purely as a **diagnostic contamination check**
— it is expected to show large bias, and that outcome is reported as evidence
the block is index-mismatched, not as a model failure.

**Freeze before looking at results:** the three block boundaries (fixed at the
two structural seams in Section 2); calibration block = Block 2 only; Block 1
= diagnostic-only, never fit; Block 3 = held-out test, evaluated once.

**Stopping rule.** Compute the five metrics once for Block 3 using parameters
frozen from Block 2; do not refit after seeing Block 3. Separately compute the
same five metrics once for Block 1 using the same Block-2-fit parameters, and
report both readouts as-is — a large Block 1 bias confirms contamination as
expected; a large Block 3 bias is the actual model-adequacy signal. Do not
re-pick calibration or holdout blocks after seeing either result.

**Power note.** This design leaves exactly **one** genuine held-out block
(Block 3, under 8 years). This is a real reduction from a naive three-block
reading and is carried into Section 6 as a power limit, not glossed over.

### Experiment B — Index-substitution attribution test

**Estimand.** How much of Block 1's tracking gap between the XLK-driven
formula and real TYH/TECL is attributable to using XLK/Technology-Select-
Sector as a stand-in for an index the fund was not tracking (Russell 1000
Technology), versus genuine model/financing error. Operationalized as:
tracking error of [XLK-driven formula vs. real TYH] minus tracking error of
[an investable Russell-1000-Technology-style proxy vs. real TYH], both over
Block 1. This does not calibrate anything used elsewhere; it only quantifies
how much of Block 1's contamination (Experiment A) is index-substitution
specifically.

**Freeze before looking at results:** the substitute proxy ticker and its
provenance, declared before computing any error — not chosen after trying
several and keeping the best fit.

**Stopping rule.** One side-by-side comparison, reported as-is. If no clean
free-data proxy for the actual 2008–2012 Russell 1000 Technology Index exists
(plausible — Section 6), report that constraint honestly and fall back to a
qualitative, documentation-based attribution rather than force a numeric
comparison against a poor substitute.

### Experiment C — Rate-conditioned financing-drag recalibration

**Estimand.** Whether replacing the flat 189.7 bps/yr financing haircut with
a short-rate-linked function, `haircut_t = a + b × fed_funds_t`, fit **only
on Block 2** (`data/fed-funds-rate.csv` supplies the free predictor),
reduces out-of-block bias/tracking error vs. the flat-haircut baseline when
evaluated once on **Block 3**. The dependent variable is *not* a disclosed
financing rate — none is published (Section 2, row 3) — it is realized NAV
tracking drag left over after removing index return, leverage, and expense
ratio from observed Block 2 TECL returns: a noisier target than a published
schedule would give.

**Freeze before looking at results:** functional form (linear, one
calibration block, no interaction terms); calibration = Block 2, holdout =
Block 3 — fixed to match Experiment A, not left open to whichever block
later looks cleaner.

**Stopping rule.** Fit once, evaluate once, report the delta vs. the
flat-haircut baseline. No grid search over alternative forms declared after
seeing which fits best — that would relocate the overfitting problem into
the diagnostic meant to detect it.

### Experiment D — Catastrophic-veto candidate calibration (gated on A–C)

**Estimand.** At a fixed, predeclared false-trigger budget on honest control
strategies, does a candidate veto rule (e.g., "flag if synthetic-era max
drawdown exceeds X% while real-era drawdown for the same config stays under
Y%") catch seeded ruinous-behavior defects (Section 4) without vetoing
honest, non-degenerate controls at an unacceptable rate? Deliberately
method-first: X and Y calibrate against control-battery behavior, never
against any specific strategy's current standing on `spike/leaderboard.json`.

**Freeze before looking at results:** trigger definition and acceptable
false-trigger rate, agreed before running any control battery.

**Stopping rule.** One pass over the fixed control battery; report catch
rate and false-trigger rate as the answer, whatever it is. Do not adjust the
trigger post hoc to avoid vetoing a particular strategy — this experiment
should not run at all until A–C are reviewed, since a veto calibrated on an
unreconciled index-mismatch era would target the wrong population.

## 4. Null, defect, and planted-signal controls

- **Dependence-preserving null (resampling mechanism specified).** Bootstrap
  Block 2 real XLK/TECL returns (the same block Experiment A calibrates on)
  and re-run them through the identical builder, using a **stationary/
  circular block bootstrap** (Politis & Romano, 1994) — not an i.i.d.
  resample, which would understate serial dependence and could produce a
  falsely "clean" null given the volatility clustering the Avellaneda-Zhang
  RV term (Section 2, row 1) exists to capture. The mean block length must be
  **frozen before looking at results**, derived from the observed decay of
  the squared-return autocorrelation function on Block 2 data — not chosen
  after seeing which length makes the null pass — and recorded in the frozen
  overlap artifact (Section 7). A systematic non-zero result here indicates a
  bug in the stitching or haircut code, not a real phenomenon, and must be
  fixed before Experiment A is trusted.
- **Known-structural-break positive control.** The June 29, 2012 index-target
  switch is a real, independently sourced discontinuity. The overlap pipeline
  must show a detectable jump in tracking error/regime right at that date
  across the Block 1/Block 2 boundary. If it does not detect a break already
  known from a primary filing, the diagnostic lacks power generally — and
  should not be trusted with any weight or veto role until fixed.
- **Seeded-defect control.** In a scratch copy, deliberately corrupt the
  builder (wrong stitch anchor, sign-flipped expense, wrong leverage
  multiple) and confirm the pipeline flags an obviously large tracking-error
  spike. If a broken builder still "passes," the check has no discriminating
  power.
- **Planted-signal control.** Inject a known artificial return pattern into
  a scratch copy of the pre-inception synthetic segment and confirm the
  overlap metric does not validate it as authentic tracking fidelity — guards
  against a metric that rewards any smooth-looking series regardless of
  mechanism.
- **Determinism control.** Re-run the full overlap experiment twice on
  byte-identical inputs and confirm bit-identical output metrics (extends
  `rebuild_synthetic.py`'s existing `--verify` claim to the overlap-report
  layer). Catches numeric nondeterminism that could otherwise look like
  "close enough" model fit.

## 5. False-Gold and false-rejection consequences

**False-Gold risk (synthetic evidence trusted too much).** If a strategy's
apparent edge concentrates in the smoother 1993–2008 synthetic segment, or is
inadvertently rewarded by the index-mismatched 2008–2012 real-but-wrong-index
segment, an uncalibrated diagnostic weight could nudge it toward Gold when its
true forward TECL behavior would differ. Because Max executes manually with
real capital based on this signal, the cost of this failure mode is real
dollars deployed on a false-confidence basis, not just a research write-off.

**False-rejection risk (synthetic evidence discarded too aggressively).**
Charter policy already treats synthetic history as diagnostic-only [Evidence:
repo-internal, D30/D56]. If Stream 6's findings — a real index-mismatch gap,
an uncalibrated flat haircut — are used to suppress *all* synthetic-era
signal, including the named 2001/2008 crash-shape diagnostics, Max loses the
only available (if imperfect) proxy for how a candidate strategy behaves in a
dot-com-scale collapse: real TECL has never lived through one. A strategy
could pass Gold looking safe while carrying a structural fragility to a
2001-style megacrash that only the synthetic-era diagnostic could have hinted
at.

**Asymmetry.** Given that Montauk's mission already treats synthetic history
as never-a-Gold-substitute, the marginal risk today [Inference] leans toward
*under*-using a properly-caveated crash-shape signal rather than over-trusting
it — provided the calibration work above is actually done. If it is skipped
and the diagnostic weight is turned on anyway with the current flat-haircut,
uncalibrated design, the risk flips toward false-Gold, because an unmeasured
model's error direction is unknown.

## 6. Assumptions and power/limits

- **Real-data ceiling is small, and Decision #1's calibration rule shrinks it
  further.** Real TECL history is ~15 years [Evidence: product-primary,
  launch date]. Once Block 1 is correctly excluded from calibration
  (Experiment A), only **one** genuine held-out block remains (Block 3,
  under 8 years) against one calibration block (Block 2, ~6 years) — smaller
  and more fragile than a naive "three non-overlapping blocks" reading would
  suggest, and the same small-N ceiling that already constrains Montauk's
  economic-gate power [Evidence: repo-internal, `charter.md`].
- **Multiple-comparisons exposure across a small, shared block set.**
  Experiments A–D plus the four Section 4 controls all draw on the same
  at-most-three blocks — effectively one train/test split once Block 1 is
  excluded from fitting. Running eight-plus checks against that shared
  population raises real risk that an apparently clean result reflects
  chance, not genuine adequacy. No formal family-wise correction is applied,
  since these are diagnostic checks feeding a research judgment rather than a
  hypothesis-test gate — but a single clean Block 3 pass should be read as
  one data point, not confirmation.
- **Regime-stability assumption is unverified.** The rate-conditioned haircut
  (Experiment C) assumes the short-rate-to-swap-financing-spread relationship
  is stable across the fit-to-test window (2012–2018 fit, 2018–present test),
  spanning the LIBOR-to-SOFR transition. No source establishes that
  stability; it is an assumption to state, not a result to claim [Inference].
- **Financing-rate data constraint.** No disclosed financing-rate time series
  exists to calibrate against — financing costs are excluded from the capped
  operating-expense figure and disclosed only qualitatively (Section 2, row
  3). The dependent variable must be back-solved as realized NAV tracking
  drag: noisier and more model-dependent than fitting against a published
  rate, and it changes what a "good fit" can honestly be attributed to.
- **Index-substitution data constraint.** A clean, free, daily total-return
  history for the actual 2008–2012 Russell 1000 Technology Index may not be
  available without a paid Russell/FTSE license. Experiment B may fall back
  to a qualitative, documentation-based attribution — state that ceiling
  plainly rather than force a comparison against a poor substitute.
- **Pre-inception segments cannot become real-data evidence.** No overlap-fit
  quality converts 1993–2008 synthetic history, or the 2008–2012
  index-mismatched real segment, into observed-real TECL passage for Gold
  purposes. That ceiling is charter policy (D30, D56, G15), not a result this
  stream can move by fitting better.
- **This report does not attempt to re-derive the "<3% tracking error"
  threshold** used in the legacy Montauk 2.0 audit; its population of origin
  was not established by any source found, and reusing it here would violate
  the standing rule against importing unrelated-market thresholds.

## 7. Required fixtures and durable artifacts

- **Determinism fixture (extends existing coverage).** `rebuild_synthetic.py`
  already claims same-bytes-in → same-bytes-out determinism for the raw
  series [Evidence: repo-internal]; extend this to the overlap-report layer —
  two runs on identical inputs must produce bit-identical metrics.
- **Hand-computed toy-universe fixture.** A small (~20-trading-day)
  hand-computed underlying-return series with an independently hand-derived
  expected 3×+expense+haircut output, checked to float tolerance — isolates
  formula-implementation bugs from real-market noise, and doubles as a
  sanity check against the Avellaneda–Zhang closed form (Section 2, row 1).
- **Seeded-negative fixture.** The corrupted-builder variants from Section 4,
  each with its expected (large, detectable) tracking-error/bias recorded as
  the accepted "should fail loudly" result.
- **Structural-break-detection fixture.** The two known discontinuity dates
  (2012-06-29 TYH→TECL/index-target switch; 2018-09-21 GICS reshuffle) each
  get a recorded expected-detectable-discontinuity acceptance criterion, so
  future versions can re-verify the diagnostic still has power to see breaks
  already known to be visible.
- **Frozen bootstrap-block-length record.** The stationary-bootstrap mean
  block length used in Section 4's null (and the ACF decay estimate it was
  derived from) is recorded alongside the run, so a reviewer can confirm it
  was set before results were seen, not tuned to make the null pass.
- **Frozen overlap-experiment artifact.** One versioned markdown+JSON report
  per calibration run (block boundaries, fitted parameters, held-out
  metrics), stored alongside a bumped `synthetic_model_version` in
  `data/manifest.json`, so any future builder/haircut/seam change must
  re-run and re-file this artifact rather than silently drift.
- **Three-way provenance fixture.** A provenance value distinguishing (a)
  clean synthetic, (b) real-but-index-mismatched (2008-12-17–2012-06-28),
  and (c) clean real/current-index — so downstream diagnostics can weight or
  exclude the middle category deliberately instead of the pipeline treating
  it as ordinary real data.

## 8. Unresolved owner decisions

1. **Should the 2008-12-17–2012-06-28 real segment (then TYH, Russell 1000
   Technology Index) count as "real TECL" for economic-gate/B&H purposes,
   even though it's excluded from overlap calibration?** Recommended: yes for
   economic-gate/B&H (the fund really traded at those NAVs; the execution
   comparator cares about tradeable NAV, not target index) but exclude it
   from calibration (given concrete effect in Experiment A: fit on Block 2
   only, run Block 1 as a read-only contamination diagnostic), since mixing
   it in conflates index-mismatch error with model error. Tradeoff: the
   design collapses to a single Block 2 → Block 3 train/test split.
2. **Pursue Experiment B's quantitative index-substitution test, given likely
   data-access limits, or accept a qualitative fallback?** Recommended: try
   one free-data proxy first, label the result directional/weak, and do not
   purchase a Russell/FTSE license for a diagnostic that can never exceed
   "diagnostic" status. Tradeoff: weaker resolution, proportionate cost.
3. **Implement the rate-conditioned financing haircut (Experiment C) now, or
   defer to a broader `loader.py` hardening pass?** Recommended: now — the
   predictor data exists, the change is self-contained, and it addresses
   named gap G15. Tradeoff: the fitting target (back-solved NAV drag, not a
   disclosed rate — Section 6) is noisier than initially assumed, so this
   ships as an explicitly-labeled empirical estimate and a versioned
   `synthetic_model_version` bump, never a silent mutation.
4. **What role should the 2001/2008 named-moment diagnostics keep, now that
   part of the "real" 2008 data is index-mismatched?** Recommended: keep them
   visible and source-labeled per D47/charter (never a real-data Gold gate),
   reported *with* Stream 6's calibration uncertainty attached rather than
   suppressed — Max still needs some signal for a dot-com-scale scenario
   TECL has never lived through. Tradeoff: an uncertainty-qualified
   diagnostic, not a clean pass/fail.
5. **Accept a single-block-pair (Block 2→Block 3) design as sufficient
   evidence for any diagnostic weight, given the multiple-comparisons and
   small-N concerns in Section 6?** Recommended: treat a first pass through
   Experiments A–D as *design validation*, not grounds to turn on a
   diagnostic weight or veto — require the null and positive controls
   (Section 4) to pass cleanly first, and revisit after that evidence
   exists. Tradeoff: slower path to using synthetic evidence for anything
   beyond narrative color.

## References

**Primary**

1. Avellaneda, M. & Zhang, S. (2010). "Path-Dependence of Leveraged ETF
   Returns." *SIAM Journal on Financial Mathematics*, 1, 586–603.
   https://math.nyu.edu/inmemoriam/avellaneda/SIAMLETFS.pdf — [Primary]
2. Cheng, M. & Madhavan, A. (2009). "The Dynamics of Leveraged and Inverse
   Exchange-Traded Funds." *Journal of Investment Management*, Winter 2009.
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1393995 — [Primary;
   full text paywalled/not independently re-read — see Section 2 notes]
3. Direxion Shares ETF Trust. Prospectus dated October 1, 2008, as Supplemented
   April 10, 2009 (SEC Form 497). SEC EDGAR:
   https://www.sec.gov/Archives/edgar/data/1424958/000089843209000516/a497.htm
   — [Primary, product/regulatory]
4. Direxion Shares ETF Trust. Supplement dated April 30, 2012 to the Prospectus
   dated February 28, 2012 (SEC Form 497 "sticker") — TYH→TECL rename and
   benchmark change from Russell 1000 Technology Index to Technology Select
   Sector Index, effective on or about June 29, 2012. SEC EDGAR:
   https://www.sec.gov/Archives/edgar/data/1424958/000089418912002411/drxnshrs-etftrst_497e.htm
   — [Primary, product/regulatory]
5. State Street Global Advisors. "Technology Select Sector SPDR ETF (XLK) Fact
   Sheet." https://www.ssga.com/library-content/products/factsheets/etfs/us/factsheet-us-en-xlk.pdf
   — [Primary, product]
6. Direxion. "TECL/TECS Fact Sheet."
   https://www.direxion.com/uploads/TECL-TECS-Fact-Sheet.pdf — [Primary,
   product]
7. **Select Sector SPDR Trust.** Form 497 Supplement dated June 19, 2018, to
   the Prospectus, Summary Prospectus, and Statement of Additional Information
   each dated June 18, 2018 — describes the GICS structure changes (announced
   Nov 2017, effective after close September 21, 2018) and the resulting
   reconstitution of the Technology Select Sector Index and Consumer
   Discretionary Select Sector Index. SEC EDGAR:
   https://www.sec.gov/Archives/edgar/data/1064641/000119312518196887/d578872d497.htm
   — [Primary, product/regulatory — this is XLK's own trust describing the
   reconstitution directly]
8. S&P Dow Jones Indices & MSCI Inc. "S&P Dow Jones Indices And MSCI Announce
   Revisions To The Global Industry Classification Standard (GICS®) Structure
   In 2018." Press release, November 15, 2017.
   https://press.spglobal.com/2017-11-15-S-P-Dow-Jones-Indices-And-MSCI-Announce-Revisions-To-The-Global-Industry-Classification-Standard-GICS-R-Structure-In-2018
   — [Primary, index provider]

**Secondary**

9. ETFtrends.com. "GICS Changes Scheduled to Take Place in Tech Sector."
   https://www.etftrends.com/gics-changes-scheduled-to-take-place-in-tech-sector/;
   CNBC, "Alphabet, Facebook and Netflix are about to destroy the stock
   market's biggest dividend trade,"
   https://www.cnbc.com/2018/09/21/on-monday-google-facebook-and-netflix-will-make-a-big-market-move.html
   — [Secondary corroboration only; References #7–8 carry the primary weight]

**Repo-internal (project evidence, not external literature)**

10. `data/manifest.json` — current `synthetic_model_version`, seam dates,
    checksums.
11. `scripts/data/rebuild_synthetic.py` — deterministic rebuild formula,
    segment definitions, expense-ratio assumptions.
12. `scripts/data/loader.py` — `_apply_tecl_synthetic_financing_drag`, the
    flat 189.7 bps/yr financing/tracking haircut (`TECL_SYNTHETIC_FINANCING_DRAG_ANNUAL
    = 0.01897`).
13. `docs/Montauk 2.0/deep-validation-report.md` — legacy D2.1/D2.2 (8.96%/yr
    synthetic tracking error vs. an unsourced "<3%" bar), D2.9 (6–12× full-
    history inflation). Historical context only, not a 3.0 requirement.
14. `docs/*NEXT/Montauk 3.0/charter.md`, `decisions.md` (D30, D47, D56),
    `validation-engine-hardening.md` (gap G15, §3e) — the governing 3.0 policy
    for synthetic evidence that this stream operationalizes.

# Montauk 3.0 Research — Stream 10: Ranking and human decision quality

**Scope.** This stream does not touch Gold eligibility. Once a configuration
is already Gold, what is the smallest owner-facing ranking, recommendation,
and switch-confirmation surface that (a) gives Validation Score priority over
Performance without re-scoring what a hard gate already decided, (b) tells Max
the truth about statistical separation between top rows *without blocking the
recommendation that separation warning is about*, (c) avoids manufactured
churn or alert fatigue, and (d) makes "approve" unambiguous about whether it
reorders a board or issues an opposite-state trade instruction for tomorrow's
open? Every claim is tagged by evidence type; no threshold is imported from
outside literature without saying so.

---

## 1. One-page plain-English conclusion

**What to build.** The existing four-field leaderboard row (`charter.md`
§9.1), plus two additions:

1. A **rank-confidence flag** — `leader not clearly separated` — next to rank.
   Per charter §9.1 (**DECIDED**), this flag "does not create another score
   or prevent Montauk from naming one recommendation; it makes rank precision
   honest." It is disclosure, not a gate.
2. A **switch-confirmation card**, shown only when Recommended or Active
   changes, in one of two visibly different modes depending on whether
   approving it changes today's actual trade instruction.

**What Max should do.** Nothing, if nothing is flagged. If "Recommended
changed" appears, open the card once. **"Pointer only — no trade today"**:
approve or ignore at leisure. **"Opposite-state instruction"**: read the
drawdown/catastrophe line first, then approve only via a deliberate second
step, not one click.

**Concrete example.** A is Active, risk-on. B's Validation Score climbs 78→90
(clears the +10 threshold) with no Performance loss, so Montauk names B
Recommended.

- B's signal today is also risk-on: *"Pointer only — today's instruction
  stays risk-on either way."* One click.
- B's signal today is risk-off: *"Opposite-state instruction: risk-off at
  tomorrow's open."* Requires a second explicit step; drawdown/catastrophe
  shown first.
- B's edge over A instead sits inside the region a Model-Confidence-Set-style
  test can't statistically separate: Montauk **still names B Recommended**,
  because it independently cleared the deterministic §9.2 threshold — that
  threshold, not the separation test, triggers the change. What changes is
  disclosure: both the board and the card show `leader not clearly separated`,
  so Max reads the change knowing the gap is statistically thin, rather than
  reading it as more certain than it is.

*Correction note:* an earlier pass of this analysis proposed blocking the
recommendation itself whenever separation was ambiguous. That directly
reverses the DECIDED §9.1 rule and has been removed; see §6.

---

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Raw probabilities/relative risks are reliably misread versus natural frequencies, even by professionals. | [Primary] | Gigerenzer & Edwards, *BMJ* 327(7417):741–744 (2003). doi:10.1136/bmj.327.7417.741 | Strong in its domain | Partially — a *communication-design* principle (Validation Score is never typeset as "% confidence"), not a numeric threshold. | No open-access mirror confirmed this session; cite the DOI only, not a PMC link (prior draft's PMC link was broken/unverifiable). |
| Subjective confidence is reliably overconfident without calibrated feedback across many repeated, resolvable trials. | [Primary] | Lichtenstein, Fischhoff & Phillips, in *Judgment Under Uncertainty*, 1982, pp. 306–334. | Strong, foundational | Partially, as **[Inference]** only. The tested mechanism is repeated professional judgments with feedback; it does not test, and cannot evidence, that TECL's handful of macro regimes guarantees poor calibration — that extension is an analogy this document constructs, not the paper's finding. No numeric cutoff transfers. | Why the charter refuses to call Validation Score a probability until a frozen calibration target and genuine forward outcomes exist (§0.1, §4.1). |
| A statistical procedure can name a *set* of statistically indistinguishable models rather than force a single point rank; the set widens as evidence thins. | [Primary] | Hansen, Lunde & Nason, "The Model Confidence Set," *Econometrica* 79(2) (2011). doi:10.3982/ECTA5771 | Moderate–Strong (bibliographic/abstract confirmed via secondary indexing; proof not re-derived behind paywall) | Partially — the *mechanism* transfers cleanly and is what the ambiguity flag needs; the method's own literature warns it may need high signal-to-noise and isn't fully robust to multiple testing, both live concerns for TECL. | `validation-engine-hardening.md` (~line 336, verified present) already logs MCS as "ranking diagnostic candidate, not the board-wide multiplicity fix"; this stream inherits that disposition. |
| Judgment "noise" (unwanted variability in repeated professional calls) is large and reducible by standardizing the decision procedure. | [Primary for the framework; book synthesizes other studies, treat individual figures as secondary] | Kahneman, Sibony & Sunstein, *Noise*, 2021. | Moderate (trade-book synthesis) | Partially — the *design principle* (one deterministic ranking pass, not a daily judgment call) mirrors §3.1's mandate. No numeric threshold transfers. | Justifies a frozen, uniformly-applied switch-review rule over a fresh per-day judgment call. |
| Clinical alert override rates rise sharply with alert volume and repeat-alert share; raw workload and time-based desensitization did not predict overrides. | [Primary] | Ancker, Edwards, Nosal, et al., *BMC Med Inform Decis Mak* 17:36 (2017). | Strong — quantified: acceptance fell with each additional alert (IRR 0.70, p<.001) and each 5-pt rise in repeat share (IRR 0.90, p<.001); full text fetched and figures verified this session. | Weak as numbers, Moderate as mechanism — clinical population, IRRs don't transfer; the mechanism (repetition of uninformative signals, not volume) does. | Argues against re-alerting Max daily about the same unresolved gap. |
| Pre-selected defaults are chosen far more than an economically identical opt-in, even at high stakes and trivial switching cost. | [Primary] | Johnson & Goldstein, "Do Defaults Save Lives?" *Science* 302(5649) (2003). doi:10.1126/science.1091721 | Strong (cross-country natural experiment; corroborated via secondary sources this session, publisher page 403'd direct fetch) | Weak as numbers, Moderate as mechanism — organ-donation defaults aren't TECL trading, but "defaults dominate active choice" is why "approve" can't be equally easy for pointer-only vs. opposite-state changes. | Supports asymmetric friction (§1, §8 Q3). |
| Composite indices double-count when sub-indicators share statistical information; check inter-indicator correlation before finalizing weights. | [Primary for existence/purpose; Moderate for the specific passage] | OECD/JRC, *Handbook on Constructing Composite Indicators*, 2008. | Moderate | Strong as a domain-agnostic principle — Montauk Score is literally a composite index. | **Not fully verified.** Two attempts this session (direct PDF fetch, targeted search) failed to extract a clean quoted passage; a secondary summary corroborates the handbook addresses this, but it's still not a verified primary quote. Experiment C's actual decision rule (R²/correlation) is self-contained statistics and doesn't depend on this citation's wording — but the citation shouldn't be called verified authority until a quoted passage is found (§3, §6, §8 Q5). |
| Montauk's own contract: one leaderboard, Recommended≠Active, Validation Score non-probability until calibrated, four-field row, and — verbatim — the ambiguity flag "does not create another score or prevent Montauk from naming one recommendation." Initial thresholds: +10 abs Validation Score / +10% relative performance / +5 abs Montauk Score, 5-bar persistence. | [Product-primary] | `charter.md` §9.1–9.2; `decisions.md` D18, D34, D51. | Strong as owner intent | N/A — target system | §3–§8 implement this contract. The prior draft's "ambiguity blocks the recommendation" language contradicted D51 verbatim; corrected in §1/§4, disclosed in §6. Genuinely open parameters are in §8. |

---

## 3. Recommended Montauk experiment(s)

Each is a **Phase 1 calibration study** under charter §16 item 8. None may be
re-run with adjusted thresholds after seeing which strategy benefits.

### Experiment A — Recommendation-churn calibration

**Estimand.** Expected Recommended-strategy changes per rolling 252-bar
window under the D34/§9.2 threshold rule, on (i) a synthetic null panel (no
genuine improvement, noise calibrated to empirical score volatility) and
(ii) the real Gold-eligible cohort once it exists.

**Frozen before results.** Threshold values (D34), the null-model noise
process, 500 simulated 252-bar years, and the churn summary statistic
(mean + 95th percentile switches/year). The acceptable ceiling is written
down before simulating.

**Stopping rule.** Run once on the null spec, once on real history; report
both. No iterating on parameters after seeing churn count. High churn is a
finding for a new owner-approved threshold version, not a silent re-search.

### Experiment B — Leader-separation calibration (`leader not clearly separated`)

**Estimand.** The smallest realistic cohort size and score gap at which an
MCS procedure, applied to the daily net log-wealth-difference series under a
stationary block bootstrap, would exclude the #2 row from the confidence set
at a fixed confidence level. **This governs disclosure only** — it has no
bearing on whether Montauk names a Recommended, which Experiment A's
threshold rule alone decides.

**Frozen before results.** A single target level, **90%, pre-registered
before Fixture 1 runs** — not chosen by comparing candidates. A predeclared
fallback: if 90% produces a flag rate above a ceiling fixed alongside
Experiment A's churn ceiling, 75% becomes operative starting from the *next*,
separately dated pass — never substituted within the same pass after
informally comparing which "looks better" (this closes a soft
multiple-comparisons exposure in an earlier draft). Also frozen: the loss
function (terminal deployable TECL wealth/share multiple, not Sharpe), block
length (from the series' own measured autocorrelation), 1,000 resamples, and
cohort sizes {5, 20, 50}.

**Stopping rule.** Evaluate on Fixture F1 plus every rolling annual real
cohort to date; apply the frozen level/fallback rule after that single pass.
Adding real cohorts later is monitoring, not a re-run; the rule itself only
changes via a new owner-approved version.

### Experiment C — Double-counting audit of the Montauk Score formula

**Estimand.** Pairwise correlation/R² between each named formula input and
(a) every other named input, (b) every binary Gold admission gate. An input
double-counts if it's a monotonic transform of a variable a hard gate already
consumed, with no added information beyond magnitude-above-threshold.

**Frozen before results.** The full input/gate list (from §4.3, §9.2), fixed
before computing correlations. Decision rule fixed first: "R² > 0.6 between
two named pillars requires merging or an explicit written justification."
**Precondition not yet satisfied:** the OECD/JRC citation anchoring this
audit is only secondarily corroborated (§2). The R²-rule itself is
self-contained statistics and may run now; the audit should not be presented
as backed by verified external authority until resolved (§6, §8 Q5).

**Stopping rule.** Run once per proposed formula version, before
ratification. A flagged overlap means fix the formula and re-run as a fresh,
dated pass — never loosen the threshold to pass a flagged version.

---

## 4. Null, defect, and planted-signal controls

| Control | Setup | Required result | What failure reveals |
|---|---|---|---|
| **Null-clone leaderboard** | N near-identical noisy copies of one strategy (same true edge, independent noise). | MCS reports all clones in one confidence set; board shows `leader not clearly separated`. Per §9.1 (DECIDED), the board still names one deterministic top rank, eligible for Recommended if it clears §9.2 — ambiguity is disclosed, not used to suppress the recommendation. | If the flag is absent while a crisp-looking top rank is shown among indistinguishable clones, the flag is decorative. (The opposite failure — silently blocking the recommendation on a tie — would itself violate the DECIDED rule.) |
| **Planted true-signal control** | One row with a large simulated true edge amid null clones. | Excluded from ambiguity at a materially lower confidence requirement than clones need; no flag once its edge exceeds a predeclared size. | If still flagged, the test has near-zero power at Montauk's sample sizes — reportable, not to be silently tuned away. |
| **Pure-noise churn null** | Random-walk trajectory, no genuine improvement (Experiment A's null). | Recommended-change events at or below the frozen ceiling. | Excess churn under a known null proves the threshold isn't protecting against noise-driven switching. |
| **Seeded double-counting defect** | A synthetic pillar wired to re-derive an existing Validation-Score sub-term. | Experiment C flags the seeded high R² and blocks ratification. | Missing this obvious defect means subtler real overlaps won't be caught either. |
| **Pointer-vs-opposite-state fixture** | {Recommended-only, Active-eligible} × {pointer-only, opposite-state}, each with ambiguity flag on/off. | Pointer-only always renders "pointer only"; opposite-state always renders inline drawdown/catastrophe + a second confirmation step, regardless of ambiguity state — ambiguity changes card *content*, never which card type appears. | Same generic dialog for both means a real opposite-state instruction can be approved as casually as a harmless pointer update — the highest-severity failure this stream exists to prevent. |
| **Deferral vs. dismissal fixture** | Deferred item resurfaces on schedule; dismissed item stays silent until the re-trigger delta (§8 Q1) is met. | Transitions match exactly for a scripted sequence. | Deferral behaving like dismissal loses a live decision; dismissal behaving like deferral reproduces Ancker-style alert fatigue. |
| **Drawdown/catastrophe completeness check** | Gold row with a known large max drawdown and named-catastrophe result. | Card renders both inline, before the confirmation control, no click-through. | Buried disclosure lets Max approve without seeing worst-case evidence already computed. |

---

## 5. False-Gold and false-rejection consequences

Downstream of Gold — every error here happens to a row that already passed
the five-plank exam. Not the headline false-Gold/false-reject risks
(Stream 3/4/6); an additive human-decision-quality layer.

- **Spurious Recommended change.** Attention spent on noise, not edge;
  repeated, this is Ancker et al.'s alert-fatigue mechanism. [Inference,
  extending Ancker's clinical finding to this domain.]
- **Over-flagging ambiguity.** Max reads more caution than warranted into a
  genuinely valuable switch. Lower severity than the reverse (mirrors charter
  §2.3's asymmetry): foregone upside vs. a decision made on noise presented
  as certainty.
- **Under-flagging ambiguity (false confident rank).** Max approves a switch
  believing the leader is clearly better when evidence can't distinguish it.
  Because the flag is disclosure, not a gate, this risk lands entirely on
  whether it's rendered saliently in the switch-confirmation card, not just
  the leaderboard row — Fixture F3 is the acceptance test.
- **Mislabeled pointer-only vs. opposite-state switch.** The single
  highest-severity error possible here — it can trigger a real, wrong trade
  even when every statistic is correct. Per Johnson & Goldstein, the
  path-of-least-resistance option dominates; equal-ease "approve" buttons
  mean Max treats both cases equally, which is exactly wrong.
- **Missing drawdown/catastrophe disclosure.** Approving without seeing
  worst-case evidence the pipeline already computed — a preventable
  omission, not a genuine unknown.

**The asymmetry to hold onto:** errors that can *cause an unwanted real
trade* are strictly worse than errors that only *cost attention or delay*.
Bias toward the safer failure mode — show the warning, show the number,
disclose ambiguity — even at the cost of occasional over-caution, without
ever using that disclosure to block the recommendation itself.

---

## 6. Assumptions and power/limits

- **A design error was found and corrected during review.** An earlier pass
  proposed that ambiguity should block Montauk from naming a Recommended at
  all. Charter §9.1 (DECIDED) and D51 state the opposite verbatim; that
  language is removed from §1/§4. A **residual, non-mechanical risk**
  remains: Max, seeing the flag, may on his own initiative delay approving an
  Active switch anyway — a soft, individual-judgment form of incumbent
  protection running through his own risk aversion, not system logic. That's
  his legitimate prerogative, not a defect, but it means the flag's actual
  effect on switch behavior and churn should be *measured* (Experiment A,
  F2), not assumed neutral.
- **TECL's history is short; regimes are few** (a handful of materially
  independent macro episodes). Experiments A–B are necessarily low-power;
  report results as **provisional and diagnostic**, not settled, until
  several real Gold cohorts accumulate. This is a plausible extension — not
  a directly tested claim — of Lichtenstein/Fischhoff/Phillips' low-repetition
  calibration problem (§2).
- **The cited literature is medicine, organ donation, and general judgment
  research — not finance, not single-user appliances.** Every numeric effect
  size in §2 explicitly does not transfer as a Montauk threshold; only the
  qualitative mechanisms do (nudge repetition erodes attention; unlabeled
  probabilities mislead; defaults dominate choice; standardizing judgment
  reduces noise). No re-trigger day-count or confidence level is licensed
  without Montauk's own calibration (§3).
- **MCS conservatism for TECL is a hypothesis, not an established fact.**
  Published financial-simulation critiques of MCS's multiple-testing
  robustness are logged repo-internally ([Evidence: secondary, repo-internal])
  but not independently re-verified this session. This document predicts MCS
  will run conservative (wide sets, frequent flags) rather than falsely
  precise for TECL — the safer direction per §5 — but that is exactly what
  Fixture F1 and Experiment B must confirm, not a fact Max should assume
  before seeing it demonstrated.
- **The OECD/JRC citation anchoring Experiment C remains only secondarily
  corroborated** (§2, §3, §8 Q5). Its role is limited to context for a
  self-contained statistical decision rule.
- **No statistically validated claim about Max's own decision quality is
  possible** — one user, no controlled trial. Every recommendation here is a
  decision-architecture design control informed by transferable mechanisms,
  not an empirically validated causal claim about this specific user.
- **Double-counting audits are only as good as their input list.** Experiment
  C must be re-run whenever §9.2's formula changes.

---

## 7. Required fixtures and durable artifacts

| Fixture | Contents | Expected result | Retention |
|---|---|---|---|
| **F1 — Synthetic leaderboard panel** | Seeded generator, N∈{5,20,50}: one true-signal row, noisy clones, pure-noise rows. | MCS excludes the true-signal row above a predeclared edge size; clones/noise stay ambiguous. Board still names one deterministic top rank among ambiguous rows — ambiguity and naming a recommendation aren't mutually exclusive. | Permanent; Experiment B's acceptance fixture. |
| **F2 — Historical churn-replay** | Replay the frozen rule against the null model and full real record. | Churn at/below the frozen ceiling under null; real churn reported alongside, not substituted. | Permanent, extended as history accrues. |
| **F3 — Switch-confirmation copy matrix** | {Recommended-only, Active-eligible} × {pointer-only, opposite-state}, ambiguity on/off. | Distinct predeclared copy/friction per scenario; opposite-state always gets inline disclosure + second step; ambiguity changes content, never card type. | Permanent; re-run on any confirmation-flow change. |
| **F4 — Deferral/dismissal state table** | Flagged → {deferred→resurfaces; dismissed→suppressed until re-trigger delta} → resolved. | Transitions match exactly for a scripted sequence. | Permanent; re-run if the re-trigger delta changes. |
| **F5 — Double-counting seeded-defect fixture** | Score-input matrix with one deliberately duplicated input. | Audit flags seeded R² above threshold, blocks ratification. | Permanent; run before every formula version is ratified. |
| **F6 — Drawdown/catastrophe completeness fixture** | Gold row with known large drawdown and named-catastrophe result. | Card renders both inline, above the fold, before any control is interactable. | Permanent; re-run on any card redesign. |

All fixtures are deterministic (fixed seeds/inputs/expected output) so CI or
manual acceptance can detect drift without re-deriving the calibration.

---

## 8. Unresolved owner decisions

1. **Re-trigger delta for a dismissed recommendation.** **Default:** re-alert
   if the gap widens by an additional 50% of its own threshold, or 20 new
   verified bars pass, whichever first. **Tradeoff:** tighter → more churn
   risk; looser → Max could miss a strengthening edge.
2. **Confidence level for `leader not clearly separated`.** **Default:**
   pre-register 90% before Fixture 1 runs, with a predeclared fallback to 75%
   from the next dated pass if 90%'s flag rate exceeds the frozen ceiling —
   never chosen by comparing both after the fact (§3, Experiment B).
   **Tradeoff:** honest disclosure vs. a flag fired often enough to be tuned
   out.
3. **Friction for opposite-state switch approval.** **Default:** mandatory
   two-step confirmation (view → dedicated "this changes tomorrow's
   instruction, here is the evidence" screen → explicit confirm); no
   default-accept, no timeout auto-approval; pointer-only stays single-step.
   **Tradeoff:** friction on a real trade decision vs. protection against the
   highest-severity error in §5. The after-close-to-next-open cadence (§4.2)
   already removes intraday time pressure.
4. **Visibility of dismissed items.** **Default:** always retained in the
   append-only control database, visible on request, excluded from the
   default digest (§12). **Tradeoff:** small storage/UI cost vs. Max later
   wondering whether a candidate was ever evaluated.
5. **Standing of the double-counting audit in sign-off.** **Default:** a
   named, separately dated acceptance item before any formula ratification —
   contingent on resolving the OECD/JRC citation's verification status first:
   obtain a primary quoted passage, or ratify the audit as standing on its
   R²/correlation statistics alone, without citing the handbook as verified
   authority. **Tradeoff:** a short delay vs. treating a load-bearing audit as
   settled on an unverified secondary read.
6. **Should ambiguity add friction to an Active-switch confirmation beyond
   its existing disclosure?** The charter forecloses gating the Recommended
   pointer itself (§9.1, DECIDED) but doesn't decide whether an ambiguous
   change proposed for Active needs anything beyond Q3's mandatory friction.
   **Default:** no additional mechanical friction layer — fold the flag into
   the existing card as context (F3), rather than inventing a second, ungated
   policy the charter never asked for. **Tradeoff:** simplicity/compliance vs.
   a stronger nudge some might want when ambiguity and opposite-state
   coincide.

---

## References

1. Gigerenzer, G. & Edwards, A. "Simple tools for understanding risks."
   *BMJ* 327(7417):741–744 (2003). doi:10.1136/bmj.327.7417.741 — **Primary.**
   No open-access mirror confirmed this session; cite the DOI only.
2. Lichtenstein, S., Fischhoff, B. & Phillips, L. D. "Calibration of
   Probabilities: The State of the Art to 1980." In *Judgment Under
   Uncertainty*, Cambridge University Press, 1982, pp. 306–334. — **Primary.**
3. Hansen, P. R., Lunde, A. & Nason, J. M. "The Model Confidence Set."
   *Econometrica* 79(2):453–497 (2011). doi:10.3982/ECTA5771 — **Primary**
   (bibliographic/abstract confirmed via secondary indexing; full proof text
   not independently re-derived behind paywall).
4. Kahneman, D., Sibony, O. & Sunstein, C. R. *Noise: A Flaw in Human
   Judgment*. Little, Brown Spark, 2021. — **Primary** for the "decision
   hygiene" framework; synthesizes earlier studies needing separate tracing
   for individual figures.
5. Ancker, J. S., Edwards, A., Nosal, S., et al. "Effects of workload, work
   complexity, and repeated alerts on alert fatigue." *BMC Med Inform Decis
   Mak* 17:36 (2017). https://pmc.ncbi.nlm.nih.gov/articles/PMC5387195/ —
   **Primary,** full text fetched and figures verified this session.
6. Johnson, E. J. & Goldstein, D. "Do Defaults Save Lives?" *Science*
   302(5649):1338–1339 (2003). doi:10.1126/science.1091721 — **Primary;**
   core finding corroborated via secondary sources this session (publisher
   page returned 403 to direct fetch).
7. OECD / European Commission Joint Research Centre. *Handbook on
   Constructing Composite Indicators*. OECD Publishing, 2008. —
   **Primary** (official guidance); the specific correlation/double-counting
   passage remains **not independently verified** after two attempts this
   session (PDF fetch failed to extract clean text; targeted search returned
   only a secondary characterization). Open until a follow-up read confirms
   the exact passage — see §2, §3, §6, §8 item 5.
8. Project Montauk 3.0 charter, decision log, and implementation plan
   (`charter.md` §§0.1, 2.3, 4.2–4.3, 9.1–9.2, 12, 16; `decisions.md` D18,
   D34, D51; `implementation-plan.md` Stage 6) — **Product-primary**
   (repo-internal, no external URL).
9. `validation-engine-hardening.md`, candidate-disposition table (Model
   Confidence Set row) — **Secondary within this repo** (file's presence and
   quoted line confirmed this session; references an unnamed published
   critique of MCS this session did not independently locate — flagged as a
   follow-up in §6).

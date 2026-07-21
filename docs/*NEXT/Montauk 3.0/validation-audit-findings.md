# Montauk 3.0 — G10 Validation Correctness Audit (findings log)

Line-by-line correctness audit of `scripts/validation/` against each method's cited
literature. This is the **G10** item from [validation-engine-hardening.md](validation-engine-hardening.md),
made a committed Montauk 3.0 deliverable (2026-06-17). Findings are logged here as each
file is audited. Severity is about the **certification claim**, not code style.

**Scope:** `scripts/validation/` (~5,900 lines).

> **Contract note (updated 2026-07-21):** The owner intends every backtest survivor,
> regardless of human/AI origin, to face the same mandatory evidence planks and
> rigor. A structurally inapplicable algorithm may use a predeclared equivalent
> or valid `not_applicable` result; origin-based skipping and silent weight
> renormalization remain current behavior to audit, not the target 3.0 design.
> Missing, skipped, underpowered, incomplete, or unverifiable mandatory evidence
> blocks Gold, and Montauk Score cannot compensate. Search provenance still
> matters to multiplicity, but correction must estimate effective dependence
> rather than use raw near-twin counts. This implementation audit now feeds a
> separate validation-of-validation harness that measures both false-Gold and
> false-rejection behavior. The composite remains **Validation Score**, not a
> calibrated confidence probability, until forward reliability evidence earns
> that interpretation.

| File | Lines | Status |
|---|--:|---|
| `deflate.py` | 373 | ✅ audited 2026-06-17 |
| `pbo.py` | 391 | ⏳ next |
| `uncertainty.py` | 229 | ⏳ |
| `oos_walk_forward.py` | 300 | ⏳ |
| `reality_check.py` | 434 | ⏳ |
| `sprint1.py` | 506 | ⏳ |
| `candidate.py` | 804 | ⏳ |
| `integrity.py` | 565 | ⏳ |
| `confidence_v2.py` | 545 | ⏳ |
| `cross_asset.py` | 225 | ⏳ |
| `pipeline.py` | 1518 | ⏳ |

**Severity key.** **High** = could let an overfit strategy through, or materially
misstate the overfit verdict. **Medium** = directional bias / fragility, bounded
impact. **Low** = reproducibility / documentation.

---

## `deflate.py` — selection-bias deflation (audited 2026-06-17)

**Verified correct.** The Beta method-of-moments fit (`α=μ·c, β=(1−μ)·c,
c=μ(1−μ)/σ²−1`), the `P(max < observed) = F(observed)^N_eff` identity, the
**no-silent-fallback** fit (raises on an infeasible MoM solve instead of substituting
`Beta(10,10)`), the engine+data **cache fingerprint**, and the **ratcheting N_eff
high-water mark** are all implemented correctly. The *design* is sound.

### D-1 — Parametric tail extrapolation (HIGH)
The verdict hinges on the Beta CDF/PPF at the `1 − 1/N_eff` quantile (N_eff ≈ 4,000+ →
~0.99975), but the Beta is fit **by moments to the body** of the null. Moment-matching
does not constrain the extreme upper tail, and the result is violently tail-sensitive:
`0.999^4116 ≈ 0.016` ("noise") vs `0.9999^4116 ≈ 0.66` ("strong") — the verdict swings
on the 4th decimal of the fitted CDF, exactly where a body-fit Beta is least
trustworthy. The empirical `rs_p99` / `rs_max` are computed but never used to validate
or cap the parametric tail.
**Fix:** compare and validate appropriate bounded-tail / generalized-extreme-value
models on per-family block maxima rather than preselecting a Gumbel shape, or at
minimum cross-check the Beta tail against the empirical max and raise the null if
they diverge. Highest-value correctness fix in the file.

### D-2 — Expected-max quantile proxy is not a validated expectation (MEDIUM)
`expected_max_beta` substitutes the `(1 − 1/n)` quantile for `E[max]`.
No single plotting-position quantile is the expected maximum for an arbitrary
fitted Beta distribution, so the size and even practical importance of the
approximation error must be measured rather than asserted.
**Fix:** compute the fitted-Beta maximum expectation from
`E[max] = integral_0^1 (1 - F(x)^n) dx` using stable numerical integration (or
an independently verified analytic/simulation equivalent), then test the current
proxy's bias across the fitted parameter range.

### D-3 — N_eff blind to generation breadth (MEDIUM now; CRITICAL at 3.0 scale — G1)
`estimate_n_eff` counts only **hash-indexed (mined) configs**. Families that die on the
cheap screen, and authored-but-un-mined families, never enter the count. Under Montauk
3.0 (auto-enter, grind-constantly) the *uncounted* breadth becomes the dominant
multiplicity. This is the design-level G1 gap, confirmed at the code level.
**Fix:** retain the complete observable proposal/search ledger, then estimate
effective dependence at family, campaign, and board/lifetime levels. Do not
simply feed a raw family/configuration count in as independent hypotheses;
validate the correction's operating characteristics against controls.

### D-4 — Null conditioned on ≥3 trades (LOW)
Only random configs with `num_trades ≥ 3` enter the null, reshaping its distribution
(drops the degenerate low tail). Plausibly consistent (the champion is also ≥3 trades)
and likely conservative, but it's an undocumented modeling choice that should be stated
and its directional effect confirmed.

### D-5 — Rounded β params used downstream (LOW)
`deflate_regime_score` reads the cache's `beta_alpha`/`beta_beta`, stored `round(…, 2)`.
Numerically negligible, but for bit-exact reproducibility keep full precision in cache.

**Net:** the design is sound and the core identities are correct; the robustness risk is
concentrated in **D-1** (tail extrapolation), which is also where the whole
"is-it-noise" verdict is most sensitive. **D-3 (=G1)** remains the structural priority.

> Also worth noting (current implementation, not endorsed 3.0 policy): this
> RS-deflation feeds the `selection_bias` sub-score at weight **0.10** on the T2
> route. The anti-overfit deflation therefore has bounded influence on the final
> composite. The universal-contract design must decide whether selection-bias
> evidence is a mandatory plank rather than something stronger scores can offset.

# Montauk 3.0 — G10 Validation Correctness Audit (findings log)

Line-by-line correctness audit of `scripts/validation/` against each method's cited
literature. This is the **G10** item from [validation-engine-hardening.md](validation-engine-hardening.md),
made a committed Montauk 3.0 deliverable (2026-06-17). Findings are logged here as each
file is audited. Severity is about the **certification claim**, not code style.

**Scope:** `scripts/validation/` (~5,900 lines).

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
**Fix:** fit the tail directly (EVT / Gumbel on per-family block maxima), or at minimum
cross-check the Beta tail against the empirical max and raise the null if they diverge.
Highest-value correctness fix in the file.

### D-2 — Expected-max proxy is mildly anti-conservative (MEDIUM)
`expected_max_beta` uses the `(1 − 1/n)` quantile as `E[max]`. For n iid draws
`E[max] ≈ F⁻¹(1 − 1/(n+1))`, which is *higher*, so the proxy slightly **underestimates**
the expected max → `beats_noise = observed > expected_max` is marginally too easy.
Honestly documented as a proxy, but the bias direction favors passing.
**Fix:** use `1 − 1/(n+1)` (or the standard −Euler-γ correction); near-free.

### D-3 — N_eff blind to generation breadth (MEDIUM — this *is* G1)
`estimate_n_eff` counts only **hash-indexed (mined) configs**. Families that die on the
cheap screen, and authored-but-un-mined families, never enter the count. Under Montauk
3.0 (auto-enter, grind-constantly) the *uncounted* breadth becomes the dominant
multiplicity. This is the design-level G1 gap, confirmed at the code level.
**Fix:** the G1 backlog item — count generated families and feed them in here.

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

> Also worth noting (not a bug): this RS-deflation feeds the `selection_bias` sub-score
> at weight **0.10** (T2). The anti-overfit deflation therefore has bounded influence on
> the final composite — a design choice (deflation *informs*, it doesn't *dominate*),
> but worth keeping in view when reasoning about how much the gate actually punishes
> selection bias.

# Project Montauk — Validation Philosophy

> No real strategy is ever 100% certain. The market will move in ways we can't predict. What we can do is *be honest about how confident we are* in each candidate, and use that confidence — not a binary stamp — to decide which strategy to trade right now.

---

## 1. Why Validation Exists

Project Montauk is trying to discover robust long-only TECL strategies. Overfitting is the default failure mode whenever a search is involved.

Validation exists to answer **two** questions:

1. Is this strategy *correct* — no lookahead, not cheating, respects the charter, beats B&H on shares?
2. *How confident* are we that the strategy will survive out-of-sample?

Question 1 is binary. Question 2 is a continuum.

The old pipeline tried to answer both with binary gates. That produced two failure modes: (a) real strategies with one marginal gate got rejected outright; (b) nothing T2 ever passed. This revision separates the two questions.

---

## 2. The Core Insight (unchanged)

**Overfitting risk is a property of how the strategy was selected, not the strategy itself.**

A 2-parameter strategy hand-authored from a hypothesis lives in a different statistical universe than the same 2-parameter strategy pulled from a 50,000-config GA population. The tier system still applies: T0/T1/T2 route candidates to the scrutiny their selection process deserves. What changes is *what the scrutiny produces*: a confidence score, not a verdict.

---

## 3. The Three Tiers (unchanged structure, new output)

Each candidate is registered under a tier that reflects how it was selected. The tier determines **which sub-scores apply** to its confidence composite.

### Tier 0 — Hypothesis

Hand-authored from an external prior (marker chart, charter, leverage-decay math, a published rule).

- ≤ 5 free parameters, all from the strict canonical set
- Pre-registered before first backtest

T0 composite uses: marker_shape, marker_timing, walk_forward, named_windows, era_consistency, cross_asset, trade_sufficiency.

### Tier 1 — Tuned

Hand-authored logic with a small declared grid sweep or non-canonical values.

- ≤ 8 free parameters
- Grid size committed up front

T1 adds parameter fragility (Gate 3) on top of T0's sub-scores.

### Tier 2 — Discovered

Pulled from optimizer top-N, GA population, or any large search.

- Any param count, any values

T2 adds Morris fragility + bootstrap + selection-bias deflation + concentration/jackknife on top of T1.

Selection bias scales validation scrutiny. It does not scale *whether* we pass — it scales *what evidence* we require before we'd be confident.

---

## 4. The Two-Layer Model

### Layer 1 — Correctness (hard-fail, no negotiation)

Strategies that fail any of these are disqualified regardless of everything else. These aren't about overfitting — they're about "is this even a valid strategy?":

- Engine integrity (bar-close signals, no lookahead, single position)
- Golden regression pass (`tests/test_regression.py` matches frozen ledger within ±0.001%)
- Shadow-comparator agreement (dev-only)
- Data-quality pre-check pass (all sources agree, manifest checksum valid, OHLC sane)
- Artifact completeness (all five standardized JSON artifacts emitted)
- Charter guardrails: TECL-only, long-only, single-position, ≤ 5 trades/year
- `share_multiple ≥ 1.0` (below B&H = charter mission violation)
- Strategy in registry + charter-compatible family
- No degenerate exposure (always-in or always-out across every 4-year window)

A correctness failure means the strategy *isn't a strategy*. No confidence score can rescue it.

### Layer 2 — Confidence (weighted, scored 0–100)

Everything else feeds a single `composite_confidence` score on [0, 1]. It is a weighted geometric mean of tier-applicable sub-scores (see `validation-thresholds.md` for weights) and remains the validation-stack composite for PASS/WARN/FAIL. Confidence v2 adds separate diagnostic `edge_confidence` and `capital_readiness` scores for future usefulness and deployability.

Each sub-score is a smooth [0, 1] value: hard-fail threshold → 0.0, soft-warn threshold → 0.5, full pass → 1.0, with smooth interpolation between. A close miss costs a little. A far miss costs a lot. Nothing is binary.

---

## 5. Admission Tiers

| Confidence | Label | Leaderboard |
|:-:|---|---|
| **0–39** | Reject | Hidden |
| **40–59** | Research only | Archived |
| **60–69** | Low-confidence PASS/WARN evidence | Archived |
| **70–89** | Certifiable confidence range | Eligible if anti-overfit certification also passes |
| **90–100** | High confidence | Highlighted if certified |

**70 is the validation PASS threshold.** It is necessary but not sufficient for the leaderboard. Leaderboard admission also requires the required anti-overfit certification checks to pass, producing `certified_not_overfit=True`. Below 70, the strategy is research output.

`promotion_ready` is the tier-appropriate PASS verdict. `certified_not_overfit = promotion_ready AND required anti-overfit certification checks`. `backtest_certified = certified_not_overfit AND artifact completeness`.

---

## 6. What "Confidence" Actually Means

A 78 is not a promise the strategy will beat B&H in 2027. It's a claim that across the checks we care about — time generalization, cycle timing vs markers, cross-asset sanity, parameter fragility, statistical search-bias correction — the candidate held up in **78% of the evidence we asked it to stand on**, with more weight on the checks that matter most for overfit detection.

A 92 is not "certainty." It's "across every bucket of evidence we had, this candidate was strong." That's the honest frame. The market will still do what the market does. The confidence score tells us *which strategy is the least-shaky bet we currently have*, not *which strategy will work*.

Operational consequence: confidence still matters, but it is not itself a permission slip. The leaderboard is the certified set, and confidence helps compare already-certified strategies rather than decide whether uncertified ones belong there.

---

## 7. What Changed From The Previous Framework

| Before | After |
|---|---|
| 7 gates, each with hard-fail power | 1 correctness whitelist (hard-fail) + weighted confidence score |
| Verdict: PASS / WARN / FAIL | Verdict: correctness check (binary) + confidence score (0–100) |
| Cross-asset TQQQ re-opt = hard fail | Cross-asset = weighted input (0.05) |
| Walk-forward OOS/IS < 0.65 = hard fail | Walk-forward = smooth score input |
| Named-window share_multiple ≤ 0 = hard fail | Named-window = smooth score input |
| Morris fragility max_swing > threshold = hard fail | Morris = smooth score input |
| Marker shape folded into one number | Marker shape AND per-cycle timing both weighted separately |
| Soft-warning cap as verdict mechanic | Removed — warnings are advisory only |
| composite_confidence as advisory number | composite_confidence IS the verdict |

The old mechanics are still computed internally (the thresholds still inform where the 0.5 and 1.0 anchors sit). They just no longer have veto power individually.

---

## 8. Principles

1. **Correctness is binary, confidence is a continuum.** Don't conflate them.
2. **Confidence ≠ certainty.** A 95 is not a promise. It's a claim that across every bucket of evidence, this candidate held up best.
3. **Selection bias still determines scrutiny.** T2 candidates face more sub-scores than T0. That's honest.
4. **Pre-registration still prevents laundering.** A T0 strategy is identified by its registration timestamp, not its final params.
5. **Low-frequency strategies are not punished.** A year of holding through new highs is a successful year.
6. **The leaderboard is a certified set.** Confidence drifts over time, so certification should be re-run as new data arrives. A strategy that falls out of certification should leave the leaderboard.
7. **Multiple strategies can run simultaneously** — this is the future state. The oscillator vision ("7 of 25 strategies are calling sell") requires a pool of high-confidence candidates, not a single PASS/FAIL anointed winner.

---

## 9. What Each Tier's Composite Looks Like

See `validation-thresholds.md` for exact weights. Summary:

- **T0 composite** is dominated by marker_shape + marker_timing + walk_forward + named_windows (together ~70% of weight). Cross-asset and trade-sufficiency fill the rest. No statistical overfit penalties because T0 cannot overfit.
- **T1 composite** adds parameter fragility (Gate 3) at ~15%. Marker and time sub-scores dilute slightly.
- **T2 composite** adds Morris fragility + bootstrap + selection-bias + regime consistency (~35% combined). The full statistical stack earns weight because the search process earns it.

Weights renormalize when sub-scores are skipped — T0 doesn't pay a penalty for not having a Morris score; its remaining weights scale up.

---

## 10. Per-Cycle Marker Timing

Previously, marker alignment was reported as a single `state_agreement` number that averaged timing-accuracy across the entire history. A strategy that was 60 bars late on COVID but early on 2018 could still score reasonably.

The new framework splits this into two sub-scores:

- **`marker_shape`** (state agreement): are the strategy's risk-on / risk-off periods in the same place as the markers, overall?
- **`marker_timing`** (per-cycle, magnitude-weighted): for each marker cycle transition, how close was the nearest strategy transition? Weighted by cycle magnitude (bigger drawdowns and bigger rallies carry more weight).

This is the change that directly penalizes strategies that fire late on COVID, late on 2022, or miss 2025. It is *the* structural answer to "why does my passing strategy make obviously dumb mistakes?"

---

## 11. Cross-Asset, Demoted

The cross-asset gate (Gate 6) previously hard-failed any strategy whose TQQQ same-param share_multiple fell below 0.50, and required a successful TQQQ re-optimization. The demotion:

- Cross-asset becomes a weighted sub-score (0.05, lowest of all)
- TQQQ re-opt hard-fail removed; it becomes a scored input
- The rationale: TECL is 3× leveraged and uniquely volatile. A strategy that works on TECL but struggles on QQQ is not automatically overfit — it may be exploiting leverage-regime dynamics that only exist at TECL's volatility. Cross-asset remains a useful check (it catches pure TECL cosplay) but it does not deserve veto power.

This directly addresses the manual-admission override of gc_vjbb that the team performed in 2026-04-20. Under the new framework, gc_vjbb would clear the 70 threshold without needing a manual exception.

---

*Last updated: 2026-04-21*

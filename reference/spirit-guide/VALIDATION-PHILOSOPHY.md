# Project Montauk — Validation Philosophy

> Validation difficulty must match selection bias. Same backtest result, different selection process, different statistical meaning.

---

## 1. Why Validation Exists

Project Montauk is trying to discover robust long-only TECL strategies. Overfitting is the default failure mode whenever a search is involved.

Validation exists to answer:

> Is this strategy probably real, or is it just the luckiest thing we found given how it was selected?

If the project cannot answer that question honestly, the rest of the factory does not matter.

---

## 2. The Core Insight

**Overfitting risk is a property of how the strategy was selected, not the strategy itself.**

A 2-parameter strategy hand-authored from a hypothesis lives in a different statistical universe than the same 2-parameter strategy pulled from the top of a 50,000-config GA population. The first was selected from a search space of size ~1 (a human's hypothesis). The second was selected from a search space of size 50,000.

Applying the same validation gates to both is incoherent. The honest move is to scale validation difficulty with selection bias.

This is why Project Montauk uses three validation tiers.

---

## 3. The Three Tiers

Each candidate is registered under a tier that reflects how it was selected. The tier determines which validation pipeline runs.

### Tier 0 — Hypothesis

Hand-authored from an external prior (the marker chart, charter principles, the math of leverage decay, a published rule).

Requirements:

- ≤ 5 free parameters
- All parameter values from the **strict canonical set** (see Section 5)
- Strategy registered with name, description, and committed parameter values **before** any backtest is run
- Conceptually motivated, not laundered from observed GA outputs

T0 candidates clear a **light pipeline**. The selection bias is small, so the gates can be small.

### Tier 1 — Tuned

Hand-authored logic, but parameter values come from a small declared grid search or use non-canonical values.

Requirements:

- ≤ 8 free parameters
- Either: (a) param values are non-canonical but committed up front, or (b) values come from a declared grid sweep with size committed up front
- The grid size is recorded and factored into the validation gates

T1 candidates clear a **medium pipeline** that adds parameter-plateau and small-basin checks.

### Tier 2 — Discovered

Pulled from optimizer top-N, GA population, or any large search.

Requirements:

- Any param count
- Any param values
- Selected from any search budget

T2 candidates clear the **full statistical stack**: deflation, regime boundary perturbation, fragility, jackknife, HHI, mutation survival, the works.

---

## 4. Tier Routing Rules

These rules prevent T0 from becoming a backdoor for hidden search bias.

1. **Pre-registration is mandatory for T0.** The strategy file, parameter values, and a one-line hypothesis are committed to the registry before the first backtest. No exceptions.
2. **Optimizer-tuning auto-promotes the tier.** If the GA touches a strategy, it becomes T2. If a small declared grid search touches it, it becomes T1.
3. **Provenance honesty.** A T0 strategy that came from staring at GA outputs ("the GA winner used EMA-37 so let me try EMA-50 by hand") is laundered selection bias and should be registered as T2. T0 means *conceptually motivated from outside the search*.
4. **Cross-asset is mandatory at every tier.** It is the highest-power honesty check available and costs almost nothing.
5. **Same data, different gates.** All tiers see the full TECL history. The split is about what additional scrutiny is warranted, not what data is shown.

---

## 5. Strict Canonical Parameter Set (T0)

T0 strategies may only use parameter values drawn from this fixed list:

| Parameter family | Allowed values |
|------------------|---------------|
| EMA / SMA / TEMA period | 7, 9, 14, 20, 21, 30, 50, 100, 150, 200, 300 |
| RSI period | 7, 14, 21 |
| ATR period | 7, 14, 20, 40 |
| ATR multiplier | 0.5, 1.0, 1.5, 2.0, 2.5, 3.0 |
| Lookback / Donchian / Highest-Lowest period | 5, 10, 20, 50, 100, 200 |
| Slope / confirmation bars | 1, 2, 3, 5 |
| Cooldown bars | 0, 1, 2, 3, 5, 10 |
| Percent thresholds (drawdown, drop, etc.) | 5%, 8%, 10%, 15%, 20%, 25% |
| MACD fast / slow / signal | (12, 26, 9), (8, 17, 9) |

Anything outside this list lifts the strategy to T1.

The reason for the strict list: it forces hypotheses to be argued from first principles, not param-fiddled into existence. "200-day moving average" is a thing in the world. "EMA-187" is a search result.

---

## 6. The Core Rule

A raw optimizer winner is **not** a winner.

A strategy only becomes real when it receives a final **PASS** verdict from the validation pipeline **at its tier**.

Operational consequences:

- **PASS**: eligible for leaderboard promotion, champion selection, and Pine generation. Tagged as `T0-PASS`, `T1-PASS`, or `T2-PASS`.
- **WARN**: useful research output, but not promotable
- **FAIL**: archive only, keep searching

The leaderboard is a memory of validated PASS results across all tiers. The tier tag is honest disclosure of what level of evidence backs the strategy.

---

## 7. What Each Tier's Pipeline Tests

### T0 Pipeline (Hypothesis)

Failure modes being defended against:

- coding bug (lookahead, repaint, off-by-one)
- TECL-only cosplay (works on TECL, fails on TQQQ / UPRO)
- regime-period dependence (worked one half of the data, failed the other)
- doesn't actually trade the marker shape

Pipeline:

1. Code integrity checks (no lookahead, bar-close exits, single position)
2. Cross-asset on TQQQ + UPRO + QQQ — must beat B&H share count on at least 2 of 3
3. Walk-forward split at the midpoint — both halves beat B&H share count
4. Marker shape alignment — state agreement ≥ 80%, median lag < 20 bars, zero missed marker cycles

### T1 Pipeline (Tuned)

T0 pipeline plus:

5. Parameter plateau — strategy survives ±30% wiggle on each tuned parameter without losing share-count edge
6. Concentric shell on the tuned region — small basin (high fitness only on a knife-edge config) is a fail

### T2 Pipeline (Discovered)

T1 pipeline plus the full statistical stack from the research synthesis:

7. Deflated regime score (selection-bias correction)
8. Regime boundary perturbation
9. Delete-one-cycle jackknife
10. HHI on per-cycle contributions
11. Morris fragility / interaction effects
12. Mutation survival rate
13. Stationary bootstrap CIs
14. Cross-asset re-optimization

The full stack is the price of using the search machine. It is not punishment — it is what a 50,000-config selection process actually requires to be honest.

---

## 8. Principles

1. **Validation is mandatory at every tier.** Light is not the same as absent.
2. **PASS at the appropriate tier gets promoted.** Raw scores never outrank a failed validation.
3. **Pre-registration prevents laundering.** A T0 strategy is identified by its registration timestamp, not by its final params.
4. **Honesty beats excitement.** A strategy that looks great but fails its tier's gates is not "almost ready." It is rejected.
5. **The output must be deployable.** The end product is a Pine candidate.
6. **Deployment overlays are downstream.** The Roth overlay sits after PASS, not before.
7. **Low-frequency strategies are not punished.** A year of holding through new highs is a successful year.

---

## 9. Current Direction

The project has the right validation culture (integrity checks, cross-asset work, statistical governor, fragility). What changes with this philosophy revision:

- introduce explicit T0 / T1 / T2 routing
- formalize the strict canonical parameter set for T0
- formalize marker-shape alignment as a first-class gate (not a soft prior)
- formalize share-count multiplier as the primary metric (not vs_bah dollars)
- remove trade-frequency punishment for low-trade strategies
- keep the existing T2 stack intact — it is not wrong, it is just being scoped to its actual job

Threshold values, formulas, and implementation details belong in the validation scripts. This document defines the framework.

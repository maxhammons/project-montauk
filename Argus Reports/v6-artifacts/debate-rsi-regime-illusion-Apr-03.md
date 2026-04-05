# Debate: RSI Regime 4.7x Fitness Superiority -- Illusion or Reality?

**Date**: 2026-04-03
**Debate ID**: v6-debate-rsi-regime-illusion
**Format**: 3-round structured debate with judgment

---

## Claim Under Debate

> "RSI Regime's 4.7x fitness superiority over Montauk 8.2.1 is an illusion created by a crippled baseline, wrong RSI signals, and in-sample-only evaluation. The actual superiority is unknown and could be zero."

**Defender (Data-Integrity)**: The claim is TRUE -- the 4.7x is an illusion.
**Attacker (Velocity)**: The claim is OVERSTATED -- RSI Regime likely IS superior even with a correct baseline.

---

## Evidence Audit (Code-Verified Before Debate)

Before beginning arguments, both sides stipulate to the following facts verified directly in the codebase:

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| 1 | `montauk_821` in `strategies.py` uses 30-bar EMA for cross exit instead of real 8.2.1's 500-bar EMA | **TRUE** | `strategies.py:74` uses `ema_s < ema_m` (15 vs 30). Real 8.2.1 Pine at line 20: `longEmaLen = input.int(500)`, line 157: `crossunder(emaShort, emaLong)` |
| 2 | `montauk_821` missing 6+ features | **TRUE** | Missing: sideways filter (Donchian), TEMA entry gates, TEMA slope exit, trailing stop, sell confirmation bars (`barssince` logic), 500-bar long EMA. All present in `backtest_engine.py` `StrategyParams` and the Pine Script. |
| 3 | RSI uses `np.diff(series, prepend=series[0])` causing 1-2 bar shift | **PARTIALLY FALSE** | `strategy_engine.py:95`. The `prepend=series[0]` makes `delta[0]=0` and `delta[i]=series[i]-series[i-1]` for i>=1, which correctly mirrors Pine's `close - close[1]`. No bar shift occurs. The delta array is the same length as the input, correctly aligned. |
| 4 | Only 19 generations / 36 seconds / 1,330 evaluations | **TRUE** | `evolve-results-2026-04-03.json:3-5`: `elapsed_hours: 0.01`, `total_evaluations: 1330`, `generations: 19` |
| 5 | No walk-forward validation | **TRUE** | `evolve.py` runs the full dataset through `backtest()` with no train/test split. `validation.py` exists in the project but is not called by `evolve.py`. |
| 6 | 100% win rate on 10 trades | **TRUE** | `rsi-regime-2026-04-03.json:10-11`: `trades: 10`, `win_rate: 100.0`. The evolve results show a slightly different config with 12 trades / 75% win rate. |
| 7 | 75.1% max drawdown | **TRUE** | `evolve-results-2026-04-03.json:28`: `max_dd: 75.1` |
| 8 | Fitness ratio is 4.7x | **TRUE** | RSI Regime: 2.18, montauk_821: 0.46. Ratio = 4.74x. Source: `evolve-results-2026-04-03.json` |

---

## ROUND 1: Opening Statements

### Defender (Data-Integrity) -- "The 4.7x is an illusion"

The 4.7x fitness gap is meaningless because the denominator is broken. The montauk_821 implementation in `strategies.py` is not Montauk 8.2.1. It is a lobotomized version missing the core exit mechanism and 6+ production features.

**The EMA cross exit is catastrophically wrong.** The real 8.2.1 exits when the 15-bar EMA crosses below the **500-bar EMA** -- a slow, structural trend signal. The `strategies.py` version exits when the 15-bar EMA crosses below the **30-bar EMA** -- a fast, noisy signal that fires constantly. This single change transforms the strategy from a trend-follower that holds for months into a jittery system that exits on every minor pullback. The evolve results confirm this: montauk_821's best config produces 28 trades (1.6/yr) with all 28 exits labeled "Q" (Quick EMA) -- the EMA cross exit never even fires meaningfully because the 30-bar cross is so fast it is redundant with the Quick EMA exit.

**Six production features are missing.** The sideways filter, TEMA entry gates, trailing stop, TEMA slope exit, sell confirmation bars, and the actual long EMA. These are not minor additions -- the sideways filter alone prevents entries during range-bound markets, and the `barssince(crossunder)` confirmation logic is the entire intellectual core of 8.2.1's exit system. Without them, the optimizer is testing a different strategy that happens to share a name.

**The evaluation is in-sample only.** 19 generations over 36 seconds on the full TECL dataset with no walk-forward split. The winning RSI Regime config has 10-12 trades over 17 years of data. With parameters tuned to fit this tiny sample, overfitting is not just possible -- it is the default expectation. The 100% win rate on 10 trades is the signature of a curve-fitted strategy.

**75.1% max drawdown.** Even accepting the fitness number at face value, a strategy that draws down 75.1% has destroyed three-quarters of the account. On a 3x leveraged ETF, this means a period where TECL dropped and the strategy was fully invested the entire way down. The fitness function's drawdown penalty (`1 - DD/200`) is far too gentle -- at 75.1% DD, the penalty is only 0.625x.

The true comparison should be RSI Regime vs the full `backtest_engine.py` implementation of 8.2.1 (which has all features, including the 500-bar EMA), run through walk-forward validation. That comparison has never been done.

---

### Attacker (Velocity) -- "The 4.7x is overstated but RSI Regime IS superior"

The Defender is correct that the baseline is crippled. This is stipulated. But the claim overreaches when it says the actual superiority "could be zero." Let me explain why.

**The gap is so large that even generous corrections cannot close it.** RSI Regime fitness: 2.18. Montauk_821 fitness: 0.46. Even if the full, correct 8.2.1 implementation were 3x better than the crippled version (fitness ~1.38), RSI Regime still wins by 1.6x. To claim the gap "could be zero" requires believing the full 8.2.1 would score 2.18+ -- a 4.7x improvement over its crippled version. That is extraordinary.

**The structural logic of RSI Regime is sound.** Buy when RSI crosses up through 35 (oversold recovery) with price above a 150-bar trend EMA. Exit when RSI hits 80 (overbought). This is textbook mean-reversion on a leveraged ETF -- exactly the kind of regime where 3x instruments overshoot and snap back. The logic is not a random parameter coincidence; it exploits a known structural property of leveraged ETFs.

**The RSI calculation is NOT shifted.** The Defender's brief claimed `np.diff(series, prepend=series[0])` shifts signals 1-2 bars, but code inspection proves this is false. The prepend approach produces `delta[i] = series[i] - series[i-1]` for all i >= 1, which is identical to Pine Script's `close - close[1]`. This invalidates one of the three pillars of the claim.

**The v3 backtest engine already validated 8.2.1's real performance.** The full `backtest_engine.py` implements every feature of 8.2.1 (500-bar EMA, sideways filter, TEMA, trailing stop, confirmation bars). Its default parameters match the Pine Script exactly. The project has the infrastructure to test the real 8.2.1 -- and the real 8.2.1's known performance on TECL is modest. It is a conservative trend-follower that holds long positions through extended bull runs. Its strength is avoiding bear markets, not maximizing returns.

**10-12 trades over 17 years is structurally appropriate.** A strategy that trades 0.6-0.7 times per year on TECL is not "overfitting" -- it is capturing major regime shifts. The low trade count is a feature of the oversold-recovery logic, not a sign of data-mining. Each trade corresponds to a major TECL drawdown and recovery.

---

## ROUND 2: Cross-Examination

### Defender questions Attacker

**Q1: You claim even a 3x correction cannot close the gap. But the crippled montauk_821 exits every trade via "Quick EMA" (all 28 exits are "Q"). If the real 8.2.1 with 500-bar EMA holds through those minor pullbacks and captures the full bull runs, couldn't its fitness easily be 3-5x higher?**

**Attacker's response:** This is a fair challenge. The 500-bar EMA cross exit would indeed fire far less frequently, allowing longer holds through bull runs. But here is the critical counter: the optimizer already explored the parameter space for montauk_821, including `trend_ema` up to 120 and `med_ema` up to 60. The best it found was 0.46. Even doubling `med_ema` to 60 -- which makes the cross exit much slower -- did not produce fitness above 0.46. The structural ceiling of an EMA cross system appears to be well below 2.18.

However, I concede that 500-bar EMA is well outside the search space (max med_ema is 60), and the missing features (sideways filter, TEMA gates) could compound to produce a meaningfully higher score. I revise my estimate: the full 8.2.1 could plausibly reach fitness 0.8-1.2, but 2.18 remains implausible for an EMA cross system on TECL.

**Q2: You say the RSI logic is "sound." But a 100% win rate on 10 trades over 17 years, with 75.1% max drawdown, means the strategy was fully invested during a near-total wipeout and still profited on exit. Doesn't this suggest the RSI thresholds were precisely calibrated to the specific TECL drawdown/recovery dates?**

**Attacker's response:** The 100% win rate is indeed suspicious and I flagged it as concerning. However, note that the evolve results file shows a *different* winning config with 12 trades and 75% win rate (3 losing trades), which is more realistic. The 100%-win-rate config in the winners file appears to be from an earlier, shorter run.

On the 75.1% drawdown -- this is serious. It means the strategy was in a position that lost 75% of equity at one point before eventually recovering. This is not a "win" in any practical sense even if the trade was technically profitable at exit. I concede this significantly undermines the quality of the result.

### Attacker questions Defender

**Q1: You claim the full 8.2.1 has "never been tested" against RSI Regime. But `backtest_engine.py` has a complete implementation. If the Argus team ran that comparison right now, what is your prediction for the full 8.2.1's fitness score?**

**Defender's response:** I predict the full 8.2.1 with default parameters would score in the range of 0.7-1.5 on this fitness function. The 500-bar EMA makes it hold through minor pullbacks, capturing more bull run upside. The sideways filter prevents bad entries in choppy markets. The confirmation bars reduce whipsaws. All of these would improve vs_bah_multiple and reduce trade count (improving the frequency penalty).

However -- and this is critical -- even if the full 8.2.1 scored 1.5, the RSI Regime at 2.18 would still appear to "win" by 1.45x. My argument is not that 8.2.1 would match 2.18. My argument is that we do not know the true gap, the 4.7x number is fabricated by the broken baseline, and the RSI Regime's own score is unreliable due to in-sample-only evaluation. Both numbers need to be recalculated before any claim of superiority is valid.

**Q2: You emphasize that `strategies.py` montauk_821 is "lobotomized." But the optimizer tested 7 strategies including golden_cross, breakout, bollinger_squeeze, trend_stack, and tema_momentum. RSI Regime beat ALL of them by 4-70x. Are all 7 strategies crippled too?**

**Defender's response:** No -- but this actually helps my case. The other strategies in `strategies.py` (golden_cross, breakout, bollinger_squeeze, trend_stack, tema_momentum) are *complete implementations* of their respective logics. They are not missing features. And yet RSI Regime still crushed them by enormous margins. This tells us one of two things: either RSI Regime is genuinely exceptional, OR the fitness function and evaluation methodology (in-sample, 36 seconds, no validation) systematically favors the kind of strategy RSI Regime happens to be -- one that makes very few trades precisely at the bottoms of major TECL drawdowns, which are well-known historical events easily overfit.

The fact that breakout (fitness 0.50, 20 trades) and golden_cross (fitness 0.10, 10 trades) also performed poorly suggests the fitness function disproportionately rewards strategies with very few, very large winning trades -- exactly the profile produced by overfitting to known crash dates.

---

## ROUND 3: Revised Positions

### Defender (Data-Integrity) -- Revised

I maintain the core claim: **the 4.7x number is an illusion** and should not appear in any decision-making context. The evidence is overwhelming:

1. The denominator (montauk_821 at 0.46) represents a crippled strategy missing its core 500-bar EMA and 6+ features. **Stipulated by both sides.**
2. The RSI calculation is NOT shifted as originally claimed. **I concede this point.** One of the three pillars of the original claim falls.
3. The in-sample-only evaluation with 19 generations remains a fatal flaw. No walk-forward validation was performed, and `validation.py` exists in the project specifically for this purpose but was never called.
4. The 75.1% max drawdown makes the result practically useless regardless of fitness score.

**Revised position:** The 4.7x is definitively an illusion. The RSI signal shift claim was wrong, so one supporting argument fails. But the crippled baseline and absent validation are each independently sufficient to invalidate the comparison. The actual superiority of RSI Regime over a correct 8.2.1 baseline is **unknown**, and while it is unlikely to be zero (the Attacker makes reasonable structural arguments), it could plausibly be anywhere from 1.0x (no superiority) to 2.5x.

### Attacker (Velocity) -- Revised

I revise my position significantly after cross-examination:

1. **The 4.7x number is indeed wrong** and should be discarded. I agree with the Defender that the crippled baseline invalidates this specific ratio.
2. **RSI Regime likely has genuine superiority** over a correctly implemented 8.2.1, but the magnitude is unknown. My revised estimate is 1.3-2.0x, not 4.7x.
3. **The 75.1% max drawdown is a dealbreaker** for practical deployment regardless of fitness superiority. A strategy that loses 75% of equity is unsurvivable.
4. **The in-sample evaluation must be validated** before any claim of superiority is actionable. The fact that `validation.py` exists and was not used is damning.
5. **I withdraw my defense of the 100% win rate.** Upon reflection, 10 winning trades over 17 years on a 3x leveraged ETF that experienced multiple 70-90% drawdowns strains credulity.

**Revised position:** RSI Regime is a *promising candidate* that merits proper evaluation (walk-forward validation, correct 8.2.1 baseline, drawdown-appropriate fitness function). The 4.7x claim is wrong. The actual superiority is likely in the range of 1.3-2.0x but this is speculative until the proper comparison is run.

---

## JUDGMENT

### Verdict: CLAIM IS SUBSTANTIALLY TRUE (with one factual error)

The claim that "RSI Regime's 4.7x fitness superiority over Montauk 8.2.1 is an illusion created by a crippled baseline, wrong RSI signals, and in-sample-only evaluation" is **substantially true on 2 of 3 pillars and factually wrong on 1.**

#### Pillar-by-pillar:

| Pillar | Verdict | Weight |
|--------|---------|--------|
| Crippled baseline | **TRUE** -- `strategies.py` montauk_821 is missing 500-bar EMA, sideways filter, TEMA gates, trailing stop, confirmation bars, and TEMA slope exit. The 30-bar EMA cross exit is fundamentally different from the 500-bar cross used in production. | HIGH -- this alone invalidates the 4.7x |
| Wrong RSI signals | **FALSE** -- `np.diff(series, prepend=series[0])` correctly produces `delta[i] = series[i] - series[i-1]` with no bar shift. The RSI calculation is sound. | LOW -- this pillar collapses |
| In-sample-only evaluation | **TRUE** -- 19 generations / 1,330 evaluations / 36 seconds on the full dataset with no train/test split. `validation.py` exists and was not used. 10-12 trades over 17 years is a textbook overfitting scenario. | HIGH -- independently sufficient to invalidate |

#### The 4.7x number:

**Discard it.** The numerator (RSI Regime at 2.18) is in-sample-only and unvalidated. The denominator (montauk_821 at 0.46) represents a different, weaker strategy than production 8.2.1. The ratio of these two unreliable numbers is doubly unreliable.

#### What the actual superiority might be:

Both sides converged on a range of **1.0-2.5x** as plausible, with the Attacker estimating 1.3-2.0x. This is speculative. The proper comparison requires:

1. Running RSI Regime against the full `backtest_engine.py` implementation of 8.2.1 (which has all features and the 500-bar EMA)
2. Walk-forward validation using `validation.py`
3. A fitness function that penalizes 75%+ drawdowns far more aggressively
4. Running the optimizer for its intended 8 hours, not 36 seconds

#### Addendum -- the 75.1% max drawdown:

Both sides agreed this is a dealbreaker. Even if RSI Regime is genuinely superior by fitness, a strategy that draws down 75.1% is not deployable. On a $100,000 account, this means watching it drop to $24,900 before recovery. No human trader survives this psychologically, and most would be margin-called.

### Actionable Recommendations

1. **Fix `strategies.py` montauk_821** to use 500-bar EMA for cross exit (matching `backtest_engine.py`'s `StrategyParams.long_ema_len = 500`), and add the missing features (sideways filter, TEMA gates, trailing stop, sell confirmation).
2. **Re-run the optimizer** for the intended 8-hour duration with the corrected baseline.
3. **Integrate `validation.py`** into `evolve.py` so walk-forward validation runs automatically on winning configs.
4. **Tighten the fitness function** -- a 75% drawdown should produce a near-zero score, not a 0.625x penalty.
5. **Do not cite the 4.7x figure** in any analysis, decision, or report. It is wrong.

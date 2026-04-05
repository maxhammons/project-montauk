# Debate: Fitness Function Drawdown Permissiveness

**Claim:** "The fitness function in evolve.py is dangerously permissive on drawdown — a 75% max drawdown gets only a 0.625x penalty, actively promoting strategies that could ruin capital. A hard cap at 50-60% max drawdown should be imposed."

**Defender (Risk lens):** Hard cap IS necessary — 75% DD is unsurvivable for real capital.
**Attacker (Data-Integrity lens):** Hard cap is premature — the optimizer needs freedom to explore; drawdown is tunable later.

---

## Evidence Summary

### Code (evolve.py lines 49-70)
```python
def fitness(result: BacktestResult) -> float:
    if result is None or result.num_trades < 3:
        return 0.0
    bah = max(result.vs_bah_multiple, 0.001)
    dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)
    if result.trades_per_year > MAX_TRADES_PER_YEAR:
        freq_penalty = max(0.1, 1.0 - (result.trades_per_year - MAX_TRADES_PER_YEAR) * 0.3)
    else:
        freq_penalty = 1.0
    return bah * dd_penalty * freq_penalty
```

### Penalty curve
| Max DD | dd_penalty | Effect on raw fitness |
|--------|------------|-----------------------|
| 0%     | 1.000x     | No penalty            |
| 25%    | 0.875x     | Mild                  |
| 50%    | 0.750x     | Moderate              |
| 75%    | 0.625x     | Still passes easily   |
| 100%   | 0.500x     | Total wipeout halved  |
| Floor  | 0.300x     | Minimum multiplier    |

### Winning strategy (best-ever.json)
- **RSI Regime**: fitness 2.18, vs_bah 3.49x, CAGR 48.6%, max_dd **75.1%**, trades/yr 0.7, MAR 0.647
- 12 trades over ~17 years, 75% win rate, all exits on RSI signal ("R")
- On TECL (3x leveraged): 75% DD = $100K becomes $25K, requiring 300% gain to recover

### Comparison: other strategies
- montauk_821: fitness 0.46, max_dd 54.8% (current production strategy)
- breakout: fitness 0.50, max_dd 64.5%
- golden_cross: fitness 0.10, max_dd 75.1%
- trend_stack: fitness 0.03, max_dd 49.3%

---

## ROUND 1: Opening Statements

### RISK (Defender) — Hard cap is necessary

The numbers speak for themselves. RSI Regime won the tournament with fitness 2.18 while carrying a 75.1% maximum drawdown. Let me be precise about what this means in dollar terms on a 3x leveraged ETF:

**$100,000 becomes $25,000.** The investor then needs a 300% return just to break even. At 48.6% CAGR (which itself is the *best case* from an in-sample backtest), that recovery takes approximately 3 years — assuming the strategy even continues to work out of sample.

The fitness function awarded this strategy a dd_penalty of 0.625x. That is not a penalty — it is a *discount*. The strategy's raw vs_bah of 3.49x was multiplied down to only 2.18, which was still higher than every other strategy by a factor of 4x. The drawdown "penalty" did nothing to prevent this strategy from dominating.

The core problem is mathematical: the penalty function is linear and gentle (`1 - DD/200`), but the real-world damage from drawdown is exponential. A 50% drawdown requires 100% recovery. A 75% drawdown requires 300% recovery. A 90% drawdown requires 900% recovery. The penalty curve does not remotely reflect this asymmetry.

Furthermore, examine the strategy itself: 0.7 trades per year, 12 trades over 17 years. These are enormous, concentrated bets. When a strategy trades this rarely and carries 75% drawdown, you are essentially betting the portfolio on each position. One bad sequence — which the backtest cannot guarantee won't happen — and the capital is destroyed.

A hard cap at 50-60% drawdown would:
1. Eliminate strategies that are fundamentally unsurvivable in practice
2. Force the optimizer to find parameter combinations that balance return AND risk
3. Still allow significant drawdown tolerance (50% is already aggressive for a leveraged product)
4. Not require walk-forward validation infrastructure — it's a single `if` statement

**Proposed change:**
```python
if result.max_drawdown_pct > 60.0:
    return 0.0  # Hard kill — unsurvivable drawdown
dd_penalty = max(0.3, 1.0 - result.max_drawdown_pct / 200.0)
```

### DATA-INTEGRITY (Attacker) — Hard cap is premature

Risk's argument sounds compelling until you examine what evolve.py actually is: a *search tool*, not a deployment recommendation.

The optimizer ran for **36 seconds** (0.01 elapsed hours), 19 generations, 1,330 evaluations across 7 strategies. This is not a production run. This is a rapid exploration pass. Imposing a hard cap on a search tool because its 36-second output looks scary is like banning a telescope because you saw something you didn't like.

Let me address the specific points:

**1. RSI Regime's 75% DD is a property of *these specific parameters*, not the strategy class.**
The winning params use entry_rsi=35, exit_rsi=85, panic_rsi=15, trend_len=150. These are aggressive thresholds found in 19 generations. A longer optimization run would explore the parameter space more thoroughly and likely find configurations with lower drawdown. The search space allows entry_rsi from 25-45 and exit_rsi from 65-85 — tighter thresholds (entry_rsi=45, exit_rsi=70) would almost certainly reduce drawdown, but the optimizer hasn't had time to find those trade-offs.

**2. The optimizer already penalizes drawdown — it just needs more time.**
At 0.625x, the dd_penalty *is* doing work. If RSI Regime had achieved 3.49x vs B&H with only 30% drawdown, its fitness would be 3.49 * 0.85 = 2.97 — significantly higher. The penalty function creates selection pressure toward lower drawdown. After 19 generations, it hasn't had enough iterations to refine.

**3. A hard cap at 50% would have eliminated 4 of 6 viable strategies.**
Looking at the results: montauk_821 (54.8%), breakout (64.5%), rsi_regime (75.1%), golden_cross (75.1%). Only trend_stack (49.3%) and bollinger_squeeze (53.9%) survive a 50% cap. You'd be cutting the search space by two-thirds before the optimizer has had a chance to tune parameters downward.

**4. The correct fix is walk-forward validation, not a blunt filter.**
The real danger isn't that the optimizer found a high-DD strategy — it's that the optimizer might be overfitting. Walk-forward validation (which the codebase already has in `validation.py`) is the proper tool: it tests whether the strategy generalizes, including its drawdown characteristics. A hard cap is a band-aid over the actual problem.

**5. Drawdown is a continuous property, not a binary one.**
A strategy with 51% max DD and a strategy with 49% max DD are essentially identical in risk profile. A hard cap at 50% would reject one and accept the other. This is statistically arbitrary and discards information that the continuous penalty function preserves.

---

## ROUND 2: Rebuttals

### RISK rebuts Data-Integrity

Data-Integrity makes three errors that I need to address directly.

**Error 1: "It's just a search tool" is a dangerous framing.**
The purpose of a search tool is to surface *useful* results. A search tool that surfaces strategies with 75% drawdown as its top recommendation is broken, regardless of whether it's "just searching." The output of evolve.py flows directly into best-ever.json, which is the baseline that all future optimization work builds on. If the best-ever is a strategy that would destroy capital, every subsequent /spike session starts from a poisoned baseline.

Look at the actual code path: `save_best()` writes to `remote/best-ever.json` whenever a new global best is found (line 220-221). There is no intermediate validation step. The optimizer's output IS the project's canonical "best strategy." Calling it "just a search tool" understates its influence.

**Error 2: "The optimizer needs more time" is unfalsifiable.**
Data-Integrity argues that longer runs would find lower-DD variants. Perhaps. But this is equally an argument that longer runs would find *even higher-DD variants* with even higher raw returns, which the permissive penalty would continue to reward. The penalty function's gradient is simply too shallow: reducing DD from 75% to 50% gains only 0.125x in the multiplier (from 0.625x to 0.750x). That's a 20% fitness improvement for cutting drawdown by a third. The optimizer has very little incentive to explore lower-DD space when it can get more fitness by boosting raw return.

**Error 3: "4 of 6 strategies would be eliminated" is the point.**
Yes. Strategies with unsurvivable drawdown *should* be eliminated. montauk_821 at 54.8% DD is borderline but at least within the realm of aggressive trading. golden_cross at 75.1% is not. The optimizer should be steered away from these regions so it spends compute finding viable configurations, not polishing unsurvivable ones.

On the walk-forward validation point: I agree it's necessary, but it solves a *different* problem (overfitting). Walk-forward validation with a strategy that has 75% in-sample drawdown will produce 75-90% out-of-sample drawdown. Validation doesn't fix the underlying risk profile — it only measures whether the risk profile is stable.

**The analogy is seat belts.** Walk-forward validation is the crash test. A drawdown cap is the seat belt. You need both. You don't skip the seat belt because you plan to crash-test later.

### DATA-INTEGRITY rebuts Risk

Risk's rebuttal contains its own errors.

**On "poisoned baseline":** The best-ever.json file is a *tracking* mechanism, not a deployment gate. Nobody is auto-deploying from best-ever.json to TradingView. The human operator reviews the output, which is exactly what's happening right now in this debate. The system is working as designed: a high-DD strategy surfaced, was identified as problematic, and is being discussed. The fitness function flagged it — it just didn't kill it. That's signal, not poison.

**On "shallow gradient":** Risk correctly identifies that the gradient from 75% to 50% DD is only 0.125x, calling it insufficient incentive. But this is a feature, not a bug. The optimizer's job is to find the frontier of the return-risk tradeoff, not to pre-filter it. The human reviews the Pareto frontier and decides what risk level is acceptable. If the gradient were steeper, the optimizer would collapse toward low-DD, low-return strategies and the human would never see what's possible at higher risk levels.

Consider: if the cap had been at 50%, the human would only see montauk_821 (fitness 0.46) and bollinger_squeeze (fitness 0.06) as viable strategies. They would have no idea that an RSI regime approach exists that beats buy-and-hold by 3.49x. Even if 75% DD is unacceptable, the *knowledge* that this strategy class is powerful informs the next optimization run — "run RSI Regime for 8 hours with tighter exit_rsi and panic_rsi parameters."

**On the seat belt analogy:** A seat belt doesn't prevent you from driving fast — it protects you when something goes wrong. Risk's proposed hard cap is more like a speed limiter that prevents the car from exceeding 60 mph. It makes the car safer, but also prevents the driver from learning what the car can do. The correct seat belt equivalent is position sizing and portfolio allocation, which are deployment-level decisions, not optimizer-level decisions.

**The real question is: what is evolve.py optimizing FOR?**
If it's optimizing for deployable strategies, Risk is correct — hard cap now.
If it's optimizing for strategy discovery, Data-Integrity is correct — let it explore.

The codebase design (multiple strategies, parameter spaces, /spike workflow, generate_pine.py as a separate step) strongly suggests discovery. The pipeline has explicit human review gates. A hard cap removes information from the human reviewer.

---

## ROUND 3: Final Arguments

### RISK — Final

I'll concede one point and double down on two.

**Concession:** Data-Integrity is right that strategy discovery benefits from seeing the full risk-return frontier. I would not want to hide the existence of RSI Regime as a strategy class. The knowledge that RSI-based mean reversion on TECL can beat buy-and-hold by 3.49x is genuinely valuable.

**But here's what I won't concede:**

**1. The fitness score is used as a ranking mechanism, and high-DD strategies dominate the ranking.** RSI Regime's 2.18 fitness is 4.3x higher than the #2 strategy (breakout at 0.50). This isn't a close contest — the drawdown-permissive fitness function creates a massive moat for high-DD strategies. Every generation of evolution, the top-ranked chromosomes are high-DD variants. The optimizer spends the vast majority of its compute budget refining high-DD strategies because they consistently score highest. Lower-DD strategies are pushed to extinction in the population.

This is the operational damage: it's not that one bad strategy appeared in the output. It's that the fitness landscape is *shaped* to favor high-DD strategies, which means the evolutionary pressure systematically produces more of them and discards lower-DD alternatives that might have been tunable.

**2. The floor of 0.3x means even total wipeout strategies survive.** A strategy with 100% drawdown (total loss of capital) receives a 0.5x penalty. A strategy that wipes out the account then somehow recovers (which is impossible in reality) would score 0.5x of its raw return. The 0.3x floor means that even the most catastrophically dangerous strategies maintain 30% of their fitness. This is indefensible.

**My refined proposal — a compromise:**

Instead of a hard kill at 50%, implement an exponential penalty that respects both concerns:

```python
# Exponential DD penalty: gentle below 40%, aggressive above 60%
dd_penalty = np.exp(-2.0 * (result.max_drawdown_pct / 100.0) ** 2)
# 25% DD -> 0.88x | 50% DD -> 0.61x | 75% DD -> 0.32x | 100% DD -> 0.14x
```

This preserves the full frontier for discovery (no hard cap) while ensuring that 75% DD strategies score 0.32x instead of 0.625x. It would cut RSI Regime's fitness from 2.18 to ~1.12, still competitive but no longer 4.3x above everything else. The optimizer would face genuine selection pressure to explore lower-DD parameter space.

### DATA-INTEGRITY — Final

Risk's refined proposal is substantially more reasonable than the original hard-cap claim, and I want to acknowledge that. An exponential penalty preserves the information surface while reshaping the gradient. That said:

**1. The timing problem remains.** The 0.01-hour run is the elephant in the room. All fitness values from a 36-second, 19-generation run are noise. montauk_821's fitness of 0.46 is not a reliable estimate of that strategy's potential — it reflects the optimizer's best guess after barely exploring the space. Before redesigning the penalty function based on one run's output, the correct action is to run for 8 hours (the default) and see if the problem persists. The current penalty may be adequate when given real compute time.

**2. Changing the penalty function changes the fitness landscape, invalidating all prior comparisons.** best-ever.json tracks fitness scores. If the penalty changes, all historical scores become incomparable. This is a data integrity issue: any analysis that references "fitness 2.18" would now be meaningless. If the penalty must change, all historical results need to be re-evaluated — which the codebase doesn't currently support.

**3. My refined counter-proposal: add a secondary ranking dimension, don't change the primary score.**

Keep the existing fitness function for continuity and exploration. Add a "deployability score" that applies the stricter penalty:

```python
deploy_score = fitness(result) * np.exp(-2.0 * (result.max_drawdown_pct / 100.0) ** 2)
```

Report both. The optimizer evolves on fitness (discovery). The human reviews deploy_score (viability). This preserves the information surface, maintains historical comparability, and makes the drawdown cost visible without distorting the search.

---

## JUDGMENT

### Claim Evaluation

**The claim is PARTIALLY VALID.**

The claim has two parts:
1. "The fitness function is dangerously permissive on drawdown" -- **VALID**
2. "A hard cap at 50-60% max drawdown should be imposed" -- **INVALID as stated; a better solution exists**

### Reasoning

**On permissiveness (valid):** The evidence is unambiguous. A 75% max drawdown receives only a 0.625x penalty — barely a third of fitness removed for a loss that requires 300% recovery on a 3x leveraged ETF. The linear penalty curve (`1 - DD/200`) does not reflect the exponential real-world damage of deep drawdowns. The 0.3x floor means even total-wipeout strategies retain 30% of their fitness. The consequence is observable: RSI Regime won with 4.3x the fitness of any competitor despite carrying a drawdown that would destroy any real portfolio. This is not theoretical — the optimizer's evolutionary pressure is shaped by this function, and it is shaped toward high-DD strategies.

**On the hard cap (invalid as stated):** A hard `return 0.0` at 50-60% DD is too blunt. It discards valuable information about the strategy space, creates arbitrary cliff edges (51% vs 49% DD are nearly identical risks), and prevents the optimizer from surfacing strategy classes that could be tuned to lower drawdown with different parameters. Data-Integrity correctly identified that RSI Regime's 75% DD is a property of *specific parameter choices in a 36-second run*, not an inherent property of the strategy class.

### Recommended Action

**Implement an exponential drawdown penalty** (Risk's refined Round 3 proposal):

```python
dd_penalty = np.exp(-2.0 * (result.max_drawdown_pct / 100.0) ** 2)
```

| Max DD | Current penalty | Proposed penalty | Change |
|--------|----------------|-----------------|--------|
| 25%    | 0.875x         | 0.882x          | ~same  |
| 40%    | 0.800x         | 0.726x          | -9%    |
| 50%    | 0.750x         | 0.607x          | -19%   |
| 60%    | 0.700x         | 0.487x          | -30%   |
| 75%    | 0.625x         | 0.325x          | -48%   |
| 100%   | 0.500x         | 0.135x          | -73%   |

This preserves strategy discovery (no hard cap), removes the 0.3x floor that protects catastrophic strategies, and creates meaningful selection pressure against deep drawdowns. RSI Regime's fitness would drop from 2.18 to ~1.13 — still the best strategy, but now within striking distance of alternatives, giving the optimizer real incentive to explore lower-DD parameter space.

Additionally, **run the optimizer for its intended 8 hours** before making permanent changes. The 36-second run is not a reliable basis for architectural decisions about the fitness function.

### Severity

**MEDIUM-HIGH.** The current penalty function creates systematic bias toward unsurvivable strategies. This doesn't cause immediate damage (there's a human review gate), but it wastes optimizer compute on the wrong region of the search space and risks normalizing extreme drawdown as acceptable if the human reviewer becomes accustomed to seeing it in best-ever.json.

### Confidence: 0.82

High confidence that the penalty is too permissive. Moderate uncertainty about the exact right penalty curve — the exponential proposal is principled but the coefficient (2.0) should be validated empirically.

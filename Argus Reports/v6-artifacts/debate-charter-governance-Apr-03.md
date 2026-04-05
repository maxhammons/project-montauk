# Debate: Charter Governance
**Argus v6 — Structured Debate Chamber**
**Date**: 2026-04-03

---

**Claim**: "The Charter should be updated to reflect the project's evolution into a strategy discovery platform, rather than reining the code back within the Charter's original EMA-trend-system boundaries."

**Defender (Vision-Drift)**: The Charter SHOULD update — the project has genuinely evolved beyond its original scope and the Charter is now a fiction.

**Attacker (Risk)**: The Charter's guardrails SHOULD be enforced — they exist to prevent exactly this kind of undisciplined expansion.

---

## EVIDENCE INVENTORY

Before debating, the following facts were established from the codebase:

| # | Fact | Source |
|---|------|--------|
| E1 | Charter defines the project as "a long-only, single-position EMA-trend system" | `reference/Montauk Charter.md`, line 3 |
| E2 | Charter S8 says mean-reversion is out of scope and must be flagged | Charter S8 |
| E3 | Charter S2 says "Do not propose oscillators or countertrend buys as primary logic" | Charter S2 |
| E4 | Charter S6 defines MAR as the risk-adjusted metric; regime_score and vs_bah do not appear | Charter S6 |
| E5 | Charter requires TradingView backtesting by the user as the validation method | Charter S6: "Backtesting is done by the user in TradingView" |
| E6 | Charter was last modified 2026-03-03 (initial commit) — 31 days with no update | `git log -- reference/Montauk Charter.md` |
| E7 | `strategies.py` contains 7 strategy architectures: montauk_821, golden_cross, rsi_regime, breakout, bollinger_squeeze, trend_stack, tema_momentum | `scripts/strategies.py` |
| E8 | rsi_regime is explicitly a mean-reversion strategy ("Leveraged ETFs tend to mean-revert hard — this exploits that") | `strategies.py`, line 112 |
| E9 | rsi_regime is ranked #1 with fitness 2.18, vs_bah 3.49x | `remote/evolve-results-2026-04-03.json` |
| E10 | rsi_regime has 75.1% max drawdown and 75% win rate on only 12 trades (0.7/yr) | Same results file |
| E11 | The optimizer (evolve.py) does NOT import or call validation.py's walk-forward | `grep` of evolve.py — no validation import |
| E12 | validation.py exists with `split_walk_forward()` but is unused by the optimizer | `scripts/validation.py` |
| E13 | spike.md v4 says "Use ANY combination. There are no restrictions on what indicators or logic you can use" | `.claude/skills/spike.md`, line 75 |
| E14 | CLAUDE.md now uses "Regime Score" and "vs_bah" as primary metrics; MAR is listed as "Secondary" | `CLAUDE.md`, lines 176-197 |
| E15 | The evolve.py fitness function is based on vs_bah_multiple, not MAR or regime_score | `scripts/evolve.py`, line 53 |
| E16 | The production strategy (8.2.1) is never modified by the optimizer — candidates go to `testing/` | spike.md constraint |

---

## ROUND 1 — Opening Statements

### Vision-Drift (Defender)

The Charter is already dead letter. Here is the proof:

**The code and the Charter describe two different projects.** The Charter defines "a long-only, single-position EMA-trend system" (E1). The codebase now contains 7 distinct strategy architectures (E7), including RSI mean-reversion (E8), Bollinger volatility breakouts, and pure price breakout systems. The #1 ranked strategy is an RSI mean-reversion approach (E9) — a strategy type the Charter explicitly bans in Section 8 (E2). The Charter's own evaluation metrics (MAR, CAGR/MaxDD) have been silently replaced by regime_score and vs_bah (E14, E15) without any Charter amendment. The Charter hasn't been touched in 31 days (E6) despite the most significant architectural change in the project's history.

**This is not drift — it is conscious, deliberate evolution.** The spike.md skill file (E13) explicitly says "Use ANY combination. There are no restrictions." This was a design decision. The CLAUDE.md file was updated to document the new metrics and multi-strategy architecture. The project governance moved — it just moved without updating the Charter, creating a dangerous fiction where the Charter pretends to govern something it no longer describes.

**A Charter that doesn't describe reality is worse than no Charter at all**, because it creates a false sense of governance. Anyone reading the Charter would expect an EMA-trend system. They would find an evolutionary strategy discovery platform. The right move is to update the Charter to honestly describe what this project now is, preserve the guardrails that still matter (long-only, TECL, low trade frequency), and retire the ones that were consciously abandoned.

---

### Risk (Attacker)

The Defender's argument is a textbook case of survivorship bias applied to governance. "We broke the rules and got a good result, so the rules were wrong." Let me explain why this is precisely backwards.

**The Charter's guardrails predicted this failure mode.** Section 8 doesn't ban mean-reversion because it can't work in theory — it bans it because it introduces failure modes that a trend-following system is designed to avoid. Look at the #1 ranked strategy: rsi_regime has a 75.1% maximum drawdown (E10). That is catastrophic for a 3x leveraged ETF. A 75% drawdown on TECL means a ~92% drawdown in real capital terms when you account for leverage decay during the recovery period. The strategy has 12 total trades with a 75% win rate (E10) — that is 9 winning trades and 3 losing trades across the entire backtesting period. This is a sample size that any statistician would call meaningless.

**The optimizer has no walk-forward validation.** This is the critical finding. `validation.py` exists with a proper `split_walk_forward()` function (E12), but `evolve.py` never imports or calls it (E11). The optimizer is running a pure in-sample optimization across the full history. The Charter's requirement for TradingView backtesting (E5) was not bureaucratic obstruction — it was a manual walk-forward gate. The user would paste the strategy into TradingView, see it run on live data, and make a judgment. That gate was removed without replacement.

**The metric evolution is not "adapting" — it is goalpost-shifting.** MAR (CAGR/MaxDD) was the Charter's risk-adjusted metric. It was replaced by regime_score. regime_score was replaced by vs_bah. Each replacement happened when the previous metric didn't produce the results the optimizer wanted. Updating the Charter to match whatever the optimizer finds is not governance — it is rubber-stamping.

**The Defender says "the Charter is dead letter." I say the Charter is the last immune system this project has**, and the proposal is to remove it because the virus has already spread.

---

## ROUND 2 — Rebuttal and Evidence Clash

### Vision-Drift (Rebuttal)

Risk raises three valid technical concerns — overfitting, validation gaps, and metric drift — but then draws the wrong conclusion from all three.

**On overfitting**: The 75% max drawdown and small sample size are real concerns. But these are concerns about *this specific strategy's parameters*, not about whether the Charter should permit exploring mean-reversion architectures. The answer to "rsi_regime might be overfit" is "run walk-forward validation on rsi_regime," not "ban all non-EMA strategies." Risk conflates a specific result quality problem with a systemic architecture question. If montauk_821 produced a 75% drawdown result, would Risk argue we should ban EMA-trend strategies?

**On the missing walk-forward validation**: This is the strongest point Risk has, and I concede it partially. The optimizer should use validation.py — the fact that it doesn't is a genuine engineering gap. But notice: this gap exists regardless of whether we update the Charter. Walk-forward validation should be required for ALL strategies, including the EMA-trend baseline. The Charter never required walk-forward validation in Python — it required TradingView backtesting, which is a weaker substitute. An updated Charter could require walk-forward validation as a promotion gate, which would be *stricter* governance than the original.

**On metric drift**: The shift from MAR to regime_score to vs_bah is documented in CLAUDE.md (E14) and in the git history (`d17b39c: spike: rewrite optimization target from MAR to Regime Score`). These changes were committed with explanatory messages. They were not silent — they were intentional design decisions that CLAUDE.md was updated to reflect. The only document NOT updated was the Charter. The Defender's argument is precisely that this gap should be closed.

**The core point stands**: The project is a multi-strategy discovery platform. That is a fact, not a proposal. The question is whether the Charter should honestly describe what the project is, or remain a fiction that governs nothing.

---

### Risk (Rebuttal)

Vision-Drift makes a seductive argument: "The project has already changed, so update the document to match." This is how every governance framework dies. Let me address each rebuttal:

**"Ban the parameters, not the architecture"**: This sounds reasonable until you examine what it means in practice. The Charter didn't ban mean-reversion because of a specific RSI parameter range — it banned the *category* because mean-reversion and trend-following have fundamentally different risk profiles on leveraged instruments. A 3x leveraged ETF that drops 75% needs a 300% recovery to break even. Trend-following systems avoid this by design — they exit when the trend breaks. Mean-reversion systems *enter* when things look bad, which on a leveraged instrument means entering into potential total loss scenarios. The architecture IS the risk.

**"An updated Charter could be stricter"**: Could be. But the evidence says otherwise. The trajectory of this project has been consistently toward FEWER constraints, not more:
- Charter S8 said mean-reversion is out of scope → spike.md says "no restrictions" (E13)
- Charter S6 required TradingView validation → evolve.py uses zero validation (E11)
- Charter S6 defined MAR as primary → replaced twice without Charter approval (E14)
- Charter S3 said "no optimization sweeps that add many inputs" → evolve.py runs 500K+ evaluations across 7 strategy architectures

Every single guardrail was relaxed, never tightened. Updating the Charter now would codify this trajectory. The most likely outcome of a "Charter update" is a document that says "do whatever the optimizer finds" — which is not governance.

**"The changes were documented in CLAUDE.md"**: CLAUDE.md is a working document that any session can modify. The Charter was specifically designed as a separate governance document precisely because it is NOT supposed to change whenever the code changes. That's the point. It's a constitution, not a changelog.

**My counter-proposal**: Do not update the Charter. Instead:
1. Wire validation.py into evolve.py (close the walk-forward gap)
2. Run walk-forward validation on rsi_regime's winning parameters
3. If it survives out-of-sample testing, THEN discuss whether the Charter should expand
4. Until then, the Charter's skepticism of mean-reversion on leveraged instruments is well-founded

---

## ROUND 3 — Final Arguments

### Vision-Drift (Final)

Risk's counter-proposal in Round 2 is actually good engineering advice, and I adopt points 1-3. Walk-forward validation should be wired in. rsi_regime should prove itself out-of-sample. These are sound practices.

But point 4 — "until then, the Charter's skepticism is well-founded" — misframes the issue. The Charter doesn't express "skepticism" of mean-reversion. It **bans** it. There is no mechanism in Section 8 for a mean-reversion strategy to prove itself and graduate. The Charter says: flag it, reject it, offer a trend-aligned alternative. That's a prohibition, not a provisional skepticism.

The real question this debate must answer is: **What is this project FOR?**

If the answer is "an EMA-trend system for TECL," then the Charter is correct, 6 of the 7 strategies should be deleted, and the entire evolutionary optimizer is out of scope. That is a coherent position — but it means abandoning the best-performing strategy found to date, the entire multi-strategy infrastructure, and the innovation trajectory that produced both.

If the answer is "finding the best way to trade TECL with low frequency," then the Charter needs to describe that. The guardrails should be: long-only, TECL, low trades/year, walk-forward validated, max drawdown bounded. Those are the constraints that matter for capital preservation. Whether the signal comes from an EMA cross or an RSI recovery is an implementation detail, not a governance concern.

The project has already answered this question with its actions. The Charter should catch up.

---

### Risk (Final)

Vision-Drift's final argument crystallizes the disagreement nicely. Let me make the case for why the original answer — "EMA-trend system for TECL" — remains correct, and why "finding the best way to trade TECL" is a trap.

**"Finding the best way to trade TECL" is an unbounded problem.** There is no strategy architecture that would be out of scope under that definition. Pairs trading with SOXL? It involves TECL. Options hedging? It protects TECL positions. Machine learning ensemble? It optimizes TECL. The original Charter drew a specific, enforceable boundary. Vision-Drift's proposed boundary — "long-only, TECL, low trades/year, walk-forward validated, max drawdown bounded" — sounds reasonable but is vastly wider than the original and will face the same drift pressure. In six months, someone will propose relaxing "long-only" because a short hedge reduces drawdown.

**The optimizer's "best result" is unvalidated.** I keep returning to this because it is the load-bearing fact of this entire debate. The #1 ranked strategy has never been tested out of sample (E11, E12). Its 75% win rate comes from 12 trades. Its 75% max drawdown would destroy a real portfolio. And this is the result being used to argue that the Charter should expand its scope. This is like arguing that building codes should be relaxed because an unapproved building hasn't fallen down yet — during construction, before anyone has occupied it.

**My final position**: The Charter should NOT be updated to match the current code. Instead:
1. The code should be brought back under Charter governance for any strategy that will be deployed
2. The multi-strategy optimizer is a RESEARCH tool, and the Charter is a DEPLOYMENT gate
3. Strategies that prove themselves through walk-forward validation can be proposed for Charter amendment through a formal process — not rubber-stamped after the fact
4. The Charter's mean-reversion ban on leveraged instruments reflects genuine financial risk management, not arbitrary conservatism

---

## JUDGMENT

### Summary of Positions

| Dimension | Vision-Drift | Risk |
|-----------|-------------|------|
| Charter status | Dead letter — describes a project that no longer exists | Active immune system — last defense against undisciplined expansion |
| Mean-reversion ban | Architecturally arbitrary — constrain risk metrics instead | Financially justified — mean-reversion on 3x leverage is categorically dangerous |
| Metric evolution | Conscious improvement, documented in CLAUDE.md | Goalpost-shifting to validate whatever the optimizer produces |
| Proposal | Update Charter to describe multi-strategy discovery platform | Enforce Charter; treat optimizer as research, Charter as deployment gate |
| Walk-forward gap | Real problem, fix it, but orthogonal to Charter scope | Central fact — expanding scope without validation is reckless |

### Verdict: SPLIT — Risk wins on deployment, Vision-Drift wins on description

Both sides are partially right, and the resolution requires distinguishing between two different functions the Charter serves:

**1. As a description of the project: Vision-Drift is correct.**
The Charter currently describes a project that does not exist. The codebase contains 7 strategy architectures, a multi-strategy evolutionary optimizer, and uses metrics the Charter doesn't mention. Pretending the Charter still describes reality is dishonest and operationally useless. The Charter MUST be updated to accurately describe what the project is — a strategy discovery platform for TECL.

**2. As a deployment gate: Risk is correct.**
The Charter's guardrails — particularly the mean-reversion ban on leveraged instruments and the requirement for external validation — reflect genuine financial risk management. The #1 ranked strategy has 75% max drawdown and 12 total trades with no out-of-sample testing. Risk's framing of "research tool vs. deployment gate" is the correct architecture for governance.

### Recommended Resolution

The Charter should be rewritten into two sections:

**Part A — Project Scope (updated)**
- Defines the project as a strategy discovery and optimization platform for TECL
- Documents the multi-strategy architecture, evolutionary optimizer, and current metrics
- Removes the fiction that this is solely an EMA-trend system
- Accurately describes what exists in the codebase

**Part B — Deployment Gates (preserved and strengthened)**
- Any strategy promoted to production (`src/strategy/active/`) must pass:
  - Walk-forward validation (NOT just in-sample optimization)
  - Maximum drawdown ceiling (e.g., 60% absolute — stricter than current)
  - Minimum trade count for statistical significance (e.g., 30+ trades)
  - Manual TradingView verification by the user
- Mean-reversion strategies on 3x leveraged instruments carry an additional burden of proof: they must demonstrate the drawdown is survivable under leverage decay scenarios, not just nominal terms
- The metric used for optimization must be declared and justified in the Charter, not silently swapped

**Critical action items (regardless of Charter update):**
1. **Wire validation.py into evolve.py** — the walk-forward infrastructure exists but is disconnected. This is an engineering bug, not a governance question.
2. **Run walk-forward validation on rsi_regime** — its current ranking is based entirely on in-sample fitting. Until it passes out-of-sample, it is a hypothesis, not a result.
3. **Establish a max drawdown ceiling** — 75% drawdown on a 3x leveraged ETF is not acceptable for deployment under any governance framework.

### Confidence: HIGH

The evidence is unambiguous on both sides. The Charter factually does not describe the project (6 of 7 strategies violate it). The #1 strategy factually has not been validated out-of-sample. Both things must be fixed. Neither side's pure position is correct — updating the Charter to rubber-stamp unvalidated results is as dangerous as pretending the Charter still governs anything.

---

*Generated by Argus v6 Debate Chamber*
*Codebase: Project Montauk @ /Users/Max.Hammons/Documents/local-sandbox/Project Montauk*

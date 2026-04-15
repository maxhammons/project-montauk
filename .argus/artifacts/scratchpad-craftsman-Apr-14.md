# Craftsman Scratchpad: Project Montauk
Date: April 14, 2026

## Initial Impressions
The codebase has transitioned from manual Pine Script tuning to a programmatic backtesting suite. I am looking for gaps between what the code says it is and what it actually is. Are the boundaries real? Are the names honest? 

The code is communication. It makes claims about the world — this thing is an Engine, this thing is a Result, this boundary separates concerns — and those claims are either true or they're lies. If the names in the code don't match the concepts in the developers' heads, bugs are inevitable. Confused models in the code become confused models in the engineers, and confused engineers make confident mistakes.

## Finding 1: The Engine Naming Inversion
There are two files that claim to be engines: `backtest_engine.py` and `strategy_engine.py`.
If I read these cold, I would build the following model:
- `backtest_engine.py` sounds like the core backtester loop. It should be the agnostic runner.
- `strategy_engine.py` sounds like the logic that decides *when* to trade, feeding into the backtester.

The reality is exactly the opposite. 
`strategy_engine.py` contains the generic, modular backtesting loop (`def backtest(df, entries, exits, ...)`). It properly separates the "WHAT" (strategy logic) from the "HOW" (position management and PnL). It is the actual, agnostic engine.
`backtest_engine.py`, on the other hand, contains `class StrategyParams` with fields like `short_ema_len`, `med_ema_len`, `enable_trend`. It is a hardcoded, specific strategy implementation (Montauk 8.2.1) that happens to have an embedded, specialized backtesting loop to run itself. 

This is a profound conceptual integrity violation. The name `backtest_engine.py` is a lie. It is not an engine; it is a legacy script that has grown into a God object containing a specific strategy, redundant indicator logic, and regime scoring. It creates a confused mental model for any new engineer coming into the codebase. The name creates an expectation, and when behavior violates that expectation, every caller is working from bad information.

## Finding 2: The Redundant and Conflicting Domain Models
Because there are two "engines", there are two parallel domain models fighting for dominance.
`strategy_engine.py` defines its own reality:
- `class Trade`
- `class BacktestResult`
- `def _ema()`, `def _sma()`, `def _rma()`

`backtest_engine.py` also defines its own reality:
- `class Trade`
- `class BacktestResult`
- Its own inline math functions that do the exact same things.

This is not just code duplication; it's a fractured domain model. When an engineer says "pass me the BacktestResult", they now have to clarify *which* BacktestResult. The types are not interchangeable, even though they share the exact same name and represent the exact same concept. This is an abstraction that doesn't just leak; it actively misleads. This is how tribal knowledge becomes load-bearing infrastructure.

## Finding 3: `vs_bah_multiple` and the Gap in the Mental Model
The North Star document notes that the charter's primary metric is the "share-count multiplier vs B&H".
The code implements this mathematically, but the vocabulary is entirely wrong. Throughout the codebase, this critical value is stored, passed, and serialized as `vs_bah` or `vs_bah_multiple`.
There are comments explicitly explaining this discrepancy:
`# vs_bah_multiple in BacktestResult is mathematically identical to the share-count multiplier... So this fitness function reads vs_bah_multiple but is actually rewarding share accumulation.`
In `strategy_engine.py`, they even added a property:
`# share_multiple = terminal strategy equity / terminal B&H equity. Math identity: this equals (strategy_shares_equiv / bah_shares) ... vs_bah_multiple is kept as a legacy alias.`

This is the precise definition of an implicit second model growing up alongside the official one. The official vocabulary (`vs_bah`) describes dollar returns, but the team's actual mental model is share count accumulation. They've glued the new concept onto the old vocabulary. It works mathematically, but it's a confused model. The code is not honest about what it's actually measuring.

## Finding 4: The Phantom `trade_scale`
The North Star document mentions a tension where the Python scripts still use a `trade_scale` factor to punish low trade frequency.
My investigation revealed this is a ghost. The `trade_scale` factor was explicitly removed in `evolve.py` on 2026-04-13. The codebase actually *is* aligned with the charter on this specific point, but the documentation/North Star is lagging behind. This is a positive finding for the code, but indicates a drift in the team's shared understanding of the system's current state. The code has moved on.

## Conclusion for Roundtable
The most pressing issue for the team's velocity is not the complex optimization loops or missing test coverage. It's the fact that the foundational vocabulary of the system — "What is the engine?" and "What is our primary metric?" — is fundamentally dishonest. The system cannot be safely expanded until these concepts are unified and accurately named.
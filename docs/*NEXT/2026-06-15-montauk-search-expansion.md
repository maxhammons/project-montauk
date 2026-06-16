# MONTAUK SEARCH EXPANSION — break the monoculture without touching the gate

**Status: DESIGN / DISCUSSION — needs a charter decision before any build.**
This is a direction-setting analysis, not a build plan (2026-06-15). It came out
of the question *"what is preventing Montauk from finding better strategies, and
how is it actually better than a plain EMA crossover?"* The answer turned out to
be structural, not a tuning problem — so this doc lays out the structure and the
decision it forces. Treat every section as a prompt for discussion.

---

## The hard constraint (read first)

**The validation / overfitting-detection pipeline does not change. What it takes
to be Gold is non-negotiable and stays fixed.** Specifically untouchable:

- the Layer-1 correctness checks (integrity, golden regression, shadow
  comparator, data quality, artifact completeness)
- the Layer-2 confidence composite, its sub-scores, weights, and anchors
  (`docs/validation-thresholds.md`)
- the Gold contract: `certified_not_overfit` + `backtest_certified` + **beats
  B&H in the full, real, and modern eras**
- the deflation / N_eff / PBO multiple-testing machinery

Every idea in this doc is constrained to **feed the unchanged gate better
candidates** — never to lower the bar or weaken the proof. This is not a
limitation on the solution; it is the thing that makes the solution honest. See
"Why the fixed gate forces the answer" below.

---

## The idea in one paragraph

Today's leaderboard is a monoculture: 12 Gold rows that are really 4 strategies
that are really **one golden-cross family** (`gc_vjatr` + two re-entry overlays +
an ensemble of the three). This is not because the search is biased toward
golden-cross — it is because the *only thing a strategy is allowed to do* is be
100% long TECL or 100% flat. Against a 3× leveraged ETF in a 15-year tech bull,
the only economic shape that can beat buy-and-hold is "ride the uptrends,
sidestep the crashes" — i.e. trend-following. Mean-reversion, defensive, and
contrarian strategies don't lose because they're bad; they lose because **going
flat is the only defensive move they're allowed, and flat earns nothing.** The
fix is therefore *not* to force the search to try more variety (those candidates
just die at the gate). The fix is to **widen what a strategy can express and
trade**, so other archetypes gain the tools to clear the *same* fixed Gold bar on
their own merits. In short: don't move the finish line — give the other runners
real equipment.

---

## Why the fixed gate forces the answer (not limits it)

There are two ways to get a more diverse board:

1. **Lower / reshape the bar** so non-trend strategies pass more easily. ❌
   Off the table by charter, and dishonest — it manufactures false Gold.
2. **Expand the toolset** so a defensive or mean-reverting strategy can actually
   *out-accumulate B&H* in down regimes and clear the unchanged bar. ✅

With option 1 banned, option 2 is the *only* path — and it happens to be the
correct one. A genuinely uncorrelated strategy that clears the real B&H-beating
bar with a richer toolset is a real diversifier. A strategy that only passes
because we softened the gate is just overfitting with better PR. **The constraint
is doing exactly what it should: routing all the design pressure onto the search
and action space instead of onto the proof.**

Key distinction that runs through everything below:

> **Charter (what a strategy may trade / do / how often) ≠ Validation+Gold (the
> proof that an edge is real).** The owner has frozen the second. The first is
> where the unlock lives — and most of it is a charter amendment, not a code
> change to the pipeline.

---

## The four ceilings and how to lift each — gate untouched

Recap of the four structural ceilings, and the specific change that lifts each
one *without* touching validation or Gold.

### Ceiling 1 — Representation (the big lever)

**Problem.** Every strategy collapses to binary long/flat on a single asset
(`strategy_engine.py` `backtest()` / `run_montauk_821()`, `position ∈ {0,1}`).
The richest constructs in the library — 5-state regime machines, weighted
committees, vote scores — throw away all their gradation at the
`state >= threshold` step. "Rotate to T-bills in a bear" is structurally
impossible: SGOV / VIX / treasuries exist only as *signals*, never as holdable
positions.

**Lift it by widening the action space:**

- **A real defensive leg.** Let "flat" optionally become "hold SGOV" (earns
  ~T-bill yield) instead of dead cash. *This is the single highest-leverage
  change.* A defensive or mean-reverting strategy now has a **return source** in
  down regimes, so it can beat B&H TECL across the real/modern eras and clear the
  unchanged gate. The data (`SGOV.csv`) is already loaded as a signal input — this
  promotes it to a position.
- **Inverse / short leg** for bear regimes. The VIX/airbag detectors already
  *find* the crashes; today they can only step aside, never profit.
- **0–100% position sizing.** Let conviction-weighted and regime strategies
  express partial exposure instead of discarding their gradation at the long/flat
  boundary.

**Gate impact: none.** The Gold contract still reads "beat B&H TECL in all three
eras, certified not overfit." We've handed contestants better equipment, not moved
the line. (Benchmark caveat → Open Question Q3.)

### Ceiling 2 — Search

**Problem.** Parameters snap to a discrete lattice (an EMA of 37 or an ATR
multiple of 2.7 is unreachable). The GA is elitist, seeds ~20% of its population
from past winners, and injects only ~5% randomness — so it re-converges into the
golden-cross basin every run. There is no cross-concept recombination.

**Lift it with search hygiene (all gate-untouched):**

- **Continuous params** via the half-wired Optuna/Bayesian path in `evolve.py`,
  to escape the lattice.
- **Reward orthogonality in the optimizer fitness** (`scripts/search/fitness.py`),
  *not* in the gate: bonus for candidates whose return stream is uncorrelated to
  the current board. This changes *what the GA hunts for*; the Gold gate still
  certifies the winners. The diversity reward lives in the search, the proof lives
  in the (unchanged) pipeline.
- **Cut winner-seeding, raise random injection** so the search stops collapsing
  back into the known basin.
- **Target idea-generation at the board's missing styles**, not by volume (the
  `2026-06-09-idea-to-gold-pipeline.md` roadmap item #3) — author hypotheses for
  the regimes/economics the board lacks.

### Ceiling 3 — Data / regimes

**Problem.** One asset, ~17 years of *real* data, maybe 3–4 independent macro
regimes (2008, 2020, 2022). The current champion carries ~53 params and trades 19
times in 33 years — far more knobs than independent events. The headline "35×" is
dominated by *synthetic* pre-2008 compounding; the real-era multiple is ~1.0–1.3×.

**Lift it by adding independent regimes, not by lowering the bar:**

- **Run the machine per-sector** (the `2026-06-14-multi-sector-autonomous-machine`
  vision). Each sector instance keeps the *same* per-asset Gold contract ("beat
  B&H of the thing you trade in all three eras"); the gate logic is unchanged, it
  is simply *instantiated per asset*. You gain many more independent macro regimes
  across assets, and cross-asset robustness becomes real signal rather than a
  noisy diagnostic.
- **Keep validation fixed — it is doing its job here.** The "53 params vs 3–4
  regimes" over-parameterization is exactly what the (unchanged) pipeline exists to
  reject. The way to make headroom is to add regimes for it to certify against, not
  to relax it.

### Ceiling 4 — Diversity wall

**Problem.** The Gold contract ("beat B&H in real AND modern eras") is currently
only clearable by golden-cross trend-followers tuned to the 2020/2023 rebounds.
Strict scans of 679 then 2,407 non-Bonobo configs found **zero** survivors
(`docs/project-status.md`; `runs/near_miss_autopsy.json`). The diverse near-misses
(e.g. `rsi_regime_canonical`, correlation −0.02 to the champion) are "too
defensive in rebound years" and die below B&H.

**This ceiling is downstream of #1 and #3 — it is not a separate fix.** With a
defensive/short/sizing action space (#1) and more independent regimes (#3), the
diverse archetypes finally have the *means* to beat B&H and clear the fixed bar.
Add the orthogonality reward from #2 and you actively hunt the missing styles. The
bar never moves; the contestants get real tools. **That is the only diversity that
isn't gate-softening in disguise.**

---

## What NOT to do

- ❌ **Don't force variety in the search alone.** Diversity quotas, "explore more
  families," round-robin authoring — without a wider action space these just
  generate more candidates that die at the (correct) gate. Wasted compute, same
  board.
- ❌ **Don't touch the gate, the composite, the weights, or the Gold contract.**
  Frozen by owner decision. Any "diversity" bought by softening the proof is false
  Gold.
- ❌ **Don't re-weight eras or down-weight synthetic data to flatter the headline.**
  That is a scoring change = a gate change. Out of scope.
- ❌ **Don't add an action-space feature without re-confirming Layer-1 integrity.**
  Shorts/sizing/defensive-leg all touch `backtest()` — the golden-regression net
  and shadow comparator must still pass, and the no-lookahead / single-decision
  invariants must hold for the new position states.

---

## The decision this forces (the crux)

Two charter rules sit *physically inside* Gate 1 of the validation pipeline, but
they are **style preferences, not overfitting checks**:

- **`trades_per_year ≤ 5`** — mean-reversion and rotation strategies *inherently*
  trade more than this. If this stays locked, the entire family of higher-frequency
  diversifiers is banned no matter what tools we add. This is arguably the
  **second-biggest cause of the monoculture after long/flat.**
- **long/flat single-position + TECL-only** — the literal action-space and
  asset-universe constraints.

Whether these count as "the fixed Gold gate" (untouchable) or "charter style"
(amendable) is the fork that determines how far this work can go. The owner froze
*validation and overfitting detection*; these three rules are neither. But they
live in the same file (`scripts/validation/candidate.py`, Gate 1), so the call
must be explicit. → Open Question Q1.

---

## Open questions

**Q1 — Charter scope: which Gate-1 rules are frozen?** Pick the boundary:
- (a) **Only the economic + overfit contract is fixed** ("beat B&H all eras +
  certified not overfit"). Trades/year, long/flat, and TECL-only are charter —
  amendable. *Maximum room to break the monoculture.*
- (b) **Keep the ≤5 trades/year cap too** (regime-trader identity is sacred), but
  allow a defensive/SGOV leg, shorts, and sizing.
- (c) **Everything in Gate 1 is frozen.** Only the search engine and
  idea-generation may change — not what a strategy can trade or do. *Most
  constrained; likely keeps the board a golden-cross monoculture.*

**Q2 — Action-space priority.** If we widen the action space, in what order?
Recommended: (1) SGOV defensive leg → (2) position sizing → (3) inverse/short.
The SGOV leg is the cheapest, safest, highest-leverage first move and directly
attacks the diversity wall. Shorts add the most modeling/borrow-cost realism risk.

**Q3 — Benchmark definition under a richer action space.** The Gold contract is
"beat B&H." Beat B&H of *what*?
- For a **defensive-leg / sizing** strategy that still ultimately trades TECL: the
  benchmark stays **B&H TECL** — the strategy just has better tools to beat it. No
  gate change. ✅ Cleanest.
- For a **multi-asset / multi-sector** strategy: each instance is benchmarked
  against B&H of *its own* asset. Same contract logic, instantiated per asset. ✅
- A blended/portfolio benchmark would be a *new* contract definition → that *is* a
  gate change → **out of scope.** ❌

**Q4 — Does an SGOV defensive leg break the "share accumulation vs TECL B&H"
metric?** The primary GA target is *terminal TECL-share count vs B&H*. If a
strategy parks in SGOV, we need a defined rule for converting the SGOV leg back to
TECL-share-equivalent at the benchmark price so the share metric stays coherent.
Needs a small spec. (Does not change the gate — it defines how the existing metric
reads a new position state.)

**Q5 — Generative logic synthesis (longer horizon).** Even with a wider action
space, the search can still only *re-tune* ~150 hand-written functions; it cannot
invent new signal structure. A small typed DSL / grammar over the existing
`Indicators` menu would let search discover new logic — but it multiplies
overfitting risk, which the `idea-to-gold-pipeline` doc flags as the project's #1
danger. Worth it only *after* #1–#4 land and *only* because the fixed gate is
strong enough to catch the extra false positives. Park for now.

**Q6 — Realism for shorts/leverage.** Shorts need borrow cost, hard-to-borrow
handling, and an inverse-instrument decision (short TECL vs hold SOXS-style
inverse). Sizing needs a financing-drag model. Scope before building, not during.

---

## Next steps

1. **Owner answers Q1** (charter scope). Nothing downstream is buildable until the
   frozen boundary is explicit. Everything else branches on this.
2. **If Q1 = (a) or (b): prototype the SGOV defensive leg** as the first action-space
   change. Smallest, safest, highest-leverage. Spec the share-metric conversion
   (Q4) first, then implement behind a flag in `backtest()`, then re-confirm
   Layer-1 integrity (golden regression + shadow comparator still pass).
3. **Re-run a focused search with the defensive leg enabled** and ask the empirical
   question: *do any genuinely uncorrelated archetypes now clear the unchanged Gold
   gate?* This is the single cleanest test of the whole thesis — if a defensive
   strategy reaches Gold without touching the bar, the diagnosis is confirmed.
4. **Add the orthogonality reward to the optimizer fitness** (`fitness.py`) so the
   search starts hunting board gaps. Verify it changes *only* the GA target, not
   any validation sub-score.
5. **Only then** consider sizing → shorts → multi-sector → generative DSL, each
   gated behind its own realism scoping (Q6) and a fresh Layer-1 integrity pass.
6. **Update `docs/pipeline.md`** whenever the fitness function or the engine's
   position model changes (doc-sync protocol).

---

## One-line summary

The board is a monoculture because the *action space* — not the search, not the
gate — is too narrow for anything but trend-following to beat a leveraged-ETF
benchmark. Keep the proof fixed, widen what a strategy can *do*, and let real
diversifiers clear the same bar on their own merits.

---

## Provenance

Derived from a four-angle codebase audit on 2026-06-15: search mechanics
(`scripts/search/`), strategy representation/expressivity (`scripts/strategies/
library.py`, `scripts/engine/strategy_engine.py`), validation & overfitting
controls (`scripts/validation/`, `spike/`), and the live leaderboard / roadmap
(`spike/leaderboard.json`, `runs/operations/`, this `*NEXT/` folder). Companion
to `2026-06-09-idea-to-gold-pipeline.md` (the generation engine) and
`2026-06-14-multi-sector-autonomous-machine.md` (the multi-asset vision) — this
doc is the *action-space* leg those two assume but don't specify.

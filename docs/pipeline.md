# Project Montauk — Pipeline

**Canonical flow**: discover or hypothesize long-only TECL strategies, route them to the validation tier appropriate to how they were selected, promote only PASS winners, and generate Pine for the best validated winner.

This document defines the intended operating model of the project under the charter. If this document ever conflicts with `Montauk Charter.md`, the charter wins.

---

## 1. Naming

The skill is **Spike**. Spike launches and runs the **Montauk Engine** — the optimizer + validator + Pine generator pipeline.

- "Spike" = the entrypoint / command surface (`/spike`, `/spike-focus`, `/spike-results`)
- "Montauk Engine" = the underlying machinery (search + tier-routed validation + Pine emission)

This is a semantic split, not a code rename.

---

## 2. Canonical Full-Run Flow

The authoritative full-run path is:

1. **Refresh data**
   Update TECL and validation datasets.

2. **Hypothesize and / or Discover**
   - Hand-author T0 hypothesis strategies (registered with committed params before any backtest)
   - Or: run the optimizer for T1 / T2 candidates across registered strategy families
   - Marker shape alignment is recorded for every candidate

3. **Save raw results**
   Preserve raw output for research and audit. Each candidate carries its tier tag.

4. **Validate at the candidate's tier**
   - T0 candidates clear the light pipeline
   - T1 candidates clear the medium pipeline
   - T2 candidates clear the full statistical stack
   See `VALIDATION-PHILOSOPHY.md` for what each tier tests.

5. **Promote**
   Only final **PASS** entries make the validated leaderboard. Each entry is tagged `T0-PASS`, `T1-PASS`, or `T2-PASS`.

6. **Simulate deployment overlay**
   Run the approved Roth account overlay for the validated champion.

7. **Generate Pine**
   Emit a Pine candidate for the best PASS winner regardless of tier.

8. **Manually review in TradingView**
   Compile, inspect, and decide whether to promote the candidate.

That is the Montauk Engine. Everything else is support work.

---

## 3. Canonical Entrypoints

### Full runs

`scripts/spike_runner.py --hours ...` is the canonical promotion path.

It is responsible for:

- running discovery (T1 / T2 search) and accepting registered T0 candidates
- recording marker shape alignment for every candidate
- preserving raw results with tier tags
- running tier-routed validation
- updating the validated leaderboard
- simulating the approved Roth overlay for the validated champion
- generating human-readable reporting
- emitting Pine artifacts for the validated champion

### Raw optimization

`scripts/evolve.py` is the search engine, not the promotion authority.

Its outputs default to T2. They may discover good ideas, but by themselves they do not define what becomes real project memory.

### Hypothesis registration

T0 candidates are registered through the strategy registry with:

- name
- one-line hypothesis description
- committed parameter values (from the strict canonical set)
- registration timestamp

A T0 strategy that fails registration discipline (missing timestamp, non-canonical params, post-hoc registration) is rerouted to T1 or T2.

### Research chunk mode

`spike_runner.py --chunk` is a research loop for iterative local work. It is useful for exploration. It is not the canonical leaderboard promotion path unless explicitly brought under the same tier-routed validation rules.

---

## 4. Required Artifacts Per Full Run

Each full run leaves behind a complete audit trail under `spike/runs/NNN/`:

| Artifact | Purpose |
|----------|---------|
| `raw_results.json` | Raw output before validation, with tier tags and marker shape metrics |
| `results.json` | Validated run output with verdicts, tier tags, and champion state |
| `report.md` | Human-readable summary of raw vs validated outcomes, tier-by-tier |
| `log.txt` | Full execution log |
| `candidate_strategy.txt` | Pine candidate for the best PASS winner |
| `patched_strategy.txt` | Convenience Montauk patch output when the winner is `montauk_821` |
| `overlay_report.json` | Roth overlay simulation for the validated champion |

Raw output is for research. Validated output is for memory and promotion.

---

## 5. Promotion Rules

The pipeline has a simple rule:

- raw winner -> **not promotable**
- validated **PASS** winner at its tier -> promotable

Operationally:

- only PASS entries belong on `leaderboard.json`, each carrying its tier tag
- WARN and FAIL entries remain in run artifacts only
- if no strategy passes, the run still matters, but the leaderboard does not change
- if a strategy cannot be expressed as a valid Pine candidate, it is not deployment-ready
- the champion is the highest-share-count PASS entry across all tiers

A T0-PASS strategy and a T2-PASS strategy are both promotable. The tier tag tells the user what level of statistical scrutiny backs the result. Both are real winners.

---

## 6. Validation In The Pipeline

Validation is not an optional post-processing step. It is the center of the pipeline.

The validation stack is **tier-routed**:

- Tier 0 (Hypothesis): code integrity → cross-asset → walk-forward → marker shape
- Tier 1 (Tuned): T0 stack + parameter plateau + concentric shell on tuned region
- Tier 2 (Discovered): T1 stack + deflation + boundary perturbation + jackknife + HHI + fragility + bootstrap + cross-asset re-optimization

The best raw strategy can still be rejected. That is a healthy run, not a broken one.

This document defines the sequence and promotion logic. Exact thresholds, formulas, and heuristic settings belong in the scripts.

---

## 7. Pine Generation In The Pipeline

The end product of the factory is not just a params dict. It is a Pine artifact.

Rules:

- the best validated PASS winner gets a Pine candidate, regardless of tier
- `montauk_821` may also get a parameter-patched Montauk file for convenience
- the active TradingView script is not overwritten automatically
- final promotion to live use remains manual

Python is the research and validation layer. Pine is the execution layer.

The Roth overlay sits after validation and before manual deployment review. It is an account-analysis layer, not a change to the signal definition.

### Python-vs-Pine Parity

Gate 7 runs automated **structural parity checks** (`scripts/parity.py`) before setting `pine_eligible`. These verify that the generated Pine Script matches the Python source on:

- **Param defaults** — every Python param appears as a Pine `input.*()` with the correct default value
- **Strategy settings** — `process_orders_on_close=true`, `commission_value=0.05`, `pyramiding=0`, etc.
- **Indicator coverage** — every Python indicator has a corresponding `ta.*()` call
- **Condition structure** — entry/exit counts, cooldown logic, exit-priority order

If structural parity fails, the strategy is not Pine-eligible and cannot be promoted.

For deeper trust, two additional tiers are available via CLI:

- **Signal replay** (`parity.py replay`): generates a diagnostic Pine with extra plots + a reference CSV for visual comparison in TradingView
- **Trade-list comparison** (`parity.py trade-compare`): parses a TradingView export and compares trade-by-trade against the Python backtest

---

## 8. CI And Local Should Match

GitHub Actions should run the same promotion logic as local full runs:

- discover and / or accept registered hypotheses
- validate at each candidate's tier
- promote PASS only
- generate artifacts
- commit `spike/` outputs

There should never be a special CI-only path that bypasses tier routing or validation rules.

---

## 9. Strategy Scope

Project Montauk is allowed to search across many TECL strategy families.

What it is **not** allowed to do is drift outside the charter:

- no non-TECL production strategy
- no shorting
- no intraday logic
- no multi-position system
- no "research winner" that skips Pine generation and still counts as complete
- no strategy that punishes low trade frequency

The project is a TECL share-accumulation factory, not a generic quant sandbox.

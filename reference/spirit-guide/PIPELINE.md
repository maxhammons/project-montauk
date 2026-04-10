# Project Montauk — Pipeline

**Canonical flow**: discover many long-only TECL strategies, validate them hard, promote only PASS winners, and generate Pine for the best validated winner.

This document defines the intended operating model of the project under the charter. If this document ever conflicts with `Montauk Charter.md`, the charter wins.

---

## 1. Canonical Full-Run Flow

The authoritative full-run path is:

1. **Refresh data**
   Update TECL and validation datasets.

2. **Discover**
   Run the optimizer across the registered TECL strategy families, with approved soft discovery priors allowed to shape raw search preference.

3. **Save raw results**
   Preserve raw optimizer output for research and audit.

4. **Validate**
   Run the validation pipeline on the strongest raw candidates.

5. **Promote**
   Allow only final **PASS** entries onto the validated leaderboard.

6. **Simulate deployment overlay**
   Run the approved Roth account overlay for the validated champion.

7. **Generate Pine**
   Emit a Pine candidate for the best PASS winner.

8. **Manually review in TradingView**
   Compile, inspect, and decide whether to promote the candidate.

That is the factory. Everything else is support work.

---

## 2. Canonical Entrypoints

### Full runs

`scripts/spike_runner.py --hours ...` is the canonical promotion path.

It is responsible for:

- running optimization
- applying approved discovery priors during raw search
- preserving raw results
- running validation
- updating the validated leaderboard
- simulating the approved Roth overlay for the validated champion
- generating human-readable reporting
- emitting Pine artifacts for the validated champion

### Raw optimization

`scripts/evolve.py` is the search engine, not the promotion authority.

It may discover good ideas, but by itself it does not define what becomes real project memory.

### Research chunk mode

`spike_runner.py --chunk` is a research loop for iterative local work. It is useful for exploration, but it is not the canonical leaderboard promotion path unless it is explicitly brought under the same validation and promotion rules.

---

## 3. Required Artifacts Per Full Run

Each full run should leave behind a complete audit trail under `spike/runs/NNN/`:

| Artifact | Purpose |
|----------|---------|
| `raw_results.json` | Raw optimizer output before validation |
| `results.json` | Validated run output with verdicts and champion state |
| `report.md` | Human-readable summary of raw vs validated outcomes |
| `log.txt` | Full execution log |
| `candidate_strategy.txt` | Pine candidate for the best PASS winner |
| `patched_strategy.txt` | Convenience Montauk patch output when the winner is `montauk_821` |
| `overlay_report.json` | Roth overlay simulation for the validated champion |

Raw output is for research. Validated output is for memory and promotion.

---

## 4. Promotion Rules

The pipeline has a simple rule:

- raw winner -> **not promotable**
- validated **PASS** winner -> promotable

Operationally:

- only PASS entries belong on `leaderboard.json`
- WARN and FAIL entries remain in run artifacts only
- if no strategy passes, the run still matters, but the leaderboard must not change
- if a strategy cannot be expressed as a valid Pine candidate, it is not deployment-ready

---

## 5. Validation In The Pipeline

Validation is not an optional post-processing step. It is the center of the pipeline.

The intended validation stack is:

1. run and search integrity
2. candidate eligibility
3. statistical overfit checks
4. parameter and time robustness
5. uncertainty and cross-asset concept validation
6. final PASS / WARN / FAIL decision

The best raw strategy can still be rejected. That is a healthy run, not a broken one.

This document defines the sequence and promotion logic. Exact thresholds, formulas, and heuristic settings belong in the scripts.

Discovery priors may influence who gets validated first. They do not change PASS / WARN / FAIL logic.

---

## 6. Pine Generation In The Pipeline

The end product of the factory is not just a params dict. It is a Pine artifact.

Rules:

- the best validated PASS winner gets a Pine candidate
- `montauk_821` may also get a parameter-patched Montauk file for convenience
- the active TradingView script is not overwritten automatically
- final promotion to live use remains manual

Python is the research and validation layer. Pine is the execution layer.

The Roth overlay sits after validation and before manual deployment review. It is an account-analysis layer, not a change to the signal definition.

---

## 7. CI And Local Should Match

GitHub Actions should run the same promotion logic as local full runs:

- optimize
- validate
- promote PASS only
- generate artifacts
- commit `spike/` outputs

There should never be a special CI-only path that bypasses the validation rules.

---

## 8. Strategy Scope

Project Montauk is allowed to search across many TECL strategy families.

What it is **not** allowed to do is drift outside the charter:

- no non-TECL production strategy
- no shorting
- no intraday logic
- no multi-position system
- no "research winner" that skips Pine generation and still counts as complete

The project is a TECL strategy factory, not a generic quant sandbox.

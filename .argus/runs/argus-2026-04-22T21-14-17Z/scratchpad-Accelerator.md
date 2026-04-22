# Accelerator Scratchpad

## Pass 1 Reading List

### Hypothesis 1
- Claim: The repo's main onboarding and pipeline docs no longer agree on what qualifies for leaderboard admission, so a new engineer can follow the "source of truth" and still ship the wrong operational behavior.
- Expected signal: `docs/pipeline.md`, `scripts/README.md`, and `scripts/validation/pipeline.py` use materially different admission thresholds or different definitions of `promotion_ready` / `backtest_certified`.
- Why it matters: semantic drift is operational drift; once labels stop matching enforcement, reviews get slower and fixes become negotiation instead of execution.

### Hypothesis 2
- Claim: The codebase now has better engine-level tests than the prior run recognized, but those tests protect engine math more than they protect the higher-risk run-state and promotion semantics.
- Expected signal: `tests/test_regression.py` and related tests are strong on backtest determinism, while `spike/leaderboard.json` and promotion logic remain lightly defended by convention rather than test coverage.
- Why it matters: a new engineer can change promotion behavior or state schema safely in syntax terms while silently changing what "trusted strategy" means.

### Hypothesis 3
- Claim: The long-running paths are operationally recoverable but still not newcomer-safe because failure handling is split across multiple scripts and manual follow-ups.
- Expected signal: `scripts/search/safe_runner.py`, `scripts/certify/full_sweep.py`, and `scripts/certify/recertify_leaderboard.py` expose manual recovery instructions, nontrivial sequencing, or partial-success states that require project lore.
- Why it matters: if a long run fails halfway through, the team needs a crisp, bounded recovery path; otherwise expensive runs produce fear debt.

### Hypothesis 4
- Claim: The leaderboard is acting as both memory and trust boundary, but its schema and admission semantics are changing faster than the docs and operator surfaces can keep up.
- Expected signal: `spike/leaderboard.json` contains manual-admission flags, legacy compatibility fields, or confidence-tier fields that do not map cleanly onto the prose contract.
- Why it matters: once the leaderboard becomes a soft stateful artifact instead of a hard contract, engineers stop trusting what "eligible" and "certified" mean.

## Files To Read
- `CLAUDE.md`
  Hypothesis: top-level onboarding is helpful for navigation but contains stale implementation pointers or overstates the simplicity of routine workflows.
  Expected signal: command examples or file names drift from current package paths, especially around data-quality flows and promotion semantics.
- `docs/README.md`
  Hypothesis: doc read order is sensible, but it advertises a tighter certification contract than the running pipeline currently enforces.
  Expected signal: "best PASS winner" language persists even where watchlist semantics were introduced elsewhere.
- `docs/pipeline.md`
  Hypothesis: this is the highest-signal doc for operational drift.
  Expected signal: it mixes old PASS-only promotion language with new 0.60 watchlist language in the same document.
- `scripts/README.md`
  Hypothesis: engineer-facing Python docs still frame the leaderboard as a hard "not overfit" list, which is stronger than current code semantics justify.
  Expected signal: categorical language like "if and only if" that ignores WARN/watchlist paths or advisory-heavy gates.
- `scripts/validation/pipeline.py`
  Hypothesis: actual synthesis logic still anchors promotion on `PASS >= 0.70`, even though docs now describe a 0.60 watchlist admission path.
  Expected signal: `promotion_ready = verdict == "PASS"` and `backtest_certified` chained to that.
- `scripts/search/evolve.py`
  Hypothesis: the live leaderboard updater may be looser than gate 7 and admit entries based on confidence plus certification checks even when they are not `promotion_ready`.
  Expected signal: `_is_leaderboard_eligible` keys off `composite_confidence` thresholds and required cert checks instead of gate-7 PASS only.
- `scripts/certify/recertify_leaderboard.py`
  Hypothesis: recertification likely codifies whichever admission rule actually matters in practice.
  Expected signal: it rebuilds the leaderboard from confidence/cert checks and may bypass stricter prose expectations.
- `tests/test_regression.py`
  Hypothesis: the engine has a real fast safety net now.
  Expected signal: low-latency regression assertions around trade ledger, summary metrics, and compatibility shims.
- `spike/leaderboard.json`
  Hypothesis: live state will reveal whether the system behaves like a PASS-only hall of fame or a mixed-confidence watchlist.
  Expected signal: entries with advisory baggage, manual flags, or fields implying admission despite imperfect validation posture.
- `scripts/search/safe_runner.py`
  Hypothesis: the codebase knows long runs are fragile and has added a harness, but the recovery story is still manual enough to scare a new engineer.
  Expected signal: explicit "rerun manually" branches, partial artifact survival, and nontrivial resumability language.

## Justified Expansion Budget
- Expansion 1: `docs/validation-thresholds.md`
  Reason: needed if code/doc drift on 0.40 / 0.60 / 0.70 thresholds is real.
- Expansion 2: `scripts/certify/full_sweep.py`
  Reason: likely the canonical one-command operational gate for exhaustive verification.
- Expansion 3: `scripts/search/spike_runner.py`
  Reason: needed only if the actual promotion authority differs from what docs claim.
- Expansion 4: `scripts/validation/integrity.py`
  Reason: needed only if certification checks appear stronger or weaker than advertised.
- Expansion 5: one representative `spike/runs/NNN/dashboard_data.json`
  Reason: needed only if I must prove live PASS/WARN labeling mismatch on a concrete strategy.

## Pass 0 Quick Scan Notes
- Tests are present now; prior Accelerator concern about "no pytest safety net" is outdated.
- The test surface is still concentrated in engine correctness and compatibility, not repo-state governance.
- `docs/pipeline.md` already shows contradiction on first read: 0.60 watchlist admission in the intro, but later sections still say PASS-only promotion.
- `scripts/validation/pipeline.py` header still claims only PASS candidates are leaderboard-eligible.
- `CLAUDE.md` and `scripts/README.md` present the leaderboard as a trusted memory surface, which raises the cost of semantic drift.
- `spike/leaderboard.json` already exposes manual-admission related fields in adjacent tooling and historical backups, which is a trust-boundary smell.
- `scripts/certify/full_sweep.py` and `scripts/search/safe_runner.py` appear to be the operational chokepoints for long or fragile runs.
- Ownership signals are effectively absent; the repo assumes the owner can context-switch directly into the tree.
- Manual execution at the brokerage edge is accepted, but internal certification semantics still need to be machine-clear or humans will compensate with folklore.
- The likely Accelerator question is no longer "can they run tests?" but "can they know which result is actually safe to treat as real?"

## Working Judgement
- Directionally, I expect the main blocker to be trust-boundary ambiguity rather than missing commands.
- If the code is stricter than the docs, onboarding is confusing but safer than it looks.
- If the docs are stricter than the live leaderboard updater, velocity may feel high while trust quietly degrades.
- I need to determine which side is authoritative in practice.

## Pass 2 Evidence Notes
- `CLAUDE.md:155` still tells engineers to run `scripts/data.py`, `scripts/data_manifest.py`, and `scripts/data_quality.py`.
- Those files do not exist in the current tree.
- `docs/pipeline.md:68` still says the canonical promotion path is `scripts/spike_runner.py --hours ...`.
- The actual runner lives at `scripts/search/spike_runner.py`; that file itself still advertises `python3 scripts/spike_runner.py` in its usage block.
- `docs/pipeline.md:168` still points `StrategyParams` at `scripts/backtest_engine.py`, which also does not exist.
- `docs/pipeline.md:183` still names `scripts/data_quality.py` instead of `scripts/data/quality.py`.
- Result: first-contact operational docs are stale in exactly the commands a new engineer would use first.

## Promotion Contract Map
- `scripts/validation/pipeline.py:837-975` defines gate-7 verdicts as FAIL `<0.40`, WARN `0.40-0.69`, PASS `>=0.70`.
- Same block sets `promotion_ready = verdict == "PASS"`.
- Same block sets `backtest_certified = promotion_ready and all(certification_checks)`.
- Because `artifact_completeness` is seeded as pending there, gate 7 initially leaves `backtest_certified=False` for everyone.
- `scripts/search/evolve.py:210-235` defines leaderboard eligibility differently: any entry with `composite_confidence >= 0.60` plus four required certification checks is eligible.
- `scripts/search/evolve.py:250-255` comment claims leaderboard admission requires `promotion_ready`, but implementation does not check it.
- `scripts/certify/recertify_leaderboard.py:95-105` doubles down on the 0.60 watchlist rule during recertification.
- `docs/pipeline.md` mixes both stories in one file: line 10 says 0.60 watchlist entries are admitted, while lines 135-139 and 186 say only PASS / `promotion_ready` entries reach the leaderboard.
- `scripts/README.md:24-37` presents the strictest version: "if and only if" `promotion_ready=True` plus required certification checks.

## Live State Notes
- Current leaderboard top 20 are all `gc_vjatr` variants with `validation.verdict="PASS"` and `promotion_ready=true`.
- Current leaderboard top 20 all still show `backtest_certified=false`.
- Example at `spike/leaderboard.json:431-470`: top entry is PASS with `composite_confidence=0.7345`, but `artifact_completeness` is pending and `backtest_certified=false`.
- That means the current leaderboard is not a list of fully sealed deployment bundles, even though several docs speak as if it is.
- I did not find any current leaderboard entries with overall `validation.verdict="WARN"`.
- So the live board is stricter than the looser admission code path, but the code path remains ready to admit WARN entries.

## Safety Net Notes
- Prior Accelerator run said there was no pytest suite. That is no longer true.
- `tests/test_regression.py:1-161` is a real low-latency engine guardrail.
- It checks trade count, every trade's dates / reason / pnl tolerance, summary metrics, slippage baseline, compatibility facade parity, and legacy leaderboard schema reading.
- This materially improves local change safety for engine edits.
- I still saw no comparable test that pins leaderboard admission semantics or docs-to-code consistency.

## Long-Run Workflow Notes
- `scripts/search/safe_runner.py` is a pragmatic improvement: crash tracking, checkpoints, heartbeat, signal handling, and recovery-file persistence all reduce wasted compute.
- But `safe_runner.py:355-387` still pushes recovery back to the operator with a manual `python -c` rerun command if validation throws.
- `scripts/certify/full_sweep.py:1-18` offers a one-command rescore path, but it is explicitly exhaustive across the full registry and not a newcomer-safe sanity loop.
- `scripts/certify/recertify_leaderboard.py` backs up the live leaderboard before rewriting it, which is responsible, but it still means recertification is a live-state mutation path rather than a dry-run-first posture.

## Worldview Conclusion
- The repo is no longer blocked by missing engine tests.
- The real Accelerator concern is that the codebase cannot decide whether the leaderboard is a PASS-only contract, a 0.60+ watchlist, or a fully backtest-certified deploy surface.
- That ambiguity is worse than a missing command because it lets engineers move quickly while shipping a different meaning of "trusted" each time.
- For a new engineer, the unsafe step is not editing a strategy; it is deciding which output is real.

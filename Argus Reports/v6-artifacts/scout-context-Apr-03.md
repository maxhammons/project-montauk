# Scout Context — Apr-03

## Project Classification
- Type: Trading strategy development (TradingView/Pine Script)
- Primary language: Python (scripts), Pine Script v6 (strategies/indicators)
- Framework: Custom backtest engine + TradingView Pine Script v6
- Domain: Quantitative trading — leveraged ETF strategy optimization (TECL)
- Team size signal: solo (3 committers, but all are the same person + Claude AI pair)
- Maturity signal: growing (27 commits, first commit 2026-03-03)

## File Manifest

### Summary
| Category | Count | Est. Tokens |
|----------|-------|-------------|
| Source (Pine Script) | 16 | ~14,952 |
| Source (Python scripts) | 12 | ~19,704 |
| Config | 5 | ~1,048 |
| Tests | 0 | 0 |
| Docs / Reference | 30 | ~210,180 |
| Spirit-guide | 0 | 0 |
| Task history / Remote | 10 | ~4,884 |
| QA reports | 1 | ~52 |
| Previous Argus | 1 | ~52 |
| Static assets (data) | 1 | ~17,364 |
| Dependencies | 1 | ~40 |
| CI/CD | 0 | 0 |
| Other (.DS_Store) | 11 | 0 |
| **Total** | **88** | **~249,720** |

*Token estimate: 62,430 total lines x 4 tokens/line = ~249,720 tokens*

### Full File List (grouped by category)

#### Source — Pine Script (16 files)
- `src/indicator/active/Montauk Composite Oscillator 1.3.txt`
- `src/indicator/archive/Montauk Composite Oscillator 1.0.txt`
- `src/indicator/archive/Montauk Composite Oscillator 1.2.txt`
- `src/strategy/active/Project Montauk 8.2.1.txt`
- `src/strategy/archive/Project Montauk 1.0 (FMC).txt`
- `src/strategy/archive/Project Montauk 1.1 (FMC).txt`
- `src/strategy/archive/Project Montauk 1.4 (FMC).txt`
- `src/strategy/archive/Project Montauk 6.4 b.txt`
- `src/strategy/archive/Project Montauk 6.8 c.txt`
- `src/strategy/archive/Project Montauk 7-6.txt`
- `src/strategy/archive/Project Montauk 7-7.txt`
- `src/strategy/archive/Project Montauk 7.8.txt`
- `src/strategy/archive/Project Montauk 7.9.txt`
- `src/strategy/archive/Project Montauk 8.1.txt`
- `src/strategy/archive/Project Montauk 8.2.txt`
- `src/strategy/debug/Project Montauk 7.6 – Debug.txt`
- `src/strategy/debug/Project Montauk 7.8 – Debug.txt`
- `src/strategy/testing/Montauk RSI Regime.txt`
- `src/strategy/testing/archive/Project Montauk 8.3-conservative.txt`
- `src/strategy/testing/archive/Project Montauk 9.0-candidate.txt`

#### Source — Python Scripts (12 files)
- `scripts/backtest_engine.py`
- `scripts/data.py`
- `scripts/evolve.py`
- `scripts/generate_pine.py`
- `scripts/parity_check.py`
- `scripts/run_optimization.py`
- `scripts/spike_auto.py`
- `scripts/spike_state.py`
- `scripts/strategies.py`
- `scripts/strategy_engine.py`
- `scripts/validation.py`
- `scripts/signal_queue.json`

#### Config (5 files)
- `.gitignore`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `.claude/commands/sync.md`
- `CLAUDE.md`

#### Docs / Reference (30 files)
- `reference/Montauk Charter.md`
- `reference/pinescriptv6-main/LLM_MANIFEST.md`
- `reference/pinescriptv6-main/README.md`
- `reference/pinescriptv6-main/Pine Script language reference manual`
- `reference/pinescriptv6-main/pinescriptv6_complete_reference.md`
- `reference/pinescriptv6-main/pine_script_execution_model.md`
- `reference/pinescriptv6-main/release_notes.md`
- `reference/pinescriptv6-main/concepts/colors_and_display.md`
- `reference/pinescriptv6-main/concepts/common_errors.md`
- `reference/pinescriptv6-main/concepts/execution_model.md`
- `reference/pinescriptv6-main/concepts/methods.md`
- `reference/pinescriptv6-main/concepts/objects.md`
- `reference/pinescriptv6-main/concepts/timeframes.md`
- `reference/pinescriptv6-main/reference/constants.md`
- `reference/pinescriptv6-main/reference/functions/ta.md`
- `reference/pinescriptv6-main/reference/keywords.md`
- `reference/pinescriptv6-main/reference/types.md`
- `reference/pinescriptv6-main/reference/variables.md`
- `reference/pinescriptv6-main/visuals/backgrounds.md`
- `reference/pinescriptv6-main/visuals/bar_coloring.md`
- `reference/pinescriptv6-main/visuals/bar_plotting.md`
- `reference/pinescriptv6-main/visuals/colors.md`
- `reference/pinescriptv6-main/visuals/fills.md`
- `reference/pinescriptv6-main/visuals/levels.md`
- `reference/pinescriptv6-main/visuals/lines_and_boxes.md`
- `reference/pinescriptv6-main/visuals/overview.md`
- `reference/pinescriptv6-main/visuals/plots.md`
- `reference/pinescriptv6-main/visuals/tables.md`
- `reference/pinescriptv6-main/visuals/texts_and_shapes.md`
- `reference/pinescriptv6-main/writing_scripts/debugging.md`
- `reference/pinescriptv6-main/writing_scripts/limitations.md`
- `reference/pinescriptv6-main/writing_scripts/profiling_and_optimization.md`
- `reference/pinescriptv6-main/writing_scripts/publishing_scripts.md`
- `reference/pinescriptv6-main/writing_scripts/style_guide.md`
- `.claude/skills/about.md`
- `.claude/skills/spike.md`
- `src/strategy/testing/archive/backtest-comparison.md`

#### Task History / Remote (10 files)
- `remote/best-ever.json`
- `remote/diff-2026-04-02-8.3-conservative.txt`
- `remote/diff-2026-04-02-9.0-candidate.txt`
- `remote/evolve-results-2026-04-03.json`
- `remote/report-2026-03-04.md`
- `remote/spike-2026-04-02.md`
- `remote/spike-progress.json`
- `remote/spike-results-2026-04-03.json`
- `remote/spike-state.json`
- `remote/winners/rsi-regime-2026-04-03.json`

#### Static Assets / Data (1 file)
- `reference/TECL Price History (2-23-26).csv`

#### Dependencies (1 file)
- `scripts/requirements.txt`

#### Previous Argus Reports (1 file)
- `Argus Reports/v6-artifacts/calibration-context-Apr-03.md`

#### QA Reports
*None found outside Argus Reports.*

#### CI/CD
*None found.*

#### Tests
*None found.*

## Large Codebase Flag
**No.** 88 files, ~249,720 estimated tokens. The bulk (~210K tokens) is Pine Script v6 reference documentation in `reference/pinescriptv6-main/`. The actual project source code (Pine scripts + Python) is modest at ~35K tokens. Well within single-context limits.

## Spirit-Guide Detection
**Not found.** No `spirit-guide/` directory exists. This will need to be scaffolded if Gojo/Loom/Botan workflows are required.

## Previous Argus Reports
**Found.** `Argus Reports/v6-artifacts/calibration-context-Apr-03.md` exists (13 lines). An empty `Argus Reports/remediation-tasks/` directory also exists, suggesting a prior Argus run was initiated today.

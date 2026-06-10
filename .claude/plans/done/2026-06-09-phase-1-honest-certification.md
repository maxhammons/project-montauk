# Phase 1 — Honest certification (execution tracker)

Canonical plan: `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md` (Phase 1).

- [x] 1.5a Sideways filter — **resolved as KEEP + document** (deviation from original recommendation, justified by measurement): unsuppressing even just risk stops cuts the 8.2.1 reference 12.69x → 4.18x (35 ATR exits on recoverable calm-regime shocks); exposure is self-disarming (big moves break the range classification and re-arm exits). Loud rationale comment in engine; residual creep-down risk accepted + documented. Goldens unchanged.
- [x] 1.5b Dead EMA-cross exit fixed: confirm window collapses to 1 bar when sell-confirm off; pinned by `test_ema_cross_exit_fires_with_sell_confirm_disabled_and_window_geq_2`
- [x] 1.5c End-of-Data: documented mark-to-market (no slippage, symmetric with B&H) in both close-out blocks
- [x] 1.5d `_rma` NaN-tolerant (mirrors `_ema`): single NaN no longer silently disables ATR exit forever; identical on clean data
- [x] Goldens intact (no regen needed — all fixes no-op on defaults); suite green
- [x] 1.4 Gate-0 integrity real: `_run_engine_behavior_checks` (prefix-consistency ×2 depths, bar-close fill contract, single-position scan) + `CHARTER_INCOMPATIBLE_STRATEGIES` registry; verified live, all pass
- [x] 1.6 Named windows scored strictly in-range (era-style growth ratio; warmup feeds indicators only); verified on champion — 2024_onward 1.75→0.93, 2020_meltup 0.68→1.73
- [x] 1.7 Deleted broken `validation/walk_forward.py` + updated references
- [x] 1.3 `contract.py`: stamps never trusted — bundle re-verified on disk every sync, machine-portable path rebasing, path-less stamps = unverifiable; all 20 board rows resolve locally
- [x] 1.2 `recertify_leaderboard.py` deadlock fixed (stored bundles re-linked post-pipeline); mechanism verified by simulation (pending → re-link → gold ✓); ranking contract updated to Montauk Score
- [x] 1.1 Drift: `spike_runner` stamps `reproducibility` block on champion; new `verify_board_reproducibility.py` (report/--stamp/--enforce, 1% relative tolerance, exit 1 on drift). Live result: 0/20 rows reproduce → Phase 4 recert required
- [x] Doc-sync (validation-thresholds Layer-1 mechanisms, named_windows note, CLAUDE.md tree, scripts/README, project-status §2b) + full suite green (79 passed)

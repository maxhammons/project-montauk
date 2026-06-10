# Phase 4 — Re-certify the board + governance sync (execution tracker)

Canonical plan: `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md` (Phase 4).
Intent (Max, 2026-06-09): Gold certified = fit to trade, beats B&H, full confidence of the system.

- [x] 4.2 Diversity floor: MAX_ROWS_PER_STRATEGY=4 in update_leaderboard (8 reclaimer variants dropped at recert)
- [x] Quick-mode budget check: reopt_minutes=0.5 in quick mode → gate_oos OOS-WF ran
- [x] 4.1 Recertification complete: 20/20 PASS under hardened rules (fresh data, measured-N_eff deflation, PBO, OOS-WF, execution realism, event dependence, 1,000-resample bootstrap, in-range named windows); diversity cap → final board 12 rows, all Gold, backed up to leaderboard.json.pre_recert_backup
- [x] 4.3 Doc sync: CLAUDE.md weight table + paths, philosophy addendum, design-guide banner
- [x] 4.4 Spirit: pr/2026-06-09-a (Gold contract, Max's formulation + falsifiability), quick-reference populated, INDEX conflict resolved
- [x] Post-recert: verify_board_reproducibility --stamp → 12/12 reproduce with 0.0000 drift; active champion = chimera (montauk 0.6524, Gold)
- [x] 4.5 Acceptance gate: suite green (138), recert completes end-to-end, deflation on measured N_eff, true OOS + PBO reported per T2 row, deep-val report written, signal chain + demotion live

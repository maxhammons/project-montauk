# Offline spike + app refresh + viz staleness gate + divergence triage

Goals from Max 2026-06-09 (evening):
1. Spike runs offline with NO agent — drains a strategy queue (queue stocked by LLM sessions separately)
2. App "refresh" button triggers viz rebuild (build_viz) so the viz view is current
3. Viz must not open unless built from current data (staleness gate: compare bundle's data_end/leaderboard hash vs live; block/warn + rebuild if stale)
4. TRIAGE FIRST: governance active_blocked — live-holdout replay diverged on 1 snapshot → demotion stamped. Identify which snapshot/date, why (engine change vs data refresh vs champion validation swap during recert), rule benign-restamp vs real drift, document the ruling + add a sanctioned reset path (never silent).

- [x] 0. Divergence triage DONE: champion-swap artifact (snapshot by old champion timing_repair vs replay by chimera); fixed comparison semantics (champion_changed status, demotion only on same-identity divergence); stamp removed; governance unblocked (runs/operations/live_holdout.json — find diverged date; replay vs snapshot diff; ruling + remediation)
- [x] 1. Offline queue-drain DONE — spike-drain job (nightly 02:00, 2h budget, enabled, dual-lock vs daily, headless, events + job records); end-to-end verified on run 262 (4,164 evals, 20 validated, 0 admitted — bar held); --hours override duplication fixed in run_job: scheduler job (launchd) running spike_runner with --hours budget against the search roster; no LLM anywhere in path; results auto-validate + gold-gate as today
- [x] 2. App refresh DONE — Rust rebuild_viz command, Refresh rebuilds only-if-stale; → tauri command (or wrapper script) that runs build_viz.py then reloads the webview/viz view
- [x] 3. Staleness gate DONE — freshness stamp (data_end, leaderboard sha, built time) in bundle + HTML head; Open Viz hard-gates (auto-rebuild; refuses on failure); standalone badge + >24h banner in viz boot + app open-viz path: bundle stamps data_end_date + leaderboard sha; loader compares vs current files; stale → refuse + offer rebuild
- [x] Suite green (245) + doc-sync (CLAUDE.md viz section, pipeline.md ops section)
- [x] 4. Golden regression pinned DONE — both paths truncate to golden data_last_date; survived a live refresh same-session; compat test horizon-matched to frozen data: truncate live df to golden's data_last_date in both test_regression and integrity golden check (bar-immutability ledger guarantees the truncated prefix is frozen) — daily refreshes stop tripping goldens

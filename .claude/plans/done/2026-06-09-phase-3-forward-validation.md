# Phase 3 — Forward validation (execution tracker)

Canonical plan: `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md` (Phase 3).

- [x] Map existing infra — snapshots immutable + scheduled (launchd 13:30 UTC) + git-committed; live_holdout replay + governance blockers existed; gaps were chain/fills/demotion/immutability/calibration-feed
- [x] 3.1 Hash-chained signal log — `ops/signal_chain.py` + `signals/chain.jsonl` (19 snapshots backfilled, verify ok); new snapshots embed `prev_snapshot_sha256`; tamper tests in `tests/test_signal_chain.py`
- [x] 3.2 Fills journal + reconciliation — `ops/fills.py`: append-only `runs/ops/fills.jsonl`, `record`/`reconcile` CLI, slippage_bps vs next-snapshot-close proxy, execution-discipline gaps flagged
- [x] 3.3 Live auto-demotion — `live_holdout.evaluate_demotion` (live/B&H < 0.85 at ≥21 snapshots, divergence at any n, degradation < −0.15); governance blocker + `live_demotion` event + row stamping; eligibility gate deferred to Phase-4 recert per thresholds doc
- [x] 3.4 Data immutability — `data/manifest-history.jsonl` (seeded, 11 files), `verify_bar_immutability` + `refresh_determinism` in quality LOCAL_TESTS (13→15); tests in `tests/test_data_immutability.py` + `tests/test_data_quality.py`
- [x] 3.5 Calibration feed — `runs/confidence_v2/live_outcomes.jsonl` appended per live-holdout build (idempotent per date, production-guarded); consumed by confidence_vintage harness
- [x] Docs (thresholds: live demotion rule section) + suite green: **138 passed**

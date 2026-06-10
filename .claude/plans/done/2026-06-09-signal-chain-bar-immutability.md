# Hash-chained signal log (Phase 3.1) + historical-bar immutability (Phase 3.4)

- [x] Create `scripts/ops/signal_chain.py` (build_chain / verify_chain / chain_health / CLI)
- [x] Wire prev_snapshot_sha256 embed + ledger append into `daily.py::write_signal_snapshot`
- [x] Backfill: run build_chain once over the 19 existing snapshots
- [x] `manifest.py`: `data/manifest-history.jsonl` append on write_manifest + `verify_bar_immutability`
- [x] `quality.py`: add `test_bar_immutability` + `test_refresh_determinism` to LOCAL_TESTS
- [x] Seed manifest-history once (write_manifest)
- [x] Tests: chain build/verify/tamper in tests/test_ops.py; bar-immutability in new tests/test_data_quality.py
- [x] Live verification: signal_chain CLI (ok=True entries=19) + quality audit (45 PASS, 0 FAIL)
- [x] `make test` green before/after (79 baseline → 95)

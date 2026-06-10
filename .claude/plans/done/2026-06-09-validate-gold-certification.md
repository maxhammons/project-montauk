# Validate backtesting + Gold Status certification integrity

Goal: confirm the math checks out end-to-end (engine → validation → certification → leaderboard) and that "Gold Status" actually defends against overfitting, per the intent in spirit docs / charter / validation-philosophy.

- [x] Read spirit-memory (principles, decisions) + charter + validation-philosophy/thresholds for binding intent
- [x] Audit engine math: indicators (_ema/_tema/_atr/_adx), backtest loop, lookahead, slippage, share_multiple
- [x] Audit validation pipeline: gates 0–7, composite confidence weights, deflate/Monte Carlo, Morris/bootstrap, walk-forward
- [x] Audit certification chain: certify_champion, contract sync, gold_status criteria, montauk_score math
- [x] Cross-check spike/leaderboard.json entries against the stated admission rules (incl. gc_vjbb manual-admission exception)
- [x] Run the pytest suite and confirm golden regression passes — RAN: 5 FAILED / 72 passed; golden regression red (trade 50 exit 2026-06-05 vs golden 2026-05-22; share_multiple 12.689 vs 13.475)
- [x] Verify highest-severity agent findings personally (integrity stub, N_eff=300 stub, WF no-refit, drift warn-only, artifact pending-stamp, deep-val FAILs)
- [x] Write up verdict: what checks out, what doesn't, overfitting-defense assessment — delivered in conversation 2026-06-09

# Decisions

Choices made + rationale. A log of project-shaping calls — not every ticket, but the ones that lock in a direction.

Populated automatically by the prompt-submit hook when the user states decisions ("we're going with…", "we decided to drop…", "we chose X because…"). Seeded at setup time from historical decisions in raw docs if a seed source was provided.

Entries follow the format defined in `README.md`.

<!-- Entries below -->

## 2026-04-20-a
**Tags**: #process #tech #data
**Status**: active
**Important**: true
**Refs**: conflicts with principles#2026-04-20-a (leaderboard = certification)
**Statement**: Manually admitted `gc_vjbb` (fast=120/slow=150, bb_len=50, bb_width_look=50, bb_pct=40) to `spike/leaderboard.json` at #1 (fit=46.33, share=126.80x) despite validation verdict=WARN. WARN reason: single soft warning on gate 6 cross-asset (QQQ same-param share=0.443 < 0.50). Entry carries `manually_admitted: true` and a `manual_admission` block preserving the original WARN verdict and blocking reason — honest override, not a rule change. Principle pr/2026-04-20-a still stands for automated promotions; this is a one-off exception.
**Context**: Max explicit directive after diagnosis showed gc_vjbb was the strongest overlay across 28 candidates tested (raw TECL +9% vs VJ, marker alignment 0.617 > VJ's 0.577, only soft warning is a 0.057 miss on the QQQ gate). VJ itself passes that gate only via grandfathering at QQQ ~0.41. Admitted as an acknowledged exception rather than by weakening the gate threshold or changing `_is_leaderboard_eligible`.
---

## 2026-04-20-b
**Tags**: #tech #data #process
**Status**: active
**Important**: true
**Statement**: Decoupled external cross-source data verification from per-validation data-quality precheck. `scripts/data/quality.py::audit_all()` now splits into LOCAL_TESTS (default, 13 checks, no network) and AUDIT_TESTS (opt-in, includes `crosscheck_divergence` vs Tiingo/Stooq). Validation pipeline's `_run_data_quality_precheck` calls `audit_all()` default → local-only. Explicit audits use `audit_all(include_crosscheck=True)` or CLI `python scripts/data/quality.py --full`.
**Context**: Max identified that cross-source verification is an audit function, not a per-run precondition. Previous design ran Tiingo API call on every validation pass, causing HTTP-429 rate-limit failures to spuriously block legitimate strategy promotions (`slope_only_200` initially, `vj_or_slope_meta` during Next-Frontier Round D). After the fix, `vj_or_slope_meta` immediately promoted 9 configs to the leaderboard on retry — they had been blocked all along by the rate-limit cascade, not by strategy defects. Leaderboard grew 5 → 15 entries in one run.
---

## 2026-04-28-a
**Tags**: #strategy #validation #leaderboard
**Status**: active
**Important**: true
**Statement**: Treat `gc_vjatr_reclaimer` as an economic accumulation overlay, not the marker-timing repair module. The Gold Status leaderboard stays Gold-only; timing-improvement modules that degrade full / real / modern era economics belong in a research track, not the authority leaderboard.
**Context**: The fitness-ranked reclaimer certified as Gold and became the top authority row. A separate marker-first grid found reclaimer variants with better marker timing, but overlay-on-Gold-champion tests showed they cut full-history and modern performance too much. The next marker-timing work should target smaller explicit post-drawdown re-entry modules against the champion error atlas rather than continuing to force reclaimer to solve both economics and timing.
---

# Deep-Validation Adjudication Report

**Date:** 2026-06-09
**Mandated by:** `docs/*NEXT/archive/2026-04-deep-validation-real-world-accuracy-audit.md` §12 (checked 2026-05-22, never adjudicated until now)
**Context:** Phase 2 of `docs/*NEXT/2026-06-09-gold-standard-remediation-plan.md`
**Decision rule being applied:** the audit's own — "Any CRITICAL FAIL blocks live trading. All MATERIAL issues must be dispositioned."

This report gives every recorded CRITICAL/MATERIAL finding an explicit ruling:
**RESOLVED** (fixed in code), **RESOLVED BY POLICY** (reporting/scoring change),
**ACCEPTED RISK** (documented, bounded, signed off), or **OPEN** (still blocking).

---

## 1. Rulings on recorded FAILs

### D2.1 / D2.2 — Synthetic tracking error (TECL 8.96%/yr, TQQQ 3.29%/yr vs <3% threshold) — **ACCEPTED RISK (bounded)**
The synthetic pre-2008 series is structurally smoother than real TECL (D2.6) and
no financing-drag constant can fix dynamics, only level. Ruling:
- Synthetic-era data is retained for **shape** (regime structure, dotcom-class
  crash pressure in the GA fitness) — it is the only 2000-crash sample we have.
- Synthetic-era data is **never** quotable as expected performance (see D2.9).
- The provenance columns (`is_synthetic`), seam tests, and era-weighted scoring
  (modern 0.60 / real 0.25 / full 0.15, squash-saturated) bound the damage.
- Backlog: real-overlap residual calibration (stretch synthetic vol to match
  the 2008-12→present overlap distribution) if synthetic-era results are ever
  promoted above diagnostic status.

### D2.9 — Full-history share multiples 6–12× the real-era multiples — **RESOLVED BY POLICY**
Ruling: **the headline performance claim of any strategy is its real-era and
modern-era share multiple.** Full-history (synthetic-inclusive) multiples are
diagnostic-only and must be labeled as such wherever surfaced (viz, reports,
leaderboard discussion). The Montauk Performance pillar already era-weights
(full^0.15 × real^0.25 × modern^0.60) and saturates, so scores were never
dominated by the synthetic era; this ruling fixes the *narrative* layer.
Concretely: Jade Bonobo is honestly "1.29× real-era / 3.21× modern-era," not "35×."

### D3.2 / D3.4 / D9.6 / D9.7 — Close-to-next-open fill gaps; −15% degradation budget breached by 4 of 5 top rows — **RESOLVED (gate added)**
`execution_realism` is now a weighted sub-score in the composite
(2026-06-09): every candidate is re-run under `execution_timing="next_open"`
(now supported by both engine paths) and the share-multiple degradation is
scored with anchors −30% → 0.0, −15% → 0.5 (the audit's budget), −5% → 1.0.
Current champion: −12.2% (passes budget). Rows that breach the budget are
penalized in certification, not just noted in an archived audit.

### D4.9 — COVID-exclusion edge collapse 83–90% on all top-5 — **RESOLVED (gate added), with calibration note**
`event_dependence` is now a weighted sub-score: COVID-crash and 2022-bear
windows are spliced out, strategy + B&H re-run, worst collapse scored.
Anchors: ≥0.95 collapse → 0.0 (edge is literally one event), 0.80 → 0.5,
≤0.50 → 1.0, plus a critical warning at ≥0.80. Calibration note: a
charter-aligned defensive strategy *must* concentrate edge in the few real
crashes ("sell high, re-enter lower" is the mission), so moderate
concentration is structural; the anchors punish near-total dependence.
Current champion: 0.81 collapse → scored ≈0.46 with critical warning.
Null-calibrated anchors are in the backlog.

### D8.4 — Golden regression failing while board stayed certified — **RESOLVED**
Phase 0 (2026-06-09): ledger regenerated after verifying the divergence was
data-refresh-driven; `make test` + CI test gate added so the optimizer can
never run on a red net; the rtk silent-swallow hazard closed.

### D4.5 / D4.6 — Deflation N_eff wrong by orders of magnitude; null thin and stale — **RESOLVED**
N_eff now reads the live hash-index (4,116 deduped configs) with a ratcheting
high-water mark; the null distribution is recalibrated with ≥5,000 valid
samples, fingerprinted to engine hash + data manifest, with no silent
Beta(10,10) fallback.

## 2. Rulings on previously unexecuted CRITICAL checks

| Check | Ruling | Disposition |
|---|---|---|
| D5.2–D5.4 paper-trade journal + reconciliation | **OPEN** | Phase 3.2 — needs Max's actual fills |
| D5.5 point-in-time replay | **OPEN** | Phase 3.1 hash-chained signal log is the prerequisite |
| D8.1 / D8.2 refresh determinism + bar immutability | **OPEN** | Phase 3.4 |
| D1.1–D1.3 multi-source price verification | **OPEN** (partially mitigated by `data/quality.py --full` crosscheck) | Phase 3.4 / data-audit lane |
| D3.5 / D3.9 / D3.11 spreads, halts, survivorship | **OPEN** | research lane, MATERIAL not CRITICAL |

## 3. The live-trading question (the audit's decision rule)

The audit's rule says CRITICAL FAILs block live trading. As of this report:
D2.9, D3.x, D4.9, D8.4, D4.5/D4.6 are resolved by gate/policy/fix; D2.1/D2.2
are accepted-risk with the synthetic era demoted to diagnostic; the remaining
OPEN criticals are all **forward-evidence** checks (paper reconciliation,
point-in-time replay, immutability) that no backtest change can satisfy —
they are exactly Phase 3.

**Interim ruling (requires owner sign-off):** manual execution may continue
under the explicit understanding that (a) the believable edge is the real/
modern-era multiple, not the full-history number, and (b) forward-evidence
verification (Phase 3) is the only thing that can upgrade the confidence
claim. Until Phase 3 lands, every certified row carries unverified
forward-reconciliation risk.

> Owner sign-off: ☐ Max — I accept the interim risk and the real/modern-era
> framing of all performance claims. (Check on next review.)

## 4. Re-certification consequence

The board must be re-certified (remediation plan Phase 4) under: honest
deflation (N_eff 4,116), the two new sub-scores, in-range named windows, and
current data. Expect lower composites and possible Gold shrinkage — that is
the framework working. The reproducibility verifier already shows 0/20 rows
reproduce their stamped metrics under current data.

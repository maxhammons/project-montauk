# Committee validation performance (deferred)

**Context.** Validating `chimera_v2_2026_07_12` (11-member two-stage committee) took ~50
minutes single-core because every gate evaluation re-runs all member strategies (~1.2s per
committee evaluation, thousands of evaluations across the T2 gates). The pipeline's
existing multicore path only parallelizes *across candidates*, so a single committee
candidate always runs single-core.

**Two candidate speedups, in order of preference:**

1. **Memoize member signals in `library.py::_static_gold_two_stage_committee`** (and
   `_static_gold_committee`). At fixed member params, the 11 member state series are
   identical across repeated calls; only the thresholds/weights change in most gate
   perturbations (Morris, weight sweeps). Cache keyed by (data identity, strategy,
   params-hash) — data identity must distinguish truncated/era-sliced frames so
   prefix-consistency and era reruns stay correct. Signal-identical, testable against the
   frozen reproduction check.
2. **Intra-gate parallelism** (bootstrap resamples, Morris trajectories). This is
   validation-engine surgery: needs its own verification pass and doc-sync per the
   validation-hardening rules. Only worth it if committee candidates become routine.

Neither was done during the v2 certification on purpose — changing engine code
mid-certification would have broken comparability with the run that certified the current
board.

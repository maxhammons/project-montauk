# Montauk 3.0 Research — Stream 8: Independent reproduction and numerical determinism

## 1. One-page plain-English conclusion

Montauk's Gold claim rests on one sentence: *"a second, independent
implementation reproduces this exact signal, fill, trade, and verdict from the
same frozen inputs."* That is only true if (a) the reproduction
implementation is genuinely independent enough to catch a Rust engine bug,
and (b) "reproduce" is defined with enough numerical precision that a
harmless rounding difference isn't mistaken for a correctness failure, nor a
real bug waved off as "just floating point." Montauk has defined neither
"independent" nor "reproduce" precisely, and has no policy for the
randomness (mentioned once in the prior draft with no source) driving Gate 5
(Morris/bootstrap), PBO, and OOS walk-forward re-optimization. This stream
fixes all three gaps.

**What "independent" can and cannot mean here.** Knight & Leveson's 1986
n-version programming study is the load-bearing finding: 27 programmers
independently wrote the same anti-missile spec in Pascal from scratch, run
against one million random test cases, and their failures were *not*
statistically independent — several pairs failed on shared inputs, and on
two separate test cases eight of the 27 programs failed simultaneously,
because the spec's genuinely hard cases were hard for everyone [Evidence:
primary, Knight & Leveson 1986; confirmed by direct read of the paper's
"Experimental Results"]. The lesson is **not** "don't bother with a second
implementation" — it's "a second implementation written from the same prose
spec mostly protects against typos and slips, not a shared misreading of the
contract." Montauk's reference oracle is Python versus Rust (different
language, numeric libraries, and author sessions). **[Inference, not
itself evidence-sourced]:** this is plausibly a stronger design than Knight
& Leveson's same-language, same-cohort setup — but the charter's own
vocabulary ("family specification," fill timing, warm-up rules) is still the
single shared prose document both implementations read, and a shared
misreading of it will reproduce identically in both and pass every parity
check. Independent reproduction catches **implementation bugs**, not
**specification bugs**; the hand-derived fixtures in Section 7 are Montauk's
separate defense against the latter.

**What "numerically reproduce" must mean.** Floating-point addition is not
associative — `(a+b)+c` can differ from `a+(b+c)` in the last bit, and this
is IEEE 754 behaving as specified, not a bug [Evidence: primary, IEEE
754-2019; Goldberg 1991]. A backtest that sums ~4,000 daily log-returns in a
different order can legitimately produce a terminal wealth figure differing
in the 12th significant digit from the Python reference, with zero economic
implication. Bit-exact equality everywhere fails "reproduction" for no real
reason, training Max and future agents to ignore the alarm; zero tolerance
floor lets a genuine one-day-early signal bug pass as "probably just
floating point." Montauk needs a **tolerance ladder**: bit-exact for
integer-valued/categorical outputs (trade count, position state, fill date,
verdict), a measured tolerance for per-bar float quantities, and a separate,
tighter tolerance on the primary Gold number.

**What "reproduce" must mean for RNG-dependent validation math.** Gate 5
(Morris/bootstrap), PBO, and OOS walk-forward (`scripts/validation/
uncertainty.py`, `pbo.py`, `oos_walk_forward.py`) all draw from
`numpy.random.default_rng(42)`/`(43)`, whose default bit generator is PCG64.
Rust's `rand` crate default (`StdRng`) is ChaCha12 — a different algorithm
family [Evidence: primary/product docs, NumPy Random Generator manual; Rust
`rand` book]. No integer seed makes these produce comparable draws. No Rust
implementation of this validation math exists today, so this is a
**latent**, not active, gap — but the brief requires RNGs be addressed, and
bit-exact cross-implementation RNG parity is not the right bar here;
**distributional parity** (matching CI bounds, PBO estimate, Morris ranking
within a predeclared tolerance) is.

**What Max should decide now.** (1) A frozen numeric specification —
evaluation order, summation algorithm, rounding mode — wherever
cross-implementation order can be made to agree; (2) a tolerance ladder
derived from measured error, not guessed, for the places bit-exact agreement
isn't achievable; (3) an explicit RNG parity policy (distributional, not
bit-exact) if Gate 5/PBO/OOS math is ever duplicated outside Python; (4) a
permanent parity fixture suite (Section 7), re-run every release as a
release-blocking gate.

## 2. Evidence-quality table

| Claim | Evidence type | Source (URL) | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| Floating-point addition/multiplication is not associative; result depends on evaluation order | primary paper | Goldberg 1991, ACM Computing Surveys 23(1):5–48. https://dl.acm.org/doi/10.1145/103162.103163 | Strong | Yes — directly | Explains why summing daily log-returns in a different order changes the last bits of the result. |
| IEEE 754 arithmetic is deterministic *given* operation, operand values, and rounding mode; basic ops (+,−,×,÷,sqrt,abs,compare) are exactly specified for non-NaN cases; `exp`/`log`/trig are not required to be correctly rounded and can differ by platform/libm | primary/standard | IEEE 754-2019. https://ieeexplore.ieee.org/document/8766229 ; Rust RFC 3514. https://rust-lang.github.io/rfcs/3514-float-semantics.html | Strong | Yes — directly | Correction: RFC 3514 also documents NaN-generation nondeterminism **within a single run on one platform**, stronger than "differs across platforms." Montauk's NaN fixture (#11) only needs categorical fail-closed behavior, so unaffected. |
| Parallel/vectorized reductions change summation order and can change bit-level results run-to-run or platform-to-platform | primary paper | Demmel & Nguyen, "Fast Reproducible Floating-Point Summation," ARITH 2013; extended as Ahrens, Demmel & Nguyen, "Algorithms for Efficient Reproducible Floating Point Summation," ACM TOMS 46(3), 2020. https://dl.acm.org/doi/10.1145/3389360 | Strong | Yes — directly | Correction: previously cited the 2020 paper as "Demmel & Nguyen," dropping lead author Willow Ahrens; fixed to match References. Motivates pinning any SIMD/parallel reduction touching Gold-relevant sums. |
| Independently-written versions of the same spec do NOT fail independently; correlated failures are common and significant (up to 8-of-27 simultaneous, on two separate test cases) | primary paper | Knight & Leveson 1986, IEEE TSE 12(1):96–109. https://www.csc.kth.se/utbildning/kth/kurser/DA2210/vettig13/Seminarier/KnightLeveson.pdf | Strong | Partial — safety-critical embedded Pascal, not trading engines | Correction: prior draft said the 8-program failure happened "once"; direct read confirms two test cases. Qualitative lesson transfers; the 1986 rate does not. |
| Reproducible builds (bit-identical binaries from identical source/build environment) are an established, tooled discipline | primary/product-primary | reproducible-builds.org. https://reproducible-builds.org/docs/definition/ | Moderate | Yes, as engineering discipline, not strategy correctness | Relevant to pinning the Rust toolchain/CPU target for a certified Gold artifact; overlaps Stream 7. |
| Differential testing (two implementations, same input, diff outputs) is an established QA methodology | primary paper | McKeeman, "Differential Testing for Software," 1998. https://www.cs.tufts.edu/comp/150FP/archive/bill-mckeeman/DifferentailTesting.pdf | Strong | Yes — directly | Originally for compilers; transfers directly to signal/fill/trade parity. |
| Property-based testing (many random inputs, check invariants) finds edge cases hand-written examples miss | primary paper | Claessen & Hughes, "QuickCheck," ICFP 2000. https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf | Strong | Yes — for warm-up/lag/causal-boundary invariants | Complements fixed golden-master fixtures. |
| Kahan/compensated summation reduces summation error; to first order the leading error term is independent of n, but a smaller higher-order, n-dependent residual remains | primary paper | Kahan, "Further Remarks on Reducing Truncation Errors," Comm. ACM 8(1), 1965. | Strong | Yes — directly | Correction: prior draft stated the bound as unqualified "independent of n." Candidate order for the wealth-path summation. |
| The IANA tz database is the de facto source of truth for timezone/DST rules, including historical changes | primary/product-primary | IANA tzdata. https://data.iana.org/time-zones/tz-link.html | Strong | Yes — directly | "Next regular-session open" is a US/Eastern civil-time concept subject to historical DST changes; both implementations must pin the same tzdata version. |
| NumPy's `default_rng` uses PCG64 by default; Rust's `rand` crate default (`StdRng`) uses ChaCha12 — different algorithm families, no comparable output even from a matching integer seed | primary/product docs | NumPy manual, https://numpy.org/doc/stable/reference/random/generator.html ; Rust `rand` book, https://rust-random.github.io/book/guide-rngs.html ; `StdRng` docs, https://docs.rs/rand/latest/rand/rngs/struct.StdRng.html | Strong | Not yet — no Rust consumer exists today; latent risk if Gate 5/PBO/OOS math is ported to Rust | New row (prior draft had no RNG treatment). `uncertainty.py`, `pbo.py`, `oos_walk_forward.py` seed via `default_rng(42)`/`(43)`, feeding bootstrap (0.05), pbo (0.05), oos_walk_forward (0.10) composite weights. |
| A previously-Gold certificate is only reproducible if random seeds, library versions, and CPU/compiler target are all recorded | inference (synthesizing primary sources above) | — | Moderate | Yes | Not itself cited; implication of the IEEE 754/reproducible-builds/RNG literature combined. |

## 3. Recommended Montauk experiment(s)

### Experiment 8.1 — Parity fixture matrix (signals → verdict)

**Preregistered estimand:** for each fixture in Section 7, the maximum
discrepancy between Rust's output and Python's output on the identical
frozen input, across seven output classes: (1) daily signal state
(categorical, bit-identical); (2) fill price/date (date bit-identical;
price tolerance per 8.2); (3) trade ledger (timestamps bit-identical;
price/pnl_pct tolerance per 8.2); (4) daily wealth/equity curve (tolerance
on cumulative log-wealth, not compounding dollars, since log-wealth error
does not compound); (5) matched B&H terminal share count/value (same
tolerance class as 4); (6) the final Gold/no-Gold verdict and each plank
label (categorical, exact match — a plank flip is a correctness-gate
failure, not an "acceptable numerical difference"); (7) any RNG-dependent
validation output produced by Python alone today (Gate 5, PBO, OOS
walk-forward) — evaluated for **statistical** parity (bootstrap CI overlap,
matching PBO estimate, matching Morris ranking) rather than bit-identical
draws, since no second implementation exists to diff against; a placeholder
policy for the day one is proposed.

**Stopping rule:** run once per signed Rust engine release on the complete
fixture matrix, no partial runs, no re-running a failed fixture after an
undocumented code change. A failure blocks the release until fixed or the
expected value is corrected through an explicit reviewed diff, never
silently loosened.

**What is frozen before results:** fixture inputs, the expected-value
computation method, and the per-class tolerance table — all committed
before the new release is run against them.

### Experiment 8.2 — Tolerance calibration study

**Preregistered estimand:** the empirical worst-case per-bar floating-point
error in the Rust engine's actual summation order across the complete
observed TECL history (~4,000+ bars), measured by running the same Rust
binary twice — normal (possibly vectorized) path vs. a reference-forced
strictly sequential path — recording maximum absolute divergence in
cumulative log-wealth. Produces a data-derived tolerance, not a guessed one.

**Stopping rule:** run once on the complete real-data history plus once per
frozen named-event window; the resulting maximum divergence, times a fixed
safety factor (e.g., 10x, illustrative — the measured value governs)
predeclared before the run, becomes the frozen 8.1 tolerance. No re-running
with a different safety factor after seeing the result.

**What is frozen:** the safety-factor multiplier and the definition of
divergence (max absolute difference in cumulative log-wealth, sampled every
bar, not just terminal — a mid-series divergence that cancels by the end
must still be caught).

### Experiment 8.3 — Adjudication drill (seeded discrepancy)

**Preregistered estimand:** time-to-detection and correct classification
rate when a known, seeded discrepancy (Section 4) is injected into either
implementation in a disposable branch and the standard release pipeline is
run against the frozen fixture matrix.

**Stopping rule:** each seeded-defect class in Section 4 is injected exactly
once, the pipeline runs to completion, and the classification (caught as
correctness failure / silently passed / miscategorized as floating-point
noise) is recorded verbatim. No retries, no threshold-tuning after seeing a
miss — a miss is itself the finding.

## 4. Null, defect, and planted-signal controls

- **Null control:** identical inputs run through both implementations twice
  each (Rust-vs-Rust, Python-vs-Python) before comparing Rust-vs-Python,
  isolating internal nondeterminism (uninitialized memory, hash-order
  dependence, thread races) from cross-implementation "parity."
- **Seeded off-by-one-bar defect:** shift the Rust engine's fill date forward
  one day for one trade type in a disposable branch. Expected: the
  trade-ledger fixture flags a bit-exact mismatch every run, not just under
  deep audit.
- **Seeded rounding-mode defect:** compile Rust with flush-to-zero/
  denormals-as-zero enabled and confirm the suite detects a wealth-curve
  divergence exceeding the 8.2 tolerance, proving the ladder isn't so loose
  that a real numeric-mode bug slides through as "just floating point."
- **Seeded DST/timezone defect:** pin a disposable branch to a stale tzdata
  release predating a known historical US DST change and confirm a fixture
  straddling that date produces a detectably different fill date.
- **Seeded RNG-algorithm-mismatch control:** confirm a hypothetical Rust
  bootstrap using ChaCha12 with a "matching" integer seed produces resample
  indices with **zero bit overlap** with numpy's PCG64 output (expected, not
  a bug), while confirming both, at the predeclared resample count, converge
  to overlapping confidence intervals (required; a failure here is flagged).
  Distinguishes "should not require" bit parity from "should require"
  statistical parity for RNG-dependent outputs.
- **Planted economically-meaningful signal:** a fixture engineered so both
  implementations should agree AND reproduce a specific hand-derived number
  (e.g., a synthetic 3-trade series with hand-computed terminal wealth) — the
  positive control proving the fixtures detect disagreement *from ground
  truth*, not just disagreement between implementations.
- **Adversarial silent-cheat control (design review, not a runnable test):**
  if the Python oracle and Rust engine were both derived by copy-pasting the
  same buggy helper (the Knight & Leveson correlated-failure risk), only the
  fixture suite's hand-computed expected values — not cross-implementation
  agreement — would catch it. Argues for independently-derived expected
  values in Section 7, not merely Rust-matches-Python.

## 5. False-Gold and false-rejection consequences

**If the tolerance ladder is too loose:** a genuine off-by-one-bar fill
error, a wrong slippage sign, or a corrupted comparator could produce a
wealth multiple that looks Gold but isn't actually reproducible — the
charter's false-Gold failure mode. This maps specifically to **Plank 1
(Correctness)**, whose fail condition explicitly includes "implementation
divergence" (charter §4.3) — not **Plank 5 (Reproducibility and currency)**,
the separate clean-environment/build-reproducibility question (charter
§4.5), which Section 6 already concedes is "a supply-chain concern (Stream
7) this stream depends on but does not own." Stream 8's differential-testing
deliverable closes Plank 1's divergence clause; it only partially informs
Plank 5, and a reader should not conflate the two.

**If the tolerance ladder is too tight:** every release intermittently
"fails" parity for reasons unrelated to correctness — a compiler upgrade, a
different CPU's SIMD width, a changed libm version for a volatility
indicator's `log()` call. Repeated false alarms train Max (and future
agents) to ignore "parity failed" alerts, which is precisely the condition
under which a real discrepancy later gets waved through unexamined — a
false-rejection culture that quietly degrades into false acceptance once
alarm fatigue sets in.

**Asymmetry:** the charter is explicit that false Gold is worse than a
missed good strategy, but for this stream specifically the practical risk
skews the other way — an unmeasured, "safe-looking" tight tolerance is more
likely in practice than a clean false Gold (Gold also requires passing the
other four planks). Calibrate tolerances from measured data (Experiment 8.2),
not by feel.

## 6. Assumptions and power/limits

- **Independent reproduction bounds confidence; it doesn't replace spec
  review.** A shared misreading of the StrategySpec vocabulary, fill-timing
  contract, or a primitive's semantics reproduces identically in Rust and
  Python and passes every parity fixture. This stream's fixtures catch
  implementation divergence, not a specification both implementations
  correctly and identically implement incorrectly — the hand-derived
  Section 7 fixtures plus periodic adversarial spec review (outside this
  stream's scope) are the actual defense.
- **Knight & Leveson's scale does not transfer numerically.** Montauk has
  two implementations, not 27, and a finite fixture matrix, not a million
  random tests. The qualitative lesson (correlated failure is real and
  common) transfers; the 1986 quantitative rate does not.
- **Transcendental-function nondeterminism is real and bounded, but the
  trigger is specifically `log`/`exp`/trig, not every operation in a
  volatility calculation.** A primitive that annualizes volatility by
  scaling with `sqrt(252)` uses a correctly-rounded, deterministic operation
  per IEEE 754; nondeterminism enters only if the underlying volatility
  estimate is built from `log()`-based returns upstream of that scaling
  step. (Correction: prior draft cited "volatility annualization"
  generically without isolating which sub-operation is actually
  nondeterministic.) This is permanent sub-tolerance noise for
  `log`/`exp`/trig-based primitives specifically, not a bug to chase to
  zero.
- **RNG algorithm parity across Python and Rust is not free and may not be
  the right goal.** NumPy's PCG64 and Rust's default ChaCha12 are different
  algorithm families; bit-exact cross-language draw parity would require
  porting matching PCG64 parameters into Rust (fragile against numpy
  version changes to seed-sequence hashing) for a benefit — bit-identical
  Monte Carlo draws — the validation math does not need. Distributional
  parity is the recommended bar, but this stream cannot certify it today
  because no second implementation of Gate 5/PBO/OOS walk-forward exists to
  test it against; flagged as insufficient evidence pending a concrete
  second implementation, not resolved.
- **Reproducibility of a Gold certificate requires more than numeric
  agreement.** It also requires exact library/compiler/CPU-target versions
  to be recorded, a supply-chain concern (Stream 7) this stream depends on
  but does not own (see Section 5).
- **This stream cannot certify economic validity.** A perfectly
  reproducible, bit-exact-parity strategy can still be overfit or worthless.
  Reproduction answers "did both implementations compute the same thing,"
  not "is it worth trading" — that belongs to Streams 2–4 and the charter's
  economic-passage and search-honesty planks.

## 7. Required fixtures and durable artifacts

**Deterministic positive fixtures** (expected output hand-derived or
independently-tool-derived, not merely cross-checked between Rust and
Python):

1. *Single-trade fixture*: one entry, one exit, hand-computed fill price
   (slippage/fee applied by hand), pnl_pct, and terminal wealth on a 3-row
   synthetic series.
2. *Multi-trade cooldown fixture*: exercises the entry-cooldown state
   machine; expected trade count/dates computed by hand.
3. *Warm-up boundary fixture*: a series exactly as long as the longest
   indicator's warm-up window plus one bar; verifies no primitive signals
   before warm-up is satisfied.
4. *Causal-boundary (prefix-replay invariance) fixture*: run on the full
   array, then on every historical prefix; assert each prefix's last-bar
   signal is bit-identical to the full run's corresponding bar. Operationalizes
   "no lookahead, no repainting" as a fixture, not just a design intention.
5. *Matched B&H fixture*: hand-computed share count/terminal value from
   fixed starting capital and a short frozen series, using the exact
   eligible-start and cost-convention rules the comparator uses.
6. *DST-boundary fill-date fixture*: a frozen window straddling a documented
   historical US DST transition, confirming both implementations resolve
   "next regular-session open" to the identical date via pinned tzdata, not
   system-local time.
7. *Stable-sort tie-break fixture*: two candidates/events with identical
   sort keys; confirms both implementations use a stable sort or an
   explicit tie-break, so ordering isn't hardware/library-dependent.
8. *RNG-dependent statistical-parity fixture (new)*: for any output drawn
   from `np.random.default_rng` (Gate 5 Morris, bootstrap, PBO, OOS
   walk-forward), assert two independent runs at the production resample
   count produce overlapping confidence intervals / matching qualitative
   rankings — a same-implementation stability check today, becoming a
   cross-implementation statistical-parity check once a second
   implementation exists.

**Seeded-negative fixtures** (expected result: fail closed with a structured
discrepancy artifact, never a silent pass):

9. Off-by-one-bar fill date (Section 4).
10. Flush-to-zero/denormals-as-zero compiler-flag defect (Section 4).
11. Stale-tzdata defect (Section 4).
12. Non-finite input (`NaN`/`Inf` injected mid-series) — must fail closed
    with a structured error, never propagate `NaN` silently.
13. Duplicated/shuffled-row input (violates "one row per verified trading
    day") — must reject before computing a signal.
14. *Silently-reduced Monte Carlo resample count* (e.g., B=1000 becomes
    B=10) — must flag insufficient resample count as a structured warning,
    never silently return a narrower/wider CI as ordinary sampling variance.
    Guards against a real RNG-budget defect being misdiagnosed as noise.

**Retained acceptance artifacts** (durable, versioned, per release):

- Fixture input files (frozen CSVs/generators with fixed seeds) and their
  hand-derived or independently-tool-derived expected outputs, version-stamped.
- Per-release parity report: for every fixture, Rust output, Python output,
  discrepancy, tolerance used, pass/fail.
- Tolerance-calibration report from Experiment 8.2, re-run whenever the Rust
  engine's parallelism/vectorization strategy changes.
- Exact Rust toolchain version, target triple, and enabled CPU feature flags
  (e.g., AVX2 on/off) per signed release, so a clean-environment rebuild can
  be checked for byte-identical output.
- The tzdata version pinned by both implementations, re-fixture-tested
  whenever tzdata publishes a release affecting US market-calendar dates.
- The RNG bit-generator identity and seed(s) used for every Gate 5/PBO/OOS
  walk-forward run, recorded alongside the resample count, so a
  reproducibility question about a certified row's confidence interval can
  be answered without re-deriving it from scratch.

## 8. Unresolved owner decisions

1. **How tight should the primary-metric tolerance be, and who sets the
   safety factor?** Recommended default: derive it empirically per
   Experiment 8.2 (measured worst-case divergence x a fixed, predeclared
   safety margin) rather than a round number. Tradeoff: more defensible, but
   requires the calibration study before any fixture is finalized.
2. **Should transcendental-function primitives (log/exp/trig volatility
   measures) carry their own wider, individually-justified tolerance, or be
   excluded from the registry until a reproducible-math library is
   adopted?** Recommended default: allow them with their own wider
   tolerance rather than inheriting the tight arithmetic-only tolerance.
   Tradeoff: exclusion is safer but removes economically plausible
   indicators before evidence says they're a problem.
3. **Is Rust engine parallelism/SIMD auto-vectorization allowed on the
   primary wealth-path summation?** Recommended default: disable it (or
   force a fixed reduction order per Demmel & Nguyen / Ahrens et al.)
   specifically for cumulative-wealth and comparator calculations; allow
   normal optimization elsewhere. Tradeoff: modest speed cost on the one
   path that touches the Gold-certifying number.
4. **How often must the parity fixture suite re-run, and does a failure
   block only new releases or also revalidate already-Gold rows?**
   Recommended default: every signed core release (release-blocking) plus
   whenever tzdata, Rust toolchain, or CPU target changes; a failure blocks
   new releases but does not retroactively revoke existing Gold certificates
   unless the defect is shown to have affected their inputs.
5. **(New) Should Montauk require bit-exact or distributional parity for
   RNG-dependent validation math (Gate 5, PBO, OOS walk-forward), if a
   second implementation is ever built?** Recommended default:
   distributional/statistical parity (overlapping CIs, matching qualitative
   rankings, at a predeclared resample count), not bit-identical draws —
   porting numpy's exact PCG64 stream into Rust is fragile and buys no
   correctness benefit the statistical bar doesn't already provide.
   Tradeoff: distributional parity is a fuzzier pass/fail line than a diff,
   needing its own predeclared tolerance (Fixture 8) before it is a release
   gate rather than a judgment call. **Unresolved and explicitly deferred**
   — no second implementation exists today to calibrate against.

## References

- Goldberg, D. (1991). "What Every Computer Scientist Should Know About
  Floating-Point Arithmetic." *ACM Computing Surveys* 23(1): 5–48.
  https://dl.acm.org/doi/10.1145/103162.103163 — Primary.
- IEEE. (2019). *IEEE 754-2019 — IEEE Standard for Floating-Point
  Arithmetic*. https://ieeexplore.ieee.org/document/8766229 — Primary (standard).
- Rust Project. RFC 3514 — Float Semantics.
  https://rust-lang.github.io/rfcs/3514-float-semantics.html — Primary
  (digest of IEEE 754 conformance and its limits, incl. single-platform
  run-to-run NaN nondeterminism).
- Kahan, W. (1965). "Further Remarks on Reducing Truncation Errors."
  *Communications of the ACM* 8(1): 40. — Primary (compensated summation;
  bound holds to first order in n, with a smaller n-dependent residual).
- Demmel, J., & Nguyen, H. D. (2013). "Fast Reproducible Floating-Point
  Summation." *ARITH 2013*: 163–172; extended as Ahrens, W., Demmel, J., &
  Nguyen, H. D. (2020), "Algorithms for Efficient Reproducible Floating
  Point Summation," *ACM TOMS* 46(3). https://dl.acm.org/doi/10.1145/3389360
  — Primary.
- Knight, J. C., & Leveson, N. G. (1986). "An Experimental Evaluation of the
  Assumption of Independence in Multi-Version Programming." *IEEE TSE*
  12(1): 96–109.
  https://www.csc.kth.se/utbildning/kth/kurser/DA2210/vettig13/Seminarier/KnightLeveson.pdf
  — Primary. Verified by direct read: 27 versions, one million tests; the
  most extreme correlated failure was eight programs failing on a common
  test case, on two separate test cases (not "once," correcting the prior
  draft).
- McKeeman, W. M. (1998). "Differential Testing for Software." *Digital
  Technical Journal* 10(1): 100–107.
  https://www.cs.tufts.edu/comp/150FP/archive/bill-mckeeman/DifferentailTesting.pdf
  — Primary.
- Claessen, K., & Hughes, J. (2000). "QuickCheck: A Lightweight Tool for
  Random Testing of Haskell Programs." *ICFP 2000*.
  https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf — Primary.
- IANA. *Time Zone Database (tzdata)*.
  https://data.iana.org/time-zones/tz-link.html — Primary (product/authority).
- Reproducible Builds Project. "Definitions."
  https://reproducible-builds.org/docs/definition/ — Primary (bit-for-bit
  rebuild discipline referenced in Section 7's toolchain-pinning artifact).
- NumPy. "Random Generator" manual (`default_rng`'s default PCG64 bit
  generator). https://numpy.org/doc/stable/reference/random/generator.html —
  Primary (product documentation).
- Rust `rand` crate. "Our RNGs" (Rand Book) and `StdRng` docs (default
  ChaCha12 algorithm). https://rust-random.github.io/book/guide-rngs.html ;
  https://docs.rs/rand/latest/rand/rngs/struct.StdRng.html — Primary.
- Project Montauk 3.0. `charter.md` (§4.3 five planks, §4.5
  reproducibility), `rust-strategy-and-evaluation-policy.md`,
  `validation-engine-hardening.md`, `decisions.md`,
  `scripts/validation/uncertainty.py`, `pbo.py`, `oos_walk_forward.py` —
  Primary (internal spec/code; repo-grounding for every Montauk-specific
  claim above).

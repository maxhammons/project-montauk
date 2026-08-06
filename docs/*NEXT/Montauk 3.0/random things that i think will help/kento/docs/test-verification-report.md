# Kento Test Suite Verification Report

> **Historical (2026-08-04).** The 38% survivor rate below was driven to
> seven documented equivalents (98.5% caught), enforced by
> `tools/mutation_sweep.py` in CI; see `kento-done-audit/2026-08-05-resolution.md`.

**Date:** 2026-08-04
**Scope:** `src/app.rs`, `src/install.rs`, `src/lint.rs`, `src/types.rs`, `src/lib.rs`, `src/main.rs`, `tests/integration.rs`, `.github/workflows/ci.yml`
**Toolchain:** rustc 1.95.0, cargo 1.95.0, git 2.50.1, macOS (APFS, case-insensitive)
**Method:** independent re-verification, hostile-environment injection, concurrency stress, fuzzing, and mutation testing.

**Verdict: the suite is stable and honest, but it is not yet bulletproof.**
Everything it asserts, it asserts well. The problem is what it does not assert: 38% of viable
semantic mutations to product code pass the entire suite undetected, including a hook-tampering
case with real safety consequences.

No product or test file was modified. Source hash before and after testing:
`4766b964…0e847bf` (unchanged).

---

## 1. What passed

| Check | Result |
| --- | --- |
| `cargo test` (debug) | 31/31 pass (12 unit, 19 integration) |
| `cargo test --release` | 31/31 pass |
| `cargo fmt --check` | clean |
| `cargo clippy --all-targets -- -D warnings` | clean |
| 30 serial repeats of the release suite | 30/30 pass, zero flakes |
| `--test-threads` = 1, 2, 8, 32 | pass at every level |
| 30 concurrent suites (6-way × 5 rounds) | 30/30 pass |
| 16 concurrent `cargo test --release`, shared target dir | 16/16 pass |
| 12 concurrent `cargo test --release` with forced rebuild | 12/12 pass |
| umask 000 / 022 / 027 / 077 | pass at every umask |
| `LC_ALL=tr_TR.UTF-8`, `LC_ALL=C` | pass |
| `PATH` reduced to `/usr/bin:/bin`, exotic `TMPDIR` | pass |
| Git removed from `PATH` | fails loudly, never skips silently |
| Real `$HOME` pollution | none — no `~/.local/bin/kento*`, no `~/.local/share/kento` |
| Workspace cleanup | zero `target/kento-*` leftovers after ~120 suite runs |
| Fuzz corpus: 632 files (random bytes, NUL, BOM, CRLF, invalid UTF-8, 2 MB single line, 60k-line file) | no crash, no hang, 60,390 valid JSONL diagnostics, correctly sorted |
| Output determinism | byte-identical across 8 runs (single SHA-256) |

Three design decisions deserve credit, because they are the reason the suite is as stable as it is:

- **Workspace isolation** keys on process id *and* nanosecond clock, so parallel test processes
  cannot collide. Verified across 30 concurrent suites.
- **`Cleanup` implements `Drop` and calls `unlock_tree` first**, so a panicking permission test
  cannot leave an unremovable directory behind. Verified — zero leftovers.
- **`lock_directory` proves the denial took effect** and panics if writes still succeed. Under root
  or a mode-ignoring filesystem the suite fails loudly instead of passing vacuously. This is the
  single most important anti-vacuity guard in the file.
- **`global_uninstall_rolls_back_hooks_removed_before_a_later_failure` is order-deterministic by
  construction.** `read_records` sorts by hook path (`src/install.rs:376`), and the second repo is
  deliberately named `repository z with spaces` so `w` < `z` forces the first hook to be removed
  before the second fails. The rollback path is genuinely exercised, every run.

I could **not** reproduce the previous audit's concurrency finding. Across 58 concurrent suites in
three configurations — prebuilt binary, shared target dir, and forced simultaneous rebuild — there
were zero failures.

---

## 2. Findings

### HIGH — 38% of product-code mutations survive the suite

I generated semantic mutations of product code (excluding `#[cfg(test)]` blocks), ran the full
suite against each, and recorded whether any test failed.

| Outcome | Count |
| --- | --- |
| Caught (a test failed) | 69 |
| **Survived (suite still green)** | **43** |
| Uncompilable (invalid mutant, excluded) | 13 |
| Timeout (mutant hangs) | 5 |

**Mutation score: 69/112 = 61.6%.**

Survivors by file: `src/lint.rs` 26, `src/install.rs` 12, `src/app.rs` 5.

I hand-verified four survivors independently of the harness to confirm the result is real. All four
reproduced: the mutant compiles, changes behaviour, and `cargo test` still reports 19/19 pass.

- `src/install.rs:744` — `||` → `&&` in hook tamper detection
- `src/app.rs:478` — `==` → `!=` in the `KENTO201` language mapping
- `src/lint.rs:312` — `==` → `!=` in the CSS comment terminator search
- `src/install.rs:74` — `ends_with` → `starts_with` in the shebang compatibility check

### HIGH — hook tampering inside the managed block is untested, and the consequence is severe

`install_hook_and_uninstall_preserve_or_refuse_safely` (`tests/integration.rs:801-811`) tests
exactly one tamper: it overwrites the hook with `#!/bin/sh\n# altered\n`, destroying **both**
markers and the block body at once. That satisfies both halves of the guard at
`src/install.rs:744`, so the test passes even when the guard is weakened to `&&`.

The untested case is tampering that **leaves the markers intact and edits the body**. I built the
mutant and ran it:

```
# hook after tampering (markers intact, command neutralised)
# >>> kento managed block >>>
'/…/kento' all --staged --ATTACKER-NEUTRALISED
# <<< kento managed block <<<

$ kento uninstall
exit=0                      # reports success
```

Under the mutant, `uninstall` exits 0, deletes the binary and the manifest, and **leaves the
tampered block in the hook pointing at a binary that no longer exists** — a repository left in a
broken, silently mis-reporting state.

The real build refuses correctly:

```
kento: recorded hook /…/pre-commit has altered Kento block
exit=2
```

**So the product is right and the test is missing.** Nothing in the suite would notice if that
guard regressed.

### HIGH — six install/uninstall refusal paths are never asserted

Six `return Err(...)` sites in `src/install.rs` can be turned into `return Ok(())` — converting a
refusal into a silent success — with the suite still green:
lines **206, 241, 260, 476, 530, 737**.

These are precisely the "refuse rather than clobber" guarantees the tool exists to provide. The
suite asserts several refusals very well (`assert_refused` correctly checks exit code 2 *and* the
specific stderr message, which is good practice), but these six are not among them.

### MEDIUM — `hermetic()` does not clear every Git configuration carrier

`hermetic()` (`tests/integration.rs:66-77`) clears `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`,
`XDG_CONFIG_HOME`, `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_INDEX_FILE`. Git reads configuration from
more places than that:

| Injected variable | Suite result |
| --- | --- |
| `GIT_CONFIG_COUNT` + `GIT_CONFIG_KEY_0=core.hooksPath` | **9 of 19 fail** |
| `GIT_CONFIG_PARAMETERS='core.hooksPath'='…'` | **9 of 19 fail** |
| `GIT_COMMON_DIR` | **12 of 19 fail** |
| `GIT_TEMPLATE_DIR` containing a `pre-commit` hook | **1 of 19 fails** |
| `GIT_CEILING_DIRECTORIES`, `GIT_NAMESPACE`, `GIT_OBJECT_DIRECTORY`, `GIT_PREFIX`, `GIT_AUTHOR_*`, `GIT_COMMITTER_*`, `GIT_*_PATHSPECS`, `GIT_ATTR_NOSYSTEM` | pass |

Severity is **medium, not high**, and the previous audit overstated it. I captured the exact
environment Git exports inside a real `pre-commit` hook and ran the suite under it verbatim: it
**passes**, because the keys Git injects (`safe.bareRepository`, `credential.interactive`) are
harmless. Reaching the failure requires a config-carrying variable that actually matters.

It is still worth fixing. The suite already clears `GIT_DIR`/`GIT_INDEX_FILE`, which shows the
intent is full hermeticity; leaving `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_COMMON_DIR`,
and `GIT_TEMPLATE_DIR` uncleared is an inconsistency in that intent, and these are set by
`git rebase --exec`, `git bisect run`, and wrapper tooling — exactly the unattended paths where a
false failure costs the most trust.

### MEDIUM — `src/lint.rs` is the weakest-tested file by a wide margin

26 of 43 survivors are in `lint.rs`, concentrated in the lexer state machines that decide what is
*not* code — string masking, escape handling, raw strings, heredocs, CSS comment scanning, HTML tag
scanning. Representative survivors:

| Line | Mutation | Meaning |
| --- | --- | --- |
| 312 | `window == b"*/"` → `!=` | CSS unterminated-comment terminator search |
| 254, 257, 274 | `byte == b'\\'` → `!=` | escape-sequence handling inside strings |
| 356, 359, 368 | quote/`r`/`#` comparisons | Rust and Python raw/triple-quoted string detection |
| 808 | `tag[cursor] != *current` → `==` | HTML attribute tag scan |
| 84 | `||` → `&&` | HTML element name matching |

The existing `lint.rs` unit tests are thoughtfully chosen — the unpaired-quote docstring case and
the `<<FIRST <<SECOND` double-heredoc case show real adversarial thinking. But ~150 lines of tests
cover ~890 lines of dense byte-level state machine, and the mutation data shows the gap.

### MEDIUM — `KENTO001` and `KENTO002` have no end-to-end coverage

Both rules are exercised only by unit tests in `src/lint.rs` (conflict markers, missing final
newline). Neither appears in `tests/integration.rs`, so neither is verified through the real
discovery → lint → render → exit-code path.

### LOW — extensionless shell detection over-matches by prefix

`src/types.rs:42-47` uses `bytes.starts_with(b"#!/usr/bin/env bash")`, so any interpreter whose
name merely *begins* with a known shell is linted as shell. Confirmed against the real binary:

```
$ kento sh --format text
KENTO003 weird:2:8:  …    # file begins '#!/usr/bin/env bashful'
KENTO003 weird2:2:8: …    # file begins '#!/bin/shenanigans'
```

The unit test is named `recognizes_extensionless_shell_scripts_only_by_shebang` and asserts the
negative cases `#!/usr/bin/env python3`, `plain text`, and `notes.txt` — but never a shebang that
shares a prefix with a real shell. The name promises more than the test delivers.

### LOW — CI is not reproducible and will break on its own schedule

`.github/workflows/ci.yml` pins no toolchain and passes no `--locked`. `cargo clippy -- -D warnings`
on a floating `stable` fails the day a new Rust release adds a lint — an unattended, unprovoked red
build. There is no `rust-toolchain.toml`. Coverage and mutation gates are not automated, which is
why the gaps above went unnoticed.

### LOW — coverage limits of this run

- The host volume is **case-insensitive** (APFS). Case-sensitivity bugs cannot surface locally and
  would only appear on the Linux CI leg.
- Linux was not exercised: no Linux runner or Docker daemon available.
- The repository has no commits, so the workflow has never actually run.
- Root-execution behaviour was inspected but not run. The `lock_directory` guard is correct by
  construction and would panic rather than pass vacuously.

---

## 3. Recommended order of work

1. Add a test that tampers **inside** the managed block while leaving both markers intact, and
   assert `uninstall` refuses with `has altered Kento block`. Highest value per line of test code.
2. Assert the six unasserted refusal paths in `src/install.rs` (206, 241, 260, 476, 530, 737).
3. Add `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_COMMON_DIR`, and `GIT_TEMPLATE_DIR` to the
   `env_remove` list in `hermetic()`.
4. Strengthen `lint.rs` unit tests around string, escape, heredoc, and comment boundaries — the
   26 survivors are a ready-made worklist.
5. Add integration coverage for `KENTO001` and `KENTO002`.
6. Add a prefix-collision case (`#!/usr/bin/env bashful`) to
   `recognizes_extensionless_shell_scripts_only_by_shebang`, and fix `src/types.rs` to require a
   terminator after the interpreter name.
7. Pin the toolchain with `rust-toolchain.toml`, add `--locked`, and run mutation testing in CI so
   score regressions are caught automatically.

---

## 4. Bottom line

The suite is **reliable** — it does not flake, does not pollute the host, cleans up after itself,
is deterministic, is concurrency-safe, and fails loudly rather than skipping when its prerequisites
are missing. Those properties were verified across roughly 120 suite executions and are genuinely
hard to achieve.

It is not yet **complete**. A mutation score of 61.6%, six unasserted refusal paths, and a
demonstrated hook-tampering blind spot mean the suite would stay green through regressions that
matter. Reliability without sensitivity is confidence you have not earned. Items 1–3 above close
the serious gaps and are small, contained changes.

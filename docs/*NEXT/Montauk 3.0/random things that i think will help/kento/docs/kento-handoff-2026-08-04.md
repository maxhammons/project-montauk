# Kento — session handoff, 2026-08-04

> **Historical.** Superseded by `kento-handoff-2026-08-05.md`, and every
> remaining item was closed on 2026-08-05; see
> `kento-done-audit/2026-08-05-resolution.md`.

Repo: `/Users/Max.Hammons/Developer/local-sandbox/kento` (branch `master`, 7 commits, tree clean)

## The bar this work is measured against

> it is of paramount importance that these tests are bulletproof. they must work all the
> time. there should be no errors in them. they must work without human oversight. trust in
> these is the very essence of kento.

**This bar is NOT yet met, and it is now measured rather than guessed.** A mechanical
mutation sweep over the product code found **24 guards that no test is watching** in the
first 40% of the search space — projecting to roughly 60. The worklist is below. Do not read
the committed gate's "34/34" as evidence the bar is met: those 34 mutations were chosen by
hand, and the mechanical sweep is what showed the suite is materially less sensitive than
that number implies. See *The trap* below.

Also unmet: **Linux has never executed**, and CI has never run at all.

---

## What was done

Two audit reports in `docs/` were verified finding-by-finding. **Every finding was real** —
nothing was a false positive. Three corrections to the reports themselves:

- Both atomicity bugs were **worse** than reported: they wedge the tool permanently, not
  just fail a retry. Only manual file deletion recovered.
- Report 2's "could not reproduce the concurrency finding" was **wrong**. It reproduces at
  ~1 in 20. Cause: concurrent `cargo test` runs sharing one target dir relink
  `CARGO_BIN_EXE_kento` in place, and a child executing that file while it is rewritten dies
  by signal with no exit status.
- Three of the six named "unasserted refusal paths" are **not reachable from the CLI**.

### Commits

| Commit | What |
| --- | --- |
| `148b9bb` | Baseline import of the audited tree (repo had no commits) |
| `2410ef3` | install rollback, resumable uninstall, shebang terminator fix |
| `102fc3f` | rustfmt + Clippy as `KENTO401`/`KENTO402`; pinned CI |
| `33b16d3` | Plan record |
| `04890d7` | Upgrade wedge closed; suite hardening |
| `55d302f` | Adaptive mode marker in the upgrade test |
| `5ec2469` | `tools/mutation-gate.py` + CI sensitivity job |

### Product fixes (all verified fail-before / pass-after)

- `install` rolls back commands it created if it fails before writing the manifest.
- `install` sets the previous binary aside when replacing it and restores it on failure
  (this was the upgrade-path wedge).
- `uninstall` is resumable: a manifest describing an already-removed binary no longer
  dead-ends.
- Shell shebangs need a terminator after the interpreter name (`#!/bin/shenanigans` is no
  longer linted as shell; `#!/bin/sh -e` still is).

### Feature: Kento runs rustfmt and Clippy

`src/toolchain.rs`. `cargo fmt --check` → `KENTO401`, `cargo clippy --all-targets` →
`KENTO402`, merged into the one sorted report. Gated on a repo-root `Cargo.toml` plus at
least one discovered Rust file; findings filtered to the files the run actually linted; a
tool that runs but never gets as far as checking exits 2 rather than reporting clean.
`Diagnostic.message`/`help` became `String` to carry tool wording. Kento passes its own
checks (`cargo run --release -- all` exits 0).

---

## OPEN: the mutation sweep (highest priority)

`kento-broad-sweep.py` (copied to this Desktop) enumerates every single-token semantic
mutation of product code, with comments, string/char literals, and `#[cfg(test)]` excluded so
a no-op cannot masquerade as a survivor. **453 sites.** I stopped it deliberately at index
180 — it mutates `src/` in place, and a session teardown mid-mutation would have handed you a
corrupted source file. The repo is verified clean at `5ec2469`.

| Verdict | Count |
| --- | --- |
| Caught (unit tests) | 48 |
| Caught (integration) | 89 |
| Caught (hang, killed) | 1 |
| **Survived** | **24** |
| Uncompilable | 19 |

**138/162 viable = 85%.** Extrapolating over all 453 sites: expect roughly **60 survivors**.

**Resume with `python3 kento-broad-sweep.py 181 453`** (it takes a start and stop index; fix
the hardcoded `REPO` and output paths first). Raw partial log:
`kento-mutation-sweep-partial.log`. Design notes worth keeping: stage 1 `cargo test --lib`
(~1.2s) then stage 2 `--test integration` (~6s), so cheap kills stay cheap; 45s/180s timeouts
with `os.killpg` on the process group; restore via `git checkout -- src`; refuse to run
against a dirty `src/`.

### Survivor worklist — 24 confirmed guards no test is watching (lines at `5ec2469`)

| Site | Mutation | Line |
| --- | --- | --- |
| `app.rs:294` | `\|\|`→`&&` | `if line.is_empty() \|\| line.starts_with('#') {` |
| `app.rs:302` | `false`→`true` | `\|\| !is_valid_relative_path(path, false)` |
| `app.rs:337` | `false`→`true` | `return false;` |
| `app.rs:371` | `true`→`false` | `if !explicit_file && !relative.is_empty() && ignored(.., true) {` |
| `app.rs:386` | `false`→`true` | `if !explicit_file && ignored(&relative, ignore, false) {` |
| `app.rs:412` | `false`→`true` | `vec![(root.to_path_buf(), false)]` |
| `app.rs:424` | `false`→`true` | `.unwrap_or(false);` |
| `app.rs:634` | `false`→`true` | `if staged_path_is_skipped(&path) \|\| ignored(&path, &ignore, false) {` |
| `app.rs:699` | `&&`→`\|\|` | `if fields.len() == 3 && fields[2] == "0" {` |
| `install.rs:304` | `\|\|`→`&&` | `if !metadata.is_file() \|\| metadata.file_type().is_symlink() {` |
| `install.rs:366` | `\|\|`→`&&` | `if !file_type.is_file() \|\| file_type.is_symlink() {` |
| `install.rs:374` | `\|\|`→`&&` | `if path.is_empty() \|\| path.contains('\n') {` |
| `install.rs:392` | `false`→`true` | `return false;` (in `path_in_path`) |
| `install.rs:394` | `==`→`!=` | `env::split_paths(&paths).any(\|c\| c == path)` |
| `install.rs:430` | `\|\|`→`&&` | `if !metadata.is_file() \|\| metadata.file_type().is_symlink() {` |
| `install.rs:462` | `&&`→`\|\|` | `2 if recorded && existing.matches(&expected).count() == 1 =>` |
| `install.rs:484` | `==`→`!=` | `Err(error) if error.kind() == ErrorKind::NotFound => {}` |
| `install.rs:566` | `true`→`false` | `Some(Ok(_)) => true,` |
| `install.rs:609` | `==`→`!=` | `if source == resolved {` |
| `install.rs:709` | `!=`→`==` | `.filter(\|error\| error.kind() != ErrorKind::NotFound)` |
| `install.rs:921` | `==`→`!=` | `Err(error) if error.kind() == ErrorKind::NotFound => {}` |
| `lint.rs:47` | `<`→`>=` | `if start < bytes.len() {` |
| `lint.rs:67` | `==`→`!=` | `if bytes[cursor] == current {` (in `html_tag_end`) |
| `lint.rs:72` | `==`→`!=` | `} else if bytes[cursor] == b'>' {` (in `html_tag_end`) |

Patterns worth exploiting rather than grinding one at a time:

- **`install.rs:304` and `:430`** are `!is_file() || is_symlink()` — the identical guard whose
  *uninstall* twin at `:793` now has a working test. A directory satisfies one half and a
  symlink the other, so the same directory-plus-symlink pair should kill both.
- **`install.rs:484`, `:709`, `:921`** are all `ErrorKind::NotFound` tolerance branches — the
  resumability fixes. One test that exercises a partially-removed installation may cover
  several.
- **`app.rs:371`/`:386`/`:412`/`:424`/`:634`** are the `explicit_file` boolean and the
  ignore-path plumbing. `discovery_skips_implicit_ignored_files_but_not_explicit_files` exists
  but clearly isn't discriminating; check whether it asserts the *directory* case too.
- **`lint.rs:47`/`:67`/`:72`** are `lines()` final-line handling and `html_tag_end` quote
  tracking — the file the first audit already called the weakest tested, so expect more
  survivors in the unrun 273 sites.

### The trap this exposed — read before trusting any score

`tools/mutation-gate.py` reports **34/34**, and that is honest but narrow: the 34 mutations
are ones *chosen by hand*. The broad sweep proves the suite is materially less sensitive than
that number suggests. During this session **three tests were found passing for the wrong
reason**, all three caught by mutation testing rather than by reading them:

1. The `Cargo.toml` manifest gate looked tested — but the fixture lives inside Kento's own
   package, so an ungated run walked up, found *that* manifest, and quietly checked it. Now
   pinned by a unit test rooted outside any package.
2. A dedup assertion counted a rustfmt message, which is never duplicated. Cargo already
   dedups across targets, so the `dedup` call was unreachable; removed.
3. "A tool that cannot run is an error" only covered a *missing* `cargo`, never the failure
   the guard exists for.

Also worth knowing: two measurement harnesses lied during this session. One grepped
rtk-filtered output and produced false `CAUGHT` verdicts. The other used `shutil.copytree`,
which preserves mtimes, so cargo kept serving a **mutant binary** while verdicts were being
recorded — every `CAUGHT` from that run was meaningless. Both are fixed in the committed
gate (`git checkout` restore, exit codes as ground truth), but the lesson generalises:
**verify the harness before trusting its verdicts.**

---

## OPEN: Linux has never run

Half the CI matrix (`ubuntu-latest`) is unexercised, and CI has **never run at all** — the
repo had no commits before today, so push it and read the first run carefully.

I tried to close this locally: `Docker.app` exists, `open -a Docker` was issued, but the
daemon never came up within the session (it likely wants a login or a terms acceptance).
**Next session: bring Docker up, then run the suite in a `rust:1.95` container** with
`CARGO_TARGET_DIR` set *inside the container* so it cannot collide with the host `target/`.
Reviewed-not-run assumptions that Linux would actually test:

- `fs::copy` carrying permission bits (the upgrade test's mode marker depends on it)
- `std::env::temp_dir()` having no ancestor `Cargo.toml` (the manifest-gate unit test
  depends on it — it is `/tmp` on Linux)
- No case-insensitive path comparisons anywhere

---

## OPEN: three untestable guards, deliberately kept

Cleanup-of-cleanup paths in `src/install.rs`, reachable only under a concurrent `install` or
a filesystem where a write succeeds but the matching removal fails. Not portably injectable.
They were **kept, not deleted** — removing real defence-in-depth to raise a mutation score is
backwards. But they are unverified lines in a tool whose whole job is refusing to clobber
files, so they belong on any honest status report.

Two pieces of genuinely unreachable code *were* removed, because an unexercised line is an
unverified one and neither protected anything: a `dedup` Cargo already does, and a sort the
caller repeats.

---

## What is actually solid

50 tests (19 unit, 31 integration), up from 31. Zero failures across:

| Dimension | Coverage |
| --- | --- |
| Serial repeats | 20 release, 20 debug |
| Parallelism | `--test-threads` 1, 2, 4, 8, 32 |
| Concurrent suites, shared target dir | 32 |
| umask | 000, 022, 027, 077 |
| Locale | `tr_TR.UTF-8`, `C`, `en_US.UTF-8`, `POSIX` |
| Git config carriers | `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_COMMON_DIR`, `GIT_TEMPLATE_DIR`, each injected alone |
| Ambient `CARGO_TARGET_DIR` | redirected; does not derail the toolchain tests |
| Hygiene | no `target/kento-*` leftovers, no `$HOME` pollution, no stray processes |

`cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` clean. `kento all` on
its own repo exits 0.

Suite hardening that matters for unattended runs: workspace names carry an atomic counter
(the clock is coarser than a thread switch, and two tests sharing a directory would have one
cleanup delete the other's tree); each workspace runs its own copy of the binary (kills the
concurrency flake); toolchain tests inherit the real environment instead of guessing rustup
lives at `$HOME/.rustup`; Clippy's wording is never asserted, only the rule, file, and
position, so a reworded lint cannot turn a green suite red.

---

## Watch out for

- **A mutation can turn a lexer state machine into an infinite loop.** A previous session
  left five hung `kento` test binaries spinning at 99–297% CPU for ~50 minutes each, plus two
  hung Python harnesses. Max spotted them in Activity Monitor. Any mutation harness needs a
  timeout *and* `os.killpg` on the process group. Check `ps` for
  `kento-[a-f0-9]{16}` before and after.
- **Never run two things against the repo at once.** A mutation sweep plus a stray
  `cargo test` fight over the cargo lock and each other's `src/`; it inflated per-mutant time
  from 6s to 45s and produced one bogus "real" failure that was actually mutant residue.
- **`.claude/plans/` auto-archives** a plan whose checkboxes are all ticked into `done/`.
  Don't pre-tick boxes for unfinished work.

## Files left on the Desktop

| File | What |
| --- | --- |
| `kento-handoff-2026-08-04.md` | this document |
| `kento-broad-sweep.py` | the mechanical mutation sweep; resume with `181 453` |
| `kento-mutation-sweep-partial.log` | raw verdicts for indices 0–180 |

## First three moves next session

1. **Finish the sweep** — `python3 kento-broad-sweep.py 181 453` — for the true score. 273
   sites unrun, and `lint.rs` (the weakest-tested file per the first audit) is barely touched.
2. **Work the survivor list**, exploiting the four patterns above rather than one at a time.
   Start with `install.rs:304`/`:430`, which have a working test pattern to copy.
3. **Get Linux green** — Docker locally, or push and read the first real CI run.

Then, and only then, is the bar in the opening section arguably met — and the honest way to
state it even at that point is "measured at N% sensitivity across 453 mutations on two
platforms," not "bulletproof."


---
## High Level

❯ what are we building here? what are we working twards. one sentnence

A linter an AI agent can be trusted to obey without a human checking its work — which is why the real deliverable isn't the seven rules, it's proof the tests would catch it if any of them ever broke.

✻ Sautéed for 6s · 1 shell still running

❯ is it a deterministic linter that checks a codebase and fails anything that is against the rules

Yes — that's exactly it, with two qualifications worth naming.

What matches your description: seven fixed rules across seven languages, no config, no warning mode, no severity levels. Exit 0 clean, 1 findings, 2 error. lint_bytes is pure — bytes in, sorted diagnostics out, no filesystem or network — and the audit verified byte-identical output across 20 runs on a 700-file random corpus. The pre-commit hook lints index blobs, not the worktree, so it fails what you're actually committing.

Qualification one: escapes exist, deliberately. .kentoignore for paths, .kentoexceptions for a rule+path pair — but each exception requires a written reason, and kento ignore-audit flags any that have gone stale or no longer apply. So it's "fails everything unless you've explicitly justified it, and it checks your justifications."

Qualification two, and this one is mine: the KENTO401/KENTO402 rules I added today shell out to rustfmt and Clippy. Their wording and lint set depend on the toolchain version. I pinned it in rust-toolchain.toml and stopped asserting Clippy's exact wording in tests, so it's reproducible — but that's determinism by pinning, not by construction like the other seven. Before today, "offline, no language runtime" was true without exception; now there's one, gated on a repo-root Cargo.toml.

You asked for it explicitly and I think it's right — a Rust linter that reports clean while Clippy has something to say isn't telling you the truth. But it does mean the tool now has two tiers of trustworthiness, and given that trust is the whole point, that's worth deciding consciously rather than inheriting from me.

✻ Sautéed for 23s · 1 shell still running

❯ what is big hang up? why is it taking so long?

Three things, and only one of them is legitimate.

The legitimate one: the deliverable isn't the linter, it's proof the tests would catch a regression — so every layer needs its own verification. Test the code, then test the tests (mutation), then verify the mutation harness. That regress is real work, and the sweep is inherently serial: mutate → rebuild → run → restore, ~6s × 453 sites. It can't be rushed, only parallelized.

The one that's on me: a large share of elapsed time was me fixing my own instrumentation, not doing the work. Harness one grepped filtered output and produced false CAUGHT verdicts. Harness two preserved mtimes so cargo served a mutant binary while I recorded results — every verdict from that run was garbage. My probe binary was named wrong, so argv[0] dispatch made all 38 probes exit 2. Then a printf "$2" in double quotes let zsh expand $((...)) before it hit the file. Four instrumentation bugs, each discovered only after acting on its bad output. That's rework, not progress.

The structural one: "bulletproof" has no stopping point. Every measurement finds more — 24 survivors in the first 40% of the space, and 273 sites unrun.

The lever, if you want speed: run the sweep across 8 git worktrees in parallel — 45 minutes becomes ~6 — and fix the 24 survivors by their four shared patterns rather than one at a time. And pin the bar to something finite: 100% mutation score across all 453 sites, green on Linux and macOS. That's achievable and checkable. Left as "bulletproof," I'll keep finding things indefinitely and you'll keep getting reports like this one.

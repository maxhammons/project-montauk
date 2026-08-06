# Is Kento done? — audit, 2026-08-05

The bar this is measured against:

> it is of paramount importance that these tests are bulletproof. they must work
> all the time. there should be no errors in them. they must work without human
> oversight. trust in these is the very essence of kento.

**Verdict: not done.** One blocker, four open issues, and two fixed while writing
this. Everything below is measured, and each item says how it was measured so the
number can be re-derived rather than believed.

## What passes

| Check | Result | How |
| --- | --- | --- |
| Mutation score | 472/480 viable = **98.3%** | `tools/mutation_sweep.py 0 514 12` |
| Of what a test can kill | **100%** (472/472) | 8 survivors, each proven equivalent |
| Tests | 82 (39 unit, 43 integration) | `cargo test` |
| macOS | green, self-lint exit 0 | `cargo test && kento all` |
| Debian 13 / glibc 2.41 | green, self-lint exit 0 | `tools/linux-suite.sh` on `rust:1.97` |
| Alpine / musl | green, self-lint exit 0 | `tools/linux-suite.sh` on `rust:1.97-alpine` |
| Real-world corpus | 27 repos, 97,333 files | `kento-test/check.py` |
| Crashes, hangs | **0** | same |
| Determinism | byte-identical on repeat | same |
| False positives | **0** of 22,458 verified against bytes | same |
| Silent misses | **0.6%**, every case explained | `kento-test/canary-sample.py` |

## BLOCKER

### 1. CI has never executed. Not once.

The workflow in `.github/workflows/ci.yml` is written and looks right. It has
never run, because the repository has no Git remote — it exists only on one
laptop.

This is the item that decides the verdict. Every result in the table above was
produced by a human deciding to run it. The bar says *work without human
oversight*, and a suite that runs only when someone remembers to run it **is**
human oversight, by definition. Nothing else on this list matters as much.

**Cannot be closed from inside the repository.** Pushing the code to GitHub is a
decision for its owner, not for the tool.

**Effort:** minutes to push; then read the first run carefully, because it will
be the first time the matrix has been exercised by anything but Docker on one
machine.

## Open issues

### 2. `kento maintenance` edits whatever repository it is run in

`maintenance` resolves its root the same way linting does — the nearest ancestor
holding `.git` — and rewrites that repository's `rust-toolchain.toml`.

Run inside somebody else's checkout it will raise *their* pin, verify with
`cargo fmt` and `clippy`, and keep the change if those pass. It reverts on
failure and it never touches a repository without a pin, so it cannot corrupt
anything. It is still surprising: a command named "maintenance" modifying a file
in a repository the user was only linting.

**Options:** restrict it to the repository Kento was built from; require a
confirmation flag for any other; or document it loudly and leave it. Not decided.

### 3. The staleness note tells foreign repositories to run a command that would edit them

Reproduced against a scratch package pinned to 1.60.0:

```text
kento: pinned Rust is 1584 days old (1.60.0 (7737e0b5c 2022-04-04)); run `kento maintenance` to move it forward
```

The note is accurate and the advice is wrong for that repository: running
`kento maintenance` there would rewrite its pin, which is issue 2. The note
should either say something a bystander can act on, or not fire for a pin Kento
does not own.

### 4. `kento all` takes 230s on one corpus repository

Measured on `nvm`, which holds 307 shell files (302 found by shebang, not
extension). ShellCheck alone on those same files takes 220.4s; Kento's own share
is about 2s, and `kento sh nvm.sh` matches `shellcheck nvm.sh` to within 0.1s.

So this is the cost of the industry-standard checker on an outlier repository,
not a defect in Kento. It matters anyway, because the stated purpose is a linter
an agent runs after editing a file:

| Workload | Time |
| --- | --- |
| One file, no shell | 0.003s |
| One shell file, 1 KB | 0.02s |
| One shell file, 164 KB | 10.3s |
| Whole repository, 3,394 files, no shell | 0.7s |
| Whole repository, 307 shell files | 230s |

The agent workflow — edit a file, lint that file — is unaffected. A full-repository
run on a shell-heavy tree is not.

**Options:** run ShellCheck in parallel batches (it is single-threaded per
invocation, and the machine has cores idle); leave it and document the number.
Adding concurrency would add untested surface, so it was not done today.

### 5. Two `install.rs` cleanup paths remain unverified

`install.rs:484` and `:709`, the cleanup-of-cleanup branches, were closed today
by driving `undo_install` directly from a unit test. **This item is resolved** and
is listed only because earlier handoffs carried it as open.

## Fixed while writing this audit

### `.kentoexceptions` accepted rules it must not

Adding `KENTO501` to the list of rules an exception may name also added
`KENTO401` and `KENTO402`. Both are excluded by design and the README says so:
`kento ignore-audit` validates exceptions offline and cannot re-run rustfmt,
Clippy or ShellCheck, so an exception naming one could never be shown to have
gone stale. It would have been a suppression with no expiry and no audit — the
one shape of escape hatch this tool deliberately does not offer.

Caught by reading the README against the code, not by any test. Three cases now
pin it.

### The corpus canary blamed Kento for its own invalidity

`check.py` planted `x = 1 ` as its probe. That is a syntax error at the top of a
Rust file, so in any Cargo package `cargo fmt` failed, Kento exited 2 with no
findings, and an errored run was counted as a missed one. Four repositories were
reported as failing a check they had never been given a fair chance at.

The same mistake had already been made and fixed in `canary-sample.py` earlier
the same day, and was not carried across. The probe is a comment now, and a run
that exits 2 is skipped rather than counted.

## The eight survivors, for completeness

All proven equivalent — no input distinguishes mutant from original, so no test
can kill them. Full arguments in `docs/kento-equivalent-mutants.md`.

| Site | Why unkillable |
| --- | --- |
| `app.rs:433`, `app.rs:445` | A boolean a short-circuit makes unreachable |
| `install.rs:367` | Bypassing the guard hits an identical error message downstream |
| `lint.rs:226` | Steps onto a newline no rule reads |
| `lint.rs:737` | `unwrap_or` behind a bounds check that guarantees `Some` |
| `lint.rs:740` | Widens a predicate; every new admission is rejected a line later |
| `toolchain.rs:103` | The file was read successfully moments earlier |
| `toolchain.rs:124` | `getcwd` never returns a symlink, so both branches agree |

Counting these as failures makes 100% unreachable and the score unusable. They
are subtracted from the denominator, and the reason for each is written down so
the subtraction can be argued with.

## What "done" would take

1. **Push and read the first CI run.** Blocker. Everything else is a judgement
   call; this is not.
2. Decide issues 2 and 3 — the scope of `maintenance` and what the staleness note
   says to a repository Kento does not own.
3. Decide issue 4 — parallelise ShellCheck, or publish 230s as the known cost.
4. Re-run the sweep and the corpus after any of the above. Every time code was
   added today it arrived undertested: 15 of 47 new sites the first time, 3 of 14
   the second. That pattern is the reason for the rule, not an argument against
   it.

## How to re-derive every number here

```sh
cargo test                                              # 82 tests
python3 tools/mutation_sweep.py 0 514 12                # 98.3%, 8 survivors
python3 tools/mutation_recheck.py <indices> 6           # re-check a subset
docker run --rm -v "$PWD":/src:ro \
  -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97 sh /s.sh
docker run --rm -v "$PWD":/src:ro \
  -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97-alpine sh /s.sh

cd ../kento-test
./fetch.sh                                              # 27 repos, 1.9 GB
python3 check.py ../kento/target/release/kento          # crash, hang, determinism, truth
python3 canary-sample.py ../kento/target/release/kento  # silent-miss rate
./reset.sh                                              # corpus back to pristine
```

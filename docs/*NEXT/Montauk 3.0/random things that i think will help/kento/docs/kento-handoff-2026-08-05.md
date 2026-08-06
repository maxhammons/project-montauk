# Kento — session handoff, 2026-08-05

> **Historical.** Every open item below was closed on 2026-08-05; see
> `kento-done-audit/2026-08-05-resolution.md`. CI now exists and is green,
> the gate is fixed, and the survivor count is 7, enforced by the sweep.

Repo: `/Users/Max.Hammons/Developer/local-sandbox/kento` (branch `master`, tree clean)

Supersedes `kento-handoff-2026-08-04.md`. Where the two disagree, this one is measured.

## The bar

> it is of paramount importance that these tests are bulletproof. they must work all the
> time. there should be no errors in them. they must work without human oversight. trust in
> these is the very essence of kento.

**Every killable mutant is killed, and the tool no longer goes silent on real
code.** What remains is a decision about CI. Every number below is measured.

| | 2026-08-04 | now |
| --- | --- | --- |
| Mutation score | 76.1% *(324/426 viable)* | **98.5%** *(460/467)* |
| Excluding proven-equivalent mutants | not distinguished | **100%** *(460/460)* |
| Survivors | 102 | **7, every one proven equivalent** |
| Mutation sites | 453 | 500 |
| Tests | 50 | **74** (32 unit, 42 integration) |
| Platforms | macOS only | **macOS, Debian/glibc, Alpine/musl** |
| Real-world corpus | none | **27 repos, 97,333 files** |
| False positives on that corpus | unknown | **0 of 22,806 findings** |
| Silent misses on that corpus | unknown, and it was 3.5% | **0.6%, all explained** |
| CI | never run | **still never run** — a judgement call, see below |

The previous handoff projected ~60 survivors from a 40% sample. The real number
was 102. Projections from a partial sweep are not reliable.

## The finding that mattered most

Mutation testing measures whether the tests would notice a regression. It cannot
notice code that is wrong on purpose-built input but wrong on real input too,
because the code does exactly what it was written to do.

Linting 27 real repositories found that **Kento silently reported clean on 3.5%
of files** — 11.5% of Rust files. `quote_mask` read a byte as an opening quote,
the string never closed, and everything after it was masked. A Rust lifetime is
an apostrophe. A shell here-string `<<<` parsed as a heredoc. A backslash in a
CSS selector escaped nothing. An apostrophe in HTML prose — `didn't` — silenced
the rest of the document. A JavaScript regular expression holding a quote
desynchronised the scan.

That is the worst way for a linter to be wrong. A false positive is loud and
gets fixed; this exits 0 and says clean, which is what an agent told to obey
Kento would act on. All five are fixed; the rate is now 0.6%, and every
remaining case is a file that is not the language its extension claims.

Two lessons worth keeping. **The first measurement of it was wrong**: the probe
was `x = 1 `, a syntax error at the top of a Rust file, so `cargo fmt` failed,
Kento exited 2, and an errored run was counted as a miss — inflating Rust from
11.5% to 15.5%. **And the fix arrived undertested**: it added 47 mutation sites,
15 of them uncovered, and it silently disarmed an existing test that had proved
its point with an apostrophe that no longer opens a string. Both were caught by
re-running the sweep afterwards, which is the argument for doing so.

## What happened today

### The sweep was finished, and parallelised

`tools/mutation_sweep.py` shards all 453 single-token mutations across git worktrees, so no
two mutants share a `src/` or a target directory. It reproduces the old serial harness's
verdicts exactly (25/25 on a sampled range) and runs the full space in well under an hour.

`tools/mutation_recheck.py` re-runs a chosen set of sites. That is the loop that matters
after writing a test — the full sweep answers "what is the score", the recheck answers "did
what I just wrote kill anything", in a minute rather than an hour.

Both take `KENTO_SWEEP_DIR` (default `/tmp/kento-sweep`) and refuse to start if test binaries
from an earlier run are alive.

### 67 of the 102 survivors were killed

All verified fail-before / pass-after. The productive move was never one mutant at a time —
it was finding the *probe* that makes an internal boundary observable:

- **Trailing whitespace as a mask probe.** `quote_mask` decides which bytes are literal
  content and so exempt. Asserting the exact set of *reporting lines* — rather than "a
  finding exists somewhere" — states each boundary to the byte. One table killed 16.
- **Fixtures that reach the code at all.** Every heredoc fixture used a bare `<<END`, so the
  delimiter parser's escape and quote paths had never executed. Nine mutations survived on
  code no test reached.
- **Inputs where two readings disagree.** A raw string and an ordinary string mask the same
  span unless the fixture holds a quote that ends one and not the other.
- **Both directions of a rule.** The duplicate-attribute rule needed prose that *looks* like
  a tag (`set x=1 and x=2 -> done`) as much as it needed real duplicates.

### Two real defects, neither findable on macOS

**The suite could write into the repository it was running in.** `workspace()` created an
empty `.git` directory. Git does not recognise that as a repository — finding no `HEAD`,
`objects` or `refs` it walks *up* — so `git rev-parse --git-path hooks` answered with the
nearest real repository above the workspace. Under the sweep, whose workspaces live inside a
worktree of this checkout (and worktrees share one hooks directory with the main repository),
a mutated `install` wrote its managed pre-commit hook into `.git/hooks/pre-commit` here,
aimed at a binary under a temporary directory. Every commit afterwards failed. Fixed by
writing the three entries Git looks for; `a_workspace_is_a_repository_git_stops_at` pins it.

**`ETXTBSY` on Linux.** A workspace writes its own copy of the binary and immediately
executes it. On Linux a concurrently forking test thread holds that write descriptor open
between its `fork` and its `exec`, and every other thread's `execve` fails for that window.
It scales with how many tests fork at once — rare locally, likely on a loaded CI runner.
macOS does not enforce it at all. Kento-binary spawns now retry.

A third was caught by a hardening assertion the same hour it was written: `assert!(!git(merge))`
only says the merge failed. On Linux it failed at the committer identity rather than at the
conflict, leaving a clean index, and the test would have gone green having exercised nothing.
The general `git()` helper now passes an identity, as `commit()` always did.

## The 9 remaining survivors

All classified in `docs/kento-equivalent-mutants.md`, each with an argument about behaviour
rather than about difficulty.

**Seven are proven equivalent** — no input can distinguish mutant from original, so no test
can ever kill them, and counting them as failures makes 100% unreachable:

| Site | Why it cannot be observed |
| --- | --- |
| `install.rs:366` | Bypassing the guard hits `read_to_string`, which fails with the identical message |
| `app.rs:412` | The boolean is read only where a short-circuit has already made the condition false |
| `app.rs:424` | Produced on an error branch whose same failing call re-runs and returns first |
| `toolchain.rs:43` | `getcwd` never returns a symlink, so the two branches cannot differ |
| `lint.rs:604` | `unwrap_or` behind a bounds check that guarantees `Some` |
| `lint.rs:607` | Widens a predicate; every newly admitted byte is rejected one line later |
| `lint.rs:226` | Steps onto a newline, and no rule reads the mask at a newline |

**Two are unreachable in practice and explicitly NOT claimed equivalent.** `install.rs:484`
and `:709` are cleanup-of-cleanup paths, reachable only under a concurrent `install` or a
filesystem where a write succeeds and its matching removal fails. They are unverified lines
in a tool whose job is refusing to clobber files, and they stay on the report until something
can inject a filesystem failure mid-rollback. They were **kept, not deleted** — removing real
defence-in-depth to raise a score is backwards.

## Next moves

1. **CI is a judgement call, not a blocker.** The workflow is written and looks right, but the
   repo has no remote, so it has never executed. Docker already covers the platform matrix by
   hand. The argument for pushing it is the bar itself — *work without human oversight* — and a
   suite that runs only when someone remembers to run it is human oversight. The argument
   against is that there is one developer and a local repo. Decide it deliberately.
2. **Mutate `tests/` as well as `src/`.** The sweep only mutates product code, so a test that
   cannot fail is invisible to it. That is the next real blind spot, and it is the same class
   of problem this whole session was about.
3. **Retire `tools/mutation-gate.py`'s 34 hand-picked mutations** for the mechanical sweep.
   34/34 is honest, unrepresentative, and the number most likely to be quoted as proof.
4. **Re-run the 2026-08-04 stress dimensions** — umask, locale, parallelism, Git config
   carriers — against the 21 new tests. They were verified against the old suite, not this one.
5. **`install.rs:484` and `:709`** need a filesystem-failure injection to close. Everything
   else is done.

## Watch out for

- **A mutation can turn a scanner into an infinite loop.** 24 of the 453 do. The harness kills
  the process group on timeout; without that they spin at 100–300% CPU indefinitely.
  `python3 tools/mutation_sweep.py --status` shows what each shard is running and for how
  long, and `--strays` lists leftovers. Cargo names test binaries `<target>-<hash>`, so `ps`
  alone cannot tell you which shard is which — the status file is the diagnostic.
- **Never run anything else against the repo during a sweep.** A loaded machine can push a
  legitimate run past the harness timeout and record a false `CAUGHT-HANG`.
- **A partial sweep does not extrapolate.** See the 60-vs-102 miss above.
- **Verify the harness before trusting its verdicts.** Two measurement harnesses lied in
  earlier sessions. Today's was validated against the previous one's recorded verdicts before
  a single number from it was believed.

## Running things

```sh
cargo test                                            # 71 tests
python3 tools/mutation_sweep.py 0 453 10              # full sweep, 10 shards
python3 tools/mutation_sweep.py --status              # what each shard is doing
python3 tools/mutation_recheck.py 47,67,72 4          # did my new test kill these?
python3 tools/mutation_recheck.py sweep-0-453.jsonl 8 # re-check a sweep's survivors
docker run --rm -v "$PWD":/src:ro \
  -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97 sh /s.sh          # Debian, glibc
docker run --rm -v "$PWD":/src:ro \
  -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97-alpine sh /s.sh   # Alpine, musl
```

The Linux runner copies the repo rather than mounting it writable, so a container cannot
leave root-owned files in the tree, and runs as a non-root user — `lock_directory` and
`lock_file` *panic* rather than skip when mode bits are not enforced, so a root run fails the
very tests that depend on a denied write.

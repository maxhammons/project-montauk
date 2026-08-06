# Resolution of the done audits — 2026-08-05

Every issue the three audits in this directory raised, what closed it, and how
the closure was verified. Fixes are in commit `5b81a49`; the sweep artifact is
`docs/kento-mutation-sweep-2026-08-05.jsonl`, produced against that commit.

## Blockers

### CI has never executed → CLOSED

The repository now lives at `https://github.com/fev-test/kento` (private).
Run `31059705212` — the first CI execution ever — is green end to end:
`test (ubuntu-24.04)`, `test (macos-15)`, and `sensitivity` all passed.

The user-account remote was tried first and Actions is disabled there by
enterprise policy; the `fev-test` organization allows it. Pushes now trigger
the suite on both declared platforms with no human in the loop.

### The sensitivity gate failed at HEAD → CLOSED

The "app: leave the merged report unsorted" case now names the current
adjacency (`shell_checks` + `sort`), and a new "app: skip ShellCheck entirely"
case pins the surface whose introduction broke the old snippet. Verified two
ways: `python3 tools/mutation-gate.py` locally — **35/35 caught, exit 0** —
and the same command green in CI's sensitivity job.

### The `install.rs:367` FIFO survivor was killable → CLOSED

`uninstall_refuses_a_fifo_hook_state_record_without_hanging` plants a FIFO
among the hook state records and runs `uninstall` under a 10-second deadline.
Verified in both directions: the test passes on current code, and with the
`||`→`&&` mutant applied by hand it fails in 10.4s. The full sweep confirms
the site is now CAUGHT. `docs/kento-equivalent-mutants.md` moves the entry to
"closed" and records why the original equivalence argument was wrong.

## High

### The sweep was not an enforceable gate → CLOSED

`tools/mutation_sweep.py` now: derives its stop index from the current
population (the `453` constant had silently dropped 61 sites); exits nonzero
for survivors not in `tools/equivalent-mutants.txt`, for `ERROR(...)` records,
for missing records, and for stray test binaries; and warns about stale
allowlist entries. `tools/mutation_recheck.py` applies the same verdict rule.
Both warm each fresh worktree before mutating — previously a cold build inside
the mutant's timeout was scored CAUGHT-HANG, a false kill.

Full re-run at `5b81a49`: **514 sites, 473/480 viable caught = 98.5%, 34
uncompilable, 7 survivors — every one a documented equivalent — exit 0.**

CI runs the sweep weekly and on `workflow_dispatch`, so score currency no
longer depends on anyone remembering. The job is proven, not just written:
its first execution failed on a real defect — concurrent shards racing
rustup's toolchain install on a fresh runner, caught loudly by the new exit
discipline — and after the fix (serial provisioning), run `31061218921`
reproduced the local result exactly on a cold CI runner: 473/480, the same
seven documented equivalents, zero strays, exit 0, in 25 minutes.

### The tests were not tested → NARROWED, honestly not closed

The gate that was ten commits stale now runs on every push, which is what
caught-nothing-since-`7caba1b` needed. The sweep's own failure modes now fail
its exit status. What remains true: nothing mutates the tests themselves or
the harness scripts, and `docs/kento-equivalent-mutants.md` now states the
operator-set limitation wherever the score is quoted.

### Maintenance had no integration coverage → CLOSED

Six new tests: the `maintenance bogus` usage error; `kento:maintenance` in the
installed-alias assertion; and four end-to-end runs over a fake rustup on
`PATH` — no pin, current pin, upgrade kept, upgrade reverted (exit 1, pin
restored byte for byte). All hermetic, no network. Writing them exposed a real
bug: `newer_stable()` matched only lowercase `"update available"`, and rustup
has shipped both casings — an update could be reported as "already the newest
stable". Parsing is now case-insensitive, with both casings unit-tested.

## Open issues from the first audit

### `kento maintenance` edits the repository it is run in → DECIDED: document loudly

The behaviour is the feature — it is how any repository's pin is brought
forward — and it already reverts on failure and skips unpinned repositories.
The README now states in bold that it edits the repository it is run in, and
names the one file it ever writes.

### The staleness note's advice → CLOSED

The note now reads "`kento maintenance` moves this repository's pin forward" —
it names the side effect, so a bystander in a foreign checkout knows what the
command would edit. Pinned by a unit test.

### 230s on a shell-heavy repository → DECIDED: publish the number

Documented in the README's shell section with the measurements: ShellCheck is
220 of the 230 seconds, the per-file agent workflow is unaffected, and
parallelizing would add concurrent surface to a tool whose value is being
trustable. Not built.

## Medium

### CI reproducibility → CLOSED to the extent possible

Runner images pinned to versioned labels (`ubuntu-24.04`, `macos-15`),
`actions/checkout` pinned to a commit SHA, ShellCheck installed on macOS
rather than assumed, and the workflow comment now says exactly what still
floats (the image patch level and its ShellCheck build, with the version
recorded in every run's log).

### No sweep artifact proved score currency → CLOSED

`docs/kento-mutation-sweep-2026-08-05.jsonl`: all 514 records at `5b81a49`,
committed. The weekly CI sweep keeps it from being the last one.

## Not addressed, on purpose

- SIGKILL-leaked workspaces: hygiene only, self-describing names, nothing
  accumulates across clean runs.
- `linux-suite.sh` needing the network for ShellCheck: the product needs no
  network; its cross-platform verification harness does. Documented here,
  unchanged.

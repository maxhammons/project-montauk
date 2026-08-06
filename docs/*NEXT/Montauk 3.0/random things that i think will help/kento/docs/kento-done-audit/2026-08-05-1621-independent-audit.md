# Is Kento done? — independent audit, 2026-08-05 16:21

The bar:

> "Done" = these tests are bulletproof. they work all the time. there are no
> errors in them. they work without human oversight. They can be trusted
> completely.

**Verdict: NOT done.** Two blockers — one carried, one new. The new one is an
error *inside the test tooling itself*, at HEAD, today: `tools/mutation-gate.py`
exits 1 on a clean checkout, and the CI workflow that runs it would fail its
first-ever run. Nothing in this audit edited a file; every number below was
re-measured in this session, not inherited from `kento-done-audit.md`.

## What was re-verified today (all green)

| Check | Result | How measured |
| --- | --- | --- |
| `cargo fmt --check` | clean | ran it |
| `cargo clippy --locked --all-targets -- -D warnings` | clean | ran it |
| Debug suite | 82/82, **4 consecutive runs, 0 flakes** | `cargo test --locked` ×4 |
| Release suite | 82/82 | `cargo test --locked --release` |
| Release, single-threaded | 82/82 (462s) | `-- --test-threads=1` |
| Release under `umask 077` | 82/82 | `umask 077 && cargo test` |
| Self-lint | exit 0 | `cargo run --release -- all --format text` |
| Debian 13 / glibc | 82/82, self-lint exit 0 | `tools/linux-suite.sh` on `rust:1.97` |
| Alpine / musl | 82/82, self-lint exit 0 | `tools/linux-suite.sh` on `rust:1.97-alpine` |
| Mutation-site enumeration | 514 sites, matching the prior sweep's `0 514` range | drove `mutations()` from `tools/mutation_sweep.py` |
| Workspace cleanup | 0 dirs leaked across today's 5 suite runs | counted `target/kento-integration-*` before/after |
| Time bombs | none found | no test asserts empty stderr, so the 90-day staleness note cannot break the suite; the threshold is tested at fixed ages (`staleness_line(91)`), never against the wall clock |

The suite itself is in good shape: hermetic workspaces (pid + nanos + counter
naming; `HOME` redirected; nine Git env carriers scrubbed; per-workspace
binary copy; workspace-local `CARGO_TARGET_DIR`), a Drop guard that unlocks
permissions before removal, ETXTBSY retry on Linux, and real `.git` markers so
no test can resolve to this checkout.

## BLOCKER 1 (new): the sensitivity gate is broken at HEAD

`tools/mutation-gate.py` case **"app: leave the merged report unsorted"**
targets the snippet:

```rust
    diagnostics.extend(toolchain::rust_checks(root, &rust)?);
    diagnostics.sort();
```

Commit `7caba1b` (ShellCheck integration) inserted
`diagnostics.extend(toolchain::shell_checks(root, &shell)?);` between those two
lines. The snippet now appears **0 times** in `src/app.rs`, so the case reports
`AMBIGUOUS(0)` and the gate exits 1 — by design, as its own docstring says.

Verified statically by extracting all 34 `CASES` and counting occurrences in
current source: 33 match exactly once, 1 matches zero times. Root cause
confirmed with `git show 7caba1b~1:src/app.rs`, where the snippet appears once.

Why this decides the verdict on its own terms:

1. **"There are no errors in them"** — there is an error in the test tooling,
   right now, at HEAD.
2. **The CI workflow would fail its first run.** `.github/workflows/ci.yml`'s
   `sensitivity` job runs exactly this script.
3. **It proves the gate has not been run since `7caba1b`** — ten commits and
   two handoff documents ago. A guard nobody runs is a guard nothing is
   watching, which is the precise failure mode the gate exists to catch, now
   exhibited by the gate itself.

The fix is one snippet update in `CASES` (not made — this audit edits nothing).
The prior handoff's suggestion to retire the 34 hand-picked cases in favor of
the mechanical sweep is also a fix; either way, decide it, then run it.

## BLOCKER 2 (carried): CI has never executed

`git remote -v` is empty. The workflow has never run anywhere. Every green
result above exists because a human chose to run it — which is the definition
of human oversight. Unchanged from the prior audit; cannot be closed from
inside the repository. And Blocker 1 guarantees the first run will be red.

## Open issues (carried, re-confirmed in code today)

1. **`kento maintenance` edits whatever repository it is run in.**
   `app.rs:94` — `maintenance::maintenance(&repository_root(&cwd()))`. Still
   rewrites a foreign repository's `rust-toolchain.toml` (revert-on-failure
   intact, so no corruption — but still surprising).
2. **The staleness note tells foreign repositories to run that command.**
   `app.rs:179` fires for any lint root whose `rust-toolchain.toml` exists;
   the note's advice (`run \`kento maintenance\``) is issue 1's footgun.

## New findings, below blocker level

3. **The maintenance command path is effectively untested and unmeasured.**
   - No integration test invokes `kento maintenance` at all; `maintenance()`,
     `update_stable()`, and `newer_stable()` never execute under test. The
     unit tests cover the pure pieces (`raise_pin`, `staleness_line`,
     `update_summary`, `release_date`, `day_number`, `pinned_channel`) — good,
     and legitimately hard to go further without hitting the network — but the
     orchestration that calls rustup is trusted, not tested.
   - The sweep cannot compensate: `maintenance.rs` holds **6 of 514 mutation
     sites (1.2%)**. The 11 token-swap operators (`&&/||`, `==/!=`,
     comparisons, `true/false`, `+=/-=`) barely apply to it. "100% of what a
     test can kill" is true *within that operator set*; statement deletion,
     return-value replacement, and call-swap mutants were never in the
     population. Worth stating wherever the score is quoted.
   - `reports_every_usage_error_with_its_own_message` omits the maintenance
     usage error despite the name: `kento maintenance bogus` → "maintenance
     takes no arguments", exit 2 (verified by running it) appears in no test.
     `uninstall`'s twin case is tested.
4. **No sweep artifact proves the final sweep ran against HEAD.** The audit
   two commits ago cites `0 514 12`; today's enumeration also yields 514
   sites, and the one src-touching commit since (`2ebe80f`) changed only a
   const list with no mutable tokens — so the claim is *consistent*, but the
   evidence chain is inference, not a log. `/tmp/kento-sweep` is gone;
   `docs/kento-mutation-sweep-partial.log` is explicitly partial. A repo-tracked
   result file (or CI) would close this permanently.
5. **The verification harness needs the network.** `linux-suite.sh` installs
   ShellCheck via `apt-get`/`apk` at container start, and today's Debian run
   downloaded the `clippy` component for 1.97.1. The *product* needs no
   network; its cross-platform verification does. On an offline day the Linux
   half of "bulletproof" cannot be demonstrated.
6. **CI assumes ShellCheck is preinstalled on both runner images**
   (`shellcheck --version` as a bare step, no install). True of
   `ubuntu-latest`; for `macos-latest` it is an assumption that has never been
   exercised — see Blocker 2.
7. **SIGKILL leaks workspaces** (hygiene only). 13 `kento-integration-*` dirs
   in `target/` all timestamp to one killed run (PID 45612, Aug 4 18:09);
   `Drop` cannot run under `kill -9`. Five `kento-discover-*` unit-test
   scratch dirs likewise persist from mutants that panicked mid-test, because
   unit tests clean up on the success path only. Nothing accumulated across
   today's five clean runs. Self-describing names make the dirs easy to sweep.

## What "done" would take, in order

1. Fix (or retire) the broken `mutation-gate.py` case, and make the gate part
   of something that runs without being remembered — which is item 2.
2. Push the repository and read the first CI run end to end. Until CI executes,
   "works without human oversight" is false by construction, whatever the
   local results say.
3. Decide the two carried maintenance-scope issues (restrict, confirm, or
   document loudly).
4. Cover the maintenance orchestration: at minimum the usage error and a
   `maintenance` run against a root with no pin (both networkless); ideally a
   fake-`rustup`-on-PATH test for `update_stable`/`newer_stable` parsing.
5. Track a sweep result artifact in-repo (or run the sweep in CI) so score
   currency is provable rather than inferable.

## How to re-derive everything here

```sh
cargo fmt --check && cargo clippy --locked --all-targets -- -D warnings
cargo test --locked                       # ×4 today, 82/82 each
cargo test --locked --release
cargo test --locked --release -- --test-threads=1
umask 077 && cargo test --locked --release
cargo run --locked --release -- all --format text   # exit 0

docker run --rm -v "$PWD":/src:ro -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97 sh /s.sh
docker run --rm -v "$PWD":/src:ro -v "$PWD/tools/linux-suite.sh":/s.sh:ro rust:1.97-alpine sh /s.sh

# The broken gate case, without mutating anything:
python3 - <<'EOF'
import ast, pathlib
tree = ast.parse(pathlib.Path("tools/mutation-gate.py").read_text())
cases = next(ast.literal_eval(n.value) for n in ast.walk(tree)
             if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "CASES")
for label, path, snippet, _ in cases:
    n = pathlib.Path(path).read_text().count(snippet)
    if n != 1: print(f"BROKEN ({n}x): {label}")
EOF
```

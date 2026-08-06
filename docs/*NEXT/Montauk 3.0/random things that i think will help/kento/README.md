# Kento

Kento is a deterministic, hard pass/fail linter for AI coding agents on macOS and Linux. Its own rules use only the Rust standard library and need no Git or network connection.

It also runs the industry-standard checker for two languages rather than a weaker substitute: rustfmt and Clippy in a Cargo package, and ShellCheck over shell files. A Rust linter that reports clean while Clippy has something to say is not telling you the truth, and the same goes for shell. Those are the only external tools, and each is documented below.

## Use

```sh
kento all [--format jsonl|text] [path ...]
kento rs|py|js|ts|css|html|sh [--format jsonl|text] [path ...]
kento ignore-audit [--format jsonl|text]
kento maintenance
kento install [--no-hook]
kento uninstall
```

| Command | What it does |
| --- | --- |
| `kento all` | Lints every supported language. Add `--staged` to lint the Git index instead of the worktree. |
| `kento rs`/`py`/`js`/`ts`/`css`/`html`/`sh` | Lints one language only. Paths still narrow it further. |
| `kento ignore-audit` | Checks every entry in `.kentoexceptions` without applying it, and reports the ones that no longer hold. |
| `kento maintenance` | Updates the toolchain and moves the pin forward, keeping the new one only if the checks pass. See [Maintenance](#maintenance). |
| `kento install` | Copies the executable to `~/.local/bin`, creates the aliases, and installs the pre-commit hook. `--no-hook` skips the hook. |
| `kento uninstall` | Removes only what `install` created, and refuses anything it cannot prove it owns. |

The installed literal aliases are `kento:all`, `kento:rs`, `kento:py`, `kento:js`, `kento:ts`, `kento:css`, `kento:html`, `kento:sh`, `kento:ignore-audit`, `kento:maintenance`, `kento:install`, and `kento:uninstall`.

With no paths, Kento walks from the nearest ancestor containing `.git`; otherwise it walks the current directory. Explicit files bypass `.kentoignore`; directories and implicit discovery honor it. Kento skips symlinks, `.git`, `.hg`, `.svn`, `node_modules`, `target`, `dist`, `build`, `vendor`, `.venv`, `venv`, `__pycache__`, `coverage`, `*.min.js`, `*.min.css`, and source maps.

Supported inputs are Rust (`.rs`), Python (`.py`), JavaScript (`.js`, `.jsx`), TypeScript (`.ts`, `.tsx`), CSS (`.css`), HTML (`.html`, `.htm`), and shell (`.sh`, `.bash`, `.zsh`, or extensionless files with an sh/bash/zsh shebang).

Findings go to stdout. Errors go to stderr. Exit status is `0` for clean, `1` for findings, and `2` for usage, configuration, I/O, or integration errors.

## Diagnostics

JSON Lines is the default:

```json
{"schema":"kento.diagnostic/v1","rule_id":"KENTO101","path":"src/example.py","line":3,"column":1,"end_line":3,"end_column":8,"message":"bare except catches every exception","help":"Catch a specific exception type instead."}
```

Paths are normalized repository-relative paths and positions are 1-based. Output is sorted by path, line, column, rule, end position, and message. `--format text` provides a readable one-line alternative.

Kento has exactly these rules:

* `KENTO001` — a complete, ordered merge-conflict marker block.
* `KENTO002` — a nonempty file without a final LF.
* `KENTO003` — trailing ASCII spaces or tabs, excluding conservatively recognized literal, heredoc, and HTML raw-text payloads.
* `KENTO101` — a true Python bare `except:`.
* `KENTO102` — Python `== None` or `!= None` comparisons, in either order.
* `KENTO201` — duplicate ASCII-case-insensitive HTML attributes in static start tags.
* `KENTO301` — an unclosed CSS comment outside a string.
* `KENTO401` — a file rustfmt would reformat.
* `KENTO402` — a Clippy or compiler diagnostic, carrying that tool's own wording.
* `KENTO501` — a ShellCheck diagnostic, carrying that tool's own wording and `SC` code.

Kento deliberately has no warning mode, configurable rules, or line-length rule.

## Rust toolchain rules

`KENTO401` and `KENTO402` come from `cargo fmt --check` and `cargo clippy --all-targets`. Running them is deliberate: rustfmt and Clippy are the industry-standard Rust checks, and a Rust linter that reports clean while Clippy has something to say is not telling you the truth. The first run pays for the build; later runs replay cached diagnostics and are fast.

They run only when the repository root holds a `Cargo.toml` and the run discovered at least one Rust file. Every other repository, and every non-Rust run, is untouched and still needs no toolchain. When the tools are needed but cannot run, Kento exits `2` with their failure rather than reporting clean.

Cargo always reports on the whole package, so Kento keeps only findings for the Rust files that run actually linted. `kento rs src/one.rs` stays about `src/one.rs`, `.kentoignore` still applies, and the pre-commit hook stays about the files being committed. Both tools read the worktree, so under `--staged` they see the files on disk rather than the index blobs Kento lints itself.

Neither rule is accepted in `.kentoexceptions`, because `kento ignore-audit` validates exceptions offline and cannot re-run an external tool. Suppress these the way Rust already does, with `#[rustfmt::skip]` or `#[allow(..)]` — which also records the decision where the code is.

## Shell rules

`KENTO501` comes from ShellCheck, which is the industry-standard shell checker and finds the hazards Kento's own three rules cannot: unquoted expansions, word splitting, tests that never fail.

It runs whenever a run discovers a shell file. Unlike the Rust rules there is no manifest to gate on, because a repository does not declare itself a shell project — so a repository holding one script needs ShellCheck the same way a Cargo package needs Cargo. If it is not installed, Kento exits `2` rather than reporting clean on a file nobody checked.

zsh is not sent to it. ShellCheck analyses sh, bash, dash and ksh, and answers "ShellCheck only supports…" for anything else — as a finding rather than an error, so handing it zsh would bury the report under one refusal per file. Measured across 27 real repositories, 29% of the shell files Kento discovers are zsh. Those files still get Kento's own rules.

Install it with `brew install shellcheck` or `apt-get install shellcheck`.

ShellCheck sets the cost of a shell-heavy run. It is invoked once per run and
is single-threaded, so a whole-repository lint pays for every shell file at
once: measured on a 307-script repository (`nvm`), `kento all` takes 230
seconds, of which ShellCheck alone is 220 — Kento's own share is about 2. The
per-file workflow this tool exists for is unaffected (`kento sh file.sh`
matches `shellcheck file.sh` to within 0.1s; a 1 KB script is 0.02s), and a
3,394-file repository with no shell lints in 0.7s. The number is documented
rather than parallelized away: sharding ShellCheck would add concurrent,
hard-to-test surface to a tool whose whole value is that its results can be
trusted.

## Maintenance

`rust-toolchain.toml` pins the Rust version so that a new release cannot turn an unattended run red on a day nobody touched the code. The cost of a pin is that it rots: Clippy falls behind, and eventually a package Kento is asked to lint needs a newer compiler than the machine has — which Kento reports as an error, correctly, rather than pretending to have checked it.

`kento maintenance` is the deliberate upgrade:

```sh
kento maintenance
```

**It edits the repository it is run in.** The pin it raises is the
`rust-toolchain.toml` of the nearest ancestor holding `.git` — the same root
every lint resolves — so run it in someone else's checkout and it is their pin
it moves. That is the intended way to bring any repository's pin forward, but
it is an edit, not a report: a rejected toolchain is reverted byte for byte,
a repository without a pin is left untouched, and the one file it ever writes
is that pin.

1. Reports the version of every tool Kento depends on.
2. Updates the default `stable` toolchain. This is the half that matters for **other** repositories: when Kento lints somebody else's Cargo package, that package's toolchain governs, and a stale `stable` is what makes Kento refuse a package needing a newer compiler.
3. Raises the pin in `rust-toolchain.toml` if a newer stable exists, then runs `cargo fmt --check` and `cargo clippy -- -D warnings`.
4. Keeps the new pin if they pass. **Reverts it and says exactly what failed if they do not**, so a bad release is rejected rather than inherited.

Exit status is `0` when nothing needed doing or the upgrade held, `1` when an upgrade was available but failed its checks and was reverted. Run `cargo test` afterwards before committing the new pin — `maintenance` verifies the checks Kento is responsible for, not your test suite.

### How often

**Every three weeks**, and any time Kento refuses a repository because its toolchain is too old.

Rust ships every six weeks, so a three-week habit checks twice per release and is usually a no-op that takes seconds. That is the point: the cost of running it too often is nothing, and the cost of running it too rarely is a pin far enough behind that raising it becomes a job rather than a command.

You do not have to remember. When the pinned compiler is more than 90 days old — about two missed releases — every Rust run prints one line to stderr:

```text
kento: pinned Rust is 104 days old (1.95.0 (59807616e 2026-04-14)); `kento maintenance` moves this repository's pin forward
```

That note is a note. It goes to stderr so it can never contaminate the diagnostics on stdout, and it never changes the exit status: a linter that refused to lint because of its own age would fail for a reason that has nothing to do with the code in front of it, at the least convenient moment. Nothing is counted and nothing is stored on disk — the age comes from the date `rustc --version` prints, so there is no state to grow stale, corrupt, or clean up.

## Ignore and exceptions

The root `.kentoignore` accepts one normalized repository-relative path per line:

```text
# comments and blank lines are accepted
generated/client.py
generated/
```

An entry without a trailing slash is an exact path. An entry ending in `/` ignores that directory prefix. Absolute paths, `.`/`..` segments, globs, negation, and wildcards are errors.

The root `.kentoexceptions` suppresses one exact rule/path pair during normal lint:

```text
KENTO102 legacy/check.py compatibility with a vendor API
```

Its syntax is `RULE_ID repo/relative/path required free-form reason`. Blank lines and comments are allowed. Kento rejects malformed UTF-8, malformed rows, duplicate rule/path pairs, unknown rules, absolute paths, `.`/`..` paths, and wildcard paths. `kento ignore-audit` checks every exception without applying it and emits `KENTO901` when the file is missing, the rule cannot apply to its file type, or the finding is no longer present.

## Git hook integration

`kento install` copies the current executable to `~/.local/bin/kento`, creates the literal aliases, and warns if that bin directory is not on `PATH`. By default it also installs a pre-commit block in the current repository. Use `--no-hook` to install only the executable and aliases.

Hook installation requires Git. Kento refuses a nonempty `core.hooksPath`, an existing hook without an sh/bash/zsh-compatible shebang, or malformed/duplicate Kento markers. It inserts its exact marked block immediately after the shebang, preserving existing hook content and mode, and records every managed hook under `~/.local/share/kento`. Installation also records a content fingerprint and refuses to replace commands it cannot prove it owns.

The hook runs `kento all --staged`. Staged mode reads NUL-delimited Git status and index metadata, lints only staged added/copied/modified/renamed regular files from index blob content, and reads `.kentoignore` and `.kentoexceptions` from the index rather than the worktree. It therefore validates what will be committed.

Neither command can wedge itself. The manifest that proves Kento owns a command is written only once all of them exist, so an install that fails in between undoes what it made: commands it created are removed, and a binary it replaced is put back. An uninstall is resumable — it deletes the binary before the manifest, and a manifest describing a binary that is already gone lets the operation finish rather than refusing forever. Either way the fix is to run the command again, never to delete files by hand.

`kento uninstall` preflights every recorded hook, command, and state entry before changing anything. It refuses altered, missing, duplicated, or malformed managed blocks/state, and refuses to remove a binary or alias that no longer matches its ownership record. Otherwise it removes only exact Kento blocks, preserves other hook content and modes, removes a hook only when it consists solely of Kento's created shebang and block, then removes managed aliases, binary, and state.

## How this repository verifies itself

Trust in the tests is the point of the tool, so the tests are themselves gated,
and every gate's exit status is its verdict — nothing here is a report someone
has to remember to read.

**On every push**, CI runs on `ubuntu-24.04` and `macos-15`: `cargo fmt
--check`, `clippy -D warnings`, the suite in debug, release, single-threaded,
and under `umask 077`, and Kento linting its own checkout. A separate
`sensitivity` job runs `tools/mutation-gate.py`: 35 hand-aimed mutations that
each break one guard on purpose, failing if the suite stays green. Editing code
a case names makes that case fail `AMBIGUOUS` — the prompt to update it, which
is how the gate polices its own staleness.

**Weekly, and on demand** (`workflow_dispatch`), CI runs the full mechanical
sweep: `tools/mutation_sweep.py` applies every single-token mutation to every
product file (514 sites at last count) and exits nonzero unless each survivor
appears in `tools/equivalent-mutants.txt` — and every entry there must carry a
written argument in `docs/kento-equivalent-mutants.md`. Missing records,
harness errors, and stray test processes also fail it. Sweep results are
committed as `docs/kento-mutation-sweep-<date>.jsonl`.

Locally, the same commands, in rising cost:

```sh
cargo test                                # the suite, seconds
python3 tools/mutation_recheck.py 47,67 4 # did my new test kill these sites
python3 tools/mutation-gate.py           # the 35 aimed cases, ~30 minutes
python3 tools/mutation_sweep.py          # every site, ~35 minutes on 12 cores
```

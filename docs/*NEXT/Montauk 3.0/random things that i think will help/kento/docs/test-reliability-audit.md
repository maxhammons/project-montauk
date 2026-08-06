# Kento Test Reliability Audit

> **Historical (2026-08-04).** Every finding below was fixed the same week;
> the closure record is `kento-done-audit/2026-08-05-resolution.md`.

**Date:** 2026-08-04  
**Verdict:** FAIL - the test suite is not yet bulletproof.

## Findings

| Severity | Finding | Evidence |
| --- | --- | --- |
| High | Git isolation is incomplete. | Injecting `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0=core.hooksPath`, and `GIT_CONFIG_VALUE_0=...` caused 9 of 19 integration tests to fail. `tests/integration.rs:69-77` does not clear inline Git configuration. |
| High | Concurrent test invocations are flaky. | Four-way same-target `cargo test --release` stress produced 5 failures in 158 suites. Tests intermittently could not execute or read `target/release/kento`, referenced through `CARGO_BIN_EXE_kento` at `tests/integration.rs:62-63`. |
| High | Installation failure is non-atomic. | Denying writes to the installation state directory returned exit code 2 but left the binary and all 11 aliases installed. A retry then refused the 12 commands as unmanaged. Commands are created before `write_manifest` at `src/install.rs:641-655`. |
| High | Uninstallation failure is non-atomic. | Denying removal of the installation manifest returned exit code 2 after aliases and the binary had already been deleted. The retained manifest then made retry impossible. See `src/install.rs:783-793`. |
| Medium | Extensionless shell detection accepts interpreter prefixes. | `#!/usr/bin/env bashful` was treated as a Bash shebang and linted. Detection uses `starts_with` at `src/types.rs:42-47`. |
| Medium | CI is not fully reproducible. | `.github/workflows/ci.yml:17-21` does not pin the Rust toolchain, uses `actions/checkout@v4`, and runs Cargo without `--locked`. Mutation and coverage checks are not automated. |

## Passing Evidence

- All 31 declared tests passed in normal debug and release runs.
- `cargo fmt --check`, Clippy with warnings denied, Cargo metadata, documentation, release build, self-lint, and exception audit passed.
- 30 serialized release suites passed across umasks `000`, `027`, and `077`.
- Missing Git failed loudly as intended.
- A locale-varied, single-threaded run passed.
- A 701-file random-byte corpus produced valid, sorted JSONL without crashes.
- All 20 corpus runs produced byte-for-byte identical output.
- All 14 non-generated repository files passed UTF-8, NUL, final-LF, trailing-whitespace, TOML, YAML, and ignore-rule checks.

## Limitations

- Linux execution was not available locally because no Linux runner or Docker daemon was running.
- The repository had no commits, so the GitHub Actions workflow had not run remotely.
- Mutation and coverage tools were unavailable, and the repository does not contain an automated equivalent.

The audit itself did not modify product or test files. Their aggregate content hash was unchanged before and after testing.

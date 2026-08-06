use crate::types::Diagnostic;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use std::process::Command;

/// Runs rustfmt and Clippy over the repository's Cargo package and reports what
/// they find as Kento diagnostics.
///
/// `linted` is the set of Rust files this run discovered. Cargo always reports on
/// the whole package, so findings outside that set — a file `.kentoignore`
/// excludes, a path the caller did not name, a file not staged — are dropped.
/// That keeps `kento rs src/one.rs` about `src/one.rs` and keeps the pre-commit
/// hook about what is being committed.
///
/// Both tools read the worktree. In `--staged` mode they therefore see the files
/// on disk rather than the index blobs Kento itself lints.
///
/// The order is the caller's business: it merges these with Kento's own findings
/// and sorts the whole report.
pub fn rust_checks(root: &Path, linted: &BTreeSet<String>) -> Result<Vec<Diagnostic>, String> {
    if linted.is_empty() || !root.join("Cargo.toml").is_file() {
        return Ok(Vec::new());
    }
    let roots = Roots::new(root);
    let mut diagnostics = formatting(root, &roots, linted)?;
    diagnostics.extend(lints(root, &roots, linted)?);
    Ok(diagnostics)
}

/// Runs ShellCheck over the shell files this run discovered and reports what it
/// finds as Kento diagnostics.
///
/// Unlike the Rust rules there is no manifest to gate on: a repository does not
/// declare itself a shell project. The gate is the files themselves, so a
/// repository holding one script needs ShellCheck the same way a Cargo package
/// needs Cargo. Reporting clean on a script nobody checked would be the lie this
/// whole tool exists to avoid.
///
/// ShellCheck analyses sh, bash, dash and ksh, and refuses zsh — as a finding
/// rather than an error, so passing zsh files would bury the report under one
/// "ShellCheck only supports…" per file. On a real corpus that is 29% of what
/// Kento calls shell, so those files are not sent.
///
/// Every finding becomes `KENTO501` carrying ShellCheck's own wording and code,
/// the way Clippy's carry its own.
pub fn shell_checks(root: &Path, linted: &BTreeSet<String>) -> Result<Vec<Diagnostic>, String> {
    let supported: Vec<&String> = linted
        .iter()
        .filter(|path| !names_zsh(&root.join(path)))
        .collect();
    if supported.is_empty() {
        return Ok(Vec::new());
    }
    let mut arguments = vec!["--format=gcc", "--"];
    arguments.extend(supported.iter().map(|path| path.as_str()));
    let output = Command::new("shellcheck")
        .current_dir(root)
        .args(&arguments)
        .output()
        .map_err(|error| format!("ShellCheck is required for shell checks: {error}"))?;
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));

    let mut diagnostics = Vec::new();
    let mut parsed = 0;
    for line in text.lines() {
        let Some((path, number, column, message)) = short_diagnostic(line) else {
            continue;
        };
        parsed += 1;
        // ShellCheck is given repository-relative paths and echoes them back, so
        // these match `linted` without the resolving the Rust rules need.
        if let Some(path) = linted.get(path) {
            diagnostics.push(Diagnostic {
                rule_id: "KENTO501",
                path: path.clone(),
                line: number,
                column,
                end_line: number,
                end_column: column,
                message: message.to_owned(),
                help: "Fix the finding, or silence it with a `# shellcheck disable` directive."
                    .to_owned(),
            });
        }
    }
    // Exit 0 is clean and exit 1 is findings; both mean it looked. Anything else
    // — a file it cannot open, an argument it does not understand — means it
    // never got as far as checking, and reporting clean there would be a lie.
    let looked = matches!(output.status.code(), Some(0 | 1));
    confirm("shellcheck", looked, parsed, &text)?;
    Ok(diagnostics)
}

/// Whether a shell file is zsh, by extension or by shebang. ShellCheck does not
/// analyse zsh and says so once per file, which is noise rather than a finding.
fn names_zsh(path: &Path) -> bool {
    if path.extension().is_some_and(|extension| extension == "zsh") {
        return true;
    }
    let Ok(bytes) = fs::read(path) else {
        return false;
    };
    let first = bytes
        .split(|byte| *byte == b'\n')
        .next()
        .unwrap_or_default();
    first.starts_with(b"#!") && first.windows(3).any(|window| window == b"zsh")
}

/// The repository root as Kento knows it and as the filesystem resolves it. A
/// checkout reached through a symlink — `/tmp` on macOS is one — makes the tools
/// report the resolved path, which the unresolved root cannot strip.
struct Roots {
    declared: std::path::PathBuf,
    resolved: Option<std::path::PathBuf>,
}

impl Roots {
    fn new(root: &Path) -> Self {
        let resolved = fs::canonicalize(root)
            .ok()
            .filter(|resolved| resolved != root);
        Self {
            declared: root.to_path_buf(),
            resolved,
        }
    }

    /// The repository-relative form of a path a tool reported, or `None` when it
    /// is not one of the files this run linted.
    fn relative<'a>(&self, reported: &str, linted: &'a BTreeSet<String>) -> Option<&'a String> {
        let path = Path::new(reported);
        let relative = self
            .resolved
            .as_deref()
            .and_then(|resolved| path.strip_prefix(resolved).ok())
            .or_else(|| path.strip_prefix(&self.declared).ok())
            .unwrap_or(path);
        linted.get(relative.to_string_lossy().as_ref())
    }
}

fn cargo(root: &Path, arguments: &[&str]) -> Result<(bool, String), String> {
    let output = Command::new("cargo")
        .current_dir(root)
        .args(arguments)
        .output()
        .map_err(|error| format!("Cargo is required for Rust checks: {error}"))?;
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));
    Ok((output.status.success(), text))
}

/// Confirms the tool got as far as checking. A non-zero exit with no findings at
/// all means it did not — a manifest it cannot read, a missing component, a
/// package that does not build — and reporting clean there would turn a broken
/// toolchain into a passing lint.
///
/// Both tools go through this one check so there is one place to get it right.
fn confirm(tool: &str, succeeded: bool, parsed: usize, text: &str) -> Result<(), String> {
    if succeeded || parsed > 0 {
        return Ok(());
    }
    let detail = text
        .lines()
        .rev()
        .find(|line| !line.trim().is_empty())
        .unwrap_or("no output")
        .trim();
    Err(format!("{tool} failed: {detail}"))
}

fn formatting(
    root: &Path,
    roots: &Roots,
    linted: &BTreeSet<String>,
) -> Result<Vec<Diagnostic>, String> {
    let (succeeded, text) = cargo(root, &["fmt", "--check"])?;
    let mut diagnostics = Vec::new();
    let mut parsed = 0;
    for line in text.lines() {
        // `Diff in <path>:<line>:` heads each hunk rustfmt would rewrite.
        let Some(rest) = line.strip_prefix("Diff in ") else {
            continue;
        };
        let Some((path, number)) = rest.trim_end_matches(':').rsplit_once(':') else {
            continue;
        };
        let Ok(number) = number.parse::<usize>() else {
            continue;
        };
        parsed += 1;
        if let Some(path) = roots.relative(path, linted) {
            diagnostics.push(Diagnostic {
                rule_id: "KENTO401",
                path: path.clone(),
                line: number,
                column: 1,
                end_line: number,
                end_column: 1,
                message: "rustfmt would reformat this file".to_owned(),
                help: "Run `cargo fmt`.".to_owned(),
            });
        }
    }
    confirm("cargo fmt", succeeded, parsed, &text)?;
    Ok(diagnostics)
}

fn lints(root: &Path, roots: &Roots, linted: &BTreeSet<String>) -> Result<Vec<Diagnostic>, String> {
    let (succeeded, text) = cargo(
        root,
        &["clippy", "--all-targets", "--message-format", "short"],
    )?;
    let mut diagnostics = Vec::new();
    let mut parsed = 0;
    for line in text.lines() {
        let Some((path, number, column, message)) = short_diagnostic(line) else {
            continue;
        };
        parsed += 1;
        if let Some(path) = roots.relative(path, linted) {
            diagnostics.push(Diagnostic {
                rule_id: "KENTO402",
                path: path.clone(),
                line: number,
                column,
                end_line: number,
                end_column: column,
                message: message.to_owned(),
                help: "Fix the finding, or allow it explicitly with `#[allow(..)]`.".to_owned(),
            });
        }
    }
    confirm("cargo clippy", succeeded, parsed, &text)?;
    Ok(diagnostics)
}

/// Splits one `--message-format short` line: `path:line:column: level: message`.
/// Cargo's own progress and summary lines have no `line:column` and are skipped.
fn short_diagnostic(line: &str) -> Option<(&str, usize, usize, &str)> {
    let mut fields = line.splitn(4, ':');
    let path = fields.next()?;
    let number = fields.next()?.parse().ok()?;
    let column = fields.next()?.parse().ok()?;
    let message = fields.next()?.trim();
    (!path.is_empty() && !message.is_empty()).then_some((path, number, column, message))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_only_positioned_diagnostics_from_short_output() {
        assert_eq!(
            short_diagnostic("src/lib.rs:1:13: warning: writing `&Vec` instead of `&[_]`"),
            Some((
                "src/lib.rs",
                1,
                13,
                "warning: writing `&Vec` instead of `&[_]`"
            ))
        );
        assert_eq!(
            short_diagnostic("src/lib.rs:2:21: error[E0308]: mismatched types"),
            Some(("src/lib.rs", 2, 21, "error[E0308]: mismatched types"))
        );
        // Cargo's progress and summary lines carry no position.
        assert_eq!(
            short_diagnostic("    Checking kento v0.1.0 (/tmp/kento)"),
            None
        );
        assert_eq!(
            short_diagnostic("warning: `kento` (lib) generated 1 warning"),
            None
        );
        assert_eq!(short_diagnostic("error: could not compile `kento`"), None);
        assert_eq!(short_diagnostic(""), None);
        assert_eq!(short_diagnostic("src/lib.rs:1:13: "), None);
    }

    #[test]
    fn keeps_tool_paths_only_when_this_run_linted_them() {
        let root = Path::new("/repository");
        let roots = Roots {
            declared: root.to_path_buf(),
            resolved: None,
        };
        let linted: BTreeSet<String> = ["src/lib.rs".to_owned()].into_iter().collect();
        // rustfmt reports absolute paths, Clippy relative ones; both resolve.
        assert_eq!(
            roots.relative("/repository/src/lib.rs", &linted),
            Some(&"src/lib.rs".to_owned())
        );
        assert_eq!(
            roots.relative("src/lib.rs", &linted),
            Some(&"src/lib.rs".to_owned())
        );
        // A file outside this run is not this run's business.
        assert_eq!(roots.relative("/repository/src/other.rs", &linted), None);
        assert_eq!(roots.relative("/elsewhere/src/lib.rs", &linted), None);
    }

    #[test]
    fn a_symlinked_checkout_still_matches_reported_paths() {
        let roots = Roots {
            declared: Path::new("/tmp/repository").to_path_buf(),
            resolved: Some(Path::new("/private/tmp/repository").to_path_buf()),
        };
        let linted: BTreeSet<String> = ["src/lib.rs".to_owned()].into_iter().collect();
        assert_eq!(
            roots.relative("/private/tmp/repository/src/lib.rs", &linted),
            Some(&"src/lib.rs".to_owned())
        );
        assert_eq!(
            roots.relative("/tmp/repository/src/lib.rs", &linted),
            Some(&"src/lib.rs".to_owned())
        );
    }

    #[test]
    fn a_tool_that_never_checked_anything_is_a_failure_not_a_clean_result() {
        // Failed, and never got as far as a finding: report it.
        assert_eq!(
            confirm(
                "cargo clippy",
                false,
                0,
                "error: no override and no default toolchain\n"
            ),
            Err("cargo clippy failed: error: no override and no default toolchain".to_owned())
        );
        assert_eq!(
            confirm("cargo fmt", false, 0, ""),
            Err("cargo fmt failed: no output".to_owned())
        );
        // Failed *because* of what it found — `cargo fmt --check` exits non-zero on
        // any diff — so the findings are the answer, not an error.
        assert_eq!(confirm("cargo fmt", false, 3, "Diff in x:1:\n"), Ok(()));
        // Succeeded with nothing to say.
        assert_eq!(confirm("cargo clippy", true, 0, ""), Ok(()));
    }

    /// The gate that keeps Kento from checking a package it is not rooted in.
    /// Cargo searches ancestors for a manifest, so without it a run in any
    /// directory nested inside some other Cargo project would quietly check that
    /// project instead.
    #[test]
    fn a_root_without_a_manifest_runs_no_tools() {
        // Deliberately outside any package: had this shelled out, Cargo would find
        // no manifest in any parent and fail, so `Ok(empty)` is the proof it never
        // ran. Under `target/` it would find Kento's own manifest and pass
        // vacuously instead.
        let root = std::env::temp_dir().join(format!(
            "kento-toolchain-gate-{}-{:?}",
            std::process::id(),
            std::thread::current().id()
        ));
        fs::create_dir_all(&root).expect("directory");
        let linted: BTreeSet<String> = ["src/lib.rs".to_owned()].into_iter().collect();

        let result = rust_checks(&root, &linted);

        let _ = fs::remove_dir_all(&root);
        assert_eq!(result.expect("no manifest means no run"), Vec::new());
        // Nothing to lint means nothing to check, manifest or not.
        assert_eq!(
            rust_checks(Path::new("/"), &BTreeSet::new()).expect("nothing linted"),
            Vec::new()
        );
    }
}

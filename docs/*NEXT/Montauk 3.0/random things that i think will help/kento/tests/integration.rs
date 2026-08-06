use std::ffi::OsStr;
use std::fs;
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// Removes a workspace even when a test panics, restoring locked permissions
/// first so a denied directory can never leave `target` unremovable.
struct Cleanup {
    base: PathBuf,
}

impl Drop for Cleanup {
    fn drop(&mut self) {
        unlock_tree(&self.base);
        let _ = fs::remove_dir_all(&self.base);
    }
}

fn unlock_tree(path: &Path) {
    let Ok(metadata) = fs::symlink_metadata(path) else {
        return;
    };
    if metadata.file_type().is_symlink() {
        return;
    }
    if !metadata.is_dir() {
        let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o600));
        return;
    }
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(0o700));
    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            unlock_tree(&entry.path());
        }
    }
}

/// Creates the `.git` marker so no test can accidentally resolve its repository
/// root to the Kento checkout and lint this source tree.
///
/// Three things make the name unique, because two tests sharing a workspace would
/// have one's cleanup delete the other's tree mid-run. The process id separates
/// concurrent test processes. The clock separates repeat runs. The counter
/// separates threads within this process, and is what makes the name unique
/// rather than merely unlikely to collide: the clock here is only microsecond
/// granular, so two threads can read the same value, and nothing otherwise
/// enforces that every caller passes a different label.
fn workspace(label: &str) -> (PathBuf, PathBuf, Cleanup) {
    static SEQUENCE: AtomicUsize = AtomicUsize::new(0);
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
    let process = std::process::id();
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("target")
        .join(format!(
            "kento-integration-{label}-{process}-{unique}-{sequence}"
        ));
    let root = base.join("repository with spaces");
    let home = base.join("home with spaces");
    fs::create_dir_all(&home).expect("home");
    make_repository(&root);
    fs::copy(built_binary(), base.join("kento")).expect("binary copy");
    (root, home, Cleanup { base })
}

/// Makes `root` a repository Git will actually stop at.
///
/// An empty `.git` directory is not one. Git looks for `HEAD`, `objects` and
/// `refs`, and finding none of them it keeps walking *up* — so
/// `git rev-parse --git-path hooks` answers with the nearest real repository
/// above the workspace, which under a test runner is the checkout these tests
/// are running from. A single Kento run that consulted Git for its hook path
/// then wrote a pre-commit hook into the developer's own repository, pointed at
/// a binary in a temporary directory, and every later commit failed.
///
/// These three entries are written rather than shelled out to `git init` so
/// that tests which never touch Git do not acquire a dependency on it.
fn make_repository(root: &Path) {
    fs::create_dir_all(root.join(".git/objects")).expect("objects");
    fs::create_dir_all(root.join(".git/refs")).expect("refs");
    fs::write(root.join(".git/HEAD"), "ref: refs/heads/main\n").expect("HEAD");
}

fn built_binary() -> &'static str {
    env!("CARGO_BIN_EXE_kento")
}

/// The copy of the binary this workspace runs, found from any directory inside
/// it. Concurrent `cargo test` invocations sharing one target directory relink
/// `CARGO_BIN_EXE_kento` in place, and a child executing that file while it is
/// rewritten dies by signal with no exit status at all — a flake that reads as a
/// Kento failure. Nothing rewrites the copy.
fn workspace_binary(inside: &Path) -> PathBuf {
    inside
        .ancestors()
        .find(|ancestor| {
            ancestor
                .file_name()
                .and_then(OsStr::to_str)
                .is_some_and(|name| name.starts_with("kento-integration-"))
        })
        .expect("workspace base")
        .join("kento")
}

/// Isolates a child from the developer's Git configuration. `HOME` alone is not
/// enough: Git also reads `$XDG_CONFIG_HOME/git/config` and `/etc/gitconfig`, so
/// a global `core.hooksPath` would otherwise reroute the code under test.
///
/// Inline configuration carriers matter just as much. `GIT_CONFIG_COUNT` and
/// `GIT_CONFIG_PARAMETERS` each smuggle a `core.hooksPath` past the two file
/// paths above, and `GIT_COMMON_DIR` and `GIT_TEMPLATE_DIR` relocate the hooks
/// directory outright. `git rebase --exec`, `git bisect run`, and wrapper tools
/// set them, which is exactly where a false failure costs the most trust.
fn hermetic(program: &OsStr) -> Command {
    let mut command = Command::new(program);
    command
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null")
        .env_remove("XDG_CONFIG_HOME")
        .env_remove("GIT_DIR")
        .env_remove("GIT_WORK_TREE")
        .env_remove("GIT_INDEX_FILE")
        .env_remove("GIT_CONFIG_COUNT")
        .env_remove("GIT_CONFIG_PARAMETERS")
        .env_remove("GIT_COMMON_DIR")
        .env_remove("GIT_TEMPLATE_DIR");
    command
}

/// Runs a prepared command, retrying while Linux reports the executable as
/// busy.
///
/// `ETXTBSY` here is not Kento misbehaving. A workspace writes its own copy of
/// the binary, and `install` writes another; on Linux, `execve` refuses a file
/// that any process holds open for writing. Rust's descriptors are
/// close-on-exec, but a *concurrently forking* test thread still holds the
/// write descriptor open for the window between its `fork` and its `exec`, and
/// during that window every other thread's `execve` of that file fails. It is
/// purely a function of how many tests fork at once, so it is rare locally and
/// far likelier on a loaded CI runner — the worst possible place to learn about
/// it. macOS does not enforce this at all, which is why it took a Linux run to
/// surface.
fn output(command: &mut Command) -> Output {
    for _ in 0..50 {
        match command.output() {
            Ok(output) => return output,
            Err(error) if error.raw_os_error() == Some(libc_etxtbsy()) => {
                std::thread::sleep(std::time::Duration::from_millis(20));
            }
            Err(error) => panic!("run kento: {error}"),
        }
    }
    panic!("run kento: still ETXTBSY after 50 attempts");
}

/// `ETXTBSY` is 26 on Linux and has no meaning on macOS, where the kernel does
/// not refuse the exec at all. Naming it directly avoids a dependency for one
/// integer.
const fn libc_etxtbsy() -> i32 {
    26
}

fn run(root: &Path, home: &Path, args: &[&str]) -> Output {
    output(
        hermetic(workspace_binary(root).as_os_str())
            .current_dir(root)
            .env("HOME", home)
            .args(args),
    )
}

/// Like `run`, but bounded. For probes where the regression under test is a
/// hang — reading a FIFO, above all — `output()` would wait forever right
/// alongside the child, turning a caught bug into a wedged suite. The deadline
/// converts that hang into this test's own failure.
fn run_with_deadline(root: &Path, home: &Path, args: &[&str], deadline: Duration) -> Output {
    let binary = workspace_binary(root);
    let mut command = hermetic(binary.as_os_str());
    command
        .current_dir(root)
        .env("HOME", home)
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = 'spawn: {
        for _ in 0..50 {
            match command.spawn() {
                Ok(child) => break 'spawn child,
                Err(error) if error.raw_os_error() == Some(libc_etxtbsy()) => {
                    std::thread::sleep(Duration::from_millis(20));
                }
                Err(error) => panic!("run kento: {error}"),
            }
        }
        panic!("run kento: still ETXTBSY after 50 attempts");
    };
    let started = Instant::now();
    while child.try_wait().expect("poll kento").is_none() {
        if started.elapsed() > deadline {
            let _ = child.kill();
            let _ = child.wait();
            panic!("kento still running after {deadline:?}; a refusal has become a hang");
        }
        std::thread::sleep(Duration::from_millis(20));
    }
    child.wait_with_output().expect("collect kento output")
}

/// The identity is inline because `hermetic` discards user configuration, and
/// commands that build a commit — `merge` above all — check for one before they
/// do any work. Without it `git merge` fails at the identity rather than at the
/// conflict it was called to produce, which looks the same to a caller testing
/// only the exit status. macOS derives a fallback identity from the OS user and
/// Linux does not, so the difference is invisible until the suite leaves the
/// developer's machine.
fn git(root: &Path, args: &[&str]) -> bool {
    hermetic(OsStr::new("git"))
        .current_dir(root)
        .args([
            "-c",
            "user.name=Kento Test",
            "-c",
            "user.email=kento@example.invalid",
        ])
        .args(args)
        .output()
        .is_ok_and(|output| output.status.success())
}

/// Commits through Git so the installed pre-commit hook actually runs. The
/// identity is passed inline because `hermetic` discards user configuration.
fn commit(root: &Path, home: &Path, message: &str) -> bool {
    hermetic(OsStr::new("git"))
        .current_dir(root)
        .env("HOME", home)
        .args([
            "-c",
            "user.name=Kento Test",
            "-c",
            "user.email=kento@example.invalid",
            "commit",
            "-q",
            "-m",
            message,
        ])
        .output()
        .is_ok_and(|output| output.status.success())
}

/// Like `run`, but arranged so the child can actually invoke Cargo.
///
/// `HOME` is inherited rather than replaced. Under rustup the toolchains live in
/// `$HOME/.rustup`, but a distribution package or a Nix store puts them somewhere
/// else entirely, and a guess that is wrong anywhere fails this test on a machine
/// where nothing is wrong. Inheriting is also simply what a real `kento` run has.
/// It is safe because linting never reads `HOME` — only `install` and `uninstall`
/// do, and no test here runs either — while `hermetic` still cuts off the Git
/// configuration that `HOME` would otherwise reach.
///
/// `CARGO_TARGET_DIR` is pinned inside the workspace, so neither an ambient
/// setting nor a `~/.cargo/config.toml` can send this build into a directory
/// shared with the outer test run, and `Cleanup` takes it away afterwards. It sits
/// beside the repository rather than inside it, where discovery would walk it.
fn run_with_toolchain(root: &Path, args: &[&str]) -> Output {
    let binary = workspace_binary(root);
    output(
        hermetic(binary.as_os_str())
            .current_dir(root)
            .env("CARGO_TARGET_DIR", binary.with_file_name("cargo-target"))
            .args(args),
    )
}

/// Cargo alone is not enough: Kento drives `cargo fmt` and `cargo clippy`, and a
/// toolchain missing either component would otherwise surface as a confusing
/// assertion failure rather than as the missing component it is.
fn require_shellcheck() {
    assert!(
        Command::new("shellcheck")
            .arg("--version")
            .output()
            .is_ok_and(|output| output.status.success()),
        "ShellCheck is required: Kento runs it over every shell file it finds, and these tests must never pass by skipping"
    );
}

fn require_cargo() {
    for component in [["fmt", "--version"], ["clippy", "--version"]] {
        assert!(
            Command::new("cargo")
                .args(component)
                .output()
                .is_ok_and(|output| output.status.success()),
            "`cargo {}` is required: Kento runs rustfmt and Clippy, and these tests must never pass by skipping",
            component[0]
        );
    }
}

fn require_git() {
    assert!(
        hermetic(OsStr::new("git"))
            .arg("--version")
            .output()
            .is_ok_and(|output| output.status.success()),
        "Git is required: these tests cover Kento's Git integration and must never pass by skipping"
    );
}

fn stdout(output: &Output) -> String {
    String::from_utf8(output.stdout.clone()).expect("utf8 stdout")
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

/// Asserts a refusal, and that it is *this* refusal. Exit status 2 alone is
/// shared by every usage, configuration, I/O, and integration error, so an
/// exit-code-only assertion passes on the wrong failure.
fn assert_refused(output: &Output, expected: &str) {
    let stderr = stderr(output);
    assert_eq!(output.status.code(), Some(2), "stderr: {stderr}");
    assert!(
        stderr.contains(expected),
        "expected `{expected}` in stderr, got: {stderr}"
    );
}

fn assert_clean(output: &Output) {
    assert_eq!(output.status.code(), Some(0), "stderr: {}", stderr(output));
}

/// Denies writes inside `path` and proves the denial took effect. Root and
/// filesystems that ignore mode bits would otherwise turn every test built on
/// this injection into a vacuous pass.
fn lock_directory(path: &Path) {
    fs::set_permissions(path, fs::Permissions::from_mode(0o500)).expect("lock directory");
    let probe = path.join(".kento-write-probe");
    if fs::write(&probe, b"probe").is_ok() {
        let _ = fs::remove_file(&probe);
        panic!(
            "writes to {} are still permitted; run as a non-root user on a filesystem that enforces mode bits",
            path.display()
        );
    }
}

fn unlock_directory(path: &Path) {
    fs::set_permissions(path, fs::Permissions::from_mode(0o700)).expect("unlock directory");
}

fn lock_file(path: &Path) -> fs::Permissions {
    let original = fs::metadata(path).expect("file metadata").permissions();
    fs::set_permissions(path, fs::Permissions::from_mode(0o444)).expect("lock file");
    assert!(
        fs::OpenOptions::new().write(true).open(path).is_err(),
        "writes to {} are still permitted; run as a non-root user on a filesystem that enforces mode bits",
        path.display()
    );
    original
}

#[test]
fn command_output_order_discovery_and_exceptions() {
    let (root, home, _cleanup) = workspace("lint");
    fs::create_dir_all(root.join("node_modules")).expect("skip dir");
    fs::write(root.join("b.py"), "x = 1\nexcept:\n").expect("python");
    fs::write(root.join("a.py"), "x == None\n").expect("python");
    fs::write(root.join("bundle.min.js"), "var x = 1 \n").expect("generated");
    fs::write(root.join("node_modules/skip.py"), "except:\n").expect("skipped");
    fs::write(root.join(".kentoignore"), "b.py\n").expect("ignore");
    let output = run(&root, &home, &["all"]);
    assert_eq!(output.status.code(), Some(1));
    let listing = stdout(&output);
    assert!(listing.contains("\"path\":\"a.py\""));
    assert!(!listing.contains("\"path\":\"b.py\""));
    assert!(!listing.contains("skip.py"));
    assert!(!listing.contains("bundle.min.js"));
    assert!(listing.starts_with("{\"schema\":\"kento.diagnostic/v1\""));

    let explicit = run(&root, &home, &["py", "b.py", "--format", "text"]);
    assert_eq!(explicit.status.code(), Some(1));
    assert_eq!(
        stdout(&explicit),
        "KENTO101 b.py:2:1: bare except catches every exception — Catch a specific exception type instead.\n"
    );

    fs::write(
        root.join(".kentoexceptions"),
        "KENTO102 a.py justified technical exception\n",
    )
    .expect("exception");
    let suppressed = run(&root, &home, &["all"]);
    assert_clean(&suppressed);
    assert!(suppressed.stdout.is_empty());
    assert_clean(&run(&root, &home, &["ignore-audit"]));

    fs::write(root.join("a.py"), "x is None\n").expect("fixed");
    let stale = run(&root, &home, &["ignore-audit"]);
    assert_eq!(stale.status.code(), Some(1));
    assert!(stdout(&stale).contains("KENTO901"));
    assert!(stdout(&stale).contains("exception no longer suppresses a finding"));

    // A live exception for a language-specific rule on the file type it does
    // apply to: the audit must stay quiet rather than call it inapplicable.
    fs::write(root.join("dup.html"), "<a href=x href=y>\n").expect("html");
    fs::write(
        root.join(".kentoexceptions"),
        "KENTO201 dup.html duplicate attribute is generated upstream\n",
    )
    .expect("html exception");
    assert_clean(&run(&root, &home, &["ignore-audit"]));
    fs::remove_file(root.join("dup.html")).expect("remove html");

    fs::write(
        root.join(".kentoexceptions"),
        "KENTO301 a.py wrong language\n",
    )
    .expect("unsupported");
    let unsupported = run(&root, &home, &["ignore-audit"]);
    assert_eq!(unsupported.status.code(), Some(1));
    assert!(
        stdout(&unsupported).contains("exception rule does not apply to this file type"),
        "{}",
        stdout(&unsupported)
    );

    fs::write(
        root.join(".kentoexceptions"),
        "KENTO101 gone.py removed file\n",
    )
    .expect("missing");
    let missing = run(&root, &home, &["ignore-audit"]);
    assert_eq!(missing.status.code(), Some(1));
    assert!(
        stdout(&missing).contains("exception path does not exist"),
        "{}",
        stdout(&missing)
    );

    fs::write(root.join(".kentoexceptions"), "KENTO999 a.py bad\n").expect("invalid");
    let invalid = run(&root, &home, &["all"]);
    assert_refused(&invalid, ".kentoexceptions:1: malformed exception");
    assert!(invalid.stdout.is_empty());
}

/// ShellCheck's findings, and the files it is not asked about.
///
/// It analyses sh, bash, dash and ksh. Handed zsh it answers "ShellCheck only
/// supports…" once per file, as a finding rather than an error — on a real
/// corpus that is 29% of what Kento calls shell, so it would bury the report.
/// Those files still get Kento's own rules; they just do not get this one.
#[test]
fn shellcheck_findings_join_kentos_own_and_zsh_is_not_offered() {
    require_shellcheck();
    let (root, home, _cleanup) = workspace("shellcheck");
    fs::write(root.join("bad.sh"), "#!/bin/bash\nfoo=$1\nrm $foo\n").expect("shell");
    fs::write(root.join("fine.zsh"), "#!/bin/zsh\nfoo=$1\nrm $foo\n").expect("zsh");
    fs::write(root.join("named.sh"), "#!/bin/zsh\nfoo=$1\nrm $foo\n").expect("zsh by shebang");

    let output = run(&root, &home, &["all", "--format", "text"]);
    let report = stdout(&output);

    assert_eq!(output.status.code(), Some(1), "stderr: {}", stderr(&output));
    assert!(
        report.contains("KENTO501 bad.sh:3:4") && report.contains("[SC2086]"),
        "expected ShellCheck's own finding and code: {report}"
    );
    // Neither zsh file is offered to it, so neither draws the refusal.
    assert!(
        !report.contains("SC1071"),
        "a zsh file was sent to ShellCheck: {report}"
    );
    assert!(
        !report.contains("fine.zsh") && !report.contains("named.sh"),
        "zsh files must draw no ShellCheck finding at all: {report}"
    );
}

#[test]
fn lints_every_supported_language_and_skips_generated_files() {
    let (root, home, _cleanup) = workspace("languages");
    fs::write(root.join("a.py"), "x == None\n").expect("python");
    fs::write(root.join("m.rs"), "fn main() {} \n").expect("rust");
    fs::write(root.join("t.js"), "let y = 2 \n").expect("javascript");
    fs::write(root.join("t.ts"), "let x = 1 \n").expect("typescript");
    fs::write(root.join("s.css"), "body {\n/* open\n").expect("css");
    fs::write(root.join("p.html"), "<a href=x href=y>\n").expect("html");
    // The shebang keeps this fixture about trailing whitespace: without one,
    // ShellCheck cannot know the dialect and says so, which is a finding about
    // the fixture rather than about the rule under test.
    fs::write(root.join("z.sh"), "#!/bin/sh\necho hi \n").expect("shell");
    fs::write(root.join("hookish"), "#!/usr/bin/env bash\necho hi   \n").expect("shebang");
    fs::write(root.join("bundle.min.js"), "var x = 1 \n").expect("minified script");
    fs::write(root.join("styles.min.css"), "a{color:red} \n").expect("minified stylesheet");

    let cases: &[(&str, &str)] = &[
        (
            "py",
            "KENTO102 a.py:1:6: None compared with equality — Use `is None` or `is not None`.\n",
        ),
        (
            "rs",
            "KENTO003 m.rs:1:13: trailing ASCII whitespace — Remove the trailing spaces or tabs.\n",
        ),
        (
            "js",
            "KENTO003 t.js:1:10: trailing ASCII whitespace — Remove the trailing spaces or tabs.\n",
        ),
        (
            "ts",
            "KENTO003 t.ts:1:10: trailing ASCII whitespace — Remove the trailing spaces or tabs.\n",
        ),
        (
            "css",
            "KENTO301 s.css:2:1: unterminated CSS comment — Close the comment with `*/`.\n",
        ),
        (
            "html",
            "KENTO201 p.html:1:11: duplicate HTML attribute — Keep only one instance of each attribute on this tag.\n",
        ),
        (
            "sh",
            "KENTO003 hookish:2:8: trailing ASCII whitespace — Remove the trailing spaces or tabs.\nKENTO003 z.sh:2:8: trailing ASCII whitespace — Remove the trailing spaces or tabs.\n",
        ),
    ];
    for (command, expected) in cases {
        let output = run(&root, &home, &[command, "--format", "text"]);
        assert_eq!(
            output.status.code(),
            Some(1),
            "{command}: {}",
            stderr(&output)
        );
        assert_eq!(&stdout(&output), expected, "{command}");
    }
}

/// The two language-independent rules, end to end. Unit tests cover their
/// detection; only this proves they survive discovery, exceptions, rendering,
/// and the exit code.
#[test]
fn reports_conflict_markers_and_a_missing_final_newline_end_to_end() {
    let (root, home, _cleanup) = workspace("universal-rules");
    fs::write(
        root.join("merged.rs"),
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n",
    )
    .expect("conflict");
    fs::write(root.join("truncated.css"), "a { color: red; }").expect("no final newline");

    let output = run(&root, &home, &["all", "--format", "text"]);

    assert_eq!(output.status.code(), Some(1), "{}", stderr(&output));
    assert_eq!(
        stdout(&output),
        "KENTO001 merged.rs:1:1: complete merge conflict marker block found — \
         Resolve the merge conflict and remove all conflict markers.\n\
         KENTO002 truncated.css:1:17: file does not end with a line feed — \
         End the file with a single LF newline.\n"
    );

    // An unresolved block on its own is not a finding, so a file mid-merge with
    // only an opening marker stays clean.
    fs::write(root.join("merged.rs"), "<<<<<<< HEAD\nours\n").expect("half conflict");
    fs::write(root.join("truncated.css"), "a { color: red; }\n").expect("final newline");
    assert_clean(&run(&root, &home, &["all"]));

    // Both are exceptable through the normal path.
    fs::write(
        root.join("merged.rs"),
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n",
    )
    .expect("conflict");
    fs::write(
        root.join(".kentoexceptions"),
        "KENTO001 merged.rs recorded upstream conflict fixture\n",
    )
    .expect("exception");
    assert_clean(&run(&root, &home, &["all"]));
    assert_clean(&run(&root, &home, &["ignore-audit"]));
}

/// rustfmt's and Clippy's findings, reported as Kento rules and merged into the
/// one sorted report alongside Kento's own. Unit tests cover the parsing; only
/// this proves the manifest gate, the discovered-path filter, and the merge.
#[test]
fn rust_toolchain_findings_join_kentos_own() {
    require_cargo();
    let (root, _home, _cleanup) = workspace("toolchain");
    let unformatted = "pub fn widths(v: &Vec<i32>) -> usize {\nlet n    =   v.len();\n    n\n}\n";
    fs::create_dir_all(root.join("src")).expect("src");
    fs::write(root.join("src/lib.rs"), unformatted).expect("lib");
    fs::write(root.join("trailing.py"), "x = 1 \n").expect("python");

    // Without a manifest there is no package to check, so only Kento's own rules
    // fire even though a Rust file is present. What actually pins the gate is the
    // unit test in `toolchain.rs`: this workspace sits inside Kento's own package,
    // so an ungated run would find that manifest and pass here for the wrong
    // reason.
    let ungated = run_with_toolchain(&root, &["all", "--format", "text"]);
    assert_eq!(ungated.status.code(), Some(1), "{}", stderr(&ungated));
    assert!(
        !stdout(&ungated).contains("KENTO401") && !stdout(&ungated).contains("KENTO402"),
        "the toolchain ran without a Cargo.toml: {}",
        stdout(&ungated)
    );

    fs::write(root.join("Cargo.toml"), fixture_manifest()).expect("manifest");

    let output = run_with_toolchain(&root, &["all", "--format", "text"]);

    assert_eq!(output.status.code(), Some(1), "{}", stderr(&output));
    let listing = stdout(&output);
    assert!(
        listing.contains("KENTO401 src/lib.rs:1:1: rustfmt would reformat this file"),
        "{listing}"
    );
    // Clippy's own wording is version-dependent and deliberately not asserted; the
    // rule, the file, and a position are what has to survive the mapping.
    assert!(listing.contains("KENTO402 src/lib.rs:"), "{listing}");
    // Kento's own rules still run, and everything sorts as one report by path.
    let python = listing
        .find("KENTO003 trailing.py")
        .expect("Kento's own finding");
    assert!(
        listing.find("KENTO401 src/lib.rs").expect("rustfmt") < python,
        "{listing}"
    );
    // One hunk to reformat is one finding, not one per line of it.
    assert_eq!(
        listing.matches("rustfmt would reformat this file").count(),
        1,
        "{listing}"
    );

    // A file this run did not lint is not this run's business, even though Cargo
    // still reports it.
    fs::write(root.join(".kentoignore"), "src/\n").expect("ignore");
    let ignored = run_with_toolchain(&root, &["all", "--format", "text"]);
    assert_eq!(
        stdout(&ignored),
        "KENTO003 trailing.py:1:6: trailing ASCII whitespace — Remove the trailing spaces or tabs.\n"
    );
    fs::remove_file(root.join(".kentoignore")).expect("remove ignore");

    // Formatting the file clears only the rustfmt rule.
    let formatted = "pub fn widths(v: &Vec<i32>) -> usize {\n    v.len()\n}\n";
    fs::write(root.join("src/lib.rs"), formatted).expect("format");
    let after = run_with_toolchain(&root, &["all", "--format", "text"]);
    assert!(!stdout(&after).contains("KENTO401"), "{}", stdout(&after));
    assert!(stdout(&after).contains("KENTO402"), "{}", stdout(&after));

    // And a clean package leaves the Rust rules silent.
    fs::write(
        root.join("src/lib.rs"),
        "pub fn widths(v: &[i32]) -> usize {\n    v.len()\n}\n",
    )
    .expect("clean");
    fs::remove_file(root.join("trailing.py")).expect("remove python");
    assert_clean(&run_with_toolchain(&root, &["all"]));
}

/// A manifest for a fixture package. The empty `[workspace]` table declares it
/// standalone, so it cannot be absorbed into an ancestor workspace — this fixture
/// lives inside Kento's own `target` directory. The edition is the older one on
/// purpose: nothing here depends on the newer one, and this way the fixture builds
/// on more toolchains than Kento itself needs.
fn fixture_manifest() -> &'static str {
    "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[workspace]\n"
}

/// A tool that runs but never reaches the checking is an error too. This is the
/// failure the guard exists for: Cargo exits non-zero having produced no finding
/// at all, and calling that clean would hide a package that does not even parse.
#[test]
fn rust_checks_refuse_when_the_package_cannot_be_read() {
    require_cargo();
    let (root, _home, _cleanup) = workspace("toolchain-unreadable");
    fs::create_dir_all(root.join("src")).expect("src");
    fs::write(root.join("src/lib.rs"), "pub fn f() {}\n").expect("lib");
    fs::write(root.join("Cargo.toml"), "this is not = valid toml [[[\n").expect("manifest");

    let output = run_with_toolchain(&root, &["all"]);

    assert_refused(&output, "cargo fmt failed");
    assert!(output.stdout.is_empty(), "{}", stdout(&output));
}

/// A toolchain that cannot run at all is an error, not a clean bill of health.
#[test]
fn rust_checks_refuse_rather_than_report_clean_when_cargo_cannot_run() {
    let (root, home, _cleanup) = workspace("toolchain-missing");
    fs::create_dir_all(root.join("src")).expect("src");
    fs::write(root.join("src/lib.rs"), "pub fn f() {}\n").expect("lib");
    fs::write(root.join("Cargo.toml"), fixture_manifest()).expect("manifest");

    // An empty PATH leaves no `cargo` to execute.
    let output = output(
        hermetic(workspace_binary(&root).as_os_str())
            .current_dir(&root)
            .env("HOME", home)
            .env("PATH", "")
            .args(["all"]),
    );

    assert_refused(&output, "Cargo is required for Rust checks");
    assert!(output.stdout.is_empty(), "{}", stdout(&output));
}

#[test]
fn discovers_from_the_repository_root_and_normalizes_paths() {
    let (root, home, _cleanup) = workspace("discovery");
    let nested = root.join("sub/deep");
    fs::create_dir_all(&nested).expect("nested");
    fs::write(root.join("a.py"), "x == None\n").expect("root source");
    fs::write(nested.join("b.py"), "except:\n").expect("nested source");
    std::os::unix::fs::symlink("a.py", root.join("alias.py")).expect("symlink");

    // Discovery walks from the nearest ancestor holding `.git`, not from the
    // working directory, and the symlink is skipped rather than followed.
    let from_nested = run(&nested, &home, &["all", "--format", "text"]);
    assert_eq!(from_nested.status.code(), Some(1));
    assert_eq!(
        stdout(&from_nested),
        "KENTO102 a.py:1:6: None compared with equality — Use `is None` or `is not None`.\n\
         KENTO101 sub/deep/b.py:1:1: bare except catches every exception — Catch a specific exception type instead.\n"
    );

    let relative = run(&root, &home, &["py", "./a.py", "--format", "text"]);
    assert_eq!(relative.status.code(), Some(1));
    assert_eq!(
        stdout(&relative),
        "KENTO102 a.py:1:6: None compared with equality — Use `is None` or `is not None`.\n"
    );

    // Naming a symlink explicitly still skips it, so nothing is linted twice
    // under two names.
    let named_symlink = run(&root, &home, &["py", "alias.py", "--format", "text"]);
    assert_clean(&named_symlink);
    assert!(named_symlink.stdout.is_empty());
}

#[test]
fn reports_paths_above_the_repository_root_with_parent_segments() {
    let (root, home, _cleanup) = workspace("outside");
    let outside = root.parent().expect("base").join("outside");
    fs::create_dir_all(&outside).expect("outside");
    fs::write(outside.join("away.py"), "x == None\n").expect("source");

    let output = run(
        &root,
        &home,
        &["py", "../outside/away.py", "--format", "text"],
    );
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        stdout(&output),
        "KENTO102 ../outside/away.py:1:6: None compared with equality — Use `is None` or `is not None`.\n"
    );

    // Such a finding cannot be excepted: `.kentoexceptions` rejects `..` paths,
    // so the whole file is refused rather than the entry being ignored.
    fs::write(
        root.join(".kentoexceptions"),
        "KENTO102 ../outside/away.py reason\n",
    )
    .expect("exception");
    assert_refused(
        &run(&root, &home, &["py", "../outside/away.py"]),
        ".kentoexceptions:1: malformed exception",
    );
}

#[test]
fn reports_every_usage_error_with_its_own_message() {
    let (root, home, _cleanup) = workspace("usage");
    fs::write(root.join("x.py"), "except:\n").expect("source");
    let cases: &[(&[&str], &str)] = &[
        (&[], "missing command"),
        (&["bogus"], "unknown command `bogus`"),
        (
            &["all", "--format", "bogus"],
            "--format requires `jsonl` or `text`",
        ),
        (&["all", "--format"], "--format requires `jsonl` or `text`"),
        (&["all", "--bogus"], "unknown option `--bogus`"),
        (&["all", "--staged", "--staged"], "duplicate --staged"),
        (
            &["py", "--staged"],
            "--staged is only supported by `kento all`",
        ),
        (
            &["ignore-audit", "x.py"],
            "ignore-audit does not accept paths or --staged",
        ),
        (
            &["ignore-audit", "--staged"],
            "ignore-audit does not accept paths or --staged",
        ),
        (&["install", "--bogus"], "install accepts only --no-hook"),
        (&["maintenance", "bogus"], "maintenance takes no arguments"),
        (&["uninstall", "bogus"], "uninstall takes no arguments"),
        (&["uninstall"], "Kento is not installed"),
    ];
    for (arguments, message) in cases {
        assert_refused(&run(&root, &home, arguments), message);
    }
}

/// A directory of fake tools placed ahead of `PATH`, so `maintenance` can be
/// driven end to end without rustup, the network, or a spare toolchain. The
/// scripts stand in for the exact programs `maintenance` shells out to; every
/// real tool stays reachable behind them.
fn fake_tool_dir(root: &Path) -> PathBuf {
    let directory = root.parent().expect("workspace base").join("fake tools");
    fs::create_dir_all(&directory).expect("fake tool directory");
    directory
}

fn fake_tool(directory: &Path, name: &str, script: &str) {
    let path = directory.join(name);
    fs::write(&path, script).expect("fake tool");
    fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).expect("fake tool mode");
}

fn run_with_fake_tools(root: &Path, home: &Path, fakes: &Path, args: &[&str]) -> Output {
    let mut path = std::ffi::OsString::from(fakes);
    path.push(":");
    path.push(std::env::var_os("PATH").unwrap_or_default());
    output(
        hermetic(workspace_binary(root).as_os_str())
            .current_dir(root)
            .env("HOME", home)
            .env("PATH", path)
            .args(args),
    )
}

/// The fake rustup all four maintenance tests share: `update` reports an
/// unchanged toolchain, `check` reports whatever line the test wires in.
fn fake_rustup(fakes: &Path, check_line: &str) {
    fake_tool(
        fakes,
        "rustup",
        &format!(
            "#!/bin/sh\ncase \"$1\" in\nupdate) echo \"  stable-fake unchanged - rustc 9.9.8 (fake 2099-01-01)\" ;;\ncheck) echo \"{check_line}\" ;;\nesac\n"
        ),
    );
}

/// A repository with no pin — every checkout that is not Kento's own. The
/// orchestration must report the tools, repeat the `rustup update` summary,
/// and stop without inventing a pin to move.
#[test]
fn maintenance_updates_stable_and_stops_where_there_is_no_pin() {
    let (root, home, _cleanup) = workspace("maintenance-no-pin");
    let fakes = fake_tool_dir(&root);
    fake_rustup(&fakes, "stable-fake - up to date: 9.9.8 (fake 2099-01-01)");

    let outcome = run_with_fake_tools(&root, &home, &fakes, &["maintenance"]);
    assert_eq!(
        outcome.status.code(),
        Some(0),
        "stderr: {}",
        stderr(&outcome)
    );
    let report = stdout(&outcome);
    assert!(
        report.contains("stable-fake unchanged - rustc 9.9.8"),
        "{report}"
    );
    assert!(
        report.contains("no rust-toolchain.toml here, so there is no pin to move"),
        "{report}"
    );
}

/// A pin that is already the newest stable rustup offers: report it, change
/// nothing.
#[test]
fn maintenance_leaves_a_current_pin_alone() {
    let (root, home, _cleanup) = workspace("maintenance-current");
    let fakes = fake_tool_dir(&root);
    fake_rustup(&fakes, "stable-fake - up to date: 9.9.8 (fake 2099-01-01)");
    let pin = "[toolchain]\n# a comment that must survive\nchannel = \"9.9.8\"\n";
    fs::write(root.join("rust-toolchain.toml"), pin).expect("pin");

    let outcome = run_with_fake_tools(&root, &home, &fakes, &["maintenance"]);
    assert_eq!(
        outcome.status.code(),
        Some(0),
        "stderr: {}",
        stderr(&outcome)
    );
    let report = stdout(&outcome);
    assert!(report.contains("pinned Rust  9.9.8"), "{report}");
    assert!(
        report.contains("already the newest stable rustup offers; nothing to do"),
        "{report}"
    );
    assert_eq!(
        fs::read_to_string(root.join("rust-toolchain.toml")).expect("pin"),
        pin,
        "a pin with nothing to do must not change"
    );
}

/// An update whose checks pass is kept, and the command exits 0. The fake
/// cargo stands in for a toolchain that accepts the code as it is.
#[test]
fn maintenance_keeps_a_pin_the_checks_accept() {
    let (root, home, _cleanup) = workspace("maintenance-keep");
    let fakes = fake_tool_dir(&root);
    fake_rustup(
        &fakes,
        "stable-fake - update available: 9.9.8 (fake) -> 9.9.9 (faker)",
    );
    fake_tool(&fakes, "cargo", "#!/bin/sh\nexit 0\n");
    fs::write(
        root.join("rust-toolchain.toml"),
        "[toolchain]\n# a comment that must survive\nchannel = \"9.9.8\"\n",
    )
    .expect("pin");

    let outcome = run_with_fake_tools(&root, &home, &fakes, &["maintenance"]);
    assert_eq!(
        outcome.status.code(),
        Some(0),
        "stderr: {}",
        stderr(&outcome)
    );
    let report = stdout(&outcome);
    assert!(report.contains("newer stable 9.9.9"), "{report}");
    assert!(report.contains("passed — pin left at 9.9.9"), "{report}");
    let after = fs::read_to_string(root.join("rust-toolchain.toml")).expect("pin");
    assert!(after.contains("channel = \"9.9.9\""), "{after}");
    assert!(after.contains("a comment that must survive"), "{after}");
}

/// An update whose checks fail is reverted byte for byte, and the command
/// exits 1 — the one exit code that says "an upgrade exists and did not hold".
#[test]
fn maintenance_reverts_a_pin_the_checks_reject() {
    let (root, home, _cleanup) = workspace("maintenance-revert");
    let fakes = fake_tool_dir(&root);
    fake_rustup(
        &fakes,
        "stable-fake - update available: 9.9.8 (fake) -> 9.9.9 (faker)",
    );
    fake_tool(
        &fakes,
        "cargo",
        "#!/bin/sh\necho \"error: fake toolchain rejects this code\" >&2\nexit 1\n",
    );
    let pin = "[toolchain]\n# a comment that must survive\nchannel = \"9.9.8\"\n";
    fs::write(root.join("rust-toolchain.toml"), pin).expect("pin");

    let outcome = run_with_fake_tools(&root, &home, &fakes, &["maintenance"]);
    assert_eq!(
        outcome.status.code(),
        Some(1),
        "stderr: {}",
        stderr(&outcome)
    );
    let report = stdout(&outcome);
    assert!(
        report.contains("failed — pin reverted to 9.9.8"),
        "{report}"
    );
    assert!(
        report.contains("fake toolchain rejects this code"),
        "{report}"
    );
    assert_eq!(
        fs::read_to_string(root.join("rust-toolchain.toml")).expect("pin"),
        pin,
        "a rejected toolchain must leave the pin exactly as it was"
    );
}

#[test]
fn rejects_invalid_ignore_and_exception_files() {
    let (root, home, _cleanup) = workspace("config");
    fs::write(root.join("a.py"), "x == None\n").expect("source");
    for entry in [
        "a*.py\n",
        "a?.py\n",
        "a[1].py\n",
        "!a.py\n",
        "/absolute.py\n",
        "./a.py\n",
        "../outside.py\n",
    ] {
        fs::write(root.join(".kentoignore"), entry).expect("ignore");
        assert_refused(&run(&root, &home, &["all"]), ".kentoignore:1: invalid path");
    }
    fs::write(root.join(".kentoignore"), "# comment\n\ngenerated/\n").expect("valid ignore");
    assert_eq!(run(&root, &home, &["all"]).status.code(), Some(1));
    fs::remove_file(root.join(".kentoignore")).expect("remove ignore");

    for (contents, message) in [
        (
            "KENTO999 a.py unknown rule\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO102 /absolute.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO102 ../outside.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO102 a*.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        ("KENTO102 a.py\n", ".kentoexceptions:1: malformed exception"),
        // The rules that come from an external tool cannot be excepted: an
        // offline `ignore-audit` cannot re-run rustfmt, Clippy or ShellCheck, so
        // an exception naming one could never be shown to have gone stale.
        (
            "KENTO401 a.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO402 a.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO501 a.py reason\n",
            ".kentoexceptions:1: malformed exception",
        ),
        (
            "KENTO102 a.py reason\nKENTO102 a.py again\n",
            ".kentoexceptions:2: malformed exception",
        ),
    ] {
        fs::write(root.join(".kentoexceptions"), contents).expect("exception");
        assert_refused(&run(&root, &home, &["all"]), message);
    }
}

#[test]
fn accepts_literal_command_aliases() {
    let (root, home, _cleanup) = workspace("aliases");
    fs::write(root.join("x.py"), "except:\n").expect("source");
    let bin = home.join(".local/bin");
    fs::create_dir_all(&bin).expect("bin");
    for alias in ["kento:py", "kento:all", "kento:ignore-audit"] {
        let path = bin.join(alias);
        std::os::unix::fs::symlink(workspace_binary(&root), &path).expect("alias");
        let output = output(
            hermetic(path.as_os_str())
                .current_dir(&root)
                .env("HOME", &home),
        );
        if alias == "kento:ignore-audit" {
            assert_clean(&output);
        } else {
            assert_eq!(output.status.code(), Some(1), "{alias}");
            assert!(stdout(&output).contains("KENTO101"), "{alias}");
        }
    }
}

#[test]
fn staged_lints_index_bytes_not_worktree_and_staged_exceptions() {
    require_git();
    let (root, home, _cleanup) = workspace("staged");
    assert!(git(&root, &["init", "-q"]));
    fs::write(root.join("x.py"), "except:\n").expect("source");
    assert!(git(&root, &["add", "x.py"]));
    fs::write(root.join("x.py"), "except ValueError:\n").expect("worktree");
    // A staged symlink carries mode 120000 and blob content that would lint as a
    // bare except; only regular files may be linted.
    std::os::unix::fs::symlink("except:", root.join("link.py")).expect("symlink");
    assert!(git(&root, &["add", "link.py"]));
    let staged = run(&root, &home, &["all", "--staged"]);
    assert_eq!(staged.status.code(), Some(1), "{}", stderr(&staged));
    assert!(stdout(&staged).contains("x.py"));
    assert!(!stdout(&staged).contains("link.py"), "{}", stdout(&staged));
    fs::write(
        root.join(".kentoexceptions"),
        "KENTO101 x.py staged justification\n",
    )
    .expect("exception");
    assert!(git(&root, &["add", ".kentoexceptions"]));
    assert_clean(&run(&root, &home, &["all", "--staged"]));
}

#[test]
fn staged_lint_uses_staged_ignore_not_worktree_ignore() {
    require_git();
    let (root, home, _cleanup) = workspace("staged-ignore");
    assert!(git(&root, &["init", "-q"]));
    fs::write(root.join("ignored.py"), "except:\n").expect("source");
    fs::write(root.join(".kentoignore"), "ignored.py\n").expect("ignore");
    fs::create_dir_all(root.join("node_modules")).expect("dependency directory");
    fs::write(root.join("node_modules/dependency.py"), "except:\n").expect("dependency");
    assert!(git(
        &root,
        &[
            "add",
            "-f",
            "ignored.py",
            ".kentoignore",
            "node_modules/dependency.py",
        ],
    ));
    fs::write(root.join(".kentoignore"), "").expect("worktree ignore");
    assert_clean(&run(&root, &home, &["all", "--staged"]));
}

/// A trailing slash names a directory. The staged walk has to make the same
/// distinction the worktree walk does, or a pattern that matches nothing would
/// silently exempt the file that shares its name.
#[test]
fn staged_lint_does_not_apply_a_directory_pattern_to_a_file() {
    require_git();
    let (root, home, _cleanup) = workspace("staged-ignore-kind");
    assert!(git(&root, &["init", "-q"]));
    fs::write(root.join("x.py"), "except:\n").expect("source");
    fs::write(root.join(".kentoignore"), "x.py/\n").expect("ignore");
    assert!(git(&root, &["add", "x.py", ".kentoignore"]));

    assert_eq!(
        run(&root, &home, &["all", "--staged"]).status.code(),
        Some(1),
        "a directory pattern must not exempt the file of that name"
    );
}

/// A conflicted path has stages 1, 2 and 3 and no stage 0: nothing about it is
/// staged yet. Reading one side anyway would let an unresolved `.kentoignore`
/// quietly exempt a file the commit is about to introduce.
#[test]
fn staged_lint_ignores_a_conflicted_ignore_file() {
    require_git();
    let (root, home, _cleanup) = workspace("staged-conflict");
    assert!(git(&root, &["init", "-q"]));
    fs::write(root.join(".kentoignore"), "# base\n").expect("base ignore");
    assert!(git(&root, &["add", ".kentoignore"]));
    assert!(commit(&root, &home, "base"));

    assert!(git(&root, &["checkout", "-q", "-b", "other"]));
    fs::write(root.join(".kentoignore"), "x.py\n").expect("their ignore");
    assert!(git(&root, &["add", ".kentoignore"]));
    assert!(commit(&root, &home, "theirs"));

    assert!(git(&root, &["checkout", "-q", "-"]));
    fs::write(root.join(".kentoignore"), "# ours\n").expect("our ignore");
    assert!(git(&root, &["add", ".kentoignore"]));
    assert!(commit(&root, &home, "ours"));

    // The merge is expected to fail: the conflict is the point.
    assert!(!git(&root, &["merge", "other"]));
    // ...but a merge that failed for any *other* reason would leave `.kentoignore`
    // at stage 0 saying `# ours`, which exempts nothing either — and this test
    // would pass without ever exercising a conflicted entry. Prove the stages.
    let unmerged = output(
        hermetic(OsStr::new("git"))
            .current_dir(&root)
            .args(["ls-files", "--unmerged"]),
    );
    assert!(
        stdout(&unmerged).contains(".kentoignore"),
        "the index must actually be conflicted, got: {}",
        stdout(&unmerged)
    );

    fs::write(root.join("x.py"), "except:\n").expect("source");
    assert!(git(&root, &["add", "x.py"]));

    assert_eq!(
        run(&root, &home, &["all", "--staged"]).status.code(),
        Some(1),
        "an unresolved .kentoignore must not exempt anything"
    );
}

/// A workspace has to be a boundary Git respects.
///
/// When it was not, `git rev-parse --git-path hooks` answered with the
/// enclosing checkout, and a single `install` wrote its managed hook into the
/// developer's own repository aimed at a binary in a temporary directory —
/// every later commit in that repository then failed. A test suite that can do
/// that to the tree it is running in cannot be left unattended.
#[test]
fn a_workspace_is_a_repository_git_stops_at() {
    require_git();
    let (root, home, _cleanup) = workspace("workspace-boundary");

    let resolved = output(hermetic(OsStr::new("git")).current_dir(&root).args([
        "rev-parse",
        "--git-path",
        "hooks",
    ]));
    assert!(resolved.status.success(), "stderr: {}", stderr(&resolved));
    let hooks = root.join(stdout(&resolved).trim());
    assert!(
        hooks.starts_with(&root),
        "Git resolved hooks outside the workspace, to {}",
        hooks.display()
    );

    // And the hook an install writes lands there, not above it.
    assert_clean(&run(&root, &home, &["install"]));
    assert!(root.join(".git/hooks/pre-commit").is_file());
}

#[test]
fn incompatible_hook_is_rejected_before_installing_commands() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-preflight");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    fs::write(&hook, "#!/usr/bin/env python3\n").expect("hook");

    let result = run(&root, &home, &["install"]);

    assert_refused(
        &result,
        "existing pre-commit hook needs a sh/bash/zsh shebang",
    );
    assert!(!home.join(".local/bin/kento").exists());
    assert_eq!(
        fs::read_to_string(&hook).expect("preserved hook"),
        "#!/usr/bin/env python3\n"
    );
}

#[test]
fn install_failure_does_not_overwrite_unmanaged_commands() {
    require_git();
    let (root, home, _cleanup) = workspace("install-preflight");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    let original = "#!/bin/sh\necho existing\n";
    fs::write(&hook, original).expect("hook");
    let bin = home.join(".local/bin");
    fs::create_dir_all(&bin).expect("bin");
    let installed = bin.join("kento");
    fs::write(&installed, "unrelated command\n").expect("unmanaged command");

    let result = run(&root, &home, &["install"]);

    assert_refused(&result, "refusing to replace unmanaged command");
    assert_eq!(
        fs::read_to_string(&installed).expect("preserved command"),
        "unrelated command\n"
    );
    assert_eq!(fs::read_to_string(&hook).expect("preserved hook"), original);
    assert!(!bin.join("kento:all").exists());
}

#[test]
fn hook_state_write_failure_leaves_existing_hook_unchanged() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-state-write");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    let original = "#!/bin/sh\necho existing\n";
    fs::write(&hook, original).expect("hook");
    assert_clean(&run(&root, &home, &["install", "--no-hook"]));
    let state = home.join(".local/share/kento/hooks");
    fs::create_dir_all(&state).expect("state");
    lock_directory(&state);

    let result = run(&root, &home, &["install"]);

    assert_refused(&result, "cannot stage hook state");
    assert_eq!(fs::read_to_string(&hook).expect("preserved hook"), original);
    assert!(home.join(".local/bin/kento").exists());
    unlock_directory(&state);
    assert_clean(&run(&root, &home, &["uninstall"]));
}

#[test]
fn hook_state_remove_failure_leaves_installation_unchanged() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-state-remove");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    fs::write(&hook, "#!/bin/sh\necho existing\n").expect("hook");
    assert_clean(&run(&root, &home, &["install"]));
    let installed_hook = fs::read_to_string(&hook).expect("installed hook");
    let state = home.join(".local/share/kento/hooks");
    lock_directory(&state);

    let result = run(&root, &home, &["uninstall"]);

    assert_refused(&result, "cannot remove hook state");
    assert_eq!(
        fs::read_to_string(&hook).expect("preserved hook"),
        installed_hook
    );
    assert!(home.join(".local/bin/kento").exists());
    assert!(home.join(".local/bin/kento:all").is_symlink());
    unlock_directory(&state);
    assert_clean(&run(&root, &home, &["uninstall"]));
}

#[test]
fn global_uninstall_rolls_back_hooks_removed_before_a_later_failure() {
    require_git();
    let (first, home, _cleanup) = workspace("global-rollback");
    let second = first
        .parent()
        .expect("base")
        .join("repository z with spaces");
    fs::create_dir_all(&second).expect("second repository");
    assert!(git(&first, &["init", "-q"]));
    assert!(git(&second, &["init", "-q"]));
    let first_hook = first.join(".git/hooks/pre-commit");
    let second_hook = second.join(".git/hooks/pre-commit");
    fs::write(&first_hook, "#!/bin/sh\necho first\n").expect("first hook");
    fs::write(&second_hook, "#!/bin/sh\necho second\n").expect("second hook");
    assert_clean(&run(&first, &home, &["install"]));
    assert_clean(&run(&second, &home, &["install"]));
    let installed_first = fs::read_to_string(&first_hook).expect("installed first hook");
    let installed_second = fs::read_to_string(&second_hook).expect("installed second hook");
    let second_permissions = lock_file(&second_hook);

    let result = run(&first, &home, &["uninstall"]);

    assert_refused(&result, "cannot update hook");
    assert_eq!(
        fs::read_to_string(&first_hook).expect("rolled back first hook"),
        installed_first
    );
    assert_eq!(
        fs::read_to_string(&second_hook).expect("preserved second hook"),
        installed_second
    );
    assert!(home.join(".local/bin/kento").exists());
    fs::set_permissions(&second_hook, second_permissions).expect("unlock second hook");
    assert_clean(&run(&first, &home, &["uninstall"]));
}

#[test]
fn uninstall_refuses_changed_binary_without_modifying_installation() {
    require_git();
    let (root, home, _cleanup) = workspace("uninstall-binary-ownership");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    fs::write(&hook, "#!/bin/sh\necho existing\n").expect("hook");
    assert_clean(&run(&root, &home, &["install"]));
    let installed_hook = fs::read_to_string(&hook).expect("installed hook");
    let binary = home.join(".local/bin/kento");
    fs::write(&binary, "replacement command\n").expect("replace binary");

    let result = run(&root, &home, &["uninstall"]);

    assert_refused(&result, "installed Kento binary has changed");
    assert_eq!(
        fs::read_to_string(&binary).expect("preserved replacement"),
        "replacement command\n"
    );
    assert_eq!(
        fs::read_to_string(&hook).expect("untouched hook"),
        installed_hook
    );
    assert!(home.join(".local/bin/kento:all").is_symlink());
}

/// The installed binary replaced by something Kento never wrote. A directory is
/// not a regular file and not a symlink either, so a check demanding both would
/// walk straight past it and fingerprint whatever it found.
#[test]
fn uninstall_refuses_an_installed_binary_that_is_not_a_regular_file() {
    require_git();
    let (root, home, _cleanup) = workspace("uninstall-binary-not-regular");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let binary = home.join(".local/bin/kento");
    let decoy = home.join("decoy");
    fs::write(&decoy, "decoy\n").expect("decoy");

    fs::remove_file(&binary).expect("remove binary");
    fs::create_dir(&binary).expect("directory binary");
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "no longer a managed regular file",
    );
    assert!(binary.is_dir(), "the directory must survive the refusal");

    fs::remove_dir(&binary).expect("remove directory");
    std::os::unix::fs::symlink(&decoy, &binary).expect("symlink binary");
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "no longer a managed regular file",
    );
    assert_eq!(
        fs::read_to_string(&decoy).expect("untouched decoy"),
        "decoy\n"
    );
}

/// An existing pre-commit hook that is a directory or a symlink. `install` must
/// refuse by inspection rather than read through it — the same guard the
/// uninstall path carries, on the path that runs first.
#[test]
fn install_refuses_an_existing_hook_that_is_not_a_regular_file() {
    require_git();
    let (root, home, _cleanup) = workspace("install-hook-not-regular");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    fs::create_dir_all(hook.parent().expect("hooks directory")).expect("hooks");
    let decoy = root.join("decoy");
    fs::write(&decoy, "#!/bin/sh\necho decoy\n").expect("decoy");

    fs::create_dir(&hook).expect("directory hook");
    assert_refused(&run(&root, &home, &["install"]), "is not a regular file");
    assert!(hook.is_dir(), "the directory must survive the refusal");
    assert!(!home.join(".local/bin/kento").exists());

    fs::remove_dir(&hook).expect("remove directory");
    std::os::unix::fs::symlink(&decoy, &hook).expect("symlink hook");
    assert_refused(&run(&root, &home, &["install"]), "is not a regular file");
    assert_eq!(
        fs::read_to_string(&decoy).expect("untouched decoy"),
        "#!/bin/sh\necho decoy\n"
    );
    assert!(!home.join(".local/bin/kento").exists());
}

#[test]
fn install_hook_and_uninstall_preserve_or_refuse_safely() {
    require_git();
    let (root, home, _cleanup) = workspace("install");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    fs::write(&hook, "#!/bin/sh\necho existing\n").expect("hook");
    assert_clean(&run(&root, &home, &["install"]));
    let installed = fs::read_to_string(&hook).expect("hook");
    assert!(installed.starts_with("#!/bin/sh\n# >>> kento managed block >>>\n"));
    assert!(installed.ends_with("echo existing\n"));
    for command in [
        "kento",
        "kento:all",
        "kento:rs",
        "kento:py",
        "kento:js",
        "kento:ts",
        "kento:css",
        "kento:html",
        "kento:sh",
        "kento:ignore-audit",
        "kento:maintenance",
        "kento:install",
        "kento:uninstall",
    ] {
        assert!(
            home.join(".local/bin").join(command).exists(),
            "missing {command}"
        );
    }
    assert_clean(&run(&root, &home, &["install"]));
    assert_eq!(
        fs::read_to_string(&hook)
            .expect("idempotent hook")
            .matches("# >>> kento managed block >>>")
            .count(),
        1
    );
    assert_clean(&run(&root, &home, &["uninstall"]));
    assert_eq!(
        fs::read_to_string(&hook).expect("preserved hook"),
        "#!/bin/sh\necho existing\n"
    );

    assert_clean(&run(&root, &home, &["install"]));
    fs::write(&hook, "#!/bin/sh\n# altered\n").expect("tamper");
    let refusal = run(&root, &home, &["uninstall"]);
    assert_refused(&refusal, "has altered Kento block");
    assert_eq!(
        fs::read_to_string(&hook).expect("untouched hook"),
        "#!/bin/sh\n# altered\n"
    );
}

#[test]
fn installed_hook_blocks_a_commit_with_staged_findings() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-runs");
    assert!(git(&root, &["init", "-q"]));
    // The pre-existing command must run only when Kento passes: without it the
    // hook's exit status would come from Kento by default, hiding a block that
    // fails to abort. Git ignores a hook that is not executable, and Kento
    // preserves the mode it finds, so this one has to be executable already.
    let hook = root.join(".git/hooks/pre-commit");
    fs::write(&hook, "#!/bin/sh\necho existing\n").expect("hook");
    fs::set_permissions(&hook, fs::Permissions::from_mode(0o755)).expect("hook mode");
    assert_clean(&run(&root, &home, &["install"]));

    fs::write(root.join("bad.py"), "except:\n").expect("violation");
    assert!(git(&root, &["add", "bad.py"]));
    assert!(
        !commit(&root, &home, "blocked"),
        "the installed hook must reject a commit with staged findings"
    );

    fs::write(root.join("bad.py"), "except ValueError:\n    pass\n").expect("fixed");
    assert!(git(&root, &["add", "bad.py"]));
    assert!(
        commit(&root, &home, "allowed"),
        "the installed hook must allow a clean commit"
    );
}

#[test]
fn refuses_unmanaged_aliases_and_tampered_state() {
    require_git();
    let (root, home, _cleanup) = workspace("ownership");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));

    let alias = home.join(".local/bin/kento:py");
    fs::remove_file(&alias).expect("remove alias");
    fs::write(&alias, "unrelated command\n").expect("unmanaged alias");
    assert_refused(
        &run(&root, &home, &["install"]),
        "refusing unmanaged command",
    );
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "refusing unmanaged command",
    );
    fs::remove_file(&alias).expect("clear alias");
    std::os::unix::fs::symlink("kento", &alias).expect("restore alias");

    let manifest = home.join(".local/share/kento/installation");
    let recorded = fs::read_to_string(&manifest).expect("manifest");
    for tampered in [
        "kento-install-v1\nsize=1\nhash=deadbeef\n",
        "kento-install-v2\nsize=1\nhash=00000000000000000000000000000000\n",
        "kento-install-v1\nsize=huge\nhash=00000000000000000000000000000000\n",
        "kento-install-v1\nsize=1\n",
        "kento-install-v1\nsize=1\nhash=00000000000000000000000000000000",
    ] {
        fs::write(&manifest, tampered).expect("tamper manifest");
        assert_refused(
            &run(&root, &home, &["uninstall"]),
            "malformed Kento installation manifest",
        );
    }
    fs::write(&manifest, &recorded).expect("restore manifest");

    let state = home.join(".local/share/kento/hooks");
    let record = fs::read_dir(&state)
        .expect("hook state")
        .next()
        .expect("one record")
        .expect("record entry")
        .path();
    let contents = fs::read(&record).expect("record contents");
    for tampered in ["relative/path\n", "\n", "/absolute/but/unhashed\n"] {
        fs::write(&record, tampered).expect("tamper record");
        assert_refused(
            &run(&root, &home, &["uninstall"]),
            "malformed hook state record",
        );
    }
    fs::write(&record, &contents).expect("restore record");
    fs::write(state.join("unexpected"), "stray\n").expect("stray record");
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "malformed hook state record",
    );
    fs::remove_file(state.join("unexpected")).expect("clear stray record");
    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// An install that fails after creating the commands but before writing the
/// manifest must leave nothing behind. The commands alone are indistinguishable
/// from a user's own, so a retry would refuse them as unmanaged forever.
#[test]
fn install_failing_to_record_ownership_leaves_no_commands_behind() {
    require_git();
    let (root, home, _cleanup) = workspace("install-manifest-write");
    assert!(git(&root, &["init", "-q"]));
    let state = home.join(".local/share/kento");
    fs::create_dir_all(&state).expect("state");
    lock_directory(&state);

    let result = run(&root, &home, &["install"]);

    assert_refused(&result, "cannot write installation state");
    let bin = home.join(".local/bin");
    assert!(!bin.join("kento").exists(), "the binary survived a failure");
    for alias in ["kento:all", "kento:py", "kento:uninstall"] {
        assert!(
            !bin.join(alias).exists(),
            "{alias} survived a failed install"
        );
    }
    assert!(!root.join(".git/hooks/pre-commit").exists());

    // The retry is the point: it has to be able to succeed.
    unlock_directory(&state);
    assert_clean(&run(&root, &home, &["install"]));
    assert!(bin.join("kento").exists());
    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// An upgrade that fails to record the new binary has to put the old one back.
/// Otherwise the manifest describes a binary that is no longer installed, and
/// every later install refuses it as changed — the same wedge from the other
/// direction.
///
/// The replacement is byte-identical to what it replaces here, so content cannot
/// tell a restored file from a freshly copied one. The mode can: `fs::copy`
/// carries the source's bits, so a mode the source does not have survives only if
/// the original file itself came back.
#[test]
fn install_failing_to_record_an_upgrade_restores_the_previous_binary() {
    require_git();
    let (root, home, _cleanup) = workspace("install-upgrade");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install", "--no-hook"]));
    let bin = home.join(".local/bin");
    let binary = bin.join("kento");
    // Chosen against what install actually left rather than hardcoded: a build
    // made under a restrictive umask produces a binary that is already 0o700, and
    // a marker equal to it would prove nothing.
    let installed = fs::metadata(&binary).expect("binary").permissions().mode() & 0o777;
    let marker = if installed == 0o700 { 0o500 } else { 0o700 };
    fs::set_permissions(&binary, fs::Permissions::from_mode(marker)).expect("mark binary");
    let state = home.join(".local/share/kento");
    lock_directory(&state);

    let result = run(&root, &home, &["install"]);

    assert_refused(&result, "cannot write installation state");
    assert_eq!(
        fs::metadata(&binary).expect("binary").permissions().mode() & 0o777,
        marker,
        "the previous binary was not restored"
    );
    assert!(
        !bin.join(".kento.previous.tmp").exists(),
        "the binary set aside for replacement was left behind"
    );
    assert!(!bin.join(".kento.install.tmp").exists());

    // The manifest still describes what is installed, so both commands work.
    unlock_directory(&state);
    assert_clean(&run(&root, &home, &["install"]));
    assert!(!bin.join(".kento.previous.tmp").exists());
    assert_clean(&run(&root, &home, &["uninstall"]));
    assert!(!binary.exists());
}

/// A leftover from an interrupted install is not adopted silently, in either of
/// the two places one can appear.
#[test]
fn install_refuses_unexpected_temporary_commands() {
    require_git();
    let (root, home, _cleanup) = workspace("install-temporaries");
    assert!(git(&root, &["init", "-q"]));
    let bin = home.join(".local/bin");
    fs::create_dir_all(&bin).expect("bin");
    for leftover in [".kento.install.tmp", ".kento.previous.tmp"] {
        fs::write(bin.join(leftover), "leftover\n").expect("leftover");
        assert_refused(
            &run(&root, &home, &["install"]),
            "refusing unexpected temporary command",
        );
        assert!(
            !bin.join("kento").exists(),
            "{leftover} let an install through"
        );
        fs::remove_file(bin.join(leftover)).expect("clear leftover");
    }
    assert_clean(&run(&root, &home, &["install"]));
    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// An uninstall that fails partway has to be resumable. Its last steps delete
/// the binary before the manifest, and a manifest describing a binary that is
/// already gone would otherwise refuse every later `install` and `uninstall`.
#[test]
fn uninstall_resumes_after_failing_to_remove_the_manifest() {
    require_git();
    let (root, home, _cleanup) = workspace("uninstall-manifest-remove");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let state = home.join(".local/share/kento");
    lock_directory(&state);

    let result = run(&root, &home, &["uninstall"]);

    assert_refused(&result, "cannot remove installation manifest");
    assert!(!home.join(".local/bin/kento").exists());

    // Still refused while the cause stands, and with the same message rather
    // than a new one about the binary it already removed.
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "cannot remove installation manifest",
    );
    unlock_directory(&state);
    assert_clean(&run(&root, &home, &["uninstall"]));
    assert!(!home.join(".local/share/kento").exists());
    assert!(!root.join(".git/hooks/pre-commit").exists());
}

/// Tampering that keeps both markers and edits only the body. The suite's other
/// tamper case destroys the markers and the body together, which satisfies both
/// halves of the guard at once and so cannot tell them apart.
#[test]
fn install_refuses_a_hook_with_kentos_markers_it_did_not_record() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-unrecorded-markers");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");

    // Take a real managed hook, then drop the state that says Kento owns it.
    assert_clean(&run(&root, &home, &["install"]));
    let managed = fs::read_to_string(&hook).expect("installed hook");
    assert_clean(&run(&root, &home, &["uninstall"]));
    fs::write(&hook, &managed).expect("replant hook");

    // The markers are Kento's and the block is exactly the expected one, so
    // every check but ownership passes. Ownership is the one that matters:
    // adopting it would let anyone hand Kento a hook to take responsibility for.
    assert_refused(
        &run(&root, &home, &["install"]),
        "refusing hook with unmanaged or malformed Kento markers",
    );
    assert_eq!(
        fs::read_to_string(&hook).expect("untouched hook"),
        managed,
        "a refused install must not edit the hook"
    );
    assert!(!home.join(".local/bin/kento").exists());
}

#[test]
fn uninstall_refuses_a_hook_tampered_inside_intact_markers() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-body-tamper");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let hook = root.join(".git/hooks/pre-commit");
    let installed = fs::read_to_string(&hook).expect("installed hook");
    let tampered = installed.replace("all --staged", "all --staged --NEUTRALISED");
    assert_ne!(tampered, installed, "the managed command must be rewritten");
    assert_eq!(
        tampered.matches("# >>> kento managed block >>>").count(),
        1,
        "both markers have to survive the tampering"
    );
    assert_eq!(tampered.matches("# <<< kento managed block <<<").count(), 1);
    fs::write(&hook, &tampered).expect("tamper");

    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "has altered Kento block",
    );

    assert_eq!(
        fs::read_to_string(&hook).expect("untouched hook"),
        tampered,
        "a refused uninstall must not edit the hook"
    );
    assert!(home.join(".local/bin/kento").exists());
    assert!(home.join(".local/share/kento/installation").exists());
}

/// The remaining refusals in the install and uninstall preflights. Each one
/// converts a clobbered installation into a silent success if it regresses.
#[test]
fn refuses_malformed_and_unexpected_installation_state() {
    require_git();
    let (root, home, _cleanup) = workspace("state-layout");
    assert!(git(&root, &["init", "-q"]));
    let state = home.join(".local/share/kento");

    // A leftover temporary manifest is a stray entry like any other: the layout
    // check runs first, so `write_manifest`'s own guard against it is reachable
    // only when a concurrent install creates one mid-run.
    fs::create_dir_all(&state).expect("state");
    fs::write(state.join(".installation.tmp"), "stale\n").expect("stale temporary");
    assert_refused(
        &run(&root, &home, &["install"]),
        "unexpected Kento installation state",
    );
    fs::remove_file(state.join(".installation.tmp")).expect("clear stale temporary");

    // A stray entry beside `installation` and `hooks`.
    fs::write(state.join("stray"), "unexpected\n").expect("stray entry");
    assert_refused(
        &run(&root, &home, &["install"]),
        "unexpected Kento installation state",
    );
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "unexpected Kento installation state",
    );
    fs::remove_file(state.join("stray")).expect("clear stray entry");

    // The state root replaced by something that is not a directory.
    fs::remove_dir_all(&state).expect("clear state");
    fs::write(&state, "not a directory\n").expect("state as file");
    assert_refused(
        &run(&root, &home, &["install"]),
        "malformed Kento installation state",
    );
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "malformed Kento installation state",
    );
    fs::remove_file(&state).expect("clear state file");

    // `installation` present as a directory rather than a file.
    fs::create_dir_all(state.join("installation")).expect("installation as directory");
    assert_refused(
        &run(&root, &home, &["install"]),
        "malformed Kento installation state",
    );
    fs::remove_dir(state.join("installation")).expect("clear installation directory");

    // `hooks` present as a file rather than a directory.
    fs::write(state.join("hooks"), "not a directory\n").expect("hooks as file");
    assert_refused(
        &run(&root, &home, &["install"]),
        "malformed Kento installation state",
    );
    fs::remove_file(state.join("hooks")).expect("clear hooks file");
}

/// State in a shape the layout check accepts, but with no manifest to say Kento
/// owns it. Installing over it would adopt files it never wrote.
#[test]
fn install_refuses_state_that_has_no_ownership_manifest() {
    require_git();
    let (root, home, _cleanup) = workspace("state-no-manifest");
    assert!(git(&root, &["init", "-q"]));
    fs::create_dir_all(home.join(".local/share/kento/hooks")).expect("hooks");

    assert_refused(
        &run(&root, &home, &["install"]),
        "without an ownership manifest",
    );

    assert!(!home.join(".local/bin/kento").exists());
}

/// `--no-hook` writes no hook state at all, so uninstall meets a state
/// directory that was never created. Absent is the expected shape here, not a
/// failure to report.
#[test]
fn uninstall_succeeds_when_no_hook_state_was_ever_written() {
    let (root, home, _cleanup) = workspace("no-hook-state");
    assert_clean(&run(&root, &home, &["install", "--no-hook"]));
    assert!(!home.join(".local/share/kento/hooks").exists());
    assert!(home.join(".local/bin/kento").exists());

    assert_clean(&run(&root, &home, &["uninstall"]));

    assert!(!home.join(".local/share/kento").exists());
    assert!(!home.join(".local/bin/kento").exists());
}

/// The note that tells the user the commands are unreachable. It has to track
/// the real `PATH`: claiming the directory is listed when it is not leaves a
/// working install nobody can invoke.
#[test]
fn install_reports_whether_the_command_directory_is_on_path() {
    let (root, home, _cleanup) = workspace("path-note");
    let bin = home.join(".local/bin");
    let note = format!("{} is not on PATH", bin.display());
    let install_with_path = |value: Option<&OsStr>| {
        let mut command = hermetic(workspace_binary(&root).as_os_str());
        command
            .current_dir(&root)
            .env("HOME", &home)
            .args(["install", "--no-hook"]);
        match value {
            Some(value) => command.env("PATH", value),
            None => command.env_remove("PATH"),
        };
        output(&mut command)
    };

    // No PATH at all names no directory, so the commands are not on it.
    let absent = install_with_path(None);
    assert_clean(&absent);
    assert!(
        stderr(&absent).contains(&note),
        "stderr: {}",
        stderr(&absent)
    );
    assert_clean(&run(&root, &home, &["uninstall"]));

    // A PATH without the directory earns the same note.
    let elsewhere = install_with_path(Some(OsStr::new("/usr/bin:/bin")));
    assert_clean(&elsewhere);
    assert!(
        stderr(&elsewhere).contains(&note),
        "stderr: {}",
        stderr(&elsewhere)
    );
    assert_clean(&run(&root, &home, &["uninstall"]));

    // A PATH that lists it earns none.
    let listed = install_with_path(Some(bin.as_os_str()));
    assert_clean(&listed);
    assert!(
        !stderr(&listed).contains("is not on PATH"),
        "stderr: {}",
        stderr(&listed)
    );
    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// `install` run from the binary it would install. Source and destination are
/// the same file, so there is nothing to replace — and replacing a file with
/// itself moves it out from under the copy that is about to read it.
#[test]
fn install_from_the_installed_binary_is_a_no_op() {
    let (root, home, _cleanup) = workspace("install-self");
    assert_clean(&run(&root, &home, &["install", "--no-hook"]));
    let binary = home.join(".local/bin/kento");
    let installed = fs::read(&binary).expect("installed binary");

    // The inode, not the bytes: staging a copy over itself reproduces the same
    // content, so identical bytes would not show that the file was left alone.
    let inode = fs::metadata(&binary).expect("installed metadata").ino();

    let again = output(
        hermetic(binary.as_os_str())
            .current_dir(&root)
            .env("HOME", &home)
            .args(["install", "--no-hook"]),
    );

    assert_clean(&again);
    assert_eq!(
        fs::metadata(&binary).expect("binary survives").ino(),
        inode,
        "installing over itself must leave the binary untouched, not replace it"
    );
    assert_eq!(fs::read(&binary).expect("binary survives"), installed);
    assert!(home.join(".local/share/kento/installation").exists());
}

/// The record filename Kento derives from a hook path. Reproduced here because
/// a record has to *look* legitimate for the checks on its contents to be the
/// thing under test — a mismatched name is rejected by a different guard.
fn record_name(path: &str) -> String {
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in path.as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("{hash:016x}")
}

/// Hook state entries that are the wrong kind, or name a path no hook could
/// have. Each one would otherwise send `uninstall` at a file of someone else's
/// choosing.
#[test]
fn uninstall_refuses_malformed_hook_state_entries() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-state-shape");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let state = home.join(".local/share/kento/hooks");

    // A directory is not a regular file and not a symlink either, so a check
    // demanding both would read straight past it.
    let directory = state.join("0123456789abcdef");
    fs::create_dir(&directory).expect("directory record");
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "malformed hook state record",
    );
    fs::remove_dir(&directory).expect("clear directory record");

    // An absolute path carrying a newline, under its own correct name: every
    // other guard passes, so only the newline check can refuse it.
    let smuggled = "/tmp/hook\nsecond line";
    fs::write(state.join(record_name(smuggled)), format!("{smuggled}\n")).expect("record");
    assert_refused(
        &run(&root, &home, &["uninstall"]),
        "malformed hook state record",
    );
    fs::remove_file(state.join(record_name(smuggled))).expect("clear record");

    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// A FIFO planted among the hook state records. It is the one entry kind the
/// directory case above cannot stand in for: weaken the kind check from `||`
/// to `&&` and a directory still fails at `read_to_string` with the identical
/// message, but a FIFO with no writer *blocks* there — the refusal becomes a
/// hang. So the guard must refuse it by inspection, and the deadline is what
/// makes a regression fail this test instead of wedging the suite.
#[test]
fn uninstall_refuses_a_fifo_hook_state_record_without_hanging() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-state-fifo");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let fifo = home.join(".local/share/kento/hooks/planted-fifo");
    assert!(
        Command::new("mkfifo")
            .arg(&fifo)
            .output()
            .is_ok_and(|output| output.status.success()),
        "mkfifo is required to plant the probe"
    );

    let refusal = run_with_deadline(&root, &home, &["uninstall"], Duration::from_secs(10));
    assert_refused(&refusal, "malformed hook state record");

    fs::remove_file(&fifo).expect("clear fifo record");
    assert_clean(&run(&root, &home, &["uninstall"]));
}

/// A recorded hook replaced by a symlink or a directory. Following it would let
/// an attacker aim Kento's block removal at a file of their choosing.
#[test]
fn uninstall_refuses_a_recorded_hook_that_is_not_a_regular_file() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-not-regular");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install"]));
    let hook = root.join(".git/hooks/pre-commit");
    let decoy = root.join("decoy");
    fs::write(&decoy, "#!/bin/sh\necho decoy\n").expect("decoy");
    fs::remove_file(&hook).expect("remove hook");
    std::os::unix::fs::symlink(&decoy, &hook).expect("symlink hook");

    assert_refused(&run(&root, &home, &["uninstall"]), "is not a regular file");

    assert_eq!(
        fs::read_to_string(&decoy).expect("untouched decoy"),
        "#!/bin/sh\necho decoy\n"
    );
    assert!(hook.is_symlink(), "the symlink must survive the refusal");
    assert!(home.join(".local/bin/kento").exists());

    // A directory is the other half of that guard: not a regular file, and not a
    // symlink either, so a check that required both would walk straight past it.
    fs::remove_file(&hook).expect("remove symlink");
    fs::create_dir(&hook).expect("directory hook");
    assert_refused(&run(&root, &home, &["uninstall"]), "is not a regular file");
    assert!(hook.is_dir(), "the directory must survive the refusal");
    assert!(home.join(".local/bin/kento").exists());
}

/// A hook Kento would have to create in a directory it cannot write. The new
/// hook must not survive, and the pre-existing installation must not change.
#[test]
fn install_refuses_a_hook_it_cannot_write() {
    require_git();
    let (root, home, _cleanup) = workspace("hook-write-denied");
    assert!(git(&root, &["init", "-q"]));
    assert_clean(&run(&root, &home, &["install", "--no-hook"]));
    let hooks = root.join(".git/hooks");
    fs::create_dir_all(&hooks).expect("hooks directory");
    assert!(!hooks.join("pre-commit").exists());
    lock_directory(&hooks);

    let refusal = run(&root, &home, &["install"]);
    assert_refused(&refusal, "cannot write hook");
    // The write failed, so no hook was ever created, so rolling one back is a
    // no-op. Reporting a rollback failure here would tell the user something
    // went wrong during cleanup when nothing did — and a message that cries
    // wolf about its own cleanup is one nobody reads twice.
    assert!(
        !stderr(&refusal).contains("hook rollback"),
        "refusal carried a spurious rollback complaint: {}",
        stderr(&refusal)
    );

    unlock_directory(&hooks);
    assert!(!hooks.join("pre-commit").exists(), "a hook was left behind");
    assert!(home.join(".local/bin/kento").exists());
    assert_clean(&run(&root, &home, &["uninstall"]));
}

#[test]
fn uninstall_removes_a_newly_created_kento_hook() {
    require_git();
    let (root, home, _cleanup) = workspace("new-hook");
    assert!(git(&root, &["init", "-q"]));
    let hook = root.join(".git/hooks/pre-commit");
    assert!(!hook.exists());
    assert_clean(&run(&root, &home, &["install"]));
    assert!(hook.exists());
    assert_clean(&run(&root, &home, &["uninstall"]));
    assert!(!hook.exists());
}

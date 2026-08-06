//! Moving the pinned toolchain forward on purpose.
//!
//! `rust-toolchain.toml` is pinned so that a new Rust release cannot turn an
//! unattended run red on a day nobody touched the code. The cost of a pin is
//! that it rots: eventually Clippy is behind, and eventually a package Kento is
//! asked to lint needs a newer compiler than the pin allows.
//!
//! This is the deliberate upgrade. It raises the pin, runs the checks Kento is
//! responsible for, and keeps the new pin only if they pass — so the decision is
//! made by evidence rather than by a calendar, and a bad release is reverted
//! rather than inherited.

use std::fs;
use std::path::Path;
use std::process::Command;

/// A pin older than this draws a note on every Rust run.
///
/// Rust ships every six weeks and the suggested habit is to run maintenance
/// every three, so this is about two missed releases: long enough that the note
/// means something has actually been skipped, short enough that it arrives while
/// the gap is still one command to close.
const STALE_AFTER_DAYS: i64 = 90;

const PIN: &str = "rust-toolchain.toml";

fn tool_version(program: &str, arguments: &[&str]) -> Option<String> {
    let output = Command::new(program).args(arguments).output().ok()?;
    if !output.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

/// The release date `rustc --version` prints, as `(YYYY, MM, DD)`.
///
/// Taking the date from the compiler itself is what keeps staleness stateless:
/// nothing has to be stored, counted, or kept in a table that would itself need
/// maintaining.
fn release_date(version: &str) -> Option<(i64, i64, i64)> {
    let inside = version.rsplit_once('(')?.1;
    let date = inside.split_whitespace().last()?.trim_end_matches(')');
    let mut parts = date.split('-');
    let year = parts.next()?.parse().ok()?;
    let month = parts.next()?.parse().ok()?;
    let day = parts.next()?.parse().ok()?;
    (1..=12).contains(&month).then_some((year, month, day))
}

/// Days from the civil calendar to a day number, so two dates can be subtracted.
/// Howard Hinnant's algorithm, which is exact for every date this will ever see.
fn day_number(year: i64, month: i64, day: i64) -> i64 {
    let year = year - i64::from(month <= 2);
    let era = if year >= 0 { year } else { year - 399 } / 400;
    let year_of_era = year - era * 400;
    let day_of_year = (153 * (month + if month > 2 { -3 } else { 9 }) + 2) / 5 + day - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    era * 146_097 + day_of_era - 719_468
}

fn today() -> i64 {
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |elapsed| elapsed.as_secs());
    (seconds / 86_400) as i64
}

/// A note for a pin that has fallen far behind, or `None` while it is current.
///
/// This warns and never blocks. A linter that refuses to lint because of its own
/// age fails for a reason that has nothing to do with the code in front of it,
/// and it would fail at the least convenient moment.
pub fn staleness_note(root: &Path) -> Option<String> {
    if !root.join(PIN).is_file() {
        return None;
    }
    let version = tool_version("rustc", &["--version"])?;
    let (year, month, day) = release_date(&version)?;
    staleness_line(today() - day_number(year, month, day), &version)
}

/// The note itself, given an age. Separated from reading the clock and the
/// compiler so the threshold can be tested at both sides of it.
///
/// The wording names what the suggested command edits — *this repository's*
/// pin — because the note fires in any repository with a stale pin, including
/// one the reader is only linting. Advice that hides its side effect is advice
/// a bystander cannot act on safely.
fn staleness_line(age: i64, version: &str) -> Option<String> {
    (age > STALE_AFTER_DAYS).then(|| {
        format!(
            "pinned Rust is {age} days old ({}); `kento maintenance` moves this repository's pin forward",
            version.trim_start_matches("rustc ")
        )
    })
}

/// Brings the default `stable` toolchain up to date.
///
/// This is the half that matters for every repository other than this one. The
/// pin below governs Kento's own checks; when Kento lints somebody else's Cargo
/// package, that package's toolchain governs, and a stale `stable` is what makes
/// Kento refuse a package needing a newer compiler than the machine has.
fn update_stable() -> Result<String, String> {
    let output = Command::new("rustup")
        .args(["update", "stable", "--no-self-update"])
        .output()
        .map_err(|error| format!("rustup is required for maintenance: {error}"))?;
    if !output.status.success() {
        let text = String::from_utf8_lossy(&output.stderr);
        let detail = text.lines().last().unwrap_or("no output").trim();
        return Err(format!("rustup update stable: {detail}"));
    }
    Ok(update_summary(&String::from_utf8_lossy(&output.stdout)))
}

/// The one line of `rustup update` worth repeating. It reports either that a
/// toolchain was updated or that it was already current, among progress noise.
fn update_summary(stdout: &str) -> String {
    stdout
        .lines()
        .find(|line| line.contains("unchanged") || line.contains("updated"))
        .unwrap_or("updated")
        .trim()
        .to_owned()
}

/// The newest stable Rust rustup knows about, when it is newer than the one in
/// use. `rustup check` reports it without installing anything.
fn newer_stable() -> Result<Option<String>, String> {
    let output = Command::new("rustup")
        .arg("check")
        .output()
        .map_err(|error| format!("rustup is required for maintenance: {error}"))?;
    let text = String::from_utf8_lossy(&output.stdout);
    Ok(text.lines().find_map(newer_stable_line))
}

/// One line of `rustup check`, parsed for a stable update. Some rustup
/// releases print "Update available" and others "update available", so the
/// match must not care about case: missing the capitalized form would report
/// "already the newest stable" over an update sitting right there.
fn newer_stable_line(line: &str) -> Option<String> {
    let lower = line.to_ascii_lowercase();
    let (head, _) = lower.split_once("update available")?;
    if !head.trim_start().starts_with("stable") {
        return None;
    }
    line.split("-> ")
        .nth(1)?
        .split_whitespace()
        .next()
        .map(str::to_owned)
}

fn pinned_channel(text: &str) -> Option<&str> {
    text.lines()
        .map(str::trim)
        .find_map(|line| line.strip_prefix("channel"))
        .and_then(|rest| rest.split_once('='))
        .map(|(_, value)| value.trim().trim_matches('"'))
}

fn verify(root: &Path) -> Result<(), String> {
    for (label, arguments) in [
        ("cargo fmt --check", vec!["fmt", "--check"]),
        (
            "cargo clippy",
            vec!["clippy", "--all-targets", "--", "-D", "warnings"],
        ),
    ] {
        let output = Command::new("cargo")
            .current_dir(root)
            .args(&arguments)
            .output()
            .map_err(|error| format!("{label} could not run: {error}"))?;
        if !output.status.success() {
            let text = String::from_utf8_lossy(&output.stderr);
            let detail = text
                .lines()
                .rev()
                .find(|line| !line.trim().is_empty())
                .unwrap_or("no output")
                .trim();
            return Err(format!("{label}: {detail}"));
        }
    }
    Ok(())
}

/// Reports the tools Kento depends on, and raises the Rust pin when a newer
/// stable passes the checks.
///
/// Returns the process exit status: `0` when nothing needed doing or the upgrade
/// held, `1` when an upgrade was available but did not pass and was reverted.
pub fn maintenance(root: &Path) -> Result<i32, String> {
    println!("tools");
    for (name, program, arguments) in [
        ("rustc     ", "rustc", ["--version"]),
        ("cargo     ", "cargo", ["--version"]),
        ("shellcheck", "shellcheck", ["--version"]),
    ] {
        let reported = tool_version(program, &arguments);
        let shown = reported
            .as_deref()
            .and_then(|text| text.lines().find(|line| line.contains('.')))
            .unwrap_or("not installed");
        println!("  {name}  {}", shown.trim());
    }

    println!("\ndefault toolchain");
    println!("  {}", update_stable()?);

    let pin_path = root.join(PIN);
    let Ok(pinned_text) = fs::read_to_string(&pin_path) else {
        println!("\nno {PIN} here, so there is no pin to move");
        return Ok(0);
    };
    let Some(current) = pinned_channel(&pinned_text) else {
        return Err(format!("{PIN} has no channel to read"));
    };
    println!("\npinned Rust  {current}");

    let Some(latest) = newer_stable()? else {
        println!("already the newest stable rustup offers; nothing to do");
        return Ok(0);
    };
    println!("newer stable {latest}\n");

    println!("raising the pin and running the checks Kento is responsible for");
    match raise_pin(root, current, &latest)? {
        Ok(()) => {
            println!("  passed — pin left at {latest}");
            println!("\nRun the full suite before committing: cargo test");
            Ok(0)
        }
        Err(reason) => {
            println!("  failed — pin reverted to {current}");
            println!("  {reason}");
            println!("\nThe newer toolchain reports something this code does not satisfy.");
            println!("Fix it, then run `kento maintenance` again.");
            Ok(1)
        }
    }
}

/// Writes the new pin, runs the checks, and puts the old pin back if they fail.
///
/// The outer `Result` is whether the file could be written and restored at all;
/// the inner one is the verdict on the new toolchain. Separating them matters:
/// a rejected toolchain is a normal outcome that must leave the file exactly as
/// it was found, while a failure to restore is the one case where this command
/// could leave a repository worse than it started.
fn raise_pin(root: &Path, current: &str, latest: &str) -> Result<Result<(), String>, String> {
    let pin_path = root.join(PIN);
    let original = fs::read_to_string(&pin_path)
        .map_err(|error| format!("cannot read {}: {error}", pin_path.display()))?;
    fs::write(&pin_path, original.replace(current, latest))
        .map_err(|error| format!("cannot write {}: {error}", pin_path.display()))?;
    match verify(root) {
        Ok(()) => Ok(Ok(())),
        Err(reason) => {
            fs::write(&pin_path, &original)
                .map_err(|error| format!("cannot restore {}: {error}", pin_path.display()))?;
            Ok(Err(reason))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn reads_the_release_date_rustc_prints() {
        assert_eq!(
            release_date("rustc 1.95.0 (59807616e 2026-04-14)"),
            Some((2026, 4, 14))
        );
        assert_eq!(
            release_date("rustc 1.90.0-nightly (abcdef123 2025-12-01)"),
            Some((2025, 12, 1))
        );
        // Nothing to read is not a date, and neither is a malformed one.
        assert_eq!(release_date("rustc 1.95.0"), None);
        assert_eq!(release_date("rustc 1.95.0 (59807616e)"), None);
        assert_eq!(release_date("rustc 1.95.0 (h 2026-13-14)"), None);
    }

    /// Day numbers only have to be consistent, not meaningful, but a wrong leap
    /// year would silently shift every age by a day.
    #[test]
    fn day_numbers_subtract_to_real_gaps() {
        assert_eq!(day_number(1970, 1, 1), 0);
        assert_eq!(day_number(2026, 4, 14) - day_number(2026, 4, 13), 1);
        assert_eq!(day_number(2027, 1, 1) - day_number(2026, 1, 1), 365);
        // 2024 is a leap year; 2100 is not, despite being divisible by four.
        assert_eq!(day_number(2025, 1, 1) - day_number(2024, 1, 1), 366);
        assert_eq!(day_number(2101, 1, 1) - day_number(2100, 1, 1), 365);
    }

    fn scratch(label: &str) -> PathBuf {
        use std::sync::atomic::{AtomicUsize, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};
        static SEQUENCE: AtomicUsize = AtomicUsize::new(0);
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!(
                "kento-{label}-{}-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .expect("clock")
                    .as_nanos(),
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
        fs::create_dir_all(path.join("src")).expect("directory");
        path
    }

    /// A crate pinned to a placeholder, so raising the pin swaps in the real
    /// toolchain this machine already has and nothing is downloaded.
    fn package(label: &str, body: &str) -> PathBuf {
        let root = scratch(label);
        fs::write(
            root.join("Cargo.toml"),
            "[package]\nname = \"probe\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\n[dependencies]\n",
        )
        .expect("manifest");
        fs::write(
            root.join(PIN),
            "[toolchain]\n# a comment that must survive\nchannel = \"PLACEHOLDER\"\n",
        )
        .expect("pin");
        fs::write(root.join("src/main.rs"), body).expect("source");
        root
    }

    fn installed() -> String {
        let version = tool_version("rustc", &["--version"]).expect("rustc");
        version
            .split_whitespace()
            .nth(1)
            .expect("version")
            .to_owned()
    }

    /// The path that could leave a repository worse than it started.
    ///
    /// A toolchain that fails its checks is an ordinary outcome, and the file
    /// has to come back exactly as it was — comment, spacing and all. If this
    /// regressed, the command meant to keep a repository current would be the
    /// thing that pinned it to a version that does not work, and the failure
    /// would surface later as an unrelated build error.
    #[test]
    fn a_rejected_toolchain_puts_the_pin_back_byte_for_byte() {
        let root = package("pin-revert", "fn main() { let x=1;println!(\"{x}\") }\n");
        let before = fs::read_to_string(root.join(PIN)).expect("pin");

        let verdict = raise_pin(&root, "PLACEHOLDER", &installed()).expect("pin is writable");

        assert!(verdict.is_err(), "unformatted source must fail the checks");
        assert_eq!(
            fs::read_to_string(root.join(PIN)).expect("pin"),
            before,
            "a rejected toolchain must leave the file exactly as it was"
        );
        let _ = fs::remove_dir_all(root);
    }

    /// And the other outcome: a toolchain that passes is kept, or the command
    /// would report success while quietly changing nothing.
    #[test]
    fn an_accepted_toolchain_is_kept() {
        let root = package("pin-keep", "fn main() {\n    println!(\"ok\");\n}\n");
        let latest = installed();

        let verdict = raise_pin(&root, "PLACEHOLDER", &latest).expect("pin is writable");

        assert!(verdict.is_ok(), "clean source must pass: {verdict:?}");
        let after = fs::read_to_string(root.join(PIN)).expect("pin");
        assert!(after.contains(&latest), "pin was not raised: {after}");
        assert!(
            after.contains("a comment that must survive"),
            "raising the pin rewrote the rest of the file: {after}"
        );
        let _ = fs::remove_dir_all(root);
    }

    /// Both sides of the threshold. Inverted, the note would appear on a fresh
    /// pin and stay silent on the stale one it exists for — and since it only
    /// writes to stderr, nothing else would ever notice.
    #[test]
    fn the_note_appears_only_once_the_pin_is_old() {
        let version = "rustc 1.95.0 (59807616e 2026-04-14)";
        assert_eq!(staleness_line(STALE_AFTER_DAYS, version), None);
        assert_eq!(staleness_line(0, version), None);
        let note =
            staleness_line(STALE_AFTER_DAYS + 1, version).expect("a note past the threshold");
        assert!(note.contains("91 days old"), "{note}");
        assert!(note.contains("1.95.0"), "{note}");
        assert!(!note.contains("rustc rustc"), "{note}");
        // The advice must own up to its side effect: maintenance edits the
        // repository it runs in, and the note fires in repositories the reader
        // may only be linting.
        assert!(note.contains("this repository's pin"), "{note}");
    }

    #[test]
    fn repeats_the_line_rustup_reports() {
        assert_eq!(
            update_summary("info: syncing\n  stable-aarch64 unchanged - rustc 1.97.1\n"),
            "stable-aarch64 unchanged - rustc 1.97.1"
        );
        assert_eq!(
            update_summary("info: downloading\n  stable updated - rustc 1.97.1 (from 1.95.0)\n"),
            "stable updated - rustc 1.97.1 (from 1.95.0)"
        );
        // Neither word present: say something rather than nothing.
        assert_eq!(update_summary("info: syncing channel updat\n"), "updated");
    }

    /// Both casings rustup has shipped, plus the two lines that must not
    /// parse: another tool's update, and a stable that is already current.
    #[test]
    fn reads_the_update_rustup_check_reports() {
        assert_eq!(
            newer_stable_line(
                "stable-aarch64-apple-darwin - update available: 1.96.0 (aaa 2026-05-01) -> 1.97.1 (8bab26f4f 2026-07-14)"
            ),
            Some("1.97.1".to_owned())
        );
        assert_eq!(
            newer_stable_line(
                "stable-x86_64-unknown-linux-gnu - Update available : 1.85.0 -> 1.86.0"
            ),
            Some("1.86.0".to_owned())
        );
        assert_eq!(
            newer_stable_line("rustup - update available: 1.29.0 -> 1.30.0"),
            None
        );
        assert_eq!(
            newer_stable_line(
                "stable-aarch64-apple-darwin - up to date: 1.97.1 (8bab26f4f 2026-07-14)"
            ),
            None
        );
    }

    #[test]
    fn reads_the_pinned_channel() {
        assert_eq!(
            pinned_channel("[toolchain]\n# a comment\nchannel = \"1.95.0\"\n"),
            Some("1.95.0")
        );
        assert_eq!(pinned_channel("[toolchain]\ncomponents = []\n"), None);
    }
}

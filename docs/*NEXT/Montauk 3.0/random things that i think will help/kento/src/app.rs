use crate::maintenance;
use crate::toolchain;
use crate::{Diagnostic, Language, install, lint_bytes};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::path::{Component, Path, PathBuf};
use std::process::Command;

/// The rules `.kentoexceptions` may name.
///
/// Only Kento's own. The rules that come from an external tool — `KENTO401`,
/// `KENTO402`, `KENTO501` — are deliberately absent: `kento ignore-audit`
/// validates exceptions offline and cannot re-run rustfmt, Clippy or ShellCheck,
/// so an exception naming one could never be shown to have gone stale. Suppress
/// those where the code is, with `#[allow(..)]` or `# shellcheck disable`.
const RULES: &[&str] = &[
    "KENTO001", "KENTO002", "KENTO003", "KENTO101", "KENTO102", "KENTO201", "KENTO301",
];
const SKIPPED_DIRS: &[&str] = &[
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "target",
    "dist",
    "build",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
];

#[derive(Clone, Copy, Eq, PartialEq)]
enum OutputFormat {
    Jsonl,
    Text,
}

struct Source {
    path: String,
    language: Language,
    bytes: Vec<u8>,
}

pub fn run_from_env() -> i32 {
    let arguments: Vec<OsString> = env::args_os().collect();
    let invoked = Path::new(&arguments[0])
        .file_name()
        .and_then(OsStr::to_str)
        .unwrap_or("kento");
    run_args(invoked, &arguments[1..])
}

pub fn run_args(invoked: &str, arguments: &[OsString]) -> i32 {
    let (command, rest) = if invoked == "kento" {
        let Some((command, rest)) = arguments.split_first() else {
            eprintln!("kento: missing command");
            return 2;
        };
        (command.to_string_lossy().into_owned(), rest)
    } else {
        (invoked.to_owned(), arguments)
    };
    match command.as_str() {
        "install" | "kento:install" => {
            let no_hook = match parse_install_arguments(rest) {
                Ok(value) => value,
                Err(message) => {
                    eprintln!("kento: {message}");
                    return 2;
                }
            };
            match install::install(&cwd(), no_hook) {
                Ok(note) => {
                    if let Some(note) = note {
                        eprintln!("kento: {note}");
                    }
                    0
                }
                Err(message) => {
                    eprintln!("kento: {message}");
                    2
                }
            }
        }
        "maintenance" | "kento:maintenance" => {
            if !rest.is_empty() {
                eprintln!("kento: maintenance takes no arguments");
                return 2;
            }
            match maintenance::maintenance(&repository_root(&cwd())) {
                Ok(code) => code,
                Err(message) => {
                    eprintln!("kento: {message}");
                    2
                }
            }
        }
        "uninstall" | "kento:uninstall" => {
            if !rest.is_empty() {
                eprintln!("kento: uninstall takes no arguments");
                return 2;
            }
            match install::uninstall() {
                Ok(()) => 0,
                Err(message) => {
                    eprintln!("kento: {message}");
                    2
                }
            }
        }
        _ => run_lint_command(&command, rest),
    }
}

fn cwd() -> PathBuf {
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn parse_install_arguments(arguments: &[OsString]) -> Result<bool, String> {
    match arguments {
        [] => Ok(false),
        [argument] if argument == "--no-hook" => Ok(true),
        _ => Err("install accepts only --no-hook".to_owned()),
    }
}

fn command(command: &str) -> Option<(Option<Language>, bool)> {
    Some(match command {
        "all" | "kento:all" => (None, false),
        "rs" | "kento:rs" => (Some(Language::Rust), false),
        "py" | "kento:py" => (Some(Language::Python), false),
        "js" | "kento:js" => (Some(Language::JavaScript), false),
        "ts" | "kento:ts" => (Some(Language::TypeScript), false),
        "css" | "kento:css" => (Some(Language::Css), false),
        "html" | "kento:html" => (Some(Language::Html), false),
        "sh" | "kento:sh" => (Some(Language::Shell), false),
        "ignore-audit" | "kento:ignore-audit" => (None, true),
        _ => return None,
    })
}

fn run_lint_command(command_name: &str, arguments: &[OsString]) -> i32 {
    let Some((language, audit)) = command(command_name) else {
        eprintln!("kento: unknown command `{command_name}`");
        return 2;
    };
    let parsed = match parse_lint_arguments(arguments) {
        Ok(value) => value,
        Err(message) => {
            eprintln!("kento: {message}");
            return 2;
        }
    };
    if audit && (parsed.staged || !parsed.paths.is_empty()) {
        eprintln!("kento: ignore-audit does not accept paths or --staged");
        return 2;
    }
    if parsed.staged && (audit || language.is_some()) {
        eprintln!("kento: --staged is only supported by `kento all`");
        return 2;
    }
    let root = repository_root(&cwd());
    let languages: Vec<Language> =
        language.map_or_else(|| Language::all().to_vec(), |item| vec![item]);
    let result = if parsed.staged {
        lint_staged(&root, &languages, parsed.format)
    } else if audit {
        audit_exceptions(&root, parsed.format)
    } else {
        lint_paths(&root, parsed.paths, &languages, parsed.format)
    };
    // On stderr, so it can never contaminate the diagnostics on stdout, and as a
    // note rather than a failure: a linter that refuses to lint because of its
    // own age fails for a reason that has nothing to do with the code.
    if let Some(note) = maintenance::staleness_note(&root) {
        eprintln!("kento: {note}");
    }
    match result {
        Ok(found) => {
            if found {
                1
            } else {
                0
            }
        }
        Err(message) => {
            eprintln!("kento: {message}");
            2
        }
    }
}

struct ParsedArguments {
    format: OutputFormat,
    paths: Vec<PathBuf>,
    staged: bool,
}

fn parse_lint_arguments(arguments: &[OsString]) -> Result<ParsedArguments, String> {
    let mut format = OutputFormat::Jsonl;
    let mut paths = Vec::new();
    let mut staged = false;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].to_string_lossy().as_ref() {
            "--format" => {
                index += 1;
                let Some(value) = arguments.get(index) else {
                    return Err("--format requires `jsonl` or `text`".to_owned());
                };
                format = match value.to_string_lossy().as_ref() {
                    "jsonl" => OutputFormat::Jsonl,
                    "text" => OutputFormat::Text,
                    _ => return Err("--format requires `jsonl` or `text`".to_owned()),
                };
            }
            "--staged" => {
                if staged {
                    return Err("duplicate --staged".to_owned());
                }
                staged = true;
            }
            value if value.starts_with('-') => return Err(format!("unknown option `{value}`")),
            _ => paths.push(PathBuf::from(&arguments[index])),
        }
        index += 1;
    }
    if staged && !paths.is_empty() {
        return Err("--staged cannot be combined with paths".to_owned());
    }
    Ok(ParsedArguments {
        format,
        paths,
        staged,
    })
}

fn repository_root(start: &Path) -> PathBuf {
    start
        .ancestors()
        .find(|ancestor| ancestor.join(".git").exists())
        .unwrap_or(start)
        .to_path_buf()
}

fn normalized_relative(root: &Path, path: &Path) -> String {
    let relative = path.strip_prefix(root).unwrap_or(path);
    let mut result = Vec::new();
    for component in relative.components() {
        match component {
            Component::Normal(item) => result.push(item.to_string_lossy().into_owned()),
            Component::ParentDir => result.push("..".to_owned()),
            Component::CurDir | Component::RootDir | Component::Prefix(_) => {}
        }
    }
    result.join("/")
}

fn is_skipped_directory(path: &Path) -> bool {
    let name = path.file_name().and_then(OsStr::to_str).unwrap_or("");
    SKIPPED_DIRS.contains(&name)
}

fn is_generated_file(path: &Path) -> bool {
    let name = path.file_name().and_then(OsStr::to_str).unwrap_or("");
    name.ends_with(".min.js") || name.ends_with(".min.css") || name.ends_with(".map")
}

fn is_valid_relative_path(path: &str, directory_allowed: bool) -> bool {
    let value = if directory_allowed {
        path.strip_suffix('/').unwrap_or(path)
    } else {
        path
    };
    !value.is_empty()
        && !path.starts_with('/')
        && !Path::new(path).is_absolute()
        && !value
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
        && !path.contains(['*', '?', '[', ']', '!'])
        && (!path.ends_with('/') || directory_allowed)
}

fn parse_ignore_bytes(bytes: &[u8]) -> Result<Vec<String>, String> {
    let text =
        std::str::from_utf8(bytes).map_err(|_| ".kentoignore: malformed UTF-8".to_owned())?;
    let mut entries = Vec::new();
    for (line_number, line) in text.lines().enumerate() {
        let entry = line.trim();
        if entry.is_empty() || entry.starts_with('#') {
            continue;
        }
        if !is_valid_relative_path(entry, true) {
            return Err(format!(".kentoignore:{}: invalid path", line_number + 1));
        }
        entries.push(entry.to_owned());
    }
    Ok(entries)
}

fn parse_ignore(root: &Path) -> Result<Vec<String>, String> {
    let path = root.join(".kentoignore");
    match fs::read(&path) {
        Ok(bytes) => parse_ignore_bytes(&bytes),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(format!("cannot read {}: {error}", path.display())),
    }
}

fn parse_exceptions_bytes(bytes: &[u8]) -> Result<BTreeSet<(String, String)>, String> {
    let text =
        std::str::from_utf8(bytes).map_err(|_| ".kentoexceptions: malformed UTF-8".to_owned())?;
    let mut exceptions = BTreeSet::new();
    for (line_number, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let fields: Vec<&str> = line.split_whitespace().collect();
        let rule = fields.first().copied().unwrap_or("");
        let path = fields.get(1).copied().unwrap_or("");
        let reason = fields.get(2..).unwrap_or_default().join(" ");
        if !RULES.contains(&rule)
            || !is_valid_relative_path(path, false)
            || reason.is_empty()
            || !exceptions.insert((rule.to_owned(), path.to_owned()))
        {
            return Err(format!(
                ".kentoexceptions:{}: malformed exception",
                line_number + 1
            ));
        }
    }
    Ok(exceptions)
}

fn read_exceptions(root: &Path) -> Result<BTreeSet<(String, String)>, String> {
    let path = root.join(".kentoexceptions");
    match fs::read(path) {
        Ok(bytes) => parse_exceptions_bytes(&bytes),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(BTreeSet::new()),
        Err(error) => Err(format!("cannot read .kentoexceptions: {error}")),
    }
}

fn ignored(path: &str, entries: &[String], is_directory: bool) -> bool {
    entries.iter().any(|entry| {
        entry.strip_suffix('/').map_or(entry == path, |directory| {
            (is_directory && path == directory) || path.starts_with(entry)
        })
    })
}

fn staged_path_is_skipped(path: &str) -> bool {
    let path = Path::new(path);
    path.parent().is_some_and(|parent| {
        parent.components().any(|component| {
            let Component::Normal(name) = component else {
                return false;
            };
            name.to_str()
                .is_some_and(|name| SKIPPED_DIRS.contains(&name))
        })
    }) || is_generated_file(path)
}

fn language_for(path: &Path, bytes: &[u8], languages: &[Language]) -> Option<Language> {
    languages
        .iter()
        .copied()
        .find(|language| language.matches(path, bytes))
}

fn discover(
    root: &Path,
    starts: Vec<(PathBuf, bool)>,
    languages: &[Language],
    ignore: &[String],
) -> Result<Vec<Source>, String> {
    let mut sources = Vec::new();
    let mut pending = starts;
    while let Some((path, explicit_file)) = pending.pop() {
        let metadata = fs::symlink_metadata(&path)
            .map_err(|error| format!("cannot inspect {}: {error}", path.display()))?;
        if metadata.file_type().is_symlink() {
            continue;
        }
        if metadata.is_dir() {
            if is_skipped_directory(&path) {
                continue;
            }
            let relative = normalized_relative(root, &path);
            if !explicit_file && !relative.is_empty() && ignored(&relative, ignore, true) {
                continue;
            }
            for entry in fs::read_dir(&path)
                .map_err(|error| format!("cannot read {}: {error}", path.display()))?
            {
                let entry = entry.map_err(|error| error.to_string())?;
                pending.push((entry.path(), false));
            }
            continue;
        }
        if !metadata.is_file() || is_generated_file(&path) {
            continue;
        }
        let relative = normalized_relative(root, &path);
        if !explicit_file && ignored(&relative, ignore, false) {
            continue;
        }
        let bytes =
            fs::read(&path).map_err(|error| format!("cannot read {}: {error}", path.display()))?;
        if let Some(language) = language_for(&path, &bytes, languages) {
            sources.push(Source {
                path: relative,
                language,
                bytes,
            });
        }
    }
    sources.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(sources)
}

fn lint_paths(
    root: &Path,
    paths: Vec<PathBuf>,
    languages: &[Language],
    format: OutputFormat,
) -> Result<bool, String> {
    let exceptions = read_exceptions(root)?;
    let ignore = parse_ignore(root)?;
    let starts = if paths.is_empty() {
        vec![(root.to_path_buf(), false)]
    } else {
        paths
            .into_iter()
            .map(|path| {
                let absolute = if path.is_absolute() {
                    path
                } else {
                    cwd().join(path)
                };
                let is_file = fs::symlink_metadata(&absolute)
                    .map(|metadata| metadata.is_file())
                    .unwrap_or(false);
                (absolute, is_file)
            })
            .collect()
    };
    let sources = discover(root, starts, languages, &ignore)?;
    let diagnostics = lint_with_toolchain(root, sources, &exceptions)?;
    render(&diagnostics, format);
    Ok(!diagnostics.is_empty())
}

/// Kento's own rules plus whatever rustfmt and Clippy report for the Rust files
/// this run discovered.
fn lint_with_toolchain(
    root: &Path,
    sources: Vec<Source>,
    exceptions: &BTreeSet<(String, String)>,
) -> Result<Vec<Diagnostic>, String> {
    let rust: BTreeSet<String> = sources
        .iter()
        .filter(|source| source.language == Language::Rust)
        .map(|source| source.path.clone())
        .collect();
    let shell: BTreeSet<String> = sources
        .iter()
        .filter(|source| source.language == Language::Shell)
        .map(|source| source.path.clone())
        .collect();
    let mut diagnostics = lint_sources(sources, exceptions);
    diagnostics.extend(toolchain::rust_checks(root, &rust)?);
    diagnostics.extend(toolchain::shell_checks(root, &shell)?);
    diagnostics.sort();
    Ok(diagnostics)
}

fn lint_sources(sources: Vec<Source>, exceptions: &BTreeSet<(String, String)>) -> Vec<Diagnostic> {
    let mut diagnostics = Vec::new();
    for source in sources {
        for diagnostic in lint_bytes(source.language, &source.bytes, &source.path) {
            if !exceptions.contains(&(diagnostic.rule_id.to_owned(), source.path.clone())) {
                diagnostics.push(diagnostic);
            }
        }
    }
    diagnostics.sort();
    diagnostics
}

fn audit_exceptions(root: &Path, format: OutputFormat) -> Result<bool, String> {
    let exceptions = read_exceptions(root)?;
    let mut diagnostics = Vec::new();
    for (rule, path) in exceptions {
        let file = root.join(&path);
        let bytes = match fs::read(&file) {
            Ok(bytes) => bytes,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                diagnostics.push(audit_diagnostic(
                    path,
                    "exception path does not exist",
                    "Remove this exception or restore the file.",
                ));
                continue;
            }
            Err(error) => return Err(format!("cannot read {}: {error}", file.display())),
        };
        let Some(language) = Language::all()
            .into_iter()
            .find(|language| language.matches(&file, &bytes))
        else {
            diagnostics.push(audit_diagnostic(
                path,
                "exception rule does not apply to this file type",
                "Remove this unsupported exception.",
            ));
            continue;
        };
        let supported = match rule.as_str() {
            "KENTO101" | "KENTO102" => language == Language::Python,
            "KENTO201" => language == Language::Html,
            "KENTO301" => language == Language::Css,
            _ => true,
        };
        if !supported {
            diagnostics.push(audit_diagnostic(
                path,
                "exception rule does not apply to this file type",
                "Remove this unsupported exception.",
            ));
        } else if !lint_bytes(language, &bytes, &path)
            .iter()
            .any(|diagnostic| diagnostic.rule_id == rule)
        {
            diagnostics.push(audit_diagnostic(
                path,
                "exception no longer suppresses a finding",
                "Remove the stale exception.",
            ));
        }
    }
    diagnostics.sort();
    render(&diagnostics, format);
    Ok(!diagnostics.is_empty())
}

fn audit_diagnostic(path: String, message: &str, help: &str) -> Diagnostic {
    Diagnostic {
        rule_id: "KENTO901",
        path,
        line: 1,
        column: 1,
        end_line: 1,
        end_column: 1,
        message: message.to_owned(),
        help: help.to_owned(),
    }
}

fn render(diagnostics: &[Diagnostic], format: OutputFormat) {
    for diagnostic in diagnostics {
        match format {
            OutputFormat::Text => println!(
                "{} {}:{}:{}: {} — {}",
                diagnostic.rule_id,
                diagnostic.path,
                diagnostic.line,
                diagnostic.column,
                diagnostic.message,
                diagnostic.help
            ),
            OutputFormat::Jsonl => println!(
                "{{\"schema\":\"kento.diagnostic/v1\",\"rule_id\":\"{}\",\"path\":\"{}\",\"line\":{},\"column\":{},\"end_line\":{},\"end_column\":{},\"message\":\"{}\",\"help\":\"{}\"}}",
                diagnostic.rule_id,
                json_escape(&diagnostic.path),
                diagnostic.line,
                diagnostic.column,
                diagnostic.end_line,
                diagnostic.end_column,
                json_escape(&diagnostic.message),
                json_escape(&diagnostic.help),
            ),
        }
    }
}

fn json_escape(value: &str) -> String {
    let mut result = String::new();
    for character in value.chars() {
        match character {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\u{08}' => result.push_str("\\b"),
            '\u{0c}' => result.push_str("\\f"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            character if character <= '\u{1f}' => {
                use std::fmt::Write;
                let _ = write!(result, "\\u{:04x}", character as u32);
            }
            character => result.push(character),
        }
    }
    result
}

fn git(root: &Path, arguments: &[&str]) -> Result<Vec<u8>, String> {
    let output = Command::new("git")
        .current_dir(root)
        .args(arguments)
        .output()
        .map_err(|error| format!("Git is required for --staged: {error}"))?;
    if output.status.success() {
        Ok(output.stdout)
    } else {
        Err(format!(
            "Git command failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ))
    }
}

fn lint_staged(root: &Path, languages: &[Language], format: OutputFormat) -> Result<bool, String> {
    let status = git(
        root,
        &[
            "diff",
            "--cached",
            "--name-status",
            "-z",
            "--diff-filter=ACMR",
        ],
    )?;
    let selected = staged_paths(&status)?;
    let stages = staged_entries(&git(root, &["ls-files", "--stage", "-z"])?)?;
    let exception_bytes = stages
        .get(".kentoexceptions")
        .map(|(_, oid)| git(root, &["cat-file", "blob", oid]))
        .transpose()?;
    let exceptions = exception_bytes
        .as_deref()
        .map_or_else(|| Ok(BTreeSet::new()), parse_exceptions_bytes)?;
    let ignore_bytes = stages
        .get(".kentoignore")
        .map(|(_, oid)| git(root, &["cat-file", "blob", oid]))
        .transpose()?;
    let ignore = ignore_bytes
        .as_deref()
        .map_or_else(|| Ok(Vec::new()), parse_ignore_bytes)?;
    let mut sources = Vec::new();
    for path in selected {
        let Some((mode, oid)) = stages.get(&path) else {
            continue;
        };
        if mode != "100644" && mode != "100755" {
            continue;
        }
        if staged_path_is_skipped(&path) || ignored(&path, &ignore, false) {
            continue;
        }
        let bytes = git(root, &["cat-file", "blob", oid])?;
        let file = Path::new(&path);
        if let Some(language) = language_for(file, &bytes, languages) {
            sources.push(Source {
                path,
                language,
                bytes,
            });
        }
    }
    let diagnostics = lint_with_toolchain(root, sources, &exceptions)?;
    render(&diagnostics, format);
    Ok(!diagnostics.is_empty())
}

fn staged_paths(output: &[u8]) -> Result<Vec<String>, String> {
    let fields: Vec<&[u8]> = output
        .split(|byte| *byte == 0)
        .filter(|field| !field.is_empty())
        .collect();
    let mut paths = Vec::new();
    let mut index = 0;
    while index < fields.len() {
        let status = std::str::from_utf8(fields[index])
            .map_err(|_| "Git returned a non-UTF-8 status".to_owned())?;
        index += 1;
        let renamed = status.starts_with('R') || status.starts_with('C');
        let path_index = if renamed {
            index += 1;
            index
        } else {
            index
        };
        let Some(path) = fields.get(path_index) else {
            return Err("malformed NUL-delimited Git status".to_owned());
        };
        paths.push(
            std::str::from_utf8(path)
                .map_err(|_| "Git returned a non-UTF-8 path".to_owned())?
                .to_owned(),
        );
        index += 1;
    }
    paths.sort();
    paths.dedup();
    Ok(paths)
}

fn staged_entries(output: &[u8]) -> Result<BTreeMap<String, (String, String)>, String> {
    let mut entries = BTreeMap::new();
    for record in output
        .split(|byte| *byte == 0)
        .filter(|record| !record.is_empty())
    {
        let Some(tab) = record.iter().position(|byte| *byte == b'\t') else {
            return Err("malformed NUL-delimited Git index".to_owned());
        };
        let header = std::str::from_utf8(&record[..tab])
            .map_err(|_| "Git returned malformed index data".to_owned())?;
        let path = std::str::from_utf8(&record[tab + 1..])
            .map_err(|_| "Git returned a non-UTF-8 path".to_owned())?;
        let fields: Vec<&str> = header.split_whitespace().collect();
        if fields.len() == 3 && fields[2] == "0" {
            entries.insert(
                path.to_owned(),
                (fields[0].to_owned(), fields[1].to_owned()),
            );
        }
    }
    Ok(entries)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    /// The counter is what makes this unique rather than merely unlikely to
    /// collide: the clock is coarser than a thread switch, so two tests can read
    /// the same value, and two tests sharing a directory would delete each
    /// other's fixtures.
    fn temporary_dir(label: &str) -> PathBuf {
        static SEQUENCE: AtomicUsize = AtomicUsize::new(0);
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let process = std::process::id();
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!("kento-{label}-{process}-{unique}-{sequence}"));
        fs::create_dir_all(&path).expect("directory");
        path
    }

    #[test]
    fn parses_commands_and_options() {
        assert_eq!(
            command("kento:js"),
            Some((Some(Language::JavaScript), false))
        );
        assert!(command("bad").is_none());
        assert!(
            parse_lint_arguments(&[OsString::from("--format"), OsString::from("bad")]).is_err()
        );
        assert!(parse_lint_arguments(&[OsString::from("--staged"), OsString::from("x")]).is_err());
    }

    #[test]
    fn validates_ignore_and_exception_syntax() {
        let root = temporary_dir("syntax");
        fs::write(root.join(".kentoignore"), "src/\n# okay\n").expect("ignore");
        assert_eq!(parse_ignore(&root).expect("parse"), vec!["src/"]);
        assert!(ignored("src", &["src/".to_owned()], true));
        assert!(!ignored("src", &["src/".to_owned()], false));
        assert!(ignored("src/file.py", &["src/".to_owned()], false));
        assert!(!ignored("src.py", &["src/".to_owned()], false));
        assert!(!ignored("src-old/file.py", &["src/".to_owned()], false));
        assert!(staged_path_is_skipped("build/file.py"));
        assert!(!staged_path_is_skipped("build"));
        // Only a normal component can name a skipped directory. A root or
        // parent component names no directory at all, so it must not be read as
        // one and skip the file wholesale.
        assert!(!staged_path_is_skipped("/a/file.py"));
        fs::write(root.join(".kentoignore"), "../bad\n").expect("invalid");
        assert!(parse_ignore(&root).is_err());
        assert!(parse_exceptions_bytes(b"KENTO101 x.py reason\n").is_ok());
        assert!(parse_exceptions_bytes(b"KENTO999 x.py reason\n").is_err());
        assert!(parse_exceptions_bytes(b"KENTO101 x.py\n").is_err());
        assert!(parse_exceptions_bytes(b"\xff").is_err());
        // Blank and comment lines carry no exception and are not malformed ones.
        assert!(parse_exceptions_bytes(b"# comment\n\nKENTO101 x.py reason\n").is_ok());
        // An exception names one file, so a directory path cannot be one.
        assert!(parse_exceptions_bytes(b"KENTO101 x.py/ reason\n").is_err());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn discovery_skips_implicit_ignored_files_but_not_explicit_files() {
        let root = temporary_dir("discover");
        fs::create_dir_all(root.join(".git")).expect("git");
        fs::write(root.join(".kentoignore"), "ignored.py\n").expect("ignore");
        fs::write(root.join("ignored.py"), "except:\n").expect("source");
        let ignored = discover(
            &root,
            vec![(root.clone(), false)],
            &[Language::Python],
            &parse_ignore(&root).expect("ignore"),
        )
        .expect("discover");
        assert!(ignored.is_empty());
        let explicit = discover(
            &root,
            vec![(root.join("ignored.py"), true)],
            &[Language::Python],
            &parse_ignore(&root).expect("ignore"),
        )
        .expect("discover");
        assert_eq!(explicit.len(), 1);
        let _ = fs::remove_dir_all(root);
    }

    /// A trailing slash names a directory, so it must not match a file of the
    /// same name — discovery has to pass the entry's real kind, not a constant.
    #[test]
    fn a_directory_pattern_does_not_ignore_a_file_of_that_name() {
        let root = temporary_dir("ignore-kind");
        fs::create_dir_all(root.join(".git")).expect("git");
        fs::write(root.join(".kentoignore"), "x.py/\n").expect("ignore");
        fs::write(root.join("x.py"), "except:\n").expect("source");
        let sources = discover(
            &root,
            vec![(root.clone(), false)],
            &[Language::Python],
            &parse_ignore(&root).expect("ignore"),
        )
        .expect("discover");
        assert_eq!(sources.len(), 1);
        let _ = fs::remove_dir_all(root);
    }

    /// An ignored directory is not merely filtered out of the results: it is
    /// never read. A tree Kento was told to leave alone must not be able to fail
    /// the run, so an unreadable one has to stay unreachable.
    #[test]
    fn an_ignored_directory_is_never_read() {
        let root = temporary_dir("ignore-unread");
        fs::create_dir_all(root.join(".git")).expect("git");
        fs::write(root.join(".kentoignore"), "third_party/\n").expect("ignore");
        let vendor = root.join("third_party");
        fs::create_dir(&vendor).expect("vendor");
        fs::write(vendor.join("x.py"), "except:\n").expect("source");
        // The unlock has to survive a panic inside `discover`. Under a mutation
        // run panicking is the normal outcome, and an unreadable directory left
        // in `target/` cannot be deleted by the next run either — one aborted
        // test would otherwise wedge every sweep after it.
        struct Unlock(PathBuf);
        impl Drop for Unlock {
            fn drop(&mut self) {
                let _ = fs::set_permissions(&self.0, fs::Permissions::from_mode(0o700));
            }
        }
        let unlock = Unlock(vendor.clone());

        fs::set_permissions(&vendor, fs::Permissions::from_mode(0o000)).expect("lock");
        let readable = fs::read_dir(&vendor).is_ok();
        let sources = discover(
            &root,
            vec![(root.clone(), false)],
            &[Language::Python],
            &parse_ignore(&root).expect("ignore"),
        );
        drop(unlock);
        assert!(
            !readable,
            "reads of {} are still permitted; run as a non-root user on a filesystem that enforces mode bits",
            vendor.display()
        );
        assert!(sources.expect("discover").is_empty());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn sorts_and_escapes_diagnostics() {
        assert_eq!(json_escape("a\"\\\n\u{0001}"), "a\\\"\\\\\\n\\u0001");
        assert_eq!(json_escape("a\tb\rc\u{08}d\u{0c}e"), "a\\tb\\rc\\bd\\fe");
        let mut diagnostics = [
            Diagnostic {
                rule_id: "KENTO002",
                path: "b".to_owned(),
                line: 1,
                column: 1,
                end_line: 1,
                end_column: 1,
                message: "x".to_owned(),
                help: "x".to_owned(),
            },
            Diagnostic {
                rule_id: "KENTO001",
                path: "a".to_owned(),
                line: 1,
                column: 1,
                end_line: 1,
                end_column: 1,
                message: "x".to_owned(),
                help: "x".to_owned(),
            },
        ];
        diagnostics.sort();
        assert_eq!(diagnostics[0].path, "a");
    }

    #[test]
    fn parses_renamed_nul_statuses() {
        let paths = staged_paths(b"R100\0old name.py\0new name.py\0A\0x.py\0").expect("paths");
        assert_eq!(paths, vec!["new name.py", "x.py"]);
    }
}

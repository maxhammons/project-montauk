use std::collections::BTreeSet;
use std::env;
use std::fs::{self, File};
use std::io::{ErrorKind, Read};
use std::path::{Path, PathBuf};
use std::process::Command;

const ALIASES: &[&str] = &[
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
];
const STAGING: &str = ".kento.install.tmp";
const PREVIOUS: &str = ".kento.previous.tmp";
const BLOCK_START: &str = "# >>> kento managed block >>>";
const BLOCK_END: &str = "# <<< kento managed block <<<";
const MANIFEST_VERSION: &str = "kento-install-v1";

fn home() -> Result<PathBuf, String> {
    env::var_os("HOME")
        .map(PathBuf::from)
        .ok_or_else(|| "HOME is not set".to_owned())
}

fn bin_dir() -> Result<PathBuf, String> {
    Ok(home()?.join(".local/bin"))
}

fn state_root() -> Result<PathBuf, String> {
    Ok(home()?.join(".local/share/kento"))
}

fn state_dir() -> Result<PathBuf, String> {
    Ok(state_root()?.join("hooks"))
}

fn manifest_path() -> Result<PathBuf, String> {
    Ok(state_root()?.join("installation"))
}

fn shell_quote(value: &Path) -> String {
    let text = value.to_string_lossy();
    format!("'{}'", text.replace('\'', "'\"'\"'"))
}

fn block(binary: &Path) -> String {
    format!(
        "{BLOCK_START}\n{} all --staged\nstatus=$?\n[ \"$status\" -eq 0 ] || exit \"$status\"\n{BLOCK_END}\n",
        shell_quote(binary)
    )
}

fn marker_count(text: &str) -> usize {
    text.matches(BLOCK_START).count() + text.matches(BLOCK_END).count()
}

fn compatible_shebang(text: &str) -> bool {
    let Some(line) = text.lines().next() else {
        return false;
    };
    if !line.starts_with("#!") {
        return false;
    }
    let executable = line[2..].split_whitespace().last().unwrap_or("");
    matches!(executable, "sh" | "bash" | "zsh")
        || executable.ends_with("/sh")
        || executable.ends_with("/bash")
        || executable.ends_with("/zsh")
}

fn git(root: &Path, arguments: &[&str]) -> Result<Vec<u8>, String> {
    let output = Command::new("git")
        .current_dir(root)
        .args(arguments)
        .output()
        .map_err(|error| format!("Git is required for hook integration: {error}"))?;
    if output.status.success() {
        Ok(output.stdout)
    } else {
        Err(format!(
            "Git command failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ))
    }
}

fn hook_path(root: &Path) -> Result<PathBuf, String> {
    let configured = Command::new("git")
        .current_dir(root)
        .args(["config", "--get", "core.hooksPath"])
        .output()
        .map_err(|error| format!("Git is required for hook integration: {error}"))?;
    if !configured.status.success() && configured.status.code() != Some(1) {
        return Err(format!(
            "Git command failed: {}",
            String::from_utf8_lossy(&configured.stderr).trim()
        ));
    }
    if !configured.stdout.is_empty() {
        return Err("refusing nonempty core.hooksPath".to_owned());
    }
    let path = git(root, &["rev-parse", "--git-path", "hooks"])?;
    let path =
        String::from_utf8(path).map_err(|_| "Git returned a non-UTF-8 hooks path".to_owned())?;
    let path = PathBuf::from(path.trim());
    Ok(if path.is_absolute() {
        path
    } else {
        root.join(path)
    }
    .join("pre-commit"))
}

fn record_name(path: &Path) -> String {
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in path.to_string_lossy().as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("{hash:016x}")
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Fingerprint {
    size: u64,
    hash: u128,
}

fn fingerprint(path: &Path) -> Result<Fingerprint, String> {
    const OFFSET: u128 = 0x6c62_272e_07bb_0142_62b8_2175_6295_c58d;
    const PRIME: u128 = 0x0000_0000_0100_0000_0000_0000_0000_013b;

    let mut file =
        File::open(path).map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    let mut buffer = [0_u8; 16 * 1024];
    let mut result = Fingerprint {
        size: 0,
        hash: OFFSET,
    };
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
        if count == 0 {
            break;
        }
        result.size += count as u64;
        for byte in &buffer[..count] {
            result.hash ^= u128::from(*byte);
            result.hash = result.hash.wrapping_mul(PRIME);
        }
    }
    Ok(result)
}

fn manifest_text(value: Fingerprint) -> String {
    format!(
        "{MANIFEST_VERSION}\nsize={}\nhash={:032x}\n",
        value.size, value.hash
    )
}

fn parse_manifest(text: &str) -> Result<Fingerprint, String> {
    let Some(text) = text.strip_suffix('\n') else {
        return Err("malformed Kento installation manifest".to_owned());
    };
    let lines: Vec<&str> = text.split('\n').collect();
    if lines.len() != 3 || lines[0] != MANIFEST_VERSION {
        return Err("malformed Kento installation manifest".to_owned());
    }
    let size = lines[1]
        .strip_prefix("size=")
        .and_then(|value| value.parse().ok())
        .ok_or_else(|| "malformed Kento installation manifest".to_owned())?;
    let hash = lines[2]
        .strip_prefix("hash=")
        .filter(|value| value.len() == 32)
        .and_then(|value| u128::from_str_radix(value, 16).ok())
        .ok_or_else(|| "malformed Kento installation manifest".to_owned())?;
    Ok(Fingerprint { size, hash })
}

fn read_manifest() -> Result<Option<Fingerprint>, String> {
    let path = manifest_path()?;
    match fs::read_to_string(&path) {
        Ok(text) => parse_manifest(&text).map(Some),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(None),
        Err(error) => Err(format!("cannot read {}: {error}", path.display())),
    }
}

fn write_manifest(value: Fingerprint) -> Result<(), String> {
    let root = state_root()?;
    fs::create_dir_all(&root)
        .map_err(|error| format!("cannot create {}: {error}", root.display()))?;
    let path = manifest_path()?;
    let temporary = root.join(".installation.tmp");
    match fs::symlink_metadata(&temporary) {
        Ok(_) => {
            return Err(format!(
                "refusing unexpected temporary state {}",
                temporary.display()
            ));
        }
        Err(error) if error.kind() == ErrorKind::NotFound => {}
        Err(error) => {
            return Err(format!(
                "cannot inspect temporary state {}: {error}",
                temporary.display()
            ));
        }
    }
    fs::write(&temporary, manifest_text(value))
        .map_err(|error| format!("cannot write installation state: {error}"))?;
    if let Err(error) = fs::rename(&temporary, &path) {
        return match fs::remove_file(&temporary) {
            Ok(()) => Err(format!("cannot publish installation state: {error}")),
            Err(cleanup) => Err(format!(
                "cannot publish installation state: {error}; cannot remove {}: {cleanup}",
                temporary.display()
            )),
        };
    }
    Ok(())
}

fn validate_state_layout() -> Result<(), String> {
    let root = state_root()?;
    let metadata = match fs::symlink_metadata(&root) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(format!("cannot inspect {}: {error}", root.display())),
    };
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return Err("malformed Kento installation state".to_owned());
    }
    for entry in
        fs::read_dir(&root).map_err(|error| format!("cannot read installation state: {error}"))?
    {
        let entry = entry.map_err(|error| format!("cannot read installation state: {error}"))?;
        let name = entry.file_name();
        let file_type = entry
            .file_type()
            .map_err(|error| format!("cannot inspect installation state: {error}"))?;
        if name == "installation" {
            if !file_type.is_file() || file_type.is_symlink() {
                return Err("malformed Kento installation state".to_owned());
            }
        } else if name == "hooks" {
            if !file_type.is_dir() || file_type.is_symlink() {
                return Err("malformed Kento installation state".to_owned());
            }
        } else {
            return Err(format!(
                "unexpected Kento installation state {}",
                entry.path().display()
            ));
        }
    }
    Ok(())
}

fn alias_paths(bin: &Path) -> Vec<PathBuf> {
    ALIASES.iter().map(|alias| bin.join(alias)).collect()
}

fn verify_aliases(aliases: &[PathBuf]) -> Result<(), String> {
    for alias in aliases {
        match fs::symlink_metadata(alias) {
            Ok(metadata)
                if metadata.file_type().is_symlink()
                    && fs::read_link(alias).map_err(|error| {
                        format!("cannot inspect {}: {error}", alias.display())
                    })? == Path::new("kento") => {}
            Ok(_) => {
                return Err(format!("refusing unmanaged command {}", alias.display()));
            }
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => return Err(format!("cannot inspect {}: {error}", alias.display())),
        }
    }
    Ok(())
}

fn verify_binary(binary: &Path, expected: Fingerprint) -> Result<(), String> {
    let metadata = match fs::symlink_metadata(binary) {
        Ok(metadata) => metadata,
        // An interrupted uninstall can leave the manifest behind after the
        // binary is gone. Refusing here would wedge `install` and `uninstall`
        // alike, and a file that no longer exists has no ownership to prove.
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(()),
        Err(error) => {
            return Err(format!("cannot inspect installed Kento binary: {error}"));
        }
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return Err("installed Kento binary is no longer a managed regular file".to_owned());
    }
    if fingerprint(binary)? != expected {
        return Err("installed Kento binary has changed; refusing unsafe replacement".to_owned());
    }
    Ok(())
}

fn record_contents(path: &Path) -> Result<String, String> {
    let path = path
        .to_str()
        .ok_or_else(|| "non-UTF-8 hook paths are not supported".to_owned())?;
    if path.contains('\n') {
        return Err("hook paths containing newlines are not supported".to_owned());
    }
    Ok(format!("{path}\n"))
}

fn stage_record(path: &Path) -> Result<(PathBuf, PathBuf), String> {
    let directory = state_dir()?;
    fs::create_dir_all(&directory)
        .map_err(|error| format!("cannot create state directory: {error}"))?;
    let name = record_name(path);
    let record = directory.join(&name);
    let temporary = directory.join(format!(".{name}.tmp"));
    for candidate in [&record, &temporary] {
        match fs::symlink_metadata(candidate) {
            Ok(_) => {
                return Err(format!(
                    "refusing unexpected hook state {}",
                    candidate.display()
                ));
            }
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => {
                return Err(format!(
                    "cannot inspect hook state {}: {error}",
                    candidate.display()
                ));
            }
        }
    }
    fs::write(&temporary, record_contents(path)?)
        .map_err(|error| format!("cannot stage hook state: {error}"))?;
    Ok((temporary, record))
}

fn read_records() -> Result<Vec<(PathBuf, PathBuf)>, String> {
    let directory = state_dir()?;
    let entries = match fs::read_dir(&directory) {
        Ok(entries) => entries,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(Vec::new()),
        Err(error) => return Err(format!("cannot read hook state: {error}")),
    };
    let mut records = Vec::new();
    let mut paths = BTreeSet::new();
    for entry in entries {
        let entry = entry.map_err(|error| format!("cannot read hook state: {error}"))?;
        let file_type = entry
            .file_type()
            .map_err(|error| format!("cannot inspect hook state: {error}"))?;
        if !file_type.is_file() || file_type.is_symlink() {
            return Err("malformed hook state record".to_owned());
        }
        let contents = fs::read_to_string(entry.path())
            .map_err(|_| "malformed hook state record".to_owned())?;
        let Some(path) = contents.strip_suffix('\n') else {
            return Err("malformed hook state record".to_owned());
        };
        if path.is_empty() || path.contains('\n') {
            return Err("malformed hook state record".to_owned());
        }
        let path = PathBuf::from(path);
        if !path.is_absolute()
            || entry.file_name().to_string_lossy() != record_name(&path)
            || !paths.insert(path.clone())
        {
            return Err("malformed hook state record".to_owned());
        }
        records.push((entry.path(), path));
    }
    records.sort_by(|left, right| left.1.cmp(&right.1));
    Ok(records)
}

fn path_in_path(path: &Path) -> bool {
    let Some(paths) = env::var_os("PATH") else {
        return false;
    };
    env::split_paths(&paths).any(|candidate| candidate == path)
}

struct HookPlan {
    path: PathBuf,
    contents: Option<String>,
    original: Option<String>,
    permissions: Option<fs::Permissions>,
}

fn preflight_hook(
    root: &Path,
    binary: &Path,
    records: &[(PathBuf, PathBuf)],
) -> Result<HookPlan, String> {
    let hook = hook_path(root)?;
    let recorded = records.iter().any(|(_, path)| path == &hook);
    let metadata = match fs::symlink_metadata(&hook) {
        Ok(metadata) => Some(metadata),
        Err(error) if error.kind() == ErrorKind::NotFound => None,
        Err(error) => return Err(format!("cannot inspect hook {}: {error}", hook.display())),
    };
    let Some(metadata) = metadata else {
        if recorded {
            return Err(format!(
                "recorded hook {} is missing its Kento block",
                hook.display()
            ));
        }
        return Ok(HookPlan {
            path: hook,
            contents: Some(format!("#!/bin/sh\n{}", block(binary))),
            original: None,
            permissions: None,
        });
    };
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return Err(format!(
            "existing pre-commit hook {} is not a regular file",
            hook.display()
        ));
    }
    let existing = fs::read_to_string(&hook)
        .map_err(|error| format!("cannot read hook {}: {error}", hook.display()))?;
    let expected = block(binary);
    match marker_count(&existing) {
        0 if recorded => Err(format!(
            "recorded hook {} is missing its Kento block",
            hook.display()
        )),
        0 => {
            if !compatible_shebang(&existing) {
                return Err("existing pre-commit hook needs a sh/bash/zsh shebang".to_owned());
            }
            let first_newline = existing
                .find('\n')
                .ok_or_else(|| "existing pre-commit hook has no shebang newline".to_owned())?;
            let mut result = String::new();
            result.push_str(&existing[..=first_newline]);
            result.push_str(&expected);
            result.push_str(&existing[first_newline + 1..]);
            Ok(HookPlan {
                path: hook,
                contents: Some(result),
                original: Some(existing),
                permissions: Some(metadata.permissions()),
            })
        }
        2 if recorded && existing.matches(&expected).count() == 1 => Ok(HookPlan {
            path: hook,
            contents: None,
            original: Some(existing),
            permissions: Some(metadata.permissions()),
        }),
        _ => Err("refusing hook with unmanaged or malformed Kento markers".to_owned()),
    }
}

fn restore_hook(plan: &HookPlan) -> Result<(), String> {
    if let Some(original) = &plan.original {
        fs::write(&plan.path, original)
            .map_err(|error| format!("cannot restore hook {}: {error}", plan.path.display()))?;
        if let Some(permissions) = &plan.permissions {
            fs::set_permissions(&plan.path, permissions.clone()).map_err(|error| {
                format!("cannot restore hook mode {}: {error}", plan.path.display())
            })?;
        }
    } else {
        match fs::remove_file(&plan.path) {
            Ok(()) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => {
                return Err(format!(
                    "cannot remove new hook {} during rollback: {error}",
                    plan.path.display()
                ));
            }
        }
    }
    Ok(())
}

fn apply_hook(plan: HookPlan) -> Result<(), String> {
    let Some(contents) = &plan.contents else {
        return Ok(());
    };
    let (staged_record, record) = stage_record(&plan.path)?;
    if let Some(parent) = plan.path.parent()
        && let Err(error) = fs::create_dir_all(parent)
    {
        let cleanup = fs::remove_file(&staged_record);
        return Err(match cleanup {
            Ok(()) => format!("cannot create hooks directory: {error}"),
            Err(cleanup) => format!(
                "cannot create hooks directory: {error}; cannot remove {}: {cleanup}",
                staged_record.display()
            ),
        });
    }
    let update = fs::write(&plan.path, contents)
        .map_err(|error| format!("cannot write hook: {error}"))
        .and_then(|()| {
            if let Some(permissions) = &plan.permissions {
                fs::set_permissions(&plan.path, permissions.clone())
                    .map_err(|error| format!("cannot preserve hook mode: {error}"))
            } else {
                make_executable(&plan.path)
            }
        });
    if let Err(error) = update {
        let restore = restore_hook(&plan);
        let cleanup = fs::remove_file(&staged_record);
        return Err(match (restore, cleanup) {
            (Ok(()), Ok(())) => error,
            (restore, cleanup) => format!(
                "{error}; hook rollback: {}; state cleanup: {}",
                restore.err().unwrap_or_else(|| "ok".to_owned()),
                cleanup
                    .err()
                    .map_or_else(|| "ok".to_owned(), |error| error.to_string())
            ),
        });
    }
    if let Err(error) = fs::rename(&staged_record, &record) {
        let restore = restore_hook(&plan);
        let cleanup = fs::remove_file(&staged_record);
        return Err(match (restore, cleanup) {
            (Ok(()), Ok(())) => format!("cannot publish hook state: {error}"),
            (restore, cleanup) => format!(
                "cannot publish hook state: {error}; hook rollback: {}; state cleanup: {}",
                restore.err().unwrap_or_else(|| "ok".to_owned()),
                cleanup
                    .err()
                    .map_or_else(|| "ok".to_owned(), |error| error.to_string())
            ),
        });
    }
    Ok(())
}

fn preflight_install_targets(binary: &Path, aliases: &[PathBuf]) -> Result<(), String> {
    validate_state_layout()?;
    let manifest = read_manifest()?;
    if let Some(expected) = manifest {
        verify_binary(binary, expected)?;
        verify_aliases(aliases)?;
        return Ok(());
    }

    let root = state_root()?;
    let has_state = match fs::read_dir(&root) {
        Ok(mut entries) => match entries.next() {
            Some(Ok(_)) => true,
            Some(Err(error)) => return Err(format!("cannot read installation state: {error}")),
            None => false,
        },
        Err(error) if error.kind() == ErrorKind::NotFound => false,
        Err(error) => return Err(format!("cannot read installation state: {error}")),
    };
    if has_state {
        return Err("Kento installation state exists without an ownership manifest".to_owned());
    }
    for path in std::iter::once(binary).chain(aliases.iter().map(PathBuf::as_path)) {
        match fs::symlink_metadata(path) {
            Ok(_) => {
                return Err(format!(
                    "refusing to replace unmanaged command {}",
                    path.display()
                ));
            }
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => return Err(format!("cannot inspect {}: {error}", path.display())),
        }
    }
    Ok(())
}

/// What a failed install has to put back: the commands it brought into existence,
/// and the binary it moved aside to replace.
#[derive(Default)]
struct Staged {
    created: Vec<PathBuf>,
    replaced: Option<(PathBuf, PathBuf)>,
}

fn install_binary(
    source: &Path,
    destination: &Path,
    expected: Fingerprint,
    staged: &mut Staged,
) -> Result<(), String> {
    let source = fs::canonicalize(source)
        .map_err(|error| format!("cannot resolve current executable: {error}"))?;
    let existed = match fs::canonicalize(destination) {
        Ok(resolved) => {
            if source == resolved {
                return Ok(());
            }
            true
        }
        Err(error) if error.kind() == ErrorKind::NotFound => false,
        Err(error) => return Err(format!("cannot resolve installed executable: {error}")),
    };
    let staging = scratch(destination, STAGING)?;
    let previous = scratch(destination, PREVIOUS)?;
    fs::copy(&source, &staging)
        .map_err(|error| format!("cannot stage installed executable: {error}"))?;
    if existed {
        if let Err(error) = fs::rename(destination, &previous) {
            let cleanup = fs::remove_file(&staging);
            return Err(also_failed(
                format!("cannot set aside installed executable: {error}"),
                &staging,
                cleanup,
            ));
        }
        staged.replaced = Some((destination.to_path_buf(), previous));
    }
    if let Err(error) = fs::rename(&staging, destination) {
        let cleanup = fs::remove_file(&staging);
        return Err(also_failed(
            format!("cannot install executable: {error}"),
            &staging,
            cleanup,
        ));
    }
    if !existed {
        staged.created.push(destination.to_path_buf());
    }
    if fingerprint(destination)? != expected {
        return Err("installed executable failed content verification".to_owned());
    }
    Ok(())
}

/// A path beside `destination` for Kento's own use, refused if something already
/// holds it: that means either a concurrent install or a leftover this one must
/// not silently adopt.
fn scratch(destination: &Path, name: &str) -> Result<PathBuf, String> {
    let path = destination.with_file_name(name);
    match fs::symlink_metadata(&path) {
        Ok(_) => Err(format!(
            "refusing unexpected temporary command {}",
            path.display()
        )),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(path),
        Err(error) => Err(format!(
            "cannot inspect temporary command {}: {error}",
            path.display()
        )),
    }
}

fn also_failed(error: String, path: &Path, cleanup: std::io::Result<()>) -> String {
    match cleanup {
        Ok(()) => error,
        Err(failure) => format!("{error}; cannot remove {}: {failure}", path.display()),
    }
}

fn create_commands(
    executable: &Path,
    binary: &Path,
    aliases: &[PathBuf],
    expected: Fingerprint,
    staged: &mut Staged,
) -> Result<(), String> {
    install_binary(executable, binary, expected, staged)?;
    for alias in aliases {
        match fs::symlink_metadata(alias) {
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => {
                std::os::unix::fs::symlink("kento", alias)
                    .map_err(|error| format!("cannot create alias {}: {error}", alias.display()))?;
                staged.created.push(alias.clone());
            }
            Err(error) => return Err(format!("cannot inspect alias {}: {error}", alias.display())),
        }
    }
    Ok(())
}

/// Puts back everything a failed install changed. The manifest that proves Kento
/// owns these commands is written only once they are all in place, so a failure
/// in between would otherwise leave a state the next install refuses outright:
/// commands it cannot prove it owns, or a manifest describing a binary that is no
/// longer the one installed.
fn undo_install(staged: Staged, error: String) -> String {
    let mut failures: Vec<String> = staged
        .created
        .iter()
        .rev()
        .filter_map(|path| {
            fs::remove_file(path)
                .err()
                .filter(|error| error.kind() != ErrorKind::NotFound)
                .map(|failure| format!("cannot remove {}: {failure}", path.display()))
        })
        .collect();
    if let Some((destination, previous)) = staged.replaced
        && let Err(failure) = fs::rename(&previous, &destination)
    {
        failures.push(format!(
            "cannot restore {} from {}: {failure}",
            destination.display(),
            previous.display()
        ));
    }
    if failures.is_empty() {
        error
    } else {
        format!("{error}; install rollback failed: {}", failures.join("; "))
    }
}

/// Discards the replaced binary once the manifest has made the new one official.
/// A leftover would block the next install, so a failure here is reported even
/// though the installation itself is complete.
fn discard_replaced(staged: Staged) -> Result<(), String> {
    let Some((_, previous)) = staged.replaced else {
        return Ok(());
    };
    fs::remove_file(&previous).map_err(|error| {
        format!(
            "installed, but cannot remove {}: {error}; remove it before installing again",
            previous.display()
        )
    })
}

pub fn install(root: &Path, no_hook: bool) -> Result<Option<String>, String> {
    let bin = bin_dir()?;
    let binary = bin.join("kento");
    let executable =
        env::current_exe().map_err(|error| format!("cannot locate current executable: {error}"))?;
    let source_fingerprint = fingerprint(&executable)?;
    let aliases = alias_paths(&bin);
    preflight_install_targets(&binary, &aliases)?;
    let records = read_records()?;
    let hook = if no_hook {
        None
    } else {
        Some(preflight_hook(root, &binary, &records)?)
    };

    fs::create_dir_all(&bin)
        .map_err(|error| format!("cannot create {}: {error}", bin.display()))?;
    let mut staged = Staged::default();
    if let Err(error) = create_commands(
        &executable,
        &binary,
        &aliases,
        source_fingerprint,
        &mut staged,
    )
    .and_then(|()| write_manifest(source_fingerprint))
    {
        return Err(undo_install(staged, error));
    }
    discard_replaced(staged)?;
    if let Some(hook) = hook {
        apply_hook(hook)?;
    }
    Ok((!path_in_path(&bin)).then(|| format!("{} is not on PATH", bin.display())))
}

fn make_executable(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    let mut permissions = fs::metadata(path)
        .map_err(|error| format!("cannot inspect {}: {error}", path.display()))?
        .permissions();
    permissions.set_mode(0o755);
    fs::set_permissions(path, permissions)
        .map_err(|error| format!("cannot make hook executable: {error}"))
}

struct HookRemoval {
    record: PathBuf,
    record_bytes: Vec<u8>,
    hook: PathBuf,
    original: String,
    remaining: String,
    permissions: fs::Permissions,
    remove_file: bool,
}

fn restore_removed_hook(plan: &HookRemoval) -> Result<(), String> {
    fs::write(&plan.record, &plan.record_bytes).map_err(|error| {
        format!(
            "cannot restore hook state {}: {error}",
            plan.record.display()
        )
    })?;
    fs::write(&plan.hook, &plan.original)
        .map_err(|error| format!("cannot restore hook {}: {error}", plan.hook.display()))?;
    fs::set_permissions(&plan.hook, plan.permissions.clone())
        .map_err(|error| format!("cannot restore hook mode {}: {error}", plan.hook.display()))
}

fn remove_hook(plan: &HookRemoval) -> Result<(), String> {
    fs::remove_file(&plan.record).map_err(|error| {
        format!(
            "cannot remove hook state {}: {error}",
            plan.record.display()
        )
    })?;
    let update = if plan.remove_file {
        fs::remove_file(&plan.hook)
            .map_err(|error| format!("cannot remove hook {}: {error}", plan.hook.display()))
    } else {
        fs::write(&plan.hook, &plan.remaining)
            .map_err(|error| format!("cannot update hook {}: {error}", plan.hook.display()))
            .and_then(|()| {
                fs::set_permissions(&plan.hook, plan.permissions.clone()).map_err(|error| {
                    format!("cannot preserve hook mode {}: {error}", plan.hook.display())
                })
            })
    };
    if let Err(error) = update {
        return match restore_removed_hook(plan) {
            Ok(()) => Err(error),
            Err(restore) => Err(format!("{error}; rollback failed: {restore}")),
        };
    }
    Ok(())
}

pub fn uninstall() -> Result<(), String> {
    validate_state_layout()?;
    let expected = read_manifest()?.ok_or_else(|| "Kento is not installed".to_owned())?;
    let bin = bin_dir()?;
    let binary = bin.join("kento");
    let aliases = alias_paths(&bin);
    verify_binary(&binary, expected)?;
    verify_aliases(&aliases)?;

    let records = read_records()?;
    let expected_block = block(&binary);
    let mut hooks = Vec::new();
    for (record, hook) in &records {
        let metadata = fs::symlink_metadata(hook)
            .map_err(|error| format!("cannot inspect recorded hook {}: {error}", hook.display()))?;
        if !metadata.is_file() || metadata.file_type().is_symlink() {
            return Err(format!(
                "recorded hook {} is not a regular file",
                hook.display()
            ));
        }
        let text = fs::read_to_string(hook)
            .map_err(|error| format!("cannot read recorded hook {}: {error}", hook.display()))?;
        if marker_count(&text) != 2 || text.matches(&expected_block).count() != 1 {
            return Err(format!(
                "recorded hook {} has altered Kento block",
                hook.display()
            ));
        }
        let permissions = metadata.permissions();
        let remaining = text.replacen(&expected_block, "", 1);
        hooks.push(HookRemoval {
            record: record.clone(),
            record_bytes: fs::read(record)
                .map_err(|error| format!("cannot read hook state {}: {error}", record.display()))?,
            hook: hook.clone(),
            remove_file: remaining == "#!/bin/sh\n",
            original: text,
            remaining,
            permissions,
        });
    }

    let mut removed = Vec::new();
    for hook in hooks {
        if let Err(error) = remove_hook(&hook) {
            let rollback_errors: Vec<String> = removed
                .iter()
                .rev()
                .filter_map(|previous| restore_removed_hook(previous).err())
                .collect();
            return if rollback_errors.is_empty() {
                Err(error)
            } else {
                Err(format!(
                    "{error}; global rollback failed: {}",
                    rollback_errors.join("; ")
                ))
            };
        }
        removed.push(hook);
    }
    for alias in aliases {
        match fs::symlink_metadata(&alias) {
            Ok(_) => fs::remove_file(&alias)
                .map_err(|error| format!("cannot remove alias {}: {error}", alias.display()))?,
            Err(error) if error.kind() == ErrorKind::NotFound => {}
            Err(error) => return Err(format!("cannot inspect alias {}: {error}", alias.display())),
        }
    }
    match fs::remove_file(&binary) {
        Ok(()) => {}
        Err(error) if error.kind() == ErrorKind::NotFound => {}
        Err(error) => return Err(format!("cannot remove executable: {error}")),
    }
    fs::remove_file(manifest_path()?)
        .map_err(|error| format!("cannot remove installation manifest: {error}"))?;
    let hooks = state_dir()?;
    match fs::remove_dir(&hooks) {
        Ok(()) => {}
        Err(error) if error.kind() == ErrorKind::NotFound => {}
        Err(error) => return Err(format!("cannot remove hook state directory: {error}")),
    }
    fs::remove_dir(state_root()?)
        .map_err(|error| format!("cannot remove installation state directory: {error}"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognizes_shell_shebangs_and_block_integrity() {
        assert!(compatible_shebang("#!/bin/sh\nexit 0\n"));
        assert!(compatible_shebang("#!/usr/bin/env bash\n"));
        // Every shell Kento claims to support, at an absolute path and through
        // `env`, since the block it injects is written for all three.
        assert!(compatible_shebang("#!/bin/zsh\n"));
        assert!(compatible_shebang("#!/usr/bin/env zsh\n"));
        assert!(compatible_shebang("#!/bin/bash\n"));
        assert!(compatible_shebang("#!/usr/local/bin/zsh\n"));
        assert!(!compatible_shebang("#!/usr/bin/env python\n"));
        assert!(!compatible_shebang("#!/usr/bin/perl\n"));
        assert!(!compatible_shebang("no shebang at all\n"));
        assert!(!compatible_shebang(""));
        let content = block(Path::new("/a space/kento"));
        assert_eq!(marker_count(&content), 2);
        assert!(content.contains("'/a space/kento'"));
    }

    /// The counter is what makes this unique rather than merely unlikely to
    /// collide: the clock is coarser than a thread switch, so two tests can read
    /// the same value.
    fn temporary_dir(label: &str) -> PathBuf {
        use std::sync::atomic::{AtomicUsize, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};
        static SEQUENCE: AtomicUsize = AtomicUsize::new(0);
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!(
                "kento-{label}-{}-{unique}-{}",
                std::process::id(),
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
        fs::create_dir_all(&path).expect("directory");
        path
    }

    /// What a failed install says about its own cleanup.
    ///
    /// Reaching this through the CLI would take a filesystem that fails a
    /// removal at one exact moment mid-rollback, so it is driven directly. The
    /// two halves are opposite mistakes and both are damaging: complaining about
    /// a file that was already gone buries the real error under noise about a
    /// cleanup that succeeded, and staying silent about a removal that genuinely
    /// failed leaves commands behind that the next install will refuse, with
    /// nothing in the message to say why.
    #[test]
    fn rollback_reports_only_what_it_could_not_remove() {
        let root = temporary_dir("rollback-report");

        let staged = Staged {
            created: vec![root.join("never-created")],
            replaced: None,
        };
        assert_eq!(
            undo_install(staged, "original failure".to_owned()),
            "original failure",
            "a file that is already gone is a rollback that succeeded"
        );

        // A directory cannot be removed as a file, and the error is not
        // NotFound — the one shape a test can produce without a race.
        let stubborn = root.join("stubborn");
        fs::create_dir(&stubborn).expect("directory");
        let staged = Staged {
            created: vec![stubborn.clone()],
            replaced: None,
        };
        let message = undo_install(staged, "original failure".to_owned());
        assert!(
            message.starts_with("original failure; install rollback failed: cannot remove "),
            "{message}"
        );
        assert!(
            message.contains(&stubborn.display().to_string()),
            "{message}"
        );

        let _ = fs::remove_dir_all(root);
    }
}

#!/usr/bin/env python3
"""Fail if the test suite would stay green through a semantic change to Kento.

A suite that does not flake is not the same as a suite that would notice a
regression. Each case below breaks one guard on purpose; the suite has to fail.
Anything that survives is a guard nothing is watching.

    python3 tools/mutation-gate.py            # every case
    python3 tools/mutation-gate.py toolchain  # cases whose label contains this

Targets are addressed by a unique source snippet rather than a line number, so
adding tests cannot silently point a case at the wrong code. Editing the code a
case names makes it report AMBIGUOUS and fail, which is the intended prompt to
update the case rather than to delete it.

Requires a clean `src/`: the run mutates it and restores with `git checkout`.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 300

# (label, file, snippet to find, replacement)
CASES = [
    # --- refusing to clobber what Kento does not own ---
    (
        "install: hook tamper || -> &&",
        "src/install.rs",
        "if marker_count(&text) != 2 || text.matches(&expected_block).count() != 1 {",
        "if marker_count(&text) != 2 && text.matches(&expected_block).count() != 1 {",
    ),
    (
        "install: recorded-hook guard || -> &&",
        "src/install.rs",
        'if !metadata.is_file() || metadata.file_type().is_symlink() {\n            return Err(format!(\n                "recorded hook {} is not a regular file",',
        'if !metadata.is_file() && metadata.file_type().is_symlink() {\n            return Err(format!(\n                "recorded hook {} is not a regular file",',
    ),
    (
        "install: recorded-hook refusal -> Ok",
        "src/install.rs",
        'return Err(format!(\n                "recorded hook {} is not a regular file",',
        'return Ok(()); #[allow(unreachable_code)] return Err(format!(\n                "recorded hook {} is not a regular file",',
    ),
    (
        "install: shebang ends_with -> starts_with",
        "src/install.rs",
        'executable.ends_with("/zsh")',
        'executable.starts_with("/zsh")',
    ),
    (
        "install: state-root refusal -> Ok",
        "src/install.rs",
        'if !metadata.is_dir() || metadata.file_type().is_symlink() {\n        return Err("malformed Kento installation state".to_owned());',
        "if !metadata.is_dir() || metadata.file_type().is_symlink() {\n        return Ok(());",
    ),
    (
        "install: manifest-type refusal -> Ok",
        "src/install.rs",
        'if name == "installation" {\n            if !file_type.is_file() || file_type.is_symlink() {\n                return Err("malformed Kento installation state".to_owned());',
        'if name == "installation" {\n            if !file_type.is_file() || file_type.is_symlink() {\n                return Ok(());',
    ),
    (
        "install: hooks-type refusal -> Ok",
        "src/install.rs",
        '} else if name == "hooks" {\n            if !file_type.is_dir() || file_type.is_symlink() {\n                return Err("malformed Kento installation state".to_owned());',
        '} else if name == "hooks" {\n            if !file_type.is_dir() || file_type.is_symlink() {\n                return Ok(());',
    ),
    (
        "install: stray-entry refusal -> Ok",
        "src/install.rs",
        'return Err(format!(\n                "unexpected Kento installation state {}",',
        'return Ok(()); #[allow(unreachable_code)] return Err(format!(\n                "unexpected Kento installation state {}",',
    ),
    (
        "install: adopt a leftover temporary command",
        "src/install.rs",
        '        Ok(_) => Err(format!(\n            "refusing unexpected temporary command {}",\n            path.display()\n        )),',
        "        Ok(_) => Ok(path.clone()),",
    ),
    # --- an install or uninstall that fails must not wedge ---
    (
        "install: skip setting the previous binary aside",
        "src/install.rs",
        "    if existed {\n        if let Err(error) = fs::rename(destination, &previous) {",
        "    if false {\n        if let Err(error) = fs::rename(destination, &previous) {",
    ),
    (
        "install: rollback restores in the wrong direction",
        "src/install.rs",
        "&& let Err(failure) = fs::rename(&previous, &destination)",
        "&& let Err(failure) = fs::rename(&destination, &previous)",
    ),
    (
        "install: never discard the replaced binary",
        "src/install.rs",
        "    fs::remove_file(&previous).map_err(|error| {",
        "    return Ok(()); #[allow(unreachable_code)] fs::remove_file(&previous).map_err(|error| {",
    ),
    (
        "install: undo removes nothing",
        "src/install.rs",
        "    let mut failures: Vec<String> = staged\n        .created\n        .iter()\n        .rev()",
        "    let mut failures: Vec<String> = staged\n        .created\n        .iter()\n        .skip(usize::MAX)\n        .rev()",
    ),
    (
        "install: a missing binary is refused again",
        "src/install.rs",
        '        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(()),\n        Err(error) => {\n            return Err(format!("cannot inspect installed Kento binary: {error}"));',
        '        Err(error) if false && error.kind() == ErrorKind::NotFound => return Ok(()),\n        Err(error) => {\n            return Err(format!("cannot inspect installed Kento binary: {error}"));',
    ),
    (
        "install: removing an absent binary is an error again",
        "src/install.rs",
        "    match fs::remove_file(&binary) {\n        Ok(()) => {}\n        Err(error) if error.kind() == ErrorKind::NotFound => {}",
        "    match fs::remove_file(&binary) {\n        Ok(()) => {}\n        Err(error) if false && error.kind() == ErrorKind::NotFound => {}",
    ),
    # --- the rules ---
    (
        "app: KENTO201 language == -> !=",
        "src/app.rs",
        '"KENTO201" => language == Language::Html,',
        '"KENTO201" => language != Language::Html,',
    ),
    (
        "app: leave the merged report unsorted",
        "src/app.rs",
        "    diagnostics.extend(toolchain::shell_checks(root, &shell)?);\n    diagnostics.sort();",
        "    diagnostics.extend(toolchain::shell_checks(root, &shell)?);",
    ),
    (
        "app: skip the Rust toolchain entirely",
        "src/app.rs",
        "    diagnostics.extend(toolchain::rust_checks(root, &rust)?);",
        "    toolchain::rust_checks(root, &rust)?;",
    ),
    (
        "app: skip ShellCheck entirely",
        "src/app.rs",
        "    diagnostics.extend(toolchain::shell_checks(root, &shell)?);",
        "    toolchain::shell_checks(root, &shell)?;",
    ),
    (
        "lint: mask comment terminator == -> !=",
        "src/lint.rs",
        'index += bytes[index + 2..]\n                .windows(2)\n                .position(|window| window == b"*/")',
        'index += bytes[index + 2..]\n                .windows(2)\n                .position(|window| window != b"*/")',
    ),
    (
        "lint: css_rules terminator == -> !=",
        "src/lint.rs",
        'if let Some(end) = bytes[index + 2..]\n                .windows(2)\n                .position(|window| window == b"*/")',
        'if let Some(end) = bytes[index + 2..]\n                .windows(2)\n                .position(|window| window != b"*/")',
    ),
    (
        "lint: protected element name || -> &&",
        "src/lint.rs",
        "if bytes.get(start) != Some(&b'<')\n        || !bytes.get(name_start..name_end)?.eq_ignore_ascii_case(name)",
        "if bytes.get(start) != Some(&b'<')\n        && !bytes.get(name_start..name_end)?.eq_ignore_ascii_case(name)",
    ),
    (
        "lint: raw-string prefix r == -> !=",
        "src/lint.rs",
        "&& bytes[index] == b'r'",
        "&& bytes[index] != b'r'",
    ),
    (
        "lint: raw hash terminator == -> !=",
        "src/lint.rs",
        "bytes[index + 1 + hashes] == b'\"'",
        "bytes[index + 1 + hashes] != b'\"'",
    ),
    (
        "lint: python single triple == -> !=",
        "src/lint.rs",
        "&& ((bytes[index] == b'\\'' && bytes[index + 1] == b'\\''",
        "&& ((bytes[index] != b'\\'' && bytes[index + 1] == b'\\''",
    ),
    (
        "lint: arithmetic quoted escape == -> !=",
        "src/lint.rs",
        "                quote = None;\n                cursor += 1;\n            } else if byte == b'\\\\' {\n                cursor = (cursor + 2).min(bytes.len());\n            } else {\n                cursor += 1;\n            }\n        } else if matches!(byte, b'\\'' | b'\"') {\n            quote = Some(byte);\n            cursor += 1;\n        } else if byte == b'(' {",
        "                quote = None;\n                cursor += 1;\n            } else if byte != b'\\\\' {\n                cursor = (cursor + 2).min(bytes.len());\n            } else {\n                cursor += 1;\n            }\n        } else if matches!(byte, b'\\'' | b'\"') {\n            quote = Some(byte);\n            cursor += 1;\n        } else if byte == b'(' {",
    ),
    (
        "lint: arithmetic bare escape == -> !=",
        "src/lint.rs",
        "            if depth == 0 {\n                return Some(cursor);\n            }\n        } else if byte == b'\\\\' {",
        "            if depth == 0 {\n                return Some(cursor);\n            }\n        } else if byte != b'\\\\' {",
    ),
    (
        "lint: html attr value scan != -> ==",
        "src/lint.rs",
        "while cursor < tag.len() && tag[cursor] != *current {",
        "while cursor < tag.len() && tag[cursor] == *current {",
    ),
    (
        "lint: conflict separator gate",
        "src/lint.rs",
        '} else if open.is_some() && line.starts_with(b"=======") {',
        '} else if open.is_some() || line.starts_with(b"=======") {',
    ),
    (
        "lint: final-newline check",
        "src/lint.rs",
        "if !bytes.is_empty() && bytes.last() != Some(&b'\\n') {",
        "if !bytes.is_empty() && bytes.last() == Some(&b'\\n') {",
    ),
    (
        "types: shebang terminator",
        "src/types.rs",
        ".is_none_or(|byte| matches!(byte, b' ' | b'\\t' | b'\\r' | b'\\n'))",
        ".is_none_or(|_byte| true)",
    ),
    # --- the Rust toolchain rules ---
    (
        "toolchain: ignore the discovered-path filter",
        "src/toolchain.rs",
        "        linted.get(relative.to_string_lossy().as_ref())",
        "        linted.iter().next()",
    ),
    (
        "toolchain: report clean when a tool never checked",
        "src/toolchain.rs",
        "    if succeeded || parsed > 0 {\n        return Ok(());",
        "    if true {\n        return Ok(());",
    ),
    (
        "toolchain: treat findings-with-nonzero-exit as failure",
        "src/toolchain.rs",
        "    if succeeded || parsed > 0 {\n        return Ok(());",
        "    if succeeded && parsed > 0 {\n        return Ok(());",
    ),
    (
        "toolchain: drop the manifest gate",
        "src/toolchain.rs",
        '    if linted.is_empty() || !root.join("Cargo.toml").is_file() {',
        "    if linted.is_empty() {",
    ),
]


def restore():
    subprocess.run(
        ["git", "checkout", "--", "src"], cwd=REPO, check=True, capture_output=True
    )


def run_case(label, relative, find, replace):
    path = REPO / relative
    text = path.read_text()
    hits = text.count(find)
    if hits != 1:
        return f"AMBIGUOUS({hits})", label, "the snippet this case names no longer appears exactly once"
    path.write_text(text.replace(find, replace, 1))

    # A mutation can turn a lexer state machine into an infinite loop. Without the
    # timeout and the process-group kill, the hung test binary outlives this script
    # and spins a core until somebody notices.
    process = subprocess.Popen(
        ["cargo", "test", "--quiet"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        output = process.communicate(timeout=TIMEOUT_SECONDS)[0]
        code = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        process.wait()
        return "CAUGHT", label, "hung, killed after the timeout"
    finally:
        restore()

    if "error[E" in output or "could not compile" in output:
        return "UNCOMPILABLE", label, "not a viable mutant"
    if code == 0:
        return "SURVIVED", label, "no test noticed"
    return "CAUGHT", label, ""


def main():
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "src"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        print("src/ has uncommitted changes; this run rewrites and restores it")
        return 2

    only = sys.argv[1:]
    selected = [
        case for case in CASES if not only or any(term in case[0] for term in only)
    ]
    verdicts = []
    for label, relative, find, replace in selected:
        verdict, label, detail = run_case(label, relative, find, replace)
        print(f"{verdict:14} | {label}{f' — {detail}' if detail else ''}", flush=True)
        verdicts.append(verdict)

    viable = [v for v in verdicts if v != "UNCOMPILABLE"]
    caught = [v for v in viable if v == "CAUGHT"]
    print(f"\ncaught {len(caught)}/{len(viable)} viable mutants")
    unwatched = [v for v in verdicts if v in ("SURVIVED", "AMBIGUOUS")]
    if unwatched or any(v.startswith("AMBIGUOUS") for v in verdicts):
        print("a guard nothing is watching is a guard that can regress silently")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

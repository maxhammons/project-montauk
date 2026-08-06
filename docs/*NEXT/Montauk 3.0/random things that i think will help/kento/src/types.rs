use std::ffi::OsStr;
use std::path::Path;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Language {
    Rust,
    Python,
    JavaScript,
    TypeScript,
    Css,
    Html,
    Shell,
}

/// A shebang naming a shell and nothing else. The interpreter name has to end
/// where the shell's name ends: on a bare prefix test `#!/bin/shenanigans` and
/// `#!/usr/bin/env bashful` both read as shell.
fn shell_shebang(bytes: &[u8]) -> bool {
    const INTERPRETERS: [&[u8]; 6] = [
        b"#!/bin/sh",
        b"#!/bin/bash",
        b"#!/bin/zsh",
        b"#!/usr/bin/env sh",
        b"#!/usr/bin/env bash",
        b"#!/usr/bin/env zsh",
    ];
    INTERPRETERS.iter().any(|interpreter| {
        bytes.starts_with(interpreter)
            && bytes
                .get(interpreter.len())
                .is_none_or(|byte| matches!(byte, b' ' | b'\t' | b'\r' | b'\n'))
    })
}

impl Language {
    pub const fn all() -> [Self; 7] {
        [
            Self::Rust,
            Self::Python,
            Self::JavaScript,
            Self::TypeScript,
            Self::Css,
            Self::Html,
            Self::Shell,
        ]
    }

    pub fn matches(self, path: &Path, bytes: &[u8]) -> bool {
        let name = path.file_name().and_then(OsStr::to_str).unwrap_or("");
        match self {
            Self::Rust => name.ends_with(".rs"),
            Self::Python => name.ends_with(".py"),
            Self::JavaScript => name.ends_with(".js") || name.ends_with(".jsx"),
            Self::TypeScript => name.ends_with(".ts") || name.ends_with(".tsx"),
            Self::Css => name.ends_with(".css"),
            Self::Html => name.ends_with(".html") || name.ends_with(".htm"),
            Self::Shell => {
                name.ends_with(".sh")
                    || name.ends_with(".bash")
                    || name.ends_with(".zsh")
                    || (path.extension().is_none() && shell_shebang(bytes))
            }
        }
    }
}

/// `message` and `help` are owned because the Rust toolchain rules carry
/// rustfmt's and Clippy's own wording, which is not known at compile time.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Diagnostic {
    pub rule_id: &'static str,
    pub path: String,
    pub line: usize,
    pub column: usize,
    pub end_line: usize,
    pub end_column: usize,
    pub message: String,
    pub help: String,
}

impl Ord for Diagnostic {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        (
            &self.path,
            self.line,
            self.column,
            self.rule_id,
            self.end_line,
            self.end_column,
            &self.message,
        )
            .cmp(&(
                &other.path,
                other.line,
                other.column,
                other.rule_id,
                other.end_line,
                other.end_column,
                &other.message,
            ))
    }
}

impl PartialOrd for Diagnostic {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn matched(name: &str, bytes: &[u8]) -> Option<Language> {
        Language::all()
            .into_iter()
            .find(|language| language.matches(Path::new(name), bytes))
    }

    #[test]
    fn maps_extensions_to_languages() {
        assert_eq!(matched("a.rs", b""), Some(Language::Rust));
        assert_eq!(matched("a.py", b""), Some(Language::Python));
        assert_eq!(matched("a.js", b""), Some(Language::JavaScript));
        assert_eq!(matched("a.jsx", b""), Some(Language::JavaScript));
        assert_eq!(matched("a.ts", b""), Some(Language::TypeScript));
        assert_eq!(matched("a.tsx", b""), Some(Language::TypeScript));
        assert_eq!(matched("a.css", b""), Some(Language::Css));
        assert_eq!(matched("a.html", b""), Some(Language::Html));
        assert_eq!(matched("a.htm", b""), Some(Language::Html));
        assert_eq!(matched("a.sh", b""), Some(Language::Shell));
        assert_eq!(matched("a.bash", b""), Some(Language::Shell));
        assert_eq!(matched("a.zsh", b""), Some(Language::Shell));
        assert_eq!(matched("a.txt", b""), None);
    }

    #[test]
    fn recognizes_extensionless_shell_scripts_only_by_shebang() {
        for shebang in [
            "#!/bin/sh\n",
            "#!/bin/bash\n",
            "#!/bin/zsh\n",
            "#!/usr/bin/env sh\n",
            "#!/usr/bin/env bash\n",
            "#!/usr/bin/env zsh\n",
        ] {
            assert_eq!(
                matched("script", shebang.as_bytes()),
                Some(Language::Shell),
                "{shebang}"
            );
        }
        // Arguments after the interpreter are still that interpreter.
        assert_eq!(matched("script", b"#!/bin/sh -e\n"), Some(Language::Shell));
        assert_eq!(
            matched("script", b"#!/usr/bin/env bash -x\n"),
            Some(Language::Shell)
        );
        assert_eq!(matched("script", b"#!/bin/sh"), Some(Language::Shell));
        // A longer interpreter name that merely starts with a shell's is not it.
        for impostor in [
            "#!/bin/shenanigans\n",
            "#!/bin/bashful\n",
            "#!/usr/bin/env bashful\n",
            "#!/usr/bin/env shellcheck\n",
            "#!/bin/zshrc\n",
        ] {
            assert_eq!(matched("script", impostor.as_bytes()), None, "{impostor}");
        }
        assert_eq!(matched("script", b"#!/usr/bin/env python3\n"), None);
        assert_eq!(matched("script", b"plain text\n"), None);
        assert_eq!(matched("notes.txt", b"#!/bin/sh\n"), None);
    }
}

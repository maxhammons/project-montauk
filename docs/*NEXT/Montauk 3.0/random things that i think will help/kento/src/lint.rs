use crate::types::{Diagnostic, Language};
use std::collections::BTreeSet;

fn location(bytes: &[u8], at: usize) -> (usize, usize) {
    let before = &bytes[..at.min(bytes.len())];
    (
        before.iter().filter(|byte| **byte == b'\n').count() + 1,
        before
            .iter()
            .rposition(|byte| *byte == b'\n')
            .map_or(before.len() + 1, |index| before.len() - index),
    )
}

fn diagnostic(
    rule_id: &'static str,
    path: &str,
    bytes: &[u8],
    start: usize,
    end: usize,
    message: &str,
    help: &str,
) -> Diagnostic {
    let (line, column) = location(bytes, start);
    let (end_line, end_column) = location(bytes, end);
    Diagnostic {
        rule_id,
        path: path.to_owned(),
        line,
        column,
        end_line,
        end_column,
        message: message.to_owned(),
        help: help.to_owned(),
    }
}

fn lines(bytes: &[u8]) -> Vec<(usize, &[u8])> {
    let mut result = Vec::new();
    let mut start = 0;
    for (index, byte) in bytes.iter().enumerate() {
        if *byte == b'\n' {
            result.push((start, &bytes[start..index]));
            start = index + 1;
        }
    }
    if start < bytes.len() {
        result.push((start, &bytes[start..]));
    }
    result
}

fn mark_range(mask: &mut [bool], start: usize, end: usize) {
    let length = mask.len();
    let start = start.min(length);
    let end = end.min(length);
    for item in &mut mask[start..end] {
        *item = true;
    }
}

fn html_tag_end(bytes: &[u8], start: usize) -> Option<usize> {
    let mut quote = None;
    let mut cursor = start;
    while cursor < bytes.len() {
        if let Some(current) = quote {
            if bytes[cursor] == current {
                quote = None;
            }
        } else if matches!(bytes[cursor], b'\'' | b'"') {
            quote = Some(bytes[cursor]);
        } else if bytes[cursor] == b'>' {
            return Some(cursor + 1);
        }
        cursor += 1;
    }
    None
}

fn html_open_tag_end(bytes: &[u8], start: usize, name: &[u8]) -> Option<usize> {
    let name_start = start.checked_add(1)?;
    let name_end = name_start.checked_add(name.len())?;
    if bytes.get(start) != Some(&b'<')
        || !bytes.get(name_start..name_end)?.eq_ignore_ascii_case(name)
        || !bytes
            .get(name_end)
            .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\r' | b'\n' | b'/' | b'>'))
    {
        return None;
    }
    html_tag_end(bytes, name_end)
}

fn html_close_tag(bytes: &[u8], start: usize, name: &[u8]) -> Option<(usize, usize)> {
    let mut cursor = start;
    while cursor < bytes.len() {
        let relative = bytes[cursor..].iter().position(|byte| *byte == b'<')?;
        let tag_start = cursor + relative;
        let name_start = tag_start + 2;
        let name_end = name_start + name.len();
        if bytes.get(tag_start + 1) == Some(&b'/')
            && bytes
                .get(name_start..name_end)
                .is_some_and(|candidate| candidate.eq_ignore_ascii_case(name))
            && bytes
                .get(name_end)
                .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\r' | b'\n' | b'>'))
            && let Some(tag_end) = html_tag_end(bytes, name_end)
        {
            return Some((tag_start, tag_end));
        }
        cursor = tag_start + 1;
    }
    None
}

fn shell_heredoc_word(bytes: &[u8], cursor: &mut usize) -> Option<Vec<u8>> {
    let mut word = Vec::new();
    let mut quote = None;
    while *cursor < bytes.len() {
        let byte = bytes[*cursor];
        if let Some(current) = quote {
            *cursor += 1;
            if byte == current {
                quote = None;
            } else if current == b'"' && byte == b'\\' {
                let escaped = *bytes.get(*cursor)?;
                if matches!(escaped, b'$' | b'`' | b'"' | b'\\') {
                    word.push(escaped);
                } else {
                    word.extend_from_slice(&[b'\\', escaped]);
                }
                *cursor += 1;
            } else {
                word.push(byte);
            }
        } else if matches!(byte, b'\'' | b'"') {
            quote = Some(byte);
            *cursor += 1;
        } else if byte == b'\\' {
            *cursor += 1;
            word.push(*bytes.get(*cursor)?);
            *cursor += 1;
        } else if byte.is_ascii_whitespace()
            || matches!(byte, b';' | b'|' | b'&' | b'(' | b')' | b'<' | b'>')
        {
            break;
        } else {
            word.push(byte);
            *cursor += 1;
        }
    }
    (quote.is_none() && !word.is_empty()).then_some(word)
}

struct ShellHeredoc {
    delimiter: Vec<u8>,
    strip_tabs: bool,
}

fn shell_heredoc_specs(bytes: &[u8], start: usize) -> Option<(Vec<ShellHeredoc>, usize)> {
    let mut specs = Vec::new();
    let mut cursor = start;
    let mut quote = None;
    while cursor < bytes.len() {
        let byte = bytes[cursor];
        if let Some(current) = quote {
            if byte == current {
                quote = None;
                cursor += 1;
            } else if current == b'"' && byte == b'\\' {
                cursor = (cursor + 2).min(bytes.len());
            } else {
                cursor += 1;
            }
        } else if matches!(byte, b'\'' | b'"') {
            quote = Some(byte);
            cursor += 1;
        } else if byte == b'\\' {
            cursor = (cursor + 2).min(bytes.len());
        } else if byte == b'#' {
            let body_start = bytes[cursor..]
                .iter()
                .position(|byte| *byte == b'\n')
                .map_or(bytes.len(), |offset| cursor + offset + 1);
            return (!specs.is_empty()).then_some((specs, body_start));
        } else if byte == b'\n' {
            return (!specs.is_empty()).then_some((specs, cursor + 1));
        } else if bytes[cursor..].starts_with(b"<<") && !bytes[cursor..].starts_with(b"<<<") {
            cursor += 2;
            let strip_tabs = bytes.get(cursor) == Some(&b'-');
            cursor += usize::from(strip_tabs);
            while cursor < bytes.len() && matches!(bytes[cursor], b' ' | b'\t') {
                cursor += 1;
            }
            let delimiter = shell_heredoc_word(bytes, &mut cursor)?;
            specs.push(ShellHeredoc {
                delimiter,
                strip_tabs,
            });
        } else {
            cursor += 1;
        }
    }
    (!specs.is_empty()).then_some((specs, bytes.len()))
}

fn protect_shell_heredocs(mask: &mut [bool], bytes: &[u8], start: usize) -> Option<usize> {
    let (specs, mut cursor) = shell_heredoc_specs(bytes, start)?;
    for spec in specs {
        let body_start = cursor;
        let mut terminated = false;
        while cursor < bytes.len() {
            let next = bytes[cursor..]
                .iter()
                .position(|byte| *byte == b'\n')
                .map_or(bytes.len(), |offset| cursor + offset);
            let line = &bytes[cursor..next];
            let comparable = if spec.strip_tabs {
                &line[line.iter().take_while(|byte| **byte == b'\t').count()..]
            } else {
                line
            };
            if comparable == spec.delimiter {
                mark_range(mask, body_start, cursor);
                cursor = next + usize::from(next < bytes.len());
                terminated = true;
                break;
            }
            cursor = next + usize::from(next < bytes.len());
        }
        if !terminated {
            mark_range(mask, body_start, bytes.len());
            return Some(bytes.len());
        }
    }
    Some(cursor)
}

fn shell_arithmetic_end(bytes: &[u8], start: usize) -> Option<usize> {
    let prefix = if bytes[start..].starts_with(b"$((") {
        3
    } else if bytes[start..].starts_with(b"((") {
        2
    } else {
        return None;
    };
    let mut depth = 2_usize;
    let mut cursor = start + prefix;
    let mut quote = None;
    while cursor < bytes.len() {
        let byte = bytes[cursor];
        if let Some(current) = quote {
            if byte == current {
                quote = None;
                cursor += 1;
            } else if byte == b'\\' {
                cursor = (cursor + 2).min(bytes.len());
            } else {
                cursor += 1;
            }
        } else if matches!(byte, b'\'' | b'"') {
            quote = Some(byte);
            cursor += 1;
        } else if byte == b'(' {
            depth += 1;
            cursor += 1;
        } else if byte == b')' {
            depth -= 1;
            cursor += 1;
            if depth == 0 {
                return Some(cursor);
            }
        } else if byte == b'\\' {
            cursor = (cursor + 2).min(bytes.len());
        } else {
            cursor += 1;
        }
    }
    None
}

/// Whether the `'` at `index` opens a character literal rather than a lifetime
/// or a loop label.
///
/// `'a'` and `'\n'` are literals; `'a`, `'static` and `'outer:` are not. Reading
/// a lifetime as an opening quote is how an ordinary Rust file ends up with
/// everything after it masked: lifetimes come in odd numbers as often as even.
fn rust_char_literal(bytes: &[u8], index: usize) -> bool {
    if bytes.get(index + 1) == Some(&b'\\') {
        return true;
    }
    let mut cursor = index + 1;
    while cursor < bytes.len() && (bytes[cursor].is_ascii_alphanumeric() || bytes[cursor] == b'_') {
        cursor += 1;
    }
    if cursor > index + 1 {
        // One identifier byte then a quote is `'a'`; anything longer is a name.
        return cursor == index + 2 && bytes.get(cursor) == Some(&b'\'');
    }
    // Not an identifier byte at all — a literal like `' '` or `'é'`.
    true
}

/// Keywords a `/` may follow and still begin a regular expression. After
/// anything else that ends an expression — a name, a number, `)`, `]` — a `/`
/// is division.
const REGEX_KEYWORDS: &[&[u8]] = &[
    b"return",
    b"typeof",
    b"instanceof",
    b"in",
    b"of",
    b"new",
    b"delete",
    b"void",
    b"case",
    b"do",
    b"else",
    b"yield",
    b"await",
    b"throw",
];

/// Whether the `/` at `index` opens a regular expression rather than dividing.
///
/// `previous` is the last byte that was neither whitespace nor part of a comment
/// or string, and `word_start` where the identifier it belongs to began.
fn js_regex_start(bytes: &[u8], previous: Option<(usize, u8)>) -> bool {
    let Some((at, byte)) = previous else {
        return true; // nothing before it: the file opens with a regex
    };
    if !(byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'$') {
        return !matches!(byte, b')' | b']');
    }
    let mut start = at;
    while start > 0 && (bytes[start - 1].is_ascii_alphanumeric() || bytes[start - 1] == b'_') {
        start -= 1;
    }
    REGEX_KEYWORDS.contains(&&bytes[start..=at])
}

/// The byte after a regular expression literal, or `None` when it does not
/// terminate on its line. A `/` inside a character class does not end it.
fn js_regex_end(bytes: &[u8], start: usize) -> Option<usize> {
    let mut cursor = start + 1;
    let mut in_class = false;
    while cursor < bytes.len() {
        match bytes[cursor] {
            b'\\' => cursor += 1,
            b'\n' => return None,
            b'[' => in_class = true,
            b']' => in_class = false,
            b'/' if !in_class => return Some(cursor + 1),
            _ => {}
        }
        cursor += 1;
    }
    None
}

fn quote_mask(bytes: &[u8], language: Language) -> Vec<bool> {
    let mut mask = vec![false; bytes.len()];
    let mut index = 0;
    // The last byte that was code rather than whitespace, a comment or a
    // string. Only JavaScript needs it, to tell a regular expression from a
    // division, and only the byte and where it sat.
    let mut previous: Option<(usize, u8)> = None;
    while index < bytes.len() {
        // `<<<` is a here-string. The heredoc branch below already declines to
        // treat it as one, but it looks at a single position: walking on, the
        // second `<` of three begins a two-byte run that is not itself `<<<`,
        // and that run parses as a heredoc whose body never ends.
        if language == Language::Shell && bytes[index..].starts_with(b"<<<") {
            index += 3;
            continue;
        }
        // In CSS a backslash escapes the next byte anywhere, not only inside a
        // string — selectors are full of them, and `\'` is not an open quote.
        if language == Language::Css && bytes[index] == b'\\' {
            index = (index + 2).min(bytes.len());
            continue;
        }
        if matches!(language, Language::JavaScript | Language::TypeScript)
            && bytes[index] == b'/'
            && !bytes[index..].starts_with(b"//")
            && !bytes[index..].starts_with(b"/*")
            && js_regex_start(bytes, previous)
            && let Some(end) = js_regex_end(bytes, index)
        {
            previous = Some((end - 1, bytes[end - 1]));
            index = end;
            continue;
        }
        if matches!(language, Language::Python | Language::Shell) && bytes[index] == b'#' {
            index += bytes[index..]
                .iter()
                .position(|byte| *byte == b'\n')
                .unwrap_or(bytes.len() - index);
            continue;
        }
        if matches!(
            language,
            Language::Rust | Language::JavaScript | Language::TypeScript | Language::Css
        ) && bytes[index..].starts_with(b"//")
        {
            index += bytes[index..]
                .iter()
                .position(|byte| *byte == b'\n')
                .unwrap_or(bytes.len() - index);
            continue;
        }
        if matches!(
            language,
            Language::Rust | Language::JavaScript | Language::TypeScript | Language::Css
        ) && bytes[index..].starts_with(b"/*")
        {
            index += bytes[index + 2..]
                .windows(2)
                .position(|window| window == b"*/")
                .map_or(bytes.len() - index, |end| end + 4);
            continue;
        }
        if language == Language::Html && bytes[index..].starts_with(b"<!--") {
            index += bytes[index + 4..]
                .windows(3)
                .position(|window| window == b"-->")
                .map_or(bytes.len() - index, |end| end + 7);
            continue;
        }
        if language == Language::Html {
            let mut protected_tag = None;
            for name in [b"script".as_slice(), b"style", b"pre", b"textarea"] {
                if let Some(open_end) = html_open_tag_end(bytes, index, name)
                    && let Some((_, close_end)) = html_close_tag(bytes, open_end, name)
                {
                    protected_tag = Some((open_end, close_end));
                    break;
                }
            }
            if let Some((open_end, close_end)) = protected_tag {
                mark_range(&mut mask, open_end, close_end);
                index = close_end;
                continue;
            }
        }
        if language == Language::Shell
            && (bytes[index..].starts_with(b"$((") || bytes[index..].starts_with(b"(("))
            && let Some(end) = shell_arithmetic_end(bytes, index)
        {
            index = end;
            continue;
        }
        if language == Language::Shell
            && bytes[index..].starts_with(b"<<")
            && !bytes[index..].starts_with(b"<<<")
            && let Some(end) = protect_shell_heredocs(&mut mask, bytes, index)
        {
            index = end;
            continue;
        }
        let triple = language == Language::Python
            && index + 2 < bytes.len()
            && ((bytes[index] == b'\'' && bytes[index + 1] == b'\'' && bytes[index + 2] == b'\'')
                || (bytes[index] == b'"' && bytes[index + 1] == b'"' && bytes[index + 2] == b'"'));
        let raw_rust = language == Language::Rust
            && bytes[index] == b'r'
            && (index + 1 < bytes.len() && (bytes[index + 1] == b'"' || bytes[index + 1] == b'#'));
        let quote_start = if triple {
            Some((index, 3usize, bytes[index]))
        } else if raw_rust {
            let mut hashes = 0;
            while index + 1 + hashes < bytes.len() && bytes[index + 1 + hashes] == b'#' {
                hashes += 1;
            }
            if index + 1 + hashes < bytes.len() && bytes[index + 1 + hashes] == b'"' {
                Some((index, hashes + 2, b'"'))
            } else {
                None
            }
        } else if matches!(bytes[index], b'\'' | b'"' | b'`') {
            // Two bytes that look like an opening quote and are not one.
            //
            // In markup a quote delimits an attribute value, and only inside a
            // tag; in prose it is punctuation, and reading `didn't` as an open
            // string silences the rest of the document. The regions HTML really
            // does protect — script, style, pre, textarea — are handled above
            // and do not come from here.
            //
            // In Rust an apostrophe is far more often a lifetime than a
            // character literal, and lifetimes come in odd numbers as readily as
            // even ones.
            let punctuation = language == Language::Html
                || (language == Language::Rust
                    && bytes[index] == b'\''
                    && !rust_char_literal(bytes, index));
            if punctuation {
                None
            } else {
                Some((index, 1, bytes[index]))
            }
        } else {
            None
        };
        if let Some((start, prefix, quote)) = quote_start {
            let mut cursor = start + prefix;
            let raw_hashes = if raw_rust { prefix - 2 } else { 0 };
            while cursor < bytes.len() {
                if raw_rust
                    && bytes[cursor] == b'"'
                    && cursor + raw_hashes < bytes.len()
                    && bytes[cursor + 1..cursor + 1 + raw_hashes]
                        .iter()
                        .all(|byte| *byte == b'#')
                {
                    cursor += raw_hashes + 1;
                    break;
                }
                if triple
                    && cursor + 2 < bytes.len()
                    && bytes[cursor] == quote
                    && bytes[cursor + 1] == quote
                    && bytes[cursor + 2] == quote
                {
                    cursor += 3;
                    break;
                }
                if !raw_rust && bytes[cursor] == b'\\' {
                    cursor = (cursor + 2).min(bytes.len());
                    continue;
                }
                if !triple && !raw_rust && bytes[cursor] == quote {
                    cursor += 1;
                    break;
                }
                cursor += 1;
            }
            mark_range(&mut mask, start, cursor);
            if cursor > 0 {
                previous = Some((cursor - 1, bytes[cursor - 1]));
            }
            index = cursor;
        } else {
            if !bytes[index].is_ascii_whitespace() {
                previous = Some((index, bytes[index]));
            }
            index += 1;
        }
    }
    mask
}

fn find_ascii_case_insensitive(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).position(|window| {
        window
            .iter()
            .zip(needle)
            .all(|(left, right)| left.eq_ignore_ascii_case(right))
    })
}

fn conflict_starts(bytes: &[u8]) -> Vec<usize> {
    let mut starts = Vec::new();
    let mut open = None;
    let mut separator = false;
    for (offset, line) in lines(bytes) {
        if line.starts_with(b"<<<<<<<") {
            open = Some(offset);
            separator = false;
        } else if open.is_some() && line.starts_with(b"=======") {
            separator = true;
        } else if separator && line.starts_with(b">>>>>>>") {
            starts.push(open.take().unwrap_or(offset));
            separator = false;
        }
    }
    starts
}

fn python_code_mask(bytes: &[u8]) -> Vec<bool> {
    let mut masked = quote_mask(bytes, Language::Python);
    let mut index = 0;
    while index < bytes.len() {
        if !masked[index] && bytes[index] == b'#' {
            let end = bytes[index..]
                .iter()
                .position(|byte| *byte == b'\n')
                .map_or(bytes.len(), |offset| index + offset);
            mark_range(&mut masked, index, end);
            index = end;
        } else {
            index += 1;
        }
    }
    masked
}

fn python_line_continuation(bytes: &[u8], index: usize) -> Option<usize> {
    match bytes.get(index..) {
        Some(value) if value.starts_with(b"\\\r\n") => Some(3),
        Some(value) if value.starts_with(b"\\\n") => Some(2),
        _ => None,
    }
}

fn skip_python_spacing(bytes: &[u8], mut index: usize) -> usize {
    loop {
        while bytes
            .get(index)
            .is_some_and(|byte| matches!(byte, b' ' | b'\t' | b'\r'))
        {
            index += 1;
        }
        let Some(length) = python_line_continuation(bytes, index) else {
            return index;
        };
        index += length;
    }
}

#[derive(Clone, Copy)]
enum PythonToken {
    Name(usize, usize),
    Operator,
    Symbol(u8),
}

fn python_token_is_none(token: &PythonToken, bytes: &[u8]) -> Option<(usize, usize)> {
    let PythonToken::Name(start, end) = *token else {
        return None;
    };
    (&bytes[start..end] == b"None").then_some((start, end))
}

fn python_none_after(
    tokens: &[PythonToken],
    bytes: &[u8],
    operator: usize,
) -> Option<(usize, usize)> {
    let mut cursor = operator + 1;
    let mut parentheses = 0;
    while matches!(tokens.get(cursor), Some(PythonToken::Symbol(b'('))) {
        parentheses += 1;
        cursor += 1;
    }
    let result = python_token_is_none(tokens.get(cursor)?, bytes)?;
    cursor += 1;
    for _ in 0..parentheses {
        if !matches!(tokens.get(cursor), Some(PythonToken::Symbol(b')'))) {
            return None;
        }
        cursor += 1;
    }
    if matches!(
        tokens.get(cursor),
        Some(PythonToken::Symbol(b'.' | b'(' | b'['))
    ) {
        return None;
    }
    Some(result)
}

fn python_group_boundary(token: &PythonToken, bytes: &[u8]) -> bool {
    match *token {
        PythonToken::Operator => true,
        PythonToken::Symbol(byte) => matches!(
            byte,
            b'=' | b':'
                | b','
                | b'('
                | b'['
                | b'{'
                | b'+'
                | b'-'
                | b'*'
                | b'/'
                | b'%'
                | b'&'
                | b'|'
                | b'^'
                | b'~'
                | b'<'
                | b'>'
        ),
        PythonToken::Name(start, end) => matches!(
            &bytes[start..end],
            b"if"
                | b"elif"
                | b"while"
                | b"return"
                | b"yield"
                | b"assert"
                | b"and"
                | b"or"
                | b"not"
                | b"lambda"
                | b"in"
                | b"is"
        ),
    }
}

fn python_none_before(
    tokens: &[PythonToken],
    bytes: &[u8],
    operator: usize,
) -> Option<(usize, usize)> {
    let mut cursor = operator;
    let mut parentheses = 0;
    while cursor > 0 && matches!(tokens.get(cursor - 1), Some(PythonToken::Symbol(b')'))) {
        parentheses += 1;
        cursor -= 1;
    }
    cursor = cursor.checked_sub(1)?;
    let result = python_token_is_none(tokens.get(cursor)?, bytes)?;
    for _ in 0..parentheses {
        cursor = cursor.checked_sub(1)?;
        if !matches!(tokens.get(cursor), Some(PythonToken::Symbol(b'('))) {
            return None;
        }
    }
    if parentheses > 0 && cursor > 0 && !python_group_boundary(tokens.get(cursor - 1)?, bytes) {
        return None;
    }
    Some(result)
}

fn python_rules(bytes: &[u8], path: &str, diagnostics: &mut Vec<Diagnostic>) {
    let masked = python_code_mask(bytes);
    for (offset, line) in lines(bytes) {
        let mut cursor = 0;
        while cursor < line.len() && matches!(line[cursor], b' ' | b'\t' | b'\r') {
            cursor += 1;
        }
        let token_start = offset + cursor;
        if bytes[token_start..].starts_with(b"except")
            && !masked.get(token_start).copied().unwrap_or(true)
            && bytes
                .get(token_start + 6)
                .is_none_or(|byte| !byte.is_ascii_alphanumeric() && *byte != b'_')
        {
            let after = skip_python_spacing(bytes, token_start + 6);
            if bytes.get(after) == Some(&b':') && !masked[after] {
                diagnostics.push(diagnostic(
                    "KENTO101",
                    path,
                    bytes,
                    token_start,
                    after + 1,
                    "bare except catches every exception",
                    "Catch a specific exception type instead.",
                ));
            }
        }
    }

    let mut tokens = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        if masked[index] || bytes[index].is_ascii_whitespace() {
            index += 1;
        } else if let Some(length) = python_line_continuation(bytes, index) {
            index += length;
        } else if bytes[index].is_ascii_alphabetic() || bytes[index] == b'_' {
            let start = index;
            index += 1;
            while index < bytes.len()
                && !masked[index]
                && (bytes[index].is_ascii_alphanumeric() || bytes[index] == b'_')
            {
                index += 1;
            }
            tokens.push(PythonToken::Name(start, index));
        } else if index + 1 < bytes.len()
            && !masked[index + 1]
            && matches!(&bytes[index..index + 2], b"==" | b"!=")
        {
            tokens.push(PythonToken::Operator);
            index += 2;
        } else {
            tokens.push(PythonToken::Symbol(bytes[index]));
            index += 1;
        }
    }
    for (position, token) in tokens.iter().enumerate() {
        let PythonToken::Operator = *token else {
            continue;
        };
        if let Some((none_start, none_end)) = python_none_before(&tokens, bytes, position)
            .or_else(|| python_none_after(&tokens, bytes, position))
        {
            diagnostics.push(diagnostic(
                "KENTO102",
                path,
                bytes,
                none_start,
                none_end,
                "None compared with equality",
                "Use `is None` or `is not None`.",
            ));
        }
    }
}

fn css_rules(bytes: &[u8], path: &str, diagnostics: &mut Vec<Diagnostic>) {
    let mut index = 0;
    let mut quote = None;
    while index < bytes.len() {
        if let Some(current) = quote {
            if bytes[index] == b'\\' {
                index = (index + 2).min(bytes.len());
            } else if bytes[index] == current {
                quote = None;
                index += 1;
            } else {
                index += 1;
            }
        } else if matches!(bytes[index], b'\'' | b'"') {
            quote = Some(bytes[index]);
            index += 1;
        } else if bytes[index..].starts_with(b"/*") {
            if let Some(end) = bytes[index + 2..]
                .windows(2)
                .position(|window| window == b"*/")
            {
                index += end + 4;
            } else {
                diagnostics.push(diagnostic(
                    "KENTO301",
                    path,
                    bytes,
                    index,
                    index + 2,
                    "unterminated CSS comment",
                    "Close the comment with `*/`.",
                ));
                break;
            }
        } else {
            index += 1;
        }
    }
}

fn html_rules(bytes: &[u8], path: &str, diagnostics: &mut Vec<Diagnostic>) {
    let mut index = 0;
    let mut raw_until: Option<&[u8]> = None;
    while index < bytes.len() {
        if let Some(name) = raw_until {
            if let Some(close) = find_ascii_case_insensitive(&bytes[index..], name) {
                index += close + name.len();
                raw_until = None;
            } else {
                break;
            }
        } else if bytes[index..].starts_with(b"<!--") {
            index += bytes[index + 4..]
                .windows(3)
                .position(|window| window == b"-->")
                .map_or(bytes.len() - index, |end| end + 7);
        } else if bytes[index] != b'<'
            || index + 1 >= bytes.len()
            || matches!(bytes[index + 1], b'/' | b'!' | b'?')
        {
            index += 1;
        } else {
            let tag_start = index;
            let mut end = index + 1;
            let mut quote = None;
            while end < bytes.len() {
                if let Some(current) = quote {
                    if bytes[end] == current {
                        quote = None;
                    }
                } else if matches!(bytes[end], b'\'' | b'"') {
                    quote = Some(bytes[end]);
                } else if bytes[end] == b'>' {
                    break;
                }
                end += 1;
            }
            if end == bytes.len() {
                break;
            }
            let tag = &bytes[tag_start + 1..end];
            let mut cursor = 0;
            while cursor < tag.len() && !matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n' | b'/')
            {
                cursor += 1;
            }
            let tag_name = &tag[..cursor];
            let templated = tag
                .windows(2)
                .any(|window| window == b"{{" || window == b"{%")
                || tag.windows(2).any(|window| window == b"<%");
            if !templated {
                let mut seen = BTreeSet::new();
                while cursor < tag.len() {
                    while cursor < tag.len()
                        && matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n' | b'/')
                    {
                        cursor += 1;
                    }
                    let start = cursor;
                    while cursor < tag.len()
                        && !matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n' | b'=' | b'/')
                    {
                        cursor += 1;
                    }
                    if start == cursor {
                        break;
                    }
                    let name = tag[start..cursor].to_ascii_lowercase();
                    if !seen.insert(name) {
                        diagnostics.push(diagnostic(
                            "KENTO201",
                            path,
                            bytes,
                            tag_start + 1 + start,
                            tag_start + 1 + cursor,
                            "duplicate HTML attribute",
                            "Keep only one instance of each attribute on this tag.",
                        ));
                    }
                    while cursor < tag.len() && matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n')
                    {
                        cursor += 1;
                    }
                    if tag.get(cursor) == Some(&b'=') {
                        cursor += 1;
                        while cursor < tag.len()
                            && matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n')
                        {
                            cursor += 1;
                        }
                        if let Some(current) = tag
                            .get(cursor)
                            .filter(|byte| matches!(**byte, b'\'' | b'"'))
                        {
                            cursor += 1;
                            while cursor < tag.len() && tag[cursor] != *current {
                                cursor += 1;
                            }
                            cursor += usize::from(cursor < tag.len());
                        } else {
                            while cursor < tag.len()
                                && !matches!(tag[cursor], b' ' | b'\t' | b'\r' | b'\n')
                            {
                                cursor += 1;
                            }
                        }
                    }
                }
            }
            if tag_name.eq_ignore_ascii_case(b"script") {
                raw_until = Some(b"</script");
            } else if tag_name.eq_ignore_ascii_case(b"style") {
                raw_until = Some(b"</style");
            }
            index = end + 1;
        }
    }
}

/// Lints content without filesystem access.
pub fn lint_bytes(language: Language, bytes: &[u8], path: &str) -> Vec<Diagnostic> {
    let mut diagnostics = Vec::new();
    for start in conflict_starts(bytes) {
        diagnostics.push(diagnostic(
            "KENTO001",
            path,
            bytes,
            start,
            start + 7,
            "complete merge conflict marker block found",
            "Resolve the merge conflict and remove all conflict markers.",
        ));
    }
    if !bytes.is_empty() && bytes.last() != Some(&b'\n') {
        diagnostics.push(diagnostic(
            "KENTO002",
            path,
            bytes,
            bytes.len() - 1,
            bytes.len(),
            "file does not end with a line feed",
            "End the file with a single LF newline.",
        ));
    }
    let protected = quote_mask(bytes, language);
    for (offset, line) in lines(bytes) {
        let content_end = if line.last() == Some(&b'\r') {
            line.len() - 1
        } else {
            line.len()
        };
        let mut start = content_end;
        while start > 0 && matches!(line[start - 1], b' ' | b'\t') {
            start -= 1;
        }
        if start < content_end
            && protected[offset + start..offset + content_end]
                .iter()
                .any(|item| !item)
        {
            diagnostics.push(diagnostic(
                "KENTO003",
                path,
                bytes,
                offset + start,
                offset + content_end,
                "trailing ASCII whitespace",
                "Remove the trailing spaces or tabs.",
            ));
        }
    }
    match language {
        Language::Python => python_rules(bytes, path, &mut diagnostics),
        Language::Css => css_rules(bytes, path, &mut diagnostics),
        Language::Html => html_rules(bytes, path, &mut diagnostics),
        _ => {}
    }
    diagnostics.sort();
    diagnostics
}

#[cfg(test)]
mod tests {
    use super::*;

    fn has(language: Language, source: &[u8], rule: &str) -> bool {
        lint_bytes(language, source, "test")
            .iter()
            .any(|diagnostic| diagnostic.rule_id == rule)
    }

    #[test]
    fn finds_only_complete_conflict_blocks() {
        assert!(has(
            Language::Rust,
            b"<<<<<<< a\nx\n=======\ny\n>>>>>>> b\n",
            "KENTO001"
        ));
        assert!(!has(Language::Rust, b"<<<<<<< a\n=======\n", "KENTO001"));
        assert!(!has(
            Language::Rust,
            b"<<<<<<< a\nx\n>>>>>>> b\n",
            "KENTO001"
        ));
        assert!(!has(Language::Rust, b">>>>>>> stray\n", "KENTO001"));
        // A completed block resets the state it consumed. Leaving the separator
        // set would let the next stray `>>>>>>>` claim a block of its own.
        assert_eq!(
            lines_with(
                Language::Rust,
                b"<<<<<<< a\nx\n=======\ny\n>>>>>>> b\n>>>>>>> stray\n",
                "KENTO001"
            ),
            vec![1]
        );
    }

    /// An HTML comment is stepped over as a unit.
    ///
    /// The step is what keeps an apostrophe inside a comment from opening a
    /// string that runs to the end of the file, and what keeps markup inside a
    /// comment from being read as markup. Both fixtures pad the comment so that
    /// a step of the wrong length lands *before* what it was meant to skip
    /// rather than harmlessly past it.
    #[test]
    fn html_comments_are_stepped_over_as_a_unit() {
        // An apostrophe no longer opens a string in markup, so the probe is a
        // raw-text element instead: an opening `<script>` inside a comment,
        // whose closing tag sits below. Read as markup it protects everything
        // between them; stepped over, it protects nothing. The comment is
        // padded so that a step of the wrong length lands in front of the tag.
        assert_eq!(
            lines_with(
                Language::Html,
                b"<!-- xxxx <script> -->\n<p>y</p>   \n</script>\n",
                "KENTO003"
            ),
            vec![2],
            "a script tag inside a comment must not open a protected region"
        );
        assert_eq!(
            lines_with(
                Language::Html,
                b"<!-- xxxx <a href=z href=z> -->\n<a href=p href=q>\n",
                "KENTO201"
            ),
            vec![2],
            "a tag inside a comment is not a tag, wherever it sits in the comment"
        );
    }

    #[test]
    fn reports_final_newline_and_trailing_space_but_not_raw_payload() {
        assert!(has(Language::Rust, b"x ", "KENTO002"));
        assert!(!has(Language::Rust, b"x\n", "KENTO002"));
        // An unterminated final line is still a line: it carries its own
        // findings, not just the missing-newline one.
        assert!(has(Language::Rust, b"x ", "KENTO003"));
        assert!(has(Language::Rust, b"x \n", "KENTO003"));
        assert!(!has(Language::Rust, b"x\r\n", "KENTO003"));
        assert!(has(Language::Rust, b"x \r\n", "KENTO003"));
        assert!(has(Language::Rust, b"x\t\r\n", "KENTO003"));
        assert!(!has(Language::Rust, b"r#\"text   \nmore\"#\n", "KENTO003"));
        assert!(has(Language::Rust, b"// \"not a string\" \n", "KENTO003"));
        assert!(!has(
            Language::Shell,
            b"cat <<END\npayload   \nEND\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Shell,
            b"cat <<'END'\npayload   \nEND\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Shell,
            b"cat <<-END\n\tpayload   \n\tEND\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Shell,
            b"cat <<FIRST <<SECOND\nfirst payload\nFIRST\nsecond payload   \nSECOND\n",
            "KENTO003"
        ));
        assert!(has(
            Language::Shell,
            b"value=$((1 << 2))\necho trailing   \n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Shell,
            b"cat <<ONE<<TWO\nfirst payload\nONE\nsecond payload   \nTWO\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Html,
            b"<SCRIPT>\npayload   \n</SCRIPT>\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Html,
            b"<PRE>\npayload   \n</PRE>\n",
            "KENTO003"
        ));
    }

    #[test]
    fn python_rules_exclude_strings_and_comments() {
        assert!(has(Language::Python, b"except:\n", "KENTO101"));
        assert!(has(
            Language::Python,
            b"try:\n    pass\nexcept \\\n:\n    pass\n",
            "KENTO101"
        ));
        assert!(!has(
            Language::Python,
            b"\"except:\"\n# except:\nexcept ValueError:\n",
            "KENTO101"
        ));
        assert!(has(Language::Python, b"value ==\n None\n", "KENTO102"));
        assert!(has(
            Language::Python,
            b"if value == \\\n    None:\n    pass\n",
            "KENTO102"
        ));
        assert!(has(Language::Python, b"None != value\n", "KENTO102"));
        assert!(has(
            Language::Python,
            b"if value == (None):\n    pass\n",
            "KENTO102"
        ));
        assert!(has(
            Language::Python,
            b"if (None) != value:\n    pass\n",
            "KENTO102"
        ));
        assert!(!has(
            Language::Python,
            b"value == factory(None)\nvalue == (None).attribute\n",
            "KENTO102"
        ));
        assert!(!has(
            Language::Python,
            b"\"x == None\"\n# None == x\n",
            "KENTO102"
        ));
        // The unpaired quote matters: pairing quotes naively would leave the rest
        // of the docstring exposed.
        for rule in ["KENTO101", "KENTO102", "KENTO003"] {
            assert!(
                !has(
                    Language::Python,
                    b"\"\"\"\nhe said \"hi\nexcept:\nx == None   \n\"\"\"\n",
                    rule
                ),
                "{rule} fired inside a triple-quoted string"
            );
        }
    }

    /// The mask walks comments and literals to decide what is *not* code, and a
    /// desynchronized walk goes wrong silently: it either exposes a payload or
    /// swallows real code. Each case here pins one boundary in that walk.
    #[test]
    fn masking_survives_comment_and_literal_boundaries() {
        // An empty block comment must advance past exactly `/**/`. Landing one
        // byte late steps over the quote that opens the literal after it, and
        // the literal's payload is then read as code.
        assert!(!has(
            Language::Rust,
            b"let s = /**/\"a   \nb\";\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Rust,
            b"/**/\nlet s = \"text   \nmore\";\n",
            "KENTO003"
        ));
        assert!(!has(
            Language::Css,
            b"/**/\na { content: \"text   \nmore\"; }\n",
            "KENTO003"
        ));
        // A block comment is skipped, not masked, so an unpaired quote inside it
        // must not open a string that runs past the comment's end.
        assert!(has(
            Language::Rust,
            b"/* \" */\nlet x = 1;   \n",
            "KENTO003"
        ));
        // Raw strings at every hash count, and a `"#` that only looks terminal.
        assert!(!has(Language::Rust, b"let s = r\"text   \";\n", "KENTO003"));
        assert!(!has(
            Language::Rust,
            b"let s = r##\"text   \"#still\"##;\n",
            "KENTO003"
        ));
        // A bare `r` that begins an identifier is not a raw string prefix, and
        // `r#` without a quote is not one either.
        assert!(has(Language::Rust, b"let route = 1;   \n", "KENTO003"));
        assert!(has(Language::Rust, b"let s = r#ident;   \n", "KENTO003"));
        // Only an `r` opens a raw string. Any other byte before the quote leaves
        // an ordinary literal, which processes `\"` instead of ending on it.
        assert!(has(Language::Rust, b"let s = \"a\\\"b\";   \n", "KENTO003"));
        // Single-quoted triples, not only the double-quoted ones.
        assert!(!has(
            Language::Python,
            b"'''\npayload   \n'''\n",
            "KENTO003"
        ));
        for rule in ["KENTO101", "KENTO102", "KENTO003"] {
            assert!(
                !has(
                    Language::Python,
                    b"'''\nhe said 'hi\nexcept:\nx == None   \n'''\n",
                    rule
                ),
                "{rule} fired inside a single-quoted triple string"
            );
        }
        // Arithmetic expansion is consumed as a unit so its `<<` is a shift, not
        // a heredoc. An escape inside it, quoted or not, must not desynchronize
        // the scan: losing the closing paren turns the `<<` into a heredoc that
        // masks the rest of the file.
        assert!(has(
            Language::Shell,
            b"echo $(( \"\\\"\" << 1 ))\ntrailing   \n",
            "KENTO003"
        ));
        assert!(has(
            Language::Shell,
            b"echo $(( 1 \\<< 2 ))\ntrailing   \n",
            "KENTO003"
        ));
        assert!(has(
            Language::Shell,
            b"echo $(( \")\" << 1 ))\ntrailing   \n",
            "KENTO003"
        ));
        assert!(has(
            Language::Shell,
            b"if (( 1 << 2 )); then\n  echo trailing   \nfi\n",
            "KENTO003"
        ));
    }

    /// The Python rules at the edges of a line and of a parenthesised group.
    ///
    /// Both rules had only been shown the easy shape: `except` in the first
    /// column, and a `(None)` sitting directly beside its operator. Real code
    /// indents, and real code puts calls and groups either side of a
    /// comparison.
    #[test]
    fn python_rules_hold_at_line_and_group_edges() {
        for (source, rule, expected, description) in [
            (
                b"def f():\n    try:\n        pass\n    except:\n        pass\n".as_slice(),
                "KENTO101",
                vec![4],
                "an indented bare except is still a bare except",
            ),
            (
                b"\n\nexcept:\n",
                "KENTO101",
                vec![3],
                "blank lines before it are not lines to scan",
            ),
            (
                b"exception = 1\nexcepting = 2\nexcept_ = 3\n",
                "KENTO101",
                vec![],
                "`except` starting a longer name is not the keyword",
            ),
            // A six-letter name followed by a colon lands a colon exactly where
            // a bare `except` would put one. Only the keyword check itself
            // separates the two.
            (
                b"foobar: int = 1\n",
                "KENTO101",
                vec![],
                "an annotation is not an except clause wearing its shape",
            ),
            (
                b"(None) == x\n",
                "KENTO102",
                vec![1],
                "a group opening the file has nothing before it to check",
            ),
            (
                b"value == f(None) != other\n",
                "KENTO102",
                vec![],
                "a call's argument is not a parenthesised operand",
            ),
            // Both operators see the same `(None)`: the first from the right,
            // the second from the left. The token before the group is the other
            // operator, which is a boundary — so both report.
            (
                b"x == (None) != y\n",
                "KENTO102",
                vec![1, 1],
                "an operator is a group boundary like any other",
            ),
        ] {
            assert_eq!(
                lines_with(Language::Python, source, rule),
                expected,
                "{description}"
            );
        }
    }

    /// Arithmetic is consumed whole, and the `<<` inside it is a shift.
    ///
    /// Every fixture puts the `<<` *after* the nesting and quoting, because
    /// that is what makes a wrong answer visible: stop scanning early and the
    /// `<<` is left to read as a heredoc, whose body then masks the rest of the
    /// file. So the probe is not the arithmetic line at all — it is whether the
    /// lines below it still report.
    #[test]
    fn arithmetic_is_consumed_whole_so_its_shift_is_not_a_heredoc() {
        for (source, expected, description) in [
            (
                b"echo $(( (1) + 2 << 3 ))   \npayload   \nmore   \n".as_slice(),
                vec![1, 2, 3],
                "nested parens before the shift",
            ),
            (
                b"echo $(( \"a\" + 2 << 3 ))   \npayload   \nmore   \n",
                vec![1, 2, 3],
                "a quoted operand before the shift",
            ),
            (
                b"echo $(( '(' + 2 << 3 ))   \npayload   \nmore   \n",
                vec![1, 2, 3],
                "a paren inside quotes does not change the depth",
            ),
            (
                b"echo $(( \"\\\"\" + 2 << 3 ))   \npayload   \nmore   \n",
                vec![1, 2, 3],
                "an escaped quote inside a quoted operand",
            ),
            (
                b"if (( (1) + 2 << 3 )); then\n  echo body   \nfi\n",
                vec![2],
                "the bare (( form nests the same way",
            ),
            // An unterminated quote inside the arithmetic abandons it, and the
            // quote then runs to end of file as an open string — the same rule
            // every other unterminated quote here follows.
            (
                b"echo $(( \"abc << 3 ))   \npayload   \nmore   \n",
                vec![],
                "an unterminated quote abandons the arithmetic",
            ),
        ] {
            assert_eq!(
                lines_with(Language::Shell, source, "KENTO003"),
                expected,
                "{description}"
            );
        }
    }

    /// What counts as a tag, and where one attribute ends and the next begins.
    ///
    /// The duplicate-attribute rule is the only one that parses tag internals,
    /// so it is the only probe for them. Two failure directions matter equally:
    /// missing a duplicate that is there, and inventing one in text that was
    /// never a tag — the second is worse, because a linter that fires on prose
    /// is one nobody leaves switched on.
    #[test]
    fn duplicate_attributes_are_found_in_tags_and_only_in_tags() {
        for (source, expected, description) in [
            (
                b"<a href = \"x\" href = \"y\">\n".as_slice(),
                vec![1],
                "spaces before the equals sign",
            ),
            (
                b"<a href= \"x\" href= \"y\">\n",
                vec![1],
                "spaces after the equals sign",
            ),
            (b"<a href='x' href='y'>\n", vec![1], "single-quoted values"),
            (
                b"<a href=x href=y >\n",
                vec![1],
                "unquoted values with trailing space before the close",
            ),
            (
                b"<a href=\"x>y\" href=\"z\">\n",
                vec![1],
                "a > inside a quoted value does not end the tag early",
            ),
            (
                b"<a href=\"x>y\" title=\"z\">\n",
                vec![],
                "and that tag has no duplicate to report",
            ),
            (
                b"<!-- <a href=x href=y> -->\n<a href=p href=q>\n",
                vec![2],
                "a tag inside a comment is not a tag",
            ),
            // Prose is not markup. `set x=1 and x=2 -> done` reads as a tag with
            // a repeated `x` to anything that starts a tag at a plain byte.
            (
                b"<p>set x=1 and x=2 -> done</p>\n",
                vec![],
                "text outside a tag is never parsed as one",
            ),
            (
                b"</a href=x href=x>\n",
                vec![],
                "a closing tag carries no attributes",
            ),
            (
                b"<a href=x href=y>\n<",
                vec![1],
                "a lone < at the end of the buffer reads no further",
            ),
            // A value has to be consumed as a value. Left unconsumed it is read
            // as the next attribute name, and a value that happens to spell an
            // earlier name then invents a duplicate out of nothing.
            (
                b"<a href=x id=href>\n",
                vec![],
                "an unquoted value spelling another name is still a value",
            ),
            (
                b"<a href= x id= href>\n",
                vec![],
                "the same with a space after the equals sign",
            ),
            (b"<a href=\"x\" id=\"href\">\n", vec![], "the same quoted"),
            (
                b"<a href='x' id='href'>\n",
                vec![],
                "the same single-quoted",
            ),
            // Degenerate markup, and deliberately so. A name runs until
            // whitespace, `=` or `/`, so a quote can sit inside one — which
            // means a value whose closing quote is left unconsumed becomes the
            // tail of the next name, and `href="ab"` starts spelling `b"`.
            // There is one real duplicate here, the two `b"` attributes, and
            // exactly one finding must be reported for it.
            (
                b"<a href=\"ab\" b\"=1 b\"=2>\n",
                vec![1],
                "a closing quote is consumed, not left to spell a later name",
            ),
        ] {
            assert_eq!(
                lines_with(Language::Html, source, "KENTO201"),
                expected,
                "{description}"
            );
        }
    }

    /// Bytes that look like an opening quote and are not one.
    ///
    /// Every case here was found by linting real repositories, not by reading
    /// the code. They share one failure: the scanner opens a string that never
    /// closes, masks everything to end of file, and Kento reports the file clean
    /// and exits 0. That is the worst way for a linter to be wrong — a false
    /// positive is loud and gets fixed, and this is silent.
    ///
    /// Each fixture ends with a line carrying trailing whitespace. It must be
    /// reported; a miss means the scanner went blind somewhere above it.
    #[test]
    fn punctuation_that_is_not_a_quote_does_not_open_a_string() {
        for (language, source, description) in [
            // A lifetime is an apostrophe. Two of them pair up by luck; an odd
            // number does not, and odd is the common case.
            (
                Language::Rust,
                b"struct S<'a>(&'a u8);\nstatic X: &'static str = \"\";\nlet y = 1; \n".as_slice(),
                "Rust lifetimes",
            ),
            (
                Language::Rust,
                b"fn f<'a>(x: &'a str) -> &'a str { x }\nlet y = 1; \n",
                "an odd number of Rust lifetimes",
            ),
            // ...but a char literal really is one, and still masks its content.
            (
                Language::Rust,
                b"let c = '\\'';\nlet d = 'x';\nlet y = 1; \n",
                "Rust char literals, including an escaped quote",
            ),
            // A regular expression is not a string, and the quotes in it are
            // not delimiters.
            (
                Language::JavaScript,
                b"var re = /f?'[^']*'/g;\nvar y = 1; \n",
                "a JavaScript regex holding quotes",
            ),
            (
                Language::TypeScript,
                b"const re = /'/g;\nconst y = 1; \n",
                "a TypeScript regex holding a quote",
            ),
            // Division is not a regex. If it were read as one, the span between
            // two slashes would stop being scanned.
            (
                Language::JavaScript,
                b"var z = a / b / c;\nvar y = 1; \n",
                "JavaScript division, which is not a regex",
            ),
            // In markup an apostrophe is punctuation. Quotes delimit attribute
            // values, and only inside a tag.
            (
                Language::Html,
                b"<p>didn't match</p>\n<p>x</p> \n",
                "an apostrophe in HTML prose",
            ),
            // A backslash escapes the next byte in CSS wherever it appears, not
            // only inside a string.
            (
                Language::Css,
                b".a\\'b { color: red; }\nbody { color: blue; } \n",
                "an escaped quote in a CSS selector",
            ),
            // `<<<` is a here-string. Only `<<` opens a heredoc, and reading the
            // second `<` of three as the start of one masks the rest of the file.
            (
                Language::Shell,
                b"cat <<< 'text'\necho hi \n",
                "a shell here-string",
            ),
        ] {
            let lines = lines_with(language, source, "KENTO003");
            let last = source.split(|byte| *byte == b'\n').count() - 1;
            assert!(
                lines.contains(&last),
                "{description}: nothing reported on line {last}, so the scan went \
                 blind above it — findings were {lines:?}"
            );
        }
    }

    /// The two decisions the scanner makes about an ambiguous byte.
    ///
    /// A `'` in Rust is a character literal or a lifetime; a `/` in JavaScript
    /// opens a regular expression or divides. Both readings mask different
    /// spans, so each fixture puts a quote where only one reading survives it,
    /// and the trailing whitespace on the last line says which reading won.
    #[test]
    fn ambiguous_bytes_are_read_the_way_the_language_reads_them() {
        for (language, source, expected, description) in [
            // A character literal holds its content, quote characters included.
            // Read as a lifetime, that `"` opens a string that never closes.
            (
                Language::Rust,
                b"let c = '\"';\nlet y = 1; \n".as_slice(),
                vec![2],
                "a Rust char literal holding a double quote",
            ),
            (
                Language::Rust,
                b"let c = '\\\\';\nlet y = 1; \n",
                vec![2],
                "a Rust char literal holding an escaped backslash",
            ),
            // A label is a name, not a literal, however short.
            (
                Language::Rust,
                b"'a: loop { break 'a; }\nlet y = 1; \n",
                vec![2],
                "a Rust loop label",
            ),
            // A file may open with a regular expression: there is no token
            // before it to judge by.
            (
                Language::JavaScript,
                b"/'/.test(s);\nvar y = 1; \n",
                vec![2],
                "a regex as the very first token",
            ),
            // After a keyword a slash still opens one...
            (
                Language::JavaScript,
                b"function f(s) { return /'/.test(s); }\nvar y = 1; \n",
                vec![2],
                "a regex after `return`",
            ),
            // ...but after a name, a number or a closing bracket it divides,
            // and the quote between these slashes stays a quote.
            (
                Language::JavaScript,
                b"var q = (a) / \"x\n\" / b;\nvar y = 1; \n",
                vec![3],
                "division after a closing parenthesis",
            ),
            // An escaped slash does not end the expression, and a slash inside
            // a character class is not the end either.
            (
                Language::JavaScript,
                b"var re = /a\\/'/g;\nvar y = 1; \n",
                vec![2],
                "a regex holding an escaped slash",
            ),
            (
                Language::JavaScript,
                b"var re = /[/']/g;\nvar y = 1; \n",
                vec![2],
                "a regex whose character class holds a slash",
            ),
            // A `/` with no closing `/` before the newline is not a regex, so
            // the scan must fall through rather than swallow the line.
            (
                Language::JavaScript,
                b"var q = 6 / 2;\nvar y = 1; \n",
                vec![2],
                "a lone division with no second slash",
            ),
            // The rest turn on which reading wins, so each leaves a quote
            // unclosed: read as division the quote opens a string that runs to
            // the end of the file and the last line goes quiet, read as a regex
            // the quote is skipped with it and the last line reports.
            (
                Language::JavaScript,
                b"var a = x / \"y / 3;\nvar z = 1; \n",
                vec![],
                "after a name it divides, so the quote opens a string",
            ),
            (
                Language::JavaScript,
                b"var a_ = 2;\nvar b = a_ / \"y / 3;\nvar z = 1; \n",
                vec![],
                "an underscore ends a name like any other name byte",
            ),
            (
                Language::JavaScript,
                b"var s = \"text / more;\nvar y = 1; \n",
                vec![],
                "a quote is not a slash and does not begin an expression",
            ),
            // Degenerate on purpose. What precedes the `/` is the *string* that
            // ends just before it, not the `)` before that string, and the two
            // read the slash differently.
            (
                Language::JavaScript,
                b"var a = f()\"x\" / \"y / 3;\nvar z = 1; \n",
                vec![2],
                "the token before a slash is the string that just closed",
            ),
        ] {
            assert_eq!(
                lines_with(language, source, "KENTO003"),
                expected,
                "{description}"
            );
        }
    }

    /// Raw and triple-quoted strings end where their own syntax says, not where
    /// an ordinary quote would.
    ///
    /// The distinction only shows when the two readings disagree, so every
    /// fixture holds a quote that ends the string under one reading and not the
    /// other, with the probe placed after the close. Two of them sit at the end
    /// of the buffer, where the prefix checks are all that stand between the
    /// scanner and an index past the last byte.
    #[test]
    fn raw_and_triple_quoted_strings_end_on_their_own_terms() {
        for (language, source, expected, description) in [
            (
                Language::Rust,
                b"let s = r\"a\\\";   \n".as_slice(),
                vec![1],
                "a raw string ends at the first quote, escape or not",
            ),
            (
                Language::Rust,
                b"let s = r#\"a\"b\"#;   \n",
                vec![1],
                "a hashed raw string ends only at a quote with matching hashes",
            ),
            (
                Language::Rust,
                b"let a = r",
                vec![],
                "a trailing `r` is not a raw string prefix and reads no further",
            ),
            (
                Language::Python,
                b"a = r\"x\\\"   \n",
                vec![],
                "Python has no Rust raw strings: the escape is an escape",
            ),
            (
                Language::Python,
                b"a = ''   \n",
                vec![1],
                "two quotes are an empty string, not the start of a triple",
            ),
            (
                Language::Python,
                b"'''\npay   \n''x\n'''   \n",
                vec![4],
                "a triple closes on three quotes, not on two and anything",
            ),
        ] {
            assert_eq!(
                lines_with(language, source, "KENTO003"),
                expected,
                "{description}"
            );
        }
    }

    /// Every form a heredoc delimiter can take, and the exact span each masks.
    ///
    /// The delimiter is parsed with the shell's own quoting and escaping rules,
    /// and getting it wrong is not a small error: an unrecognised delimiter is
    /// never matched, so the body runs to the end of the file and every finding
    /// after it disappears. The fixtures below reach the escape and quote paths
    /// that the plain `<<END` cases never do.
    #[test]
    fn heredoc_delimiters_are_parsed_the_way_the_shell_writes_them() {
        for (source, expected, description) in [
            (
                b"cat <<E\\ND   \npayload   \nEND\necho done   \n".as_slice(),
                vec![1, 4],
                "a backslash escape in a bare delimiter",
            ),
            (
                b"cat <<\"E\\\"D\"   \npayload   \nE\"D\necho done   \n",
                vec![1, 4],
                "a double-quoted delimiter holding an escaped quote",
            ),
            (
                b"cat <<'E\\D'   \npayload   \nE\\D\necho done   \n",
                vec![1, 4],
                "a single-quoted delimiter, where a backslash is literal",
            ),
            (
                b"cat <<-  END   \n\tpayload   \n\tEND\necho done   \n",
                vec![1, 4],
                "blanks between <<- and the delimiter",
            ),
            (
                b"cat <<END \"a # b\"   \npayload   \nEND\necho done   \n",
                vec![1, 4],
                "a # inside a quoted word is not a comment",
            ),
            (
                b"cat <<END \"a\\\"b\"   \npayload   \nEND\necho done   \n",
                vec![1, 4],
                "an escaped quote inside a word on the operator's line",
            ),
            (
                b"cat <<END # note   \npayload   \nEND\necho done   \n",
                vec![1, 4],
                "a real comment after the operator still starts the body next line",
            ),
            // A quoted `<<` on the operator's line is a string, not a second
            // heredoc. Reading it as one queues a body that never terminates,
            // and everything below is masked away.
            (
                b"cat <<END \"x<<OTHER\"   \npayload   \nEND\necho done   \n",
                vec![1, 4],
                "a << inside quotes does not open a second heredoc",
            ),
            // An unterminated quote yields no delimiter, so there is no heredoc
            // and nothing is masked as a body. The quote itself is still an
            // unterminated string, which runs to the end of the file exactly as
            // one does in every other language here — so the findings after it
            // disappear for that reason, not because a body swallowed them.
            (
                b"cat <<\"END   \npayload   \n",
                vec![],
                "an unterminated quote yields no heredoc, only an open string",
            ),
            // A body with no terminator runs to the end of the file, which is
            // what the shell does with it.
            (
                b"cat <<END   \npayload   \nnot the end   \n",
                vec![1],
                "an unterminated body masks through end of file",
            ),
        ] {
            assert_eq!(
                lines_with(Language::Shell, source, "KENTO003"),
                expected,
                "{description}"
            );
        }
    }

    /// Protected raw-text elements are matched by exact name. A prefix match
    /// would treat `<pretend>` as `<pre>` and mask ordinary markup.
    #[test]
    fn protected_html_elements_match_by_exact_name() {
        for (document, description) in [
            (b"<pretend>payload   \n</pre>\n".as_slice(), "pre"),
            (b"<scriptish>payload   \n</script>\n", "script"),
            (b"<styled>payload   \n</style>\n", "style"),
        ] {
            assert!(
                has(Language::Html, document, "KENTO003"),
                "a tag merely starting with `{description}` was treated as it"
            );
        }
        // A `<` that does not open a tag at all must not be read as one. Here the
        // element name never matches, so nothing downstream is protected.
        assert!(has(
            Language::Html,
            b"x < pre>payload   \n</pre>\n",
            "KENTO003"
        ));
        // The real elements still protect their payloads.
        assert!(!has(
            Language::Html,
            b"<pre>payload   \n</pre>\n",
            "KENTO003"
        ));
    }

    /// Protection starts where the opening tag ends, so trailing whitespace
    /// inside that tag is ordinary markup. A `>` in a quoted attribute value
    /// does not end the tag, and so must not start the protected span early.
    #[test]
    fn protection_starts_where_the_opening_tag_actually_ends() {
        assert!(has(
            Language::Html,
            b"<script\n  src=\"a>b\" \n>\npayload\n</script>\n",
            "KENTO003"
        ));
    }

    /// Every line carrying `rule`, in order. Line numbers are what pins a mask
    /// boundary: `has` only says a finding exists somewhere, which a boundary
    /// off by one whole line still satisfies.
    fn lines_with(language: Language, source: &[u8], rule: &str) -> Vec<usize> {
        lint_bytes(language, source, "test")
            .iter()
            .filter(|diagnostic| diagnostic.rule_id == rule)
            .map(|diagnostic| diagnostic.line)
            .collect()
    }

    /// Where each masked region begins and ends, to the byte.
    ///
    /// Trailing whitespace is the probe: it is reported outside a masked region
    /// and suppressed inside one, so the set of reporting lines states the mask
    /// boundary exactly. Every fixture puts a violation on the line before the
    /// region, inside it, and on the line that closes it — an edge that moves in
    /// either direction changes the answer.
    #[test]
    fn masked_regions_begin_and_end_where_the_syntax_says() {
        for (language, source, expected, description) in [
            (
                Language::Rust,
                b"let a = 1;   \nlet b = \"x   \ny\";   \n".as_slice(),
                vec![1, 3],
                "a string masks from its opening quote to its closing one",
            ),
            (
                Language::Rust,
                b"let a = 1;   \nlet b = r#\"x   \ny\"#;   \n",
                vec![1, 3],
                "a raw string ends at its matching hash count, not the first quote",
            ),
            (
                Language::Python,
                b"a = 1   \nb = \"\"\"x   \ny\"\"\"   \n",
                vec![1, 3],
                "a triple-quoted string masks its body only",
            ),
            (
                Language::Shell,
                b"echo hi   \ncat <<END   \npayload   \nEND\necho bye   \n",
                vec![1, 2, 5],
                "a heredoc body starts on the line after the operator, not at it",
            ),
            (
                Language::Shell,
                b"echo hi   \ncat <<'END'   \npayload   \nEND\necho bye   \n",
                vec![1, 2, 5],
                "a quoted heredoc delimiter masks the same span as a bare one",
            ),
            (
                Language::Html,
                b"<p>a</p>   \n<script>   \npayload   \n</script>   \n",
                vec![1, 4],
                "a raw-text element masks between its tags, not through them",
            ),
            // Comments are stepped over, never masked: the step exists so a quote
            // inside one cannot open a string, and the trailing whitespace in a
            // comment is a finding like any other. Both fixtures below carry a
            // lone quote, so a step that lands wrong opens a string and silences
            // every line after it.
            (
                Language::Rust,
                b"let a = 1;   \n/* \" x   \n*/ let b = 2;   \nlet c = 3;   \n",
                vec![1, 2, 3, 4],
                "a block comment is stepped over without masking",
            ),
            (
                Language::Css,
                b"a { }   \n/* \" x   \n*/ b { }   \nc { }   \n",
                vec![1, 2, 3, 4],
                "a CSS comment is stepped over without masking",
            ),
        ] {
            assert_eq!(
                lines_with(language, source, "KENTO003"),
                expected,
                "{description}"
            );
        }
    }

    #[test]
    fn css_and_html_are_lexical() {
        assert!(has(Language::Css, b"\"/*\"\n/* open", "KENTO301"));
        assert!(!has(Language::Css, b"\"/*\"\n/* closed */\n", "KENTO301"));
        assert!(!has(Language::Css, b"a { content: \"/*\"; }\n", "KENTO301"));
        // The `/*` sits a byte inside the string rather than against the quote,
        // so a scan that closes the string one byte early still meets it.
        assert!(!has(
            Language::Css,
            b"a { content: \"x/*y\"; }\n",
            "KENTO301"
        ));
        assert!(!has(Language::Css, b"a { content: '/*'; }\n", "KENTO301"));
        assert!(has(Language::Html, b"<a HREF=x href=y>\n", "KENTO201"));
        // A quoted attribute value is skipped whole: names inside it are text,
        // even when they repeat and would otherwise read as duplicate attributes.
        assert!(!has(
            Language::Html,
            b"<a href=\"x x\" title=y>\n",
            "KENTO201"
        ));
        assert!(!has(
            Language::Html,
            b"<a href='x x' title=y>\n",
            "KENTO201"
        ));
        assert!(!has(
            Language::Html,
            b"<div class=\"row a a \" id=y>\n",
            "KENTO201"
        ));
        // An unterminated quoted value must not resurface as attributes either.
        assert!(!has(Language::Html, b"<a href=\"x x>\n", "KENTO201"));
        assert!(!has(
            Language::Html,
            b"<!-- <a x x> --><script><a x x></script>\n",
            "KENTO201"
        ));
        assert!(!has(
            Language::Html,
            b"<script nonce=\"{{ nonce }}\">const value = \"<a x x>\";</script>\n",
            "KENTO201"
        ));
        assert!(!has(Language::Html, b"<a {{ value }} x x>\n", "KENTO201"));
    }
}

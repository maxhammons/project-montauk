#!/usr/bin/env python3
"""Generate every single-token semantic mutation of Kento's product code and
measure how many the suite catches.

Not the curated gate: this enumerates sites mechanically, so it finds guards
nobody thought to name. Skips #[cfg(test)] blocks, comments, and string/char
literals — a mutation inside any of those is either a no-op that would report as
a false survivor, or not a semantic change at all.
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/Max.Hammons/Developer/local-sandbox/kento")
FILES = ["src/app.rs", "src/install.rs", "src/lint.rs", "src/toolchain.rs", "src/types.rs"]
TIMEOUT = 300

# Longest first so `<=` is matched before `<`.
SWAPS = [
    ("&&", "||"), ("||", "&&"),
    ("==", "!="), ("!=", "=="),
    ("<=", ">"), (">=", "<"),
    ("<", ">="), (">", "<="),
    ("+=", "-="),
    ("true", "false"), ("false", "true"),
]


def code_spans(text):
    """Yield (offset, line_number) for byte offsets that are real code."""
    in_block_comment = False
    in_string = False
    in_char = False
    raw_hashes = None
    offset = 0
    line_number = 1
    index = 0
    # Everything from the test module onward is off limits.
    limit = text.find("#[cfg(test)]")
    limit = len(text) if limit < 0 else limit
    while index < limit:
        rest = text[index:]
        if text[index] == "\n":
            line_number += 1
            index += 1
            continue
        if in_block_comment:
            if rest.startswith("*/"):
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue
        if raw_hashes is not None:
            if rest.startswith('"' + "#" * raw_hashes):
                index += 1 + raw_hashes
                raw_hashes = None
            else:
                index += 1
            continue
        if in_string:
            if text[index] == "\\":
                index += 2
            elif text[index] == '"':
                in_string = False
                index += 1
            else:
                index += 1
            continue
        if in_char:
            if text[index] == "\\":
                index += 2
            elif text[index] == "'":
                in_char = False
                index += 1
            else:
                index += 1
            continue
        if rest.startswith("//"):
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
            continue
        if rest.startswith("/*"):
            in_block_comment = True
            index += 2
            continue
        if rest.startswith('r"') or (rest.startswith("r#") and '"' in rest[:8]):
            hashes = 0
            probe = index + 1
            while probe < len(text) and text[probe] == "#":
                hashes += 1
                probe += 1
            if probe < len(text) and text[probe] == '"':
                raw_hashes = hashes
                index = probe + 1
                continue
        if text[index] == '"':
            in_string = True
            index += 1
            continue
        # A byte/char literal, but not a lifetime like 'a or a label.
        if text[index] == "'" and index + 2 < len(text) and text[index + 2] in "'\\":
            in_char = True
            index += 1
            continue
        yield index, line_number
        index += 1


def mutations():
    found = []
    for relative in FILES:
        text = (REPO / relative).read_text()
        offsets = dict(code_spans(text))
        for offset, line_number in sorted(offsets.items()):
            for find, replace in SWAPS:
                if not text.startswith(find, offset):
                    continue
                if find in ("<", ">"):
                    before = text[offset - 1] if offset else " "
                    after = text[offset + 1] if offset + 1 < len(text) else " "
                    if before != " " or after != " ":
                        continue
                if find in ("true", "false"):
                    before = text[offset - 1] if offset else " "
                    after_index = offset + len(find)
                    after = text[after_index] if after_index < len(text) else " "
                    if before.isalnum() or before == "_" or after.isalnum() or after == "_":
                        continue
                # Only the first matching swap per site, so `<=` does not also
                # register as `<`.
                found.append((relative, offset, line_number, find, replace))
                break
    return found


def apply(relative, offset, find, replace):
    path = REPO / relative
    text = path.read_text()
    assert text.startswith(find, offset)
    path.write_text(text[:offset] + replace + text[offset + len(find) :])


def restore():
    subprocess.run(["git", "checkout", "--", "src"], cwd=REPO, check=True, capture_output=True)


def run_suite(arguments, timeout):
    process = subprocess.Popen(
        ["cargo", "test", "--quiet"] + arguments, cwd=REPO,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        output = process.communicate(timeout=timeout)[0]
        return process.returncode, output
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        process.wait()
        return None, "TIMEOUT"


def evaluate(relative, offset, line_number, find, replace):
    apply(relative, offset, find, replace)
    try:
        code, output = run_suite(["--lib"], 45)
        if code is None:
            return "CAUGHT-HANG", ""
        if "error[E" in output or "could not compile" in output:
            return "UNCOMPILABLE", ""
        if code != 0:
            return "CAUGHT-UNIT", ""
        code, output = run_suite(["--test", "integration"], 180)
        if code is None:
            return "CAUGHT-HANG", ""
        if "error[E" in output or "could not compile" in output:
            return "UNCOMPILABLE", ""
        return ("SURVIVED" if code == 0 else "CAUGHT-INTEGRATION"), ""
    finally:
        restore()


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("src/ is dirty; commit first")
        return 2

    all_mutations = mutations()
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    stop = int(sys.argv[2]) if len(sys.argv) > 2 else len(all_mutations)
    print(f"{len(all_mutations)} mutation sites; evaluating [{start}:{stop}]", flush=True)

    results = []
    for index in range(start, min(stop, len(all_mutations))):
        relative, offset, line_number, find, replace = all_mutations[index]
        verdict, _ = evaluate(relative, offset, line_number, find, replace)
        line = f"{index:4} {verdict:15} {relative}:{line_number} {find!r} -> {replace!r}"
        print(line, flush=True)
        results.append({"index": index, "verdict": verdict, "file": relative,
                        "line": line_number, "find": find, "replace": replace})

    out = Path("/private/tmp/claude-502/-Users-Max-Hammons/24c9374e-2492-40cf-a4da-00b2a68f07ab/scratchpad")
    out.joinpath(f"sweep-{start}-{stop}.json").write_text(json.dumps(results, indent=1))
    viable = [r for r in results if r["verdict"] != "UNCOMPILABLE"]
    caught = [r for r in viable if r["verdict"].startswith("CAUGHT")]
    survivors = [r for r in viable if r["verdict"] == "SURVIVED"]
    print(f"\ncaught {len(caught)}/{len(viable)} viable")
    for r in survivors:
        print(f"  SURVIVOR {r['file']}:{r['line']} {r['find']!r} -> {r['replace']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

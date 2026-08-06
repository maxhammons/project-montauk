#!/usr/bin/env python3
"""Parallel mutation sweep: the serial harness from docs/kento-broad-sweep.py,
sharded across git worktrees so no two mutants share a src/ or a target dir.

Enumeration is byte-identical to the serial version — index N here is the same
site as index N there, so partial logs stay comparable.

Cargo names test binaries `<target>-<metadata-hash>`, which no harness can
change. What it can do is make the *path* say which shard a spinning process
belongs to, and keep a status file so `ps` is never the diagnostic tool:

    python3 sweep.py --status     # what every shard is running, and for how long
    python3 sweep.py --strays     # test binaries this harness left behind

The exit status is a verdict, not a courtesy: 0 means every evaluated site got
a record and every survivor is a documented equivalent from
tools/equivalent-mutants.txt. Survivors outside that list, ERROR records,
missing records, stray test binaries, or a rewritten pre-commit hook all exit 1.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("KENTO_SWEEP_DIR", "/tmp/kento-sweep")).resolve()
# Named so `ps` reads as kento-sweep-s3/target/... rather than wt/s3/target/...
WORKTREES = OUT / "worktrees"
SHARD_PREFIX = "kento-sweep-s"
STATUS = OUT / "status"
# Every file holding product logic. A file missing from this list is not scored
# low, it is not scored at all — which is how `maintenance.rs` shipped with no
# measurement behind it.
FILES = [
    "src/app.rs",
    "src/install.rs",
    "src/lint.rs",
    "src/maintenance.rs",
    "src/toolchain.rs",
    "src/types.rs",
]

# A clean --lib run is ~0.4s and a clean --test integration run is ~6s, or ~50s
# with every shard loading the machine. Anything past these is a mutation that
# turned a scanner loop into an infinite one, and every extra second is a core
# spinning at 100% for nothing.
LIB_TIMEOUT = 45
INTEGRATION_TIMEOUT = 120

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
    line_number = 1
    index = 0
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
                found.append((relative, offset, line_number, find, replace))
                break
    return found


def allowed_survivors():
    """The proven-equivalent sites from tools/equivalent-mutants.txt.

    Each line is `file:line find replace`. A survivor not in this set fails
    the sweep, so the score is a gate rather than a report someone has to
    remember to read.
    """
    allowed = set()
    for line in (REPO / "tools" / "equivalent-mutants.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        site, find, replace = line.split()
        relative, line_number = site.rsplit(":", 1)
        allowed.add((relative, int(line_number), find, replace))
    return allowed


def repository_hook():
    """The main checkout's pre-commit hook, or None.

    A mutant can invert `--no-hook`, and before the workspaces were real
    repositories a mutated `install` resolved its hook path to *this* checkout
    and wrote there. The suite fix makes that unreachable; this makes it
    unmissable if it ever comes back, because the symptom otherwise appears
    hours later as an unrelated commit failure.
    """
    path = REPO / ".git" / "hooks" / "pre-commit"
    return path.read_text() if path.exists() else None


def stray_processes():
    """Test binaries under our worktrees that are still running."""
    listing = subprocess.run(["ps", "-eo", "pid,etime,command"],
                             capture_output=True, text=True).stdout.splitlines()
    return [line.strip() for line in listing
            if str(WORKTREES) in line and "/target/debug/deps/" in line]


def run_suite(tree, arguments, timeout):
    environment = dict(os.environ, CARGO_TARGET_DIR=str(tree / "target"))
    environment.pop("RUSTFLAGS", None)
    process = subprocess.Popen(
        ["cargo", "test", "--quiet"] + arguments, cwd=tree,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True, env=environment,
    )
    try:
        return process.communicate(timeout=timeout)[0], process.returncode
    except subprocess.TimeoutExpired:
        # The group, not the process: cargo's child is what spins.
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        process.wait()
        return "TIMEOUT", None


def ensure_toolchain():
    """Installs the pinned toolchain, serially, before any shard needs it.

    Rustup installs a missing pinned toolchain on first use, and several
    shards hitting that install concurrently race in ~/.rustup/downloads —
    seen on a fresh CI runner as `could not rename 'downloaded' file`, which
    failed every shard's warm-up at once. One `cargo --version` in the main
    checkout resolves (and if needed installs) the pin with nobody to race.
    Returns None, or what went wrong.
    """
    probe = subprocess.run(["cargo", "--version"], cwd=REPO,
                           capture_output=True, text=True)
    if probe.returncode == 0:
        return None
    lines = [line for line in probe.stderr.splitlines() if line.strip()]
    return f"cannot provision the pinned toolchain: {lines[-1] if lines else 'no output'}"


def warm(tree):
    """Builds the unmutated tree's test binaries, with no timeout.

    Without this, the first evaluation in a fresh worktree pays the whole
    compile — and on a fresh machine the toolchain download too — inside the
    mutant's timeout, and a cold build is scored CAUGHT-HANG: a false kill
    that inflates the score. Returns None, or what went wrong.
    """
    for arguments in (["--lib"], ["--test", "integration"]):
        output, code = run_suite(tree, ["--no-run"] + arguments, None)
        if code != 0:
            lines = [line for line in output.splitlines() if line.strip()]
            return f"cannot build {tree.name}: {lines[-1] if lines else 'no output'}"
    return None


def evaluate(tree, relative, offset, find, replace):
    path = tree / relative
    text = path.read_text()
    assert text.startswith(find, offset), f"{relative}@{offset} is not {find!r}"
    path.write_text(text[:offset] + replace + text[offset + len(find):])
    try:
        for arguments, timeout in ((["--lib"], LIB_TIMEOUT),
                                   (["--test", "integration"], INTEGRATION_TIMEOUT)):
            output, code = run_suite(tree, arguments, timeout)
            if code is None:
                return "CAUGHT-HANG"
            if "error[E" in output or "could not compile" in output:
                return "UNCOMPILABLE"
            if code != 0:
                return "CAUGHT-UNIT" if arguments == ["--lib"] else "CAUGHT-INTEGRATION"
        return "SURVIVED"
    finally:
        subprocess.run(["git", "checkout", "--", "src"], cwd=tree, check=True, capture_output=True)


def worker(shard, tree, work, lock, sink):
    status = STATUS / f"{SHARD_PREFIX}{shard}.json"
    status.write_text(json.dumps({
        "shard": shard, "index": None, "site": "warm-up build",
    }))
    failure = warm(tree)
    for index, (relative, offset, line_number, find, replace) in work:
        status.write_text(json.dumps({
            "shard": shard, "index": index, "site": f"{relative}:{line_number}",
            "mutation": f"{find} -> {replace}", "started": time.time(),
        }))
        try:
            # A shard whose baseline does not build has no verdict to offer on
            # anything; saying so per record is what makes the gate fail loudly
            # instead of the shard's sites silently vanishing from the total.
            verdict = f"ERROR(warm-up: {failure})" if failure else \
                evaluate(tree, relative, offset, find, replace)
        except Exception as error:  # a shard must never take the sweep down with it
            verdict = f"ERROR({type(error).__name__})"
        record = {"index": index, "verdict": verdict, "file": relative,
                  "line": line_number, "find": find, "replace": replace}
        with lock:
            print(f"{index:4} s{shard} {verdict:19} {relative}:{line_number} "
                  f"{find!r} -> {replace!r}", flush=True)
            sink.write(json.dumps(record) + "\n")
            sink.flush()
    status.write_text(json.dumps({"shard": shard, "index": None, "site": "idle"}))


def show_status():
    now = time.time()
    for path in sorted(STATUS.glob(f"{SHARD_PREFIX}*.json")):
        state = json.loads(path.read_text())
        if state.get("index") is None:
            print(f"  s{state['shard']:<2} idle")
            continue
        print(f"  s{state['shard']:<2} #{state['index']:<4} {state['site']:24} "
              f"{state['mutation']:16} {now - state['started']:6.1f}s")
    strays = stray_processes()
    print(f"\n{len(strays)} test binaries running under {WORKTREES.name}/")
    return 0


def main():
    if "--status" in sys.argv:
        return show_status()
    if "--strays" in sys.argv:
        strays = stray_processes()
        print("\n".join(strays) if strays else "no strays")
        return 0

    # The stop index defaults to the current population, never to a constant: a
    # constant goes stale the day a file grows, and a no-argument run would then
    # silently skip the tail — which is exactly how maintenance.rs once shipped
    # with no measurement behind it. `all` says the same thing explicitly, for
    # callers that need to reach the shard-count argument behind it.
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    stop = None if len(sys.argv) <= 2 or sys.argv[2] == "all" else int(sys.argv[2])
    shards = int(sys.argv[3]) if len(sys.argv) > 3 else 6

    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("src/ is dirty; commit first")
        return 2
    strays = stray_processes()
    if strays:
        print(f"{len(strays)} test binaries from an earlier run are still alive; "
              f"kill them first:\n" + "\n".join(strays))
        return 2

    provisioning = ensure_toolchain()
    if provisioning:
        print(provisioning)
        return 2

    hook_before = repository_hook()
    STATUS.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout.strip()
    trees = []
    for shard in range(shards):
        tree = WORKTREES / f"{SHARD_PREFIX}{shard}"
        if not tree.exists():
            subprocess.run(["git", "worktree", "add", "--detach", str(tree), head],
                           cwd=REPO, check=True, capture_output=True)
        trees.append(tree)

    all_mutations = mutations()
    if stop is None:
        stop = len(all_mutations)
    work = [(index, all_mutations[index]) for index in range(start, min(stop, len(all_mutations)))]
    print(f"{len(all_mutations)} sites; evaluating [{start}:{stop}] over {shards} worktrees",
          flush=True)

    lock = threading.Lock()
    with open(OUT / f"sweep-{start}-{stop}.jsonl", "w") as sink:
        threads = [threading.Thread(target=worker,
                                    args=(shard, trees[shard], work[shard::shards], lock, sink))
                   for shard in range(shards)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    records = [json.loads(line) for line in (OUT / f"sweep-{start}-{stop}.jsonl").read_text().splitlines()]
    viable = [r for r in records if r["verdict"] != "UNCOMPILABLE"]
    caught = [r for r in viable if r["verdict"].startswith("CAUGHT")]
    errors = [r for r in records if r["verdict"].startswith("ERROR")]
    survivors = sorted((r for r in viable if r["verdict"] == "SURVIVED"),
                       key=lambda r: (r["file"], r["line"]))
    allowed = allowed_survivors()
    unexplained = [r for r in survivors
                   if (r["file"], r["line"], r["find"], r["replace"]) not in allowed]
    print(f"\ncaught {len(caught)}/{len(viable)} viable = "
          f"{100 * len(caught) / max(len(viable), 1):.1f}% "
          f"({len(records) - len(viable)} uncompilable)")
    for record in survivors:
        key = (record["file"], record["line"], record["find"], record["replace"])
        marker = "documented equivalent" if key in allowed else "NOT IN THE ALLOWLIST"
        print(f"  SURVIVOR {record['file']}:{record['line']} "
              f"{record['find']!r} -> {record['replace']!r} — {marker}")
    survived_keys = {(r["file"], r["line"], r["find"], r["replace"]) for r in survivors}
    evaluated = {(relative, line_number, find, replace)
                 for _, (relative, _, line_number, find, replace) in work}
    for relative, line_number, find, replace in sorted(allowed & (evaluated - survived_keys)):
        print(f"  STALE ALLOWLIST ENTRY {relative}:{line_number} {find!r} -> {replace!r} "
              f"did not survive; update tools/equivalent-mutants.txt")

    leftover = stray_processes()
    print(f"\nleftover test binaries: {len(leftover)}")
    for line in leftover:
        print(f"  {line}")

    # Anything short of "every evaluated site has a verdict, every survivor is
    # explained, nothing was left running, nothing was tampered with" is a
    # failure. A sweep that exits 0 with survivors in its output is a report
    # someone has to remember to read; this is a gate.
    failed = False
    if len(records) != len(work):
        print(f"FAIL: {len(work) - len(records)} of {len(work)} sites have no record")
        failed = True
    if errors:
        for record in errors:
            print(f"FAIL: {record['verdict']} at {record['file']}:{record['line']}")
        failed = True
    if unexplained:
        print(f"FAIL: {len(unexplained)} survivors are not documented equivalents")
        failed = True
    if leftover:
        print("FAIL: test binaries left running")
        failed = True
    if repository_hook() != hook_before:
        print("FAIL: a mutant rewrote this checkout's pre-commit hook. "
              "Inspect .git/hooks/pre-commit before committing anything.")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

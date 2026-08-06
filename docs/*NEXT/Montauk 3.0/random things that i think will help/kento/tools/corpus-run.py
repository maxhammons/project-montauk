#!/usr/bin/env python3
"""Run Kento over real repositories and check the things a mutation sweep cannot.

Mutation testing asks "would the tests notice a regression". This asks the
questions that only real input can: does it ever crash, does it ever hang, and
does it give the same answer twice. A linter an agent is told to obey has to be
all three on code nobody wrote for it.
"""

import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

CORPUS = Path(os.environ.get("KENTO_CORPUS", "/tmp/kento-corpus")).resolve()
OUT = CORPUS.parent / "kento-corpus-out"
KENTO = Path(sys.argv[1]) if len(sys.argv) > 1 else None
TIMEOUT = 900


def run(repo):
    """One `kento all` over one repository. Returns (code, seconds, stdout, stderr)."""
    started = time.time()
    process = subprocess.Popen(
        [str(KENTO), "all", "--format", "jsonl"], cwd=repo,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=TIMEOUT)
        return process.returncode, time.time() - started, out, err
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        process.wait()
        return None, time.time() - started, b"", b"TIMEOUT"


def main():
    OUT.mkdir(exist_ok=True)
    repos = sorted(path for path in CORPUS.iterdir() if (path / ".git").exists())
    failures = []

    for repo in repos:
        results = []
        for pass_number in (1, 2):
            code, seconds, out, err = run(repo)
            (OUT / f"{repo.name}.{pass_number}.jsonl").write_bytes(out)
            (OUT / f"{repo.name}.{pass_number}.err").write_bytes(err)
            results.append((code, seconds, out, err))

        (code, seconds, out, err) = results[0]
        findings = out.count(b"\n")
        digest = hashlib.sha256(out).hexdigest()[:12]
        text = err.decode("utf-8", "replace")

        print(f"{repo.name:12} exit={code!s:5} {seconds:6.1f}s  "
              f"findings={findings:<6} sha={digest}")

        # A crash is any exit outside the documented contract. `None` is a hang.
        if code not in (0, 1, 2):
            failures.append(f"{repo.name}: exit {code}")
        if any(word in text.lower() for word in ("panic", "backtrace", "stack overflow")):
            failures.append(f"{repo.name}: panic in stderr")
        # Two empty outputs agree trivially, so identical output only counts as
        # determinism when there was output to disagree about.
        if results[0][2] != results[1][2]:
            failures.append(f"{repo.name}: output differs between runs")
        elif findings == 0:
            print(f"{'':12} note: no findings, so the determinism check is vacuous here")
        if text.strip():
            print(f"{'':12} stderr: {text.strip()[:200]}")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"all {len(repos)} repositories: no crash, no hang, identical output on repeat")
    return 0


if __name__ == "__main__":
    sys.exit(main())

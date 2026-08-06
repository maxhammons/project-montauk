#!/usr/bin/env python3
"""Re-evaluate a chosen set of mutation sites.

The full sweep answers "what is the score"; this answers "did the test I just
wrote kill anything", which is the question worth asking after every commit and
is far too slow to answer with a full sweep.

    python3 recheck.py survivors.json 6      # indices from a sweep's jsonl
    python3 recheck.py 47,67,72 4            # explicit indices
"""

import json
import os
import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent))
import subprocess
import sys
import threading
from pathlib import Path

from mutation_sweep import (
    OUT,
    REPO,
    SHARD_PREFIX,
    WORKTREES,
    allowed_survivors,
    ensure_toolchain,
    evaluate,
    mutations,
    stray_processes,
    warm,
)


def wanted(argument):
    path = Path(argument)
    if path.exists():
        records = [json.loads(line) for line in path.read_text().splitlines()]
        return sorted(r["index"] for r in records if r["verdict"] == "SURVIVED")
    return sorted(int(piece) for piece in argument.split(","))


def main():
    indices = wanted(sys.argv[1])
    shards = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    dirty = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("src/ is dirty; commit first")
        return 2
    if stray_processes():
        print("test binaries from an earlier run are still alive; kill them first")
        return 2
    provisioning = ensure_toolchain()
    if provisioning:
        print(provisioning)
        return 2

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout.strip()
    trees = []
    for shard in range(shards):
        tree = WORKTREES / f"{SHARD_PREFIX}recheck{shard}"
        if not tree.exists():
            subprocess.run(["git", "worktree", "add", "--detach", str(tree), head],
                           cwd=REPO, check=True, capture_output=True)
        else:
            subprocess.run(["git", "checkout", "-q", "--detach", head], cwd=tree,
                           check=True, capture_output=True)
        trees.append(tree)

    all_mutations = mutations()
    work = [(index, all_mutations[index]) for index in indices]
    print(f"re-checking {len(work)} sites over {shards} worktrees", flush=True)

    lock = threading.Lock()
    results = []

    def worker(tree, items):
        # The warm-up build, for the same reason the sweep does it: a fresh
        # worktree's first compile happens inside the mutant's timeout and a
        # cold build would be scored CAUGHT-HANG.
        failure = warm(tree)
        for index, (relative, offset, line_number, find, replace) in items:
            try:
                verdict = f"ERROR(warm-up: {failure})" if failure else \
                    evaluate(tree, relative, offset, find, replace)
            except Exception as error:
                verdict = f"ERROR({type(error).__name__})"
            with lock:
                print(f"{index:4} {verdict:19} {relative}:{line_number} "
                      f"{find!r} -> {replace!r}", flush=True)
                results.append({"index": index, "verdict": verdict, "file": relative,
                                "line": line_number, "find": find, "replace": replace})

    threads = [threading.Thread(target=worker, args=(trees[shard], work[shard::shards]))
               for shard in range(shards)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    killed = [r for r in results if r["verdict"].startswith("CAUGHT")]
    still = sorted((r for r in results if r["verdict"] == "SURVIVED"),
                   key=lambda r: (r["file"], r["line"]))
    errors = [r for r in results if r["verdict"].startswith("ERROR")]
    allowed = allowed_survivors()
    unexplained = [r for r in still
                   if (r["file"], r["line"], r["find"], r["replace"]) not in allowed]
    print(f"\nnewly killed {len(killed)}/{len(results)}; {len(still)} still surviving")
    for record in still:
        key = (record["file"], record["line"], record["find"], record["replace"])
        marker = "documented equivalent" if key in allowed else "NOT IN THE ALLOWLIST"
        print(f"  SURVIVOR {record['file']}:{record['line']} "
              f"{record['find']!r} -> {record['replace']!r} — {marker}")
    (OUT / "recheck-result.jsonl").write_text(
        "\n".join(json.dumps(r) for r in sorted(results, key=lambda r: r["index"])) + "\n")
    # The same verdict rule as the sweep: an undocumented survivor or a harness
    # error is a failure, not a line in a report.
    if errors:
        for record in errors:
            print(f"FAIL: {record['verdict']} at {record['file']}:{record['line']}")
        return 1
    if len(results) != len(work):
        print(f"FAIL: {len(work) - len(results)} of {len(work)} sites have no record")
        return 1
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Staged, resumable batch sweep over the entire strategy grid space.

This is the "test (nearly) every combination" driver. It does NOT reimplement
scoring or validation — it drives the existing `grid_search.py` once per concept
as an isolated subprocess, so:

  * **Exhaustive** — every concept's full canonical param grid is charter-
    prefiltered (Stage 1) and, for survivors, fully validated (Stage 2).
  * **Resumable** — progress is checkpointed to a manifest after each concept.
    Re-running skips completed concepts. Ctrl-C between concepts loses nothing;
    Ctrl-C during a concept costs only that one concept (re-run picks it up).
  * **Crash-isolated** — each concept runs in its own subprocess, so a single
    bad concept (e.g. a corrupt cache file) can't abort the whole batch.

Note on scale: single-strategy param grids total ~353k valid combos — feasible.
The *committee/ensemble* space (members × weights × thresholds) is super-
exponential and is NOT swept here; that belongs to the GA (`evolve.py`) and the
`chimera_weight_grid.py` diagnostic. See the response that introduced this file.

Trust boundary: always runs `grid_search` with `--no-admit`, so the authority
leaderboard is never mutated by the sweep. Promotion stays a human decision.

Usage
-----
    # Stage 1 — exhaustive charter prefilter over every concept (fast):
    python scripts/search/batch_sweep.py --stage prefilter

    # Stage 2 — full validation of survivors (heavy; resumable):
    python scripts/search/batch_sweep.py --stage full --top-n 20

    # Skip the two monster grids on a first pass:
    python scripts/search/batch_sweep.py --stage prefilter --max-combos 50000

    # Merge all concept outputs into one ranked survivor table:
    python scripts/search/batch_sweep.py --aggregate
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from search.grid_search import GRIDS, _grid_combos, _is_valid_combo  # noqa: E402

GRID_SEARCH = os.path.join(HERE, "grid_search.py")
DEFAULT_DIR = os.path.join(PROJECT_ROOT, "runs", "batch_sweep")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_combo_count(concept: str) -> int:
    grid = GRIDS.get(concept)
    if not grid:
        return 0
    try:
        combos = list(_grid_combos(grid))
    except Exception:
        return 0
    return sum(1 for c in combos if _is_valid_combo(concept, c))


def _manifest_path(out_dir: str) -> str:
    return os.path.join(out_dir, "_manifest.json")


def _load_manifest(out_dir: str) -> dict:
    p = _manifest_path(out_dir)
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"schema_version": 1, "stage": None, "started_utc": None, "concepts": {}}


def _save_manifest(out_dir: str, manifest: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    tmp = _manifest_path(out_dir) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, _manifest_path(out_dir))  # atomic — never leaves a half file


def _concept_out(out_dir: str, concept: str) -> str:
    return os.path.join(out_dir, "concepts", f"{concept}.json")


def _ordered_concepts(selected: list[str] | None, max_combos: int | None) -> list[tuple[str, int]]:
    concepts = selected if selected else list(GRIDS.keys())
    sized = [(c, _valid_combo_count(c)) for c in concepts if c in GRIDS]
    if max_combos is not None:
        sized = [(c, n) for c, n in sized if n <= max_combos]
    sized.sort(key=lambda cn: cn[1])  # smallest grids first — quick wins, monsters last
    return sized


def run_sweep(
    *,
    stage: str,
    out_dir: str,
    concepts: list[str] | None,
    top_n: int,
    max_combos: int | None,
    restart: bool,
    per_concept_timeout: int,
) -> int:
    os.makedirs(os.path.join(out_dir, "concepts"), exist_ok=True)
    manifest = _load_manifest(out_dir)
    if restart:
        manifest = {"schema_version": 1, "stage": stage, "started_utc": _utc(), "concepts": {}}
    manifest["stage"] = stage
    manifest.setdefault("started_utc", _utc())

    queue = _ordered_concepts(concepts, max_combos)
    total_combos = sum(n for _, n in queue)
    print(f"[batch] stage={stage} concepts={len(queue)} total_valid_combos={total_combos:,}")
    print(f"[batch] out_dir={out_dir}")

    done_already = sum(
        1 for c, _ in queue
        if manifest["concepts"].get(c, {}).get("status") == "done" and not restart
    )
    if done_already:
        print(f"[batch] resuming — {done_already}/{len(queue)} concepts already done")

    extra = ["--no-validate"] if stage == "prefilter" else ["--no-admit", "--top-n", str(top_n)]

    for idx, (concept, ncombos) in enumerate(queue, start=1):
        rec = manifest["concepts"].get(concept, {})
        if rec.get("status") == "done" and not restart:
            continue
        out_path = _concept_out(out_dir, concept)
        cmd = [
            sys.executable, GRID_SEARCH,
            "--concepts", concept,
            "--output", out_path,
            "--progress-every", "0",
            *extra,
        ]
        t0 = time.time()
        print(f"[batch] ({idx}/{len(queue)}) {concept}  {ncombos:,} combos … ", end="", flush=True)
        status, returncode, summary = "done", 0, {}
        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
                timeout=per_concept_timeout,
            )
            returncode = proc.returncode
            if returncode != 0:
                status = "error"
            if os.path.exists(out_path):
                try:
                    with open(out_path) as f:
                        summary = json.load(f)
                except (json.JSONDecodeError, OSError):
                    summary = {}
        except subprocess.TimeoutExpired:
            status, returncode = "timeout", -1
        except KeyboardInterrupt:
            print("interrupted — progress saved, re-run to resume.")
            _save_manifest(out_dir, manifest)
            return 130
        dt = time.time() - t0
        manifest["concepts"][concept] = {
            "status": status,
            "returncode": returncode,
            "combos": ncombos,
            "charter_pass": summary.get("charter_pass"),
            "survivors": len(summary.get("raw_rankings", []) or []),
            "seconds": round(dt, 1),
            "updated_utc": _utc(),
            "tail": (proc.stderr[-300:] if status == "error" and "proc" in dir() else None),
        }
        _save_manifest(out_dir, manifest)
        cp = summary.get("charter_pass")
        flag = "" if status == "done" else f"  [{status}]"
        print(f"{dt:5.1f}s  charter_pass={cp}{flag}")

    n_done = sum(1 for r in manifest["concepts"].values() if r.get("status") == "done")
    n_err = sum(1 for r in manifest["concepts"].values() if r.get("status") in ("error", "timeout"))
    print(f"[batch] complete: {n_done} done, {n_err} error/timeout. Run --aggregate for the survivor table.")
    return 0


def aggregate(out_dir: str, top_n: int) -> int:
    concept_dir = os.path.join(out_dir, "concepts")
    if not os.path.isdir(concept_dir):
        print(f"[batch] no concept outputs under {concept_dir}; run a sweep first.")
        return 1
    survivors = []
    for fn in sorted(os.listdir(concept_dir)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(concept_dir, fn)) as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for r in d.get("raw_rankings", []) or []:
            m = r.get("metrics", {}) or {}
            full = m.get("share_multiple")
            real = m.get("real_share_multiple")
            modern = m.get("modern_share_multiple")
            survivors.append({
                "strategy": r.get("strategy"),
                "fitness": r.get("fitness"),
                "full": full,
                "real": real,
                "modern": modern,
                "trades": m.get("trades"),
                "max_dd": m.get("max_dd"),
                "marker": r.get("marker_alignment_score"),
                "all_era_beat": bool(
                    full is not None and real is not None and modern is not None
                    and full >= 1.0 and real >= 1.0 and modern >= 1.0
                ),
                "params": r.get("params"),
            })
    survivors.sort(key=lambda s: (s["all_era_beat"], s.get("fitness") or 0.0), reverse=True)
    out = {
        "generated_utc": _utc(),
        "survivor_count": len(survivors),
        "all_era_beat_count": sum(1 for s in survivors if s["all_era_beat"]),
        "survivors": survivors,
    }
    out_path = os.path.join(out_dir, "survivors.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[batch] survivors={out['survivor_count']}  all-era-beat={out['all_era_beat_count']}")
    print(f"\n  {'strategy':28} {'fit':>5} {'full':>7} {'real':>5} {'modern':>6} {'trd':>4} {'maxDD':>6} {'allEra'}")
    for s in survivors[:top_n]:
        def fmt(v, w, p=2):
            return f"{v:>{w}.{p}f}" if isinstance(v, (int, float)) else f"{'-':>{w}}"
        print(
            f"  {str(s['strategy'])[:28]:28} {fmt(s['fitness'],5,3)} {fmt(s['full'],7)} "
            f"{fmt(s['real'],5)} {fmt(s['modern'],6)} {fmt(s['trades'],4,0)} "
            f"{fmt(s['max_dd'],6,1)} {'YES' if s['all_era_beat'] else ''}"
        )
    print(f"\n[batch] wrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stage", choices=["prefilter", "full"], default="prefilter",
                   help="prefilter = exhaustive charter filter (fast); full = validate survivors (heavy).")
    p.add_argument("--concepts", default=None, help="Comma-separated concept subset (default: all grids).")
    p.add_argument("--top-n", type=int, default=20, help="Validate top-N survivors per concept in --stage full.")
    p.add_argument("--max-combos", type=int, default=None,
                   help="Skip concepts whose valid-combo count exceeds this (e.g. 50000 to skip the monster grids).")
    p.add_argument("--out-dir", default=DEFAULT_DIR, help="Output/checkpoint directory.")
    p.add_argument("--restart", action="store_true", help="Ignore existing checkpoint and start over.")
    p.add_argument("--per-concept-timeout", type=int, default=7200, help="Seconds before a concept is marked timeout.")
    p.add_argument("--aggregate", action="store_true", help="Merge concept outputs into a ranked survivor table and exit.")
    args = p.parse_args(argv)

    if args.aggregate:
        return aggregate(args.out_dir, args.top_n)

    concepts = args.concepts.split(",") if args.concepts else None
    return run_sweep(
        stage=args.stage,
        out_dir=args.out_dir,
        concepts=concepts,
        top_n=args.top_n,
        max_combos=args.max_combos,
        restart=args.restart,
        per_concept_timeout=args.per_concept_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())

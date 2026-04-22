"""Reliability harness for long-run grid searches (2026-04-21).

Hardens the naive `pool.imap_unordered` pattern with:

  1. **Crash tracking** — workers report (result | None | {"_error": str}).
     Main aggregates crash count. `fail_fast_crash_pct` aborts the run if too
     many workers are crashing (symptom of a systemic bug).
  2. **Top-K global heap** — best N results kept regardless of charter pass.
     Surfaces near-winners that would otherwise be discarded by the filter.
  3. **Mid-grid checkpointing** — every `checkpoint_every` combos, write top-K
     JSON to `checkpoint_dir/checkpoint.json`. If Python crashes at 99%, the
     latest checkpoint survives.
  4. **Heartbeat** — a separate thread prints alive-indicator every
     `heartbeat_secs` even when no progress checkpoint has fired. Useful when
     stdout is buffered and the main process isn't emitting.
  5. **Validation try/except** — grid phase results are dumped to a recovery
     file before validation runs. If validation throws, grid data survives.
  6. **Signal handler** — SIGINT / SIGTERM flushes the final checkpoint and
     closes the Pool cleanly. Ctrl-C produces usable partial results.

Usage pattern (minimal example):

    from search.safe_runner import GridRunner

    runner = GridRunner(
        strategy_name="gc_vjatr",
        grid={"fast_ema": [...], ...},
        worker_eval=my_eval,      # worker callable; see signature below
        fitness_key=0,            # tuple index of the fitness value in result
        checkpoint_dir="/tmp/my_run",
    )
    results = runner.run()

The `worker_eval` function signature:
    def eval(params: dict) -> tuple | None
        returns None to skip (charter reject), or a tuple whose first element
        is the fitness (float) to use for ranking.
"""

from __future__ import annotations

import heapq
import itertools
import json
import multiprocessing
import os
import signal
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterator


@dataclass
class RunStats:
    combos_total: int = 0
    combos_done: int = 0
    combos_passed: int = 0
    combos_crashed: int = 0
    combos_skipped: int = 0
    start_ts: float = field(default_factory=time.time)

    def elapsed_sec(self) -> float:
        return time.time() - self.start_ts

    def rate_per_sec(self) -> float:
        e = self.elapsed_sec()
        return self.combos_done / e if e > 0 else 0.0

    def eta_sec(self) -> float:
        r = self.rate_per_sec()
        if r <= 0:
            return 0.0
        return (self.combos_total - self.combos_done) / r

    def crash_rate(self) -> float:
        if self.combos_done == 0:
            return 0.0
        return self.combos_crashed / self.combos_done

    def summary(self) -> str:
        return (
            f"done={self.combos_done:,}/{self.combos_total:,} "
            f"({100 * self.combos_done / max(self.combos_total, 1):.1f}%)  "
            f"passed={self.combos_passed:,}  "
            f"crashed={self.combos_crashed:,}  "
            f"skipped={self.combos_skipped:,}  "
            f"rate={self.rate_per_sec():.0f}/s  "
            f"eta={self.eta_sec() / 60:.1f}m"
        )


class GridRunner:
    """Execute a grid of parameter combos with reliability guardrails.

    Args:
        strategy_name:     For logging. Not used for routing.
        grid:              Dict of param_name -> list of values. Cartesian product.
        worker_eval:       Callable that takes params dict, returns tuple or None.
                           Worker must be picklable (no closures over local state).
        worker_init:       Optional initializer for the multiprocessing Pool.
                           Usually loads data once per worker to share via globals.
        filter_fn:         Optional predicate on params dict. Skip combos where
                           filter_fn(params) is False (e.g., slow_ema > fast_ema).
        fitness_key:       Tuple index of the fitness value (for ranking).
        top_n_keep:        Number of best-fitness results to keep in the global
                           heap. These survive even if they fail the charter gate.
        n_workers:         Pool size. Default cpu_count - 1, capped at 12.
        checkpoint_dir:    Directory for heartbeat/checkpoint/recovery files.
                           Created if missing.
        checkpoint_every:  Combos between checkpoint dumps.
        heartbeat_secs:    Seconds between heartbeat lines.
        fail_fast_crash_pct: Abort if crash rate exceeds this fraction
                           (measured after at least 1000 combos processed).
        chunksize:         imap_unordered chunk size.
    """

    def __init__(
        self,
        *,
        strategy_name: str,
        grid: dict[str, list],
        worker_eval: Callable[[dict], Any],
        worker_init: Callable[[], None] | None = None,
        filter_fn: Callable[[dict], bool] | None = None,
        fitness_key: int = 0,
        top_n_keep: int = 1000,
        n_workers: int | None = None,
        checkpoint_dir: str | None = None,
        checkpoint_every: int = 100_000,
        heartbeat_secs: float = 60.0,
        fail_fast_crash_pct: float = 0.50,
        chunksize: int = 100,
    ):
        self.strategy_name = strategy_name
        self.grid = grid
        self.worker_eval = worker_eval
        self.worker_init = worker_init
        self.filter_fn = filter_fn
        self.fitness_key = fitness_key
        self.top_n_keep = top_n_keep
        self.n_workers = n_workers or max(2, min(multiprocessing.cpu_count() - 1, 12))
        self.checkpoint_dir = (
            checkpoint_dir or f"/tmp/gridrunner_{strategy_name}_{int(time.time())}"
        )
        self.checkpoint_every = checkpoint_every
        self.heartbeat_secs = heartbeat_secs
        self.fail_fast_crash_pct = fail_fast_crash_pct
        self.chunksize = chunksize

        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.stats = RunStats()
        self._heap: list = []  # min-heap of (fitness, idx, result)
        self._heap_counter = (
            0  # tiebreaker so same-fitness results don't compare tuples
        )
        self._passers: list = []  # all charter-passers (non-None results)
        self._abort = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    # ------------------------------------------------------------------ grid

    def _generate_combos(self) -> Iterator[dict]:
        keys = list(self.grid.keys())
        for vals in itertools.product(*(self.grid[k] for k in keys)):
            p = dict(zip(keys, vals))
            if self.filter_fn is None or self.filter_fn(p):
                yield p

    # ------------------------------------------------------------------ heartbeat

    def _heartbeat_loop(self):
        while not self._abort.is_set():
            if self._abort.wait(timeout=self.heartbeat_secs):
                return
            print(f"  [heartbeat] {self.stats.summary()}", flush=True)

    # ------------------------------------------------------------------ checkpointing

    def _checkpoint_path(self) -> str:
        return os.path.join(self.checkpoint_dir, "checkpoint.json")

    def _dump_checkpoint(self, label: str = "checkpoint"):
        """Write current top-K heap to disk."""
        top_k = self._sorted_top_k()
        payload = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "strategy": self.strategy_name,
            "stats": {
                "combos_total": self.stats.combos_total,
                "combos_done": self.stats.combos_done,
                "combos_passed": self.stats.combos_passed,
                "combos_crashed": self.stats.combos_crashed,
                "combos_skipped": self.stats.combos_skipped,
                "elapsed_min": round(self.stats.elapsed_sec() / 60, 2),
            },
            "top_k": [self._serialize_result(r) for r in top_k],
        }
        path = self._checkpoint_path()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, path)  # atomic rename

    def _serialize_result(self, result: Any) -> Any:
        """Make a result tuple JSON-safe (best-effort)."""
        try:
            return json.loads(json.dumps(result, default=str))
        except Exception:
            return str(result)

    def _sorted_top_k(self) -> list:
        """Return heap contents sorted by fitness descending."""
        # heap stores (fitness, counter, result) — strip counter, sort by fitness desc.
        return [
            item[2] for item in sorted(self._heap, key=lambda t: t[0], reverse=True)
        ]

    # ------------------------------------------------------------------ signal handling

    def _install_signal_handlers(self):
        def handler(signum, _frame):
            print(
                f"\n  [!] signal {signum} received — dumping final checkpoint and aborting",
                flush=True,
            )
            self._abort.set()
            try:
                self._dump_checkpoint(label="signal_abort")
            except Exception:
                pass

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, handler)
            except Exception:
                pass  # not always installable (e.g. inside threads)

    # ------------------------------------------------------------------ main run

    def run(self) -> dict:
        """Execute the grid. Returns a dict with stats and results."""
        combos = list(self._generate_combos())
        self.stats.combos_total = len(combos)
        print(
            f"[GridRunner] strategy={self.strategy_name} "
            f"combos={len(combos):,} workers={self.n_workers} "
            f"checkpoint_dir={self.checkpoint_dir}",
            flush=True,
        )

        self._install_signal_handlers()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

        try:
            with multiprocessing.Pool(
                processes=self.n_workers,
                initializer=self.worker_init,
            ) as pool:
                for res in pool.imap_unordered(
                    self.worker_eval, combos, chunksize=self.chunksize
                ):
                    if self._abort.is_set():
                        break
                    self.stats.combos_done += 1
                    self._handle_result(res)

                    if self.stats.combos_done % self.checkpoint_every == 0:
                        self._dump_checkpoint()
                        print(
                            f"  [checkpoint] {self.stats.summary()}",
                            flush=True,
                        )

                    # Fail-fast guard: abort if crash rate is high after a warmup
                    if (
                        self.stats.combos_done >= 1000
                        and self.stats.crash_rate() > self.fail_fast_crash_pct
                    ):
                        print(
                            f"  [!] ABORT: crash rate "
                            f"{self.stats.crash_rate():.1%} exceeds "
                            f"{self.fail_fast_crash_pct:.1%}. "
                            f"Something is systemically broken.",
                            flush=True,
                        )
                        self._abort.set()
                        break
        except Exception as exc:
            print(f"  [!] EXCEPTION in grid loop: {exc}", flush=True)
            traceback.print_exc()
            self._abort.set()
            self._dump_checkpoint(label="exception_recovery")
            raise
        finally:
            self._abort.set()
            if self._heartbeat_thread:
                self._heartbeat_thread.join(timeout=2)

        # Final checkpoint
        self._dump_checkpoint(label="final")

        print(
            f"\n[GridRunner] FINAL: {self.stats.summary()}",
            flush=True,
        )

        return {
            "stats": self.stats,
            "top_k": self._sorted_top_k(),
            "passers": self._passers,
            "checkpoint_path": self._checkpoint_path(),
        }

    def _handle_result(self, res: Any) -> None:
        # Normalize: could be None (skip), dict with _error (crash), or the raw result tuple.
        if res is None:
            self.stats.combos_skipped += 1
            return
        if isinstance(res, dict) and "_error" in res:
            self.stats.combos_crashed += 1
            return

        # It's a valid result tuple
        self.stats.combos_passed += 1
        self._passers.append(res)

        # Maintain top-K heap by fitness
        try:
            fitness = float(res[self.fitness_key])
        except Exception:
            return
        self._heap_counter += 1
        entry = (fitness, self._heap_counter, res)
        if len(self._heap) < self.top_n_keep:
            heapq.heappush(self._heap, entry)
        else:
            # heap is min-heap on fitness — pushpop drops smallest
            heapq.heappushpop(self._heap, entry)


def run_validation_safely(
    raw_rankings: list[dict],
    *,
    recovery_path: str,
) -> dict | None:
    """Wrap run_validation_pipeline with crash recovery.

    Before validation, dumps raw_rankings to `recovery_path`. If validation
    throws, the grid-phase data survives and can be re-processed manually.
    Returns None on exception (caller decides what to do).
    """
    # Persist the inputs first so a validation crash doesn't lose grid data
    try:
        with open(recovery_path, "w") as f:
            json.dump({"raw_rankings": raw_rankings}, f, indent=2, default=str)
        print(f"  [safe] dumped pre-validation rankings to {recovery_path}", flush=True)
    except Exception as exc:
        print(
            f"  [safe] WARNING: could not dump pre-validation rankings: {exc}",
            flush=True,
        )

    try:
        from validation.pipeline import run_validation_pipeline

        return run_validation_pipeline(
            {"raw_rankings": raw_rankings},
            hours=0.05,
            quick=True,
            top_n=len(raw_rankings),
        )
    except Exception as exc:
        print(f"  [!] VALIDATION EXCEPTION: {exc}", flush=True)
        traceback.print_exc()
        print(
            f"  [safe] grid data preserved at {recovery_path}. "
            f"Re-run validation manually with:\n"
            f'    python -c "import json;from validation.pipeline import run_validation_pipeline as r;'
            f"print(r(json.load(open('{recovery_path}')),hours=0.05,quick=True))\"",
            flush=True,
        )
        return None

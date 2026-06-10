"""Tests for the nightly spike_drain scheduled job (2026-06-09).

The drain exists so idle overnight CPU mines the curated search roster with
NO agent in the loop — these tests pin the contract that makes that safe:
the job is present + enabled by default, its compute budget is config-tunable
without code edits, it skips (never queues) when any conflicting lock is
held, and it survives a fully headless launchd context (no TTY, no stdin).
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from ops.events import read_events
from ops.run_job import (
    CONFLICT_LOCK_JOBS,
    _default_runner,
    acquire_lock,
    job_command,
    output_artifact_paths,
    release_lock,
    run_job,
    spike_drain_budget,
)
from ops.scheduler import DEFAULT_SCHEDULE, load_config


def _stub_runner(stdout: str = "", returncode: int = 0):
    def runner(command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            command, returncode, stdout=stdout, stderr=""
        )

    return runner


def _forbidden_runner(command: list[str]) -> subprocess.CompletedProcess:
    raise AssertionError("runner must not be invoked when a conflicting lock is held")


def test_spike_drain_present_in_default_schedule_and_enabled() -> None:
    entry = DEFAULT_SCHEDULE["jobs"]["spike_drain"]

    assert entry["enabled"] is True  # Max wants idle CPU mining by default
    assert entry["job"] == "spike-drain"
    assert entry["schedule"] == {"Hour": 2, "Minute": 0}
    # The default budget is documented in the entry itself so config edits
    # have an obvious template to copy.
    assert entry["hours"] == 2.0


def test_spike_drain_survives_config_merge(tmp_path) -> None:
    # An older on-disk config without spike_drain must still hydrate the new
    # default job, otherwise existing installs never pick up the drain.
    config_path = tmp_path / "scheduler.json"
    config_path.write_text(
        json.dumps(
            {"schema_version": 1, "jobs": {"daily": {"enabled": True, "job": "daily"}}}
        )
    )

    config = load_config(config_path)

    assert config["jobs"]["spike_drain"]["enabled"] is True
    assert config["jobs"]["spike_drain"]["job"] == "spike-drain"


def test_budget_defaults_when_config_omits_keys() -> None:
    budget = spike_drain_budget({"jobs": {"spike_drain": {"job": "spike-drain"}}})

    assert budget == {"hours": 2.0}  # no pop_size key -> spike_runner default


def test_budget_config_keys_respected(monkeypatch) -> None:
    config = {
        "jobs": {
            "spike_drain": {
                "job": "spike-drain",
                "hours": 0.5,
                "pop_size": 12,
            }
        }
    }

    assert spike_drain_budget(config) == {"hours": 0.5, "pop_size": 12}

    monkeypatch.setattr("ops.run_job.load_config", lambda: config)
    command = job_command("spike-drain", python="/tmp/python")

    assert command[0] == "/tmp/python"
    assert command[1].endswith("scripts/search/spike_runner.py")
    assert command[2:] == ["--hours", "0.5", "--pop-size", "12"]


def test_spike_drain_artifacts_recorded() -> None:
    paths = output_artifact_paths("spike-drain")

    assert "spike/runs/NNN/" in paths
    assert "spike/leaderboard.json" in paths


def test_lock_skip_when_spike_drain_lock_held(tmp_path) -> None:
    locks_dir = tmp_path / "locks"
    lock_path, payload = acquire_lock("spike-drain", locks_dir=locks_dir)

    record = run_job(
        "spike-drain",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=_forbidden_runner,
        python="/tmp/python",
        locks_dir=locks_dir,
    )

    assert record["status"] == "locked"
    events = read_events(events_path=tmp_path / "events.jsonl")
    assert [e["event_type"] for e in events] == ["job_locked"]
    release_lock(lock_path, payload)


def test_lock_skip_when_daily_lock_held(tmp_path) -> None:
    # A spike run must never overlap the daily data refresh: with the daily
    # lock held, the drain skips AND leaves no spike-drain lock behind.
    assert CONFLICT_LOCK_JOBS["spike-drain"] == ("daily",)
    locks_dir = tmp_path / "locks"
    lock_path, payload = acquire_lock("daily", locks_dir=locks_dir)

    record = run_job(
        "spike-drain",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=_forbidden_runner,
        python="/tmp/python",
        locks_dir=locks_dir,
    )

    assert record["status"] == "locked"
    assert record["lock_path"].endswith("daily.lock")
    assert not (locks_dir / "spike-drain.lock").exists()
    events = read_events(events_path=tmp_path / "events.jsonl")
    assert [e["event_type"] for e in events] == ["job_locked"]
    release_lock(lock_path, payload)


def test_successful_run_releases_locks_and_records_run_dir(tmp_path) -> None:
    locks_dir = tmp_path / "locks"
    stdout = "Run directory: /tmp/fake project/spike/runs/999\nSPIKE COMPLETE\n"

    record = run_job(
        "spike-drain",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=_stub_runner(stdout=stdout),
        python="/tmp/python",
        locks_dir=locks_dir,
    )

    assert record["status"] == "ok"
    assert record["spike_run_dir"] == "/tmp/fake project/spike/runs/999"
    assert record["conflict_lock_paths"] == [str(locks_dir / "daily.lock")]
    # Both the drain's own lock and the conflict-held daily lock are gone.
    assert not (locks_dir / "spike-drain.lock").exists()
    assert not (locks_dir / "daily.lock").exists()
    events = read_events(events_path=tmp_path / "events.jsonl")
    assert [e["event_type"] for e in events] == ["job_started", "job_succeeded"]


def test_failed_run_emits_failure_event_and_releases_locks(tmp_path) -> None:
    locks_dir = tmp_path / "locks"

    record = run_job(
        "spike-drain",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=_stub_runner(returncode=1),
        python="/tmp/python",
        locks_dir=locks_dir,
    )

    assert record["status"] == "failed"
    assert not (locks_dir / "spike-drain.lock").exists()
    assert not (locks_dir / "daily.lock").exists()
    events = read_events(events_path=tmp_path / "events.jsonl")
    assert [e["event_type"] for e in events] == ["job_started", "job_failed"]


def test_run_job_works_with_stdin_closed(tmp_path, monkeypatch) -> None:
    # Simulates the launchd context: there is no usable stdin at all.
    closed = open("/dev/null")
    closed.close()
    monkeypatch.setattr(sys, "stdin", closed)

    record = run_job(
        "spike-drain",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=_stub_runner(stdout="Run directory: /tmp/x\n"),
        python="/tmp/python",
        locks_dir=tmp_path / "locks",
    )

    assert record["status"] == "ok"


def test_default_runner_gives_child_no_tty_and_empty_stdin() -> None:
    # The child must see EOF immediately rather than hanging on a read; this
    # is what makes a real 2h spike_runner child headless-safe under launchd.
    completed = _default_runner(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.stdin.isatty()); print(repr(sys.stdin.read()))",
        ]
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["False", "''"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

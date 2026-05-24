from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ops.daily import (
    comparable_signal,
    detect_signal_change,
    load_active_champion,
    simulate_signal_state,
    write_signal_snapshot,
)
from ops.doctor import build_doctor_report
from ops.events import append_event, read_events
from ops.governance import build_governance, evaluate_governance
from ops.install_launch_agent import build_plist, job_keys, launch_agent_label, launchctl_command, status_for_job
from ops.live_holdout import build_live_holdout
from ops.notifications import (
    build_outbox,
    event_id,
    is_notifiable,
    mark_sent,
    scan_notifications,
    send_pending_notifications,
    set_notification_preference,
)
from ops.research_queue import generate_proposals, update_idea_status, write_proposals
from ops.research_runner import build_research_plan, create_research_run
from ops.run_job import JobLockedError, acquire_lock, output_artifact_paths, release_lock, run_job
from ops.scheduler import init_config, list_jobs, load_config, next_run_at, scheduler_status, set_enabled
from ops.strategy_review import build_strategy_review


def _snapshot(date: str = "2026-05-08", risk_state: str = "risk_on") -> dict:
    return {
        "snapshot_schema_version": 1,
        "generated_utc": "2026-05-09T01:00:00Z",
        "data_end_date": date,
        "active_champion": {
            "strategy": "example",
            "params_hash": "abc123",
        },
        "risk_state": risk_state,
        "risk_on": risk_state == "risk_on",
        "entry_signal": False,
        "exit_signal": False,
        "buy_event": False,
        "sell_event": False,
        "close": 123.45,
    }


def test_simulate_signal_state_does_not_force_end_of_data_exit() -> None:
    risk_on, buy_events, sell_events = simulate_signal_state(
        [False, True, False, False],
        [False, False, False, False],
        cooldown_bars=0,
    )

    assert risk_on == [False, True, True, True]
    assert buy_events == [False, True, False, False]
    assert sell_events == [False, False, False, False]


def test_load_active_champion_uses_highest_confidence_gold(tmp_path) -> None:
    leaderboard_path = tmp_path / "leaderboard.json"
    leaderboard_path.write_text(
        json.dumps(
            [
                {
                    "strategy": "first",
                    "gold_status": True,
                    "validation": {"gold_status": True, "composite_confidence": 0.5},
                },
                {
                    "strategy": "best",
                    "gold_status": True,
                    "validation": {"gold_status": True, "composite_confidence": 0.8},
                },
            ]
        )
    )

    champion = load_active_champion(leaderboard_path)

    assert champion["strategy"] == "best"


def test_detect_signal_change_reports_changed_fields() -> None:
    previous = _snapshot(risk_state="risk_on")
    current = _snapshot(date="2026-05-09", risk_state="risk_off")
    current["sell_event"] = True

    change = detect_signal_change(current, previous)

    assert change["changed"] is True
    assert change["previous_risk_state"] == "risk_on"
    assert change["changed_fields"] == ["risk_state", "sell_event"]


def test_write_signal_snapshot_is_immutable_without_overwrite(tmp_path) -> None:
    first = _snapshot()
    path, status, stored = write_signal_snapshot(first, signals_dir=tmp_path)
    assert status == "written"
    assert path.exists()
    assert comparable_signal(stored) == comparable_signal(first)

    same = dict(first)
    same["generated_utc"] = "2026-05-09T02:00:00Z"
    path, status, stored = write_signal_snapshot(same, signals_dir=tmp_path)
    assert status == "unchanged"
    assert stored["generated_utc"] == "2026-05-09T01:00:00Z"

    changed = dict(first)
    changed["risk_state"] = "risk_off"
    changed["risk_on"] = False
    path, status, stored = write_signal_snapshot(changed, signals_dir=tmp_path)
    assert status == "existing_differs"
    assert stored["risk_state"] == "risk_on"

    path, status, stored = write_signal_snapshot(
        changed,
        signals_dir=tmp_path,
        allow_overwrite=True,
    )
    assert status == "overwritten"
    assert json.loads(path.read_text())["risk_state"] == "risk_off"


def test_event_log_roundtrip(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    append_event(
        "signal_changed",
        "Signal changed to risk_off.",
        severity="notice",
        payload={"risk_state": "risk_off"},
        events_path=events_path,
        timestamp_utc="2026-05-09T01:00:00Z",
    )

    events = read_events(events_path=events_path)

    assert len(events) == 1
    assert events[0]["event_type"] == "signal_changed"
    assert events[0]["severity"] == "notice"
    assert events[0]["payload"] == {"risk_state": "risk_off"}


def test_scheduler_config_can_be_initialized_and_toggled(tmp_path) -> None:
    config_path = tmp_path / "scheduler.json"

    config = init_config(config_path)
    jobs = {item["key"]: item for item in list_jobs(config)}

    assert jobs["daily"]["enabled"] is True
    assert jobs["daily"]["job"] == "daily"

    updated = set_enabled("daily", False, path=config_path)
    assert updated["jobs"]["daily"]["enabled"] is False


def test_scheduler_status_includes_next_run_and_last_record(tmp_path) -> None:
    config = {
        "jobs": {
            "daily": {
                "enabled": True,
                "job": "daily",
                "label": "Daily operations",
                "schedule": {"Hour": 16, "Minute": 30},
            }
        }
    }
    record_dir = tmp_path / "jobs"
    record_dir.mkdir()
    (record_dir / "20260512T041151Z-daily.json").write_text(
        json.dumps(
            {
                "job": "daily",
                "status": "ok",
                "started_utc": "2026-05-12T04:11:51Z",
                "finished_utc": "2026-05-12T04:12:01Z",
                "returncode": 0,
            }
        )
    )

    now = datetime(2026, 5, 12, 15, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    status = scheduler_status(config, record_dir=record_dir, now=now)

    assert status["jobs"][0]["next_run_local"] == "2026-05-12T16:30-07:00"
    assert status["jobs"][0]["last_run"]["status"] == "ok"


def test_scheduler_load_merges_new_default_jobs(tmp_path) -> None:
    config_path = tmp_path / "scheduler.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jobs": {
                    "daily": {
                        "enabled": False,
                        "job": "daily",
                        "schedule": {"Hour": 15, "Minute": 0},
                    }
                },
            }
        )
    )

    config = load_config(config_path)

    assert config["jobs"]["daily"]["enabled"] is False
    assert config["jobs"]["daily"]["schedule"] == {"Hour": 15, "Minute": 0}
    assert "daily-governance" in config["jobs"]
    assert "daily-notifications" in config["jobs"]
    assert "daily-recertify" in config["jobs"]
    assert config["jobs"]["daily-recertify"]["schedule"] == {"Hour": 13, "Minute": 0}


def test_next_run_weekly_rolls_forward() -> None:
    now = datetime(2026, 5, 12, 20, 0, tzinfo=ZoneInfo("America/Los_Angeles"))

    result = next_run_at({"Weekday": 1, "Hour": 18, "Minute": 0}, now=now)

    assert result == "2026-05-18T18:00-07:00"


def test_launch_agent_plist_uses_run_job_command() -> None:
    config = {
        "jobs": {
            "daily": {
                "job": "daily",
                "schedule": {"Hour": 16, "Minute": 30},
            }
        }
    }

    plist = build_plist("daily", python="/tmp/python", config=config)

    assert plist["Label"] == launch_agent_label("daily")
    assert plist["ProgramArguments"][0] == "/tmp/python"
    assert plist["ProgramArguments"][1].endswith("scripts/ops/run_job.py")
    assert plist["ProgramArguments"][-2:] == ["--job", "daily"]
    assert plist["StartCalendarInterval"] == {"Hour": 16, "Minute": 30}
    assert launchctl_command("load", "/tmp/montauk.plist")[-1] == "/tmp/montauk.plist"


def test_launch_agent_status_and_enabled_keys(tmp_path) -> None:
    config = {
        "jobs": {
            "daily": {"enabled": True, "job": "daily", "schedule": {"Hour": 16}},
            "monthly": {"enabled": False, "job": "confidence-vintage", "schedule": {"Day": 1}},
        }
    }

    assert job_keys(enabled_only=True, config=config) == ["daily"]
    status = status_for_job("daily", launch_agents_dir=tmp_path)
    assert status["installed"] is False
    (tmp_path / f"{launch_agent_label('daily')}.plist").write_text("<plist/>")
    assert status_for_job("daily", launch_agents_dir=tmp_path)["installed"] is True


def test_job_lock_blocks_overlap_and_allows_release(tmp_path) -> None:
    lock_path, payload = acquire_lock("daily", locks_dir=tmp_path)
    assert lock_path.exists()

    try:
        acquire_lock("daily", locks_dir=tmp_path)
    except JobLockedError as exc:
        assert exc.lock_path == lock_path
    else:
        raise AssertionError("expected lock acquisition to fail")

    release_lock(lock_path, payload)
    assert not lock_path.exists()


def test_run_job_writes_record_and_event(tmp_path) -> None:
    def runner(command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="status ok",
            stderr="",
        )

    record = run_job(
        "status",
        record_dir=tmp_path / "jobs",
        events_path=tmp_path / "events.jsonl",
        runner=runner,
        python="/tmp/python",
    )

    assert record["status"] == "ok"
    assert record["returncode"] == 0
    assert record["command"][0] == "/tmp/python"
    assert record["command"][1].endswith("scripts/ops/status.py")
    assert "schedule" in record
    assert record["output_artifact_paths"] == ["runs/operations/latest.json"]
    assert "runs/operations/latest.json" in output_artifact_paths("daily")
    assert (tmp_path / "events.jsonl").exists()
    assert read_events(events_path=tmp_path / "events.jsonl")[0]["event_type"] == "job_succeeded"


def test_notification_outbox_filters_routine_events() -> None:
    routine = {
        "timestamp_utc": "2026-05-09T01:00:00Z",
        "severity": "info",
        "event_type": "job_succeeded",
        "message": "Daily job completed.",
        "payload": {},
    }
    changed = {
        "timestamp_utc": "2026-05-09T02:00:00Z",
        "severity": "notice",
        "event_type": "signal_changed",
        "message": "Signal changed to risk_off.",
        "payload": {"risk_state": "risk_off"},
    }

    assert is_notifiable(routine) is False
    assert is_notifiable(changed) is True
    outbox = build_outbox([routine, changed])
    assert [note["event_type"] for note in outbox] == ["signal_changed"]
    assert outbox[0]["target_view"] == "current"
    assert "target" in outbox[0]


def test_notification_preferences_are_persisted_and_filter_events(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "notification_state.json"
    outbox_path = tmp_path / "notifications.json"
    append_event(
        "data_stale",
        "Data is stale.",
        severity="warning",
        events_path=events_path,
        timestamp_utc="2026-05-09T01:00:00Z",
    )

    state = set_notification_preference("data_stale", False, state_path=state_path)
    payload = scan_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
    )

    assert state["preferences"]["event_types"]["data_stale"]["enabled"] is False
    assert payload["pending_count"] == 0
    assert json.loads(state_path.read_text())["preferences"]["event_types"]["data_stale"]["enabled"] is False

    set_notification_preference("data_stale", True, state_path=state_path)
    payload = scan_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
    )

    assert payload["pending_count"] == 1
    assert payload["notifications"][0]["target_view"] == "data"
    assert payload["notifications"][0]["artifact_path"] == "runs/operations/governance.json"


def test_notification_scan_respects_sent_state(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "notification_state.json"
    outbox_path = tmp_path / "notifications.json"
    event = append_event(
        "job_failed",
        "Scheduled job failed.",
        severity="error",
        events_path=events_path,
        timestamp_utc="2026-05-09T01:00:00Z",
    )

    first = scan_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
    )
    assert first["pending_count"] == 1

    mark_sent([event_id(event)], state_path=state_path)
    second = scan_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
    )
    assert second["pending_count"] == 0


def test_notification_send_marks_sent_and_persists_outbox(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    state_path = tmp_path / "notification_state.json"
    outbox_path = tmp_path / "notifications.json"
    append_event(
        "job_failed",
        "Scheduled job failed.",
        severity="error",
        events_path=events_path,
        timestamp_utc="2026-05-09T01:00:00Z",
    )

    def sender(note: dict) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(["notify"], 0, stdout="", stderr="")

    payload = send_pending_notifications(
        events_path=events_path,
        outbox_path=outbox_path,
        state_path=state_path,
        sender=sender,
    )

    assert payload["sent_count"] == 1
    assert payload["pending_count"] == 0
    assert payload["notifications"][0]["status"] == "sent"
    assert json.loads(outbox_path.read_text())["notifications"][0]["status"] == "sent"


def test_governance_blocks_non_gold_active_champion() -> None:
    latest = {
        "active_signal": {
            "data_end_date": "2026-05-08",
            "risk_state": "risk_on",
            "validation": {"verdict": "WARN", "gold_status": False},
            "data_quality": {"fail": 0},
        }
    }

    report = evaluate_governance(latest, {"diverged_count": 0}, max_stale_calendar_days=999)

    assert report["state"] == "active_blocked"
    assert "active champion is not Gold Status" in report["blockers"]


def test_governance_flags_replacement_candidate_state() -> None:
    latest = {
        "active_signal": {
            "data_end_date": "2026-05-08",
            "risk_state": "risk_on",
            "active_champion": {"strategy": "old", "params_hash": "old-hash"},
            "validation": {"verdict": "PASS", "gold_status": True},
            "data_quality": {"fail": 0},
        }
    }
    strategy_review = {
        "status": "switch_candidate",
        "best_certified": {"strategy": "new", "params_hash": "new-hash"},
    }

    report = evaluate_governance(
        latest,
        {"diverged_count": 0},
        strategy_review,
        max_stale_calendar_days=999,
    )

    assert report["state"] == "replacement_candidate"
    assert "replacement candidate available: new" in report["reasons"]


def test_governance_requires_manual_review_for_trust_deterioration() -> None:
    latest = {
        "active_signal": {
            "data_end_date": "2026-05-08",
            "risk_state": "risk_on",
            "active_champion": {"strategy": "active", "params_hash": "hash"},
            "validation": {"verdict": "PASS", "gold_status": True},
            "data_quality": {"fail": 0},
        }
    }
    live = {
        "diverged_count": 0,
        "confidence_drift": {"delta": -0.08},
        "active_champion_performance_since_live_start": {
            "live_vs_buy_hold_multiple_proxy": 0.82,
        },
    }

    report = evaluate_governance(
        latest,
        live,
        {"status": "on_best_certified"},
        max_stale_calendar_days=999,
    )

    assert report["state"] == "manual_review_required"
    assert any("confidence drift deteriorated" in reason for reason in report["reasons"])
    assert any("live trust proxy" in reason for reason in report["reasons"])


def test_governance_logs_champion_change_event(tmp_path) -> None:
    latest_path = tmp_path / "latest.json"
    live_path = tmp_path / "live.json"
    strategy_review_path = tmp_path / "strategy_review.json"
    output_path = tmp_path / "governance.json"
    events_path = tmp_path / "events.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "active_signal": {
                    "data_end_date": "2026-05-07",
                    "risk_state": "risk_off",
                    "strategy": "old",
                    "params_hash": "old-hash",
                }
            }
        )
    )
    latest_path.write_text(
        json.dumps(
            {
                "active_signal": {
                    "data_end_date": "2026-05-08",
                    "risk_state": "risk_on",
                    "active_champion": {"strategy": "new", "params_hash": "new-hash"},
                    "validation": {"verdict": "PASS", "gold_status": True},
                    "data_quality": {"fail": 0},
                }
            }
        )
    )
    live_path.write_text(json.dumps({"diverged_count": 0}))
    strategy_review_path.write_text(json.dumps({"status": "on_best_certified"}))

    import ops.governance as governance

    old_append = governance.append_event

    def append_with_test_path(event_type: str, message: str, **kwargs) -> dict:
        kwargs["events_path"] = events_path
        return old_append(event_type, message, **kwargs)

    governance.append_event = append_with_test_path
    try:
        build_governance(
            latest_path=latest_path,
            live_holdout_path=live_path,
            strategy_review_path=strategy_review_path,
            output_path=output_path,
        )
    finally:
        governance.append_event = old_append

    events = read_events(events_path=events_path)
    assert events[0]["event_type"] == "champion_changed"
    assert events[0]["payload"]["previous"]["strategy"] == "old"
    assert events[0]["payload"]["current"]["strategy"] == "new"


def test_governance_emits_stale_data_event(tmp_path) -> None:
    latest_path = tmp_path / "latest.json"
    live_path = tmp_path / "live.json"
    strategy_review_path = tmp_path / "strategy_review.json"
    events_path = tmp_path / "events.jsonl"
    latest_path.write_text(
        json.dumps(
            {
                "active_signal": {
                    "data_end_date": "2026-01-01",
                    "risk_state": "risk_on",
                    "validation": {"verdict": "PASS", "gold_status": True},
                    "data_quality": {"fail": 0},
                }
            }
        )
    )
    live_path.write_text(json.dumps({"diverged_count": 0}))
    strategy_review_path.write_text(json.dumps({"status": "on_best_certified"}))

    import ops.governance as governance

    old_append = governance.append_event

    def append_with_test_path(event_type: str, message: str, **kwargs) -> dict:
        kwargs["events_path"] = events_path
        return old_append(event_type, message, **kwargs)

    governance.append_event = append_with_test_path
    try:
        report = build_governance(
            latest_path=latest_path,
            live_holdout_path=live_path,
            strategy_review_path=strategy_review_path,
            output_path=tmp_path / "governance.json",
        )
    finally:
        governance.append_event = old_append

    assert report["state"] == "active_watch"
    assert read_events(events_path=events_path)[0]["event_type"] == "data_stale"


def test_live_holdout_matches_latest_snapshot(tmp_path, monkeypatch) -> None:
    snapshot = _snapshot()
    (tmp_path / "2026-05-08.json").write_text(json.dumps(snapshot))

    import ops.live_holdout as live_holdout

    monkeypatch.setattr(live_holdout, "load_active_champion", lambda: {"strategy": "example"})
    monkeypatch.setattr(live_holdout, "compute_replay_by_date", lambda champion: {"2026-05-08": snapshot})

    report = build_live_holdout(signals_dir=tmp_path, output_path=tmp_path / "live.json")

    assert report["status"] == "ok"
    assert report["matched_count"] == 1
    assert report["diverged_count"] == 0


def test_live_holdout_tracks_proxy_performance_and_confidence_drift(tmp_path, monkeypatch) -> None:
    first = _snapshot(date="2026-05-08")
    first["buy_event"] = True
    first["validation"] = {}
    first["validation"]["composite_confidence"] = 0.7
    second = _snapshot(date="2026-05-09")
    second["close"] = 132.0
    second["validation"] = {}
    second["validation"]["composite_confidence"] = 0.8
    second["active_champion"]["metrics"] = {"share_multiple": 30.4933}
    (tmp_path / "2026-05-08.json").write_text(json.dumps(first))
    (tmp_path / "2026-05-09.json").write_text(json.dumps(second))

    import ops.live_holdout as live_holdout

    monkeypatch.setattr(live_holdout, "load_active_champion", lambda: {"strategy": "example"})
    monkeypatch.setattr(
        live_holdout,
        "compute_replay_by_date",
        lambda champion: {"2026-05-08": first, "2026-05-09": second},
    )

    report = build_live_holdout(signals_dir=tmp_path, output_path=tmp_path / "live.json")

    assert report["expected_next_open_execution_proxy"][0]["event"] == "entry"
    assert report["active_champion_performance_since_live_start"]["signal_return_pct"] == 6.9259
    assert report["backtest_vs_live_degradation"]["backtest_share_multiple"] == 30.4933
    assert report["confidence_drift"]["delta"] == 0.1


def test_research_queue_generates_warning_based_proposals(tmp_path) -> None:
    latest = {
        "active_signal": {
            "warnings": [
                "2023_rebound: share_multiple=0.434",
                "bootstrap downside probability 0.79 > 0.50",
                "n_params=53 exceeds regime_transitions=19",
                "QQQ same-param share_multiple=0.484 < 0.50",
            ]
        }
    }

    proposals = generate_proposals(latest, {"state": "active_watch"})
    kinds = {item["kind"] for item in proposals}

    assert "rebound_capture_repair" in kinds
    assert "drawdown_resilience_probe" in kinds
    assert "parsimony_challenger" in kinds
    assert "portability_repair" in kinds

    queue = write_proposals(
        proposals,
        ideas_dir=tmp_path / "ideas",
        queue_path=tmp_path / "queue.json",
    )
    assert queue["idea_count"] == len(proposals)


def test_research_queue_review_updates_queue_and_idea_file(tmp_path) -> None:
    proposals = [
        {
            "schema_version": 1,
            "id": "abc123",
            "created_utc": "2026-05-12T01:00:00Z",
            "status": "proposed",
            "kind": "example",
            "rationale": "test",
            "suggested_tests": [],
        }
    ]
    queue_path = tmp_path / "queue.json"
    ideas_dir = tmp_path / "ideas"
    write_proposals(proposals, ideas_dir=ideas_dir, queue_path=queue_path)

    queue = update_idea_status(
        "abc123",
        "approved",
        queue_path=queue_path,
        ideas_dir=ideas_dir,
        events_path=tmp_path / "events.jsonl",
    )

    assert queue["ideas"][0]["status"] == "approved"
    assert json.loads((ideas_dir / "abc123.json").read_text())["status"] == "approved"
    assert read_events(events_path=tmp_path / "events.jsonl")[0]["event_type"] == "research_idea_reviewed"


def test_research_runner_creates_bounded_plan_record(tmp_path) -> None:
    idea = {
        "id": "abc123",
        "kind": "parsimony_challenger",
        "rationale": "test",
        "status": "approved",
        "validation_tier": "T0/T1",
        "suggested_tests": ["family_confidence_leaderboard", "unknown_test"],
        "time_budget": "bounded",
        "expected_failure_mode": "fails validation",
    }

    plan = build_research_plan(idea, python="/tmp/python")
    record = create_research_run(idea, runs_dir=tmp_path, events_path=tmp_path / "events.jsonl")

    assert plan["steps"][0]["command"][0] == "/tmp/python"
    assert plan["steps"][1]["status"] == "manual_review"
    assert record["status"] == "planned"
    assert Path(record["record_path"]).exists()


def test_doctor_report_has_structured_checks() -> None:
    report = build_doctor_report()

    assert report["schema_version"] == 1
    assert isinstance(report["checks"], list)
    assert "scheduler" in report


def test_strategy_review_flags_best_certified_candidate(tmp_path) -> None:
    leaderboard_path = tmp_path / "leaderboard.json"
    latest_path = tmp_path / "latest.json"
    output_path = tmp_path / "strategy_review.json"
    leaderboard_path.write_text(
        json.dumps(
            [
                {
                    "strategy": "old",
                    "rank": 1,
                    "gold_status": True,
                    "validation": {"verdict": "PASS", "gold_status": True, "composite_confidence": 0.6},
                },
                {
                    "strategy": "best",
                    "rank": 2,
                    "gold_status": True,
                    "validation": {"verdict": "PASS", "gold_status": True, "composite_confidence": 0.9},
                },
            ]
        )
    )
    latest_path.write_text(
        json.dumps(
            {
                "active_signal": {
                    "risk_state": "risk_on",
                    "data_end_date": "2026-05-13",
                    "active_champion": {"strategy": "old", "rank": 1},
                }
            }
        )
    )

    report = build_strategy_review(
        leaderboard_path=leaderboard_path,
        latest_path=latest_path,
        output_path=output_path,
        events_path=tmp_path / "events.jsonl",
    )

    assert report["status"] == "switch_candidate"
    assert report["best_certified"]["strategy"] == "best"
    assert output_path.exists()

    read_only_output = tmp_path / "read_only_strategy_review.json"
    read_only_events = tmp_path / "read_only_events.jsonl"
    read_only_report = build_strategy_review(
        leaderboard_path=leaderboard_path,
        latest_path=latest_path,
        output_path=read_only_output,
        events_path=read_only_events,
        write=False,
    )

    assert read_only_report["status"] == "switch_candidate"
    assert not read_only_output.exists()
    assert not read_only_events.exists()

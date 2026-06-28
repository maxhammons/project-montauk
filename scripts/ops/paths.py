from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = PROJECT_ROOT / "runs"
SPIKE_DIR = PROJECT_ROOT / "spike"
SIGNALS_DIR = PROJECT_ROOT / "signals"
OPERATIONS_DIR = RUNS_DIR / "operations"
SCHEDULER_DIR = RUNS_DIR / "scheduler"
JOB_RECORDS_DIR = SCHEDULER_DIR / "jobs"
LOCKS_DIR = SCHEDULER_DIR / "locks"
RESEARCH_QUEUE_DIR = RUNS_DIR / "research_queue"
RESEARCH_RUNS_DIR = RESEARCH_QUEUE_DIR / "runs"
RESEARCH_HYPOTHESES_DIR = RESEARCH_QUEUE_DIR / "hypotheses"
EVENTS_PATH = OPERATIONS_DIR / "events.jsonl"
LATEST_PATH = OPERATIONS_DIR / "latest.json"
NOTIFICATIONS_PATH = OPERATIONS_DIR / "notifications.json"
NOTIFICATION_STATE_PATH = OPERATIONS_DIR / "notification_state.json"
LIVE_HOLDOUT_PATH = OPERATIONS_DIR / "live_holdout.json"
GOVERNANCE_PATH = OPERATIONS_DIR / "governance.json"
ACKNOWLEDGED_WARNINGS_PATH = OPERATIONS_DIR / "acknowledged_warnings.json"
STRATEGY_REVIEW_PATH = OPERATIONS_DIR / "strategy_review.json"
LEADERBOARD_PATH = SPIKE_DIR / "leaderboard.json"
SCHEDULER_CONFIG_PATH = SCHEDULER_DIR / "config.json"
IDEAS_DIR = RESEARCH_QUEUE_DIR / "ideas"
RESEARCH_QUEUE_PATH = RESEARCH_QUEUE_DIR / "queue.json"


def ensure_ops_dirs() -> None:
    for path in (
        SIGNALS_DIR,
        OPERATIONS_DIR,
        SCHEDULER_DIR,
        JOB_RECORDS_DIR,
        LOCKS_DIR,
        RESEARCH_QUEUE_DIR,
        RESEARCH_RUNS_DIR,
        RESEARCH_HYPOTHESES_DIR,
        IDEAS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)

"""Historical-bar immutability ledger tests (Phase 3.4, 2026-06-09).

Exercises data/manifest.py's append-only manifest-history.jsonl mechanism in a
tmp dir: the ledger pins the hash of "all rows up to the build-time cutoff" so
a later refresh that retroactively rewrites old bars is caught even though the
whole-file manifest checksum legitimately changes every day.
"""

from __future__ import annotations

import json

from data.manifest import (
    append_history,
    load_history,
    verify_bar_immutability,
)

_HEADER = "date,open,high,low,close,volume"
_ROWS = [
    "2026-01-02,10.0,10.5,9.5,10.2,1000",
    "2026-01-05,10.2,10.8,10.0,10.6,1100",
    "2026-01-06,10.6,11.0,10.4,10.9,1200",
]


def _write_csv(tmp_path, rows, name: str = "TECL.csv"):
    # The ledger iterates CSV_SPECS, so the tmp file must use a spec'd name.
    path = tmp_path / name
    path.write_text("\n".join([_HEADER, *rows]) + "\n")
    return path


def test_bar_immutability_bootstrap_when_no_history(tmp_path) -> None:
    # First-run bootstrap: a missing/empty ledger is "nothing to verify yet",
    # not a failure — quality.py maps this to PASS with a note.
    history_path = tmp_path / "manifest-history.jsonl"
    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is True
    assert result["checked"] == 0
    assert result["note"] == "no history yet"


def test_bar_immutability_passes_on_legit_append(tmp_path) -> None:
    history_path = tmp_path / "manifest-history.jsonl"
    csv_path = _write_csv(tmp_path, _ROWS)

    appended = append_history(data_dir=str(tmp_path), history_path=str(history_path))
    assert [e["file"] for e in appended] == ["TECL.csv"]
    assert appended[0]["cutoff_date"] == "2026-01-06"
    assert appended[0]["rows_to_cutoff"] == 3

    # New bars after the cutoff are normal refresh behavior, never a failure.
    _write_csv(tmp_path, _ROWS + ["2026-01-07,10.9,11.2,10.7,11.1,1300"])
    assert csv_path.exists()
    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is True
    assert result["checked"] == 1
    assert result["failures"] == []


def test_bar_immutability_catches_retroactive_edit(tmp_path) -> None:
    history_path = tmp_path / "manifest-history.jsonl"
    _write_csv(tmp_path, _ROWS)
    append_history(data_dir=str(tmp_path), history_path=str(history_path))

    # Rewrite a bar that existed at ledger time — the exact tamper class
    # whole-file manifest checksums cannot distinguish from a refresh.
    mutated = list(_ROWS)
    mutated[1] = "2026-01-05,10.2,10.8,10.0,99.9,1100"
    _write_csv(tmp_path, mutated + ["2026-01-07,10.9,11.2,10.7,11.1,1300"])

    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is False
    assert len(result["failures"]) == 1
    failure = result["failures"][0]
    assert failure["file"] == "TECL.csv"
    assert failure["cutoff_date"] == "2026-01-06"
    assert "retroactive bar change" in failure["reason"]


def test_bar_immutability_fails_when_history_shrinks(tmp_path) -> None:
    history_path = tmp_path / "manifest-history.jsonl"
    _write_csv(tmp_path, _ROWS)
    append_history(data_dir=str(tmp_path), history_path=str(history_path))

    # A rebuild that drops coverage below an old cutoff must be loud — history
    # silently shrinking is indistinguishable from deleted bars.
    _write_csv(tmp_path, _ROWS[:1])
    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is False
    assert "coverage shrank" in result["failures"][0]["reason"]


def test_bar_immutability_tolerates_float_reserialization(tmp_path) -> None:
    # Recipe v2: a one-ULP reprint of the same price (100.44999694824219 vs
    # 100.4499969482422) is not a retroactive change — numeric cells hash by
    # normalized value, not raw text.
    history_path = tmp_path / "manifest-history.jsonl"
    _write_csv(tmp_path, ["2026-01-02,100.44999694824219,10.5,9.5,10.2,1000"])
    append_history(data_dir=str(tmp_path), history_path=str(history_path))

    _write_csv(
        tmp_path,
        [
            "2026-01-02,100.4499969482422,10.5,9.5,10.2,1000",  # same value, reprinted
            "2026-01-05,10.2,10.8,10.0,10.6,1100",
        ],
    )
    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is True
    assert result["failures"] == []


def test_bar_immutability_tolerates_derived_column_backfill(tmp_path) -> None:
    # Recipe v2: vix_close is a DERIVED column on TECL.csv (mirror of VIX.csv,
    # which is itself ledgered). It arrives a day late, so backfilling it
    # empty->populated on an existing bar must not trip immutability.
    history_path = tmp_path / "manifest-history.jsonl"
    header = "date,open,high,low,close,volume,vix_close"
    (tmp_path / "TECL.csv").write_text(
        header + "\n2026-01-02,10.0,10.5,9.5,10.2,1000,\n"
    )
    append_history(data_dir=str(tmp_path), history_path=str(history_path))

    (tmp_path / "TECL.csv").write_text(
        header
        + "\n2026-01-02,10.0,10.5,9.5,10.2,1000,18.92"  # vix_close backfilled
        + "\n2026-01-05,10.2,10.8,10.0,10.6,1100,19.1\n"
    )
    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is True
    assert result["failures"] == []


def test_bar_immutability_skips_legacy_recipe_entries(tmp_path) -> None:
    # A pre-v2 ledger entry (no recipe_version) is not comparable to the current
    # recipe, so verify ignores it rather than reading a recipe bump as tampering.
    history_path = tmp_path / "manifest-history.jsonl"
    history_path.write_text(
        json.dumps(
            {
                "file": "TECL.csv",
                "built_utc": "2026-06-09T00:00:00+00:00",
                "cutoff_date": "2026-01-02",
                "rows_to_cutoff": 1,
                "history_sha256": "deadbeef",  # v1 hash that won't match v2
            }
        )
        + "\n"
    )
    _write_csv(tmp_path, ["2026-01-02,10.0,10.5,9.5,10.2,1000"])

    result = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(history_path)
    )
    assert result["ok"] is True
    assert result["checked"] == 0  # legacy entry skipped, nothing to verify


def test_append_history_dedupes_unchanged_state(tmp_path) -> None:
    # write_manifest runs on every daily launch; repeat builds over unchanged
    # data must not bloat the append-only ledger.
    history_path = tmp_path / "manifest-history.jsonl"
    _write_csv(tmp_path, _ROWS)

    first = append_history(data_dir=str(tmp_path), history_path=str(history_path))
    second = append_history(data_dir=str(tmp_path), history_path=str(history_path))
    assert len(first) == 1
    assert second == []
    assert len(load_history(str(history_path))) == 1

    # New data state (appended bar) gets a fresh ledger entry.
    _write_csv(tmp_path, _ROWS + ["2026-01-07,10.9,11.2,10.7,11.1,1300"])
    third = append_history(data_dir=str(tmp_path), history_path=str(history_path))
    assert len(third) == 1
    entries = load_history(str(history_path))
    assert len(entries) == 2
    assert entries[1]["cutoff_date"] == "2026-01-07"
    # Ledger lines are valid JSONL.
    raw_lines = history_path.read_text().strip().splitlines()
    assert all(json.loads(line)["file"] == "TECL.csv" for line in raw_lines)

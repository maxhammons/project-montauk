"""Phase 3.4 — data immutability + refresh determinism (deep-val D8.1 / D8.2).

Covers the historical-bar immutability ledger in scripts/data/manifest.py
(_canonical_history, append_history, verify_bar_immutability), the
data-quality wiring in scripts/data/quality.py (bar_immutability +
refresh_determinism checks), and loader-level refresh determinism: a second
pull on the same day must be a byte-identical no-op.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data import loader, quality
from data.manifest import (
    _canonical_history,
    append_history,
    load_history,
    verify_bar_immutability,
)

HEADER = "date,open,high,low,close,adj_close,volume"


def _bar(date: str, base: float = 10.0, volume: int = 1000) -> str:
    return f"{date},{base},{base + 1},{base - 1},{base + 0.5},{base + 0.5},{volume}"


def _write_csv(path: Path, rows: list[str], header: str = HEADER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _seed_tecl(tmp_path: Path, rows: list[str]) -> tuple[Path, Path, Path]:
    """Tmp data dir with a TECL.csv + seeded history ledger."""
    data_dir = tmp_path / "data"
    csv_path = data_dir / "TECL.csv"
    history_path = data_dir / "manifest-history.jsonl"
    _write_csv(csv_path, rows)
    appended = append_history(data_dir=str(data_dir), history_path=str(history_path))
    assert [e["file"] for e in appended] == ["TECL.csv"]
    return data_dir, csv_path, history_path


def _verify(data_dir: Path, history_path: Path) -> dict:
    return verify_bar_immutability(
        data_dir=str(data_dir), history_path=str(history_path)
    )


# ─────────────────────────────────────────────────────────────────────
# _canonical_history — the frozen hashing recipe
# ─────────────────────────────────────────────────────────────────────


def test_canonical_history_defaults_to_max_date(tmp_path) -> None:
    csv_path = tmp_path / "TECL.csv"
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")])

    canon = _canonical_history(str(csv_path))
    assert canon["cutoff_date"] == "2026-06-03"
    assert canon["max_date"] == "2026-06-03"
    assert canon["rows_to_cutoff"] == 3
    assert isinstance(canon["history_sha256"], str)
    assert len(canon["history_sha256"]) == 64


def test_canonical_history_cutoff_excludes_later_rows(tmp_path) -> None:
    csv_path = tmp_path / "TECL.csv"
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")])
    full = _canonical_history(str(csv_path))
    partial = _canonical_history(str(csv_path), cutoff_date="2026-06-02")

    assert partial["rows_to_cutoff"] == 2
    assert partial["history_sha256"] != full["history_sha256"]
    assert partial["max_date"] == "2026-06-03"  # max_date reports the file, not the cut


def test_canonical_history_stable_across_legitimate_appends(tmp_path) -> None:
    csv_path = tmp_path / "TECL.csv"
    rows = [_bar("2026-06-01"), _bar("2026-06-02")]
    _write_csv(csv_path, rows)
    before = _canonical_history(str(csv_path), cutoff_date="2026-06-02")

    _write_csv(csv_path, rows + [_bar("2026-06-03"), _bar("2026-06-04")])
    after = _canonical_history(str(csv_path), cutoff_date="2026-06-02")

    assert after["history_sha256"] == before["history_sha256"]
    assert after["rows_to_cutoff"] == before["rows_to_cutoff"]


def test_canonical_history_detects_single_cell_edit(tmp_path) -> None:
    csv_path = tmp_path / "TECL.csv"
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02")])
    before = _canonical_history(str(csv_path))

    _write_csv(csv_path, [_bar("2026-06-01", base=10.01), _bar("2026-06-02")])
    after = _canonical_history(str(csv_path))

    assert after["history_sha256"] != before["history_sha256"]


def test_canonical_history_detects_formatting_only_rewrite(tmp_path) -> None:
    # The recipe hashes raw row text on purpose: a refresh that re-rounds
    # floats in historical rows is a retroactive change, not a no-op.
    csv_path = tmp_path / "TECL.csv"
    _write_csv(csv_path, ["2026-06-01,10,11,9,10.5,10.5,1000"])
    before = _canonical_history(str(csv_path))

    _write_csv(csv_path, ["2026-06-01,10.0,11.0,9.0,10.5,10.5,1000"])
    after = _canonical_history(str(csv_path))

    assert after["history_sha256"] != before["history_sha256"]


def test_canonical_history_falls_back_to_first_field_without_date_column(
    tmp_path,
) -> None:
    # TECL_distributions.csv keys rows by ex_date — field 0 is the date.
    csv_path = tmp_path / "TECL_distributions.csv"
    _write_csv(
        csv_path,
        ["2026-03-24,0.25", "2026-06-20,0.30"],
        header="ex_date,amount",
    )
    canon = _canonical_history(str(csv_path), cutoff_date="2026-03-31")
    assert canon["rows_to_cutoff"] == 1
    assert canon["max_date"] == "2026-06-20"


def test_canonical_history_empty_file(tmp_path) -> None:
    csv_path = tmp_path / "TECL.csv"
    csv_path.write_text("", encoding="utf-8")
    canon = _canonical_history(str(csv_path))
    assert canon["history_sha256"] is None
    assert canon["rows_to_cutoff"] == 0


# ─────────────────────────────────────────────────────────────────────
# append_history — append-only ledger semantics
# ─────────────────────────────────────────────────────────────────────


def test_append_history_is_idempotent_on_unchanged_data(tmp_path) -> None:
    data_dir, _, history_path = _seed_tecl(tmp_path, [_bar("2026-06-01")])

    again = append_history(data_dir=str(data_dir), history_path=str(history_path))
    assert again == []  # entries mark data states, not build invocations
    assert len(load_history(str(history_path))) == 1


def test_append_history_ledgers_each_new_data_state(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(
        tmp_path, [_bar("2026-06-01"), _bar("2026-06-02")]
    )
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")])

    appended = append_history(data_dir=str(data_dir), history_path=str(history_path))
    assert [e["file"] for e in appended] == ["TECL.csv"]

    entries = load_history(str(history_path))
    assert len(entries) == 2  # append-only: the old state stays ledgered
    assert entries[0]["cutoff_date"] == "2026-06-02"
    assert entries[1]["cutoff_date"] == "2026-06-03"


def test_append_history_skips_files_not_in_specs_or_missing(tmp_path) -> None:
    data_dir = tmp_path / "data"
    history_path = data_dir / "manifest-history.jsonl"
    _write_csv(data_dir / "TECL.csv", [_bar("2026-06-01")])
    _write_csv(data_dir / "rogue.csv", [_bar("2026-06-01")])  # not a spec'd CSV

    appended = append_history(data_dir=str(data_dir), history_path=str(history_path))
    assert [e["file"] for e in appended] == ["TECL.csv"]


# ─────────────────────────────────────────────────────────────────────
# verify_bar_immutability — retroactive-change detection (D8.1)
# ─────────────────────────────────────────────────────────────────────


def test_verify_passes_with_no_history_yet(tmp_path) -> None:
    res = verify_bar_immutability(
        data_dir=str(tmp_path), history_path=str(tmp_path / "manifest-history.jsonl")
    )
    assert res["ok"] is True
    assert res["checked"] == 0


def test_verify_passes_after_legitimate_append(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(
        tmp_path, [_bar("2026-06-01"), _bar("2026-06-02")]
    )
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")])

    res = _verify(data_dir, history_path)
    assert res["ok"] is True
    assert res["checked"] == 1
    assert res["failures"] == []


def test_verify_detects_retroactive_bar_edit(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(
        tmp_path, [_bar("2026-06-01"), _bar("2026-06-02")]
    )
    # Reprice a ledgered bar while legitimately appending a new one.
    _write_csv(
        csv_path,
        [_bar("2026-06-01", base=99.0), _bar("2026-06-02"), _bar("2026-06-03")],
    )

    res = _verify(data_dir, history_path)
    assert res["ok"] is False
    assert len(res["failures"]) == 1
    failure = res["failures"][0]
    assert failure["file"] == "TECL.csv"
    assert "retroactive bar change" in failure["reason"]


def test_verify_detects_deleted_historical_row(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(
        tmp_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")]
    )
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-03")])  # 06-02 vanished

    res = _verify(data_dir, history_path)
    assert res["ok"] is False
    assert any("retroactive bar change" in f["reason"] for f in res["failures"])


def test_verify_detects_coverage_shrink(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(
        tmp_path, [_bar("2026-06-01"), _bar("2026-06-02"), _bar("2026-06-03")]
    )
    _write_csv(csv_path, [_bar("2026-06-01"), _bar("2026-06-02")])  # truncated tail

    res = _verify(data_dir, history_path)
    assert res["ok"] is False
    assert any("coverage shrank" in f["reason"] for f in res["failures"])


def test_verify_detects_file_missing_from_disk(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(tmp_path, [_bar("2026-06-01")])
    csv_path.unlink()

    res = _verify(data_dir, history_path)
    assert res["ok"] is False
    assert any("missing on disk" in f["reason"] for f in res["failures"])


def test_verify_checks_every_ledgered_state(tmp_path) -> None:
    data_dir, csv_path, history_path = _seed_tecl(tmp_path, [_bar("2026-06-01")])
    rows = [_bar("2026-06-01")]
    for date in ("2026-06-02", "2026-06-03"):
        rows.append(_bar(date))
        _write_csv(csv_path, rows)
        append_history(data_dir=str(data_dir), history_path=str(history_path))

    res = _verify(data_dir, history_path)
    assert res["ok"] is True
    assert res["checked"] == 3  # one per ledgered data state


# ─────────────────────────────────────────────────────────────────────
# data-quality wiring (scripts/data/quality.py)
# ─────────────────────────────────────────────────────────────────────


def test_quality_registers_immutability_and_determinism_checks() -> None:
    names = [name for name, _ in quality.LOCAL_TESTS]
    assert "bar_immutability" in names
    assert "refresh_determinism" in names


def test_quality_bar_immutability_bootstrap_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        quality,
        "verify_bar_immutability",
        lambda: {"ok": True, "checked": 0, "failures": [], "note": "no history yet"},
    )
    results = quality.test_bar_immutability()
    assert [r["status"] for r in results] == ["PASS"]
    assert "no history yet" in results[0]["summary"]


def test_quality_bar_immutability_pass_and_fail_mapping(monkeypatch) -> None:
    monkeypatch.setattr(
        quality,
        "verify_bar_immutability",
        lambda: {"ok": True, "checked": 7, "failures": []},
    )
    assert [r["status"] for r in quality.test_bar_immutability()] == ["PASS"]

    failure = {
        "file": "TECL.csv",
        "cutoff_date": "2026-06-08",
        "reason": "retroactive bar change: …",
    }
    monkeypatch.setattr(
        quality,
        "verify_bar_immutability",
        lambda: {"ok": False, "checked": 7, "failures": [failure]},
    )
    results = quality.test_bar_immutability()
    assert [r["status"] for r in results] == ["FAIL"]
    assert results[0]["scope"] == "TECL.csv"
    assert "retroactive bar change" in results[0]["summary"]


@pytest.mark.skipif(
    not (Path(loader.TECL_CSV).exists()),
    reason="project data files not present",
)
def test_quality_refresh_determinism_on_real_loaders() -> None:
    # D8.2 — two loads through the full loader path (drag haircut, merges)
    # must fingerprint identically. Runs on the real project CSVs.
    results = quality.test_refresh_determinism()
    assert results, "expected at least one loader to be checked"
    assert [r["status"] for r in results] == ["PASS"] * len(results)


# ─────────────────────────────────────────────────────────────────────
# refresh determinism at the loader level (D8.2)
# ─────────────────────────────────────────────────────────────────────


def _fake_remote(rows: list[str]):
    """A canned Yahoo response covering `rows` (date,o,h,l,c,adj,v lines)."""
    records = []
    for row in rows:
        date, o, h, lo, c, adj, v = row.split(",")
        records.append(
            {
                "date": pd.Timestamp(date),
                "open": float(o),
                "high": float(h),
                "low": float(lo),
                "close": float(c),
                "adj_close": float(adj),
                "volume": int(v),
            }
        )
    frame = pd.DataFrame(records)

    def fetch(ticker: str, start: str = "2008-12-01", end: str | None = None):
        return frame.copy()

    return fetch


def test_second_pull_same_day_is_a_byte_identical_noop(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "TECL.csv"
    base = [_bar("2026-06-01"), _bar("2026-06-02")]
    fresh = [_bar("2026-06-03"), _bar("2026-06-04")]
    _write_csv(csv_path, base)
    monkeypatch.setattr(loader, "_fetch_ticker_yahoo", _fake_remote(base + fresh))

    first = loader._append_new_bars(str(csv_path), "TECL")
    assert first == 2
    after_first = csv_path.read_bytes()

    second = loader._append_new_bars(str(csv_path), "TECL")
    assert second == 0  # same-day re-pull appends nothing
    assert csv_path.read_bytes() == after_first  # …and rewrites nothing


def test_append_is_deterministic_across_identical_pulls(tmp_path, monkeypatch) -> None:
    base = [_bar("2026-06-01"), _bar("2026-06-02")]
    fresh = [_bar("2026-06-03")]
    path_a = tmp_path / "a" / "TECL.csv"
    path_b = tmp_path / "b" / "TECL.csv"
    _write_csv(path_a, base)
    _write_csv(path_b, base)
    monkeypatch.setattr(loader, "_fetch_ticker_yahoo", _fake_remote(base + fresh))

    assert loader._append_new_bars(str(path_a), "TECL") == 1
    assert loader._append_new_bars(str(path_b), "TECL") == 1
    assert path_a.read_bytes() == path_b.read_bytes()


def test_append_preserves_canonical_history_of_prior_bars(
    tmp_path, monkeypatch
) -> None:
    # The full Phase 3.4 contract in one motion: a real loader append must not
    # disturb the ledgered hash of the bars that existed before the pull.
    data_dir = tmp_path / "data"
    csv_path = data_dir / "TECL.csv"
    history_path = data_dir / "manifest-history.jsonl"
    base = [_bar("2026-06-01"), _bar("2026-06-02")]
    _write_csv(csv_path, base)
    append_history(data_dir=str(data_dir), history_path=str(history_path))

    monkeypatch.setattr(
        loader, "_fetch_ticker_yahoo", _fake_remote(base + [_bar("2026-06-03")])
    )
    assert loader._append_new_bars(str(csv_path), "TECL") == 1

    res = verify_bar_immutability(
        data_dir=str(data_dir), history_path=str(history_path)
    )
    assert res["ok"] is True, res["failures"]

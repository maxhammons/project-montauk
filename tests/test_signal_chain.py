"""Phase 3.1 — hash-chained immutable signal log (scripts/ops/signal_chain.py).

Covers the chain ledger contract end-to-end:
  - backfill/build is date-ordered, idempotent, and append-only
  - every tamper class is detectable: snapshot edit, snapshot deletion,
    ledger-line tamper, out-of-order backfill, unparseable ledger lines
  - a broken chain is never extended (appending past a break would launder it)
  - ops.daily.write_signal_snapshot embeds prev_snapshot_sha256 and ledgers
    each newly written snapshot; allow_overwrite rewrites are tamper-visible
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ops import daily, signal_chain


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _write_snapshot(signals_dir: Path, date: str, **extra) -> Path:
    """Write a minimal date-named snapshot file."""
    signals_dir.mkdir(parents=True, exist_ok=True)
    payload = {"data_end_date": date, "risk_state": "risk_on", **extra}
    path = signals_dir / f"{date}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _chain_entries(chain_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in chain_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _setup_chain(tmp_path: Path, dates: list[str]) -> tuple[Path, Path]:
    """Signals dir with snapshots for `dates`, ledgered. Returns (dir, chain)."""
    signals_dir = tmp_path / "signals"
    for date in dates:
        _write_snapshot(signals_dir, date)
    chain_path = signals_dir / "chain.jsonl"
    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"], built
    return signals_dir, chain_path


# ─────────────────────────────────────────────────────────────────────
# file_sha256
# ─────────────────────────────────────────────────────────────────────


def test_file_sha256_hashes_raw_bytes(tmp_path) -> None:
    path = tmp_path / "x.json"
    path.write_bytes(b'{"a": 1}\n')
    assert signal_chain.file_sha256(path) == hashlib.sha256(b'{"a": 1}\n').hexdigest()


# ─────────────────────────────────────────────────────────────────────
# build_chain — backfill semantics
# ─────────────────────────────────────────────────────────────────────


def test_build_chain_backfills_in_date_order_with_linkage(tmp_path) -> None:
    signals_dir = tmp_path / "signals"
    # Write deliberately out of filesystem order; ledger must sort by date.
    for date in ("2026-06-03", "2026-06-01", "2026-06-02"):
        _write_snapshot(signals_dir, date)
    chain_path = signals_dir / "chain.jsonl"

    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"] is True
    assert built["appended"] == 3
    assert built["entries"] == 3

    entries = _chain_entries(chain_path)
    assert [e["date"] for e in entries] == ["2026-06-01", "2026-06-02", "2026-06-03"]
    # Genesis link is null; every later link is the previous line's sha256.
    assert entries[0]["prev_sha256"] is None
    for prev, curr in zip(entries, entries[1:]):
        assert curr["prev_sha256"] == prev["sha256"]
    # Ledgered hashes are the raw byte hashes of the snapshot files.
    for entry in entries:
        assert entry["sha256"] == signal_chain.file_sha256(signals_dir / entry["file"])


def test_build_chain_is_idempotent(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    before = chain_path.read_bytes()

    again = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert again["ok"] is True
    assert again["appended"] == 0
    assert again["entries"] == 2
    assert chain_path.read_bytes() == before  # repeat builds never rewrite the ledger


def test_build_chain_extends_with_newer_snapshot(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    _write_snapshot(signals_dir, "2026-06-03")

    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"] is True
    assert built["appended"] == 1

    entries = _chain_entries(chain_path)
    assert entries[-1]["date"] == "2026-06-03"
    assert entries[-1]["prev_sha256"] == entries[-2]["sha256"]


def test_build_chain_ignores_non_snapshot_files(tmp_path) -> None:
    signals_dir = tmp_path / "signals"
    _write_snapshot(signals_dir, "2026-06-01")
    (signals_dir / "notes.json").write_text("{}\n", encoding="utf-8")
    (signals_dir / "2026-06-01.json.bak").write_text("{}\n", encoding="utf-8")
    chain_path = signals_dir / "chain.jsonl"

    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"] is True
    assert built["appended"] == 1
    assert [e["file"] for e in _chain_entries(chain_path)] == ["2026-06-01.json"]


def test_build_chain_refuses_out_of_order_backfill(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-02", "2026-06-03"])
    # A snapshot dated before the last ledgered date appears later: an
    # append-only date-ordered ledger cannot insert it — loud break, no append.
    _write_snapshot(signals_dir, "2026-06-01")

    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"] is False
    assert built["appended"] == 0
    assert [b["kind"] for b in built["breaks"]] == ["out_of_order_backfill"]
    assert built["breaks"][0]["date"] == "2026-06-01"


def test_build_chain_never_extends_a_broken_chain(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    # Tamper with a ledgered snapshot, then present a new date for appending.
    (signals_dir / "2026-06-01.json").write_text(
        '{"tampered": true}\n', encoding="utf-8"
    )
    _write_snapshot(signals_dir, "2026-06-03")
    before = chain_path.read_bytes()

    built = signal_chain.build_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert built["ok"] is False
    assert built["appended"] == 0  # appending past a break would launder the tamper
    assert any(b["kind"] == "hash_mismatch" for b in built["breaks"])
    assert chain_path.read_bytes() == before


# ─────────────────────────────────────────────────────────────────────
# verify_chain — tamper detection
# ─────────────────────────────────────────────────────────────────────


def test_verify_chain_clean(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(
        tmp_path, ["2026-06-01", "2026-06-02", "2026-06-03"]
    )
    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is True
    assert result["entries"] == 3
    assert result["breaks"] == []
    assert result["unledgered"] == []


def test_verify_chain_empty_ledger_is_ok_but_reports_unledgered(tmp_path) -> None:
    signals_dir = tmp_path / "signals"
    _write_snapshot(signals_dir, "2026-06-01")
    chain_path = signals_dir / "chain.jsonl"  # never built

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is True  # not-yet-ledgered is build work, not a tamper signal
    assert result["entries"] == 0
    assert result["unledgered"] == ["2026-06-01"]


def test_verify_chain_detects_retroactive_snapshot_edit(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    # Even a formatting-only edit must break the chain — bytes are the contract.
    target = signals_dir / "2026-06-01.json"
    target.write_text(
        json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=4) + "\n",
        encoding="utf-8",
    )

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is False
    mismatches = [b for b in result["breaks"] if b["kind"] == "hash_mismatch"]
    assert len(mismatches) == 1
    assert mismatches[0]["file"] == "2026-06-01.json"


def test_verify_chain_detects_deleted_snapshot(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    (signals_dir / "2026-06-01.json").unlink()

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is False
    assert any(
        b["kind"] == "missing_file" and b["file"] == "2026-06-01.json"
        for b in result["breaks"]
    )


def test_verify_chain_detects_ledger_line_tamper(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    entries = _chain_entries(chain_path)
    entries[0]["sha256"] = "0" * 64  # rewrite history inside the ledger itself
    chain_path.write_text(
        "".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8"
    )

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is False
    kinds = {b["kind"] for b in result["breaks"]}
    # The forged line no longer matches the file on disk, and the next line's
    # back-pointer no longer matches the forged sha — both must surface.
    assert "hash_mismatch" in kinds
    assert "linkage" in kinds


def test_verify_chain_reports_unparseable_ledger_line(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01"])
    with chain_path.open("a", encoding="utf-8") as f:
        f.write("not json at all\n")

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is False
    assert any(b["kind"] == "unparseable_line" for b in result["breaks"])


def test_verify_chain_detects_duplicate_and_out_of_order_dates(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01", "2026-06-02"])
    entries = _chain_entries(chain_path)
    forged = dict(entries[0])
    forged["prev_sha256"] = entries[-1]["sha256"]
    with chain_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(forged) + "\n")  # re-ledger an old date at the tail

    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is False
    kinds = {b["kind"] for b in result["breaks"]}
    assert "duplicate_date" in kinds
    assert "date_order" in kinds


def test_chain_health_is_read_only(tmp_path) -> None:
    signals_dir, chain_path = _setup_chain(tmp_path, ["2026-06-01"])
    _write_snapshot(signals_dir, "2026-06-02")  # unledgered on purpose
    before = chain_path.read_bytes()

    health = signal_chain.chain_health(signals_dir=signals_dir, chain_path=chain_path)
    assert health["ok"] is True
    assert health["unledgered"] == ["2026-06-02"]
    assert chain_path.read_bytes() == before  # probe never mutates the ledger


def test_verify_chain_missing_signals_dir(tmp_path) -> None:
    signals_dir = tmp_path / "nope"
    result = signal_chain.verify_chain(
        signals_dir=signals_dir, chain_path=signals_dir / "chain.jsonl"
    )
    assert result["ok"] is True
    assert result["entries"] == 0
    assert result["unledgered"] == []


# ─────────────────────────────────────────────────────────────────────
# ops.daily.write_signal_snapshot integration
# ─────────────────────────────────────────────────────────────────────


def test_write_signal_snapshot_embeds_prev_sha_and_ledgers(tmp_path) -> None:
    signals_dir = tmp_path / "signals"

    day1 = {"data_end_date": "2026-06-01", "risk_state": "risk_on"}
    path1, status1, _ = daily.write_signal_snapshot(day1, signals_dir=signals_dir)
    assert status1 == "written"
    stored1 = json.loads(path1.read_text(encoding="utf-8"))
    assert stored1["prev_snapshot_sha256"] is None  # genesis snapshot

    day1_sha = signal_chain.file_sha256(path1)
    day2 = {"data_end_date": "2026-06-02", "risk_state": "risk_off"}
    path2, status2, _ = daily.write_signal_snapshot(day2, signals_dir=signals_dir)
    assert status2 == "written"
    stored2 = json.loads(path2.read_text(encoding="utf-8"))
    assert stored2["prev_snapshot_sha256"] == day1_sha

    chain_path = signals_dir / "chain.jsonl"
    result = signal_chain.verify_chain(signals_dir=signals_dir, chain_path=chain_path)
    assert result["ok"] is True
    assert result["entries"] == 2
    assert result["unledgered"] == []


def test_write_signal_snapshot_unchanged_dedup_survives_chain_fields(tmp_path) -> None:
    signals_dir = tmp_path / "signals"
    snapshot = {"data_end_date": "2026-06-01", "risk_state": "risk_on"}
    daily.write_signal_snapshot(dict(snapshot), signals_dir=signals_dir)

    # Re-submitting the same comparable signal must dedup as "unchanged" even
    # though the stored copy carries prev_snapshot_sha256 and the new one
    # doesn't — chain fields are not part of the comparable contract.
    _, status, _ = daily.write_signal_snapshot(dict(snapshot), signals_dir=signals_dir)
    assert status == "unchanged"


def test_write_signal_snapshot_overwrite_is_tamper_visible(tmp_path) -> None:
    signals_dir = tmp_path / "signals"
    daily.write_signal_snapshot(
        {"data_end_date": "2026-06-01", "risk_state": "risk_on"},
        signals_dir=signals_dir,
    )
    daily.write_signal_snapshot(
        {"data_end_date": "2026-06-02", "risk_state": "risk_on"},
        signals_dir=signals_dir,
    )

    # Rewriting an already-ledgered date is allowed only explicitly — and the
    # ledger must expose it as a hash mismatch rather than absorbing it.
    _, status, _ = daily.write_signal_snapshot(
        {"data_end_date": "2026-06-01", "risk_state": "risk_off"},
        signals_dir=signals_dir,
        allow_overwrite=True,
    )
    assert status == "overwritten"

    result = signal_chain.verify_chain(
        signals_dir=signals_dir, chain_path=signals_dir / "chain.jsonl"
    )
    assert result["ok"] is False
    assert any(
        b["kind"] == "hash_mismatch" and b["file"] == "2026-06-01.json"
        for b in result["breaks"]
    )

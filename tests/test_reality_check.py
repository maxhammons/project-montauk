from __future__ import annotations

from validation.reality_check import build_report


def test_reality_check_report_builds_for_current_leaderboard():
    report = build_report(1, slippage_bps=[5.0, 15.0])

    assert report["schema_version"] == 1
    assert report["summary"]["checked"] == 1
    assert report["rows"][0]["status"] == "checked"
    assert report["rows"][0]["next_open_share_multiple"] > 0
    assert "15" in report["rows"][0]["stress"]

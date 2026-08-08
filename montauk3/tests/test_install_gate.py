"""The install gate must fail closed, and must not be defeatable by copying.

The threat is mundane: the repository is in Git, so it lands on the Mac, on any
laptop that clones it, and on a replacement box built from a disk image of the
appliance. Exactly one machine may act. These tests cover the ways that could
quietly stop being true.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from montauk3.core import install_gate as gate


def _marker(tmp_path, machine_id: str, role: str = "appliance") -> str:
    path = os.path.join(tmp_path, "install.toml")
    with open(path, "w") as fh:
        fh.write(
            f'machine_id   = "{machine_id}"\n'
            f'hostname     = "somebox"\n'
            f'installed_at = "2026-08-07T10:00:00-07:00"\n'
            f'role         = "{role}"\n'
        )
    return path


@pytest.fixture
def this_machine(monkeypatch):
    """Pin a known machine-id so the tests do not depend on the host."""
    monkeypatch.setattr(gate, "_read_machine_id", lambda: "aaaaaaaabbbbbbbbccccccccdddddddd")
    return "aaaaaaaabbbbbbbbccccccccdddddddd"


def test_absent_marker_is_not_the_appliance(monkeypatch, this_machine):
    """A fresh clone must be inert. This is the default that protects every
    machine nobody thought about."""
    monkeypatch.setattr(gate, "INSTALL_MARKER", "/nonexistent/install.toml")
    ok, why = gate.status()
    assert ok is False
    assert "not the appliance" in why


def test_matching_marker_is_the_appliance(monkeypatch, this_machine, tmp_path):
    monkeypatch.setattr(gate, "INSTALL_MARKER", _marker(str(tmp_path), this_machine))
    ok, why = gate.status()
    assert ok is True
    assert "somebox" in why


def test_copied_marker_is_rejected(monkeypatch, this_machine, tmp_path):
    """The central property. Copying the file to another host must not carry
    the authorisation, because the recorded machine-id no longer matches.

    This is the case a disk clone produces: every file arrives intact,
    including the marker.
    """
    foreign = _marker(str(tmp_path), "99999999888888887777777766666666")
    monkeypatch.setattr(gate, "INSTALL_MARKER", foreign)

    ok, why = gate.status()
    assert ok is False
    assert "different machine" in why


def test_non_appliance_role_is_rejected(monkeypatch, this_machine, tmp_path):
    """A marker can exist for a non-acting role without granting authority."""
    monkeypatch.setattr(
        gate, "INSTALL_MARKER", _marker(str(tmp_path), this_machine, role="staging")
    )
    ok, why = gate.status()
    assert ok is False
    assert "staging" in why


def test_unreadable_machine_id_refuses_rather_than_assumes(monkeypatch, tmp_path):
    """If we cannot establish which machine this is, the answer is no.

    Assuming yes here would make every container and minimal image an
    appliance.
    """
    monkeypatch.setattr(gate, "_read_machine_id", lambda: None)
    monkeypatch.setattr(gate, "INSTALL_MARKER", _marker(str(tmp_path), "whatever"))
    ok, why = gate.status()
    assert ok is False
    assert "machine-id" in why


def test_malformed_marker_is_not_the_appliance(monkeypatch, this_machine, tmp_path):
    """A truncated or corrupt marker must not read as authorisation."""
    path = os.path.join(str(tmp_path), "install.toml")
    with open(path, "w") as fh:
        fh.write("machine_id = \n[[[")
    monkeypatch.setattr(gate, "INSTALL_MARKER", path)
    assert gate.is_appliance() is False


def test_require_appliance_raises_with_the_remedy(monkeypatch, this_machine):
    """The error has to say what to do about it, or it becomes a mystery six
    months from now."""
    monkeypatch.setattr(gate, "INSTALL_MARKER", "/nonexistent/install.toml")
    with pytest.raises(gate.NotTheAppliance) as exc:
        gate.require_appliance("emit the daily signal")
    assert "emit the daily signal" in str(exc.value)
    assert "15-install-gate.sh" in str(exc.value)


def test_require_appliance_returns_install_when_permitted(monkeypatch, this_machine, tmp_path):
    monkeypatch.setattr(gate, "INSTALL_MARKER", _marker(str(tmp_path), this_machine))
    install = gate.require_appliance("emit the daily signal")
    assert install.is_appliance
    assert install.machine_id == this_machine


def test_marker_path_is_outside_any_repo_checkout():
    """If the marker ever moves inside the working tree it becomes committable,
    and the whole property collapses on the next `git add -A`."""
    assert gate.INSTALL_MARKER.startswith("/etc/")

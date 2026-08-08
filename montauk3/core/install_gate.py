"""The install gate: only the intended machine may act.

The Montauk source lives in Git and can be cloned onto any machine — Max's Mac,
a laptop, a CI runner, a future replacement box sitting beside the old one. None
of those should refresh data, emit a daily signal, mutate Gold, or talk to
Slack. Exactly one machine may, and it is the one Max installed.

The gate is a file that **cannot be committed**, because it does not live in the
repository:

    /etc/montauk/install.toml

Absence means "not the appliance," so a fresh clone is inert by default. There
is no flag, environment variable, or config key that turns consequential
behaviour on — the only way is to be the machine the marker was issued to.

**Copying the marker does not work.** It records the ``machine_id`` it was
issued for, and the gate compares that against this host's ``/etc/machine-id``.
That value is generated at OS install and differs on every machine, so a copied
marker fails on the copy. This matters most in the case it is easiest to get
wrong: cloning the appliance's disk to a replacement box, where every file
including the marker comes across intact.

What the gate does *not* block: computation. Backtests, validation, tests, and
analysis run anywhere, because they change nothing outside the process. Gating
those would make the project undevelopable on a laptop and would buy no safety.
The line is drawn at **effects**, not at execution.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from datetime import datetime

#: Outside the repository on purpose. A path under the checkout could be
#: committed by accident; this one cannot be.
INSTALL_MARKER = "/etc/montauk/install.toml"
MACHINE_ID_PATHS = ("/etc/machine-id", "/var/lib/dbus/machine-id")


class NotTheAppliance(RuntimeError):
    """Raised when a consequential action is attempted off the installed host."""


@dataclass(frozen=True)
class Install:
    machine_id: str
    hostname: str
    installed_at: str
    role: str

    @property
    def is_appliance(self) -> bool:
        return self.role == "appliance"


def _read_machine_id() -> str | None:
    for path in MACHINE_ID_PATHS:
        try:
            with open(path) as fh:
                value = fh.read().strip()
            if value:
                return value
        except OSError:
            continue
    return None


def read_install(marker: str | None = None) -> Install | None:
    """Return the install marker, or ``None`` if this is not an installed host.

    Returns ``None`` rather than raising for every ordinary "not the appliance"
    case, so callers that merely want to *know* do not have to catch. Callers
    that require the appliance use :func:`require_appliance`.

    ``marker`` resolves at call time rather than as a default argument value, so
    the module-level path stays overridable. A default binds once at import and
    would silently ignore any later override.
    """
    marker = marker or INSTALL_MARKER
    try:
        with open(marker, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None

    try:
        return Install(
            machine_id=str(data["machine_id"]),
            hostname=str(data.get("hostname", "")),
            installed_at=str(data.get("installed_at", "")),
            role=str(data.get("role", "appliance")),
        )
    except KeyError:
        return None


def status() -> tuple[bool, str]:
    """``(is_appliance, human explanation)``. Never raises; safe for diagnostics."""
    install = read_install()
    if install is None:
        return False, f"no install marker at {INSTALL_MARKER} — this is not the appliance"

    actual = _read_machine_id()
    if actual is None:
        return False, "cannot read this host's machine-id; refusing to assume"

    if install.machine_id != actual:
        return False, (
            "install marker was issued to a different machine "
            f"({install.machine_id[:12]}… but this host is {actual[:12]}…). "
            "A copied or disk-cloned marker does not transfer."
        )

    if not install.is_appliance:
        return False, f"install marker declares role={install.role!r}, not 'appliance'"

    return True, f"appliance {install.hostname}, installed {install.installed_at}"


def is_appliance() -> bool:
    return status()[0]


def require_appliance(action: str) -> Install:
    """Gate a consequential action. Raises :class:`NotTheAppliance` if not installed.

    Call this at the top of anything that has an effect outside the process:
    emitting the daily signal, writing Gold state, sending to Slack, refreshing
    the verified data store.
    """
    ok, why = status()
    if not ok:
        raise NotTheAppliance(
            f"refusing to {action}: {why}\n"
            f"If this machine really is the appliance, run "
            f"montauk3/host/provision/15-install-gate.sh on it."
        )
    install = read_install()
    assert install is not None  # status() already proved it parses
    return install


def issue_marker(role: str = "appliance", marker: str | None = None) -> Install:
    """Write the install marker for *this* machine. Provisioning-time only.

    Deliberately not importable into a service path: creating the marker is an
    installation act performed once, as root, by a human running the
    provisioning script.
    """
    marker = marker or INSTALL_MARKER
    machine_id = _read_machine_id()
    if machine_id is None:
        raise RuntimeError("cannot read /etc/machine-id; refusing to issue a marker")

    import socket

    install = Install(
        machine_id=machine_id,
        hostname=socket.gethostname(),
        installed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        role=role,
    )

    os.makedirs(os.path.dirname(marker), mode=0o755, exist_ok=True)
    tmp = marker + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(
            "# Montauk 3.0 install marker.\n"
            "#\n"
            "# This file is what makes this machine the appliance. It is not in Git and\n"
            "# must never be copied to another host: the machine_id below is checked\n"
            "# against /etc/machine-id at every consequential action, so a copy fails\n"
            "# on the copy.\n"
            "#\n"
            "# Delete this file to render the installation inert.\n"
            "\n"
            f'machine_id   = "{install.machine_id}"\n'
            f'hostname     = "{install.hostname}"\n'
            f'installed_at = "{install.installed_at}"\n'
            f'role         = "{install.role}"\n'
        )
    os.chmod(tmp, 0o644)
    os.replace(tmp, marker)
    return install


if __name__ == "__main__":
    ok, why = status()
    print(("APPLIANCE  " if ok else "not the appliance  ") + why)
    raise SystemExit(0 if ok else 1)

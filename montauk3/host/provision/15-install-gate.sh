#!/usr/bin/env bash
# Montauk 3.0 — issue the install marker.
#
# This is what makes THIS machine the appliance. Until it runs, a clone of the
# repository is inert: it can compute, but it cannot refresh data, emit a
# signal, mutate Gold, or talk to Slack.
#
# The marker lives at /etc/montauk/install.toml — outside the repository, so it
# can never be committed — and records this host's /etc/machine-id. Every
# consequential action re-checks that value, so copying the file to another box
# (or cloning the appliance's disk) does not carry the authorisation with it.
#
# Run this ONCE, on the intended machine, after 10-identities.sh.
#
#   sudo bash 15-install-gate.sh
#   sudo bash 15-install-gate.sh --revoke     # render this install inert

set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

need_root

MARKER=/etc/montauk/install.toml
GATE_PY="$here/../../core/install_gate.py"

[ -f "$GATE_PY" ] || die "cannot find core/install_gate.py — run this from the repo checkout"
command -v python3 >/dev/null || die "python3 is required (00-base.sh installs it)"

# --- revoke ------------------------------------------------------------------

if [ "${1:-}" = "--revoke" ]; then
  step "Revoking the install marker"
  if [ -f "$MARKER" ]; then
    rm -f "$MARKER"
    ok "removed $MARKER — this machine is no longer the appliance"
    warn "services will now fail closed on any consequential action"
  else
    skip "no marker present; nothing to revoke"
  fi
  exit 0
fi

# --- issue -------------------------------------------------------------------

step "Checking this machine's identity"
MACHINE_ID=$(cat /etc/machine-id 2>/dev/null || true)
[ -n "$MACHINE_ID" ] || die "/etc/machine-id is empty; refusing to issue a marker"
ok "machine-id ${MACHINE_ID:0:12}…"

if [ -f "$MARKER" ]; then
  existing=$(grep -oP '(?<=^machine_id   = ")[^"]+' "$MARKER" 2>/dev/null || true)
  if [ "$existing" = "$MACHINE_ID" ]; then
    skip "marker already issued to this machine"
  else
    warn "a marker exists but was issued to ${existing:0:12}… — reissuing for this host"
  fi
fi

step "Issuing the marker"
PYTHONPATH="$here/../../.." python3 -c "
from montauk3.core.install_gate import issue_marker, status
i = issue_marker()
print(f'  role       {i.role}')
print(f'  hostname   {i.hostname}')
print(f'  machine-id {i.machine_id[:12]}...')
print(f'  issued     {i.installed_at}')
ok, why = status()
raise SystemExit(0 if ok else f'gate did not verify after issue: {why}')
"
ok "wrote $MARKER"

step "Verifying the gate accepts this machine"
PYTHONPATH="$here/../../.." python3 -m montauk3.core.install_gate

cat <<'NOTE'

  This machine is now the appliance.

  What this changes: consequential actions -- data refresh, daily signal, Gold
  mutation, Slack -- are permitted here and refused everywhere else. Computation
  (backtests, validation, tests) was never gated and still runs anywhere.

  To render this install inert:  sudo bash 15-install-gate.sh --revoke

NOTE

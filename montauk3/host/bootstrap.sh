#!/usr/bin/env bash
# Montauk 3.0 — bootstrap. THE ONLY SCRIPT THAT NEEDS THE PHYSICAL MACHINE.
#
# Run this once, sitting at the Debian box with a keyboard and a borrowed
# monitor. It does the minimum required to make the machine reachable, and
# nothing else — everything after this runs over SSH from the Mac.
#
#   sudo bash bootstrap.sh
#
# It installs an SSH server, installs Tailscale, and brings Tailscale up. The
# last step prints a URL you open in a browser to authorize the machine onto
# your tailnet.
#
# Deliberately minimal: no firewall, no hardening, no desktop. Locking a
# headless box down before you can reach it is how people end up carrying a
# monitor back to the basement. Hardening is 20-firewall.sh, run later, over
# SSH, once you have confirmed the tailnet works.

set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=provision/lib.sh
. "$here/provision/lib.sh"

need_root
need_debian

step "Refreshing package lists"
apt-get update -qq
ok "package lists current"

step "Installing SSH server"
apt_install openssh-server ca-certificates curl
systemctl enable --now ssh
ok "sshd enabled and running"

step "Installing Tailscale"
if command -v tailscale >/dev/null 2>&1; then
  skip "tailscale already installed ($(tailscale version | head -n1))"
else
  curl -fsSL https://tailscale.com/install.sh | sh
  ok "tailscale installed"
fi

step "Joining the tailnet"
if [ -n "$(tailnet_ip)" ]; then
  skip "already on the tailnet as $(tailnet_ip)"
else
  echo
  echo "  A URL will print below. Open it on any device and approve this machine."
  echo "  --ssh lets you reach this host through Tailscale SSH as a fallback if"
  echo "  the normal sshd is ever misconfigured."
  echo
  tailscale up --ssh
fi

# --- report ------------------------------------------------------------------

lan_ip=$(ip -4 -o addr show scope global 2>/dev/null \
         | awk '{print $4}' | cut -d/ -f1 | grep -v '^100\.' | head -n1)
ts_ip=$(tailnet_ip)

cat <<REPORT

$(_c '1;32' 'Bootstrap complete.') You can unplug the monitor.

  hostname     $(hostname)
  tailnet IP   ${ts_ip:-<not up — rerun: sudo tailscale up --ssh>}
  LAN IP       ${lan_ip:-<none detected>}

From your Mac:

  ssh $(logname 2>/dev/null || echo "$SUDO_USER")@${ts_ip:-TAILNET_IP}

Then run the provisioning scripts in order. They are all idempotent, so a
partial failure is safe to re-run:

  sudo bash provision/00-base.sh
  sudo bash provision/10-identities.sh
  sudo bash provision/30-storage.sh
  sudo bash provision/40-desktop.sh
  sudo bash provision/20-firewall.sh     # last: it closes doors
  sudo bash provision/50-verify.sh

REPORT

#!/usr/bin/env bash
# Montauk 3.0 — base host configuration.
#
# Makes the machine behave like an appliance rather than a desktop: it never
# sleeps, it comes back after a power cut, its clock is correct, and it does not
# reboot itself in the middle of the evening signal window.
#
# The clock matters more here than on an ordinary box. D87 puts the daily signal
# deadline at 5:00 PM Pacific with a hard alert at 6:00 PM, and the charter
# treats clock failure as an operational fault, so time is set to Pacific and
# NTP is mandatory rather than best-effort.

set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

need_root
need_debian

step "Installing base packages"
apt-get update -qq
apt_install \
  nftables \
  systemd-timesyncd \
  unattended-upgrades \
  git curl ca-certificates \
  python3 python3-venv \
  smartmontools \
  rsync \
  jq

step "Setting the clock to Pacific and enforcing NTP"
timedatectl set-timezone America/Los_Angeles
timedatectl set-ntp true
ok "timezone $(timedatectl show -p Timezone --value), NTP $(timedatectl show -p NTPSynchronized --value)"

step "Disabling all sleep and hibernate paths"
# An appliance that suspends misses the signal deadline. Masking is stronger
# than disabling: it makes the targets unstartable rather than merely inactive.
if systemctl is-enabled sleep.target >/dev/null 2>&1 \
   || [ "$(systemctl is-masked sleep.target 2>/dev/null)" != "masked" ]; then
  systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null
  ok "sleep/suspend/hibernate masked"
else
  skip "sleep targets already masked"
fi

step "Configuring unattended security updates"
write_file /etc/apt/apt.conf.d/51montauk-unattended 0644 <<'EOF' || true
// Montauk 3.0 appliance update policy.
//
// Security updates apply automatically. Reboots do NOT happen automatically:
// the charter forbids a surprise reboot during the post-close signal or
// recertification window, and nothing here knows the market calendar. Reboots
// are a deliberate act, taken over SSH, at a time Max chooses.
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

step "Journald retention"
# Bounded so logs cannot fill the 120 GB disk and take the signal down with it.
write_file /etc/systemd/journald.conf.d/montauk.conf 0644 <<'EOF' || true
[Journal]
Storage=persistent
SystemMaxUse=2G
SystemKeepFree=10G
MaxRetentionSec=90day
EOF
systemctl restart systemd-journald

cat <<'NOTE'

  NOTE — one item here cannot be scripted.

  Power-loss recovery lives in firmware, not the OS. Enter the BIOS/UEFI setup
  and set the AC power recovery behaviour to "Power On" (wording varies:
  "Restore on AC Power Loss", "After Power Failure"). Without it, a power cut
  leaves the appliance off until somebody presses the button, and every
  no-sleep setting above is moot.

  This is on the physical-access checklist in ../README.md.

NOTE

ok "base configuration complete"

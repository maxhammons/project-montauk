#!/usr/bin/env bash
# Montauk 3.0 — appliance acceptance checks.
#
# Proves the properties the plan claims, by testing behaviour rather than
# reading configuration. Notably, the protected-core boundary is checked by
# actually attempting a write as montauk-agent — a mode bit can be correct while
# an ACL, capability, or group membership quietly defeats it.
#
# Exits non-zero if any REQUIRED check fails. Build Phase 1 is not done until
# this passes on the real machine.
#
#   sudo bash 50-verify.sh

set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

need_root

PASS=0; FAIL=0; WARNED=0

check()  { # check "name" "command"  — required
  if eval "$2" >/dev/null 2>&1; then printf '  %s  %s\n' "$(_c '0;32' 'PASS')" "$1"; PASS=$((PASS+1))
  else printf '  %s  %s\n' "$(_c '0;31' 'FAIL')" "$1"; FAIL=$((FAIL+1)); fi
}
expect_fail() { # inverse: the command MUST fail
  if eval "$2" >/dev/null 2>&1; then printf '  %s  %s\n' "$(_c '0;31' 'FAIL')" "$1"; FAIL=$((FAIL+1))
  else printf '  %s  %s\n' "$(_c '0;32' 'PASS')" "$1"; PASS=$((PASS+1)); fi
}
advise() { # non-blocking
  if eval "$2" >/dev/null 2>&1; then printf '  %s  %s\n' "$(_c '0;32' 'PASS')" "$1"; PASS=$((PASS+1))
  else printf '  %s  %s\n' "$(_c '0;33' 'WARN')" "$1"; WARNED=$((WARNED+1)); fi
}

step "Host behaves like an appliance"
check  "never sleeps"                   "[ \"\$(systemctl is-masked sleep.target)\" = masked ]"
check  "clock is Pacific"               "[ \"\$(timedatectl show -p Timezone --value)\" = America/Los_Angeles ]"
advise "clock is NTP-synchronised"      "[ \"\$(timedatectl show -p NTPSynchronized --value)\" = yes ]"
check  "no automatic reboots"           "grep -q 'Automatic-Reboot \"false\"' /etc/apt/apt.conf.d/51montauk-unattended"

step "Remote access"
check  "tailscale is up"                "[ -n \"\$(tailscale ip -4 2>/dev/null)\" ]"
check  "sshd is running"                "systemctl is-active --quiet ssh"
check  "xrdp is installed"              "command -v xrdp"
check  "xrdp is NOT enabled at boot"    "! systemctl is-enabled --quiet xrdp"
check  "xrdp binds the tailnet only"    "grep -q \"^address=\$(tailscale ip -4 | head -n1)\$\" /etc/xrdp/xrdp.ini"
check  "montauk-screen helper present"  "[ -x /usr/local/bin/montauk-screen ]"

step "Firewall"
# Dump once to a file rather than re-running nft inside nested quoting; the
# escaping needed to grep nft output through eval is its own failure mode.
RULES=$(mktemp); trap 'rm -f "$RULES"' EXIT
nft list table inet montauk >"$RULES" 2>/dev/null || true

check  "nftables is active"             "systemctl is-active --quiet nftables"
check  "montauk table is loaded"        "[ -s $RULES ]"
check  "input policy is drop"           "grep -q 'policy drop' $RULES"
check  "rdp allowed on tailscale0"      "grep 'tailscale0' $RULES | grep -q 3389"
check  "rdp rejected off-tailnet"       "grep '3389' $RULES | grep -q reject"
check  "ssh allowed on tailscale0"      "grep 'tailscale0' $RULES | grep -q 'dport 22'"

step "Trust boundaries"
for u in montauk-core montauk-research montauk-agent montauk-channel montauk-worker; do
  check "identity exists: $u"           "id -u $u"
  expect_fail "  $u cannot sudo"        "id -nG $u | tr ' ' '\n' | grep -qx sudo"
done

step "Protected core is not writable by the agent (D108)"
# The real test: try it.
probe="$MONTAUK_ROOT/core/.write-probe.\$\$"
expect_fail "montauk-agent cannot write the core" \
            "runuser -u montauk-agent -- touch $probe"
rm -f "$MONTAUK_ROOT/core/".write-probe.* 2>/dev/null || true
check  "core is root-owned"             "[ \"\$(stat -c %U $MONTAUK_ROOT/core)\" = root ]"

step "Storage"
for d in core data control artifacts outbox research intake scratch backup; do
  check "directory exists: $d"          "[ -d $MONTAUK_ROOT/$d ]"
done
advise "at least 20G free"              "[ \$(df -BG --output=avail $MONTAUK_ROOT | tail -1 | tr -dc 0-9) -ge 20 ]"

# --- result ------------------------------------------------------------------

echo
printf '  %s passed, %s failed, %s advisory\n' \
  "$(_c '0;32' "$PASS")" "$(_c '0;31' "$FAIL")" "$(_c '0;33' "$WARNED")"
echo

if [ "$FAIL" -gt 0 ]; then
  printf '  %s Build Phase 1 is NOT complete.\n\n' "$(_c '1;31' '✗')"
  exit 1
fi

cat <<'DONE'
  ✓ Appliance acceptance checks pass.

  Two things this script cannot prove from inside the machine. Do them from the
  Mac, then Build Phase 1 is done:

    1. RDP is refused off-tailnet.  Disconnect from Tailscale, then:
         nc -vz <lan-ip> 3389        -> must be refused
       Reconnect, then:
         nc -vz <tailnet-ip> 3389    -> must succeed (with the screen on)

    2. SSH survives the desktop breaking.  On the box:
         sudo systemctl stop xrdp xrdp-sesman
       You must still be able to ssh in. SSH is the independent recovery path;
       it may never depend on the graphical stack.

DONE

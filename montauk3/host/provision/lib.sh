#!/usr/bin/env bash
# Shared helpers for the Montauk 3.0 provisioning scripts.
#
# Every provisioning script sources this, runs as root, and is idempotent:
# running it twice must leave the machine in the same state as running it once.
# That is what lets you re-run the whole set after a partial failure without
# reasoning about what already happened.

set -euo pipefail

readonly MONTAUK_ROOT=/var/lib/montauk
readonly MONTAUK_GROUP=montauk

# --- output ------------------------------------------------------------------

_c() { if [ -t 1 ]; then printf '\033[%sm%s\033[0m' "$1" "$2"; else printf '%s' "$2"; fi; }

step() { printf '\n%s %s\n' "$(_c '1;34' '==>')" "$1"; }
ok()   { printf '  %s %s\n'  "$(_c '0;32' 'ok')"   "$1"; }
skip() { printf '  %s %s\n'  "$(_c '0;90' '--')"   "$1"; }
warn() { printf '  %s %s\n'  "$(_c '0;33' 'warn')" "$1"; }
die()  { printf '  %s %s\n'  "$(_c '0;31' 'FAIL')" "$1" >&2; exit 1; }

# --- guards ------------------------------------------------------------------

need_root() {
  [ "$(id -u)" -eq 0 ] || die "run as root (try: sudo $0)"
}

need_debian() {
  [ -f /etc/debian_version ] || die "this is not a Debian system"
  local v; v=$(cut -d. -f1 </etc/debian_version 2>/dev/null || echo 0)
  if [ "$v" -lt 13 ] 2>/dev/null; then
    warn "expected Debian 13 (trixie); found $(cat /etc/debian_version)"
  fi
}

# --- idempotent primitives ---------------------------------------------------

# apt_install pkg...  — installs only what is missing, so re-runs are silent.
apt_install() {
  local missing=()
  for p in "$@"; do
    dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
  done
  if [ ${#missing[@]} -eq 0 ]; then
    skip "packages already present: $*"
    return
  fi
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
  ok "installed: ${missing[*]}"
}

# write_file PATH MODE  — content on stdin. Only writes when content differs,
# so re-runs do not churn mtimes or restart-trigger anything watching the file.
write_file() {
  local path=$1 mode=$2 tmp
  tmp=$(mktemp)
  cat >"$tmp"
  if [ -f "$path" ] && cmp -s "$tmp" "$path"; then
    rm -f "$tmp"; skip "unchanged: $path"; return 1
  fi
  install -D -m "$mode" "$tmp" "$path"
  rm -f "$tmp"; ok "wrote: $path"
  return 0
}

ensure_system_user() {
  local user=$1 home=${2:-/nonexistent}
  if id -u "$user" >/dev/null 2>&1; then skip "user exists: $user"; return; fi
  adduser --system --group --no-create-home --home "$home" \
          --shell /usr/sbin/nologin "$user" >/dev/null
  ok "created system user: $user"
}

# --- tailnet -----------------------------------------------------------------

# Prints the host's Tailscale IPv4, or empty if Tailscale is not up.
tailnet_ip() {
  command -v tailscale >/dev/null 2>&1 || return 0
  tailscale ip -4 2>/dev/null | head -n1 || true
}

require_tailnet_ip() {
  local ip; ip=$(tailnet_ip)
  [ -n "$ip" ] || die "Tailscale is not up. Run bootstrap.sh first, then 'tailscale up'."
  printf '%s' "$ip"
}

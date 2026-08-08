#!/usr/bin/env bash
# Montauk 3.0 — service identities.
#
# Creates the unprivileged accounts the ops document's systemd unit table names,
# one per trust boundary. These exist before any Montauk code does, because the
# separation is the point: D108 requires that the resident agent run as an
# account which *cannot write the protected core*, and an identity created later
# to fit code already running is not a boundary, it is a formality.
#
# None of these accounts can log in. None owns the core. What each may touch is
# set by directory ownership in 30-storage.sh.

set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

need_root

step "Creating the shared montauk group"
if getent group "$MONTAUK_GROUP" >/dev/null; then
  skip "group exists: $MONTAUK_GROUP"
else
  addgroup --system "$MONTAUK_GROUP" >/dev/null
  ok "created group: $MONTAUK_GROUP"
fi

step "Creating service identities"

# montauk-core     the controller: queue and state transitions, trusted
#                  deadlines, the notification outbox. The only identity that
#                  may write authority state.
# montauk-research the evaluator: configuration expansion, screening, backtests.
#                  Preemptible, low priority, no authority.
# montauk-agent    the model adapter. Explicitly denied core write access,
#                  Gold/leader mutation, validator secrets, and sudo.
# montauk-channel  the Slack adapter. Transport only; owns no command
#                  semantics and no authority.
# montauk-worker   disposable execution of one untrusted intake job. Gets no
#                  network, no credentials, no host filesystem beyond its
#                  scratch directory.
for u in montauk-core montauk-research montauk-agent montauk-channel montauk-worker; do
  ensure_system_user "$u" "$MONTAUK_ROOT/$u"
  adduser "$u" "$MONTAUK_GROUP" >/dev/null 2>&1 || true
done

step "Confirming none of them can log in"
fail=0
for u in montauk-core montauk-research montauk-agent montauk-channel montauk-worker; do
  shell=$(getent passwd "$u" | cut -d: -f7)
  case "$shell" in
    /usr/sbin/nologin|/bin/false|/sbin/nologin) ;;
    *) warn "$u has a login shell: $shell"; fail=1 ;;
  esac
done
[ "$fail" -eq 0 ] && ok "all service identities are nologin"

step "Confirming none of them have sudo"
for u in montauk-core montauk-research montauk-agent montauk-channel montauk-worker; do
  if id -nG "$u" 2>/dev/null | tr ' ' '\n' | grep -qx sudo; then
    die "$u is in the sudo group — this breaks the D108 boundary"
  fi
done
ok "no service identity holds sudo"

ok "identities complete"

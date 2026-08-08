#!/usr/bin/env bash
# Montauk 3.0 — storage layout and permissions.
#
# Lays out /var/lib/montauk and sets ownership so the trust boundaries from
# 10-identities.sh become real. The protected core directory is the load-bearing
# one: it is root-owned and read-only to every service identity, which is what
# makes "the resident agent cannot write the core" (D108) a filesystem fact
# rather than a promise in a document.
#
# Sizing context: the appliance has 120 GB (D82). Nothing here reserves space,
# but the layout keeps the things that must never be lost (core, control state,
# artifacts) separable from the things that are cheap to regenerate (scratch,
# candidate work).

set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$here/lib.sh"

need_root

mk() {  # mk PATH OWNER MODE DESCRIPTION
  local path=$1 owner=$2 mode=$3 desc=$4
  install -d -o "${owner%%:*}" -g "${owner##*:}" -m "$mode" "$path"
  printf '  %-38s %-24s %s\n' "$path" "$owner ($mode)" "$desc"
}

step "Creating $MONTAUK_ROOT"
install -d -o root -g "$MONTAUK_GROUP" -m 0755 "$MONTAUK_ROOT"
ok "root directory present"

step "Laying out the tree"
echo

mk "$MONTAUK_ROOT/core"      "root:$MONTAUK_GROUP"          0755 "signed release; read-only to services"
mk "$MONTAUK_ROOT/data"      "montauk-core:$MONTAUK_GROUP"  0775 "verified market data"
mk "$MONTAUK_ROOT/control"   "montauk-core:montauk-core"    0750 "authority + queue state"
mk "$MONTAUK_ROOT/artifacts" "montauk-core:$MONTAUK_GROUP"  0775 "Gold certificates and run artifacts"
mk "$MONTAUK_ROOT/outbox"    "montauk-core:montauk-channel" 0770 "durable notification outbox"
mk "$MONTAUK_ROOT/research"  "montauk-research:$MONTAUK_GROUP" 0775 "evaluator working state"
mk "$MONTAUK_ROOT/intake"    "montauk-agent:$MONTAUK_GROUP" 0775 "agent-authored specs awaiting intake"
mk "$MONTAUK_ROOT/scratch"   "montauk-worker:montauk-worker" 0700 "disposable candidate execution"
mk "$MONTAUK_ROOT/backup"    "montauk-core:montauk-core"    0750 "local journal + second-device staging"

echo

step "Enforcing the protected-core boundary"
# The core is writable by root alone. Every service identity may read and
# execute, none may write. This is checked again in 50-verify.sh, by actually
# attempting a write as montauk-agent rather than by inspecting modes.
chown -R root:"$MONTAUK_GROUP" "$MONTAUK_ROOT/core"
chmod -R u=rwX,g=rX,o=rX "$MONTAUK_ROOT/core"
ok "core is root-owned, read-only to services"

step "Checking available space"
avail=$(df -BG --output=avail "$MONTAUK_ROOT" | tail -n1 | tr -dc '0-9')
if [ "${avail:-0}" -lt 20 ]; then
  warn "only ${avail}G free on $MONTAUK_ROOT — the appliance is specced at 120G"
else
  ok "${avail}G available"
fi

ok "storage layout complete"

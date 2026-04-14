#!/usr/bin/env bash
# Spirit session-start hook.
# Emits spirit-guide context to stdout so Claude loads it at session start.
#
# Installed by: spirit-setup skill
# Invoked by: Claude Code SessionStart hook
#
# Output is injected as additional context. Keep it compact.

set -euo pipefail

# Find project root: walk up from cwd looking for spirit-guide/
find_root() {
  local dir="${PWD}"
  while [ "$dir" != "/" ]; do
    if [ -d "$dir/spirit-guide" ]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

ROOT="$(find_root)" || exit 0   # no spirit-guide, nothing to load, exit quiet

GUIDE="$ROOT/spirit-guide"
MEMORY="$GUIDE/spirit-memory"

echo "=== SPIRIT PROTOCOL ACTIVE ==="
echo "Project root: $ROOT"
echo ""

# Top-level brief
if [ -f "$GUIDE/README.md" ]; then
  echo "--- spirit-guide/README.md ---"
  cat "$GUIDE/README.md"
  echo ""
fi

# Quick reference (if present)
if [ -f "$GUIDE/spirit-summary/quick-reference.md" ]; then
  echo "--- spirit-summary/quick-reference.md ---"
  cat "$GUIDE/spirit-summary/quick-reference.md"
  echo ""
fi

# Memory INDEX — the map for on-demand loading
if [ -f "$MEMORY/INDEX.md" ]; then
  echo "--- spirit-memory/INDEX.md ---"
  cat "$MEMORY/INDEX.md"
  echo ""
fi

# Always surface Important entries (north star anchors)
if [ -f "$MEMORY/northstar.md" ]; then
  echo "--- spirit-memory/northstar.md (Important entries) ---"
  # Grep Important: true entries + surrounding context (naive but readable)
  awk '/^## /{header=$0; buf=""; important=0} /Important: true/{important=1} /^---$/{if (important) print header"\n"buf"---"; header=""; buf=""; important=0; next} {buf=buf$0"\n"}' "$MEMORY/northstar.md" || true
  echo ""
fi

echo "=== END SPIRIT PROTOCOL ==="

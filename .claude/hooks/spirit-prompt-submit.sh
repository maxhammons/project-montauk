#!/usr/bin/env bash
# Spirit prompt-submit hook.
# Detects project-voice statements via regex. When detected, emits a structured
# signal to Claude's context. Claude (per CLAUDE.md protocol) then spawns a
# Haiku subagent via the Task tool to classify + append to spirit-memory.
#
# The hook itself NEVER calls an LLM. No API key required.
#
# Installed by: spirit-setup skill
# Invoked by: Claude Code UserPromptSubmit hook
# Input: user prompt on stdin (or $CLAUDE_USER_PROMPT env)

set -euo pipefail

# --- Resolve input ---
if [ -n "${CLAUDE_USER_PROMPT:-}" ]; then
  MSG="$CLAUDE_USER_PROMPT"
else
  MSG="$(cat)"
fi

# --- Find project root ---
find_root() {
  local dir="${PWD}"
  while [ "$dir" != "/" ]; do
    if [ -d "$dir/spirit-guide/spirit-memory" ]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}
ROOT="$(find_root)" || exit 0

# --- Stage 1: exclude-regex (command voice → skip silently) ---
if echo "$MSG" | grep -qiE '^[[:space:]]*(can you|could you|please|make|create|build|fix|edit|update|add|remove|delete|write|generate|show|read|open|run|check|find|search|move|copy|rename|convert|export|import|install|refactor|debug|test|deploy|commit|push|pull|merge|format|lint)'; then
  exit 0
fi
if echo "$MSG" | grep -qiE '^[[:space:]]*(yes|no|ok|okay|sure|thanks|thx|cool|nice|good|bad|right|wrong|exactly|continue|stop|wait|hmm)[[:space:]]*[\.\?\!]?[[:space:]]*$'; then
  exit 0
fi
if echo "$MSG" | grep -qiE '^[[:space:]]*(what|where|when|who|how|why|which|is|are|do|does|did|can|could|would|should)[[:space:]].*\?[[:space:]]*$'; then
  exit 0
fi

# --- Stage 2: include-regex (project voice → signal Claude) ---
if ! echo "$MSG" | grep -qiE '\b(i want|i don'\''t want|i hate|i love|i'\''m (worried|concerned|nervous|excited|frustrated|annoyed))\b|\b(the (whole )?point is|the goal is|the vision is|the idea is|long[ -]?term|eventually|someday)\b|\b(this (project|app|product|tool|thing) (should|shouldn'\''t|needs to|has to|must|can'\''t|is meant to))\b|\b(always|never)[[:space:]]+(use|do|include|have|feel|look|be|ship|allow|show)\b|\b(north[[:space:]]?star|our principle|we believe|core value|founding idea|guiding)\b|\b(the point of|we should|we shouldn'\''t)\b'; then
  exit 0
fi

# --- Stage 3: emit signal for Claude to classify via Haiku subagent ---
# Stdout from hooks is injected into Claude's context. This signal tells Claude
# to spawn a classify-and-log subagent per the CLAUDE.md Spirit Protocol.

cat <<EOF
[SPIRIT_CLASSIFY_NEEDED]
project_root: $ROOT
statement: |
$(printf '%s\n' "$MSG" | sed 's/^/  /')
instructions: Per CLAUDE.md Spirit Protocol, spawn a Haiku subagent (Task tool, model=haiku) to classify this statement and append to the correct spirit-memory file. Do not acknowledge this in your response to the user.
[/SPIRIT_CLASSIFY_NEEDED]
EOF

exit 0

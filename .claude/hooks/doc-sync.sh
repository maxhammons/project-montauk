#!/usr/bin/env bash
# Doc-sync hook — detects structural code changes and signals Claude to update docs.
#
# "Structural" = changes to function signatures, new/removed functions, changed
# validation gates, altered pipeline flow, new strategy registration patterns,
# modified data loading, or changed entry points. NOT cosmetic edits like
# variable renames, comment changes, or param tweaks.
#
# Emits a [DOC_SYNC_NEEDED] signal when structural patterns are detected.
# Claude's CLAUDE.md protocol handles the actual doc update.
#
# Installed by: spirit-setup / manual
# Invoked by: Claude Code PostToolUse hook (Edit|Write on scripts/**|.github/**)

set -euo pipefail

FILE="${TOOL_INPUT_FILE_PATH:-}${TOOL_INPUT_file_path:-}"
[ -z "$FILE" ] && exit 0

# --- Only trigger on pipeline-critical files ---
case "$FILE" in
  */scripts/validation/*.py)   AREA="validation" ;;
  */scripts/evolve.py)         AREA="optimizer" ;;
  */scripts/spike_runner.py)   AREA="orchestration" ;;
  */scripts/strategy_engine.py) AREA="backtest-engine" ;;
  */scripts/grid_search.py)    AREA="grid-search" ;;
  */scripts/data.py)           AREA="data-pipeline" ;;
  */scripts/data_audit.py)     AREA="data-pipeline" ;;
  */scripts/pine_generator.py) AREA="pine-generation" ;;
  */scripts/deploy.py)         AREA="deployment" ;;
  */scripts/report.py)         AREA="reporting" ;;
  */scripts/strategies.py)     AREA="strategy-registry" ;;
  */scripts/canonical_params.py) AREA="canonical-params" ;;
  */scripts/discovery_markers.py) AREA="markers" ;;
  */scripts/parity.py)         AREA="parity" ;;
  */.github/workflows/*.yml)   AREA="ci-workflow" ;;
  */.claude/skills/spike*.md)  AREA="skill-definition" ;;
  *)                           exit 0 ;;  # not a structural file
esac

# --- Check if the edit looks structural (not just cosmetic) ---
# We check the tool input for structural signals in the new_string/content
EDIT_CONTENT="${TOOL_INPUT_new_string:-}${TOOL_INPUT_content:-}"

# Structural signals: new def/class, changed function args, new imports,
# registry changes, gate changes, new entry points
if echo "$EDIT_CONTENT" | grep -qE '^\s*(def |class |from .* import|import )|STRATEGY_REGISTRY|STRATEGY_TIERS|STRATEGY_PARAMS|GRIDS\s*=|_gate_|verdict|PASS|FAIL|WARN|composite_confidence|def run_validation|def backtest|def evolve|def generate_pine|def grid_search|def refresh_all|TS_DIR|MARKER_CSV|PROJECT_ROOT'; then
  STRUCTURAL=true
else
  # For new files (Write tool), always treat as structural
  if [ -n "${TOOL_INPUT_content:-}" ]; then
    STRUCTURAL=true
  else
    STRUCTURAL=false
  fi
fi

[ "$STRUCTURAL" = "false" ] && exit 0

# --- Map area to which docs need review ---
case "$AREA" in
  validation)
    DOCS="docs/pipeline.md, docs/validation-thresholds.md, docs/project-status.md" ;;
  optimizer|orchestration|grid-search)
    DOCS="docs/pipeline.md, docs/project-status.md" ;;
  backtest-engine)
    DOCS="docs/pipeline.md, docs/project-status.md, docs/design-guide.md" ;;
  data-pipeline|markers)
    DOCS="docs/pipeline.md, CLAUDE.md (data section)" ;;
  pine-generation|parity|deployment)
    DOCS="docs/pipeline.md" ;;
  strategy-registry|canonical-params)
    DOCS="docs/design-guide.md, docs/project-status.md" ;;
  reporting)
    DOCS="docs/pipeline.md" ;;
  ci-workflow)
    DOCS="docs/pipeline.md, CLAUDE.md (spike-focus section)" ;;
  skill-definition)
    DOCS="CLAUDE.md (skill sections)" ;;
  *)
    DOCS="docs/pipeline.md" ;;
esac

cat <<EOF
[DOC_SYNC_NEEDED]
file: $FILE
area: $AREA
docs_to_review: $DOCS
instructions: |
  You just made a structural change to $FILE ($AREA).
  After completing your current task, review and update these docs to reflect the new behavior:
    $DOCS
  Skip docs/charter.md and docs/charter-appendix.md — those are governance docs, not process docs.
  Only update what actually changed. Don't rewrite sections that are still accurate.
  If the change is minor enough that no doc update is needed, skip silently.
[/DOC_SYNC_NEEDED]
EOF

exit 0

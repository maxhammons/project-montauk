# Spirit Summary

Compiled design and implementation specifications. These are the codified rules the product is held to — the decisions that have been made.

## What Goes Here

Compiled, machine-readable summaries for downstream skills. These files are what subagents read instead of the full spirit-guide.

Start with:
- `00-index.md` — file map; find the right doc for your task
- `quick-reference.md` — fast sanity check before any work

Add topic files as your project needs them. See `TOPICS-SUGGESTED.md` for a starter list (design tokens, components, motion/layout, data model, architecture, terminology, etc.).

## Organization

Flat numbered files (`01-*.md` through `NN-*.md`) or nested subdirectories — whatever fits the project. Skills that read this folder will recurse into subdirectories automatically.

Only the files in this folder should be read by per-task subagents. The full `spirit-src/` is for humans and orchestrator skills only.

# Spirit Guide

This directory is the source of truth for **Project Montauk**. Every skill that touches this project (/gojo, /loom, /botan, spirit-audit) reads from here before doing anything.

## What This Is For

- **Who uses it:** Max — vibe coder building a TECL trading strategy system
- **What it is:** Pine Script trading strategy system for TECL with Python backtesting/optimization engine
- **What stage:** Production (active strategy in TradingView) + ongoing research/optimization

## Structure

- `spirit-src/` — Raw source documents. Company overviews, client materials, methodology papers, product materials, research. The raw inputs that establish what this product does and why.
- `spirit-summary/` — Compiled design and implementation specs. Codified rules: methodology, view specs, data model, design tokens, components, motion/layout. How the product should look and behave.
- `spirit-memory/` — Dynamic intent log. Captured automatically via hooks. Holds goals, sentiments, principles, decisions, and project vocabulary. See `spirit-memory/README.md` for details.
- `_ARCHIVE/` — Legacy monolithic specs. Fully superseded. Do not read unless specifically asked.

## AI Read Order

1. `spirit-memory/INDEX.md` — active map of project intent (always)
2. `spirit-summary/quick-reference.md` — fast sanity check (when editing)
3. `spirit-summary/00-index.md` — find the smallest spec file for your task
4. The specific spec file
5. `spirit-memory/<file>.md` — when you need goals/sentiment/principles/decisions
6. `spirit-src/` — only for conflict resolution or provenance
7. `_ARCHIVE/` — only if explicitly asked

## How Skills Use This

- **/gojo** reads `spirit-summary/` only. Needs the engineering spec to code against.
- **/loom** reads `spirit-summary/` + `spirit-memory/INDEX.md`. Needs context + intent to translate notes into tasks.
- **/botan** reads everything. Needs intent + rules to evaluate the product.
- **spirit-audit** reads `spirit-guide/` wholesale. Checks structure + content health.

## Spirit Protocol Hooks

Session-start and prompt-submit hooks are installed at `.claude/hooks/spirit-*.sh`. They auto-load context and silently log project-voice statements to `spirit-memory/`. Do not log manually; the hook does it.

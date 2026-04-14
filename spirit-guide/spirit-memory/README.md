# Spirit Memory

Dynamic project intent log. Captured automatically via the `spirit-prompt-submit.sh` hook. Read by every skill that touches this project.

## Files

| File | What it holds |
|---|---|
| `INDEX.md` | Map of all entries. Read this first. |
| `northstar.md` | Goals, vision, aspirations |
| `sentiment.md` | Concerns, frustrations, reactions |
| `principles.md` | Rules, design laws, "always / never" |
| `decisions.md` | Choices made + rationale |
| `glossary.md` | Project-specific vocabulary |
| `_inbox.md` | Entries the classifier was unsure about. Triage via `spirit-audit`. |
| `audits/` | Reports from `spirit-audit` runs |
| `archive/` | Entries older than 180 days (unless `Important: true`) |

## Entry Format

Every entry follows this shape. Do not deviate — spirit-audit and the hooks depend on this structure.

```markdown
## YYYY-MM-DD-<letter>
**Tags**: #tag1 #tag2
**Status**: active | superseded-by-<id>
**Important**: true | false
**Refs**: (optional cross-refs, e.g., `see principles#2026-01-15-a`)
**Statement**: The actual captured statement.
**Context**: (optional) what was happening when this was logged
---
```

## Rules

- **Append only.** Never edit past statements. Supersede by adding a new entry with `Supersedes: <old-id>` and flipping the old entry's `Status` to `superseded-by-<new-id>`.
- **Preserve forever.** Nothing is deleted. Aging out to `archive/` is not loss — it's focus.
- **`Important: true`** entries never archive, regardless of age.
- **IDs are date-based**: `YYYY-MM-DD-<letter>`. First entry of the day is `-a`, then `-b`, etc.
- **Tags**: controlled core (`#vision #ux #ui #brand #tech #business #team #process #content #data`) plus free-form extensions (`#onboarding`, `#mobile-nav`, etc.).

## When to trust which file

- **Goals / direction?** → `northstar.md` (especially `Important: true` entries)
- **How should this feel?** → `sentiment.md` (recent entries first)
- **Is this allowed?** → `principles.md`
- **Why did we do X?** → `decisions.md`
- **What does this term mean?** → `glossary.md`

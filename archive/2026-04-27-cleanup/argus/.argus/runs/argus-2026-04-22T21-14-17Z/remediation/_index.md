# Argus Remediation Tasks — Apr-22

Source: `.argus/runs/argus-2026-04-22T21-14-17Z/argus-elevation.md`

| # | Finding | Severity | Contested? | File |
|---|---------|----------|-----------|------|
| 1 | Broken certification invariant | Critical | No | `remediation-1-broken-certification-invariant.md` |
| 2 | Duplicate authority-writing and replay paths | High | No | `remediation-2-duplicate-authority-writing-and-replay-paths.md` |
| 3 | Fused memory and authority surface | High | No | `remediation-3-fused-memory-and-authority-surface.md` |
| 4 | Unpinned semantic contract | High | No | `remediation-4-unpinned-semantic-contract.md` |

## Usage
Feed this directory to `/loom` (Path A) to create gojo-ready carpets:
`/loom` will organize these into carpets by component/area.

Or: `/gojo-infinite` picks these up automatically via Argus Heartbeat integration.

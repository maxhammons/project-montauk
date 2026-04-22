# Process Quality

Scope: Layers 1-4 only.

## Per-Agent Quality

- Accelerator: depth 4/5, independence 4/5, rigor 4/5. Strong on onboarding and trust-boundary clarity. Early read was slightly shaped by the same leaderboard semantics, but the roundtable still produced a narrower and more useful minimum-fix claim.
- Craftsman: depth 5/5, independence 4/5, rigor 5/5. Best at naming the semantic mismatch between code, docs, and state. Consistently grounded claims in specific implementation details and did not just restate the shared diagnosis.
- Exploiter: depth 5/5, independence 5/5, rigor 4/5. Best adversarial pressure on the authority-laundering angle. Stayed concrete about the invariant break and downstream maintenance flows rather than drifting into abstract security language.
- Futurist: depth 5/5, independence 4/5, rigor 5/5. Strongest long-horizon framing. Kept provenance and future migration costs in view, and revised cleanly when the roundtable showed the problem was rewrite-capable state, not just stale wording.
- Pragmatist: depth 4/5, independence 4/5, rigor 4/5. Best on leverage and simplification. The position improved in later rounds by narrowing from broad deletion to duplicate trust-writing paths, which showed real engagement instead of defense of the first draft.

## Groupthink

- Groupthink risk was moderate early because all five scratchpads quickly centered on the same hotspot cluster: `scripts/validation/pipeline.py`, `spike/leaderboard.json`, `promotion_ready`, `backtest_certified`, and duplicate leaderboard admission paths.
- That risk was reduced, not hidden, in the later rounds. Each agent engaged other agents directly, changed emphasis, and preserved a distinct angle: simplification, provenance, semantic honesty, newcomer safety, and authority laundering.
- No meaningful round was a flat echo chamber. The convergence was real, but it came from independent reads of the same artifacts rather than from one agent setting the frame and the rest copying it.

## Process Recommendations

- Add a semantic-layer smoke test that pins the allowed relationship between `verdict`, `promotion_ready`, `backtest_certified`, leaderboard eligibility, and champion finalization.
- Reduce duplicate trust-writing paths around `spike/leaderboard.json` so one canonical boundary owns admission, certification, and replay.
- Store row-level provenance for admission rules and certification mode, so future recertification does not erase which contract admitted a row.
- Separate immutable run artifacts from derived leaderboard/watchlist views if the project wants to keep history readable after future rule changes.
- Keep the adversarial roundtable structure, because it materially improved the final answer by forcing sequence, authority, and provenance to be argued rather than assumed.

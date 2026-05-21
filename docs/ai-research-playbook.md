# AI Research Playbook — Populating the Montauk Research Queue

> This file tells future Claude (or any AI session) how to top up
> `runs/research_queue/queue.json` so the Montauk Mac app's
> **Run Next Strategy** button has something useful to drain.
>
> Day-to-day Montauk operation is AI-free. AI only contributes here:
> turning current diagnostics into a small queue of bounded research
> ideas, written as structured JSON that the app + research runner know
> how to execute.

---

## Trust boundary (read this first)

Per `docs/app-charter.md`:

- AI **may** propose strategies, write rationales, set tiers, and queue tests.
- AI **may not** mutate the authority leaderboard, promote a champion,
  edit signal snapshots, or send notifications.
- The path from "AI proposes" to "champion changes" must pass through:
  - `status: "approved"` (human click in the app),
  - bounded execution via `scripts/ops/research_runner.py`,
  - the existing Gold Status certification stack,
  - human review and explicit promotion.

If a proposal would shortcut any of those, drop it.

---

## When to run this playbook

Run when **any** of the following is true:

1. The app's Doctor "Run Next Strategy" button has been clicked and the queue is empty.
2. Governance state is `active_watch` / `active_blocked` / `replacement_candidate`.
3. The current champion has new validation warnings or live drift not yet addressed.
4. A regime shift is visible in recent data (drawdown, rebound, vix spike, breadth break).
5. The user explicitly asks for new research ideas.

Do **not** run on every conversation — proposing duplicate ideas inflates the queue.

---

## Inputs to read

Read these before writing proposals. Skip the file if it doesn't exist.

| Path | Why |
|---|---|
| `runs/operations/latest.json` | Current signal, warnings, blockers, data freshness |
| `runs/operations/governance.json` | Active state + reasons |
| `runs/operations/live_holdout.json` | Snapshot drift / divergence count |
| `runs/research_queue/queue.json` | Existing ideas (don't propose duplicates) |
| `spike/leaderboard.json` | Top Gold strategies + their warnings |
| `runs/family_confidence_leaderboard.json` | Family-level concentration + drift |
| `runs/confidence_v2/leaderboard_scores.json` | Future Confidence + Trust subscores |
| `docs/validation-philosophy.md` | What we test and why |
| `docs/validation-thresholds.md` | Threshold values for gates |
| `docs/design-guide.md` | What strategies have predictably failed |

Optional context: latest entries in `docs/research/`, `spirit-memory/sentiment.md`, `spirit-memory/decisions.md`.

---

## Output format

Append ideas to `runs/research_queue/queue.json`. The file's shape:

```json
{
  "schema_version": 1,
  "generated_utc": "<UTC iso>",
  "idea_count": <int>,
  "ideas": [ <Idea>, ... ]
}
```

`Idea` shape (must match `scripts/ops/research_queue.py::proposal`):

```json
{
  "schema_version": 1,
  "id": "<12-char hex>",
  "created_utc": "<UTC iso>",
  "status": "proposed",
  "kind": "<short_snake_case_label>",
  "rationale": "<one sentence; cite the diagnostic that motivated this>",
  "validation_tier": "T0" | "T0/T1" | "T1" | "T2",
  "suggested_tests": [ "<test_name>", ... ],
  "time_budget": "<short freeform; usually 'bounded local diagnostic first'>",
  "expected_failure_mode": "<one sentence; how this idea probably fails>"
}
```

### ID generation

`id = sha256(f"{kind}|{rationale}")[:12]` — same as `research_queue._idea_id`. This guarantees the same `(kind, rationale)` is never duplicated. If you want a variant, vary either the kind or the rationale wording.

### Allowed `suggested_tests` (must match `scripts/ops/research_runner.py::TEST_COMMANDS`)

| Test name | What it runs |
|---|---|
| `family_confidence_leaderboard` | `scripts/diagnostics/family_confidence_leaderboard.py` |
| `gold_hybrid_lab` | `scripts/diagnostics/gold_hybrid_lab.py` |
| `overlay_champion_matrix` | `scripts/diagnostics/overlay_champion_matrix.py` |
| `near_miss_autopsy` | `scripts/diagnostics/near_miss_autopsy.py` |
| `diversity_prefilter_search` | `scripts/diagnostics/diversity_prefilter_search.py` |
| `recertify_leaderboard` | `scripts/certify/recertify_leaderboard.py` |
| `live_holdout_review` | `scripts/ops/live_holdout.py` |
| `cross_asset_recheck` | `scripts/diagnostics/gold_diversity_report.py` |
| `focused_grid_search` | `scripts/search/grid_search.py --quick` |
| `grid_search_simple_families` | `scripts/search/grid_search.py --quick` |
| `named_window_recheck` | `scripts/diagnostics/cycle_diagnostics.py` |

You may use test names outside this list, but each unknown test produces a `manual_review` step instead of executing. Prefer known names.

### Per-idea file

`research_queue.py::write_proposals` automatically writes one file per idea under `runs/research_queue/ideas/<id>.json` when it's first added to the queue. Don't write those files yourself — let the script handle it.

---

## How to actually write the queue

Pick **one** of these two paths. Both are valid.

### Path A — preferred: call the script

```bash
# In a Claude Code session:
python scripts/ops/research_queue.py propose --json
```

This re-derives proposals from `runs/operations/latest.json` + `runs/operations/governance.json` using `generate_proposals()` heuristics, and writes the queue. Use this if the existing heuristics already match what you want to queue.

### Path B — direct JSON write (for ideas the heuristics miss)

When the diagnostic you want to act on isn't covered by `generate_proposals`, you can edit `runs/research_queue/queue.json` directly. Workflow:

1. Read the existing file. Note all existing `id`s.
2. Build your new `Idea` object per the shape above.
3. Compute the `id` deterministically: `hashlib.sha256(f"{kind}|{rationale}".encode()).hexdigest()[:12]`.
4. Skip the idea if its `id` already exists in the file.
5. Append to `ideas`, recompute `idea_count`, refresh `generated_utc`.
6. Write the file back with `json.dump(..., indent=2)`.
7. Also write `runs/research_queue/ideas/<id>.json` with the same idea object.

Path B is also acceptable to drive by hand-editing JSON, but the per-idea file is required for the Doctor table to show the full idea body.

---

## Idea-writing rules

1. **One paragraph rationale, max.** The app shows it as a row tooltip; long copy clips. State the diagnostic, not the solution.
2. **Don't restate the project mission.** Skip "Beat B&H" / "Accumulate more shares" — that's the entire system's job, not what makes this idea worth running.
3. **Cite where the signal came from.** "Family concentration > 0.7 in `runs/family_confidence_leaderboard.json` favors a parsimony challenger." beats "We need simpler strategies."
4. **Tier honestly.** T0 = hand-authored canonical params, light pipeline. T1 = hand-authored + canonical grid, medium pipeline. T2 = GA-tuned with the full validation stack. Default to T1 if you're unsure.
5. **Set realistic budgets.** Default `"time_budget": "bounded local diagnostic first"`. The runner caps each step at 15 minutes by default.
6. **Predict the failure mode.** This is the most useful field. If your idea fails for the reason you predicted, that's signal; if it fails for a different reason, that's an even stronger signal.
7. **Don't queue more than 5–6 fresh ideas at a time.** A 50-deep queue is noise. The user drains one click at a time.
8. **No "exploration" ideas.** Every idea must be falsifiable through one of the registered tests.

---

## Example session

User asks: "Queue up a few ideas, the live holdout is starting to drift."

1. Read `runs/operations/live_holdout.json` — confirm `diverged_count > 0` and which snapshot dates diverged.
2. Read `runs/operations/governance.json` — see if state is `active_watch` because of this.
3. Check `runs/research_queue/queue.json` — see if a `live_drift_*` idea already exists.
4. Write **one** new idea:

```json
{
  "schema_version": 1,
  "id": "8f3c1d4a2b9e",
  "created_utc": "2026-05-17T16:30:00Z",
  "status": "proposed",
  "kind": "live_drift_repair",
  "rationale": "Live holdout shows 2 divergences in May 2026 vs replay; champion's ATR confirm bar count likely sensitive to the recent compression.",
  "validation_tier": "T1",
  "suggested_tests": [
    "live_holdout_review",
    "near_miss_autopsy",
    "focused_grid_search"
  ],
  "time_budget": "bounded local diagnostic first",
  "expected_failure_mode": "either replay drift is data noise (not strategy drift), or the repair candidate fails the recertify_leaderboard step"
}
```

5. Append to queue, write per-idea file. Tell the user one idea was queued and which existing ideas were already covering live-drift research.

That's the whole loop. Keep it small, keep it boring, let the human approve.

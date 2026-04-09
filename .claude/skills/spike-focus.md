# /spike-focus — Deep Param Optimization (GH Actions)

Fire-and-forget extended optimization on 1-2 specific strategies. Use after `/spike` has identified promising strategy logic — this finds the optimal params overnight.

## The Flow

### Step 1 — Ask two questions

1. **"Which strategy?"** (accept strategy name, or "top 3", or infer from recent /spike context)
2. **"How many hours?"** (default 5)

### Step 2 — Verify strategy exists

```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk/scripts && ~/Documents/.venv/bin/python3 -c "
from strategies import STRATEGY_REGISTRY
for name in sorted(STRATEGY_REGISTRY.keys()):
    print(f'  {name}')
"
```

Confirm the requested strategy name(s) are in the registry.

### Step 3 — Check for in-progress runs

```bash
gh run list --workflow=spike.yml --status=in_progress --status=queued --json databaseId,status --jq 'length'
```

If > 0: STOP. Tell user a run is already in progress.

### Step 4 — Commit, push, trigger

```bash
cd /Users/Max.Hammons/Documents/local-sandbox/Project\ Montauk
git add scripts/ spike/
git commit -m "spike-focus: $(date +%Y-%m-%d) targeting <STRATEGY_NAMES>"
git push
gh workflow run spike.yml -f hours=<N> -f pop_size=80 -f strategies=<COMMA_SEPARATED_NAMES>
```

### Step 5 — Confirm launch

```bash
sleep 3 && gh run list --workflow=spike.yml --limit=1 --json url,status --jq '.[0]'
```

Tell the user:
> "Spike-focus is running on **<STRATEGY_NAMES>** for **<N> hours** with pop=80. Close your laptop — results auto-commit when done. Run `/spike-results` to check later."

## When to use

- After `/spike` has identified 1-2 promising strategies through the creative loop
- "I like `always_in_trend`, now find the best params for it"
- "Focus on the top 3 from the last spike run"
- Overnight runs while you sleep

## Key differences from /spike

| | /spike | /spike-focus |
|---|---|---|
| Where | Local CLI | GitHub Actions |
| Duration | 1-3h interactive | 5+ hours overnight |
| Scope | All strategies | 1-2 specific strategies |
| Pop size | 40 | 80 (deeper search) |
| Claude's role | Active (revises code) | Passive (triggers and walks away) |

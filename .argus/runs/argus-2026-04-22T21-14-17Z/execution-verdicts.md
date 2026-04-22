# Execution Agent Report — Apr-22

Findings selected for execution: 3
PROVEN: 3
DISPROVEN: 0
INCONCLUSIVE: 0

## Verdicts

EXECUTION VERDICT: Soft admission below PASS / `promotion_ready`
---------------------------------------------------------------
Status: PROVEN

Reproduction:
```bash
'/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.venv/bin/python' '/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.argus/runs/argus-2026-04-22T21-14-17Z/poc-soft-admission.py'
```

Exit code: 0

Output:
```text
[data] TECL: 8298 bars, 1993-05-04 to 2026-04-21
[data] VIX: 8298/8298 dates matched
workdir=/tmp/argus-poc-soft-admission-ugmozk3z
eligible=True
reason=ok
saved_rows=1
saved_verdict=WARN
saved_promotion_ready=False
saved_backtest_certified=False
saved_path=/tmp/argus-poc-soft-admission-ugmozk3z/leaderboard.json
cleanup_removed=True
```

Proof: `search.evolve._is_leaderboard_eligible()` and `update_leaderboard()` admitted and wrote a `WARN` row with `promotion_ready=False`, so the admission surface is softer than PASS-only / promotion-ready-only rhetoric.

Script saved to: `.argus/runs/argus-2026-04-22T21-14-17Z/poc-soft-admission.py`


EXECUTION VERDICT: Post-hoc finalization can set `backtest_certified=True` without preserving Gate 7's intended invariant
---------------------------------------------------------------------------------------------------------------------------
Status: PROVEN

Reproduction:
```bash
'/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.venv/bin/python' '/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.argus/runs/argus-2026-04-22T21-14-17Z/poc-broken-invariant.py'
```

Exit code: 0

Output:
```text
workdir=/tmp/argus-poc-broken-invariant-4_qwr3mw
verdict=WARN
promotion_ready=False
backtest_certified=True
gate7_backtest_certified=True
artifact_status=pass
artifact_passed=True
gate7_advisories=[]
cleanup_removed=True
```

Proof: `search.spike_runner._finalize_champion_certification()` recomputed `backtest_certified` as `all(checks)` after artifact generation, producing `backtest_certified=True` while `promotion_ready=False` on the same `WARN` row and mirroring that contradiction into `gate7`.

Corroborating real artifact read:
```bash
python3 - <<'PY'
import json
for run in ['094','148']:
    path=f'/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/spike/runs/{run}/dashboard_data.json'
    data=json.load(open(path))
    v=data['validation']
    print(f'run={run} source={data.get("validation_summary",{}).get("source")} verdict={v.get("verdict")} promotion_ready={v.get("promotion_ready")} backtest_certified={v.get("backtest_certified")}')
PY
```

Corroborating output:
```text
run=094 source=leaderboard_artifact_backfill verdict=WARN promotion_ready=False backtest_certified=True
run=148 source=leaderboard_artifact_backfill verdict=PASS promotion_ready=True backtest_certified=True
```

Script saved to: `.argus/runs/argus-2026-04-22T21-14-17Z/poc-broken-invariant.py`


EXECUTION VERDICT: Maintenance artifact generation can consume leaderboard rows without rerunning the full validation contract in that path
-------------------------------------------------------------------------------------------------------------------------------------------
Status: PROVEN

Reproduction:
```bash
'/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.venv/bin/python' '/Users/Max.Hammons/Documents/local-sandbox/Project Montauk/.argus/runs/argus-2026-04-22T21-14-17Z/poc-maintenance-backfill.py'
```

Exit code: 0

Output:
```text
[data] TECL: 8298 bars, 1993-05-04 to 2026-04-21
[data] VIX: 8298/8298 dates matched
[artifacts] Warning: recomputed share_multiple diverged from stored metrics (1.1453 vs 1.2000)
[backfill] created ../../../../../tmp/argus-poc-maintenance-94rd_489/runs/001 for #1 gc_vjatr
workdir=/tmp/argus-poc-maintenance-94rd_489
created=1
skipped=0
source=leaderboard_artifact_backfill
validation_verdict=WARN
validation_promotion_ready=False
validation_backtest_certified=True
pipeline_imported=False
cleanup_removed=True
```

Proof: `certify.backfill_artifacts.backfill_leaderboard_dashboard_artifacts()` materialized a full run artifact bundle from a leaderboard row in `/tmp`, marked the output as `source=leaderboard_artifact_backfill`, never imported `validation.pipeline`, and still ended with `backtest_certified=True` on a `WARN` / non-`promotion_ready` validation block.

Script saved to: `.argus/runs/argus-2026-04-22T21-14-17Z/poc-maintenance-backfill.py`

## Proof of Concept Files

- `.argus/runs/argus-2026-04-22T21-14-17Z/poc-soft-admission.py`
- `.argus/runs/argus-2026-04-22T21-14-17Z/poc-broken-invariant.py`
- `.argus/runs/argus-2026-04-22T21-14-17Z/poc-maintenance-backfill.py`

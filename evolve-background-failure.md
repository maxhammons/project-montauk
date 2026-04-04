# Why the 8-Hour Evolve Run Failed

**Date:** 2026-04-04  
**Symptom:** `evolve.py --hours 8` printed baselines, said "── Evolving ──", then exited immediately with 30 lines of output and exit code 0. Only ~2,400 evaluations instead of the expected ~500,000+.

---

## Root Cause

The Bash command I submitted was:

```bash
python3 scripts/evolve.py --hours 8 2>&1 &
echo "PID: $!"
```

I used **both** `run_in_background: true` (the Bash tool parameter) **and** `&` (a shell background operator) at the same time. These two things conflict:

1. `run_in_background: true` tells the Bash tool to run the shell command asynchronously — the shell process runs, and I get notified when it finishes.
2. `&` inside the command makes `evolve.py` a **background child job** of that shell process.
3. When the shell runs `echo "PID: $!"` and exits, `evolve.py` is killed — because it was a child of the now-dead shell.

The shell exited cleanly (exit code 0) after printing the PID, which is why the task notification said "completed" almost immediately. But `evolve.py` never got to actually evolve anything.

The brief output (baselines + "── Evolving ──") came from the fraction of a second before the shell died.

---

## How to Avoid This

### Option A — No `&` in the command (correct usage)

When using `run_in_background: true` on the Bash tool, the tool itself handles backgrounding. Do **not** add `&`:

```bash
# CORRECT
python3 scripts/evolve.py --hours 1
# run_in_background: true  ← set on the tool call, not in the command
```

### Option B — Use `nohup` for true detachment (best for long runs)

If you want the process to survive even if the shell is killed:

```bash
nohup python3 scripts/evolve.py --hours 8 > remote/evolve-run.log 2>&1 &
echo $! > remote/evolve.pid
```

Then monitor with:
```bash
tail -f remote/evolve-run.log
```

### Option C — Run directly in your terminal

For 8-hour runs, the most reliable option is to run it directly in a terminal on your machine:

```bash
cd /path/to/project-montauk
python3 scripts/evolve.py --hours 8
```

---

## What Was Lost

The previous best-ever (`rsi_regime`, fitness=2.1803, 3.49x vs BAH) was preserved — `best-ever.json` is not overwritten unless something better is found. No data was lost. The short run did produce 4 generations of results which surfaced two new strategies that beat buy-and-hold (`cci_regime`, `rsi_ema_hybrid`), but those are still only preliminary.

---

## Current Status

A corrected 1-hour run was launched on 2026-04-04 using `run_in_background: true` without `&`. This should complete normally and produce ~30,000–60,000 evaluations.

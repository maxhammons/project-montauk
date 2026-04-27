# Accelerator Scratchpad - Project Montauk (Apr-14)

## Initial Impressions & The "Can We Ship?" Test

I'm looking at Project Montauk to answer my core question: Can a new engineer ship safely here today?
The short answer is **no, but they can run experiments safely.** Shipping here means getting Pine Script into TradingView, and that pipeline is inherently manual, which creates a hard ceiling on velocity. My worldview cares about the time from "code works locally" to "code is live." In this project, that path is blocked by a massive, manual copy-paste operation.

### Deploy Complexity & The Copy-Paste Bottleneck

The biggest red flag for velocity in this repository is the deploy process.
According to `CLAUDE.md` and `scripts/deploy.py`, the deployment pipeline ends abruptly at a generated text file.
`scripts/deploy.py` takes the results from the optimizer, patches `Project Montauk 8.2.1.txt`, and spits out `patched_strategy.txt`. 
The engineer must then open TradingView, open the Pine Editor, manually select all the code, paste the new code, and hit save or publish.

This is not a "one-command deploy." This is a manual, UI-dependent, human-in-the-loop deployment process. 
- What happens if the copy-paste drops a line? 
- What happens if the engineer pastes it into the wrong TradingView account or wrong chart? 
- What happens if the person who normally does the deploy is on vacation?

This guarantees that deploys are slow, batched, and scary. We can't do continuous deployment. Rollbacks are equally terrifying because they require the exact same manual intervention—finding the old text file in the `archive/` folder and pasting it back in. Without automated rollback, every deploy is a massive commitment.

### The Testing Story

Tests exist, but they aren't the kind that give a new engineer immediate confidence about code changes.
The `scripts/validation/` folder is full of heavy, domain-specific validation logic (Monte Carlo, Walk-Forward, Cross-Asset). These are data-science tests, not software engineering tests. They ensure the *strategy* is good, but they don't ensure the *code* is sound.

If a new engineer modifies a core function in `backtest_engine.py` or tweaks how arrays are sliced in pandas, how do they know they didn't break basic logic? 
There is no `pytest` or `unittest` suite visible in the repository structure. 
- If I change a line of Python, I have to run a full `/spike` or validation pipeline to see if it explodes.
- That feedback loop is too long. A fast test suite (milliseconds to seconds) is required for fearless refactoring.
Fear in a codebase comes from not knowing if you broke something. A new engineer will be afraid to refactor the Python engine because there's no fast safety net.

### The Tooling & AI Dependency

The project has deeply integrated Claude Code skills (`/spike`, `/spike-focus`) and explicit `.github/workflows/spike.yml`.
This is fascinating, but also slightly worrying from an onboarding perspective. The "onboarding" essentially tells the engineer to use an AI agent to do the work. 
While this might accelerate a solo developer who is comfortable with these tools, it creates a strange onboarding path for a *human* engineer. 
- If Claude is down, how do they run the optimization loop? 
- If the engineer doesn't have access to the specific CLI tool, are they locked out of contributing?
The reliance on `spike_runner.py` wrapped in AI skills hides the underlying execution complexity from the human. It creates a single point of failure around the AI tooling.

### The Charter vs. Code Divergence

There is a massive, documented contradiction that will terrify any new engineer trying to make a change:
The `docs/charter.md` explicitly mandates "share-count multiplier vs B&H" as the primary optimization metric and removes trade-frequency punishment.
However, the codebase itself (`scripts/` and the fitness functions) still optimizes for absolute dollar `vs_bah` and includes a `trade_scale` punishment.

If I'm a new engineer, what do I do? 
- Do I fix the code to match the docs? 
- Do I leave it alone because "it's working"?
This is the exact kind of ambiguity that creates "fear in the codebase." Engineers will avoid touching the fitness function because they don't know which source of truth to trust. The documentation literally says there is an "implementation gap," which means the system is currently optimizing for the wrong thing. Until this is fixed, every strategy generated is suspect.

### Summary of Velocity Blockers

1. **Manual Deploys:** TradingView copy-paste is a hard block on true CI/CD. It makes deploys and rollbacks expensive and error-prone.
2. **Missing Unit Tests:** Great data validation, terrible unit testing. We need fast feedback loops for Python code changes.
3. **Ambiguous Source of Truth:** Code and Charter disagree on the primary objective. This must be resolved to restore confidence.
4. **AI-Coupled Tooling:** Human onboarding is bypassed in favor of AI workflows, hiding system complexity.

We need to fix the metric divergence immediately to unblock engineers, and we need a standard `pytest` suite for the Python engine to make refactoring safe. The TradingView deploy might be a platform constraint, but we need to acknowledge it as our velocity ceiling and document exactly how to execute a rollback under pressure.
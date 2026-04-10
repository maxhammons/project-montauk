# Project Montauk — Project Status

> As of 2026-04-10

---

## 1. Current Project Identity

The project is no longer best described as “an EMA strategy with some optimizer scripts around it.”

The correct framing is:

> Project Montauk is a TECL strategy factory: discover many long-only TECL strategies, validate them hard against overfitting, and generate Pine for the best PASS winner.

That is now the standard the codebase should be measured against.

---

## 2. What Is True Today

### Discovery is real

The repo can already search across multiple TECL strategy families rather than only tuning `montauk_821`.

The project now also has room for approved discovery priors that express the kind of low-frequency cycle capture the factory is looking for, without turning those priors into validation rules.

### Promotion gating exists in the canonical full-run path

The local full-run flow now distinguishes between:

- raw optimizer output
- validated output

Only validated PASS entries are intended to become promotable memory.

### Pine generation exists

The repo can now generate Pine candidates for validated winners, with a Montauk-specific patch path for `montauk_821`.

### Deployment-context modeling exists as a separate concern

The project now has a clearer path for account-level deployment analysis, including a Roth overlay model that can sit on top of a validated binary TECL signal without changing the identity of the strategy.

### The right direction is visible

The project clearly wants:

- broader strategy discovery
- stronger anti-overfit validation
- a Pine artifact for the best survivor

That is the right architecture for the mission.

---

## 3. What Is Still Incomplete

The project is moving in the right direction, but it is not yet “done” in the strong sense the charter requires.

### Validation still needs hardening

The validation funnel now exists as a real operating system, not just a research intention.

What is still incomplete is not the existence of validation, but the final level of trust and hardening:

- some validation mechanics will continue to evolve as the research standard improves
- the scripts remain the correct place for exact thresholds and formulas
- the project still needs stronger end-to-end confidence that the validation governor is as strict as it should be

### Python-to-Pine trust is not fully closed

Pine candidates are generated, but the project still needs formal parity confidence between:

- Python strategy logic
- emitted Pine logic
- actual TradingView compile/runtime behavior

Until those parity checks exist, Pine generation is useful but not fully hardened.

### Local full runs are ahead of the rest of the operating model

The full-run path is the canonical flow. Other modes, especially research chunk flows, should not be confused with final promotion logic.

### Final deployment is still manual

That is acceptable for now, but it means the factory currently ends at:

- validated champion
- Pine candidate
- manual TradingView review

not at autonomous live deployment.

---

## 4. Current Strategic Risks

### Overfit winners still look seductive

This will remain the core risk until the validation governor is fully hardened. The project must continue to treat raw winners with suspicion.

### Strategy-family concentration is still a real risk

If too much of the validated memory depends on one idea cluster, the project can fool itself into thinking it has diversity when it only has variants.

### Documentation drift has been a real problem

Before this rewrite, the spirit-guide mixed at least three different stories:

- single-strategy Montauk system
- multi-family optimizer
- optional validation / optional Pine generation

That drift itself is a risk because it causes engineering work to optimize for the wrong thing.

---

## 5. Immediate Priorities

The next priorities are straightforward:

1. Keep the docs aligned to the factory mission.
2. Keep hardening validation without pushing brittle implementation detail into the spirit-guide.
3. Add formal Python-vs-Pine parity checks.
4. Keep the leaderboard PASS-only.
5. Treat Pine generation as part of the definition of done, not a bonus step.
6. Keep discovery priors and account overlays clearly separated from core validation truth.

---

## 6. Plain-English Summary

Project Montauk already behaves like a promising strategy factory.

What it still needs is to become a **trustworthy** strategy factory:

- broad discovery
- hard validation
- PASS-only promotion
- Pine output for the real winner
- deployment analysis that sits downstream of validation instead of corrupting it

That is the line between “interesting research repo” and “rock-solid guiding system.”

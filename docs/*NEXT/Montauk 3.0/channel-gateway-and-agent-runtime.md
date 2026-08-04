# Montauk 3.0 — Channel Gateway and Agent Runtime

**Status: DESIGN / IMPLEMENTATION CONTRACT (drafted 2026-07-26).** This document
fills in the *how* for the conversation channel that
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md)
specifies as policy. That document owns the policy — identity, the mutation
allowlist, the nine-step ritual, what may not be borrowed from OpenClaw — and
this one cannot weaken any of it. The [charter](charter.md) still owns product,
Gold, authority, and safety policy.

The short version is:

> **Build the gateway; rent the agent runtime. Montauk owns the Slack adapter,
> the typed command schema, the command cards, and the outbox renderer, because the
> charter forbids any third party from owning command semantics. Montauk does not
> own the agent loop, session context, or model retry. The authority path —
> digests out, mutations in — never touches a model at all.**

## 1. Decision: subscription-first, API as documented fallback

Max's stated preference (2026-07-26) is to run the resident agent on the **Claude
subscription** rather than metered API billing, accepting API billing where a
capability genuinely requires it. This is a cost/operations preference, not a
Gold or completion criterion, and it is reversible without reopening the strategy
or validation contract.

The preference has one significant architectural consequence, because the two
auth paths do not reach the same runtimes:

| Runtime | Subscription (`claude setup-token`) | API key |
|---|:-:|:-:|
| Claude Code non-interactive (`claude -p`) | ✅ | ✅ |
| Claude Agent SDK | ✅ | ✅ |
| Messages API / Tool Runner | ❌ | ✅ |
| Managed Agents (sessions, deployments, webhooks) | ❌ | ✅ |

Managed Agents is therefore **out of scope for the subscription path**, and the
capabilities it would have supplied for free — server-side session context,
cron-driven deployments, webhook notifications, a first-class interrupt event —
return to Montauk's own plate. §5 specifies how each is replaced. §7 defines the
conditions under which crossing to API billing becomes the correct call.

## 2. Runtime selection under the subscription constraint

Six runtimes were considered. Under the subscription-first decision the field
reduces to two, and they differ mainly in how much of the loop Montauk rebuilds:

| Runtime | Agent loop | Tools run | Verdict |
|---|---|---|---|
| Claude Code `claude -p` one-shot | host | host | Viable; the §5.1 baseline. Sessions, hooks, and permissions must be rebuilt around a subprocess. |
| **Claude Agent SDK** | host | host | **Selected.** Same harness as Claude Code, as a library: built-in tools, agent loop, context management, hooks, subagents, permissions, sessions. |
| Managed Agents (cloud sandbox) | Anthropic | Anthropic | Excluded — API-key auth only. |
| Managed Agents (self-hosted sandbox) | Anthropic | host | Excluded — API-key auth only. Strongest technical fit; see §7. |
| Messages API + Tool Runner | own code | own code | Excluded — API-key auth only, and strictly more work than the Agent SDK for less capability. |
| OpenClaw or an equivalent general gateway | host | host | Excluded by D62 and §8.2. See §6. |

The Agent SDK is preferred over `claude -p` because it supplies as library
features three things §5.1's subprocess model leaves undefined: session
continuity, permission gating, and lifecycle hooks. It remains **harness only** —
Montauk still hosts and supervises it, so the `systemd` topology in §4 of the
operations document is unchanged.

Selecting the Agent SDK does **not** relax §5.1's prohibition. The rule that
survives is the one that matters: *no permanently privileged interactive session
is kept alive to imitate a daemon.* An SDK-hosted agent invocation is a bounded,
supervised, non-interactive job under the `montauk-agent` identity, with a
wall-clock timeout, a turn limit, and a candidate-only working directory —
exactly the containment §5.1 requires, obtained through a library rather than a
subprocess.

## 3. The three-path architecture

Every general-purpose gateway assumes **the model is the interface**. The charter
assumes the opposite: free-form conversation is advisory and can never approve an
Active switch. Building the adapter rather than adopting one lets that be a
property of the transport instead of an instruction the model is asked to honor.

Three paths share one Slack channel. They have different trust levels and the
most dangerous one is model-free:

```text
              ┌─────────────────────────────────────────────┐
              │              SLACK (one private channel)     │
              └───┬──────────────┬───────────────────┬──────┘
                  │              │                   │
        (1) digests out   (2) mutations in    (3) chat both ways
          NO MODEL          NO MODEL             MODEL
                  │              │                   │
                  ▼              ▼                   ▼
        notification      typed command        bounded agent task
            outbox      + interactive          (read-only views,
                          confirmation           candidate workspace)
                  │              │                   │
                  └──────────────┴───────────────────┘
                                 ▼
                       MONTAUK CONTROLLER
              queue truth, authorization, audit, ledger
```

**Path 1 — digests and alerts (no model).** Rendered directly from the durable
notification outbox, per §7.4. The daily signal must not depend on a model being
reachable, in budget, or well-behaved. This also means routine operation costs
nothing against the subscription's agent allowance.

**Path 2 — mutations (no model).** A mutation is initiated by a slash command or
a **Slack interactive component** — a button carrying the immutable proposal ID —
never by prose a model interprets. A button click arrives as a typed, signed
payload; it cannot be prompt-injected, and it cannot be produced by anything that
merely writes text into the channel. This is the mechanical form of §7.4's rule
that free-form conversation can never trigger a mutation, and it resolves
the ambiguity about how typed commands are separated from ordinary conversation
at ingress: **slash command or button = typed; anything else = advisory.**

**Path 3 — conversation (model).** Free-form messages route to a bounded agent
task with read-only status/report views, redacted logs, the failure ledger, and
the generated candidate workspace. It may explain a verdict, inspect a
non-sensitive failure, propose or author a candidate family, and *surface* a
typed command card — but surfacing a card is not invoking it. The card's button is
Path 2.

**Revised 2026-08-03.** This section previously centred on an Active-switch review
card. D124 removed the approval ceremony and D125 removed the authority states, so
there is no switch to confirm, no proposal to defer, and no review card. Path 2
now carries exactly two mutations: `request_research(named_campaign)` and
`request_recertification(scope)`. The three-path architecture is unaffected — the
point was always that a mutation must arrive as a signed typed payload rather than
as text, and that holds for two operations as firmly as it did for four.

Path 2 still renders from the controller's own records via Block Kit, and no
general gateway can render Montauk's status or funnel views, because none of them
know what Gold is.

## 4. Build / rent boundary

**Montauk builds (and would have had to regardless):**

- the Slack Socket Mode adapter (`montauk-channel.service`)
- the typed command schema and its validation
- the typed command cards and confirmation components
- the notification outbox renderer
- the controller: queue leases, idempotency, replay protection, durable ledger

The charter forbids any gateway from owning command semantics, task state, or
audit truth, so none of the above can be delegated to a third party. §7.1 already
committed to this: *"Montauk implements one small, versioned request/reply adapter
contract."* Adopting OpenClaw would have removed none of it — §8.2 explicitly
refuses its task ledger as a second Montauk queue.

**Montauk does not build:**

- the agent loop
- session and context management
- model retry, backoff, and streaming
- tool execution plumbing

That is what the Agent SDK supplies. The glue between the two is small: a Slack
event becomes an agent invocation; agent output becomes a threaded reply.

## 5. What the subscription path costs, and how each cost is paid

Four capabilities that Managed Agents would have supplied become Montauk's
responsibility. None is a blocker; each has a defined answer.

| Capability | Managed Agents would give | Subscription path answer |
|---|---|---|
| **Thread context** | Server-side sessions | Agent SDK sessions, keyed by Slack thread ID, with the session record owned by the controller database — **not** by Slack history (§7.2 forbids treating channel history as durable memory). |
| **Scheduled autonomy** | Cron deployments | `systemd` timers, which §5.2 already designates as the source of scheduling truth. No change from the plan. |
| **Notifications** | Webhooks | The durable notification outbox, which the plan already requires for Path 1. No change from the plan. |
| **Steering / interrupt** | `user.interrupt` event | Cooperative cancellation at a tool boundary via the SDK's hook surface. This is the weakest substitute of the four and should be treated as an open implementation risk. |

Two of the four were already Montauk's job. The genuinely new work is thread
context and steering.

**Thread context is the load-bearing design item.** The controller stores a
compact per-thread record; each agent invocation receives it as part of its
redacted research packet and returns an updated one. This keeps §7.2's rule
intact (provider history is never Montauk's memory), keeps the context auditable
inside Montauk's own database, and survives an adapter restart — which §7.5 and
§10 both require.

## 6. Why not a general gateway

OpenClaw and its equivalents do supply, out of the box, the thing this document
otherwise assembles: an always-on gateway with Slack transport, session routing,
a task queue, and scheduling. D62 and §8 nonetheless set them aside, and the
reason is specific rather than stylistic:

> §8.2: *"current OpenClaw documentation states that ACP sessions execute on the
> **host runtime** under the external CLI's permissions and are not wrapped by the
> OpenClaw sandbox. Selecting a candidate-only working directory is useful
> organization; it is not a security boundary."*

The capability that makes such a gateway convenient — driving a coding agent on
the host — is precisely what places the signed core, the Gold database, and the
Active switch inside its blast radius. Recovering the boundary means rebuilding
containment at the OS layer and owning it across upstream releases. For a
single-user bot on one private channel with four typed commands, the attack
surface of a purpose-built adapter is smaller than the containment work avoided.

This is not a claim that a purpose-built adapter is better engineering in
general. It is narrower on purpose, and it is better **for Montauk** because
Montauk's threat model inverts the assumption general gateways are built on.

## 7. Migration trigger to API billing

The subscription preference is reversible. Crossing to API billing — and with it
Managed Agents — becomes the correct call if any of the following is observed
during commissioning or steady state:

1. The subscription agent allowance cannot sustain the research restocking
   cadence D15 requires, and reducing cadence would harm the discovery queue.
2. The `setup-token` credential proves operationally fragile — the token is
   one-year and inference-only, and a hard expiry that silently stops autonomous
   restocking is an outage.
3. Thread context or cooperative steering (§5) proves materially worse in
   practice than server-side sessions and `user.interrupt`.
4. A capability Montauk actually needs is API-only and has no adequate substitute.

The migration target is **Managed Agents with a self-hosted sandbox**
(`config: {type: "self_hosted"}`), which was not evaluated in the 2026-07-21
research snapshot and is the strongest technical fit if cost stops being the
binding constraint. Its properties align unusually well with this plan: the agent
loop runs on Anthropic's orchestration layer while **tool execution stays on the
Debian host** via an outbound-polling worker — no inbound port, no forwarding,
behind NAT, which is the same property that made Slack Socket Mode correct in
§7.2. It supplies sessions, cron-driven deployments, webhooks, and a first-class
interrupt.

Its known limitations at the time of writing, which must be rechecked before any
migration: memory stores and vault `environment_variable` credentials are not yet
supported on self-hosted sandboxes; worker helpers exist for Python, TypeScript,
and Go only; and the customer owns container hardening, egress restriction, and
custody of the environment key.

Crucially, **the three-path architecture in §3 does not change under migration.**
Paths 1 and 2 are model-free and therefore runtime-independent; only Path 3's
invocation mechanism moves. Nothing in the build/rent boundary of §4 is wasted
work if the trigger fires.

## 8. Open items

These must be closed before the command schema is written.

1. ~~**Mutation count is inconsistent between two sections of the operations
   document.**~~ **CLOSED 2026-08-03.** §7.1 listed three mutations after
   `status()` while §7.4 and the charter both list four. The charter governs, so
   §7.1 was the defect: `defer_or_dismiss_proposal(exact_proposal_id)` has been
   added to its envelope list. The allowlist is four operations.
2. **The typed command schema itself** — field types, expiry semantics,
   idempotency-key derivation, and schema versioning — is named but not
   specified anywhere.
3. **Steering semantics.** §8.1 promises a running agent can receive guidance or
   stop after its current tool boundary. The cooperative-cancellation substitute
   in §5 needs a concrete contract and a test.
4. ~~**Slack-versus-Buzz bake-off** remains formally unrun.~~ **CLOSED
   2026-07-30 by D81.** Slack is the selected primary channel; the bake-off is
   closed by owner decision on cost and maturity grounds rather than by
   measurement, and is not run. Email was evaluated in the same decision and
   rejected at the transport layer (§7.6). The observation this item made still
   holds and now describes migration cost rather than an open comparison:
   nothing in §3 or §4 is Slack-specific except the interactive-component
   mechanism, so a future transport change would need only an equivalent signed
   typed-payload primitive.

## 9. Facts that must be rechecked at commissioning

Following the convention of §5.2, these are version-sensitive and were not
re-verified against primary sources for this document:

- Claude Agent SDK package names, session API, hook surface, and permission
  model. This document describes the SDK architecturally; **implementation must
  read the current SDK documentation** rather than rely on this file.
- Whether subscription authentication is supported for the Agent SDK on the same
  terms as `claude -p`, and the current state of the separate monthly Agent SDK
  allowance noted in §5.2 as beginning 2026-06-15.
- `claude setup-token` lifetime, renewal procedure, and failure mode on expiry.
- Managed Agents self-hosted sandbox status, and whether its beta limitations in
  §7 still hold.
- Slack interactive-component payload verification requirements and scopes beyond
  the minimal set in §7.2.

## 10. Primary sources

Architecture and policy in this document derive from
[debian-host-agent-and-channel-operations.md](debian-host-agent-and-channel-operations.md)
§§5–8 and [decisions.md](decisions.md) D60–D62. Runtime capability claims derive
from Anthropic platform documentation current as of 2026-07-26; per §9, the
Agent SDK specifics in particular are architectural summaries and are not a
substitute for reading `code.claude.com/docs/en/agent-sdk` at implementation
time.

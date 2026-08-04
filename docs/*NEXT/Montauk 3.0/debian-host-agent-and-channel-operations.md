# Montauk 3.0 — Debian Host, Remote Agent, and Conversation-Channel Policy

**Status: DEPLOYMENT BASELINE / IMPLEMENTATION CONTRACT (researched
2026-07-21).** This document owns the way Montauk 3.0 runs as an always-on
appliance. The [charter](charter.md) still owns product, Gold, authority, and
safety policy; this document cannot weaken those rules. Exact hardware,
provider, budget, and strategies-per-hour remain deployment choices rather than
Gold or completion criteria.

The short version is:

> **Run Montauk natively on a minimal Debian 13 host; let `systemd` supervise the
> deterministic controller, low-priority Rust research workers, bounded remote
> model calls, backup, and one private conversation-channel adapter; reach the
> machine through Tailscale/SSH, with an on-demand graphical desktop on the same
> tailnet when the work is visual; and copy the useful interaction patterns from
> OpenClaw and Buzz without giving either product—or any conversational
> agent—authority over Montauk's core.**

## 1. The operating picture

```text
                              MAX
                 +-------------+-------------+
                 |                           |
      private conversation         Tailscale: SSH + on-demand
       status, chat, commands        XFCE/RDP desktop (D83)
                 |                    deliberate administration
                 |                           |
                 v                           v
       deterministic channel        optional local-agent session
             adapter                for deliberate diagnosis/repair
                 |                           |
                 +-------------+-------------+
                               |
                               v
                    MONTAUK CONTROLLER
        queue truth, authorization, audit, notifications,
          service health, recertification, and priorities
                    /                    \
                   v                      v
       protected signed core       resident model adapter
     data -> Rust pipeline -> Gold  bounded one-shot calls only
                   ^                      |
                   |                      v
                   +--- candidate inbox / generated workspace

All processes are supervised by systemd. Research can use spare CPU, but
verified data, the trusted signal, Active recertification, recovery, and alerts
always preempt it.
```

This is **OpenClaw/Buzz-like in interaction, but independent of either product
for authority**. The selected channel should feel like a conversation with the
appliance, but the deterministic controller—not the model, Slack, Buzz, or an
outer gateway—owns every accepted command and state transition.

## 2. Host and operating-system baseline

### 2.1 Native Debian is the production default

The 3.0 deployment baseline is **Debian 13 `trixie`** on the old Windows tower,
installed natively rather than through WSL or a virtual machine. Max confirmed
the release on 2026-08-02 (D82), so this is a settled commissioning fact rather
than "whatever Stable happens to be."

Install the minimal 64-bit system. Debian's own installer offers no desktop
environment at this step and none is selected here: the base appliance is
headless, and every resident service — controller, research workers, channel
adapter — runs without a display. The XFCE desktop that D83 requires for
graphical remote administration is added afterward as a deliberate, on-demand
surface under §6, not as part of the base install and not as a running default.

Why this is the default:

- lower idle CPU/RAM and fewer background services than a normal Windows
  desktop installation;
- first-class service supervision, logging, resource controls, and restart
  behavior through `systemd`;
- a simpler Rust/Linux deployment and sandboxing target;
- reliable headless SSH administration; and
- fewer unrelated OS updates, desktop applications, and sleep policies competing
  with continuous work.

The likely gain is operational simplicity and predictable resource ownership,
not a magical multiplication of backtest speed. Rust design, memory behavior,
storage, CPU age, and thermals will usually matter more than the OS difference.
Debian is therefore a deployment default, not part of the Gold definition. If a
commissioning hardware check finds an irreplaceable driver, firmware, or stability
problem, Max may revisit the OS without reopening the strategy or validation
contract.

### 2.2 Storage

- **SSD is required for the live system and hot Montauk data.** NVMe is preferred
  when the motherboard supports it; SATA SSD is still far preferable to an HDD.
- Put the OS, control database, verified market data, current experiment
  partitions, build artifacts, and active logs on SSD.
- An HDD is acceptable for cold compressed snapshots, bulk historical archives,
  and a local secondary backup. It is not the hot database or scratch device.
- Keep an off-machine GitHub recovery path and **a second local device** holding
  a copy that a single-disk failure cannot destroy. Zero loss of acknowledged
  Active/approval/signal/Gold mutations is promised against ordinary process and
  disk failure; the physical-disaster recovery point is explicitly bounded by the
  last verified GitHub sync until a second offsite domain exists.
- A GitHub-only outage must not suppress a valid daily signal. Journal locally,
  enter `degraded_backup`, alert Max, deliver the signal on time, and block Gold
  publication and Active changes until replication catches up.
- Begin with a conventional, well-supported filesystem such as `ext4`. Change
  mount options or filesystems only after profiling demonstrates a real problem.
- Monitor free space and SSD health. Storage-pressure thresholds must pause new
  research before they threaten the control database, Gold artifacts, or backup.

### 2.3 CPU, memory, and thermals

- Install RAM in matched channels and verify the expected capacity/speed in the
  firmware and OS. Memory bandwidth and avoiding swap are more valuable than
  cosmetic OS tuning.
- Research workers may consume all **spare** CPU, not all CPU unconditionally.
  Reserve or preempt capacity for verified data, the current signal, Active
  recertification, recovery, the controller, and the channel adapter.
- Benchmark physical-core-only and logical-thread worker counts. On an older CPU,
  maximum logical concurrency is not automatically the fastest or most
  thermally sustainable setting.
- Use bounded streaming shards/batches. Do not materialize billions of
  configuration objects or files at once.
- Keep a small emergency swap area so one spike does not instantly kill the
  host, but alert and shed research load before sustained swapping becomes normal.
- The §6 graphical desktop is **not** reserved capacity. It is an on-demand
  administration surface: when Max is not connected, its units are idle and its
  cost is disk plus a few megabytes of resident state. When he does connect, the
  desktop and its session take priority over research the same way any other
  administration path does — research sheds load, the trusted signal does not.
- Clean the machine, verify fans, replace failing thermal components, and run a
  sustained CPU/RAM/disk soak. A benchmark that lasts one minute is not evidence
  of 24/7 throughput.
- Do not overclock. Stable, reproducible computation is worth more than a small
  peak-speed gain.
- Record temperature, throttling, memory pressure, disk latency, queue age, and
  trusted-job deadline misses during performance tests.

### 2.4 Power, firmware, and unattended behavior

- **Wired Ethernet to the home LAN is the confirmed baseline** (D82, 2026-08-02).
  Wi-Fi is not the deployed transport and its power-save/reassociation failure
  modes therefore do not apply. If the machine is ever moved to Wi-Fi, that is a
  commissioning change requiring disabled NetworkManager power-save, verified
  reassociation after an access-point reboot, and a re-run of the §10 unattended
  reboot evidence.
- Use a UPS if the machine and local network equipment will support trusted
  unattended operation.
- Configure firmware to restore power after an outage.
- Disable suspend, hibernation, and desktop power-saving behavior that stops
  work.
- Synchronize time and treat clock failure as an operational fault.
- Apply security updates under a controlled maintenance/reboot policy. Do not
  permit surprise reboots during the post-close signal or recertification window.
- Preserve a documented Windows backup/recovery image until Debian commissioning
  is complete.

## 3. OS identities and trust separation

Linux users and permissions enforce the charter; prompts do not.

| Identity | Purpose | Must not have |
|---|---|---|
| Max/admin | Deliberate maintenance, release review, deployment, recovery | Routine unattended ownership of agent tasks |
| `montauk-core` | Run the signed deterministic controller and trusted jobs | Max's release-signing key; arbitrary candidate writes |
| `montauk-agent` | Invoke the model adapter and write candidate specs/modules | Protected-core write access, Gold/Active DB mutation, validator secrets, `sudo` |
| candidate worker | Disposable execution of one untrusted intake job | Network, credentials, host filesystem, subprocess freedom, core writes |
| `montauk-channel` | Receive events from the one selected private channel and write typed requests/replies to the command inbox/outbox | Shell access, core writes, direct Gold/Active mutation |

The exact count of Unix users can be simplified if the same effective capability
separation is proven. The non-negotiable properties are:

1. the resident model cannot write the sealed core or its fixtures;
2. the channel process cannot turn text into shell access;
3. candidate execution has no provider, channel, GitHub, or signing credentials;
4. Max's signing key is not resident in an unattended service; and
5. every state mutation enters through the deterministic controller's typed,
   audited command contract.

Provider, channel, GitHub, and Tailscale credentials stay outside Git and candidate
workspaces. Use restrictive service credentials/files or a system credential
facility; pass secret references to services and redact them from logs. A secret
in an environment variable is still accessible to that process, so service
boundaries must remain narrow.

## 4. `systemd` service topology

`systemd` is the durable scheduler and supervisor. An interactive model session,
Claude `/loop`, a Slack/Buzz thread, or an OpenClaw conversation is not the
control plane.

The initial logical units are:

| Unit | Responsibility | Execution character |
|---|---|---|
| `montauk-core.service` | Controller, queue/state transitions, trusted deadlines, notification outbox | Long-lived, protected, high priority |
| `montauk-research.service` | Rust configuration expansion, screening, backtests, candidate validation | Long-lived or leased workers, low priority, preemptible |
| `montauk-agent.timer` + `montauk-agent.service` | Restock/repair/analyze through one bounded provider call | Durable timer plus one-shot service; no overlapping runs |
| `montauk-channel.service` | The one selected private channel adapter and outbox delivery | Long-lived, bounded, restartable |
| `montauk-backup.timer` + `montauk-backup.service` | Snapshot, off-machine replication, and verification | Scheduled, idempotent |
| `montauk-doctor.timer` + `montauk-doctor.service` | Deep health, deadline, integrity, storage, and backup checks | Scheduled; alerts through durable outbox |

These names are implementation defaults, not six new product stages. They operate
the one conveyor documented in the charter.

Service requirements:

- start on boot and restart with bounded backoff;
- use explicit working directories, users, capabilities, memory/CPU limits, and
  writable paths;
- refuse concurrent agent ticks and use leases/idempotency for retried jobs;
- log structured run IDs and state transitions to the authoritative ledger;
- expose a cheap health probe and a deeper doctor probe;
- stop accepting new research before disk, memory, thermal, or deadline pressure
  harms trusted work;
- recover from process death without duplicating an authority mutation; and
- make a failed or repeatedly restarting unit visible through the notification
  outbox.

The controller owns the global concurrency cap and per-lane FIFO queues. Chat,
agent, recertification, backup, and research requests do not race directly for
shared files or start arbitrary duplicate processes.

## 5. Resident frontier-agent operation

### 5.1 Provider-neutral one-shot adapter

The scheduled unit calls a provider adapter, not a Claude-specific business
interface. The adapter must be able to invoke Claude Code, Codex, an API-backed
agent, or a later provider while producing the same versioned input/output
envelope.

Each autonomous run is bounded and fresh:

1. the controller writes a compact, redacted research packet with recent
   aggregate outcomes, failure summaries, queue needs, allowed primitives, and
   immutable versions;
2. `montauk-agent.service` invokes one configured provider with a wall-clock
   timeout, token/turn limit, candidate-only working directory, and structured
   output requirement;
3. the provider may write only candidate definitions/modules and a proposed
4. deterministic intake accepts or rejects each artifact; and
5. the run, usage, artifacts, repair attempts, and outcome are durably recorded.

For Claude Code, a non-interactive `claude -p` invocation can implement this
adapter, but the contract is the structured envelope—not the CLI syntax. Use a
machine-readable result, bounded turns, a service timeout, and the
`montauk-agent` identity. Do not keep a permanently privileged interactive CLI
session alive merely to imitate a daemon.

### 5.2 Scheduling and authentication facts that must be rechecked

Claude Code supports Debian, but its built-in `/loop` and session cron tasks are
session-scoped, require the session to remain running/idle, miss catch-up fires,
and currently expire after seven days. They are useful interactively, not for
Montauk's durable hourly operation. The Debian `systemd` timer remains the
source of scheduling truth.

At the 2026-07-21 research snapshot, Claude permits either API authentication or
a one-year subscription OAuth token produced by `claude setup-token` for
non-interactive use. Anthropic also states that subscription `claude -p`/Agent
SDK use draws from a separate monthly Agent SDK credit beginning 2026-06-15.
These commercial/authentication details can change, so commissioning must test
the actual Max subscription and an API option for reliability and cost. The
system records which provider/account path produced each artifact without making
that provider part of Gold. The long-lived `setup-token` is inference-only and
does not establish a Remote Control session; deliberate Remote Control repair
uses an eligible interactive subscription login under its own Linux identity.

### 5.3 Interactive repair is separate from autonomy

Claude Code Remote Control is useful for a deliberate repair session because the
Claude process continues to execute on the Debian machine while Max talks from a
browser or phone. It is an optional maintenance convenience, not the service
scheduler, channel adapter, queue database, or authority layer. It currently
requires a supported Claude subscription login rather than an API key.

Any remotely steered coding session inherits the Linux identity and filesystem
permissions under which it was launched. Start ordinary repair under
`montauk-agent`; enter Max-authorized maintenance/release mode only deliberately,
with the charter's review, signing, audit, and credential-revocation ceremony.

Anthropic's direct Claude/Claude Code Slack integration is also not a Montauk
adapter: it routes coding requests to Claude Code on the web against connected
GitHub repositories and plan limits. It does not provide the local Debian
controller, deterministic command authorization, or Montauk audit truth.

## 6. Remote administration

Use four distinct surfaces:

1. **Selected private channel:** daily operation, explanations, status, alerts,
   and the three narrow mutations allowed by the charter.
2. **Tailscale + SSH:** reliable private administration, logs, service state,
   upgrades, recovery, and emergency diagnosis. Do not expose SSH directly to
   the public internet; restrict tailnet access to Max's devices/account.
3. **Tailscale + graphical desktop:** an XFCE session reached over RDP from Max's
   Mac, for work that is genuinely visual — reading a chart, driving a GUI tool,
   watching a long run, or any diagnosis where a terminal is the wrong shape.
   Required by D83. It is an *administration* surface only: it carries no
   authority SSH does not already carry, and it is never a path for approving an
   Active switch.
4. **Provider Remote Control:** optional conversational access to a deliberately
   launched local coding-agent session for diagnosis or repair.

Tailscale is the default remote network because it avoids router port forwarding
and gives the server a stable private identity. SSH remains independently usable
over the tailnet even if the channel or model provider is down. Recovery must never
depend on the same AI or chat surface that is failing.

**Surface 3 must never weaken surface 2.** SSH is the recovery path and its
availability is load-bearing; the desktop is a convenience layered on the same
tailnet. If the graphical stack is broken, wedged, or mid-upgrade, SSH recovery
must still work. Commissioning proves that ordering explicitly (§10).

Commissioning sequence:

1. install Tailscale from its supported Debian packages and enroll the server in
   Max's tailnet;
2. restrict the server tag/device and SSH policy to Max's approved identities and
   devices;
3. choose and document either ordinary OpenSSH reachable only through the
   tailnet or Tailscale SSH—do not accidentally expose a second public path;
4. disable router port forwarding and reject public-interface SSH in the host
   firewall;
5. test access, reboot recovery, key/device revocation, and an emergency login
   from a second approved device;
6. do not enable Tailscale Funnel or another public publishing feature for the
   Montauk control surface; and
7. build the graphical surface per §6.1.

### 6.1 Graphical remote administration (D83)

The shape:

- **Desktop:** XFCE, installed on top of the minimal system. It is chosen over
  GNOME/KDE because the appliance is a two-core i3-6100 whose capacity is
  committed elsewhere (§2.3), and because a compositing desktop buys nothing for
  remote administration.
- **Protocol:** RDP via `xrdp`, with each connection starting its own X session.
  RDP is preferred over VNC here because it degrades far better over a home
  uplink and because it does not require a display to already exist on a headless
  box. macOS connects with Microsoft's free Windows App client.
- **Reachability:** `xrdp` binds to the **tailnet interface only** — never
  `0.0.0.0`, never the LAN interface, never a forwarded router port. The host
  firewall rejects RDP on every other interface. Reaching the desktop requires
  already being on the tailnet, so it inherits Tailscale's device authorization
  rather than introducing a second, weaker front door.
- **On-demand, not resident:** the `xrdp` units are installed but **not**
  enabled at boot. Max starts the surface over SSH when he wants it and stops it
  when done. This keeps §2.3's capacity reservation honest and keeps the idle
  attack surface at zero listening sockets.
- **Identity:** the desktop session runs as Max's ordinary administrative login,
  never as a Montauk service identity. It gets no protected-core write access, no
  service credentials, and no ability to mutate Gold or Active — §3's separation
  is not relaxed to make a GUI convenient.

What it is explicitly not: a display for Montauk to render anything to, a
substitute for the Slack digest, or a supported place for the resident agent to
run interactive graphical tools. Montauk's own output surfaces are unchanged.

## 7. Conversation-channel contract and provider choice

### 7.1 One invariant adapter, one deployed primary channel

Montauk implements one small, versioned request/reply adapter contract. Slack
and Buzz are replaceable outer transports; neither is allowed to define command
semantics, task state, audit truth, Gold, recommendation, Active, or the trusted
signal. Only **one primary conversational adapter runs in production at a time**.
Do not build and operate two complete command paths indefinitely “for
flexibility.” The unselected implementation is removed or retained only as a
non-running test fixture.

**One adapter, one provider, two rooms (D116).** Montauk uses two Slack channels
inside the same workspace, served by the same adapter: an **operational** channel
carrying the daily digest, alerts, and status — the things Max reads — and an
**approvals** channel carrying every item blocking on his decision: new-block
proposals (D96), the Phase 1 package, a third score pillar or new veto, restore
and Chimera scheduling. (Restore drills, Active switches, the 2.0→3.0 cutover,
and the completion declaration were struck from the approval set on 2026-08-03 by
D123/D124.) Everything in the approvals channel is by definition
blocking something, so its unread count is a real work queue rather than noise.

This is **not** a second command path and does not weaken the one-provider rule
above: same workspace, same adapter, same typed mutation envelope, same D80
model-free path. Both rooms appear in the approved room/channel identifier list.

Every adapter must provide:

- a stable cryptographic or provider-issued identity that maps only to Max;
- approved room/channel identifiers;
- threaded requests and replies tied to Montauk task IDs;
- deterministic outbound delivery from the durable notification outbox;
- a typed mutation envelope with explicit confirmation, expiry, idempotency,
  replay protection, and visible failure;
- restart reconciliation against the controller ledger; and
- no credential or capability that can write the protected core or directly
  mutate Gold/Active.

Free-form conversation is advisory. Provider syntax may differ, but every
mutation maps to exactly one controller operation:

```text
status()
request_research(named_campaign)
request_recertification(scope)
```

`status` is read-only. The last **two** are the charter's complete mutation
allowlist.

Both removals happened on 2026-08-03. `approve_active_switch` went with D124:
there is no approval ceremony and no authority handover — Montauk publishes the
leader's signal as an operational fact. `defer_or_dismiss_proposal` went with
D125, which deleted the Recommended/Active/Override states, leaving no proposals
to defer. Max decides what he does about the signal entirely outside Montauk.

Corrected 2026-08-03: this list previously omitted `defer_or_dismiss_proposal`,
contradicting §7.4 and the charter's own four-item allowlist. The charter governs;
this was a documentation defect, and it closes open item 1 of
[channel-gateway-and-agent-runtime.md](channel-gateway-and-agent-runtime.md).

### 7.2 Slack is the selected channel

**Selected 2026-07-30 by D81.** This section was written as a conservative
default pending the §7.3 bake-off; that bake-off is now closed unrun and these
steps are the commissioning procedure. Slack remains a replaceable outer
transport, not a permanent product dependency or a claim that it is
architecturally better — D81 records the conditions that would reopen the choice.

Use one workspace-scoped custom Montauk Slack app. Slack is the lower-operational-
risk choice because mature mobile clients and push delivery already cover the
daily-digest and critical-alert use case, and because the deployment carries no
recurring cost: a free workspace, a free app install, Socket Mode as a standard
platform feature, and an adapter hosted on the appliance. No paid Slack plan may
become a dependency without a new owner decision.

For a single home server behind NAT, use Slack Socket Mode: the Debian process
opens an outbound WebSocket and no public request URL is required. Use an
official Slack Bolt SDK when practical. This adapter is not a Rust throughput
bottleneck; a maintained Python or JavaScript SDK is preferable to hand-writing
reconnection and envelope acknowledgement behavior.

Start with the least privilege needed for a private Montauk channel and slash
commands:

- app-level token: `connections:write`;
- bot scopes: `chat:write`, `commands`, and `app_mentions:read` if mentions are
  enabled; and
- add channel/DM history, files, reactions, or user lookup only when a tested
  feature actually requires them.

The adapter must allow only Max's immutable Slack user ID and approved channel
IDs. Display names, email addresses, and natural-language claims of identity are
not authorization.

One-time Slack setup:

1. create a workspace-scoped private Montauk app, preferably from a versioned
   minimal app manifest retained with protected operations code;
2. enable Socket Mode and create an app-level `xapp-...` token with only
   `connections:write`;
3. add the minimal bot scopes and the `/montauk` slash command, install the app
   to the workspace, and obtain its `xoxb-...` bot token;
4. invite the bot only to the intended private channel(s), record Max's stable
   `U...` user ID and the allowed `C...` channel IDs, and place those IDs in
   protected configuration;
5. place tokens in the service credential store with restrictive permissions,
   never in Git, prompts, candidate workspaces, or logs;
6. start the Slack implementation of `montauk-channel.service` and first prove
   outbound status plus a rejected unauthorized/malformed inbound event; and
7. enable each mutating command only after its confirmation, expiry, replay,
   idempotency, audit, and recovery tests pass.

Socket Mode is the correct initial Slack shape for one private host behind NAT.
Workspace plan, history, app, and rate limits are rechecked during commissioning;
Slack history is never Montauk's durable memory. If a future deployment has
several adapter replicas behind an existing public HTTPS load balancer,
reevaluate Slack's signed HTTP Request URL transport rather than stretching the
single-host choice into a scaling architecture.

### 7.3 Buzz is a strong candidate, not an assumed replacement

> **CLOSED 2026-07-30 by D81 — retained as rationale, not as an open task.** Max
> selected Slack and declined to run the bake-off specified below. The decision
> rests on evidence already in this section — Buzz's four-service resident
> footprint against a two-core/120 GB appliance (§2.2, §2.3), and its pre-1.0
> status with mobile push and approval gates still being wired up — not on
> measurements, which were never taken. The eight criteria below are retired
> unrun and are preserved because D81's reopening conditions invoke them by
> reference. **Do not budget bake-off work from this section.** Email was
> evaluated in the same decision and rejected; see §7.6.

Buzz is unusually well aligned with the desired interaction model: it is an
Apache-2.0 self-hostable workspace where people and agents share rooms; messages
and workflow events are signed; the relay keeps a hash-chained audit log; and
`buzz-cli` is JSON-in/JSON-out with ACP support. Those are useful advantages over
a custom Slack bridge: owner-controlled conversation data, first-class agent
identity, searchable project threads, and a provider-neutral agent surface.

It is not automatically the simpler or safer 3.0 choice. At the 2026-07-21
snapshot Buzz is pre-1.0, supports only `main` fully, describes mobile clients,
push notifications, and workflow approval gates as still being wired up, and
requires a relay plus PostgreSQL, Redis, and S3/MinIO-style object storage for
its full self-hosted architecture. Its architecture document also says rate
limiting is not currently enforced. Channel membership is Buzz's primary access
gate, which is not fine-grained enough to replace Montauk's typed mutation
allowlist. `buzz-dev-mcp` gives an agent shell/file editor and explicitly runs
the shell at the operator's trust level; working-directory resolution and
bounded output are good hygiene, not a Montauk security boundary.

Before writing a full channel integration, run a time-boxed **Slack-versus-Buzz
bake-off** against the same fake controller and notification outbox. Measure:

1. daily and critical delivery, phone access, push behavior, and recovery from
   missed/offline delivery;
2. thread continuity, search, readable receipts, and agent handoff quality;
3. immutable Max identity plus typed confirmation, expiry, idempotency, replay,
   duplicate-delivery, and unauthorized-user rejection;
4. clean restart reconciliation without treating provider history as truth;
5. Debian CPU/RAM/disk/network overhead while Rust research is saturated;
6. install, TLS/private-network, backup, update, key-rotation, and restore burden;
7. provider-neutral agent use without giving the channel agent protected-core
   credentials or general host-shell authority; and
8. the ability to disable every non-Montauk feature that broadens the blast
   radius.

The selection rule is simple: choose Buzz only if it is at least as reliable for
Max's phone/digest workflow, passes the identical authority/security tests, and
its better conversation/agent continuity is worth the measured operational
cost. Otherwise use Slack. Max makes the final UX choice from the evidence. The
winner becomes the one primary channel; the bake-off does not authorize two
permanent gateways.

If Buzz is selected, expose its relay only through the tailnet or properly
terminated TLS, run the adapter and any agent under `montauk-channel`/
`montauk-agent`, protect the Buzz private key as a service credential, and deny
its agent tools core credentials and writes at the OS/container layer. Buzz's
signed/hash-chained event history is a useful receipt, but it is a second copy,
not Montauk's command or audit authority. Consider hosting its database/relay on
a separate low-power machine only if same-host measurements show that it harms
trusted deadlines or research throughput; a second machine is not required by
3.0.

### 7.4 Message and command behavior

Routine digests and deterministic alerts are rendered directly from the
notification outbox. They do not require a model call. Conversation may ask the
resident agent to explain already-authorized data or propose research, but its
answer is advisory.

Free-form chat is routed to a thread-bound, bounded agent task with read-only
Montauk status/report views, redacted logs, the failure ledger, and the generated
candidate workspace. From the selected channel the agent can explain a verdict,
inspect a non-sensitive failure, propose or author a candidate family, and
report what it did. It cannot receive core credentials or turn a conversation into protected
maintenance. If a request requires core edits, secret access, release signing,
or unrestricted diagnosis, the agent explains that boundary and Max deliberately
opens a Tailscale/SSH or provider Remote Control maintenance session.

Every mutation must:

1. identify Max by the adapter's stable identity and verify the allowed room;
2. parse against a typed schema—never infer a command from free-form prose;
3. show the exact effect, immutable ID, and expiry in a confirmation message;
4. require explicit confirmation;
5. use an idempotency key and replay protection;
6. submit to the controller rather than execute locally in the bridge;
7. record accepted/queued/running/completed/failed state in the durable ledger;
8. reply and update status in the same conversation thread; and
9. make denial or failure visible rather than silently falling back.

The allowlisted mutations are exactly two: **request a named research campaign**
and **trigger recertification** (D125). There is no switch approval, no proposal
to defer or dismiss, and no review card — D124 removed the approval ceremony and
D125 removed the authority states it operated on. Montauk publishes the leader's
signal as an operational fact; nothing in the channel confirms, authorizes, or
changes that.

Free-form conversation can never change Gold, change which strategy is the leader,
acknowledge a brokerage fill, edit methodology, enter maintenance mode, or run a
shell command outside the bounded agent/candidate capability set. Channel
history is not the audit log and message delivery is not proof that the
controller committed a change.

Read-only update rooms plus a command DM live inside this one selected channel.
They are **not** an independent dead-man path: if the host, home internet, or the
channel provider fails completely, Montauk cannot report its own absence. An
independent outbound heartbeat service is out of scope for 3.0 by owner
decision, and that residual risk is accepted rather than mitigated.

### 7.5 Reliability

- Acknowledge provider events promptly, then do durable work asynchronously.
- Expect disconnects/duplicates and reconnect with bounded backoff.
- Serialize commands per conversation thread/session and enforce a global agent
  concurrency cap.
- Store pending replies in the durable outbox so a bridge restart does not erase
  the underlying event.
- Keep notification delivery separate from state mutation: a channel outage cannot
  change Gold or Active.
- Critical undelivered alerts remain visible in local status and are retried;
  Tailscale/SSH remains the repair path.

### 7.6 Email is not a candidate for the primary channel

Email was raised as a primary conversational channel on 2026-07-30 — Max mails
Montauk, the host is notified, and the resident agent reads the mailbox — and is
**rejected** (D81). The rejection is not a preference between comfortable
options. Email fails §7.1's adapter requirements at the transport layer, and two
of the failures are unfixable without rebuilding the property that makes the
channel safe.

**1. No identity that maps only to Max.** §7.1 requires "a stable cryptographic
or provider-issued identity that maps only to Max," and §7.2 has already ruled
that "display names, **email addresses**, and natural-language claims of
identity are not authorization." A `From:` header is trivially forged. Reaching a
defensible identity means implementing inbound DKIM/SPF/DMARC verification —
building a mail authentication stack as a precondition of the channel — and even
a DMARC pass authenticates a *sending domain*, not Max. Slack supplies an
immutable `U…` user ID inside a signed payload with no equivalent work.

**2. No typed mutation envelope — the disqualifying failure.** §7.4 requires
every mutation to parse against a typed schema and never be inferred from
free-form prose, and D80 fixes the ingress rule as *slash command or button =
typed; anything else = advisory*. Email offers no typed component, so it degrades
to exactly one of two prohibited shapes:

- **prose approval**, which requires a model to interpret intent and so violates
  the rule that free-form conversation can never invoke a mutation; or
- **a click-through approval link**, which is an HTTP endpoint — reintroducing
  the public inbound ingress that Socket Mode was chosen to eliminate (§7.2), and
  pointing it at the host holding the signed core, the Gold database, and the
  Active switch.

There is no third option. The property D80 obtained mechanically — a signed
interactive payload that cannot be produced by anything that merely writes text
into the channel, and therefore cannot be prompt-injected — has no email
equivalent.

**3. Delivery semantics are adversarial to the mutation contract.** Email is
at-least-once, unordered, arbitrarily delayed, and silently spam-filed. An
approval that arrives hours late, past its expiry, and is then re-delivered by a
retrying MTA is precisely the failure §7.4 steps 3 and 5 exist to prevent. Those
guarantees would have to be rebuilt on top of a transport that actively works
against them.

**4. The blast radius inverts.** Ingress means IMAP against Max's personal
mailbox, so the channel service holds a credential far broader than §7.2's least
privilege set. Compromise of the Slack adapter exposes one private channel;
compromise of a mail-reading adapter exposes the mailbox that holds the
password-reset path for the brokerage account this system generates signals for.
"It could read all the emails" is the liability, not the feature.

**5. The address is an open namespace.** Anyone who learns it can inject content
into Path 3's model context. A private Slack channel is a closed room in which
only invited members can post.

**Where email is still appropriate.** Email's one recorded strength is that it
depends on nothing Montauk built, which makes it a natural **out-of-band alert
path** of the kind the durability research contemplates — a notification route
outside Tailscale and GitHub. That is not a 3.0 deliverable: §7.4 records that an
independent outbound heartbeat service is out of scope for 3.0 by owner decision
and the residual risk is accepted. Email is therefore retained as the obvious
candidate *if* that scope decision is ever revisited, and is admitted for nothing
else. It is not a conversational channel, and it never carries a mutation.

## 8. What Montauk should borrow from OpenClaw

OpenClaw is a useful analogy because it puts an always-on gateway between chat
channels, agent sessions, scheduled work, and a computer. Montauk needs the same
calm relationship—“talk to the appliance, see what it is doing, and intervene
when necessary”—but its trading authority requires a much smaller blast radius.

### 8.1 Borrow these patterns

| OpenClaw pattern | Montauk adoption |
|---|---|
| One long-lived gateway owns channels and state routing | One Montauk channel-adapter/controller boundary owns chat ingress/egress; no parallel bot paths |
| Typed request/response/event protocol with schema validation | Structured command and status envelopes with immutable IDs and versioned schemas |
| Immediate accepted status followed by streamed/final run state | Conversation thread shows accepted, queued, running, completed, or failed |
| Side-effect idempotency keys | Required for every research, recertification, or approval mutation |
| Stable session/channel routing | One channel thread maps to one bounded conversation/run context and durable task ID |
| Per-session FIFO plus global concurrency/backpressure | Avoid colliding model sessions, shared-workspace races, and provider-rate spikes |
| Exact cron, approximate heartbeat, event hooks, and task ledger are distinct | `systemd` timers schedule exact work; doctor checks health; events trigger safe reactions; database records tasks |
| One master gateway on an always-on host | One deterministic Montauk controller owns queue/authority truth on the Debian host |
| Loopback/private access with Tailscale or SSH | No public control port; private remote administration only |
| Device/user pairing and explicit scopes | Stable Max/room allowlist, tailnet device access, read versus mutate roles |
| Health, doctor, audit, and recovery surfaces | Cheap health probe, deep doctor, durable audit, backup/restore drills |
| Provider/runtime adapters | Claude/Codex/API replaceable behind one candidate-output contract |
| Workspace, state, configuration, and secrets separated | Candidate workspace cannot contain controller secrets or protected core |
| Layered sandbox, tool policy, and approvals; stricter layer wins | OS permissions + candidate sandbox + typed intake + exact owner approval |
| Steering at safe boundaries | A running agent can receive guidance or stop after its current tool boundary; trusted jobs are never interrupted by chat |

These patterns make the relationship easy without adding research or Gold
stages.

### 8.2 Do not borrow these parts

Montauk 3.0 should not import:

- a general personal-assistant or collaboration suite beyond Montauk's one
  private channel;
- browser, camera, microphone, location, desktop-control, or arbitrary computer-
  use tools;
- a large plugin/skill marketplace or automatic third-party code installation;
- broad host-shell authority, “YOLO” execution, or agent-controlled privilege
  escalation;
- inferred conversational commitments as methodology or trading authority;
- conversational memory as product truth;
- multiple gateways, multi-user tenancy, or swarms without a measured need;
- OpenClaw's task ledger as a second Montauk queue or audit authority;
- OpenClaw as the backtest, validator, Gold, leaderboard, rank, signal, or Active
  controller; or
- complexity whose only justification is that OpenClaw implements it.

The current recommendation is therefore **not to make OpenClaw a required 3.0
dependency**. Implement the smaller Montauk-owned adapter contract and select
Slack or Buzz through §7.3. OpenClaw may later be evaluated only if it provides
measured value not supplied by the selected channel.

If OpenClaw is trialed, it runs under `montauk-agent` or a stricter container with
candidate/inbox access only. It receives no protected-core write access, signing
key, validator/Gold database credential, or direct Active mutation capability.
Its ACP/external-agent feature is especially important to contain: current
OpenClaw documentation states that ACP sessions execute on the **host runtime**
under the external CLI's permissions and are not wrapped by the OpenClaw
sandbox. Selecting a candidate-only working directory is useful organization;
it is not a security boundary. OS/container permissions must make the forbidden
actions impossible.

The governing phrase is:

> **Borrow OpenClaw's gateway UX and orchestration discipline, not its
> general-purpose blast radius.**

## 9. Clean-machine setup sequence

This is the commissioning order, not a shell script:

1. Inventory CPU, RAM layout, disks/SMART health, motherboard, firmware,
   networking, and remote-power behavior; preserve a Windows recovery image.
2. Install Debian 13 `trixie` amd64 minimally and apply firmware/security
   updates. Do not select a desktop task at install time; the D83 desktop is
   added at step 6a, after the trust boundaries exist.
3. Configure time synchronization, wired Ethernet to the home LAN, no-sleep
   behavior, power-loss restart, controlled reboot windows, and UPS shutdown if
   available.
4. Put OS/hot data on SSD; mount any HDD only for cold archive/backup; enable
   free-space and health alerts.
5. Create the separated service identities, SSH keys, directory ownership,
   writable-path allowlists, and human-only release/signing process.
6. Install Tailscale, restrict access to Max, verify SSH from a second device,
   and confirm there is no public SSH/control port.
7. Install XFCE and `xrdp` per §6.1: bind `xrdp` to the tailnet interface only,
   leave its units disabled at boot, run sessions as Max's administrative login,
   and verify from the Mac that the desktop is reachable over the tailnet and
   refused from the LAN and the public interface.
8. Install the pinned Rust/build/runtime toolchain and reproduce the protected
   release from a clean checkout.
9. Deploy the signed content-addressed core read-only and create candidate,
   state, artifact, log, and backup paths outside it.
10. Install and harden the `systemd` services/timers; test boot start, bounded
    restart, no-overlap leases, resource limits, and trusted-work preemption.
11. Deploy the Slack private-channel adapter per §7.2. The provider choice is
    already resolved by D81 — no bake-off is run, and no second adapter is built.
12. Add the three mutating channel commands one by one only after identity,
    confirmation, expiry, idempotency, replay, and audit tests pass.
13. Configure one provider adapter and auth path; test bounded non-interactive
    failure, timeout, rate limit, invalid output, and credential expiry. Add a
    second provider only to prove the seam when useful—not as standing complexity.
14. Configure GitHub/off-machine backup and prove restore on a clean environment.
15. Run sustained CPU/RAM/disk/thermal benchmarks; tune worker count, batch size,
    memory cap, and research priority from evidence.
16. Run shadow operation and the Phase 5 commissioning drills before Max
    authorizes the new appliance.

## 10. Required operational acceptance evidence

Before unattended cutover, retain evidence that:

- the host boots after power loss and every required unit reaches the correct
  state without duplicate jobs;
- killing each service at every important transition produces recovery rather
  than silent loss or double mutation;
- research saturation cannot delay verified data, the trusted signal, Active
  recertification, recovery, or critical notification work;
- sustained load does not thermally throttle into missed deadlines or corrupt
  results;
- swapping, disk-full, SSD/HDD failure, clock error, internet loss, provider
  outage, channel outage, Tailscale outage, and GitHub outage reach explicit safe
  states;
- the resident model, channel process, and candidate worker cannot write protected
  core, read forbidden secrets, or directly mutate Gold/Active;
- channel identity spoofing, replay, expired confirmation, duplicate delivery,
  malformed command, and free-form “approval” are rejected visibly;
- conversation status and the durable ledger reconcile after adapter restart;
- `systemd` catches a wedged/restarting service and the doctor detects failures
  that a process-alive check misses;
- Max can recover through Tailscale/SSH when the channel and model are both down;
- the graphical surface is reachable from the Mac over the tailnet, is refused on
  the LAN and public interfaces, does not start itself at boot, and — the
  ordering that matters — **SSH recovery still works with the graphical stack
  stopped, broken, or mid-upgrade**; and
- a GitHub-only outage produces `degraded_backup` and still delivers the valid
  signal on time while blocking Gold publication and Active changes; queued
  events reconcile correctly on recovery;
- a material TECL product-change event alerts immediately, suspends new trusted
  signals, and stales affected certificates without auto-substituting a ticker;
  and
- an owner-approved, isolated, non-authoritative clean-machine restore reproduces
  the last acknowledged authority and Gold state, then is destroyed or resealed.

## 11. Deployment calibration still required

These are measured commissioning values, not open product-policy questions:

- actual tower hardware inventory and whether Debian has every needed driver;
- SSD/NVMe availability and the cold-backup device;
- sustainable physical/logical worker count, batch size, memory limit, reserve
  capacity, and thermal ceiling;
- exact `systemd` resource-control and service-hardening directives;
- post-close trusted-job deadline and controlled update/reboot window;
- selected channel, stable Max identity, room IDs, required scopes, notification
  routing, and the rejected provider's removal/non-running state;
- provider selected by Max, subscription/API authentication, usage budget, token
  expiry monitoring, and provider-specific bounded invocation flags;
- backup destination, encryption, snapshot size/retention, and restore SLA; and
- whether OpenClaw supplies any measured value not already provided by the
  selected channel without broadening authority.

None of these values changes what Gold means or permits the agent to choose its
own language, methodology, permissions, or trading authority.

## 12. Primary-source research snapshot

The implementation agent must recheck version-sensitive facts during
commissioning. Sources reviewed on 2026-07-21:

- [Debian releases](https://www.debian.org/releases/) and
  [Debian 13 release information](https://www.debian.org/releases/stable/)
- [Debian systemd services](https://wiki.debian.org/systemd/Services)
- [Claude Code setup and Debian support](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- [Claude Code non-interactive CLI](https://docs.anthropic.com/en/docs/claude-code/cli-usage)
- [Claude Code authentication and `setup-token`](https://code.claude.com/docs/en/team)
- [Claude scheduled tasks and their limits](https://code.claude.com/docs/en/scheduled-tasks)
- [Claude Code Remote Control](https://code.claude.com/docs/en/remote-control)
- [Claude Code in Slack](https://code.claude.com/docs/en/slack)
- [Slack Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode/)
- [Buzz repository and current feature status](https://github.com/block/buzz),
  [architecture](https://github.com/block/buzz/blob/main/ARCHITECTURE.md),
  [security model](https://github.com/block/buzz/blob/main/SECURITY.md),
  [agent/tool model](https://github.com/block/buzz/blob/main/VISION_AGENT.md),
  and [JSON CLI](https://github.com/block/buzz/tree/main/crates/buzz-cli)
- [Tailscale Linux installation](https://tailscale.com/docs/install/linux) and
  [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh)
- [OpenClaw gateway architecture](https://docs.openclaw.ai/concepts/architecture),
  [remote access](https://docs.openclaw.ai/gateway/remote),
  [Slack transport](https://docs.openclaw.ai/channels/slack),
  [automation](https://docs.openclaw.ai/automation),
  [command queue](https://docs.openclaw.ai/concepts/queue), and
  [ACP host-runtime warning](https://docs.openclaw.ai/tools/acp-agents)

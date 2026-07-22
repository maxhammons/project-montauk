# Montauk 3.0 Research — Stream 9: Durability, availability, and dead-man monitoring

## 1. One-page plain-English conclusion

Montauk's durability problem has two halves that are easy to conflate and must be
kept separate: **"don't lose an acknowledged result"** and **"don't let a copy
mechanism block a valid trade signal."** The charter already states the first
half plainly — authority, signal, approval, and Gold mutations must be
"durably journaled and replicated before acknowledgement," with GitHub as the
off-machine recovery path and a maximum one-hour background sync bound
[Evidence: primary, `charter.md` §7 "System architecture," lines 610–615;
§11 "Storage, audit, and failure memory," lines 930–938]. The open design
question is *what replicates synchronously (must finish before Montauk says
"done") versus asynchronously (can lag and just needs a bounded, alerted
window)* — because if "synchronous" is read as "wait for GitHub," a home
internet blip or a GitHub incident would silently veto a correct post-close
`risk_on`/`risk_off` call, which the charter explicitly does not want.

**The resolution:** split state into classes and give each its own replication
tier, mirroring how the codebase already separates a transactional control
database from bulk experiment history and content-addressed artifacts
(`implementation-plan.md` §7, "Persistence model"). Authority-critical state
(current signal, Active/Recommended pointer, Gold publication, approvals)
replicates **synchronously to a second local device on the same machine** — a
real second disk/partition with its own fsync path, fsync'd before
acknowledgement, **not** an application-level dual-write (which cannot
atomically guarantee both legs land together; Section 8 #6). This is fast,
has no network dependency, and satisfies "replicate before acknowledgement"
without depending on GitHub's availability. GitHub replication of that same
state happens **asynchronously** on the existing ≤1-hour cadence, and its
staleness or failure is a *monitored, alerted* condition — never a gate on
emitting today's signal. Bulk, re-runnable research history is lower stakes
by charter design ("in-flight computations may be rerun") and can tolerate a
longer, cheaper, asynchronous path to object storage. The signing key and
channel/provider credentials get a third, deliberately manual model: never
auto-replicated anywhere, recovered only through a rehearsed human ceremony.

**Concrete example.** Suppose GitHub is down for six hours the evening of a
verified close. Under the recommended design, the local control database
already fsync'd tonight's signal and Gold-state change to the second local
disk before Montauk told the channel "signal ready" — Max still gets a
correct, on-time `risk_on`/`risk_off` instruction. Separately, the doctor
service notices GitHub push attempts have failed past the bound and raises
the required "backup overdue" alert. No trade decision was suppressed; the
only consequence is a temporarily stale off-machine copy, visible and being
retried, not silently accepted.

**What Max should decide, concretely:** (1) which independent, **read-only**
heartbeat service and alert channel monitor Montauk's pulse — read-only
meaning it can only receive outbound pings, with no credential able to write
back into Montauk's command inbox (Section 8, #1); (2) whether to add a
second, WORM-style off-machine copy beyond GitHub (Section 8, #2); (3) a
designated clean-machine restore target (Section 8, #3); (4) the RPO/RTO
numbers to freeze per state class (Section 8, #4); and (5) whether the
synchronous second copy is a real second device or a dual-write (Section 8,
#6).

## 2. Evidence-quality table

| Claim | Evidence type | Source | Strength | Transfers to TECL? | Notes |
|---|---|---|---|---|---|
| RPO = "point in time to which data must be recovered"; RTO = "length of time components can be in recovery before mission impact" | primary regulatory | [NIST SP 800-34 Rev. 1 — RPO](https://csrc.nist.gov/glossary/term/recovery_point_objective), [RTO](https://csrc.nist.gov/glossary/term/recovery_time_objective) | Strong | N/A — infra/ops definition | Directly fetched; standard federal contingency-planning vocabulary. |
| 3-2-1 rule: 3 copies, 2 media types, 1 offsite; test restores; encrypt backups | regulatory/secondary | [CISA — Back Up Business Data](https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/back-up-business-data), [CISA data backup options](https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf) | Moderate | N/A — infra doctrine | cisa.gov blocks direct fetch (403) on the HTML page, PDF, and an archive.org mirror, all re-tried this revision. Confirmed only via independent search-summary corroboration — held at Moderate deliberately, the weakest-sourced claim this architecture leans on (§6). |
| GitHub recommends objects ≤1 MB, hard-blocks files >100 MiB in ordinary Git history, recommends `.git` ≤10 GB; separately, Git *warns* (doesn't block) at >50 MiB | product-primary | [Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits) (1MB/100MB/10GB), [About large files on GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) (50 MiB warning) | Strong | N/A — infra | Both re-fetched this revision. **Correction**: the prior draft attached the 50 MiB fact to the repository-limits URL, which doesn't state it — it's on the second, separate page, now split out and cited correctly. |
| Git LFS free tier = 10 GiB storage + 10 GiB bandwidth/month (Free/Pro); metered beyond quota | product-primary | [GitHub Docs — Git LFS billing](https://docs.github.com/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage) | Strong | N/A — infra | Directly re-fetched this revision (previously search-summary only). Matches the charter's LFS guidance; quota is small relative to Montauk's claimed research volume (§6). |
| S3 Object Lock provides WORM retention on versioned objects; requires Versioning; compliance mode cannot be shortened/deleted by any principal, including root, before expiry | product-primary | [AWS Docs — Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) | Strong | N/A — infra | Directly fetched, full page. Closest primary analogue to "immutable encrypted snapshot" storage. |
| restic: AES-256-CTR + Poly1305-AES authenticated encryption; append-only remote access blocks delete/rewrite — **except** `forget`/prune can still orphan legitimate snapshots under append-only credentials | primary (project docs) | [restic design document](https://restic.readthedocs.io/en/v0.13.1/design.html) | Strong | N/A — infra | Directly fetched. The `forget` caveat is material: an append-only credential alone is not sufficient; `forget`/prune must be withheld from any unattended credential. |
| borgbackup: append-only mode still permits client-side `delete`/`prune` (a repository-storage property, not a full command lockout); `keyfile`/`repokey` need an offsite key backup or the repo is permanently unreadable | primary (project docs) | [Borg init docs](https://borgbackup.readthedocs.io/en/stable/usage/init.html) | Strong | N/A — infra | Directly fetched. Key-recovery is a distinct design problem, not a side effect of data backup. |
| SQLite WAL: commits are durable once flushed with `synchronous=FULL`; default `NORMAL` sacrifices durability across power loss; WAL requires all processes on one host, not a network filesystem | primary (project docs) | [SQLite — Write-Ahead Logging](https://sqlite.org/wal.html) | Strong | N/A — infra | Directly fetched. Bounds the architecture: the local second copy cannot be a naive network-mounted SQLite WAL. |
| OpenZFS: per-block checksums detect read-time corruption; corrupt blocks auto-repair from redundancy; `scrub` proactively checks/repairs latent corruption | primary (project docs) | [OpenZFS — Checksums](https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Data%20Storage/Checksums.html) | Strong | N/A — infra | Re-fetched at a corrected URL (prior redirected); confirms verbatim. Baseline `ext4` (lines 95–96) has **no** block checksumming — does not transfer without deliberately adopting ZFS. |
| "Monthly-to-weekly" scrub cadence is common ZFS vendor guidance, not a figure the OpenZFS docs themselves state | [Inference] secondary | Oracle Solaris ZFS admin guidance; vendor best-practice pages | Weak–Moderate | N/A — infra | Direct fetch confirms OpenZFS gives no scrub-interval figure; downgraded from the prior draft's implicit primary framing to an explicit inference, per the review's grading-consistency finding. |
| Parchive/PAR2 (Reed–Solomon) creates recovery blocks that reconstruct a file after localized corruption without a second whole copy | primary (project docs) | [Parchive](https://parchive.github.io/), [par2cmdline](https://github.com/Parchive/par2cmdline) | Strong | N/A — infra | A cheap, filesystem-independent corruption-repair layer substituting for the ZFS gap above. |
| healthchecks.io / Dead Man's Snitch: independent SaaS heartbeat services — a job pings a unique URL on success; a missed ping past a grace period raises an alert; explicitly marketed as a dead-man's-switch pattern | product-primary | [healthchecks.io docs](https://healthchecks.io/docs/), [Dead Man's Snitch](https://deadmanssnitch.com/) | Strong | N/A — infra | Both directly fetched. Pattern is outbound-ping-only by construction — structurally consistent with "read-only" (§8 #1). |
| Montauk's own current-contract requirements: replicate authority/Gold/signal mutations before acknowledgement; ≤1-hour max background GitHub sync; ordinary Git blobs below GitHub's 100 MiB limit; backup-overdue and corruption are critical alerts; restore drills must prove the copies, not the push exit code | product-primary (internal) | `charter.md` §7 (lines 600–615) and §11 (lines 926–938), `implementation-plan.md` §7 (lines 495–541), `decisions.md` D17 (lines 307–325) / D37 (lines 706–729) | Strong | N/A — this *is* the governing internal contract | Line ranges corrected this revision: lines 610–615 are actually in §7 ("System architecture"), not §11 as the prior draft claimed — only 926–938 fall in §11. `decisions.md` ranges tightened to exact header spans. Not external evidence, but the binding spec Stream 9 must satisfy. |
| Repo's actual current scale: `.git` ≈456 MB, `spike/` run output ≈1.4 GB, 235 numbered run directories deep (highest run: 287) | primary (internal, direct measurement) | `du -sh .git spike`; `ls spike/runs \| wc -l` | Strong | N/A — direct measurement of this project | Re-measured this revision: sizes match the prior draft, but its "~150 numbered runs" was stale — the true count is 55–90% higher, meaning the volume trajectory is *faster* than previously cited, which makes the "GitHub/LFS is insufficient" conclusion stronger, not weaker. |

## 3. Recommended Montauk experiment(s)

Stream 9's claims are software/ops reliability facts, not statistical
inferences about markets. Each experiment below is a fault-injection drill
with a **preregistered estimand** (the exact thing being counted, frozen
before running) and a **stopping rule** (when the drill is done and how
"pass/fail" is decided) — the same discipline the validation-hardening
document demands of statistical gates, applied to recovery engineering.

**Experiment 9.1 — Kill-at-every-transition durability drill.**
*Estimand:* across a predeclared, numbered list of job-transition points
(control-DB commit, local second-device fsync, Gold/authority-state
publication, GitHub push, notification-outbox write), the count of trials (out
of N) in which killing the process at that exact point produces either (a) an
acknowledged mutation that disappears, or (b) a duplicated/replayed authority
mutation. **Process-kill only** — a second local device that completes its
write but silently returns wrong content (a degraded disk) is a separate,
currently untested failure mode covered by Section 4's read-back control and
flagged in Section 6. *Freeze before running:* the transition
list, the definition of "acknowledged," and that both (a) and (b) count as
failures regardless of probability. *Stopping rule:* run ≥20 independent kill
trials per transition point; any single (a) or (b) event stops the drill
immediately and is reported as a defect, not averaged into a rate.

**Experiment 9.2 — Clean-machine restore RTO measurement.**
*Estimand:* wall-clock time from "start on a freshly provisioned machine with
only GitHub access" to "last acknowledged Gold/authority state reproduced
byte-identically, verified by checksum, and no protected-core write path
enabled by accident." *Freeze before running:* the exact target state
(a specific frozen Gold/authority snapshot chosen in advance), the checksum
method, and the machine image used. *Stopping rule:* three independent restore
attempts (ideally staggered in time so undocumented tribal knowledge decays
naturally); any attempt that fails to reproduce the exact frozen state fails
the whole drill and blocks sign-off until fixed and rerun — do not average a
failed attempt away against two successes.

**Experiment 9.3 — Corruption-detection sensitivity and specificity.**
*Estimand:* detection rate and false-negative rate of the manifest-checksum +
PAR2-verify pipeline across a predeclared seeded-fault set (single-bit flip,
truncation, silent zero-fill, and a stale-but-correctly-named file swap),
applied separately to a Gold-tier snapshot and a bulk experiment-ledger
partition. *Freeze before running:* the exact fault catalogue and count (e.g.,
50 seeded faults, split evenly across fault types and tiers) before any
detector is run against them. *Stopping rule:* run the full predeclared set
once; report the exact detected/missed counts; do not add more seeded cases
after seeing partial results, and any single missed fault is reported as a
defect in the checker, not smoothed into an aggregate pass rate.

**Experiment 9.4 — Missed-heartbeat alert-path latency and coverage.**
*Estimand:* time-to-alert-delivery and false-negative rate of the external
dead-man switch under four predeclared failure scenarios: (a) Debian host
powered off, (b) Tailscale unreachable but host up, (c) GitHub unreachable but
host up, (d) home internet fully down. *Freeze before running:* the expected alert channel, the configured grace
period, the maximum acceptable delay (e.g., ≤2× grace period), and a one-time
check that the monitoring service's credential is receive-only — pings in,
alerts out, no scope able to write back into Montauk's command inbox —
confirmed by attempting exactly that write and expecting rejection. *Stopping
rule:* 4 scenarios × 3 trials = 12 predetermined trials; report per-scenario
delivered/missed and observed latency; any missed alert, or a successful
write-back during the credential check, is an immediate defect.

**Experiment 9.5 — Signal continuity under a deliberate GitHub blackout.**
*Estimand:* whether a valid post-close trusted signal is generated and
delivered on schedule when GitHub is deliberately made unreachable (DNS/IP
block) for a full session window, compared bit-for-bit against a control run
with GitHub reachable. *Freeze before running:* that "signal timestamp and
content identical to control" is the sole pass criterion, and that this runs
against a shadow/staging strategy, never the live Active pointer. *Stopping
rule:* this is a deterministic code-path test, not a statistical one — a
single run with a matching control is sufficient to pass, but the drill must
be repeated once after any future change touching the recovery or signal-
emission path, permanently, as a regression gate.

## 4. Null, defect, and planted-signal controls

- **Positive fixture must pass, always.** A small, permanently retained
  known-good control-DB snapshot + matching sha256 manifest (mirroring the
  pattern already used in `data/manifest.json`) must verify clean on every run
  of the integrity checker. If it ever fails, the checker itself is broken.
- **Seeded-negative fixtures must fail, always.** Deliberately corrupted
  siblings of the positive fixture (bit-flip, truncation, zero-fill, stale
  swap — see Experiment 9.3) must be caught on every run. A checker that
  silently passes a seeded-negative fixture is the exact "silent fallback"
  the charter prohibits (`charter.md` line 926) and is a release-blocking
  defect, not a tuning issue.
- **"Push succeeded" is not "copy verified" — for the local second device
  too.** Per the charter's own instruction that "restore drills must prove
  the copies, not merely prove that a push command ran" (`charter.md` line
  937), every backup cycle reads back the remote HEAD/object hash against the
  local source hash, not just the push exit code. The same discipline must
  extend to the synchronous local write itself: an `fsync()` success does not
  prove disk 2's *content* matches disk 1 (a degraded disk can silently store
  the wrong bytes). Control: every synchronous write is followed by a
  read-back-and-hash-compare before acknowledgement. A planted test simulates
  a partial-success GitHub push (stale remote content, exit 0) and a
  partial-success local write (corrupted content, syscall success) and
  confirms the read-back — not the exit code — flips each status to failed.
- **Independent heartbeat monitor must be read-only.** The external dead-man
  switch (Section 8 #1) must hold no credential able to write back into
  Montauk's command inbox — a monitoring dependency that can mutate state is
  a new attack surface, not just an observer. Verify by attempting exactly
  that write with the service's own credential (Experiment 9.4) and
  confirming rejection.
- **`forget`/prune must be withheld from unattended credentials.** restic's
  own docs note an append-only remote does not stop `forget` from orphaning
  legitimate snapshots [Evidence: primary, restic design doc]. Control: the
  unattended backup service's credential must be incapable of invoking
  `forget`/`prune`/delete at all — verify by attempting those operations with
  the live credential and confirming rejection. For Borg, enforce
  `append-only` at the SSH-forced-command layer, not only a client-side flag.
- **Dead-man switch must self-test on a schedule, not just at commissioning.**
  A quarterly fire drill that deliberately stops heartbeats and confirms the
  alert fires is required — a path that passed once and silently rotted
  (expired key, changed email) is indistinguishable from no alert path until
  the day it's needed.
- **Key-recovery rehearsal without the live key.** Periodically reconstruct
  release-signing capability using *only* the offline backup copy, on a
  machine that never held the live key, confirming the resident
  `montauk-agent`/`montauk-core` identities were never queried — testing that
  "Max's signing key is not resident in an unattended service"
  (`debian-host-agent-and-channel-operations.md` line 155) holds in practice.

## 5. False-Gold and false-rejection consequences

Stream 9 has its own version of the false-positive/false-negative asymmetry,
distinct from a bad strategy passing validation:

- **False "recovery succeeded" (silent loss undetected).** The worst case:
  Montauk resumes operation believing its authority state is intact when it
  is actually stale or corrupted — e.g., it forgets a strategy was already
  revoked, replays an already-executed Active switch, or acknowledges a
  mutation against a second-device write that silently completed with wrong
  content (Section 4's read-back gap). Cost: real capital risk, not a
  research artifact, and silent by construction — Max has no way to know to
  distrust the state.
- **False "backup is fine" during an actually-stale/failed off-machine sync.**
  If GitHub replication silently falls behind with no alert, and the local
  disk then fails for an unrelated reason, the off-machine copy is stale or
  missing exactly when needed. Cost: total loss of Gold provenance and
  research history, forcing full recertification from scratch.
- **Over-conservative failure mode (the assignment's named risk).** If the
  design is built naively — e.g., signal emission waits on a GitHub push — a
  transient GitHub incident or ISP blip needlessly suppresses a correct
  post-close call. Cost: forgone gains, and it quietly retrains Max to
  distrust or work around Montauk's caution next time it hesitates
  legitimately.
- **Missed-heartbeat false negative.** If the dead-man switch itself silently
  stops working (expired credential, provider policy change), the appliance
  can be down for days unnoticed — in a single-user system with no team
  backstop, this is the single most severe availability failure mode.
- **Missed-heartbeat false positive (alert fatigue).** A switch tuned too
  tight (e.g., grace period shorter than normal weekend gaps) trains Max to
  ignore alerts, defeating the mechanism exactly when a true failure occurs.

The asymmetry that should govern Stream 9's defaults: **silent loss and silent
monitoring failure are strictly worse than a loud, occasionally-wrong alert.**
Bias every design choice toward "fail loud and visible," even at the cost of
occasional false alarms, because a single silent failure in this domain can
be a real, undetected capital-affecting event rather than a research
inconvenience.

## 6. Assumptions and power/limits

- **These are engineering reliability claims, not asset-return statistics.**
  The estimands in Section 3 are pass/fail counts from deliberately run
  drills, not backtested distributions. A clean pass on Experiment 9.1 means
  "no defect found in N trials," never "proven impossible" — few real drills
  will ever run on a single-user appliance, so any claim of "P(silent loss) ≈
  0" is only as strong as the drills actually executed and must be labeled
  [Inference] beyond what was tested.
- **Single machine, single user, no hot standby.** Montauk 3.0's baseline is
  one Debian tower (`debian-host-agent-and-channel-operations.md` §2), with
  no redundant compute to fail over to. A total hardware loss's RTO includes
  replacement-hardware procurement time, which the charter places outside
  3.0 scope (`README.md` line 354). Without a predesignated restore target
  (Section 8 #3), the true disaster RTO has an unbounded tail — Experiment
  9.2 can only measure "restore onto a machine we already have."
- **GitHub's own availability is outside Montauk's control.** No design
  choice changes that third-party risk, only how much it can hurt. Framing
  GitHub failures as "monitored and alerted, never signal-blocking" (Section
  1) is the correct response to a risk Montauk cannot eliminate.
- **`ext4` has no built-in block checksumming.** The documented storage
  default is `ext4` (lines 95–96). ZFS's checksum/scrub-repair mechanism is
  directly confirmed (Section 2), but its "monthly-to-weekly" cadence is
  industry convention, not something the OpenZFS docs themselves state —
  labeled [Inference]. Neither transfers to the deployed filesystem unless
  Max adopts ZFS deliberately — corruption detection for the near-term
  default must live at the application/backup-tool layer (manifest
  checksums, restic/Borg hashes, PAR2 parity).
- **The synchronous-replication mechanism has an untested failure mode.**
  Section 1 recommends a real second device over a dual-write because a
  dual-write cannot atomically guarantee both legs land together if disk 2
  fails or lags at the acknowledgement instant. Even with a real device,
  Experiment 9.1 only tests process-kill at the fsync point — it does
  **not** yet test a second device that completes the write but silently
  returns wrong content (bounded by SQLite WAL's own host-local-only
  guarantee [Evidence: primary, sqlite.org], which rules out a naive
  network-mounted WAL as the mechanism). Section 4's read-back control
  targets this gap but has not been run as a drill; until it has, "RPO = 0"
  (Section 8 #4) is a design target, not a measured result.
- **"RPO = 0" is qualified by disaster scope.** It holds for process/software
  failure, not for a physical event destroying both local copies at once
  (Section 8 #5), in which case the async GitHub replica is the only
  survivor and the true RPO is up to its 1-hour bound.
- **Append-only is a storage property, not a full command lockout.** Both
  restic and Borg's docs note naive append-only access still permits
  `forget`/`prune`-style operations to orphan legitimate data [Evidence:
  primary, both projects' docs] — the explicit control in Section 4 is
  required, not just the feature flag.

## 7. Required fixtures and durable artifacts

- **Golden control-DB fixture.** A small, permanently retained known-good
  snapshot of the control database plus a manifest (sha256, byte count,
  timestamp) in the same style as `data/manifest.json`. Expected result:
  verify passes; a full restore from it reproduces byte-identical content.
- **Seeded-negative fixture set.** Deliberately damaged siblings of the
  golden fixture: single-bit flip, truncated file, correct-size all-zero
  file, and a stale file under the current filename. Each carries an
  expected result of "FAIL / detected," stored beside the positive fixture so
  the checker is itself regression-tested every time it changes.
- **Restore-drill ledger.** A permanent, human-readable, append-only log of
  every restore drill: timestamp, operator, which copy was used (local
  second device, GitHub, or the optional immutable object-storage tier),
  target machine, hash comparison result, and pass/fail — directly
  implementing "restore drills must prove the copies" (`charter.md` line
  937).
- **Local second-device read-back verification log.** A companion log,
  populated on every synchronous write (not just drills), recording the
  hash comparison between the primary write and the second-device read-back
  and whether it matched before acknowledgement — the fixture that makes
  Section 4's local-write control auditable on an ongoing basis, not only
  during a deliberate drill.
- **Dead-man-switch fire-drill log.** Dated record of each deliberate
  heartbeat-suppression test (Section 4) and its measured alert latency,
  retained so a silently rotted alert path (expired key, changed contact)
  would show up as a gap in the schedule, not just an assumption of health.
- **Key-recovery ceremony record.** A dated, secret-free log of each rehearsal
  of the signing-key recovery process: which offline artifact was used, how
  long the ceremony took, and confirmation that no unattended service was
  queried for key material during the rehearsal.
- **PAR2 parity sidecars for cold archives.** For HDD-tier cold snapshots and
  the encrypted off-machine repository, retain PAR2 recovery data alongside
  the archive so localized corruption can be repaired without needing a full
  second whole copy, independent of whatever filesystem-level protection is
  or isn't in place.

## 8. Unresolved owner decisions

1. **Which independent, read-only heartbeat provider and which alert
   channel(s)?** Recommended default: healthchecks.io (or Dead Man's Snitch),
   with an alert channel genuinely outside Montauk's own chat channel and
   outside Tailscale/GitHub — e.g., plain email plus a phone push — so a
   Slack/Buzz, Tailscale, or GitHub outage cannot also hide that Montauk
   itself is dead. Both providers are outbound-ping-only by construction,
   which structurally satisfies "read-only" — but this should be verified,
   not assumed (Section 4, Experiment 9.4). Tradeoff: a paid tier costs a few
   dollars a month for more integrations/redundancy; the free tier is likely
   sufficient for a single daily check-in but has fewer failover channels.

2. **Add a second, WORM-style off-machine copy beyond GitHub for the
   authority/Gold tier?** GitHub gives an off-machine copy but not true
   immutability — a compromised or misused credential can still force-push or
   delete history. Recommended default: one small encrypted restic or Borg
   repository (control-DB snapshot and Gold artifacts only, not the bulk
   ledger) pointed at object storage with Object Lock or an append-only
   remote, `forget`/delete withheld per Section 4. Tradeoff: modest recurring
   cost and one more moving part, versus real protection against credential
   compromise or an accidental destructive push, which GitHub-only backup
   does not cover.

3. **A designated clean-machine restore target.** Recommended default: one
   documented, periodically-rehearsed cloud-VM restore recipe (Experiment
   9.2), purely a bounded RTO drill target rather than a live failover
   system, so "restore from GitHub" has a concrete rehearsed home. Tradeoff:
   small ongoing drill overhead versus an otherwise open-ended disaster RTO.

4. **Concrete RPO/RTO numbers to freeze per state class.** The charter already
   fixes GitHub sync at ≤1 hour for the authority tier; Stream 9 needs Max to
   set the remaining numbers explicitly. Recommended default, **scoped
   explicitly rather than left as a bare figure**: RPO = 0 for
   authority/Gold/signal state against process/software failure (crash, kill,
   bug) via the local synchronous second copy — **but RPO ≤ 1 hour, not 0,
   under a physical-disaster scenario destroying both local copies at once**
   (#5), since the async GitHub replica becomes the sole survivor; RPO ≤ 24
   hours for the bulk research ledger; RTO ≤ 24 hours for a full
   clean-machine restore onto the target from #3. Tradeoff: tightening these
   (especially full-machine RTO, or closing the physical-disaster RPO gap by
   separating the two local copies) needs more pre-staged infrastructure and
   drill discipline; loosening risks a longer visible gap during a genuine
   disaster.

5. **Does the local "second copy" need to be physically separate from the
   tower, not just a second internal disk?** A second internal HDD satisfies
   the 3-2-1 rule's "two different media" cheaply and is already in the
   storage plan (`debian-host-agent-and-channel-operations.md` §2.2), but does
   not by itself protect against fire, theft, or a shared power-supply failure
   taking out both local copies at once — GitHub (and optionally #2) already
   supplies the "one offsite" leg. Recommended default: accept the
   second-internal-disk model as sufficient, but Max should explicitly
   confirm he accepts both local copies sharing one physical location and
   one power circuit.

6. **Which synchronous-replication mechanism: a real second local device, or
   an application-level dual-write?** Section 1 recommends the former to
   avoid the dual-write atomicity gap (disk 1 succeeds, disk 2 fails or lags
   at the acknowledgement instant, no rule for which copy wins) — but neither
   is implemented yet, so this is a real open choice. Recommended default: a
   real second local device (its own filesystem and fsync path) plus the
   Section 4 read-back verification control, so a degraded-but-"successful"
   write is caught rather than trusted. Tradeoff: a real second device is
   simpler to drill than a dual-write shim, but the read-back check adds
   latency to every synchronous write — acceptable given the alternative is
   an unverified copy.

## References

- [NIST SP 800-34 Rev. 1, via CSRC Glossary — Recovery Point Objective](https://csrc.nist.gov/glossary/term/recovery_point_objective) — Primary (federal standard).
- [NIST SP 800-34 Rev. 1, via CSRC Glossary — Recovery Time Objective](https://csrc.nist.gov/glossary/term/recovery_time_objective) — Primary (federal standard).
- [CISA — Back Up Business Data](https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/back-up-business-data) — Primary/regulatory (403 on direct fetch, PDF, and archive.org mirror; search-summary corroboration only — Moderate strength).
- [CISA — Data Backup Options (PDF)](https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf) — Primary/regulatory (same fetch caveat).
- [GitHub Docs — Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits) — Primary (directly fetched; 1 MB/100 MB/10 GB guidance only — no 50 MiB warning).
- [GitHub Docs — About large files on GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) — Primary (directly fetched; the actual source of the 50 MiB warning, mis-cited to the page above in the prior draft).
- [GitHub Docs — About billing for Git Large File Storage](https://docs.github.com/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage) — Primary (directly re-fetched this revision, upgraded from search-summary only).
- [AWS Docs — Locking objects with Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) — Primary (directly fetched, full page).
- [restic design document (v0.13.1)](https://restic.readthedocs.io/en/v0.13.1/design.html) — Primary (directly fetched).
- [Borg — `borg init` usage documentation](https://borgbackup.readthedocs.io/en/stable/usage/init.html) — Primary (directly fetched).
- [SQLite — Write-Ahead Logging](https://sqlite.org/wal.html) — Primary (directly fetched).
- [OpenZFS — Checksums and Their Use in ZFS](https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Data%20Storage/Checksums.html) — Primary (directly re-fetched at corrected URL; no scrub-frequency figure — that's labeled [Inference] in Section 2).
- [OpenZFS — System Administration](https://openzfs.org/wiki/System_Administration) — Primary (fetch blocked by bot-protection this revision; retained for reference only, not independently verified).
- [Parchive project](https://parchive.github.io/) — Primary (project site).
- [par2cmdline / libpar2 repository](https://github.com/Parchive/par2cmdline) — Primary (reference implementation).
- [healthchecks.io documentation](https://healthchecks.io/docs/) — Primary (directly fetched).
- [Dead Man's Snitch](https://deadmanssnitch.com/) — Primary (directly fetched).
- Montauk 3.0 internal governance (Primary, internal): `charter.md` §7 (lines 600–615), §11 (lines 926–938), §16 (lines 1147–1153); `implementation-plan.md` §7 "Persistence model" (lines 495–541) and Workstream 2B/3B (lines 725–798); `decisions.md` D17 (lines 307–325), D37 (lines 706–729); `debian-host-agent-and-channel-operations.md` §2.2–2.4, §3 (lines 85–163); `README.md` (lines 179, 354).
- Repo direct measurement (Primary, internal): `.git` (≈456 MB), `spike/` output (≈1.4 GB), run-directory count (235, highest #287) via `du -sh` and `ls spike/runs | wc -l` — the run count corrects a stale "~150" in the prior draft.

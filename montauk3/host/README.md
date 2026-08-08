# Build Phase 1 — appliance readiness

Everything needed to stand the Debian box up, written and idempotent.

**Not the same thing as "Phase 1" in `implementation-plan.md`.** That one proves
the Gold exam and runs on the Mac. This one prepares the machine. They run in
parallel (D127) and neither blocks the other. Two things called Phase 1 is
exactly the kind of vocabulary collision that produced the cutover mess, so the
names are kept apart deliberately: **Build Phase 1** is always the appliance.

## Done means

Every item below is either **done** or **needs the physical machine**. Nothing
is "half configured" and nothing is waiting on a decision.

`provision/50-verify.sh` exits zero. Until it does, Build Phase 1 is not done.

---

## What needs the physical machine

Three things. Everything else runs over SSH from the Mac.

| # | Item | Why it cannot be scripted from here |
|---|---|---|
| 1 | Run `bootstrap.sh` | The box has no SSH and no tailnet yet. Chicken and egg: something has to open the first door, sitting at the machine. |
| 2 | Approve the Tailscale login | `tailscale up` prints a URL. Authorizing the machine onto your tailnet is an identity decision only you can make. |
| 3 | Set BIOS power-on after AC loss | Firmware, not the OS. Without it a power cut leaves the appliance off until somebody presses the button — and every no-sleep setting is moot. |

Borrow a monitor and keyboard once. Items 1 and 2 take about five minutes
together; item 3 is a reboot into setup.

---

## Order

Run these from the repo, copied to the box (or cloned there).

```bash
# ---- at the machine, once ----
sudo bash bootstrap.sh              # ssh + tailscale + join the tailnet

# ---- from the Mac, over ssh, in this order ----
sudo bash provision/00-base.sh        # no sleep, Pacific clock, no surprise reboots
sudo bash provision/10-identities.sh  # the five service accounts
sudo bash provision/30-storage.sh     # /var/lib/montauk + the core boundary
sudo bash provision/40-desktop.sh     # XFCE + xrdp, tailnet-bound, off at boot
sudo bash provision/20-firewall.sh    # LAST — it closes doors
sudo bash provision/50-verify.sh      # must exit 0
```

`20-firewall.sh` runs last on purpose. It is the only script that can lock you
out, so it goes after everything it needs to protect already exists.

All scripts are idempotent. A partial failure is safe to re-run from the top.

---

## Using the screen

D126: this is a real screen you see and control, including Montauk's own charts.
It is not a component Montauk depends on — every service runs headless.

```bash
ssh you@<tailnet-ip>
montauk-screen on        # bring the desktop up
# connect to <tailnet-ip>:3389 with Microsoft's Windows App (free, Mac App Store)
montauk-screen off       # take it down
```

Off by default at boot. An idle appliance has zero RDP sockets listening, which
keeps both the attack surface and the two-core budget honest.

---

## The lockout hazard, and how it is handled

This box is headless. A firewall admitting only the tailnet is one Tailscale
outage away from carrying a monitor back downstairs.

So **LAN SSH stays open by default.** You close it deliberately, only after
proving the tailnet path works:

```bash
ssh you@<tailnet-ip> 'echo reachable'      # must print: reachable
sudo bash provision/20-firewall.sh --deny-lan-ssh
```

The script refuses `--deny-lan-ssh` outright if Tailscale is down.

Recovery from a physical console, always available:

```bash
sudo nft flush ruleset && sudo systemctl restart ssh
```

---

## What Build Phase 1 does *not* include

Named so the boundary is unambiguous, and so nobody later reports it "done"
having built more or less than this.

- **No Montauk services.** The systemd units in the ops document describe
  programs that do not exist yet. Their identities and directories are created
  here because those are host concerns and D108's boundary must predate the code
  it constrains; the units themselves arrive with the code.
- **No Rust toolchain, no evaluator, no agent, no Slack adapter.** Phases 2–4.
- **No backup replication.** Needs somewhere to replicate *to* and something
  worth replicating.
- **No Montauk 2.0 migration.** D121: 2.0 stays exactly where it runs today.

---

## Acceptance evidence

`50-verify.sh` checks behaviour, not configuration. The protected-core boundary
is proven by attempting a write as `montauk-agent` and requiring it to fail — a
mode bit can look right while an ACL or group membership quietly defeats it.

Two checks cannot be made from inside the machine and are printed as manual
steps when the script passes:

1. **RDP refused off-tailnet.** Disconnect Tailscale on the Mac, `nc -vz <lan-ip>
   3389` must be refused; reconnect and `nc -vz <tailnet-ip> 3389` must succeed.
2. **SSH survives the desktop breaking.** Stop `xrdp` and `xrdp-sesman`; SSH must
   still work. SSH is the independent recovery path and may never depend on the
   graphical stack.

---

## Status

Scripts are written and committed but **have not been run against the real
machine**. They are checked for shell syntax only. First execution is the first
real test, which is why every one of them is idempotent and why the firewall
fails open.

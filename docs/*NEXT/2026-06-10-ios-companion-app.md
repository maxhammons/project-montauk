# iOS Companion App — read-only iPhone surface with regime-flip push + widget

**Goal (Max, 2026-06-10):** a personal (not App Store) iPhone app that is
strictly read-only: real app icon, a home-screen widget showing the current
regime, and a push notification the moment `risk_state` flips. The Mac stays
the sole engine and authority — the phone displays artifacts, nothing more.
This is consistent with the app charter: no remote runners, no strategy logic
off the Mac.

## Why native (not PWA / not Tauri-iOS)

The widget is the forcing constraint. Home-screen widgets are WidgetKit
extensions — native Swift targets only. A PWA can't have one; Tauri's iOS
support can't produce one either. Since the app is read-only ("fetch one JSON,
render it"), a small SwiftUI app + WidgetKit extension is the cheapest path
that satisfies all three requirements (icon, widget, push).

## Hard prerequisite: paid Apple Developer account ($99/yr)

- The APNs (push) entitlement is **not available** on a free Apple ID.
- Free provisioning expires installed apps every 7 days (weekly re-sign ritual).
- Paid account → push capability + 1-year direct installs or 90-day
  auto-updating TestFlight builds.
- No third-party push service needed: the Mac calls Apple's APNs HTTP/2 API
  directly with a `.p8` token key (~30-line script).

## Data contract (already exists)

- `runs/operations/latest.json` → `active_signal.risk_state`
  (`risk_on` / `risk_off`), `risk_on`, `entry_signal`, confidence, active
  champion, `generated_utc`, `data_end_date`.
- `signals/YYYY-MM-DD.json` daily files → flip detection = today's
  `risk_state` vs previous file's.
- App/widget consume a slimmed `status.json` published from these; schema
  additions only, never a second source of truth.

## Architecture

```
 Mac (engine, unchanged authority)
 ├── ops run completes
 ├── publish step: slim status.json → private HTTPS endpoint   ← new
 │     (default: private GitHub repo raw URL + token; zero infra)
 ├── flip detector: risk_state changed vs prior signal file?   ← new
 │     └── yes → APNs HTTP/2 push (direct, .p8 key, no 3rd party)
 ▼
 iPhone (read-only)
 ├── SwiftUI app: dashboard (stance, position, confidence,
 │     flip pressure, freshness, active champion)
 ├── WidgetKit widget (small + medium): risk_on/risk_off w/ color,
 │     confidence, last-updated; ~30-min timeline refresh;
 │     push also triggers immediate widget reload
 └── captures APNs device token once → written where Mac script reads it
```

## Work plan (~2–4 days total)

- [ ] **Phase 0 — prerequisites (Max):** Apple Developer enrollment ($99/yr),
      Xcode installed on the Mac, choose publish location (default: private
      GitHub repo).
- [ ] **Phase 1 — Mac publish step (~2 h):** after each ops run, emit slim
      `status.json` (risk_state, confidence, flip pressure, generated_utc,
      champion name) and push to the private endpoint. Lives in
      `scripts/ops/`; useful + testable before any Swift exists.
- [ ] **Phase 2 — flip detection + APNs push (~half day):** compare current
      `risk_state` vs previous `signals/*.json`; on change, send push via APNs
      HTTP/2 with `.p8` key. Device-token registration file checked into the
      publish repo (or local drop the Mac reads).
- [ ] **Phase 3 — SwiftUI app (~1 day):** single dashboard screen mirroring
      the Tauri dashboard's top strip. Icon reused from
      `app/src-tauri/icons/`. Read-only; no commands, no scheduler controls.
- [ ] **Phase 4 — WidgetKit widget (~0.5–1 day):** small/medium widget,
      stance + color + confidence + freshness; 30-min timeline; reload on push.
- [ ] **Phase 5 — signing + install (~half day, one-time):** provisioning,
      build, install to phone via cable or TestFlight.

## Division of labor

- Claude writes entirely: publish step, flip/push script, all Swift (app +
  widget), schemas.
- Max's hands required: Apple account enrollment, one-time Xcode signing
  clicks, install to phone.

## Guardrails

- Phone is display-only. No `run_job`, no scheduler control, no research
  actions from iOS — ever.
- Published `status.json` is derived from existing artifacts; the Python
  engine remains the single source of truth (charter).
- Private repo/token only; nothing public.

## Decision log

- 2026-06-10: PWA and Tauri-iOS rejected (no widget support). Native
  SwiftUI + WidgetKit chosen.
- 2026-06-10: APNs direct-from-Mac chosen over ntfy/Pushover so the alert
  comes from the Montauk app itself (single icon, single surface).

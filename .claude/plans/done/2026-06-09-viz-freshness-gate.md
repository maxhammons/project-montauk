# Viz freshness stamp + staleness gate (app Refresh rebuilds viz)

- [x] build_viz.py: embed `freshness` block (generated_utc, data_end_date, leaderboard_sha256, signals_latest_date) in bundle + montauk-bundle.json + HTML stamp comment
- [x] viz-engine.js: render freshness badge ("data through YYYY-MM-DD · built HH:MM") + >24h standalone warning banner; clean up on reset()
- [x] src-tauri/main.rs: async `rebuild_viz` command ({ok, stdout_tail, error}) + async `check_viz_freshness` command (stamp vs live leaderboard sha / signal dates); add sha2 dep; register commands
- [x] main.js: Open Viz staleness gate (fresh → open; stale → rebuild then open; rebuild-fail → block with clear error); Refresh flow ensures viz freshness non-blockingly
- [x] Run viz/build_viz.py — confirm freshness block in outputs
- [x] `npm run build && npm run tauri:build` in app/ — Montauk.app bundle built (not installed)

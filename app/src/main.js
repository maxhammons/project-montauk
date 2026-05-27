const fallbackStatus = {
  project_root: "static preview",
  latest_operation: {
    status: "preview",
    steps: {
      data_quality: { summary: { pass: 41, warn: 0, fail: 0, skip: 0, total: 41 } },
    },
  },
  latest_signal: {
    data_end_date: null,
    risk_state: "risk_on",
    risk_on: true,
    entry_signal: false,
    exit_signal: false,
    buy_event: false,
    sell_event: false,
    signal_changed: false,
    signal_change: { changed: false, reason: "unchanged", previous_risk_state: "risk_on" },
    active_champion: {
      strategy: "gc_vjatr_timing_repair",
      metrics: {
        share_multiple: 10.0909,
        real_share_multiple: 1.5469,
        modern_share_multiple: 2.239,
        max_dd: 98.2,
        trades: 44,
      },
      params: {
        fast_ema: 140,
        slow_ema: 160,
        atr_confirm: 3,
        repair_len: 30,
        rsi_floor: 35,
        vix_ceiling: 50,
      },
    },
    validation: {
      verdict: "PASS",
      composite_confidence: 0.7678,
      warnings: ["Static preview. Launch through Tauri to read live ops artifacts."],
    },
    warnings: ["Static preview. Launch through Tauri to read live ops artifacts."],
    blockers: [],
    data_quality: { total: 41, pass: 41, warn: 0, fail: 0, skip: 0 },
  },
  scheduler_detail: {
    jobs: [
      {
        key: "daily",
        label: "Daily update",
        enabled: true,
        job: "daily",
        schedule: { Hour: 13, Minute: 30 },
        next_run_local: null,
        last_run: null,
      },
    ],
  },
  notifications: { pending_count: 0, notifications: [] },
  research_runs: { runs: [], run_count: 0 },
  governance: { state: "active_watch", reasons: ["Static preview"] },
  live_holdout: { status: "ok", snapshot_count: 4, diverged_count: 0 },
  strategy_review: {
    status: "on_best_certified",
    on_best_certified: true,
    selection_metric: "confidence",
    active: {
      strategy: "gc_vjatr_timing_repair",
      confidence: 0.7678,
      data_end_date: null,
      risk_state: "risk_on",
    },
    best_certified: {
      strategy: "gc_vjatr_timing_repair",
      display_name: "Cerulean Hare #2",
      confidence: 0.7678,
      share_multiple: 10.0909,
      real_share_multiple: 1.5469,
      modern_share_multiple: 2.239,
    },
    leaderboard_count: 8,
    gold_count: 8,
  },
  metric_reviews: {
    confidence: null,
    share_multiple: null,
    real_share_multiple: null,
    modern_share_multiple: null,
  },
  family_leaderboard: {
    gold_rows: 8,
    strategy_family_leaders: [
      {
        rank: 1,
        family: "gc_vjatr_timing_repair",
        display_name: "Cerulean Hare #2",
        strategy: "gc_vjatr_timing_repair",
        confidence: 0.7678,
        future_confidence: 0.6058,
        trust: 0.7767,
        metrics: { share_multiple: 10.0909, real_share_multiple: 1.5469, modern_share_multiple: 2.239, max_dd: 98.2 },
      },
      {
        rank: 2,
        family: "gc_vjatr",
        display_name: "Marbled Bonobo",
        strategy: "gc_vjatr",
        confidence: 0.6279,
        future_confidence: 0.5764,
        trust: 0.7361,
        metrics: { share_multiple: 8.32, real_share_multiple: 1.41, modern_share_multiple: 2.01, max_dd: 94.5 },
      },
    ],
  },
  leaderboard: [
    {
      display_name: "Chimera v1 - 2026-05-26",
      strategy: "chimera_v1_2026_05_26",
      validation: { composite_confidence: 0.7594 },
      metrics: { share_multiple: 30.4933, real_share_multiple: 1.3324, modern_share_multiple: 3.32, max_dd: 65.8 },
    },
    {
      display_name: "Marbled Bonobo",
      strategy: "gc_vjatr",
      validation: { composite_confidence: 0.7345 },
      metrics: { share_multiple: 13.1308, real_share_multiple: 1.1311, modern_share_multiple: 2.7144, max_dd: 64.7 },
    },
    {
      display_name: "Ember Bonobo",
      strategy: "gc_vjatr",
      validation: { composite_confidence: 0.7345 },
      metrics: { share_multiple: 13.1308, real_share_multiple: 1.1311, modern_share_multiple: 2.7144, max_dd: 64.7 },
    },
    {
      display_name: "Russet Bonobo #2",
      strategy: "gc_vjatr",
      validation: { composite_confidence: 0.7345 },
      metrics: { share_multiple: 12.1231, real_share_multiple: 1.1311, modern_share_multiple: 2.7144, max_dd: 64.7 },
    },
    {
      display_name: "Crimson Bonobo",
      strategy: "gc_vjatr",
      validation: { composite_confidence: 0.7345 },
      metrics: { share_multiple: 12.1231, real_share_multiple: 1.1311, modern_share_multiple: 2.7144, max_dd: 64.7 },
    },
    {
      display_name: "Ivory Hare",
      strategy: "gc_vjatr_timing_repair",
      validation: { composite_confidence: 0.7678 },
      metrics: { share_multiple: 10.6316, real_share_multiple: 1.5469, modern_share_multiple: 2.239, max_dd: 98.2 },
    },
    {
      display_name: "Cerulean Hare #2",
      strategy: "gc_vjatr_timing_repair",
      validation: { composite_confidence: 0.7678 },
      metrics: { share_multiple: 10.0909, real_share_multiple: 1.5469, modern_share_multiple: 2.239, max_dd: 98.2 },
    },
    {
      display_name: "Sable Hare",
      strategy: "gc_vjatr_timing_repair",
      validation: { composite_confidence: 0.7678 },
      metrics: { share_multiple: 10.0909, real_share_multiple: 1.5469, modern_share_multiple: 2.239, max_dd: 98.2 },
    },
  ],
  launch_agent: {
    job_key: "daily",
    label: "com.project-montauk.daily",
    installed: false,
    loaded: null,
    path: "~/Library/LaunchAgents/com.project-montauk.daily.plist",
  },
  launch_agents: { jobs: [] },
  doctor: { status: "preview", checks: [], failure_count: 0 },
  app_update: { can_install: false, candidate_exists: false },
  recent_events: [],
};

for (const key of Object.keys(fallbackStatus.metric_reviews)) {
  fallbackStatus.metric_reviews[key] = {
    status: "on_best_certified",
    best_certified: fallbackStatus.strategy_review.best_certified,
    active: fallbackStatus.strategy_review.active,
    selected_signal: fallbackStatus.latest_signal,
  };
}

const state = {
  status: fallbackStatus,
  metricReviews: {},
  lastActionError: null,
};

const metricDefinitions = [
  { key: "confidence", label: "Main route", short: "Main" },
  { key: "share_multiple", label: "Long run", short: "History" },
  { key: "real_share_multiple", label: "Live era", short: "Live" },
  { key: "modern_share_multiple", label: "Modern tape", short: "Modern" },
];

function tauriInvoke(command, args = {}) {
  const api = window.__TAURI__?.core;
  if (!api?.invoke) return null;
  return api.invoke(command, args);
}

async function readStatus() {
  const invoke = tauriInvoke("read_status");
  if (!invoke) return fallbackStatus;
  return invoke;
}

function text(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value ?? "";
}

function setHidden(id, hidden) {
  const node = document.getElementById(id);
  if (node) node.hidden = hidden;
}

function setMeter(id, value) {
  const node = document.getElementById(id);
  if (!node) return;
  const safeValue = Number.isFinite(Number(value)) ? Math.max(0, Math.min(100, Number(value))) : 0;
  node.style.width = `${safeValue}%`;
}

function setButtonBusy(id, busy, label) {
  const button = document.getElementById(id);
  if (!button) return () => {};
  const previousLabel = button.textContent;
  button.disabled = busy;
  if (label) button.textContent = label;
  return () => {
    button.disabled = false;
    button.textContent = previousLabel;
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function errorPayload(action, command, error, detail = {}) {
  return {
    action,
    command,
    detail,
    message: error?.message || String(error || "Unknown error"),
    stack: error?.stack || null,
    app_source: "app/src/main.js",
    native_source: "app/src-tauri/src/main.rs",
    project_root: state.status?.project_root || null,
    timestamp_local: new Date().toISOString(),
  };
}

function showActionError(payload) {
  state.lastActionError = payload;
  text("action-error-title", `${payload.action} failed`);
  text(
    "action-error-body",
    `${payload.command}: ${payload.message}`
  );
  setHidden("action-error", false);
}

function clearActionError() {
  state.lastActionError = null;
  setHidden("action-error", true);
}

async function copyActionError() {
  if (!state.lastActionError) return;
  const debugText = JSON.stringify(state.lastActionError, null, 2);
  try {
    await navigator.clipboard?.writeText(debugText);
    text("action-error-title", "Debug copied");
  } catch {
    text("action-error-body", debugText);
  }
}

function formatSchedule(schedule = {}) {
  const parts = [];
  if (schedule.Weekday) parts.push(`weekday ${schedule.Weekday}`);
  if (schedule.Day) parts.push(`day ${schedule.Day}`);
  if (Number.isInteger(schedule.Hour)) {
    const minute = String(schedule.Minute ?? 0).padStart(2, "0");
    parts.push(`${schedule.Hour}:${minute}`);
  }
  return parts.join(" / ") || "manual";
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function parseDateOnly(value) {
  if (!value) return null;
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function calendarAgeDays(dateText) {
  const date = parseDateOnly(dateText);
  if (!date) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.floor((today.getTime() - date.getTime()) / 86_400_000);
}

function freshnessText(signal = {}) {
  const age = calendarAgeDays(signal.data_end_date);
  if (age === null) return { label: "No data", help: "No snapshot", stale: true };
  const day = new Date().getDay();
  const weekendAllowance = day === 0 ? 2 : day === 6 ? 1 : 0;
  if (age <= 0) return { label: "Fresh", help: "Today", stale: false };
  if (age <= weekendAllowance) return { label: "Fresh", help: `${age}d old`, stale: false };
  return { label: "Stale", help: `${age}d old`, stale: true };
}

function dailyJob(status = {}) {
  return (status.scheduler_detail?.jobs || []).find((job) => job.key === "daily") || {};
}

function dailyAgent(status = {}) {
  if (status.launch_agent?.job_key === "daily" && status.launch_agent.loaded !== undefined) {
    return status.launch_agent;
  }
  return (status.launch_agents?.jobs || []).find((job) => job.job_key === "daily" || job.key === "daily") || status.launch_agent || {};
}

function automationText(status = {}) {
  const job = dailyJob(status);
  const agent = dailyAgent(status);
  const enabled = job.enabled !== false;
  const loaded = agent.loaded === true;
  if (enabled && loaded) {
    return {
      label: "Armed",
      help: job.next_run_local ? `Next ${formatDateTime(job.next_run_local)}` : "Ready",
    };
  }
  if (!enabled) return { label: "Paused", help: "Schedule off" };
  if (agent.loaded === false) return { label: "Manual", help: "Agent off" };
  return { label: "Manual", help: "Local read" };
}

function riskMode(signal = {}) {
  const isOn = signal.risk_state === "risk_on" || signal.risk_on === true;
  const isOff = signal.risk_state === "risk_off" || signal.risk_on === false;
  if (signal.buy_event || signal.entry_signal) {
    return {
      key: "risk_on",
      action: "Buy TECL",
      position: "Entering trade",
      short: "Entry",
      help: "A fresh entry fired on the latest snapshot.",
    };
  }
  if (signal.sell_event || signal.exit_signal) {
    return {
      key: "risk_off",
      action: "Sell TECL",
      position: "Leaving trade",
      short: "Exit",
      help: "An exit fired on the latest snapshot.",
    };
  }
  if (isOn) {
    return {
      key: "risk_on",
      action: "Hold TECL",
      position: "In the trade",
      short: "In trade",
      help: "Trend remains intact and no exit fired today.",
    };
  }
  if (isOff) {
    return {
      key: "risk_off",
      action: "Stay in Cash",
      position: "Out of the trade",
      short: "Out",
      help: "Exit conditions are still in force.",
    };
  }
  return {
    key: "unknown",
    action: "No Call",
    position: "Unknown",
    short: "--",
    help: "No signal snapshot is loaded yet.",
  };
}

function formatConfidence(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${(number * 100).toFixed(1)}%`;
}

function formatCompactPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${Math.round(number * 100)}%`;
}

function formatMultiple(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${number.toFixed(number >= 10 ? 1 : 2)}x`;
}

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return number.toLocaleString();
}

function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function animalFamily(value) {
  const clean = String(value || "").replace(/\s+#?\d+$/u, "").trim();
  if (!clean) return "Unknown";
  if (clean.includes("_")) return titleCase(clean).split(" ").at(-1) || "Strategy";
  const words = clean.split(/\s+/).filter((word) => !/^#?\d+$/.test(word));
  return words.at(-1) || clean;
}

function activeDisplayName(status = state.status) {
  const review = status.strategy_review || {};
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const champion = signal.active_champion || {};
  const best = review.best_certified || {};
  const active = review.active || {};
  return (
    active.display_name ||
    best.display_name ||
    champion.display_name ||
    displayNameFromLeaderboard(status, active.strategy || champion.strategy || best.strategy) ||
    titleCase(active.strategy || champion.strategy || best.strategy || "unknown")
  );
}

function activeFamilyName(status = state.status) {
  return animalFamily(activeDisplayName(status));
}

function displayNameFromLeaderboard(status, strategy) {
  const rows = status.family_leaderboard?.strategy_family_leaders || [];
  const match = rows.find((row) => row.strategy === strategy || row.family === strategy);
  return match?.display_name || null;
}

function confidenceValue(status = state.status, signal = {}) {
  const review = status.strategy_review || {};
  const value =
    review.best_certified?.confidence ??
    review.active?.confidence ??
    signal.validation?.composite_confidence ??
    review.best_certified?.selected_score;
  const number = Number(value);
  return Number.isFinite(number) ? number : NaN;
}

function pressureScore(status = state.status, signal = {}) {
  const confidence = confidenceValue(status, signal);
  let pressure = Number.isFinite(confidence) ? (1 - confidence) * 100 : 48;
  const warnings = signal.warnings || signal.validation?.warnings || [];
  const blockers = signal.blockers || [];
  if (status.governance?.state && status.governance.state !== "active_ok") pressure += 6;
  pressure += Math.min(14, warnings.length * 2);
  pressure += Math.min(30, blockers.length * 15);
  if (signal.signal_changed) pressure += 8;
  return Math.max(0, Math.min(99, pressure));
}

function pressureLabel(score) {
  if (!Number.isFinite(Number(score))) return "--";
  if (score < 34) return "Low";
  if (score < 67) return "Rising";
  return "High";
}

function strategyStatus(review = {}) {
  if (!review.status) return "Checking";
  if (review.status === "on_best_certified" || review.on_best_certified) return "Current";
  if (review.status === "switch_candidate") return "Switch ready";
  if (review.status === "no_certified_strategy") return "No certified leader";
  return titleCase(review.status);
}

function positionClass(modeOrKey) {
  const key = typeof modeOrKey === "string" ? modeOrKey : modeOrKey?.key;
  if (key === "risk_on") return "risk-on-text";
  if (key === "risk_off") return "risk-off-text";
  return "muted-text";
}

function metricEvidence(status = state.status) {
  const officialReview = status.strategy_review || {};
  const officialMetric = officialReview.selection_metric || "confidence";
  return metricDefinitions.map((metric) => {
    const review =
      state.metricReviews[metric.key] ||
      status.metric_reviews?.[metric.key] ||
      (metric.key === officialMetric ? officialReview : null);
    const signal =
      review?.selected_signal ||
      (metric.key === officialMetric ? status.latest_signal || status.latest_operation?.active_signal || {} : {});
    const mode = review ? riskMode(signal) : null;
    const record = review?.best_certified || review?.active || {};
    const display = record.display_name || displayNameFromLeaderboard(status, record.strategy) || titleCase(record.strategy || "");
    return {
      metric,
      review,
      signal,
      mode,
      strategy: display || "--",
      family: display ? animalFamily(display) : "--",
      confidence: Number(record.confidence ?? review?.best_certified?.selected_score ?? NaN),
    };
  });
}

function renderConsensus(status = state.status) {
  const node = document.getElementById("consensus-list");
  const evidence = metricEvidence(status).filter((item) => item.review);
  const inTrade = evidence.filter((item) => item.mode?.key === "risk_on").length;
  const out = evidence.filter((item) => item.mode?.key === "risk_off").length;
  const loaded = evidence.length;
  const leader = inTrade >= out ? "in trade" : "out";
  const agreement = Math.max(inTrade, out);

  if (!loaded) {
    text("consensus-main", "--");
    text("consensus-meta", "Checking");
  } else if (inTrade === out) {
    text("consensus-main", `${inTrade}-${out}`);
    text("consensus-meta", "Split");
  } else {
    text("consensus-main", `${agreement}/${loaded}`);
    text("consensus-meta", leader);
  }

  if (!node) return;
  node.innerHTML = "";
  for (const item of metricDefinitions.map((metric) => evidence.find((entry) => entry.metric.key === metric.key) || { metric })) {
    const call = item.mode?.short || "--";
    const chip = document.createElement("div");
    chip.className = `consensus-chip ${item.mode?.key === "risk_on" ? "on" : item.mode?.key === "risk_off" ? "off" : ""}`;
    chip.innerHTML = `
      <span>${escapeHtml(item.metric.short)}</span>
      <strong>${escapeHtml(call)}</strong>
    `;
    node.appendChild(chip);
  }
}

function renderMetricMatrix(status = state.status) {
  const node = document.getElementById("metric-grid");
  if (!node) return;
  node.innerHTML = `
    <div class="metric-row metric-head">
      <span>Route</span>
      <span>Family</span>
      <span>Position</span>
      <span>Confidence</span>
      <span>Status</span>
    </div>
  `;

  for (const item of metricEvidence(status)) {
    const row = document.createElement("div");
    const call = item.mode?.short || "--";
    row.className = `metric-row ${item.review?.status === "switch_candidate" ? "candidate" : ""}`;
    row.dataset.tip = `${item.metric.label} asks which certified strategy would currently lead if this route were used.`;
    row.innerHTML = `
      <span>
        <strong>${escapeHtml(item.metric.label)}</strong>
      </span>
      <span>
        <strong>${escapeHtml(item.family)}</strong>
        <small>${escapeHtml(item.strategy)}</small>
      </span>
      <span class="${positionClass(item.mode)}">${escapeHtml(call)}</span>
      <span>${escapeHtml(formatConfidence(item.confidence))}</span>
      <span>${escapeHtml(item.review ? strategyStatus(item.review) : "Not loaded")}</span>
    `;
    node.appendChild(row);
  }
}

function routeCallForRow(row, status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const activeStrategy = signal.active_champion?.strategy || status.strategy_review?.active?.strategy || status.strategy_review?.best_certified?.strategy;
  if (row.strategy === activeStrategy || row.display_name === activeDisplayName(status)) return riskMode(signal).short;
  const route = metricEvidence(status).find((item) => {
    const reviewStrategy = item.review?.best_certified?.strategy || item.review?.active?.strategy;
    const display = item.review?.best_certified?.display_name || item.review?.active?.display_name;
    return reviewStrategy === row.strategy || display === row.display_name;
  });
  return route?.mode?.short || "not checked";
}

function activeLeaderboardRow(status = state.status) {
  const review = status.strategy_review || {};
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const champion = signal.active_champion || {};
  const best = review.best_certified || {};
  const active = review.active || {};
  const metrics = best.share_multiple
    ? {
        share_multiple: best.share_multiple,
        real_share_multiple: best.real_share_multiple,
        modern_share_multiple: best.modern_share_multiple,
        max_dd: champion.metrics?.max_dd,
      }
    : champion.metrics || {};
  return {
    rank: "Now",
    family: active.strategy || best.strategy || champion.strategy,
    display_name: activeDisplayName(status),
    strategy: active.strategy || best.strategy || champion.strategy,
    confidence: confidenceValue(status, signal),
    validation_confidence: confidenceValue(status, signal),
    metrics,
    current: true,
  };
}

function leaderboardRows(status = state.status) {
  // Join Confidence-v2 fields (future_confidence, trust, overall_confidence)
  // from runs/family_confidence_leaderboard.json into the spike leaderboard
  // rows. The spike file doesn't carry those fields directly, which is why
  // the Edge/Trust columns rendered blank.
  const familyLeaders = status.family_leaderboard?.strategy_family_leaders || [];
  const familyByStrategy = new Map();
  for (const leader of familyLeaders) {
    if (leader?.strategy) familyByStrategy.set(leader.strategy, leader);
    if (leader?.family) familyByStrategy.set(leader.family, leader);
  }
  const join = (row) => {
    const leader = familyByStrategy.get(row?.strategy) || familyByStrategy.get(row?.family);
    if (!leader) return row;
    return {
      future_confidence: leader.future_confidence ?? leader.edge_confidence,
      trust: leader.trust ?? leader.capital_readiness,
      overall_confidence: leader.overall_confidence,
      ...row,
    };
  };
  const rawRows = Array.isArray(status.leaderboard) && status.leaderboard.length
    ? status.leaderboard.map((row, index) => ({ ...join(row), rank: index + 1 }))
    : familyLeaders;
  const rows = [...rawRows];
  const active = activeLeaderboardRow(status);
  const activeIndex = rows.findIndex(
    (row) => row.strategy === active.strategy || row.display_name === active.display_name
  );
  if (activeIndex >= 0) {
    const [match] = rows.splice(activeIndex, 1);
    rows.unshift({ ...match, ...active, source_rank: match.rank, current: true });
  } else {
    rows.unshift(active);
  }
  return rows;
}

function rowConfidence(row, status = state.status) {
  if (row.current) return confidenceValue(status, status.latest_signal || status.latest_operation?.active_signal || {});
  return row.overall_confidence ?? row.confidence ?? row.validation_confidence ?? row.validation?.composite_confidence;
}

function renderLeaderboard(status = state.status) {
  const node = document.getElementById("leaderboard-list");
  if (!node) return;
  const rows = leaderboardRows(status);

  node.innerHTML = `
    <div class="leader-row leader-head">
      <span>Rank</span>
      <span>Family</span>
      <span>Now</span>
      <span>Confidence</span>
      <span>Edge</span>
      <span>Trust</span>
      <span>Share</span>
    </div>
  `;

  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "leader-row";
    empty.innerHTML = "<span>--</span><span>No leaderboard found.</span><span></span><span></span><span></span><span></span><span></span>";
    node.appendChild(empty);
    return;
  }

  for (const rowData of rows.slice(0, 10)) {
    const current = Boolean(rowData.current);
    const call = routeCallForRow(rowData, status);
    const row = document.createElement("div");
    row.className = `leader-row ${current ? "current" : ""}`;
    row.dataset.tip = current
      ? "This is the strategy currently driving the dashboard."
      : "Gold strategy on the local leaderboard. Its current signal is only shown when the app has computed that route.";
    row.innerHTML = `
      <span>${escapeHtml(current ? "Now" : rowData.rank ?? "--")}</span>
      <span>
        <strong>${escapeHtml(animalFamily(rowData.display_name || rowData.family || rowData.strategy))}</strong>
        <small>${escapeHtml(rowData.display_name || titleCase(rowData.family || rowData.strategy))}</small>
      </span>
      <span class="${current ? positionClass(status.latest_signal?.risk_state || status.latest_operation?.active_signal?.risk_state) : "muted-text"}">${escapeHtml(call)}</span>
      <span>${escapeHtml(formatConfidence(rowConfidence(rowData, status)))}</span>
      <span>${escapeHtml(formatCompactPercent(rowData.future_confidence ?? rowData.edge_confidence))}</span>
      <span>${escapeHtml(formatCompactPercent(rowData.trust ?? rowData.capital_readiness))}</span>
      <span>${escapeHtml(formatMultiple(rowData.metrics?.share_multiple))}</span>
    `;
    node.appendChild(row);
  }
}

function cleanIssueText(value) {
  return String(value || "")
    .replaceAll("warnings", "notes")
    .replaceAll("warning", "note")
    .replaceAll("warn", "note")
    .replaceAll("risk_on", "in trade")
    .replaceAll("risk_off", "out of trade")
    .replaceAll("active_watch", "review")
    .replaceAll("_", " ");
}

function buildDecisionReasons(status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const review = status.strategy_review || {};
  const quality = signal.data_quality || status.latest_operation?.steps?.data_quality?.summary || {};
  const live = status.live_holdout || {};
  const family = activeFamilyName(status);
  const reasons = [];

  if (review.status === "switch_candidate") {
    reasons.push(`A stronger family is waiting, but the current call is still being shown.`);
  } else if (review.on_best_certified || review.status === "on_best_certified") {
    reasons.push(`${family} is still the certified leader.`);
  } else {
    reasons.push(`No cleaner certified leader has replaced ${family}.`);
  }

  if (signal.signal_change?.changed) {
    reasons.push("The latest data changed the call.");
  } else if (signal.signal_change?.previous_data_end_date) {
    reasons.push(`The call is unchanged from ${signal.signal_change.previous_data_end_date}.`);
  } else {
    reasons.push("No entry or exit fired on this snapshot.");
  }

  if ((quality.fail ?? 0) === 0 && (quality.total ?? 0) > 0) {
    reasons.push(`${quality.pass ?? 0}/${quality.total ?? 0} data checks are clean.`);
  }

  if (live.status === "ok" && Number(live.diverged_count ?? 0) === 0 && Number(live.snapshot_count ?? 0) > 0) {
    reasons.push("Live replay has no drift.");
  }

  return reasons.slice(0, 4);
}

function buildFlipTriggers(status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const champion = signal.active_champion || {};
  const params = champion.params || {};
  const mode = riskMode(signal);
  const slow = params.slow_ema || params.trend_len || "slow";
  const fast = params.fast_ema || "fast";
  const atrBars = params.atr_confirm || 1;
  const repairLen = params.repair_len || params.drawdown_lookback || null;

  if (mode.short === "TECL") {
    return [
      { label: "Trend", value: `${fast}-bar line loses the ${slow}-bar track` },
      { label: "Volatility", value: `ATR pressure confirms for ${atrBars} bar${atrBars === 1 ? "" : "s"}` },
      { label: "Repair", value: repairLen ? `${repairLen}-bar rebound filter breaks` : "Rebound filter breaks" },
    ];
  }
  if (mode.short === "Cash") {
    return [
      { label: "Trend", value: `${fast}-bar line clears the ${slow}-bar track` },
      { label: "Slope", value: "Trend slope turns positive" },
      { label: "Volatility", value: "Shock filter clears" },
    ];
  }
  return [
    { label: "Snapshot", value: "Load a current signal" },
    { label: "Data", value: "Run the daily update" },
  ];
}

function renderSignalList(id, items) {
  const node = document.getElementById(id);
  if (!node) return;
  node.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("li");
    if (typeof item === "string") {
      row.innerHTML = `<span></span><strong>${escapeHtml(item)}</strong>`;
    } else {
      row.innerHTML = `<span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong>`;
    }
    node.appendChild(row);
  }
}

function renderEngineStats(status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const quality = signal.data_quality || status.latest_operation?.steps?.data_quality?.summary || {};
  const live = status.live_holdout || status.governance?.live_holdout || {};
  const review = status.strategy_review || {};
  const fresh = freshnessText(signal);
  const automation = automationText(status);
  const goldCount = review.gold_count ?? (Array.isArray(status.leaderboard) ? status.leaderboard.length : null) ?? status.family_leaderboard?.gold_rows ?? review.leaderboard_count ?? "--";
  const replayCount = live.snapshot_count ?? status.governance?.live_holdout?.snapshot_count ?? 0;

  text("engine-gold", formatNumber(goldCount));
  text("engine-set", formatNumber(goldCount));
  text("engine-data", quality.total ? `${quality.pass ?? 0}/${quality.total}` : "--");
  text("engine-data-meta", quality.fail ? `${quality.fail} fail` : "clean");
  text("engine-drift", live.status === "ok" ? `${live.diverged_count ?? 0}` : "--");
  text("engine-drift-meta", replayCount ? `${replayCount} replayed` : "no replay");
  text("data-end", signal.data_end_date || "--");
  text("freshness-state", fresh.help);
  text("automation-state", automation.label);
  text("automation-main", automation.label);
  text("automation-meta", automation.help);
}

function friendlyCheckLabel(label) {
  return String(label)
    .replace("mac_app_bundle", "Mac app")
    .replace("latest_operations", "Latest signal")
    .replace("live_holdout", "Live replay")
    .replace("launch_agent:", "Background update: ")
    .replaceAll("_", " ");
}

function addIssue(issues, level, area, status, detail) {
  if (!detail) return;
  issues.push({ level, area, status, detail });
}

function renderCheckup(status = state.status) {
  const report = status.doctor || {};
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const quality = signal.data_quality || status.latest_operation?.steps?.data_quality?.summary || {};
  const governance = status.governance || {};
  const notifications = status.notifications || {};
  const checks = report.checks || [];
  const fresh = freshnessText(signal);
  const automation = automationText(status);
  const issues = [];

  for (const check of checks.filter((item) => !item.ok)) {
    const launchd = check.launchd || {};
    addIssue(
      issues,
      "fix",
      friendlyCheckLabel(check.label || "check"),
      launchd.state || "Fix",
      cleanIssueText(check.path || check.error || "Check failed.")
    );
  }
  if (fresh.stale) addIssue(issues, "review", "Data age", fresh.label, fresh.help);
  if (automation.label !== "Armed") addIssue(issues, "review", "Automation", automation.label, automation.help);
  if ((quality.fail ?? 0) > 0) addIssue(issues, "fix", "Data", `${quality.fail} failed`, "Data check failed.");
  if ((quality.warn ?? 0) > 0) addIssue(issues, "review", "Data", `${quality.warn} notes`, "Data is not clean.");
  if (governance.state && governance.state !== "active_ok") {
    for (const reason of governance.reasons || ["Review current strategy."]) {
      addIssue(issues, "review", "Strategy", cleanIssueText(governance.state), cleanIssueText(reason));
    }
  }
  for (const blocker of signal.blockers || []) {
    addIssue(issues, "fix", "Strategy", "Blocked", cleanIssueText(blocker));
  }
  if ((notifications.pending_count ?? 0) > 0) {
    addIssue(issues, "review", "Notices", `${notifications.pending_count} pending`, "Pending notices.");
  }

  text("doctor-status", issues.length ? `${issues.length} items need review` : "Clean");
  text("doctor-meta", issues.length ? "Open items are below." : "No checkup issues found.");

  const node = document.getElementById("doctor-list");
  if (!node) return;
  node.innerHTML = `
    <div class="readiness-row readiness-head">
      <span>Level</span>
      <span>Area</span>
      <span>Status</span>
      <span>Detail</span>
    </div>
  `;
  if (!issues.length) {
    const row = document.createElement("div");
    row.className = "readiness-row";
    row.innerHTML = `
      <span class="ok-text">ok</span>
      <span>Montauk</span>
      <span>Clean</span>
      <span>No issues.</span>
    `;
    node.appendChild(row);
    return;
  }
  for (const issue of issues) {
    const row = document.createElement("div");
    row.className = "readiness-row";
    row.innerHTML = `
      <span class="${issue.level === "fix" ? "danger-text" : "review-text"}">${escapeHtml(issue.level)}</span>
      <span>${escapeHtml(issue.area)}</span>
      <span>${escapeHtml(issue.status)}</span>
      <span>${escapeHtml(issue.detail)}</span>
    `;
    node.appendChild(row);
  }
}

function renderDoctorSummary(status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const quality = signal.data_quality || status.latest_operation?.steps?.data_quality?.summary || {};
  const notifications = status.notifications || {};
  const live = status.live_holdout || {};

  text("doctor-leader", activeFamilyName(status));
  text("doctor-rank", activeDisplayName(status));
  text("quality-main", quality.fail ? `${quality.fail} fail` : `${quality.pass ?? 0} pass`);
  text("quality-meta", `${quality.total ?? 0} checks`);
  text("doctor-live", live.status === "ok" ? `${live.diverged_count ?? 0} drift` : live.status || "--");
  text("doctor-live-meta", live.snapshot_count ? `${live.snapshot_count} snapshots` : "No replay");
  text("notifications-main", `${notifications.pending_count ?? 0} pending`);
  text("notifications-meta", notifications.pending_count ? "Review required" : "Outbox clean");
}

function renderJobs(status) {
  const node = document.getElementById("jobs-list");
  if (!node) return;
  node.innerHTML = "";
  const detailedJobs = status?.scheduler_detail?.jobs || [];
  const jobs = detailedJobs.length
    ? detailedJobs.map((job) => [job.key, job])
    : Object.entries(status?.scheduler?.jobs || {});
  if (!jobs.length) {
    node.textContent = "No scheduler config found.";
    return;
  }
  for (const [key, job] of jobs) {
    const lastRun = job.last_run;
    const nextRun = job.next_run_local ? formatDateTime(job.next_run_local) : job.enabled ? "manual" : "-";
    const lastStatus = lastRun ? `${lastRun.status} ${formatDateTime(lastRun.finished_utc || lastRun.started_utc)}` : "-";
    const nextEnabled = !job.enabled;
    const row = document.createElement("div");
    row.className = "table-row";
    row.innerHTML = `
      <span>${escapeHtml(job.label || key)}</span>
      <span>${job.enabled ? "on" : "off"}</span>
      <span>${escapeHtml(formatSchedule(job.schedule))}</span>
      <span>${escapeHtml(nextRun)}</span>
      <span>${escapeHtml(lastStatus)}</span>
      <span><button class="button small job-toggle" data-job-key="${escapeHtml(key)}" data-enabled="${nextEnabled}">${
        nextEnabled ? "Enable" : "Disable"
      }</button></span>
    `;
    node.appendChild(row);
  }
  node.querySelectorAll(".job-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      setSchedulerJob(button.dataset.jobKey, button.dataset.enabled === "true");
    });
  });
}

function renderLaunchAgent(agent = {}) {
  text("agent-job", agent.job_key || "daily");
  text("agent-installed", agent.installed === true ? "yes" : "no");
  text("agent-loaded", agent.loaded === null || agent.loaded === undefined ? "unknown" : agent.loaded ? "yes" : "no");
  text("agent-path", agent.path || "unknown");
}

function renderLaunchAgents(agents = {}) {
  const jobs = agents.jobs || [];
  if (!jobs.length) {
    text("agents-summary", agents.error || "No enabled jobs found.");
    return;
  }
  const installed = jobs.filter((job) => job.installed).length;
  text("agents-summary", `${installed}/${jobs.length} background tasks installed`);
}

const notificationPreferenceOrder = [
  "signal_changed",
  "data_stale",
  "data_quality_failed",
  "job_failed",
  "champion_changed",
  "champion_blocked",
  "manual_review_required",
  "replacement_candidate",
  "live_holdout_drift",
  "signal_snapshot_conflict",
  "viz_build_failed",
];

function renderNotificationPreferences(status = {}) {
  const node = document.getElementById("notification-prefs-list");
  if (!node) return;
  node.innerHTML = "";
  const preferences =
    status.notification_state?.preferences?.event_types ||
    status.notifications?.preferences?.event_types ||
    {};
  const keys = notificationPreferenceOrder.filter((key) => preferences[key]).concat(
    Object.keys(preferences).filter((key) => !notificationPreferenceOrder.includes(key)).sort()
  );
  text("notification-prefs-state", keys.length ? `${keys.length} event types persisted` : "No preferences found");
  if (!keys.length) {
    node.textContent = "Run a notification scan to initialize preferences.";
    return;
  }
  for (const key of keys) {
    const pref = preferences[key] || {};
    const row = document.createElement("label");
    row.className = "table-row checkbox-row";
    row.innerHTML = `
      <span>${escapeHtml(titleCase(key))}</span>
      <span>${pref.enabled === false ? "off" : "on"}</span>
      <span><input type="checkbox" data-notification-event="${escapeHtml(key)}" ${
        pref.enabled === false ? "" : "checked"
      } /></span>
    `;
    node.appendChild(row);
  }
  node.querySelectorAll("input[data-notification-event]").forEach((input) => {
    input.addEventListener("change", () => {
      setNotificationPreference(input.dataset.notificationEvent, input.checked);
    });
  });
}

function render(status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const mode = riskMode(signal);
  const confidence = confidenceValue(status, signal);
  const pressure = pressureScore(status, signal);
  const family = activeFamilyName(status);
  const displayName = activeDisplayName(status);
  const runtimeMode = window.__TAURI__?.core ? "tauri bridge" : "static fallback";

  text("signal-title", mode.action);
  text("action-main", mode.action);
  text("position-label", mode.position);
  text("decision-help", `${family}: ${mode.help}`);
  text("confidence-state", formatConfidence(confidence));
  text("pressure-state", `${pressureLabel(pressure)} ${Math.round(pressure)}%`);
  text("confidence-help", "Higher means Montauk has more reason to trust this position.");
  text("pressure-help", mode.key === "risk_on" ? "Lower is more stable." : "Higher means closer to a new entry.");
  text("champion-family", family);
  text("champion-name", displayName);
  text("sidebar-position", mode.short);
  text("sidebar-family", family);
  text("runtime-mode", runtimeMode);
  text("project-root", status.project_root || "unknown");

  setMeter("confidence-meter", Number.isFinite(confidence) ? confidence * 100 : 0);
  setMeter("pressure-meter", pressure);
  document.body.dataset.risk = mode.key;
  document.body.dataset.freshness = freshnessText(signal).stale ? "stale" : "fresh";

  renderEngineStats(status);
  renderConsensus(status);
  renderMetricMatrix(status);
  renderLeaderboard(status);
  renderDoctorSummary(status);
  renderJobs(status);
  renderLaunchAgent(status.launch_agent);
  renderLaunchAgents(status.launch_agents);
  renderNotificationPreferences(status);
  renderCheckup(status);
  renderResearchQueue(status);
  renderConfidenceLedger(status);
  drawFlipPressureSparkline();
}

async function refresh() {
  try {
    clearActionError();
    state.status = await readStatus();
    state.metricReviews = {};
    render(state.status);
    text("last-refreshed", `Refreshed ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`);
    loadMetricMatrix();
    loadFlipPressureHistory();
  } catch (error) {
    showActionError(errorPayload("Refresh", "read_status", error, {
      tauri_bridge: Boolean(window.__TAURI__?.core),
      local_files_read_by_native_command: [
        "app/src-tauri/src/main.rs::read_status",
        "app/src/main.js::refresh",
      ],
      expected_artifacts: [
        "runs/operations/latest.json",
        "signals/*.json",
        "runs/operations/strategy_review.json",
        "spike/leaderboard.json",
      ],
    }));
  }
}

async function loadMetricMatrix() {
  if (!window.__TAURI__?.core) return;
  try {
    const entries = await Promise.all(
      metricDefinitions.map(async (metric) => {
        const review = await tauriInvoke("strategy_metric_signal", { metric: metric.key });
        return [metric.key, review];
      })
    );
    state.metricReviews = Object.fromEntries(entries);
    renderConsensus(state.status);
    renderMetricMatrix(state.status);
    renderLeaderboard(state.status);
  } catch (error) {
    text("last-refreshed", error?.message || String(error));
  }
}

async function runJob(job) {
  const invoke = tauriInvoke("run_job", { job });
  if (!invoke) {
    showActionError(errorPayload("Update", "run_job", "Tauri bridge is unavailable.", {
      job,
      expected_context: "Use /Applications/Montauk.app, not the browser-only dev preview.",
      local_command: `.venv/bin/python scripts/ops/run_job.py --job ${job} --json`,
    }));
    return;
  }
  const resetButton = setButtonBusy("daily-btn", true, "Updating");
  try {
    clearActionError();
    text("last-refreshed", "Update running locally...");
    const result = await invoke;
    if (result?.status && result.status !== "ok") {
      throw new Error(result.stderr_tail || result.stdout_tail || `Job returned status ${result.status}`);
    }
    await refresh();
  } catch (error) {
    showActionError(errorPayload("Update", "run_job", error, {
      job,
      python_entry: "scripts/ops/run_job.py",
      resolved_job: job === "daily" ? "scripts/ops/daily.py" : job,
      local_command: `.venv/bin/python scripts/ops/run_job.py --job ${job} --json`,
      likely_record_dir: "runs/scheduler/jobs",
    }));
  } finally {
    resetButton();
  }
}

async function manageAgent(action, jobKey = "daily") {
  text("agent-message", `${action} running...`);
  const invoke = tauriInvoke("manage_launch_agent", { jobKey, action });
  if (!invoke) {
    text("agent-message", "Launch through the Mac app to manage the background agent.");
    return;
  }
  try {
    const result = await invoke;
    if (jobKey === "__enabled") {
      state.status.launch_agents = result;
      renderLaunchAgents(result);
    } else {
      state.status.launch_agent = result;
      renderLaunchAgent(result);
    }
    text("agent-message", `${result.last_action || action} complete.`);
  } catch (error) {
    text("agent-message", error?.message || String(error));
  }
  await refresh();
}

async function setSchedulerJob(jobKey, enabled) {
  const invoke = tauriInvoke("set_scheduler_job", { jobKey, enabled });
  if (!invoke) return;
  try {
    const result = await invoke;
    state.status.scheduler_detail = result;
    renderJobs(state.status);
  } catch (error) {
    text("last-refreshed", error?.message || String(error));
  }
  await refresh();
}

async function setNotificationPreference(eventType, enabled) {
  const invoke = tauriInvoke("set_notification_preference", { eventType, enabled });
  if (!invoke) return;
  try {
    const result = await invoke;
    state.status.notification_state = result;
    renderNotificationPreferences(state.status);
    await refresh();
  } catch (error) {
    text("notification-prefs-state", error?.message || String(error));
  }
}

async function runNextResearch() {
  const invoke = tauriInvoke("run_next_research", { timeout_seconds: 15 * 60 });
  if (!invoke) {
    showActionError(errorPayload("Run Next Strategy", "run_next_research", "Tauri bridge is unavailable.", {
      expected_context: "Use /Applications/Montauk.app, not the browser-only dev preview.",
      local_command: ".venv/bin/python scripts/ops/research_runner.py --execute --json",
    }));
    return;
  }
  const reset = setButtonBusy("doctor-next-research-btn", true, "Running…");
  text("research-queue-last", "Running next approved idea…");
  try {
    clearActionError();
    const result = await invoke;
    if (result?.status === "empty") {
      text("research-queue-last", "No approved ideas in the queue. Approve one below or have an AI session top up runs/research_queue/queue.json.");
    } else if (result?.status === "ok") {
      const runResult = result.result || {};
      const runs = Array.isArray(runResult.runs) ? runResult.runs : [];
      const record = runs[0] || {};
      const statusLabel = record.status || "complete";
      const summary = result.kind
        ? `Ran ${result.kind} (${result.idea_id}). Status: ${statusLabel}.`
        : `Ran idea ${result.idea_id || "?"}. Status: ${statusLabel}.`;
      text("research-queue-last", summary);
    } else {
      text("research-queue-last", `Runner returned status ${result?.status || "?"}.`);
    }
    await refresh();
  } catch (error) {
    showActionError(errorPayload("Run Next Strategy", "run_next_research", error, {
      python_entry: "scripts/ops/research_runner.py --execute",
      local_command: ".venv/bin/python scripts/ops/research_runner.py --execute --json",
      reads: ["runs/research_queue/queue.json"],
      writes: ["runs/research_queue/runs/*.json", "runs/operations/events.jsonl"],
    }));
  } finally {
    reset();
  }
}

async function enqueueResearchIdeas() {
  const invoke = tauriInvoke("enqueue_research_ideas");
  if (!invoke) {
    text("research-queue-last", "Enqueue only works in the Mac app.");
    return;
  }
  const reset = setButtonBusy("research-enqueue-btn", true, "Queuing");
  try {
    const result = await invoke;
    const count = result?.idea_count ?? result?.ideas?.length ?? 0;
    text("research-queue-last", `Queue refreshed with ${count} ideas.`);
    await refresh();
  } catch (error) {
    text("research-queue-last", error?.message || String(error));
  } finally {
    reset();
  }
}

async function startResearchIdea(ideaId) {
  const invoke = tauriInvoke("start_research_run", { ideaId });
  if (!invoke) {
    text("research-queue-last", "Start only works in the Mac app.");
    return;
  }
  try {
    const result = await invoke;
    const run = Array.isArray(result?.runs) ? result.runs[0] : null;
    text("research-queue-last", run?.record_path ? `Planned run: ${run.record_path}` : `Planned run for ${ideaId}.`);
    await refresh();
  } catch (error) {
    text("research-queue-last", error?.message || String(error));
  }
}

async function setResearchIdeaStatus(ideaId, action) {
  const invoke = tauriInvoke("research_queue_action", { ideaId, action });
  if (!invoke) {
    text("research-queue-last", "Approve/dismiss only works in the Mac app.");
    return;
  }
  try {
    await invoke;
    await refresh();
  } catch (error) {
    text("research-queue-last", error?.message || String(error));
  }
}

function inspectResearchIdea(item) {
  const runs = state.status?.research_runs?.runs || [];
  const related = runs
    .filter((run) => run.idea_id === item.id || run.plan?.idea_id === item.id)
    .slice(-3)
    .map((run) => run.record_path || run.run_id)
    .filter(Boolean);
  const diagnostics = Array.isArray(item.input_diagnostics) ? item.input_diagnostics.join(", ") : "none";
  const artifacts = Array.isArray(item.expected_artifact_paths) ? item.expected_artifact_paths.join(", ") : "none";
  const stops = Array.isArray(item.stop_conditions) ? item.stop_conditions.join("; ") : "none";
  const runText = related.length ? ` Recent runs: ${related.join(" | ")}.` : "";
  text("research-queue-last", `Inputs: ${diagnostics}. Artifacts: ${artifacts}. Stop: ${stops}.${runText}`);
}

function renderResearchQueue(status = state.status) {
  const queue = status.research_queue || {};
  const ideas = Array.isArray(queue.ideas) ? queue.ideas : [];
  const summary = document.getElementById("research-queue-summary");
  if (summary) {
    const counts = { approved: 0, proposed: 0, paused: 0, dismissed: 0 };
    for (const item of ideas) {
      const key = (item.status || "proposed").toLowerCase();
      if (counts[key] != null) counts[key] += 1;
    }
    summary.textContent = ideas.length
      ? `${counts.approved} approved · ${counts.proposed} proposed · ${counts.paused} paused · ${counts.dismissed} dismissed`
      : "Empty queue. Have an AI session populate runs/research_queue/queue.json.";
  }

  const node = document.getElementById("research-queue-list");
  if (!node) return;
  node.innerHTML = `
    <div class="leader-row leader-head">
      <span>Status</span>
      <span>Kind</span>
      <span>Tier</span>
      <span>Why</span>
      <span>Tests</span>
      <span>Actions</span>
      <span></span>
    </div>
  `;
  if (!ideas.length) {
    const empty = document.createElement("div");
    empty.className = "leader-row";
    empty.innerHTML = `<span>--</span><span>No queued ideas. Read docs/ai-research-playbook.md to see the format.</span><span></span><span></span><span></span><span></span><span></span>`;
    node.appendChild(empty);
    return;
  }
  for (const item of ideas) {
    const ideaStatus = item.status || "proposed";
    const row = document.createElement("div");
    row.className = "leader-row";
    row.dataset.tip = item.rationale || "";
    const tests = Array.isArray(item.suggested_tests) ? item.suggested_tests.join(", ") : "";
    const buttons = ideaStatus === "approved"
      ? `<button class="button small primary" data-research-id="${escapeHtml(item.id)}" data-research-action="start">Start</button>
         <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="pause">Pause</button>
         <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="inspect">Inspect</button>`
      : ideaStatus === "paused"
        ? `<button class="button small primary" data-research-id="${escapeHtml(item.id)}" data-research-action="resume">Resume</button>
           <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="dismiss">Dismiss</button>
           <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="inspect">Inspect</button>`
      : ideaStatus === "dismissed"
        ? `<button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="reset">Reopen</button>
           <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="inspect">Inspect</button>`
        : `<button class="button small primary" data-research-id="${escapeHtml(item.id)}" data-research-action="approve">Approve</button>
           <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="dismiss">Dismiss</button>
           <button class="button small" data-research-id="${escapeHtml(item.id)}" data-research-action="inspect">Inspect</button>`;
    row.innerHTML = `
      <span>${escapeHtml(ideaStatus)}</span>
      <span><strong>${escapeHtml(titleCase(item.kind || "?"))}</strong><small>${escapeHtml(item.id || "")}</small></span>
      <span>${escapeHtml(item.validation_tier || "T?")}</span>
      <span>${escapeHtml(item.rationale || "—")}</span>
      <span>${escapeHtml(tests)}</span>
      <span class="row-actions">${buttons}</span>
      <span></span>
    `;
    node.appendChild(row);
  }
  node.querySelectorAll("button[data-research-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ideaId = btn.dataset.researchId;
      const action = btn.dataset.researchAction;
      const item = ideas.find((candidate) => candidate.id === ideaId);
      if (!ideaId || !action) return;
      if (action === "inspect" && item) inspectResearchIdea(item);
      else if (action === "start") startResearchIdea(ideaId);
      else setResearchIdeaStatus(ideaId, action);
    });
  });
}

async function runDoctor() {
  const invoke = tauriInvoke("doctor_report");
  if (!invoke) {
    showActionError(errorPayload("Run Checkup", "doctor_report", "Tauri bridge is unavailable.", {
      expected_context: "Use /Applications/Montauk.app, not the browser-only dev preview.",
      local_command: ".venv/bin/python scripts/ops/doctor.py --json",
    }));
    return;
  }
  const resetButton = setButtonBusy("doctor-run-btn", true, "Checking");
  try {
    clearActionError();
    text("doctor-meta", "Running local checkup...");
    const result = await invoke;
    state.status.doctor = result;
    renderCheckup(state.status);
  } catch (error) {
    showActionError(errorPayload("Run Checkup", "doctor_report", error, {
      python_entry: "scripts/ops/doctor.py --json",
      local_command: ".venv/bin/python scripts/ops/doctor.py --json",
      checks: [
        "app bundle",
        "latest operations",
        "governance",
        "live holdout",
        "notifications",
        "local LaunchAgents",
      ],
    }));
  } finally {
    resetButton();
  }
}

const vizState = {
  boot_attempted: false,
  booted: false,
  loading: false,
  last_error: null,
};

function vizControlsVisible(visible) {
  for (const id of ["viz-topbar", "viz-sidebar", "viz-center", "viz-right"]) {
    const node = document.getElementById(id);
    if (node) node.hidden = !visible;
  }
  const empty = document.getElementById("viz-empty");
  if (empty) empty.hidden = visible;
}

function vizSetEmpty(title, detail) {
  const empty = document.getElementById("viz-empty");
  if (!empty) return;
  empty.innerHTML = `<strong>${escapeHtml(title)}</strong><span class="muted">${escapeHtml(detail || "")}</span>`;
  empty.hidden = false;
  for (const id of ["viz-topbar", "viz-sidebar", "viz-center", "viz-right"]) {
    const node = document.getElementById(id);
    if (node) node.hidden = true;
  }
}

async function ensureVizBooted({ forceRebuild = false } = {}) {
  if (vizState.booted && !forceRebuild) {
    window.__MONTAUK_VIZ__?.refit?.();
    return;
  }
  if (vizState.loading) return;
  if (!window.__MONTAUK_VIZ__ || typeof window.__MONTAUK_VIZ__.boot !== "function") {
    vizSetEmpty("Viz engine not loaded", "/lib/viz-engine.js failed to load. Check the browser console.");
    return;
  }
  const invoke = tauriInvoke("read_viz_bundle", { rebuild: forceRebuild });
  if (!invoke) {
    vizSetEmpty(
      "Viz only runs in the Mac app",
      "Launch through /Applications/Montauk.app — the browser preview cannot read the local bundle."
    );
    return;
  }
  vizState.loading = true;
  vizSetEmpty(
    forceRebuild ? "Rebuilding viz bundle…" : "Loading viz bundle…",
    "Reading viz/montauk-bundle.json (or running build_viz.py --bundle-only if missing)."
  );
  try {
    const bundle = await invoke;
    if (!bundle) {
      vizSetEmpty("Viz bundle is empty", "build_viz.py returned no payload. Try Rebuild.");
      return;
    }
    // Hot-swap path: tear down the live engine first so boot() can reattach
    // to fresh DOM hosts and chart instances. reset() is a no-op the first
    // time around.
    if (vizState.booted && forceRebuild && typeof window.__MONTAUK_VIZ__.reset === "function") {
      window.__MONTAUK_VIZ__.reset();
      vizState.booted = false;
    }
    vizControlsVisible(true);
    window.__MONTAUK_VIZ__.boot(bundle);
    vizState.booted = true;
    vizState.boot_attempted = true;
    requestAnimationFrame(() => window.__MONTAUK_VIZ__?.refit?.());
  } catch (error) {
    vizState.last_error = error;
    vizSetEmpty("Viz failed to load", error?.message || String(error));
  } finally {
    vizState.loading = false;
  }
}

async function rebuildViz() {
  const reset = setButtonBusy("viz-rebuild-btn", true, "Rebuilding");
  try {
    await ensureVizBooted({ forceRebuild: true });
  } finally {
    reset();
  }
}

async function popoutViz() {
  const invoke = tauriInvoke("open_viz");
  if (!invoke) {
    showActionError(errorPayload("Open standalone", "open_viz", "Tauri bridge is unavailable.", {
      expected_context: "Use /Applications/Montauk.app, not the browser-only dev preview.",
      local_command: "open viz/montauk-viz.html",
    }));
    return;
  }
  try {
    await invoke;
  } catch (error) {
    showActionError(errorPayload("Open standalone", "open_viz", error, {
      local_command: "open viz/montauk-viz.html",
    }));
  }
}

/* ===== Maintenance orchestrator ============================================
 * One-button flow: spawns scripts/ops/maintenance.py via Tauri, polls
 * runs/operations/maintenance_status.json, drives the modal. */

const maintenanceState = {
  running: false,
  pollHandle: null,
  lastStatus: null,
};

function setMaintenanceModalOpen(open) {
  const modal = document.getElementById("maintenance-modal");
  if (modal) {
    modal.hidden = !open;
    modal.setAttribute("aria-hidden", open ? "false" : "true");
    modal.classList.toggle("is-open", open);
  }
  document.body.classList.toggle("modal-open", open);
}

function closeMaintenanceModal() {
  if (maintenanceState.pollHandle && isMaintenanceTerminal(maintenanceState.lastStatus)) {
    clearInterval(maintenanceState.pollHandle);
    maintenanceState.pollHandle = null;
    maintenanceState.running = false;
  }
  setMaintenanceModalOpen(false);
}

function copyMaintenanceDebug() {
  if (!maintenanceState.lastStatus) return;
  const debug = JSON.stringify(maintenanceState.lastStatus, null, 2);
  navigator.clipboard?.writeText(debug).catch(() => {
    text("maintenance-phase-detail", debug);
  });
}

function maintenancePhases(status) {
  return Array.isArray(status?.phases) ? status.phases : [];
}

function isMaintenanceTerminal(status) {
  const phases = maintenancePhases(status);
  const phaseTerminal = phases.length > 0 && phases.every((phase) =>
    ["ok", "failed", "empty", "skipped"].includes(phase.status)
  );
  return status?.status === "ok" || status?.status === "failed" || phaseTerminal;
}

function hasEmptyResearchQueue(status) {
  return maintenancePhases(status).some((phase) =>
    phase.key === "research" && phase.status === "empty"
  ) || status?.summary?.research?.status === "empty";
}

function renderMaintenanceModal(status) {
  maintenanceState.lastStatus = status;
  const list = document.getElementById("maintenance-steps");
  if (list) {
    list.innerHTML = "";
    const phases = maintenancePhases(status);
    for (const phase of phases) {
      const li = document.createElement("li");
      li.className = `step step-${phase.status || "pending"}`;
      const icon =
        phase.status === "ok"
          ? "✓"
          : phase.status === "failed"
            ? "✕"
            : phase.status === "running"
              ? "▸"
              : phase.status === "empty"
                ? "·"
                : "○";
      li.innerHTML = `
        <span class="step-icon">${icon}</span>
        <span class="step-body">
          <strong>${escapeHtml(phase.label || phase.key)}</strong>
          <small>${escapeHtml(phase.detail || "")}</small>
        </span>
      `;
      list.appendChild(li);
    }
  }
  // Title + progress bar
  const phases = maintenancePhases(status);
  const total = Math.max(phases.length, 1);
  const done = phases.filter((p) => ["ok", "failed", "empty", "skipped"].includes(p.status)).length;
  const current = phases.find((p) => p.status === "running") || phases.find((p) => ["ok", "failed", "empty"].includes(p.status));
  const emptyQueue = hasEmptyResearchQueue(status);
  const terminal = isMaintenanceTerminal(status);
  const titleText = status?.status === "ok"
    ? emptyQueue ? "Maintenance complete — no research queued" : "Maintenance complete"
    : status?.status === "failed"
      ? "Maintenance failed"
      : terminal && emptyQueue
        ? "Maintenance complete — no research queued"
      : status?.status === "starting"
        ? "Starting maintenance…"
        : current?.label || "Working…";
  text("maintenance-phase-title", titleText);
  text(
    "maintenance-phase-detail",
    emptyQueue && terminal
      ? "Data refresh and health checks finished. No approved strategy ideas are queued, so research was skipped."
      : current?.detail || ""
  );
  const fill = document.getElementById("maintenance-bar-fill");
  if (fill) {
    const ratio = terminal ? 1 : done / total;
    fill.style.width = `${Math.max(6, Math.min(100, ratio * 100))}%`;
  }
  // Show Close + Copy Debug at the end
  const closeBtn = document.getElementById("maintenance-close-btn");
  const copyBtn = document.getElementById("maintenance-copy-btn");
  if (closeBtn) {
    closeBtn.hidden = !terminal;
    closeBtn.textContent = emptyQueue && status?.status !== "failed" ? "Continue" : "Close";
  }
  if (copyBtn) copyBtn.hidden = !(status?.status === "failed");
}

async function pollMaintenance() {
  const invoke = tauriInvoke("read_maintenance_status");
  if (!invoke) return null;
  try {
    return await invoke;
  } catch (err) {
    return null;
  }
}

async function runMaintenance(opts = {}) {
  if (maintenanceState.running) {
    setMaintenanceModalOpen(true);
    return;
  }
  const start = tauriInvoke("start_maintenance");
  if (!start) {
    if (!opts.autoLaunched) {
      showActionError(errorPayload("Run Maintenance", "start_maintenance",
        "Tauri bridge is unavailable.", {
          expected_context: "Use /Applications/Montauk.app, not the browser-only dev preview.",
          local_command: ".venv/bin/python scripts/ops/maintenance.py --json",
        }));
    }
    return;
  }
  maintenanceState.running = true;
  const btn = document.getElementById("maintenance-btn");
  if (btn) {
    btn.disabled = true;
    btn.classList.add("is-running");
  }
  setMaintenanceModalOpen(true);
  renderMaintenanceModal({
    status: "starting",
    phases: [
      { key: "daily", label: "Refresh data & recompute signal", detail: "Preparing…", status: "pending" },
      { key: "doctor", label: "Run health checks", detail: "Preparing…", status: "pending" },
      { key: "research", label: "Drain one approved research idea", detail: "Preparing…", status: "pending" },
    ],
  });
  try {
    await start;
  } catch (err) {
    renderMaintenanceModal({
      status: "failed",
      phases: maintenanceState.lastStatus?.phases || [],
      error: err?.message || String(err),
    });
    maintenanceState.running = false;
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("is-running");
    }
    return;
  }
  const tick = async () => {
    const status = await pollMaintenance();
    if (status) renderMaintenanceModal(status);
    const terminal = isMaintenanceTerminal(status);
    if (terminal) {
      clearInterval(maintenanceState.pollHandle);
      maintenanceState.pollHandle = null;
      maintenanceState.running = false;
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("is-running");
      }
      // Pull fresh artifacts back into the rest of the UI.
      await refresh();
      // Hot-reload viz bundle if booted.
      if (vizState.booted && typeof window.__MONTAUK_VIZ__?.reset === "function") {
        window.__MONTAUK_VIZ__.reset();
        vizState.booted = false;
        if (document.body.dataset.view === "viz") ensureVizBooted();
      }
    }
  };
  maintenanceState.pollHandle = setInterval(tick, 350);
  tick();
}

/* ===== Confidence ledger (Doctor) ========================================== */

function deriveConfidencePills(status = state.status) {
  const signal = status.latest_signal || status.latest_operation?.active_signal || {};
  const quality = signal.data_quality || status.latest_operation?.steps?.data_quality?.summary || {};
  const live = status.live_holdout || {};
  const governance = status.governance || {};
  const review = status.strategy_review || {};
  const family = status.family_leaderboard || {};
  const families = family.strategy_family_leaders || [];

  const pills = [];

  const dataOk = (quality.fail ?? 0) === 0 && (quality.total ?? 0) > 0;
  pills.push({
    key: "data",
    label: "Data integrity",
    value: quality.total ? `${quality.pass ?? 0}/${quality.total}` : "—",
    level: dataOk ? "ok" : (quality.fail ?? 0) > 0 ? "fail" : "warn",
    detail: dataOk ? "All sources verified, manifest sha256 matches." : `${quality.fail ?? 0} failed · ${quality.warn ?? 0} warnings.`,
  });

  const replayOk = live.status === "ok" && (live.diverged_count ?? 0) === 0;
  pills.push({
    key: "replay",
    label: "Live replay",
    value: live.snapshot_count ? `${live.diverged_count ?? 0} drift` : "no replay",
    level: replayOk ? "ok" : (live.diverged_count ?? 0) > 0 ? "warn" : "warn",
    detail: live.snapshot_count
      ? `${live.snapshot_count} saved snapshot${live.snapshot_count === 1 ? "" : "s"} replayed.`
      : "No live snapshots yet — backtest only.",
  });

  const champion = review.best_certified || review.active || {};
  const conf = Number(champion.confidence);
  pills.push({
    key: "validation",
    label: "Validation composite",
    value: Number.isFinite(conf) ? `${(conf * 100).toFixed(1)}%` : "—",
    level: !Number.isFinite(conf) ? "warn" : conf >= 0.7 ? "ok" : conf >= 0.4 ? "warn" : "fail",
    detail: `Champion ${champion.display_name || champion.strategy || "?"} composite confidence.`,
  });

  const govState = governance.state || "unknown";
  const govLevel = govState === "active_ok" ? "ok" : govState === "active_blocked" ? "fail" : "warn";
  pills.push({
    key: "governance",
    label: "Governance",
    value: titleCase(govState),
    level: govLevel,
    detail: (governance.reasons || []).slice(0, 2).join(" · ") || "No governance reasons recorded.",
  });

  const familyLeader = families[0];
  if (familyLeader) {
    const familyConf = Number(familyLeader.future_confidence ?? familyLeader.overall_confidence);
    pills.push({
      key: "family",
      label: "Family leader",
      value: Number.isFinite(familyConf) ? `${(familyConf * 100).toFixed(0)}%` : "—",
      level: Number.isFinite(familyConf) && familyConf >= 0.6 ? "ok" : "warn",
      detail: `${familyLeader.display_name || familyLeader.family} (family size ${familyLeader.family_size ?? "?"}).`,
    });
  }

  const warnings = signal.warnings || signal.validation?.warnings || [];
  if (warnings.length) {
    pills.push({
      key: "warnings",
      label: "Active warnings",
      value: `${warnings.length}`,
      level: warnings.length >= 3 ? "warn" : "warn",
      detail: warnings.slice(0, 2).map((w) => String(w)).join(" · "),
    });
  }
  return pills;
}

function overallConfidence(pills) {
  // Composite of the per-pill levels, rendered as 0-100.
  if (!pills.length) return null;
  const score = pills.reduce((acc, pill) => {
    if (pill.level === "ok") return acc + 1.0;
    if (pill.level === "warn") return acc + 0.5;
    return acc + 0.0;
  }, 0) / pills.length;
  return Math.round(score * 100);
}

function renderConfidenceLedger(status = state.status) {
  const pills = deriveConfidencePills(status);
  const score = overallConfidence(pills);
  const number = document.getElementById("confidence-big");
  if (number) {
    number.textContent = score == null ? "—" : `${score}`;
    number.dataset.level = score == null ? "warn" : score >= 70 ? "ok" : score >= 40 ? "warn" : "fail";
  }
  text(
    "confidence-narrative",
    score == null
      ? "Confidence not yet derived."
      : score >= 70
        ? "Position is supported by the active checks."
        : score >= 40
          ? "Some checks are soft. Review the pills below before re-deploying capital."
          : "Multiple checks are failing. Treat the current position as research-only.",
  );
  const host = document.getElementById("ledger-pills");
  if (!host) return;
  host.innerHTML = "";
  for (const pill of pills) {
    const li = document.createElement("div");
    li.className = `pill pill-${pill.level}`;
    li.dataset.tip = pill.detail || "";
    li.innerHTML = `
      <span class="pill-label">${escapeHtml(pill.label)}</span>
      <span class="pill-value">${escapeHtml(pill.value)}</span>
    `;
    host.appendChild(li);
  }
}

/* ===== Flip pressure sparkline ============================================ */

const sparklineState = { points: [] };

async function loadFlipPressureHistory() {
  const invoke = tauriInvoke("read_flip_pressure_history", { days: 60 });
  if (!invoke) return;
  try {
    const payload = await invoke;
    sparklineState.points = Array.isArray(payload?.points) ? payload.points : [];
    drawFlipPressureSparkline();
  } catch (err) {
    // soft fail — sparkline just stays empty
  }
}

function drawFlipPressureSparkline() {
  const canvas = document.getElementById("pressure-spark");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth || canvas.width;
  const cssHeight = canvas.clientHeight || canvas.height;
  if (canvas.width !== cssWidth * dpr) canvas.width = cssWidth * dpr;
  if (canvas.height !== cssHeight * dpr) canvas.height = cssHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const points = sparklineState.points;
  if (!points.length) {
    ctx.fillStyle = "rgba(127, 144, 141, 0.6)";
    ctx.font = "11px Inter, ui-sans-serif, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillText("no history yet — run Maintenance", 8, cssHeight / 2);
    return;
  }
  const padX = 6;
  const padY = 6;
  const w = cssWidth - padX * 2;
  const h = cssHeight - padY * 2;
  const step = points.length > 1 ? w / (points.length - 1) : 0;
  const ys = points.map((p) => Math.max(0, Math.min(100, Number(p.pressure) || 0)));
  const xy = ys.map((y, i) => [padX + i * step, padY + (1 - y / 100) * h]);

  // Gradient fill under the line.
  const grad = ctx.createLinearGradient(0, padY, 0, padY + h);
  grad.addColorStop(0, "rgba(255, 95, 210, 0.45)");
  grad.addColorStop(0.5, "rgba(124, 92, 255, 0.18)");
  grad.addColorStop(1, "rgba(99, 199, 214, 0)");
  ctx.beginPath();
  ctx.moveTo(xy[0][0], padY + h);
  xy.forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.lineTo(xy[xy.length - 1][0], padY + h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Glow line.
  ctx.shadowBlur = 8;
  ctx.shadowColor = "rgba(255, 95, 210, 0.55)";
  ctx.strokeStyle = "#ff5fd2";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  xy.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Last point dot.
  const [lx, ly] = xy[xy.length - 1];
  ctx.fillStyle = "#63c7d6";
  ctx.beginPath();
  ctx.arc(lx, ly, 2.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(99, 199, 214, 0.75)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(lx, ly, 5, 0, Math.PI * 2);
  ctx.stroke();
}

window.addEventListener("resize", () => drawFlipPressureSparkline());

function showView(viewName) {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.getElementById(`${viewName}-view`)?.classList.add("active");
  document.body.dataset.view = viewName;
  if (viewName === "viz") ensureVizBooted();
}

function wireNav() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      showView(button.dataset.view);
    });
  });
}

function wireActions() {
  document.getElementById("maintenance-btn")?.addEventListener("click", runMaintenance);
  document.getElementById("research-enqueue-btn")?.addEventListener("click", enqueueResearchIdeas);
  document.getElementById("doctor-next-research-btn")?.addEventListener("click", runNextResearch);
  document.getElementById("viz-popout-btn")?.addEventListener("click", popoutViz);
  document.getElementById("maintenance-close-btn")?.addEventListener("click", closeMaintenanceModal);
  document.getElementById("maintenance-modal")?.addEventListener("click", (event) => {
    const closeTarget = event.target.closest?.("#maintenance-close-btn, [data-maintenance-close]");
    if (closeTarget || (event.target.id === "maintenance-modal" && isMaintenanceTerminal(maintenanceState.lastStatus))) {
      closeMaintenanceModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isMaintenanceTerminal(maintenanceState.lastStatus)) {
      closeMaintenanceModal();
    }
  });
  document.getElementById("maintenance-copy-btn")?.addEventListener("click", copyMaintenanceDebug);
  document.getElementById("action-error-copy")?.addEventListener("click", copyActionError);
  document.querySelectorAll("button[data-agent-action]").forEach((button) => {
    button.addEventListener("click", () => {
      manageAgent(button.dataset.agentAction, button.dataset.jobKey || "daily");
    });
  });
}

function wireTooltips() {
  const bubble = document.getElementById("tooltip-bubble");
  if (!bubble) return;
  const margin = 12;
  const preferredWidth = 320; // wider so long copy doesn't wrap into 4 lines

  function hide() {
    bubble.classList.remove("visible");
    bubble.hidden = true;
  }

  function place(target) {
    const message = target.dataset.tip;
    if (!message) return;
    bubble.textContent = message;
    bubble.hidden = false;
    bubble.classList.add("visible");

    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;
    // Width budget: prefer 320 but never bigger than the viewport minus margins.
    const maxWidth = Math.min(preferredWidth, viewportW - margin * 2);
    bubble.style.maxWidth = `${maxWidth}px`;

    const rect = target.getBoundingClientRect();
    // Measure the bubble after width clamp so wrapping is settled.
    const tip = bubble.getBoundingClientRect();

    // Prefer placing above the target. Auto-flip below if there isn't room.
    const spaceAbove = rect.top;
    const spaceBelow = viewportH - rect.bottom;
    const placeBelow = spaceAbove < tip.height + margin && spaceBelow >= tip.height + margin;
    let top = placeBelow ? rect.bottom + 10 : rect.top - tip.height - 10;

    // Horizontally, align tip's left edge with target's left edge if possible.
    // If the target is too far right, slide left so the tip stays on-screen.
    let left = rect.left;
    if (left + tip.width > viewportW - margin) {
      left = viewportW - tip.width - margin;
    }
    left = Math.max(margin, left);

    // Clamp vertical if both above and below overflow (very small viewport).
    top = Math.max(margin, Math.min(top, viewportH - tip.height - margin));

    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;
  }

  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest?.("[data-tip]");
    if (target) place(target);
  });
  document.addEventListener("focusin", (event) => {
    const target = event.target.closest?.("[data-tip]");
    if (target) place(target);
  });
  document.addEventListener("mouseout", (event) => {
    if (event.target.closest?.("[data-tip]")) hide();
  });
  document.addEventListener("focusout", (event) => {
    if (event.target.closest?.("[data-tip]")) hide();
  });
  window.addEventListener("scroll", hide, true);
  window.addEventListener("resize", hide);
}

wireNav();
wireActions();
wireTooltips();
document.body.dataset.view = "dashboard";
refresh().then(() => {
  // Auto-run Maintenance on launch so the user opens the app to a fresh state.
  if (window.__TAURI__?.core) runMaintenance({ autoLaunched: true });
});
setInterval(refresh, 60_000);

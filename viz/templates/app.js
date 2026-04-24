/* Montauk Viz — Lightweight-Charts frontend */
(function () {
  "use strict";

  const D = window.__MONTAUK_DATA__;
  if (!D) {
    document.body.innerHTML = '<div style="color:#ef5350;padding:30px;font-family:monospace">' +
      'No __MONTAUK_DATA__ payload. Did build_viz.py run?</div>';
    return;
  }

  /* ---- Time helpers ---- */
  function dateToTime(iso) {
    const [year, month, day] = String(iso).split("-").map(Number);
    return { year, month, day };
  }

  /* ---- Chart factory shared options ---- */
  const baseChartOpts = {
    layout: {
      background: { type: "solid", color: "#0b0d12" },
      textColor: "#7c8493",
      fontSize: 11,
      fontFamily: '-apple-system,BlinkMacSystemFont,"SF Pro Text",Helvetica,Arial,sans-serif',
    },
    grid: {
      vertLines: { color: "#1a1f29" },
      horzLines: { color: "#1a1f29" },
    },
    rightPriceScale: {
      borderColor: "#232a38",
    },
    timeScale: {
      borderColor: "#232a38",
      timeVisible: false,
      secondsVisible: false,
      minBarSpacing: 0.01,
    },
    crosshair: {
      mode: 0, // Normal — free, does not snap to the line
      vertLine: { color: "#3a4458", width: 1, style: 3, labelBackgroundColor: "#1f2532" },
      horzLine: { color: "#3a4458", width: 1, style: 3, labelBackgroundColor: "#1f2532" },
    },
    handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
  };

  /* ---- Build the two charts (drawdown pane removed 2026-04-21) ---- */
  const elPrice = document.getElementById("chart-price");
  const elEquity = document.getElementById("chart-equity");
  const tooltipEl = document.getElementById("tooltip");
  const hoverReadout = document.getElementById("hover-readout");

  const priceChart = LightweightCharts.createChart(elPrice, { ...baseChartOpts });
  const equityChart = LightweightCharts.createChart(elEquity, { ...baseChartOpts });
  const pricePaneOverlay = document.createElement("div");
  pricePaneOverlay.style.position = "absolute";
  pricePaneOverlay.style.inset = "0";
  pricePaneOverlay.style.pointerEvents = "none";
  pricePaneOverlay.style.zIndex = "4";
  elPrice.appendChild(pricePaneOverlay);

  // Bidirectional time-scale sync across both charts.
  const allCharts = [priceChart, equityChart];
  let syncing = false;
  allCharts.forEach((src) => {
    src.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range || syncing) return;
      syncing = true;
      try {
        allCharts.forEach((c) => { if (c !== src) c.timeScale().setVisibleLogicalRange(range); });
      } finally {
        syncing = false;
      }
    });
  });

  // Cross-chart crosshair sync is set up below, after all series are created.

  /* ---- Indexed-to-viewport state + series populator ----
     When enabled, the equity lines renormalize: divide by the value at the
     first visible bar (so viewport-start = 1.0x). */
  const indexedToggle = document.getElementById("toggle-indexed");
  let indexedStartIdx = 0;

  function currentViewportStartIdx() {
    const r = equityChart.timeScale().getVisibleLogicalRange();
    if (!r || r.from == null) return 0;
    return Math.max(0, Math.min(Math.floor(r.from), (activeStrategy?.equity_curve?.length || 1) - 1));
  }

  function applyEquityDrawdownSeries() {
    const strat = activeStrategy;
    if (!strat || !strat.equity_curve) return;
    const curve = strat.equity_curve;
    const indexed = indexedToggle.checked;
    const startIdx = indexed ? currentViewportStartIdx() : 0;

    const stratBase = indexed ? (curve[startIdx]?.equity || 1) : 1;
    const bahBase = indexed ? (curve[startIdx]?.bah_equity || 1) : 1;

    const eqStrat = curve.map((p) => ({ time: dateToTime(p.date), value: (p.equity || 0) / stratBase }));
    const eqBah = curve.map((p) => ({ time: dateToTime(p.date), value: (p.bah_equity || 0) / bahBase }));
    stratEquitySeries.setData(eqStrat);
    bahEquitySeries.setData(eqBah);
  }

  // Recompute on toggle change
  indexedToggle.addEventListener("change", () => applyEquityDrawdownSeries());

  // Recompute on viewport change (only when indexed mode is active — otherwise it's a no-op)
  let reindexRaf = null;
  allCharts.forEach((c) => {
    c.timeScale().subscribeVisibleLogicalRangeChange(() => {
      if (!indexedToggle.checked) return;
      if (reindexRaf) return;
      reindexRaf = requestAnimationFrame(() => {
        reindexRaf = null;
        const newIdx = currentViewportStartIdx();
        if (newIdx !== indexedStartIdx) {
          indexedStartIdx = newIdx;
          applyEquityDrawdownSeries();
        }
      });
    });
  });

  /* ---- Synthetic-period tint (price pane) ----
     Lightweight Charts has no native shading region, so we use a histogram
     series at full height with low-opacity fill over the synthetic bars. */
  const candleSeries = priceChart.addLineSeries({
    color: "#e6e9ef",
    lineWidth: 1,
    priceLineVisible: false,
    crosshairMarkerRadius: 3,
    crosshairMarkerBorderColor: "#e6e9ef",
    crosshairMarkerBackgroundColor: "#0b0d12",
  });

  const tecl = D.tecl;
  const candleData = tecl.dates.map((d, i) => ({
    time: dateToTime(d),
    value: tecl.close[i],
  }));
  candleSeries.setData(candleData);

  // Synthetic tint via separate area series with very low opacity covering only synthetic period.
  if (tecl.synthetic_end_index >= 0 && tecl.synthetic_end_index < tecl.dates.length) {
    const tintData = tecl.dates.map((d, i) => {
      // Only render value during synthetic period; whitespace elsewhere
      if (i <= tecl.synthetic_end_index) {
        return { time: dateToTime(d), value: tecl.high[i] * 1.05 };
      }
      return { time: dateToTime(d) };
    });
    const tintSeries = priceChart.addAreaSeries({
      topColor: "rgba(168, 123, 214, 0.08)",
      bottomColor: "rgba(168, 123, 214, 0.02)",
      lineColor: "rgba(168, 123, 214, 0)",
      lineWidth: 1,
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    tintSeries.setData(tintData);

  }

  function renderSeamBoundary() {
    pricePaneOverlay.innerHTML = "";
    const seamDate = tecl.dates[tecl.synthetic_end_index + 1];
    if (!seamDate) return;

    const x = priceChart.timeScale().timeToCoordinate(dateToTime(seamDate));
    if (x == null || Number.isNaN(x)) return;

    const line = document.createElement("div");
    line.style.position = "absolute";
    line.style.left = `${x}px`;
    line.style.top = "0";
    line.style.bottom = "0";
    line.style.borderLeft = "1px dashed rgba(168, 123, 214, 0.7)";

    const label = document.createElement("div");
    label.textContent = "Real data starts";
    label.style.position = "absolute";
    label.style.left = `${Math.min(x + 8, Math.max(8, elPrice.clientWidth - 120))}px`;
    label.style.top = "10px";
    label.style.padding = "2px 6px";
    label.style.border = "1px solid rgba(168, 123, 214, 0.45)";
    label.style.borderRadius = "3px";
    label.style.background = "rgba(11, 13, 18, 0.88)";
    label.style.color = "#a87bd6";
    label.style.fontSize = "11px";
    label.style.letterSpacing = "0.3px";
    label.style.whiteSpace = "nowrap";

    pricePaneOverlay.appendChild(line);
    pricePaneOverlay.appendChild(label);
  }
  priceChart.timeScale().subscribeVisibleLogicalRangeChange(renderSeamBoundary);

  /* ---- Equity pane ---- */
  const stratEquitySeries = equityChart.addLineSeries({
    color: "#4ea1ff",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true,
    title: "Strategy",
  });
  const bahEquitySeries = equityChart.addLineSeries({
    color: "#7c8493",
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: true,
    title: "B&H",
  });

  // Cross-chart crosshair sync: when the cursor hovers over one chart, the
  // other gets a vertical line at the same time. We pass -Infinity as price
  // so the horizontal crosshair line falls off-screen on the target chart
  // (leaving just the vertical line, which is the shared-time indicator).
  const chartPrimarySeries = [
    [priceChart, candleSeries],
    [equityChart, stratEquitySeries],
  ];
  let crosshairSyncing = false;
  chartPrimarySeries.forEach(([srcChart]) => {
    srcChart.subscribeCrosshairMove((param) => {
      if (crosshairSyncing) return;
      crosshairSyncing = true;
      try {
        if (!param || !param.time) {
          chartPrimarySeries.forEach(([c]) => { if (c !== srcChart) c.clearCrosshairPosition(); });
          return;
        }
        chartPrimarySeries.forEach(([chart, series]) => {
          if (chart === srcChart) return;
          chart.setCrosshairPosition(Number.NEGATIVE_INFINITY, param.time, series);
        });
      } finally { crosshairSyncing = false; }
    });
  });

  /* ---- North-star markers (always on candle series; toggled by visibility) ---- */
  const northStarToggle = document.getElementById("toggle-northstar");
  function buildAllMarkers(strat, includeNorthStar) {
    const m = [];
    if (includeNorthStar && D.markers && D.markers.north_star) {
      D.markers.north_star.forEach((ev) => {
          m.push({
            time: dateToTime(ev.date),
            position: ev.type === "buy" ? "belowBar" : "aboveBar",
            color: ev.type === "buy" ? "#a87bd6" : "#a87bd6",
          shape: "circle",
          text: ev.type === "buy" ? "★ buy" : "★ sell",
          size: 0.9,
        });
      });
    }
    if (strat && strat.trades) {
      strat.trades.forEach((t) => {
        if (t.entry_date) {
          m.push({
            time: dateToTime(t.entry_date),
            position: "belowBar",
            color: "#26a69a",
            shape: "arrowUp",
            text: "▲",
            size: 1,
          });
        }
        if (t.exit_date) {
          // "End of Data" means the backtest force-closed an open position at
          // the last bar to compute a final PnL — NOT a real sell signal. Show
          // it as a neutral "still holding" circle rather than a red sell arrow.
          const isOpen = t.exit_reason === "End of Data";
          m.push({
            time: dateToTime(t.exit_date),
            position: "aboveBar",
            color: isOpen ? "#f0b429" : "#ef5350",
            shape: isOpen ? "circle" : "arrowDown",
            text: isOpen ? "● open" : "▼",
            size: isOpen ? 0.8 : 1,
          });
        }
      });
    }
    // Sort by time ASC (Lightweight Charts requires sorted markers)
    m.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    return m;
  }

  /* ---- Build trades-by-date index for tooltip lookups ---- */
  function buildTradeIndex(strat) {
    const idx = {};
    if (!strat || !strat.trades) return idx;
    strat.trades.forEach((t) => {
      if (t.entry_date) {
        (idx[t.entry_date] ||= []).push({ kind: "entry", trade: t });
      }
      if (t.exit_date) {
        (idx[t.exit_date] ||= []).push({ kind: "exit", trade: t });
      }
    });
    return idx;
  }

  /* ---- Strategy state ---- */
  let activeStrategy = null;
  let activeTradeIndex = {};

  function loadStrategy(strat) {
    activeStrategy = strat;
    activeTradeIndex = buildTradeIndex(strat);

    // Populate equity + drawdown series, respecting the current indexed-to-viewport toggle.
    applyEquityDrawdownSeries();

    // Trade markers
    candleSeries.setMarkers(buildAllMarkers(strat, northStarToggle.checked));

    // Right panel
    renderRightPanel(strat);

    // Active name in toolbar
    document.getElementById("active-name").textContent = `${strat.name} · fitness ${fmtNum(strat.fitness, 3)}`;

    // Sidebar highlight
    document.querySelectorAll(".strat").forEach((el) => {
      el.classList.toggle("active", el.dataset.id === strat.id);
    });
  }

  /* ---- Number formatting ---- */
  function fmtNum(v, dp = 2) {
    if (v == null || isNaN(v)) return "—";
    return Number(v).toLocaleString(undefined, {
      minimumFractionDigits: dp,
      maximumFractionDigits: dp,
    });
  }
  function fmtPct(v, dp = 1) {
    if (v == null || isNaN(v)) return "—";
    return fmtNum(v, dp) + "%";
  }
  function fmtMult(v, dp = 2) {
    if (v == null || isNaN(v)) return "—";
    return fmtNum(v, dp) + "×";
  }

  /* ---- Leaderboard ranking ---- */
  // The leaderboard is a certified set first. Within that set, rows are
  // ordered by all-era performance so the top of the board reflects the
  // strongest certified strategy across full / real / modern history.
  const CONFIDENCE_KEY = {
    label: "Composite confidence (0–100; validation robustness)",
    extract: (s) => (s.composite_confidence != null ? s.composite_confidence : null),
    format: (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}`),
  };
  function admissionLabel(confidence) {
    if (confidence == null) return { tag: "—", cls: "unknown" };
    if (confidence >= 0.70) return { tag: "ADMITTED", cls: "admitted" };
    if (confidence >= 0.60) return { tag: "WATCHLIST", cls: "watchlist" };
    return { tag: "RESEARCH", cls: "research" };
  }

  /* ---- Secondary share-multiple sources ---- */
  // Uses the same multi_era era breakdown the right panel shows, so the two
  // views always agree.
  const SECONDARY_SOURCES = {
    real: {
      label: "real",
      tooltip: "Canonical real-era share multiplier: standalone rerun on TECL from 2008-12-17 forward with fresh capital.",
      extract: (s) => s.multi_era?.eras?.real?.share_multiple ?? null,
    },
    modern: {
      label: "modern",
      tooltip: "Canonical modern-era share multiplier: standalone rerun from 2015 forward with fresh capital.",
      extract: (s) => s.multi_era?.eras?.modern?.share_multiple ?? null,
    },
  };
  let _secondarySource = "real";

  /* ---- Sidebar render ---- */
  function renderSidebar() {
    const list = document.getElementById("strat-list");
    list.innerHTML = "";
    // Rank by balanced all-era performance first among already-certified rows.
    const sorted = D.strategies.slice().sort((a, b) => {
      const as = a.overall_performance_score != null ? a.overall_performance_score : -Infinity;
      const bs = b.overall_performance_score != null ? b.overall_performance_score : -Infinity;
      if (bs !== as) return bs - as;
      const af = a.fitness != null ? a.fitness : -Infinity;
      const bf = b.fitness != null ? b.fitness : -Infinity;
      if (bf !== af) return bf - af;
      const av = CONFIDENCE_KEY.extract(a) ?? -Infinity;
      const bv = CONFIDENCE_KEY.extract(b) ?? -Infinity;
      return bv - av;
    });
    const secondaryDef = SECONDARY_SOURCES[_secondarySource] || SECONDARY_SOURCES.real;
    sorted.forEach((s, idx) => {
      const div = document.createElement("div");
      div.className = "strat" + (s.stale ? " stale" : "");
      div.dataset.id = s.id;
      const sm = s.metrics?.share_multiple;
      const confidence = CONFIDENCE_KEY.extract(s);
      const confStr = CONFIDENCE_KEY.format(confidence);
      const admission = admissionLabel(confidence);
      const cert = s.certified_not_overfit ? "✓" : "·";
      const manual = s.manually_admitted ? '<span class="manual-flag" title="manually admitted — see spirit-memory/decisions.md 2026-04-20-a">★</span>' : "";
      const displayRank = idx + 1;
      const rankLabel = `#${displayRank}`;
      const secondaryVal = secondaryDef.extract(s);
      const secondaryCls = secondaryVal == null
        ? "secondary-mult missing"
        : `secondary-mult ${secondaryVal < 1 ? "bad" : ""}`;
      const secondaryStr = secondaryVal == null ? "— " + secondaryDef.label : `${fmtMult(secondaryVal)} ${secondaryDef.label}`;
      const secondaryTip = `${secondaryDef.tooltip} Value shown: ${secondaryVal == null ? "not available for this strategy" : fmtMult(secondaryVal)}.`;
      div.innerHTML = `
        <div class="row1">
          <span class="rank" title="${CONFIDENCE_KEY.label}">${rankLabel}${manual}</span>
          <span class="name">${escapeHtml(s.name)}</span>
          <span class="metric-col">
            <span class="fitness" title="${CONFIDENCE_KEY.label}">${confStr}</span>
            <span class="${secondaryCls}" title="${escapeHtml(secondaryTip)}">${secondaryStr}</span>
          </span>
        </div>
        <div class="row2">
          <span class="tier ${s.tier || "T0"}">${s.tier || "T0"}</span>
          <span class="admission ${admission.cls}" title="Confidence tier: ${admission.tag}">${admission.tag}</span>
          <span class="mult ${sm < 1 ? "bad" : ""}" title="share multiple vs B&H (full history — includes synthetic pre-2008)">${fmtMult(sm)}</span>
          <span class="cert ${s.certified_not_overfit ? "" : "no"}" title="${s.certified_not_overfit ? "verified not overfit" : "not verified not overfit"}">${cert}</span>
          ${s.stale ? '<span style="color:var(--amber);font-size:10px;">stale</span>' : ""}
        </div>
      `;
      div.addEventListener("click", () => loadStrategy(s));
      list.appendChild(div);
    });
    initBadges();
  }

  function initSecondaryToggle() {
    const group = document.getElementById("secondary-toggle");
    if (!group) return;
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".toggle-btn");
      if (!btn) return;
      const source = btn.dataset.source;
      if (!source || source === _secondarySource) return;
      _secondarySource = source;
      group.querySelectorAll(".toggle-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.source === source);
      });
      renderSidebar();
    });
  }

  /* ---- Right panel render ---- */
  function renderRightPanel(s) {
    document.getElementById("r-name").textContent = s.name;
    const cn = document.getElementById("r-codename");
    if (cn) cn.textContent = s.codename && s.codename !== s.name ? s.codename : "";

    const meta = document.getElementById("r-meta");
    meta.innerHTML = "";
    meta.appendChild(makeBadge(`#${s.rank}`, ""));
    const tierBadge = makeBadge(s.tier || "T0", "");
    tierBadge.classList.add("has-tip");
    tierBadge.dataset.tip = "Validation tier. T0 = hand-authored canonical params (light pipeline). T1 = hand-authored + canonical grid (medium). T2 = GA-tuned or optimizer-discovered (full statistical stack).";
    meta.appendChild(tierBadge);
    meta.appendChild(makeBadge(s.certified_not_overfit ? "verified not overfit ✓" : "not verified not overfit", s.certified_not_overfit ? "ok" : "warn"));
    meta.appendChild(makeBadge(s.backtest_certified ? "artifact bundle emitted" : "artifact bundle not emitted", s.backtest_certified ? "ok" : "warn"));
    const regimeSummary = s.multi_era?.regime_summary;
    if (regimeSummary) {
      meta.appendChild(
        makeBadge(
          regimeSummary.critical_guardrail_passed ? "critical regimes passed" : "critical regime breach",
          regimeSummary.critical_guardrail_passed ? "ok" : "warn",
        )
      );
    }
    if (s.stale) meta.appendChild(makeBadge("stale artifact", "warn"));

    const m = s.metrics || {};
    const metricsEl = document.getElementById("r-metrics");
    metricsEl.innerHTML = "";
    addMetric(metricsEl, "Share multiple", fmtMult(m.share_multiple), m.share_multiple >= 1 ? "pos" : "neg");
    addMetric(metricsEl, "CAGR", fmtPct(m.cagr));
    addMetric(metricsEl, "Max drawdown", fmtPct(m.max_dd), "neg");
    addMetric(metricsEl, "MAR (CAGR/DD)", fmtNum(m.mar, 3));
    addMetric(metricsEl, "Trades", `${m.trades || 0} (${fmtNum(m.trades_yr, 2)}/yr)`);
    addMetric(metricsEl, "Win rate", fmtPct(m.win_rate));
    addMetric(metricsEl, "Regime score", fmtNum(m.regime_score, 3), "", "0-1 composite. 1 = perfect bull capture + bear avoidance. Combines cycle-level bull_capture, bear_avoidance, and concentration.");
    addMetric(metricsEl, "Bull capture", fmtPct(m.bull_capture * 100));
    addMetric(metricsEl, "Bear avoidance", fmtPct(m.bear_avoidance * 100));
    addMetric(metricsEl, "Marker alignment", fmtNum(m.marker_alignment, 3), "", "State-agreement % vs the hand-marked buy/sell cycle file (north-star). 1 = perfectly mirrors Max's hindsight-perfect timing.");
    addMetric(metricsEl, "HHI (concentration)", fmtNum(m.hhi, 3), "", "Herfindahl index of per-trade PnL contribution. Low (0.05-0.15) = diversified across many trades. High (>0.3) = one lucky trade carries the result. Lower is better.");

    // Era breakdown — dual view for "crash insurance vs modern participation"
    // See spirit-memory/decisions.md 2026-04-20 for why this exists.
    renderEraBreakdown(s);
    renderMarketRegimes(s);

    // Scorecard (5Y only — 1Y/3Y are too noisy for low-tpy strategies)
    const sc = s.recent_scorecards || {};
    const scEl = document.getElementById("r-scorecards");
    scEl.innerHTML = "";
    const v5 = sc["5y"] || {};
    const sm5 = v5.share_multiple;
    const cls5 = sm5 == null ? "" : sm5 >= 1 ? "good" : "bad";
    scEl.innerHTML = `
      <div class="scorecard">
        <div class="period">5Y</div>
        <div class="mult ${cls5}">${fmtMult(sm5)}</div>
        <div class="sub">DD ${fmtPct(v5.max_dd)}</div>
        <div class="sub">${v5.trades || 0} trades</div>
      </div>`;

    // Validation — collapsed summary + expandable detail
    const gatesEl = document.getElementById("r-gates");
    const summaryEl = document.getElementById("r-val-summary");
    const vsum = s.validation_summary || {};
    const entries = Object.entries(vsum);
    let pass = 0, skip = 0, warn = 0, fail = 0;
    entries.forEach(([, v]) => {
      const verdict = (typeof v === "object" ? v.verdict : v) || "—";
      if (verdict === "PASS") pass++;
      else if (verdict === "SKIPPED") skip++;
      else if (verdict === "WARN") warn++;
      else if (verdict === "FAIL") fail++;
    });
    // Build summary text
    const parts = [`<span class="vs-pass">${pass} PASS</span>`];
    if (skip) parts.push(`<span class="vs-skip">${skip} skipped (tier)</span>`);
    if (warn) parts.push(`<span class="vs-warn">${warn} WARN</span>`);
    if (fail) parts.push(`<span class="vs-fail">${fail} FAIL</span>`);
    summaryEl.innerHTML = `<span><span class="vs-caret">▸</span>Validation</span><span>${parts.join(" · ")}</span>`;

    // Populate detail
    gatesEl.innerHTML = "";
    entries.forEach(([k, v]) => {
      const verdict = (typeof v === "object" ? v.verdict : v) || "—";
      gatesEl.innerHTML += `<div class="gate-row"><span>${k}</span><span class="gv ${verdict}">${verdict}</span></div>`;
    });
    if (entries.length === 0) {
      gatesEl.innerHTML = '<div style="color:var(--text-3);font-size:11px;">No gate data</div>';
    }
    // Auto-expand if any non-PASS (not counting SKIPPED, which is expected for tier-skipped gates)
    const autoExpand = warn > 0 || fail > 0;
    const expanded = autoExpand;
    gatesEl.classList.toggle("collapsed", !expanded);
    summaryEl.classList.toggle("expanded", expanded);
    summaryEl.onclick = () => {
      const nowExpanded = gatesEl.classList.toggle("collapsed");
      summaryEl.classList.toggle("expanded", !nowExpanded);
    };

    // Params
    const paramsEl = document.getElementById("r-params");
    paramsEl.innerHTML = "";
    const params = s.params || {};
    paramsEl.innerHTML = Object.entries(params)
      .map(([k, v]) => `<span class="pk">${escapeHtml(k)}</span>=<span class="pv">${escapeHtml(String(v))}</span>`)
      .join("  ");
    if (Object.keys(params).length === 0) paramsEl.textContent = "—";
  }

  function renderEraBreakdown(s) {
    const header = document.getElementById("r-era-header");
    const el = document.getElementById("r-era-breakdown");
    if (!el || !header) return;
    const me = s.multi_era;
    if (!me || !me.eras) {
      header.style.display = "none";
      el.style.display = "none";
      el.innerHTML = "";
      return;
    }
    header.style.display = "";
    el.style.display = "";
    const eras = me.eras;
    const decayed = me.decayed || {};
    const full = eras.full || {};
    const real = eras.real || {};
    const modern = eras.modern || {};

    function shareCls(v) { return v == null ? "" : v >= 1 ? "pos" : "neg"; }
    function fmtShare(v) { return v == null ? "—" : fmtMult(v); }
    function fmtFit(v) { return v == null ? "—" : fmtNum(v, 2); }

    const rows = [
      ["Full history (1993–now)", full, "Includes synthetic pre-2008 dotcom era. This is the optimizer's training window and the current leaderboard fitness."],
      ["Real era (2008-12-17 →)", real, "Canonical real-era rerun starting at TECL inception with fresh capital and no pre-2008 carried state."],
      ["Modern era (2015 →)", modern, "Canonical modern-era rerun starting in 2015 with fresh capital and no earlier carried state."],
    ];
    let html = '<table class="era-table"><thead><tr><th></th><th>Share</th><th>CAGR</th><th>Max DD</th><th>Trades</th><th>Fit</th></tr></thead><tbody>';
    for (const [label, data, tip] of rows) {
      const sm = data.share_multiple;
      html += `<tr>
        <td class="era-label has-tip" data-tip="${escapeHtml(tip)}">${label}</td>
        <td class="era-val ${shareCls(sm)}">${fmtShare(sm)}</td>
        <td class="era-val">${data.cagr_pct != null ? fmtPct(data.cagr_pct) : "—"}</td>
        <td class="era-val neg">${data.max_dd_pct != null ? fmtPct(data.max_dd_pct) : "—"}</td>
        <td class="era-val">${data.trades || 0}</td>
        <td class="era-val">${fmtFit(data.fitness)}</td>
      </tr>`;
    }
    html += "</tbody></table>";
    const halfLife = decayed.half_life_years;
    const decayTip = `Time-decayed fitness on full history. Each trade's PnL is weighted by exp(-λ × years_ago) with λ=${decayed.lambda || "—"} (half-life ≈ ${halfLife ? halfLife.toFixed(1) : "—"}y). Recent trades dominate; dotcom-era trades count 1/4×.`;
    html += `<div class="era-decayed has-tip" data-tip="${escapeHtml(decayTip)}">
      <span>Time-decayed fitness (λ=${decayed.lambda || "—"}, half-life ≈ ${halfLife ? halfLife.toFixed(1) : "—"}y)</span>
      <span class="v">${fmtFit(decayed.fitness_decayed)}</span>
    </div>`;
    el.innerHTML = html;
    initBadges(); // re-bind tooltips on the new elements
  }

  function renderMarketRegimes(s) {
    const header = document.getElementById("r-regime-header");
    const el = document.getElementById("r-market-regimes");
    if (!el || !header) return;
    const regimes = s.multi_era?.regimes || [];
    const summary = s.multi_era?.regime_summary || {};
    if (!regimes.length) {
      header.style.display = "none";
      el.style.display = "none";
      el.innerHTML = "";
      return;
    }
    header.style.display = "";
    el.style.display = "";

    function shareCls(v) { return v == null ? "" : v >= 1 ? "pos" : "neg"; }
    function fmtShare(v) { return v == null ? "—" : fmtMult(v); }
    function fmtAlpha(v) {
      if (v == null) return "—";
      return `${v >= 0 ? "+" : ""}${fmtPct(v * 100)}`;
    }
    function kindClass(kind) {
      return kind ? `rg-${kind}` : "";
    }
    function kindLabel(kind) {
      return kind ? String(kind).replace("_", " ") : "—";
    }

    const overall = summary.overall_score;
    const components = summary.components || {};
    const criticalPass = summary.critical_guardrail_passed;
    const failures = summary.critical_failures || [];
    const weakest = summary.weakest_regime;
    let html = '<div class="metric-grid" style="margin-bottom:10px;">';
    html += `
      <div class="metric-row">
        <span class="k has-tip" data-tip="Weighted aggregate of the named regime components below. Emphasizes crash defense and bear survival more than bull capture.">Regime robustness</span>
        <span class="v ${overall != null && overall >= 0.7 ? "pos" : ""}">${overall != null ? `${Math.round(overall * 100)}/100` : "—"}</span>
      </div>`;
    for (const key of ["crash_defense", "bear_survival", "bull_participation", "recovery_capture", "policy_resilience"]) {
      const component = components[key];
      if (!component) continue;
      html += `
      <div class="metric-row">
        <span class="k has-tip" data-tip="Aggregate share-multiple score across the named ${escapeHtml(component.label.toLowerCase())} windows.">${escapeHtml(component.label)}</span>
        <span class="v ${component.score >= 0.7 ? "pos" : component.score < 0.5 ? "neg" : ""}">${Math.round(component.score * 100)}/100</span>
      </div>`;
    }
    const criticalTip = failures.length
      ? `Critical-regime floor is ${(summary.critical_floor || 0).toFixed(2)}x. Breaches: ${failures.map((f) => `${f.label} ${fmtMult(f.share_multiple)}`).join(", ")}.`
      : `Critical-regime floor is ${(summary.critical_floor || 0).toFixed(2)}x across dot-com bust, GFC crash, COVID crash, 2018 tightening drawdown, and 2022 inflation/hiking bear.`;
    html += `
      <div class="metric-row">
        <span class="k has-tip" data-tip="${escapeHtml(criticalTip)}">Critical regimes</span>
        <span class="v ${criticalPass ? "pos" : "neg"}">${criticalPass ? "pass" : `${failures.length} breach${failures.length === 1 ? "" : "es"}`}</span>
      </div>`;
    if (weakest && weakest.label) {
      html += `
      <div class="metric-row">
        <span class="k has-tip" data-tip="Weakest named regime by share multiple versus buy-and-hold.">Weakest regime</span>
        <span class="v ${weakest.share_multiple >= 1 ? "pos" : "neg"}">${escapeHtml(weakest.label)} · ${fmtMult(weakest.share_multiple)}</span>
      </div>`;
    }
    html += "</div>";

    html += '<table class="era-table"><thead><tr><th>Regime</th><th>Type</th><th>Share</th><th>Alpha</th><th>Max DD</th><th>Trades</th></tr></thead><tbody>';
    for (const regime of regimes) {
      const share = regime.share_multiple;
      const alpha = share == null ? null : share - 1.0;
      const tip = regime.description || "";
      html += `<tr>
        <td class="era-label has-tip" data-tip="${escapeHtml(tip)}">${escapeHtml(regime.label || "—")}</td>
        <td class="era-val"><span class="badge ${kindClass(regime.kind)}">${escapeHtml(kindLabel(regime.kind))}</span></td>
        <td class="era-val ${shareCls(share)}">${fmtShare(share)}</td>
        <td class="era-val ${shareCls(share)}">${fmtAlpha(alpha)}</td>
        <td class="era-val neg">${regime.max_dd_pct != null ? fmtPct(regime.max_dd_pct) : "—"}</td>
        <td class="era-val">${regime.trades || 0}</td>
      </tr>`;
    }
    html += "</tbody></table>";
    html += '<div style="color:var(--text-3);font-size:11px;margin-top:8px;">Share is strategy shares vs buy-and-hold over each named window. Alpha is excess share gain/loss versus buy-and-hold.</div>';
    el.innerHTML = html;
    initBadges();
  }

  function addMetric(parent, k, v, cls = "", tip = "") {
    const row = document.createElement("div");
    row.className = "metric-row";
    const kHtml = tip
      ? `<span class="k has-tip" data-tip="${escapeHtml(tip)}">${k}</span>`
      : `<span class="k">${k}</span>`;
    row.innerHTML = `${kHtml}<span class="v ${cls}">${v}</span>`;
    parent.appendChild(row);
  }
  function makeBadge(text, cls) {
    const b = document.createElement("span");
    b.className = "badge " + cls;
    b.textContent = text;
    return b;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  /* ---- Top-bar provenance + generated badges ---- */
  function initBadges() {
    const provText = document.getElementById("prov-text");
    const provBadge = document.getElementById("provenance-badge");
    const ok = D.tecl?.manifest?.sha256;
    if (ok) {
      provText.textContent = `manifest verified (${ok.slice(0, 8)}…)`;
      provBadge.classList.add("ok");
    } else {
      provText.textContent = "manifest missing";
      provBadge.classList.remove("ok");
      provBadge.classList.add("warn");
    }
    document.getElementById("generated-badge").textContent = `built ${D.generated || "—"}`;
  }

  /* ---- Time-range buttons ---- */
  function initRangeButtons() {
    document.querySelectorAll(".btn[data-range]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".btn[data-range]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const range = btn.dataset.range;
        applyRange(range);
      });
    });
  }
  function applyRange(range) {
    const dates = D.tecl.dates;
    if (!dates.length) return;
    const lastDate = new Date(dates[dates.length - 1]);
    const setAllVisibleRange = (from, to) => {
      [priceChart, equityChart].forEach((chart) => {
        chart.timeScale().setVisibleRange({ from, to });
      });
    };
    let from;
    if (range === "ALL") {
      setAllVisibleRange(dateToTime(dates[0]), dateToTime(dates[dates.length - 1]));
      return;
    }
    if (range === "1Y") { from = new Date(lastDate); from.setFullYear(lastDate.getFullYear() - 1); }
    if (range === "5Y") { from = new Date(lastDate); from.setFullYear(lastDate.getFullYear() - 5); }
    if (!from) return;
    const cutoff = from.toISOString().slice(0, 10);
    const fromStr = dates.find((d) => d >= cutoff) || dates[0];
    const toStr = dates[dates.length - 1];
    setAllVisibleRange(dateToTime(fromStr), dateToTime(toStr));
  }

  /* ---- North-star toggle ---- */
  northStarToggle.addEventListener("change", () => {
    if (activeStrategy) {
      candleSeries.setMarkers(buildAllMarkers(activeStrategy, northStarToggle.checked));
    }
  });

  /* ---- Crosshair tooltip + hover readout ---- */
  function setupHover() {
    function findIdxForTime(time) {
      // dates is sorted YYYY-MM-DD strings; time may also be a string or business-day obj
      if (!time) return -1;
      const t = typeof time === "string" ? time
        : (time.year ? `${time.year}-${String(time.month).padStart(2,'0')}-${String(time.day).padStart(2,'0')}` : null);
      if (!t) return -1;
      return D.tecl.dates.indexOf(t);
    }

    priceChart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.point) {
        tooltipEl.style.display = "none";
        hoverReadout.textContent = "";
        return;
      }
      const idx = findIdxForTime(param.time);
      if (idx < 0) {
        tooltipEl.style.display = "none";
        return;
      }
      const t = D.tecl;
      const date = t.dates[idx];
      const o = t.open[idx], h = t.high[idx], l = t.low[idx], c = t.close[idx], v = t.volume[idx];
      const synthBadge = idx <= t.synthetic_end_index
        ? '<span style="color:var(--purple)">[synthetic]</span>' : '';

      let html = `<div class="t-date">${date} ${synthBadge}</div>`;
      html += `O ${fmtNum(o, 2)} · H ${fmtNum(h, 2)}<br>`;
      html += `L ${fmtNum(l, 2)} · C ${fmtNum(c, 2)}<br>`;
      html += `Vol ${(v || 0).toLocaleString()}`;

      const trades = activeTradeIndex[date];
      if (trades) {
        trades.forEach((te) => {
          const tr = te.trade;
          if (te.kind === "entry") {
            html += `<div class="t-trade">▲ ENTRY @ ${fmtNum(tr.entry_price, 2)}</div>`;
          } else if (tr.exit_reason === "End of Data") {
            // Position is still open — backtest force-closed at last bar for PnL accounting only
            html += `<div class="t-trade" style="color:var(--amber)">● STILL OPEN · unrealized ${fmtPct(tr.pnl_pct)} (as of last bar)</div>`;
          } else {
            html += `<div class="t-trade">▼ EXIT @ ${fmtNum(tr.exit_price, 2)} · ${fmtPct(tr.pnl_pct)} · ${tr.exit_reason || "—"}</div>`;
          }
        });
      }

      tooltipEl.innerHTML = html;
      tooltipEl.style.display = "block";

      // Position the tooltip relative to chart container, offset from cursor
      const rect = elPrice.getBoundingClientRect();
      const x = rect.left + param.point.x + 14;
      const y = rect.top + param.point.y + 14;
      const tw = tooltipEl.offsetWidth;
      const th = tooltipEl.offsetHeight;
      const adjX = (x + tw > window.innerWidth - 8) ? rect.left + param.point.x - tw - 14 : x;
      const adjY = (y + th > window.innerHeight - 8) ? rect.top + param.point.y - th - 14 : y;
      tooltipEl.style.left = adjX + "px";
      tooltipEl.style.top = adjY + "px";

      hoverReadout.textContent = `${date}  ·  C ${fmtNum(c, 2)}  ·  Vol ${(v || 0).toLocaleString()}`;
    });

    elPrice.addEventListener("mouseleave", () => {
      tooltipEl.style.display = "none";
      hoverReadout.textContent = "";
    });
  }

  /* ---- Resize handling ---- */
  function fitAll() {
    [
      [priceChart, elPrice],
      [equityChart, elEquity],
    ].forEach(([chart, el]) => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    renderSeamBoundary();
  }
  window.addEventListener("resize", fitAll);

  /* ---- Boot ---- */
  initBadges();
  initSecondaryToggle();
  renderSidebar();
  initRangeButtons();
  setupHover();
  fitAll();

  if (D.strategies && D.strategies.length) {
    loadStrategy(D.strategies[0]);
  }
  applyRange("ALL");
})();

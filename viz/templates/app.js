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
      mode: 1, // Magnet
      vertLine: { color: "#3a4458", width: 1, style: 3, labelBackgroundColor: "#1f2532" },
      horzLine: { color: "#3a4458", width: 1, style: 3, labelBackgroundColor: "#1f2532" },
    },
    handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
  };

  /* ---- Build the three charts ---- */
  const elPrice = document.getElementById("chart-price");
  const elEquity = document.getElementById("chart-equity");
  const elDd = document.getElementById("chart-dd");
  const tooltipEl = document.getElementById("tooltip");
  const hoverReadout = document.getElementById("hover-readout");

  const priceChart = LightweightCharts.createChart(elPrice, { ...baseChartOpts });
  const equityChart = LightweightCharts.createChart(elEquity, { ...baseChartOpts });
  const ddChart = LightweightCharts.createChart(elDd, { ...baseChartOpts });
  const pricePaneOverlay = document.createElement("div");
  pricePaneOverlay.style.position = "absolute";
  pricePaneOverlay.style.inset = "0";
  pricePaneOverlay.style.pointerEvents = "none";
  pricePaneOverlay.style.zIndex = "4";
  elPrice.appendChild(pricePaneOverlay);

  // Sync timescales
  function syncTimeScale(source, others) {
    source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range) return;
      others.forEach((c) => c.timeScale().setVisibleLogicalRange(range));
    });
  }
  syncTimeScale(priceChart, [equityChart, ddChart]);

  /* ---- Synthetic-period tint (price pane) ----
     Lightweight Charts has no native shading region, so we use a histogram
     series at full height with low-opacity fill over the synthetic bars. */
  const candleSeries = priceChart.addCandlestickSeries({
    upColor: "#26a69a",
    downColor: "#ef5350",
    borderUpColor: "#26a69a",
    borderDownColor: "#ef5350",
    wickUpColor: "#26a69a",
    wickDownColor: "#ef5350",
    priceLineVisible: false,
  });

  const tecl = D.tecl;
  const candleData = tecl.dates.map((d, i) => ({
    time: dateToTime(d),
    open: tecl.open[i],
    high: tecl.high[i],
    low: tecl.low[i],
    close: tecl.close[i],
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

  /* ---- Drawdown pane (red area below zero) ---- */
  const ddSeries = ddChart.addAreaSeries({
    topColor: "rgba(239, 83, 80, 0.4)",
    bottomColor: "rgba(239, 83, 80, 0.05)",
    lineColor: "#ef5350",
    lineWidth: 1,
    priceLineVisible: false,
    title: "DD %",
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
          m.push({
            time: dateToTime(t.exit_date),
            position: "aboveBar",
            color: "#ef5350",
            shape: "arrowDown",
            text: "▼",
            size: 1,
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

    // Update equity curves
    const eqStrat = (strat.equity_curve || []).map((p) => ({ time: dateToTime(p.date), value: p.equity }));
    const eqBah = (strat.equity_curve || []).map((p) => ({ time: dateToTime(p.date), value: p.bah_equity }));
    stratEquitySeries.setData(eqStrat);
    bahEquitySeries.setData(eqBah);

    // Drawdown — make values negative so they live below zero
    const dd = (strat.equity_curve || []).map((p) => ({
      time: dateToTime(p.date),
      value: -Math.abs(p.drawdown_pct || 0),
    }));
    ddSeries.setData(dd);

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

  /* ---- Sidebar render ---- */
  function renderSidebar() {
    const list = document.getElementById("strat-list");
    list.innerHTML = "";
    D.strategies.forEach((s) => {
      const div = document.createElement("div");
      div.className = "strat" + (s.stale ? " stale" : "");
      div.dataset.id = s.id;
      const sm = s.metrics?.share_multiple;
      const cert = s.backtest_certified ? "✓" : "·";
      div.innerHTML = `
        <div class="row1">
          <span class="rank">#${s.rank}</span>
          <span class="name">${escapeHtml(s.name)}</span>
          <span class="fitness">${fmtNum(s.fitness, 2)}</span>
        </div>
        <div class="row2">
          <span class="tier ${s.tier || "T0"}">${s.tier || "T0"}</span>
          <span class="mult ${sm < 1 ? "bad" : ""}">${fmtMult(sm)}</span>
          <span class="cert ${s.backtest_certified ? "" : "no"}" title="${s.backtest_certified ? "backtest certified" : "not certified"}">${cert}</span>
          ${s.stale ? '<span style="color:var(--amber);font-size:10px;">stale</span>' : ""}
        </div>
      `;
      div.addEventListener("click", () => loadStrategy(s));
      list.appendChild(div);
    });
  }

  /* ---- Right panel render ---- */
  function renderRightPanel(s) {
    document.getElementById("r-name").textContent = s.name;

    const meta = document.getElementById("r-meta");
    meta.innerHTML = "";
    meta.appendChild(makeBadge(`#${s.rank}`, ""));
    meta.appendChild(makeBadge(s.tier || "T0", ""));
    meta.appendChild(makeBadge(s.backtest_certified ? "certified ✓" : "not certified", s.backtest_certified ? "ok" : "warn"));
    meta.appendChild(makeBadge(s.promotion_ready ? "promo-ready" : "not promo-ready", s.promotion_ready ? "ok" : ""));
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
    addMetric(metricsEl, "Regime score", fmtNum(m.regime_score, 3));
    addMetric(metricsEl, "Bull capture", fmtPct(m.bull_capture * 100));
    addMetric(metricsEl, "Bear avoidance", fmtPct(m.bear_avoidance * 100));
    addMetric(metricsEl, "Marker alignment", fmtNum(m.marker_alignment, 3));
    addMetric(metricsEl, "HHI (concentration)", fmtNum(m.hhi, 3));

    // Scorecards
    const sc = s.recent_scorecards || {};
    const scEl = document.getElementById("r-scorecards");
    scEl.innerHTML = "";
    ["1y", "3y", "5y"].forEach((p) => {
      const v = sc[p] || {};
      const sm = v.share_multiple;
      const cls = sm == null ? "" : sm >= 1 ? "good" : "bad";
      scEl.innerHTML += `
        <div class="scorecard">
          <div class="period">${p.toUpperCase()}</div>
          <div class="mult ${cls}">${fmtMult(sm)}</div>
          <div class="sub">DD ${fmtPct(v.max_dd)}</div>
          <div class="sub">${v.trades || 0} trades</div>
        </div>`;
    });

    // Gates
    const gatesEl = document.getElementById("r-gates");
    gatesEl.innerHTML = "";
    const vsum = s.validation_summary || {};
    Object.entries(vsum).forEach(([k, v]) => {
      const verdict = (typeof v === "object" ? v.verdict : v) || "—";
      gatesEl.innerHTML += `<div class="gate-row"><span>${k}</span><span class="gv ${verdict}">${verdict}</span></div>`;
    });
    if (Object.keys(vsum).length === 0) {
      gatesEl.innerHTML = '<div style="color:var(--text-3);font-size:11px;">No gate data</div>';
    }

    // Params
    const paramsEl = document.getElementById("r-params");
    paramsEl.innerHTML = "";
    const params = s.params || {};
    paramsEl.innerHTML = Object.entries(params)
      .map(([k, v]) => `<span class="pk">${escapeHtml(k)}</span>=<span class="pv">${escapeHtml(String(v))}</span>`)
      .join("  ");
    if (Object.keys(params).length === 0) paramsEl.textContent = "—";
  }

  function addMetric(parent, k, v, cls = "") {
    const row = document.createElement("div");
    row.className = "metric-row";
    row.innerHTML = `<span class="k">${k}</span><span class="v ${cls}">${v}</span>`;
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
      [priceChart, equityChart, ddChart].forEach((chart) => {
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
      [ddChart, elDd],
    ].forEach(([chart, el]) => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    renderSeamBoundary();
  }
  window.addEventListener("resize", fitAll);

  /* ---- Boot ---- */
  initBadges();
  renderSidebar();
  initRangeButtons();
  setupHover();
  fitAll();

  if (D.strategies && D.strategies.length) {
    loadStrategy(D.strategies[0]);
  }
  applyRange("ALL");
})();

"use strict";

const TIER = {
  0: { name: "Safe", color: "#059669" },
  1: { name: "Watch", color: "#d97706" },
  2: { name: "High Risk", color: "#ea580c" },
  3: { name: "Critical", color: "#dc2626" },
};

const RESULT_COLOR = {
  Pass: "#059669",
  Distinction: "#2563eb",
  Fail: "#ea580c",
  Withdrawn: "#dc2626",
};

const GENDER = { M: "Male", F: "Female" };

const PLY_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: {
    family: "'Plus Jakarta Sans', system-ui, sans-serif",
    size: 11.5,
    color: "#4e5f73",
  },
};

const PLY_CFG = { displayModeBar: false, responsive: true, scrollZoom: true };

const Dashboard = (() => {
  let _drawn = {
    donut: false,
    actual: false,
    scatter: false,
    module: false,
    ageband: false,
  };

  function _set(id, val) {
    const el = document.getElementById(id);
    if (el)
      el.textContent = typeof val === "number" ? val.toLocaleString() : val;
  }

  function _bar(pct, color) {
    return `<div class="attention-bar-fill" style="width:${Math.min(100, Math.max(0, pct))}%;background:${color};"></div>`;
  }

  /* ── Predicted risk donut ────────────────────────────────────────────── */
  function _donut(s) {
    const data = [
      {
        type: "pie",
        hole: 0.55,
        values: [s.safe, s.watch, s.high_risk, s.critical],
        labels: ["Safe", "Watch", "High Risk", "Critical"],
        marker: { colors: Object.values(TIER).map((t) => t.color) },
        textinfo: "percent",
        textfont: { family: "'Space Mono', monospace", size: 10.5 },
        hovertemplate:
          "<b>%{label}</b><br>%{value:,} students (%{percent})<extra></extra>",
        sort: false,
        direction: "clockwise",
      },
    ];

    const layout = {
      ...PLY_BASE,
      margin: { t: 0, r: 0, b: 0, l: 0 },
      showlegend: true,
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.06,
        font: { size: 11 },
        itemgap: 12,
      },
    };

    const fn = _drawn.donut ? Plotly.react : Plotly.newPlot;
    fn("chart-donut", data, layout, PLY_CFG);
    _drawn.donut = true;
  }

  /* ── Actual outcome donut ────────────────────────────────────────────── */
  function _actualDonut(rows) {
    const counts = { Pass: 0, Distinction: 0, Fail: 0, Withdrawn: 0 };
    rows.forEach((d) => {
      if (counts[d.final_result] !== undefined) counts[d.final_result]++;
    });

    const labels = Object.keys(counts);
    const values = Object.values(counts);
    const colors = labels.map((l) => RESULT_COLOR[l]);

    const data = [
      {
        type: "pie",
        hole: 0.55,
        values,
        labels,
        marker: { colors },
        textinfo: "percent",
        textfont: { family: "'Space Mono', monospace", size: 10.5 },
        hovertemplate:
          "<b>%{label}</b><br>%{value:,} students (%{percent})<extra></extra>",
        sort: false,
      },
    ];

    const layout = {
      ...PLY_BASE,
      margin: { t: 0, r: 0, b: 0, l: 0 },
      showlegend: true,
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.06,
        font: { size: 11 },
        itemgap: 12,
      },
    };

    const fn = _drawn.actual ? Plotly.react : Plotly.newPlot;
    fn("chart-actual", data, layout, PLY_CFG);
    _drawn.actual = true;
  }

  /* ── Score vs engagement scatter (WebGL) ─────────────────────────────── */
  function _scatter(rows) {
    const groups = { 0: [], 1: [], 2: [], 3: [] };
    rows.forEach((d) => {
      const t = d.risk ?? 0;
      if (groups[t]) groups[t].push(d);
    });

    const traces = [0, 1, 2, 3].map((tier) => {
      const pts = groups[tier];
      return {
        type: "scattergl",
        mode: "markers",
        name: TIER[tier].name,
        x: pts.map((d) => d.score),
        y: pts.map((d) => d.clicks),
        text: pts.map((d) => d.id),
        hovertemplate:
          "<b>%{text}</b><br>Score: %{x:.1f}<br>Clicks: %{y:,}<extra>" +
          TIER[tier].name +
          "</extra>",
        marker: { color: TIER[tier].color, size: 4.5, opacity: 0.6 },
      };
    });

    const layout = {
      ...PLY_BASE,
      margin: { t: 8, r: 16, b: 52, l: 60 },
      xaxis: {
        title: { text: "Average score", standoff: 10 },
        range: [-2, 102],
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      yaxis: {
        title: { text: "Total clicks", standoff: 10 },
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      legend: { orientation: "h", y: -0.16, font: { size: 11 }, itemgap: 16 },
      hovermode: "closest",
    };

    const fn = _drawn.scatter ? Plotly.react : Plotly.newPlot;
    fn("chart-scatter", traces, layout, PLY_CFG);
    _drawn.scatter = true;
    _set("scatter-count", rows.length.toLocaleString());
  }

  /* ── Risk by module ──────────────────────────────────────────────────── */
  function _moduleChart(rows) {
    const counts = {};
    rows.forEach((d) => {
      const mod = d.code_module || "Unknown";
      if (!counts[mod]) counts[mod] = { crit: 0, high: 0 };
      if (d.risk === 3) counts[mod].crit++;
      else if (d.risk === 2) counts[mod].high++;
    });

    const modules = Object.entries(counts)
      .map(([mod, c]) => ({
        mod,
        crit: c.crit,
        high: c.high,
        total: c.crit + c.high,
      }))
      .filter((x) => x.total > 0)
      .sort((a, b) => b.total - a.total);

    if (!modules.length) return;

    const labels = modules.map((x) => x.mod);
    const traces = [
      {
        type: "bar",
        name: "Critical",
        x: modules.map((x) => x.crit),
        y: labels,
        orientation: "h",
        marker: { color: TIER[3].color },
        hovertemplate: "<b>%{y}</b> — Critical: %{x}<extra></extra>",
      },
      {
        type: "bar",
        name: "High Risk",
        x: modules.map((x) => x.high),
        y: labels,
        orientation: "h",
        marker: { color: TIER[2].color },
        hovertemplate: "<b>%{y}</b> — High Risk: %{x}<extra></extra>",
      },
    ];

    const layout = {
      ...PLY_BASE,
      barmode: "stack",
      margin: { t: 8, r: 16, b: 36, l: 52 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      yaxis: { tickfont: { size: 11 }, automargin: true },
      legend: { orientation: "h", y: -0.2, font: { size: 11 }, itemgap: 12 },
      showlegend: false,
    };

    const fn = _drawn.module ? Plotly.react : Plotly.newPlot;
    fn("chart-module", traces, layout, PLY_CFG);
    _drawn.module = true;
  }

  /* ── Risk by age band ────────────────────────────────────────────────── */
  function _ageBandChart(rows) {
    const bands = {};
    rows.forEach((d) => {
      const band = d.age_band || "Unknown";
      if (!bands[band]) bands[band] = { 0: 0, 1: 0, 2: 0, 3: 0 };
      bands[band][d.risk]++;
    });

    // Plotly horizontal bars render y values bottom→top, so reverse order
    // to put 0-35 (most students) at the top and 55<= at the bottom
    const ORDER = ["55<=", "35-55", "0-35"];
    const labels = Object.keys(bands).sort((a, b) => {
      const ia = ORDER.indexOf(a),
        ib = ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });

    if (!labels.length) return;

    // Render Critical → Safe so legend reads worst-to-best (matches donut convention)
    const traces = [3, 2, 1, 0].map((tier) => ({
      type: "bar",
      name: TIER[tier].name,
      x: labels.map((l) => bands[l][tier]),
      y: labels,
      orientation: "h",
      marker: { color: TIER[tier].color },
      hovertemplate:
        "<b>%{y}</b> — " + TIER[tier].name + ": %{x:,}<extra></extra>",
    }));

    const layout = {
      ...PLY_BASE,
      barmode: "stack",
      margin: { t: 8, r: 16, b: 36, l: 52 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      yaxis: { tickfont: { size: 11 }, automargin: true },
      legend: { orientation: "h", y: -0.2, font: { size: 11 }, itemgap: 8 },
    };

    const fn = _drawn.ageband ? Plotly.react : Plotly.newPlot;
    fn("chart-ageband", traces, layout, PLY_CFG);
    _drawn.ageband = true;
  }

  /* ── Attention list (enriched) ───────────────────────────────────────── */
  function _attentionList(rows) {
    const urgent = rows
      .filter((d) => d.risk >= 2)
      .sort((a, b) => {
        if (b.withdrew_early !== a.withdrew_early)
          return b.withdrew_early - a.withdrew_early;
        if (b.risk !== a.risk) return b.risk - a.risk;
        return a.score - b.score;
      })
      .slice(0, 10);

    const el = document.getElementById("attention-list");
    if (!el) return;

    if (!urgent.length) {
      el.innerHTML =
        '<div class="attention-empty text-3 text-sm">No critical or high-risk students found.</div>';
      return;
    }

    el.innerHTML = urgent
      .map((d) => {
        const t = TIER[d.risk];
        const scorePct = Math.max(0, Math.min(100, d.score));
        const subPct = Math.max(
          0,
          Math.min(100, (d.submission_rate ?? 0) * 100),
        );
        const scoreColor = d.risk === 3 ? "#dc2626" : "#ea580c";
        const subColor =
          subPct < 40 ? "#dc2626" : subPct < 70 ? "#d97706" : "#059669";
        const module = d.code_module || "—";

        // Demographic context
        const genderStr = GENDER[d.gender] || d.gender || "";
        const ageStr = d.age_band || "";
        const demoStr = [genderStr, ageStr].filter(Boolean).join(" · ");

        const withdrewPill = d.withdrew_early
          ? `<span class="withdrew-pill"><i class="fas fa-person-walking-arrow-right"></i> Withdrew</span>`
          : "";

        return `
        <a class="attention-row" href="/students?search=${encodeURIComponent(d.id)}">
          <span class="attention-id">${d.id}</span>
          <span class="attention-meta">
            <span class="attention-meta-top">
              <span class="attention-module">${module}</span>
              ${demoStr ? `<span class="attention-demo">${demoStr}</span>` : ""}
              ${withdrewPill}
            </span>
            <span class="attention-bars">
              <span class="attention-bar-row">
                <span class="attention-bar-label">Score</span>
                <span class="attention-bar-wrap">${_bar(scorePct, scoreColor)}</span>
                <span class="attention-bar-val">${d.score.toFixed(1)}</span>
              </span>
              <span class="attention-bar-row">
                <span class="attention-bar-label">Sub.</span>
                <span class="attention-bar-wrap">${_bar(subPct, subColor)}</span>
                <span class="attention-bar-val">${subPct.toFixed(0)}%</span>
              </span>
            </span>
          </span>
          <span class="attention-badge-col">
            <span class="badge ${d.risk === 3 ? "badge-crit" : "badge-high"}">${t.name}</span>
          </span>
        </a>`;
      })
      .join("");
  }

  /* ── Fetch & render ──────────────────────────────────────────────────── */
  async function _fetch() {
    try {
      const res = await fetch("/api/realtime-data");
      if (!res.ok) throw new Error("API " + res.status);
      const data = await res.json();

      const s = data.summary;
      _set("stat-total", s.total);
      _set("stat-safe", s.safe);
      _set("stat-watch", s.watch);
      _set("stat-high", s.high_risk);
      _set("stat-crit", s.critical);
      if (s.last_updated) _set("last-updated", "Updated " + s.last_updated);

      _donut(s);
      _actualDonut(data.raw_data);
      _moduleChart(data.raw_data);
      _ageBandChart(data.raw_data);
      _attentionList(data.raw_data);
      _scatter(data.raw_data);
    } catch (err) {
      console.error("[Dashboard]", err);
    }
  }

  async function refresh() {
    const btn = document.getElementById("refresh-btn");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-rotate-right fa-spin"></i>';
    }
    try {
      await fetch("/api/refresh-cache", { method: "POST" });
      await _fetch();
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-rotate-right"></i> Refresh';
      }
    }
  }

  function init() {
    _fetch();
    setInterval(_fetch, 15_000);
  }

  return { init, refresh };
})();

document.addEventListener("DOMContentLoaded", Dashboard.init);

"use strict";

const TIER = {
  0: { label: "Safe", color: "#059669", cls: "badge-safe" },
  1: { label: "Watch", color: "#d97706", cls: "badge-watch" },
  2: { label: "High Risk", color: "#ea580c", cls: "badge-high" },
  3: { label: "Critical", color: "#dc2626", cls: "badge-crit" },
};

const PLY_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: {
    family: "'Plus Jakarta Sans', system-ui, sans-serif",
    size: 11.5,
    color: "#4e5f73",
  },
};

const PLY_CFG = { displayModeBar: false, responsive: true };

const Cohort = (() => {
  let _module = "";
  let _presentation = "";
  let _drawn = { score: false, age: false, edu: false };

  function _set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function _pct(v) {
    return (v * 100).toFixed(1) + "%";
  }
  function _fmt(n) {
    return Number(n).toLocaleString();
  }

  function _hideLoading(id) {
    const el = document.getElementById(id + "-loading");
    if (el) el.classList.add("hidden");
  }

  /* ── URL state ────────────────────────────────────────────────────────── */
  function _pushState() {
    const p = new URLSearchParams();
    if (_module) p.set("module", _module);
    if (_presentation) p.set("presentation", _presentation);
    history.pushState(
      { module: _module, presentation: _presentation },
      "",
      "/cohort" + (p.toString() ? "?" + p.toString() : ""),
    );
  }

  function _restoreFromURL() {
    const p = new URLSearchParams(window.location.search);
    _module = p.get("module") || "";
    _presentation = p.get("presentation") || "";
  }

  function _syncDropdowns() {
    const modSel = document.getElementById("cohort-module");
    const presSel = document.getElementById("cohort-presentation");
    if (modSel) modSel.value = _module;
    if (presSel) presSel.value = _presentation;
  }

  /* ── Health strip ─────────────────────────────────────────────────────── */
  function _renderHealth(h) {
    const heroLoading = document.getElementById("cohort-hero-loading");
    if (heroLoading) heroLoading.classList.add("hidden");

    if (!h.enrollments) {
      _set("ch-enrollments", "—");
      _set("ch-students-note", "no enrollment data");
      _set("ch-at-risk", "—");
      _set("ch-at-risk-note", "Critical + High Risk");
      _set("ch-avg-score", "—");
      _set("ch-avg-eng", "—");
      _set("ch-withdrawal", "—");
      _set("ch-reattempt", "—");
      return;
    }

    _set("ch-enrollments", _fmt(h.enrollments));
    _set(
      "ch-students-note",
      `${_fmt(h.unique_students)} unique student${h.unique_students !== 1 ? "s" : ""}`,
    );

    const atRisk = h.critical + h.high_risk;
    const atRiskPct = h.enrollments
      ? ((atRisk / h.enrollments) * 100).toFixed(1)
      : "0.0";
    _set("ch-at-risk", _fmt(atRisk));
    _set("ch-at-risk-note", `${atRiskPct}% · Critical + High Risk`);

    _set("ch-avg-score", h.avg_score.toFixed(1));
    _set("ch-avg-eng", _pct(h.avg_engagement));
    _set("ch-withdrawal", _pct(h.withdrawal_rate));
    _set("ch-reattempt", _pct(h.reattempt_rate));
  }

  /* ── Score distribution chart ─────────────────────────────────────────── */
  function _renderScoreDist(buckets) {
    const labels = buckets.map((b) => b.label);
    const traces = [3, 2, 1, 0].map((tier) => ({
      type: "bar",
      name: TIER[tier].label,
      x: labels,
      y: buckets.map(
        (b) => b[{ 3: "crit", 2: "high", 1: "watch", 0: "safe" }[tier]],
      ),
      marker: { color: TIER[tier].color },
      hovertemplate:
        "<b>%{x}</b><br>" + TIER[tier].label + ": %{y}<extra></extra>",
    }));

    const layout = {
      ...PLY_BASE,
      barmode: "stack",
      margin: { t: 8, r: 16, b: 36, l: 44 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 9.5 },
      },
      yaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 9.5 },
      },
      legend: { orientation: "h", y: -0.16, font: { size: 10 }, itemgap: 10 },
      showlegend: true,
    };

    const fn = _drawn.score ? Plotly.react : Plotly.newPlot;
    fn("chart-score-dist", traces, layout, PLY_CFG);
    if (!_drawn.score) _hideLoading("chart-score-dist");
    _drawn.score = true;
  }

  /* ── Risk driver table ────────────────────────────────────────────────── */
  function _renderDriverTable(rows) {
    const wrap = document.getElementById("cohort-driver-table");
    if (!wrap) return;

    _hideLoading("cohort-driver");
    wrap.classList.remove("hidden");

    if (!rows.length) {
      wrap.innerHTML = `<div class="cohort-table-empty text-3 text-sm">No data for the selected cohort.</div>`;
      return;
    }

    wrap.innerHTML = `
      <table class="cohort-table">
        <thead>
          <tr>
            <th>Tier</th>
            <th>Count</th>
            <th>Avg score</th>
            <th>Submission</th>
            <th>Engagement</th>
            <th>Active days</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((r) => {
              const t = TIER[r.tier];
              return `<tr>
              <td><span class="badge ${t.cls}">${t.label}</span></td>
              <td>${_fmt(r.count)}</td>
              <td>${r.avg_score.toFixed(1)}</td>
              <td>${(r.avg_submission * 100).toFixed(1)}%</td>
              <td>${(r.avg_engagement * 100).toFixed(1)}%</td>
              <td>${r.avg_active_days.toFixed(1)}</td>
            </tr>`;
            })
            .join("")}
        </tbody>
      </table>`;
  }

  /* ── Age band chart ───────────────────────────────────────────────────── */
  function _renderAgeBand(data) {
    const labels = data.map((d) => d.band);
    const traces = [3, 2, 1, 0].map((tier) => ({
      type: "bar",
      name: TIER[tier].label,
      orientation: "h",
      y: labels,
      x: data.map(
        (d) => d[{ 3: "crit", 2: "high", 1: "watch", 0: "safe" }[tier]],
      ),
      marker: { color: TIER[tier].color },
      hovertemplate:
        "<b>%{y}</b> — " + TIER[tier].label + ": %{x}<extra></extra>",
    }));

    const layout = {
      ...PLY_BASE,
      barmode: "stack",
      margin: { t: 8, r: 16, b: 32, l: 52 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 9.5 },
      },
      yaxis: { tickfont: { size: 10.5 }, automargin: true },
      legend: { orientation: "h", y: -0.22, font: { size: 10 }, itemgap: 8 },
    };

    const fn = _drawn.age ? Plotly.react : Plotly.newPlot;
    fn("chart-age-band", traces, layout, PLY_CFG);
    if (!_drawn.age) _hideLoading("chart-age-band");
    _drawn.age = true;
  }

  /* ── Education chart ──────────────────────────────────────────────────── */
  function _renderEducation(data) {
    const labels = data.map((d) => d.level);
    const traces = [3, 2, 1, 0].map((tier) => ({
      type: "bar",
      name: TIER[tier].label,
      orientation: "h",
      y: labels,
      x: data.map(
        (d) => d[{ 3: "crit", 2: "high", 1: "watch", 0: "safe" }[tier]],
      ),
      marker: { color: TIER[tier].color },
      hovertemplate:
        "<b>%{y}</b> — " + TIER[tier].label + ": %{x}<extra></extra>",
    }));

    const layout = {
      ...PLY_BASE,
      barmode: "stack",
      margin: { t: 8, r: 16, b: 32, l: 16 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 9.5 },
      },
      yaxis: { tickfont: { size: 10 }, automargin: true },
      legend: { orientation: "h", y: -0.22, font: { size: 10 }, itemgap: 8 },
    };

    const fn = _drawn.edu ? Plotly.react : Plotly.newPlot;
    fn("chart-education", traces, layout, PLY_CFG);
    if (!_drawn.edu) _hideLoading("chart-education");
    _drawn.edu = true;
  }

  /* ── PDF export link — disabled during fetch and when no data ────────── */
  function _updatePdfLink(hasData) {
    const btn = document.getElementById("cohort-pdf-btn");
    if (!btn) return;
    if (!hasData) {
      btn.classList.add("btn-disabled");
      return;
    }
    btn.classList.remove("btn-disabled");
    const p = new URLSearchParams();
    if (_module) p.set("module", _module);
    if (_presentation) p.set("presentation", _presentation);
    btn.href = "/api/cohort/report" + (p.toString() ? "?" + p.toString() : "");
  }

  /* ── Resize observer ──────────────────────────────────────────────────── */
  function _initResizeObserver() {
    if (typeof ResizeObserver === "undefined") return;
    ["chart-score-dist", "chart-age-band", "chart-education"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (el.children.length) {
            setTimeout(() => {
              Plotly.relayout(el, { width: null, height: null }).then(() => {
                Plotly.Plots.resize(el);
              });
            }, 100);
          }
        });
      }).observe(el);
    });
  }

  /* ── Fetch & render ───────────────────────────────────────────────────── */
  async function fetch() {
    const p = new URLSearchParams();
    if (_module) p.set("module", _module);
    if (_presentation) p.set("presentation", _presentation);

    try {
      const res = await window.fetch(
        "/api/cohort/data" + (p.toString() ? "?" + p.toString() : ""),
      );
      const data = await res.json();

      const d = res.ok
        ? data
        : {
            health: {
              enrollments: 0,
              unique_students: 0,
              critical: 0,
              high_risk: 0,
              watch: 0,
              safe: 0,
              withdrawal_rate: 0,
              reattempt_rate: 0,
              avg_score: 0,
              avg_engagement: 0,
            },
            score_distribution: [],
            risk_driver: [],
            age_band: [],
            education: [],
          };

      _renderHealth(d.health);
      _renderScoreDist(d.score_distribution);
      _renderDriverTable(d.risk_driver);
      _renderAgeBand(d.age_band);
      _renderEducation(d.education);
      _updatePdfLink(d.health.enrollments > 0);
    } catch (err) {
      console.error("[Cohort]", err);
      _updatePdfLink(false);
    }
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */
  function init() {
    _restoreFromURL();
    _syncDropdowns();

    const modSel = document.getElementById("cohort-module");
    const presSel = document.getElementById("cohort-presentation");

    if (modSel) {
      modSel.addEventListener("change", () => {
        _module = modSel.value;
        _drawn = { score: false, age: false, edu: false };
        _pushState();
        fetch();
      });
    }

    if (presSel) {
      presSel.addEventListener("change", () => {
        _presentation = presSel.value;
        _drawn = { score: false, age: false, edu: false };
        _pushState();
        fetch();
      });
    }

    window.addEventListener("popstate", (e) => {
      if (e.state) {
        _module = e.state.module || "";
        _presentation = e.state.presentation || "";
      } else {
        _restoreFromURL();
      }
      _syncDropdowns();
      _drawn = { score: false, age: false, edu: false };
      fetch();
    });

    _initResizeObserver();
    fetch();
  }

  return { init, fetch };
})();

document.addEventListener("DOMContentLoaded", Cohort.init);

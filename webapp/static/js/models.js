"use strict";

const Models = (() => {
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

  // Injected by the template
  let _models = [];
  let _history = {};

  const COLORS = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed"];

  /* ── Radar chart ─────────────────────────────────────────────────────── */
  function _radar() {
    if (!_models.length) return;

    const axes = ["AUC", "CV-AUC", "Accuracy", "Precision", "Recall", "F1"];
    const keys = ["auc", "cv_auc", "accuracy", "precision", "recall", "f1"];

    const traces = _models.map((m, i) => {
      // Replace cv_auc=0 with null when CV was skipped — avoids misleading
      // zero spike on the radar for non-Spark-ML models (e.g. XGBoost)
      const vals = keys.map((k) =>
        k === "cv_auc" && m[k] === 0 ? null : m[k],
      );
      return {
        type: "scatterpolar",
        name: m.name,
        r: [...vals, vals[0]],
        theta: [...axes, axes[0]],
        fill: "toself",
        fillcolor: COLORS[i % COLORS.length] + "22",
        line: { color: COLORS[i % COLORS.length], width: 2 },
        connectgaps: false,
        hovertemplate:
          "<b>" + m.name + "</b><br>%{theta}: %{r:.4f}<extra></extra>",
      };
    });

    const layout = {
      ...PLY_BASE,
      polar: {
        radialaxis: {
          visible: true,
          range: [0, 1],
          tickfont: { size: 9, family: "'Space Mono', monospace" },
          gridcolor: "#e2e8f0",
        },
        angularaxis: {
          tickfont: { size: 11 },
          gridcolor: "#e2e8f0",
        },
        bgcolor: "rgba(0,0,0,0)",
      },
      margin: { t: 20, r: 20, b: 20, l: 20 },
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.18,
        yanchor: "top",
        font: { size: 9.5 },
        itemgap: 6,
        bgcolor: "rgba(255,255,255,0.8)",
      },
      showlegend: true,
    };

    Plotly.newPlot("chart-radar", traces, layout, PLY_CFG);
  }

  /* ── Feature importance ──────────────────────────────────────────────── */
  function showImportance(modelName) {
    // Update tab styles
    document.querySelectorAll(".models-imp-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.model === modelName);
    });

    const m = _models.find((x) => x.name === modelName);
    if (!m || !m.importance || !m.importance.length) return;

    const sorted = [...m.importance].sort((a, b) => a.score - b.score);
    const labels = sorted.map((x) => x.feature.replace(/_/g, " "));
    const values = sorted.map((x) => x.score);

    const colorIdx = _models.indexOf(m);
    const color = COLORS[colorIdx % COLORS.length];

    const traces = [
      {
        type: "bar",
        orientation: "h",
        x: values,
        y: labels,
        marker: {
          color: values.map(
            (v) =>
              color +
              Math.round(40 + v * 200)
                .toString(16)
                .padStart(2, "0"),
          ),
        },
        hovertemplate: "<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>",
      },
    ];

    const layout = {
      ...PLY_BASE,
      margin: { t: 8, r: 24, b: 28, l: 160 },
      xaxis: {
        range: [0, Math.max(...values) * 1.12],
        gridcolor: "#edf2f7",
        zeroline: false,
        tickfont: { family: "'Space Mono', monospace", size: 9.5 },
      },
      yaxis: { tickfont: { size: 10.5 }, automargin: true },
    };

    Plotly.react("chart-importance", traces, layout, PLY_CFG);
  }

  /* ── AUC history ─────────────────────────────────────────────────────── */
  function _renderHistory() {
    const el = document.getElementById("chart-history");
    if (!el) return;

    const names = Object.keys(_history);

    // Check if any model has more than one run
    const hasHistory = names.some((n) => _history[n].length > 1);

    if (!hasHistory) {
      el.innerHTML = `
        <div style="height:100%;display:flex;flex-direction:column;align-items:center;
                    justify-content:center;gap:.5rem;color:var(--tx-3);">
          <i class="fas fa-clock-rotate-left" style="font-size:1.75rem;opacity:.35;"></i>
          <span style="font-size:.875rem;">Run the pipeline again to see AUC trends</span>
        </div>`;
      return;
    }

    const traces = names.map((name, i) => {
      const runs = _history[name];
      return {
        type: "scatter",
        mode: "lines+markers",
        name: name,
        x: runs.map((r, idx) => `Run ${idx + 1}`),
        y: runs.map((r) => r.auc),
        line: { color: COLORS[i % COLORS.length], width: 2 },
        marker: { color: COLORS[i % COLORS.length], size: 6 },
        hovertemplate:
          "<b>" + name + "</b><br>%{x}: AUC %{y:.4f}<extra></extra>",
      };
    });

    const layout = {
      ...PLY_BASE,
      margin: { t: 8, r: 16, b: 72, l: 52 },
      xaxis: {
        gridcolor: "#edf2f7",
        zeroline: false,
        tickangle: -35,
        tickfont: { size: 9.5 },
      },
      yaxis: {
        range: [0, 1],
        gridcolor: "#edf2f7",
        zeroline: false,
        title: { text: "AUC", standoff: 8 },
        tickfont: { family: "'Space Mono', monospace", size: 10 },
      },
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.28,
        yanchor: "top",
        font: { size: 9.5 },
        itemgap: 6,
        bgcolor: "rgba(255,255,255,0.8)",
      },
      hovermode: "x unified",
    };

    // Draw AUC=0.85 target line
    layout.shapes = [
      {
        type: "line",
        x0: 0,
        x1: 1,
        xref: "paper",
        y0: 0.85,
        y1: 0.85,
        line: { color: "#059669", width: 1.5, dash: "dot" },
      },
    ];
    layout.annotations = [
      {
        x: 1,
        xref: "paper",
        y: 0.85,
        text: "Target 0.85",
        showarrow: false,
        font: { size: 10, color: "#059669" },
        xanchor: "right",
        yanchor: "bottom",
      },
    ];

    Plotly.newPlot("chart-history", traces, layout, PLY_CFG);
  }

  function showTuning(modelName) {
    document.querySelectorAll("#tuning-tabs .models-imp-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.model === modelName);
    });
    document.querySelectorAll(".models-tuning-panel").forEach((panel) => {
      panel.classList.add("hidden");
    });
    const id = "tuning-panel-" + modelName.replace(/ /g, "-");
    document.getElementById(id)?.classList.remove("hidden");
  }

  /* ── Resize observer ─────────────────────────────────────────────────── */

  function _initResizeObserver() {
    // Plotly responsive:true only fires on window resize, not CSS reflow.
    // ResizeObserver catches grid collapse (2-col → 1-col at 900px breakpoint).
    if (typeof ResizeObserver === "undefined") return;
    ["chart-radar", "chart-importance", "chart-history"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      new ResizeObserver(() => {
        if (el.children.length) Plotly.Plots.resize(el);
      }).observe(el);
    });
  }

  /* ── Init ────────────────────────────────────────────────────────────── */
  function init(models, history) {
    _models = models;
    _history = history;

    _radar();
    _renderHistory();

    // Render importance for the best model by default
    const best = _models.find((m) => m.is_best) || _models[0];
    if (best) showImportance(best.name);

    _initResizeObserver();
  }

  return { init, showImportance, showTuning };
})();

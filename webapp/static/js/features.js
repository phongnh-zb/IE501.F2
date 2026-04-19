"use strict";

const TIER = {
  0: { label: "Safe", color: "#059669" },
  1: { label: "Watch", color: "#d97706" },
  2: { label: "High Risk", color: "#ea580c" },
  3: { label: "Critical", color: "#dc2626" },
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

const Features = (() => {
  let _distDrawn = false;

  function _hideLoading(id) {
    const el = document.getElementById(id + "-loading");
    if (el) el.classList.add("hidden");
  }

  /* ── URL state ────────────────────────────────────────────────────────── */
  function _pushState(field) {
    const p = new URLSearchParams();
    if (field) p.set("feature", field);
    history.pushState(
      { feature: field },
      "",
      "/features" + (p.toString() ? "?" + p.toString() : ""),
    );
  }

  function _restoreFromURL() {
    const p = new URLSearchParams(window.location.search);
    return p.get("feature") || DEFAULT_FIELD;
  }

  /* ── Resize observer ──────────────────────────────────────────────────── */
  function _initResizeObserver() {
    if (typeof ResizeObserver === "undefined") return;
    ["chart-dist", "chart-box", "chart-corr"].forEach((id) => {
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

  /* ── Feature distribution ─────────────────────────────────────────────── */
  async function loadDistribution(field) {
    try {
      const res = await fetch(
        `/api/features/distribution?feature=${encodeURIComponent(field)}`,
      );
      if (!res.ok) {
        _hideLoading("chart-dist");
        return;
      }
      const d = await res.json();

      const traces = [3, 2, 1, 0].map((tier) => ({
        type: "bar",
        name: TIER[tier].label,
        x: d.buckets,
        y: d[{ 3: "crit", 2: "high", 1: "watch", 0: "safe" }[tier]],
        marker: { color: TIER[tier].color },
        hovertemplate:
          "<b>%{x}</b><br>" + TIER[tier].label + ": %{y}<extra></extra>",
      }));

      const layout = {
        ...PLY_BASE,
        barmode: "stack",
        margin: { t: 8, r: 16, b: 56, l: 52 },
        xaxis: {
          gridcolor: "#edf2f7",
          zeroline: false,
          tickangle: -45,
          nticks: 20,
          automargin: true,
          tickfont: { family: "'Space Mono', monospace", size: 9 },
          title: { text: "", standoff: 10, font: { size: 11 } },
        },
        yaxis: {
          gridcolor: "#edf2f7",
          zeroline: false,
          tickfont: { family: "'Space Mono', monospace", size: 9.5 },
          title: { text: "", standoff: 8, font: { size: 11 } },
        },
        legend: { orientation: "h", y: -0.32, font: { size: 10 }, itemgap: 10 },
        showlegend: true,
      };

      const fn = _distDrawn ? Plotly.react : Plotly.newPlot;
      fn("chart-dist", traces, layout, PLY_CFG);
      _hideLoading("chart-dist");
      _distDrawn = true;
    } catch (err) {
      _hideLoading("chart-dist");
      console.error("[Features] distribution:", err);
    }
  }

  /* ── Box plot ─────────────────────────────────────────────────────────── */
  async function _loadBoxplot() {
    try {
      const res = await fetch("/api/features/boxplot");
      if (!res.ok) {
        _hideLoading("chart-box");
        return;
      }
      const d = await res.json();
      const features = d.features;
      if (!features.length) {
        _hideLoading("chart-box");
        return;
      }

      const traces = [0, 1, 2, 3].map((tier) => ({
        type: "box",
        name: TIER[tier].label,
        x: features.map((f) => f.label),
        q1: features.map((f) => f.tiers[tier]?.q1 ?? null),
        median: features.map((f) => f.tiers[tier]?.median ?? null),
        q3: features.map((f) => f.tiers[tier]?.q3 ?? null),
        lowerfence: features.map((f) => f.tiers[tier]?.min ?? null),
        upperfence: features.map((f) => f.tiers[tier]?.max ?? null),
        fillcolor: TIER[tier].color + "55",
        marker: { color: TIER[tier].color },
        line: { color: TIER[tier].color },
        boxpoints: false,
        hovertemplate:
          "<b>%{x}</b><br>" +
          TIER[tier].label +
          "<br>Median: %{median:.4f}<extra></extra>",
      }));

      const layout = {
        ...PLY_BASE,
        boxmode: "group",
        margin: { t: 8, r: 16, b: 60, l: 52 },
        xaxis: {
          gridcolor: "#edf2f7",
          tickfont: { size: 10.5 },
          tickangle: -25,
          automargin: true,
        },
        yaxis: {
          gridcolor: "#edf2f7",
          zeroline: false,
          tickfont: { family: "'Space Mono', monospace", size: 9.5 },
        },
        legend: { orientation: "h", y: -0.22, font: { size: 10 }, itemgap: 8 },
        showlegend: true,
      };

      Plotly.newPlot("chart-box", traces, layout, PLY_CFG);
      _hideLoading("chart-box");
    } catch (err) {
      _hideLoading("chart-box");
      console.error("[Features] boxplot:", err);
    }
  }

  /* ── Correlation heatmap ──────────────────────────────────────────────── */
  async function _loadCorrelation() {
    try {
      const res = await fetch("/api/features/correlation");
      if (!res.ok) {
        _hideLoading("chart-corr");
        return;
      }
      const d = await res.json();

      const annotations = d.matrix.flatMap((row, i) =>
        row
          .map((val, j) => {
            if (val === null) return null;
            return {
              x: d.features[j],
              y: d.features[i],
              text: val.toFixed(2),
              font: {
                size: 8,
                color: Math.abs(val) > 0.5 ? "#fff" : "#334155",
              },
              showarrow: false,
            };
          })
          .filter(Boolean),
      );

      const traces = [
        {
          type: "heatmap",
          x: d.features,
          y: d.features,
          z: d.matrix,
          colorscale: "RdBu",
          reversescale: true,
          zmin: -1,
          zmax: 1,
          hovertemplate:
            "<b>%{y}</b> × <b>%{x}</b><br>r = %{z:.3f}<extra></extra>",
          colorbar: {
            len: 0.8,
            thickness: 14,
            tickfont: { size: 9.5 },
            title: { text: "r", side: "right", font: { size: 10 } },
          },
        },
      ];

      const layout = {
        ...PLY_BASE,
        annotations,
        margin: { t: 8, r: 80, b: 80, l: 80 },
        xaxis: { tickfont: { size: 9.5 }, tickangle: -40, automargin: true },
        yaxis: { tickfont: { size: 9.5 }, automargin: true },
      };

      const corrEl = document.getElementById("chart-corr");
      const fn =
        corrEl && corrEl.children.length ? Plotly.react : Plotly.newPlot;
      fn("chart-corr", traces, layout, PLY_CFG);
      _hideLoading("chart-corr");
    } catch (err) {
      _hideLoading("chart-corr");
      console.error("[Features] correlation:", err);
    }
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */
  function init() {
    const sel = document.getElementById("feat-select");
    const initialField = _restoreFromURL();

    if (sel) {
      sel.value = initialField;

      sel.addEventListener("change", () => {
        _distDrawn = false;
        _pushState(sel.value);
        loadDistribution(sel.value);
      });

      sel.addEventListener("mousedown", () => sel.classList.add("open"));
      sel.addEventListener("change", () => sel.classList.remove("open"));
      sel.addEventListener("blur", () => sel.classList.remove("open"));
    }

    window.addEventListener("popstate", (e) => {
      const field =
        e.state && e.state.feature ? e.state.feature : _restoreFromURL();
      if (sel) sel.value = field;
      _distDrawn = false;
      loadDistribution(field);
    });

    _initResizeObserver();

    loadDistribution(initialField);
    _loadBoxplot();
    _loadCorrelation();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", Features.init);

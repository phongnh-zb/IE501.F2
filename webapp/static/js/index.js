let pieChart = null;
let scatterChart = null;

const TIER_COLORS = {
  0: { bg: "#28a745", label: "Safe" },
  1: { bg: "#ffc107", label: "Watch" },
  2: { bg: "#fd7e14", label: "High Risk" },
  3: { bg: "#dc3545", label: "Critical" },
};

async function fetchData() {
  try {
    const response = await fetch("/api/realtime-data");
    if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
    const result = await response.json();
    updateDashboard(result);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function updateDashboard(data) {
  const s = data.summary;

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
  };
  set("total-count", s.total);
  set("safe-count", s.safe);
  set("watch-count", s.watch);
  set("high-risk-count", s.high_risk);
  set("critical-count", s.critical);

  // ── Pie chart ─────────────────────────────────────────────────────────
  const ctxPie = document.getElementById("riskPieChart").getContext("2d");
  if (pieChart) pieChart.destroy();

  pieChart = new Chart(ctxPie, {
    type: "doughnut",
    data: {
      labels: ["Safe", "Watch", "High Risk", "Critical"],
      datasets: [
        {
          data: [s.safe, s.watch, s.high_risk, s.critical],
          backgroundColor: ["#28a745", "#ffc107", "#fd7e14", "#dc3545"],
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: 10 },
      plugins: {
        legend: {
          position: "bottom",
          labels: { padding: 16, font: { size: 12 } },
        },
        datalabels: {
          color: "#ffffff",
          font: { weight: "bold", size: 13 },
          formatter: (value, ctx) => {
            const total = ctx.chart.data.datasets[0].data.reduce(
              (a, b) => a + b,
              0,
            );
            const pct = (value * 100) / total;
            return pct > 5 ? pct.toFixed(1) + "%" : null;
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return `${ctx.label}: ${ctx.raw} students (${pct}%)`;
            },
          },
        },
      },
    },
  });

  // ── Scatter chart ─────────────────────────────────────────────────────
  const grouped = { 0: [], 1: [], 2: [], 3: [] };
  data.raw_data.forEach((d) => {
    const tier = d.risk ?? 0;
    if (grouped[tier])
      grouped[tier].push({ x: d.score, y: d.clicks, id: d.id });
  });

  const ctxScatter = document.getElementById("scatterChart").getContext("2d");
  if (scatterChart) scatterChart.destroy();

  scatterChart = new Chart(ctxScatter, {
    type: "scatter",
    data: {
      datasets: [0, 1, 2, 3].map((tier) => ({
        label: TIER_COLORS[tier].label,
        data: grouped[tier],
        backgroundColor: TIER_COLORS[tier].bg,
        pointRadius: 4,
        hoverRadius: 8,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: 10 },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: (ctx) =>
              `${ctx.dataset.label} — ID: ${ctx.raw.id || "N/A"} (Score: ${ctx.raw.x}, Clicks: ${ctx.raw.y})`,
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Average Score (0–100)" },
          min: 0,
          max: 100,
          grid: { color: "#f0f0f0" },
        },
        y: {
          title: { display: true, text: "Total Interaction Clicks" },
          beginAtZero: true,
          grid: { color: "#f0f0f0" },
        },
      },
    },
  });
}

async function triggerManualRefresh() {
  const btn = document.getElementById("refreshBtn");
  if (btn) {
    btn.disabled = true;
    btn.classList.add("opacity-50", "cursor-not-allowed");
    btn.style.minWidth = btn.offsetWidth + "px";
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Updating...`;
  }
  try {
    const response = await fetch("/api/refresh-cache", { method: "POST" });
    const result = await response.json();
    if (response.ok) {
      await fetchData();
    } else {
      console.error("Refresh failed:", result.message);
      alert("Failed to refresh data. Check server logs.");
    }
  } catch (error) {
    console.error("Network error during refresh:", error);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("opacity-50", "cursor-not-allowed");
      btn.innerHTML = `<i class="fas fa-sync-alt" id="refreshIcon"></i> Refresh Data`;
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (typeof ChartDataLabels !== "undefined") {
    Chart.register(ChartDataLabels);
  }
  fetchData();
  setInterval(fetchData, 15000);
});

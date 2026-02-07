// Initialize global Chart variables to manage instances
let pieChart = null;
let scatterChart = null;

async function fetchData() {
  try {
    const response = await fetch("/api/realtime-data");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    updateDashboard(result);
  } catch (error) {
    console.error("Error fetching data from Server:", error);
  }
}

function updateDashboard(data) {
  // Update Statistical Text
  // Check elements existence before assignment to avoid null errors
  const elTotal = document.getElementById("total-count");
  const elRisk = document.getElementById("risk-count");
  const elSafe = document.getElementById("safe-count");

  if (elTotal) elTotal.innerText = data.summary.total;
  if (elRisk) elRisk.innerText = data.summary.risk;
  if (elSafe) elSafe.innerText = data.summary.safe;

  // Update Pie Chart
  const ctxPie = document.getElementById("riskPieChart").getContext("2d");

  // Destroy previous chart instance if it exists (to avoid overlapping)
  if (pieChart) {
    pieChart.destroy();
  }

  // --- PIE CHART CONFIGURATION ---
  pieChart = new Chart(ctxPie, {
    type: "doughnut",
    data: {
      labels: ["Safe", "High Risk"],
      datasets: [
        {
          data: [data.summary.safe, data.summary.risk],
          backgroundColor: ["#28a745", "#dc3545"],
          borderWidth: 1,
          hoverOffset: 4,
        },
      ],
    },
    options: {
      // --- FORCE FULL WIDTH & HEIGHT ---
      responsive: true,
      maintainAspectRatio: false, // Important: Allows filling the container
      layout: {
        padding: 10,
      },
      // --------------------------------
      plugins: {
        legend: {
          position: "bottom",
          labels: { padding: 20, font: { size: 12 } },
        },
        datalabels: {
          color: "#ffffff",
          font: { weight: "bold", size: 14 },
          formatter: (value, ctx) => {
            let sum = 0;
            let dataArr = ctx.chart.data.datasets[0].data;
            dataArr.map((data) => {
              sum += data;
            });
            let percentage = ((value * 100) / sum).toFixed(1) + "%";
            if ((value * 100) / sum > 5) {
              return percentage;
            } else {
              return null;
            }
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let value = context.raw;
              let total = context.dataset.data.reduce((a, b) => a + b, 0);
              let percentage = ((value / total) * 100).toFixed(1) + "%";
              return `${context.label}: ${value} students (${percentage})`;
            },
          },
        },
      },
    },
  });

  // Update Scatter Chart
  // Prepare data: x=Score, y=Clicks
  const scatterDataRisk = data.raw_data
    .filter((d) => d.risk === 1)
    .map((d) => ({ x: d.score, y: d.clicks, id: d.id }));

  const scatterDataSafe = data.raw_data
    .filter((d) => d.risk === 0)
    .map((d) => ({ x: d.score, y: d.clicks, id: d.id }));

  const ctxScatter = document.getElementById("scatterChart").getContext("2d");

  if (scatterChart) {
    scatterChart.destroy();
  }

  scatterChart = new Chart(ctxScatter, {
    type: "scatter",
    data: {
      datasets: [
        // DATASET 1: SAFE (Green) - Now First
        {
          label: "Safe",
          data: scatterDataSafe,
          backgroundColor: "#28a745", // Green
          pointRadius: 4,
          hoverRadius: 8,
        },
        // DATASET 2: HIGH RISK (Red) - Now Second
        {
          label: "High Risk",
          data: scatterDataRisk,
          backgroundColor: "#dc3545", // Red
          pointRadius: 4,
          hoverRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false, // Ensures full height/width
      layout: {
        padding: 10,
      },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `ID: ${context.raw.id || "N/A"} (Score: ${
                context.raw.x
              }, Clicks: ${context.raw.y})`;
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Average Score (0-100)" },
          min: 0,
          max: 100,
          grid: { display: true, color: "#f0f0f0" },
        },
        y: {
          title: { display: true, text: "Total Interaction Clicks" },
          beginAtZero: true,
          grid: { display: true, color: "#f0f0f0" },
        },
      },
    },
  });
}

// --- MANUAL REFRESH LOGIC ---
async function triggerManualRefresh() {
  const btn = document.getElementById("refreshBtn");
  const icon = document.getElementById("refreshIcon");

  // UI Loading State
  if (btn) {
    btn.disabled = true;
    btn.classList.add("opacity-50", "cursor-not-allowed");

    // Prevent layout jump by fixing width
    btn.style.minWidth = btn.offsetWidth + "px";

    // Change text to "Updating..." with spinner
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Updating...`;
  }

  try {
    console.log("Requesting manual cache update...");

    // Call API
    const response = await fetch("/api/refresh-cache", { method: "POST" });
    const result = await response.json();

    if (response.ok) {
      console.log("Cache updated:", result.message);
      // Re-fetch Dashboard Data immediately
      await fetchData();

      // Optional: You can add a small success indication here if you want
    } else {
      console.error("Refresh failed:", result.message);
      alert("Failed to refresh data. Check server logs.");
    }
  } catch (error) {
    console.error("Network error during refresh:", error);
  } finally {
    // Reset UI State
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("opacity-50", "cursor-not-allowed");
      // Revert text back to "Refresh Data"
      btn.innerHTML = `<i class="fas fa-sync-alt" id="refreshIcon"></i> Refresh Data`;
    }
  }
}

// --- MAIN EXECUTION ---
document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard initialized. Waiting for data...");

  // Register the plugin if available (Prevents ReferenceError)
  if (typeof ChartDataLabels !== "undefined") {
    Chart.register(ChartDataLabels);
  } else {
    console.warn(
      "ChartDataLabels plugin not found. Percentages will not be displayed on slices."
    );
  }

  // Initial fetch immediately after load
  fetchData();

  // Auto-refresh every 15 seconds (Real-time Simulation)
  setInterval(fetchData, 15000);
});

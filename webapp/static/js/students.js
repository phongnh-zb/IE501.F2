document.addEventListener("DOMContentLoaded", () => {
  console.log("Student Logic Loaded.");

  // --- DOM ELEMENTS ---
  const modal = document.getElementById("studentModal");
  const modalOverlay = document.getElementById("modalOverlay");
  const searchInput = document.querySelector('input[name="search"]');

  // --- HELPER: URL PARAMETER MANAGEMENT ---
  window.changeParams = function (key, value) {
    const url = new URL(window.location.href);
    url.searchParams.set(key, value);
    if (key === "page_size") {
      url.searchParams.set("page", 1);
    }
    window.location.href = url.toString();
  };

  // --- AUTO-SEARCH LOGIC ---
  if (searchInput) {
    // Restore Focus: If user was searching, put cursor back at the end of text
    if (searchInput.value) {
      searchInput.focus();
      const val = searchInput.value;
      searchInput.value = "";
      searchInput.value = val;
    }
  }

  // --- MODAL FUNCTIONS ---
  window.openStudentModal = async function (studentId) {
    try {
      const response = await fetch(`/api/student/${studentId}`);
      if (!response.ok) throw new Error("Student not found");
      const data = await response.json();
      const info = data.info;

      document.getElementById("modalId").innerText = info.id;
      document.getElementById(
        "modalAvatar"
      ).src = `https://ui-avatars.com/api/?name=${info.id}&background=random&color=fff`;
      document.getElementById("modalScore").innerText = info.score.toFixed(1);
      document.getElementById("modalClicks").innerText = parseInt(info.clicks);

      const header = document.getElementById("modalHeader");
      const badge = document.getElementById("modalStatusBadge");
      const progressBar = document.getElementById("modalProgressBar");

      // --- RISK STYLING (For Header & Badge) ---
      if (info.risk === 1) {
        header.className =
          "bg-red-600 h-24 relative transition-colors duration-300";
        badge.className =
          "px-3 py-1 rounded-full text-xs font-bold border bg-red-100 text-red-800 border-red-200";
        badge.innerHTML =
          '<i class="fas fa-exclamation-triangle"></i> HIGH RISK';
      } else {
        header.className =
          "bg-green-600 h-24 relative transition-colors duration-300";
        badge.className =
          "px-3 py-1 rounded-full text-xs font-bold border bg-green-100 text-green-800 border-green-200";
        badge.innerHTML = '<i class="fas fa-check-circle"></i> SAFE';
      }

      // --- SCORE STYLING (For Progress Bar - MATCHING TABLE LIST) ---
      // Logic: Red (<40), Yellow (<70), Green (>=70)
      let barColor = "bg-green-500"; // Default Green

      if (info.score < 40) {
        barColor = "bg-red-500";
      } else if (info.score < 70) {
        barColor = "bg-yellow-400";
      }

      // Apply Width and Color
      progressBar.className = `${barColor} h-1.5 rounded-full transition-all duration-500`;
      progressBar.style.width = `${info.score}%`;

      // --- RECOMMENDATIONS ---
      const recList = document.getElementById("modalRecs");
      recList.innerHTML = "";
      data.recommendations.forEach((rec) => {
        const li = document.createElement("li");
        li.innerText = rec;
        recList.appendChild(li);
      });

      modal.classList.remove("hidden");
    } catch (err) {
      console.error(err);
      alert("Error loading student data: " + err);
    }
  };

  window.closeModal = function () {
    modal.classList.add("hidden");
  };

  // Attached to window so it can be called from HTML
  window.triggerManualRefresh = async function () {
    const btn = document.getElementById("refreshBtn");
    const icon = document.getElementById("refreshIcon");

    // UI Loading State
    if (btn && icon) {
      btn.disabled = true;
      btn.classList.add("opacity-50", "cursor-not-allowed");
      icon.classList.add("fa-spin");
      // Maintain width to prevent layout jump
      btn.style.minWidth = btn.offsetWidth + "px";
      btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Updating...`;
    }

    try {
      console.log("Requesting manual cache update...");
      const response = await fetch("/api/refresh-cache", { method: "POST" });
      const result = await response.json();

      if (response.ok) {
        console.log("Cache updated:", result.message);
        window.location.reload();
      } else {
        console.error("Refresh failed:", result.message);
        alert("Failed to refresh data. Please try again.");

        // RESET BUTTON STATE ON ERROR
        if (btn) {
          btn.disabled = false;
          btn.classList.remove("opacity-50", "cursor-not-allowed");
          // UPDATED: Make sure this text matches the HTML
          btn.innerHTML = `<i class="fas fa-sync-alt"></i> Refresh Data`;
        }
      }
    } catch (error) {
      console.error("Network error during refresh:", error);
      alert("Network error. Could not reach server.");

      // RESET BUTTON STATE ON ERROR
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("opacity-50", "cursor-not-allowed");
        // UPDATED: Make sure this text matches the HTML
        btn.innerHTML = `<i class="fas fa-sync-alt"></i> Refresh Data`;
      }
    }
  };

  // --- EVENT LISTENERS ---
  if (modalOverlay) {
    modalOverlay.addEventListener("click", function (e) {
      if (e.target === this || e.target.classList.contains("min-h-full")) {
        closeModal();
      }
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeModal();
    }
  });
});

const TIER_CONFIG = {
  0: {
    header: "bg-green-600 h-24 relative transition-colors duration-300",
    badge:
      "px-3 py-1 rounded-full text-xs font-bold border bg-green-100 text-green-800 border-green-200",
    icon: '<i class="fas fa-check-circle"></i> SAFE',
  },
  1: {
    header: "bg-yellow-500 h-24 relative transition-colors duration-300",
    badge:
      "px-3 py-1 rounded-full text-xs font-bold border bg-yellow-100 text-yellow-800 border-yellow-300",
    icon: '<i class="fas fa-eye"></i> WATCH',
  },
  2: {
    header: "bg-orange-500 h-24 relative transition-colors duration-300",
    badge:
      "px-3 py-1 rounded-full text-xs font-bold border bg-orange-100 text-orange-800 border-orange-300",
    icon: '<i class="fas fa-exclamation-triangle"></i> HIGH RISK',
  },
  3: {
    header: "bg-red-700 h-24 relative transition-colors duration-300",
    badge:
      "px-3 py-1 rounded-full text-xs font-bold border bg-red-100 text-red-800 border-red-300",
    icon: '<i class="fas fa-user-slash"></i> CRITICAL',
  },
};

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("studentModal");
  const modalOverlay = document.getElementById("modalOverlay");
  const searchInput = document.querySelector('input[name="search"]');

  window.changeParams = function (key, value) {
    const url = new URL(window.location.href);
    url.searchParams.set(key, value);
    if (key === "page_size") url.searchParams.set("page", 1);
    window.location.href = url.toString();
  };

  if (searchInput && searchInput.value) {
    searchInput.focus();
    const val = searchInput.value;
    searchInput.value = "";
    searchInput.value = val;
  }

  window.openStudentModal = async function (studentId) {
    try {
      const response = await fetch(`/api/student/${studentId}`);
      if (!response.ok) throw new Error("Student not found");
      const data = await response.json();
      const info = data.info;

      const risk = info.risk ?? 0;
      const tier = TIER_CONFIG[risk] || TIER_CONFIG[0];

      document.getElementById("modalId").innerText = info.id;
      document.getElementById("modalScore").innerText = info.score.toFixed(1);
      document.getElementById("modalClicks").innerText = parseInt(info.clicks);
      document.getElementById("modalAvatar").src =
        `https://ui-avatars.com/api/?name=${info.id}&background=random&color=fff`;

      document.getElementById("modalHeader").className = tier.header;
      document.getElementById("modalStatusBadge").className = tier.badge;
      document.getElementById("modalStatusBadge").innerHTML = tier.icon;

      const bar = document.getElementById("modalProgressBar");
      let barColor =
        info.score < 40
          ? "bg-red-500"
          : info.score < 70
            ? "bg-yellow-400"
            : "bg-green-500";
      bar.className = `${barColor} h-1.5 rounded-full transition-all duration-500`;
      bar.style.width = `${info.score}%`;

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

  window.triggerManualRefresh = async function () {
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
        window.location.reload();
      } else {
        alert("Failed to refresh data. Please try again.");
        if (btn) {
          btn.disabled = false;
          btn.classList.remove("opacity-50", "cursor-not-allowed");
          btn.innerHTML = `<i class="fas fa-sync-alt"></i> Refresh Data`;
        }
      }
    } catch (error) {
      alert("Network error. Could not reach server.");
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("opacity-50", "cursor-not-allowed");
        btn.innerHTML = `<i class="fas fa-sync-alt"></i> Refresh Data`;
      }
    }
  };

  if (modalOverlay) {
    modalOverlay.addEventListener("click", function (e) {
      if (e.target === this || e.target.classList.contains("min-h-full"))
        closeModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
});

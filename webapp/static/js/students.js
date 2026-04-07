"use strict";

const TIER_NAMES = { 3: "Critical", 2: "High Risk", 1: "Watch", 0: "Safe" };

const RiskFilter = (() => {
  function _panel() {
    return document.getElementById("risk-panel");
  }
  function _btn() {
    return document.getElementById("risk-multiselect");
  }
  function _label() {
    return document.getElementById("risk-label");
  }
  function _checks() {
    return document.querySelectorAll("#risk-panel input[type=checkbox]");
  }

  function toggle() {
    const panel = _panel();
    const open = panel.style.display === "none";
    panel.style.display = open ? "block" : "none";
    _btn().classList.toggle("open", open);
  }

  function update() {
    const selected = [..._checks()]
      .filter((c) => c.checked)
      .map((c) => c.value);

    // Update label
    const lbl = _label();
    if (selected.length === 0) {
      lbl.textContent = "All risk tiers";
    } else {
      lbl.textContent = selected.map((v) => TIER_NAMES[+v]).join(", ");
    }

    // Navigate with comma-separated values in ?risk=
    const p = new URLSearchParams(window.location.search);
    if (selected.length) p.set("risk", selected.join(","));
    else p.delete("risk");
    p.set("page", "1");
    window.location.href = "/students?" + p.toString();
  }

  function clear() {
    _checks().forEach((c) => (c.checked = false));
    update();
  }

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    const wrap = document.getElementById("risk-multiselect");
    if (wrap && !wrap.contains(e.target)) {
      const panel = _panel();
      if (panel) panel.style.display = "none";
      wrap.classList.remove("open");
    }
  });

  return { toggle, update, clear };
})();

const IMD_BANDS = {
  0: "0–10%",
  1: "10–20%",
  2: "20–30%",
  3: "30–40%",
  4: "40–50%",
  5: "50–60%",
  6: "60–70%",
  7: "70–80%",
  8: "80–90%",
  9: "90–100%",
};

const TIER = {
  0: { name: "Safe", cls: "badge-safe" },
  1: { name: "Watch", cls: "badge-watch" },
  2: { name: "High Risk", cls: "badge-high" },
  3: { name: "Critical", cls: "badge-crit" },
};

const Students = (() => {
  let _searchTimer = null;
  let _activeId = null;

  /* ── URL helpers ─────────────────────────────────────────────────────── */

  function _params() {
    return new URLSearchParams(window.location.search);
  }

  function _go(changes, resetPage = true) {
    const p = _params();
    Object.entries(changes).forEach(([k, v]) => {
      if (v === null || v === "") p.delete(k);
      else p.set(k, String(v));
    });
    if (resetPage) p.set("page", "1");
    window.location.href = "/students?" + p.toString();
  }

  /* ── Toolbar actions ─────────────────────────────────────────────────── */

  function filter(key, value) {
    _go({ [key]: value });
  }

  function sort(field) {
    const p = _params();
    const cur = p.get("sort_by");
    const order = p.get("order") || "desc";

    let nextOrder;
    if (cur === field) {
      // Same column — toggle direction
      nextOrder = order === "asc" ? "desc" : "asc";
    } else {
      // New column — start ascending so the user sees the change immediately
      nextOrder = "asc";
    }

    _go({ sort_by: field, order: nextOrder });
  }

  function clearSearch() {
    _go({ search: null });
  }

  function clearAll() {
    window.location.href = "/students";
  }

  function exportCSV(e) {
    e.preventDefault();
    const btn = document.getElementById("export-btn");
    if (btn) {
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting…';
      btn.style.pointerEvents = "none";
    }
    // Build export URL preserving all current filters except page/page_size
    const p = _params();
    p.delete("page");
    p.delete("page_size");
    const url = "/students/export?" + p.toString();
    // Trigger download via hidden link
    const a = document.createElement("a");
    a.href = url;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Restore button after short delay
    setTimeout(() => {
      if (btn) {
        btn.innerHTML = '<i class="fas fa-download"></i> Export CSV';
        btn.style.pointerEvents = "";
      }
    }, 2000);
  }

  function jumpPage(e, max) {
    if (e.key !== "Enter") return;
    const val = parseInt(e.target.value, 10);
    if (val >= 1 && val <= max) _go({ page: val }, false);
  }

  /* ── Detail panel ────────────────────────────────────────────────────── */

  function _setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value ?? "—";
  }

  function _setColor(id, color) {
    const el = document.getElementById(id);
    if (el) el.style.color = color || "";
  }

  function openPanel(studentId) {
    const panel = document.getElementById("st-panel");
    const backdrop = document.getElementById("st-backdrop");

    // Highlight active row
    document
      .querySelectorAll(".st-row")
      .forEach((r) => r.classList.remove("active"));
    const row = document.querySelector(`.st-row[data-id="${studentId}"]`);
    if (row) row.classList.add("active");

    // Reset to Overview tab
    switchTab(document.querySelector(".st-panel-tab"), "tab-overview");

    // Show panel with loading state
    _setText("panel-id", studentId);
    _setText("panel-module", "");
    document.getElementById("panel-badge").innerHTML = "";
    document.getElementById("panel-withdrew").style.display = "none";
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    backdrop.classList.add("show");
    _activeId = studentId;

    // Update PDF link
    const pdfBtn = document.getElementById("panel-pdf-btn");
    if (pdfBtn) pdfBtn.href = `/api/student/${studentId}/report`;

    fetch(`/api/student/${studentId}`)
      .then((r) => r.json())
      .then((data) => {
        if (_activeId !== studentId) return; // stale response
        _populateOverview(data.info);
        _populateRecommendations(data.recommendations);
      })
      .catch(() => {
        _setText("panel-id", "Error loading student");
      });
  }

  function _populateOverview(s) {
    if (!s) return;

    const tier = TIER[s.risk] || TIER[0];
    document.getElementById("panel-badge").innerHTML =
      `<span class="badge ${tier.cls}">${tier.name}</span>`;

    _setText("panel-id", s.id);
    _setText(
      "panel-module",
      [s.code_module, s.code_presentation].filter(Boolean).join(" · ") || "—",
    );

    const withdrewEl = document.getElementById("panel-withdrew");
    if (s.withdrew_early) {
      withdrewEl.style.display = "inline-flex";
    } else {
      withdrewEl.style.display = "none";
    }

    // Academic
    const sub = ((s.submission_rate ?? 0) * 100).toFixed(0) + "%";
    _setText("pf-score", (s.score ?? 0).toFixed(2));
    _setText("pf-w-score", (s.weighted_score ?? 0).toFixed(2));
    _setText("pf-sub-rate", sub);
    _setColor(
      "pf-sub-rate",
      s.submission_rate * 100 < 40
        ? "var(--crit)"
        : s.submission_rate * 100 < 70
          ? "var(--watch)"
          : "var(--safe)",
    );
    _setText("pf-days-early", (s.avg_days_early ?? 0).toFixed(1));

    // Engagement
    const cpd =
      s.active_days > 0 ? (s.clicks / s.active_days).toFixed(1) : "0.0";
    _setText("pf-clicks", (s.clicks ?? 0).toLocaleString());
    _setText("pf-active-days", s.active_days ?? 0);
    _setText("pf-cpd", cpd);
    _setText("pf-forum", (s.forum_clicks ?? 0).toLocaleString());
    _setText("pf-quiz", (s.quiz_clicks ?? 0).toLocaleString());
    _setText("pf-resource", (s.resource_clicks ?? 0).toLocaleString());

    // Background
    const imd =
      s.imd_band_encoded >= 0
        ? IMD_BANDS[s.imd_band_encoded] || "Unknown"
        : "—";
    const disability =
      s.disability_encoded === 1
        ? "Yes"
        : s.disability_encoded === 0
          ? "No"
          : "—";

    _setText("pf-attempts", s.num_prev_attempts ?? 0);
    _setText("pf-dbs", (s.days_before_start ?? 0).toFixed(0) + " days");
    _setText("pf-imd", imd);
    _setText("pf-disability", disability);
  }

  function _populateRecommendations(recs) {
    const el = document.getElementById("panel-recs");
    if (!el) return;

    if (!recs || !recs.length) {
      el.innerHTML =
        '<div class="st-recs-loading text-3">No recommendations available.</div>';
      return;
    }

    const LEVEL_ICON = {
      crit: "fa-triangle-exclamation",
      high: "fa-arrow-up-right-dots",
      watch: "fa-eye",
      safe: "fa-circle-check",
    };

    el.innerHTML = recs
      .map((rec) => {
        const level = rec.level || "watch";
        const icon = LEVEL_ICON[level] || LEVEL_ICON.watch;
        return `<div class="st-rec-item st-rec-${level}">
        <i class="fas ${icon}"></i>
        <span>${rec.text || rec}</span>
      </div>`;
      })
      .join("");
  }

  function closePanel() {
    const panel = document.getElementById("st-panel");
    const backdrop = document.getElementById("st-backdrop");
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("show");
    document
      .querySelectorAll(".st-row")
      .forEach((r) => r.classList.remove("active"));
    _activeId = null;
  }

  function switchTab(btn, tabId) {
    document
      .querySelectorAll(".st-panel-tab")
      .forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document
      .querySelectorAll("#tab-overview, #tab-recommendations")
      .forEach((t) => (t.style.display = "none"));
    const tab = document.getElementById(tabId);
    if (tab) tab.style.display = "block";
  }

  /* ── Real-time search ────────────────────────────────────────────────── */

  function _initSearch() {
    const input = document.getElementById("search-input");
    if (!input) return;
    input.addEventListener("input", () => {
      clearTimeout(_searchTimer);
      _searchTimer = setTimeout(() => {
        _go({ search: input.value.trim() });
      }, 350);
    });
  }

  /* ── Keyboard shortcuts ──────────────────────────────────────────────── */

  function _initKeyboard() {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePanel();
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
        e.preventDefault();
        document.getElementById("search-input")?.focus();
      }
    });
  }

  function init() {
    _initSearch();
    _initKeyboard();
  }

  return {
    init,
    filter,
    sort,
    clearSearch,
    clearAll,
    export: exportCSV,
    jumpPage,
    openPanel,
    closePanel,
    switchTab,
  };
})();

document.addEventListener("DOMContentLoaded", Students.init);

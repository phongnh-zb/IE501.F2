"use strict";

/* ── Constants ───────────────────────────────────────────────────────────── */

const TIER_NAMES = { 3: "Critical", 2: "High Risk", 1: "Watch", 0: "Safe" };
const TIER_CLS = { 3: "crit", 2: "high", 1: "watch", 0: "safe" };

const RESULT_CLS = {
  Pass: "result-pass",
  Distinction: "result-distinction",
  Fail: "result-fail",
  Withdrawn: "result-withdrawn",
};
const RESULT_ICON = {
  Pass: "fa-circle-check",
  Distinction: "fa-star",
  Fail: "fa-circle-xmark",
  Withdrawn: "fa-person-walking-arrow-right",
};
const GENDER = { M: "Male", F: "Female" };
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

const LEVEL_ICON = {
  crit: "fa-triangle-exclamation",
  high: "fa-arrow-up-right-dots",
  watch: "fa-eye",
  safe: "fa-circle-check",
};

/* ── State ───────────────────────────────────────────────────────────────── */

let _all = []; // full dataset
let _filtered = []; // after filters applied
let _state = {
  search: "",
  risk: [],
  module: "",
  presentation: "",
  withdrew: "",
  sortBy: "risk",
  order: "desc",
  page: 1,
  pageSize: 50,
};
let _activeId = null;
let _searchTimer = null;

/* ── RiskFilter module ───────────────────────────────────────────────────── */

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

  function _getSelected() {
    return [..._checks()].filter((c) => c.checked).map((c) => +c.value);
  }

  function _updateLabel(sel) {
    const lbl = _label();
    if (!lbl) return;
    lbl.textContent =
      sel.length === 0
        ? "All risk tiers"
        : sel.length === 1
          ? TIER_NAMES[sel[0]]
          : `${sel.length} tiers selected`;
  }

  function _close() {
    const p = _panel();
    if (p) p.style.display = "none";
    _btn().classList.remove("open");
  }

  function _applyAndClose() {
    _state.risk = _getSelected();
    _state.page = 1;
    _close();
    Students.applyFilters();
  }

  function toggle() {
    const panel = _panel();
    const open = panel.style.display === "none";
    if (open) {
      const btn = document.querySelector(".st-multiselect-btn");
      if (btn) {
        const r = btn.getBoundingClientRect();
        panel.style.top = r.bottom + 4 + "px";
        panel.style.left = r.left + "px";
      }
      panel.style.display = "block";
      _btn().classList.add("open");
    } else {
      _applyAndClose();
    }
  }

  function update() {
    _updateLabel(_getSelected());
  }

  function clear() {
    _checks().forEach((c) => (c.checked = false));
    _updateLabel([]);
    _state.risk = [];
    _state.page = 1;
    _close();
    Students.applyFilters();
  }

  function syncFromState() {
    _checks().forEach((c) => {
      c.checked = _state.risk.includes(+c.value);
    });
    _updateLabel(_state.risk);
  }

  document.addEventListener("click", (e) => {
    const wrap = document.getElementById("risk-multiselect");
    if (wrap && !wrap.contains(e.target)) {
      const panel = _panel();
      if (panel && panel.style.display !== "none") _applyAndClose();
    }
  });

  return { toggle, update, clear, syncFromState };
})();

/* ── Rendering ───────────────────────────────────────────────────────────── */

function _fmt(n) {
  return Number(n).toLocaleString();
}

function _miniBar(label, cls, width) {
  const w = width !== undefined ? width : +label;
  return `<div class="st-cell-bar-wrap">
    <span class="st-cell-val mono">${label}</span>
    <div class="st-mini-bar-wrap">
      <div class="st-mini-bar st-mini-bar-${cls}" style="width:${Math.min(100, Math.max(0, w))}%"></div>
    </div>
  </div>`;
}

function _renderRow(s) {
  const tc = TIER_CLS[s.risk] || "safe";
  const sc =
    s.score < 40
      ? "crit"
      : s.score < 60
        ? "watch"
        : s.score < 75
          ? "high"
          : "safe";
  const sub = Math.round((s.submission_rate || 0) * 100);
  const subc = sub < 40 ? "crit" : sub < 70 ? "watch" : "safe";
  const status = s.withdrew_early
    ? `<span class="st-status-badge st-status-withdrew"><i class="fas fa-person-walking-arrow-right"></i> Withdrew</span>`
    : `<span class="st-status-badge st-status-active"><i class="fas fa-circle-check"></i> Active</span>`;

  return `<tr class="st-row" onclick="Students.openPanel('${s.id}')" data-id="${s.id}">
    <td class="text-left"><span class="st-id">${s.id}</span></td>
    <td class="text-center">
      ${s.code_module ? `<span class="st-module-tag">${s.code_module}</span>` : ""}
      ${s.code_presentation ? `<span class="st-pres-tag">${s.code_presentation}</span>` : ""}
    </td>
    <td class="text-center"><span class="badge badge-${tc}"><i class="fas fa-circle" style="font-size:.45rem;"></i> ${TIER_NAMES[s.risk]}</span></td>
    <td class="text-center">${_miniBar(s.score.toFixed(1), sc)}</td>
    <td class="text-center">${_miniBar(sub + "%", subc, sub)}</td>
    <td class="text-center mono text-2">${s.active_days}</td>
    <td class="text-center mono text-2">${_fmt(Math.round(s.clicks))}</td>
    <td class="text-center">${status}</td>
  </tr>`;
}

function _renderTable(rows) {
  const tbody = document.getElementById("st-tbody");
  const loading = document.getElementById("st-loading");
  const emptyEl = document.getElementById("st-empty");
  const wrap = document.querySelector(".st-table-wrap");
  const pagination = document.getElementById("st-pagination");

  if (loading) loading.classList.add("hidden");

  if (!rows.length) {
    if (wrap) wrap.classList.add("hidden");
    if (pagination) pagination.classList.add("hidden");
    if (emptyEl) {
      emptyEl.classList.remove("hidden");
      emptyEl.innerHTML = `<i class="fas fa-users-slash"></i>
        <p>No students match the current filters.</p>
        <button class="btn btn-outline btn-sm mt-2" onclick="Students.clearAll()">Clear filters</button>`;
    }
    return;
  }

  if (emptyEl) emptyEl.classList.add("hidden");
  if (wrap) wrap.classList.remove("hidden");
  if (pagination) pagination.classList.remove("hidden");
  if (!tbody) return;
  tbody.innerHTML = rows.map(_renderRow).join("");
}

function _renderSummary(total, tiers) {
  const el = document.getElementById("st-summary");
  if (!el) return;
  const chips = [
    tiers.critical > 0
      ? `<span class="st-tier-chip chip-crit">${_fmt(tiers.critical)} Critical</span>`
      : "",
    tiers.high > 0
      ? `<span class="st-tier-chip chip-high">${_fmt(tiers.high)} High</span>`
      : "",
    tiers.watch > 0
      ? `<span class="st-tier-chip chip-watch">${_fmt(tiers.watch)} Watch</span>`
      : "",
    tiers.safe > 0
      ? `<span class="st-tier-chip chip-safe">${_fmt(tiers.safe)} Safe</span>`
      : "",
  ]
    .filter(Boolean)
    .join("");

  el.innerHTML = `<span>Showing <strong>${_fmt(total)}</strong> student${total !== 1 ? "s" : ""}</span>
    ${chips ? `<span class="st-summary-dot">·</span>${chips}` : ""}
    ${_state.search ? `<span class="st-summary-dot">·</span><span class="text-3 text-xs">Search: <strong class="text-2">${_state.search}</strong></span>` : ""}`;
}

function _renderPagination(total, pageSize, page) {
  const el = document.getElementById("st-pagination");
  if (!el) return;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) {
    el.innerHTML = "";
    return;
  }

  function _pgBtn(icon, p, disabled) {
    return `<button class="st-pg-btn${disabled ? " st-pg-disabled" : ""}"
      onclick="Students.goPage(${p})" ${disabled ? "disabled" : ""}>${icon}</button>`;
  }

  // Build page range
  const range = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) range.push(i);
  } else {
    range.push(1);
    if (page > 3) range.push(null);
    for (
      let i = Math.max(2, page - 1);
      i <= Math.min(totalPages - 1, page + 1);
      i++
    )
      range.push(i);
    if (page < totalPages - 2) range.push(null);
    range.push(totalPages);
  }

  const pages = range
    .map((p) =>
      p === null
        ? `<span class="st-pg-ellipsis">…</span>`
        : `<button class="st-pg-btn${p === page ? " st-pg-active" : ""}" onclick="Students.goPage(${p})">${p}</button>`,
    )
    .join("");

  el.innerHTML = `
    ${_pgBtn('<i class="fas fa-angles-left"></i>', 1, page === 1)}
    ${_pgBtn('<i class="fas fa-angle-left"></i>', page - 1, page === 1)}
    ${pages}
    ${_pgBtn('<i class="fas fa-angle-right"></i>', page + 1, page === totalPages)}
    ${_pgBtn('<i class="fas fa-angles-right"></i>', totalPages, page === totalPages)}
    <span class="st-pg-info">Page ${page} of ${totalPages}</span>
    <div class="st-pg-jump">
      <input type="number" min="1" max="${totalPages}" placeholder="${page}"
        onkeydown="if(event.key==='Enter'){const v=+this.value;if(v>=1&&v<=${totalPages})Students.goPage(v);}" />
      <span class="text-xs text-3">/ ${totalPages}</span>
    </div>`;
}

function _updateSortHeaders() {
  document.querySelectorAll("#st-table thead th[data-field]").forEach((th) => {
    const field = th.dataset.field;
    const icon = th.querySelector("i");
    if (!icon) return;
    if (field === _state.sortBy) {
      th.classList.add("st-th-active");
      icon.className = `fas fa-sort-${_state.order === "desc" ? "down" : "up"}`;
    } else {
      th.classList.remove("st-th-active");
      icon.className = "fas fa-sort st-sort-idle";
    }
  });
}

function _updateClearBtn() {
  const btn = document.getElementById("clear-btn");
  if (!btn) return;
  const active =
    _state.search ||
    _state.risk.length ||
    _state.module ||
    _state.presentation ||
    _state.withdrew;
  btn.style.display = active ? "inline-flex" : "none";
}

/* ── Filter + sort + paginate ────────────────────────────────────────────── */

function _applyFiltersAndSort() {
  let data = _all;

  if (_state.risk.length)
    data = data.filter((s) => _state.risk.includes(s.risk));
  if (_state.module) data = data.filter((s) => s.code_module === _state.module);
  if (_state.presentation)
    data = data.filter((s) => s.code_presentation === _state.presentation);
  if (_state.withdrew !== "") {
    const w = +_state.withdrew;
    data = data.filter((s) => s.withdrew_early === w);
  }
  if (_state.search) {
    const q = _state.search.toLowerCase();
    data = data.filter((s) => s.id.toLowerCase().includes(q));
  }

  // Sort
  const rev = _state.order === "desc";
  data = [...data].sort((a, b) => {
    let av = a[_state.sortBy] ?? 0;
    let bv = b[_state.sortBy] ?? 0;
    if (typeof av === "string")
      return rev ? bv.localeCompare(av) : av.localeCompare(bv);
    // Secondary sort: within same risk tier, sort by score ascending
    if (_state.sortBy === "risk" && av === bv) return a.score - b.score;
    return rev ? bv - av : av - bv;
  });

  _filtered = data;
}

/* ── Public API ──────────────────────────────────────────────────────────── */

const Students = (() => {
  function applyFilters() {
    _applyFiltersAndSort();
    _render();
    _pushState();
    _updateClearBtn();
  }

  function _render() {
    const { page, pageSize } = _state;
    const total = _filtered.length;
    const start = (page - 1) * pageSize;
    const rows = _filtered.slice(start, start + pageSize);

    const tiers = {
      critical: _filtered.filter((s) => s.risk === 3).length,
      high: _filtered.filter((s) => s.risk === 2).length,
      watch: _filtered.filter((s) => s.risk === 1).length,
      safe: _filtered.filter((s) => s.risk === 0).length,
    };

    _renderTable(rows);
    _renderSummary(total, tiers);
    _renderPagination(total, pageSize, page);
    _updateSortHeaders();
  }

  function sort(field) {
    if (_state.sortBy === field) {
      _state.order = _state.order === "desc" ? "asc" : "desc";
    } else {
      _state.sortBy = field;
      _state.order = "asc";
    }
    _state.page = 1;
    applyFilters();
  }

  function goPage(p) {
    _state.page = p;
    applyFilters();
    document
      .querySelector(".st-table-card")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function clearSearch() {
    _state.search = "";
    _state.page = 1;
    const input = document.getElementById("search-input");
    if (input) input.value = "";
    const clear = document.getElementById("search-clear");
    if (clear) clear.style.display = "none";
    applyFilters();
  }

  function clearAll() {
    _state.search = "";
    _state.risk = [];
    _state.module = "";
    _state.presentation = "";
    _state.withdrew = "";
    _state.page = 1;
    const input = document.getElementById("search-input");
    if (input) input.value = "";
    document.getElementById("search-clear")?.style &&
      (document.getElementById("search-clear").style.display = "none");
    document.getElementById("filter-module")?.value &&
      (document.getElementById("filter-module").value = "");
    document.getElementById("filter-presentation")?.value &&
      (document.getElementById("filter-presentation").value = "");
    document.getElementById("filter-withdrew")?.value &&
      (document.getElementById("filter-withdrew").value = "");
    RiskFilter.syncFromState();
    applyFilters();
  }

  function exportCSV(e) {
    e.preventDefault();
    const btn = document.getElementById("export-btn");
    if (btn) {
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      btn.style.pointerEvents = "none";
    }
    // Build export URL from current filter state
    const p = new URLSearchParams();
    if (_state.search) p.set("search", _state.search);
    if (_state.risk.length) p.set("risk", _state.risk.join(","));
    if (_state.module) p.set("module", _state.module);
    if (_state.presentation) p.set("presentation", _state.presentation);
    if (_state.withdrew !== "") p.set("withdrew", _state.withdrew);
    p.set("sort_by", _state.sortBy);
    p.set("order", _state.order);
    const a = document.createElement("a");
    a.href = "/students/export?" + p.toString();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => {
      if (btn) {
        btn.innerHTML = '<i class="fas fa-download"></i> Export CSV';
        btn.style.pointerEvents = "";
      }
    }, 2000);
  }

  /* ── Panel ────────────────────────────────────────────────────────────── */

  function _setText(id, v) {
    const el = document.getElementById(id);
    if (el) el.textContent = v ?? "—";
  }
  function _setColor(id, c) {
    const el = document.getElementById(id);
    if (el) el.style.color = c || "";
  }

  function openPanel(sid) {
    const panel = document.getElementById("st-panel");
    const backdrop = document.getElementById("st-backdrop");
    document
      .querySelectorAll(".st-row")
      .forEach((r) => r.classList.remove("active"));
    document
      .querySelector(`.st-row[data-id="${sid}"]`)
      ?.classList.add("active");
    switchTab(document.querySelector(".st-panel-tab"), "tab-overview");
    _setText("panel-id", sid);
    _setText("panel-module", "");
    document.getElementById("panel-badge").innerHTML = "";
    document.getElementById("panel-withdrew").style.display = "none";
    const fr = document.getElementById("panel-final-result");
    if (fr) fr.style.display = "none";
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    backdrop.classList.add("show");
    _activeId = sid;
    const pdfBtn = document.getElementById("panel-pdf-btn");
    if (pdfBtn) pdfBtn.href = `/api/student/${sid}/report`;
    fetch(`/api/student/${sid}`)
      .then((r) => r.json())
      .then((data) => {
        if (_activeId !== sid) return;
        _populateOverview(data.info);
        _populateRecommendations(data.recommendations);
      })
      .catch(() => _setText("panel-id", "Error loading student"));
  }

  function _populateOverview(s) {
    if (!s) return;
    const tier = {
      0: { name: "Safe", cls: "badge-safe" },
      1: { name: "Watch", cls: "badge-watch" },
      2: { name: "High Risk", cls: "badge-high" },
      3: { name: "Critical", cls: "badge-crit" },
    }[s.risk] || { name: "Unknown", cls: "badge-safe" };
    document.getElementById("panel-badge").innerHTML =
      `<span class="badge ${tier.cls}">${tier.name}</span>`;
    _setText("panel-id", s.id);
    _setText(
      "panel-module",
      [s.code_module, s.code_presentation].filter(Boolean).join(" · ") || "—",
    );
    document.getElementById("panel-withdrew").style.display = s.withdrew_early
      ? "inline-flex"
      : "none";

    const fr = document.getElementById("panel-final-result");
    if (fr && s.final_result) {
      fr.className = `st-panel-final-result ${RESULT_CLS[s.final_result] || "result-fail"}`;
      fr.innerHTML = `<i class="fas ${RESULT_ICON[s.final_result] || "fa-circle"}"></i> ${s.final_result}`;
      fr.style.display = "inline-flex";
    }

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
    const cpd =
      s.active_days > 0 ? (s.clicks / s.active_days).toFixed(1) : "0.0";
    _setText("pf-clicks", (s.clicks ?? 0).toLocaleString());
    _setText("pf-active-days", s.active_days ?? 0);
    _setText("pf-cpd", cpd);
    _setText("pf-forum", (s.forum_clicks ?? 0).toLocaleString());
    _setText("pf-quiz", (s.quiz_clicks ?? 0).toLocaleString());
    _setText("pf-resource", (s.resource_clicks ?? 0).toLocaleString());
    _setText("pf-gender", GENDER[s.gender] || s.gender || "—");
    _setText("pf-age-band", s.age_band || "—");
    _setText("pf-region", s.region || "—");
    _setText("pf-edu", s.highest_education || "—");
    const imd =
      s.imd_band ||
      (s.imd_band_encoded >= 0
        ? IMD_BANDS[s.imd_band_encoded] || "Unknown"
        : "—");
    _setText("pf-imd", imd);
    _setText(
      "pf-disability",
      s.disability === "Y"
        ? "Yes"
        : s.disability === "N"
          ? "No"
          : s.disability_encoded === 1
            ? "Yes"
            : s.disability_encoded === 0
              ? "No"
              : "—",
    );
    _setText("pf-credits", s.studied_credits ?? "—");
    _setText("pf-attempts", s.num_prev_attempts ?? 0);
    _setText("pf-dbs", (s.days_before_start ?? 0).toFixed(0) + " days");
  }

  function _populateRecommendations(recs) {
    const el = document.getElementById("panel-recs");
    if (!el) return;
    if (!recs?.length) {
      el.innerHTML =
        '<div class="st-recs-loading text-3">No recommendations available.</div>';
      return;
    }
    el.innerHTML = recs
      .map((rec) => {
        const level = rec.level || "watch";
        const icon = LEVEL_ICON[level] || LEVEL_ICON.watch;
        return `<div class="st-rec-item st-rec-${level}"><i class="fas ${icon}"></i><span>${rec.text || rec}</span></div>`;
      })
      .join("");
  }

  function closePanel() {
    document.getElementById("st-panel")?.classList.remove("open");
    document.getElementById("st-panel")?.setAttribute("aria-hidden", "true");
    document.getElementById("st-backdrop")?.classList.remove("show");
    document
      .querySelectorAll(".st-row")
      .forEach((r) => r.classList.remove("active"));
    _activeId = null;
  }

  function switchTab(btn, tabId) {
    document
      .querySelectorAll(".st-panel-tab")
      .forEach((t) => t.classList.remove("active"));
    btn?.classList.add("active");
    document
      .querySelectorAll("#tab-overview,#tab-recommendations")
      .forEach((t) => (t.style.display = "none"));
    document.getElementById(tabId)?.style &&
      (document.getElementById(tabId).style.display = "block");
  }

  /* ── URL state ────────────────────────────────────────────────────────── */

  function _pushState() {
    const p = new URLSearchParams();
    if (_state.search) p.set("search", _state.search);
    if (_state.risk.length) p.set("risk", _state.risk.join(","));
    if (_state.module) p.set("module", _state.module);
    if (_state.presentation) p.set("presentation", _state.presentation);
    if (_state.withdrew !== "") p.set("withdrew", _state.withdrew);
    if (_state.sortBy !== "risk") p.set("sort_by", _state.sortBy);
    if (_state.order !== "desc") p.set("order", _state.order);
    if (_state.page !== 1) p.set("page", _state.page);
    if (_state.pageSize !== 50) p.set("page_size", _state.pageSize);
    const url = "/students" + (p.toString() ? "?" + p.toString() : "");
    history.pushState(_state, "", url);
  }

  function _restoreFromURL() {
    const p = new URLSearchParams(window.location.search);
    _state.search = p.get("search") || "";
    _state.risk = (p.get("risk") || "").split(",").filter(Boolean).map(Number);
    _state.module = p.get("module") || "";
    _state.presentation = p.get("presentation") || "";
    _state.withdrew = p.get("withdrew") ?? "";
    _state.page = +p.get("page") || 1;
    _state.pageSize = +p.get("page_size") || 50;
    // Only override sort defaults when the param is explicitly in the URL
    if (p.has("sort_by")) _state.sortBy = p.get("sort_by");
    if (p.has("order")) _state.order = p.get("order");
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */

  function _populateDropdowns() {
    const modSel = document.getElementById("filter-module");
    const presSel = document.getElementById("filter-presentation");
    if (modSel && typeof ST_MODULES !== "undefined") {
      ST_MODULES.forEach((m) => {
        const o = document.createElement("option");
        o.value = m;
        o.textContent = m;
        if (m === _state.module) o.selected = true;
        modSel.appendChild(o);
      });
      modSel.addEventListener("change", () => {
        _state.module = modSel.value;
        _state.page = 1;
        applyFilters();
      });
    }
    if (presSel && typeof ST_PRESENTATIONS !== "undefined") {
      ST_PRESENTATIONS.forEach((p) => {
        const o = document.createElement("option");
        o.value = p;
        o.textContent = p;
        if (p === _state.presentation) o.selected = true;
        presSel.appendChild(o);
      });
      presSel.addEventListener("change", () => {
        _state.presentation = presSel.value;
        _state.page = 1;
        applyFilters();
      });
    }
    const withdrewSel = document.getElementById("filter-withdrew");
    if (withdrewSel) {
      withdrewSel.value = _state.withdrew;
      withdrewSel.addEventListener("change", () => {
        _state.withdrew = withdrewSel.value;
        _state.page = 1;
        applyFilters();
      });
    }
    const pageSizeSel = document.getElementById("filter-page-size");
    if (pageSizeSel) {
      pageSizeSel.value = String(_state.pageSize);
      pageSizeSel.addEventListener("change", () => {
        _state.pageSize = +pageSizeSel.value;
        _state.page = 1;
        applyFilters();
      });
    }
  }

  function _initSearch() {
    const input = document.getElementById("search-input");
    const clear = document.getElementById("search-clear");
    if (!input) return;
    input.value = _state.search;
    if (_state.search && clear) clear.style.display = "inline-flex";
    input.addEventListener("input", () => {
      clearTimeout(_searchTimer);
      _searchTimer = setTimeout(() => {
        _state.search = input.value.trim();
        _state.page = 1;
        if (clear) clear.style.display = _state.search ? "inline-flex" : "none";
        applyFilters();
      }, 250);
    });
  }

  function _initKeyboard() {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePanel();
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
        e.preventDefault();
        document.getElementById("search-input")?.focus();
      }
    });
    window.addEventListener("popstate", (e) => {
      if (e.state) Object.assign(_state, e.state);
      else _restoreFromURL();
      RiskFilter.syncFromState();
      _populateDropdowns();
      applyFilters();
    });
  }

  async function init() {
    _restoreFromURL();

    // Hide table, show loading until data arrives
    document.querySelector(".st-table-wrap")?.classList.add("hidden");

    // Fetch all data once
    try {
      const res = await fetch("/api/students");
      const json = await res.json();
      _all = json.students || [];
      const note = document.getElementById("st-last-updated");
      if (note && json.last_updated)
        note.textContent = "Updated " + json.last_updated;
    } catch (err) {
      console.error("[Students] fetch failed:", err);
      const tbody = document.getElementById("st-tbody");
      if (tbody)
        tbody.innerHTML = `<tr><td colspan="8" class="st-loading-cell" style="color:var(--crit)">
        Failed to load student data.</td></tr>`;
      return;
    }

    _populateDropdowns();
    RiskFilter.syncFromState();
    _initSearch();
    _initKeyboard();
    applyFilters();
  }

  return {
    init,
    applyFilters,
    sort,
    goPage,
    clearSearch,
    clearAll,
    export: exportCSV,
    openPanel,
    closePanel,
    switchTab,
  };
})();

document.addEventListener("DOMContentLoaded", Students.init);

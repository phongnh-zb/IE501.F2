"use strict";

const Pipeline = (() => {
  let _timer = null;
  const _STATUS_CLASSES = ["ok", "warn", "err"];

  /* ── Render services ─────────────────────────────────────────────────── */
  function _renderServices(services, summary) {
    const groups = {};
    services.forEach((s) => {
      groups[s.group] = groups[s.group] || [];
      groups[s.group].push(s);
    });

    Object.entries(groups).forEach(([group, items]) => {
      const el = document.getElementById(`group-${group}`);
      if (!el) return;
      el.innerHTML = items
        .map((s) => {
          const link =
            s.up && s.web_ui
              ? `<a href="${s.web_ui}" target="_blank" rel="noopener" class="pipe-service-link" title="Open web UI">
               <i class="fas fa-arrow-up-right-from-square"></i>
             </a>`
              : "";
          return `
          <div class="pipe-service-row">
            <span class="pipe-dot ${s.up ? "pipe-dot-up" : "pipe-dot-down"}"></span>
            <span class="pipe-service-name">${s.name}</span>
            <span class="pipe-service-detail">${s.detail}</span>
            ${link}
            <span class="pipe-service-badge ${s.up ? "pipe-badge-up" : "pipe-badge-down"}">
              ${s.up ? "UP" : "DOWN"}
            </span>
          </div>`;
        })
        .join("");
    });

    // Update timestamp — format: HH:MM:SS YYYY/MM/DD
    const ts = document.getElementById("svc-updated");
    if (ts) {
      const now = new Date();
      const time = now.toTimeString().slice(0, 8);
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, "0");
      const d = String(now.getDate()).padStart(2, "0");
      ts.textContent = `Updated ${time} ${y}/${m}/${d}`;
    }

    // Update summary badge
    const sumEl = document.getElementById("pipe-summary");
    if (sumEl) {
      if (summary.down === 0) {
        sumEl.textContent = `All ${summary.total} services running`;
        sumEl.className = "pipe-summary all-up";
      } else if (summary.up === 0) {
        sumEl.textContent = `All services down`;
        sumEl.className = "pipe-summary all-down";
      } else {
        sumEl.textContent = `${summary.down} service${summary.down > 1 ? "s" : ""} down`;
        sumEl.className = "pipe-summary some-down";
      }
    }
  }

  /* ── Render data inventory ───────────────────────────────────────────── */
  function _renderData(data, cache) {
    function _hdfsValue(info) {
      if (!info.exists) return { text: "Not found", cls: "err" };
      return {
        text: `${info.count} file${info.count !== 1 ? "s" : ""}`,
        cls: "ok",
      };
    }

    function _set(id, text, cls = "") {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      // Preserve any existing styling classes from the template (e.g. mono, text-sm)
      el.classList.add("pipe-field-value");
      _STATUS_CLASSES.forEach((c) => el.classList.remove(c));
      if (cls) el.classList.add(cls);
    }

    const raw = _hdfsValue(data.hdfs_raw);
    const proc = _hdfsValue(data.hdfs_proc);

    _set("hdfs-raw", raw.text, raw.cls);
    _set("hdfs-proc", proc.text, proc.cls);

    _set(
      "hbase-predictions",
      data.predictions != null
        ? data.predictions.toLocaleString() + " rows"
        : "— (HBase offline)",
      data.predictions != null ? "ok" : "warn",
    );

    _set(
      "hbase-models",
      data.models != null
        ? data.models.toLocaleString() + " rows"
        : "— (HBase offline)",
      data.models != null ? "ok" : "warn",
    );

    _set(
      "cache-status",
      cache.is_ready ? "Ready" : "Not ready",
      cache.is_ready ? "ok" : "warn",
    );

    _set(
      "cache-count",
      cache.is_ready ? cache.student_count.toLocaleString() + " students" : "—",
    );

    _set("cache-updated", cache.last_updated || "—");
  }

  /* ── Fetch status ────────────────────────────────────────────────────── */
  async function _fetch() {
    const btn = document.getElementById("refresh-btn");
    try {
      const res = await fetch("/api/pipeline/status");
      if (!res.ok) throw new Error("status " + res.status);
      const data = await res.json();
      _renderServices(data.services, data.summary);
      _renderData(data.data, data.cache);
    } catch (err) {
      const sumEl = document.getElementById("pipe-summary");
      if (sumEl) {
        sumEl.textContent = "Status check failed";
        sumEl.className = "pipe-summary all-down";
      }
      console.error("[Pipeline]", err);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-rotate-right"></i> Refresh';
      }
    }
  }

  function toggleSection(btn) {
    const body = btn.nextElementSibling;
    const caret = btn.querySelector(".pipe-collapse-caret");
    const open = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!open));
    body.style.display = open ? "none" : "block";
    if (caret) {
      caret.className = open
        ? "fas fa-chevron-down pipe-collapse-caret"
        : "fas fa-chevron-up pipe-collapse-caret";
    }
  }

  function refresh() {
    const btn = document.getElementById("refresh-btn");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-rotate-right fa-spin"></i>Refreshing...';
    }
    _fetch();
  }

  function stop() {
    if (_timer) {
      clearInterval(_timer);
      _timer = null;
    }
  }

  function init() {
    // Defensive: avoid stacking multiple intervals if init() is called again
    stop();
    _fetch();
    // Auto-refresh every 15 seconds
    _timer = setInterval(_fetch, 15_000);
  }

  return { init, stop, refresh, toggleSection };
})();

document.addEventListener("DOMContentLoaded", Pipeline.init);
// Ensure polling stops when navigating away (including bfcache).
window.addEventListener("pagehide", Pipeline.stop);
window.addEventListener("beforeunload", Pipeline.stop);

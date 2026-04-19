"use strict";

const Users = (() => {
  let _mode = "create";
  let _editId = null;

  /* ── Eye toggle ───────────────────────────────────────────────────────── */
  function toggleEye(btn) {
    const input = btn.closest(".users-input-wrap").querySelector("input");
    const icon = btn.querySelector("i");
    if (input.type === "password") {
      input.type = "text";
      icon.className = "fas fa-eye-slash";
    } else {
      input.type = "password";
      icon.className = "fas fa-eye";
    }
  }

  /* ── Password strength ───────────────────────────────────────────────── */
  function checkStrength(value, barId, fillId, labelId) {
    const bar = document.getElementById(barId);
    const fill = document.getElementById(fillId);
    const label = document.getElementById(labelId);
    if (!bar) return;
    if (!value) {
      bar.style.display = "none";
      return;
    }
    bar.style.display = "flex";

    let score = 0;
    if (value.length >= 8) score++;
    if (value.length >= 10) score++;
    if (/[A-Z]/.test(value)) score++;
    if (/[0-9]/.test(value)) score++;
    if (/[^A-Za-z0-9]/.test(value)) score++;

    const levels = [
      {
        pct: "20%",
        color: "var(--crit)",
        text: "Weak",
        labelColor: "var(--crit)",
      },
      {
        pct: "40%",
        color: "var(--high)",
        text: "Fair",
        labelColor: "var(--high)",
      },
      {
        pct: "60%",
        color: "var(--watch)",
        text: "Good",
        labelColor: "var(--watch)",
      },
      { pct: "80%", color: "#059669", text: "Strong", labelColor: "#059669" },
      { pct: "100%", color: "#059669", text: "Great", labelColor: "#059669" },
    ];
    const lv = levels[Math.max(0, Math.min(score - 1, 4))];
    fill.style.width = lv.pct;
    fill.style.background = lv.color;
    label.textContent = lv.text;
    label.style.color = lv.labelColor;
  }

  /* ── Password match ──────────────────────────────────────────────────── */
  function _checkMatch(passwordId, confirmId, barId, fillId, labelId) {
    const pw = document.getElementById(passwordId);
    const conf = document.getElementById(confirmId);
    const bar = document.getElementById(barId);
    const fill = document.getElementById(fillId);
    const label = document.getElementById(labelId);
    if (!pw || !conf || !bar) return;
    if (!conf.value) {
      bar.style.display = "none";
      return;
    }
    bar.style.display = "flex";
    if (pw.value === conf.value) {
      label.textContent = "✓ Passwords match";
      label.style.color = "var(--safe)";
    } else {
      label.textContent = "✗ Passwords do not match";
      label.style.color = "var(--crit)";
    }
  }

  /* ── Panel helpers ────────────────────────────────────────────────────── */
  function _openPanel() {
    const panel = document.getElementById("users-panel");
    const backdrop = document.getElementById("users-backdrop");
    if (panel) {
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
    }
    if (backdrop) backdrop.classList.add("show");
  }

  function closePanel() {
    const panel = document.getElementById("users-panel");
    const backdrop = document.getElementById("users-backdrop");
    if (panel) {
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
    }
    if (backdrop) backdrop.classList.remove("show");
    _mode = "create";
    _editId = null;
  }

  function _resetPasswordFields() {
    ["form-password", "form-confirm"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.value = "";
        el.type = "password";
      }
    });
    document.querySelectorAll("#users-panel .users-eye i").forEach((i) => {
      i.className = "fas fa-eye";
    });
    ["form-strength", "form-match-bar"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = "none";
    });
  }

  function _setPanelReadonly(readonly) {
    ["form-full-name", "form-email"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.readOnly = readonly;
    });
    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => {
        cb.disabled = readonly;
      });
  }

  function _setPanelFoot(mode) {
    const foot = document.querySelector(".users-panel-foot");
    if (!foot) return;
    if (mode === "view") {
      foot.innerHTML = `<button class="btn btn-outline btn-sm" onclick="Users.closePanel()">Close</button>`;
    } else {
      const label = mode === "edit" ? "Update" : "Create";
      foot.innerHTML = `
        <button class="btn btn-outline btn-sm" onclick="Users.closePanel()">Cancel</button>
        <button class="btn btn-primary btn-sm" onclick="Users.submitForm()">${label}</button>`;
    }
  }

  /* ── View ─────────────────────────────────────────────────────────────── */
  function openView(userId, displayName, username, email, modules, isBlocked) {
    _mode = "view";
    _editId = userId;

    const title = document.getElementById("users-panel-title");
    title.innerHTML = isBlocked
      ? `${displayName} <span class="badge badge-crit" style="font-size:.7rem;vertical-align:middle;">Blocked</span>`
      : displayName;

    document.getElementById("form-full-name").value = displayName;
    document.getElementById("form-username").value = username;
    document.getElementById("form-email").value = email;
    document.getElementById("form-username").disabled = true;
    document.getElementById("form-password-group").style.display = "none";
    document.getElementById("form-confirm-group").style.display = "none";

    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => {
        cb.checked = modules.includes(cb.value);
      });

    _setPanelReadonly(true);
    _setPanelFoot("view");
    _openPanel();
  }

  /* ── Create ───────────────────────────────────────────────────────────── */
  function openCreate() {
    _mode = "create";
    _editId = null;

    document.getElementById("users-panel-title").textContent = "New Lecturer";
    document.getElementById("users-form").action = "/admin/users/create";
    document.getElementById("form-full-name").value = "";
    document.getElementById("form-username").value = "";
    document.getElementById("form-email").value = "";
    document.getElementById("form-username").disabled = false;
    document.getElementById("form-password-group").style.display = "";
    document.getElementById("form-confirm-group").style.display = "";

    _resetPasswordFields();
    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => (cb.checked = false));

    _setPanelReadonly(false);
    _setPanelFoot("create");
    _openPanel();
    document.getElementById("form-full-name").focus();
  }

  /* ── Edit ─────────────────────────────────────────────────────────────── */
  function openEdit(userId, displayName, username, email, modules) {
    _mode = "edit";
    _editId = userId;

    document.getElementById("users-panel-title").textContent =
      `Edit — ${displayName}`;
    document.getElementById("users-form").action =
      `/admin/users/${userId}/edit`;
    document.getElementById("form-full-name").value = displayName;
    document.getElementById("form-email").value = email;
    document.getElementById("form-username").value = username;
    document.getElementById("form-username").disabled = true;
    document.getElementById("form-password-group").style.display = "none";
    document.getElementById("form-confirm-group").style.display = "none";

    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => {
        cb.checked = modules.includes(cb.value);
      });

    _setPanelReadonly(false);
    _setPanelFoot("edit");
    _openPanel();
    document.getElementById("form-full-name").focus();
  }

  /* ── Form submit ──────────────────────────────────────────────────────── */
  function submitForm() {
    const form = document.getElementById("users-form");
    if (form.requestSubmit) {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  /* ── Reset password ───────────────────────────────────────────────────── */
  function openResetPassword(userId, displayName) {
    document.getElementById("reset-title").textContent =
      `Reset password — ${displayName}`;
    document.getElementById("reset-form").action =
      `/admin/users/${userId}/reset-password`;
    ["reset-password", "reset-confirm"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.value = "";
        el.type = "password";
      }
    });
    document.querySelectorAll("#reset-modal .users-eye i").forEach((i) => {
      i.className = "fas fa-eye";
    });
    ["reset-strength", "reset-match-bar"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = "none";
    });
    document.getElementById("reset-overlay").classList.remove("hidden");
    document.getElementById("reset-modal").classList.remove("hidden");
    document.getElementById("reset-password").focus();
  }

  function closeReset() {
    document.getElementById("reset-overlay").classList.add("hidden");
    document.getElementById("reset-modal").classList.add("hidden");
  }

  function submitReset() {
    const form = document.getElementById("reset-form");
    if (form.requestSubmit) {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  /* ── Block ────────────────────────────────────────────────────────────── */
  function confirmBlock(userId, displayName) {
    document.getElementById("block-name").textContent = displayName;
    document.getElementById("block-form").action =
      `/admin/users/${userId}/block`;
    document.getElementById("block-overlay").classList.remove("hidden");
    document.getElementById("block-modal").classList.remove("hidden");
  }

  function closeBlock() {
    document.getElementById("block-overlay").classList.add("hidden");
    document.getElementById("block-modal").classList.add("hidden");
  }

  /* ── Delete ───────────────────────────────────────────────────────────── */
  function confirmDelete(userId, displayName) {
    document.getElementById("delete-name").textContent = displayName;
    document.getElementById("delete-form").action =
      `/admin/users/${userId}/delete`;
    document.getElementById("delete-overlay").classList.remove("hidden");
    document.getElementById("delete-modal").classList.remove("hidden");
  }

  function closeDelete() {
    document.getElementById("delete-overlay").classList.add("hidden");
    document.getElementById("delete-modal").classList.add("hidden");
  }

  /* ── Keyboard ─────────────────────────────────────────────────────────── */
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    closePanel();
    closeReset();
    closeBlock();
    closeDelete();
  });

  /* ── Wire match bars ──────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    const formConfirm = document.getElementById("form-confirm");
    const formPassword = document.getElementById("form-password");
    if (formConfirm)
      formConfirm.addEventListener("input", () =>
        _checkMatch(
          "form-password",
          "form-confirm",
          "form-match-bar",
          "form-match-fill",
          "form-match-label",
        ),
      );
    if (formPassword)
      formPassword.addEventListener("input", () => {
        if (document.getElementById("form-confirm").value)
          _checkMatch(
            "form-password",
            "form-confirm",
            "form-match-bar",
            "form-match-fill",
            "form-match-label",
          );
      });

    const resetConfirm = document.getElementById("reset-confirm");
    const resetPassword = document.getElementById("reset-password");
    if (resetConfirm)
      resetConfirm.addEventListener("input", () =>
        _checkMatch(
          "reset-password",
          "reset-confirm",
          "reset-match-bar",
          "reset-match-fill",
          "reset-match-label",
        ),
      );
    if (resetPassword)
      resetPassword.addEventListener("input", () => {
        if (document.getElementById("reset-confirm").value)
          _checkMatch(
            "reset-password",
            "reset-confirm",
            "reset-match-bar",
            "reset-match-fill",
            "reset-match-label",
          );
      });
  });

  return {
    toggleEye,
    checkStrength,
    openView,
    openCreate,
    openEdit,
    closePanel,
    submitForm,
    openResetPassword,
    closeReset,
    submitReset,
    confirmBlock,
    closeBlock,
    confirmDelete,
    closeDelete,
  };
})();

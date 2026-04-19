"use strict";

const Users = (() => {
  let _mode = "create";
  let _editId = null;

  /* ── Eye toggle — mirrors Profile.toggleEye ───────────────────────────── */
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

  /* ── Panel helpers ────────────────────────────────────────────────────── */
  function _openPanel() {
    const panel = document.getElementById("users-panel");
    const backdrop = document.getElementById("users-backdrop");
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    backdrop.classList.add("show");
  }

  function closePanel() {
    const panel = document.getElementById("users-panel");
    const backdrop = document.getElementById("users-backdrop");
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("show");
    _mode = "create";
    _editId = null;
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
    document.getElementById("form-password").value = "";
    document.getElementById("form-confirm").value = "";

    // Reset eye icons to hidden state
    document.querySelectorAll(".users-eye i").forEach((i) => {
      i.className = "fas fa-eye";
    });
    document
      .querySelectorAll(".users-input-wrap input[type=text]")
      .forEach((inp) => {
        inp.type = "password";
      });

    document.getElementById("form-username").disabled = false;
    document.getElementById("form-password-group").style.display = "";
    document.getElementById("form-confirm-group").style.display = "";

    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => (cb.checked = false));

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

    const usernameField = document.getElementById("form-username");
    usernameField.value = username;
    usernameField.disabled = true;

    document.getElementById("form-password-group").style.display = "none";
    document.getElementById("form-confirm-group").style.display = "none";

    document
      .querySelectorAll("#form-modules input[type=checkbox]")
      .forEach((cb) => {
        cb.checked = modules.includes(cb.value);
      });

    _openPanel();
    document.getElementById("form-full-name").focus();
  }

  /* ── Form submit ──────────────────────────────────────────────────────── */
  function submitForm() {
    document.getElementById("users-form").submit();
  }

  /* ── Reset password ───────────────────────────────────────────────────── */
  function openResetPassword(userId, displayName) {
    document.getElementById("reset-title").textContent =
      `Reset password — ${displayName}`;
    document.getElementById("reset-form").action =
      `/admin/users/${userId}/reset-password`;
    document.getElementById("reset-password").value = "";
    document.getElementById("reset-confirm").value = "";

    document.getElementById("reset-overlay").classList.remove("hidden");
    document.getElementById("reset-modal").classList.remove("hidden");
    document.getElementById("reset-password").focus();
  }

  function closeReset() {
    document.getElementById("reset-overlay").classList.add("hidden");
    document.getElementById("reset-modal").classList.add("hidden");
  }

  function submitReset() {
    document.getElementById("reset-form").submit();
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
    closeDelete();
  });

  return {
    toggleEye,
    openCreate,
    openEdit,
    closePanel,
    submitForm,
    openResetPassword,
    closeReset,
    submitReset,
    confirmDelete,
    closeDelete,
  };
})();

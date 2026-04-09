"use strict";

const Profile = (() => {
  /* ── Eye toggle ──────────────────────────────────────────────────────── */
  function toggleEye(btn) {
    const input = btn.closest(".prof-input-wrap").querySelector("input");
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
  function checkStrength(value) {
    const wrap = document.getElementById("pw-strength");
    const fill = document.getElementById("pw-strength-fill");
    const label = document.getElementById("pw-strength-label");
    if (!value) {
      wrap.style.display = "none";
      return;
    }
    wrap.style.display = "flex";

    let score = 0;
    if (value.length >= 8) score++;
    if (value.length >= 12) score++;
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

    checkMatch();
    _checkPasswordBtn();
  }

  /* ── Confirm match ───────────────────────────────────────────────────── */
  function checkMatch() {
    const newPw = document.getElementById("new_password");
    const confPw = document.getElementById("confirm_password");
    const msg = document.getElementById("pw-match-msg");
    if (!confPw || !msg || !confPw.value) {
      if (msg) msg.textContent = "";
      return;
    }

    if (newPw.value === confPw.value) {
      msg.textContent = "✓ Passwords match";
      msg.style.color = "var(--safe)";
    } else {
      msg.textContent = "✗ Passwords do not match";
      msg.style.color = "var(--crit)";
    }
    _checkPasswordBtn();
  }

  /* ── Button enable/disable logic ─────────────────────────────────────── */

  function _checkInfoBtn() {
    const btn = document.getElementById("btn-save-info");
    const form = document.getElementById("form-info");
    if (!btn || !form) return;
    const name = form.full_name.value.trim();
    const email = form.email.value.trim();
    const changed =
      name !== btn.dataset.initName || email !== btn.dataset.initEmail;
    btn.disabled = !changed;
  }

  function _checkPasswordBtn() {
    const btn = document.getElementById("btn-change-pw");
    const current = document.getElementById("current_password");
    const newPw = document.getElementById("new_password");
    const confPw = document.getElementById("confirm_password");
    if (!btn || !current || !newPw || !confPw) return;
    const allFilled = current.value && newPw.value && confPw.value;
    const matching = newPw.value === confPw.value;
    const longEnough = newPw.value.length >= 8;
    btn.disabled = !(allFilled && matching && longEnough);
  }

  function _initInfoTracking() {
    const btn = document.getElementById("btn-save-info");
    const form = document.getElementById("form-info");
    if (!btn || !form) return;
    // Store initial values as data attributes on the button
    btn.dataset.initName = form.full_name.value.trim();
    btn.dataset.initEmail = form.email.value.trim();
    form.full_name.addEventListener("input", _checkInfoBtn);
    form.email.addEventListener("input", _checkInfoBtn);
  }

  function _initPasswordTracking() {
    ["current_password", "new_password", "confirm_password"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("input", _checkPasswordBtn);
    });
  }

  /* ── Disabled button style ───────────────────────────────────────────── */
  function _initDisabledStyle() {
    const style = document.createElement("style");
    style.textContent =
      ".btn:disabled { opacity: .45; cursor: not-allowed; pointer-events: none; }";
    document.head.appendChild(style);
  }

  function init() {
    _initDisabledStyle();
    _initInfoTracking();
    _initPasswordTracking();
  }

  return { init, toggleEye, checkStrength, checkMatch };
})();

document.addEventListener("DOMContentLoaded", Profile.init);

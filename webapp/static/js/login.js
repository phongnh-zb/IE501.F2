"use strict";

document.getElementById("login-form").addEventListener("keydown", function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    this.submit();
  }
});

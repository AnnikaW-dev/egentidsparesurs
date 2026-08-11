/* Mobile nav + Behandlingar submenu — keyboard friendly; respect reduced motion. */
(function () {
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("site-nav");
  if (!toggle || !nav) return;

  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    // Adjust: Swedish labels for screen readers
    toggle.setAttribute("aria-label", open ? "Dölj meny" : "Visa meny");
  }

  toggle.addEventListener("click", function () {
    setOpen(!nav.classList.contains("is-open"));
  });

  // Escape closes the mobile menu (no keyboard trap).
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setOpen(false);
      toggle.focus();
    }
  });
})();

/* Nav disclosure submenu (Behandlingar) — click/keyboard; Escape closes. */
(function () {
  var toggles = document.querySelectorAll("[data-submenu-toggle]");
  if (!toggles.length) return;

  function setSubmenu(btn, open) {
    var id = btn.getAttribute("aria-controls");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) return;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    panel.classList.toggle("is-open", open);
  }

  function closeAll(except) {
    toggles.forEach(function (btn) {
      if (btn !== except) setSubmenu(btn, false);
    });
  }

  toggles.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var willOpen = btn.getAttribute("aria-expanded") !== "true";
      closeAll(btn);
      setSubmenu(btn, willOpen);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    var openBtn = document.querySelector('[data-submenu-toggle][aria-expanded="true"]');
    if (!openBtn) return;
    setSubmenu(openBtn, false);
    openBtn.focus();
  });

  document.addEventListener("click", function (event) {
    if (event.target.closest(".has-submenu")) return;
    closeAll(null);
  });
})();

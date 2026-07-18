/* Mobile nav — keyboard friendly; respect reduced motion. */
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

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

/* Telefon: keep only digits while typing (do not block form submit). */
(function () {
  document.querySelectorAll('input[data-digits-only="true"]').forEach(function (input) {
    function digitsOnly(value) {
      return (value || "").replace(/\D/g, "");
    }

    input.addEventListener("beforeinput", function (event) {
      if (event.data && /\D/.test(event.data)) {
        event.preventDefault();
      }
    });

    input.addEventListener("input", function () {
      var cleaned = digitsOnly(input.value);
      if (input.value !== cleaned) {
        input.value = cleaned;
      }
    });

    input.addEventListener("paste", function (event) {
      event.preventDefault();
      var text = (event.clipboardData || window.clipboardData).getData("text") || "";
      var digits = digitsOnly(text);
      var start = input.selectionStart || 0;
      var end = input.selectionEnd || 0;
      var value = input.value || "";
      input.value = value.slice(0, start) + digits + value.slice(end);
    });

    // Before submit: strip non-digits so autofill with spaces/dashes still works.
    var form = input.form;
    if (form && !form.dataset.phoneStripBound) {
      form.dataset.phoneStripBound = "1";
      form.addEventListener("submit", function () {
        form.querySelectorAll('input[data-digits-only="true"]').forEach(function (el) {
          el.value = digitsOnly(el.value);
        });
      });
    }
  });
})();

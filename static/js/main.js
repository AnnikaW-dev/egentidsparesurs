/* Mobile nav + e-post validation — keyboard friendly; respect reduced motion. */
(function () {
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
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
  }
})();

/* E-post fields: enforce mail format and show Swedish message when invalid */
(function () {
  // Adjust: keep in sync with pages.forms.EMAIL_INVALID_MSG / EMAIL_REQUIRED_MSG
  var INVALID_MSG = "Ange en giltig e-postadress, t.ex. namn@exempel.se.";
  var REQUIRED_MSG = "Ange en e-postadress.";
  // Practical check: local@domain.tld (rejects bare words without @ / domain)
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function syncValidity(input) {
    var value = (input.value || "").trim();
    if (!value) {
      input.setCustomValidity(input.required ? REQUIRED_MSG : "");
      return;
    }
    if (!EMAIL_RE.test(value)) {
      input.setCustomValidity(INVALID_MSG);
      return;
    }
    input.setCustomValidity("");
  }

  function ensureErrorNode(input) {
    var id = input.getAttribute("aria-describedby") || "error_" + (input.name || "email");
    var node = document.getElementById(id);
    if (!node) {
      node = document.createElement("p");
      node.className = "field-error";
      node.id = id;
      node.setAttribute("role", "alert");
      input.insertAdjacentElement("afterend", node);
      input.setAttribute("aria-describedby", id);
    }
    return node;
  }

  function showInlineError(input, message) {
    var row = input.closest(".aligned-row");
    if (row) row.classList.add("has-error");
    input.setAttribute("aria-invalid", "true");
    var node = ensureErrorNode(input);
    node.textContent = message;
  }

  function clearInlineError(input) {
    var row = input.closest(".aligned-row");
    if (row) row.classList.remove("has-error");
    input.removeAttribute("aria-invalid");
    var id = input.getAttribute("aria-describedby");
    var node = id ? document.getElementById(id) : null;
    // Only clear client-injected errors; leave server-rendered ones until next edit.
    if (node && node.dataset.clientError === "1") {
      node.remove();
      input.removeAttribute("aria-describedby");
    }
  }

  document.querySelectorAll('input[type="email"]').forEach(function (input) {
    syncValidity(input);

    input.addEventListener("input", function () {
      syncValidity(input);
      if (EMAIL_RE.test((input.value || "").trim())) {
        clearInlineError(input);
      }
    });

    input.addEventListener("blur", function () {
      syncValidity(input);
      var value = (input.value || "").trim();
      if (!value && input.required) {
        var node = ensureErrorNode(input);
        node.dataset.clientError = "1";
        showInlineError(input, REQUIRED_MSG);
      } else if (value && !EMAIL_RE.test(value)) {
        var err = ensureErrorNode(input);
        err.dataset.clientError = "1";
        showInlineError(input, INVALID_MSG);
      } else if (value && EMAIL_RE.test(value)) {
        clearInlineError(input);
      }
    });

    var form = input.form;
    if (form && !form.dataset.emailValidateBound) {
      form.dataset.emailValidateBound = "1";
      form.addEventListener("submit", function (event) {
        var emails = form.querySelectorAll('input[type="email"]');
        var firstInvalid = null;
        emails.forEach(function (el) {
          syncValidity(el);
          var value = (el.value || "").trim();
          if (el.required && !value) {
            var n = ensureErrorNode(el);
            n.dataset.clientError = "1";
            showInlineError(el, REQUIRED_MSG);
            if (!firstInvalid) firstInvalid = el;
          } else if (value && !EMAIL_RE.test(value)) {
            var n2 = ensureErrorNode(el);
            n2.dataset.clientError = "1";
            showInlineError(el, INVALID_MSG);
            if (!firstInvalid) firstInvalid = el;
          }
        });
        if (firstInvalid) {
          event.preventDefault();
          firstInvalid.focus();
        }
      });
    }
  });
})();

/* Telefon: only digits allowed while typing; Swedish message if letters slip through */
(function () {
  // Adjust: keep in sync with pages.forms.PHONE_DIGITS_MSG
  var DIGITS_MSG = "Telefonnummer får bara innehålla siffror.";

  function ensureErrorNode(input) {
    var id = input.getAttribute("aria-describedby") || "error_" + (input.name || "phone");
    var node = document.getElementById(id);
    if (!node) {
      node = document.createElement("p");
      node.className = "field-error";
      node.id = id;
      node.setAttribute("role", "alert");
      input.insertAdjacentElement("afterend", node);
      input.setAttribute("aria-describedby", id);
    }
    return node;
  }

  function showInlineError(input, message) {
    var row = input.closest(".aligned-row");
    if (row) row.classList.add("has-error");
    input.setAttribute("aria-invalid", "true");
    var node = ensureErrorNode(input);
    node.dataset.clientError = "1";
    node.textContent = message;
  }

  function clearInlineError(input) {
    var row = input.closest(".aligned-row");
    if (row) row.classList.remove("has-error");
    input.removeAttribute("aria-invalid");
    var id = input.getAttribute("aria-describedby");
    var node = id ? document.getElementById(id) : null;
    if (node && node.dataset.clientError === "1") {
      node.remove();
      input.removeAttribute("aria-describedby");
    }
  }

  document.querySelectorAll('input[data-digits-only="true"]').forEach(function (input) {
    input.addEventListener("beforeinput", function (event) {
      if (event.data && /\D/.test(event.data)) {
        event.preventDefault();
      }
    });

    input.addEventListener("input", function () {
      var cleaned = (input.value || "").replace(/\D/g, "");
      if (input.value !== cleaned) {
        input.value = cleaned;
      }
      input.setCustomValidity("");
      clearInlineError(input);
    });

    input.addEventListener("paste", function (event) {
      event.preventDefault();
      var text = (event.clipboardData || window.clipboardData).getData("text") || "";
      var digits = text.replace(/\D/g, "");
      var start = input.selectionStart || 0;
      var end = input.selectionEnd || 0;
      var value = input.value || "";
      input.value = value.slice(0, start) + digits + value.slice(end);
      clearInlineError(input);
    });

    var form = input.form;
    if (form && !form.dataset.phoneValidateBound) {
      form.dataset.phoneValidateBound = "1";
      form.addEventListener("submit", function (event) {
        var phones = form.querySelectorAll('input[data-digits-only="true"]');
        var firstInvalid = null;
        phones.forEach(function (el) {
          var value = (el.value || "").trim();
          if (value && /\D/.test(value)) {
            el.setCustomValidity(DIGITS_MSG);
            showInlineError(el, DIGITS_MSG);
            if (!firstInvalid) firstInvalid = el;
          } else {
            el.setCustomValidity("");
          }
        });
        if (firstInvalid) {
          event.preventDefault();
          firstInvalid.focus();
        }
      });
    }
  });
})();

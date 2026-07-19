/* Site JS — nav + form field helpers. Prefer server validation; show clear Swedish errors. */
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

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setOpen(false);
      toggle.focus();
    }
  });
})();

/* Shared: show / clear field errors without setCustomValidity (avoids silent submit blocks). */
(function () {
  // Adjust: keep copy in sync with pages.forms messages
  var EMAIL_INVALID = "Ange en giltig e-postadress, t.ex. namn@exempel.se.";
  var EMAIL_REQUIRED = "Ange en e-postadress.";
  var PHONE_DIGITS = "Telefonnummer får bara innehålla siffror.";
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function errorIdFor(input) {
    return "error_" + (input.name || input.id || "field");
  }

  function ensureErrorNode(input) {
    var id = input.getAttribute("aria-describedby") || errorIdFor(input);
    var node = document.getElementById(id);
    if (!node) {
      node = document.createElement("p");
      node.className = "field-error";
      node.id = id;
      node.setAttribute("role", "alert");
      node.dataset.clientError = "1";
      input.insertAdjacentElement("afterend", node);
      input.setAttribute("aria-describedby", id);
    }
    return node;
  }

  function showError(input, message) {
    var row = input.closest(".aligned-row");
    if (row) row.classList.add("has-error");
    input.setAttribute("aria-invalid", "true");
    var node = ensureErrorNode(input);
    node.dataset.clientError = "1";
    node.textContent = message;
  }

  function clearError(input) {
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

  function digitsOnly(value) {
    return (value || "").replace(/\D/g, "");
  }

  /* Telefon: digits only while typing */
  document.querySelectorAll('input[data-digits-only="true"]').forEach(function (input) {
    input.addEventListener("keydown", function (event) {
      // Allow control keys, arrows, tab, etc.
      if (
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        event.key === "Backspace" ||
        event.key === "Delete" ||
        event.key === "Tab" ||
        event.key === "Escape" ||
        event.key === "Enter" ||
        event.key.indexOf("Arrow") === 0 ||
        event.key === "Home" ||
        event.key === "End"
      ) {
        return;
      }
      if (event.key.length === 1 && /\D/.test(event.key)) {
        event.preventDefault();
        showError(input, PHONE_DIGITS);
      }
    });

    input.addEventListener("beforeinput", function (event) {
      if (event.data && /\D/.test(event.data)) {
        event.preventDefault();
        showError(input, PHONE_DIGITS);
      }
    });

    input.addEventListener("input", function () {
      var cleaned = digitsOnly(input.value);
      if (input.value !== cleaned) {
        input.value = cleaned;
        showError(input, PHONE_DIGITS);
      } else if (cleaned) {
        clearError(input);
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
      if (digits !== text.replace(/\s/g, "")) {
        showError(input, PHONE_DIGITS);
      } else {
        clearError(input);
      }
    });
  });

  /* E-post: validate on blur + submit with visible message */
  document.querySelectorAll('input[data-validate-email="true"], input[type="email"]').forEach(
    function (input) {
      function validateEmail(show) {
        var value = (input.value || "").trim();
        if (!value) {
          if (input.required && show) {
            showError(input, EMAIL_REQUIRED);
            return false;
          }
          clearError(input);
          return !input.required;
        }
        if (!EMAIL_RE.test(value)) {
          if (show) showError(input, EMAIL_INVALID);
          return false;
        }
        clearError(input);
        return true;
      }

      input.addEventListener("blur", function () {
        validateEmail(true);
      });
      input.addEventListener("input", function () {
        if (EMAIL_RE.test((input.value || "").trim())) {
          clearError(input);
        }
      });
    }
  );

  /* Form submit: strip phone, validate e-post, show errors (do not fail silently) */
  document.querySelectorAll("form.aligned-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      form.querySelectorAll('input[data-digits-only="true"]').forEach(function (el) {
        el.value = digitsOnly(el.value);
      });

      var firstInvalid = null;
      form
        .querySelectorAll('input[data-validate-email="true"], input[type="email"]')
        .forEach(function (el) {
          var value = (el.value || "").trim();
          el.value = value;
          if (el.required && !value) {
            showError(el, EMAIL_REQUIRED);
            if (!firstInvalid) firstInvalid = el;
          } else if (value && !EMAIL_RE.test(value)) {
            showError(el, EMAIL_INVALID);
            if (!firstInvalid) firstInvalid = el;
          } else {
            clearError(el);
          }
        });

      if (firstInvalid) {
        event.preventDefault();
        firstInvalid.focus();
        firstInvalid.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    });
  });
})();

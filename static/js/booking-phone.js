/* booking-phone.js — block non-digits in Telefonnummer on the booking form. */
(function () {
  var PHONE_SELECTOR = "#id_customer_phone, [data-phone-digits-only]";

  function isPhoneInput(el) {
    return el && el.matches && el.matches(PHONE_SELECTOR);
  }

  function stripDigits(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function attachPhoneInput(input) {
    if (!input || input.dataset.phoneDigitsBound === "1") return;
    input.dataset.phoneDigitsBound = "1";
    input.setAttribute("inputmode", "numeric");
    input.setAttribute("autocomplete", "tel");

    input.addEventListener("keydown", function (event) {
      var allowed = [
        "Backspace",
        "Delete",
        "Tab",
        "Escape",
        "Enter",
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "Home",
        "End",
      ];
      if (allowed.indexOf(event.key) !== -1) return;
      if (event.ctrlKey || event.metaKey) return;
      if (/^\d$/.test(event.key)) return;
      event.preventDefault();
    });

    input.addEventListener("beforeinput", function (event) {
      if (event.inputType === "insertFromPaste") return;
      if (event.data && /\D/.test(event.data)) {
        event.preventDefault();
      }
    });

    input.addEventListener("paste", function (event) {
      event.preventDefault();
      var pasted = (event.clipboardData || window.clipboardData).getData("text");
      var digits = stripDigits(pasted);
      var start = input.selectionStart;
      var end = input.selectionEnd;
      var value = input.value;
      input.value = value.slice(0, start) + digits + value.slice(end);
      var pos = start + digits.length;
      input.setSelectionRange(pos, pos);
    });

    input.addEventListener("input", function () {
      var cleaned = stripDigits(input.value);
      if (input.value !== cleaned) {
        input.value = cleaned;
      }
    });
  }

  function init() {
    document.querySelectorAll(PHONE_SELECTOR).forEach(attachPhoneInput);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

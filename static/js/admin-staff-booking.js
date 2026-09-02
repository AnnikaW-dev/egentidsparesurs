/* admin-staff-booking.js — show klockslag for the date chosen on Boka in kund. */
(function () {
  function init() {
    var dateInput = document.getElementById("id_booking_date");
    var timeSelect = document.getElementById("id_booking_time");
    if (!dateInput || !timeSelect) {
      return;
    }
    var byDay = {};
    try {
      byDay = JSON.parse(dateInput.getAttribute("data-slots") || "{}");
    } catch (err) {
      return;
    }

    function fillTimes(keepValue) {
      var day = dateInput.value;
      var current = keepValue ? String(timeSelect.value || "") : "";
      timeSelect.innerHTML = "";
      var empty = document.createElement("option");
      empty.value = "";
      var slots = byDay[day] || [];
      if (!day) {
        empty.textContent = "Välj datum först";
      } else if (!slots.length) {
        empty.textContent = "Inga lediga tider den dagen";
      } else {
        empty.textContent = "Välj tid";
      }
      timeSelect.appendChild(empty);
      slots.forEach(function (slot) {
        var option = document.createElement("option");
        option.value = String(slot.id);
        option.textContent = slot.time;
        if (String(slot.id) === current) {
          option.selected = true;
        }
        timeSelect.appendChild(option);
      });
    }

    dateInput.addEventListener("change", function () {
      fillTimes(false);
    });
    fillTimes(true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

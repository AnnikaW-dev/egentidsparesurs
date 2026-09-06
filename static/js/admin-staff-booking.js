/* admin-staff-booking.js — klockslag for the chosen treatment and date. */
(function () {
  function init() {
    var dateInput = document.getElementById("id_booking_date");
    var timeSelect = document.getElementById("id_booking_time");
    var serviceSelect = document.getElementById("id_service");
    var jsonEl = document.getElementById("staff-booking-slots");
    if (!dateInput || !timeSelect || !jsonEl) {
      return;
    }
    var byService = {};
    try {
      byService = JSON.parse(jsonEl.textContent || "{}");
    } catch (err) {
      return;
    }

    function slotsForSelection() {
      var sid = serviceSelect ? String(serviceSelect.value || "") : "";
      var day = dateInput.value;
      if (sid && byService[sid]) {
        return byService[sid][day] || [];
      }
      var seen = {};
      var merged = [];
      Object.keys(byService).forEach(function (key) {
        (byService[key][day] || []).forEach(function (slot) {
          if (!seen[slot.id]) {
            seen[slot.id] = true;
            merged.push(slot);
          }
        });
      });
      merged.sort(function (a, b) {
        return a.time < b.time ? -1 : a.time > b.time ? 1 : 0;
      });
      return merged;
    }

    function fillTimes(keepValue) {
      var day = dateInput.value;
      var current = keepValue ? String(timeSelect.value || "") : "";
      timeSelect.innerHTML = "";
      var empty = document.createElement("option");
      empty.value = "";
      var slots = slotsForSelection();
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

    dateInput.addEventListener("input", function () {
      fillTimes(false);
    });
    dateInput.addEventListener("change", function () {
      fillTimes(false);
    });
    if (serviceSelect) {
      serviceSelect.addEventListener("change", function () {
        fillTimes(false);
      });
    }
    fillTimes(true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

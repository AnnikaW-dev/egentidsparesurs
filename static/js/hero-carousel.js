/* hero-carousel.js — prev/next/dots for page heroes; autoplay unless reduced motion. */
(function () {
  var INTERVAL_MS = 7000; /* Adjust: seconds between slides on Hem / Behandlingar */
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function init(root) {
    var slides = root.querySelectorAll("[data-hero-slide]");
    var dots = root.querySelectorAll("[data-hero-dot]");
    var status = root.querySelector("[data-hero-status]");
    var pauseBtn = root.querySelector("[data-hero-pause]");
    var total = slides.length;
    if (total < 2) return;

    var index = 0;
    var timer = null;
    var paused = reduceMotion;

    function show(next) {
      index = (next + total) % total;
      slides.forEach(function (slide, i) {
        var on = i === index;
        slide.classList.toggle("is-active", on);
        if (on) slide.removeAttribute("hidden");
        else slide.setAttribute("hidden", "");
      });
      dots.forEach(function (dot, i) {
        if (i === index) dot.setAttribute("aria-current", "true");
        else dot.removeAttribute("aria-current");
      });
      if (status) status.textContent = "Bild " + (index + 1) + " av " + total;
    }

    function stopTimer() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function startTimer() {
      stopTimer();
      if (paused || reduceMotion) return;
      timer = window.setInterval(function () {
        show(index + 1);
      }, INTERVAL_MS);
    }

    function setPaused(value) {
      paused = value;
      if (pauseBtn) {
        pauseBtn.setAttribute("aria-pressed", paused ? "true" : "false");
        pauseBtn.setAttribute("aria-label", paused ? "Spela bildspel" : "Pausa bildspel");
        pauseBtn.textContent = paused ? "Spela" : "Pausa";
      }
      if (paused) stopTimer();
      else startTimer();
    }

    var prev = root.querySelector("[data-hero-prev]");
    var next = root.querySelector("[data-hero-next]");
    if (prev) prev.addEventListener("click", function () { show(index - 1); startTimer(); });
    if (next) next.addEventListener("click", function () { show(index + 1); startTimer(); });
    dots.forEach(function (dot, i) {
      dot.addEventListener("click", function () { show(i); startTimer(); });
    });
    if (pauseBtn) {
      pauseBtn.addEventListener("click", function () { setPaused(!paused); });
    }

    root.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        show(index - 1);
        startTimer();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        show(index + 1);
        startTimer();
      }
    });
    root.setAttribute("tabindex", "0");

    root.addEventListener("mouseenter", stopTimer);
    root.addEventListener("mouseleave", startTimer);
    root.addEventListener("focusin", stopTimer);
    root.addEventListener("focusout", function (event) {
      if (!root.contains(event.relatedTarget)) startTimer();
    });

    var touchStartX = null;
    root.addEventListener("touchstart", function (event) {
      if (event.changedTouches && event.changedTouches[0]) {
        touchStartX = event.changedTouches[0].screenX;
      }
    }, { passive: true });
    root.addEventListener("touchend", function (event) {
      if (touchStartX == null || !event.changedTouches || !event.changedTouches[0]) return;
      var dx = event.changedTouches[0].screenX - touchStartX;
      touchStartX = null;
      if (Math.abs(dx) < 40) return;
      if (dx > 0) show(index - 1);
      else show(index + 1);
      startTimer();
    }, { passive: true });

    if (reduceMotion) setPaused(true);
    else startTimer();
  }

  document.querySelectorAll("[data-hero-carousel]").forEach(init);
})();

/* hero-carousel.js — prev/next/dots for page heroes; no autoplay (user advances). */
(function () {
  function init(root) {
    var slides = root.querySelectorAll("[data-hero-slide]");
    var dots = root.querySelectorAll("[data-hero-dot]");
    var status = root.querySelector("[data-hero-status]");
    var total = slides.length;
    if (total < 2) return;

    var index = 0;

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

    var prev = root.querySelector("[data-hero-prev]");
    var next = root.querySelector("[data-hero-next]");
    if (prev) prev.addEventListener("click", function () { show(index - 1); });
    if (next) next.addEventListener("click", function () { show(index + 1); });
    dots.forEach(function (dot, i) {
      dot.addEventListener("click", function () { show(i); });
    });

    root.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        show(index - 1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        show(index + 1);
      }
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
    }, { passive: true });
  }

  document.querySelectorAll("[data-hero-carousel]").forEach(init);
})();

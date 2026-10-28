(function () {
  "use strict";

  const root = document.querySelector("[data-carousel]");
  if (!root) return;

  const viewport = root.querySelector("[data-carousel-viewport]");
  const track = root.querySelector("[data-carousel-track]");
  const prevBtn = root.querySelector("[data-carousel-prev]");
  const nextBtn = root.querySelector("[data-carousel-next]");
  const dotsEl = root.querySelector("[data-carousel-dots]");
  if (!viewport || !track) return;

  const cards = Array.from(track.children);
  if (cards.length === 0) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const INTERVAL_MS = 5000;
  let autoTimer = null;
  let paused = false;

  // Build one dot per card.
  const dots = cards.map((card, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "carousel-dot";
    dot.setAttribute("aria-label", "Show " + (card.dataset.title || "tool " + (i + 1)));
    dot.addEventListener("click", () => { scrollToIndex(i); resetTimer(); });
    if (dotsEl) dotsEl.appendChild(dot);
    return dot;
  });

  function smooth() { return reducedMotion ? "auto" : "smooth"; }

  function scrollToIndex(i) {
    if (i < 0) i = 0;
    if (i >= cards.length) i = cards.length - 1;
    const card = cards[i];
    const delta = card.getBoundingClientRect().left - viewport.getBoundingClientRect().left;
    viewport.scrollTo({ left: viewport.scrollLeft + delta, behavior: smooth() });
  }

  function currentIndex() {
    const viewportLeft = viewport.getBoundingClientRect().left;
    let best = 0, bestDist = Infinity;
    cards.forEach((card, i) => {
      const dist = Math.abs(card.getBoundingClientRect().left - viewportLeft);
      if (dist < bestDist) { bestDist = dist; best = i; }
    });
    return best;
  }

  function updateDots() {
    const i = currentIndex();
    dots.forEach((dot, idx) => {
      dot.setAttribute("aria-current", idx === i ? "true" : "false");
    });
  }

  function next() {
    const i = currentIndex();
    scrollToIndex(i >= cards.length - 1 ? 0 : i + 1);
  }
  function prev() {
    const i = currentIndex();
    scrollToIndex(i <= 0 ? cards.length - 1 : i - 1);
  }

  function resetTimer() {
    clearTimeout(autoTimer);
    if (reducedMotion || paused) return;
    autoTimer = setTimeout(() => {
      if (paused) return;
      next();
      resetTimer();
    }, INTERVAL_MS);
  }

  function pause() { paused = true; clearTimeout(autoTimer); }
  function resume() { paused = false; resetTimer(); }

  prevBtn?.addEventListener("click", () => { prev(); resetTimer(); });
  nextBtn?.addEventListener("click", () => { next(); resetTimer(); });

  viewport.addEventListener("mouseenter", pause);
  viewport.addEventListener("mouseleave", resume);
  viewport.addEventListener("focusin", pause);
  viewport.addEventListener("focusout", (e) => {
    if (!viewport.contains(e.relatedTarget)) resume();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
    else resume();
  });

  // Keyboard: left/right arrows on the region scroll the carousel.
  viewport.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") { e.preventDefault(); prev(); resetTimer(); }
    if (e.key === "ArrowRight") { e.preventDefault(); next(); resetTimer(); }
  });

  // Throttle dot updates via rAF.
  let raf = false;
  viewport.addEventListener("scroll", () => {
    if (raf) return;
    raf = true;
    requestAnimationFrame(() => { raf = false; updateDots(); });
  });

  updateDots();
  resetTimer();
})();

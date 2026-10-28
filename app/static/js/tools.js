/* Directory filtering and search. */
(function () {
  "use strict";

  const grid = document.querySelector("[data-tool-grid]");
  const search = document.querySelector("[data-tool-search]");
  const empty = document.querySelector("[data-empty-state]");
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll(".tool-card"));
  const chips = Array.from(document.querySelectorAll(".chip[data-category]"));
  let activeCategory = "all";

  function applyFilter() {
    const query = (search?.value || "").trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const category = card.dataset.category;
      const title = card.dataset.title || "";
      const matchesCategory = activeCategory === "all" || category === activeCategory;
      const matchesSearch = !query || title.includes(query);
      const show = matchesCategory && matchesSearch;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => {
        c.classList.toggle("is-active", c === chip);
        c.setAttribute("aria-selected", c === chip ? "true" : "false");
      });
      activeCategory = chip.dataset.category || "all";
      applyFilter();
    });
  });

  search?.addEventListener("input", applyFilter);
  applyFilter();
})();
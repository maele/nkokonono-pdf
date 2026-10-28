(function () {
  "use strict";

  const area = document.querySelector("[data-organise-preview]");
  if (!area) return;

  const uploadArea = document.querySelector(".upload-area");
  const tool = uploadArea?.dataset.tool;
  if (tool !== "organise-pdf") return;

  const gridEl = area.querySelector("[data-organise-grid]");
  const hintEl = area.querySelector("[data-organise-hint]");
  const toolbarEl = area.querySelector("[data-organise-toolbar]");
  const statusEl = area.querySelector("[data-organise-status]");
  const resetBtn = area.querySelector("[data-organise-reset]");

  const state = {
    fileId: null,
    pageCount: 0,
    items: [], // {source, rotation, uid}
  };

  let sortable = null;

  function newUid() {
    return "u" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
  }

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.dataset.state = kind || "";
  }

  function announce() {
    document.body.dataset.organisePages = String(state.items.length);
    document.dispatchEvent(new CustomEvent("nkokonono:organise-updated"));
  }

  function clear() {
    state.fileId = null;
    state.pageCount = 0;
    state.items = [];
    if (gridEl) {
      gridEl.innerHTML = "";
      gridEl.hidden = true;
    }
    if (toolbarEl) toolbarEl.hidden = true;
    if (hintEl) hintEl.hidden = false;
    setStatus("");
    announce();
  }

  function move(uid, delta) {
    const idx = state.items.findIndex((i) => i.uid === uid);
    if (idx < 0) return;
    const target = idx + delta;
    if (target < 0 || target >= state.items.length) return;
    const [item] = state.items.splice(idx, 1);
    state.items.splice(target, 0, item);
    render();
  }

  function renderCard(item) {
    const card = document.createElement("div");
    card.className = "organise-card";
    card.dataset.uid = item.uid;
    card.dataset.source = String(item.source);
    card.dataset.rotation = String(item.rotation);

    const thumb = document.createElement("div");
    thumb.className = "organise-thumb";

    const leftBtn = document.createElement("button");
    leftBtn.type = "button";
    leftBtn.className = "organise-move organise-move-left";
    leftBtn.title = "Move left";
    leftBtn.setAttribute("aria-label", "Move left");
    leftBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';
    leftBtn.addEventListener("click", (e) => { e.stopPropagation(); move(item.uid, -1); });

    const rightBtn = document.createElement("button");
    rightBtn.type = "button";
    rightBtn.className = "organise-move organise-move-right";
    rightBtn.title = "Move right";
    rightBtn.setAttribute("aria-label", "Move right");
    rightBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';
    rightBtn.addEventListener("click", (e) => { e.stopPropagation(); move(item.uid, 1); });

    const img = document.createElement("img");
    img.alt = `Page ${item.source}`;
    img.loading = "lazy";
    img.draggable = false;
    img.src = `/tools/organise-pdf/preview/${encodeURIComponent(state.fileId)}/page-${item.source}.png`;
    img.style.transform = `rotate(${item.rotation}deg)`;

    thumb.append(leftBtn, img, rightBtn);

    const footer = document.createElement("div");
    footer.className = "organise-card-footer";

    const label = document.createElement("span");
    label.className = "organise-page-label";
    label.textContent = `p.${item.source}`;
    footer.appendChild(label);

    const actions = document.createElement("div");
    actions.className = "organise-actions";

    const rotateBtn = document.createElement("button");
    rotateBtn.type = "button";
    rotateBtn.className = "organise-btn";
    rotateBtn.title = "Rotate 90°";
    rotateBtn.setAttribute("aria-label", "Rotate page 90 degrees");
    rotateBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v5h-5"/></svg>';
    rotateBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      item.rotation = (item.rotation + 90) % 360;
      img.style.transform = `rotate(${item.rotation}deg)`;
      card.dataset.rotation = String(item.rotation);
    });

    const dupBtn = document.createElement("button");
    dupBtn.type = "button";
    dupBtn.className = "organise-btn";
    dupBtn.title = "Duplicate";
    dupBtn.setAttribute("aria-label", "Duplicate page");
    dupBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';
    dupBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const copy = { source: item.source, rotation: item.rotation, uid: newUid() };
      const idx = state.items.findIndex((i) => i.uid === item.uid);
      state.items.splice(idx + 1, 0, copy);
      render();
    });

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "organise-btn organise-btn-danger";
    delBtn.title = "Delete";
    delBtn.setAttribute("aria-label", "Delete page");
    delBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>';
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      state.items = state.items.filter((i) => i.uid !== item.uid);
      render();
    });

    actions.append(rotateBtn, dupBtn, delBtn);
    footer.appendChild(actions);

    card.append(thumb, footer);
    return card;
  }

  function render() {
    if (!gridEl) return;
    gridEl.innerHTML = "";
    state.items.forEach((item) => gridEl.appendChild(renderCard(item)));
    gridEl.hidden = state.items.length === 0;
    if (toolbarEl) toolbarEl.hidden = state.items.length === 0;
    if (hintEl) hintEl.hidden = state.items.length > 0;
    setStatus(`${state.items.length} page${state.items.length === 1 ? "" : "s"} in output`);
    announce();
  }

  function syncStateFromDom() {
    if (!gridEl) return;
    const cards = Array.from(gridEl.querySelectorAll("[data-uid]"));
    const byUid = new Map(state.items.map((i) => [i.uid, i]));
    state.items = cards.map((c) => byUid.get(c.dataset.uid)).filter(Boolean);
  }

  function initSortable() {
    if (sortable || !gridEl || !window.Sortable) return;
    sortable = window.Sortable.create(gridEl, {
      animation: 150,
      ghostClass: "organise-ghost",
      chosenClass: "organise-chosen",
      onEnd: () => {
        syncStateFromDom();
        announce();
      },
    });
  }

  async function loadFile(fileId) {
    setStatus("Loading pages…");
    try {
      const r = await fetch(`/tools/organise-pdf/preview/${encodeURIComponent(fileId)}/info`, {
        headers: { "Accept": "application/json" },
      });
      if (!r.ok) throw new Error(`Could not load preview (${r.status}).`);
      const data = await r.json();
      state.fileId = data.file_id;
      state.pageCount = data.page_count;
      state.items = Array.from({ length: data.page_count }, (_, i) => ({
        source: i + 1,
        rotation: 0,
        uid: newUid(),
      }));
      render();
      initSortable();
    } catch (err) {
      setStatus(err.message || "Could not load preview.", "error");
      clear();
    }
  }

  // Listen for upload lifecycle events
  document.addEventListener("nkokonono:file-uploaded", (e) => {
    if (e.detail.tool !== "organise-pdf") return;
    if (state.fileId) return; // only one file at a time for organise
    loadFile(e.detail.id);
  });

  document.addEventListener("nkokonono:file-removed", (e) => {
    if (e.detail.tool !== "organise-pdf") return;
    if (e.detail.id === state.fileId) clear();
  });

  resetBtn?.addEventListener("click", () => {
    if (!state.fileId) return;
    state.items = Array.from({ length: state.pageCount }, (_, i) => ({
      source: i + 1,
      rotation: 0,
      uid: newUid(),
    }));
    render();
    setStatus("Reset to original order.");
  });

  // Expose state for process.js
  window.NkokononoOrganise = {
    getState() {
      return {
        order: state.items.map((i) => i.source),
        rotation_list: state.items.map((i) => i.rotation),
      };
    },
    getFileId() {
      return state.fileId;
    },
  };

  // In case a file was uploaded before this script ran.
  const existing = document.querySelector("[data-file-list] [data-file-id]");
  if (existing && existing.dataset.fileId) {
    loadFile(existing.dataset.fileId);
  } else {
    clear();
  }
})();

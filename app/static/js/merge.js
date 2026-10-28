(function () {
  "use strict";

  const area = document.querySelector("[data-merge-preview]");
  if (!area) return;

  const uploadArea = document.querySelector(".upload-area");
  const tool = uploadArea?.dataset.tool;
  if (tool !== "merge-pdf") return;

  const gridEl = area.querySelector("[data-merge-grid]");
  const hintEl = area.querySelector("[data-merge-hint]");
  const toolbarEl = area.querySelector("[data-merge-toolbar]");
  const statusEl = area.querySelector("[data-merge-status]");
  const resetBtn = area.querySelector("[data-merge-reset]");

  // files: [{file_id, display_name, page_count, letter}]
  // items: [{file_id, source_page, rotation, uid}]
  const state = { files: [], items: [] };
  let sortable = null;
  const infoCache = new Map();

  function newUid() {
    return "m" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || "";
  }

  function announce() {
    document.body.dataset.mergePages = String(state.items.length);
    document.dispatchEvent(new CustomEvent("nkokonono:merge-updated"));
  }

  function fileLetter(fileId) {
    const idx = state.files.findIndex((f) => f.file_id === fileId);
    if (idx < 0) return "?";
    // A..Z then A1, B1, ...
    const n = idx;
    if (n < 26) return String.fromCharCode(65 + n);
    return String.fromCharCode(65 + (n % 26)) + String(Math.floor(n / 26));
  }

  async function fetchInfo(fileId) {
    if (infoCache.has(fileId)) return infoCache.get(fileId);
    const r = await fetch(`/tools/merge-pdf/preview/${encodeURIComponent(fileId)}/info`, {
      headers: { "Accept": "application/json" },
    });
    if (!r.ok) throw new Error(`Preview load failed (${r.status}).`);
    const data = await r.json();
    infoCache.set(fileId, data);
    return data;
  }

  async function addFile(fileId) {
    if (state.files.some((f) => f.file_id === fileId)) return;
    try {
      const info = await fetchInfo(fileId);
      const fileEntry = {
        file_id: fileId,
        display_name: info.display_name,
        page_count: info.page_count,
        letter: "", // computed by fileLetter()
      };
      state.files.push(fileEntry);
      fileEntry.letter = fileLetter(fileId);

      const newItems = Array.from({ length: info.page_count }, (_, i) => ({
        file_id: fileId,
        source_page: i + 1,
        rotation: 0,
        uid: newUid(),
      }));
      state.items.push(...newItems);
      render();
    } catch (err) {
      setStatus(err.message || "Could not load preview.");
    }
  }

  function removeFile(fileId) {
    state.files = state.files.filter((f) => f.file_id !== fileId);
    state.items = state.items.filter((i) => i.file_id !== fileId);
    // Relabel letters
    state.files.forEach((f, i) => {
      f.letter = i < 26
        ? String.fromCharCode(65 + i)
        : String.fromCharCode(65 + (i % 26)) + String(Math.floor(i / 26));
    });
    render();
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
    card.dataset.fileId = item.file_id;
    card.dataset.source = String(item.source_page);
    card.dataset.rotation = String(item.rotation);

    const thumb = document.createElement("div");
    thumb.className = "organise-thumb";

    const badge = document.createElement("span");
    badge.className = "organise-source-badge";
    badge.textContent = fileLetter(item.file_id);
    badge.title = state.files.find((f) => f.file_id === item.file_id)?.display_name || "";
    thumb.appendChild(badge);

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
    img.alt = `Page ${item.source_page}`;
    img.loading = "lazy";
    img.draggable = false;
    img.src = `/tools/merge-pdf/preview/${encodeURIComponent(item.file_id)}/page-${item.source_page}.png`;
    img.style.transform = `rotate(${item.rotation}deg)`;

    thumb.append(leftBtn, img, rightBtn);

    const footer = document.createElement("div");
    footer.className = "organise-card-footer";

    const label = document.createElement("span");
    label.className = "organise-page-label";
    label.textContent = `${fileLetter(item.file_id)}·p${item.source_page}`;
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

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "organise-btn organise-btn-danger";
    delBtn.title = "Remove from merge";
    delBtn.setAttribute("aria-label", "Remove from merge");
    delBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>';
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      state.items = state.items.filter((i) => i.uid !== item.uid);
      render();
    });

    actions.append(rotateBtn, delBtn);
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
    setStatus(`${state.items.length} page${state.items.length === 1 ? "" : "s"} in output from ${state.files.length} file${state.files.length === 1 ? "" : "s"}`);
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
      onEnd: () => { syncStateFromDom(); announce(); },
    });
  }

  document.addEventListener("nkokonono:file-uploaded", (e) => {
    if (e.detail.tool !== "merge-pdf") return;
    initSortable();
    addFile(e.detail.id);
  });

  document.addEventListener("nkokonono:file-removed", (e) => {
    if (e.detail.tool !== "merge-pdf") return;
    removeFile(e.detail.id);
  });

  resetBtn?.addEventListener("click", () => {
    state.items = [];
    state.files.forEach((f) => {
      const pages = Array.from({ length: f.page_count }, (_, i) => ({
        file_id: f.file_id,
        source_page: i + 1,
        rotation: 0,
        uid: newUid(),
      }));
      state.items.push(...pages);
    });
    render();
    setStatus("Reset to all pages in upload order.");
  });

  // Expose state for process.js
  window.NkokononoMerge = {
    getState() {
      return {
        order: state.items.map((i) => ({
          file_id: i.file_id,
          page: i.source_page,
          rotation: i.rotation,
        })),
      };
    },
    getFileCount() { return state.files.length; },
    getPageCount() { return state.items.length; },
  };

  // If files were uploaded before this script ran, load them.
  const existing = Array.from(document.querySelectorAll("[data-file-list] [data-file-id]"));
  if (existing.length) {
    initSortable();
    existing.forEach((el) => addFile(el.dataset.fileId));
  } else {
    render();
  }
})();

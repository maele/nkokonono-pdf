(function () {
  "use strict";
  const area = document.querySelector(".upload-area");
  if (!area) return;
  const accepts = (area.dataset.accepts || "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  const multiple = area.dataset.multiple === "true";
  const endpoint = area.dataset.uploadEndpoint;
  const tool = area.dataset.tool;
  const input = area.querySelector("[data-file-input]");
  const dropzone = area.querySelector("[data-dropzone]");
  const statusEl = area.querySelector("[data-status]");
  const listEl = area.querySelector("[data-file-list]");
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const maxBytes = Number.parseInt(area.dataset.maxUploadBytes, 10) || null;
  const state = { files: [] };

  function setStatus(message, kind) {
    if (!statusEl) return;
    statusEl.textContent = message || "";
    statusEl.dataset.state = kind || "";
  }
  function humanSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  function extOf(name) {
    const i = name.lastIndexOf(".");
    return i >= 0 ? name.slice(i).toLowerCase() : "";
  }
  function clientValidate(file) {
    const ext = extOf(file.name);
    if (accepts.length && !accepts.includes(ext)) return `Unsupported file type. Accepted: ${accepts.join(", ")}.`;
    if (maxBytes && file.size > maxBytes) return "File exceeds the size limit.";
    if (file.size === 0) return "File is empty.";
    return null;
  }
  function emit(name, id) {
    document.dispatchEvent(new CustomEvent(name, { detail: { tool, id } }));
  }
  function makeFileItem(file) {
    const li = document.createElement("li");
    li.className = "file-item";
    li.dataset.state = "ready";
    const meta = document.createElement("div");
    meta.className = "file-meta";
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = file.name;
    const size = document.createElement("span");
    size.className = "file-size";
    size.textContent = humanSize(file.size);
    meta.appendChild(name);
    meta.appendChild(size);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "file-remove";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      const idx = state.files.indexOf(file);
      if (idx >= 0) state.files.splice(idx, 1);
      li.remove();
      setStatus("");
      if (file._internalId) emit("nkokonono:file-removed", file._internalId);
    });

    li.appendChild(meta);
    li.appendChild(remove);
    return li;
  }
  async function uploadFile(file, item) {
    item.dataset.state = "uploading";
    const form = new FormData();
    form.append("files", file, file.name);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        body: form,
        headers: { "X-CSRFToken": csrfToken, "Accept": "application/json" },
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.error?.message || `Upload failed (${response.status}).`);
      const returned = data.files?.[0];
      if (!returned) throw new Error("Upload response did not include a file reference.");
      item.dataset.state = "ready";
      file._internalId = returned.id;
      item.dataset.fileId = returned.id;
      setStatus("Uploaded. Ready to process.", "success");
      emit("nkokonono:file-uploaded", returned.id);
    } catch (err) {
      item.dataset.state = "error";
      setStatus(err.message || "Upload failed.", "error");
      const removeBtn = item.querySelector(".file-remove");
      if (removeBtn) removeBtn.textContent = "Dismiss";
    }
  }
  async function addFiles(incoming) {
    const files = Array.from(incoming || []);
    if (!multiple && files.length + state.files.length > 1) {
      setStatus("This tool accepts a single file.", "error");
      return;
    }
    setStatus("");
    for (const file of files) {
      const problem = clientValidate(file);
      if (problem) { setStatus(problem, "error"); continue; }
      state.files.push(file);
      const item = makeFileItem(file);
      listEl.appendChild(item);
      await uploadFile(file, item);
    }
  }
  input?.addEventListener("change", (event) => { addFiles(event.target.files); event.target.value = ""; });
  if (dropzone) {
    ["dragenter", "dragover"].forEach((n) => dropzone.addEventListener(n, (e) => { e.preventDefault(); dropzone.classList.add("is-dragging"); }));
    ["dragleave", "drop"].forEach((n) => dropzone.addEventListener(n, () => dropzone.classList.remove("is-dragging")));
    dropzone.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer) addFiles(e.dataTransfer.files); });
  }
})();
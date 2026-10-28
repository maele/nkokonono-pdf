(function () {
  "use strict";
  const area = document.querySelector(".upload-area");
  if (!area) return;

  const tool = area.dataset.tool;
  const processBtn = document.querySelector("[data-process-btn]");
  const statusEl = document.querySelector("[data-process-status]");
  const downloadEl = document.querySelector("[data-download-area]");
  const optionsEl = document.querySelector("[data-options]");
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const fileIds = [];

  const MIN_FILES = { "merge-pdf": 2, "compare-pdf": 2 };
  const minFiles = MIN_FILES[tool] || 1;

  function updateButton() {
    if (!processBtn) return;
    if (tool === "organise-pdf") {
      const pages = Number(document.body.dataset.organisePages || 0);
      processBtn.disabled = pages < 1;
      return;
    }
    if (tool === "merge-pdf") {
      const pages = Number(document.body.dataset.mergePages || 0);
      processBtn.disabled = (fileIds.length < 2) || (pages < 2);
      return;
    }
    processBtn.disabled = fileIds.length < minFiles;
  }

  document.addEventListener("nkokonono:organise-updated", () => {
    if (tool === "organise-pdf") updateButton();
  });
  document.addEventListener("nkokonono:merge-updated", () => {
    if (tool === "merge-pdf") updateButton();
  });

  document.addEventListener("nkokonono:file-uploaded", (e) => {
    if (e.detail.tool !== tool) return;
    if (!fileIds.includes(e.detail.id)) fileIds.push(e.detail.id);
    updateButton();
  });

  document.addEventListener("nkokonono:file-removed", (e) => {
    if (e.detail.tool !== tool) return;
    const idx = fileIds.indexOf(e.detail.id);
    if (idx >= 0) fileIds.splice(idx, 1);
    updateButton();
  });

  function collectOptions() {
    if (!optionsEl) return {};
    const options = {};
    optionsEl.querySelectorAll('input[type="radio"]:checked').forEach((el) => { options[el.name] = el.value; });
    optionsEl.querySelectorAll('input[type="checkbox"]').forEach((el) => { options[el.name] = el.checked; });
    optionsEl.querySelectorAll('input[type="text"], input[type="password"], select').forEach((el) => {
      const v = el.value;
      if (v === "") return;
      if (el.name === "angle" || el.name === "dpi") options[el.name] = Number(v);
      else options[el.name] = v;
    });
    // organise-pdf: page order and per-output-page rotation come from the
    // interactive preview, not from a form field.
    if (tool === "organise-pdf" && window.NkokononoOrganise) {
      const state = window.NkokononoOrganise.getState();
      options.order = state.order;
      options.rotation_list = state.rotation_list;
    }
    // merge-pdf: page-level order across multiple files.
    if (tool === "merge-pdf" && window.NkokononoMerge) {
      const state = window.NkokononoMerge.getState();
      options.order = state.order;
    }
    return options;
  }

  function showResult(job) {
    if (!downloadEl) return;
    downloadEl.innerHTML = "";
    downloadEl.hidden = true;
    if (job.status === "completed") {
      const note = job.outputs && job.outputs[0] && job.outputs[0].notes;
      statusEl.textContent = note ? `Done. ${note}` : "Done. Your file is ready.";
      statusEl.dataset.state = "success";
      const a = document.createElement("a");
      a.href = `/api/jobs/${job.id}/download`;
      a.className = "inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700";
      a.textContent = "Download result";
      downloadEl.appendChild(a);
      downloadEl.hidden = false;
      processBtn.disabled = false;
    } else {
      const message = job?.error?.message || "Processing failed.";
      statusEl.textContent = message;
      statusEl.dataset.state = "error";
      processBtn.disabled = false;
    }
  }

  processBtn?.addEventListener("click", async () => {
    processBtn.disabled = true;
    if (downloadEl) { downloadEl.innerHTML = ""; downloadEl.hidden = true; }
    statusEl.textContent = "Processing…";
    statusEl.dataset.state = "processing";

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
          "Accept": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({ tool, file_ids: fileIds.slice(), options: collectOptions() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = data?.error?.message || `Request failed (${response.status}).`;
        throw new Error(message);
      }
      showResult(data);
    } catch (err) {
      statusEl.textContent = err.message || "Processing failed.";
      statusEl.dataset.state = "error";
      processBtn.disabled = false;
    }
  });
})();
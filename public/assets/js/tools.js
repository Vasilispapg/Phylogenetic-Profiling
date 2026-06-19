// Shared helpers for the tool pages. Pages opt in; nothing runs on its own.
window.Phylo = (function () {
  function humanSize(bytes) {
    if (!bytes && bytes !== 0) return "";
    const u = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < u.length - 1) { bytes /= 1024; i++; }
    return `${bytes.toFixed(i ? 1 : 0)} ${u[i]}`;
  }

  // Wire a drag-and-drop zone around a hidden <input type=file>.
  // opts: { zone, input, pill, onFile? }
  function dropzone(opts) {
    const { zone, input, pill, onFile } = opts;
    if (!zone || !input) return;

    const show = () => {
      const f = input.files[0];
      if (f && pill) {
        pill.innerHTML =
          `<i class="fas fa-file"></i> ${f.name} <span style="opacity:.6">(${humanSize(f.size)})</span>`;
        pill.style.display = "inline-flex";
      }
      if (f && onFile) onFile(f);
    };

    zone.addEventListener("click", () => input.click());
    input.addEventListener("change", show);
    ["dragenter", "dragover"].forEach((e) =>
      zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.add("is-dragover"); })
    );
    ["dragleave", "drop"].forEach((e) =>
      zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.remove("is-dragover"); })
    );
    zone.addEventListener("drop", (ev) => {
      if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; show(); }
    });
  }

  // Set a themed status banner. kind: info | error | success.
  function status(el, message, kind, withProgress) {
    if (!el) return;
    el.className = `tool-status show is-${kind || "info"}`;
    el.innerHTML = message + (withProgress ? '<div class="tool-progress"><span></span></div>' : "");
  }
  function clearStatus(el) { if (el) el.className = "tool-status"; }

  // Upload one file (plus optional extra fields) to url; resolves the JSON body.
  async function upload(url, file, fields) {
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(fields || {}).forEach(([k, v]) => fd.append(k, v));
    const r = await fetch(url, { method: "POST", body: fd });
    return r.json();
  }

  // Generic poller. opts: { url, interval=2500, isDone, isFailed, onTick }
  // Resolves with the final JSON on done; rejects on failure/404.
  function poll(opts) {
    const { url, interval = 2500, isDone, isFailed, onTick } = opts;
    return new Promise((resolve, reject) => {
      const id = setInterval(async () => {
        try {
          const r = await fetch(typeof url === "function" ? url() : url);
          if (r.status === 404) { clearInterval(id); return reject(new Error("not found")); }
          const data = await r.json();
          if (onTick) onTick(data);
          if (isDone(data)) { clearInterval(id); resolve(data); }
          else if (isFailed && isFailed(data)) { clearInterval(id); reject(new Error(data.message || "failed")); }
        } catch (e) { clearInterval(id); reject(e); }
      }, interval);
    });
  }

  return { dropzone, status, clearStatus, upload, poll, humanSize };
})();

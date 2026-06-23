// Thin client for the Flask JSON API (proxied in dev via vite.config.js).
export async function uploadFile(url, file, fields = {}) {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  const r = await fetch(url, { method: "POST", body: fd });
  return r.json();
}

export async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function getJSON(url) {
  const r = await fetch(url);
  return { status: r.status, body: await r.json() };
}

// Generic poller. opts: { interval, isDone, isFailed, onTick }
export function poll(urlFn, { interval = 2500, isDone, isFailed, onTick } = {}) {
  return new Promise((resolve, reject) => {
    const id = setInterval(async () => {
      try {
        const res = await fetch(typeof urlFn === "function" ? urlFn() : urlFn);
        if (res.status === 404) { clearInterval(id); return reject(new Error("Job not found")); }
        const data = await res.json();
        onTick && onTick(data);
        if (isDone(data)) { clearInterval(id); resolve(data); }
        else if (isFailed && isFailed(data)) { clearInterval(id); reject(new Error(data.message || "failed")); }
      } catch (e) { clearInterval(id); reject(e); }
    }, interval);
  });
}

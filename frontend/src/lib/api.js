// Thin client for the Flask JSON API (proxied in dev via vite.config.js).

// Parse a response as JSON, turning the common failure modes into clear errors
// instead of the cryptic "Unexpected end of JSON input" you get from res.json()
// on an empty body (which usually means the Flask backend isn't reachable).
async function asJSON(r, what = "the server") {
  const text = await r.text();
  if (!text) {
    if (!r.ok) {
      throw new Error(
        `Can't reach the analysis server (HTTP ${r.status}). ` +
        `Is the Flask backend running on :8000?  Start both servers with ./dev.sh`
      );
    }
    throw new Error(`Empty response from ${what}.`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid (non-JSON) response from ${what} (HTTP ${r.status}).`);
  }
}

export async function uploadFile(url, file, fields = {}) {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  const r = await fetch(url, { method: "POST", body: fd });
  return asJSON(r, "upload");
}

export async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return asJSON(r, "the server");
}

export async function getJSON(url) {
  const r = await fetch(url);
  return { status: r.status, body: await asJSON(r, "the server") };
}

// Generic poller. opts: { interval, isDone, isFailed, onTick }
export function poll(urlFn, { interval = 2500, isDone, isFailed, onTick } = {}) {
  return new Promise((resolve, reject) => {
    const id = setInterval(async () => {
      try {
        const res = await fetch(typeof urlFn === "function" ? urlFn() : urlFn);
        if (res.status === 404) { clearInterval(id); return reject(new Error("Job not found")); }
        const data = await asJSON(res, "status endpoint");
        onTick && onTick(data);
        if (isDone(data)) { clearInterval(id); resolve(data); }
        else if (isFailed && isFailed(data)) { clearInterval(id); reject(new Error(data.message || "failed")); }
      } catch (e) { clearInterval(id); reject(e); }
    }, interval);
  });
}

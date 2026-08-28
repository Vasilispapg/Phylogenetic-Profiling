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

// Generic poller.
//
// setTimeout-chained rather than setInterval: a slow response must not stack up
// overlapping requests. A single transient network error no longer kills a job
// that is still running on the server -- it takes `maxErrors` in a row, with
// backoff -- and the whole thing gives up after `timeout` instead of polling
// forever when a job is stuck.
export function poll(urlFn, {
  interval = 2500,
  timeout = 30 * 60 * 1000,
  maxErrors = 3,
  isDone,
  isFailed,
  onTick,
} = {}) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();
    let errors = 0;

    const tick = async () => {
      if (Date.now() - startedAt > timeout) {
        return reject(new Error("Timed out waiting for the job. It may still be running on the server."));
      }
      try {
        const res = await fetch(typeof urlFn === "function" ? urlFn() : urlFn);
        if (res.status === 404) return reject(new Error("Job not found"));
        const data = await asJSON(res, "status endpoint");
        errors = 0;
        onTick && onTick(data);
        if (isDone(data)) return resolve(data);
        if (isFailed && isFailed(data)) return reject(new Error(data.message || "failed"));
      } catch (e) {
        if (++errors >= maxErrors) return reject(e);
      }
      setTimeout(tick, interval * 2 ** errors);
    };

    setTimeout(tick, interval);
  });
}

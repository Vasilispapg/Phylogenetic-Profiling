import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { parseMatrix, lbl } from "../lib/matrix.js";
import { postJSON } from "../lib/api.js";

const L = { display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" };
const cc = (l) => `hsl(${(l * 47) % 360},66%,55%)`;

export default function Embedding() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [feat, setFeat] = useState(null);
  const [axis, setAxis] = useState("domains");
  const [method, setMethod] = useState("pca");
  const [k, setK] = useState(8);
  const [emb, setEmb] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState(null);
  const ref = useRef(null);

  const onFile = (f) => {
    setFile(f); setStatus({ kind: "info", msg: "Reading CSV…", progress: true }); setEmb(null);
    const reader = new FileReader();
    reader.onload = () => {
      try { const d = parseMatrix(String(reader.result)); setData(d); setFeat(d.features[0]); setSel(null); setStatus(null); }
      catch { setStatus({ kind: "error", msg: "Could not parse the CSV." }); }
    };
    reader.readAsText(f);
  };

  // Compute the embedding on the backend (PCA / t-SNE + KMeans) on any param change.
  useEffect(() => {
    if (!data || !feat) return;
    let alive = true;
    setBusy(true); setEmb(null); setSel(null);
    setStatus({ kind: "info", msg: `Projecting ${axis} with ${method.toUpperCase()}…`, progress: true });
    postJSON("/embedding", { z: data.data[feat], axis, method, k })
      .then((r) => {
        if (!alive) return;
        if (r.status !== "success") { setStatus({ kind: "error", msg: r.message || "Embedding failed." }); setBusy(false); return; }
        setEmb(r); setBusy(false); setStatus(null);
      })
      .catch((e) => { if (!alive) return; setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); setBusy(false); });
    return () => { alive = false; };
  }, [data, feat, axis, method, k]);

  // Scatter, one trace per cluster (discrete colours + legend).
  useEffect(() => {
    if (!data || !emb || !ref.current) return;
    const names = axis === "domains" ? data.cols : data.rows;
    const groups = {};
    emb.labels.forEach((l, i) => { (groups[l] = groups[l] || []).push(i); });
    const traces = Object.entries(groups).map(([l, idxs]) => ({
      x: idxs.map((i) => emb.coords[i][0]), y: idxs.map((i) => emb.coords[i][1]),
      text: idxs.map((i) => names[i]), customdata: idxs.map((i) => i),
      name: `cluster ${l}`, type: "scattergl", mode: "markers",
      marker: { size: 8, color: cc(+l), line: { width: 0.5, color: "rgba(255,255,255,.7)" } },
      hovertemplate: `%{text}<extra>cluster ${l}</extra>`,
    }));
    Plotly.react(ref.current, traces, {
      autosize: true, height: 660, margin: { l: 36, r: 10, t: 10, b: 36 },
      xaxis: { zeroline: false, showgrid: true, gridcolor: "rgba(18,28,54,.06)", title: { text: method === "pca" ? "PC1" : "dim 1" } },
      yaxis: { zeroline: false, showgrid: true, gridcolor: "rgba(18,28,54,.06)", title: { text: method === "pca" ? "PC2" : "dim 2" }, scaleanchor: "x", scaleratio: 1 },
      legend: { orientation: "v", x: 1.01, y: 1, font: { size: 10 } },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    }, { responsive: true, displaylogo: false, toImageButtonOptions: { filename: "phyloflask-embedding", scale: 2 } });
    const div = ref.current;
    if (div.removeAllListeners) div.removeAllListeners("plotly_click");
    div.on("plotly_click", (e) => {
      const pt = e.points[0]; if (!pt) return;
      setSel({ name: pt.text, cluster: pt.fullData.name.replace("cluster ", "") });
    });
    return () => { try { Plotly.purge(div); } catch { /* noop */ } };
  }, [data, emb, axis, method]);

  const npoints = axis === "domains" ? (data ? data.cols.length : 0) : (data ? data.rows.length : 0);

  return (
    <div className="fade-up" style={{ maxWidth: 1120, margin: "0 auto" }}>
      <h1>Embedding map</h1>
      <p className="muted">Project each <strong>domain</strong> (or species) into 2D by its <strong>co-occurrence profile</strong>:
         points that appear in the same genomes land close together. Coloured by a <strong>KMeans</strong> grouping of the
         profiles — a fast bird's-eye view of which domains travel together. PCA (linear) or t-SNE (non-linear).</p>

      {!data && <>
        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · correlation_matrix.csv / feature_matrix.csv" file={file} onFile={onFile} />
        <Status s={status} />
      </>}

      {data && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "8px 0 12px" }}>
          <label style={L}>Embed
            <select className="select" style={{ width: "auto" }} value={axis} onChange={(e) => setAxis(e.target.value)}>
              <option value="domains">Domains</option><option value="species">Species</option>
            </select></label>
          <label style={L}>Method
            <select className="select" style={{ width: "auto" }} value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="pca">PCA (fast, linear)</option><option value="tsne">t-SNE (clusters)</option>
            </select></label>
          <label style={L}>Groups (k)
            <select className="select" style={{ width: "auto" }} value={k} onChange={(e) => setK(+e.target.value)}>
              {[4, 6, 8, 10, 12, 16].map((v) => <option key={v} value={v}>{v}</option>)}
            </select></label>
          {data.kind === "feature" && <label style={L}>Metric
            <select className="select" style={{ width: "auto" }} value={feat} onChange={(e) => setFeat(e.target.value)}>
              {data.features.map((f) => <option key={f} value={f}>{lbl(f)}</option>)}
            </select></label>}
          <button className="btn btn-secondary" onClick={() => { setData(null); setFile(null); setEmb(null); setSel(null); }}>Load another</button>
        </div>

        <div style={{ fontSize: ".82rem", color: "var(--text-2)", marginBottom: 8 }}>
          <strong>{npoints}</strong> {axis} projected{emb ? ` · ${emb.n_clusters} groups` : ""}{busy ? " · computing…" : ""}
          {sel && <> · selected <strong style={{ wordBreak: "break-all" }}>{sel.name}</strong> (cluster {sel.cluster})</>}
        </div>

        {busy && <Status s={status} />}
        <div ref={ref} style={{ width: "100%", minHeight: 200, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
      </>}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { parseMatrix, transform, COLORSCALES, lbl } from "../lib/matrix.js";
import { postJSON } from "../lib/api.js";

const L = { display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" };

export default function Clustergram() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [feat, setFeat] = useState(null);
  const [scale, setScale] = useState("Viridis");
  const [norm, setNorm] = useState("none");
  const [log, setLog] = useState(false);
  const [clu, setClu] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState(null);
  const ref = useRef(null);

  const onFile = (f) => {
    setFile(f); setStatus({ kind: "info", msg: "Reading CSV…", progress: true }); setClu(null);
    const reader = new FileReader();
    reader.onload = () => {
      try { const d = parseMatrix(String(reader.result)); setData(d); setFeat(d.features[0]); setSel(null); setStatus(null); }
      catch { setStatus({ kind: "error", msg: "Could not parse the CSV." }); }
    };
    reader.readAsText(f);
  };

  // Cluster (backend scipy: correlation distance + average linkage) per dataset/metric.
  useEffect(() => {
    if (!data || !feat) return;
    let alive = true;
    setBusy(true); setClu(null);
    setStatus({ kind: "info", msg: "Clustering rows & columns…", progress: true });
    postJSON("/clustergram", { z: data.data[feat] })
      .then((r) => {
        if (!alive) return;
        if (r.status !== "success") { setStatus({ kind: "error", msg: r.message || "Clustering failed." }); setBusy(false); return; }
        setClu(r); setBusy(false); setStatus(null);
      })
      .catch((e) => { if (!alive) return; setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); setBusy(false); });
    return () => { alive = false; };
  }, [data, feat]);

  // Render clustergram (heatmap + two dendrograms) on clustering / display changes.
  useEffect(() => {
    if (!data || !feat || !clu || !ref.current) return;
    const { rows, cols } = data;
    const ro = clu.row_order, co = clu.col_order;
    const t = transform(data.data[feat], cols, { norm, log });
    const z = ro.map((i) => co.map((j) => t[i][j]));
    const text = ro.map((i) => co.map((j) => `${rows[i]}<br>${cols[j]}`));
    const colpos = co.map((_, j) => 10 * j + 5), rowpos = ro.map((_, i) => 10 * i + 5);

    // scipy gives links along a leaf axis (icoord, leaves at 5,15,25…) and a height
    // axis (dcoord). swap=true puts the height on x (left row dendrogram).
    const dendro = (coords, xaxis, yaxis, swap) => {
      const xs = [], ys = [];
      (coords.icoord || []).forEach((seg, k) => {
        const dc = coords.dcoord[k];
        (swap ? dc : seg).forEach((v) => xs.push(v)); xs.push(null);
        (swap ? seg : dc).forEach((v) => ys.push(v)); ys.push(null);
      });
      return { x: xs, y: ys, xaxis, yaxis, type: "scatter", mode: "lines", line: { color: "#9aa4b8", width: 1 }, hoverinfo: "skip", showlegend: false };
    };

    const traces = [
      { z, x: colpos, y: rowpos, text, type: "heatmap", colorscale: scale, xaxis: "x", yaxis: "y",
        colorbar: { thickness: 11, len: 0.84, y: 0.42 }, hovertemplate: `%{text}<br>${lbl(feat)}: %{z}<extra></extra>` },
      dendro(clu.col_dendro, "x", "y2", false),
      dendro(clu.row_dendro, "x2", "y", true),
    ];
    const layout = {
      autosize: true, height: 820, margin: { l: 8, r: 8, t: 8, b: 56 },
      xaxis: { domain: [0.14, 1], showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      yaxis: { domain: [0, 0.86], showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      yaxis2: { domain: [0.875, 1], anchor: "x", showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      xaxis2: { domain: [0, 0.12], anchor: "y", autorange: "reversed", showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", showlegend: false,
    };
    Plotly.react(ref.current, traces, layout, { responsive: true, displaylogo: false, toImageButtonOptions: { filename: "phyloflask-clustergram", scale: 2 } });

    const div = ref.current;
    if (div.removeAllListeners) div.removeAllListeners("plotly_click");
    div.on("plotly_click", (e) => {
      const pt = e.points[0]; if (!pt || pt.data.type !== "heatmap") return;
      const j = Math.round((pt.x - 5) / 10), i = Math.round((pt.y - 5) / 10);
      const oi = ro[i], oj = co[j]; if (oi == null || oj == null) return;
      const vals = {}; data.features.forEach((f) => (vals[f] = data.data[f][oi][oj]));
      setSel({ species: rows[oi], domain: cols[oj], vals });
    });
    return () => { try { Plotly.purge(div); } catch { /* noop */ } };
  }, [data, feat, clu, scale, norm, log]);

  return (
    <div className="fade-up" style={{ maxWidth: 1120, margin: "0 auto" }}>
      <h1>Clustergram</h1>
      <p className="muted">A <strong>hierarchically-clustered heatmap</strong>: species (rows) and domains (columns) are
         reordered by profile similarity (correlation distance, average linkage) so <strong>co-evolving domain modules</strong>
         and <strong>species groups</strong> emerge as blocks. Dendrograms top &amp; left; click a cell to inspect it.</p>

      {!data && <>
        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · correlation_matrix.csv / feature_matrix.csv" file={file} onFile={onFile} />
        <Status s={status} />
      </>}

      {data && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "8px 0 12px" }}>
          {data.kind === "feature" && <label style={L}>Metric
            <select className="select" style={{ width: "auto" }} value={feat} onChange={(e) => setFeat(e.target.value)}>
              {data.features.map((f) => <option key={f} value={f}>{lbl(f)}</option>)}
            </select></label>}
          <label style={L}>Colour
            <select className="select" style={{ width: "auto" }} value={scale} onChange={(e) => setScale(e.target.value)}>
              {COLORSCALES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label style={L}>Normalize
            <select className="select" style={{ width: "auto" }} value={norm} onChange={(e) => setNorm(e.target.value)}>
              <option value="none">None</option><option value="row">Per species (row)</option><option value="col">Per domain (col)</option>
            </select></label>
          <label style={L}><input type="checkbox" checked={log} onChange={(e) => setLog(e.target.checked)} /> Log</label>
          <button className="btn btn-secondary" onClick={() => { setData(null); setFile(null); setClu(null); setSel(null); }}>Load another</button>
        </div>

        <div style={{ fontSize: ".82rem", color: "var(--text-2)", marginBottom: 8 }}>
          <strong>{data.rows.length}</strong> species × <strong>{data.cols.length}</strong> domains
          {busy ? " · clustering…" : clu ? " · clustered · click a cell to inspect" : ""}
        </div>

        {busy && <Status s={status} />}
        <div ref={ref} style={{ width: "100%", minHeight: 200, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />

        {sel && <div className="card card-pad" style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <strong>Cell detail</strong>
            <button className="btn btn-secondary" style={{ padding: "4px 11px" }} onClick={() => setSel(null)}>✕</button>
          </div>
          <div style={{ fontSize: ".85rem", wordBreak: "break-all", marginBottom: 10 }}>
            <span className="muted">species</span> {sel.species} &nbsp;·&nbsp; <span className="muted">domain</span> {sel.domain}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 8 }}>
            {Object.entries(sel.vals).map(([k, v]) => (
              <div key={k} style={{ background: "var(--surface-2)", borderRadius: 8, padding: "8px 10px" }}>
                <div className="muted" style={{ fontSize: ".72rem" }}>{lbl(k)}</div>
                <div style={{ fontWeight: 700 }}>{typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(3)) : v}</div>
              </div>
            ))}
          </div>
        </div>}
      </>}
    </div>
  );
}

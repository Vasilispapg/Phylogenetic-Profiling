import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { parseMatrix, computeOrder, transform, COLORSCALES, lbl } from "../lib/matrix.js";

const L = { display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" };

export default function Heatmap() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [feat, setFeat] = useState(null);
  const [featB, setFeatB] = useState(null);
  const [compare, setCompare] = useState(false);
  const [order, setOrder] = useState("total");
  const [norm, setNorm] = useState("none");
  const [log, setLog] = useState(false);
  const [scale, setScale] = useState("Viridis");
  const [sel, setSel] = useState(null);
  const ref = useRef(null);

  const onFile = (f) => {
    setFile(f); setStatus({ kind: "info", msg: "Reading CSV…", progress: true });
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const d = parseMatrix(String(reader.result));
        setData(d); setFeat(d.features[0]); setFeatB(d.features[1] || d.features[0]);
        setCompare(false); setSel(null); setStatus(null);
      } catch { setStatus({ kind: "error", msg: "Could not parse the CSV." }); }
    };
    reader.readAsText(f);
  };

  useEffect(() => {
    if (!data || !feat || !ref.current) return;
    const { rows, cols } = data;
    const { ri, ci } = computeOrder(data.data[feat], rows, cols, order);
    const x = ci.map((j) => cols[j]), y = ri.map((i) => rows[i]);
    const za = (() => { const t = transform(data.data[feat], cols, { norm, log }); return ri.map((i) => ci.map((j) => t[i][j])); })();

    let traces, layout;
    const dual = compare && featB && data.kind === "feature";
    if (dual) {
      const t2 = transform(data.data[featB], cols, { norm, log });
      const zb = ri.map((i) => ci.map((j) => t2[i][j]));
      traces = [
        { z: za, x, y, type: "heatmap", colorscale: scale, xaxis: "x", yaxis: "y",
          colorbar: { x: 0.45, thickness: 10, len: 1 }, hovertemplate: `%{y} · %{x}<br>${lbl(feat)}: %{z}<extra></extra>` },
        { z: zb, x, y, type: "heatmap", colorscale: scale, xaxis: "x2", yaxis: "y",
          colorbar: { x: 1.0, thickness: 10, len: 1 }, hovertemplate: `%{y} · %{x}<br>${lbl(featB)}: %{z}<extra></extra>` },
      ];
      layout = {
        autosize: true, height: 780, margin: { l: 130, r: 50, t: 32, b: 90 },
        xaxis: { domain: [0, 0.42], automargin: true, anchor: "y" },
        xaxis2: { domain: [0.58, 0.95], automargin: true, anchor: "y" },
        yaxis: { automargin: true },
        annotations: [
          { text: lbl(feat), x: 0.21, y: 1.04, xref: "paper", yref: "paper", showarrow: false, font: { size: 13 } },
          { text: lbl(featB), x: 0.76, y: 1.04, xref: "paper", yref: "paper", showarrow: false, font: { size: 13 } },
        ],
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      };
    } else {
      traces = [{ z: za, x, y, type: "heatmap", colorscale: scale, colorbar: { thickness: 12 },
                  hovertemplate: `%{y} · %{x}<br>${lbl(feat)}: %{z}<extra></extra>` }];
      layout = { autosize: true, height: 780, margin: { l: 130, r: 10, t: 10, b: 90 },
                 xaxis: { automargin: true }, yaxis: { automargin: true },
                 paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)" };
    }

    Plotly.react(ref.current, traces, layout, { responsive: true, displaylogo: false, toImageButtonOptions: { filename: "phyloflask-heatmap", scale: 2 } });

    const div = ref.current;
    if (div.removeAllListeners) div.removeAllListeners("plotly_click");
    div.on("plotly_click", (e) => {
      const pt = e.points[0]; if (!pt) return;
      const i0 = rows.indexOf(pt.y), j0 = cols.indexOf(pt.x); if (i0 < 0 || j0 < 0) return;
      const vals = {}; data.features.forEach((f) => (vals[f] = data.data[f][i0][j0]));
      setSel({ species: pt.y, domain: pt.x, vals });
    });
    return () => { try { Plotly.purge(div); } catch { /* noop */ } };
  }, [data, feat, featB, compare, order, norm, log, scale]);

  return (
    <div className="fade-up" style={{ maxWidth: 1100, margin: "0 auto" }}>
      <h1>Heatmaps</h1>
      <p className="muted">Upload a <strong>correlation matrix</strong> (presence/absence) or a <strong>feature matrix</strong>
         (rich per-cell BLAST metrics). Feature matrices unlock a <strong>metric selector</strong>, a
         <strong> compare-two-metrics</strong> view, and a <strong>click-to-inspect</strong> cell panel. Box-zoom, hover, export PNG.</p>

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
          {data.kind === "feature" && <label style={L} title="Show two metrics side by side on the same grid">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} /> Compare two</label>}
          {data.kind === "feature" && compare && <label style={L}>vs
            <select className="select" style={{ width: "auto" }} value={featB} onChange={(e) => setFeatB(e.target.value)}>
              {data.features.map((f) => <option key={f} value={f}>{lbl(f)}</option>)}
            </select></label>}
          <label style={L}>Colour
            <select className="select" style={{ width: "auto" }} value={scale} onChange={(e) => setScale(e.target.value)}>
              {COLORSCALES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label style={L}>Order
            <select className="select" style={{ width: "auto" }} value={order} onChange={(e) => setOrder(e.target.value)}>
              <option value="total">By total (group similar)</option><option value="alpha">Alphabetical</option>
            </select></label>
          <label style={L}>Normalize
            <select className="select" style={{ width: "auto" }} value={norm} onChange={(e) => setNorm(e.target.value)}>
              <option value="none">None</option><option value="row">Per species (row)</option><option value="col">Per domain (col)</option>
            </select></label>
          <label style={L}><input type="checkbox" checked={log} onChange={(e) => setLog(e.target.checked)} /> Log</label>
          <button className="btn btn-secondary" onClick={() => { setData(null); setFile(null); setSel(null); }}>Load another</button>
        </div>

        <div style={{ fontSize: ".82rem", color: "var(--text-2)", marginBottom: 8 }}>
          <strong>{data.rows.length}</strong> species × <strong>{data.cols.length}</strong> domains
          {data.kind === "feature" && <> · <strong>{data.features.length}</strong> metrics per cell · <strong>click a cell</strong> to inspect all metrics</>}
        </div>

        <div ref={ref} style={{ width: "100%", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />

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

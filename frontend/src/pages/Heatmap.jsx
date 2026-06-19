import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";

function parseMatrix(text) {
  const lines = text.trim().split(/\r?\n/);
  const cols = lines[0].split(",").slice(1);
  const rows = [], z = [];
  for (let i = 1; i < lines.length; i++) {
    const p = lines[i].split(",");
    rows.push(p[0]);
    z.push(p.slice(1).map((v) => Number(v) || 0));
  }
  return { rows, cols, z };
}

export default function Heatmap() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [order, setOrder] = useState("total");
  const [log, setLog] = useState(true);
  const ref = useRef(null);

  const onFile = (f) => {
    setFile(f); setStatus({ kind: "info", msg: "Reading CSV…", progress: true });
    const reader = new FileReader();
    reader.onload = () => {
      try { const d = parseMatrix(String(reader.result)); setData(d); setStatus(null); }
      catch { setStatus({ kind: "error", msg: "Could not parse the CSV." }); }
    };
    reader.readAsText(f);
  };

  useEffect(() => {
    if (!data || !ref.current) return;
    const { rows, cols } = data;
    let zz = data.z.map((r) => r.map((v) => (log ? (v > 0 ? Math.log1p(v) : 0) : v)));
    let ri = rows.map((_, i) => i), ci = cols.map((_, i) => i);
    if (order === "alpha") {
      ri.sort((a, b) => rows[a].localeCompare(rows[b]));
      ci.sort((a, b) => cols[a].localeCompare(cols[b]));
    } else {
      const rs = zz.map((r) => r.reduce((s, v) => s + v, 0));
      const cs = cols.map((_, c) => zz.reduce((s, r) => s + r[c], 0));
      ri.sort((a, b) => rs[b] - rs[a]); ci.sort((a, b) => cs[b] - cs[a]);
    }
    const z = ri.map((i) => ci.map((j) => zz[i][j]));
    Plotly.newPlot(ref.current, [{
      z, x: ci.map((j) => cols[j]), y: ri.map((i) => rows[i]), type: "heatmap", colorscale: "YlGnBu",
      hovertemplate: "%{y} · %{x}: %{z}<extra></extra>",
    }], {
      autosize: true, height: 760, margin: { l: 120, r: 10, t: 10, b: 90 },
      xaxis: { automargin: true }, yaxis: { automargin: true }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    }, { responsive: true, displaylogo: false, toImageButtonOptions: { filename: "heatmap", scale: 2 } });
    return () => { try { Plotly.purge(ref.current); } catch {} };
  }, [data, order, log]);

  return (
    <div className="fade-up" style={{ maxWidth: 1040, margin: "0 auto" }}>
      <h1>Heatmap</h1>
      <p className="muted">Upload a numeric matrix CSV (rows = species, columns = domains) to render an interactive heatmap
         — box-zoom, hover, download a PNG.</p>

      {!data && <>
        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · numeric matrix .csv" file={file} onFile={onFile} />
        <Status s={status} />
      </>}

      {data && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "8px 0 12px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" }}>Order
            <select className="select" style={{ width: "auto" }} value={order} onChange={(e) => setOrder(e.target.value)}>
              <option value="total">By total (group similar)</option><option value="alpha">Alphabetical</option>
            </select></label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" }}>
            <input type="checkbox" checked={log} onChange={(e) => setLog(e.target.checked)} /> Log scale</label>
          <button className="btn btn-secondary" onClick={() => { setData(null); setFile(null); }}>Load another</button>
        </div>
        <div ref={ref} style={{ width: "100%", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
      </>}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { parseMatrix, transform } from "../lib/matrix.js";
import { postJSON, uploadFile, poll, getJSON } from "../lib/api.js";

cytoscape.use(fcose);
const cc = (c) => (c == null ? "#94a3b8" : `hsl(${(c * 47) % 360},66%,55%)`);

export default function Explorer() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [clu, setClu] = useState(null);
  const [net, setNet] = useState(null);
  const [sel, setSel] = useState(null);     // selected domain name (shared across views)
  const hmRef = useRef(null), netRef = useRef(null), cyRef = useRef(null);
  const colNamesRef = useRef([]);

  const run = async () => {
    if (!file) return setStatus({ kind: "error", msg: "Choose a correlation matrix CSV." });
    setData(null); setClu(null); setNet(null); setSel(null);
    let d;
    try { setStatus({ kind: "info", msg: "Reading CSV…", progress: true }); d = parseMatrix(await file.text()); setData(d); }
    catch { return setStatus({ kind: "error", msg: "Could not parse the CSV." }); }
    try {
      setStatus({ kind: "info", msg: "Clustering rows/cols + building the domain network…", progress: true });
      const cluP = postJSON("/clustergram", { z: d.data[d.features[0]] });
      const netP = (async () => {
        const up = await uploadFile("/tools/allvsall", file);
        if (up.status !== "success") throw new Error(up.message || "upload failed");
        const fn = up.filename;
        await poll(() => `/allvsall_status/${encodeURIComponent(fn)}`, {
          interval: 2000,
          isDone: (s) => s.status === "success" && s.message === "Completed.",
          isFailed: (s) => s.status === "error" || (s.message || "").startsWith("Error"),
        });
        const { body } = await getJSON(`/allvsall_data/${encodeURIComponent(fn)}`);
        if (body.status !== "success") throw new Error(body.message || "no network");
        return body;
      })();
      const [cluR, netR] = await Promise.all([cluP, netP]);
      if (cluR.status !== "success") throw new Error(cluR.message || "clustering failed");
      setClu(cluR); setNet(netR); setStatus(null);
    } catch (e) { setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); }
  };

  // Heatmap (clustered, columns = domains). x is a numeric index so we can mark a column.
  useEffect(() => {
    if (!data || !clu || !hmRef.current) return;
    const { rows, cols } = data, feat = data.features[0];
    const ro = clu.row_order, co = clu.col_order;
    const colNames = co.map((j) => cols[j]); colNamesRef.current = colNames;
    const t = transform(data.data[feat], cols, { norm: "none", log: false });
    const z = ro.map((i) => co.map((j) => t[i][j]));
    const text = ro.map((i) => co.map((j) => `${rows[i]}<br>${cols[j]}`));
    Plotly.react(hmRef.current, [{
      z, x: co.map((_, j) => j), y: ro.map((_, i) => i), text, type: "heatmap", colorscale: "YlGnBu",
      showscale: false, hovertemplate: "%{text}<extra></extra>",
    }], {
      autosize: true, height: 540, margin: { l: 6, r: 6, t: 6, b: 6 },
      xaxis: { showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      yaxis: { showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    }, { responsive: true, displaylogo: false });
    const div = hmRef.current;
    if (div.removeAllListeners) div.removeAllListeners("plotly_click");
    div.on("plotly_click", (e) => { const pt = e.points[0]; if (pt) setSel(colNames[Math.round(pt.x)] ?? null); });
    return () => { try { Plotly.purge(div); } catch { /* noop */ } };
  }, [data, clu]);

  // Domain network (cytoscape + fcose).
  useEffect(() => {
    if (!net || !netRef.current) return;
    const nc = net.node_cluster || {}, deg = net.degree || {};
    const maxDeg = Math.max(1, ...net.nodes.map((n) => deg[n] || 0));
    const cy = cytoscape({
      container: netRef.current,
      elements: [
        ...net.nodes.map((n) => ({ data: { id: n, color: cc(nc[n]), deg: deg[n] || 1 } })),
        ...net.edges.map((e) => ({ data: { source: e.source, target: e.target, weight: e.weight != null ? e.weight : 1 } })),
      ],
      style: [
        { selector: "node", style: { "background-color": "data(color)", width: `mapData(deg,1,${maxDeg},10,30)`, height: `mapData(deg,1,${maxDeg},10,30)` } },
        { selector: "node.faded", style: { "background-opacity": 0.1 } },
        { selector: "node.hl", style: { "border-width": 3, "border-color": "#0e1726" } },
        { selector: "edge", style: { "line-color": "rgba(18,28,54,.12)", "curve-style": "haystack", width: `mapData(weight,0,1,.3,2.5)` } },
        { selector: "edge.faded", style: { "line-opacity": 0.03 } },
        { selector: "edge.hl", style: { "line-color": "#e11d48", "line-opacity": 0.9, width: 2 } },
      ],
      layout: { name: "fcose", quality: "proof", animate: true, packComponents: true, nodeSeparation: 130, nodeRepulsion: 7000, idealEdgeLength: 60, padding: 40 },
      minZoom: 0.1, maxZoom: 3, wheelSensitivity: 0.3,
    });
    cyRef.current = cy;
    cy.on("tap", "node", (e) => setSel(e.target.id()));
    cy.on("tap", (e) => { if (e.target === cy) setSel(null); });
    return () => { cy.destroy(); cyRef.current = null; };
  }, [net]);

  // The link: a selected domain lights up the network neighbourhood AND marks the
  // matching heatmap column — click in either view drives both.
  useEffect(() => {
    const cy = cyRef.current;
    if (cy) cy.batch(() => {
      cy.elements().removeClass("faded hl");
      if (sel) {
        const n = cy.getElementById(sel);
        if (n.nonempty()) {
          const hood = n.closedNeighborhood();
          cy.elements().addClass("faded"); hood.removeClass("faded"); hood.addClass("hl");
          cy.animate({ center: { eles: n }, zoom: Math.min(1.4, cy.zoom() * 1.2) }, { duration: 400 });
        }
      }
    });
    if (hmRef.current && colNamesRef.current.length) {
      const idx = sel ? colNamesRef.current.indexOf(sel) : -1;
      try {
        Plotly.relayout(hmRef.current, {
          shapes: idx >= 0 ? [{ type: "line", xref: "x", yref: "paper", x0: idx, x1: idx, y0: 0, y1: 1, line: { color: "#e11d48", width: 2 } }] : [],
        });
      } catch { /* noop */ }
    }
  }, [sel, data, clu, net]);

  const info = (() => {
    if (!sel || !net) return null;
    const deg = net.degree ? net.degree[sel] : undefined;
    const cl = net.node_cluster ? net.node_cluster[sel] : undefined;
    let present = null;
    if (data) { const j = data.cols.indexOf(sel); if (j >= 0) present = data.data[data.features[0]].reduce((s, r) => s + (r[j] > 0 ? 1 : 0), 0); }
    const nbrs = (net.edges || []).filter((e) => e.source === sel || e.target === sel).map((e) => (e.source === sel ? e.target : e.source));
    return { deg, cl, present, nbrs };
  })();

  return (
    <div className="fade-up" style={{ maxWidth: 1280, margin: "0 auto" }}>
      <h1>Linked explorer</h1>
      <p className="muted">One dataset, two synchronised views. The <strong>clustered heatmap</strong> (left) and the
         <strong> domain network</strong> (right) share the same domains — <strong>click a column or a node</strong> and the
         other view lights up the match and its neighbours. Upload a correlation matrix to begin.</p>

      {!net && <>
        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · correlation_matrix.csv" file={file} onFile={setFile} />
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-primary" onClick={run}><i className="fa-solid fa-diagram-project" /> Build explorer</button>
        </div>
        <Status s={status} />
      </>}

      {net && <>
        <div className="card card-pad" style={{ marginBottom: 12, minHeight: 64 }}>
          {!sel && <span className="muted">Click a <strong>heatmap column</strong> or a <strong>network node</strong> to link the views.</span>}
          {sel && info && <div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <strong style={{ wordBreak: "break-all" }}>{sel}</strong>
              <span className="muted" style={{ fontSize: ".85rem" }}>
                cluster {info.cl} · {info.deg ?? 0} network links{info.present != null ? ` · present in ${info.present} species` : ""}
              </span>
            </div>
            {info.nbrs.length > 0 && <div style={{ marginTop: 8, fontSize: ".82rem", display: "flex", gap: 6, flexWrap: "wrap" }}>
              {info.nbrs.slice(0, 8).map((nb) => (
                <button key={nb} className="btn btn-secondary" style={{ padding: "3px 9px", fontSize: ".76rem" }} onClick={() => setSel(nb)}>{nb}</button>
              ))}
              {info.nbrs.length > 8 && <span className="muted">+{info.nbrs.length - 8} more</span>}
            </div>}
          </div>}
        </div>
        <div className="explorer-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <div style={{ fontSize: ".8rem", color: "var(--text-2)", marginBottom: 6 }}>Clustered heatmap · species × domains</div>
            <div ref={hmRef} style={{ width: "100%", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
          </div>
          <div>
            <div style={{ fontSize: ".8rem", color: "var(--text-2)", marginBottom: 6 }}>Domain network · MCL clusters</div>
            <div ref={netRef} style={{ width: "100%", height: 540, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
          </div>
        </div>
      </>}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { transform } from "../lib/matrix.js";
import { API, postJSON, uploadFile, loadMatrix, poll, getJSON } from "../lib/api.js";
import { EDGE, EDGE_FADED, HIGHLIGHT, INK, NODE_SIZE_COMPACT, ZOOM, clusterColor as cc, fcose as fcoseOpts } from "../lib/network.js";
import { C, PLOT_CONFIG, VIRIDIS, plotLayout } from "../lib/theme.js";
import Tips from "../components/Tips.jsx";
import { sampleFile, samplePreview } from "../lib/samples.js";

cytoscape.use(fcose);

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
    try { setStatus({ kind: "info", msg: "Reading matrix…", progress: true }); d = await loadMatrix(file, "first"); setData(d); }
    catch (e) { return setStatus({ kind: "error", msg: e.message || "Could not read the matrix." }); }
    try {
      setStatus({ kind: "info", msg: "Clustering rows/cols + building the domain network…", progress: true });
      const cluP = postJSON(API.clustergram, { file_id: d.file_id, metric: d.features[0] });
      const netP = (async () => {
        const up = await uploadFile(API.allvsall, file);
        if (up.status !== "success") throw new Error(up.message || "upload failed");
        const fn = up.job_id;
        await poll(() => API.allvsallStatus(fn), {
          interval: 2000,
          isDone: (s) => s.state === "done",
          isFailed: (s) => s.state === "failed" || s.status === "error",
        });
        const { body } = await getJSON(API.allvsallData(fn));
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
    const { rows, cols } = data, feat = Object.keys(data.data)[0];
    const ro = clu.row_order, co = clu.col_order;
    const colNames = co.map((j) => cols[j]); colNamesRef.current = colNames;
    const t = transform(data.data[feat], cols, { norm: "none", log: false });
    const z = ro.map((i) => co.map((j) => t[i][j]));
    const text = ro.map((i) => co.map((j) => `${rows[i]}<br>${cols[j]}`));
    Plotly.react(hmRef.current, [{
      z, x: co.map((_, j) => j), y: ro.map((_, i) => i), text, type: "heatmap", colorscale: VIRIDIS,
      showscale: false, hovertemplate: "%{text}<extra></extra>",
    }], plotLayout({
      autosize: true, height: 520, margin: { l: 6, r: 6, t: 6, b: 6 },
      xaxis: { showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
      yaxis: { showticklabels: false, showgrid: false, zeroline: false, ticks: "" },
    }), PLOT_CONFIG);
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
    // The API already sends only the strongest links (and reports edges_total),
    // so the network reads as structure rather than a hairball without the client
    // having to hide anything of its own.
    const edges = net.edges;
    const cy = cytoscape({
      container: netRef.current,
      elements: [
        ...net.nodes.map((n) => ({ data: { id: n, color: cc(nc[n]), deg: deg[n] || 1 } })),
        ...edges.map((e) => ({ data: { source: e.source, target: e.target, weight: e.weight != null ? e.weight : 1 } })),
      ],
      style: [
        { selector: "node", style: { "background-color": "data(color)", width: `mapData(deg,1,${maxDeg},${NODE_SIZE_COMPACT.min},${NODE_SIZE_COMPACT.max})`,
            height: `mapData(deg,1,${maxDeg},${NODE_SIZE_COMPACT.min},${NODE_SIZE_COMPACT.max})`, "border-width": 0 } },
        { selector: "node.faded", style: { "background-opacity": 0.08 } },
        { selector: "node.hl", style: { "border-width": 2, "border-color": C.signal } },
        { selector: "edge", style: { "line-color": EDGE, "curve-style": "haystack", width: `mapData(weight,0,1,.25,1.6)` } },
        { selector: "edge.faded", style: { "line-color": EDGE_FADED } },
        { selector: "edge.hl", style: { "line-color": HIGHLIGHT, "line-opacity": 0.9, width: 2 } },
      ],
      layout: fcoseOpts({ padding: 40 }),
      ...ZOOM,
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
          shapes: idx >= 0 ? [{ type: "line", xref: "x", yref: "paper", x0: idx, x1: idx, y0: 0, y1: 1, line: { color: HIGHLIGHT, width: 2 } }] : [],
        });
      } catch { /* noop */ }
    }
  }, [sel, data, clu, net]);

  const info = (() => {
    if (!sel || !net) return null;
    const deg = net.degree ? net.degree[sel] : undefined;
    const cl = net.node_cluster ? net.node_cluster[sel] : undefined;
    let present = null;
    if (data) { const j = data.cols.indexOf(sel); if (j >= 0) present = data.data[Object.keys(data.data)[0]].reduce((s, r) => s + (r[j] > 0 ? 1 : 0), 0); }
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
        <Tips
          format={"A correlation matrix (species × domains)"}
          sample={samplePreview("matrix", 3)}
          tips={[
          <>Click a <b>heatmap column</b> or a <b>network node</b>: both views follow the same
            selection, which is the point of having them side by side.</>,
          <>The network carries only the <b>strongest links</b> — the caption says how many of how
            many. It is a view of the graph, not the whole graph.</>,
          <>“Present in N species” is counted from the matrix you uploaded, not from the network,
            so it does not change when links are hidden.</>,
        ]}
        />

        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · correlation_matrix.csv" file={file} onFile={setFile}
                  onSample={() => setFile(sampleFile("matrix"))} />
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
            <div style={{ fontSize: ".8rem", color: "var(--dim)", marginBottom: 6 }}>Clustered heatmap · species × domains</div>
            <div ref={hmRef} style={{ width: "100%", background: "var(--void)", border: "1px solid var(--rule)", borderRadius: 5 }} />
          </div>
          <div>
            <div style={{ fontSize: ".8rem", color: "var(--dim)", marginBottom: 6 }}>
              Domain network · MCL clusters
              {net.edges_total > net.edges.length &&
                ` · strongest ${net.edges.length.toLocaleString()} of ${net.edges_total.toLocaleString()} links`}
            </div>
            <div ref={netRef} style={{ width: "100%", height: 540, background: "var(--void)", border: "1px solid var(--rule)", borderRadius: 5 }} />
          </div>
        </div>
      </>}
    </div>
  );
}

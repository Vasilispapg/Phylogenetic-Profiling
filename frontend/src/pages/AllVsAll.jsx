import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import Dropzone from "../components/Dropzone.jsx";
import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";
import { uploadFile, poll } from "../lib/api.js";

const clusterColor = (c) => (c == null ? "#5dcaa5" : `hsl(${(c * 47) % 360},70%,55%)`);

export default function AllVsAll() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [minW, setMinW] = useState(0);
  const [layout, setLayout] = useState("cose");
  const [tip, setTip] = useState(null);
  const boxRef = useRef(null);
  const cyRef = useRef(null);

  const start = async () => {
    if (!file) return setStatus({ kind: "error", msg: "Please choose a correlation matrix CSV." });
    setData(null);
    setStatus({ kind: "info", msg: "Uploading & clustering…", progress: true });
    try {
      const res = await uploadFile("/tools/allvsall", file);
      if (res.status !== "success") return setStatus({ kind: "error", msg: res.message || "Failed to start." });
      const fn = res.filename;
      await poll(() => `/allvsall_status/${encodeURIComponent(fn)}`, {
        interval: 2000,
        isDone: (d) => d.status === "success" && d.message === "Completed.",
        isFailed: (d) => d.status === "error",
        onTick: (d) => d.message && setStatus({ kind: "info", msg: d.message, progress: true }),
      });
      const r = await fetch(`/allvsall_data/${encodeURIComponent(fn)}`);
      const d = await r.json();
      if (d.status !== "success") return setStatus({ kind: "error", msg: d.message || "No data." });
      setStatus(null);
      setData(d);
    } catch (e) { setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); }
  };

  useEffect(() => {
    if (!data || !boxRef.current) return;
    const nc = data.node_cluster || {}, deg = data.degree || {};
    const maxDeg = Math.max(1, ...data.nodes.map((n) => deg[n] || 0));
    const cy = cytoscape({
      container: boxRef.current,
      elements: [
        ...data.nodes.map((n) => ({ data: { id: n, color: clusterColor(nc[n]), deg: deg[n] || 1, cl: nc[n] } })),
        ...data.edges.map((e) => ({ data: { source: e.source, target: e.target, weight: e.weight != null ? e.weight : 1 } })),
      ],
      style: [
        { selector: "node", style: { "background-color": "data(color)", width: `mapData(deg,1,${maxDeg},12,34)`, height: `mapData(deg,1,${maxDeg},12,34)`, label: "data(id)", "font-size": 9, color: "#0e1726", "text-halign": "center", "text-valign": "bottom", "min-zoomed-font-size": 14 } },
        { selector: "node.dim", style: { "background-opacity": 0.12, "text-opacity": 0 } },
        { selector: "node:selected", style: { "border-color": "#0e1726", "border-width": 3 } },
        { selector: "edge", style: { "line-color": "rgba(18,28,54,.14)", width: `mapData(weight,0,1,0.4,4)`, "curve-style": "haystack" } },
        { selector: "edge.dim", style: { "line-opacity": 0.03 } },
      ],
      layout: { name: "cose", animate: true, animationDuration: 600, padding: 40, nodeRepulsion: 9000, idealEdgeLength: 90, fit: true },
      minZoom: 0.15, maxZoom: 3, wheelSensitivity: 0.3,
    });
    cyRef.current = cy;
    cy.on("mouseover", "node", (e) => { const n = e.target; const p = e.renderedPosition; setTip({ x: p.x, y: p.y, t: `${n.id()} · cluster ${n.data("cl")} · ${n.data("deg")} links` }); });
    cy.on("mouseout", "node", () => setTip(null));
    cy.on("tap", "node", (e) => { const cl = e.target.data("cl"); const same = cy.nodes().filter((x) => x.data("cl") === cl); cy.elements().addClass("dim"); same.removeClass("dim"); same.connectedEdges().filter((ed) => same.contains(ed.source()) && same.contains(ed.target())).removeClass("dim"); });
    cy.on("tap", (e) => { if (e.target === cy) cy.elements().removeClass("dim"); });
    return () => cy.destroy();
  }, [data]);

  useEffect(() => {
    const cy = cyRef.current; if (!cy) return;
    cy.batch(() => cy.edges().forEach((ed) => ed.style("display", ed.data("weight") >= minW ? "element" : "none")));
  }, [minW]);

  useEffect(() => {
    const cy = cyRef.current; if (!cy) return;
    const opts = { name: layout, animate: true, padding: 40, fit: true };
    if (layout === "concentric") { opts.concentric = (n) => n.data("deg"); opts.levelWidth = () => 4; }
    cy.layout(opts).run();
  }, [layout]);

  const m = data && data.metrics;
  return (
    <div className="fade-up" style={{ maxWidth: 1040, margin: "0 auto" }}>
      <Stepper steps={[{ label: "Correlation matrix", state: "done" }, { label: "Cluster domains (MCL)", state: "active" }]} />
      <h1>All-vs-all domain clustering</h1>
      <p className="muted">Upload a <strong>correlation matrix CSV</strong>. Domains are clustered by shared profile
         (Markov Clustering) and shown as an interactive network.</p>

      {!data && <>
        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · .csv (species × domains)" file={file} onFile={setFile} />
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-primary" onClick={start}><i className="fa-solid fa-share-nodes" /> Generate graph</button>
        </div>
        <Status s={status} />
      </>}

      {data && <>
        {m && <div className={"note" + (m.warning ? " warn" : "")}>
          <strong>{m.n_domains} domains → {m.n_clusters} clusters</strong> (modularity {m.modularity}).{" "}
          {m.warning ? m.warning : "Hover a node to read it; click to isolate its cluster; zoom in for labels."}
        </div>}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "12px 0" }}>
          <button className="btn btn-secondary" onClick={() => cyRef.current && cyRef.current.fit(undefined, 40)}><i className="fa-solid fa-expand" /> Reset</button>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" }}>Layout
            <select className="select" style={{ width: "auto" }} value={layout} onChange={(e) => setLayout(e.target.value)}>
              <option value="cose">Force</option><option value="concentric">Concentric</option><option value="circle">Circle</option><option value="grid">Grid</option>
            </select></label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem", flex: 1, minWidth: 200 }}>Min similarity
            <input type="range" min="0" max="1" step="0.05" value={minW} onChange={(e) => setMinW(parseFloat(e.target.value))} style={{ flex: 1 }} />
            <span style={{ width: 34 }}>{minW.toFixed(2)}</span></label>
        </div>
        <div style={{ position: "relative" }}>
          <div ref={boxRef} style={{ width: "100%", height: 560, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
          {tip && <div style={{ position: "absolute", left: tip.x + 14, top: tip.y + 10, pointerEvents: "none", background: "#111827", color: "#fff", borderRadius: 8, padding: "6px 10px", fontSize: ".8rem" }}>{tip.t}</div>}
        </div>
      </>}
    </div>
  );
}

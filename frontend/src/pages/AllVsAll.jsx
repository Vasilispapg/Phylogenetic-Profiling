import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import Dropzone from "../components/Dropzone.jsx";
import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";
import { API, uploadFile, poll, getJSON } from "../lib/api.js";
import { EDGE, EDGE_FADED, HIGHLIGHT, INK, LABEL_BG, MUTED, NODE_SIZE, ZOOM, clusterColor, fcose as fcoseOpts } from "../lib/network.js";

cytoscape.use(fcose);

export default function AllVsAll() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [data, setData] = useState(null);
  const [minW, setMinW] = useState(0);
  const [layout, setLayout] = useState("clusters");
  const [hideIso, setHideIso] = useState(false);
  const [info, setInfo] = useState({ shown: 0, iso: 0, links: 0 });
  const [wRange, setWRange] = useState({ min: 0, max: 1 });
  const [tip, setTip] = useState(null);
  const boxRef = useRef(null);
  const cyRef = useRef(null);
  const pinRef = useRef(null);

  const start = async () => {
    if (!file) return setStatus({ kind: "error", msg: "Please choose a correlation matrix CSV." });
    setData(null);
    setStatus({ kind: "info", msg: "Uploading & clustering…", progress: true });
    try {
      const res = await uploadFile(API.allvsall, file);
      if (res.status !== "success") return setStatus({ kind: "error", msg: res.message || "Failed to start." });
      const fn = res.job_id;
      await poll(() => API.allvsallStatus(fn), {
        interval: 2000,
        isDone: (d) => d.state === "done",
        isFailed: (d) => d.state === "failed" || d.status === "error",
        onTick: (d) => d.message && setStatus({ kind: "info", msg: d.message, progress: true }),
      });
      const { body: d } = await getJSON(API.allvsallData(fn));
      if (d.status !== "success") return setStatus({ kind: "error", msg: d.message || "No data." });
      // The slider must span the ACTUAL weight range (the backend already keeps only
      // Jaccard ≥ 0.5, so a 0–1 slider would have a dead lower half). Smart default
      // keeps roughly the 4·N strongest edges so the first view shows structure.
      const ws = d.edges.map((e) => (e.weight == null ? 0 : e.weight)).sort((a, b) => b - a);
      const wmax = ws.length ? ws[0] : 1, wmin = ws.length ? ws[ws.length - 1] : 0;
      const idx = Math.min(ws.length - 1, 4 * d.nodes.length);
      const def = ws.length ? Math.round((ws[idx] || wmin) * 100) / 100 : 0;
      setWRange({ min: Math.floor(wmin * 100) / 100, max: Math.ceil(wmax * 100) / 100 });
      setMinW(def);
      setStatus(null);
      setData(d);
    } catch (e) { setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); }
  };

  // Build the graph once per dataset.
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
        { selector: "node", style: {
            "background-color": "data(color)",
            width: `mapData(deg,1,${maxDeg},${NODE_SIZE.min},${NODE_SIZE.max})`,
            height: `mapData(deg,1,${maxDeg},${NODE_SIZE.min},${NODE_SIZE.max})`,
            label: "data(id)", "font-size": 8, color: INK, "font-family": "IBM Plex Mono, monospace",
            "text-opacity": 0, "text-halign": "center", "text-valign": "bottom",
            "text-background-color": LABEL_BG, "text-background-opacity": 0.95,
            "text-background-shape": "roundrectangle", "text-background-padding": 2,
            "text-max-width": 150, "text-wrap": "ellipsis", "min-zoomed-font-size": 7,
            "transition-property": "background-opacity, border-width", "transition-duration": "120ms" } },
        { selector: "node.iso", style: { "background-color": MUTED, width: 9, height: 9 } },
        { selector: "node.faded", style: { "background-opacity": 0.08, "text-opacity": 0 } },
        { selector: "node.hl", style: { "text-opacity": 1, "z-index": 30, "border-width": 2, "border-color": INK } },
        { selector: "node:selected", style: { "border-color": INK, "border-width": 3, "text-opacity": 1 } },
        { selector: "edge", style: { "line-color": EDGE, width: `mapData(weight,0,1,0.4,2.6)`, "curve-style": "haystack" } },
        { selector: "edge.faded", style: { "line-color": EDGE_FADED } },
        { selector: "edge.hl", style: { "line-color": HIGHLIGHT, "line-opacity": 0.95, width: 2.2, "z-index": 29, "curve-style": "straight" } },
      ],
      ...ZOOM,
    });
    cyRef.current = cy;

    const lit = (node) => {
      // Only count/show links that pass the current threshold (i.e. visible edges).
      const vEdges = node.connectedEdges().filter((e) => e.visible());
      const hood = vEdges.union(vEdges.connectedNodes()).union(node);
      cy.batch(() => { cy.elements().addClass("faded"); hood.removeClass("faded").addClass("hl"); });
      const partners = vEdges.map((e) => (e.source().id() === node.id() ? e.target().id() : e.source().id()));
      const p = node.renderedPosition();
      setTip({ x: p.x, y: p.y, name: node.id(), cl: node.data("cl"),
               k: vEdges.length, names: partners.slice(0, 6) });
    };
    const clear = () => { cy.batch(() => cy.elements().removeClass("faded hl")); setTip(null); };

    cy.on("mouseover", "node", (e) => lit(e.target));
    cy.on("mouseout", "node", () => { if (!pinRef.current) clear(); });
    cy.on("tap", "node", (e) => { pinRef.current = e.target.id(); lit(e.target); });
    cy.on("tap", (e) => { if (e.target === cy) { pinRef.current = null; clear(); } });

    applyVisibility();
    runLayout("clusters", true);
    return () => { cy.destroy(); cyRef.current = null; pinRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Filter edges by min similarity and grey/hide isolated nodes (cheap, no relayout).
  function applyVisibility(opts = {}) {
    const cy = cyRef.current; if (!cy) return;
    const min = opts.min ?? minW, hide = opts.hide ?? hideIso;
    let iso = 0, links = 0;
    cy.batch(() => {
      cy.edges().forEach((ed) => {
        const on = ed.data("weight") >= min; ed.style("display", on ? "element" : "none"); if (on) links++;
      });
      cy.nodes().forEach((n) => {
        const vdeg = n.connectedEdges().filter((e) => e.data("weight") >= min).length;
        n.data("vdeg", vdeg);
        const isolated = vdeg === 0;
        n.toggleClass("iso", isolated);
        n.style("display", hide && isolated ? "none" : "element");
        if (isolated) iso++;
      });
    });
    setInfo({ shown: cy.nodes(":visible").length, iso, links });
  }

  // Lay out each connected component as its own separated circle (clusters mode):
  // many small groups → a clean grid of rings; a big tangled component → fcose.
  function runLayout(lay = layout, randomize = false) {
    const cy = cyRef.current; if (!cy) return;
    const vis = cy.elements(":visible");
    if (lay === "clusters") {
      const comps = vis.components().sort((a, b) => b.nodes().length - a.nodes().length);
      // Recolour by current connected group so separate groups are never confused.
      cy.batch(() => comps.forEach((c, i) => {
        const col = c.nodes().length > 1 ? clusterColor(i, { saturation: 62 }) : MUTED;
        c.nodes().forEach((nd) => nd.data("color", col));
      }));
      const big = comps.length ? comps[0].nodes().length : 0;
      if (comps.length > 1 && big <= 25) return packGrid(comps);
      vis.layout(fcoseOpts({ randomize, padding: 50 })).run();
      return;
    }
    if (lay === "concentric")
      vis.layout({ name: "concentric", concentric: (n) => n.data("vdeg") || 0, levelWidth: () => 3,
                   minNodeSpacing: 14, animate: true, padding: 45, fit: true }).run();
    else
      vis.layout({ name: "grid", animate: true, padding: 45, fit: true, avoidOverlap: true }).run();
  }

  // Each connected group becomes a ring in a grid cell; isolated dots packed below.
  function packGrid(comps) {
    const cy = cyRef.current; if (!cy) return;
    const multi = comps.filter((c) => c.nodes().length > 1);
    const singles = comps.filter((c) => c.nodes().length === 1).map((c) => c.nodes()[0]);
    const perRow = Math.max(1, Math.ceil(Math.sqrt(multi.length || 1))), cell = 180;
    cy.batch(() => {
      multi.forEach((c, i) => {
        const cx = (i % perRow) * cell, cy0 = Math.floor(i / perRow) * cell;
        const nodes = c.nodes(), k = nodes.length, r = Math.min(64, 20 + k * 7);
        nodes.forEach((nd, j) => {
          const a = (2 * Math.PI * j) / k - Math.PI / 2;
          nd.position({ x: cx + r * Math.cos(a), y: cy0 + r * Math.sin(a) });
        });
      });
      const baseY = Math.ceil((multi.length || 1) / perRow) * cell + 50;
      const sPerRow = Math.max(1, Math.ceil(Math.sqrt(singles.length || 1)));
      singles.forEach((nd, i) => nd.position({ x: (i % sPerRow) * 26, y: baseY + Math.floor(i / sPerRow) * 26 }));
    });
    cy.animate({ fit: { eles: cy.elements(":visible"), padding: 45 } }, { duration: 400 });
  }

  const m = data && data.metrics;
  return (
    <div className="fade-up" style={{ maxWidth: 1040, margin: "0 auto" }}>
      <Stepper steps={[{ label: "Correlation matrix", state: "done" }, { label: "Cluster domains (MCL)", state: "active" }]} />
      <h1>All-vs-all domain clustering</h1>
      <p className="muted">Upload a <strong>correlation matrix CSV</strong>. Domains are clustered by shared profile
         (Markov Clustering) and shown as an interactive network. <strong>Hover</strong> a node to light up everything
         it links to; <strong>click</strong> to pin that focus; raise <strong>min similarity</strong> to break the
         graph into tighter groups.</p>

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
          {m.warning ? m.warning : "Hover a node to read it and its links; click to pin; zoom for labels."}
        </div>}

        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "12px 0" }}>
          <button className="btn btn-secondary" onClick={() => cyRef.current && cyRef.current.fit(undefined, 45)}><i className="fa-solid fa-expand" /> Fit</button>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" }}>Layout
            <select className="select" style={{ width: "auto" }} value={layout}
                    onChange={(e) => { setLayout(e.target.value); runLayout(e.target.value, true); }}>
              <option value="clusters">Clusters</option><option value="concentric">Concentric</option><option value="grid">Grid</option>
            </select></label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem", flex: 1, minWidth: 220 }}>Min similarity
            <input type="range" min={wRange.min} max={wRange.max} step="0.01" value={minW}
                   onChange={(e) => { const v = parseFloat(e.target.value); setMinW(v); applyVisibility({ min: v }); }}
                   onMouseUp={() => runLayout(layout, true)} onTouchEnd={() => runLayout(layout, true)} onKeyUp={() => runLayout(layout, true)}
                   style={{ flex: 1 }} />
            <span style={{ width: 34 }}>{minW.toFixed(2)}</span></label>
          <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: ".88rem" }}>
            <input type="checkbox" checked={hideIso} onChange={(e) => { setHideIso(e.target.checked); applyVisibility({ hide: e.target.checked }); runLayout(layout, true); }} />
            Hide isolated</label>
        </div>

        <div style={{ fontSize: ".82rem", color: "var(--dim)", margin: "0 0 8px" }}>
          <strong>{info.shown}</strong> domains shown · <strong>{info.iso}</strong> isolated · <strong>{info.links}</strong> links ≥ {minW.toFixed(2)}
          {data.edges_total > data.edges.length &&
            ` · server sent the strongest ${data.edges.length.toLocaleString()} of ${data.edges_total.toLocaleString()}`}
        </div>

        <div style={{ position: "relative" }}>
          <div ref={boxRef} style={{ width: "100%", height: 600, background: "var(--void)", border: "1px solid var(--rule)", borderRadius: 5 }} />
          {tip && <div style={{ position: "absolute", left: Math.min(tip.x + 14, 760), top: tip.y + 10, pointerEvents: "none",
                                 background: "var(--panel-2)", color: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 3, padding: "9px 11px", fontSize: ".74rem", fontFamily: "var(--mono)", maxWidth: 280, boxShadow: "0 12px 34px rgba(0,0,0,.5)" }}>
            <div style={{ fontWeight: 700, marginBottom: 2, wordBreak: "break-all" }}>{tip.name}</div>
            <div style={{ opacity: .8 }}>cluster {tip.cl} · {tip.k} link{tip.k === 1 ? "" : "s"}</div>
            {tip.k > 0 && <div style={{ marginTop: 5, paddingTop: 5, borderTop: "1px solid var(--rule)", opacity: .9, lineHeight: 1.5 }}>
              {tip.names.map((nm) => <div key={nm} style={{ wordBreak: "break-all" }}>↳ {nm}</div>)}
              {tip.k > tip.names.length && <div style={{ opacity: .6 }}>+{tip.k - tip.names.length} more…</div>}
            </div>}
          </div>}
        </div>
      </>}
    </div>
  );
}

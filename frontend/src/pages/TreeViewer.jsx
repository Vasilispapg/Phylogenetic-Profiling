import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { uploadFile } from "../lib/api.js";

const genus = (name) => { const p = (name || "").split("-"); return p.length > 2 ? p[2].split("_")[0] : (name || ""); };
const genusColor = (d) => {
  if (d.children || d._children) return d._children ? "#2f6bff" : "#9aa3b5";
  const g = genus(d.data.name); if (!g) return "#9aa3b5";
  let h = 0; for (const c of g) h = (h * 31 + c.charCodeAt(0)) % 360;
  return `hsl(${h},60%,55%)`;
};
const W = 1000, H = 900, R = W / 2 - 60;

export default function TreeViewer() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [tree, setTree] = useState(null);
  const [depth, setDepth] = useState(4);
  const svgRef = useRef(null);
  const ctl = useRef({});

  const upload = async () => {
    if (!file) return setStatus({ kind: "error", msg: "Please choose a .nw file." });
    setStatus({ kind: "info", msg: "Processing tree…", progress: true });
    try {
      const res = await uploadFile("/tools/tree_viewer", file);
      if (res.status === "success") { setTree(res.tree_data); setStatus({ kind: "success", msg: "Tree loaded — click nodes to expand/collapse." }); }
      else setStatus({ kind: "error", msg: res.message || "Failed to load tree." });
    } catch { setStatus({ kind: "error", msg: "An error occurred while processing the tree." }); }
  };

  useEffect(() => {
    if (!tree || !svgRef.current) return;
    const svg = d3.select(svgRef.current); svg.selectAll("*").remove();
    const g = svg.append("g").attr("transform", `translate(${W / 2},${H / 2})`);
    const root = d3.hierarchy(tree); let n = 0; root.each((d) => (d.id = ++n));

    const expandAll = (d) => { if (d._children) { d.children = d._children; d._children = null; } (d.children || []).forEach(expandAll); };
    const collapseBelow = (d, lvl) => { if (d.depth >= lvl && d.children) { d._children = d.children; d.children = null; } else (d.children || []).forEach((c) => collapseBelow(c, lvl)); };
    const update = () => {
      d3.tree().size([2 * Math.PI, R])(root);
      g.selectAll("path.lk").data(root.links(), (d) => d.target.id).join("path")
        .attr("class", "lk").attr("fill", "none").attr("stroke", "rgba(18,28,54,.22)").attr("stroke-width", 1)
        .attr("d", d3.linkRadial().angle((d) => d.x).radius((d) => d.y));
      const node = g.selectAll("g.nd").data(root.descendants(), (d) => d.id).join((enter) => {
        const e = enter.append("g").attr("class", "nd");
        e.append("circle").attr("stroke", "#fff").attr("stroke-width", 1.5).style("cursor", "pointer");
        e.append("text").attr("dy", "0.32em").attr("font-size", 9).attr("fill", "#0e1726");
        return e;
      });
      node.attr("transform", (d) => `rotate(${(d.x * 180) / Math.PI - 90}) translate(${d.y},0)`);
      node.select("circle").attr("r", (d) => (d._children ? 6 : 4)).attr("fill", genusColor);
      node.select("text")
        .attr("x", (d) => ((d.x < Math.PI) === !d.children ? 8 : -8))
        .style("text-anchor", (d) => ((d.x < Math.PI) === !d.children ? "start" : "end"))
        .attr("transform", (d) => (d.x >= Math.PI ? "rotate(180)" : null))
        .text((d) => (d.data.name && d.data.name !== "Unnamed" ? d.data.name : ""));
      node.on("click", (e, d) => {
        if (d.children) { d._children = d.children; d.children = null; }
        else if (d._children) { d.children = d._children; d._children = null; }
        update();
      });
    };
    ctl.current.expandToDepth = (lvl) => { expandAll(root); collapseBelow(root, lvl); update(); };
    ctl.current.search = (query) => {
      query = query.trim().toLowerCase(); if (!query) return;
      let t = null; root.each((d) => { if (!t && d.data.name && d.data.name.toLowerCase().includes(query)) t = d; });
      if (!t) { setStatus({ kind: "error", msg: "No species matches that name." }); return; }
      setStatus(null);
      t.ancestors().forEach((a) => { if (a._children) { a.children = a._children; a._children = null; } });
      update();
      const onPath = new Set(t.ancestors().map((a) => a.id));
      g.selectAll("path.lk").attr("stroke", (d) => (onPath.has(d.target.id) ? "#e44c65" : "rgba(18,28,54,.22)"))
        .attr("stroke-width", (d) => (onPath.has(d.target.id) ? 2.5 : 1));
    };
    svg.call(d3.zoom().scaleExtent([0.4, 4]).on("zoom", (e) => g.attr("transform", e.transform)));
    ctl.current.expandToDepth(depth);
  }, [tree]);

  useEffect(() => { ctl.current.expandToDepth && ctl.current.expandToDepth(depth); }, [depth]);

  return (
    <div className="fade-up" style={{ maxWidth: 1040, margin: "0 auto" }}>
      <h1>Phylogenetic tree viewer</h1>
      <p className="muted">Upload a Newick (<code>.nw</code>) file. Click a node to collapse/expand, search a species,
         and colour leaves by genus.</p>

      {!tree && <>
        <Dropzone accept=".nw,.newick,.nwk,.txt" hint="or click to browse · .nw" file={file} onFile={setFile} />
        <div style={{ marginTop: "1rem" }}><button className="btn btn-primary" onClick={upload}><i className="fa-solid fa-sitemap" /> View tree</button></div>
        <Status s={status} />
      </>}

      {tree && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", margin: "8px 0 12px" }}>
          <input className="input" style={{ width: "auto" }} placeholder="search species…"
                 onKeyDown={(e) => { if (e.key === "Enter") ctl.current.search(e.target.value); }} />
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" }}>Expand to depth
            <input type="range" min="1" max="20" value={depth} onChange={(e) => setDepth(parseInt(e.target.value, 10))} />
            <span>{depth}</span></label>
          <button className="btn btn-secondary" onClick={() => ctl.current.expandToDepth(99)}>Expand all</button>
          <button className="btn btn-secondary" onClick={() => ctl.current.expandToDepth(1)}>Collapse</button>
        </div>
        <Status s={status} />
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 900, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12 }} />
      </>}
    </div>
  );
}

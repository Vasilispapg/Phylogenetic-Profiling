import { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import Dropzone from "../components/Dropzone.jsx";
import Status from "../components/Status.jsx";
import { lbl } from "../lib/matrix.js";
import { API, loadMatrix, postJSON } from "../lib/api.js";

import { C, PLOT_CONFIG, plotLayout, clusterColor as cc, scatterIsSlow, scatterType } from "../lib/theme.js";
import Tips from "../components/Tips.jsx";
import { sampleFile, samplePreview } from "../lib/samples.js";

const L = { display: "flex", alignItems: "center", gap: 8, fontSize: ".88rem" };

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
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState(null);   // active cluster filter (null = all)
  const [selIdx, setSelIdx] = useState(null); // highlighted point
  const [fileId, setFileId] = useState(null);
  const ref = useRef(null);

  const names = data ? (axis === "domains" ? data.cols : data.rows) : [];

  // One upload: the labels come from the server with the numbers, and the id
  // drives the projection call.
  const onFile = async (f) => {
    setFile(f); setStatus({ kind: "info", msg: "Reading matrix…", progress: true });
    setEmb(null); setFileId(null);
    try {
      // Labels only: the projection happens server-side from the file_id, so the
      // cell values are never needed here.
      const d = await loadMatrix(f, "none");
      setData(d); setFeat(d.features[0]); setFileId(d.file_id);
      setSelIdx(null); setGroup(null); setQuery(""); setStatus(null);
    } catch (e) {
      setStatus({ kind: "error", msg: e.message || "Could not read the matrix." });
    }
  };

  useEffect(() => {
    if (!data || !feat || !fileId) return;
    let alive = true;
    setBusy(true); setEmb(null); setSelIdx(null); setGroup(null);
    setStatus({ kind: "info", msg: `Projecting ${axis} with ${method.toUpperCase()}…`, progress: true });
    postJSON(API.embedding, { file_id: fileId, metric: feat, axis, method, k })
      .then((r) => {
        if (!alive) return;
        if (r.status !== "success") { setStatus({ kind: "error", msg: r.message || "Embedding failed." }); setBusy(false); return; }
        setEmb(r); setBusy(false); setStatus(null);
      })
      .catch((e) => { if (!alive) return; setStatus({ kind: "error", msg: "Error: " + (e.message || "failed") }); setBusy(false); });
    return () => { alive = false; };
  }, [data, feat, fileId, axis, method, k]);

  const counts = useMemo(() => {
    const c = {}; if (emb) emb.labels.forEach((l) => (c[l] = (c[l] || 0) + 1)); return c;
  }, [emb]);

  const members = useMemo(() => {
    if (!emb) return [];
    const q = query.trim().toLowerCase();
    const out = [];
    for (let i = 0; i < emb.labels.length; i++) {
      if (group != null && emb.labels[i] !== group) continue;
      if (q && !names[i].toLowerCase().includes(q)) continue;
      out.push({ i, name: names[i], label: emb.labels[i] });
    }
    return out;
  }, [emb, query, group, names]);

  // Scatter (one trace per cluster) + highlight ring; dim non-active groups.
  useEffect(() => {
    if (!data || !emb || !ref.current) return;
    const groups = {};
    emb.labels.forEach((l, i) => { (groups[l] = groups[l] || []).push(i); });
    // One trace type for the whole figure: mixing scatter and scattergl layers
    // them inconsistently.
    const trace = scatterType(emb.coords.length);
    const traces = Object.entries(groups).map(([l, idxs]) => ({
      x: idxs.map((i) => emb.coords[i][0]), y: idxs.map((i) => emb.coords[i][1]),
      text: idxs.map((i) => names[i]), customdata: idxs,
      name: `cluster ${l} (${counts[l] || 0})`, type: trace, mode: "markers",
      marker: { size: 7, color: cc(+l), opacity: group == null || +l === group ? 0.92 : 0.07, line: { width: 0.5, color: "rgba(13,11,26,.8)" } },
      hovertemplate: `%{text}<extra>cluster ${l}</extra>`,
    }));
    if (selIdx != null && emb.coords[selIdx]) {
      traces.push({
        x: [emb.coords[selIdx][0]], y: [emb.coords[selIdx][1]], type: trace, mode: "markers",
        marker: { size: 20, color: "rgba(0,0,0,0)", line: { width: 2, color: C.signal } },
        hoverinfo: "skip", showlegend: false,
      });
    }
    Plotly.react(ref.current, traces, plotLayout({
      autosize: true, height: 620, margin: { l: 42, r: 10, t: 12, b: 42 },
      xaxis: { zeroline: false, showgrid: true, gridcolor: C.ruleSoft, title: { text: method === "pca" ? "PC1" : "dim 1" } },
      yaxis: { zeroline: false, showgrid: true, gridcolor: C.ruleSoft, title: { text: method === "pca" ? "PC2" : "dim 2" } },
      legend: { orientation: "v", x: 1.01, y: 1, font: { size: 10, color: C.dim } },
    }), { ...PLOT_CONFIG, toImageButtonOptions: { filename: "phyloflask-embedding", scale: 2 } });

    // Zoom to the selected point so it's easy to find.
    if (selIdx != null && emb.coords[selIdx]) {
      const xs = emb.coords.map((c) => c[0]), ys = emb.coords.map((c) => c[1]);
      const xs2 = (Math.max(...xs) - Math.min(...xs)) || 1, ys2 = (Math.max(...ys) - Math.min(...ys)) || 1;
      const [cx, cy] = emb.coords[selIdx];
      try { Plotly.relayout(ref.current, { "xaxis.range": [cx - xs2 * 0.18, cx + xs2 * 0.18], "yaxis.range": [cy - ys2 * 0.18, cy + ys2 * 0.18] }); } catch { /* noop */ }
    }

    const div = ref.current;
    if (div.removeAllListeners) div.removeAllListeners("plotly_click");
    div.on("plotly_click", (e) => { const pt = e.points[0]; if (pt && pt.customdata != null) setSelIdx(pt.customdata); });
    return () => { try { Plotly.purge(div); } catch { /* noop */ } };
  }, [data, emb, axis, method, group, selIdx]);

  const npoints = names.length;

  return (
    <div className="fade-up" style={{ maxWidth: 1240, margin: "0 auto" }}>
      <h1>Embedding map</h1>
      <p className="muted">Project each <strong>domain</strong> (or species) into 2D by its <strong>co-occurrence profile</strong>:
         points in the same genomes land close together, coloured by a <strong>KMeans</strong> grouping. Search a point or pick a
         group on the right to inspect members; click anything to zoom to it.</p>

      {!data && <>
        <Tips
          format={"A correlation matrix or a feature matrix"}
          sample={samplePreview("matrix", 3)}
          tips={[
          <><b>PCA</b> distances mean something globally. <b>t-SNE</b> distances mean something only
            locally — the gap between two t-SNE blobs is not evidence of anything.</>,
          <><b>k</b> changes the colouring, not the positions. If the colours disagree with what you
            see, that is KMeans disagreeing with the projection, which is itself informative.</>,
          <>Embed <b>domains</b> to look for functional modules; embed <b>species</b> to see which
            genomes carry similar repertoires.</>,
          <>Search a name on the right to filter the list and zoom the map to that point.</>,
        ]}
        />

        <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · correlation_matrix.csv / feature_matrix.csv" file={file} onFile={onFile}
                  onSample={() => onFile(sampleFile("matrix"))} />
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
          <button className="btn btn-secondary" onClick={() => { setData(null); setFile(null); setEmb(null); setSelIdx(null); setFileId(null); }}>Load another</button>
        </div>

        <div style={{ fontSize: ".82rem", color: "var(--dim)", marginBottom: 8 }}>
          <strong>{npoints}</strong> {axis} projected{emb ? ` · ${emb.n_clusters} groups` : ""}{busy ? " · computing…" : ""}
          {selIdx != null && names[selIdx] && <> · selected <strong style={{ wordBreak: "break-all" }}>{names[selIdx]}</strong> (cluster {emb.labels[selIdx]})</>}
          {emb && scatterIsSlow(emb.coords.length) && <> · drawing without WebGL, which is slower at this size</>}
          {emb && emb.note && <> · {emb.note}</>}
        </div>

        {/* Not gated on `busy`: a failure clears busy, which used to take
            the error message off screen with it and leave a blank panel. */}
        <Status s={status} />

        <div className="explorer-grid" style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 12 }}>
          <div ref={ref} style={{ width: "100%", minHeight: 200, background: "var(--void)", border: "1px solid var(--rule)", borderRadius: 5 }} />
          {emb && <div className="card" style={{ padding: 12, display: "flex", flexDirection: "column", height: 640 }}>
            <input className="input" placeholder="Search a name…" value={query} onChange={(e) => setQuery(e.target.value)} style={{ marginBottom: 10 }} />
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
              <button className={"btn " + (group == null ? "btn-primary" : "btn-secondary")} style={{ padding: "3px 10px", fontSize: ".76rem" }} onClick={() => setGroup(null)}>All</button>
              {Object.keys(counts).map((l) => (
                <button key={l} className={"btn " + (group === +l ? "btn-primary" : "btn-secondary")} style={{ padding: "3px 9px", fontSize: ".76rem" }}
                        onClick={() => setGroup(group === +l ? null : +l)}>
                  <span style={{ width: 8, height: 8, borderRadius: 9, background: cc(+l), display: "inline-block", marginRight: 5 }} />{l} · {counts[l]}
                </button>
              ))}
            </div>
            <div style={{ fontSize: ".75rem", color: "var(--dim-2)", marginBottom: 6 }}>{members.length} match{members.length === 1 ? "" : "es"}</div>
            <div style={{ overflowY: "auto", flex: 1, marginRight: -6, paddingRight: 6 }}>
              {members.slice(0, 200).map((m) => (
                <button key={m.i} onClick={() => setSelIdx(m.i)}
                        style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", border: "none",
                                 background: selIdx === m.i ? "var(--signal-soft)" : "transparent", cursor: "pointer", padding: "6px 8px",
                                 borderRadius: 8, fontSize: ".78rem", color: "var(--paper)", wordBreak: "break-all" }}>
                  <span style={{ width: 9, height: 9, borderRadius: 9, background: cc(m.label), flex: "0 0 9px" }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.name}</span>
                </button>
              ))}
              {members.length > 200 && <div className="muted" style={{ fontSize: ".75rem", padding: "6px 8px" }}>+{members.length - 200} more — refine the search</div>}
              {members.length === 0 && <div className="muted" style={{ fontSize: ".78rem", padding: "6px 8px" }}>No matches.</div>}
            </div>
          </div>}
        </div>
      </>}
    </div>
  );
}

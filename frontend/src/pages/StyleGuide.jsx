import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";

const Demo = ({ title, hint, children }) => (
  <section style={{ margin: "1.8rem 0" }}>
    <h2 style={{ fontSize: "1.2rem" }}>{title}</h2>
    {hint && <p className="muted" style={{ fontSize: ".88rem", margin: "0 0 12px" }}>{hint}</p>}
    <div className="card card-pad" style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center" }}>{children}</div>
  </section>
);

export default function StyleGuide() {
  return (
    <div className="doc fade-up">
      <h1>Design system &amp; templates</h1>
      <p className="lead">Live gallery of every PhyloFlask React component — copy from <code>src/components</code> and follow
         <code> docs/DESIGN.md</code>.</p>

      <Demo title="Colours">
        {[["--ink", "#111827"], ["--accent", "#2f6bff"], ["--teal", "#0bb39a"], ["coral", "#e44c65"]].map(([n, hex]) => (
          <div key={n} style={{ background: hex, color: "#fff", borderRadius: 12, padding: 14, fontSize: ".8rem", minWidth: 110 }}>{n}<br />{hex}</div>
        ))}
      </Demo>

      <Demo title="Buttons" hint="btn-primary · btn-secondary · disabled">
        <button className="btn btn-primary"><i className="fa-solid fa-play" /> Primary</button>
        <button className="btn btn-secondary"><i className="fa-solid fa-download" /> Secondary</button>
        <button className="btn btn-primary" disabled><i className="fa-solid fa-play" /> Disabled</button>
      </Demo>

      <Demo title="Inputs">
        <input className="input" placeholder="Text input…" style={{ maxWidth: 320 }} />
        <select className="select" style={{ maxWidth: 320 }}><option>Select…</option></select>
      </Demo>

      <Demo title="Stepper">
        <Stepper steps={[{ label: "Step 1", state: "done" }, { label: "Step 2", state: "active" }, { label: "Step 3" }]} />
      </Demo>

      <Demo title="Status, loader & note">
        <div style={{ width: "100%", display: "grid", gap: 10 }}>
          <Status s={{ kind: "info", msg: "Processing…", progress: true }} />
          <Status s={{ kind: "success", msg: "Done." }} />
          <Status s={{ kind: "error", msg: "Something went wrong." }} />
          <div className="loader"><div className="spin" /><div>Working…<br /><small className="muted">this can take a moment</small></div></div>
          <div className="note">7 domains → 3 clusters (modularity 0.71).</div>
        </div>
      </Demo>

      <Demo title="Cards, stats & pills">
        <div style={{ width: "100%", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 14 }}>
          <div className="stat dark"><span className="n">3,144</span><span className="l">species</span></div>
          <div className="stat light"><span className="n">218</span><span className="l">queries</span></div>
          <a className="tool-card" href="#"><div className="ic"><i className="fa-solid fa-dna" /></div><h3>Tool card</h3><p className="muted" style={{ margin: 0 }}>Hover lift.</p></a>
        </div>
        <div className="pill-tags"><span className="pill-tag"><i className="fa-solid fa-fire" /> heatmaps</span><span className="pill-tag"><i className="fa-solid fa-diagram-project" /> profiling</span></div>
      </Demo>

      <Demo title="Callouts & badges">
        <div style={{ width: "100%" }}>
          <span className="aud bio">For biologists</span> <span className="aud cs">For programmers</span>
          <div className="callout bio" style={{ marginTop: 10 }}><h4><i className="fa-solid fa-circle-info" /> Bio callout</h4>Left-accent info box.</div>
          <div className="callout cs"><h4><i className="fa-solid fa-circle-info" /> CS callout</h4>Left-accent info box.</div>
        </div>
      </Demo>
    </div>
  );
}

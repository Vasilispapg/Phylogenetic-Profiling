import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";

const TOKENS = [
  ["--void", "#0D0B1A", "page ground"],
  ["--panel", "#161230", "surfaces"],
  ["--rule", "#2C2560", "hairlines"],
  ["--dim", "#8983B5", "secondary text"],
  ["--paper", "#EDEBFA", "primary text"],
  ["--signal", "#E8E14B", "actions, presence"],
  ["--flow", "#35B7A8", "links, structure"],
  ["--warn", "#FF7B6E", "failure"],
];

const Demo = ({ title, hint, children }) => (
  <section style={{ margin: "2.4rem 0" }}>
    <h2 style={{ fontSize: "1.05rem" }}>{title}</h2>
    {hint && <p className="muted" style={{ fontSize: ".85rem", margin: "0 0 14px" }}>{hint}</p>}
    <div className="card card-pad" style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center" }}>
      {children}
    </div>
  </section>
);

export default function StyleGuide() {
  return (
    <div className="doc fade-up">
      <h1>Design system</h1>
      <p className="lead">
        The palette comes from viridis, the colormap this field already uses: an indigo floor and
        a chartreuse ceiling, so the chrome and the plots speak one language. Type is IBM Plex,
        with the mono carrying every label, count and identifier — because those really are codes.
      </p>

      <Demo title="Colour" hint="Signal is reserved for actions and for presence. Flow carries links and structure.">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 10, width: "100%" }}>
          {TOKENS.map(([name, hex, use]) => (
            <div key={name} style={{ border: "1px solid var(--rule)", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ background: hex, height: 42 }} />
              <div style={{ padding: "8px 10px" }}>
                <div className="k" style={{ color: "var(--paper)" }}>{name}</div>
                <div className="k">{hex}</div>
                <div style={{ fontSize: ".74rem", color: "var(--dim-2)", marginTop: 4 }}>{use}</div>
              </div>
            </div>
          ))}
        </div>
      </Demo>

      <Demo title="Type" hint="Display and headings in IBM Plex Mono; running text in IBM Plex Sans.">
        <div style={{ width: "100%" }}>
          <h1 style={{ margin: "0 0 6px" }}>Display · Plex Mono 600</h1>
          <h2 style={{ margin: "0 0 6px" }}>Heading · Plex Mono 600</h2>
          <p style={{ margin: "0 0 6px" }}>Body copy is Plex Sans at 15px with a 1.6 line height.</p>
          <p className="muted" style={{ margin: "0 0 10px" }}>Secondary copy sits on <code>--dim</code>.</p>
          <span className="eyebrow">Eyebrow · mono, tracked, uppercase</span>
        </div>
      </Demo>

      <Demo title="Buttons" hint="Uppercase mono labels. One primary per view.">
        <button className="btn btn-primary">Primary <span className="btn-ico"><i className="fa-solid fa-arrow-right" /></span></button>
        <button className="btn btn-secondary"><i className="fa-solid fa-download" /> Secondary</button>
        <button className="btn btn-ghost">Ghost</button>
        <button className="btn btn-primary" disabled>Disabled</button>
      </Demo>

      <Demo title="Inputs">
        <input className="input" placeholder="search species…" style={{ maxWidth: 260 }} />
        <select className="select" style={{ maxWidth: 200 }}><option>Viridis</option><option>Cividis</option></select>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--mono)", fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--dim)" }}>
          <input type="checkbox" defaultChecked /> Log
        </label>
      </Demo>

      <Demo title="Pipeline position" hint="Named stages with a dot marker — the name is the label.">
        <Stepper steps={[{ label: "Correlation matrix", state: "done" }, { label: "Cluster domains", state: "active" }, { label: "Read the report" }]} />
      </Demo>

      <Demo title="Feedback">
        <div style={{ width: "100%", display: "grid", gap: 10 }}>
          <Status s={{ kind: "info", msg: "Running Markov clustering (16,238 edges)…", progress: true }} />
          <Status s={{ kind: "success", msg: "Tree construction completed." }} />
          <Status s={{ kind: "error", msg: "That does not look like a Newick tree." }} />
          <div className="loader"><div className="spin" /> Working…</div>
          <div className="note">216 domains → 6 clusters (modularity 0.001).</div>
          <div className="note warn">Little community structure: the profiles are too uniform to form modules.</div>
        </div>
      </Demo>

      <Demo title="Data chrome" hint="The readout above a figure, and the chips that name a file or a stage.">
        <div style={{ width: "100%" }}>
          <div className="readout"><b>848</b> species × <b>216</b> domains · clustered · click a cell to inspect</div>
          <div className="pill-tags">
            <span className="pill-tag"><i className="fa-solid fa-file-lines" /> BLAST file</span>
            <span className="pill-tag"><i className="fa-solid fa-table-cells" /> matrix</span>
            <span className="pill-tag"><i className="fa-solid fa-share-nodes" /> modules</span>
          </div>
        </div>
      </Demo>

      <Demo title="Asides" hint="Two audiences read this app; the side rule says which one an aside is for.">
        <div style={{ width: "100%" }}>
          <span className="aud bio">For biologists</span> <span className="aud cs">For programmers</span>
          <div className="callout bio" style={{ marginTop: 12 }}>
            <h4><i className="fa-solid fa-circle-info" /> Presence is a threshold</h4>
            A domain counts as present at e-value ≤ 1e-5. Loosen it and co-occurrence inflates.
          </div>
          <div className="callout cs">
            <h4><i className="fa-solid fa-circle-info" /> Everything is a file</h4>
            Each step reads and writes a file you can open, so any stage can be checked on its own.
          </div>
        </div>
      </Demo>
    </div>
  );
}

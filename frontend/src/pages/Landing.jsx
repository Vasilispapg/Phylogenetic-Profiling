import { Link } from "react-router-dom";
import DnaHelix from "../components/DnaHelix.jsx";

const TOOLS = [
  ["/blast", "fa-dna", "BLAST Analysis", "Build the species × domain matrix from a BLAST file."],
  ["/tree-builder", "fa-sitemap", "Tree builder", "Neighbour-Joining species tree from domain profiles."],
  ["/tree-viewer", "fa-tree", "Tree viewer", "Collapsible radial tree — colour by genus, search, zoom."],
  ["/all-vs-all", "fa-share-nodes", "All-vs-all", "Cluster domains (MCL) as an interactive linked network."],
  ["/heatmap", "fa-fire", "Heatmaps", "Feature/correlation heatmaps with ordering, log scale, zoom."],
  ["/how-to", "fa-book-open", "How to use", "A plain-language guide for biologists and programmers."],
];
const POSTER = "https://f1000research-files.f1000.com/posters/compressed/f1000research-728675.pdf";

export default function Landing() {
  return (
    <div className="fade-up">
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1.05fr", gap: 24, alignItems: "center", minHeight: "64vh" }} className="hero-albus">
        <div>
          <div className="eyebrow" style={{ marginBottom: 14 }}>01 — phylogenetic profiling</div>
          <h1 className="display" style={{ fontSize: "clamp(2.7rem, 6vw, 4.6rem)", lineHeight: 1.0 }}>
            Phylogenetic<br />profiling,<br />by design.
          </h1>
          <p style={{ color: "var(--text-2)", fontSize: "1.06rem", maxWidth: 450, margin: "22px 0 28px", lineHeight: 1.7 }}>
            PhyloFlask reads presence/absence patterns of protein domains across thousands of proteomes —
            turning a BLAST search into interactive trees, clusters and heatmaps that reveal gene function
            and evolutionary links.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Link to="/blast" className="btn btn-accent">Learn more <i className="fa-solid fa-arrow-right" /></Link>
            <Link to="/how-to" className="btn btn-secondary">How it works</Link>
          </div>
        </div>
        <div><DnaHelix /></div>
      </section>

      <div className="section-head"><div className="eyebrow">The toolkit</div><h2>Five tools, one pipeline</h2></div>
      <div className="tools-grid">
        {TOOLS.map(([to, ic, h, p]) => (
          <Link key={to} to={to} className="tool-card">
            <div className="ic"><i className={"fa-solid " + ic} /></div>
            <h3>{h}</h3><p style={{ color: "var(--text-2)", margin: 0, fontSize: ".92rem" }}>{p}</p>
            <span className="more">Open <i className="fa-solid fa-arrow-right" /></span>
          </Link>
        ))}
      </div>

      <div className="section-head"><div className="eyebrow">About</div><h2>Built at the BCCB Group, AUTH</h2></div>
      <div className="card card-pad" style={{ marginBottom: 20 }}>
        <p><strong>PhyloFlask</strong> — by <strong>A. Michailidis, V. S. Papagrigoriou &amp; C. A. Ouzounis</strong>
           (Biological Computation &amp; Computational Biology Group, Aristotle University of Thessaloniki). Scalable
           visual inference of gene function and evolutionary relationships from presence/absence patterns across genomes.</p>
        <p style={{ marginTop: 12 }}>
          <a href={POSTER} className="btn btn-secondary" target="_blank" rel="noopener noreferrer"><i className="fa-solid fa-file-pdf" /> Read the poster</a>
        </p>
        <p className="muted" style={{ fontSize: ".9rem", marginTop: 12 }}>
          Reference: Cohen BA, Mitra RD, Hughes JD &amp; Church GM (2000). <em>Nature Genetics</em> 26(2), 183–186.{" "}
          <a href="https://doi.org/10.1038/79896" target="_blank" rel="noopener noreferrer">doi:10.1038/79896</a>
        </p>
      </div>
    </div>
  );
}

import { Link } from "react-router-dom";
import Molecule from "../components/Molecule.jsx";

const TAGS = [
  ["fa-diagram-project", "phylogenetic profiling"], ["fa-magnifying-glass", "BLAST"],
  ["fa-sitemap", "Neighbour-Joining"], ["fa-share-nodes", "Markov clustering"],
  ["fa-fire", "heatmaps"], ["fa-dna", "bioinformatics"],
];
const TOOLS = [
  ["/blast", "fa-dna", "BLAST Analysis", "Build the species × domain correlation or feature matrix from a BLAST file."],
  ["/tree-builder", "fa-sitemap", "Tree builder", "Neighbour-Joining species tree from Jaccard distances between profiles."],
  ["/tree-viewer", "fa-tree", "Tree viewer", "Collapsible radial tree — colour by genus, search a species, zoom."],
  ["/all-vs-all", "fa-share-nodes", "All-vs-all", "Cluster domains (MCL) into an interactive network linked to a co-cluster heatmap."],
  ["/heatmap", "fa-fire", "Heatmaps", "Feature/correlation heatmaps with ordering, log scale, zoom and cell details."],
  ["/how-to", "fa-book-open", "How to use", "A plain-language guide for biologists and programmers alike."],
];
const POSTER = "https://f1000research-files.f1000.com/posters/compressed/f1000research-728675.pdf";

export default function Landing() {
  return (
    <div className="fade-up">
      <section className="hero">
        <div className="hero-left">
          <div className="stat-row">
            <div className="stat dark"><span className="n">3,144</span><span className="l">reference species</span></div>
            <div className="stat light"><span className="n">218</span><span className="l">query proteins</span></div>
            <div className="feature">
              <span className="play"><i className="fa-solid fa-play" /></span>
              <div><strong>Watch the idea</strong><br /><small>How phylogenetic profiling works</small></div>
            </div>
          </div>
          <h1 className="display">Large&#8209;scale<br />phylogenetic<br />profiling</h1>
          <p className="sub">Turn a BLAST search into interactive species trees, domain clusters and
             heatmaps — explore presence/absence patterns across whole proteomes and read gene function
             straight from the data.</p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Link to="/blast" className="btn btn-primary">Get started <i className="fa-solid fa-arrow-right" /></Link>
            <Link to="/how-to" className="btn btn-secondary">Learn more</Link>
          </div>
        </div>

        <div className="hero-art">
          <Molecule />
          <div className="glass">
            <div><div className="t">Get started</div><small>upload a BLAST file &amp; explore</small></div>
            <Link to="/blast" className="go"><i className="fa-solid fa-arrow-right" /></Link>
          </div>
        </div>
      </section>

      <div className="pill-tags" style={{ marginTop: 34 }}>
        {TAGS.map(([ic, t]) => <span key={t} className="pill-tag"><i className={"fa-solid " + ic} /> {t}</span>)}
      </div>

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
        <p><strong>PhyloFlask</strong> — a software framework for large-scale phylogenetic profile
           visualization by <strong>A. Michailidis, V. S. Papagrigoriou &amp; C. A. Ouzounis</strong>
           (Biological Computation &amp; Computational Biology Group, AUTH). It analyses presence/absence
           patterns of protein domains across thousands of reference proteomes for rapid visual inference
           of gene function and evolutionary relationships.</p>
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

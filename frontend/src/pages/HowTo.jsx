import { Link } from "react-router-dom";

const TOOLS = [
  ["fa-dna", "BLAST Analysis", "Reads a BLAST results file → species × domain matrix. Run first.",
    "BLAST -outfmt 6 file. A hit counts as present when E-value ≤ 1e-5."],
  ["fa-sitemap", "Tree builder", "Neighbour-Joining species tree from domain profiles.",
    "Distance = Jaccard between presence/absence profiles. Input: correlation matrix CSV."],
  ["fa-tree", "Tree viewer", "Interactive radial viewer for any Newick tree.",
    "Click to collapse/expand, search a species, colour by genus, zoom."],
  ["fa-share-nodes", "All-vs-all", "Clusters domains that share a profile (MCL) as a network.",
    "Node colour = cluster, size = links; slider prunes weak edges; linked co-cluster heatmap."],
  ["fa-fire", "Heatmaps", "Colour grid of the matrix across species and domains.",
    "Pick a feature, filter, toggle log/order, zoom, click cells."],
];
const GLOSS = [
  ["Domain", "A functional part of a protein", "A column / a graph node"],
  ["Species", "An organism / proteome", "A row / a tree leaf"],
  ["Profile", "Presence/absence across species", "A binary vector of 0s and 1s"],
  ["Jaccard", "How much two repertoires overlap", "shared / union of two sets"],
  ["Cluster", "A candidate functional module", "A community of connected nodes"],
];

export default function HowTo() {
  return (
    <div className="doc fade-up">
      <h1>How to use PhyloFlask</h1>
      <p className="lead">A plain-language guide written so a <strong>biologist who has never coded</strong> and a
         <strong> programmer who has never opened a genome</strong> can both run the whole analysis.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 14, margin: "1rem 0" }}>
        <div className="card card-pad"><span className="aud bio">For biologists</span>
          <p style={{ marginTop: 10, color: "var(--text-2)" }}>You bring the question and the BLAST file. We explain every
             button and what the numbers mean — no programming, all in your browser.</p></div>
        <div className="card card-pad"><span className="aud cs">For programmers</span>
          <p style={{ marginTop: 10, color: "var(--text-2)" }}>You know files and matrices. We explain the biology — genomes,
             domains, homology, profiles — so the inputs and outputs make sense.</p></div>
      </div>

      <h2>The 30-second idea</h2>
      <p>Some proteins are gained and lost together across species through evolution. If two are almost always present
         in the same organisms (and absent in the same ones), they probably do related jobs. PhyloFlask measures these
         <strong> presence/absence patterns</strong> and turns them into interactive trees, clusters and heatmaps.</p>

      <div className="pill-tags" style={{ margin: "1rem 0 1.5rem" }}>
        <span className="pill-tag"><i className="fa-solid fa-file-lines" /> BLAST file</span>
        <span className="pill-tag"><i className="fa-solid fa-table-cells" /> Matrix</span>
        <span className="pill-tag"><i className="fa-solid fa-sitemap" /> Tree</span>
        <span className="pill-tag"><i className="fa-solid fa-share-nodes" /> Clusters</span>
        <span className="pill-tag"><i className="fa-solid fa-fire" /> Heatmaps</span>
      </div>

      <h2>Every tool</h2>
      {TOOLS.map(([ic, h, what, why]) => (
        <div key={h} className="card card-pad" style={{ marginBottom: 12 }}>
          <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, background: "var(--ink)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
              <i className={"fa-solid " + ic} /></span>{h}</h3>
          <p style={{ margin: "0 0 4px" }}>{what}</p>
          <p className="muted" style={{ margin: 0, fontSize: ".92rem" }}>{why}</p>
        </div>
      ))}

      <h2>Reading the results</h2>
      <p>Short tree branches between two species = very similar domain content. Domains in one cluster colour co-occur —
         a hypothesis they share a function. <strong>Modularity Q ≈ 0</strong> means no real grouping (profiles too uniform);
         <strong> Q &gt; 0.3</strong> means clear, trustworthy modules.</p>

      <h2>Glossary</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".95rem", background: "var(--surface)", borderRadius: 14, overflow: "hidden", boxShadow: "var(--shadow)", border: "1px solid var(--line)" }}>
        <thead><tr>{["Term", "In biology", "In computing"].map((h) => <th key={h} style={{ textAlign: "left", padding: "11px 14px", background: "var(--surface-2)" }}>{h}</th>)}</tr></thead>
        <tbody>{GLOSS.map(([t, b, c]) => (
          <tr key={t}><td style={{ padding: "11px 14px", fontWeight: 700, borderTop: "1px solid var(--line)" }}>{t}</td>
            <td style={{ padding: "11px 14px", borderTop: "1px solid var(--line)" }}>{b}</td>
            <td style={{ padding: "11px 14px", borderTop: "1px solid var(--line)" }}>{c}</td></tr>))}</tbody>
      </table>

      <div style={{ display: "flex", gap: 10, marginTop: 24, flexWrap: "wrap" }}>
        <Link to="/blast" className="btn btn-primary"><i className="fa-solid fa-play" /> Start with BLAST Analysis</Link>
        <Link to="/faq" className="btn btn-secondary"><i className="fa-solid fa-circle-question" /> Read the FAQ</Link>
      </div>
    </div>
  );
}

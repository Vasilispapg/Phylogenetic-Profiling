import { Link } from "react-router-dom";

const SECTIONS = [
  ["Concepts", [
    ["What is phylogenetic profiling?", "Genes/domains gained and lost together across evolution tend to be functionally related. A phylogenetic profile is a domain's presence/absence pattern across species; similar profiles suggest shared function."],
    ["What counts as “present”?", "A BLAST hit with E-value ≤ 1e-5 (configurable). Counting weak hits would inflate co-occurrence and wash out the signal."],
    ["Domain vs species?", "The BLAST query id is the domain; the subject id encodes the species (first four dash-segments, e.g. UP000005640-00009606-Homo_sapi-22)."],
  ]],
  ["Methods", [
    ["How is the species tree built?", "Pairwise Jaccard distance between binary domain profiles, then Neighbour-Joining. Branch lengths are in Jaccard units."],
    ["How are domains clustered?", "A domain × domain graph (edge when Jaccard ≥ threshold), then Markov Clustering (MCL). Clusters are co-occurring domains — candidate modules."],
    ["Is the clustering meaningful?", "We report modularity Q (≈0 = none, >0.3 = clear), cluster sizes, and a same-protein co-clustering rate. A warning shows when everything collapses into one cluster."],
  ]],
  ["Usage & troubleshooting", [
    ["In what order do I use the tools?", "BLAST Analysis first → correlation matrix → Tree builder / All-vs-all / Heatmaps. Open built .nw trees in the Tree viewer."],
    ["Blank / “AirTunes” page on :5000?", "On macOS, AirPlay owns ports 5000/7000. The backend runs on http://127.0.0.1:8000."],
    ["The network looks crowded", "Labels appear on zoom; raise the min-similarity slider, click a node to isolate its cluster, or switch layout."],
  ]],
];
const POSTER = "https://f1000research-files.f1000.com/posters/compressed/f1000research-728675.pdf";

export default function Faq() {
  return (
    <div className="doc fade-up">
      <h1>FAQ &amp; concepts</h1>
      <p className="lead">The science behind PhyloFlask and how to read the results. New here? Start with{" "}
        <Link to="/how-to">How to use</Link>.</p>

      {SECTIONS.map(([title, items]) => (
        <div key={title}>
          <h2 style={{ color: "var(--accent)", fontSize: "1.2rem" }}>{title}</h2>
          {items.map(([q, a]) => (
            <details key={q} className="card" style={{ padding: "0 1.2rem", marginBottom: 10 }}>
              <summary style={{ cursor: "pointer", padding: "15px 0", fontWeight: 600, listStyle: "none" }}>{q}</summary>
              <p style={{ padding: "0 0 16px", margin: 0, color: "var(--text)" }}>{a}</p>
            </details>
          ))}
        </div>
      ))}

      <div className="card card-pad" style={{ marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>About &amp; credits</h2>
        <p><strong>PhyloFlask</strong> — by A. Michailidis, V. S. Papagrigoriou &amp; C. A. Ouzounis,
           BCCB Group, Aristotle University of Thessaloniki.</p>
        <p><a className="btn btn-secondary" href={POSTER} target="_blank" rel="noopener noreferrer"><i className="fa-solid fa-file-pdf" /> Poster (F1000, p. 104)</a></p>
        <p className="muted" style={{ fontSize: ".9rem" }}>Reference: Cohen BA, Mitra RD, Hughes JD &amp; Church GM (2000).
           <em> Nature Genetics</em> 26(2), 183–186. <a href="https://doi.org/10.1038/79896" target="_blank" rel="noopener noreferrer">doi:10.1038/79896</a></p>
      </div>
    </div>
  );
}

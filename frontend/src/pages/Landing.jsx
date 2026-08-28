import { Link } from "react-router-dom";
import ProfileGrid from "../components/ProfileGrid.jsx";
import { POSTER, PROFILING_DOI } from "../lib/links.js";

// Each tool is a typed transform, so the index says what goes in and what comes
// out. That is the thing a researcher is actually choosing between.
const TOOLS = [
  ["/blast", "fa-align-left", "BLAST analysis", "Count hits per species and domain, at or below your e-value cutoff.", "blast tsv → matrix"],
  ["/heatmap", "fa-table-cells", "Heatmap", "Read one metric at a time, or two side by side; click any cell for the rest.", "matrix → figure"],
  ["/clustergram", "fa-bars-staggered", "Clustergram", "Reorder both axes by profile similarity, with dendrograms on each.", "matrix → blocks"],
  ["/explorer", "fa-diagram-project", "Linked explorer", "Clustered heatmap and domain network, sharing one selection.", "matrix → two views"],
  ["/embedding", "fa-braille", "Embedding map", "Project profiles to 2D with PCA or t-SNE; search and isolate groups.", "matrix → 2D map"],
  ["/all-vs-all", "fa-share-nodes", "All-vs-all", "Markov clustering over the domain similarity graph, with a quality report.", "matrix → modules"],
  ["/tree-builder", "fa-code-branch", "Tree builder", "Neighbour-Joining or UPGMA over Jaccard distances between profiles.", "matrix → newick"],
  ["/tree-viewer", "fa-sitemap", "Tree viewer", "Radial tree you can collapse, search and colour by genus.", "newick → figure"],
];

const PIPELINE = [
  ["01", "Call presence", "A domain counts as present in a proteome when BLAST finds a hit at or below 1e-5. Everything downstream rests on that one cutoff.", "BLAST tabular", "species × domain matrix"],
  ["02", "Compare profiles", "Two domains with the same presence pattern have been gained and lost together. Jaccard similarity puts a number on it.", "matrix", "similarity"],
  ["03", "Find the structure", "Cluster, project or build a tree — and read the quality report before you believe any of it.", "similarity", "modules, trees, maps"],
];

export default function Landing() {
  return (
    <div className="fade-up">
      <section className="hero">
        <div>
          <div className="hero-kicker">
            <span className="tick" />
            <span className="eyebrow">Comparative genomics</span>
          </div>
          <h1><span className="lo">What vanishes<br />together,</span><br />works together.</h1>
          <p className="sub">
            Protein domains that are gained and lost in the same genomes tend to sit in the
            same pathway. PhyloFlask turns a BLAST search into the matrix, the modules and
            the tree that show it — and tells you when the pattern is not really there.
          </p>
          <div className="actions">
            <Link to="/blast" className="btn btn-primary">
              Load a BLAST file <span className="btn-ico"><i className="fa-solid fa-arrow-right" /></span>
            </Link>
            <Link to="/faq" className="btn btn-secondary">Read the method</Link>
          </div>
        </div>
        <ProfileGrid />
      </section>

      <section className="section" style={{ marginTop: 0 }}>
        <div className="section-head"><span className="eyebrow">Method</span><h2>Three steps, one cutoff</h2></div>
        <p className="section-sub">
          The whole pipeline is a chain of small, checkable transforms. Each tool below is one
          link in it, and each keeps its inputs and outputs as files you can inspect.
        </p>
        <div className="pipeline">
          {PIPELINE.map(([n, title, body, from, to]) => (
            <div className="pipe-step" key={n}>
              <div className="n">{n}</div>
              <h3>{title}</h3>
              <p>{body}</p>
              <div className="io">{from} <b>→</b> {to}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head"><span className="eyebrow">Tools</span><h2>Eight transforms</h2></div>
        <div className="index">
          {TOOLS.map(([to, ic, name, desc, io]) => (
            <Link key={to} to={to} className="index-row">
              <span className="ic"><i className={"fa-solid " + ic} /></span>
              <span className="nm">{name}</span>
              <span className="ds">{desc}</span>
              <span className="io">{io}</span>
              <span className="go"><i className="fa-solid fa-arrow-right" /></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head"><span className="eyebrow">Credit</span><h2>Where this comes from</h2></div>
        <div className="credit">
          <div>
            <p className="who">A. Michailidis · V. S. Papagrigoriou · C. A. Ouzounis</p>
            <p>
              Biological Computation &amp; Computational Biology Group, Aristotle University of
              Thessaloniki. The method is phylogenetic profiling as introduced by Pellegrini et al.
              and applied at proteome scale here.
            </p>
            <p className="dimmer" style={{ fontSize: ".82rem" }}>
              Cohen BA, Mitra RD, Hughes JD &amp; Church GM (2000). Nature Genetics 26(2), 183–186.{" "}
              <a href={PROFILING_DOI} target="_blank" rel="noopener noreferrer">doi:10.1038/79896</a>
            </p>
          </div>
          <a href={POSTER} className="btn btn-secondary" target="_blank" rel="noopener noreferrer">
            <i className="fa-solid fa-file-pdf" /> Poster
          </a>
        </div>
      </section>
    </div>
  );
}

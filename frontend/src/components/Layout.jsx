import { NavLink, Link, Outlet } from "react-router-dom";

const LINKS = [
  ["/", "Home"],
  ["/blast", "BLAST"],
  ["/heatmap", "Heatmap"],
  ["/all-vs-all", "All-vs-all"],
  ["/tree-viewer", "Tree viewer"],
  ["/tree-builder", "Tree builder"],
  ["/how-to", "How to use"],
  ["/faq", "FAQ"],
];

const POSTER = "https://f1000research-files.f1000.com/posters/compressed/f1000research-728675.pdf";

export default function Layout() {
  return (
    <>
      <header className="navbar">
        <div className="navbar-inner">
          <Link to="/" className="logo"><i className="fa-solid fa-dna" /> PhyloFlask</Link>
          <nav className="links">
            {LINKS.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>
            ))}
          </nav>
          <span className="spacer" />
          <Link to="/blast" className="btn btn-primary" style={{ padding: "7px 8px 7px 18px", fontSize: ".9rem" }}>
            Start now <span className="btn-ico"><i className="fa-solid fa-arrow-right" /></span>
          </Link>
        </div>
      </header>

      <main className="main"><Outlet /></main>

      <footer className="footer">
        <div className="cols">
          <div>
            <Link to="/" className="brand"><i className="fa-solid fa-dna" /> PhyloFlask</Link>
            <p>Large-scale phylogenetic profile visualization — turn a BLAST search into interactive
               species trees, domain clusters and heatmaps.</p>
          </div>
          <div>
            <h4>Tools</h4>
            <ul>
              <li><Link to="/blast">BLAST Analysis</Link></li>
              <li><Link to="/tree-builder">Tree builder</Link></li>
              <li><Link to="/tree-viewer">Tree viewer</Link></li>
              <li><Link to="/all-vs-all">All-vs-all</Link></li>
              <li><Link to="/heatmap">Heatmaps</Link></li>
            </ul>
          </div>
          <div>
            <h4>Resources</h4>
            <ul>
              <li><Link to="/how-to">How to use</Link></li>
              <li><Link to="/faq">FAQ &amp; concepts</Link></li>
              <li><Link to="/styleguide">Design system</Link></li>
              <li><a href={POSTER} target="_blank" rel="noopener noreferrer">Poster (F1000)</a></li>
            </ul>
          </div>
        </div>
        <div className="bottom"><div>
          <span>© PhyloFlask · BCCB Group, Aristotle University of Thessaloniki</span>
          <span>A. Michailidis · V. S. Papagrigoriou · C. A. Ouzounis</span>
        </div></div>
      </footer>
    </>
  );
}

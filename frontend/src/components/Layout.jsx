import { useEffect, useState } from "react";
import { NavLink, Link, Outlet, useLocation } from "react-router-dom";
import { POSTER } from "../lib/links.js";

const TOOLS = [
  { to: "/blast", icon: "fa-dna", label: "BLAST analysis", desc: "Build the species × domain matrix" },
  { to: "/heatmap", icon: "fa-fire", label: "Heatmap", desc: "Feature / correlation heatmaps" },
  { to: "/clustergram", icon: "fa-border-all", label: "Clustergram", desc: "Clustered heatmap + dendrograms" },
  { to: "/explorer", icon: "fa-diagram-project", label: "Linked explorer", desc: "Heatmap ↔ network, synced" },
  { to: "/embedding", icon: "fa-braille", label: "Embedding map", desc: "2D PCA / t-SNE projection" },
  { to: "/all-vs-all", icon: "fa-share-nodes", label: "All-vs-all", desc: "Domain network (MCL)" },
  { to: "/tree-viewer", icon: "fa-tree", label: "Tree viewer", desc: "Interactive species tree" },
  { to: "/tree-builder", icon: "fa-sitemap", label: "Tree builder", desc: "Neighbour-Joining tree" },
];

export default function Layout() {
  const [openTools, setOpenTools] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => { setOpenTools(false); setMobileOpen(false); }, [loc.pathname]);
  const toolActive = TOOLS.some((t) => t.to === loc.pathname);

  return (
    <>
      <header className="navbar">
        <div className="navbar-inner">
          <Link to="/" className="logo"><i className="fa-solid fa-dna" /> PhyloFlask</Link>
          <nav className="links">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Home</NavLink>
            <div className="nav-dd" onMouseEnter={() => setOpenTools(true)} onMouseLeave={() => setOpenTools(false)}>
              <button className={"nav-dd-trigger" + (toolActive ? " active" : "")} onClick={() => setOpenTools((o) => !o)} aria-expanded={openTools}>
                Tools <i className="fa-solid fa-chevron-down" style={{ fontSize: ".62em", opacity: 0.7 }} />
              </button>
              {openTools && <div className="nav-dd-panel">
                <div className="nav-dd-card">
                  {TOOLS.map((t) => (
                    <NavLink key={t.to} to={t.to} className={({ isActive }) => "nav-dd-item" + (isActive ? " active" : "")}>
                      <span className="nav-dd-ic"><i className={"fa-solid " + t.icon} /></span>
                      <span><span className="nav-dd-label">{t.label}</span><span className="nav-dd-desc">{t.desc}</span></span>
                    </NavLink>
                  ))}
                </div>
              </div>}
            </div>
            <NavLink to="/how-to" className={({ isActive }) => (isActive ? "active" : "")}>How to use</NavLink>
            <NavLink to="/faq" className={({ isActive }) => (isActive ? "active" : "")}>FAQ</NavLink>
          </nav>
          <span className="spacer" />
          <Link to="/blast" className="btn btn-primary nav-cta" style={{ padding: "7px 8px 7px 18px", fontSize: ".9rem" }}>
            Start now <span className="btn-ico"><i className="fa-solid fa-arrow-right" /></span>
          </Link>
          <button className="nav-burger" onClick={() => setMobileOpen((o) => !o)} aria-label="Menu" aria-expanded={mobileOpen}>
            <i className={"fa-solid " + (mobileOpen ? "fa-xmark" : "fa-bars")} />
          </button>
        </div>
        {mobileOpen && <div className="mobile-menu">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Home</NavLink>
          <div className="mobile-menu-head">Tools</div>
          {TOOLS.map((t) => (
            <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? "active" : "")}><i className={"fa-solid " + t.icon} /> {t.label}</NavLink>
          ))}
          <div className="mobile-menu-head">More</div>
          <NavLink to="/how-to" className={({ isActive }) => (isActive ? "active" : "")}>How to use</NavLink>
          <NavLink to="/faq" className={({ isActive }) => (isActive ? "active" : "")}>FAQ</NavLink>
          <Link to="/blast" className="btn btn-primary" style={{ marginTop: 10, width: "100%", justifyContent: "center" }}>Start now</Link>
        </div>}
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
              <li><Link to="/clustergram">Clustergram</Link></li>
              <li><Link to="/explorer">Linked explorer</Link></li>
              <li><Link to="/embedding">Embedding map</Link></li>
              <li><Link to="/all-vs-all">All-vs-all</Link></li>
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

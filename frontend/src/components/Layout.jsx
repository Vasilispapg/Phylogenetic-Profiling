import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { POSTER } from "../lib/links.js";

const TOOLS = [
  { to: "/blast", icon: "fa-align-left", label: "BLAST analysis", desc: "hits → matrix" },
  { to: "/heatmap", icon: "fa-table-cells", label: "Heatmap", desc: "matrix → picture" },
  { to: "/clustergram", icon: "fa-bars-staggered", label: "Clustergram", desc: "matrix → blocks" },
  { to: "/explorer", icon: "fa-diagram-project", label: "Linked explorer", desc: "blocks ↔ network" },
  { to: "/embedding", icon: "fa-braille", label: "Embedding map", desc: "profiles → 2D" },
  { to: "/all-vs-all", icon: "fa-share-nodes", label: "All-vs-all", desc: "matrix → modules" },
  { to: "/tree-builder", icon: "fa-code-branch", label: "Tree builder", desc: "matrix → tree" },
  { to: "/tree-viewer", icon: "fa-sitemap", label: "Tree viewer", desc: "tree → view" },
];

/** The wordmark: two columns of a presence/absence profile. */
function Mark() {
  return (
    <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true" focusable="false">
      <g fill="currentColor">
        <rect x="0" y="0" width="5" height="3" /><rect x="0" y="6.5" width="5" height="3" />
        <rect x="0" y="13" width="5" height="3" />
        <rect x="9" y="0" width="5" height="3" opacity=".35" /><rect x="9" y="6.5" width="5" height="3" />
        <rect x="9" y="13" width="5" height="3" opacity=".35" />
      </g>
    </svg>
  );
}

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
          <Link to="/" className="logo"><Mark /> PhyloFlask</Link>
          <nav className="links">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Overview</NavLink>
            <div className="nav-dd" onMouseEnter={() => setOpenTools(true)} onMouseLeave={() => setOpenTools(false)}>
              <button className={"nav-dd-trigger" + (toolActive ? " active" : "")}
                      onClick={() => setOpenTools((o) => !o)} aria-expanded={openTools}>
                Tools <i className="fa-solid fa-chevron-down" style={{ fontSize: ".55em" }} />
              </button>
              {openTools && (
                <div className="nav-dd-panel">
                  <div className="nav-dd-card">
                    {TOOLS.map((t) => (
                      <NavLink key={t.to} to={t.to} className={({ isActive }) => "nav-dd-item" + (isActive ? " active" : "")}>
                        <span className="nav-dd-ic"><i className={"fa-solid " + t.icon} /></span>
                        <span>
                          <span className="nav-dd-label">{t.label}</span>
                          <span className="nav-dd-desc">{t.desc}</span>
                        </span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <NavLink to="/how-to" className={({ isActive }) => (isActive ? "active" : "")}>How-to</NavLink>
            <NavLink to="/faq" className={({ isActive }) => (isActive ? "active" : "")}>Method</NavLink>
          </nav>
          <span className="spacer" />
          <Link to="/blast" className="btn btn-primary nav-cta">Load a file</Link>
          <button className="nav-burger" onClick={() => setMobileOpen((o) => !o)} aria-label="Menu" aria-expanded={mobileOpen}>
            <i className={"fa-solid " + (mobileOpen ? "fa-xmark" : "fa-bars")} />
          </button>
        </div>
        {mobileOpen && (
          <div className="mobile-menu">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>Overview</NavLink>
            <div className="mobile-menu-head">Tools</div>
            {TOOLS.map((t) => (
              <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? "active" : "")}>{t.label}</NavLink>
            ))}
            <div className="mobile-menu-head">Reference</div>
            <NavLink to="/how-to" className={({ isActive }) => (isActive ? "active" : "")}>How-to</NavLink>
            <NavLink to="/faq" className={({ isActive }) => (isActive ? "active" : "")}>Method</NavLink>
          </div>
        )}
      </header>

      <main className="main"><Outlet /></main>

      <footer className="footer">
        <div className="cols">
          <div>
            <Link to="/" className="brand"><Mark /> PhyloFlask</Link>
            <p>Presence and absence of protein domains across proteomes, clustered until
               the pattern is readable. Built at the BCCB Group, Aristotle University of Thessaloniki.</p>
          </div>
          <div>
            <h4>Tools</h4>
            <ul>{TOOLS.slice(0, 5).map((t) => <li key={t.to}><Link to={t.to}>{t.label}</Link></li>)}</ul>
          </div>
          <div>
            <h4>Reference</h4>
            <ul>
              <li><Link to="/how-to">How-to</Link></li>
              <li><Link to="/faq">Method &amp; FAQ</Link></li>
              <li><Link to="/styleguide">Design system</Link></li>
              <li><a href={POSTER} target="_blank" rel="noopener noreferrer">Poster (F1000)</a></li>
            </ul>
          </div>
        </div>
        <div className="bottom">
          <div>
            <span>A. Michailidis · V. S. Papagrigoriou · C. A. Ouzounis</span>
            <span>BCCB Group · AUTH</span>
          </div>
        </div>
      </footer>
    </>
  );
}

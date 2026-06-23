// Premium 3D molecule / profile-network hero art (self-contained SVG).
const SVG = `
<svg viewBox="0 0 520 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true" style="position:absolute;inset:0;width:100%;height:100%">
  <defs>
    <radialGradient id="m-bg" cx="66%" cy="20%" r="80%"><stop offset="0%" stop-color="#27407f" stop-opacity="0.65"/><stop offset="100%" stop-color="#27407f" stop-opacity="0"/></radialGradient>
    <radialGradient id="m-blue" cx="35%" cy="30%" r="75%"><stop offset="0%" stop-color="#aeccff"/><stop offset="45%" stop-color="#3f7bff"/><stop offset="100%" stop-color="#1b3ea8"/></radialGradient>
    <radialGradient id="m-teal" cx="35%" cy="30%" r="75%"><stop offset="0%" stop-color="#7df0da"/><stop offset="45%" stop-color="#10c0a4"/><stop offset="100%" stop-color="#067160"/></radialGradient>
    <radialGradient id="m-coral" cx="35%" cy="30%" r="75%"><stop offset="0%" stop-color="#ffa9ba"/><stop offset="45%" stop-color="#e9526c"/><stop offset="100%" stop-color="#9c1c39"/></radialGradient>
    <radialGradient id="m-amber" cx="35%" cy="30%" r="75%"><stop offset="0%" stop-color="#ffe0a0"/><stop offset="45%" stop-color="#ffb528"/><stop offset="100%" stop-color="#bd7800"/></radialGradient>
    <radialGradient id="m-violet" cx="35%" cy="30%" r="75%"><stop offset="0%" stop-color="#cfc4ff"/><stop offset="45%" stop-color="#8466ff"/><stop offset="100%" stop-color="#4a31bf"/></radialGradient>
    <filter id="m-soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="m-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000" flood-opacity="0.45"/></filter>
  </defs>
  <rect width="520" height="480" fill="url(#m-bg)"/>
  <g stroke="rgba(255,255,255,0.22)" stroke-width="2" stroke-linecap="round" filter="url(#m-soft)">
    <line x1="150" y1="125" x2="250" y2="185"/><line x1="250" y1="185" x2="360" y2="130"/>
    <line x1="250" y1="185" x2="215" y2="305"/><line x1="215" y1="305" x2="335" y2="335"/>
    <line x1="360" y1="130" x2="425" y2="245"/><line x1="425" y1="245" x2="335" y2="335"/>
    <line x1="150" y1="125" x2="115" y2="255"/><line x1="115" y1="255" x2="215" y2="305"/>
    <line x1="360" y1="130" x2="335" y2="335"/><line x1="250" y1="185" x2="115" y2="255"/>
  </g>
  <g filter="url(#m-shadow)">
    <g><circle cx="115" cy="255" r="17" fill="url(#m-violet)"/><ellipse cx="109" cy="248" rx="6" ry="4" fill="#fff" opacity="0.55"/></g>
    <g><circle cx="425" cy="245" r="19" fill="url(#m-amber)"/><ellipse cx="418" cy="237" rx="7" ry="4.5" fill="#fff" opacity="0.55"/></g>
    <g><circle cx="150" cy="125" r="22" fill="url(#m-blue)"/><ellipse cx="142" cy="116" rx="8" ry="5" fill="#fff" opacity="0.6"/></g>
    <g><circle cx="360" cy="130" r="24" fill="url(#m-coral)"/><ellipse cx="351" cy="120" rx="8" ry="5" fill="#fff" opacity="0.6"/></g>
    <g><circle cx="335" cy="335" r="24" fill="url(#m-teal)"/><ellipse cx="326" cy="325" rx="8" ry="5" fill="#fff" opacity="0.6"/></g>
    <g><circle cx="215" cy="305" r="28" fill="url(#m-blue)"/><ellipse cx="205" cy="294" rx="9" ry="5.5" fill="#fff" opacity="0.6"/></g>
    <g><circle cx="250" cy="185" r="34" fill="url(#m-teal)"/><ellipse cx="238" cy="172" rx="11" ry="6.5" fill="#fff" opacity="0.6"/></g>
  </g>
</svg>`;

export default function Molecule() {
  return <div className="molecule" dangerouslySetInnerHTML={{ __html: SVG }} />;
}

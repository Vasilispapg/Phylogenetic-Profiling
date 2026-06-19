// A clean 3D DNA double-helix with stat callouts (connector lines + markers).
export default function DnaHelix() {
  const W = 660, H = 560, cx = 235, amp = 88, top = 44, bottom = 520, turns = 3, steps = 70;
  const A = [], B = [], rungs = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, y = top + (bottom - top) * t, a = t * turns * 2 * Math.PI;
    const xa = cx + amp * Math.sin(a), xb = cx + amp * Math.sin(a + Math.PI);
    A.push([xa, y]); B.push([xb, y]);
    if (i % 2 === 0) rungs.push({ xa, xb, y, depth: (Math.cos(a) + 1) / 2 });
  }
  const path = (pts) => "M" + pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" L");
  const at = (t) => { const y = top + (bottom - top) * t, a = t * turns * 2 * Math.PI; return [cx + amp * Math.sin(a), y]; };

  const callouts = [
    { p: at(0.12), lx: 520, ly: 92, end: 470, n: "3,144", l: ["reference", "species"] },
    { p: at(0.52), lx: 524, ly: 290, end: 470, n: "218", l: ["query", "proteins"] },
    { p: at(0.88), lx: 430, ly: 520, end: 380, n: "108K", l: ["BLAST", "hits"] },
  ];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }} aria-hidden="true">
      <defs>
        <linearGradient id="strand" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#dfe5ee" /><stop offset="55%" stopColor="#b9c2d3" /><stop offset="100%" stopColor="#97a2b8" />
        </linearGradient>
        <linearGradient id="rung" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#cdd5e2" /><stop offset="100%" stopColor="#aab4c8" />
        </linearGradient>
        <filter id="dna-shadow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="6" stdDeviation="9" floodColor="#1b2440" floodOpacity="0.14" />
        </filter>
      </defs>

      <g filter="url(#dna-shadow)">
        {rungs.map((r, i) => (
          <line key={i} x1={r.xa} y1={r.y} x2={r.xb} y2={r.y} stroke="url(#rung)" strokeLinecap="round"
                strokeWidth={2.5 + r.depth * 5} opacity={0.35 + r.depth * 0.6} />
        ))}
        <path d={path(B)} fill="none" stroke="url(#strand)" strokeWidth="9" strokeLinecap="round" opacity="0.85" />
        <path d={path(A)} fill="none" stroke="url(#strand)" strokeWidth="10" strokeLinecap="round" />
        <path d={path(A)} fill="none" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" opacity="0.5" />
      </g>

      {callouts.map((c, i) => (
        <g key={i}>
          <line x1={c.p[0]} y1={c.p[1]} x2={c.end} y2={c.ly} stroke="#e11d48" strokeWidth="1.4" />
          <line x1={c.end} y1={c.ly} x2={c.lx - 14} y2={c.ly} stroke="#e11d48" strokeWidth="1.4" />
          <circle cx={c.p[0]} cy={c.p[1]} r="5" fill="#fff" stroke="#e11d48" strokeWidth="2.5" />
          <text x={c.lx} y={c.ly - 2} fontFamily="Space Grotesk, sans-serif" fontWeight="700" fontSize="26" fill="#14181f">{c.n}</text>
          <text x={c.lx} y={c.ly + 14} fontFamily="Inter, sans-serif" fontSize="10.5" letterSpacing="1.2" fill="#8b93a5">{c.l[0].toUpperCase()}</text>
          <text x={c.lx} y={c.ly + 27} fontFamily="Inter, sans-serif" fontSize="10.5" letterSpacing="1.2" fill="#8b93a5">{c.l[1].toUpperCase()}</text>
        </g>
      ))}
    </svg>
  );
}

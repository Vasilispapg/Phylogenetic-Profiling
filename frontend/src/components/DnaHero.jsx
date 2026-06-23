// Real DNA photo (public-domain, NHGRI) with floating stat callouts.
const STATS = [
  { n: "3,144", l: "reference species", style: { top: "8%", right: "5%" } },
  { n: "218", l: "query proteins", style: { top: "44%", left: "4%" } },
  { n: "108K", l: "BLAST hits", style: { bottom: "8%", right: "9%" } },
];

export default function DnaHero() {
  return (
    <div className="dna-hero">
      <img src="/dna.jpg" alt="DNA double helix" loading="eager" />
      {STATS.map((s) => (
        <span key={s.n} className="chip" style={s.style}>
          <b>{s.n}</b><small>{s.l}</small>
        </span>
      ))}
    </div>
  );
}

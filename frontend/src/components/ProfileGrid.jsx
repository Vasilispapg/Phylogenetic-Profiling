import { useEffect, useRef, useState } from "react";
import { C } from "../lib/theme.js";

/**
 * The hero: a phylogenetic profile that sorts itself.
 *
 * This is the method, not decoration. A profile matrix is domains (rows) by
 * proteomes (columns), filled where the domain is present. Scrambled, it looks
 * like noise; reorder both axes by profile similarity and co-occurrence modules
 * appear as blocks. That reordering is the whole idea of the field and the thing
 * every tool here does, so the page opens by doing it once, in front of you, and
 * then stops.
 */
const ROWS = 46;
const COLS = 78;
const MODULES = 5;
const NOISE = 0.05;
const DURATION = 2600;
const HOLD = 700;

function build(seed = 11) {
  // A small deterministic PRNG so the figure is the same on every visit.
  let s = seed;
  const rnd = () => (s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;

  // Uneven module sizes: real modules are not the same size, and equal blocks
  // read as a test pattern rather than data.
  const split = (total, weights) => {
    const sum = weights.reduce((a, b) => a + b, 0);
    const out = [];
    let used = 0;
    weights.forEach((w, m) => {
      const n = m === weights.length - 1 ? total - used : Math.round((w / sum) * total);
      for (let i = 0; i < n; i++) out.push(m);
      used += n;
    });
    return out;
  };
  const rowModule = split(ROWS, [3, 1.6, 2.4, 1.2, 2]);
  const colModule = split(COLS, [2.2, 1.4, 2.8, 1.1, 2.5]);

  // A domain is present in the proteomes of its own module, plus scattered noise.
  const cells = [];
  for (let i = 0; i < ROWS; i++) {
    const row = [];
    for (let j = 0; j < COLS; j++) {
      const inBlock = rowModule[i] === colModule[j];
      // Modules are not solid either: a domain can be missing from a genome it
      // otherwise belongs with, which is exactly what makes real profiles hard.
      const present = inBlock ? rnd() > 0.16 : rnd() < NOISE;
      row.push(present ? (inBlock ? 2 : 1) : 0);   // 2 = in a module, 1 = stray
    }
    cells.push(row);
  }

  const shuffle = (n) => {
    const a = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };
  // scattered[i] is where row i sits before sorting; i is where it ends up.
  return { cells, scatteredRows: shuffle(ROWS), scatteredCols: shuffle(COLS) };
}

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const lerp = (a, b, t) => a + (b - a) * t;

function mix(from, to, t) {
  const hex = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [r1, g1, b1] = hex(from);
  const [r2, g2, b2] = hex(to);
  return `rgb(${Math.round(lerp(r1, r2, t))},${Math.round(lerp(g1, g2, t))},${Math.round(lerp(b1, b2, t))})`;
}

const STRAY = "#3B3470";
const FOUND_FROM = "#2E7C8C";

export default function ProfileGrid() {
  const canvasRef = useRef(null);
  const [phase, setPhase] = useState("unsorted");
  // Read the phase inside the animation loop without restarting it.
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const { cells, scatteredRows, scatteredCols } = build();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let frame = 0;
    let started = 0;

    const draw = (p) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (!w || !h) return;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const cw = w / COLS;
      const ch = h / ROWS;
      const gap = Math.min(cw, ch) > 6 ? 1 : 0.5;
      const found = mix(FOUND_FROM, C.signal, p);

      for (let i = 0; i < ROWS; i++) {
        const y = lerp(scatteredRows[i], i, p) * ch;
        for (let j = 0; j < COLS; j++) {
          const v = cells[i][j];
          if (!v) continue;
          const x = lerp(scatteredCols[j], j, p) * cw;
          ctx.fillStyle = v === 2 ? found : STRAY;
          ctx.fillRect(x, y, Math.max(cw - gap, 0.7), Math.max(ch - gap, 0.7));
        }
      }
    };

    if (reduced) {
      draw(1);
      setPhase("5 modules");
    } else {
      const step = (now) => {
        if (!started) started = now;
        const elapsed = now - started;
        if (elapsed < HOLD) {
          draw(0);
          frame = requestAnimationFrame(step);
          return;
        }
        const t = Math.min((elapsed - HOLD) / DURATION, 1);
        if (t > 0.02 && phaseRef.current === "unsorted") setPhase("reordering");
        draw(easeInOut(t));
        if (t < 1) frame = requestAnimationFrame(step);
        else setPhase("5 modules");
      };
      frame = requestAnimationFrame(step);
    }

    const onResize = () => draw(phaseRef.current === "unsorted" ? 0 : 1);
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", onResize); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const caption = {
    unsorted: "input order",
    reordering: "reordering by profile similarity",
    "5 modules": "5 co-occurrence modules",
  }[phase];

  return (
    <figure className="figure" style={{ margin: 0 }}>
      <canvas
        ref={canvasRef}
        aria-label="A domain-by-proteome presence matrix reordering itself until co-occurrence modules appear"
        style={{ display: "block", width: "100%", aspectRatio: "78 / 46", background: C.void }}
      />
      <figcaption className="figure-cap">
        <span>46 domains × 78 proteomes</span>
        <span className={phase === "5 modules" ? "live" : ""}>{caption}</span>
      </figcaption>
    </figure>
  );
}

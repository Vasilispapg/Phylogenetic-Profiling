// Shared matrix parsing / transforms for the heatmap, clustergram and explorer.
import Papa from "papaparse";

export const FEATURE_LABELS = {
  mean_percent_identity: "% identity",
  mean_alignment_length: "alignment length",
  mean_bitscore: "bitscore",
  num_hits: "# hits",
  min_evalue: "min e-value",
  value: "value",
};
export const COLORSCALES = ["Viridis", "Cividis", "Plasma", "YlGnBu", "Hot", "Blues", "RdBu", "Electric"];
export const lbl = (f) => FEATURE_LABELS[f] || f;

// Handles plain numeric matrices AND feature matrices whose cells are JSON
// objects (which contain commas + quotes, so a naive split breaks).
export function parseMatrix(text) {
  const grid = Papa.parse(text.trim(), { skipEmptyLines: true }).data;
  if (!grid.length || grid[0].length < 2) throw new Error("empty");
  const cols = grid[0].slice(1);
  const rows = [], cells = [];
  for (let i = 1; i < grid.length; i++) { rows.push(grid[i][0]); cells.push(grid[i].slice(1)); }

  let firstDict = null;
  outer: for (const r of cells) for (const c of r) {
    if (typeof c === "string" && c.trim().startsWith("{")) { try { firstDict = JSON.parse(c); break outer; } catch { /* keep looking */ } }
  }
  if (firstDict) {
    const features = Object.keys(firstDict);
    const data = {}; features.forEach((f) => (data[f] = []));
    for (const r of cells) {
      const per = {}; features.forEach((f) => (per[f] = []));
      for (const c of r) {
        let o = {}; try { o = JSON.parse(c); } catch { /* blank cell */ }
        features.forEach((f) => per[f].push(Number(o[f]) || 0));
      }
      features.forEach((f) => data[f].push(per[f]));
    }
    return { rows, cols, features, data, kind: "feature" };
  }
  const z = cells.map((r) => r.map((v) => Number(v) || 0));
  return { rows, cols, features: ["value"], data: { value: z }, kind: "numeric" };
}

// Order rows/cols by descending total (groups similar) or alphabetically.
export function computeOrder(z2d, rows, cols, order) {
  let ri = rows.map((_, i) => i), ci = cols.map((_, i) => i);
  if (order === "alpha") {
    ri.sort((a, b) => rows[a].localeCompare(rows[b]));
    ci.sort((a, b) => cols[a].localeCompare(cols[b]));
  } else {
    const rs = z2d.map((r) => r.reduce((s, v) => s + v, 0));
    const cs = cols.map((_, c) => z2d.reduce((s, r) => s + r[c], 0));
    ri.sort((a, b) => rs[b] - rs[a]); ci.sort((a, b) => cs[b] - cs[a]);
  }
  return { ri, ci };
}

// Per-row / per-column max normalization + optional log1p (for colour only).
export function transform(z2d, cols, { norm, log }) {
  let m = z2d;
  if (norm === "row") m = m.map((r) => { const mx = Math.max(...r, 1e-9); return r.map((v) => v / mx); });
  else if (norm === "col") {
    const mx = cols.map((_, c) => Math.max(1e-9, ...z2d.map((r) => r[c])));
    m = m.map((r) => r.map((v, c) => v / mx[c]));
  }
  if (log) m = m.map((r) => r.map((v) => (v > 0 ? Math.log1p(v) : 0)));
  return m;
}

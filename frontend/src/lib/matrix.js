// Shared matrix transforms for the heatmap, clustergram and explorer.
//
// Parsing lives on the server now (GET /api/matrices/<id>/plane): a feature
// matrix is 25 MB of CSV with a JSON object per cell, and pulling it apart in
// the browser cost far more than fetching the same numbers already parsed.

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

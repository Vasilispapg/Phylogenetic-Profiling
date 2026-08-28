// Example inputs, so every tool can be tried before you have your own data.
//
// These are built to teach, not just to fill a form: the BLAST sample straddles
// the e-value cutoff so the filter is visible, and the matrix sample has two
// clean modules plus stray hits so clustering has something real to find. Names
// follow the app's own conventions (UniProt proteome - taxid - species - build).

const SPECIES = [
  "UP000005640-00009606-Homo_sapi-22",
  "UP000002277-00009598-PanX_trog-22",
  "UP000000589-00010090-Mus_muscu-22",
  "UP000002494-00010116-Ratt_norv-22",
  "UP000000437-00007955-Dani_reri-22",
  "UP000000803-00007227-Dros_mela-22",
  "UP000001940-00006239-Caen_eleg-22",
  "UP000002311-00559292-Sacc_cere-22",
];

// Two co-occurring pairs from one protein each, plus a domain that is everywhere.
const DOMAINS = [
  ["NP_001005920.3-Cupin_8__coords_52--261", [1, 1, 1, 1, 0, 0, 0, 0]],
  ["NP_001005920.3-Cupin_4__coords_173--263", [1, 1, 1, 1, 0, 0, 1, 0]],
  ["NP_085128.2-Peptidase_S8__coords_1--312", [0, 0, 0, 1, 1, 1, 1, 0]],
  ["NP_085128.2-PA__coords_318--420", [0, 0, 0, 0, 1, 1, 1, 0]],
  ["NP_004435.2-Ribosomal_L2__coords_1--96", [1, 1, 1, 1, 1, 1, 1, 1]],
];

/** BLAST tabular (-outfmt 6): 12 tab-separated columns, no header. */
export const BLAST_SAMPLE = (() => {
  const lines = [];
  DOMAINS.forEach(([domain, presence], d) => {
    presence.forEach((present, s) => {
      if (!present) return;
      const identity = (92 - d * 3 - s * 1.4).toFixed(3);
      const bits = 2900 - d * 300 - s * 40;
      lines.push([
        domain, `${SPECIES[s]}-00${1500 + d * 7 + s}-E-0${13000 + d * 91 + s}`,
        identity, 312, 12 + s, 0, 1, 312, 1, 312, `${d + 1}e-${120 - s * 9}`, bits,
      ].join("\t"));
    });
  });
  // Two weak hits the 1e-5 cutoff drops, so the filter is visible in the result
  // without any species disappearing from the matrix entirely.
  lines.push([
    "NP_085128.2-PA__coords_318--420",
    `${SPECIES[0]}-002101-E-014990`, "24.100", 96, 61, 3, 1, 96, 1, 96, "8e-02", 41,
  ].join("\t"));
  lines.push([
    "NP_001005920.3-Cupin_8__coords_52--261",
    `${SPECIES[7]}-002144-E-015021`, "22.800", 88, 58, 4, 1, 88, 1, 88, "3e-02", 38,
  ].join("\t"));
  return lines.join("\n") + "\n";
})();

/**
 * Correlation matrix: species rows, domain columns, hit *counts*.
 *
 * Counts, not booleans — that is what create_correlation_matrix writes, and it
 * lets the example show what the colour scale actually encodes.
 */
export const MATRIX_SAMPLE = (() => {
  const header = ["Species", ...DOMAINS.map(([d]) => d)].join(",");
  const rows = SPECIES.map((sp, s) =>
    [sp, ...DOMAINS.map(([, presence], d) =>
      presence[s] ? 1 + ((s * 3 + d * 5) % 4) : 0)].join(","));
  return [header, ...rows].join("\n") + "\n";
})();

/** Newick: the tree those profiles produce, with real branch lengths. */
export const NEWICK_SAMPLE =
  "(((UP000005640-00009606-Homo_sapi-22:0.021,UP000002277-00009598-PanX_trog-22:0.019):0.084," +
  "(UP000000589-00010090-Mus_muscu-22:0.038,UP000002494-00010116-Ratt_norv-22:0.036):0.091):0.112," +
  "((UP000000437-00007955-Dani_reri-22:0.174,UP000000803-00007227-Dros_mela-22:0.263):0.078," +
  "(UP000001940-00006239-Caen_eleg-22:0.288,UP000002311-00559292-Sacc_cere-22:0.401):0.096):0.112);\n";

const SAMPLES = {
  blast: [BLAST_SAMPLE, "example.blastp", "text/plain"],
  matrix: [MATRIX_SAMPLE, "example_correlation_matrix.csv", "text/csv"],
  newick: [NEWICK_SAMPLE, "example_tree.nw", "text/plain"],
};

/**
 * A sample as a File, so it travels the same path as a real upload — same
 * validation, same endpoints, same failure modes.
 */
export function sampleFile(kind) {
  const [body, name, type] = SAMPLES[kind];
  return new File([body], name, { type });
}

/** The first few lines of a sample, for showing the shape of the format. */
export function samplePreview(kind, lines = 3) {
  return SAMPLES[kind][0].trim().split("\n").slice(0, lines).join("\n");
}

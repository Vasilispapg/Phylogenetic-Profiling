// The palette, for the JavaScript that draws things.
//
// Derived from viridis: the perceptually-uniform colormap that is the default
// in this field and the app's own first colorscale. Its floor is a deep
// indigo-violet and its ceiling a chartreuse yellow, which is where the whole
// interface takes its two poles from -- so the chrome and the data speak the
// same language instead of the data sitting inside an unrelated brand.
export const C = {
  void: "#0D0B1A",       // page ground
  panel: "#161230",      // surfaces
  panel2: "#1E1940",     // raised surfaces
  rule: "#2C2560",       // hairlines
  ruleSoft: "rgba(140,130,220,.16)",
  dim: "#8983B5",        // secondary text
  paper: "#EDEBFA",      // primary text
  signal: "#E8E14B",     // accent: presence, actions, active state
  flow: "#35B7A8",       // secondary: links, structure, edges
  warn: "#FF7B6E",
};

// Viridis, sampled, with its floor pulled down to the page ground.
//
// Plotly's stock Viridis starts at #440154, a bright purple. On a dark page that
// makes every *absent* cell the loudest thing in the figure — the opposite of
// what a presence/absence matrix should say. Anchoring zero to the background
// lets the data float on the page and the absences fall away.
export const VIRIDIS = [
  [0, "#0D0B1A"], [0.08, "#241C4A"], [0.22, "#3A2E6E"], [0.4, "#2F6B8F"],
  [0.58, "#28958A"], [0.78, "#7FCB5B"], [1, "#E8E14B"],
];

/** Resolve a colorscale name; the default one is our page-anchored viridis. */
export const scaleFor = (name) => (name === "Viridis" ? VIRIDIS : name);

/** Plotly layout defaults: transparent paper, hairline grid, Plex everywhere. */
export const plotLayout = (extra = {}) => ({
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: '"IBM Plex Mono", ui-monospace, monospace', size: 11, color: C.dim },
  margin: { l: 60, r: 16, t: 16, b: 60 },
  xaxis: { gridcolor: C.ruleSoft, zerolinecolor: C.rule, linecolor: C.rule, automargin: true },
  yaxis: { gridcolor: C.ruleSoft, zerolinecolor: C.rule, linecolor: C.rule, automargin: true },
  hoverlabel: {
    bgcolor: C.panel2, bordercolor: C.rule,
    font: { family: '"IBM Plex Mono", ui-monospace, monospace', color: C.paper, size: 11 },
  },
  ...extra,
});

export const PLOT_CONFIG = { responsive: true, displaylogo: false, displayModeBar: "hover" };

// Plotly's scattergl trace needs WebGL, and WebGL is not always there: a VM, a
// machine with hardware acceleration switched off, or a locked-down browser
// leaves it unavailable and Plotly draws a grey "WebGL is not supported" panel
// where the figure should be. Detected once, then cached.
let webglSupport = null;

export function supportsWebGL() {
  if (webglSupport !== null) return webglSupport;
  try {
    const canvas = document.createElement("canvas");
    webglSupport = Boolean(
      canvas.getContext("webgl2") || canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl")
    );
  } catch {
    webglSupport = false;
  }
  return webglSupport;
}

// Below this, SVG is the better choice regardless: it is crisper, it exports
// properly, and it needs nothing special from the machine. WebGL only earns its
// place once there are enough points that SVG would crawl.
export const GL_POINT_THRESHOLD = 3000;

/** The scatter trace to use for `count` points on this machine. */
export const scatterType = (count) =>
  count >= GL_POINT_THRESHOLD && supportsWebGL() ? "scattergl" : "scatter";

/** True when we are drawing many points the slow way because WebGL is missing. */
export const scatterIsSlow = (count) =>
  count >= GL_POINT_THRESHOLD && !supportsWebGL();

/** Distinct hues for cluster ids, kept away from the signal yellow. */
export const clusterColor = (c, { muted = C.dim } = {}) =>
  c == null ? muted : `hsl(${(c * 47 + 160) % 360},58%,62%)`;

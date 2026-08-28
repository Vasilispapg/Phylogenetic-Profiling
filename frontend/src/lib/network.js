// Shared network-view constants.
//
// AllVsAll and Explorer render the same MCL graph with cytoscape, but every
// layout number was written twice with different values (nodeSeparation 140 vs
// 170, nodeRepulsion 7000 vs 14000, gravity 0.25 vs 0.15...). One source now,
// so the two views cannot drift apart again.

export const TREE_DEPTH_DEFAULT = 6;
export const TREE_DEPTH_MAX = 30;

export const ZOOM = { minZoom: 0.1, maxZoom: 3.5, wheelSensitivity: 0.3 };

export const NODE_SIZE = { min: 14, max: 42 };
export const NODE_SIZE_COMPACT = { min: 8, max: 24 };

export const INK = "#0e1726";
export const MUTED = "#c2cad9";
export const HIGHLIGHT = "#e11d48";

// Distinct hues from a small integer, spaced so neighbouring clusters differ.
export const HUE_STEP = 47;
export const clusterColor = (c, { muted = "#94a3b8", saturation = 66 } = {}) =>
  c == null ? muted : `hsl(${(c * HUE_STEP) % 360},${saturation}%,55%)`;

export const fcose = (overrides = {}) => ({
  name: "fcose",
  quality: "proof",
  animate: true,
  animationDuration: 600,
  packComponents: true,
  nodeSeparation: 150,
  idealEdgeLength: 68,
  nodeRepresentation: undefined,
  nodeRepulsion: 9000,
  gravity: 0.2,
  gravityRange: 3.8,
  padding: 45,
  fit: true,
  ...overrides,
});

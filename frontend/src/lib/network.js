// Shared network-view constants.
//
// AllVsAll and Explorer render the same MCL graph with cytoscape; every layout
// number used to be written twice with different values. One source now, all of
// it derived from the palette in theme.js so the graphs sit in the same world as
// the rest of the interface.
import { C, clusterColor } from "./theme.js";

export { clusterColor };

export const TREE_DEPTH_DEFAULT = 6;
export const TREE_DEPTH_MAX = 30;

export const ZOOM = { minZoom: 0.1, maxZoom: 3.5, wheelSensitivity: 0.3 };

export const NODE_SIZE = { min: 12, max: 38 };
export const NODE_SIZE_COMPACT = { min: 7, max: 22 };

export const INK = C.paper;          // labels drawn on the dark canvas
export const MUTED = C.dim2 || "#635D91";
export const HIGHLIGHT = C.signal;
export const EDGE = "rgba(140,130,220,.18)";
export const EDGE_FADED = "rgba(140,130,220,.04)";
export const LABEL_BG = C.panel2;

export const fcose = (overrides = {}) => ({
  name: "fcose",
  quality: "proof",
  animate: true,
  animationDuration: 600,
  packComponents: true,
  nodeSeparation: 150,
  idealEdgeLength: 68,
  nodeRepulsion: 9000,
  gravity: 0.2,
  gravityRange: 3.8,
  padding: 45,
  fit: true,
  ...overrides,
});

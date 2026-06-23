import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout.jsx";
import Landing from "./pages/Landing.jsx";
import Blast from "./pages/Blast.jsx";
import TreeBuilder from "./pages/TreeBuilder.jsx";
import HowTo from "./pages/HowTo.jsx";
import Faq from "./pages/Faq.jsx";
import StyleGuide from "./pages/StyleGuide.jsx";

// Heavy viz pages (cytoscape / plotly / d3) are code-split so the landing stays light.
const TreeViewer = lazy(() => import("./pages/TreeViewer.jsx"));
const AllVsAll = lazy(() => import("./pages/AllVsAll.jsx"));
const Heatmap = lazy(() => import("./pages/Heatmap.jsx"));
const Clustergram = lazy(() => import("./pages/Clustergram.jsx"));

const Fallback = () => (
  <div className="main"><div className="loader"><div className="spin" /><div>Loading…</div></div></div>
);
const L = (El) => (
  <Suspense fallback={<Fallback />}>{El}</Suspense>
);

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/blast" element={<Blast />} />
        <Route path="/tree-builder" element={<TreeBuilder />} />
        <Route path="/tree-viewer" element={L(<TreeViewer />)} />
        <Route path="/all-vs-all" element={L(<AllVsAll />)} />
        <Route path="/heatmap" element={L(<Heatmap />)} />
        <Route path="/clustergram" element={L(<Clustergram />)} />
        <Route path="/how-to" element={<HowTo />} />
        <Route path="/faq" element={<Faq />} />
        <Route path="/styleguide" element={<StyleGuide />} />
        <Route path="*" element={<Landing />} />
      </Route>
    </Routes>
  );
}

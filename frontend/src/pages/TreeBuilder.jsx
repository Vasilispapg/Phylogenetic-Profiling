import { useState } from "react";
import Dropzone from "../components/Dropzone.jsx";
import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";
import { uploadFile, poll } from "../lib/api.js";

export default function TreeBuilder() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);

  const start = async () => {
    if (!file) return setStatus({ kind: "error", msg: "Please choose a correlation matrix CSV." });
    setResult(null);
    setStatus({ kind: "info", msg: "Uploading…", progress: true });
    try {
      const res = await uploadFile("/tools/tree_construct", file);
      if (res.status !== "success" || !res.job_id) return setStatus({ kind: "error", msg: res.message || "Failed to start." });
      setStatus({ kind: "info", msg: "Building tree… this can take a couple of minutes for large inputs.", progress: true });
      const done = await poll(() => `/tools/tree_status?job_id=${encodeURIComponent(res.job_id)}`, {
        interval: 3000, isDone: (d) => d.status === "completed", isFailed: (d) => d.status === "failed",
      });
      setStatus({ kind: "success", msg: "Tree construction completed." });
      setResult(done);
    } catch (e) { setStatus({ kind: "error", msg: "Tree construction failed: " + (e.message || "unknown error") }); }
  };

  return (
    <div className="fade-up" style={{ maxWidth: 900, margin: "0 auto" }}>
      <Stepper steps={[{ label: "Run BLAST", state: "done" }, { label: "Correlation matrix", state: "done" }, { label: "Build tree", state: "active" }]} />
      <h1>Build a phylogenetic tree</h1>
      <p className="muted">Upload a <strong>correlation matrix CSV</strong> (species × domains, from BLAST → Correlation).
         A Neighbour-Joining tree is built from the Jaccard distances between domain profiles.</p>

      <Dropzone accept=".csv,.tsv,.txt" hint="or click to browse · .csv (species × domains)" file={file} onFile={setFile} />

      <div style={{ marginTop: "1rem" }}>
        <button className="btn btn-primary" onClick={start}><i className="fa-solid fa-play" /> Start construction</button>
      </div>

      <Status s={status} />
      {result && result.download_url && (
        <div style={{ marginTop: "1rem" }}>
          <a className="btn btn-secondary" href={result.download_url} target="_blank" rel="noopener noreferrer">
            <i className="fa-solid fa-download" /> Download {result.original_filename}
          </a>
        </div>
      )}
    </div>
  );
}

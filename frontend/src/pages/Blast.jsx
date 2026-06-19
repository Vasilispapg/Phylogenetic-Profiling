import { useState } from "react";
import Dropzone from "../components/Dropzone.jsx";
import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";
import { uploadFile, postJSON } from "../lib/api.js";

export default function Blast() {
  const [file, setFile] = useState(null);
  const [uploaded, setUploaded] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);

  const onFile = async (f) => {
    setFile(f); setResult(null); setUploaded("");
    setStatus({ kind: "info", msg: "Uploading…", progress: true });
    try {
      const res = await uploadFile("/upload", f);
      if (res.status === "success") {
        setUploaded(res.filename);
        setStatus({ kind: "success", msg: '<i class="fa-solid fa-check"></i> File uploaded. Choose an analysis type.' });
      } else setStatus({ kind: "error", msg: res.message || "Upload failed." });
    } catch { setStatus({ kind: "error", msg: "An error occurred during upload." }); }
  };

  const run = async () => {
    if (!type) return setStatus({ kind: "error", msg: "Please select an analysis type." });
    if (!uploaded) return setStatus({ kind: "error", msg: "Please upload a file first." });
    setResult(null); setStatus({ kind: "info", msg: "Processing… please wait.", progress: true });
    try {
      const res = await postJSON("/process", { filename: uploaded, analysis_type: type });
      if (res.status === "success") { setStatus({ kind: "success", msg: '<i class="fa-solid fa-check"></i> Analysis completed.' }); setResult(res.filename); }
      else setStatus({ kind: "error", msg: res.message || "Processing failed." });
    } catch { setStatus({ kind: "error", msg: "An error occurred during processing." }); }
  };

  return (
    <div className="fade-up" style={{ maxWidth: 900, margin: "0 auto" }}>
      <Stepper steps={[{ label: "Upload BLAST", state: "active" }, { label: "Choose analysis" }, { label: "Download matrix" }]} />
      <h1>BLAST analysis</h1>
      <p className="muted">Upload a BLAST tabular file (<code>-outfmt 6</code>) to build a correlation matrix
         (species × domains) or a feature matrix.</p>

      <Dropzone accept=".blastp,.tsv,.tab,.txt,.out,.csv" hint="or click to browse · .blastp / .tsv / .txt"
                file={file} onFile={onFile} />

      <div style={{ maxWidth: 420, marginTop: "1.25rem" }}>
        <label className="label" htmlFor="atype">Analysis type</label>
        <select id="atype" className="select" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Select analysis type…</option>
          <option value="correlation">Correlation matrix</option>
          <option value="features">Feature matrix</option>
        </select>
      </div>

      <div style={{ marginTop: "1.25rem" }}>
        <button className="btn btn-primary" onClick={run} disabled={!uploaded}>
          <i className="fa-solid fa-play" /> Start analysis
        </button>
      </div>

      <Status s={status} />
      {result && (
        <div style={{ marginTop: "1rem" }}>
          <a className="btn btn-secondary" href={`/downloads/${encodeURIComponent(result)}`} target="_blank" rel="noopener noreferrer">
            <i className="fa-solid fa-download" /> Download {result}
          </a>
        </div>
      )}
    </div>
  );
}

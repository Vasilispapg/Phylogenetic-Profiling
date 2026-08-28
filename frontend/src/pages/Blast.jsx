import { useState } from "react";
import Dropzone from "../components/Dropzone.jsx";
import Stepper from "../components/Stepper.jsx";
import Status from "../components/Status.jsx";
import { API, uploadFile, postJSON } from "../lib/api.js";
import Tips from "../components/Tips.jsx";
import { sampleFile, samplePreview } from "../lib/samples.js";

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
      const res = await uploadFile(API.upload, f);
      if (res.status === "success") {
        setUploaded(res.filename);
        setStatus({ kind: "success", msg: "File uploaded. Choose an analysis type." });
      } else setStatus({ kind: "error", msg: res.message || "Upload failed." });
    } catch { setStatus({ kind: "error", msg: "An error occurred during upload." }); }
  };

  const run = async () => {
    if (!type) return setStatus({ kind: "error", msg: "Please select an analysis type." });
    if (!uploaded) return setStatus({ kind: "error", msg: "Please upload a file first." });
    setResult(null); setStatus({ kind: "info", msg: "Processing… please wait.", progress: true });
    try {
      const res = await postJSON(API.process, { filename: uploaded, analysis_type: type });
      if (res.status === "success") { setStatus({ kind: "success", msg: "Analysis completed." }); setResult(res.filename); }
      else setStatus({ kind: "error", msg: res.message || "Processing failed." });
    } catch { setStatus({ kind: "error", msg: "An error occurred during processing." }); }
  };

  return (
    <div className="fade-up" style={{ maxWidth: 900, margin: "0 auto" }}>
      <Stepper steps={[{ label: "Upload BLAST", state: "active" }, { label: "Choose analysis" }, { label: "Download matrix" }]} />
      <h1>BLAST analysis</h1>
      <p className="muted">Upload a BLAST tabular file (<code>-outfmt 6</code>) to build a correlation matrix
         (species × domains) or a feature matrix.</p>

      <Tips
        format={"BLAST tabular (-outfmt 6) — 12 tab-separated columns, no header"}
        sample={samplePreview("blast", 3)}
        tips={[
          <>The <b>species</b> is the first four dash-segments of the subject id:{" "}
            <code>UP000005640-00009606-Homo_sapi-22-001536-E-013170</code> becomes{" "}
            <code>UP000005640-00009606-Homo_sapi-22</code>.</>,
          <>The <b>domain</b> is the whole query id. Everything before its first dash is the
            protein accession, which the clustering later uses as an internal check.</>,
          <>A hit counts as present only at <b>e-value ≤ 1e-5</b>. The example file includes one
            weak hit that gets dropped, so you can see the cutoff do its work.</>,
          <>Start with the <b>correlation matrix</b> — it is what every other tool takes. The
            feature matrix carries five metrics per cell and feeds the heatmap's inspector.</>,
        ]}
      />

      <Dropzone accept=".blastp,.tsv,.tab,.txt,.out,.csv" hint="or click to browse · .blastp / .tsv / .txt"
                file={file} onFile={onFile}
                onSample={() => onFile(sampleFile("blast"))} />

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
          <a className="btn btn-secondary" href={API.download(result)} target="_blank" rel="noopener noreferrer">
            <i className="fa-solid fa-download" /> Download {result}
          </a>
        </div>
      )}
    </div>
  );
}

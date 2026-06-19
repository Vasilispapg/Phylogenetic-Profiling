import { useRef, useState } from "react";

export default function Dropzone({ accept, hint, file, onFile }) {
  const ref = useRef(null);
  const [drag, setDrag] = useState(false);
  const pick = (f) => f && onFile(f);

  return (
    <>
      <div
        className={"dropzone" + (drag ? " drag" : "")}
        onClick={() => ref.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDrag(false); }}
        onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
      >
        <input ref={ref} type="file" accept={accept} style={{ display: "none" }}
               onChange={(e) => pick(e.target.files[0])} />
        <div className="dz-icon"><i className="fa-solid fa-upload" /></div>
        <p className="dz-title">Drop a file here</p>
        <p className="dz-hint">{hint || "or click to browse"}</p>
      </div>
      {file && (
        <span className="file-pill">
          <i className="fa-solid fa-file" /> {file.name}{" "}
          <span style={{ opacity: 0.6 }}>({Math.round(file.size / 1024)} KB)</span>
        </span>
      )}
    </>
  );
}

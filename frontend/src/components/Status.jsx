// Status banners render server-supplied strings. Those strings include
// str(exception) from the API, so they are DATA and are never interpolated as
// HTML -- the icon is chosen from `kind` here instead of being baked into the
// message by each caller.
const ICON = {
  success: "fa-check",
  error: "fa-triangle-exclamation",
  info: "fa-circle-info",
};

export default function Status({ s }) {
  if (!s) return null;
  const kind = s.kind || "info";
  return (
    <div className={"status " + kind} role="status" aria-live="polite">
      <i className={"fa-solid " + (ICON[kind] || ICON.info)} aria-hidden="true" />
      <span>{s.msg}</span>
      {s.progress && <div className="progress"><span /></div>}
    </div>
  );
}

export default function Status({ s }) {
  if (!s) return null;
  const html = (s.msg || "") + (s.progress ? '<div class="progress"><span></span></div>' : "");
  return <div className={"status " + (s.kind || "info")} dangerouslySetInnerHTML={{ __html: html }} />;
}

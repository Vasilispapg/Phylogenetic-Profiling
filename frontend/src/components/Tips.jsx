/**
 * What to bring, and how to read what comes back.
 *
 * Every tool page carries one of these. It is collapsed by default so it never
 * competes with the work, and it opens to concrete things: the shape of the
 * file, and the two or three judgements that decide whether the output means
 * anything.
 */
export default function Tips({ format, sample, tips, defaultOpen = false }) {
  return (
    <details className="tips" open={defaultOpen}>
      <summary>How to read this tool</summary>
      <div>
        {format && (
          <>
            <div className="k" style={{ marginBottom: 6 }}>Input · {format}</div>
            {sample && <pre className="sample">{sample}</pre>}
          </>
        )}
        <ul className="tip-list">
          {tips.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      </div>
    </details>
  );
}

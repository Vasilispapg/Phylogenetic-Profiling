import { useEffect, useRef, useState } from "react";

// Wraps content and reveals it (fade-up + blur) when it scrolls into view.
export default function Reveal({ children, delay = 0, className = "", style }) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Fallback: if IntersectionObserver is unavailable (old/headless renderers),
    // reveal immediately so content is never gated behind a transition that won't fire.
    if (typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setSeen(true); io.disconnect(); } },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={ref} className={`reveal ${seen ? "in" : ""} ${className}`}
         style={{ transitionDelay: seen ? `${delay}ms` : "0ms", ...style }}>
      {children}
    </div>
  );
}

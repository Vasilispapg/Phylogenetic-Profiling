import { Fragment } from "react";

// steps: [{ label, state }] where state is "done" | "active" | undefined
// The marker is a dot, not a number: these are named stages, and the name is
// already the clearest label a step can have.
export default function Stepper({ steps }) {
  return (
    <nav className="stepper" aria-label="Pipeline position">
      {steps.map((st, i) => (
        <Fragment key={st.label}>
          <span className={"step " + (st.state || "")} aria-current={st.state === "active" ? "step" : undefined}>
            <span className="dot" /> {st.label}
          </span>
          {i < steps.length - 1 && <span className="bar" />}
        </Fragment>
      ))}
    </nav>
  );
}

import { Fragment } from "react";

// steps: [{ label, state }] where state is "done" | "active" | undefined
export default function Stepper({ steps }) {
  return (
    <div className="stepper">
      {steps.map((st, i) => (
        <Fragment key={i}>
          <div className={"step " + (st.state || "")}>
            <span className="dot">{st.state === "done" ? <i className="fa-solid fa-check" /> : i + 1}</span> {st.label}
          </div>
          {i < steps.length - 1 && <span className="bar" />}
        </Fragment>
      ))}
    </div>
  );
}

## What this changes

<!-- One or two sentences. If it fixes an issue: "Fixes #123". -->

## Why

<!-- The problem, not the patch. What was wrong or missing? -->

## How to verify

<!--
The steps a reviewer should take: which tool page or command, which input file,
what they should see. If a bundled example file reproduces it, say which.
-->

## Checks

- [ ] `pytest -q` passes
- [ ] `npm run test --prefix frontend` passes
- [ ] `npm run build --prefix frontend` succeeds
- [ ] New behaviour has a test, or I have said below why it cannot have one
- [ ] Docs that this change makes wrong are fixed in the same branch
      (`README.md`, `docs/*.md`, in-app How-to / FAQ)

## Impact

- [ ] **Results change.** Numbers, trees or clusters out of an existing tool
      differ from before — described below, with why the new ones are right.
- [ ] **A format or the API changes.** An input/output format or an endpoint
      response moved — [`docs/DATA.md`](https://github.com/Vasilispapg/PhyloFlask/blob/main/docs/DATA.md) /
      [`docs/API.md`](https://github.com/Vasilispapg/PhyloFlask/blob/main/docs/API.md) updated.
- [ ] **A method or default changes.** A distance, threshold, or clustering
      default moved — reasoning and reference below.
- [ ] **A config knob was added.** It lives in [`config.py`](https://github.com/Vasilispapg/PhyloFlask/blob/main/config.py)
      as an env var and is in the README table.
- [ ] **Hot path touched.** Timed on the bundled dataset, before and after, below.
- [ ] None of the above — additive or internal only.

<!-- Detail for anything ticked above: -->

## Notes for the reviewer

<!--
Anything you are unsure about, deliberately left out, or want argued with.
Also: this branch deploys to the public instance the moment it lands on main,
so flag anything that needs a config or nginx change on the server.
-->

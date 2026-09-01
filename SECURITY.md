# Security Policy

PhyloFlask runs as a public instance that accepts file uploads from anyone, so
the app is written to defend itself rather than to assume something in front of
it will. Reports that show it failing to do that are valuable — thank you for
taking the time.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` (and the `ghcr.io/vasilispapg/phyloflask:latest` image built from it) | Yes |
| Any earlier commit or image tag | No — fixes land on `main` and deploy from there |

There are no release branches. Pushing to `main` publishes a new image and
restarts the deployed container, so a fix reaches the public instance as soon as
it is merged.

## Reporting a vulnerability

**Do not open a public issue, pull request or discussion for a vulnerability.**

Report it privately through GitHub:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Describe the issue, the version or commit you tested, and the steps to
   reproduce it.

That opens an advisory thread visible only to you and the maintainers. If the
form is unavailable to you for any reason, contact the maintainer through the
details on their GitHub profile ([@Vasilispapg](https://github.com/Vasilispapg))
and ask for a private channel — do not include the details in a public message.

What helps most, in order: the request or file that triggers it, the response or
behaviour you got, and what you expected instead. A minimal input beats a large
one; if a crafted upload is involved, a few lines that reproduce it are better
than the whole file. Please do not include unpublished or third-party sequence
data.

### What to expect

- **Acknowledgement within 7 days.** This is a small academic group, not a
  staffed security team, so please allow for term dates and conference weeks.
- An assessment of whether we can reproduce it, and a rough timeline, in the
  same thread.
- Credit in the advisory and the fixing commit, unless you prefer to stay
  anonymous.
- Please give us a reasonable window to ship a fix before disclosing publicly.
  If you have a deadline, say so up front and we will work to it.

## In scope

The parts of the app that exist specifically to make an open instance safe:

- **Upload validation** ([`analysis/upload_guard.py`](analysis/upload_guard.py)) —
  bypassing the per-kind size ceiling, the maximum line length, the Newick
  nesting limit or the content sniff; getting a file to land whole or be read
  into memory before it is judged.
- **Rate limiting and banning** ([`guard.py`](guard.py)) — evading the heavy or
  API budget, forging the client identity, or making the strike/ban counters
  count against the wrong client. Note that `TRUSTED_PROXY` deliberately makes
  the app believe `X-Forwarded-For`; findings that depend on it being set to `1`
  without nginx in front are configuration errors, not vulnerabilities.
- **Execution of uploaded content** — anything that gets an upload evaluated as
  code rather than parsed as data. The repo asserts this in
  [`tests/test_no_execution.py`](tests/test_no_execution.py); a way around that
  assertion is the most serious class of bug here.
- **Path handling** — traversal or collision in `uploads/`, `downloads/`,
  `cache/`, `results/` or the job store; reading or overwriting another client's
  files or results.
- **The response headers** — Content-Security-Policy bypass, XSS in a tool page
  or in rendered matrix/tree content, framing or MIME-sniffing protections that
  do not actually apply.
- **The job store** ([`jobs.py`](jobs.py)) — reading, cancelling or poisoning jobs
  or result blobs belonging to another client; SQL injection.
- **Deployment artefacts** — secrets baked into the image, an over-privileged
  container, or anything in [`docker-compose.prod.yml`](docker-compose.prod.yml)
  or [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) that exposes
  the host.

## Out of scope

- **Resource exhaustion using inputs that are within the documented limits.**
  Neighbour-Joining is O(n³) and clustering is expensive by nature; a valid
  64 MB BLAST file is meant to be able to keep a worker busy. That is what the
  size ceilings, `MAX_TAXA`, the job timeouts and the rate limits bound. A way to
  spend unbounded work *below* those bounds is in scope — say which bound you
  evaded.
- Findings that require running with `FLASK_DEBUG=1`, a self-signed or absent
  TLS setup, or `TRUSTED_PROXY=1` with no reverse proxy. Those are documented as
  not-for-production in [`docs/DEPLOY.md`](docs/DEPLOY.md).
- Missing security headers on a self-hosted instance whose nginx configuration
  differs from the one in [`docs/DEPLOY.md`](docs/DEPLOY.md).
- Reports from automated scanners with no demonstrated impact, version-number
  fingerprinting, and best-practice suggestions unattached to an exploit.
- Vulnerabilities in third-party dependencies with no exploitable path through
  PhyloFlask — those are still worth telling us about, but as a normal issue or
  pull request bumping the pin in [`requirements.txt`](requirements.txt) or
  `frontend/package.json`.
- Social engineering of the maintainers, and anything requiring physical access
  to the server.

## Testing against the public instance

Please test locally instead — `docker compose up --build` gives you the same
image the server runs. If you must test the deployed instance, keep it to your
own uploads, stay within the rate limits, and never attempt anything that would
degrade it for other users or touch data that is not yours.

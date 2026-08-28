# Deploying PhyloFlask

Production is a single VPS: nginx terminates TLS and rate-limits, and proxies to
the app container on loopback. Pushing to `main` builds the image, publishes it
to GHCR and restarts the container over SSH
([`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)).

## What you have to set up once

### 1. Repository secrets

`Settings → Secrets and variables → Actions`:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | the server's hostname or IP |
| `DEPLOY_USER` | the SSH user that can run `docker compose` |
| `DEPLOY_KEY` | the **private** half of a key made only for this |
| `DEPLOY_KNOWN_HOSTS` | the server's public host key. Not a secret, but the workflow needs it |
| `DEPLOY_PATH` | optional, defaults to `/srv/phyloflask` |

#### `DEPLOY_KEY`

A dedicated key, not your own: it can be revoked without touching your access.

```bash
ssh-keygen -t ed25519 -f ~/phyloflask-deploy -C "phyloflask deploy" -N ""
ssh-copy-id -i ~/phyloflask-deploy.pub deployuser@your-host
pbcopy < ~/phyloflask-deploy && rm ~/phyloflask-deploy   # paste into the secret
```

Paste the whole private file, `BEGIN` and `END` lines included.

**Restrict what it can do.** A deploy key that can only deploy is worth much more
than one that can log in. On the server, put the forced command in front of the
key in `~/.ssh/authorized_keys` — all on one line:

```
command="cd /srv/phyloflask && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d --remove-orphans && docker image prune -f",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding ssh-ed25519 AAAA... phyloflask deploy
```

SSH then ignores whatever the client asks for and runs that, so if the key ever
leaks the holder can restart the container and nothing else. The workflow still
sends its own command; it is discarded, and the exit status is the forced one's.

#### `DEPLOY_KNOWN_HOSTS`

The server's public host key, so the deploy talks to *your* machine and not to
whatever answers on the day. Get it with:

```bash
ssh-keyscan -H your-host
```

Then **verify it out of band** — copying a fingerprint from an untrusted channel
defeats the point. On the server:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

The `SHA256:...` it prints has to match what `ssh-keyscan | ssh-keygen -lf -`
gave you. If they differ, do not proceed.

Without this secret the workflow falls back to trusting the key presented at
deploy time and says so in the log.

There is also an optional repository **variable** `DEPLOY_URL` (defaults to
`https://phyloflask.vspapg.gr`), used for the post-deploy health check.

### 2. On the server

```bash
sudo mkdir -p /srv/phyloflask && sudo chown "$USER" /srv/phyloflask
cd /srv/phyloflask
curl -O https://raw.githubusercontent.com/Vasilispapg/PhyloFlask/main/docker-compose.prod.yml
mkdir -p uploads downloads cache state
docker compose -f docker-compose.prod.yml up -d
curl -s localhost:8000/api/health
```

The image is public on GHCR, so the server needs no registry login.

### 3. nginx

The app listens on `127.0.0.1:8000` only. Everything below matters:
`client_max_body_size` must match `MAX_UPLOAD_MB`, and the rate limits have to
leave room for status polling — a running job is polled every 2 seconds, so a
tight general limit would throttle a single legitimate user.

```nginx
# /etc/nginx/conf.d/phyloflask-limits.conf  (http context)
limit_req_zone  $binary_remote_addr zone=phylo_api:10m   rate=2r/s;
limit_req_zone  $binary_remote_addr zone=phylo_heavy:10m rate=20r/m;
limit_conn_zone $binary_remote_addr zone=phylo_conn:10m;
```

```nginx
server {
    listen 443 ssl http2;
    server_name phyloflask.vspapg.gr;

    # TLS lines as you already have them (certbot, etc.)

    client_max_body_size 32m;        # keep in step with MAX_UPLOAD_MB
    client_body_timeout  120s;
    limit_conn phylo_conn 8;

    # Starting work: uploads and job submissions. Expensive, so kept tight.
    location ~ ^/api/(upload|process|matrices|allvsall|trees|newick)$ {
        limit_req zone=phylo_heavy burst=5 nodelay;
        include /etc/nginx/snippets/phyloflask-proxy.conf;
    }

    # Everything else under /api: mostly status polling and reading results.
    location /api/ {
        limit_req zone=phylo_api burst=40 nodelay;
        include /etc/nginx/snippets/phyloflask-proxy.conf;
    }

    # The single-page app and its assets.
    location / {
        include /etc/nginx/snippets/phyloflask-proxy.conf;
    }
}
```

```nginx
# /etc/nginx/snippets/phyloflask-proxy.conf
proxy_pass         http://127.0.0.1:8000;
proxy_http_version 1.1;
proxy_set_header   Host              $host;
proxy_set_header   X-Real-IP         $remote_addr;
proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
proxy_read_timeout 120s;
# The app gzips its own large JSON responses; nginx passes those through
# untouched because they already carry Content-Encoding.
proxy_set_header   Accept-Encoding   $http_accept_encoding;
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## What changes for anyone using the old site

- **All JSON endpoints moved under `/api`.** `/upload` is now `/api/upload`,
  `/allvsall_status/<f>` is now `/api/allvsall/<job_id>/status`, and so on. See
  [`API.md`](API.md). Nothing outside this repo consumed them.
- **The server-rendered pages are gone.** Old links such as `/tools/blast` land
  on the overview rather than 404ing, and the app redirects the ones that have a
  direct equivalent.
- **Uploads and results are now deleted after `JOB_TTL_SECONDS`** (24 h by
  default). Nothing used to clean them up.

## Rolling back

Every build is tagged with its commit, so a rollback is one command on the
server:

```bash
cd /srv/phyloflask
docker compose -f docker-compose.prod.yml down
docker run -d --name phyloflask-rollback -p 127.0.0.1:8000:8000 \
  -v "$PWD/uploads:/app/uploads" -v "$PWD/downloads:/app/downloads" \
  -v "$PWD/cache:/app/cache"     -v "$PWD/state:/app/state" \
  -e MAX_UPLOAD_MB=32 -e DB_PATH=/app/state/jobs.sqlite -e RESULT_DIR=/app/state/results \
  ghcr.io/vasilispapg/phyloflask:<previous-sha>
```

Or edit the `image:` tag in `docker-compose.prod.yml` to that sha and
`docker compose -f docker-compose.prod.yml up -d`.

## Known risk: the instance is open

There is no authentication. Anyone who can reach the site can upload a file and
start a clustering or tree job, so the exposure is CPU, disk and memory rather
than data — job and matrix ids are unguessable, so one visitor cannot read
another's results by walking URLs.

What limits it today, in two layers:

**nginx** applies the rate limits above and `client_max_body_size`.

**The app** does not depend on being behind nginx. It carries the same limits one
layer in, where it knows which requests are expensive
([`guard.py`](../guard.py)): 20 submissions a minute per address against 240
reads, since a running job is polled every two seconds and a single budget would
throttle an honest user. A client that keeps sending malformed uploads collects
strikes — inspecting a file costs real work — and enough strikes earn a
temporary ban that doubles each time, up to `BAN_SECONDS_MAX`.
`X-Forwarded-For` is only believed when `TRUSTED_PROXY=1`, so the header cannot
be used to rotate out of a limit.

Every upload is also checked before it is kept
([`analysis/upload_guard.py`](../analysis/upload_guard.py)): per-kind size cap,
rejection of binary content and archive content types, a cap on the length of a
single line, and a *sniff* that the contents match the format the extension
claims — a `.csv` full of PNG bytes, a comma-separated file calling itself BLAST
output, or a Newick string with unbalanced or absurdly deep nesting are all
refused with a message that says what was expected. Validation happens while the
file streams to disk, so a rejected upload is never written whole and never read
into memory.

Then `MAX_UPLOAD_MB=32`, `JOB_WORKERS=2` (so at most two jobs run at once and
the rest queue), `MAX_TAXA` refusing tree builds that would take hours,
`MAX_CELLS` refusing absurd matrices, and the 24-hour retention sweep.

Nothing executes an upload: the files are only ever handed to pandas, numpy,
scipy and Bio.Phylo as data. `tests/test_no_execution.py` fails the build if any
module reachable from a request gains `eval`, `exec`, `pickle.load`,
`subprocess` or a shell.

If that stops being enough, the cheapest next step is HTTP basic auth in nginx:

```nginx
auth_basic           "PhyloFlask";
auth_basic_user_file /etc/nginx/phyloflask.htpasswd;
```

## Checking a deploy

```bash
curl -s https://phyloflask.vspapg.gr/api/health
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

The workflow already does this: it polls `/api/health` for two minutes after the
restart and fails the run if the site does not come back.

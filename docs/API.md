# HTTP API Reference

Every endpoint lives under **`/api`**. Everything outside it is a client-side
route served by the React bundle, which is why the namespaces cannot collide --
`/clustergram` and `/embedding` used to be *both* a page and an endpoint.

All responses are JSON. Error responses are
`{"status": "error", "message": "..."}` **with a real HTTP status code**
(400 bad request, 404 missing, 409 not ready, 410 expired, 413 too large,
422 job failed, 500 internal). An unmatched `/api/...` path returns 404 JSON, not
the SPA. Data formats: [`DATA.md`](DATA.md).

## The SPA
`GET /<anything not under /api>` serves the built React bundle: an existing file
is returned as-is, anything else falls back to `index.html` for client-side
routing. A missing path that *looks* like a file (has an extension) returns 404
rather than HTML. If `frontend/dist` is absent the response is a 503 explaining
how to build it.

### `GET /api/health`
`{"status":"success","max_upload_mb":200,"job_workers":2,"spa_built":true}`

## Downloads
### `GET /api/downloads/<filename>`
Returns the generated file as an attachment from the `downloads/` directory.
`404` if missing; path traversal is rejected (`send_from_directory`).

## BLAST blueprint
### `POST /api/upload`
Multipart form, field `file`. Validated with `secure_filename` + extension
allowlist (`.blastp .tsv .tab .txt .out .csv`). The returned `filename` carries a
uuid prefix so concurrent users with the same file name cannot overwrite each
other; treat it as an opaque token and pass it back to `/process`.
```json
{"status":"success","message":"File uploaded successfully!",
 "filename":"<uuid>_<safe>","original_name":"<safe>"}
```

### `POST /api/process`
JSON body:
```json
{"filename": "<uploaded name>", "analysis_type": "correlation" | "features"}
```
Builds the matrix into `downloads/` under a unique name and returns it:
```json
{"status":"success","message":"Processing completed",
 "filename":"<uuid>_correlation_matrix.csv"}
```
Errors: 400 missing filename / unknown `analysis_type`, 404 file not found.

### `GET /api/results?filename=<name>`
`{"status":"success","filename":"<name>"}` if the file exists in `downloads/`,
else an error.

## All-vs-all blueprint (domain MCL clustering)
### `POST /api/allvsall`
Multipart form, field `file` = a **correlation matrix CSV**
(`.csv .tsv .txt`). Starts a background clustering job.
```json
{"status":"success","message":"File uploaded and processing started.",
 "job_id":"<job_id>"}
```
Jobs used to be keyed by the uploaded file name, so two users uploading
`correlation_matrix.csv` clobbered each other and either could read the other's
result. They are keyed by an unguessable id now.

### `GET /api/allvsall/<job_id>/status`
```json
{"status":"success","state":"queued"|"running"|"done"|"failed",
 "progress":0.55,"message":"Running Markov clustering (16,238 edges)..."}
```
Poll until `state` is `done` or `failed`. **Branch on `state`, never on
`message`** — the message is display text. 404 if the job is unknown.

### `GET /api/allvsall/<job_id>/data[?include=matrix,positions]`
```json
{
  "status": "success",
  "nodes": ["DomainA", "DomainB", "..."],
  "node_cluster": {"DomainA": 0, "DomainB": 1},
  "degree": {"DomainA": 5, "DomainB": 2},
  "edges": [{"source": "DomainA", "target": "DomainB", "weight": 0.67}],
  "edges_total": 16238,
  "metrics": {"n_clusters": 4, "modularity": 0.71, "warning": null}
}
```
Nodes are **domains**. `node_cluster` colours them, `degree` sizes them, edge
`weight` is the Jaccard similarity, and `metrics` is the validation report.

Only the strongest `EDGE_BUDGET_PER_NODE * n` edges are returned; `edges_total`
says how many there were, so a client can show what it is hiding.

`?include=matrix` adds the **O(n²)** domain × domain co-cluster matrix, derived
from `node_cluster` on the way out. It is neither stored nor sent by default
because `matrix[i][j]` is exactly `node_cluster[i] == node_cluster[j]`. The
spring layout that used to ship with it is gone entirely: every client runs its
own layout, and computing one is O(n²) per iteration.

The default response is the stored blob streamed verbatim -- already gzipped, so
there is no decompress-and-re-serialise step. Measured on the bundled data (216
domains): **6 KB gzipped**, against a 2.18 MB uncompressed payload before.

Other codes: 404 unknown job, 409 still running, 410 result expired, 422 the job
failed.

## Tree blueprint
### `POST /api/trees`
Multipart form, field `file` = a **correlation matrix CSV** (now extension-checked
like the other upload endpoints). Optional form field `method` = `nj` (default) or
`upgma`. Starts a background tree build. Responds **202**:
```json
{"status":"success","message":"Tree generation started.","job_id":"<uuid hex>"}
```

### `GET /api/trees/<job_id>`
```json
{
  "status": "in_progress" | "completed" | "failed",
  "state": "queued" | "running" | "done" | "failed",
  "progress": 0.35,
  "message": null | "<progress or error>",
  "download_url": "/api/downloads/<uuid>_<name>.nw" | null,
  "original_filename": "<name>.nw"
}
```
`status` is the legacy field; `state` and `progress` come straight from the job
store. `400` if `job_id` missing, `404` if unknown. Stop polling on
`completed`/`failed`/`404`.

### `POST /api/newick`
Multipart form, field `file` = a **Newick** file. Returns the full tree as D3
JSON (the client slider prunes depth):
```json
{
  "status": "success",
  "tree_data": {"name": "root", "children": [{"name": "A"}, {"name": "B"}]},
  "max_depth_tree": 7
}
```
`400` on missing/unparseable file.

## Heatmap blueprint (clustering & embedding)
The heatmap / clustergram / embedding **pages** parse CSVs client-side; these two
endpoints do the heavy maths server-side (SciPy / scikit-learn). Both take the
numeric matrix as JSON.

### `POST /api/matrices`
Multipart form, field `file` = a matrix CSV. Stores it and returns an id plus the
labels, so later calls can reference the matrix instead of carrying it:
```json
{"status":"success","file_id":"<uuid>_<name>","name":"<name>",
 "kind":"numeric"|"feature","rows":["s1","..."],"cols":["D1","..."],
 "features":["value"] | ["num_hits","mean_bitscore","..."]}
```
No cell values come back -- the response is O(rows + cols).

### `GET /api/matrices/<file_id>/plane[?metrics=a,b]`
The matrix as numbers, so the browser never parses the CSV:
```json
{"status":"success","kind":"feature","rows":["s1","..."],"cols":["D1","..."],
 "features":["num_hits","..."],"data":{"num_hits":[[3,0],[1,2]]}}
```
`metrics` selects columns of a feature matrix; the default is all of them.
Responses are gzipped when the client accepts it. Measured on the bundled
feature matrix: **0.87 MB gzipped for all five metrics, 0.06 MB for one**,
against a 25.5 MB CSV that the client used to download and parse cell by cell.

Both maths endpoints below accept **either** `{"file_id": "...", "metric": "..."}`
(preferred: the values never travel in a request body) **or** `{"z": [[...]]}` for
small ad-hoc matrices. They refuse matrices above `MAX_CELLS` (20M) with a 413.

Both are deterministic (t-SNE and KMeans are seeded), so results are cached on
their inputs under `cache/`. Re-requesting the same clustering or projection --
which the UI does on every metric, axis, method or k change -- is a file read.

### `POST /api/clustergram`
JSON body `{"file_id": "..."}` (or `{"z": [[...]]}`). Hierarchically
clusters both axes (**correlation distance, average linkage**) and returns leaf
orders + dendrogram line coordinates (drawn client-side):
```json
{
  "status": "success",
  "row_order": [12, 0, 5, "..."],
  "col_order": [3, 1, 8, "..."],
  "row_dendro": {"icoord": [["..."]], "dcoord": [["..."]]},
  "col_dendro": {"icoord": [["..."]], "dcoord": [["..."]]}
}
```
Constant rows/cols (undefined correlation) are treated as maximally distant.

### `POST /api/embedding`
JSON body:
```json
{"file_id": "...", "metric": "num_hits",
 "axis": "domains" | "species", "method": "pca" | "tsne", "k": 8}
```
Projects the chosen axis to 2D (**PCA** or **t-SNE** on standardized profiles)
and groups points with **KMeans**:
```json
{"status": "success", "coords": [[1.2, -0.4], "..."], "labels": [0, 3, "..."], "n_clusters": 8}
```
`axis="domains"` embeds columns, `"species"` embeds rows. Needs ≥ 3 points.

## Configuration
Every knob lives in [`../config.py`](../config.py) and is env-overridable. See the
table in [`../README.md`](../README.md).

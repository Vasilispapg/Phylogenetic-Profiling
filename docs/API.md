# HTTP API Reference

All responses are JSON unless noted. Error responses are
`{"status": "error", "message": "..."}` **with a real HTTP status code**
(400 bad request, 404 missing, 409 not ready, 410 expired, 413 too large,
422 job failed, 500 internal). Data formats: [`DATA.md`](DATA.md).

## Pages (HTML)
`GET /`, `GET /tools`, `GET /tools/blast`, `GET /tools/heatmap`,
`GET /tools/tree_construct`, `GET /tools/tree_viewer`, `GET /how-to`, `GET /faq`,
`GET /styleguide` → rendered templates (200).

`GET /app/...` serves the built React SPA (503 with instructions if
`frontend/dist` is missing). `GET /health` returns a liveness payload.

## Downloads
### `GET /downloads/<filename>`
Returns the generated file as an attachment from the `downloads/` directory.
`404` if missing; path traversal is rejected (`send_from_directory`).

## BLAST blueprint
### `POST /upload`
Multipart form, field `file`. Validated with `secure_filename` + extension
allowlist (`.blastp .tsv .tab .txt .out .csv`). The returned `filename` carries a
uuid prefix so concurrent users with the same file name cannot overwrite each
other; treat it as an opaque token and pass it back to `/process`.
```json
{"status":"success","message":"File uploaded successfully!",
 "filename":"<uuid>_<safe>","original_name":"<safe>"}
```

### `POST /process`
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

### `GET /results?filename=<name>`
`{"status":"success","filename":"<name>"}` if the file exists in `downloads/`,
else an error.

## All-vs-all blueprint (domain MCL clustering)
### `POST /tools/allvsall`
Multipart form, field `file` = a **correlation matrix CSV**
(`.csv .tsv .txt`). Starts a background clustering job.
```json
{"status":"success","message":"File uploaded and processing started.",
 "filename":"<job_id>","job_id":"<job_id>"}
```
`filename` is the job id, not the uploaded name: jobs used to be keyed by file
name, so two users uploading `correlation_matrix.csv` clobbered each other and
either could read the other's result.
`GET /tools/allvsall` renders the page.

### `GET /allvsall_status/<job_id>`
```json
{"status":"success","state":"queued"|"running"|"done"|"failed",
 "progress":0.55,"message":"Running Markov clustering (16,238 edges)..."}
```
Poll until `state` is `done` or `failed`. **Branch on `state`, never on
`message`** — the message is display text. 404 if the job is unknown.

### `GET /allvsall_data/<job_id>[?include=matrix,positions]`
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

`?include=matrix,positions` adds the two **O(n²)** fields — the domain × domain
co-cluster matrix and a spring layout. They are omitted by default because
`matrix[i][j]` is just `node_cluster[i] == node_cluster[j]` and every current
client computes its own layout. Measured on the bundled data (216 domains) the
default payload is **0.15 MB** against 2.18 MB with everything included.

Other codes: 404 unknown job, 409 still running, 410 result expired, 422 the job
failed.

## Tree blueprint
### `POST /tools/tree_construct`
Multipart form, field `file` = a **correlation matrix CSV** (now extension-checked
like the other upload endpoints). Optional form field `method` = `nj` (default) or
`upgma`. Starts a background tree build. Responds **202**:
```json
{"status":"success","message":"Tree generation started.","job_id":"<uuid hex>"}
```

### `GET /tools/tree_status?job_id=<id>`
```json
{
  "status": "in_progress" | "completed" | "failed",
  "state": "queued" | "running" | "done" | "failed",
  "progress": 0.35,
  "message": null | "<progress or error>",
  "download_url": "/downloads/<uuid>_<name>.nw" | null,
  "original_filename": "<name>.nw"
}
```
`status` is the legacy field; `state` and `progress` come straight from the job
store. `400` if `job_id` missing, `404` if unknown. Stop polling on
`completed`/`failed`/`404`.

### `POST /tools/tree_viewer`
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

Both refuse matrices above `MAX_CELLS` (20M) with a 413 rather than running out
of memory.

### `POST /clustergram`
JSON body `{"z": [[...], ...]}` — a numeric matrix (rows × cols). Hierarchically
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

### `POST /embedding`
JSON body:
```json
{"z": [[...], ...], "axis": "domains" | "species", "method": "pca" | "tsne", "k": 8}
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

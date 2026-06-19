# HTTP API Reference

All responses are JSON unless noted. Error responses are
`{"status": "error", "message": "..."}`. Data formats: [`DATA.md`](DATA.md).

## Pages (HTML)
`GET /`, `GET /tools`, `GET /tools/blast`, `GET /tools/heatmap`,
`GET /tools/tree_construct`, `GET /tools/tree_viewer` → rendered templates (200).

## Downloads
### `GET /downloads/<filename>`
Returns the generated file as an attachment from the `downloads/` directory.
`404` if missing; path traversal is rejected (`send_from_directory`).

## BLAST blueprint
### `POST /upload`
Multipart form, field `file`. Validated with `secure_filename` + extension
allowlist (`.blastp .tsv .tab .txt .out .csv`).
```json
{"status":"success","message":"File uploaded successfully!","filename":"<safe>"}
```

### `POST /process`
JSON body:
```json
{"filename": "<uploaded name>", "analysis_type": "correlation" | "features"}
```
Builds the matrix into `downloads/` (`correlation_matrix.csv` or
`feature_matrix.csv`) and returns:
```json
{"status":"success","message":"Processing completed","filename":"correlation_matrix.csv"}
```
Errors: missing filename / unknown `analysis_type` / file not found.

### `GET /results?filename=<name>`
`{"status":"success","filename":"<name>"}` if the file exists in `downloads/`,
else an error.

## All-vs-all blueprint (domain MCL clustering)
### `POST /tools/allvsall`
Multipart form, field `file` = a **correlation matrix CSV**
(`.csv .tsv .txt`). Starts a background `cluster_domains` job.
```json
{"status":"success","message":"File uploaded and processing started.","filename":"<safe>"}
```
`GET /tools/allvsall` renders the page.

### `GET /allvsall_status/<filename>`
```json
{"status":"success","message":"Performing clustering..." | "Completed." | "Error: ..."}
```
Poll until `message == "Completed."`.

### `GET /allvsall_data/<filename>`
```json
{
  "status": "success",
  "nodes": ["DomainA", "DomainB", "..."],
  "edges": [{"source": "DomainA", "target": "DomainB"}],
  "matrix": [[1, 0], [0, 1]],
  "positions": {"DomainA": [0.12, -0.34]}
}
```
Nodes are **domains**; `matrix` is the domain × domain co-cluster matrix.

## Tree blueprint
### `POST /tools/tree_construct`
Multipart form, field `file` = a **correlation matrix CSV**. Starts a background
Neighbour-Joining build. Responds **202**:
```json
{"status":"success","message":"Tree generation started.","job_id":"<uuid hex>"}
```

### `GET /tools/tree_status?job_id=<id>`
```json
{
  "status": "in_progress" | "completed" | "failed",
  "message": null | "<error>",
  "download_url": "/downloads/<job_id>_<name>.nw" | null,
  "original_filename": "<name>.nw"
}
```
`400` if `job_id` missing, `404` if unknown. Stop polling on
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

## Configuration
Server behaviour is controlled by env vars: `PORT`, `HOST`, `FLASK_DEBUG`,
`MAX_UPLOAD_MB`, `DASH_DEBUG`. See [`../README.md`](../README.md).

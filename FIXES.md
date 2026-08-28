# FIXES.md — Λύσεις, αρχιτεκτονική και optimizations

Συνέχεια του code review. Κάθε λύση δείχνει **πού** εφαρμόζεται (`αρχείο:γραμμή`), **τι
κοστίζει** και **τι κερδίζει**. Οι αριθμοί με `[μετρημένο]` προέρχονται από benchmarks που
έτρεξα στο ίδιο το repo (Python 3.13, Biopython 1.87, πραγματικά δεδομένα:
848 είδη × 216 domains).

> **Διόρθωση στο προηγούμενο review:** είχα αποδώσει το κόστος εκκίνησης (1,93 s cold)
> στο Dash. Λάθος. Με `python -X importtime`: `markov_clustering` **441 ms** (σέρνει
> `sklearn.preprocessing` → `scipy.stats`), `pandas` 132 ms, `flask` 65 ms,
> `dash`+`plotly`+`dbc` **~38 ms**. Το Dash import είναι αρχιτεκτονικό coupling, όχι
> performance πρόβλημα. Η λύση αλλάζει ανάλογα (§2.6).

---

## 0. Προτεραιότητες

| # | Πρόβλημα | Λύση | Κόστος | Όφελος |
|---|---|---|---|---|
| **P0** | NJ O(n³) καθαρή Python, 119,88 s στα 848 είδη | Vectorised NJ (numpy, ~35 γρ., 0 νέες εξαρτήσεις) | ~1 μέρα | **158× ταχύτερο, ίδια τοπολογία (RF=0)** |
| **P0** | Χρήστες γράφουν ο ένας πάνω στον άλλο· IDOR στο `/allvsall_data` | `file_id`/`job_id` παντού (το μοτίβο υπάρχει ήδη στο `templates/tree.py:149`) | ~2 μέρες | Σωστό multi-user, κλείνει διαρροή |
| **P0** | Το E-value φίλτρο δεν δοκιμάζεται ποτέ | 1 test + μεταφορά του φίλτρου στο `_load_blast` | ~1 ώρα | Προστατεύει το κρισιμότερο επιστημονικό κατώφλι |
| **P1** | `/allvsall_data` payload O(N²) | Πέτα `matrix`+`positions`, top-K ακμές | ~2 ώρες | **2,18 MB → 0,15 MB** (μετρημένο), O(N) αντί O(N²) |
| **P1** | `_jobs`/`precomputed_results` μεγαλώνουν για πάντα | Job store με TTL + αποτελέσματα στον δίσκο | ~1 μέρα | Σταθερή μνήμη, επιβίωση σε restart |
| **P1** | Σφάλματα με HTTP 200 | `fail()` helper + errorhandlers | ~2 ώρες | Σωστό monitoring, τίμιο μήνυμα στο 413 |
| **P1** | `dangerouslySetInnerHTML` με strings του server | Render ως κείμενο | ~30 λεπτά | Κλείνει το XSS μοτίβο |
| **P2** | GIL: το NJ πνίγει το API, 1 worker μόνο | `ProcessPoolExecutor` + job store εκτός μνήμης | ~2 μέρες | Responsive API, `--workers N` |
| **P2** | Δύο frontends, ~1.800 διπλές γραμμές | Ένα UI (React), `/api` prefix, serve `dist` | ~3 μέρες | Μισή επιφάνεια συντήρησης |
| **P2** | Μηδέν CI, μηδέν frontend tests | GitHub Actions + vitest | ~1 μέρα | Σταματά το drift |
| **P3** | Νεκρός κώδικας, διπλές σταθερές, `cache_dir` fantôme | Καθάρισμα + `config.py` | ~1 μέρα | Λιγότερη παραπλάνηση |

---

## 1. Αλλαγές αρχιτεκτονικής

### 1.1 `file_id` ως το μοναδικό «νόμισμα» του API  ← η βασική αλλαγή

**Λύνει ταυτόχρονα τρία προβλήματα**: την απομόνωση χρηστών, το IDOR, και τα 200 MB JSON
bodies του `/clustergram`/`/embedding`.

Σήμερα κάθε endpoint έχει δικό του μοντέλο ταυτότητας:

| Endpoint | Ταυτότητα σήμερα | Πρόβλημα |
|---|---|---|
| `POST /upload` → `POST /process` | το ίδιο το filename (`templates/blast.py:38`, `:64-71`) | σταθερά ονόματα → overwrite + διαρροή |
| `POST /tools/allvsall` | filename (`templates/allvsall.py:54`, `:130`) | overwrite + IDOR |
| `POST /tools/tree_construct` | **uuid** (`templates/tree.py:149`) | ✅ σωστό |
| `POST /clustergram`, `/embedding` | καμία — όλος ο πίνακας στο body (`templates/heatmap.py:32-38`) | 413 στα 10× |

Ένα μοντέλο για όλα:

```
POST /api/files            (multipart)  → {"file_id": "<uuid4hex>", "name": "...", "kind": "blast|matrix|newick"}
POST /api/matrix/<id>/correlation        → {"job_id": ...}   ή σύγχρονα {"result_id": ...}
POST /api/matrix/<id>/clustergram        → leaf orders + dendro   (χωρίς body με πίνακα)
POST /api/matrix/<id>/embedding          → coords + labels
POST /api/matrix/<id>/allvsall           → {"job_id": ...}
POST /api/matrix/<id>/tree               → {"job_id": ...}
GET  /api/jobs/<job_id>                  → {state, progress, message, result_id}
GET  /api/results/<result_id>            → το αρχείο
```

Υλοποίηση του upload (αντικαθιστά `templates/blast.py:26-43`,
`templates/allvsall.py:44-52`, `templates/tree.py:144-151`):

```python
# blueprints/files.py
import uuid, json, os
from werkzeug.utils import secure_filename
from config import UPLOAD_DIR

KINDS = {
    "blast":  {".blastp", ".tsv", ".tab", ".txt", ".out", ".csv"},
    "matrix": {".csv", ".tsv", ".txt"},
    "newick": {".nw", ".newick", ".nwk", ".txt"},
}

@files_bp.post("/api/files")
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return fail("No file provided.", 400)
    kind = request.form.get("kind", "matrix")
    name = secure_filename(f.filename)
    ext = os.path.splitext(name)[1].lower()
    if kind not in KINDS or ext not in KINDS[kind]:
        return fail(f"Unsupported file type for {kind}: {ext or '(none)'}", 400)

    file_id = uuid.uuid4().hex
    (UPLOAD_DIR / file_id).mkdir(parents=True)
    f.save(UPLOAD_DIR / file_id / name)
    (UPLOAD_DIR / file_id / "meta.json").write_text(json.dumps({"name": name, "kind": kind}))
    return jsonify({"status": "success", "file_id": file_id, "name": name, "kind": kind})
```

Τι κερδίζεις αμέσως:

- **Απομόνωση**: το `file_id` είναι uuid4 (122 bits εντροπίας) → κανένα collision, καμία
  απαρίθμηση. Αυτό είναι *capability URL*, όχι authentication — γράψ' το ρητά στο README·
  αν θέλεις πραγματικό auth, μπαίνει μετά ως ένα `@login_required` decorator.
- **Το `/tools/tree_construct` αποκτά επιτέλους extension allowlist** (σήμερα λείπει,
  `templates/tree.py:145`) γιατί το validation γίνεται σε ένα σημείο.
- **Τα `/clustergram` και `/embedding` σταματούν να παίρνουν πίνακες σε JSON body.** Ο
  server διαβάζει το CSV με pandas (C code) αντί ο browser να το κάνει parse και μετά να
  σειριοποιήσει 18 εκατ. αριθμούς. Η λογική για feature matrices υπάρχει ήδη:
  `visualization/display_correlation.py:15-22` (`_parse_cell`).

```python
def load_matrix(file_id, metric=None):
    """Επιστρέφει (rows, cols, z) από correlation ή feature matrix."""
    path = _resolve(file_id)
    df = pd.read_csv(path, index_col=0)
    sample = df.iloc[0, 0] if df.size else ""
    if isinstance(sample, str) and sample.strip().startswith("{"):
        metric = metric or list(json.loads(sample).keys())[0]
        df = df.map(lambda c: _parse_cell(c).get(metric, 0) or 0)
    return list(map(str, df.index)), list(map(str, df.columns)), df.to_numpy(float)
```

**Μετανάστευση χωρίς big-bang:** κράτα τα παλιά endpoints ως thin adapters που κάνουν
`302`/επανεγγραφή στο νέο σχήμα για 1-2 releases, με `logging.warning("deprecated
endpoint %s")`. Ενημέρωσε `frontend/src/lib/api.js` και `frontend/vite.config.js:11-21`
(ένα `"/api": api` αντί για 8 κανόνες).

---

### 1.2 Ένα job model, εκτός μνήμης

Σήμερα υπάρχουν **δύο** ασύμβατα μοντέλα: `_jobs` με uuid και κατάσταση
`in_progress|completed|failed` (`templates/tree.py:26`, `:180-199`), και
`progress_status` + `precomputed_results` με κλειδί filename και **magic string**
`"Completed."` (`templates/allvsall.py:23-24`, `:137`, που ο client συγκρίνει κυριολεκτικά
στο `frontend/src/pages/AllVsAll.jsx:37`, `Explorer.jsx:38`, `pages/allvsall.html:237`).

```python
# jobs.py  — ένα module, ~80 γραμμές
import json, sqlite3, time, uuid
from config import DB_PATH, RESULT_DIR, JOB_TTL

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('queued','running','done','failed')),
  progress REAL DEFAULT 0, message TEXT,
  result_id TEXT, error TEXT,
  created REAL NOT NULL, updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_created ON jobs(created);
"""

def _db():
    con = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")   # πολλοί readers + ένας writer
    return con

def create(kind):
    jid, now = uuid.uuid4().hex, time.time()
    with _db() as c:
        c.execute("INSERT INTO jobs(id,kind,state,created,updated) VALUES(?,?,'queued',?,?)",
                  (jid, kind, now, now))
    return jid

def update(jid, **kw):
    kw["updated"] = time.time()
    cols = ",".join(f"{k}=?" for k in kw)
    with _db() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*kw.values(), jid))

def get(jid):
    with _db() as c:
        r = c.execute("SELECT id,kind,state,progress,message,result_id,error FROM jobs WHERE id=?",
                      (jid,)).fetchone()
    return dict(zip(("id","kind","state","progress","message","result_id","error"), r)) if r else None

def reap():
    """Σβήνει ληγμένα jobs ΚΑΙ τα αρχεία τους. Τρέχει σε background timer."""
    cutoff = time.time() - JOB_TTL
    with _db() as c:
        rows = c.execute("SELECT id,result_id FROM jobs WHERE created < ?", (cutoff,)).fetchall()
        c.execute("DELETE FROM jobs WHERE created < ?", (cutoff,))
    for _, rid in rows:
        if rid: (RESULT_DIR / rid).unlink(missing_ok=True)
```

Το API γίνεται ένα: `GET /api/jobs/<id>` → `{"state": "running", "progress": 0.4,
"message": "Running Markov clustering…", "result_id": null}`. Ο client ελέγχει
`state === "done"` — **μηχανικό πεδίο, όχι κείμενο**. Το `message` μένει μόνο για εμφάνιση.

**Τα αποτελέσματα φεύγουν από τη RAM.** Αντί το `precomputed_results` να κρατά ένα
networkx graph + DataFrame + positions για πάντα (`templates/allvsall.py:130-136`), ο
worker γράφει το τελικό payload μία φορά:

```python
RESULT_DIR.joinpath(result_id).write_bytes(gzip.compress(json.dumps(payload).encode()))
```

και το `GET /api/results/<id>` κάνει `send_file(..., mimetype="application/json")` με
`Content-Encoding: gzip`. Μνήμη O(1), επιβίωση σε restart, και **ο δίσκος γίνεται το
cache** (§2.5).

---

### 1.3 Βγάλε τα βαριά jobs από τη διεργασία του web

Το NJ είναι καθαρή Python → κρατά το GIL. Με 8 threads σε **έναν** worker
(`Dockerfile:31`) το API υποβαθμίζεται για όλη τη διάρκεια του job.

```python
# app.py
from concurrent.futures import ProcessPoolExecutor
import atexit, jobs

POOL = ProcessPoolExecutor(max_workers=int(os.environ.get("JOB_WORKERS", 2)))
atexit.register(POOL.shutdown, wait=False)

def submit(kind, fn, *args):
    jid = jobs.create(kind)
    fut = POOL.submit(fn, *args)                     # τρέχει σε ΑΛΛΗ διεργασία
    fut.add_done_callback(lambda f: _finish(jid, f))  # το callback τρέχει στον parent
    return jid

def _finish(jid, fut):
    try:
        jobs.update(jid, state="done", result_id=fut.result(), progress=1.0)
    except Exception as e:
        logging.exception("job %s failed", jid)
        jobs.update(jid, state="failed", error=str(e))
```

Η συνάρτηση που τρέχει στο pool πρέπει να είναι top-level και **picklable** και να
επιστρέφει `result_id` (string), όχι DataFrames. Αυτό ήδη επιβάλλεται από την §1.2.

Τι αλλάζει στο ops:

```dockerfile
# Dockerfile — τα jobs δεν είναι πια in-process, ο job store είναι SQLite/WAL
CMD ["gunicorn", "--workers", "4", "--threads", "4", "--timeout", "60", \
     "--bind", "0.0.0.0:8000", "app:app"]
```

Το σχόλιο στο `Dockerfile:28-30` («ένας worker για να μοιράζεται το in-memory job
store») παύει να ισχύει και σβήνεται.

> Δεν προτείνω Celery/Redis. Είναι single-node εργαλείο ερευνητικής ομάδας· ένας broker
> προσθέτει operational βάρος χωρίς αντίκρισμα. SQLite + `ProcessPoolExecutor` καλύπτει.

---

### 1.4 Ένα frontend, `/api` prefix, το `dist` σερβίρεται από το Flask

Σήμερα ο React SPA **δεν αναπτύσσεται καθόλου**: δεν υπάρχει route για το
`frontend/dist` στο `app.py`, το `Dockerfile:17-24` δεν τρέχει `npm run build`, και το
`frontend/dist/` είναι gitignored (`frontend/.gitignore:2`). Το `docker compose up`
σερβίρει μόνο τις Jinja σελίδες, ενώ το `docs/INDEX.md:96` λέει ότι ο React είναι «the
primary UI».

**Απόφαση που πρέπει να πάρει η ομάδα, όχι εγώ.** Η πρότασή μου: **React ως το μοναδικό
UI**, γιατί εκεί έχει πάει όλη η δουλειά (τα 8 τελευταία commits) και εκεί ζουν τα τρία
εργαλεία που δεν υπάρχουν καν σε Jinja (Clustergram, Explorer, Embedding).

Βήμα 1 — πρόθεμα `/api` σε όλα τα JSON endpoints, ώστε το SPA catch-all να μην είναι
διφορούμενο:

```python
app.register_blueprint(files_bp,   url_prefix="/api")
app.register_blueprint(matrix_bp,  url_prefix="/api")
app.register_blueprint(jobs_bp,    url_prefix="/api")
```

Βήμα 2 — serve το build:

```python
DIST = Path(__file__).parent / "frontend" / "dist"

@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    target = DIST / path
    if path and target.is_file():
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")   # client-side routing
```

Βήμα 3 — multi-stage Dockerfile:

```dockerfile
FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
...
COPY --from=ui /ui/dist ./frontend/dist
```

Βήμα 4 — διαγραφή: `pages/blast.html`, `pages/heatmap.html` (808 γρ.),
`pages/allvsall.html` (986 γρ.), `pages/tree_viewer.html`, `pages/tree_construct.html`,
`pages/tools.html`, `public/assets/js/tools.js`, `public/main.js`. Αυτό εξαφανίζει
ταυτόχρονα: το διπλό ECharts (`pages/heatmap.html:12-13`), τα CDN χωρίς SRI
(`pages/allvsall.html:4-5`, `pages/tree_viewer.html:56`), και το `innerHTML` XSS μοτίβο
του `public/assets/js/tools.js:44`.

Βήμα 5 — `frontend/vite.config.js:11-21` γίνεται `proxy: { "/api": api }`.

**Αν αποφασίσετε να κρατήσετε τις Jinja σελίδες**, τότε πρέπει να γίνει ρητή πολιτική με
ιδιοκτήτη και test ανά σελίδα — αλλιώς θα ξανα-αποκλίνουν όπως τώρα.

---

## 2. Performance

### 2.1 Το NJ — τρεις επιλογές, με νούμερα

**[μετρημένο]** στο πραγματικό dataset και σε συνθετικά ×10:

| Επιλογή | n=848 | n=2000 | n=4000 | n=8480 (10×) | Ίδια μέθοδος; | Νέες εξαρτήσεις |
|---|---|---|---|---|---|---|
| **Σήμερα** `Bio.Phylo` `nj()` (`construct_tree.py:123`) | 119,88 s | — | — | ~33 h *(εκτίμηση O(n³))* | — | — |
| **A.** Vectorised NJ (numpy) | **0,76 s** | 10,3 s | 79,9 s | ~13 min *(εκτίμηση)* | ✅ **ίδιο NJ** | καμία |
| **B.** RapidNJ / FastME (C++, subprocess) | — | — | — | λεπτά *(δεν το εγκατέστησα)* | ✅ NJ | binary στο image |
| **C.** scipy UPGMA + Newick | **0,04 s** | 0,27 s | 1,12 s | **5,17 s** *(μετρημένο)* | ❌ άλλη μέθοδος | καμία |

**Επιλογή A — η πρότασή μου.** Ίδιος αλγόριθμος, ίδιο αποτέλεσμα, μηδέν νέες εξαρτήσεις,
~35 γραμμές. **Το επαλήθευσα**: σε τυχαίο υποσύνολο 60 ειδών από τα πραγματικά δεδομένα,
η τοπολογία είναι **πανομοιότυπη** με του Biopython — 57 splits και στα δύο,
**Robinson-Foulds symmetric difference = 0**.

```python
# tree_construction/nj.py
import numpy as np

def nj_newick(D, names):
    """Neighbour-Joining, διανυσματοποιημένο. D: πλήρης τετραγωνικός πίνακας αποστάσεων."""
    D = np.array(D, dtype=np.float64, copy=True)
    nodes, n = list(names), D.shape[0]
    while n > 2:
        r = D.sum(axis=1)
        Q = (n - 2) * D - r[:, None] - r[None, :]      # O(n²) σε numpy, όχι σε Python loop
        np.fill_diagonal(Q, np.inf)
        i, j = np.unravel_index(np.argmin(Q), Q.shape)
        if i > j:
            i, j = j, i
        dij = D[i, j]
        delta = (r[i] - r[j]) / (n - 2)
        li = max(0.0, 0.5 * dij + 0.5 * delta)
        lj = max(0.0, dij - li)
        newrow = 0.5 * (D[i] + D[j] - dij)
        keep = np.ones(n, dtype=bool); keep[[i, j]] = False
        newrow = newrow[keep]
        D2 = D[np.ix_(keep, keep)]
        m = D2.shape[0] + 1
        Dn = np.empty((m, m))
        Dn[:m-1, :m-1] = D2
        Dn[m-1, :m-1] = Dn[:m-1, m-1] = newrow
        Dn[m-1, m-1] = 0.0
        nodes = [nd for k, nd in enumerate(nodes) if keep[k]] + \
                ["(%s:%.6f,%s:%.6f)" % (nodes[i], li, nodes[j], lj)]
        D, n = Dn, m
    return "(%s:%.6f,%s:%.6f);" % (nodes[0], D[0, 1] / 2, nodes[1], D[0, 1] / 2)
```

Αλλαγή στο `tree_construction/construct_tree.py:104-127`: το `compute_distance_matrix`
επιστρέφει ήδη squareform στο `:94` — σταμάτα να το μετατρέπεις σε Python
list-of-lists στο `:97-100` (εκεί καίγονται τα GB) και δώσ' το κατευθείαν στο `nj_newick`.
Το `sys.setrecursionlimit` στο `:115` παύει να χρειάζεται (η υλοποίηση είναι iterative).

**Επιλογή C ως δεύτερη μέθοδος, όχι αντικαταστάτης.** Το UPGMA υποθέτει molecular clock,
το NJ όχι — είναι επιστημονικά διαφορετικό αποτέλεσμα. Πρότεινέ το ως ρητή επιλογή:

```python
def build_tree(species, D, method="nj"):        # method: "nj" | "upgma"
```

με το UI να το εκθέτει και να λέει «UPGMA: ~1000× ταχύτερο, υποθέτει σταθερό ρυθμό».

**Και στις δύο περιπτώσεις, βάλε φράχτη.** Στα 8.480 είδη ο πίνακας είναι 576 MB float64
και τα ενδιάμεσα αντίγραφα τον διπλασιάζουν:

```python
if len(species) > MAX_TAXA:                    # config.py, default 5000
    raise ValueError(
        f"{len(species)} species exceeds MAX_TAXA={MAX_TAXA}. "
        f"Use method='upgma' or raise MAX_TAXA (needs ~{8*len(species)**2/1e9:.1f} GB)."
    )
```

Καλύτερο σφάλμα από ένα OOM kill 20 λεπτά μετά.

---

### 2.2 `/allvsall_data`: από O(N²) σε O(N)

**[μετρημένο]** στο σημερινό dataset (216 domains, 16.238 ακμές):

| Payload | Μέγεθος |
|---|---|
| Σήμερα (`templates/allvsall.py:106-115`) | **2,18 MB** |
| Χωρίς `matrix` + `positions` | 1,93 MB |
| **+ μόνο οι top-5N ισχυρότερες ακμές** | **0,15 MB** — 14× μικρότερο |

Τρία ευρήματα που το κάνουν εύκολο:

1. **Οι React clients δεν χρησιμοποιούν ποτέ το `matrix` ούτε το `positions`.** Έψαξα:
   `AllVsAll.jsx:60` και `Explorer.jsx:78,133-134` διαβάζουν μόνο `nodes`,
   `node_cluster`, `degree`, `edges`, `metrics`. Μόνο το `pages/allvsall.html:263,297-301`
   τα αγγίζει — και αυτό φεύγει με την §1.4.
2. **Ο πίνακας είναι πλήρως παράγωγος.** `pages/allvsall.html:301` τον χρησιμοποιεί για
   `z[i][j]`, που ισούται με `nc[nodes[i]] === nc[nodes[j]] ? 1 : 0`. Τρεις γραμμές στον
   client αντί για N² αριθμούς στο δίκτυο.
3. **Οι clients ήδη κόβουν ακμές μόνοι τους** (`Explorer.jsx:81`: top-5N·
   `AllVsAll.jsx:48`: κατώφλι ≈ 4N) — απλώς αφού κατεβάσουν όλες. Κάν' το στον server.

```python
# templates/allvsall.py — αντικαθιστά τις :101-115
edges = sorted(
    ({"source": u, "target": v, "weight": round(float(d.get("weight", 1.0)), 3)}
     for u, v, d in graph.edges(data=True)),
    key=lambda e: -e["weight"],
)
top_k = int(request.args.get("top_k", 5 * len(graph_nodes)))
return jsonify({
    "status": "success",
    "nodes": graph_nodes,
    "node_cluster": node_cluster,
    "degree": degree,
    "edges": edges[:top_k],
    "edges_total": len(edges),        # ← ώστε το UI να ΜΗΝ κρύβει σιωπηλά
    "metrics": result.get("metrics"),
})
```

Και στο UI (λύνει και το «σιωπηλό κόψιμο» του review):

```jsx
<div className="muted">
  showing strongest {data.edges.length.toLocaleString()} of {data.edges_total.toLocaleString()} links
</div>
```

**Στα 10× (2.160 domains, ίδια πυκνότητα 70%)** *(εκτίμηση)*: σήμερα `matrix` ≈ 25 MB +
`edges` ≈ 190 MB ≈ **215 MB ανά request**· με τα παραπάνω ≈ **1,6 MB**.

---

### 2.3 `/clustergram` και `/embedding`: σταμάτα να στέλνεις τον πίνακα

Σήμερα ο browser κάνει parse το CSV (`frontend/src/lib/matrix.js:17-43`) και μετά
σειριοποιεί ολόκληρο τον πίνακα ως JSON body (`Clustergram.jsx:39`, `Embedding.jsx:43`).
Στα 10× αυτό είναι 18,3 εκατ. αριθμοί → πάνω από το `MAX_CONTENT_LENGTH` των 200 MB
(`app.py:20`) → 413 με HTML body → ο client δείχνει
`Invalid (non-JSON) response from the server (HTTP 413)` (`api.js:19-21`), δηλαδή λάθος
αιτία.

Λύση: `POST /api/matrix/<file_id>/clustergram` (§1.1). Ο server διαβάζει το CSV με pandas.
Μηδέν μεγάλα bodies, μισή δουλειά, και ο browser δεν χρειάζεται να κρατά το CSV στη RAM.

Ανεξάρτητα από αυτό, βάλε τίμιο μήνυμα:

```python
@app.errorhandler(413)
def too_large(_):
    return jsonify({"status": "error",
                    "message": f"Upload exceeds the {MAX_UPLOAD_MB} MB limit."}), 413
```

---

### 2.4 Ο co-cluster πίνακας και το spring_layout

```python
# αντικαθιστά analysis/clustering_analysis.py:383-388
labels = np.empty(len(domains), dtype=np.int32)
for ci, c in enumerate(clusters):
    labels[list(c)] = ci
# ο co-πίνακας δεν χρειάζεται καν να υπάρχει· αν τον θέλεις:
# co = (labels[:, None] == labels[None, :]).astype(np.uint8)
```

**[μετρημένο]**: το διπλό Python loop 0,003 s → numpy 0,0001 s (**30×**), πανομοιότυπο
αποτέλεσμα. Στο σημερινό μέγεθος είναι αμελητέο· στα 10× με ένα κυρίαρχο cluster των
~2.070 domains το Python loop κάνει 4,3 εκατ. επαναλήψεις.

**Μπόνους:** επιστρέφοντας τα `labels` απευθείας από το `cluster_domains`
(`analysis/clustering_analysis.py:402`) εξαφανίζεται το άρρητο συμβόλαιο σειράς του
`templates/allvsall.py:97-98` — δεν χρειάζεται πια `connected_components` για να
ξανα-βρεθεί κάτι που το MCL ήδη ήξερε, ούτε η υπόθεση ότι `list(graph.nodes())` έχει την
ίδια σειρά με το DataFrame index.

Το `nx.spring_layout` (`:390`): **[μετρημένο]** 0,04 s στα 216 domains — αλλά κανένας
React client δεν το χρησιμοποιεί. Πέτα το (ή κάν' το `if want_positions:`). Στα 10× είναι
O(N²)×50 iterations.

---

### 2.5 Κάνε το `cache_dir` να υπάρχει στ' αλήθεια

Η παράμετρος `cache_dir` δηλώνεται (`analysis/clustering_analysis.py:365`), περνάει από
`templates/allvsall.py:56 → :122 → :127`, και **δεν χρησιμοποιείται ποτέ**. Πέντε modules
φτιάχνουν τον φάκελο `./cache` και κανείς δεν γράφει.

Content-addressed cache — μία συνάρτηση:

```python
def cache_key(path, **params):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    h.update(json.dumps(params, sort_keys=True).encode())
    return h.hexdigest()

def cluster_domains(corr_path, cache_dir=CACHE_DIR, threshold=..., inflation=...):
    key = cache_key(corr_path, threshold=threshold, inflation=inflation, v=2)
    hit = Path(cache_dir) / f"{key}.json.gz"
    if hit.exists():
        return json.loads(gzip.decompress(hit.read_bytes()))
    payload = _compute(...)
    hit.write_bytes(gzip.compress(json.dumps(payload).encode()))
    return payload
```

Το `v=2` στο κλειδί είναι το version bump: αλλάζεις αλγόριθμο → αλλάζεις `v` → όλο το
cache ακυρώνεται καθαρά. Το ίδιο μοτίβο εφαρμόζεται και στο NJ, όπου το όφελος είναι
μεγαλύτερο (δευτερόλεπτα/λεπτά αντί για 0,1 s).

Το `docs/CODE_ANALYSIS.md:117-118` λέει ότι το παλιό pickle cache αφαιρέθηκε επίτηδες
επειδή «το clustering είναι φθηνό». Σωστό για τα 216 domains — αλλά τότε **σβήσε την
παράμετρο και τον φάκελο**, μην αφήνεις σκελετό που παραπλανά.

---

### 2.6 Cold start

**[μετρημένο]** `-X importtime` (cumulative, warm cache): `markov_clustering` **441 ms**
(→ `sklearn.preprocessing` 379 ms → `scipy.stats` 283 ms), `pandas` 132 ms, `flask` 65 ms,
`dash`+`dbc`+`plotly` **~38 ms**. Σύνολο `import app`: 867 ms warm / 1,93 s cold.

Δύο ανεξάρτητες κινήσεις:

1. **Lazy import του `markov_clustering`** — το πραγματικό κόστος. Ίδιο μοτίβο που ήδη
   χρησιμοποιεί σωστά το `templates/heatmap.py:28-30, 67-71`:

   ```python
   def cluster_domains(...):
       import markov_clustering as mc          # αντί για analysis/clustering_analysis.py:5
   ```
   Κερδίζεις ~440 ms σε κάθε boot και ~90 MB RSS σε workers που δεν τρέχουν ποτέ MCL.

2. **Σπάσε το `analysis/clustering_analysis.py` στα δύο** — αυτό είναι για την
   αρχιτεκτονική, όχι για τα ms:
   - `analysis/clustering.py` → `domain_jaccard`, `build_domain_graph`, `cluster_domains`,
     `validate_clusters` (μόνο numpy/networkx/scipy).
   - `visualization/dash_allvsall.py` → `create_dash_app` (και **διαγραφή** του
     `create_dash_component`, 111 νεκρές γραμμές `:25-135`).

   Το `templates/allvsall.py:10` εισάγει μόνο το πρώτο. Ένα web blueprint δεν πρέπει να
   σέρνει UI framework, ακόμα κι αν κοστίζει 38 ms.

3. Βγάλε το `joblib` από τα `requirements.txt:11` (κανένα import) και μετακίνησε
   `dash`, `plotly`, `dash-bootstrap-components` σε `requirements-cli.txt`.

---

## 3. Correctness & security — μικρά patches, μεγάλη διαφορά

### 3.1 Το E-value φίλτρο σε ένα σημείο

Σήμερα το `create_correlation_matrix` φιλτράρει (`analysis/matrix_operations.py:38-40`)
και το `create_feature_matrix` **όχι** (`:65-73`) — δύο αρχεία που πάνε στα ίδια εργαλεία
με διαφορετική σημασιολογία «παρουσίας».

```python
# analysis/matrix_operations.py
from config import EVALUE_THRESHOLD

def _load_blast(path, evalue_threshold=EVALUE_THRESHOLD):
    df = pd.read_csv(path, sep='\t', header=None, names=BLAST_COLUMNS)
    if evalue_threshold is not None:
        df = df[pd.to_numeric(df['EValue'], errors='coerce') <= evalue_threshold]
    df['Domain'] = df['QueryID']
    df['Species'] = df['SubjectID'].apply(extract_species)
    return df
```

Και οι δύο builders καλούν `_load_blast(path, evalue_threshold)`. Ίδιο μοτίβο «single
source of truth» με το `extract_species` (`analysis/utils.py:14-16`) — το repo ήδη ξέρει
να το κάνει σωστά, απλά δεν το εφάρμοσε εδώ.

⚠️ **Breaking change στα δεδομένα**: το feature matrix θα αλλάξει. Θέλει σημείωση στο
`docs/DATA.md` και bump στο cache version.

### 3.2 Σταμάτα το HTML injection

```jsx
// frontend/src/components/Status.jsx — αντικαθιστά ΟΛΟ το αρχείο
const ICON = { success: "fa-check", error: "fa-triangle-exclamation", info: "fa-circle-info" };

export default function Status({ s }) {
  if (!s) return null;
  return (
    <div className={"status " + (s.kind || "info")} role="status">
      <i className={"fa-solid " + (ICON[s.kind] || ICON.info)} aria-hidden="true" />
      <span>{s.msg}</span>
      {s.progress && <div className="progress"><span /></div>}
    </div>
  );
}
```

Και βγάλε τα `'<i class="fa-solid fa-check"></i> …'` από τους callers:
`Blast.jsx:21`, `:32`· `TreeBuilder.jsx:23`· `TreeViewer.jsx:29`.
Αν κρατήσετε τις Jinja σελίδες: `public/assets/js/tools.js:44` →
`el.textContent = message` με ξεχωριστό progress element.

### 3.3 Σωστά HTTP status codes

```python
# blueprints/_api.py
def fail(message, code=400):
    return jsonify({"status": "error", "message": message}), code

# app.py
@app.errorhandler(Exception)
def unhandled(e):
    if isinstance(e, HTTPException):
        return jsonify({"status": "error", "message": e.description}), e.code
    logging.exception("unhandled error")
    return jsonify({"status": "error", "message": "Internal server error"}), 500
```

Αντικαθιστά τα ~20 σημεία που γυρίζουν 200 με σφάλμα:
`templates/blast.py:30,34,36,43,55,57,61,69,84,93,97`,
`templates/heatmap.py:35,40,76,85,90,105`,
`templates/allvsall.py:42,47,49,75,87,89,119`.
Ο `frontend/src/lib/api.js:6-22` διαβάζει το body ανεξάρτητα από `r.ok` → **backwards
compatible**, δεν σπάει κανένας client.

Ο generic handler σβήνει και τα `try/except: return 500` του `templates/tree.py:114-116`
και `:175-177`, και το `except` χωρίς προστασία στο `templates/allvsall.py:52`
(`file.save` χωρίς try — το μόνο upload που δεν το έχει).

### 3.4 Polling με timeout, backoff και χωρίς overlap

Το `setInterval` με async callback (`frontend/src/lib/api.js:48-58`) στέλνει
επικαλυπτόμενα requests αν ο server αργεί, δεν έχει συνολικό timeout, και ένα μεμονωμένο
network glitch σκοτώνει το job (`:57`).

```js
export function poll(urlFn, { interval = 2500, timeout = 30 * 60_000,
                              maxErrors = 3, isDone, isFailed, onTick } = {}) {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    let errors = 0;
    const tick = async () => {
      if (Date.now() - t0 > timeout)
        return reject(new Error("Timed out waiting for the job. It may still be running."));
      try {
        const res = await fetch(typeof urlFn === "function" ? urlFn() : urlFn);
        if (res.status === 404) return reject(new Error("Job not found"));
        const data = await asJSON(res, "status endpoint");
        errors = 0;
        onTick?.(data);
        if (isDone(data)) return resolve(data);
        if (isFailed?.(data)) return reject(new Error(data.message || "failed"));
      } catch (e) {
        if (++errors >= maxErrors) return reject(e);      // ανέχεται παροδικά σφάλματα
      }
      setTimeout(tick, interval * 2 ** errors);           // backoff, χωρίς overlap
    };
    setTimeout(tick, interval);
  });
}
```

### 3.5 Πραγματικό progress

```python
# analysis/clustering.py
def cluster_domains(path, ..., progress=lambda p, msg: None):
    progress(0.05, "Reading correlation matrix…")
    corr = pd.read_csv(path, index_col=0)
    progress(0.20, f"Computing Jaccard similarity for {corr.shape[1]} domains…")
    domains, J = domain_jaccard(corr)
    progress(0.40, "Building the domain graph…")
    graph = build_domain_graph(domains, J, threshold)
    progress(0.55, f"Running Markov clustering ({graph.number_of_edges():,} edges)…")
    ...
```

Αντικαθιστά τα δύο back-to-back `_set_status` του `templates/allvsall.py:125-126`, που
σήμερα δείχνουν το πρώτο μήνυμα για 0 ms.

### 3.6 `config.py` — μία πηγή για paths και knobs

`UPLOAD_FOLDER`/`OUTPUT_FOLDER`/`CACHE_FOLDER` ορίζονται **πέντε φορές**
(`app.py:13-15`, `templates/blast.py:11-13`, `heatmap.py:8-9`, `allvsall.py:15-16`,
`tree.py:17-19`) — και ως **σχετικά** paths (`'./uploads'`), δηλαδή εξαρτώνται από το CWD:
αν το gunicorn ξεκινήσει από άλλον φάκελο, γράφει αλλού.

```python
# config.py
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
UPLOAD_DIR   = Path(os.environ.get("UPLOAD_DIR",   BASE / "uploads"))
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", BASE / "downloads"))
CACHE_DIR    = Path(os.environ.get("CACHE_DIR",    BASE / "cache"))
RESULT_DIR   = Path(os.environ.get("RESULT_DIR",   BASE / "results"))
DB_PATH      = Path(os.environ.get("DB_PATH",      BASE / "jobs.sqlite"))

MAX_UPLOAD_MB      = int(os.environ.get("MAX_UPLOAD_MB", 200))
JOB_TTL            = int(os.environ.get("JOB_TTL_SECONDS", 86400))
MAX_TAXA           = int(os.environ.get("MAX_TAXA", 5000))
EVALUE_THRESHOLD   = float(os.environ.get("EVALUE_THRESHOLD", 1e-5))
JACCARD_THRESHOLD  = float(os.environ.get("JACCARD_THRESHOLD", 0.5))
MCL_INFLATION      = float(os.environ.get("MCL_INFLATION", 2.0))
SPECIES_SEGMENTS   = int(os.environ.get("SPECIES_SEGMENTS", 4))

for _d in (UPLOAD_DIR, DOWNLOAD_DIR, CACHE_DIR, RESULT_DIR):
    _d.mkdir(parents=True, exist_ok=True)
```

Παράπλευρο όφελος: τα τρία επιστημονικά κατώφλια (`1e-5`, `0.5`, `2.0`) που **δεν
τεκμηριώνονται πουθενά** γίνονται ρυθμιζόμενα χωρίς αλλαγή κώδικα. Δεν απαντά στο «γιατί
αυτές οι τιμές» — αλλά επιτρέπει στους ερευνητές να απαντήσουν μόνοι τους με ένα sweep,
που είναι το σωστό επόμενο βήμα.

### 3.7 Καθάρισμα

| Διαγραφή | Γραμμές |
|---|---|
| `analysis/clustering_analysis.py:25-135` (`create_dash_component`, δεν καλείται) | 111 |
| `public/main.js` (καμία σελίδα δεν το φορτώνει) | 39 |
| `tree_construction/construct_tree.py:10-28` (`load_species_data`) | 19 |
| `analysis/blast_processing.py` (μόνο re-export· το `_load_blast` το αντικαθιστά) | 40 |
| `analysis/utils.py:29-40` (`extract_partial_species`) + το test του | 12 |
| `joblib` από `requirements.txt:11` | 1 |

Και μετονομασία `templates/` → `blueprints/` (περιέχει Python, τα Jinja templates είναι
στο `pages/`, `app.py:10`) — μαζί με τα άχρηστα `template_folder='templates'` args
(`templates/blast.py:9`, `heatmap.py:6`, `allvsall.py:13`, `tree.py:15`) που δείχνουν σε
φάκελο που δεν υπάρχει.

---

## 4. Observability

```python
# app.py, πριν από κάθε άλλο import που κάνει logging
import logging, os
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s",
)
```

Σήμερα το `logging.exception` καλείται σε `templates/tree.py:115,131,176` **χωρίς καμία
ρύθμιση logging**, ενώ όλο το analysis layer χρησιμοποιεί `print` ως logger
(`analysis/matrix_operations.py:55,102`· `tree_construction/construct_tree.py:63,118,120,
122,124,126`· `analysis/clustering_analysis.py:379,393,395`· `templates/allvsall.py:118`).
Αντικατάστησέ τα με `log = logging.getLogger(__name__)`. Κράτα `print` **μόνο** στο
`main.py` (είναι CLI UX, όχι logging).

Το CLI πρέπει να επιστρέφει σωστό exit code — σήμερα το `main.py:89-92` καταπίνει τα
πάντα και βγαίνει με **0**, δηλαδή δεν μπορεί να μπει σε script ή CI:

```python
try:
    command_function()
except Exception:
    logging.exception("command %s failed", command)
    sys.exit(1)
```

Χαμηλού κόστους προσθήκες: ένα `GET /api/health` (job counts, disk usage, έκδοση) και ένα
request-id middleware ώστε ένα σφάλμα στα logs να συνδέεται με ένα job.

---

## 5. Tests & CI

### 5.1 Το test που λείπει περισσότερο

Το E-value κατώφλι — το κρισιμότερο επιστημονικό κατώφλι του project — **δεν δοκιμάζεται
ποτέ**: όλα τα E-values του fixture (`tests/test_pipeline.py:16-22`) είναι `0.0` και
`1e-30`, δηλαδή περνάνε. Σβήνεις τις `analysis/matrix_operations.py:38-40` και τα 31 tests
περνάνε.

```python
WEAK_BLAST = (
    "D1\tUP0000001-0000001-Aaa_aaaa-22-1-E-1\t90.0\t100\t1\t0\t1\t100\t1\t100\t1e-30\t300\n"
    "D1\tUP0000002-0000002-Bbb_bbbb-22-2-E-2\t31.0\t100\t9\t0\t1\t100\t1\t100\t1e-2\t45\n"
)

def test_evalue_cutoff_drops_weak_hits(tmp_path):
    p = tmp_path / "w.blastp"; p.write_text(WEAK_BLAST)
    corr = create_correlation_matrix(str(p), output_path=str(tmp_path / "c.csv"))
    assert "UP0000001-0000001-Aaa_aaaa-22" in set(map(str, corr.index))
    assert "UP0000002-0000002-Bbb_bbbb-22" not in set(map(str, corr.index))  # 1e-2 > 1e-5

def test_evalue_cutoff_can_be_disabled(tmp_path):
    p = tmp_path / "w.blastp"; p.write_text(WEAK_BLAST)
    corr = create_correlation_matrix(str(p), output_path=str(tmp_path / "c.csv"),
                                     evalue_threshold=None)
    assert len(corr.index) == 2

def test_feature_matrix_applies_the_same_cutoff(tmp_path):   # μετά το §3.1
    p = tmp_path / "w.blastp"; p.write_text(WEAK_BLAST)
    feat = create_feature_matrix(str(p), output_path=str(tmp_path / "f.csv"))
    assert set(map(str, feat["Species"])) == {"UP0000001-0000001-Aaa_aaaa-22"}
```

### 5.2 Τα endpoints χωρίς καμία κάλυψη

`/clustergram`, `/embedding`, `POST /tools/allvsall`, `/allvsall_status`,
`/allvsall_data`, `POST /tools/tree_viewer`, `POST /tools/tree_construct`, `/results`, και
τα happy paths των `/upload` + `/process`.

```python
def test_clustergram_returns_orders(client):
    z = [[1,0,1,0],[1,0,1,0],[0,1,0,1],[0,1,0,1]]
    body = client.post("/clustergram", json={"z": z}).get_json()
    assert body["status"] == "success"
    assert sorted(body["row_order"]) == [0,1,2,3]
    assert len(body["col_dendro"]["icoord"]) == len(body["col_dendro"]["dcoord"])

def test_embedding_shapes(client):
    z = [[1,0,1,0],[1,0,1,0],[0,1,0,1],[0,1,0,1]]
    body = client.post("/embedding", json={"z": z, "axis": "domains", "method": "pca", "k": 2}).get_json()
    assert len(body["coords"]) == 4 and all(len(c) == 2 for c in body["coords"])

def test_tree_job_completes(client, tmp_path):
    csv = b"Species,D1,D2,D3\ns1,1,1,0\ns2,1,0,0\ns3,0,1,1\n"
    r = client.post("/tools/tree_construct",
                    data={"file": (io.BytesIO(csv), "m.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 202
    jid = r.get_json()["job_id"]
    for _ in range(50):                       # deterministic, χωρίς sleep-and-pray
        st = client.get(f"/tools/tree_status?job_id={jid}").get_json()
        if st["status"] in ("completed", "failed"): break
        time.sleep(0.1)
    assert st["status"] == "completed"

def test_two_uploads_same_name_do_not_collide(client):   # ο κανόνας που λείπει σήμερα
    a = client.post("/api/files", data={"file": (io.BytesIO(b"a,1\n"), "m.csv"), "kind": "matrix"},
                    content_type="multipart/form-data").get_json()
    b = client.post("/api/files", data={"file": (io.BytesIO(b"b,2\n"), "m.csv"), "kind": "matrix"},
                    content_type="multipart/form-data").get_json()
    assert a["file_id"] != b["file_id"]
```

### 5.3 Regression test για το νέο NJ

Ο τρόπος που επαλήθευσα τη vectorised NJ — γίνεται μόνιμο test:

```python
def test_vectorised_nj_matches_biopython():
    """Ίδια τοπολογία με το Bio.Phylo (Robinson-Foulds = 0)."""
    rng = np.random.default_rng(7)
    P = rng.random((40, 60)) < 0.35
    D = squareform(pdist(P, metric="jaccard"))
    names = [f"s{i}" for i in range(40)]
    lt = [[float(D[i][j]) for j in range(i + 1)] for i in range(40)]
    bio  = DistanceTreeConstructor().nj(DistanceMatrix(names=list(names), matrix=lt))
    mine = Phylo.read(io.StringIO(nj_newick(D, names)), "newick")
    assert splits(bio, names) == splits(mine, names)
```

### 5.4 Άλλα

- **Χαλάρωσε το εύθραυστο assert.** `tests/test_pipeline.py:173` ελέγχει
  `n_clusters == 2` — εξαρτάται από την ακριβή έκδοση του `markov_clustering`. Κάν' το
  `>= 2` + `modularity > 0.3` + «τα P1-* συν-ομαδοποιούνται».
- **Frontend tests.** `npm i -D vitest` και `"test": "vitest run"` στο
  `frontend/package.json:6-10`. Πρώτο αρχείο: `src/lib/matrix.test.js` για το
  `parseMatrix` — numeric matrix, feature matrix με JSON κελιά που περιέχουν κόμματα,
  ragged γραμμές, κενά κελιά. Είναι το πιο εύθραυστο κομμάτι του repo και έχει μηδέν
  κάλυψη.
- **Έλεγχος περιεχομένου, όχι μόνο 200.** Το `tests/test_web.py:24-26` ελέγχει μόνο
  status code· πρόσθεσε `assert b"<main" in resp.data` ή έναν marker ανά σελίδα.

### 5.5 CI — δεν υπάρχει κανένα σήμερα

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13", cache: pip }
      - run: pip install -r requirements.txt pytest
      - run: pytest -q
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22", cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci --prefix frontend
      - run: npm run test --prefix frontend
      - run: npm run build --prefix frontend
```

Το `npm run build` στο CI πιάνει ακριβώς το πρόβλημα της §1.4: αν το React build σπάσει,
κανείς δεν το μαθαίνει σήμερα γιατί κανείς δεν το χτίζει.

---

## 6. Σειρά εκτέλεσης

| PR | Περιεχόμενο | Ρίσκο | Μετρήσιμο αποτέλεσμα |
|---|---|---|---|
| **1** | `config.py`, logging, `fail()` + errorhandlers, CLI exit code, καθάρισμα νεκρού κώδικα | χαμηλό | −220 γραμμές, σωστά status codes |
| **2** | Tests: E-value, endpoints, isolation· CI workflow | μηδέν | 31 → ~50 tests, το CI γίνεται δίχτυ |
| **3** | Vectorised NJ + RF regression test + `MAX_TAXA` guard | μεσαίο | **119,88 s → 0,76 s** |
| **4** | `/allvsall_data`: πέτα `matrix`/`positions`, top-K ακμές, labels από το MCL | χαμηλό | **2,18 MB → 0,15 MB** |
| **5** | `jobs.py` (SQLite + TTL), ενιαίο `/api/jobs/<id>`, αποτελέσματα στον δίσκο | μεσαίο | Σταθερή μνήμη, επιβίωση restart |
| **6** | `file_id` API + `/api` prefix + deprecation adapters | **υψηλό** (σπάει contract) | Απομόνωση χρηστών, τέλος στα 200 MB bodies |
| **7** | `ProcessPoolExecutor` + `--workers 4` | μεσαίο | Responsive API κατά τη διάρκεια jobs |
| **8** | Ένα frontend: serve `dist`, multi-stage Dockerfile, διαγραφή Jinja tools | μεσαίο | −1.800 γραμμές, τέλος στο CDN/SRI/ECharts |
| **9** | Content-addressed cache, lazy `markov_clustering`, split Dash | χαμηλό | −440 ms boot, δεύτερο τρέξιμο δωρεάν |

Τα PR 1-4 δίνουν το ~80% του οφέλους με το ~20% του ρίσκου. Το PR 6 είναι το μόνο που
σπάει API contract — γι' αυτό μπαίνει αφού υπάρχουν tests (PR 2) και deprecation adapters.

---

## 7. Τι ΔΕΝ θα άλλαζα

- **`validate_clusters`** (`analysis/clustering_analysis.py:305-362`). Είναι το καλύτερο
  κομμάτι του repo. Unsupervised αλγόριθμος με ενσωματωμένο έλεγχο ποιότητας —
  modularity, same-protein co-clustering ως internal ground truth, και warning όταν η
  δομή καταρρέει (`:345-351`). **[μετρημένο]** στα bundled δεδομένα βγάζει `Q = 0,001`,
  `largest = 207/216` και **ενεργοποιεί σωστά το warning**: το εργαλείο λέει μόνο του ότι
  το αποτέλεσμα δεν έχει δομή. Μην το πειράξεις.
- **Το μοντέλο job του `templates/tree.py`** (uuid, καταχώρηση *πριν* το thread στο
  `:156-162` ώστε να μην υπάρχει race με το πρώτο poll, 202 + `job_id`). Είναι το
  πρότυπο που πρέπει να αντιγράψουν τα άλλα, όχι να αντικατασταθεί.
- **`send_from_directory` για τα downloads** (`app.py:56-59`) με το test στο
  `tests/test_web.py:42-45`. Σωστό όπως είναι.
- **Οι iterative διασχίσεις δέντρου** (`templates/tree.py:48-60`, `:63-81`). Stack-based,
  ασφαλείς για βαθιά δέντρα, με σχόλιο που εξηγεί γιατί.
- **`extract_species` ως single source of truth** (`analysis/utils.py:9-26`) — το μοτίβο
  είναι σωστό, απλά πρέπει να επεκταθεί και στο E-value φίλτρο (§3.1).
- **Το MCL.** **[μετρημένο]** 0,10 s στα 216 domains, `cluster_domains` συνολικά 1,16 s.
  Δεν είναι το bottleneck και δεν υπάρχει λόγος να αντικατασταθεί από Louvain/Leiden.
- **Client-side parsing στο Heatmap** (`frontend/src/pages/Heatmap.jsx:23-34`). Δεν
  χτυπάει καθόλου τον server και δουλεύει μια χαρά· μόνο τα clustergram/embedding χρειάζονται
  το file_id round trip.
- **Μην μπει Celery/Redis/Kubernetes.** Single-node εργαλείο ερευνητικής ομάδας. SQLite +
  process pool είναι η σωστή κλίμακα λύσης.

---

## 8. Ανοιχτά ερωτήματα — απαντήσεις που δεν δίνει ο κώδικας

Αυτά καθορίζουν ποιες από τις παραπάνω λύσεις είναι υπερβολή και ποιες υποχρεωτικές:

| Ερώτημα | Γιατί έχει σημασία |
|---|---|
| Πόσοι ταυτόχρονοι χρήστες; Δημόσιο δίκτυο ή localhost; | Αν είναι μονοχρηστικό εργαλείο localhost, τα P0 της απομόνωσης υποβαθμίζονται σε P2. |
| Μέγιστο ρεαλιστικό μέγεθος dataset; | Καθορίζει αν αρκεί η vectorised NJ (§2.1-A) ή χρειάζεται RapidNJ/UPGMA. |
| Γιατί Jaccard 0.5 και inflation 2.0; | Χωρίς αυτό, το `config.py` απλώς κάνει τους μαγικούς αριθμούς ρυθμιζόμενους — δεν τους δικαιολογεί. Ένα parameter sweep + καμπύλη modularity θα ήταν το σωστό επόμενο βήμα. |
| Το UPGMA είναι επιστημονικά αποδεκτό ως εναλλακτική; | Αν ναι, το πρόβλημα κλίμακας λύνεται σε 5 s· αν όχι, μένουμε στη vectorised NJ + φράχτη. |
| Ποιο frontend είναι το επίσημο; | Είναι η μόνη απόφαση της §1.4 που δεν μπορώ να πάρω εγώ. |
| Πολιτική διατήρησης uploads/downloads; | Καθορίζει το `JOB_TTL` και αν χρειάζεται καθόλου ο reaper. |

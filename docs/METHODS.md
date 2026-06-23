# Methods & Interpretation

The scientific rationale behind the pipeline and how to read its outputs.

## Phylogenetic profiling in one paragraph
Genes/domains that are gained and lost together across evolution tend to be
functionally related (same pathway/complex). A **phylogenetic profile** is the
presence/absence pattern of a domain across a set of species. Domains with
**similar profiles** are candidate functional partners; species with similar
domain content are phylogenetically/functionally close. (Pellegrini et al., 1999.)

## From BLAST to profiles
Each query domain is BLASTed against species proteomes. A domain is called
**present** in a species when there is a hit with **E-value ≤ 1e-5**
(`create_correlation_matrix(evalue_threshold=1e-5)`). The cutoff matters: counting
every weak hit inflates co-occurrence and erases the signal. The result is a
species × domain matrix (counts; presence == value > 0).

## Species tree (Jaccard + Neighbour-Joining)
- For two species, distance = **Jaccard distance** between their binary domain
  profiles = 1 − |shared domains| / |domains in either|. Jaccard is the natural
  choice for sparse binary vectors (it ignores joint absences).
- A **Neighbour-Joining** tree (Saitou & Nei, 1987) is built from the pairwise
  distance matrix (`compute_distance_matrix` → `construct_tree`).
- Reading it: species joined low in the tree share most of their domain
  repertoire. Branch lengths are in Jaccard units.

## Domain clustering (Markov Clustering)
- Build a **domain × domain** similarity graph: similarity = Jaccard between the
  two domains' species profiles; draw an edge when similarity ≥ `threshold`
  (default 0.5), weighted by similarity.
- **MCL** (van Dongen, 2000; Enright et al., 2002) simulates flow on this graph;
  the **inflation** parameter (default 2.0) controls granularity (higher → more,
  smaller clusters). Clusters are groups of co-occurring domains = candidate
  functional modules.

## Validation — "are the results meaningful?"
MCL is **unsupervised**; there is no training/test split. Instead
`validate_clusters` reports:

- **Number / sizes of clusters.** One cluster containing ~all domains ⇒ no
  structure.
- **Modularity Q** (Newman, 2006) of the partition on the similarity graph.
  Rule of thumb: `Q < 0.05` ≈ no community structure; `Q > 0.3` ≈ meaningful
  modular structure.
- **Same-protein co-clustering rate** — an *internal ground truth*: several
  domains can belong to the same protein (shared accession prefix before the
  first `-`). Such domains are physically linked, so they should land in the same
  cluster. A high rate is necessary (but, if everything is one cluster, trivially
  satisfied — read it together with Q and sizes).
- A **warning** is emitted when the partition collapses to one dominant cluster.

### When to trust the output
Trust clusters when Q is well above 0, there are several non-trivial clusters,
**and** same-protein domains co-cluster. If Q ≈ 0 / one giant cluster, the
profiles are too uniform — use a stricter presence cutoff, a higher Jaccard
threshold, or data with more presence/absence variation.

### Note on the bundled dataset
On `data/Sequences-218-annot.Query.blastp`, domain profiles are near-uniform
(median pairwise Jaccard ≈ 0.59), so clustering yields one dominant cluster with
`Q ≈ 0` even with the e-value cutoff. The validation correctly flags this; it is a
property of the data, not a code defect.

## References
- Pellegrini M. et al. *Assigning protein functions by comparative genome
  analysis: protein phylogenetic profiles.* PNAS, 1999.
- Saitou N., Nei M. *The neighbor-joining method.* Mol. Biol. Evol., 1987.
- van Dongen S. *Graph Clustering by Flow Simulation.* PhD thesis, Utrecht, 2000.
- Enright A.J., van Dongen S., Ouzounis C.A. *An efficient algorithm for
  large-scale detection of protein families (MCL/TribeMCL).* NAR, 2002.
- Newman M.E.J. *Modularity and community structure in networks.* PNAS, 2006.
- Jaccard P. *The distribution of the flora in the alpine zone.* New Phytol., 1912.

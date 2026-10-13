# Science register: what's involved, implied, applied — and to what extent

This document answers one question precisely: **for every piece of external science Hesperia
touches, who did the original work, what did they publish, and how much of it does Hesperia
actually use?** It consolidates citations already scattered and verified across
`docs/foundations/references.md`, `corners/pipeline_l1_l11_science.md`'s formula-lineage table, and
`docs/foundations/provenance.md` — nothing here is a new claim; this is the first pass that puts
every name, year, and extent-of-use in one register organized by scientific discipline rather than
by pipeline layer or corner. Pair with `docs/publication/NOVELTY_AND_POSITIONING.md`: that document
states the *composition-level* contribution; this document is the *citation* register beneath it.

**A methodological note on sourcing, in the interest of the same honesty this whole documentation
program is built on:** most rows' author/year/title come directly from Hesperia's own docs (Shannon
1948, Gini 1912, Kirchhoff 1847, Watts & Strogatz 1998, Moore 1959, Robertson & Spärck Jones 1976,
Levenchuk's FPF, etc. — all verified quotes from `pipeline_l1_l11_science.md` or `references.md`).
A smaller number of rows name a technique Hesperia's own docs cite only by name (e.g. "the Louvain
method," "the Lesk algorithm," "Prolog") without a full author/year/title — for those, the complete
citation (Blondel, Guillaume, Lambiotte & Lefebvre 2008; Lesk 1986; Colmerauer & Roussel 1972;
Fellbaum 1998 for WordNet; Cauchy 1821/Schwarz 1888 for the inequality bearing their names) is
supplied here from established scientific record, not from a Hesperia source file. These are
standard, easily independently verified facts, not novel research claims, but they are marked here
so a co-author knows which citations to double-check against a primary source before a paper
submission, and which are already load-bearing quotes from this project's own prior verification
work.

This register follows the same branch discipline as the rest of the documentation program: a
scientific technique used first in TFP- or COBALT-facing work is still registered here at the level
of the core mechanism it actually serves, unless a cited spec explicitly narrows the scope.

## Extent-of-application taxonomy

Every row below is scored against one of five extents, so "we use X" never means five different
things across the table:

| Extent | Meaning |
|---|---|
| **Full, verbatim** | The formula/algorithm is used exactly as published, no modification beyond parameterization. |
| **Partial / narrow slice** | A deliberately small, named subset of a larger framework is adopted; the rest is explicitly not built. |
| **Structural analogy** | The *shape* of the construct (not its formula) is borrowed — e.g. a hex grid's uniform-adjacency property, not a specific hex-grid algorithm. |
| **Conceptual inspiration** | The idea motivated a Hesperia-native design choice; no formula or algorithm is shared. |
| **Explicitly rejected** | Considered and specifically *not* used, with the reason recorded — as scientifically significant as what was adopted, for a publication's honesty. |

## A. Information theory and statistics

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Claude Shannon (1948)**, *A Mathematical Theory of Communication* | `H = −Σp·log(p)`, normalized by `ln(F)` — the entropy of the 288-family hit distribution (L1 `FAMILY_ENTROPY`/`NORMALIZED_FAMILY_ENTROPY`), reused verbatim at 5 distinct pipeline points (L1 census, L4 evidence-spread entropy, `structural_monotony` diagnostic rule, shadow-correction's entropy-rise cap, KME-adjacent comparability) | **Full, verbatim** | `pipeline_l1_l11_science.md` §"Layer 1", §"Cross-cutting theme 2"; `references.md` |
| **Corrado Gini (1912)**, *Variabilità e mutabilità* | `GINI_COEFFICIENT` — standard sorted-array Gini formula over the family hit distribution, an independent concentration measure alongside entropy (the two can disagree in direction on the same distribution) | **Full, verbatim** | `pipeline_l1_l11_science.md` §"Layer 1"; `references.md` |
| **Andrey Kolmogorov** — Kolmogorov complexity | Considered as an alternative to Shannon entropy for "how much structure is really here" | **Explicitly rejected** — Kolmogorov complexity is uncomputable in general for an arbitrary string, structurally incompatible with a deterministic, re-runnable measurement system; Shannon entropy over a known finite distribution is exactly computable | `provenance.md`'s dedicated Kolmogorov check (`grep -rli kolmogorov` → zero matches anywhere in the repo or mirrored math drafts) |
| **Kullback–Leibler divergence** (Kullback & Leibler, 1951) | Considered for profile-deviation distance (comparing observed vs. expected family/area distributions) | **Explicitly rejected** — L2 (Euclidean) distance normalized by `√2` was chosen instead, specifically for finiteness (KL diverges to infinity when a support point has zero probability in one distribution, which is common with sparse family-hit vectors) | `pipeline_l1_l11_science.md`'s lineage table; `provenance.md`'s "what did not survive" section |

## B. Graph theory and topology

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Gustav Kirchhoff (1847)**, circuit laws (the original motivation for independent-cycle counting in a graph) | `Circuit rank = E − (V−1)` — L2's `LOOP_COUNT`/`LOOP_DENSITY`, applied to the BFS-induced subgraph | **Full, verbatim** (formula), applied to a different domain (semantic activation graph, not electrical circuits) | `pipeline_l1_l11_science.md` §"Layer 2" |
| **Duncan Watts & Steven Strogatz (1998)**, "Collective dynamics of 'small-world' networks," *Nature* | `C(v) = 2t / (k(k−1))` — local clustering coefficient, computed at the dominant family node only (not network-wide) | **Partial** — the formula is verbatim; the paper's small-world network *model* is not adopted, only its clustering-coefficient definition | `pipeline_l1_l11_science.md` §"Layer 2" |
| **E. F. Moore (1959)**; **C. Y. Lee (1961)** — BFS shortest-path algorithms | L2's traversal from the dominant family, depth-capped at 8 | **Full, verbatim**, on an unweighted graph (exact shortest-path distances) | `pipeline_l1_l11_science.md` §"Layer 2" |
| **Paul Jaccard (1901)**, set-overlap similarity | `VISITED_JACCARD_SIMILARITY`, `HIT_EVIDENCE_OVERLAP_*`, and other overlap-ratio variables across L3/L4 | **Full, verbatim** | `pipeline_l1_l11_science.md`'s lineage table |
| **Gerard Salton (1975)**, vector space model / cosine similarity | `HIT_VECTOR_COSINE_SIMILARITY` (L3 baseline/shadow comparison) | **Full, verbatim** | `pipeline_l1_l11_science.md`'s lineage table |
| **Leonhard Euler** — Euler characteristic (polyhedral formula, `V − E + F = 2`) | The unavoidable-12-pentagonal-defect constraint on any hexagon tiling of a closed sphere — backs the 72,000 vs. 72,240 hex-count distinction (GCS variant) | **Full theorem application** (a mathematical necessity, not a chosen parameter) | `references.md` §"Hexagonal grids and diffusion" |
| Regular icosahedron (**Platonic solid construction**, golden ratio `φ = (1+√5)/2`) | The 12-area sphere: `sphere/topology/embedding.py` constructs area coordinates directly from `φ` | **Full, verbatim** — 12 areas is geometrically forced by this construction, not an arbitrary design choice | `references.md` §"Geometric and stochastic process foundations" |
| Hexagonal grid uniform adjacency (general spatial-indexing literature, e.g. **Uber H3**) | Structural justification for a hex (not square) substrate: every cell has the same number of equidistant neighbors | **Structural analogy** — the uniform-adjacency *property* is borrowed, not H3's specific indexing algorithm | `references.md` §"Hexagonal grids and diffusion" |

## C. Dynamical systems and stochastic processes

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Andrey Markov (1906)**; **Andrey Kolmogorov (1931)** — Chapman–Kolmogorov equations | Multi-step trajectory probability composition in `sphere/dynamism/` | **Full, verbatim** (equation form) | `pipeline_l1_l11_science.md` §"Layer 6" |
| **Aleksandr Lyapunov (1892)**, *The General Problem of the Stability of Motion* | L6's `LYAPUNOV_ESTIMATE` — a scalar proxy for how quickly small attribution perturbations grow/shrink across the BFS radius | **Conceptual inspiration / proxy** — explicitly **not** a literal Lyapunov exponent (that would require iterating a perturbation and measuring divergence rate over many steps; L6 computes a single-step proxy) | `pipeline_l1_l11_science.md` §"Layer 6", stated directly as "not live, not a literal exponent" |
| Markov chains (discrete-time, finite-state) and lazy chains | `core/math/core_math.py`'s `base_step` — row-stochastic transition matrix mixed with self-retention | **Structural analogy, explicitly qualified** — described as "Markov-**like**," per the project's own scientific-alignment discipline (`provenance.md`), because no statistical fitting, stationary-distribution analysis, or HMM likelihood inference is implemented; only the deterministic transition-matrix *shape* is borrowed | `references.md` §"Geometric and stochastic process foundations"; `provenance.md`'s terminology-precision note |
| **Sergey Brin & Larry Page (1998)**, "The Anatomy of a Large-Scale Hypertextual Web Search Engine" (PageRank) | `v' = (1−α)v + α·vW` — the diffusion step's lazy-random-walk form | **Structural analogy** — the lazy-random-walk mixing form is shared; Hesperia's `W` is a semantic adjacency matrix, not a web-link graph, and there is no eigenvector-convergence claim being made | `pipeline_l1_l11_science.md`'s lineage table |
| **Louis Lapicque (1907)** — leaky integrate-and-fire (LIF) neuron model | `H_self = v·(1−decay)` — Euler discretization of `dv/dt = −decay·v`, the self-decay term in `compute_h_total` | **Structural analogy** — the decay-ODE *shape* is shared; no spiking/threshold-firing mechanism is implemented | `pipeline_l1_l11_science.md`'s lineage table; `corners/physics_dynamics_coupling.md` |
| **Pierre Weiss (1907)** — mean-field theory (Curie–Weiss) | `H_coupling = α·mean(v)` — the coupling term in `compute_h_total` | **Structural analogy** — mean-field averaging as a coupling mechanism, not a magnetic-domain physical claim | `pipeline_l1_l11_science.md`'s lineage table |

## D. Classical / metric geometry

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Pythagoras** (~500 BCE, classical geometry); **Augustin-Louis Cauchy (1821)** / **Hermann Schwarz (1888)** — Cauchy–Schwarz inequality | L5 Part 5B's trigonometric/metric-space self-test: cosine identity consistency, `‖v‖² + ‖w‖² − ‖v+w‖² = 2(v·w)` (Pythagorean residual), triangle inequality residual — a floating-point sanity check that the system's own vector operations still satisfy Euclidean metric-space axioms | **Full, verbatim** (as a live numerical self-test, not a taught theorem) — these are formal tautologies in exact arithmetic, made non-trivial specifically by floating-point rounding | `pipeline_l1_l11_science.md` §"Layer 5, Part 5B" |
| Classical metric geometry — L2 (Euclidean) distance | `FPD`/`APD` (Family/Area Profile Deviation), normalized by `√2` (max possible L2 distance between two probability vectors) | **Full, verbatim**, chosen over KL divergence specifically for finiteness (see §A) | `pipeline_l1_l11_science.md`'s lineage table; `docs/specs/history/34_SPEC_N1_...txt` |

## E. Information retrieval

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Stephen Robertson & Karen Spärck Jones (1976)**, "Relevance weighting of search terms," crystallized through **TREC** evaluations (1994) — BM25 | L4's retrieval mode, tagged `RETRIEVAL_MODE_ID = "LEX_BM25_V1"` | **Full, verbatim** — the standard lexical retrieval function | `layers/L4_evidence_retrieval.md` (verified, lines 29 and 249) |
| **TF–IDF** (Term Frequency–Inverse Document Frequency, no single canonical author — a convergent 1970s IR development) | Cited in the founding design memo (`docs/foundations/theory_description.txt`) as the deterministic baseline for concept salience | **Conceptual inspiration** — informs why attribution/weighting uses fixed, explicit aggregation formulas rather than learned weighting; not a literally computed TF-IDF score in the shipped pipeline | `references.md` §"Association and salience measures" |
| **Pointwise Mutual Information (PMI)** | Cited in the design memo as basis for deterministic concept-graph edge construction | **Conceptual inspiration** — informs the fixed-weight philosophy behind `specs/canon/concept_relation_weights.yaml`/`propagation_weights.yaml`, not a literally computed PMI score | `references.md` §"Association and salience measures" |

## F. Knowledge organization and controlled vocabularies

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **SKOS** (Simple Knowledge Organization System, W3C) | Dict A (surface label) / Dict B (concept) split; Dict A's "hidden labels" for misspellings/transcription variants directly adopts SKOS's hidden-label concept; broader/narrower discipline constrains family/area membership | **Structural analogy / partial adoption** of the labeling and relation taxonomy, not the RDF/OWL serialization itself | `references.md` §"Knowledge organization and controlled vocabularies" |
| **MeSH** (Medical Subject Headings) / **UMLS Metathesaurus** | Cited as existence-proof that domain-stable controlled vocabularies make deterministic concept mapping tractable at scale | **Conceptual inspiration** — justifies treating TFP/clinical terminology as a controlled domain rather than open vocabulary; MeSH/UMLS data itself is not ingested | `references.md` |
| **LIWC** (Linguistic Inquiry and Word Count) | Backs the requirement that normalization support stemming/morphological families deterministically, and that a versioned, regression-tested dictionary can remain operationally stable | **Conceptual inspiration** | `references.md` |
| **Lesk algorithm** (Michael Lesk, 1986) and adapted/WordNet-extended Lesk variants | Backs the resolver's context-overlap scoring requirement: disambiguation must be deterministic, auditable per decision | **Conceptual inspiration** — the overlap-scoring *principle*, not the original dictionary-gloss-overlap implementation | `references.md` §"Word-sense disambiguation" |
| **WordNet** (Fellbaum, ed., 1998) — synsets | Closest existing analogue to Hesperia's surface-string → concept(s) → relations → grouping chain | **Structural analogy** — supports treating concepts as first-class IDs distinct from surface labels; Hesperia does not consume WordNet data directly | `references.md` |

## G. Innovation and contradiction engineering

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Genrich Altshuller** — TRIZ (Theory of Inventive Problem Solving) | 3 typed relation kinds and 4 of the 40 inventive principles (segmentation, counterbalance, parameter_change, dynamic_adaptation), classified lexically-first with a deterministic hash fallback | **Partial / narrow slice** — explicitly not the full 39×39 contradiction matrix or all 40 principles | `corners/triz_extension.md`; `references.md`; `NOVELTY_AND_POSITIONING.md` |
| **Vincent Blondel, Jean-Loup Guillaume, Renaud Lambiotte, Etienne Lefebvre (2008)**, "Fast unfolding of communities in large networks" — Louvain method | Innovation-cluster detection (`networkx.community.louvain_communities`), run with a fixed seed (`LOUVAIN_SEED=42`) specifically because Louvain's tie-breaking is otherwise non-deterministic | **Full, verbatim** (algorithm), Hesperia-specific addition is only the reproducibility seed | `references.md`; `corners/triz_extension.md`; `parameter_catalog.md` §7 |

## H. Symbolic and propositional logic

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| Standard propositional operator set (AND, OR, NOT, IMPLIES, IFF, XOR) | The YAML-driven threshold rule engine and the fpf_bridge's seven decision rules, deliberately using all six operators — IFF/XOR specifically encode consistency-checking and mutual-exclusivity that AND/OR cannot express precisely | **Full, verbatim** (standard logical calculus) | `references.md` §"Propositional and symbolic logic" |
| **Prolog** (Colmerauer & Roussel, 1972) — logic-programming, declarative inference | The optional L9b symbolic inference layer, separate from the YAML threshold engine | **Full, verbatim** (the inference paradigm), a narrow/optional slice of what a full Prolog system offers | `corners/prolog_logic.md`; `references.md` |

## I. Trust and reasoning substrates

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Anatoly Levenchuk** — FPF (First Principles Framework), a ~51,300-line transdisciplinary reasoning specification (`FPrincipleF/FPF-Spec.md`) | Layer 11's `EvidencePrimitive` trust tuples are a working implementation of FPF Part B.3's FGR ⟨Formality, Ground/Scope, Reliability⟩ trust calculus, consumed via the `fpf-thinking-map` PyPI package | **Full, verbatim** application of the FGR calculus specifically; the rest of FPF's ~51,300-line specification (holons, bounded contexts generally) is not claimed as implemented beyond this calculus | `corners/fpf_bridge.md`; `provenance.md`'s full audit; `references.md` |

## J. Clinical domain grounding

| Name(s), year, work | What Hesperia uses | Extent | Where |
|---|---|---|---|
| **Transference-Focused Psychotherapy (TFP)** clinical literature — a manualized, structured psychodynamic treatment studied via randomized controlled designs | Cited in the founding design memo to justify why structured, stage-aware trajectory features (not raw word counts) are a rational calibration/research target | **Conceptual inspiration / domain grounding only** — Hesperia does **not** implement TFP theory; it measures structural features a TFP-aware downstream consumer can interpret | `references.md` §"Domain grounding (clinical)"; `corners/corpus_wiring.md` |

## K. Documentation and quality engineering standards (this program's own meta-layer)

Not natural science, but named, published standards this documentation program itself applies —
included for completeness since a reviewer may ask the same "how much of X do you actually follow"
question about these as about TRIZ or FPF:

| Standard | What this program uses | Extent | Where |
|---|---|---|---|
| **ISO/IEC/IEEE 42010** (systems and software engineering — architecture description) | Stakeholder/concern/viewpoint structure | **Structural analogy / document-type checklist** — not seeking literal certification | `docs/iso/ARCHITECTURE_DESCRIPTION.md` |
| **ISO/IEC/IEEE 29148** (requirements engineering) | FR/NFR traceability format | **Structural analogy** | `docs/iso/REQUIREMENTS_SPECIFICATION.md` |
| **ISO/IEC 25010 (SQuaRE)** (product quality model) | Eight quality-characteristic mapping | **Structural analogy** — two of eight characteristics left honestly incomplete rather than filled with unverified claims | `docs/iso/QUALITY_MODEL.md` |
| **ISO/IEC/IEEE 12207** (software life cycle processes) | Process-category mapping over the existing seal/release discipline | **Structural analogy** | `docs/iso/LIFECYCLE_PROCESS.md` |
| **ISO/IEC/IEEE 15289** (content of life-cycle information items) | The traceability-matrix-as-information-item-register pattern | **Structural analogy** | `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md` |
| **ISO/IEC/IEEE 26511/26512** (user documentation) | Practical operator-guide structure | **Structural analogy** | `docs/iso/OPERATOR_GUIDE.md` |

## L. Productization-language boundary

The dated productization wording preserved in `UPCELERATOR_PRODUCTIZATION_QA.md` ("accountable AI,"
"deterministic validation," "evidence-grade audit trace") is **not** a separate scientific layer.
It is a buyer-facing summary of mechanisms already registered above: determinism, auditability,
governed narration, and reproducible evidence routing. This note exists so later documentation runs
do not accidentally treat product phrasing as if it named a new theory family of its own.

## Summary count

Approximately **35 distinct named scientific/engineering works** across 11 disciplines are
registered above: 3 explicitly rejected (Kolmogorov complexity, KL divergence — both in §A — plus
the general discipline of not overclaiming statistical/Markov-chain fitting in §C), roughly a dozen
at **full, verbatim** extent, roughly a dozen at **structural analogy**, and the remainder at
**conceptual inspiration**. No entry claims Hesperia invented a mathematical or algorithmic
technique — consistent with `NOVELTY_AND_POSITIONING.md`'s central claim that the contribution is
architectural composition, not new mathematics.

## What this document does not cover

- The 35 KME derived-metric codes (`KDI`, `KSI`, etc.) are Hesperia-coined *names*, not borrowed
  *science* — their terminology status (proposed expansions, pending author confirmation) is
  `docs/publication/TERMINOLOGY_AND_ABBREVIATIONS.md`'s concern, not this document's.
- `hesperia/extensions/dynamics/`'s own internal physics-styled equations
  (`SemanticFieldParamsV1`: diffusion/resistance/contradiction-pressure/source terms) are not
  registered here because, per `corners/field_dynamics.md`, that subsystem has no path to either
  live product surface — citing its science lineage in a publication about what Hesperia *does*
  today would be premature. Revisit this section if that wiring changes.

## Maintenance rule

Registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. Any new corner doc or layer doc that
introduces a new named external technique must add a row here in the same commit — an unregistered
citation is the same class of gap this document was created to close for abbreviations in
`TERMINOLOGY_AND_ABBREVIATIONS.md`.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`NOVELTY_AND_POSITIONING.md`](NOVELTY_AND_POSITIONING.md) (the composition-level claim this citation register sits beneath) · [`TERMINOLOGY_AND_ABBREVIATIONS.md`](TERMINOLOGY_AND_ABBREVIATIONS.md) (coined names, as distinct from this document's borrowed-science names) · [`../foundations/corners/pipeline_l1_l11_science.md`](../foundations/corners/pipeline_l1_l11_science.md) (the original formula-lineage table this document consolidates)

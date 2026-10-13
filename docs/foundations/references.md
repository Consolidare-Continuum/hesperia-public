# References — load-bearing scientific/theoretical grounding

This list contains only references actually invoked as reasoning support
elsewhere in `docs/foundations/`. Each entry states the specific Hesperia
decision it backs, not a general endorsement of the source.

## Knowledge organization and controlled vocabularies

- **SKOS (Simple Knowledge Organization System, W3C)** — formalizes concept
  schemes, preferred/alternative/hidden labels, and broader/narrower/mapping
  relations. Backs the Dict A (surface label) / Dict B (concept) split in
  `corners/lexicon_resolver.md`: Dict A's "hidden labels" for misspellings and
  transcription variants is a direct adoption of SKOS's hidden-label concept,
  and the broader/narrower discipline is what keeps family/area membership
  from becoming an underconstrained "everything relates to everything" graph.
- **MeSH (Medical Subject Headings) / UMLS Metathesaurus** — controlled,
  hierarchical biomedical vocabularies with systematic noun-phrase-to-concept
  matching at scale. Cited in `corners/lexicon_resolver.md` as the existence
  proof that domain-stable terminology plus a controlled vocabulary makes
  deterministic concept mapping tractable — the same logic that justifies
  Hesperia treating TFP/clinical terminology as a controlled domain rather
  than open vocabulary.
- **LIWC (Linguistic Inquiry and Word Count)** — a deterministic,
  dictionary-based text classifier supporting word stems and multi-category
  membership per match. Backs two decisions in `corners/lexicon_resolver.md`:
  the requirement that normalization support stemming/morphological families
  deterministically, and the general principle that "preset categories +
  curated dictionary" can be operationally stable across versions if the
  dictionary itself is versioned and regression-tested.

## Word-sense disambiguation

- **Knowledge-based WSD / Lesk algorithm and its WordNet-based extensions
  (adapted Lesk)** — dictionary-overlap-based sense disambiguation, extended
  via semantic-network relations rather than raw gloss text. Backs the
  resolver's context-overlap scoring requirement in
  `corners/lexicon_resolver.md`: disambiguation must be deterministic,
  auditable per decision, and based on explicit overlap/coherence scoring
  rather than opaque statistical inference.
- **WordNet synsets** — sets of cognitive synonyms representing one distinct
  concept, linked by explicit semantic relations. Cited as the closest
  existing analogue to Hesperia's "surface strings → concept(s) → relations →
  higher grouping" chain, supporting the architectural decision to treat
  concepts as first-class IDs distinct from their surface labels.

## Hexagonal grids and diffusion

- **Hexagonal grid uniform adjacency (general spatial-indexing literature,
  e.g. Uber H3)** — hex grids give every cell the same number of neighbors at
  equal distance, unlike square grids' unequal edge/corner neighbor
  distances. Backs the choice of a hex (not square or arbitrary) substrate in
  `corners/hex_substrate.md`, and the parallel choice of an icosahedral
  (uniform-degree) area layout in `corners/topology_geometry.md`.
- **Graph diffusion / heat-equation dynamics (Laplacian L = D − A, dc/dt =
  −αLc)** — standard formalism for spreading a signal across a graph in
  proportion to its structure. Backs the propagation engine's design in
  `corners/propagation_dynamics.md` as a deterministic, parameter-bounded
  alternative to a learned smoothing model, and backs the entropy-correction
  rationale in `corners/shadow_correction.md` (diffusion mathematically and
  unavoidably raises entropy on a connected graph; shadow correction exists
  to cap that known side effect, not to prevent it).
- **Geodesic sphere tessellation / unavoidable pentagon defects in
  hex-on-sphere tilings** — any attempt to tile a sphere with hexagons leaves
  exactly 12 pentagonal defects (Euler characteristic constraint on closed
  polyhedral surfaces). Backs the 72,000 vs. 72,240 hex-count distinction and
  the pentagon-pole extra-slot allocation in `corners/hex_substrate.md`'s GCS
  variant.
- **Shannon entropy (not Kolmogorov complexity)** — the actual information-theoretic tool used
  throughout (`structural_monotony` in `specs/canon/diagnostic_rules.yaml`, `corners/logic_guards.md`;
  the entropy rise shadow correction exists to bound, `corners/shadow_correction.md`). Chosen over
  Kolmogorov complexity specifically because it is exactly computable over a known distribution,
  where Kolmogorov complexity is uncomputable in general — incompatible with a deterministic,
  re-runnable system. See `provenance.md` for the explicit check that ruled Kolmogorov out.

## Geometric and stochastic process foundations

- **Regular icosahedron (Platonic solid construction, golden ratio φ)** — the unique Platonic solid
  with 12 vertices, each of constant degree 5. Backs `corners/topology_geometry.md`'s claim that 12
  areas is geometrically *forced*, not chosen: `sphere/topology/embedding.py` constructs the area
  coordinates directly from `φ = (1+√5)/2`, the standard icosahedron derivation.
- **Markov chains (discrete-time, finite-state) and lazy chains** — a row-stochastic transition
  matrix mixed with self-retention to ensure well-behaved iteration. Backs `core/math/core_math.py`'s
  `base_step` (`corners/core_math_contract.md`). The project's own scientific-alignment guidance
  (cited in `provenance.md`) is followed here: described as "Markov-like," since no statistical
  fitting, stationary-distribution analysis, or HMM likelihood inference is implemented — only the
  deterministic transition-matrix shape is borrowed.

## Innovation and contradiction analysis

- **TRIZ (Theory of Inventive Problem Solving), Genrich Altshuller** — technical contradictions and
  the 40 inventive principles. Backs `corners/triz_extension.md`: Hesperia adopts 3 typed relation
  kinds and 4 of the 40 principles (segmentation, counterbalance, parameter_change,
  dynamic_adaptation), not the full matrix/taxonomy, classified lexically-first with a deterministic
  hash fallback to preserve the system's determinism guarantee even in this normally-fuzzy domain.
- **Louvain method (modularity-maximization graph clustering)** — a standard, published community-
  detection algorithm (`networkx.community.louvain_communities`). Backs the innovation-cluster
  detection in `corners/triz_extension.md`, run with a fixed seed specifically because Louvain's
  tie-breaking is otherwise non-deterministic.

## Association and salience measures

- **TF-IDF** — cited in the founding design memo (`docs/foundations/theory_description.txt`)
  as the deterministic baseline for concept salience relative to a text;
  informs why attribution/weighting in `corners/layer_contracts_attribution.md`
  is computed via explicit, fixed aggregation formulas rather than learned
  weighting.
- **Pointwise Mutual Information (PMI)** — standard deterministic association
  measure for concept co-occurrence. Cited in the design memo as the basis
  for building deterministic concept-graph edges; informs the fixed-weight
  philosophy behind `specs/canon/concept_relation_weights.yaml` and
  `propagation_weights.yaml` discussed in `corners/propagation_dynamics.md`.

## Propositional and symbolic logic

- **Standard propositional operator set (AND, OR, NOT, IMPLIES, IFF, XOR)**
  and **logic programming (Prolog-style declarative inference)** — back the
  separation between the YAML-driven threshold rule engine and the
  Prolog-based symbolic inference layer in `corners/logic_guards.md`, and the
  deliberate use of all six operators (rather than just AND/OR) across
  fpf_bridge's seven decision rules in `corners/fpf_bridge.md`, where IFF and
  XOR specifically encode consistency-checking and mutual-exclusivity
  relationships that AND/OR cannot express precisely.

## Trust calculus and reasoning substrates

- **FPF (First Principles Framework), Anatoly Levenchuk** — a transdisciplinary reasoning
  specification built on holons, bounded contexts, and the FGR (Formality/Ground/Reliability)
  trust calculus (Part B.3). Backs `corners/fpf_bridge.md` directly: the bridge's `EvidencePrimitive`
  trust tuples are a working implementation of FPF's ⟨F, G, R⟩ calculus, consumed via the
  `fpf-thinking-map` PyPI package rather than the FPF document itself. See `provenance.md` for the
  full audit of what is and isn't actually derived from this source.

## Domain grounding (clinical)

- **Transference-Focused Psychotherapy (TFP)** — described in the clinical
  literature as a manualized, structured psychodynamic treatment studied via
  randomized controlled designs. Cited in the design memo only to justify why
  structured, stage-aware trajectory features (rather than raw word counts)
  are a rational target for the TFP-specific calibration and research work
  referenced in `corners/calibration.md` and the `research/clinical_tfp/`
  module — Hesperia does not implement TFP theory itself, only measures
  structural features that a TFP-aware downstream consumer can interpret.

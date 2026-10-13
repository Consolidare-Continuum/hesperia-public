# Corner: TRIZ Analytics Layer (`hesperia/extensions/triz/`)

**Location:** 30+ modules under `hesperia/extensions/triz/` (`contradiction_engine.py`,
`novelty_engine.py`, `commercial_intelligence.py`, `kme_bridge.py`, `guards.py`,
`topology_activation_pipeline.py`, `exporters.py`, `meta_synthesis.py`, and others).
Self-described as "isolated from KME core metrics" — a downstream consumer, not a modification, of
`corners/kme.md`'s active-graph substrate.

## Why TRIZ at all

TRIZ (Genrich Altshuller's Theory of Inventive Problem Solving) starts from a specific claim: most
apparent problems are really *contradictions* — improving one parameter degrades another — and
inventive solutions come from resolving the contradiction rather than trading it off. Hesperia
already has, by this point in the castle, a deterministic way to know which concepts are active in
a text and how they relate (`corners/hex_substrate.md`, `corners/lexicon_resolver.md`). TRIZ
supplies the missing piece: a vocabulary and a classification scheme for what it *means*, in
engineering/innovation terms, when two active concepts are in tension — something neither the
sphere pipeline's structural guards nor KME's coherence/density metrics are built to characterize
in human-actionable language.

## What was adopted, and what deliberately wasn't

Classic TRIZ has two famous heavy machines: a 39×39 engineering-parameter contradiction matrix, and
the full taxonomy of 40 inventive principles. Hesperia's `contradiction_engine.py` uses neither at
that scale. It works from three typed relation kinds (`conflict`, `negation`, `opposition`, each
with a fixed weight: 1.0, 1.0, 0.85) and classifies a detected contradiction into one of only
**four** inventive principles: `segmentation`, `counterbalance` (Altshuller's "anti-weight"),
`parameter_change`, `dynamic_adaptation` ("dynamicity"). Classification tries a lexical table first
(`triz_classifier.py`); if no lexical match exists, it falls back to a **stable hash bucket** over
the sorted concept-id pair — never a random or model-driven guess. This is the same determinism
discipline as the rest of the system applied to a domain (creative/innovation classification) that
is normally treated as inherently fuzzy: even "which of four inventive principles does this
tension resemble" must be reproducible from the same two concept IDs every time, with no hidden
state. The four-principle reduction is itself a judgment call — broad enough to be useful, narrow
enough that the lexical table and hash fallback can stay auditable rather than becoming a 40-way
classifier nobody could review by hand.

## The math: contradiction density, clustering, and innovation scoring

- **Contradiction signals** (`ContradictionSignal`) carry a `score` (the relation weight, possibly
  combined with activation strength) and a `triz_class`. `novelty_engine.py`'s
  `compute_contradiction_density` aggregates these per area/family — a count-and-weight rollup, not
  a learned model.
- **Innovation clusters** (`InnovationCluster`) come from **Louvain community detection**
  (`networkx.community.louvain_communities`), a real, well-established modularity-maximization
  graph clustering algorithm — run with a **fixed seed (`LOUVAIN_SEED = 42`)** specifically because
  Louvain's internal tie-breaking is otherwise order-dependent; pinning the seed is the same
  reproducibility discipline as `propagation_weights.yaml` being checked into canon rather than
  inferred at runtime (`corners/propagation_dynamics.md`). Each cluster carries `rarity`,
  `contradiction_density`, `propagation_reach`, and a composite `innovation_score` — explicit,
  inspectable fields, not a single opaque "novelty" scalar.
- **Narrative signals** (`NarrativeSignal`) track `penetration`, `velocity`, `stability` of an
  activated-area pattern over a sequence — the TRIZ-layer analogue of `corners/propagation_dynamics.md`'s
  dynamism module, but scoped to contradiction/narrative spread specifically rather than general
  structural-state trajectory.

## Why this is a read-only, structurally isolated layer

`guards.py`'s `TRIZ_READONLY_MESSAGE` states the boundary explicitly: "No mutation of ontology
files, dict A/B, topology adjacency, or creation of new Areas/Families/Hexes." TRIZ also treats two
"meta" areas (A6, A12 — `META_AREA_INDICES`) as non-lexically-activatable reference points rather
than ordinary content areas. This is the identical discipline `corners/fpf_bridge.md` uses for its
own read-only boundary against `sphere/`: a second analytical layer is only safe to bolt onto a
deterministic core if it cannot become a second source of truth for the structures the core already
owns. `kme_bridge.py` reinforces this at the data-structure level too — "single ActiveGraph + ...
Read-only; no second graph type" — TRIZ doesn't maintain its own competing concept graph, it reads
KME's.

## What is genuinely commercial here (and what isn't)

`commercial_intelligence.py` and `exporters.py` are the most directly product-shaped code in the
entire repo — not because the rest lacks value, but because this is the one corner whose modules
are named after the deliverable, not the mechanism: `export_policy_report` (**Policy Contradiction
Detector**), `export_innovation_radar` (**Innovation Radar**), `export_narrative_monitor**
(**Narrative Monitor**), plus comparative/system-stability schemas and (per the demo fixtures in
`examples/extensions/triz_demo/triz/outputs/`) an investor-snapshot shape. The honest distinction to
draw: the deterministic core (lexicon → hex → propagation → guards → KME) is the part that makes
*any* output trustworthy — it is necessary infrastructure, but infrastructure is not what a buyer
licenses. The TRIZ layer's exported products are what take that trustworthy substrate and turn it
into a named, demo-able, domain-framed deliverable (innovation scouting, policy-conflict
monitoring, narrative-spread tracking) that a non-technical buyer can evaluate without
understanding Sigma/Gamma/Theta at all. That framing — sellable surface on top of an unsellable
(because invisible-when-working) determinism core — is the same shape as the FPF bridge
(`corners/fpf_bridge.md`): the deterministic layers prove trustworthiness; the bridges (fpf_bridge
to an LLM, TRIZ to a policy/innovation audience) are what make that trustworthiness legible to a
consumer who isn't going to read the guard invariants.

## Relationship to neighboring corners

- Strictly downstream of and read-only against `corners/kme.md`'s `ActiveGraph` — does not define
  a second concept-graph representation.
- Shares the hex/family/area coordinate system from `corners/hex_substrate.md` and
  `corners/topology_geometry.md` (`MatrixCoordinate`), rather than inventing its own geometry.
- Independent of, and does not feed, `corners/guards.md`'s Sigma/Gamma/Theta certification path —
  TRIZ outputs are decision-intelligence products for a downstream audience, not canonical-output
  determinations.

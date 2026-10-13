# Corner: Knowledge Metrics Engine (KME) — `core.domain` + compatibility facade

**Canonical location:** `core/domain/{active_graph,bridge,extractor,fingerprint,loader,models,pipeline,primitive_metrics,derived_metrics,profile}.py`

**Compatibility surface:** `hesperia/engine/kme/` remains importable as a shim layer, including
`clinical_bridge.py` and the preserved legacy import paths. Standalone from the `sphere/` L1–L10
pipeline — it consumes Dict-A/B activation output, not raw text.

## Why this corner exists at all

The sphere pipeline (`corners/sphere_pipeline.md`) answers "what structural state does this text
produce." KME answers a different question: "how much actual knowledge structure — density,
coverage, coherence — does the activated concept graph for this text or domain exhibit, expressed
as a fixed, comparable vector?" Where Sigma/Gamma/Theta certify that a *run* was valid, KME
produces a *measurement artifact* (a fingerprint) that two different texts, or the same text at two
points in time, can be compared against — something none of L1–L10 is built to do, because their
job is per-run structural classification, not cross-run comparability.

## Why six bounded primitives, not the raw graph, feed everything downstream

`core.domain.active_graph` first canonicalizes activation into a deterministic graph
`A = (V_A, E_A)` ("same text + same domain graph → identical active graph" — its own docstring
states the determinism contract directly), then `primitives/calculator.py` reduces that graph plus
the frozen domain constants (`DomainConstants`: node count, degree p95, distance p95) to exactly
six numbers, each independently clamped to `[0, 1]`:

| Primitive | Name | What it measures |
|---|---|---|
| `LD` | LogicalDensity | how densely the activated concepts interconnect |
| `COH` | Coherence | how much the activated subgraph holds together as one structure vs. fragments |
| `NC` | NodeCoverage | how much of the reference domain graph the text actually touches |
| `PR` | PropagationRadius | how far activation had to spread to reach its coverage |
| `PV` | PropagationVolume | how much total activation mass spread, independent of radius |
| `CI` | ConcentrationIndex | how concentrated vs. diffuse the activation is |

Collapsing to six bounded numbers before any further computation is the same discipline as
Sigma's static-shape checks (`corners/guards.md`): once these six are fixed and in `[0, 1]`, every
downstream computation is pure algebra over a small, well-defined input space, with no path back to
the raw graph that could reintroduce non-determinism or unbounded values.

## Why 35 derived metrics are pure ratio/product algebra, not 35 independent measurements

`core.domain.derived_metrics` builds all 35 derived metrics as products and ratios of the same six
primitives — e.g. `KSI = clamp01(safe_div(COH * LD, PR))` (coherent, dense structure achieved per
unit of propagation radius spent reaching it — a structural-efficiency reading, not a separate
measurement), `KDI = clamp01(LD * COH)`, `CII = clamp01(safe_div(NC, PR))`. None of the 35 read the
graph again; each is `clamp01`/`safe_div` composition over the same six bounded inputs. This is
deliberate: defining new "metrics" as fresh graph computations would each need their own
correctness argument and could each introduce their own edge cases (division by a near-zero
radius, NaN propagation). Defining them as bounded algebra over six already-validated primitives
means `clamp01` (NaN/Inf/out-of-range → 0.0 or 1.0) and `safe_div` (denominator ≤ 0 → 0.0) are the
*only* two failure-handling rules in the entire 35-metric surface, proven once and inherited by
every derived metric rather than re-implemented 35 times.

## Why fingerprints are hashed vectors, not the metrics objects themselves

`core.domain.fingerprint` doesn't ship `PrimitiveMetrics`/`DerivedMetrics` objects as the
comparison artifact — it serializes them into a fixed-order 41-element vector (`PRIMITIVE_ORDER +
DERIVED_ORDER`), rounds to a fixed scale, and hashes it (`FINGERPRINT_VERSION = "hesperia_fp_v0_1"`,
docstring: "Same input metrics -> same fingerprint bytes"). A vector with a stable element order and
a content hash is what makes "compare this document's knowledge structure to that one's" a
byte-equality or vector-distance operation (`fingerprint_distance.py`) rather than a
field-by-field object comparison that would silently break the moment a field were added, renamed,
or reordered.

## Relationship to neighboring corners

- `hesperia.engine.kme.clinical_bridge` is the only preserved compatibility-facing place KME
  touches the rest of the system: it converts Dict-A/B
  session activation (`corners/lexicon_resolver.md`'s output) into the `DomainGraph`/`ConceptHit`
  shapes KME's active-graph canonicalizer expects — "concept nodes ≈ hex cells," explicitly
  reusing the hex substrate's concept identity (`corners/hex_substrate.md`) rather than defining a
  second one.
- Is the corner `docs/DOC_INDEX.md`'s disambiguation note ("Bare 'KSI' in runtime docs is
  ambiguous — always qualify") is actually about: **KSI** here is one specific derived metric
  (`KME-KSI-score`, a ratio of three primitives), distinct from **KSI-Inspector** (a separate
  inspection tool referenced in `corners/metric_registry.md`'s `metric_layer=concept_graph`
  material) — same three letters, two unrelated artifacts, and this corner is the one that owns
  the metric while not owning the tool.
- Independent of `corners/release_seal.md`'s certification path: KME produces a measurement
  artifact a downstream (e.g. clinical/TFP) consumer interprets, not a Sigma/Gamma/Theta-style
  pass/fail verdict — see `provenance.md`'s TFP grounding note for why structural fingerprints,
  not raw word counts, are the rational target here.

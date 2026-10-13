# Corner: Geometry as Math Constraint — How Topology Enforces Activation, Propagation, and Pre-placement Logic

This is a cross-cutting document. `corners/topology_geometry.md` and `corners/hex_substrate.md`
describe what the geometry *is*. `corners/core_math_contract.md` describes what the math *does*. This
corner closes the gap between them: it answers the question a physicist or systems engineer would ask —
**how does the geometry constrain, enable, or fully determine each mathematical operation in the
pipeline?** The answer is more direct than it might seem: the geometry is not a backdrop for the math.
For most of the propagation pipeline, the geometry *is* the math's primary input.

---

## The core claim: W IS the geometry

`base_step`'s diffusion equation is `D = (1−λ)·E + λ·(E·W)`. Every propagation result the system
produces depends on `W`. And `W` is the adjacency matrix of the hex graph — which means **changing
the geometry changes every result**, not through some indirect chain of effects, but directly, because
`W` is the geometry's own numeric encoding. The hex structure decides which `W[i][j]` entries are
non-zero. The hex degree (how many neighbors each cell has) decides what values those entries take.
The topology of the sphere (open or closed) decides whether all rows of `W` are identical in
structure. These are not design choices made after the geometry is set — they are the geometry, just
written as a matrix.

`make_demo_W(n)` states this plainly in its own docstring: **"Row-stochastic n × n (uniform
outflow)"** — `return [[1.0/n]*n for _ in range(n)]`. The "uniform outflow" is a direct consequence
of uniform adjacency: every node has the same number of equidistant neighbors, so each neighbor gets
the same weight, and the row automatically sums to 1 without any per-cell normalization step. On a
square grid, edge-neighbors are closer than corner-neighbors, so uniform weight would require a
correction; on a hex grid, all six neighbors are equidistant, so the uniform row-stochastic matrix
is the *exact* geometric truth, not an approximation.

---

## Icosahedral degree-5 uniformity → symmetric adjacency → uniform propagation behavior

The regular icosahedron has 12 vertices, each with exactly 5 equidistant neighbors — constant degree 5.
`sphere/topology/embedding.py` constructs these vertices directly from `PHI = (1 + √5) / 2`:

```python
ICOSAHEDRON_VERTICES_RAW = (
    (-1.0, PHI, 0.0),
    (1.0, PHI, 0.0),
    ...  # 12 vertices, all at distance √(1+φ²) from origin before normalization
)
```

Normalizing to the unit sphere gives 12 points with the property that every vertex-to-vertex
angle is identical (arccos(1/√5)). The adjacency matrix that results is therefore *doubly regular*:
every row has exactly 5 non-zero entries, and those entries are all the same (1/5 if used as a
transition matrix). This has a direct mathematical consequence for area-level propagation: **no
area is more or less connected than any other.** An energy signal starting at any area will spread
to its 5 neighbors in exactly the same way, with no area having an asymmetric advantage from the
geometry. Sigma's `adjacency_symmetric` check (which verifies that A[i][j] == A[j][i] for all
pairs) is meaningful precisely because the underlying icosahedral geometry guarantees this should
hold — it's a runtime assertion of a geometric fact.

The area-level adjacency matrix being symmetric also means the area-level propagation (via
`bridge_weight = 0.22`) is reversible: a signal can flow from A2 to A7 as easily as from A7 to
A2. This is not true for the zone structure *within* an area (center→inner weight 0.25 ≠ the
lack of an inner→center weight in the yaml, which is asymmetric by design) — but at the area-to-
area level, the icosahedral symmetry enforces bidirectional propagation as a structural fact.

---

## Hex degree-6 uniformity → row-stochastic W by construction → conservation by algebra

A regular hex tiling gives every interior cell exactly 6 neighbors at equal distance. This means
every row of the hex-level adjacency-turned-transition-matrix has exactly 6 equal entries summing
to 1 — row-stochastic *by geometric necessity*, not by normalization choice. Why does this matter?

**It makes energy conservation a theorem, not a thing to enforce:**

For any row-stochastic matrix W (`sum_j W[i][j] = 1` for all `i`):

```
sum_j (E·W)[j] = sum_j (sum_i E[i]·W[i][j])
               = sum_i E[i] · (sum_j W[i][j])
               = sum_i E[i] · 1
               = sum(E)
```

Diffusion through a row-stochastic W preserves total energy *algebraically* — no floating point
trick, no correction term, no physics law invoked as a convention. `check_conservation_pre_decay`'s
tolerance of `1e-6` exists only because floating point arithmetic is not exact, not because the
math itself is approximate. The physics of "diffusion does not create energy" is encoded in the
geometry (uniform adjacency → equal row entries → rows sum to 1) and surfaces as a provable algebraic
identity, verified at runtime.

If the hex substrate used a square grid, some cells would have 3 or 4 neighbors (boundary cells)
and others 8 (diagonal-counting interior cells), weights would be unequal across rows, rows would
not naturally sum to 1 without renormalization, and the above proof would not hold without the
normalization step being part of the math. The choice of hexes over squares is not aesthetic — it
is what makes the conservation invariant provable from the grid structure rather than imposed from
outside it.

---

## Pentagon defects — the one place geometry creates a math special case, and how GCS solves it

Euler's formula for closed polyhedral surfaces (`V - E + F = 2`) forces *exactly 12 pentagonal
defects* in any hexagonal tiling of a sphere — cells with 5 neighbors instead of 6. This is not
an approximation; it is a topological theorem independent of how fine the tiling is. For the
72,000-cell hex layer, those 12 pentagon poles coincide with the 12 icosahedron vertices (the same
12 areas) — which is not a coincidence, since the underlying surface is the icosahedral sphere.

A pentagon cell has 5 neighbors where every other cell has 6. Its W row has 5 non-zero entries
summing to 1 (still row-stochastic), but `1/5 ≈ 0.20` per neighbor vs. `1/6 ≈ 0.167` for a
regular hex — each pentagon neighbor receives slightly more energy per step than hex neighbors do.
At the semantic level, this means the 12 "pole" concepts (the ones whose hex anchors land at or
near these topological defects) have slightly enhanced propagation reach per step — not by design,
but as a side effect of the surface geometry.

The GCS variant (`schemas/anchor_map_v1.json`, 72,240 = 72,000 + 240) addresses this by adding
20 extra slots per pentagon pole. The intent is to keep local spacing near-uniform by distributing
the "missing" area around each pentagon across extra cells — reducing the energy-per-neighbor
asymmetry without eliminating the topological defect (which cannot be eliminated). It is a
capacity-engineering patch for a math anomaly that geometry makes unavoidable.

---

## Pre-placement as the pre-computation that gives W semantic meaning

`W` is determined by the hex adjacency graph. The hex adjacency graph's topology is fixed (degree-6
uniform tiling on a sphere). But whether `W[i][j] = 1/6` means "concept X is semantically near
concept Y" depends entirely on where X and Y are anchored in the hex grid.

If concept anchors were assigned arbitrarily (or randomly), the hex adjacency between two cells
would carry no semantic signal: "cell 14,389 is adjacent to cell 14,390" would be a geometric fact
with no meaning attached. Every diffusion step through `W` would distribute energy to geometrically
nearby cells, but "geometrically nearby" would mean nothing.

**Pre-placement (the deliberate assignment of concept→hex anchor coordinates) is therefore the
computation that transforms `W` from a pure topological object into a semantic one.** Two
semantically related concepts placed in adjacent or nearby hexes → their W connectivity carries
semantic relatedness. The design requirement that `corners/hex_substrate.md` states — "each concept
has a primary hex anchor, optionally a small neighborhood footprint, families occupy broad hex
territories, areas occupy macro-regions" — is not a convenience. It is what makes `E·W`
semantically meaningful.

The consequences propagate upward:
- A concept anchor at hex H1 and a semantically related concept at H2 = neighbor of H1 → a single
  `base_step` will spread activation from one to the other.
- A concept anchor at H1 and a *different-family* concept at H3 = 50 hexes away → 8 `T_steps`
  steps at the `λ=0.55` mixing rate will not bridge that gap (see "propagation geometry" below),
  correctly quarantining cross-family activation.
- Family territory occupying contiguous hex regions → the family projection step (aggregating
  hex-cell energies into family energy vectors) sums a geometrically coherent neighborhood, not
  a scattered collection of unrelated cells.

The pre-placement is the semantic contract. The math (W, base_step, T_steps) is only the
operational mechanism that enforces it.

---

## Activation geometry: `reduce_288_to_5` uses geometry as the compression key

`core/math/core_math.py` contains `reduce_288_to_5(family_vector)`, which maps a 288-dimensional
family activation vector down to 5 dimensions (the core math's working `n=5` space). The bucket
size is `288 // 5 ≈ 57.6 → 57–58` families per bucket, L1-normalized. The number 288 is not
arbitrary: it is `12 areas × 24 families/area` — the geometry's own index space.

This has a precise consequence: the 288-dim family vector's coordinate system IS the area/family
hierarchy. Bucket `i = [i×288//5, (i+1)×288//5)` corresponds to a contiguous slice of that
hierarchy, not a random subset. When `reduce_288_to_5` sums absolute values across a bucket, it is
summing activation energy across a contiguous block of the area/family geometry — a macro-region
aggregation, using the same spatial contiguity principle the hex layer relies on. The 5-dim `(S, L)`
vector that enters `fusion` is therefore a geometry-aware compression, not a dimension-reduction
technique with no geometric interpretation.

---

## Propagation geometry: T_steps, λ, and decay calibrated against graph mixing rate

Three constants govern how far a signal spreads in `base_step`: `T_steps = 8`, `lambda = 0.55`,
`decay = 0.04`. Each has a geometric interpretation on the hex graph.

**T_steps = 8** sets the diffusion radius. On a degree-6 uniform hex graph, a single `base_step`
spreads activation to the 6 immediate neighbors of each active cell. After 8 steps, activation
(however attenuated) has reached cells up to 8 hex-radii from the origin concept's anchor. On a
72,000-cell sphere, 8 hex-radii is a localized spread — roughly 8² × π × 6 / 2 ≈ 600 cells
within reach (a rough estimate on a flat hex; on a sphere the mixing is slightly different). This
is deliberate: it means a single concept activation does not flood the entire sphere in 8 steps,
which would make `P_disp` (dispersion penalty) trivially high for any strong activation.

**lambda = 0.55** sets the propagation fraction per step. At each step, 55% of each cell's energy
flows along the adjacency edges (split among 6 neighbors, so each neighbor receives ≈ 9.2% of the
origin cell's energy per step) and 45% stays put. This asymmetry in favor of movement (>0.5)
means the system is actively diffusing, not just weakly leaking — it will spread signals to
semantically adjacent concepts across 8 steps with meaningful amplitude. A λ below 0.5 would
create a system where most energy stays at the origin across T_steps, making multi-hop semantic
spreading ineffective.

**decay = 0.04 per step** introduces exponential attenuation: after 8 steps, energy has been
multiplied by `(1 − 0.04)^8 ≈ 0.72` from decay alone. Combined with the 1/6-per-neighbor
splitting at each hop, a signal at 8 hex-radii distance arrives substantially attenuated. This is
not a bug — it is what makes distance meaningful. If decay were 0, an 8-step walk from hex H to a
hex H' 8 radii away would carry the same signal as a 1-step walk to an adjacent hex — distance
would be meaningless in propagation terms. At decay=0.04, the system encodes a geometric decay
curve that makes "nearby" semantically different from "far away" even after the T_steps traversal.

The combination `T_steps × decay = 8 × 0.04 = 0.32` total decay mass is not arbitrary — it
positions the propagation "horizon" where signals become too faint to usefully activate distant
families, while still allowing genuine semantic spreading within a local neighborhood.

---

## Zone costs as a potential landscape; bridge_weight as a cross-area barrier

`propagation_weights.yaml` defines:

```
zone_weights:
  center_to_inner:   0.25
  inner_to_middle:   0.18
  middle_to_inner:   0.18
  middle_to_outer:   0.12
  outer_to_middle:   0.12

bridge_weight: 0.22
```

These numbers encode a potential landscape in the geometric sense: a descending sequence of flow
rates from the semantic core of an area outward. Activation energy flows most readily from a
family's center outward to its inner ring (weight 0.25), less readily to the middle ring (0.18),
and still less readily to the outer ring (0.12). This is a monotonically decreasing gradient — the
spatial potential well has its lowest "resistance" at the center, matching the semantic assumption
that center-zone families are the most activated, highest-coherence families in any area.

`bridge_weight = 0.22` is the cross-area propagation rate. Notably, it falls **between** the
center→inner rate (0.25) and inner↔middle rate (0.18) — meaning crossing an area boundary costs
roughly the same as moving from the inner ring to the middle ring within a single area. This is
a deliberate calibration: area boundaries are semantic barriers, but they are not absolute walls.
A strong enough activation in one area will spill into its 5 icosahedral neighbors at a rate
comparable to spreading within the area itself, just at the inner→middle step cost rather than
the center→inner step cost.

The implication for the physics: area-level propagation is not "cheap" (bridge_weight < center→inner)
but it is not prohibitive either (bridge_weight > middle→outer). The calibration targets a system
where same-area spreading dominates but cross-area spreading is reachable for strong signals —
which matches the intended semantic model where semantically related concepts within the same area
activate together readily, while concepts across areas co-activate only under discourse pressure.

---

## Closed sphere → no boundary corrections needed anywhere in the math

A flat grid — even a large one — has cells with fewer than 6 neighbors at its edges and corners.
Those cells would have `W` rows that do not sum to 1 under naive uniform weighting, requiring
boundary corrections (either zero-padding, reflection, or weight-renormalization at the boundary).
Each of those corrections would be a special case in the math: "if this cell is a boundary cell,
use a different formula."

The icosahedral sphere eliminates this class of special case entirely. A sphere is a closed
2-manifold — it has no boundary by definition. Every hex cell on the sphere surface has the same
6 hex neighbors (except the 12 pentagon poles, handled separately by the GCS variant). There are
no edge cells, no corner cells, no cells with fewer neighbors needing special treatment. The `W`
matrix has the same row structure everywhere, the conservation proof above holds everywhere, and
every propagation formula (`base_step`, `shadow_step`, `check_conservation_pre_decay`) applies
identically to every cell. The propagation code in `sphere/propagation/` never needs a
`if cell.is_boundary: ...` branch, because the geometry guarantees there is no such cell.

This is also why `corners/topology_geometry.md`'s description of the geometry as "looped" is
accurate at the math level: traversal that continues along the sphere surface will cycle back
through the same cells without ever needing to stop, reflect, or be special-cased — not because
an explicit loop was coded, but because the manifold has no edge to stop at.

---

## Shannon entropy dispersion: the sphere sets the normalization ceiling

`P_disp` (§10 of the Core Math Contract) is `k_disp · H_norm`, where
`H_norm = H / ln(M)` — the Shannon entropy of the energy distribution normalized by the maximum
possible entropy for `M` active sides. `ln(M)` is the maximum entropy, achieved when energy is
uniformly distributed over all `M` sides.

The geometry determines what "fully dispersed" means. On a 12-area sphere, a state where all 12
areas have equal activation has `H = ln(12)` — the geometric ceiling. `H_norm = 1.0` corresponds
to "activation evenly spread across every area in the sphere." `H_norm = 0.0` corresponds to "all
activation concentrated in one area." The penalization of high `H_norm` (via `k_disp = 0.25`)
is therefore penalizing *geometric* dispersion — the spreading of activation so far across the
sphere's area structure that no meaningful signal concentration remains. The geometry (12 areas,
icosahedral) sets the reference frame for what "concentrated" vs. "dispersed" means in
information-theoretic terms. Without a defined geometric structure, `H_norm` would have no
normalization denominator with semantic meaning.

---

## What this coupling means for future changes

Every constant in the pipeline that looks like a free parameter is actually constrained by the
geometry to a range of valid values:

- `T_steps` cannot be made arbitrarily large without the sphere's mixing time (the number of steps
  for a signal to reach every area from any starting point on a degree-5 area graph) becoming
  relevant — at large T_steps, the system would approach a stationary distribution regardless
  of the initial activation, losing spatial specificity.
- `lambda` cannot be pushed to 1.0 (full transition) without abandoning the self-retention term
  that makes the lazy chain well-behaved; it cannot approach 0 without losing propagation
  effectiveness on a graph that relies on diffusion for semantic spreading.
- `bridge_weight` cannot exceed `center_to_inner` (0.25) without making cross-area spreading
  cheaper than intra-area spreading, inverting the intended semantic hierarchy.
- The 288 compression key only works if the geometry's index space (12 × 24 = 288) remains
  stable. Changing the number of areas or families changes the natural compression buckets.

In this sense the geometry is not just the math's input — it is the math's constraint envelope.
The parameter values that exist in `configs/` are tuned within this envelope; they cannot be
freely tuned outside it without also changing the underlying topology.

---

## Relationship to neighboring corners

- `corners/core_math_contract.md` — supplies the exact formulas and constants this corner reasons
  about geometrically. Read together.
- `corners/topology_geometry.md` — describes the icosahedral structure whose mathematical
  properties this corner traces through to W and conservation.
- `corners/hex_substrate.md` — describes the hex grid whose uniform-adjacency property is the
  geometric foundation of the row-stochastic argument above.
- `corners/propagation_dynamics.md` — describes the production propagation layer; this corner
  explains why the math it invokes can make the claims it does (conservation, determinism,
  uniform treatment of all cells).
- `parameter_synergies.md` §2 (bridge_weight/λ synergy) — treats these as empirically calibrated
  companions; this corner explains the geometric constraint space they must stay within.

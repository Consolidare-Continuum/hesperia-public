# Corner: Topology / Geometry — Icosahedral Area Sphere and Family Zones

**Location:** `sphere/topology/` (embedding.py, embedding_alignment.py, area_structure.py,
family_structure.py, family_embedding.py, activation_propagation.py, export.py),
`specs/canon/area_geometry.yaml`, `specs/canon/family_geometry.yaml`,
`specs/canon/family_embedding_tfp.yaml`, `runtime/services/family_graph.py` (uncommitted, v0.7.0).

**Born:** geometry decision recorded at `7722d013 docs: 10+2 topology decision — 10 operational, 2
reserved service areas` (v0.4.1 era); embedding/alignment code matured through v0.5.x.

## Why this is a distinct concern

Twelve areas need a *relation structure* to each other, not just twelve independent labels —
otherwise "area A2 is activated" carries no information about whether A7 (a structurally adjacent
area) co-activating is expected or anomalous. `area_geometry.yaml` states the choice directly:
"Adjacency = geometric icosahedron (aligned to unit-sphere embedding). Degree 5, 30 edges." An
icosahedron is the natural choice because it is a regular polyhedron — 12 vertices, each with
exactly 5 equidistant neighbors — so every area has the *same* relational structure to its
neighbors, with no asymmetry baked in by accident of layout. This is graph theory doing real work:
a regular graph (constant vertex degree) is what guarantees adjacency-based reasoning (Sigma's
`adjacency_symmetric` invariant, propagation's bridge weights) behaves uniformly across all 12
areas instead of needing per-area special cases.

Family geometry (`family_geometry.yaml`, `family_embedding_tfp.yaml`) operates one level down: 24
families per area are arranged into zones — center, inner_ring, middle_ring, outer_ring — with
explicit zone-to-zone step costs (`specs/canon/propagation_weights.yaml`'s `zone_weights`). This is
a distinct concern from area adjacency because family relations within an area are not naturally a
regular graph — some families are conceptually "central" and more frequently co-activated, some
peripheral — so a zone model, not a second icosahedron, is the appropriate structure.

## What would break without it

Without a principled adjacency structure, Gamma's `area_sequence_values_in_0_11` check would be
checkable as a range constraint but carry no relational meaning — propagation between areas
(`sphere/propagation/`) would have nothing principled to propagate *along*. `propagation_weights.yaml`'s
`bridge_weight: 0.22` is specifically the cost of crossing *between* areas, as distinct from moving
between zones *within* one area — a distinction that only exists because area-level and
family-level geometries are modeled separately with their own cost structures.

`embedding_alignment.py`'s job — aligning the abstract 12-area adjacency graph to a concrete 3D
icosahedral coordinate embedding via deterministic graph isomorphism — exists because Sigma's
`adjacency_matrix_12x12` and `adjacency_symmetric` checks need *a* canonical embedding to validate
against; without alignment, two equally valid relabelings of the same icosahedron could produce
different (and incompatibly "symmetric") adjacency matrices.

## Why 12 specifically — and why this number is forced, not chosen

`sphere/topology/embedding.py` doesn't just assert 12 areas; it constructs them as the actual
vertices of a regular icosahedron, using the golden ratio `φ = (1+√5)/2` in the standard
construction (`ICOSAHEDRON_VERTICES_RAW`). This matters because it means 12 is not a round-number
design choice the way some other constants in this system are (see `corners/hex_substrate.md`'s
"forced vs. engineered" distinction) — it is a **mathematical consequence**. A regular icosahedron
is one of exactly five Platonic solids, and it is the one whose vertex count (12) gives the
*densest regular* (constant-degree-5) point arrangement on a sphere achievable by a Platonic
construction. Choosing any other vertex count for a "every area relates to every neighbor
identically" structure would mean abandoning either regularity (some areas get more neighbors than
others) or the Platonic construction (losing the closed-form, parameter-free coordinate derivation
`embedding.py` relies on). 12 is therefore the smallest, most natural number satisfying "every area
has the same relationship to its neighbors" on a sphere — not picked for narrative or capacity
reasons the way the hex layer's 250-per-family is.

## Why a closed (looped) sphere, not a bounded flat grid

A flat grid — even a large one — has edge cells and corner cells with fewer neighbors than interior
cells, which is exactly the asymmetry `corners/hex_substrate.md` already flags as the reason square
grids are avoided at the hex level. The icosahedral sphere solves this at the *area* level by
construction: a sphere is a closed 2-manifold with no boundary, so there is no "edge area" with
fewer neighbors than the rest — every one of the 12 areas has exactly degree 5, with no special
case. This is also what makes the geometry "loop": a path that keeps moving area-to-area never hits
a boundary and has to stop or reflect, it simply continues around the closed surface. Practically,
this means propagation and traversal logic (`corners/propagation_dynamics.md`) never needs
boundary-condition special-casing — the same diffusion rule that applies to any interior area
applies to literally every area, because on a closed sphere there is no other kind.

## Relationship to geometry_math_coupling

`corners/geometry_math_coupling.md` is a dedicated cross-cutting document that traces exactly how
the icosahedral degree-5 uniformity documented here propagates through to the W matrix, energy
conservation, Shannon entropy normalization, and zone/bridge cost calibration. This file documents
*what* the geometry is; that file documents *how it constrains the math*.

## How it relates to neighbors

This corner supplies the `area_sphere` distance layer the metric registry formalizes (see
`corners/metric_registry.md`): `docs/specs/24_SPEC §4.1` names `sphere/topology/embedding.py`
directly as the implementation of ordinary spherical geodesic distance,
`geodesic_distance(p_i, p_j, radius=R) = R·arccos(clamp(dot,−1,1))` — the standard metric on the
2-sphere S² embedded in ℝ³. The uncommitted `runtime/services/family_graph.py` builds a
shortest-path cost function directly on top of `family_embedding.py`'s zone keys and bridge
weights — i.e., the v0.7.0 metric wave is a thin service layer over geometry that has existed since
v0.4/v0.5, not a new geometric model. Hex substrate dynamics (`corners/hex_substrate.md`) propagate
*within* this area/family geometry, using its bridge and zone weights as the calibrated cost of
movement.

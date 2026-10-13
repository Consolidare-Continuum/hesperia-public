# Corner: Hex Substrate (`core/hexmap/`, `hesperia/engine/hex_dynamics.py`, `hex_topology_authority.py`, `hex_family_bridge.py`, `pch_builder.py`, the 72k/72,240-cell layer)

## Why this corner exists at all

Families and areas are coarse, hand-specified categories — they have to be,
because someone has to be able to read and govern them. But coarse categories
cannot represent two things Hesperia needs: (1) that two concepts in the same
family are not semantically identical, and (2) that meaning can move — a
discourse can drift from one semantic neighborhood to another over time. A
hierarchy of fixed bins can count co-occurrence but cannot represent
*trajectory*, *concentration*, or *locality* without an intermediate
substrate with its own geometry. That is what the hex layer is for: it is not
decoration on top of the family/area hierarchy, it is the only layer in the
system with enough resolution to support smoothing and motion at all.

## What would break without it

Without an intermediate substrate, concept evidence would have to jump
directly from resolved concept IDs to family/area counts. That shortcut is
exactly the failure mode the founding theory memo warns against by name:
"text → family guess" instead of "text → concept → hex → family → area."
Two concrete failures follow from skipping the hex layer:

- **No denoising.** Free/clinical speech is sparse and messy; a single
  ambiguous span can flip which family looks "activated" if there is no
  mechanism to spread a weak, local signal across nearby semantic territory
  before it gets counted. The hex layer's adjacency gives every cell uniform
  neighbor distance, which is what makes diffusion-style smoothing
  well-defined in the first place (this is the same reason hex grids — not
  square grids, which have unequal edge- and corner-neighbor distances — are
  the standard choice for spatial smoothing systems, e.g. Uber's H3).
- **No trajectory.** Without a geometric substrate, "movement" between
  concepts has no defined distance, so concepts like concentration, dispersion,
  drift, and basin-stabilization (used by `core/hexmap/dynamics.py` and the
  dynamism stack) are not expressible at all — there's nothing to compute a
  gradient over.

## Why 72,000 cells specifically (and why 72,240 in the GCS variant)

The cell count is not "big number nice" (explicitly disclaimed in the design
memo). It is sized to give each of the 288 families (12 areas × 24 families)
enough room — roughly 250 cells per family — for sub-concepts, stylistic
variants, intensity variations, and near-but-not-identical meanings to live
near each other without collapsing into one family bin. The geodesic variant
(`schemas/anchor_map_v1.json`: 72,240 = 72,000 semantic hexes + 240 extra
slots distributed to maintain even spacing at the 12 pentagon poles of an
icosahedral sphere) exists because once the hex layer is also asked to carry
*spatial* meaning (the GCS / geodesic closed sphere — see
`corners/topology_geometry.md`), a pure hexagonal tiling cannot close evenly over
a sphere; the 12 unavoidable pentagon defects of any hex-on-sphere tiling have
to be given slightly more room (`extra_hex_per_pentagon_pole: 20`) to keep
local spacing close to uniform. This is a known, structural property of
hexagonal sphere tilings, not a Hesperia-specific quirk — it is the same
constraint geodesic dome and H3-style spherical indexing schemes have to
solve.

## Forced geometry vs. engineered capacity — an honest distinction

Not every number in this structure has the same kind of justification, and conflating them would
overclaim. **12 areas is geometrically forced**: it is the vertex count of a regular icosahedron,
the unique Platonic construction giving every area the same constant-degree-5 relationship to its
neighbors (`corners/topology_geometry.md`). **24 families per area and 250 hexes per family are
not geometrically forced — they are capacity-engineering choices.** The earlier `20_GEOMETRY`
formalization derives them from a content-authoring budget, not a geometric necessity: each hex
side carries one statement of 3–5 sentences, and `24 × 250 = 6,000` hexes-worth of sides per area
was sized to land on round, human-reasoned sentence-capacity figures (108,000–180,000 sentences per
area; 1.296M–2.16M sentences across the whole sphere) — a deliberate authoring-capacity target, not
a number derived from any adjacency or packing constraint the way 12 is. This is worth keeping
straight: if someone later asks "why not 200 hexes per family instead of 250," the honest answer is
"it changes a capacity budget," not "it would break the geometry" — unlike 12, which cannot change
without abandoning the icosahedral construction entirely.

## Why concept→hex placement must be deliberate, not random

If concept-to-hex anchors were assigned arbitrarily, hex adjacency would carry
no semantic information, and every benefit claimed for the layer (locality,
smoothing, trajectory) would be vacuous — "neighboring" would mean nothing.
The design requirement (each concept has a primary hex anchor, optionally a
small neighborhood footprint, families occupy broad hex territories, areas
occupy macro-regions) is what keeps the hierarchy and the substrate in
agreement: a family boundary in hex-space has to coincide with the same
family boundary used everywhere else in the system (Sigma's `family_counts`
length-288 check, the propagation engine's family projection, etc.), or the
two representations of "family" silently diverge and nothing downstream can
tell which one is authoritative.

## Relationship to geometry_math_coupling

`corners/geometry_math_coupling.md` traces how hex degree-6 uniform adjacency documented here
makes the W matrix row-stochastic by geometric construction (not by normalization convention),
why that makes energy conservation a provable algebraic identity rather than an imposed rule, and
how the pentagon-defect W-row asymmetry at the 12 poles is the one place where geometry creates
a math special case that the GCS +20-slot patch exists to minimize. This file documents *what* the
hex substrate is; that file documents *how its geometry constrains and enables the math*.

## Relationship to neighboring corners

- Receives resolved concept IDs from `corners/lexicon_resolver.md` — never
  raw tokens. This is the explicit rule the theory memo states as the single
  most important constraint on the whole architecture ("do not allow raw
  wording to activate families directly").
- Feeds `sphere/propagation/` (diffusion, multi-step diffusion, family
  projection) and `sphere/dynamism/` (curvature, jump rate, trajectory) — the
  hex layer is the geometry those modules compute *over*.
- Is distinct from, but coordinate-aligned with, the area-level geometry in
  `corners/topology_geometry.md` (the icosahedral 12-area sphere). The hex layer
  is the fine-grained terrain; the area sphere is the coarse map. Both have to
  agree on adjacency or the metric registry (`HesperiaMetric`, `metric_layer`
  enum) cannot make distance claims that are simultaneously true at both
  scales.

# Hesperia — Metric and Distance

**Document ID:** `24_SPEC__Hesperia_Metric_and_Distance_v0_1`  
**Version:** `0.1.0`  
**Status:** FORMALIZATION (brain + Ethan ratification — promote to `igareosh/hesperia/docs/specs/`)  
**Authority:** Ethan — [SPEC-ETHAN-HESPERIA-METRIC-AND-DISTANCE.md](../../governance/SPEC-ETHAN-HESPERIA-METRIC-AND-DISTANCE.md)  
**Plane:** Geometry registry + distance semantics across Hesperia scales  
**Depends on:** `22_SPEC__Geodesic_Sphere_and_Interior_Point_of_World_View_v0_1`, `23_SPEC__General_Thought_Propagation_and_Hex_Orientation_v0_1`, `20_GEOMETRY__formalized_structure`, `40_POLICY__Loopability_and_traversal`  
**Research trace:** [METRIC_research_GAPS-AND-REMEDIATION-v01.md](../../colombo_research/hesperia/METRIC_research/METRIC_research_GAPS-AND-REMEDIATION-v01.md)

**Added:** 2026-06-22. **No implementation** in this revision unless env flags in §10.

---

## 0. Document control

| Field | Value |
|-------|--------|
| **Replaces** | Ad-hoc “distance” usage across engine, papers, KME-KSI-score / KSI-Inspector |
| **Companion pedagogy** | [METRIC-TENSOR-WHAT-IT-IS.txt](../../colombo_research/physics_cosmology/METRIC-TENSOR-WHAT-IT-IS.txt) (physics — not product) |
| **Academia** | [HESPERIA-METRIC-ACADEMIA-NARRATION-v0_1.md](HESPERIA-METRIC-ACADEMIA-NARRATION-v0_1.md) |
| **Entities** | `HesperiaMetric`, `HexSphere`, `GeodesicClosedSphere`, `InteriorPointOfWorldView`, traversal engines |

---

## 1. Scope

This specification **unifies distance semantics** in Hesperia:

1. **`HesperiaMetric`** — layered registry; each layer has its own distance law.  
2. **`metric_layer` enum** — mandatory qualifier on APIs and papers.  
3. **Path action `S_path`** — discrete cumulative cost along sealed traversals.  
4. **Glossary** — disambiguate KME-KSI-score, KSI-Inspector, KME, Gram G_hex, pipeline_metrics, spatial g_ij.  
5. **Bindings** — normative links to implemented `embedding.py` and draft 22_SPEC GCS/IPoW.

**Out of scope v0.1:** Einstein field equations; clinical interpretation of IPoW; DB migration to 251 semantic hex rows; Poisson solver.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **HesperiaMetric** | Registry object listing active distance layers and their parameters for a run |
| **metric_layer** | One of: `area_sphere`, `family_graph`, `hex_graph`, `gcs_surface`, `ipow_volume`, `concept_graph`, `state_gram` |
| **Chart coordinates** | Product IDs: `area_id`, `global_id`, `hex_index`, `side_id`, `road_coordinates[]` |
| **SemanticPlane** | Content authority — 72,000 hex, 432,000 truth units (22_SPEC) |
| **GeodesicPlane (GCS)** | Spherical spacing authority — 72,240 hex + 12 pent poles (22_SPEC) |
| **path_action S_path** | Σ_e w(e)·ℓ(e) over edges in a sealed path |
| **G_hex_ij** | `A_hex[i,:]·A_hex[j,:]` — Gram row inner product on hex activation field |
| **spatial_metric_g_ij** | Riemannian tensor in physics pedagogy — **not** a Hesperia runtime object |
| **coordinate_fingerprint** | SHA256 of aligned 12-area sphere coordinates (`embedding.coordinate_fingerprint`) |
| **anchor_map_v1** | Frozen semantic↔GCS slot assignment per 22_SPEC §6.2 |

---

## 3. Normative rule — no bare “distance”

Implementations and documents **SHALL** use the form:

```text
distance(metric_layer=<layer>, from=<id>, to=<id>, value=<float>, units=<string>)
```

Papers **SHALL** name the layer in the same sentence as any distance claim.

**Example (correct):** “Area geodesic distance (`metric_layer=area_sphere`) between A3 and A7 is 1.24 rad on the unit sphere.”

**Example (forbidden):** “The concepts are distance 0.3 apart.”

---

## 4. Layer registry (normative)

### 4.1 `area_sphere` — **IMPLEMENTED**

| Field | Value |
|-------|--------|
| **Manifold** | Unit sphere S² embedded in ℝ³ |
| **Chart** | `area_id` 0..11 → aligned icosahedral vertex |
| **Distance law** | `geodesic_distance(p_i, p_j, radius=R)` = R · arccos(clamp(dot,−1,1)) |
| **Code** | `sphere/topology/embedding.py` |
| **Tests** | `tests/topology/test_embedding.py::test_geodesic_distance` |
| **Default R** | `1.0` |
| **Fingerprint** | `coordinate_fingerprint(get_area_coordinates())` |

**Invariant:** Graph edges of icosahedral adjacency **SHALL** have nearly equal angular length (validation in `validate_embedding_matches_topology`).

### 4.2 `family_graph` — **PARTIAL**

| Field | Value |
|-------|--------|
| **Chart** | `global_id`, zone keys in `family_embedding_tfp.yaml` |
| **Distance law** | Shortest path on zone lattice + bridge edges with YAML weights |
| **Code** | `sphere/topology/family_embedding.py` |
| **Gap** | No single exported `family_geodesic()` API — graph cost only |

### 4.3 `hex_graph` — **IMPLEMENTED (discrete)**

| Field | Value |
|-------|--------|
| **Chart** | Flattened hex index per family row; periodic ring L_H |
| **Distance law** | Hop count on adjacency; corridor `gradient` as local cost |
| **Code** | `propagation_corridors.py`, `activation_propagation.py` |
| **Note** | Not a smooth ds²; discrete graph metric |

### 4.4 `gcs_surface` — **SPECIFIED (22_SPEC); emit gated**

| Field | Value |
|-------|--------|
| **Chart** | GCS hex slot 0..72239 + 12 `PentagonPole` |
| **Distance law** | `spacing_factor(family) ×` great-circle or chord distance between surface anchors |
| **Requires** | `anchor_map_v1` **FROZEN** |
| **Registry JSON** | 22_SPEC §9.1 `geodesic_sphere` block |
| **Emit** | `HESPERIA_GCS_EMIT=1` (future) |

**Local conformal factor:**

```text
spacing_factor = 250 / gcs_mean_hex_per_family   if gcs_hex_slot_count == 250
spacing_factor = 251 / gcs_mean_hex_per_family   if gcs_hex_slot_count == 251
```

### 4.5 `ipow_volume` — **SPECIFIED (22_SPEC); not in analyze**

| Field | Value |
|-------|--------|
| **Chart** | `powv_position` ∈ unit ball Ω ⊂ ℝ³ |
| **Distance law** | Chord: `‖powv_position − s_a‖` to anchor direction s_a on ∂Ω |
| **Default** | PointZero (0,0,0); symmetric tier-1 distances |
| **Coupling** | 23_SPEC GTP: Π projection Ω → ∂Ω |

### 4.6 `concept_graph` — **INSPECTION**

| Field | Value |
|-------|--------|
| **Chart** | `concept_id`, Floor-2 edges |
| **Distance law** | Edge weight W_e, resistance R_e; BELL `path_mass` on corridor bundles |
| **Code paths** | KSI-Inspector, BELL_research SPEC |
| **Bounded** | `H_max`, `mediator_max` — not infinite graph geodesic |

### 4.7 `state_gram` — **IMPLEMENTED**

| Field | Value |
|-------|--------|
| **Object** | Activation field `A_hex` (families × hexes) |
| **Coupling** | `G_hex_ij = A_hex[i,:]·A_hex[j,:]` |
| **Use** | Contradiction pressure, tension via `C_F` lift |
| **Code** | `hesperia/engine/product_signals.py` |

**Not** the same as spatial metric — **metric on activation state space**.

---

## 5. Path action S_path (normative)

For a sealed traversal path P = (e₁,…,e_k):

```text
S_path(P) = Σ_{e in P} w_layer(e) · ℓ_layer(e)
```

| Edge type e | layer | ℓ(e) | w(e) default |
|-------------|-------|------|----------------|
| Area border crossing | area_sphere | geodesic_distance(A_i, A_j) | 1.0 |
| Family bridge | family_graph | zone_path_cost | bridge_weight |
| Hex adjacency step | hex_graph | 1 hop or \|ΔA\| | α (corridor) |
| Concept relation | concept_graph | −log(max(W_e, ε)) or R_e | 1.0 |

**Optional export fields:**

```json
{
  "path_metric_cost": 12.34,
  "path_metric_layers": ["area_sphere", "hex_graph"],
  "path_action_version": "0.1"
}
```

**Sources:** `road_coordinates` (matrix_run), `propagation_trace`, `SurfaceEventBatch`.

---

## 6. Semantic ↔ geodesic map J_sem→gcs

Sparse assignment **J** with shape conceptually (72240 + 12) × 72000:

- Each semantic hex maps to one GCS slot or `geodesic_extra_index = 250` in 251-slot families.  
- Twelve PentagonPole rows absorb +240 hex budget (22_SPEC §5.3).  
- **SHALL NOT** compute until `anchor_map_v1` frozen.

Candidate: `colombo_research/hesperia/METRIC_research/schemas/anchor_map_v1.candidate.json`.

---

## 7. Glossary (normative — duplicate Ethan §7)

| Bare symbol | Use instead |
|-------------|-------------|
| KSI | **KSI-Inspector** |
| KSI (KME) | **KME-KSI-score** |
| G_ij | **G_hex_ij** in hex context |
| g_ij | **spatial_metric_g_ij** (academia only) |
| metrics (ctx) | **pipeline_metrics** |
| distance | **qualified with metric_layer** |

---

## 8. Relationship to 22_SPEC and 23_SPEC

```text
24_SPEC (this)     = naming + registry + path action
22_SPEC            = GCS counts, IPoW, dual plane invariants
23_SPEC            = GTP: IPoW → surface via Π, Ψ coherence
```

**No duplicate invariants:** 12×24×250 semantic counts remain defined only in 22_SPEC / MASTER_SPEC.

---

## 9. Discrete Laplacian cross-reference (informative)

**Δ_hex** on periodic ring L_H:

```text
(Δ_hex A)_k = A_{k-1} + A_{k+1} − 2A_k
```

Corridor update `A' = A + α L A − β R` is **diffusion**, not Poisson equation, unless steady-state source balance is defined. See physics Poisson note for pedagogy only.

---

## 10. Runtime registry (proposed JSON)

### 10.1 `meta.hesperia_metric` (when `HESPERIA_METRIC_EMIT=1`)

```json
{
  "hesperia_metric_version": "0.1.0",
  "layers_active": ["area_sphere", "hex_graph", "state_gram"],
  "area_sphere": {
    "radius": 1.0,
    "coordinate_fingerprint": "<sha256>"
  },
  "gcs_surface": null,
  "ipow_volume": null,
  "anchor_map_id": null
}
```

### 10.2 `geodesic_sphere` (when `HESPERIA_GCS_EMIT=1`)

Copy 22_SPEC §9.1 verbatim; add `"anchor_map_id": "anchor_map_v1"` when frozen.

---

## 11. ADR gates

| Change | Requires |
|--------|----------|
| Default sphere radius R ≠ 1 | Operator ADR |
| anchor_map rule change | Operator ADR + `gcs_id` bump |
| Merge semantic and GCS cell counts in DB | Operator ADR + migration |
| Clinical claims on IPoW distance | Sophia review + non-claim policy |
| Rename metric_layer enum values | 24_SPEC version bump |

---

## 12. Promotion checklist (dev repo)

1. Copy this file → `igareosh/hesperia/docs/specs/24_SPEC__Hesperia_Metric_and_Distance_v0_1.md`.  
2. `docs/DOC_INDEX.md` entry under Geometry.  
3. Cross-link `20_GEOMETRY`, `22_SPEC`, `23_SPEC`.  
4. Add `HESPERIA_METRIC_EMIT` / `HESPERIA_GCS_EMIT` to env docs.  
5. pytest: ensure `test_geodesic_distance` in CI geometry suite.

---

## 13. Traceability

| Source | Section |
|--------|---------|
| METRIC_research GAPS | §4–6, §9 |
| embedding.py | §4.1 |
| product_signals.py | §4.7 |
| 22_SPEC | §4.4–4.5, §6, §10.2 |
| 23_SPEC | §4.5, §8 |
| BELL_research | §4.6, §5 |
| Ethan SPEC | Authority + glossary |
| Ethan Minkowski–IPoW SPEC | §14 iteration geometry |

---

## 14. Iteration geometry and IPoW (Ethan ratification 2026-06-22)

**Authority:** [governance/SPEC-ETHAN-HESPERIA-MINKOWSKI-IPOW-ITERATIONS.md](../../governance/SPEC-ETHAN-HESPERIA-MINKOWSKI-IPOW-ITERATIONS.md)  
**Colombo source:** [METRIC_research_MINKOWSKI-IPOW-ITERATIONS-v01.md](../../colombo_research/hesperia/METRIC_research/METRIC_research_MINKOWSKI-IPOW-ITERATIONS-v01.md)

### 14.1 Non-claim

Hesperia **does not** implement Minkowski η_μν or special relativity. §14 defines **software iteration geometry** only.

### 14.2 State and world line

```text
X_n = (τ_n, x_n),   τ_n = powv_step,   x_n = powv_position ∈ Ω,   ‖x_n‖ ≤ 1
W = { (τ_n, x_n) }_n≥0
```

### 14.3 Iteration interval (normative default)

Product metric on **ℕ × Ω** (Riemannian, all positive):

```text
I²( n → n+1 ) = w_τ (Δτ)² + ‖x_{n+1} − x_n‖²
```

**Defaults:** `w_τ = 1`, `Δτ = 1` per sealed `SurfaceEventBatch` → `I²_n = 1 + ‖δ_powv‖²` with `δ_powv = x_{n+1} − x_n`.

```text
‖δ_powv‖_Ω = √(δ_powv · δ_powv)     (Euclidean on Ω)
```

**metric_layer:** iteration bookkeeping uses **`powv_step`** and **`I²_n`** — not bare “time” or “distance”.

### 14.4 PointZero metric (tightened)

At PointZero: `x = 0`; tier-1 `d_IPoW(a) = ‖0 − s_a‖ = 1` (unit-sphere chord); `powv_barycentric_areas[i] = 1/12`. Symmetry is **O(3)** about origin, not semantic hex permutation.

### 14.5 GTP

GTPA selects next legal hex via template **P** and **Ψ(δ_powv)** — **bias functional**, not geodesic on ∂Ω. See 23_SPEC.

### 14.6 Emit (future)

`meta.interior_point_of_world_view` **SHOULD** include at minimum: `powv_step`, `powv_point_zero`, tier-1 `powv_distances`, optional `iteration_interval_I2`, `delta_powv_norm` when IPoW active (METRIC-23).

---

**SIGNED: Chief Architect (Ethan) | 24_SPEC metric and distance v0.1 + §14 | 2026-06-22 | Hesperia product formalization**

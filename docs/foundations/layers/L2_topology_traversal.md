# Layer 2 — Topology Traversal (`core/layers/layer_2.py`, 35_SPEC)

**Position in pipeline:** Second executable layer. Receives L1's dominant family as a seed
and performs a Breadth-First Search (BFS) outward through the family adjacency graph up to
`MAX_ALLOWED_DEPTH = 8` hops. From that traversal it computes 25 variables characterizing
the topology, mass distribution, geometry, and structural quality of the neighborhood
around the text's dominant semantic concept. No LLM, no semantics, no shadow — pure graph
traversal over attribution-derived topology.

**Spec origin:** `35_SPEC`. Module docstring: *"25 variables, deterministic, topology-bound.
No semantics, no books, no shadow."*

---

## What L2 receives and why it starts at the dominant family

L2's entry point:
- `l1_output["DOMINANT_FAMILY_ID"]` — the BFS root: the single family index (0–287) that
  received the most attributed tokens in L1
- `l1_output["DOMINANT_AREA_ID"]` — for cross-area accounting
- `hits[f]` — the 288-dim raw attribution count vector from pre-L1
- `adjacency` — the family graph: `adj[f]` = set of neighboring family indices
- `F=288`, `A=12`, `MAX_ALLOWED_DEPTH=8`, `ε=1e-9`

**Why start at the dominant family, not the centroid of the attribution.** Starting at the
argmax of `hits` is the simplest, most information-dense choice: the dominant family is the
place where the text has stated its strongest semantic mass. A centroid-of-mass starting point
would depend on how distances between families are defined, requiring a metric that doesn't
exist at L2 time. The argmax is well-defined, reproducible, and directly traceable back to the
attribution step — there is no ambiguity about which node the traversal begins at.

**The family adjacency graph.** L2 takes whatever adjacency it is passed. The production
pipeline passes the real icosahedral-derived family topology (from
`sphere/topology/topology_loader.py`). The layer itself also defines a canonical stub for
testing: `build_canonical_stub_adjacency(F, A)` — a ring graph (cycle C₂₈₈) where each
family `f` is connected to `(f-1)%F` and `(f+1)%F`. The ring is a structurally minimal
connected graph that exercises all traversal metrics without requiring the full topology.
Production runs use the real topology; the stub exists so L2 can be tested deterministically
with a known graph structure.

---

## The BFS algorithm

```python
depth[start] = 0; queue = [start]; visited = [start]
mass_at_depth[0] = hits[start]

while queue not empty:
    u = dequeue()
    if depth[u] >= MAX_ALLOWED_DEPTH: continue
    for v in adjacency[u]:
        if depth[v] == -1:                        # unvisited
            depth[v] = depth[u] + 1
            parent[v] = u
            enqueue(v); visited.append(v)
            mass_at_depth[depth[v]] += hits[v]    # accumulate attribution mass at this depth
```

BFS guarantees that `depth[v]` is the **shortest path distance** from `start` to `v` in the
unweighted family graph. For each visited family, `depth[v]` and `parent[v]` are exact — no
approximation. `mass_at_depth[d]` is the total hit count across all families at exactly
distance `d` from the dominant family.

**BFS as shortest-path:** The use of BFS (not DFS, not Dijkstra) is precisely correct for
unweighted graphs. In an unweighted graph, BFS always gives shortest distances; Dijkstra's
algorithm degenerates to BFS when all edge weights are equal. Since the family adjacency
graph (whether ring stub or real icosahedral topology) treats all edges as equal-cost, BFS
is the exact, optimal algorithm.

**Depth limit MAX_ALLOWED_DEPTH = 8.** This bound is shared with the Core Math Contract's
`T_steps = 8` (`corners/core_math_contract.md`). L2's BFS explores the same radius of the
semantic graph that L7's diffusion (`base_step`) will later fill with energy. L2 characterizes
the topology of that neighborhood; L7 activates it. Using the same depth constant is not a
coincidence — it ensures the topology analysis and the propagation step are looking at the
same subgraph.

---

## The 25 variables and their formulas

### Group 1 — BFS tree structure

| Variable | Formula | Meaning |
|---|---|---|
| `TRAVERSAL_START_FAMILY` | start (= L1.DOMINANT_FAMILY_ID) | BFS root — the traversal's reference point |
| `TOTAL_REACHABLE_NODES` | \|visited\| | Families reachable from dominant within MAX_DEPTH hops |
| `REACH_RATIO` | total_reachable / (F + ε) | Fraction of all 288 families reachable |
| `MEAN_TRAVERSAL_DISTANCE` | Σ depth[v] / \|visited\| | Average hop distance from start to each visited family |
| `MAX_TRAVERSAL_DISTANCE` | max(depth[v]) over visited | Furthest family reached |
| `TRAVERSAL_RADIUS_RATIO` | max_distance / (MAX_ALLOWED_DEPTH + ε) | How far the traversal went vs. allowed maximum |
| `PATH_COUNT` | \|visited\| − 1 | BFS tree edges: number of shortest paths from root to visited nodes |

**REACH_RATIO** measures how much of the semantic space is reachable from the dominant
concept within 8 hops. On a connected graph this approaches 1.0; on a sparse or partitioned
graph it can be significantly below 1.0, indicating that large portions of the concept space
are disconnected from the dominant activation.

**TRAVERSAL_RADIUS_RATIO** answers "did the BFS saturate its depth budget?" A ratio of 1.0
means the traversal kept finding new nodes all the way to the maximum depth (the neighborhood
extends beyond 8 hops). A ratio below 1.0 means the last mass appeared at a shallower depth
— the activation-carrying neighborhood is genuinely compact within the depth budget.

### Group 2 — Local topology at the start node

| Variable | Formula | Meaning |
|---|---|---|
| `BASE_NEIGHBOR_COUNT` | \|adjacency[start]\| | Degree of the dominant family in the graph |
| `ACTIVE_NEIGHBOR_COUNT` | count(n ∈ adj[start] : hits[n] > 0) | How many neighbors are hit in the attribution |
| `NEIGHBOR_ACTIVATION_RATIO` | active_neighbors / (base_neighbors + ε) | Fraction of the local topology that is activated |
| `BRANCHING_FACTOR_MEAN` | mean(degree(v)) over visited | Average degree across the entire traversal — how bushy the graph is |
| `LOCAL_CLUSTERING_COEFFICIENT` | 2·triangles / (deg·(deg−1)) at start | Standard Watts-Strogatz clustering coefficient |
| `TRAVERSAL_COMPACTNESS` | total_reachable / (max_distance + 1) | Nodes per depth level — width vs. depth ratio |
| `TRAVERSAL_SYMMETRY_INDEX` | Var(depth[v]) = Σ(depth[v] − mean_dist)² / \|visited\| | Variance of BFS distances — how uniform the shell expansion is |
| `CENTRALITY_SHIFT` | \|deg(start) − mean_deg(visited)\| | How atypical the start node is vs. the traversal mean |
| `EDGE_UTILIZATION_RATIO` | (total_reachable − 1) / (induced_edges + ε) | Tree edges / total induced edges (1.0 = pure tree, decreases as cycles added) |

**Local clustering coefficient** (Watts & Strogatz, 1998) is the canonical small-world
network measure of local connectivity. `C(v) = 2t(v) / (k(v)(k(v)−1))` where `t(v)` =
triangles incident to `v`, `k(v)` = degree of `v`. A high clustering coefficient at the
dominant family means its neighbors are also mutually connected — the local semantic
neighborhood is a dense cluster, not a star or tree. This informs downstream propagation:
high local clustering means energy will cycle within the neighborhood rather than flowing
outward uniformly. L2 computes it only at the start node because that is the topology-relevant
question: how interconnected is the concept around which the text is centered?

**TRAVERSAL_SYMMETRY_INDEX** is the variance of BFS hop distances. Low variance means most
visited nodes are at similar distances (a spherically symmetric expansion — the BFS "shell"
is uniform). High variance means some nodes are close and others are far, indicating the
graph is elongated or asymmetric around the start — one direction of the semantic neighborhood
extends much further than others. This is graph isometry information expressed as a single
number.

**TRAVERSAL_COMPACTNESS** (`total_reachable / (max_distance + 1)`) measures how "bushy" vs.
"deep" the traversal is. For a path graph, compactness = 1.0 (one node per depth level). For
a star, compactness = (n-1) / 1 = n-1 (all nodes at depth 1). For a balanced k-ary tree,
compactness = (k^{d+1}-1)/((k-1)(d+1)) ≈ k^d/d — high if the branching factor is large.
In the semantic family graph, compactness distinguishes "the dominant concept has broad,
shallow semantic neighbors" from "it has a narrow but deep semantic chain."

### Group 3 — Mass distribution through the topology

| Variable | Formula | Meaning |
|---|---|---|
| `PROPAGATION_MASS_DECAY` | mass_at_depth[d_last] / (mass_at_depth[d_last−1] + ε) | Attribution falloff rate at the deepest occupied shell |
| `MASS_RETENTION_RATIO` | Σ hits[v] for v ∈ visited / (hits[start] + ε) | How much total mass exists within the BFS neighborhood |

**PROPAGATION_MASS_DECAY** is a pre-diffusion measurement of how the existing attribution
mass falls off with distance. It measures the ratio of mass at the deepest populated depth
to the mass one level above. If most hits are near the dominant family (depth 0–2) and few
at depth 7–8, this ratio approaches 0, meaning raw attribution already shows a strong
distance-decay profile. If attribution is flat across depths, this ratio approaches 1.0.
This is the *pre-existing decay* in the text's attribution, before the diffusion engine
applies its own `decay=0.04/step` — a signal of how organically concentrated the text is.

**MASS_RETENTION_RATIO** compares the total attribution mass within the entire BFS
neighborhood to the mass at the start node alone. A ratio of 1.0 means all hits are in the
dominant family; a high ratio (>> 1) means many hits exist throughout the traversal region.
This is the "spillover factor" — how much of the attribution has already spread into the
dominant family's semantic neighborhood, without any propagation computation. Together with
PROPAGATION_MASS_DECAY it gives a two-axis picture of mass distribution: RETENTION says
"how much is there," DECAY says "how steeply does it fall off."

**MASS_AT_DEPTH[d]** (handoff to L6): the full array of mass-per-depth-level is passed
forward to L6, which uses it to characterize the depth profile of attribution for that
layer's dynamics analysis.

### Group 4 — Cross-area geometry

| Variable | Formula | Meaning |
|---|---|---|
| `CROSS_AREA_TRAVERSAL_COUNT` | count(v ∈ visited : area[v] ≠ dominant_area) | Visited families outside the dominant area |
| `CROSS_AREA_RATIO` | cross_area_count / (total_reachable + ε) | Fraction of the BFS neighborhood outside the dominant area |
| `AREA_BOUNDARY_CROSSINGS` | count(parent[v] ≠ -1 : area[parent[v]] ≠ area[v]) | BFS tree edges that cross an area boundary |

The cross-area variables are the L2-layer expression of the geometry coupling documented in
`corners/geometry_math_coupling.md`. The 12-area icosahedral structure is not just a label
system — area boundaries have a real cost (`bridge_weight = 0.22`) in the propagation step.
CROSS_AREA_RATIO at L2 predicts how much cross-area propagation will occur before the
propagation engine even runs: if half the BFS neighborhood is in a different area, propagation
will necessarily cross many area boundaries. AREA_BOUNDARY_CROSSINGS counts the actual
boundary-crossing events in the BFS tree — the topological surface where area-bridge cost
will be paid.

### Group 5 — Loop / cycle structure

| Variable | Formula | Meaning |
|---|---|---|
| `LOOP_COUNT` | induced_edges − (total_reachable − 1) | Extra edges in the induced subgraph beyond a spanning tree |
| `LOOP_DENSITY` | loop_count / (total_reachable + ε) | Cycles per node in the traversal region |

**Loop counting from the circuit rank.** A spanning tree on `n` nodes has exactly `n−1`
edges. Every additional edge in the induced subgraph creates exactly one independent cycle.
The number of independent cycles is therefore `induced_edges − (n−1)` — the circuit rank,
also called the cyclomatic number or first Betti number of the graph. L2 computes this
exactly for the BFS-induced subgraph. This is not an approximation.

**Why loops matter for propagation.** A cyclic graph allows energy to circulate: a signal
starting at node A reaches B, flows onward to C, and eventually returns to A, reinforcing
the original activation. On a tree, every path is unique and energy disperses monotonically
outward. The loop count therefore predicts resonance risk in the propagation step — a high
LOOP_DENSITY neighborhood will sustain and amplify dominant activations rather than diffusing
them smoothly. This is the structural precondition for the shadow correction layer's job
(`corners/shadow_correction.md`): if L2 shows high LOOP_DENSITY, the shadow mechanism will
need to do more work.

### Group 6 — Composite geometric stability

| Variable | Formula | Meaning |
|---|---|---|
| `GEOMETRIC_STABILITY_INDEX` | MASS_RETENTION_RATIO × max(0, 1−CROSS_AREA_RATIO) × max(0, 1−LOOP_DENSITY) | Joint signal of mass containment × area locality × topological simplicity |

`GSI = R × (1−X) × (1−L)`:
- `R = MASS_RETENTION_RATIO`: how self-contained the attribution mass is within the BFS neighborhood
- `(1−X) = 1 − CROSS_AREA_RATIO`: how locally area-confined the traversal is
- `(1−L) = 1 − LOOP_DENSITY`: how topologically simple (tree-like) the traversal region is

GSI is maximized (→1.0) when attribution mass is fully contained in the neighborhood (R→1),
the neighborhood stays within the dominant area (X→0), and the topology is a tree (L→0).
It approaches zero whenever any factor approaches its failure state: widespread cross-area
traversal, high cycle density, or mass scattered far outside the starting region. As with
`STRUCTURAL_STABILITY_INDEX` in L1, this is a Hesperia-native product-of-three-independent-
signals composite — the product means all three must be healthy for GSI to be high; any one
failing drags the whole composite down even if the other two are perfect.

---

## The two handoff values to downstream layers

L2 produces two values that are not L2 metrics but structural handoffs:

**`VISITED_IDS`** — the list of all family IDs reached by BFS. The pipeline runner converts
this to a set and passes it forward: `input_data.metadata["visited_B"] = set(state.layers[2].get("VISITED_IDS", []))`. L3 onward knows exactly which families are "inside" the BFS
neighborhood of the dominant concept. This is the activation envelope computed by L2 — the
set of families that the traversal declares geometrically reachable.

**`MASS_AT_DEPTH`** — the array of `hits`-mass at each depth level (length MAX_ALLOWED_DEPTH+1).
Passed forward to L6, which uses this depth profile for dynamics analysis: the shape of
mass_at_depth tells L6 how attribution concentrates vs. disperses radially from the dominant
family, before any propagation smoothing has occurred.

---

## Scientific lineage of L2's toolkit

| Tool | Origin | L2 use |
|---|---|---|
| **Breadth-First Search (BFS)** | Moore (1959) "The shortest path through a maze"; Lee (1961) maze routing; formalized in Cormen et al., *Introduction to Algorithms* | Exact shortest-path distances from dominant family; mass-per-depth accumulation; parent tracking |
| **Local clustering coefficient** | Watts & Strogatz (1998) "Collective dynamics of 'small-world' networks" *Nature* 393:440 | `LOCAL_CLUSTERING_COEFFICIENT`: triangles at start / possible triangles — measures local cliquishness of the dominant family's neighborhood |
| **Circuit rank / cyclomatic number** | Kirchhoff (1847), graph cycle space; formalized as cyclomatic complexity by McCabe (1976); standard in algebraic graph theory as the first Betti number | `LOOP_COUNT = induced_edges − (n−1)`: independent cycles in the induced subgraph — predicts energy resonance in propagation |
| **Degree centrality** | Freeman (1979) "Centrality in social networks: Conceptual clarification" *Social Networks* 1:215 | `CENTRALITY_SHIFT`: raw degree of start vs. mean degree of traversal — measures how topologically typical the dominant family is |
| **Graph compactness / tree width measures** | Classical graph theory | `TRAVERSAL_COMPACTNESS = n/(max_depth+1)`: nodes-per-depth; `EDGE_UTILIZATION_RATIO = tree_edges/induced_edges` — BFS tree vs. full induced subgraph |
| **Variance of graph distances** | Classical statistics on graph metrics | `TRAVERSAL_SYMMETRY_INDEX = Var(depth[v])`: how radially symmetric the BFS shell expansion is around the dominant concept |
| **Signal decay profile** | Pre-LLM statistical measurement — "how fast does signal fall off with distance" appears in signal processing, sociology (gravity models), spatial analysis | `PROPAGATION_MASS_DECAY`: ratio of mass at deepest populated shell to the preceding shell — pre-propagation distance-decay measurement |

**No learning, no parameters to fit.** Every L2 variable is a deterministic function of three
inputs: the adjacency graph (topology), the hits vector (attribution), and the BFS starting
point (dominant family from L1). The only parameter is `MAX_ALLOWED_DEPTH = 8`, shared with
the Core Math Contract's `T_steps`. There are no threshold choices internal to L2, no learned
weights, no statistical fitting. L2 is pure graph measurement.

---

## Why L2 precedes propagation

L2 answers "what does the topology around the dominant concept look like — before energy is
moved?" This is exactly the measurement that should precede propagation:

- High `LOCAL_CLUSTERING_COEFFICIENT` → expect energy to circulate locally rather than
  spread outward → propagation will be more contained
- High `LOOP_DENSITY` → resonance risk → shadow correction will need to suppress
- High `CROSS_AREA_RATIO` → expect cross-area propagation → bridge_weight cost will be paid widely
- Low `MASS_RETENTION_RATIO` → attribution is already widely scattered → starting condition for
  propagation is diffuse, not concentrated
- `TRAVERSAL_DEPTH_REACHED < MAX_ALLOWED_DEPTH` → activation mass is genuinely compact → propagation
  radius will be naturally limited by the existing attribution topology

L2 is the structural risk assessment for the propagation step. All of this is computed before
L7 runs a single diffusion step, making it available to L3–L6 (and through them to guards
and interpretation) as a topology-grounded prediction of what propagation will look like.

---

## Relationship to neighboring layers and corners

- **L1:** L2 seeds its BFS from L1's `DOMINANT_FAMILY_ID`. L1 characterizes the full 288-family
  distribution statistically; L2 characterizes the local subgraph around its peak.
- **L3–L6:** `VISITED_IDS` constrains which families L3 focuses on. `MASS_AT_DEPTH` provides
  the depth profile for L6's dynamics analysis.
- **L7 propagation:** L2's traversal covers the same 8-hop radius that `T_steps=8` diffusion
  will energize. L2 measures the topology; L7 moves mass through it.
- **Shadow correction:** High `LOOP_DENSITY` from L2 predicts where shadow correction will
  need to suppress cyclic reinforcement — L2 gives early warning of the structural conditions
  that make shadow work necessary.
- **`corners/geometry_math_coupling.md`:** L2's `CROSS_AREA_TRAVERSAL_COUNT` and
  `AREA_BOUNDARY_CROSSINGS` are the topology-traversal realization of the area-boundary
  cost (`bridge_weight = 0.22`) documented there. L2 counts boundary crossings structurally;
  the propagation engine prices them energetically.
- **`corners/core_math_contract.md`:** `MAX_ALLOWED_DEPTH = 8 = T_steps` — the shared constant
  that aligns BFS topology exploration with diffusion depth.

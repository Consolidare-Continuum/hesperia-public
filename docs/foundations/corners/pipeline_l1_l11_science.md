# Cross-cutting: the L1–L11 pipeline, full scientific lineage

**What this document is.** A single pass through the entire Hesperia pipeline —
pre-pipeline attribution through Layer 11's LLM bridge — tracing every key
formula to its external origin (or, where none exists, to its Hesperia-native
derivation). The individual layer docs (`layers/L1_*.md` through
`layers/L10_*.md`) and `corners/fpf_bridge.md` each give exhaustive per-layer
treatment; this document instead follows the *data flow* across all eleven
stages, asks what science each stage applies and why, and surfaces the
cross-cutting themes that only become visible when the whole chain is read
together.

No per-layer content is duplicated here for its own sake. Formulas are given
where they illuminate the transition from one stage to the next, or where the
lineage is non-obvious. Stubs and placeholder layers are recorded honestly
rather than glossed over — see Layer 6 and Layer 10.

---

## The pipeline as three tiers

```
Tier 0 — Lexical resolution (pre-L1)
  raw text → Dict A / Dict C match → Dict B disambiguation → (familyGlobal, altitude) pairs

Tier 1 — Measurement cascade (L1–L9)
  attribution result → 9 layers of deterministic measurement → USF assembly

Tier 2 — Synthesis gap + LLM bridge (L10–L11)
  measurements → (declared but unimplemented synthesis) → state-machine-gated LLM narration
```

The tiers are not layers — they are architectural boundaries. Tier 0 touches
natural language, and only Tier 0. After the `matched` list is produced,
every downstream stage operates on vectors, graphs, and scores, never on
surface forms. Tier 2 is the only stage that can produce prose, and that prose
is confined inside a state machine whose legal transitions are determined by
Tier 1's measurements, not by the LLM's free generation.

---

## Tier 0 — Lexical resolution (pre-pipeline)

### The normalization chain

Before any attribution:

```
raw_text
  → NFKC normalization + casefold + whitespace collapse + hard cap (10,000 chars)
  → whitespace split + punctuation strip (fixed ASCII set)
  → tokens: list[str]
```

This is a deterministic, stateless transformation — no language model, no
learned tokenizer. The ASCII punctuation strip set is fixed in the source; it
does not depend on the input language. Every preprocessing decision is a
constant, not a parameter.

### Dict A / Dict C matching: phrase-first, priority-ranked

Dict A matching is not a lookup table. `core/lexical/matcher.py` runs a
**greedy interval-scheduling** pass: find every occurrence of every Dict A
normalized form, then resolve overlapping spans by a lexicographic sort key —
*earliest start, then longest span, then strongest match_type, then highest
declared priority*. The "longest span wins" rule is the same as the classical
**maximum-weight interval scheduling** preference for precision over recall
(Kleinberg & Tardos, *Algorithm Design*, §6.1) but implemented as a
fixed-priority greedy pass rather than a dynamic program, making the sort key
auditable and immutable.

Dict C (phrase-level) entries operate on the same pass with `priority: 99`
(highest in the system) and `match_type: exact_phrase`. Because C entries
always win ties over A-level tokens, the weighting hierarchy is:
**exact phrase** (C) > **exact token** (A) > **stem/lemma/pattern** (A).
The probabilistic justification is conditional entropy: H(concept | phrase) <
H(concept | token) — a longer, rarer surface form narrows the concept space
more than a single token does (Salton, 1975, vector space model; Manning &
Schütze, 1999, §5 phrase indexing). Dict C freezes those lower-entropy phrase
anchors into precomputed lookup entries so the runtime never re-derives them.

### Dict B disambiguation: three distinct mechanisms

Once a span lands on a Dict A `side_id`, the resolver (`core/resolver/resolver.py`
`resolve_hit`) selects among multiple candidate Dict B concept IDs using three
scoring functions:

- `label_token_overlap`: string overlap between the hit and the concept's canonical label
- `coherence_from_related`: graph-adjacency coherence of the candidate in the B concept graph
- `specificity_rank`: preference for more specific (narrower) concepts

Ties are broken by `break_tie` (specificity_rank_desc then concept_id lexicographic). The
full audit trail is written to `rule_trace`, `candidate_scores`, and `winning_reason_codes`.

Dict B itself is built in reverse of the matching direction: `tools/build_dict_b_from_tfp_sources.py`
constructs B first from theory source texts, and `tools/build_dict_a_markers.py` then extracts
Dict A surface forms *from* that B — the opposite of how a classical dictionary-then-lookup
system would be structured. This lineage reversal means the controlled vocabulary's organizing
principle (the concept hierarchy in B) preceded and determined the surface-form vocabulary (A).

### What pre-pipeline produces: the `matched` list

```python
matched: list[tuple[familyGlobal: int, altitude: float]]
```

One tuple per attributed token, ordered as tokens appear in the text.
Unattributed tokens are absent — they are not in `matched`, not in any
downstream computation. Attribution yield is the first measurement made
about the text (L1's `COVERAGE_RATIO`), but it is not computed here — it is
computed at L1 from the length of `matched` vs. the token count.

The altitude value is a per-concept property frozen in the lexicon at build
time: it encodes how domain-specific a concept is within the controlled
vocabulary (0.0 = generic, 1.0 = maximally specific). Dict B fallback
assignments receive a fixed `default_altitude_b = 0.5`. No runtime inference
modifies altitude.

---

## Layer 1 — Structural Activation Census (34_SPEC)

**Input:** `matched` list, optional `StructureProfile`  
**Output:** 27 variables characterizing the raw attribution distribution  
**No LLM, no propagation, no guard.** Module docstring: "Deterministic, input-bound."

### Information-theoretic core

L1's central measurement is the **Shannon entropy** of the 288-family hit distribution:

```
H = −Σ_{f: p_f > 0} p_f ln(p_f),   p_f = hits[f] / (attributed + ε)
H_norm = min(1, H / ln(288))
```

Shannon (1948), "A Mathematical Theory of Communication": entropy measures the average
information content of a draw from a distribution. H = 0 when all attributed tokens
land in one family (pure certainty); H_max = ln(288) ≈ 5.66 nats when the distribution
is perfectly uniform across all 288 families (maximum structural ambiguity). Normalizing
by ln(288) brings the value into [0, 1] on the same scale used by `P_disp` in the Core
Math Contract — the system is self-consistent about entropy normalization from the first
layer forward.

The **Gini coefficient** provides an independent concentration measure:

```
G = 1 − (2 / (n · Σhits)) · Σ_{i=0}^{n-1} (n − i) · sorted_hits[i]
```

Gini (1912), "Variabilità e mutabilità": measures inequality in a distribution via
rank-weighted area under the Lorenz curve. G = 0 for a perfectly uniform distribution;
G → 1 for maximal concentration. Unlike entropy (log-weighted, sensitive to small
probabilities), Gini is linear in the sorted array — the two measures agree on direction
but respond differently to tail behavior. Their simultaneous use at L1 is not redundancy:
a high-entropy text with many equally-small activations can have lower Gini than a text
where the same entropy arises from two large symmetric peaks.

### The L1 and L2 norms of the hit vector

```
FAMILY_HIT_VECTOR_L1 = Σ hits[f]            (= attributed; L1 norm = total mass)
FAMILY_HIT_VECTOR_L2 = √(Σ hits[f]²)        (L2 norm; sensitive to concentration)
```

The ratio L2 / L1 is an implicit concentration index. Two texts with identical attributed
token counts will have different L2 norms if one concentrates mass in a few families and
the other spreads it evenly — the ratio rises with concentration. This implicit index flows
downstream without requiring a dedicated concentration variable.

### Altitude aggregation

Altitude values are aggregated by standard weighted statistics:
`MEAN_ALTITUDE_GLOBAL = Σ altitude_sum[f] / attributed`,
`ALTITUDE_VARIANCE_GLOBAL = Σ hits[f]·(mean_alt[f] − mean_alt_global)² / attributed`.
These are 19th-century descriptive statistics (Gauss, Quetelet), applied to measure whether
the attributed mass came predominantly from domain-specific or generic parts of the vocabulary.

### Hesperia-native composite: STRUCTURAL_STABILITY_INDEX

```
SSI = DOMINANCE_RATIO × (1 − NORMALIZED_FAMILY_ENTROPY)
```

This product has no direct external citation — it is a Hesperia-native composite of two
classical quantities. SSI is high when the distribution is simultaneously concentrated
(DOMINANCE_RATIO close to 1) and ordered (low background entropy). Either factor failing
drives SSI to zero: a diffuse attribution or a maximally disordered one both produce
SSI → 0, for structurally different reasons. This asymmetry — one composite that is zero
for two different failure modes — is what makes SSI a genuine new quantity rather than a
redundant encoding of its components.

### Profile deviation (34_SPEC N1 extension)

When a `StructureProfile` supplies expected distributions `FEDV` (288-dim) and `AEDV`
(12-dim), L1 computes deviation metrics using **L2 distance on probability vectors**:

```
FPD = clamp01(‖P_obs − FEDV‖₂ / √2)
APD = clamp01(‖Q_obs − AEDV‖₂ / √2)
```

Normalizing by √2 (the maximum possible L2 distance between two probability vectors)
gives FPD, APD ∈ [0, 1]. L2 distance is used rather than KL divergence because KL
diverges to +∞ when the expected distribution has zero mass in a family that the observed
distribution activates — a pathological output from a measurement tool that must always
return a finite number.

`BVS = max(violations)` (L∞ norm of the governance-cap violation vector): the maximum is
taken, not the mean, because a governance cap is a hard constraint whose violation is
significant regardless of how many other caps are simultaneously violated. This is the
correct norm when "single worst" semantics are required.

### What L1 hands to downstream layers

- `hits[f]` (288-dim integer vector): the primary structural artifact — not a scalar, not
  transformed. Every layer from L2 onward works from or alongside this vector.
- `DOMINANT_FAMILY_ID`: seeds L2's BFS.
- `NORMALIZED_FAMILY_ENTROPY`: feeds the `structural_monotony` rule in the logic layer
  (threshold 0.35).
- `COVERAGE_RATIO`, `DOMINANT_AREA_ID`: enter the facts dict for guard evaluation.

---

## Layer 2 — Topology Traversal (35_SPEC)

**Input:** `DOMINANT_FAMILY_ID` (BFS root), `hits` vector, `adjacency` (family graph)  
**Output:** 25 variables characterizing the graph neighborhood around the dominant concept  
**No semantics, no LLM, no shadow.**

### BFS and shortest-path distance

```python
depth[start] = 0; queue = [start]
while queue:
    u = dequeue()
    if depth[u] >= MAX_ALLOWED_DEPTH: continue
    for v in adjacency[u]:
        if depth[v] == -1:
            depth[v] = depth[u] + 1; enqueue(v)
            mass_at_depth[depth[v]] += hits[v]
```

BFS on an unweighted graph gives exact shortest-path distances (Moore, 1959; Lee, 1961;
Cormen et al., *Introduction to Algorithms*). For an unweighted graph, Dijkstra degenerates
to BFS — using BFS directly is therefore both simpler and equally correct. `MAX_ALLOWED_DEPTH = 8`
is shared with the propagation engine's `T_steps = 8`: L2's topology analysis and L7's
energy diffusion cover the same 8-hop radius. This is an explicit design constant, not a
coincidence — the topology census sees exactly the subgraph that propagation will energize.

### Local clustering coefficient

```
C(start) = 2·t(start) / (k(start) · (k(start) − 1))
```

Watts & Strogatz (1998), "Collective dynamics of 'small-world' networks," *Nature* 393:440.
`t(start)` = triangles incident to the dominant family; `k(start)` = its degree. High C
means neighbors are mutually connected — energy introduced at the dominant family will cycle
locally rather than spreading outward uniformly. This is the topological prediction for L7's
propagation behavior before propagation runs.

### Circuit rank — independent cycle count

```
LOOP_COUNT = induced_edges − (TOTAL_REACHABLE_NODES − 1)
```

Kirchhoff (1847), circuit laws — the original motivation for counting independent cycles in
a network. A spanning tree on n nodes has exactly n−1 edges; every additional edge in the
induced subgraph creates exactly one independent cycle. This is the **circuit rank** (first
Betti number) of the BFS-induced subgraph, computed exactly. `LOOP_DENSITY = LOOP_COUNT /
TOTAL_REACHABLE_NODES` normalizes it by traversal size.

High LOOP_DENSITY predicts energy resonance in the propagation step: cyclic topology allows
activation to circulate and reinforce rather than dissipate monotonically outward. This is
the structural precondition for the shadow correction layer (`corners/shadow_correction.md`)
to have significant work to do.

### Hesperia-native composite: GEOMETRIC_STABILITY_INDEX

```
GSI = MASS_RETENTION_RATIO × max(0, 1 − CROSS_AREA_RATIO) × max(0, 1 − LOOP_DENSITY)
```

Three-way product of independent stability signals: how self-contained attribution mass is
(R), how area-local the traversal is (1−X), how topologically simple the subgraph is (1−L).
Like SSI at L1, this composite has no direct external citation — it is Hesperia-native. The
multiplicative structure means all three factors must be healthy for GSI to be high; any
one failure collapses the composite regardless of the others.

### What L2 hands to downstream layers

- `VISITED_IDS` (set of family indices): the activation envelope — which families are
  geometrically reachable from the dominant concept within 8 hops. L3 onward knows which
  families are "inside" this neighborhood.
- `MASS_AT_DEPTH` (array, length 9): hit mass per BFS depth level. L6 uses this depth
  profile for its exponential-growth curve fit.
- `LOOP_COUNT`, `LOOP_DENSITY`: feed the `PROPAGATION_LOOP` instability flag in
  `core/stability/stability_delta.py` (threshold: loop_density > 0.20 or loop_count > 2).

---

## Layer 3 — Baseline vs. Shadow Comparison (36_SPEC)

**Input:** L1_B, L2_B, hits_B (baseline), and L1_S, L2_S, hits_S (shadow variant)  
**Output:** 25 delta and similarity variables; terminal SHADOW_ACCEPTABILITY_GATE (bool)

### The shadow: a deterministic perturbation

The shadow is not a stochastic noise injection. It is a fixed perturbation applied to the
attribution family vector before L1_S and L2_S are computed:

```
hits_S[i] = abs(hits_B[i] × (1 + k_shadow_perturb × ((i×7)%11 − 5)/5))
k_shadow_perturb = 0.04
```

The pattern `(i×7)%11 − 5` cycles over {−5, −3, −1, 1, 3, 5, −3, ...} as i increases —
a deterministic, non-repeating sequence over the first 11 family indices, then cycling.
The ±4% scale ensures the perturbation is small enough that a structurally robust reading
should survive it. There is no randomness: given the same hits_B, hits_S is always identical.

This follows the spirit of **perturbation/sensitivity analysis** (standard in numerical
methods and dynamical-systems theory) applied to discrete attribution: run the system twice
with a small, controlled difference, measure the divergence. Structural robustness is
operationally defined as "small input perturbation → small output divergence."

### Divergence metrics

```
ENTROPY_DELTA       = L1_S.H_norm − L1_B.H_norm          (Shannon entropy shift)
COSINE_SIMILARITY   = (hits_B · hits_S) / (‖hits_B‖₂ · ‖hits_S‖₂ + ε)
JACCARD_SIMILARITY  = |activated_B ∩ activated_S| / |activated_B ∪ activated_S|
```

Cosine similarity (standard in information retrieval, Salton 1975) measures angular
divergence between the two hit vectors — insensitive to magnitude differences, sensitive to
the direction of mass distribution. Jaccard similarity (Jaccard, 1901, originally for set
comparison) measures activated-family overlap — insensitive to count magnitudes, sensitive
to which families received any hits at all. Together they give two complementary angles on
"are the two attribution patterns the same kind of thing."

`SHADOW_ACCEPTABILITY_GATE = True` iff the cumulative divergence across all 25 delta
variables stays within configured thresholds. When False, downstream layers receive a flag
that the structural reading is not self-consistent under perturbation — any interpretation
built on it carries elevated uncertainty. The gate itself is a boolean; what it gates is
the downstream trust level, not the pipeline execution (which continues regardless).

### The fallback case

When no shadow data is provided (single-run mode), hits_S = hits_B, L1_S = L1_B, L2_S = L2_B.
All deltas are 0, all similarities 1.0, SHADOW_ACCEPTABILITY_GATE = True. This is a correct
degenerate case — a text compared against itself is trivially stable — and it means L3
adds zero computational cost in single-run mode. The pipeline is always valid; shadow
enriches it but is not a precondition.

---

## Layer 4 — Evidence Retrieval Quality (37_SPEC)

**Input:** dominant attribution, retrieved corpus chunks `R_pos`  
**Output:** 25 variables measuring how well the retrieved evidence supports the attribution

L4 operates on a **retrieved** set of text chunks, not on the input text itself. The
corpus retrieval step (outside the layer, in pipeline_runner before L4 is called)
fetches the chunks most relevant to the dominant attribution from a pre-indexed corpus.
L4 then asks: do those chunks, when attributed, corroborate the reading that the input
text produced?

### Shannon entropy of evidence spread

```
EVIDENCE_ENTROPY_BASELINE = H(chunk family distribution) / ln(F)
```

The same Shannon entropy formula as L1, applied to the family distribution of the retrieved
chunks rather than the input text. A high entropy means retrieved evidence spreads across
many concept families — the supporting corpus is thematically diverse. A low entropy means
retrieved evidence clusters around the same families the input text activated — the corpus
strongly corroborates the dominant attribution.

`EVIDENCE_SUPPORT_INDEX_BASELINE` and `INTEGRITY_CHECK_PASS_RATIO` are composite
consistency scores across the retrieved set. The latter (`INTEGRITY_CHECK_PASS_RATIO`)
flows directly into L5's counter-evidence computation as a baseline: L5 can only measure
*contradiction pressure* relative to how robust the support baseline is.

---

## Layer 5 — Counter-Evidence Pressure & Metric Invariants (38_SPEC)

**Input:** L4 output, `R_pos` (positive retrieval), `R_neg` (negative/contradictory retrieval)  
**Output:** 25 variables in two structurally unrelated halves (5A and 5B)

### Part 5A: counter-evidence as falsification pressure

5A is the mirror of L4 under the **falsification discipline** (Popper, 1959). L4 asks
"how well does the supporting evidence corroborate the dominant attribution?" L5 5A asks
"how much contradicting evidence was retrieved, and does it materially undermine L4's
confidence?"

`R_neg` is retrieved independently against a negation or contradiction query from the same
corpus. The 5A variables measure the ratio, entropy, family overlap, and weighted scoring
of `R_neg` vs. `R_pos`. The operative question is not "is there any counter-evidence?" —
there almost always is — but "does the counter-evidence distribution have enough mass,
specificity, and family-level overlap with the dominant attribution to be epistemically
threatening?"

### Part 5B: trigonometric and metric-space axiom residuals

5B does not use `R_neg` at all. It is a **geometric self-test**: given two vectors `v` and
`w` (defaulting to orthonormal basis `[1,0]` and `[0,1]`), verify that a set of
trigonometric and metric-space axioms hold to within numerical tolerance.

The tests include:
- Cosine identity: cos(θ) = (v·w)/(‖v‖‖w‖) should be consistent with atan2
- Pythagorean residual: ‖v‖² + ‖w‖² − ‖v+w‖² should equal 2·(v·w)
- Triangle inequality residual: ‖v+w‖ ≤ ‖v‖ + ‖w‖ (should be non-negative when rearranged)
- Metric-space identity and symmetry axioms

These tests are formally trivial — they are tautologies in exact arithmetic. They are
non-trivial in floating-point arithmetic, where accumulated rounding can produce residuals
inconsistent with the geometry the rest of the pipeline assumes. `REALITY_GATE_TRIG` is
True iff all 5B residuals are within tolerance — a Boolean assertion that the floating-point
environment is behaving as a valid Euclidean metric space for the kinds of vector operations
the system uses.

**Why REALITY_GATE_TRIG gates the final human-facing output release (L9's ACTION_ALLOW_HUMAN_SUMMARY):**
`ACTION_ALLOW_HUMAN_SUMMARY` requires L5's trig/metric self-test to have passed
(`SI_TRIG_REALITY_FLAG`, the L8-standardized form of `REALITY_GATE_TRIG`). A pipeline
that produces a human-readable summary despite the underlying geometry being numerically
broken would be making claims in a coordinate system it cannot verify. The self-test
connects a foundational computational prerequisite — the floating-point geometry is sound
— directly to the authorization to emit human-facing prose.

---

## Layer 6 — Dynamical Stability Scaffold (39_SPEC)

**Status: mostly a scaffold with explicit stub groups; two live computation groups.**

L6 is unusual in the pipeline: four of its five variable groups (I, II, IV, and most of V)
hold constants or stubs — variables that are declared and named but whose computation is not
yet implemented. The names are significant (sensitivity analysis, curvature proxies,
Lyapunov estimate, potential-field analogy) but the values are not yet live. This is
documented as a scaffold, not hidden as a gap.

### What is live: Group III — depth-growth curve fitting

```python
# Fit mass_at_depth[d] to exponential profile: m(d) = m_0 · e^{λd}
DEPTH_GROWTH_COEFF   = λ (slope of ln(mass_at_depth) vs. d)
DEPTH_GROWTH_QUALITY = R² of that fit (coefficient of determination)
```

`MASS_AT_DEPTH` from L2 is the input: the array of attribution hit mass at each BFS depth
level. If mass falls off monotonically with depth, λ < 0 (decay profile). If mass grows
outward, λ > 0 (radially expanding attribution — the dominant family's neighborhood has
more mass at distance than at the center itself, a structurally unusual configuration).
`DEPTH_GROWTH_QUALITY` (R²) measures how well the exponential model fits the actual profile
— a poor fit means the depth-mass relationship is non-monotonic or irregular, which itself
is a structural signal. The exponential decay / growth model has a long lineage in
statistical mechanics (Boltzmann distribution), spatial statistics (distance-decay), and
signal processing (exponential envelope fitting).

### What is live: Group V — Lyapunov estimate

```
LYAPUNOV_ESTIMATE = derived from DEPTH_GROWTH_COEFF and an eigenvalue proxy
COMPOSITE_STABILITY_ESTIMATE = combination of L2's GEOMETRIC_STABILITY_INDEX + dynamism signals
```

The Lyapunov estimate is a scalar proxy for "how quickly do small attribution perturbations
grow or shrink across the BFS radius?" The conceptual lineage is **Lyapunov stability theory**
(Lyapunov, 1892, *The General Problem of the Stability of Motion*): a dynamical system is
Lyapunov-stable at a point if sufficiently small perturbations around that point do not grow
unboundedly. L6's estimate is not a literal Lyapunov exponent (that would require iterating
the system forward in time from nearby initial conditions), but it is a proxy of the same
sign: if DEPTH_GROWTH_COEFF > 0 (mass expands radially), the system is likely amplifying
perturbations; if < 0 (mass decays radially), the system is likely contracting them.

### The dynamism metrics from sphere/dynamism/

Separate from L6's layer output, the sphere's dynamism engine (`sphere/dynamism/`) computes
trajectory metrics across a *sequence* of pipeline runs. These are not L6 output but flow
into L7's consistency gates and the facts dict:

```
curvature      = mean of step-score changes over steps 0, 1, 2
                  (NOT Ricci curvature — Hesperia-native trajectory acceleration proxy)
jump_rate      = jump_count / total_transitions
stability_index = repeated_stays / total_transitions
structural_tension = 1 − dominant_mass / total_mass
```

The scientific framing behind these is:
- **Chapman-Kolmogorov equations** (Markov, 1906; Kolmogorov, 1931): the multi-step
  transition probability P(X_{n+k} | X_0) = P^k factorizes via the intermediate states
  — basis for trajectory analysis over a Markov-like state sequence.
- **Cybernetic feedback** (Wiener, 1948, *Cybernetics*): `stability_index` measures how
  often the system returns to a previously-visited state rather than transitioning —
  a discrete-sequence analog of a feedback-stabilized control system's tendency to orbit
  its attractor.
- `jump_rate` is a first-order derivative of structural state over the trajectory: how
  often does the dominant activation shift categorically (area or family jump) vs. staying
  near the current state?

---

## Layer 7 — Cross-Layer Consistency Gates & Decision Synthesis (40_SPEC)

**Input:** L1 through L6 outputs, dynamism metrics, propagation results  
**Output:** 25 variables including 10 boolean consistency gates and a terminal DECISION_STATUS_CODE

L7 is the first layer that synthesizes across all prior layers rather than measuring a
single property. It does this through a set of **Boolean consistency predicates** that
ask whether the measurements from different layers agree with each other.

### The 10 CONSIST_* gates

Each gate is a conjunction of conditions drawn from two or more prior layers:

```
CONSIST_ENTROPY_COHERENCE:    |L1.H_norm − L3.ENTROPY_DELTA| < threshold_H
CONSIST_TOPOLOGY_PROPAGATION: L2.GEOMETRIC_STABILITY_INDEX > θ_topo AND propagation_mass_ok
CONSIST_SHADOW_STRUCTURE:     L3.SHADOW_ACCEPTABILITY_GATE AND L3.cosine_sim > θ_shadow
CONSIST_EVIDENCE_SUPPORT:     L4.INTEGRITY_CHECK_PASS_RATIO ≈ 1.0 AND L4.ESI > θ_esi
CONSIST_COUNTER_EVIDENCE:     L5A contradiction pressure < θ_contra
CONSIST_REALITY_GATE:         L5.REALITY_GATE_TRIG (the 5B metric self-test)
CONSIST_STABILITY_SCAFFOLD:   L6.COMPOSITE_STABILITY_ESTIMATE > θ_stab
CONSIST_CROSS_LAYER_TENSION:  structural_tension within band
CONSIST_AREA_GEOMETRY:        area-level stability flags consistent
CONSIST_PROPAGATION_BOUNDS:   propagation mass conservation verified (< 1e-5 relative tolerance)
```

The specific thresholds (θ_*) are declared in `specs/canon/diagnostic_rules.yaml`, not
hardcoded in the layer. This separates the measurement logic from the operating thresholds,
allowing the spec to evolve independently of the measurement code.

### DECISION_STATUS_CODE

The terminal output of L7 is a single integer code: 0 = all gates pass, nonzero = at least
one gate failed with an encoded severity. The downstream consumption is decisive:

- L8's interpretation policy Π uses it to select the canonical interpretation tier
- L9's BRAND_WORD_TRUST checks it first: `DECISION_STATUS_CODE ≠ 0` → `"BLOCKED"` regardless
  of any other pillar
- L9's `ACTION_REQUIRE_GOVERNANCE_REVIEW` fires on `DECISION_STATUS_CODE ≠ 0` OR
  `SI_SYSTEM_CONFIDENCE_U1000 < 450`
- L9's `ACTION_ALLOW_HUMAN_SUMMARY` requires `DECISION_STATUS_CODE == 0` as a necessary condition

The code pattern is classical: a single integer exit code that encodes both presence and
nature of failure, consumed by downstream stages without needing to re-evaluate the
individual gate conditions. The semantics are analogous to HTTP status codes or POSIX
process exit codes — a universally legible compact signal.

---

## Layer 8 — Unit Standardization & Interpretation Policy (41_SPEC)

**Input:** L1–L7 outputs  
**Output:** taxonomy fields + 22 SI_* standardized fields + Π interpretation policy

L8 is the pipeline's **unit-conversion and normalization** layer. Its job is not to compute
new quantities but to render existing quantities from heterogeneous scales (ratios, raw
counts, entropy values, boolean flags) into two uniform scales that downstream consumers
can combine without scale-mismatch errors.

### The U1000 scale

```
SI_{X}_U1000 = clamp(round(raw_value × 1000), 0, 1000)
```

A **per-mille** scale: 0 = worst, 1000 = best, with integer precision. The choice of 1000
rather than 100 preserves 3× more resolution than a percentage (which bottoms out at 1-point
granularity for 0–100 values) while remaining a round number that humans can interpret at a
glance. It is not borrowed from a named standard; it is a pragmatic unit that keeps all
downstream arithmetic addition-compatible without normalization.

### SI_* fields

The 22 SI_* fields cover 11 source variables, each rendered in approximately 2 forms (U1000
and percent, or U1000 and a named enum). Every raw value from L1–L7 that flows into L9's
pillar computation is standardized here first. The one exception: L9's
`ACTION_REQUIRE_EVIDENCE_REBUILD` reaches past L8 directly to L4's raw
`RETRIEVAL_SHORTFALL_BASELINE` (a count, not a ratio) because L8 never assigned it a
U1000 rendering. This is the only direct L4→L9 reference that bypasses L8; it is explicit
in L9's source.

### The Π interpretation policy

L8's `run()` (not `compute_L8()`) appends a **policy tier** to the output:

```
Π = {
  tier:        canonical | reduced | minimal | blocked   (from L7.DECISION_STATUS_CODE)
  rationale:   ordered list of which L7 gates passed/failed
  ceiling:     maximum allowed output verbosity for this run
}
```

The `ceiling` field is the upstream counterpart of L9's action triggers: where L9's ACTIONs
say "this trigger fires," L8's Π.ceiling says "this is the maximum fidelity you are allowed
to reach." Together they form a two-directional constraint on what the final output is allowed
to claim — ceiling from above (policy), trigger from below (measurement).

---

## Layer 9 — Pillars, Bands & Human-Facing Labels (42_SPEC)

**Input:** L1–L8 outputs via the standardized SI_* fields  
**Output:** 6 confidence bands, 6 pillar scores, 5 brand-word labels, 4 action triggers

L9 is the final measurement layer: the stage that converts the full measurement cascade into
a small, legible set of governance signals that non-specialist consumers can act on.

### Confidence bands

```
SI_SYSTEM_CONFIDENCE_U1000 (u) → BAND:
  BAND_0_CRITICAL:   u  <  200
  BAND_1_WEAK:    200 ≤ u  <  400
  BAND_2_FAIR:    400 ≤ u  <  600
  BAND_3_GOOD:    600 ≤ u  <  800
  BAND_4_STRONG:  800 ≤ u  <  950
  BAND_5_EXCELLENT:    u  ≥  950
```

The band boundaries are Hesperia-native thresholds with no direct external citation. The
six-band scheme is analogous to letter-grade or tier-rating conventions found in
standards bodies (ISO certification tiers, credit rating agencies) — a convention for
converting a continuous score into an ordered categorical signal legible to governance
consumers. The precision of `u` is preserved in the underlying SI_ value; the band is
the summary.

### The six governance pillars

```
PILLAR_COVERAGE_U1000      ← SI_COVERAGE_U1000            (L1 COVERAGE_RATIO)
PILLAR_EVIDENCE_U1000      ← SI_EVIDENCE_SUPPORT_U1000    (L4 EVIDENCE_SUPPORT_INDEX)
PILLAR_CONTRADICTION_U1000 ← SI_COUNTER_EVIDENCE_U1000    (L5A counter-evidence)
PILLAR_GEOMETRY_U1000      ← (1000 − SI_AREA_LEAKAGE_U1000) (L2 CROSS_AREA_RATIO, inverted)
PILLAR_SHADOW_U1000        ← SI_SHADOW_COSINE_U1000        (L3 COSINE_SIMILARITY)
PILLAR_GOVERNANCE_U1000    ← SI_SYSTEM_CONFIDENCE_U1000 × (1 − L7.DECISION_STATUS_CODE_magnitude)
```

Each pillar is a single measurement from a single prior layer, standardized by L8, carrying
a name that makes its meaning legible without reference to the measurement machinery that
produced it. The six pillars span the same six failure modes the layer cascade was designed
to detect: insufficient lexical coverage (L1), unsupported attribution (L4), contradicted
attribution (L5), geometrically unstable reading (L2), structurally non-robust reading (L3),
and governance-gate failures (L7). Choosing which six to expose is a Hesperia-engineering
decision; the *pattern* of "many internal metrics → few named pillars for governance" is
standard in quality management systems (ISO 9001 KPIs, Six Sigma CTQs, balanced-scorecard
design).

### Brand-word labels

Five threshold-ladder mappings converting U1000 pillar values to short ordered categorical
labels (`"SUPPORTED"` / `"BACKED"` / `"THIN"` / `"ABSENT"`; `"CONSISTENT"` / `"MIXED"` /
`"CONTRADICTED"`; etc.). These are not new computations — they are a presentation layer
over the U1000 values, making the pipeline's verdict readable without requiring the consumer
to interpret a continuous score. BRAND_WORD_SHADOW is a small embedded state machine (not
a threshold ladder) over the shadow condition.

### Action triggers

The four action triggers are the pipeline's **go / no-go signals**:

```
ACTION_REQUIRE_MORE_INPUT:
  SI_COVERAGE_U1000 < 500

ACTION_REQUIRE_EVIDENCE_REBUILD:
  L4.INTEGRITY_CHECK_PASS_RATIO < 1.0  OR  L4.RETRIEVAL_SHORTFALL_BASELINE > MAX_SHORTFALL

ACTION_REQUIRE_GOVERNANCE_REVIEW:
  L7.DECISION_STATUS_CODE ≠ 0  OR  SI_SYSTEM_CONFIDENCE_U1000 < 450

ACTION_ALLOW_HUMAN_SUMMARY:
  L7.DECISION_STATUS_CODE == 0
  AND  SI_SYSTEM_CONFIDENCE_U1000 ≥ 650
  AND  SI_TRIG_REALITY_FLAG              ← L5B's trig/metric self-test
```

`ACTION_ALLOW_HUMAN_SUMMARY` is the only positive gate in the cascade — the explicit
"proceed" signal. Its three-way AND structure means no single strong pillar can override
a failure in any other: a high-confidence reading (≥ 650) that failed L7's consistency
gates still cannot emit a human summary, and a fully consistent reading that failed L5B's
geometric self-test cannot either. The trig reality gate's presence in the AND means the
entire L1–L9 measurement cascade is authorized to produce human-facing output only in an
environment where the floating-point geometry it runs on has passed its own self-test.

---

## Layer 10 — Analysis Report / Interpretation (declared, not yet implemented)

**Status:** placeholder stub in `sphere/pipeline/pipeline_runner.py`; active governance consequence.

```python
layer_outputs["layer_10"] = {
    "analysis_report": None,
    "interpretation":  None,
    "explanation":     None,
    "_placeholder":    allow_l10_placeholder,   # default True
}
```

L10 is the **synthesis gap** — the declared but unimplemented boundary between measurement
(L1–L9) and narration (L11). Its intended role is to read all `layer_outputs` simultaneously
and produce a structured interpretive account: `analysis_report` (aggregate analysis),
`interpretation` (structured semantic characterization), `explanation` (auditable reasoning
chain). None of these are produced currently; the three fields are None on every run.

### THETA_004: the active governance consequence

Theta governance (`sphere/guards/theta_governance.py`) fires Rule THETA_004 on every current
pipeline run:

```
rule_id:   THETA_004
severity:  medium
condition: layer10_placeholder == True
action:    flag_non_canonical_interpretation
```

`flag_non_canonical_interpretation` is not a hard rejection — it does not stop the pipeline.
It marks the output's certification level: any result produced while L10 is a placeholder
carries this flag in `theta_result.governance_flags`. The system explicitly acknowledges,
on every run, that it has not performed the interpretation synthesis step. This is the same
"degrade rather than silently omit" pattern used throughout the guard triad: a structural
gap does not pass unnoticed; it reduces the output's canonical status.

### The architectural argument for L10's necessity

L1–L9 each measure a single property of the attribution in sequence. L10's structural
position — after all prior outputs exist and before the LLM bridge receives them — is the
correct place for the first step that must hold all nine layers' outputs simultaneously.
No standalone `layer_10.py` can implement this, because any layer module receives only the
outputs it is explicitly passed; only `pipeline_runner.py` has access to the full
`layer_outputs` dict at the moment L10 would run. This is why the placeholder lives in
`pipeline_runner.py` rather than in a separate layer file — the architecture correctly
locates the synthesis step at the only place where synthesis is computationally possible.

---

## Layer 11 — The LLM Reasoning Bridge (fpf_bridge, implemented v7)

**Source:** `sphere/fpf_bridge/`, `specs/canon/fpf_bridge_v7.md`  
**Status:** IMPLEMENTED, v7, 2026-06-27. Pure consumer — zero modifications to sphere code.

L11 is architecturally a different kind of thing from every layer above it. L1–L10 each
produce measurements or structured data; L11 produces the conditions under which an LLM is
allowed to narrate those measurements as prose, without itself performing the narration.

### Why a state machine, not a JSON dump

The core architectural decision of L11:

> Hand the LLM a 5-state, 13-transition state graph with 8 evidence-gated gates rather
> than the raw pipeline result dict.

Handing a raw dict to an LLM and asking it to narrate would produce output whose provenance
cannot be mechanically verified after the fact. The LLM could produce a summary that reads
well but that extrapolates beyond the evidence, contradicts the guard verdicts, or silently
elides a critical flag like THETA_004. The state machine replaces "can the LLM say X" with
"is there a legal transition corresponding to X" — a question that can be checked
mechanically. If no legal transition exists for a claim, the claim cannot appear in the output
regardless of what the LLM would otherwise generate.

### FGR trust tuples

Every fact handed to the LLM via `evidence_mapper.py`'s `EvidencePrimitive` carries a
calibrated trust tuple rather than a bare value:

```
⟨F, G, R⟩  — Formality, G-context (bounded context scope), Reliability
```

This is FPF Part B.3's trust calculus (Anatoly Levenchuk, ~51,300-line specification):
trust is not a scalar confidence but a three-dimensional characterization of *how* a claim
is established. F = how rigorously the claim is expressed; G = which bounded context the
claim is scoped to; R = how well evidenced the claim is. A state machine gate can then
require not just "is this evidence present" but "is this evidence formal enough, scoped
correctly, and reliable enough" — three independent conditions rather than one threshold.

**FPF's Gamma (Γ) vs. Hesperia's Gamma guard** are not the same: FPF's Γ is an aggregation
operator for combining parts into wholes under explicit invariants; Hesperia's Gamma guard
(Era 3) verifies execution ordering. The spec keeps these genuinely separate: "9 fpf
built-in guards + 3 Hesperia guards (Sigma/Gamma/Theta)" is additive, not derivational.

### Guard closures

`guard_bridge.py` wraps Sigma, Gamma, and Theta verdicts as closures over already-computed
sphere results rather than re-running guard logic:

```python
sigma_passed  = lambda: guards.sigma.passed
gamma_passed  = lambda: guards.gamma.passed
theta_approved = lambda: guards.theta.approved
```

Closures over fixed results make drift structurally impossible: there is exactly one Sigma
verdict per pipeline run, referenced from two places (sphere and bridge), never recomputed.
If the bridge re-ran Sigma with a different algorithm version, the bridge could produce a
verdict inconsistent with the sphere's — the closure architecture eliminates that possibility.

### Prolog facts as pre-resolved atoms

`logic_bridge.py` treats `prolog_logic.derived_facts` as pre-resolved booleans, exposing
them as `CustomProp` atoms for the LogicLayer's 7 declarative rules. This preserves the
single-source-of-truth principle: the Prolog engine already performed forward-chaining;
the bridge exposes its results, not a second copy of the inference machinery.

### The LogicLayer and L10's missing input

`logic_bridge.py`'s docstring: "Build fpf LogicLayer from sphere L9/L9b/L10 outputs."

The intended three inputs to the fpf LogicLayer are L9 rule triggers, L9b Prolog-derived
facts, and L10's interpretation synthesis. Currently only two of three exist: L10's output
is None, so the LogicLayer operates without the synthesis artifact it was designed to receive.
This is the second downstream consequence of L10's placeholder state (THETA_004 being the
first): the LLM bridge is receiving a structurally incomplete evidence set on every run.

---

## Cross-cutting themes

### 1. Conservation of attribution mass

`core/math/conservation.py`'s `check_mass_conservation` asserts:

```
|sum(after) − sum(before)| / sum(before) < 1e-6
```

Applied across every propagation step. This is the discrete continuity equation — total
activation mass is conserved unless an explicit decay term accounts for the difference.
`core/dynamics/operator.py`'s `compute_h_total` additionally tracks `total_energy_before`,
`total_energy_after`, `expected_decay_loss`, `actual_loss`, and `forbidden_loss` (energy
that disappeared without being accounted for) — distinguishing dissipation from numerical
leakage, as in a physical simulation. The discipline is borrowed from physics simulation
methodology; the conserved quantity ("activation energy") is Hesperia-native.

### 2. Shannon entropy as the shared measurement language

Shannon entropy appears at five distinct points in the pipeline, each measuring a different
distribution:

| Stage | Distribution | Scale |
|---|---|---|
| L1 FAMILY_ENTROPY | 288-family hit distribution of input text | H_norm ∈ [0, 1], normalized by ln(288) |
| L1 NORMALIZED_FAMILY_ENTROPY | same | feeds logic layer `structural_monotony` rule (threshold 0.35) |
| L3 ENTROPY_DELTA | H_norm(shadow) − H_norm(baseline) | signed delta; measures perturbation sensitivity |
| L4 EVIDENCE_ENTROPY_BASELINE | 288-family distribution of retrieved chunks | H_norm ∈ [0, 1] |
| Calibration convergence | Dict B concept weight distribution in links.jsonl | target: minimal H (peaked toward covered concepts) |

The same formula, the same normalization convention, five different distributions. This is not
entropy-as-metaphor — the same quantity (Shannon 1948, −Σp log p / ln(M)) is computing
genuinely different things at each stage, each relevant to that stage's measurement question.

### 3. Falsification and dual-path structure

Three distinct stages apply a dual-path logic:

- **L3 (shadow comparison):** two attribution paths, small deterministic perturbation, measure
  divergence. Structural robustness is defined as "survives ±4% perturbation."
- **L4/L5 (support vs. contradiction):** two retrieval paths, one confirmatory and one
  adversarial. Evidential soundness requires both paths to be consistent.
- **L7 (consistency gates):** ten boolean conjunctions across layer pairs. Interpretive
  legitimacy requires all measurement stages to agree within specified tolerances.

The recurring architecture is Popperian: a reading is accepted not because it passed
confirmatory tests but because it survived falsification attempts (shadow, counter-evidence,
consistency gates). Three independent falsification mechanisms are applied before the output
is authorized.

### 4. Determinism as an architectural invariant

Every layer from L1 through L10 is deterministic: given the same input, the same output is
produced, always. This is guaranteed structurally:
- No LLM calls in L1–L9 (each layer's own docstring states this)
- Propagation weights are read from `specs/canon/propagation_weights.yaml`, not tuned at runtime
- The shadow perturbation is a deterministic function of family index (no random seed)
- Guard verdicts are bounded Boolean functions with fixed threshold constants

L11 is the single exception: it hands a bounded problem to an LLM (fundamentally non-deterministic).
The state machine, FGR gates, and guard closures are the architecture that keeps L11's
non-determinism from propagating back into L1–L10's measurement results.

### 5. Hesperia-native composites vs. borrowed science

The system applies borrowed science faithfully and creates native composites when no
appropriate external construct exists. The audit:

| Formula | Origin | Note |
|---|---|---|
| H = −Σp log p | Shannon (1948) | Used verbatim, with explicit normalization by ln(M) |
| G = Gini coefficient | Gini (1912) | Standard form |
| Circuit rank = E − (V−1) | Kirchhoff (1847) | Applied to BFS-induced subgraph |
| C(v) = 2t/(k(k−1)) | Watts & Strogatz (1998) | Applied at dominant family node only |
| Cosine similarity | Salton (1975) | Standard vector space model form |
| Jaccard (1901) | Set overlap | Standard form |
| BFS shortest path | Moore (1959) | Applied to unweighted graph |
| L2 distance normalized by √2 | Classical metric geometry | For profile deviation (FPD/APD), chosen over KL for finiteness |
| v' = (1−α)v + α·vW | Lazy random walk / PageRank | Diffusion step; Brin & Page (1998) lineage via random walk |
| H_self = v·(1−decay) | Euler discretization of dv/dt=−decay·v | LIF neuron ODE, Lapicque (1907) |
| H_coupling = α·mean(v) | Mean-field theory | Weiss (1907) Curie-Weiss |
| Chapman-Kolmogorov | Markov (1906), Kolmogorov (1931) | Multi-step trajectory probabilities |
| Lyapunov estimate | Lyapunov (1892) | Proxy, not literal exponent |
| FGR ⟨F,G,R⟩ | FPF Part B.3, Levenchuk | External specification, applied verbatim |
| SSI = D × (1−H_norm) | Hesperia-native | Named as native in `provenance.md` |
| GSI = R × (1−X) × (1−L) | Hesperia-native | Named as native in `provenance.md` |
| U1000 per-mille scale | Hesperia-native | Pragmatic unit, no external citation |
| Six pillars, band boundaries | Hesperia-native engineering decisions | Pattern from quality management, thresholds not borrowed |

---

## Inter-layer data flow: the complete handoff table

| From | To | What is handed | How used |
|---|---|---|---|
| Pre-pipeline | L1 | `matched: list[(familyGlobal, altitude)]` | Entire L1 census input |
| L1 | L2 | `DOMINANT_FAMILY_ID` | BFS root |
| L1 | L2 | `hits[f]` (288-dim) | Mass per family for BFS accumulation |
| L1 | Facts dict → L7 | `H_norm`, `COVERAGE_RATIO`, `DOMINANT_AREA_ID` | Logic rules, consistency gates |
| L2 | L3, L4 onward | `VISITED_IDS` | Activation envelope — which families are "inside" |
| L2 | L6 | `MASS_AT_DEPTH` array | Depth-growth curve fit |
| L2 | Stability module | `LOOP_COUNT`, `LOOP_DENSITY` | PROPAGATION_LOOP instability flag |
| L2 | Propagation engine | `hits` (passed through) | Pre-diffusion mass for energy computation |
| L3 | L7 | `SHADOW_ACCEPTABILITY_GATE`, `cosine_sim` | CONSIST_SHADOW_STRUCTURE gate |
| L3 | L8 | Shadow cosine → SI_SHADOW_COSINE_U1000 | PILLAR_SHADOW_U1000 |
| L4 | L5 | `INTEGRITY_CHECK_PASS_RATIO`, `ESI_BASELINE` | Counter-evidence baseline |
| L4 | L7 | `INTEGRITY_CHECK_PASS_RATIO` | CONSIST_EVIDENCE_SUPPORT gate |
| L4 | L9 (direct) | `RETRIEVAL_SHORTFALL_BASELINE` | ACTION_REQUIRE_EVIDENCE_REBUILD |
| L5 | L7 | `REALITY_GATE_TRIG` | CONSIST_REALITY_GATE gate |
| L5 | L8 | `REALITY_GATE_TRIG` → SI_TRIG_REALITY_FLAG | ACTION_ALLOW_HUMAN_SUMMARY prerequisite |
| L6 | L7 | `COMPOSITE_STABILITY_ESTIMATE` | CONSIST_STABILITY_SCAFFOLD gate |
| L7 | L8 | `DECISION_STATUS_CODE` | Π interpretation policy tier |
| L7 | L9 | `DECISION_STATUS_CODE` | BRAND_WORD_TRUST override, ACTION_* conditions |
| L8 | L9 | All SI_* fields | All PILLAR_* computations |
| L9 | L11 (via L10 gap) | All outputs + `layer_outputs` dict | fpf LogicLayer inputs (L10 currently None) |
| L9b (Prolog) | L11 | `derived_facts` | CustomProp atoms in LogicLayer |
| Guards (Sigma/Gamma/Theta) | L11 | Verdicts as closures | State machine gate preconditions |

---

## Relationship to neighboring corners

- [`layers/L1_structural_activation_census.md`](../layers/L1_structural_activation_census.md) through
  [`layers/L10_analysis_report_placeholder.md`](../layers/L10_analysis_report_placeholder.md) —
  the authoritative per-layer treatment; this document synthesizes across them without replacing them.
- [`corners/fpf_bridge.md`](fpf_bridge.md) — the authoritative L11 document; this document
  adds the cross-pipeline framing.
- [`corners/physics_dynamics_coupling.md`](physics_dynamics_coupling.md) — the exhaustive
  formula-level treatment of propagation, diffusion, and trajectory dynamics; cited here for
  the full derivation of H_total, the diffusion step, and the dynamism metrics.
- [`corners/activation_landing_loops.md`](activation_landing_loops.md) — the exhaustive
  treatment of pre-pipeline attribution, both Dict A matcher implementations, and the two
  unrelated "loop" concepts; this document's pre-pipeline section is the summary form of that corner.
- [`corners/lexicon_resolver.md`](lexicon_resolver.md) — Dict B adjudication, the three
  B/A mechanisms, and Dict C's ACB/BAC construction paths; cited here for the pre-pipeline
  stage's resolver step.
- [`provenance.md`](../provenance.md) — the full audit of which named constructs are externally
  derived vs. Hesperia-native; this document's lineage table is a derived summary.
- [`parameter_catalog.md`](../parameter_catalog.md) — every explicit constant referenced
  here (F=288, A=12, T_steps=8, k_shadow_perturb=0.04, SIDES_PER_FAMILY=1500, etc.).

# Layer 3 — Baseline vs. Shadow Comparison (`core/layers/layer_3.py`, 36_SPEC)

**Position in pipeline:** Third executable layer. The first layer that does not describe the
text itself — it describes the *stability* of the structural reading by comparing two parallel
runs: the Baseline (B) and the Shadow (S). L3 computes 25 delta and similarity variables
measuring how much the two runs diverge. Its terminal output is a binary gate —
`SHADOW_ACCEPTABILITY_GATE` — that determines whether the shadow path's perturbation was
small enough for downstream layers to treat the reading as structurally robust.

**Spec origin:** `36_SPEC`. Module docstring: *"25 variables: comparison of baseline (B) vs
shadow (S) runs. Deterministic. Inputs: L1_B, L2_B, hits_B, L1_S, L2_S, hits_S."*

---

## The B/S duality: what Baseline and Shadow are

Every Hesperia pipeline run implicitly carries two structural readings of the same text:

**Baseline (B):** The standard attribution result — `hits_B[f]` from the normal Dict A/B
matching, L1_B and L2_B computed from it.

**Shadow (S):** A deterministically perturbed variant — `hits_S` is derived from the same
attribution but with a fixed, pseudo-random perturbation applied to the family vector:
`v'[i] = abs(v[i] × (1 + k_shadow_perturb × ((i×7)%11 − 5)/5))` with `k_shadow_perturb
= 0.04`. This is a ±4% deterministic jitter over family indices using a modular arithmetic
sequence — not random noise, but a fixed perturbation that differs by family index in a
predictable, reproducible pattern. L1_S and L2_S are then computed from `hits_S` exactly
as the baseline layers were computed from `hits_B`.

**If no shadow data is provided**, the `run()` function falls back to `hits_shadow = hits_B`,
`l1_shadow = l1_B`, `l2_shadow = l2_B`. In that case all deltas are 0, cosine similarity is
1.0, Jaccard is 1.0, and `SHADOW_ACCEPTABILITY_GATE = True`. The pipeline continues with the
reading declared trivially stable.

**Why run twice at all.** L3 is doing robustness analysis: the question is not "what does this
text activate?" (that is L1's job) but "is that activation stable under small perturbation?"
A structural reading that changes fundamentally when family weights shift by 4% is a fragile
reading — it is sitting near a boundary between structural interpretations, and small variations
in attribution (different tokenization edge cases, slightly different lexicon weights) could
flip the conclusion. A reading that survives the shadow perturbation unchanged is robust —
the conclusion is stable not just for this exact input but for the neighborhood of inputs
around it.

This is a form of **local sensitivity analysis** or **influence function analysis** applied to
the structural reading: perturb inputs slightly, measure output divergence, gate on the result.

---

## The 25 variables: three tiers of divergence measurement

### Tier 1 — Categorical changes (boolean)

| Variable | Meaning |
|---|---|
| `SHADOW_ENABLED` | Always True in current implementation — marks that shadow comparison ran |
| `DOMINANT_FAMILY_CHANGED` | `dominant_S ≠ dominant_B` — did the argmax family change? |
| `DOMINANT_AREA_CHANGED` | `area_S ≠ area_B` — did the dominant area change? |

`DOMINANT_AREA_CHANGED` is treated as a qualitatively different event from
`DOMINANT_FAMILY_CHANGED`. A family change (e.g., family 47 → family 52) is a small
perturbation within the same semantic neighborhood. An area change (e.g., area 3 → area 7)
is a structural flip: the text's dominant semantic region moved from one icosahedral area to
another. The `SHADOW_ACCEPTABILITY_GATE` treats area changes as disqualifying by default
(`SHADOW_ALLOW_AREA_FLIP = False`), while a family change within the same area does not
trigger gate failure on its own.

### Tier 2 — Quantitative deltas over L1 and L2 variables

All deltas are computed as `S − B` (shadow minus baseline). Positive = shadow produces higher
value; negative = shadow produces lower value.

**L1-derived deltas:**

| Variable | Formula | Meaning |
|---|---|---|
| `DOMINANT_FAMILY_DELTA_HITS` | hits_S[dom_S] − hits_B[dom_B] | Change in peak hit count (also affected by which family is dominant) |
| `DOMINANCE_RATIO_DELTA` | L1_S.DR − L1_B.DR | Change in fraction of mass in top family |
| `COVERAGE_RATIO_DELTA` | L1_S.CR − L1_B.CR | Change in attributed/total fraction |
| `UNIQUE_FAMILIES_HIT_DELTA` | L1_S.UF − L1_B.UF | Change in how many families received ≥ 1 hit |
| `AREA_SPREAD_DELTA` | L1_S.AS − L1_B.AS | Change in fraction of 12 areas touched |
| `ENTROPY_DELTA` | L1_S.H_norm − L1_B.H_norm | Change in normalized Shannon entropy |
| `GINI_DELTA` | L1_S.G − L1_B.G | Change in Gini concentration coefficient |
| `ALTITUDE_MEAN_DELTA` | L1_S.alt_mean − L1_B.alt_mean | Change in global mean altitude |
| `ALTITUDE_DOMINANT_DELTA` | L1_S.alt_dom − L1_B.alt_dom | Change in dominant-family altitude mean |
| `FAMILY_HIT_VECTOR_L1_DELTA` | L1_S.L1 − L1_B.L1 | Change in total attributed token count |

**L2-derived deltas:**

| Variable | Formula | Meaning |
|---|---|---|
| `TRAVERSAL_DEPTH_DELTA` | L2_S.depth − L2_B.depth | Change in how deep activation mass reaches from dominant |
| `REACHABLE_NODES_DELTA` | L2_S.nodes − L2_B.nodes | Change in size of reachable neighborhood |
| `MAX_DISTANCE_DELTA` | L2_S.max_dist − L2_B.max_dist | Change in BFS radius |
| `CROSS_AREA_RATIO_DELTA` | L2_S.CAR − L2_B.CAR | Change in fraction of traversal outside dominant area |
| `LOOP_DENSITY_DELTA` | L2_S.LD − L2_B.LD | Change in cycle density of the traversal subgraph |
| `EDGE_UTILIZATION_DELTA` | L2_S.EUR − L2_B.EUR | Change in tree-edge / induced-edge ratio |

The deltas are signed — their direction carries meaning. `ENTROPY_DELTA > 0` means the shadow
run produces a more diffuse activation pattern; `ENTROPY_DELTA < 0` means it concentrates more.
`TRAVERSAL_DEPTH_DELTA > 0` means the shadow run's dominant family reaches further into the
graph. These directionality signals allow downstream layers and guards to distinguish "shadow
produces a more concentrated reading" from "shadow produces a more diffuse one."

### Tier 3 — Set and vector similarity

**Jaccard similarity of BFS neighborhoods:**

```
VISITED_JACCARD_SIMILARITY = |visited_B ∩ visited_S| / |visited_B ∪ visited_S|
VISITED_SYMMETRIC_DIFFERENCE_RATIO = |visited_B Δ visited_S| / |visited_B ∪ visited_S|
  = 1 − VISITED_JACCARD_SIMILARITY
```

The Jaccard coefficient (Jaccard, 1901) is the canonical set similarity measure: it is 1.0
when both runs visited exactly the same families, and 0.0 when the two BFS neighborhoods are
completely disjoint. Its complement `VISITED_SYMMETRIC_DIFFERENCE_RATIO` directly answers "what
fraction of the total neighborhood is exclusive to one run" — the size of the region where the
two topology explorations disagree about reachability.

Jaccard is the right measure here (rather than e.g. recall or precision) because neither B nor
S is a "reference" — both are runs of the same system on perturbed input, and the question is
symmetric: how much do they agree?

**Cosine similarity of hit vectors:**

```
HIT_VECTOR_COSINE_SIMILARITY = (hits_B · hits_S) / (‖hits_B‖₂ × ‖hits_S‖₂)
```

Standard cosine similarity over the 288-dimensional hit count vectors. Cosine measures
*direction* not magnitude — two runs with identical relative family distribution but different
total counts will have cosine = 1.0. It is 0 when the two runs activate completely orthogonal
(non-overlapping) families. Cosine similarity of term-frequency vectors is the fundamental
retrieval-similarity measure from the Vector Space Model (Salton & McGill, 1983) — L3 applies
it to hit-count vectors rather than TF-IDF vectors, but the mathematical structure is identical.

**Top-K family overlap:**

```
TOP_K_OVERLAP_RATIO = |top10_B ∩ top10_S| / K       (K=10 by default)
```

Where `top_K_B` = the 10 families with highest hit counts in B (ties broken by hits desc then
family index asc). This answers the practically most important stability question: the top 10
families are the ones that will drive dominant-area selection, entropy, tension, and eventually
the USF fingerprint. Whether family #150 changed its hit count by 1 matters little; whether
family #12 (the dominant family's closest semantic neighbor) dropped out of the top-10 matters
a great deal. `TOP_K_OVERLAP_RATIO = 1.0` means the same 10 families dominate both runs —
the reading's semantically most active region is stable.

---

## The SHADOW_DEVIATION_SCORE and the gate

### The composite deviation score

```
SHADOW_DEVIATION_SCORE =
    0.35 × (1 − HIT_VECTOR_COSINE_SIMILARITY)
  + 0.35 × VISITED_SYMMETRIC_DIFFERENCE_RATIO
  + 0.30 × |DOMINANCE_RATIO_DELTA|
```

Weights sum to 1.00 (0.35 + 0.35 + 0.30). This is a convex combination of three deviation
signals, each independently normalized to [0,1]:

- **0.35 × (1 − cosine):** Angular divergence of the full 288-dim hit distribution. High
  when the two runs activate different families or the same families with very different
  relative weights. Captures global distributional shift.

- **0.35 × symmetric_diff_ratio:** Topological divergence of the traversal neighborhoods.
  High when BFS from each dominant family explores different sets of concepts. Captures local
  structural shift independent of global distribution.

- **0.30 × |dominance_ratio_delta|:** Change in how concentrated the dominant family is.
  High when the shadow perturbation either reinforces or weakens the dominant family's
  relative mass. Captures stability of the "winner" — the most semantically important signal.

**Why these three, and why these weights.** The three terms are designed to be partially
orthogonal:
- Low cosine but high Jaccard: the visit sets are similar but the hit distributions are
  angled differently (same families reachable, different relative weights)
- High cosine but low Jaccard: proportionally similar distributions but BFS explores different
  neighborhoods (the dominant family changed, pulling the traversal to a different region)
- Both stable but high |dominance_delta|: vector direction and neighborhood agree, but one run
  concentrates mass more tightly

No single measure captures all three failure modes. The 0.35/0.35/0.30 split gives cosine
and Jaccard equal weight because they are equally important structural integrity checks at
different scales (global vs. local), while dominance delta gets slightly less (0.30) because it
is partially already captured — a large dominance shift implies angular drift, which cosine
already penalizes.

### The gate

```python
SHADOW_ACCEPTABILITY_GATE = (
    SHADOW_DEVIATION_SCORE <= 0.25             # overall deviation within tolerance
    and |CROSS_AREA_RATIO_DELTA| <= 0.10       # topology doesn't flip cross-area profile
    and (not DOMINANT_AREA_CHANGED             # dominant area is stable
         or SHADOW_ALLOW_AREA_FLIP)            # unless explicitly allowed
)
```

Three conditions must ALL hold for the reading to be declared stable:

1. **Deviation ≤ 0.25:** The composite 3-signal score must stay below 25% of maximum
   deviation. This tolerates small perturbations (a 4% family weight shift producing a 5%
   overall structural divergence is acceptable) while rejecting large structural instabilities
   (a 4% family weight shift producing 40% structural divergence signals that the reading is
   at a decision boundary).

2. **Cross-area delta ≤ 0.10:** Even if the overall SDS is low, a change of more than 10
   percentage points in the cross-area traversal ratio is independently flagged. This targets
   a specific failure mode: the dominant concept's BFS neighborhood could shift from being
   mostly within one area to spanning multiple areas, which has direct consequences for which
   `bridge_weight` costs propagation pays. That topology flip can happen even when the cosine
   similarity is high — the same families are activated, but their BFS neighborhood crosses
   more area boundaries.

3. **No area flip (unless allowed):** `DOMINANT_AREA_CHANGED` is a categorical veto. A dominant
   area change means the text's structural center of gravity moved from one icosahedral area to
   another under 4% perturbation — it is sitting near an area-boundary saddle point. Such a
   reading is structurally ambiguous at the area level, and `SHADOW_ALLOW_AREA_FLIP = False`
   by default means this always fails the gate. The parameter exists for cases where cross-area
   ambiguity is expected and permissible (e.g., profiles that explicitly span two areas).

**What gate failure means downstream.** `SHADOW_ACCEPTABILITY_GATE = False` propagates into
the pipeline state and is available to guards and interpretation. It does not abort the pipeline
— the run continues and produces all subsequent layer outputs — but it flags that the reading
is structurally fragile. A guard or interpretation rule can use this flag to escalate the output
to WARN or REVIEW rather than ALLOW.

---

## What L3 is in conceptual terms

L3 is **perturbation analysis built into the pipeline as a first-class layer.** It answers
"how far are we from a structural phase transition?" — a phrase from physics that captures
exactly what SHADOW_ACCEPTABILITY_GATE is checking. In a physical system, a phase transition
is where a small change in input causes a qualitative change in output (solid → liquid, ordered
→ disordered). In Hesperia's semantic space, a "phase transition" is a reading that flips
dominant area or develops a very different activation topology under a small perturbation.

The equivalent in classical statistics is a **influence function** (Hampel, 1974): a measure
of how much the statistical estimate changes when one observation is slightly perturbed. L3
does influence-function-style analysis not on a single observation but on the full structural
reading — measuring how much the structural conclusions shift when the attribution weights
shift by k_shadow_perturb = 0.04.

The equivalent in machine learning is **adversarial robustness analysis** or **input
sensitivity** — checking whether a model's output is stable near the input point. L3 is the
deterministic, pre-LLM version of this for structural readings.

---

## Scientific lineage

| Tool | Origin | L3 use |
|---|---|---|
| **Jaccard similarity coefficient** | Jaccard (1901) "Étude comparative de la distribution florale" — botanical species set overlap | `VISITED_JACCARD_SIMILARITY`: set-level comparison of BFS neighborhoods |
| **Cosine similarity** | Salton & McGill (1983) *Introduction to Modern Information Retrieval*; foundational in VSM/TF-IDF retrieval | `HIT_VECTOR_COSINE_SIMILARITY`: direction-preserving comparison of 288-dim hit vectors |
| **Top-K overlap / recall@K** | Standard in information retrieval evaluation (Rijsbergen, 1979 *Information Retrieval*) | `TOP_K_OVERLAP_RATIO`: stability of the 10 most-activated families |
| **Sensitivity / perturbation analysis** | Standard engineering and numerical analysis; influence functions: Hampel (1974) "The influence curve and its role in robust estimation" | The B/S dual-run architecture: run twice with slight perturbation, measure divergence |
| **Convex combination scoring** | Classical operations research / multi-attribute decision theory (Keeney & Raiffa, 1976) | `SHADOW_DEVIATION_SCORE = 0.35w₁ + 0.35w₂ + 0.30w₃`, weights summing to 1.0 |

---

## Governance parameters in L3

| Parameter | Default | Role |
|---|---|---|
| `SHADOW_MAX_DEVIATION` | 0.25 | Maximum acceptable SHADOW_DEVIATION_SCORE |
| `SHADOW_MAX_CROSS_AREA_DELTA` | 0.10 | Maximum acceptable |CROSS_AREA_RATIO_DELTA| |
| `SHADOW_ALLOW_AREA_FLIP` | False | Whether dominant area change is permitted |
| `TOP_K` | 10 | Number of top families compared in overlap ratio |
| `k_shadow_perturb` | 0.04 | Perturbation magnitude (in attribution code, not L3 itself) |

These are governance parameters, not mathematical constants. They can be tuned per-profile
or per-deployment — a more permissive deployment (e.g., early exploratory analysis)
might set `SHADOW_MAX_DEVIATION = 0.40`; a clinical-grade deployment might tighten it to 0.15.
The math inside L3 is invariant to these choices; only the gate threshold changes.

---

## Relationship to neighboring layers and corners

- **L1, L2:** L3 consumes their complete outputs for both B and S runs. All 16 delta variables
  are direct arithmetic differences of L1/L2 variables — L3 adds no new measurement concepts,
  only comparisons between two instances of the measurements L1 and L2 already defined.
- **L4–L6:** Receive L3's output including `SHADOW_ACCEPTABILITY_GATE`, which they can treat
  as a stability flag for their own computations.
- **Guards (Sigma, Gamma, Theta):** `SHADOW_ACCEPTABILITY_GATE = False` is a signal available
  to Theta governance decisions — a structurally fragile reading is more likely to be escalated.
- **`corners/shadow_correction.md`:** The shadow *correction* (L8, applied to propagation output)
  is a different concept from the shadow *comparison* in L3. L3 compares B and S attribute
  runs; L8 applies energy-domain corrections based on shadow propagation. The word "shadow"
  is used for both, but the mechanisms are distinct: L3 is a pre-propagation robustness check;
  L8 is a post-propagation entropy/dominance correction.
- **`corners/core_math_contract.md`:** `perturb_shadow` (the function that generates `hits_S`)
  is defined in `core/math/core_math.py` with `k_shadow_perturb = 0.04`. The perturbation
  formula is: `v'[i] = abs(v[i] × (1 + 0.04 × ((i×7)%11 − 5)/5))` — a modular-arithmetic
  deterministic jitter, not a random sample.

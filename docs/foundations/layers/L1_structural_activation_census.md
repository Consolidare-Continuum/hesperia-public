# Layer 1 — Structural Activation Census (`core/layers/layer_1.py`, 34_SPEC)

**Position in pipeline:** The first executable layer. Receives the output of the attribution
pipeline (`core/attribution/structural.py`) and produces a 27-variable structural census of
the input text's concept activation pattern. Nothing else in the pipeline runs before this.
No LLM, no propagation, no guards — only deterministic arithmetic over the attribution result.

**Spec origin:** `34_SPEC` (base 25 variables) + `34_SPEC N1` (6 profile variables). The
module docstring states: *"25 variables base; when profile supplied, adds FPD, APD, FMP,
ALTD, BVS, PCS. Deterministic, input-bound. No LLM, no shadow, no books."*

---

## What feeds into L1: the attribution pipeline

L1 does not touch raw text. By the time `layer_1.run()` is called, the pipeline runner
(`sphere/pipeline/pipeline_runner.py`) has already executed:

```
raw_text
  → normalize()          # NFKC, lowercase, whitespace collapse, hard cap (10,000 chars)
  → tokenize()           # whitespace split + punctuation strip (fixed ASCII set)
  → attribute(tokens, dict_a, dict_b)   # exact Dict A match → (familyGlobal, altitude)
                                         # fallback to Dict B → (familyGlobal, 0.5)
  → matched: list[(familyGlobal: int, altitude: float)]
```

The `matched` list is L1's actual input — a sequence of `(family_index, altitude)` pairs,
one per attributed token, ordered as the tokens appear in the text. Unattributed tokens
(no Dict A or Dict B match) are absent from `matched` entirely.

**The altitude signal.** Each Dict A entry carries a `familyGlobal` (0–287) and an
`altitude` (0.0–1.0), both set at lexicon-build time and frozen. Altitude is a per-concept
property of the controlled vocabulary — it encodes how domain-specific or semantically
precise a concept is within the TFP lexicon. Dict B fallback matches receive a fixed
`default_altitude_b = 0.5` (mid-scale, indicating neither precise nor noise). The altitude
domain is globally invariant: `ALT_MIN = 0.0`, `ALT_MAX = 1.0`, `ALT_NORM = 1.0`. L1
never infers or modifies altitudes — it only aggregates what the lexicon assigned.

**The region seed relationship.** `core/attribution/structural.py`'s `region_seed` formula
(`τ(side) = base_weight × hitDensity_F × (1 − meanAltitude_F)`) uses L1's altitude
aggregate in reverse: high-altitude (domain-specific) families produce lower seed weights
because their concepts are precisely positioned and do not need broad diffusion from a
seeding standpoint. Low-altitude (generic, ambiguous) families seed more broadly. This
is the pre-L2 mechanism by which lexical precision constrains propagation reach before
the diffusion engine runs.

---

## The 27 base variables and their formulas (34_SPEC)

Let:
- `total_tokens` = count of all tokens after normalization/tokenization
- `hits[f]` = number of attributed tokens landing in family `f` (f ∈ 0..287)
- `attributed` = Σ hits[f] = total attributed token count
- `altitude_sum[f]` = Σ altitude for each token landing in family `f`
- `F = 288`, `A = 12`, `fpa = F // A = 24`, `ε = 1e-9`

### Group 1 — Attribution yield

| Variable | Formula | Meaning |
|---|---|---|
| `TOTAL_TOKENS` | len(tokens) | Raw token count after normalization |
| `ATTRIBUTED_TOKENS` | Σ hits[f] | Tokens that matched a concept in Dict A or B |
| `COVERAGE_RATIO` | attributed / total_tokens | Fraction of text "legible" to the vocabulary |

`COVERAGE_RATIO` is the most fundamental signal of lexical alignment: a ratio near 1.0 means
the text uses the system's controlled vocabulary almost entirely; a ratio near 0 means the text
is speaking in language the vocabulary does not recognize. This is not a quality judgment —
clinical text from a different terminology domain would score low even if it is scientifically
sound, and colloquial paraphrase of TFP ideas might score low because the surface forms don't
match the lexicon. It is a measurement of vocabularly overlap, nothing else.

### Group 2 — Family-level distribution

| Variable | Formula | Meaning |
|---|---|---|
| `UNIQUE_FAMILIES_HIT` | count(f : hits[f] > 0) | How many of 288 families received ≥ 1 hit |
| `FAMILY_ACTIVATION_DENSITY` | unique_families / F | Fraction of the semantic space touched |
| `FAMILY_HIT_VECTOR_L1` | Σ hits[f] = attributed | L1 norm of the hit vector (total mass) |
| `FAMILY_HIT_VECTOR_L2` | √(Σ hits[f]²) | L2 norm — penalizes concentration |
| `MAX_FAMILY_HITS` | max(hits) | Peak activation count |
| `DOMINANT_FAMILY_ID` | argmax hits (first-max, lowest index tie-break) | Index 0–287 of top family |
| `DOMINANT_AREA_ID` | dominant_family // 24 | Which of 12 icosahedral areas holds the dominant family |
| `DOMINANCE_RATIO` | max_hits / (attributed + ε) | Fraction of all attributed mass in the single top family |
| `SECONDARY_FAMILY_RATIO` | second_max / (max_hits + ε) | Runner-up vs. top — how contested the peak is |
| `SIGNAL_TO_NOISE_RATIO` | max_hits / (attributed − max_hits + ε) | Dominant mass vs. all other mass |
| `SPARSITY_INDEX` | 1 − family_activation_density | Complement of density — what fraction of space is dark |
| `TOKEN_REDUNDANCY_RATIO` | 1 − (unique_families / (attributed + ε)) | Repetition rate in attributed hits |

**Why L1 and L2 norms of the same vector.** The L1 norm (sum of absolute values) simply
counts total attributed tokens — it is the mass. The L2 norm squares each component before
summing, making it sensitive to how concentrated the mass is: two texts with the same number
of attributed tokens will have different L2 norms if one concentrates all hits in one family
and the other spreads them evenly. L2 is higher for concentrated distributions. The ratio
L2/L1 is therefore an implicit concentration index (higher = more concentrated), usable by
downstream layers without computing a separate concentration variable.

**SECONDARY_FAMILY_RATIO and SIGNAL_TO_NOISE_RATIO are complementary.** SFR asks "how far
behind the runner-up is" (a ratio close to 1.0 = two nearly-equal peaks = contested signal).
SNR asks "how much bigger is the top family than everything else combined" (SNR >> 1 = strong
isolated signal, SNR ≈ 0 = dominant family barely above background). Together they characterize
the shape of the concentration: high SFR + low SNR = two nearly-equal competitors above a
flat background; low SFR + high SNR = one clear winner with a flat remainder.

### Group 3 — Information-theoretic measures

| Variable | Formula | Meaning |
|---|---|---|
| `FAMILY_ENTROPY` | −Σ p_f log(p_f), p_f = hits[f]/(attributed+ε) | Shannon entropy of the family distribution |
| `NORMALIZED_FAMILY_ENTROPY` | min(1, H / log(F)) | H normalized to [0,1] by theoretical maximum log(288) |
| `GINI_COEFFICIENT` | 1 − (2/(n·total)) · Σ (n−i)·sorted_hits[i] | Gini inequality index over the hit distribution |

**Shannon entropy** (Shannon, 1948) is the correct information-theoretic measure for "how
spread out is the probability mass." Maximum entropy (H_max = log(288) ≈ 5.66 nats) is
achieved when every family receives exactly the same number of hits — a perfectly uniform,
fully diffuse activation. Minimum entropy (H = 0) is achieved when all attributed tokens
land in a single family. NORMALIZED_FAMILY_ENTROPY maps this to [0,1] using the same
normalization as `P_disp` in the Core Math Contract — the sphere's F=288 families set the
normalization ceiling here at L1, before any diffusion has occurred.

`NORMALIZED_FAMILY_ENTROPY` feeds the facts dict for the logic layer's `structural_monotony`
rule: `if entropy < 0.35, the discourse is structurally narrow.` The 0.35 threshold is a
calibrated gate, not a mathematical constant — but the variable it gates on (NORMALIZED_FAMILY_ENTROPY
at L1) is the pre-propagation, raw-attribution entropy, representing the text's own semantic
spread before the diffusion engine operates on it.

**Gini coefficient** (Gini, 1912) was developed to measure income inequality and is now a
standard tool in any distribution-characterization problem. In L1 it serves a complementary
role to entropy: entropy is maximized by a uniform distribution and measures spread; the
Gini coefficient is 0 for a uniform distribution and measures inequality/concentration.
Both identify "how concentrated is the activation," but from different mathematical angles:
entropy is log-weighted (highly sensitive to the presence of small probabilities), while
Gini is based on the rank-ordering of values (linear in the sorted array). In practice they
correlate, but a high-entropy text with many equally-small activations will have lower Gini
than a text where the same entropy comes from two large peaks — the two measures behave
differently at the tails.

### Group 4 — Area-level rollup

| Variable | Formula | Meaning |
|---|---|---|
| `UNIQUE_AREAS_HIT` | count(a : Σ_{f in area a} hits[f] > 0) | How many of 12 icosahedral areas received ≥ 1 hit |
| `AREA_SPREAD` | unique_areas / A | Fraction of the 12-area sphere activated |
| `AREA_DOMINANCE_RATIO` | hits_in_dominant_area / (attributed + ε) | Fraction of attributed mass in the dominant area |

The area-level variables are a coarse-grained parallel to the family-level variables — the
same concentration/spread logic applied one level up the geometry. `AREA_SPREAD` is used
in profile budget-cap checks (`MIN_AREA_SPREAD`). `AREA_DOMINANCE_RATIO` directly reflects
the icosahedral structure: if one of the 12 areas dominates, it means the text is semantically
concentrated in one twelfth of the sphere's semantic surface, which in TFP terms corresponds
to a specific clinical domain cluster.

### Group 5 — Altitude signal

| Variable | Formula | Meaning |
|---|---|---|
| `MEAN_ALTITUDE_GLOBAL` | Σ altitude_sum[f] / (attributed + ε) | Average altitude across all attributed tokens |
| `MEAN_ALTITUDE_DOMINANT` | altitude_sum[dominant_family] / (hits[dominant] + ε) | Altitude mean within the top family |
| `ALTITUDE_VARIANCE_GLOBAL` | Σ hits[f]·(mean_alt[f] − mean_alt_global)² / (attributed + ε) | Weighted variance of per-family altitude means |
| `ALTITUDE_WEIGHTED_MASS` | Σ_{f: hits[f]>0} hits[f] · mean_alt[f] | Total hit mass weighted by each family's mean altitude |

Altitude aggregation is a weighted statistics problem. `mean_alt[f] = altitude_sum[f] /
(hits[f] + ε)` is the per-family mean altitude, computed over all tokens attributed to that
family. `ALTITUDE_VARIANCE_GLOBAL` is the weighted variance of those per-family means around
the global mean — a measure of how consistently altitude is distributed across the activated
families. High variance means some families received high-altitude hits and others low-altitude
hits; low variance means the altitude level is consistent across the activation pattern.

`ALTITUDE_WEIGHTED_MASS` is the L1-norm-analog weighted by altitude: it counts the total
"altitude-adjusted" activation mass, giving more weight to high-altitude (more domain-specific)
hits and less to generic (low-altitude) hits. It is the most direct signal of how much of the
attributed mass came from the high-quality, domain-specific part of the vocabulary.

### Group 6 — Composite stability

| Variable | Formula | Meaning |
|---|---|---|
| `STRUCTURAL_STABILITY_INDEX` | DOMINANCE_RATIO × (1 − NORMALIZED_FAMILY_ENTROPY) | Joint signal of concentration AND coherence |

`SSI = D × (1 − H_norm)` is the product of two independent signals:
- `D` = DOMINANCE_RATIO: how concentrated the mass is in the top family
- `(1 − H_norm)`: how non-entropic (how ordered) the overall distribution is

SSI is high when the distribution is both concentrated (one family dominates) AND ordered
(low background entropy). It is lower when concentration is high but background entropy is also
high (dominant family is large, but many other families also fire — a noisy reading). It approaches
zero whenever either factor approaches zero: a diffuse text (D low) or a maximally disordered text
(H_norm → 1) both give SSI → 0, and for different structural reasons. This makes SSI a genuinely
composite signal that neither DOMINANCE_RATIO nor NORMALIZED_FAMILY_ENTROPY alone could provide —
it is the synergy documented in `parameter_synergies.md`'s section on how two variables can jointly
produce meaning that neither gives alone.

---

## Profile mode — 34_SPEC N1 (6 additional variables)

When a `StructureProfile` is supplied with the run, L1 computes six additional variables measuring
how far the current text's activation pattern deviates from a reference (expected) distribution.

**The profile as a reference distribution.** A `StructureProfile` contains:
- `FEDV[f]` — Family Expected Distribution Vector: a 288-dim probability vector encoding the
  expected fraction of attributed tokens per family for a given profile (e.g., "mid-stage TFP
  session with dominant transference focus").
- `AEDV[a]` — Area Expected Distribution Vector: a 12-dim probability vector encoding the
  expected area distribution.
- Optional: `DENY_FAMILIES` (set of family indices that must not receive activation), `ALT_BAND`
  or `ALT_TARGET` (expected altitude range/target), and governance caps (`MAX_AREA_DOMINANCE`,
  `MAX_FAMILY_DOMINANCE`, `MIN_AREA_SPREAD`, `MIN_COVERAGE_RATIO`).

### Profile deviation variables

| Variable | Formula | Meaning |
|---|---|---|
| `FAMILY_PROFILE_DEVIATION (FPD)` | clamp01(‖P − FEDV‖₂ / √2) | L2 distance from observed to expected family distribution |
| `AREA_PROFILE_DEVIATION (APD)` | clamp01(‖Q − AEDV‖₂ / √2) | L2 distance from observed to expected area distribution |
| `FORBIDDEN_MASS_PENALTY (FMP)` | Σ_{f∈DENY} hits[f] / attributed | Fraction of attributed mass in prohibited families |
| `ALTITUDE_DEVIATION (ALTD)` | clamp01(excess_above_band / 1.0) | Distance from altitude outside the ALT_BAND or ALT_TARGET |
| `BUDGET_VIOLATION_SCORE (BVS)` | max(individual cap violations) | Single worst governance-cap breach, not averaged |
| `PROFILE_CONFORMANCE_SCORE (PCS)` | 1 − clamp01(weighted_penalty / weight_sum) | Overall conformance: 1.0 = perfect, 0.0 = total deviation |

**Why L2 distance for FPD and APD, not KL divergence.** KL divergence (`D_KL(P ‖ Q) = Σ P_f log(P_f/Q_f)`)
is unbounded (if any FEDV[f] = 0 but P[f] > 0, KL diverges to +∞), asymmetric (D_KL(P‖Q) ≠
D_KL(Q‖P)), and uncomputable as a finite number when the support does not match. L2 distance is
symmetric, bounded (maximum √2 for two probability vectors of opposite mass), and defined for any
pair of distributions regardless of support overlap. Normalizing by √2 brings FPD into [0,1].
This is an explicit engineering choice for deterministic, always-finite measurement — the same
"computable and bounded" principle that chose Shannon entropy over Kolmogorov complexity
(`provenance.md`).

**Why BVS uses max, not mean.** BVS is `max(violations)` — the L∞ norm of the violation vector.
A governance cap (e.g., `MAX_AREA_DOMINANCE = 0.6`) is a hard constraint: exceeding it by any
amount is a breach, and a single breach is as governance-significant as many simultaneous breaches
from a downstream consumer's perspective. Averaging multiple violations would allow several small
cap breaches to cancel a large one, which is precisely the wrong behavior for a governance signal.
The L∞ norm is the mathematically correct choice when "single worst" is what matters.

**PCS as a weighted metric-space distance.** `PCS = 1 − clamp01(pen / weight_sum)` where
`pen = w_f·FPD + w_a·APD + [w_forbid·FMP] + [w_alt·ALTD] + [w_budget·BVS]`. This is a
weighted L1 combination of sub-deviations, each pre-normalized to [0,1], with weights
specified by the profile (defaults 1.0 for all active terms). PCS = 1.0 means zero total
penalty across all deviation dimensions simultaneously; PCS = 0.0 means the total weighted
penalty equals or exceeds the total weight (complete structural non-conformance). The weight
parameters allow a profile to express priorities: a profile where altitude matters critically
sets `w_alt` high; a profile where area spread matters more than family-level deviation sets
`w_area > w_family`. This is a structured multi-attribute deviation model, not a single score.

**Deterministic empty case.** When `attributed == 0` (no tokens matched anything), L1 returns
`FPD = 1.0, APD = 1.0, PCS = 0.0` without attempting any division. This branch is guarded
explicitly in the code and produces defined, finite outputs regardless of FEDV/AEDV content —
the system is always runnable even on texts that are entirely outside the controlled vocabulary.

---

## What L1 produces that downstream layers consume

L1 does not write into a shared mutable state. Each layer receives its predecessor's output via
`PipelineState.layers[layer_id]`. The table below shows what L1 variables are explicitly consumed
by which downstream stages:

| L1 variable | Consumed by | How |
|---|---|---|
| `DOMINANT_AREA_ID` | Pipeline runner | `area_sequence = [f // 24 for f in family_sequence]`; also facts dict |
| `DOMINANT_FAMILY_ID` | Pipeline runner, USF assembly | `detect_dominant_family`, `raw_metrics` |
| `NORMALIZED_FAMILY_ENTROPY` | Logic layer (facts dict) | `structural_monotony` rule threshold: entropy < 0.35 |
| `COVERAGE_RATIO` | Logic layer (facts dict) | Coverage-based rule evaluation |
| `hits` (from `matched`, pre-L1) | Propagation engine | `compute_propagation(area_vector, list(hits), ...)` |
| `area_vector` (derived from hits) | Propagation, shadow, USF | All area-level downstream metrics |
| Entropy, tension, coverage | Sphere metrics (USF assembly) | `compute_entropy`, `compute_structural_tension`, `compute_family_coverage` |

The `hits` vector (288-dim) is the primary structural artifact. L1 does not transform it —
it counts into it and measures from it. The hits vector passes through to L2–L9 essentially
unchanged, with each subsequent layer adding transformations (propagation, shadow correction,
logic evaluation) on top of it. L1's role is to characterize the vector before any of that
happens.

---

## Scientific lineage of L1's toolkit

All tools L1 applies are pre-LLM and pre-deep-learning; the era-of-origin matters because L1
was designed to be an information-theoretic witness that cannot be confused with a learned model.

| Tool | Origin | L1 use |
|---|---|---|
| **Shannon entropy** H = −Σ p log p | Shannon (1948), "A Mathematical Theory of Communication" | FAMILY_ENTROPY, NORMALIZED_FAMILY_ENTROPY — measures how spread or concentrated the concept attribution is |
| **Gini coefficient** G = 1 − (2/n·Σ) · rank_sum | Gini (1912), "Variabilità e mutabilità" | GINI_COEFFICIENT — measures inequality in the hit distribution, independently of entropy |
| **L1/L2 vector norms** ‖x‖₁ = Σ|xᵢ|, ‖x‖₂ = √Σxᵢ² | Classical linear algebra (Hilbert, Minkowski, early 20th century formalizations) | FAMILY_HIT_VECTOR_L1 (total mass), FAMILY_HIT_VECTOR_L2 (concentration-sensitive mass), FPD/APD distances |
| **Signal-to-noise ratio** SNR = signal / noise | Communications theory; formalized by Shannon (1948) in channel capacity | SIGNAL_TO_NOISE_RATIO: dominant family mass vs. background |
| **Weighted mean and variance** | Classical descriptive statistics | MEAN_ALTITUDE_GLOBAL, ALTITUDE_VARIANCE_GLOBAL: altitude aggregated across hits |
| **L2 distance between probability distributions** | Standard metric in statistics (Euclidean distance on the probability simplex) | FPD, APD: L2 distance from observed to expected, normalized by √2 (max possible) |
| **L∞ norm** max(violations) | Classical linear algebra / Chebyshev norm | BVS: single worst governance breach |

The one non-classical element in L1 is `STRUCTURAL_STABILITY_INDEX = D × (1−H_norm)` — a
Hesperia-native composite that has no direct external citation. It is the product of two
classical components (concentration ratio and complement-of-entropy) but the product formula
itself is not borrowed from a named framework. It is recorded here as Hesperia-native, not
falsely attributed elsewhere (same audit discipline as `provenance.md`'s Sigma/Gamma/Theta
finding).

---

## What L1 is not

**Not a classifier.** L1 produces continuous measurements, not class labels. The only L1 output
that approaches categorical is `DOMINANT_FAMILY_ID` and `DOMINANT_AREA_ID` — integer indices.
These are the result of argmax (a deterministic operation), not a learned decision boundary.

**Not a propagation step.** All L1 outputs measure the raw attribution before any diffusion
across the hex/family/area graph. The hits vector at L1 exit is the un-diffused, un-smoothed
direct-attribution count. Propagation begins at L7 (`sphere/propagation/engine.py`).

**Not a guard.** L1 produces no verdicts, no PASS/FAIL, no ALLOW/BLOCK. Guard verdicts
(Sigma/Gamma/Theta) run after L1–L9 are complete. L1's entropy and coverage metrics feed
the logic rules (L9) that in turn inform guards, but L1 itself has no gating authority.

**Not an LLM call.** The module docstring's own statement: *"No LLM, no shadow, no books."*
This layer is a pure mathematical census of the attribution output — it can run identically in
any environment that has the attribution result, with no network, no model, no stochastic process.

---

## Relationship to neighboring layers and corners

- **Pre-L1 (`core/attribution/structural.py`):** produces `matched`. L1 is a pure consumer of
  `matched` — it never modifies or re-derives attribution. If `matched` changes, all L1 outputs
  change deterministically.
- **L2–L6 (depth layers):** L1 outputs (via `PipelineState`) are available as context for all
  subsequent layers. The `hits` vector is the most-used handoff.
- **L7 propagation:** reads the raw `hits` vector and `area_vector` derived from it —
  the pre-diffusion distribution L1 characterized.
- **L9 logic layer:** consumes L1's entropy and coverage directly from the facts dict.
- **`corners/core_math_contract.md`:** L1 uses the same Shannon entropy formula as `P_disp`
  in the Core Math Contract. Both use H_norm = H / ln(M) normalization (here M=F=288; there
  M = active sides at end of propagation). The tool is consistent system-wide.
- **`corners/geometry_math_coupling.md`:** `FAMILY_ACTIVATION_DENSITY` (unique_families/288)
  and `AREA_SPREAD` (unique_areas/12) are the L1-layer realization of the geometry's two-level
  structure: 288 = 12×24, and these two measures check spread at each level independently.
- **`parameter_catalog.md`:** F=288, A=12, eps=1e-9, ALT_MIN/MAX are all fixed constants
  catalogued there. The 0.35 entropy threshold for `structural_monotony` is in
  `specs/canon/diagnostic_rules.yaml`, cited in `corners/logic_guards.md`.

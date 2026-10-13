# Hesperia: a downward trace from the V7 roof to the foundation stone

This document reads the system top-down, the way you'd read a cross-section of a
castle: start at what is standing today, ask what forced each layer beneath it
into existence, and keep descending until you hit bedrock (the first commits).
It is reasoning documentation, not a changelog — for "what changed when," see
`eras/`; for "why does this corner of the architecture need to exist at all,"
see `corners/`. This file is the connective narrative between them.

The throughline, stated once so it doesn't need restating in every section:
**Hesperia exists to convert language into bounded, falsifiable, replayable
structure, and only then let an LLM speak.** Every layer below is either (a) a
mechanism for making that conversion deterministic, or (b) a mechanism for
proving, after the fact, that determinism wasn't violated. Nothing in the
system earns its keep unless it serves one of those two jobs.

If you came here from buyer-language or productization wording such as
`accountable AI`, `deterministic validation`, or `evidence-grade audit trace`,
read this file for the architectural why, then route outward to
`docs/publication/UPCELERATOR_PRODUCTIZATION_QA.md` and `docs/iso/OPERATOR_GUIDE.md` for the dated
commercial vocabulary and the actual product surface those phrases point at.

---

## Roof: the V7 router (unsealed, current working tree)

**What existed before:** a fully deterministic L1–L10 sphere pipeline
(topology → propagation → shadow correction → logic rules → Prolog inference
→ guards → interpretation state → USF) that produced *measurements* —
activation vectors, structural states, rule triggers, guard verdicts — but no
natural-language output, and a mature dev/prod sealed-release split (0.6.x)
with no single registry for what "distance" meant across its three separately
matured geometries (area sphere, hex graph, family graph).

**What gap forced the jump:** a measurement instrument is not a product
end-state if a consumer (clinician, operator, or another model) needs prose,
not vectors. But handing an LLM the raw pipeline dict and asking it to "narrate
it" reintroduces everything Hesperia was built to eliminate: the LLM could
silently invent transitions, contradict guard verdicts, or attend to the wrong
evidence. Separately, three independently-matured notions of "distance" had
accumulated with no shared vocabulary forcing a caller to say which one was
meant — `docs/DOC_INDEX.md` names this directly ("Bare 'KSI' in runtime docs
is ambiguous — always qualify").

**What got added:** `sphere/fpf_bridge/` (Layer 11) — a pure, read-only
consumer that translates pipeline output into a bounded state machine (5
structural states, 13 evidence-gated transitions, 8 gates, pre-evaluated
Sigma/Gamma/Theta guards as closures, 7 propositional logic rules using all 6
operators). The LLM is handed `bridge_to_llm_prompt()` output — a fixed menu of
legal next states and the evidence for each — and can only narrate inside that
menu. Alongside it, a `metric_layer` registry and frozen `anchor_map_v1`
disambiguate every distance claim in the system, gated behind env flags that
default off. See `specs/canon/fpf_bridge_v7.md`, `corners/fpf_bridge.md`,
`corners/metric_registry.md`.

**Why this was the minimal right move:** the bridge adds zero new computation
and zero new measurement. It is a *projection* of facts the sphere already
proved, into a shape an LLM-reasoning substrate (fpf-thinking-map) can
traverse. The "no-modification guarantee" (bridge never touches sphere code)
is the load-bearing constraint — it keeps the new layer from becoming a second,
competing source of truth. The metric registry is likewise a thin service over
geometry that already existed since v0.4/v0.5 — a registry, not a redesign. The
unresolved gaps (`fpf_bridge_v7_deep_learning_gaps.md`: attention extraction,
learned embeddings, RL reward signal) are explicitly deferred rather than
built speculatively — each is real but none is required for the bridge to be
coherent on day one. Neither wave required reopening Sigma, Gamma, Theta, the
resolver, or the hex substrate, which is why this era is unsealed but not
unstable: `VERSION.yaml` still reads `0.6.0` because the seal discipline
(established two eras down) correctly hasn't certified it yet.

→ [`corners/fpf_bridge.md`](corners/fpf_bridge.md), [`corners/metric_registry.md`](corners/metric_registry.md),
[`eras/06_metric_wave_v0.7.0.md`](eras/06_metric_wave_v0.7.0.md), [`eras/07_v7_router_fpf_bridge.md`](eras/07_v7_router_fpf_bridge.md)

### Roof, continued: fpf_bridge v7.2–v7.4 (2026-07-04, specs drafted, Phase-1 code shipped, Ethan ratification pending)

**What existed before:** Layer 11's evidence surface exposed only 7 signal types (5 rule types,
raw area activations, one stability score) out of roughly 239 L1–L9 variables + 41 KME metrics + 3
TRIZ export families the sealed pipeline already computes — the vast majority of what Hesperia
measures never reached the LLM at all. Separately, the only LLM consumer was Hesperia's own
internal, single-shot, server-side call (`mode="llm"`) — no path existed for an external agentic
caller (Cursor, or any tool-using LLM) to receive the bridge state and reason over it directly.

**What gap forced the jump:** widening the evidence surface without a plan risks recreating the
"raw dump" problem the bridge exists to avoid, and handing an external agent the bridge state
without a stateless, read-only-by-default design risks reopening the same non-determinism the
sealed core exists to prevent. Both needed a spec before code, same discipline as every prior wave
in this file.

**What got added:** three specs (`specs/canon/fpf_bridge_v7_2_evidence_expansion.md`,
`..._v7_3_agentic_cursor_interface.md`, `..._v7_4_cobalt_corpus_scaleup.md`), scoped to COBALT+TFP
only (MRT explicitly excluded — closed MVP, different grid). v7.2 inventories every unexposed
variable and ships Phase 1–4 code (contradiction evidence + a block-labeled logic rule, the L7
trust trio, L4 evidence support, KME's 6 primitives, TRIZ's Policy Contradiction Detector) —
**correcting itself mid-build**: KME and TRIZ are both general-purpose Hesperia mechanisms, not
TFP-/COBALT-exclusive, and the first draft wrongly defaulted their evidence to a branch-scoped
context. v7.3 adds `runtime/agentic_bridge/` — `get_hesperia_bridge_state` (read-only, proven never
to call an LLM API) and `attempt_hesperia_transition` (validation only, real gold tests proving the
actual `ABSTAIN`/`COLLECT_EVIDENCE` outcome space rather than a `BLOCK` case the installed
`fpf-thinking-map` version can't yet produce — a correction found by reading the library source
directly rather than trusting the original spec draft). v7.4 names COBALT's own exit audit's
"pilot, not production" gap explicitly (25 attributed documents and a 10-query eval against a
1,286,742-chunk corpus) and ships a conservative `branch` classifier plus a reusable eval harness,
both synthetic-tested, neither yet run against the real corpus.

**Why this was the minimal right move:** every addition is read-only against `sphere/`, defaults
off behind its own env flag, and stops exactly at the boundary between "code Felix can write and
test against synthetic input" and "decisions that need Ethan, Sophia, Abelard, Colombo, or Olga" —
the same boundary every prior wave in this file respects, just drawn explicitly this time because
three specs and three different owners' worth of open work made it necessary to write down rather
than assume.

→ [`specs/canon/fpf_bridge_v7_2_evidence_expansion.md`](../../specs/canon/fpf_bridge_v7_2_evidence_expansion.md),
[`specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md`](../../specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md),
[`specs/canon/fpf_bridge_v7_4_cobalt_corpus_scaleup.md`](../../specs/canon/fpf_bridge_v7_4_cobalt_corpus_scaleup.md),
[`eras/08_fpf_bridge_v7_2_v7_4.md`](eras/08_fpf_bridge_v7_2_v7_4.md)

---

## `0.6.x`: the sealed runtime line and the public/prod split

**What existed before:** the v0.5.x Engine Dynamics line (below) had built out
calibration, topology, and the contradiction-tracking subsystem, with a
per-release sealed-audit-bundle habit, but no single document yet defined what
a release artifact may and may not contain, and the codebase had not yet split
a public-facing line from the internal dev/research line holding corpus and
calibration-dictionary payloads.

**What gap forced the jump:** `release/v0.6.0/RELEASE_SCOPE.md` states it
directly: "Ship the existing engine as-is. Do not ship calibration dict
payloads. Do not ship corpus payloads." Without an explicit scope boundary, a
sealed release could silently include proprietary research material that was
never meant to be portable, and every cosmetic dev-only change (a new research
note) would force a re-seal of the production artifact for no architecturally
relevant reason.

**What got added:** `VERSION.yaml` as a single source of truth (per-component
versions, pinned calibration dict pack), `EXTENSION_STATUS.yaml` classifying
extensions by product surface (`none`/`internal`/`optional`), a corpus-safe CI
verifier, the `0.6.0-sealed` CI hardening pass, and the
`hesperia/rollback-line-20260518` / `hesperia/dev-ready-line-20260518` named
checkpoint pair. `hesperia-0.6.3` ships a fully data-free, runnable archive —
proof the engine's logic and its proprietary data are genuinely separable.

**Why this was the minimal right move:** the seal process doesn't add new
semantics — it adds *evidence* that existing semantics didn't drift, and the
public/prod split applies the same drift-prevention discipline to data instead
of code. That is exactly the minimum a deterministic system needs once it has
external consumers and proprietary training/calibration material to protect.

→ [`corners/release_governance.md`](corners/release_governance.md), [`corners/release_seal.md`](corners/release_seal.md),
[`eras/04_v0.5.8_contradiction_track.md`](eras/04_v0.5.8_contradiction_track.md), [`eras/05_sealed_0.6.x.md`](eras/05_sealed_0.6.x.md)

---

## `hesperia-engine-dynamics-v0.5.x`: calibration becomes governed

**What existed before:** `v0.4.1_clean`/`v1.0.0` had a documented, buildable
L1–L9 stack, but calibration, topology, and conservation-style physics checks
existed as separate, individually-built pieces with no single integration
proof that a full run used all of them coherently, and no standardized,
pytest-backed audit artifact accompanying a release.

**What gap forced the jump:** a guard checking shape or value bounds is only
as good as the canon it checks against, and at this stage area/family geometry
and calibration thresholds were still being established empirically, not yet
locked into one governed, versioned bundle. Historical note: `7722d013` recorded an
early "10+2" packing idea; **current default core/module grain is 12** (optional
ten-area module is separate — see `docs/TOPOLOGY_INVARIANTS.md`).

**What got added:** the first pytest-backed, timestamped sealed-audit-bundle
release process (`final_gate sealed=true` as a literal checked field); the
"Tasks 1–11 integration" bundling P_CH (concept→hex projection), energy,
calibration, topology, and physics validation into one sealed whole; a
modular kernel workflow gate structure (T1–T10, then T11–T20); the contradiction
track (v0.5.8, 11 tasks) propagating a contradiction signal through every
layer that needs it (lexical, family, calibration) rather than letting it be
an incidental side-flag; and `core/propagation/guard_pipeline.py`'s
foundational header comment fixing Sigma → Gamma → Theta as a strict,
non-reorderable sequence for the first time.

**Why this was the minimal right move:** once multiple independently-correct
subsystems exist, the only way to guarantee a *run* (not just each piece in
isolation) is trustworthy is a fixed execution order plus an enforced final
gate — trusting each subsystem to self-certify does not compose.

→ [`corners/calibration.md`](corners/calibration.md), [`corners/topology_geometry.md`](corners/topology_geometry.md),
[`corners/hex_substrate.md`](corners/hex_substrate.md), [`eras/03_engine_dynamics_v0.5.x.md`](eras/03_engine_dynamics_v0.5.x.md)

---

## `hesperia-v0.4.0` → `v0.4.1_clean` / `v1.0.0`: the first full L1–L9 stack

**Chronology note:** `v1.0.0` and `v0.4.1_clean` land the same day
(2026-03-14) and are effectively one milestone under two names — `v1.0.0` is a
naming/cleanup tag on the v0.4.x line, not a later "1.0 product" sitting after
the 0.6.x sealed releases (which come two to three months later). Read tag
order by date, not by the number after the "v."

**What existed before:** v0.3.0 had specs, a `shadow_layer` draft, and docs,
but no integrated pipeline — each layer was closer to a design document than a
running stage.

**What gap forced the jump:** without an end-to-end pipeline, none of the
canon YAMLs (area geometry, propagation weights, logic rules) could be
validated against real output. Theory without execution can't be falsified,
and Hesperia's entire value proposition is falsifiability.

**What got added:** the first complete L1–L9 chain, Dict B (concept layer)
freeze discipline (B0 fallback, hard-gated B1), canonical procedures, and —
critically — the first "sealed runtime" concept (release gate, CLI/API
shipping, legacy-code quarantine, an architecture fingerprint tied to a
document→commit→tag evidence chain with an OpenTimestamps proof) in
`v0.4.1_clean`. This is also where `core/attribution`, `core/resolver`, and
`core/lexical` solidify as distinct concerns, because once text actually has
to flow through nine layers, "which span produced which concept" stops being
optional bookkeeping and becomes the only way to debug the pipeline at all.

→ [`corners/lexicon_resolver.md`](corners/lexicon_resolver.md), [`corners/sphere_pipeline.md`](corners/sphere_pipeline.md),
[`corners/layer_contracts_attribution.md`](corners/layer_contracts_attribution.md),
[`corners/release_governance.md`](corners/release_governance.md),
[`eras/02_v0.4_freeze_and_seal.md`](eras/02_v0.4_freeze_and_seal.md)

---

## `hesperia-v0.2-20260220` → `hesperia-v0.3.0`: from guard scripts to a layered spec

**What existed before:** v0.2 (Feb 20, 2026) was a working prototype: a flat
API (`/hesperia/analyze`, `/health`, `/privacy`) with Sigma/Gamma/Theta guards
already wired directly into the runtime, plus a body of largely narrative
material (tutorials, design drafts, semantic stability write-ups). The guards
exist by name before any layered pipeline exists for them to validate against
— "process before product" ordering that recurs throughout the repo's history.

**What gap forced the jump:** a guard checking "area vector has length 12" or
"adjacency matrix is symmetric" presupposes a stable, canonical definition of
what those objects *are*. At v0.2 that definition was still scattered across
narrative documents rather than fixed in versioned canon — every guard was
checking a moving target.

**What got added:** a deliberate consolidation pass ("full overwrite from
cursor brain") pulling scattered design material into one canonical reference
frame, the `DOC_INDEX` and `NN_SPEC__...` numbering convention that still
organizes `specs/` today, and the first `shadow_layer` concept — the direct
ancestor of today's `sphere/shadow/` correction stage, whose job from day one
was to stop a single strong signal from dominating a structural read.

**Why this ordering was the minimal right move:** building the guard *spec*
before the guard *wiring*, and consolidating theory into canon before building
the full pipeline, means the very first lines of architectural reasoning in
the repo establish "we check before we trust" as a precedent every later era
inherits without re-arguing it.

→ [`corners/guards.md`](corners/guards.md), [`corners/shadow_correction.md`](corners/shadow_correction.md),
[`eras/01_genesis_v0.2_v0.3.md`](eras/01_genesis_v0.2_v0.3.md)

---

## Bedrock: why Hesperia has to exist as a *separate* thing from an LLM call

This is the foundation stone underneath every era above it, and it is stated
explicitly in `docs/foundations/theory_description.txt` (the design memo that predates most of
the engineering): an LLM can produce fluent, plausible structure from text,
but it cannot be forced to be the same fluent, plausible structure twice, nor
can it show its work span-by-span. Hesperia's reason to exist is the gap
between "wording" and "stable concept evidence" — closing that gap
deterministically (controlled lexicon → phrase-first matching → disambiguation
→ hex projection → family/area rollup) is a *prerequisite* for everything else
in this document, including the V7 bridge, which only works because the thing
it is bridging *to* an LLM is already deterministic. Without that foundation,
fpf_bridge would just be an elaborate way of asking an LLM to hallucinate in a
structured format. The system's single most load-bearing sentence, stated in
the founding memo itself: *"Do not allow raw wording to activate families
directly unless routed through resolved concept evidence or an explicitly
marked fallback path."*

→ [`corners/lexicon_resolver.md`](corners/lexicon_resolver.md), [`corners/hex_substrate.md`](corners/hex_substrate.md),
[`references.md`](references.md)

---

## The pipeline in plain language: activation → propagation → guards → surface logic → dynamics logic → output logic

The corners below are organized by module name, not by the stage vocabulary a non-implementer
would reach for. This is the same L1–L11 chain, named the other way, so the two can be cross-read:

| Plain-language stage | What actually happens | Corner doc(s) |
|---|---|---|
| **Activation** | Raw text → controlled-lexicon matching (Dict A) → disambiguated concept IDs (Dict B) → projection onto the 72k hex substrate. The only point where natural language is touched. | `corners/lexicon_resolver.md`, `corners/hex_substrate.md` |
| **Propagation** | Concept activations spread across hex/family/area structure via deterministic graph diffusion (Laplacian `dc/dt = −αLc`, fixed YAML weights), then a separate correction stage caps the entropy rise diffusion mathematically and unavoidably introduces. | `corners/propagation_dynamics.md`, `corners/shadow_correction.md` |
| **Guards** | Sigma (artifact shape) → Gamma (execution-order/process soundness) → Theta (release/governance eligibility) — three categorically different verdicts, sequenced because each is meaningless to evaluate before the one before it has passed. | `corners/guards.md`, `corners/logic_guards.md` |
| **Surface logic** | Layer-9 YAML threshold rules (`structural_monotony`, etc.) plus optional Prolog forward-chaining for relational/symbolic claims that threshold rules can't express. | `corners/logic_guards.md`, `corners/prolog_logic.md` |
| **Dynamics logic** | Trajectory features (curvature, jump rate, stability) computed across a *sequence* of already-deterministic propagation outputs — stateful where propagation itself is stateless per call. | `corners/propagation_dynamics.md` (dynamism section) |
| **Output logic** | The 5-state interpretation classifier consolidates everything above into the Universal Structural Fingerprint (USF); `fpf_bridge` then turns USF + guard verdicts into a bounded state machine an LLM can narrate inside, never the other way around. | `corners/interpretation_usf.md`, `corners/schemas_contracts.md`, `corners/fpf_bridge.md` |

Two analytical layers consume this chain's output without feeding back into it: **KME**
(`corners/kme.md`, structural-comparability fingerprints over the same concept graph) and **TRIZ**
(`corners/triz_extension.md`, contradiction/innovation analysis over the same concept graph,
exported as named decision-intelligence products). Both are explicitly read-only against
everything above — see each corner's "why read-only" section for why that boundary is load-bearing,
not incidental.

---

## Map of the rest of this package

If you are here as an executing agent rather than a reader, pair this file with
[`agentic_orientation.md`](agentic_orientation.md). `00_INDEX.md` explains the architecture from
roof to bedrock; `agentic_orientation.md` explains the five-pass cold-start discipline that keeps
names, branch scope, math claims, and remote choices from drifting during real work.

### Corners (one file per architectural concern)

- [`corners/lexicon_resolver.md`](corners/lexicon_resolver.md) — Dict A / Dict B / Dict C freeze discipline; the
  three mechanisms by which B catches evidence from A; Dict C as phrase-level synthesis layer built from two
  directions (ACB corpus-driven and BAC concept-recovery). The only place Hesperia touches raw natural language.
- [`corners/hex_substrate.md`](corners/hex_substrate.md) — the 72k/72,240-cell layer between
  resolved concepts and family/area rollup.
- [`corners/topology_geometry.md`](corners/topology_geometry.md) — the icosahedral area sphere and
  family zone lattice.
- [`corners/metric_registry.md`](corners/metric_registry.md) — the `metric_layer` enum and frozen
  `anchor_map_v1` that disambiguate "distance" across geometries.
- [`corners/propagation_dynamics.md`](corners/propagation_dynamics.md) — diffusion-based
  propagation and trajectory/dynamism over time.
- [`corners/shadow_correction.md`](corners/shadow_correction.md) — bounded correction of
  propagation's entropy/dominance side effects.
- [`corners/logic_guards.md`](corners/logic_guards.md) — Layer-9 declarative rules, optional Prolog
  inference, and the Sigma/Gamma/Theta guard triad together.
- [`corners/guards.md`](corners/guards.md) — Sigma (static shape) / Gamma (dynamic ordering) / Theta
  (output governance) in focused detail.
- [`corners/prolog_logic.md`](corners/prolog_logic.md) — the optional L9b symbolic inference layer
  in focused detail.
- [`corners/interpretation_usf.md`](corners/interpretation_usf.md) — the 5-state classifier and the
  Universal Structural Fingerprint consolidation.
- [`corners/sphere_pipeline.md`](corners/sphere_pipeline.md) — the L1–L10 orchestrator that makes
  canonical layer order an enforced fact, not a convention.
- [`corners/core_runtime.md`](corners/core_runtime.md) — why `core/` (computational substrate) is
  distinct from `sphere/` (orchestration).
- [`corners/layer_contracts_attribution.md`](corners/layer_contracts_attribution.md) — the
  inter-layer contract type and span-to-family attribution.
- [`corners/schemas_contracts.md`](corners/schemas_contracts.md) — USF and the frozen `/analyze`
  HTTP contract as versioned, checkable shapes.
- [`corners/fpf_bridge.md`](corners/fpf_bridge.md) — Layer 11, the read-only LLM reasoning bridge.
- [`corners/calibration.md`](corners/calibration.md) — calibration scripts and profiles, the one
  sanctioned offline use of an LLM in the system.
- [`corners/release_seal.md`](corners/release_seal.md) — the release bundle shape and
  `runtime/services/` as the boundary layer to external contracts.
- [`corners/release_governance.md`](corners/release_governance.md) — sealing as a claim about
  *which exact tree* shipped, and the public/prod split.
- [`corners/kme.md`](corners/kme.md) — the Knowledge Metrics Engine: six bounded primitives, 35
  derived ratio metrics (including KSI), and hashed comparability fingerprints.
- [`corners/triz_extension.md`](corners/triz_extension.md) — the TRIZ/Altshuller contradiction-
  analytics layer: what's adopted from classic TRIZ, what isn't, and what's genuinely commercial
  about it.
- [`corners/corpus_wiring.md`](corners/corpus_wiring.md) — what corpus exists, what's done to it
  (gap analysis, feature extraction, freezing), and what never ships.
- [`corners/field_dynamics.md`](corners/field_dynamics.md) — the ~47-constant Phase 1–4 field
  dynamics extension (`hesperia/extensions/dynamics/`): opt-in, environment-gated (Ξ tension on by
  default, everything else off), wired into the E2E release proof but **not** into
  `/product/interpret` — `internal` product surface, not `optional`/shipped. The subsystem this
  Phase 2 documentation pass originally missed because it sits off the traced output path.
- [`corners/core_math_contract.md`](corners/core_math_contract.md) — the pre-v0.4 Core Math
  Contract (22_SPEC), still live as `core/math/core_math.py`: fusion, diffusion, the five penalties,
  composite governance/obstacle scores, conservation invariants, and an honest accounting of which
  earlier (v0.2/early-v0.3) formalisms — bipolar axes, DFT ring smoothness, KL divergence — did not
  survive into the shipped contract.
- [`corners/geometry_math_coupling.md`](corners/geometry_math_coupling.md) — cross-cutting: how the
  icosahedral topology and hex substrate directly determine and constrain the math. W IS the
  adjacency matrix; row-stochastic conservation is a geometric theorem not an imposed rule; pre-placement
  of concept anchors is the computation that gives W semantic meaning; zone/bridge costs form a
  potential landscape; the closed sphere eliminates boundary-condition special cases system-wide.
- [`corners/physics_dynamics_coupling.md`](corners/physics_dynamics_coupling.md) — cross-cutting: the
  physics of motion (energy, mass, trajectory) underneath propagation and dynamism. `compute_h_total`'s
  self/coupling/inhibition energy law (decay ODEs, mean-field theory, leaky-integrate-and-fire); diffusion
  as a lazy random walk / personalized PageRank; multi-step propagation as Markov-chain power iteration
  (Chapman-Kolmogorov); stability/jump-rate feedback modulation of the diffusion rate (cybernetic
  negative/positive feedback); L6's curvature/jump-rate/stability/trajectory dynamism engine traced to
  `core/math/`; activation-side entropy and dominance detection; BFS traversal vs. diffusion as two
  unrelated movement models flagged against a "depth" naming collision.
- [`corners/activation_landing_loops.md`](corners/activation_landing_loops.md) — cross-cutting: Dict A's
  Spec-20 authority boundary (side_id only, no family/area), its two build provenances (definitional
  extraction from Dict B concept nodes; external lexicographic sourcing from OEWN/SCOWL/Wiktionary,
  hash-pinned), the two independent matcher implementations (greedy phrase-first interval scheduling;
  weighted 288-family attribution with prior-proportional tail-mass smoothing), the literal
  `explain_landing`/`landing_source` provenance mechanism and its `exclude_landing_sources` governance
  lever, the seed handoff into the hex substrate, and an explicit disambiguation between L2's structural
  loop count (graph circuit rank / cyclomatic number) and `compute_loopability`'s unrelated temporal
  return/recurrence measure.
- [`corners/pipeline_l1_l11_science.md`](corners/pipeline_l1_l11_science.md) — cross-cutting synthesis:
  the full L1–L11 pipeline in one pass, tracing every key formula to its external origin (Shannon 1948,
  Kirchhoff 1847, Watts-Strogatz 1998, Gini 1912, Moore BFS, mean-field theory, Chapman-Kolmogorov,
  Lyapunov, FGR trust tuples) or to its Hesperia-native derivation. Covers inter-layer data flow
  (complete handoff table), the three architectural tiers (lexical resolution / measurement cascade /
  synthesis gap + LLM bridge), and five cross-cutting themes: mass conservation, entropy as shared
  measurement language, dual-path falsification structure, determinism as invariant, and the
  Hesperia-native vs. borrowed-science audit.

### Layers (one file per pipeline layer, math + scientific lineage)

- [`layers/L1_structural_activation_census.md`](layers/L1_structural_activation_census.md) —
  Layer 1 (34_SPEC): 27-variable census of raw concept attribution. Shannon entropy, Gini
  coefficient, L1/L2 norms, SNR, altitude aggregation, profile deviation (FPD/APD/BVS/PCS).
  Pure arithmetic over attribution output — no LLM, no propagation, no guards.
- [`layers/L2_topology_traversal.md`](layers/L2_topology_traversal.md) —
  Layer 2 (35_SPEC): BFS from dominant family to depth 8. 25 variables: reachability,
  clustering coefficient (Watts-Strogatz), circuit rank (loop count), cross-area geometry,
  mass-per-depth profile, GEOMETRIC_STABILITY_INDEX. Topology risk assessment before propagation.
- [`layers/L3_baseline_shadow_comparison.md`](layers/L3_baseline_shadow_comparison.md) —
  Layer 3 (36_SPEC): Baseline vs. Shadow dual-run comparison. 25 delta/similarity variables:
  Jaccard (neighborhoods), cosine similarity (hit vectors), top-K overlap, signed L1/L2 deltas.
  SHADOW_DEVIATION_SCORE (weighted 0.35/0.35/0.30) + SHADOW_ACCEPTABILITY_GATE. Perturbation
  robustness analysis before any propagation or guard runs.
- [`layers/L4_evidence_retrieval.md`](layers/L4_evidence_retrieval.md) —
  Layer 4 (37_SPEC): evidence retrieval quality assessment. BM25 chunk retrieval vs. structural
  reading alignment. 25 variables: shortfall, book diversity, family/area match, MRR-weighted
  alignment, hit-evidence Jaccard (cross-system consistency), B/S evidence stability, integrity.
  EVIDENCE_SUPPORT_INDEX (0.45/0.35/0.20) + EVIDENCE_ACCEPTABILITY_GATE.
- [`layers/L5_counter_evidence_and_trig_invariants.md`](layers/L5_counter_evidence_and_trig_invariants.md) —
  Layer 5 (38_SPEC): two unrelated halves. 5A: counter-evidence/contradiction pressure
  (falsification-style negative-evidence retrieval vs. anti_families), CONTRADICTION_PRESSURE_SCORE
  (0.55/0.25/0.20) + REALITY_GATE_COUNTER_EVIDENCE. 5B: trig/metric-space axiom self-test
  (Cauchy-Schwarz, Pythagorean identity, metric axioms) — 6 of 13 residuals are hardcoded
  passing constants, documented as such, not live computations.
- [`layers/L6_dynamical_stability_scaffold.md`](layers/L6_dynamical_stability_scaffold.md) —
  Layer 6 (39_SPEC): sensitivity/curvature/rank/Lyapunov stability scaffold. Only
  DEPTH_GROWTH_RATIO, FIBONACCI_DEVIATION_SCORE, GLOBAL_STABILITY_SCORE, and
  CONCEPTUAL_COHERENCE_INDEX are live/derived; 21 of 25 variables are documented
  no-perturbation constants (0/1.0 identity defaults), named scaffold for L7/L8/L9.
- [`layers/L7_consistency_and_decision.md`](layers/L7_consistency_and_decision.md) —
  Layer 7 (40_SPEC): synthesizes L1-L6 into 10 CONSIST_* cross-layer gates, TRUST_TIER,
  limit/within-limits pairs, STRUCTURE_EVIDENCE_ALIGNMENT (0.60/0.40), SYSTEM_CONFIDENCE_SCORE
  (5-factor product), priority-encoded DECISION_STATUS_CODE (0/10/20/30/40/50/60/70/75 —
  75 permanently reserved), OUTPUT_TRUST_TAG (HIGH/MED/LOW, post-hoc LOW_CONFIDENCE demotion
  via stability_delta.py anomaly score).
- [`layers/L8_unit_standardization.md`](layers/L8_unit_standardization.md) —
  Layer 8 (41_SPEC): re-expresses L1-L7 scores into a fixed unit taxonomy
  (COUNT/PERCENT/U1000/BOOLEAN live; RATIO/RADIANS/SECONDS/BYTES/HASH/CODE
  declared-only), per-mille (U1000) scale convention, declared clamp/epsilon/
  rounding policy, and the Π interpretation-policy gate (POLICY_MODE,
  INTERPRETATION_SCOPE) feeding L9. No new measurement — pure re-expression layer.
- [`layers/L9_pillars_and_brand_labels.md`](layers/L9_pillars_and_brand_labels.md) —
  Layer 9 (42_SPEC, final layer): 6 confidence BANDs, directionalization convention,
  6 balanced-scorecard-style PILLAR_* scores (governance pillar linearly penalized
  by L7 decision-code magnitude), 5 BRAND_WORD_* categorical labels, 4 ACTION_*
  workflow triggers. L1-L9 metrics become human-facing labels; no locale (i18n wraps
  L9 output). Terminus of the numbered-layer chain.
- [`layers/L10_analysis_report_placeholder.md`](layers/L10_analysis_report_placeholder.md) —
  Layer 10 (declared, not yet implemented): placeholder stub in `pipeline_runner.py`;
  contract specifies `analysis_report`/`interpretation`/`explanation`; active governance
  consequence is Theta THETA_004 (`flag_non_canonical_interpretation`). Intended synthesis
  layer feeding the fpf-bridge LogicLayer.
- [`layers/GUARDS_sigma_gamma_theta.md`](layers/GUARDS_sigma_gamma_theta.md) —
  Exhaustive invariant-by-invariant documentation of the guard triad, run after
  L1-L9: Sigma (15 static shape/value invariants, Hoare-precondition/Design-by-
  Contract lineage), Gamma (8 dynamic execution invariants — several honestly
  documented as default-permissive/vacuous-unless-flagged, not independently
  verified), Theta (5 declarative governance rules, canonical/quarantined
  status). Plus core/guards/ (determinism contract guard, and the
  state-mutating enforce_invariants repair guard — distinct from Sigma's
  read-only checks). Flags a layer_9 naming collision between the logic-rule
  engine and core/layers/layer_9.py.

### Eras (one file per version era, with commit evidence)

- [`eras/01_genesis_v0.2_v0.3.md`](eras/01_genesis_v0.2_v0.3.md) — guard scripts before any layered
  pipeline existed to guard.
- [`eras/02_v0.4_freeze_and_seal.md`](eras/02_v0.4_freeze_and_seal.md) — the first full L1–L9 stack,
  lexicon freeze, and first sealed-runtime gate.
- [`eras/03_engine_dynamics_v0.5.x.md`](eras/03_engine_dynamics_v0.5.x.md) — calibration becomes a
  governed, versioned subsystem.
- [`eras/04_v0.5.8_contradiction_track.md`](eras/04_v0.5.8_contradiction_track.md) — contradiction
  threaded as a cross-cutting signal through every existing layer.
- [`eras/05_sealed_0.6.x.md`](eras/05_sealed_0.6.x.md) — the 0.6.0 sealed mainline and the dev/prod
  split.
- [`eras/06_metric_wave_v0.7.0.md`](eras/06_metric_wave_v0.7.0.md) — the `metric_layer` registry and
  frozen `anchor_map_v1`.
- [`eras/07_v7_router_fpf_bridge.md`](eras/07_v7_router_fpf_bridge.md) — the read-only LLM reasoning
  bridge, Layer 11.
- [`eras/08_fpf_bridge_v7_2_v7_4.md`](eras/08_fpf_bridge_v7_2_v7_4.md) — evidence expansion, the
  agentic Cursor interface, and COBALT corpus scale-up prep; two self-corrections recorded (KME/TRIZ
  domain scoping, `GateDecision.BLOCK`).

### References

- [`agentic_orientation.md`](agentic_orientation.md) — the shortest safe cold-start path for agents:
  five passes (surface, branch, names, math, execution), plus the owner map and anti-drift rules.
- [`parameter_catalog.md`](parameter_catalog.md) — every explicit math constant in the system,
  ground up from geometry through FGR calibration to KME/TRIZ, with what specific meaning each one
  contributes to the final output (not what it is — what changes in the output if it changes).
- [`parameter_rationale_and_theory.md`](parameter_rationale_and_theory.md) — the academic companion
  to `parameter_catalog.md`: why each parameter or parameter family exists, why its value/range is
  shaped the way it is, and which theory family it borrows from, with verified-vs-inferred honesty
  called out explicitly.
- [`output_catalog.md`](output_catalog.md) — the other half of that question: every named,
  user/LLM-facing aggregated variable from L1 through `fpf_bridge`, which of the two live product
  surfaces (`/analyze` vs. `/product/interpret`) actually returns it, and — for the handful of
  variables with real multi-layer composition depth (`SYSTEM_CONFIDENCE_SCORE`,
  `EVIDENCE_SUPPORT_INDEX_BASELINE`) — traced end to end as worked examples rather than left as a
  layer count.
- [`parameter_synergies.md`](parameter_synergies.md) — which parameters from different stages
  combine to produce a signal neither gives alone (KME primitive pairs, propagation/shadow-correction
  weight pairs, Sigma-AND-Gamma guard gating), and the worked example of exactly what trust/freshness
  metadata reaches the LLM per piece of evidence and why.
- [`references.md`](references.md) — the load-bearing scientific/theoretical citations, each tied
  to the specific decision it backs.
- [`provenance.md`](provenance.md) — an audit of named principles found in specs/core (FPF, FGR,
  BELL, KSI, GCS, Sigma/Gamma/Theta): where each name actually comes from, whether `grep` finds it
  running in `core`/`sphere`/`runtime`, and where it's documented. Distinguishes externally-sourced
  theory genuinely wired into the system from names that exist only in a spec.

### Standards-mapped and publication tiers (built on top of, not instead of, the above)

This package (`docs/foundations/`) stays the engineering-reasoning tier. Two further tiers
re-organize the same source-verified facts for different audiences — every claim in them cites back
here rather than re-deriving it. Master registry, entry points, and maintenance rule for both tiers:
[`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md).

- `docs/iso/` — standards-mapped project documentation: `ARCHITECTURE_DESCRIPTION.md` (42010),
  `REQUIREMENTS_SPECIFICATION.md` (29148), `QUALITY_MODEL.md` (25010), `LIFECYCLE_PROCESS.md`
  (12207), `OPERATOR_GUIDE.md` (26511/26512).
- `docs/publication/` — the scientific-publication-facing track:
  `NOVELTY_AND_POSITIONING.md` (the invention-vs-innovation statement every paper draft should cite
  instead of re-arguing), `METHODS.md`, `VALIDATION_EVIDENCE.md`, `REPRODUCIBILITY_PACKAGE.md`,
  `TERMINOLOGY_AND_ABBREVIATIONS.md` (the academic nomenclature register — every abbreviation in
  this documentation program, verified/inferred/proposed/unresolved, including the 35 KME
  derived-metric codes that have no stated expansion anywhere in source), `SCIENCE.md` (~35 named
  scientific/engineering works across 11 disciplines, each scored on a 5-level extent-of-application
  taxonomy from full-verbatim to explicitly-rejected — the citation register
  `NOVELTY_AND_POSITIONING.md`'s composition-level claim sits on top of).

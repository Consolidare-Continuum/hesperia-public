# Provenance — named principles, where they actually come from, and whether they're built

The repo's specs and comments drop names and acronyms — FPF, FGR, BELL, KSI, GCS, IPoW,
Minkowski — without saying where they come from or whether the thing they name is actually
running. That gap is what this file closes. It is an audit, not a narrative: for every named
principle found in Hesperia's specs/core, three questions are answered —

1. **Where does the name come from** (external framework, a named role/spec author, or
   Hesperia-native)?
2. **Does it exist in `core`/`sphere`/`runtime` as running code**, or only in a spec/doc?
3. **Where is it now described** in this `docs/foundations/` package, if anywhere?

Verification method: `grep` across `*.py` for the symbol/acronym, cross-checked against
`/data/hesperia/cursor-brain-mirror` (the "brain" repo) where a name's origin lives outside this
repo. Where the brain repo's local mirror does not contain a file the Hesperia docs link to
(e.g. a `github.com/igareosh/cursor` URL with no matching path in the mirror), that is stated
plainly rather than guessed at.

## External frameworks actually wired into core

| Name | Origin | Implemented? | Documented in |
|---|---|---|---|
| **FPF (First Principles Framework)** | External. Primary author **Anatoly Levenchuk** (+ LLM assistance), a ~51,300-line transdisciplinary reasoning spec (`FPrincipleF/FPF-Spec.md` in the brain repo), distributed as a RAG-loadable file, not a library to import. | **Yes, via a real dependency boundary.** `sphere/fpf_bridge/` declares `fpf-thinking-map` (PyPI, v1.2.1+) as a dependency and feeds it `EvidencePrimitive`s, gated transitions, and `FGR` tuples. | `corners/fpf_bridge.md` (enriched this pass), this file. |
| **FGR (Formality, Ground/Scope, Reliability)** | External. FPF Part **B.3, "Trust & Assurance Calculus."** FPF defines trust as a computed tuple ⟨F, G, R⟩ — F = how rigorously a claim is expressed, G = the context-slice it claims to hold over, R = how well it is evidenced — rather than a single confidence scalar. | **Yes.** `sphere/fpf_bridge/constants.py` carries "FGR tables" and `corners/fpf_bridge.md` already referenced "calibrated trust values (FGR)" without naming the source theory; this pass adds the theory. | `corners/fpf_bridge.md`. |
| **fpf-thinking-map** | Hesperia/Felix-side engineering: a PyPI package that operationalizes FPF's holon / bounded-context / evidence-graph primitives as an actual Python reasoning substrate (state graphs, gates, guard closures) an LLM can traverse. Not part of the original FPF spec itself — it is the bridge artifact that makes FPF's abstract calculus executable. | **Yes** — it is the substrate `sphere/fpf_bridge/` targets. | `corners/fpf_bridge.md`. |
| **fpf-thinking-map's per-section FPF anchors** (`A.21` GateProfilization, `A.10`/`B.3.4` evidence+decay, `A.3.3`/`B.4`/`A.2.5` transitions, `A.1.1` `U.BoundedContext`) | External, verified directly against the installed package's own docstrings (`fpf_thinking_map/primitives.py`), not inferred — e.g. `GatePrimitive`: "FPF A.21: gates aggregate GateChecks via join-semilattice." | **Partially wired, partially dormant.** `GatePrimitive`/`GateCheck`/`EvidencePrimitive`/`TransitionPrimitive` are used by `sphere/fpf_bridge/state_graph.py`. Two capabilities the package ships but Hesperia never used before fpf_bridge_v7.2: `EvidencePrimitive.contradicts` (now wired) and `SemanticFloor`/`computed_ttl` decay (still unset on every evidence primitive — real, callable, not yet used). One finding worth flagging explicitly: `GateCheck.evaluate()`'s actual logic only ever returns `PASS`/`DEGRADE`/`ABSTAIN` — `GateDecision.BLOCK` is a defined enum value nothing in the installed version's gate-evaluation path currently produces, though `ThinkingMapTraversal.attempt_transition()` correctly special-cases it if a future gate implementation does. | `specs/canon/fpf_bridge_v7_2_evidence_expansion.md` §4.1–4.2, `specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md` §1.2 (this pass, 2026-07-04). |
| **TRIZ (Theory of Inventive Problem Solving)** | External. Genrich Altshuller's framework: technical contradictions, the 40 inventive principles, the engineering-parameter contradiction matrix. Hesperia adopts a deliberately narrow slice — 3 typed relation kinds, 4 of the 40 principles, no 39×39 matrix — not the full apparatus. | **Yes.** `hesperia/extensions/triz/` (30+ modules): `contradiction_engine.py`, `novelty_engine.py` (Louvain clustering, seeded), `commercial_intelligence.py`, `exporters.py`. | `corners/triz_extension.md` (added this pass). |
| **Louvain community detection** | External. A real, published modularity-maximization graph-clustering algorithm (`networkx.community.louvain_communities`), not Hesperia-invented. | **Yes**, seeded (`LOUVAIN_SEED = 42`) specifically to keep an otherwise order-dependent algorithm reproducible. | `corners/triz_extension.md`. |

## Names confirmed Hesperia-native (no external borrowing, despite surface resemblance)

| Name | Why it could be mistaken for borrowed | Verification | Documented in |
|---|---|---|---|
| **Sigma / Gamma / Theta guard triad** | FPF prominently features a "Γ (Gamma)" composition/aggregation operator (Part B.1), and the same Greek letter appears in both systems. | `grep -c 'Sigma\|Theta' FPF-Spec.md` → **0** matches in 51,305 lines. FPF's Γ is an aggregation algebra over wholes/parts; Hesperia's Gamma is a dynamic-ordering guard verifying execution sequence. Same letter, unrelated concept, independently named (Era 3, `eras/03_engine_dynamics_v0.5.x.md`). `specs/canon/fpf_bridge_v7.md` itself keeps them distinct: "9 fpf built-in guards **+ 3 Hesperia guards (Sigma/Gamma/Theta)**" — additive, not derived. | `corners/guards.md`, `corners/fpf_bridge.md` (this pass adds the explicit non-derivation note). |

## Names found only in spec/doc text, not (yet) in core

| Name | Where it appears | Core implementation check | Status |
|---|---|---|---|
| **BELL `path_mass`** | `docs/DOC_INDEX.md`, `docs/specs/24_SPEC__Hesperia_Metric_and_Distance_v0_1.md` §4.6/§5, referenced as "BELL_research SPEC" | `grep -rl "path_mass\|BELL" --include=*.py` → **no matches** anywhere in the repo. | Specified, not built. The `metric_layer=concept_graph` enum slot exists in the registry (`corners/metric_registry.md`) reserving the name, but the resistance-distance formula (`W_e`/`R_e` on Floor-2 corridor bundles) itself has no running code. Treat as a real, named, future obligation — not a present capability. |
| **GCS (Geodesic Sphere) / IPoW (Interior Point of World View)** | `docs/DOC_INDEX.md` links a brain-repo draft (`HESPERIA-FORMALIZATION-GEODESIC-SPHERE-AND-INTERIOR-POINT-OF-WORLD-VIEW-v0_1.md`) not present in the local `cursor-brain-mirror` checkout (only a partial/sparse mirror was available — could not verify the full draft's content from this environment). | `grep -rl "geodesic_sphere\|anchor_map"` → **matches**: `runtime/services/{anchor_map_registry,hesperia_metric_emit,gcs_lookup}.py` (uncommitted v0.7.0 work). `HESPERIA_GCS_EMIT` is a real, tested env flag (`tests/test_metric_22_26.py`). | **Partially built.** The registry/lookup/emit-gating scaffolding exists and is tested; the full IPoW formalization (whatever the brain-repo draft specifies beyond the `ipow_volume` enum slot) is not verifiable from this repo alone — `24_SPEC` itself scopes out "clinical interpretation of IPoW" and "Poisson solver" as explicitly deferred. |
| **"Ethan" specs (`SPEC-ETHAN-...`), Minkowski–IPoW SPEC, 22_SPEC, 23_SPEC, 24_SPEC** | Cross-linked from `docs/DOC_INDEX.md` as living in the brain repo under a named-author/role convention ("Ethan ratification"). | Not present in the local `cursor-brain-mirror` mirror under that name; `24_SPEC` (the one specced *and* mirrored into this repo, at `docs/specs/`) is the only one of this family with a local, checkable text. | Authority chain exists (the repo defers to these specs as ratifying authority) but only `24_SPEC`'s content was directly verifiable here. Do not treat unverified specs as implemented fact in foundations docs — `corners/metric_registry.md` already correctly scopes its claims to what `24_SPEC` itself states. |
| **`34_SPEC` through `42_SPEC`** (the nine per-layer specs `core/layers/layer_1.py`…`layer_9.py` each cite by docstring as their canonical origin, e.g. `layer_1.py`: "Layer-1 (34_SPEC + 34_SPEC N1)") | **Found, recovered, and restored to the live tree.** Originally located only in `hesperia_full_repo_snapshot_20260314.tar.gz` (`/data/hesperia/hesperia-backup/snapshots/`, a full-repo tarball snapshot three weeks after the Feb 2026 deliverable date) — not in the live working tree at the time, not in `docs/specs/` (only `24_SPEC` lived there), and not in `cursor-brain-mirror/CLIENTS/hesperia/` (that mirrored dir contains only an empty `api/` subfolder). Now copied into this repo at `docs/specs/history/34_SPEC__V0_4_Layer1_Instrumentation_25_Variables_v1_0.txt` through `42_SPEC__V0_4_Layer9_Human_Reference_Brand_Treatment_25_Variables_v1_0.txt` (plus `34_SPEC_N1__L1_Normative_Structure_Profile_Extension_v0_4.txt`) — the archive tarball remains the historical source of truth, but this repo no longer depends on it to check these citations. | **Verified, not merely cited.** Extracted and read directly: each spec's own numbered list (25 items for L1/L2/…/L9) was cross-checked line-by-line against the running `compute_L1`…`compute_L9` implementations for `output_catalog.md`. Every apparent count discrepancy resolved cleanly against the spec text itself (e.g. `34_SPEC` item 18 bundles `UNIQUE_AREAS_HIT`/`AREA_SPREAD` as one numbered entry, explaining L1's 25-spec-items → 26-actual-variables; `40_SPEC` confirms `OUTPUT_TRUST_TAG` is L7's spec item 25, not an uncounted afterthought) — with one genuine exception: L7's `STABILITY_ANOMALY_SCORE` and the profile-conformance fields are real code-only additions made after `40_SPEC`/`34_SPEC N1`, not spec omissions. Treat "per `NN_SPEC`" in `layers/*.md` and `output_catalog.md` as independently verified against spec text, not merely against the code's own docstring claim (a stronger status than the row above, once these were located). Same recovery applies to the missing `hesperia/extensions/dynamics/` spec (`corners/field_dynamics.md`) — checked in this same tarball and in the `hesperia-dev-backup` git mirror; genuinely absent from both, so that one stays in "spec-only claim, unverified" status. |
| **KSI / KME-KSI-score** | `docs/DOC_INDEX.md` ("Bare 'KSI' in runtime docs is ambiguous — always qualify") | `grep -rl "KSI"` → **matches**: canonical implementation in `core/domain/{models,fingerprint,derived_metrics}.py`, plus compatibility shims under `hesperia/engine/kme/`. Formula: `KSI = clamp01(safe_div(COH * LD, PR))`. | **Built and now documented.** A real derived metric (KME-KSI-score, distinct from "KSI-Inspector" the tool), correctly disambiguated in `docs/DOC_INDEX.md`'s own table. See `corners/kme.md` for the full six-primitive/35-derived-metric structure it belongs to. |

## Pre-v0.4 math: what's still load-bearing vs. what was exploratory

| Name | Origin | Implemented? | Documented in |
|---|---|---|---|
| **Core Math Contract (22_SPEC)** — fusion, base/shadow step, the five penalties, composite governance/obstacle scores, conservation invariants | v0.3 era, `backup/hesperia-mrt-fork:22_SPEC__V0_3_Core_Math_Contract_v1_0.md` | **Yes, live.** `core/math/core_math.py`, imported by `runtime/pipeline/analyze.py`. CI-enforced as the *only* place math may live (`tests/architecture/test_no_math_in_sphere.py`). | `corners/core_math_contract.md` (added this pass). |
| **Bipolar activation axes, `Σ B[k]²` tension formula, KL divergence, DFT/Fourier "ring smoothness," 4-constant decay model (`ALPHA/BETA/GAMMA/DELTA`), turn coherence, cumulative drift** | v0.2/early-v0.3, `backup/hesperia-mrt-fork:21_MATH__HESPERIA_formalization_v1_1_java.txt` | **No.** `grep` for each name/function across every `.py` file: zero matches. Only `tension_energy` (different formula) and `cosine_similarity` (repurposed for fingerprinting, not drift) persisted. | `corners/core_math_contract.md`'s "what did not survive" section — recorded as real, dated exploratory work, not folded into present-tense reasoning elsewhere. |

## Terminology precision: "Markov-like," not "Markov chain model"

`core/math/core_math.py`'s `base_step` is structurally a lazy Markov chain step (row-stochastic
transition matrix `W`, mixed with self-retention, iterated `T_steps` times — see
`corners/core_math_contract.md`). The project's own brain-repo scientific-alignment guidance
(`ETHAN-HESPERIA-SCIENTIFIC-ALIGNMENT-BOOKS-REDISCOVERY-2026-03-25.md`) states the correct
terminology boundary explicitly: describe this as **"Markov-like"** discrete-time state-sequence
behavior, not as a fitted Markov chain or Hidden Markov Model — there is no stationary-distribution
analysis, no estimated transition probabilities, no likelihood-based latent-state inference. The
weights are hand-set constants (`lambda=0.55`, `decay=0.04`), not learned. Foundations docs should
follow this same discipline: name the real mathematical shape, do not borrow the prestige of the
fuller statistical framework that was never built — the same rule already applied to Kolmogorov
below.

## Names that turned out not to be there: Kolmogorov

A direct check, asked for explicitly: does Hesperia adopt anything from **Kolmogorov** (complexity
theory, or the axiomatic probability theory)? `grep -rli kolmogorov` across every `.py`, `.md`,
`.txt`, and `.yaml` file in the repo, plus the mirrored brain-repo math drafts
(`21_MATH__HESPERIA_formalization_v1*.txt` on `backup/hesperia-mrt-fork`) — **zero matches,
anywhere.** What *is* used, pervasively, is **Shannon entropy**: `areaEntropy`/`entropy` functions
in the brain repo's formalization draft, and `structural_monotony` in
`specs/canon/diagnostic_rules.yaml` (entropy below 0.35 ⇒ structurally narrow discourse,
`corners/logic_guards.md`). Shannon entropy and Kolmogorov complexity are related ideas — both
formalize "how much information/structure is really here" — but they are not the same tool, and
the choice of Shannon over Kolmogorov is not an oversight: Kolmogorov complexity is **uncomputable**
in general (no algorithm can compute it exactly for an arbitrary string), which makes it
structurally incompatible with a system whose entire reason to exist is deterministic,
re-runnable measurement. Shannon entropy over a known, finite distribution (area activation
weights, propagated vectors) is exactly computable and decomposable, which is why it — not its
more famous, uncomputable cousin — is the information-theoretic tool actually load-bearing
throughout the propagation, shadow-correction, and logic-guard corners. State this plainly rather
than retrofitting a Kolmogorov connection that the code does not contain.

## What this means for the rest of the package

The discipline this audit enforces, and that the rest of `docs/foundations/` should keep
following: **a name earns a place in a corner/era doc's load-bearing reasoning only if `grep`
finds it running.** A spec-only name is real (it represents a real, often dated, intention) and
worth recording — but it belongs in a "deferred/specified" note, not folded into the present-tense
"why this exists" reasoning used for shipped mechanisms elsewhere in this package.

→ [`corners/fpf_bridge.md`](corners/fpf_bridge.md), [`corners/metric_registry.md`](corners/metric_registry.md),
[`references.md`](references.md)

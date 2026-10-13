# SPEC: fpf_bridge v7.2 — Evidence Expansion (COBALT + TFP scope)

**Version:** v7.2 (extension)
**Status:** RATIFIED (Ethan) — 2026-07-19
**Date:** 2026-07-04 (draft) · **Ratified:** 2026-07-19
**Author:** Felix (Developer, Claude Code)
**Parent:** `spec/fpf_bridge_v7.md`
**Sibling spec:** `fpf_bridge_v7_deep_learning_gaps.md` (attention/embeddings/reward — orthogonal, still deferred, not touched by this spec)
**Scope:** **COBALT** (library evidence, CHROMA-2) and **TFP** (clinical application, spearhead branch) only.
**Explicitly out of scope:** MRT. MRT was a confirmed-MVP branch on its own 96-family grid; it does not
share sealed core geometry with the 288-family production line this expansion targets, and the operator
has closed it as MVP-complete. No evidence type, gate, or context tag in this spec should reference MRT,
its grid, or `hesperia_mrt`. If a future need arises to re-open that branch, it gets its own spec.

---

## 0. What this spec is, in one paragraph

`sphere/fpf_bridge/evidence_mapper.py` currently wraps exactly **7 signal types** (5 rule types,
raw area activations, one stability score) out of roughly **239–248 named L1–L9 variables + 41 KME
metrics + 3 TRIZ export families** the sealed pipeline already computes. This spec inventories every
one of those unexposed variables, marks which are real candidates for evidence-ification vs which are
structurally unfit (stub constants, internal-only handoffs), and specifies the mapper functions, FGR
calibration, and gates needed to bring the qualifying ones into `bridge_to_llm_prompt()`'s evidence
set — so an LLM agent (Felix, Cursor, or any FPF-aware caller) reasons over the same named,
FGR-scored vocabulary Hesperia already computes, rather than a hand-picked sliver of it. Nothing here
touches sealed `/analyze`; every addition is strictly downstream and read-only, same discipline as
`corners/fpf_bridge.md` already documents for the existing 7.

---

## 1. Full parameter inventory — candidates for evidence-ification

Source: `docs/foundations/output_catalog.md` (verified letter-for-letter against implementing code).
Status column: **EXPOSED** (already an `EvidencePrimitive` today) / **CANDIDATE** (real, live-computed,
worth wrapping) / **UNFIT** (stub constant, internal-only handoff, or reserved-zero — wrapping it would
hand the LLM a number that looks like evidence but carries no signal).

### 1.1 L1 — structural activation census (27 base + up to 6 profile)

| Variable | Status | Why |
|---|---|---|
| `STRUCTURAL_STABILITY_INDEX` | **CANDIDATE** | Feeds L7 `SYSTEM_CONFIDENCE_SCORE`; a real per-run composite, not yet its own evidence primitive (today only the *downstream* stability score from `dynamism_metrics` is wrapped, not L1's own) |
| `FAMILY_ENTROPY` / `NORMALIZED_FAMILY_ENTROPY` | **CANDIDATE** | Directly what `entropy_drop` rule type gestures at, but the raw value itself isn't visible to the LLM today — only the boolean "a drop event fired" |
| `GINI_COEFFICIENT` | **CANDIDATE** | Concentration signal, cheap to add, useful for TFP (hit-distribution skew across clinical concept families) |
| `SIGNAL_TO_NOISE_RATIO` | **CANDIDATE** | Direct "how clean is this read" signal, currently invisible |
| `COVERAGE_RATIO` | **CANDIDATE** | Already gates L9 `ACTION_REQUIRE_MORE_INPUT`; agent-visible version lets the LLM reason about "not enough signal" *before* being told to ask for more input, not after |
| `PROFILE_CONFORMANCE_SCORE` + `FORBIDDEN_MASS_PENALTY`/`ALTITUDE_DEVIATION`/`BUDGET_VIOLATION_SCORE` | **CANDIDATE (conditional)** | Only present when a structure profile is active — real for TFP if/when session profiles are used; skip if no profile path exists yet in the TFP branch |
| Everything else in L1 (tokens, norms, ratios not named above) | **UNFIT for v1** | Real numbers, but redundant with the composites above for an LLM-facing evidence set — adding all 27 would recreate the "raw dump" problem the bridge exists to avoid. Revisit per-field only if a specific TFP/COBALT gate needs one. |

### 1.2 L2 — topology traversal (27)

| Variable | Status | Why |
|---|---|---|
| `GEOMETRIC_STABILITY_INDEX` | **CANDIDATE** | Feeds L7/L9 `PILLAR_GEOMETRY`; a genuine composite worth its own evidence primitive |
| `CROSS_AREA_RATIO` | **CANDIDATE** | Directly interpretable as "is the dominant read leaking outside its own area" — relevant to TFP (is a clinical read staying inside one construct or bleeding across unrelated ones) |
| `LOOP_DENSITY` | **CANDIDATE** | Cheap, real, feeds `GEOMETRIC_STABILITY_INDEX` already — exposing it separately lets the LLM distinguish "unstable because leaking" from "unstable because looping" |
| `VISITED_IDS`, `MASS_AT_DEPTH` | **UNFIT** | Explicitly internal handoffs to L3/L6 per the code's own comments — not designed as terminal, human/LLM-facing values |
| Remaining traversal counts/ratios | **UNFIT for v1** | Same "don't recreate the raw dump" reasoning as L1 |

### 1.3 L3 — baseline/shadow comparison (25)

| Variable | Status | Why |
|---|---|---|
| `SHADOW_DEVIATION_SCORE` / `SHADOW_ACCEPTABILITY_GATE` | **CANDIDATE** | Only meaningful when a shadow run exists (perturbation-robustness check) — real signal for TFP research work when a session is re-run with a perturbed variant, currently invisible to the LLM entirely |
| `VISITED_JACCARD_SIMILARITY` | **CANDIDATE (secondary)** | Useful confirmatory signal alongside `SHADOW_DEVIATION_SCORE`; skip unless shadow runs become routine in the TFP workflow |
| Remaining deltas | **UNFIT for v1** | Only meaningful in aggregate (already rolled into `SHADOW_DEVIATION_SCORE`) |

### 1.4 L4 — evidence retrieval (25)

| Variable | Status | Why |
|---|---|---|
| `EVIDENCE_SUPPORT_INDEX_BASELINE` | **CANDIDATE — high priority** | The single most load-bearing L4 output; directly relevant once COBALT is piping library evidence — "how well does the retrieved library evidence actually support the dominant read" is exactly the kind of claim an FPF-aware agent should see with its own FGR, distinct from COBALT's own retrieval-quality metadata |
| `INTEGRITY_CHECK_PASS_RATIO` | **CANDIDATE** | Hard-gates L7 `g6`; worth surfacing directly rather than only via the downstream boolean |
| `RETRIEVAL_SHORTFALL_BASELINE` | **CANDIDATE** | Directly actionable ("ask for more evidence") signal, currently only visible as an L9 action trigger after the fact |
| Remaining book/family/area match ratios | **UNFIT for v1** | Redundant with `EVIDENCE_SUPPORT_INDEX_BASELINE`, which already blends them |

### 1.5 L5 — counter-evidence & contradiction (25) — **the pilot slice**

| Variable | Status | Why |
|---|---|---|
| **`CONTRADICTION_PRESSURE_SCORE`** | **CANDIDATE — pilot, build first** | Real, computed, tested, exactly the worked example from the prior conversation. This is the one that gets an actual gate (§5), not just an evidence wrapper. |
| **`REALITY_GATE_COUNTER_EVIDENCE`** | **CANDIDATE — pilot, build first** | The hard AND-gate behind the pressure score; exposing both the continuous score and the boolean gate lets the LLM distinguish "pressure is elevated but still within policy" from "pressure exceeds policy, gate failed" |
| `ANTI_REGION_SIZE`, `NEG_SUPPORT_INDEX` | **CANDIDATE (secondary)** | Useful decomposition of *why* pressure is high — add once the primary score/gate pair is live and proven useful, not before |
| 5B trig/metric-space residuals (13 fields, 6 hardcoded 0.0) | **UNFIT** | Six of thirteen are literal reserved constants for a non-deterministic-input mode that doesn't exist yet — wrapping these as "evidence" would hand the agent numbers that look measured but are placeholders. `REALITY_GATE_TRIG` (the AND of all 13) is already implicitly covered by existing gate logic; do not expose the residuals individually. |

### 1.6 L6 — dynamical stability scaffold (25, 21 of which are stubs)

| Variable | Status | Why |
|---|---|---|
| `GLOBAL_STABILITY_SCORE` | **CANDIDATE** | One of only 4 genuinely live fields in this layer; feeds L7/L8/L9 `PILLAR_STABILITY` |
| `CONCEPTUAL_COHERENCE_INDEX` | **CANDIDATE** | Also genuinely live; a real composite worth its own primitive |
| `DEPTH_GROWTH_RATIO`, `FIBONACCI_DEVIATION_SCORE` | **CANDIDATE (secondary)** | Live, but narrower/more technical — lower priority than the two composites above |
| The other 21 fields | **UNFIT, hard rule** | Documented no-perturbation identity stubs (`0.0`/`1.0`/`True`/`False` by construction). Wrapping a stub as an `EvidencePrimitive` is the single worst mistake this expansion could make — it would hand the agent something indistinguishable in shape from real evidence that is, by the layer's own docstring, not measuring anything yet. **Do not expose any L6 field not explicitly marked live in `output_catalog.md` §6.** |

### 1.7 L7 — consistency and decision (25 base + up to 3 conditional) — **high-value tier**

| Variable | Status | Why |
|---|---|---|
| **`TRUST_TIER`** | **CANDIDATE — high priority** | Named in the original ask directly. A 4-level (0–3) verdict already computed from the gate cascade — natural evidence primitive with FGR scaled by tier itself |
| **`SYSTEM_CONFIDENCE_SCORE`** | **CANDIDATE — high priority** | The single most-aggregated number in the system (four-factor product across L1/L2/L4/L5/L6). Exposing this directly, with high formality (it's a well-defined composite) and reliability scaled to its own value, gives the agent the closest thing Hesperia has to "how much should you trust this whole read," in one field. |
| **`DECISION_STATUS_CODE`** | **CANDIDATE — high priority** | Named in the original ask directly. Already a clean enum (0 = pass, 10–70 = which gate failed first, 75 = profile-conformance). Maps almost directly onto an FPF gated-transition concept: this *is* "which gate blocked you," already computed. |
| `CONTRADICTION_ADJUSTED_SUPPORT` | **CANDIDATE (secondary)** | The specific field where L4 support and L5 contradiction are already combined — useful once both L4 and L5 evidence exist, as a cross-check |
| `OUTPUT_TRUST_TAG` | **CANDIDATE (secondary)** | Human-readable HIGH/MED/LOW; redundant with `TRUST_TIER` numerically but may read better inline in an LLM prompt |
| The 10 `CONSIST_*` gate booleans (`g1`–`g10`) | **UNFIT for v1** | Already fully summarized by `TRUST_TIER` and `DECISION_STATUS_CODE`; exposing all 10 individually recreates the raw-dump problem this whole discipline exists to avoid |

### 1.8 L8 — unit standardization (30)

| Variable | Status | Why |
|---|---|---|
| All `SI_*_U1000`/`SI_*_PCT` fields | **UNFIT, structurally** | L8's entire job is re-expressing L1–L7 composites on a different scale — no new information, pure rescale. Exposing both the L7-native value and its L8 rescale as two separate "pieces of evidence" would double-count the same signal under two names. **Skip L8 entirely as an evidence source; if a scale is needed for LLM-facing prose, do the rescale at prompt-formatting time, not as a second primitive.** |

### 1.9 L9 — pillars, brand labels, actions (25) — **terminal, mostly redundant by design**

| Variable | Status | Why |
|---|---|---|
| `PILLAR_*_U1000` (6 fields), `BRAND_WORD_*` (5 fields) | **UNFIT for evidence, but keep as prose vocabulary** | These are L9's whole purpose: human-facing labels *derived from* the composites already captured above (L7's `TRUST_TIER`/`SYSTEM_CONFIDENCE_SCORE`, L2's `GEOMETRIC_STABILITY_INDEX`, etc.). Feeding them back in as "evidence" would be citing a summary of the evidence as if it were independent evidence. They belong in the LLM's *output vocabulary* (the words it's allowed to use when narrating), not its *input evidence set*. |
| `ACTION_*` (4 fields) | **CANDIDATE, different mechanism** | These are already close to gate-shaped ("require more input," "require evidence rebuild," "require governance review," "allow human summary"). Rather than wrapping them as `EvidencePrimitive`s, they map more naturally onto **new `GateCheck`s** directly (§5) — an action trigger *is* a gate condition, not evidence for one. |

### 1.10 KME — 6 primitives + 35 derived metrics (41 total) — **richest untapped pool**

| Variable group | Status | Why |
|---|---|---|
| 6 primitives (`LD`, `COH`, `NC`, `PR`, `PV`, `CI`) | **CANDIDATE — high priority** | Bounded `[0,1]`, independently meaningful, already the input to everything else in KME. **Correction from an earlier draft of this spec**: these are core Hesperia semantics — domain-agnostic measures over *any* activated concept graph (`corners/kme.md` never scopes KME to a domain) — not clinical/TFP-exclusive. TFP was simply the first corpus they were validated against (`clinical_bridge.py`'s name reflects that history, not a domain restriction). `COH` (does the activated subgraph hold together as one structure) and `NC` (how much of the reference domain graph was actually touched) are generically meaningful for TFP, COBALT-retrieved library content, or any future domain — default evidence context is `CONTEXT_ID` (core), same as L4/L5/L7. |
| `KSI` (KME-KSI-score) | **CANDIDATE** | Already disambiguated in canon from KSI-Inspector; a real, named, formula-verified ratio (`clamp01(safe_div(COH*LD, PR))`) — good single-field efficiency signal |
| Remaining 34 derived metrics | **CANDIDATE, staged rollout, not all at once** | All are `clamp01`/`safe_div` algebra over the same 6 bounded primitives — genuinely safe to expose (no new failure modes beyond the two already proven: `clamp01`, `safe_div`), but 34 additional evidence primitives in one prompt would overwhelm the "menu, not dump" design. **Stage this**: primitives first, then a hand-picked 5–8 derived metrics chosen by Colombo/TFP research relevance (candidates: `CDR` contradiction-density-related, `TCI`/`CII` coherence-related — actual selection needs Colombo's clinical judgment, not an engineering guess), full 35 only if the staged subset proves useful in practice. |
| Fingerprint hash itself | **UNFIT as evidence** | It's a comparison artifact (cross-run/cross-document), not a claim about the current run — wrong shape for `EvidencePrimitive` |

### 1.11 TRIZ — 3 export families (contradiction/innovation/narrative)

| Export | Status | Why |
|---|---|---|
| Policy Contradiction Detector (`contradiction_score`, `contradiction_density`, `triz_principle`) | **CANDIDATE** | A second, independently-computed contradiction signal (different mechanism than L5's `CONTRADICTION_PRESSURE_SCORE` — this one works over the KME active-graph via typed relations, not counter-evidence retrieval). **Correction from an earlier draft**: TRIZ is a general-purpose Hesperia mechanism — a problem/contradiction/solution-path advisor derived from Altshuller's TRIZ (Theory of Inventive Problem Solving; `corners/triz_extension.md`), not a COBALT-exclusive tool. Analyzing COBALT-retrieved library content is one application of it, not what it is. Worth exposing separately, clearly labeled as a distinct mechanism from L5's score, defaulting to the same core context — never merged with L5's score, and not assumed to only matter for COBALT. |
| Innovation Radar / Narrative Propagation Monitor | **UNFIT for v1** | Real and well-built, but scoped to a "decision-intelligence product" audience (policy/innovation buyers), not obviously relevant to either COBALT's library-retrieval role or TFP's clinical role. Leave out unless a concrete TFP or COBALT use case names one of these fields specifically. |

### 1.12 Summary — what actually gets built in Phase 1

Ranked by the inventory above, the v1 build list (everything marked **CANDIDATE — high priority** or
**pilot**, nothing marked UNFIT or staged-later):

1. `CONTRADICTION_PRESSURE_SCORE` + `REALITY_GATE_COUNTER_EVIDENCE` (L5) — pilot, with the new gate (§5)
2. `TRUST_TIER`, `SYSTEM_CONFIDENCE_SCORE`, `DECISION_STATUS_CODE` (L7)
3. `EVIDENCE_SUPPORT_INDEX_BASELINE` (L4) — the COBALT-relevant one
4. KME's 6 primitives, led by `COH`/`NC`/`KSI`
5. TRIZ's Policy Contradiction Detector output, clearly namespaced apart from L5's contradiction signal

Everything else in the inventory is either explicitly deferred to a later staged pass (KME's remaining
34 metrics) or ruled out on structural grounds (L6 stubs, L8 rescales, L9 pillar/brand labels, 5B trig
residuals) — those exclusions are permanent, not "later," unless the underlying code changes (e.g. L6's
stub fields become genuinely live).

---

## 2. New evidence mapper functions (`sphere/fpf_bridge/evidence_mapper.py`)

Same pattern as the existing five rule-type handlers — each new function takes the relevant layer's
output dict, returns `list[EvidencePrimitive]`, and gets its own FGR calibration table in
`constants.py`, following the existing `RULE_FGR_HIGH`/`RULE_FGR_LOW` convention:

| New function | Reads from | Emits |
|---|---|---|
| `map_contradiction_to_evidence(l5_metrics)` | L5 output | `contradiction_pressure`, `counter_evidence_gate` |
| `map_decision_state_to_evidence(l7_metrics)` | L7 output | `trust_tier`, `system_confidence`, `decision_status` |
| `map_evidence_support_to_evidence(l4_metrics)` | L4 output | `evidence_support_baseline` |
| `map_kme_primitives_to_evidence(kme_metrics)` | `clinical_bridge.py` output | one primitive per bounded `[0,1]` value: `kme_ld`, `kme_coh`, `kme_nc`, `kme_pr`, `kme_pv`, `kme_ci`, plus `kme_ksi` |
| `map_triz_contradiction_to_evidence(triz_export)` | TRIZ Policy Contradiction Detector | `triz_contradiction` (explicitly labeled distinct from `contradiction_pressure`) |

`collect_all_evidence()` gets each of the above added as an optional argument (default `None` →
function returns `[]`, same "absent field = today's behaviour" discipline COBALT's schema already
uses), so this is additive and cannot regress any existing caller.

### 2.1 FGR calibration guidance

- **`contradiction_pressure`**: formality high (it's a well-defined weighted composite, `0.55·neg_support + 0.25·(1−pos_support) + 0.20·bookset_jaccard`), reliability scaled inversely with how close to policy cap it sits (near the cap = less confident this is "clean" contradiction vs. borderline noise).
- **`trust_tier` / `system_confidence` / `decision_status`**: formality very high — these are the most rigorously defined composites in the system, each with a traceable formula. Reliability should scale with `TRUST_TIER` itself (tier 3 → high reliability; tier 0 → the evidence is "this whole run failed gate 1," which is itself highly reliable information, just about failure).
- **`evidence_support_baseline`**: formality moderate-high, reliability scaled by `INTEGRITY_CHECK_PASS_RATIO` (a shaky integrity check should discount how much the support number itself can be trusted).
- **KME primitives**: formality high (bounded, deterministic, `clamp01`-proven), reliability moderate by default — these are new to the bridge and haven't accumulated the same track record as the L1–L9 pipeline; do not start them at the same reliability ceiling as `dominant_area`.
- **`triz_contradiction`**: formality moderate (four-principle reduction, hash-fallback classification is deliberately coarse), explicitly namespaced so the LLM never conflates it with `contradiction_pressure` — different mechanism, different meaning, same English word.

---

## 3. Bounded-context tagging (reinstating FPF's `U.BoundedContext`, narrowly)

Today `FGR.scope` is a flattened float. With COBALT and TFP as the only two live application contexts,
add an explicit `context_scope` field (string enum: `"core"` / `"tfp"` / `"cobalt"`) to every
`EvidencePrimitive` produced by the new mappers above — **not** the existing five, which stay
`"core"` implicitly (they come from the sealed engine itself, not a branch).

- L5, L7, L4 composites: `context_scope="core"` (they're computed by the sealed pipeline, branch-agnostic).
- KME primitives default to `context_scope="core"` (domain-agnostic engine semantics, see the
  correction in §1.10) — a caller may set `context_scope="tfp"` explicitly for a specific run it
  knows was computed from TFP session content, but that is a property of that run's input, not
  of what KME measures.
- TRIZ Policy Contradiction Detector output defaults to `context_scope="core"` (general-purpose
  mechanism, see the correction in §1.11); a caller analyzing specifically COBALT-retrieved
  library chunks may set `context_scope="cobalt"` explicitly for that run.

This is the concrete, narrow piece of FPF's bounded-context concept worth reinstating — not the
philosophical apparatus, just the one guarantee it buys: **an agent must not apply a TFP-scoped signal
to a COBALT-scoped question, or vice versa**, and now it can check that mechanically instead of
inferring it from field names.

---

## 4. The FPF library itself as the shared stage

Everything above treats `fpf-thinking-map` as a mechanism. This section names it as what it actually
is for this spec: the **shared reference layer both sides read from** — the "stage where the whole
spectacle meets," per the operator's framing. Not executed as prose at runtime by either side (that
would reintroduce the non-determinism `corners/fpf_bridge.md` exists to avoid), but the naming
authority both the evidence taxonomy in §1–§3 and any FPF-aware agent should check against, so that
when Hesperia's code says `GateCheck` and an agent reasons about "a gate," both mean the same
FPF-anchored concept — not two independently invented words that happen to collide (the exact
discipline `provenance.md` already applies to keep Sigma/Gamma/Theta explicitly *not* derived from
FPF's own Γ, despite the letter overlap).

### 4.1 Verified anchors — every primitive this spec uses, traced to its actual FPF section

Checked directly against `fpf_thinking_map/primitives.py`'s own docstrings (installed package,
`.venv/lib/python3.12/site-packages/fpf_thinking_map/primitives.py`), not guessed — same
grep-before-claiming discipline as `provenance.md`:

| Hesperia/bridge mechanism | FPF spec anchor | Verified how | Status |
|---|---|---|---|
| `GatePrimitive` / `GateCheck` | **A.21 — GateProfilization (`OperationalGate`)** | Docstring: "FPF A.21: gates aggregate GateChecks via join-semilattice. Gate ≠ commitment (structural vs deontic)." | Verified derivation |
| `FGR` (F–G–R trust tuple) | **B.3 — Trust & Assurance Calculus** | Docstring: "Trust tuple — FPF B.3 Trust & Assurance Calculus." | Verified derivation |
| `EvidencePrimitive` (+ freshness/decay) | **A.10 — Evidence Graph**, **B.3.4** | Docstring: "FPF A.10: claims must be supported by evidence with traceability. FPF B.3.4: evidence decays." | Verified derivation |
| `TransitionPrimitive` / the 5-state graph | **A.3.3 — U.Dynamics**, **B.4 — Canonical Evolution Loop**, **A.2.5 — U.RoleStateGraph** | Docstring cites all three directly | Verified derivation |
| `context_scope` (this spec, §3) | **A.1.1 — `U.BoundedContext`** | FPF section exists and is the named source of the bounded-context idea; the `context_scope` field itself is new (introduced by this spec), correctly modeled as one narrow instance of that concept — **not** an import of FPF's fuller **A.2.6 Unified Scope Mechanism** (context slices/scopes), which stays out of scope here | Concept anchor verified; field is new, deliberately narrow |
| Sigma / Gamma / Theta guards | *(none)* | `provenance.md`: `grep -c 'Sigma\|Theta' FPF-Spec.md` → 0 matches in 51,305 lines | **Confirmed non-derivation** — keep these explicitly separate from FPF's Γ; do not relabel them as FPF-sourced anywhere in this expansion |

### 4.2 Capability already paid for, currently dormant — activate as part of this expansion, not later

`fpf-thinking-map` ships more machinery than the existing bridge code uses. None of the following
require a new dependency or a new spec elsewhere — they're already installed, already imported,
already part of the same library this whole bridge is built on. Wiring them into Phase 1 (§7) costs
far less than the impression of "add all parameters" might suggest, because most of the work is
*using what's already there* rather than building new primitives:

1. **`EvidencePrimitive.contradicts: list[str]`** — a native field on every evidence primitive
   today, never set by `evidence_mapper.py`. `map_contradiction_to_evidence()` (§2) should populate
   it directly: when `contradiction_pressure` evidence is emitted, list the specific evidence_ids it
   contradicts (e.g. a specific `rule_dominant_area` or KME primitive it's in tension with). This is
   the literal, already-built FPF mechanism for "contradiction high" — expressed as a structured
   evidence-to-evidence relation, not a lone floating score the agent has to interpret unaided.

2. **`GateDecision`'s 4-value outcome lattice** (`ABSTAIN ≤ PASS ≤ DEGRADE ≤ BLOCK`) — richer than a
   binary pass/fail. `gate_contradiction_block` (§5) should be designed to actually produce `DEGRADE`
   (proceed with caution, evidence incomplete or borderline) as a distinct, real outcome from `BLOCK`
   (hard denial) — not collapsed to a boolean. This is what gives "contradiction high → avoid" a
   middle setting instead of only on/off, and the lattice already exists; nothing new to build.

3. **`SemanticFloor` + `computed_ttl`** (evidence decay) — completely unused today; no evidence
   primitive in the current bridge sets `semantic_floor` or `ttl_steps`, so nothing the bridge
   produces ever expires. For TFP specifically — a session happens at a point in time, and an old
   session's contradiction reading should not silently keep gating a new, unrelated session — tagging
   the new evidence types with `SemanticFloor.EVIDENTIARY` (matching B.3/B.3.4, the same floor FGR
   itself lives on) turns on real, already-implemented decay: `max(1, round(F × R × 8))` steps,
   computed from the same FGR values this spec already calibrates in §2.1. No new decay logic to
   write — just set the field.

4. **`ContextPrimitive.glossary`** — the literal shared-vocabulary registration point in
   `bridge.py::_build_semantic_map`. Currently 6 terms (`area`, `family`, `tension`, `dominance`,
   `propagation`, `stability`). Extend it with the terms this spec introduces —
   `contradiction_pressure`, `trust_tier`, `bounded_context`/`context_scope` — so the semantic map
   defines its own vocabulary in the same object the agent reads, rather than the agent needing this
   spec document alongside the live map to know what a term means. This is the most direct
   implementation of "same scene for both to understand each other": the definitions live in the
   artifact both sides consume, not only in this prose.

5. **`RolePrimitive` / `CommitmentPrimitive`** — currently exactly one role (`structural_analyst`)
   and one commitment (`evidence_coverage`). A `librarian` role scoped to `context_scope="cobalt"`
   and a `clinical_researcher` role scoped to `context_scope="tfp"`, each with their own
   `DeonticModality.SHOULD`/`MUST` commitments, is a natural Phase 3/4 addition once the branch-scoped
   evidence from §3 exists — **flagged here, not built in Phase 1**; don't front-load it before the
   contradiction pilot is proven.

### 4.3 What this means for "rebuilding the map based on library FPF"

The inventory in §1 decides *which Hesperia-computed values* become evidence. This section is the
other half: *how those values get expressed* so they're legible in FPF's own terms, using mechanisms
the dependency already provides rather than inventing Hesperia-specific equivalents beside them. Once
§4.2's five items are wired, the semantic map (`SemanticMap` built in `bridge.py`) genuinely is the
single artifact where Hesperia's measurements and an FPF-aware agent's reasoning vocabulary coincide —
not because the philosophical apparatus was reintroduced, but because the operational slice already
kept (gates, evidence, transitions, context) is being used to its actual, already-built capacity
instead of a fraction of it.

## 5. New gate: contradiction (the pilot, build and prove this first)

`sphere/fpf_bridge/state_graph.py` gets one new `GatePrimitive`:

```python
GatePrimitive(
    gate_id="gate_contradiction_block",
    label="Contradiction pressure block",
    context_id=context_id,
    checks=[
        GateCheck(
            check_id="chk_contradiction_within_policy",
            description="Contradiction pressure must be within policy cap to proceed",
            required_evidence=["counter_evidence_gate"],  # = L5 REALITY_GATE_COUNTER_EVIDENCE
        ),
    ],
    fail_closed=True,
)
```

Applied to any transition where `contradiction_pressure` evidence is present and the corresponding
`counter_evidence_gate` boolean is `False` — the transition is blocked, not just annotated. This is
what turns "the agent can see the number" into "the agent is structurally prevented from concluding X
while contradiction is high": the gate mechanism already exists and already works this way for the
other 6 gates in the file; this is the same pattern applied to a signal that was previously invisible.

Once this pilot gate is live and proven (i.e., at least one real run where it actually blocks a
transition it should block, per COBALT-19-style gold test discipline), the same pattern extends to
`trust_tier`/`decision_status` gating and the `ACTION_*` fields from §1.9 — but **ship the
contradiction gate alone first** and validate it before adding more gates in the same pass.

---

## 6. Env flags and rollout discipline

Same pattern as `HESPERIA_FGR_FREEZE` / `HESPERIA_COBALT_ENABLED` — every addition here defaults off:

| Flag | Default | Effect |
|---|---|---|
| `HESPERIA_FPF_EVIDENCE_EXPANSION` | `0` | When `1`, `collect_all_evidence()` includes the new mapper outputs (§2) |
| `HESPERIA_FPF_CONTRADICTION_GATE` | `0` | When `1`, `gate_contradiction_block` (§5) is active and can actually block a transition |
| `HESPERIA_FPF_KME_EVIDENCE` | `0` | When `1`, KME primitives (§1.10) are included — separate flag because it's a new data source (`clinical_bridge.py`), not just a new field on existing data |

No flag here changes `sphere/` — every new mapper function reads already-computed output dicts, exactly
as the existing five do. The "sphere stays deterministic, fpf_bridge is a pure consumer" guarantee from
`corners/fpf_bridge.md` is unmodified by this spec.

---

## 7. Phase plan

| Phase | Scope | Gate default |
|---|---|---|
| **0** | Ethan ratify this spec | — |
| **1** | Contradiction pilot: `map_contradiction_to_evidence`, `gate_contradiction_block` using `DEGRADE`/`BLOCK` (§4.2.2), `contradicts` wired on the new evidence (§4.2.1), `EVIDENTIARY` floor decay (§4.2.3), glossary terms added (§4.2.4), gold test proving it actually blocks a bad transition | off |
| **2** | L7 trio (`trust_tier`, `system_confidence`, `decision_status`) + L4 `evidence_support_baseline` | off |
| **3** | KME primitives (6) via `clinical_bridge.py`, core-scoped by default (see §1.10 correction) | off |
| **4** | TRIZ Policy Contradiction Detector, core-scoped by default (see §1.11 correction), clearly namespaced apart from L5's signal — when applied to COBALT-retrieved library content specifically, **precondition: `fpf_bridge_v7_4_cobalt_corpus_scaleup.md` exit criteria passed**, not just `HESPERIA_COBALT_ENABLED=1` | off |
| **5** | Staged rollout of hand-picked KME derived metrics (Colombo selects, not engineering default) | off |
| **6** | Operator + Ethan review of Phase 1–5 in practice → decide prod flag-on, same discipline as COBALT's G1–G5 gates | — |

Branches do not block each other within this plan the same way COBALT/TFP don't block each other at the
architecture level — Phase 3 (TFP/KME) and Phase 4 (COBALT/TRIZ) can run in parallel once Phase 1–2 are
proven.

---

## 8. Exit criteria (this spec's MVP)

- [x] Full parameter inventory (§1) reviewed by Ethan (2026-07-19) — structure + Phase 1 build list ratified; Colombo still owns Phase 5 KME derived selection (FBV72-04b)
- [x] Phase 1 (contradiction pilot) gold test landing — FBV72-01 DONE (code + tests; flags default off)
- [x] `context_scope` / ContextPrimitive tagging — FBV72-03 DONE (ContextPrimitive registration path)
- [x] §4.2 dormant-capability items reviewed — Phase 1 wiring landed under FBV72-01; roles/commitments stay deferred
- [x] No change to sealed `/analyze` determinism tests (downstream-only consumer)
- [x] All new flags default off
- [x] Register rows on `active.md` for Phase 1–4 execution (Grace triage) — FBV72-01..05

**Still open (not blocking this ratification):** FBV72-04b Colombo Phase 5 KME derived selection; prod flag-on remains Phase 6 / operator+Ethan after practice.

---

## 9. Ratification

| Role | Action | Date | Status |
|---|---|---|---|
| Felix | Draft spec (inventory + mapper/gate design) | 2026-07-04 | DONE |
| Ethan | Ratify / amend | 2026-07-19 | **RATIFIED** |
| Colombo | Review KME derived-metric selection (§1.10, Phase 5) and TFP relevance judgments throughout §1 | — | PENDING (FBV72-04b) |
| Grace | Triage Phase 1 execution rows | 2026-07 | DONE (FBV72 rows live) |

### Ethan ratification notes (2026-07-19)

1. **Architecture:** Downstream-only evidence expansion; sealed `/analyze` untouched; flags default off — **accepted**.
2. **MRT out of scope** — **accepted** (closed MVP, different grid).
3. **Mid-build corrections ratified into canon:** KME primitives and TRIZ Policy Contradiction Detector are **core** Hesperia semantics (domain-agnostic), not TFP-/COBALT-exclusive — matches FBV72-04a / FBV72-05 DONE rows and §1.10 / §1.11 corrections already in this file.
4. **Phase 5:** Remaining 34 KME derived metrics stay **Colombo-selected** (FBV72-04b) — engineering must not default the menu.
5. **Catch-up:** Phase 1–4 code shipped under Felix self-ratify for build; this row is the formal team-facing ratification of the spec those rows implemented.

`SIGNED: Developer (Felix) | Claude Code context | 2026-07-04 | fpf_bridge v7.2 evidence expansion spec draft`

`SIGNED: Architecture (Ethan) | Hesperia day run | 2026-07-19 | FBV72-00 RATIFIED — inventory + Phase 1–4 design; Colombo Phase 5 still open`

# Hesperia formalization — General thought propagation, hex orientation, and surface coherence

**Document ID:** `23_SPEC__General_Thought_Propagation_and_Hex_Orientation_v0_1`
**Short name:** **GTP** (General Thought Propagation) / **GTPA** (algorithm)
**Status:** IMPLEMENTED v0.1 (2026-07-19) — see §0.1 below. Original text (unchanged) starts at §0.
**Authority:** Ethan (governance) for the spec; Felix (Claude Code) for the v0.1 implementation.
**Plane:** Sphere logic expansion on `HexSphere` + **IPoW** coupling.
**Depends on:** [HESPERIA-FORMALIZATION-GEODESIC-SPHERE-AND-INTERIOR-POINT-OF-WORLD-VIEW-v0_1.md](../brain-export/operational/assignments/HESPERIA-FORMALIZATION-GEODESIC-SPHERE-AND-INTERIOR-POINT-OF-WORLD-VIEW-v0_1.md) (`22_SPEC__`, GCS, IPoW) — only the PointZero/PointZeroDelta slice; full GCS/IPoW (anchor_map_v1) remains a separate, operator-gated implementation wave per `22_SPEC` §12.
**Source:** `docs/brain-export/operational/assignments/HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md` (brain draft, unchanged, kept as the historical record).
**Added:** 2026-05-24. **Implemented:** 2026-07-19 (GTP-01..08, closing a false-`DONE` mismatch found on `active.md` — the rows were marked DONE with no supporting code prior to this pass).

---

## 0.1 Implementation status (2026-07-19)

All eight backlog items (GTP-01..08) are implemented in `sphere/topology/gtp/`:

| ID | Module | Notes |
|----|--------|-------|
| GTP-01 | `sphere/topology/gtp/side_operators.py` | `LogicalOperator` L_0..L_5, RO/EN `SemanticOperator` pairs, `FARA` reserved, `INV-*` self-checks |
| GTP-02 | `schemas/gtp/gtp_v0_1.schema.json`, `tests/fixtures/gtp/gtp_v0_1_fixture.json` | Schema matches the real `gtp_step_to_dict()` output shape, not a literal re-statement of §13's placeholder JSON |
| GTP-03 | `sphere/topology/gtp/rotation.py` | `hex_rotation` calibration, `m_s` match, `phi(input)` as a minimal deterministic token set |
| GTP-04 | `sphere/topology/gtp/ipow.py`, `sphere/topology/gtp/coherence.py` | PointZero-scoped `InteriorPointOfWorldView` slice only; `Psi` broadcast/aggregate |
| GTP-05 | `sphere/topology/gtp/neighbors.py`, `sphere/topology/gtp/gtpa.py` | `N(h)`, `Score(h')`, deterministic argmax + tie-break |
| GTP-06 | `sphere/topology/gtp/imprint.py`, `sphere/topology/gtp/pipeline.py` | `ThoughtImprint`, `ImprintDifference`, `run_gtp_step()` end-to-end entrypoint |
| GTP-07 | `sphere/router/envelope_v0_1.py`, `sphere/router/pre_llm_compiler.py` | Optional `gtp` envelope field, flag-gated by `HESPERIA_GTP_ENABLED` (default off) + explicit `context_packet["gtp_current_hex"]`; absent = today's behavior, same discipline as `HESPERIA_COBALT_ENABLED` |
| GTP-08 | `tests/gtp/test_gtp_gold.py` | 5-case deterministic gold matrix, pinned |

Tests: `tests/gtp/` (unit, ~50 cases) + `tests/router/test_gtp_envelope_wiring.py` (5 cases). All green locally and in CI (`Sealed runtime gate`).

### Two scoping decisions made explicit, not silently patched

1. **No `40_POLICY__Loopability_and_traversal` exists.** §10.1 cites it as the source of "legal neighbors" (area ring / family patch / hex index steps). It was never written. `neighbors.py` freezes a rule for `gcs_id="GCS_NU85_v0_1"` using the real icosahedral area adjacency plus a simple deterministic ring rule for family/hex steps — documented in that module's docstring as the frozen rule pending a real `40_POLICY`.
2. **The literal §5.2 rotation formula is mathematically degenerate.** `hex_rotation' = argmax_r Σ_{k=0}^{5} match(...)` sums over a full cyclic permutation of all 6 sides for any fixed `r`, so the sum is identical for every `r` by construction — it cannot discriminate between rotations. **ADR FPF-HSR-02/14 Option B shipped (2026-07-19):** `select_hex_rotation` scores only the primary active side `k=0` per candidate `r` (`sphere/topology/gtp/rotation.py`). Gold: `tests/gtp/test_rotation.py::test_option_b_primary_side_discriminates_includes`. Provisional GapReport tag `hex_rotation_r0_interim` cleared.

**No 22_SPEC / anchor_map_v1 claim is made here.** The 288 family anchor directions used by `coherence.py` are a documented, deterministic placeholder (derived from the real 12 area vertices + a small per-family tangent offset), not the frozen GCS embedding — that remains a separate, operator-gated wave.

### 0.2 How to invoke this today (internal / Python only — no HTTP surface yet)

GTP is **not reachable over `/product/interpret`**. `InterpretBody` (`runtime/shipping/api_main.py`)
only accepts `text`, `mode`, `overlay_hint`, `temp_relation_overlay` — there is no `context_packet`
field on the HTTP request at all, so an external caller has no way to supply `gtp_current_hex` today.
This is a real gap, not an oversight to route around quietly — anyone extending the HTTP contract to
carry `context_packet` should go through the same review D-48 (`API security review — auth, rate
limiting, input validation on /product/interpret`) already applied to the rest of the endpoint.

What works today, Python-level, inside the dev repo:

```python
from sphere.router.pre_llm_compiler import compile_router_envelope

env = compile_router_envelope(
    text,
    context_packet={
        "gtp_current_hex": {"area_id": 0, "global_id": 3, "hex_index": 10},
        "gtp_powv_position": [0.3, -0.2, 0.15],  # optional, defaults to PointZero
    },
)
# env["gtp"] present only if HESPERIA_GTP_ENABLED=1 was also set — absent otherwise.
```

Or standalone, without a full router envelope:

```python
from sphere.router.pre_llm_compiler import compile_gtp_block

block = compile_gtp_block(text, current_hex={"area_id": 0, "global_id": 3, "hex_index": 10})
```

Both return the `hesperia.gtp_v0_1` shape validated by `schemas/gtp/gtp_v0_1.schema.json`.

### 0.3 Forward direction (not built, not scoped yet — recorded here per operator intent 2026-07-19)

Operator intent, stated directly, ahead of any implementation: proceed toward full fpf-thinking-map
integration before sealing, such that the OpenAI API, Felix (Claude Code), Cursor, and MCP servers
using fpf may invoke Hesperia freely and reason over results **on their own** — i.e. agent-autonomous
invocation, not just operator-triggered `/product/interpret` calls.

This is flagged rather than quietly built toward, because it intersects a standing V7 invariant this
same campaign signed off on (`HSR-V7-2026-REGISTER.md` rule 5: "No black-box chain-of-thought treated
as auditable evidence"; D-46 "No-bypass enforcement — verify no code path exists from raw model text
to surfaced authority", security-reviewed by Sophia/Daniel). "Agents may invoke Hesperia freely and
reason on their own" and "no raw-model-text path to surfaced authority without audit" are not
automatically the same thing — the existing router (`compile_router_envelope` → LLM call → post-LLM
audit → `RouterDecision`) already lets an LLM reason over engine output *inside* that audited loop; the
open question this direction raises is whether "freely, on their own" means staying inside that loop
(propose/verify, same as GTP-03's rotation calibration: "LLM may propose; engine must verify
deterministically") or means something looser. That distinction is exactly the kind of thing that
needs its own scoped spec and a fresh security pass before code — not an assumption baked in here.

No new `active.md` row was created for this by me (Felix triages tasks through Grace, not directly)
— this section exists so the intent is on record and traceable to today's date, ready for Grace
triage / Ethan ratification when the operator is ready to scope it.

**Update 2026-07-19, same day:** operator clarified the actual principle directly — *"we dont limit
llm in operationability, only logically and on weights and on sources activated. the rest what it
reasons upon it, kinda - not my job."* This resolves the tension above cleanly (verified against the
D-46 test and rule 5, not just asserted) and is written up as a three-axis model — operational freedom
unrestricted; logical/weight/source-activation always engine-computed and attached; reasoning content
unpoliced — in brain repo `governance/SPEC-ETHAN-HESPERIA-AGENT-AUTONOMOUS-INVOCATION.md` (draft for
Ethan ratification, not yet implemented). GTP-03's propose/verify pattern turns out to already be the
right template for the whole router, not just hex_rotation.

SIGNED: Developer (Felix) | Claude Code context | 2026-07-19 | GTP-01..08 implementation, closing false-DONE on active.md; §0.3 forward-direction note recorded per operator instruction, resolved same day in governance/SPEC-ETHAN-HESPERIA-AGENT-AUTONOMOUS-INVOCATION.md

---

## 0. Document control

| Field | Value |
|-------|--------|
| **Version** | `0.1.0` |
| **Principle** | **As above, so below** — interior **IPoW** in Ω deterministically constrains the next surface move on ∂Ω. |
| **Future product name** | **General thought propagation algorithm** (`gtp.v0_1` / `sphere.thought_propagation`) |

---

## 1. Scope

This specification extends Hesperia **hex logic** without changing **INV-HEX-PER-FAM-SEM** (250) or area/family counts:

1. **Hex orientation** — each **HexCell** may **rotate** in the surface plane (sixfold symmetry). Rotation changes which **logical** and **semantic** operator is "forward" for traversal.
2. **Six sides × dual operators** — each **TruthUnit** side carries:
   - a **logical operator** (programming / set-theoretic), and
   - a **semantic operator** (Romanian preset with English equivalent).
3. **Calibration rotation** — during calibration (LLM-assisted or deterministic), a hex may rotate to align input wording with a **preprogrammed basic logical path** (existing traversal / loopability policy).
4. **`PointZeroDelta` broadcast** — change in **IPoW** relative to **PointZero** is sent to **all** areas and families as one **coherence precursor** field.
5. **Coherence aggregate Ψ** — single large calculable variable (vector + scalar summaries) used to **precalculate** the best **next hex** direction on the surface with **minimal semantic involvement** (logic + imprint + difference vs baseline families/areas).
6. **Path discovery** — new surface paths from **input wording** → logic check → imprint → difference, tied to original area/family anchors, not free-form LLM semantics.

**Out of scope v0.1:** Production code, calibration JSON, LLM prompts, clinical claims.

---

## 2. Normative references

| Ref | Role |
|-----|------|
| `22_SPEC__` GCS + IPoW | Volume Ω, surface ∂Ω, PointZero, GCS_NU85 |
| `40_POLICY__Loopability_and_traversal` | Preprogrammed path templates, borders, loops |
| `20_GEOMETRY__formalized_structure` | HexCell, TruthUnit, six sides |
| `propagation_trace` (TFP) | **Distinct** — graph field propagation; GTP is path/orientation logic |
| `context_rag` `coherence_hints` | Extension point for Ψ |

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **HexOrientation** | Rotation of a HexCell in the tangent plane of ∂Ω; **`hex_rotation`** ∈ {0,…,5} (side index offset) or **`hex_rotation_deg`** ∈ [0,360). |
| **LogicalOperator** | Set-theoretic / programming-style test on input features (includes, excludes, …). |
| **SemanticOperator** | Surface-language relation label (RO preset; EN equivalent). |
| **SideSlot** | One of **6** sides of a hex; **`side_id`** 0..5. |
| **PointZeroDelta** | **`δ_powv`** = change in IPoW position vs PointZero (or step-to-step); broadcast to all area/family anchors. |
| **CoherenceField Ψ** | Aggregated calculable object from **`δ_powv`** + light area/family weights — **one coherence variable** for next-step steering. |
| **ThoughtImprint** | Surface record of which sides/operators fired on input wording (minimal semantic). |
| **ImprintDifference** | Δ between imprint and baseline / prior step — drives path discovery. |
| **GTPA** | General thought propagation algorithm — deterministic next-hex choice given Ψ, orientation, path template. |

---

## 4. Principle — as above, so below

```text
Ω  (volume)                    ∂Ω  (surface)
─────────────────────────────────────────────
IPoW.powv_position  ──Π──►   HexOrientation + exit SideSlot + next HexCell
PointZeroDelta δ    ──B──►   CoherenceField Ψ  ──►  argmax next hex on GCS
```

**Normative:** For frozen **`anchor_map_v1`**, **`gcs_id`**, and path template **P**:

```text
(next_hex, next_side, hex_rotation') = GTPA(
    powv_position_t,
    δ_powv_t,
    current_hex,
    hex_rotation,
    input_wording_features φ,
    path_template P
)
```

**Π** (above-to-below map): projects interior vector to local surface frame (area ring angle, family patch, hex coordinates). **B** (broadcast): distributes **`δ_powv`** to all **12 + 288** anchors (areas + families). **No contradiction** with Apple surface path: Apple walks ∂Ω; GTPA chooses **legal** next step; IPoW supplies **Ω** bias.

---

## 5. Hex orientation (rotation)

### 5.1 State

Each **HexCell** at `(area_id, global_id, hex_index)` carries:

| Field | Type | Meaning |
|-------|------|---------|
| `hex_rotation` | int mod 6 | Permutation offset of side labels (default **0**) |
| `hex_rotation_deg` | float | Optional display: `hex_rotation × 60°` |

**Active side** after rotation:

```text
side_active(k) = (k + hex_rotation) mod 6    for k ∈ {0,…,5}
```

### 5.2 Calibration rotation (thought mimic)

During **calibration** (LLM may propose; engine **must** verify deterministically):

```text
hex_rotation' = argmax_{r ∈ {0,…,5}}  Σ_{k=0}^{5}  match( φ(input), LogicalOperator[side_active(k;r)], SemanticOperator[side_active(k;r)] ) )
```

- **LLM role:** propose candidate `r` or wording→operator alignments.
- **Engine role:** score, select, log provenance; **same input + same pins → same `hex_rotation'`**.

Rotation **mimics thought orientation**: input wording approaches the hex from a different "face" without moving the hex's semantic `(area, family)` anchor.

> **Implementation note (§0.1):** this formula is rotation-invariant as literally written — see §0.1 item 2.

---

## 6. Six sides — logical operators (programming logic)

Each **SideSlot** `s ∈ {0,…,5}` has exactly one **LogicalOperator** `L_s` from the closed set:

| `side_id` | `L_s` (id) | Programming reading | Typical test on input feature set `F` and hex/local set `H` |
|-----------|------------|---------------------|---------------------------------------------------------------|
| 0 | `INCLUDES` | includes / contains | `F ∩ H ≠ ∅` (non-empty intersection) |
| 1 | `NOT_INCLUDES` | does not include | `F ∩ H = ∅` |
| 2 | `SUBSUMES` | covers / implies all | `H ⊆ closure(F)` (configurable closure) |
| 3 | `OVERLAPS` | partial overlap | `F ∩ H ≠ ∅` and `F \ H ≠ ∅` and `H \ F ≠ ∅` |
| 4 | `DISJOINT` | disjoint from | `F ∩ H = ∅` and required separation |
| 5 | `EQUIVALENT` | same extension (under policy) | `symmetric_match(F, H)` |

**Invariant:** **INV-HEX-SIDES-6** — exactly **6** sides; **INV-LOGICAL-OPS-6** — one `L_s` per side in the preset table above (v0.1).

Implementations **MAY** map `L_s` to existing traversal / guard predicates already in the product; GTP **formalizes** the binding to **SideSlot**, not new ad-hoc rules per run.

---

## 7. Six sides — semantic operators (Romanian preset, English equivalent)

Romanian surface labels (operator-endorsed preset) and **English equivalents** for docs/code:

| `side_id` | RO (semantic) | EN (equivalent) | Role on surface |
|-----------|---------------|-----------------|-----------------|
| 0 | **cu** | **with** | comitative / accompaniment |
| 1 | **din** | **from** | source / origin |
| 2 | **la** | **at** / **to** | location / goal |
| 3 | **spre** | **toward** | direction |
| 4 | **după** | **after** | temporal / sequential follow |
| 5 | **pentru** | **for** | purpose / beneficiary |

### 7.1 Reserved — **fără** (without)

| Term | Status |
|------|--------|
| **fără** | **WITHOUT** — exists in Romanian operator vocabulary; **stateless / undefined** in v0.1 (not bound to a `side_id`). |

**Normative:**

- **`fără`** **SHALL** appear in the operator registry as **`SemanticOperator.FARA`** with `stateless: true`, `side_id: null`.
- Future ADR may assign **`fără`** to a side, a guard, or a **volume-only** (Ω) modifier — not on ∂Ω without explicit approval.
- Matching **`fără`** in input **does not** rotate the hex in v0.1; it **may** affect **`δ_powv`** magnitude (inward / exclusion bias) when wired.

**Invariant:** **INV-SEM-OPS-6** — six **assigned** RO/EN pairs on sides; **INV-FARA-STATELESS** — `fără` registered but unassigned.

---

## 8. Dual operator on one side

For side `s` after rotation:

```text
SideSpec(s) = ( L_{(s + hex_rotation) mod 6},  Σ_{(s + hex_rotation) mod 6} )
```

**Match score** for input wording features **φ**:

```text
m_s = w_L · match_logical(φ, L) + w_Σ · match_semantic(φ, Σ)     with w_L + w_Σ = 1
```

Default **`w_L = 0.7`**, **`w_Σ = 0.3`** (calibration file may override). GTPA prioritizes **logic**; semantic RO/EN is tie-break and audit label.

---

## 9. PointZeroDelta and coherence field Ψ

### 9.1 PointZeroDelta

At step `t`, with IPoW position **`r_t`** (from `22_SPEC__`):

```text
δ_powv_t = r_t − r_zero        where r_zero = (0,0,0) at PointZero
```

Step-to-step variant (optional):

```text
δ_powv_step_t = r_t − r_{t−1}
```

**Broadcast** to every area `i` and family `j` with unit anchor direction **`s_{i,j}`**:

```text
δ_{i,j} = dot(δ_powv_t, s_{i,j})     scalar signed projection
```

Also broadcast to **12** area ring anchors and **288** family anchors (families use patch center directions from `anchor_map_v1`).

### 9.2 Coherence field Ψ — "one big variable"

**Ψ** is the **single coherence object** precalculating surface propagation. v0.1 decomposition:

**Vector part** (dimension **300** = 12 areas + 288 families):

```text
Ψ_k = δ_k     for k in areas ∪ families
```

**Scalar summaries** (for logs / `coherence_hints`):

```text
Ψ_abs   = ||δ_powv_t||
Ψ_ent   = −Σ_k  p_k log p_k     where p_k = |δ_k| / Σ|δ_k|   (distribution shape)
Ψ_align = max_k δ_k − min_k δ_k
```

**Coherence scalar (one number for driver):**

```text
C_t = aggregate(Ψ) = α·Ψ_abs + β·Ψ_align − γ·variance(δ_family)
```

Coefficients **`α, β, γ`** live in calibration (`gtp_coherence_v0_1.json` — future).

**Use:** **`C_t`** and full **`Ψ`** steer **next hex** jointly with path template **P** — **not** full LLM semantic re-classification.

---

## 10. GTPA — next hex selection (deterministic core)

### 10.1 Neighborhood

Let **`h`** = current HexCell on GCS. **`N(h)`** = legal neighbors from **loopability / traversal** policy (area ring steps, family patch steps, hex index steps — frozen graph).

> **Implementation note (§0.1):** no `40_POLICY` exists; `sphere/topology/gtp/neighbors.py` freezes this rule for v0.1 — see §0.1 item 1.

### 10.2 Score

For each candidate **`h' ∈ N(h)`**:

```text
Score(h') = η · PathPrior(h, h', P)
          + κ · CoherenceAlign(h', Ψ)
          + λ · Σ_{s=0}^{5} m_s(h', s)
          − μ · SemanticPenalty(h')        # small; default μ → 0 for "almost no semantic"
```

| Term | Meaning |
|------|---------|
| `PathPrior` | Existing basic logical path — borders, direction, loopability from `40_POLICY` |
| `CoherenceAlign` | `dot(direction(h→h'), normalize(Ψ_vector))` or lookup table from anchor map |
| `Σ m_s` | Side match under trial rotation at `h'` |
| `SemanticPenalty` | Optional dampener on heavy concept/lexical jumps — default **off** in discovery mode |

**Choice:**

```text
h* = argmax_{h' ∈ N(h)} Score(h')
exit_side* = argmax_{s} m_s(h*, s)
hex_rotation* = argmax_{r ∈ {0,…,5}}  (rotation score at h*)
```

Ties broken by: lower `global_id`, then lower `hex_index`, then lower `side_id` (**deterministic**).

### 10.3 Path discovery pipeline (wording → surface)

```mermaid
flowchart LR
  W[input wording]
  φ[feature φ minimal]
  L[logic check L_s per side]
  I[ThoughtImprint]
  D[ImprintDifference vs baseline]
  δ[PointZeroDelta from IPoW]
  Ψ[CoherenceField Ψ]
  G[GTPA next hex]
  W --> φ --> L --> I --> D
  δ --> Ψ
  I --> G
  Ψ --> G
  D --> G
```

| Stage | Output | Semantic load |
|-------|--------|----------------|
| Logic check | which `L_s` fire | **low** |
| Imprint | `(hex, side, operators)` | **low** |
| Difference | Δ vs area/family baseline | **anchor-only** |
| GTPA step | next `(hex', side', rotation')` | **low** |

**Baseline** = original **Area** / **Family** attachment of the session slice, not book corpus retrieval.

---

## 11. Math summary (implementation card)

| # | Formula | Symbol |
|---|---------|--------|
| 1 | Active side | `(k + hex_rotation) mod 6` |
| 2 | Side match | `m_s = w_L·match_logical + w_Σ·match_semantic` |
| 3 | PointZeroDelta | `δ_powv = r_t − r_zero` |
| 4 | Broadcast | `δ_k = dot(δ_powv, s_k)` for each area/family anchor `k` |
| 5 | Coherence scalar | `C_t = α·‖δ_powv‖ + β·(max δ_k − min δ_k) − γ·Var(δ_family)` |
| 6 | Next hex | `h* = argmax_{h'∈N(h)} Score(h'; Ψ, P, {m_s})` |
| 7 | Above-below | `(h*, side*, rot*) = GTPA(r_t, δ_powv, h, rot, φ, P)` |

---

## 12. Relation to existing Hesperia planes

| Existing | GTP relation |
|----------|----------------|
| **TFP `areas` / `families` vectors** | Baseline anchor weights; **not** replaced by Ψ |
| **`propagation_trace`** | Separate graph smoothing; **must not** duplicate GTPA |
| **Apple path** | Records actual walk; GTPA **proposes** legal next step |
| **Guards / shadow** | May veto `h*` if `Score` violates guard policy |
| **IPoW** | Supplies **`r_t`**, **`δ_powv`**; GTP supplies **surface** move |

---

## 13. Proposed registry (future bundle)

```json
{
  "gtp_v0_1": {
    "hex_rotation": 0,
    "side_specs": [
      { "side_id": 0, "logical": "INCLUDES", "semantic_ro": "cu", "semantic_en": "with" },
      { "side_id": 1, "logical": "NOT_INCLUDES", "semantic_ro": "din", "semantic_en": "from" },
      { "side_id": 2, "logical": "SUBSUMES", "semantic_ro": "la", "semantic_en": "at" },
      { "side_id": 3, "logical": "OVERLAPS", "semantic_ro": "spre", "semantic_en": "toward" },
      { "side_id": 4, "logical": "DISJOINT", "semantic_ro": "dupa", "semantic_en": "after" },
      { "side_id": 5, "logical": "EQUIVALENT", "semantic_ro": "pentru", "semantic_en": "for" }
    ],
    "semantic_reserved": [
      { "id": "FARA", "semantic_ro": "fara", "semantic_en": "without", "stateless": true, "side_id": null }
    ],
    "point_zero_delta": { "x": 0.0, "y": 0.0, "z": 0.0 },
    "coherence": {
      "psi_scalar": 0.0,
      "psi_abs": 0.0,
      "psi_align": 0.0,
      "vector_dim": 300
    },
    "thought_imprint": [],
    "imprint_difference": {}
  }
}
```

> **Implementation note (§0.1):** the real runtime output shape is `sphere.topology.gtp.pipeline.gtp_step_to_dict()` / `schemas/gtp/gtp_v0_1.schema.json`, not a literal re-statement of this placeholder — see GTP-02 in §0.1.

---

## 14. ADR gates

| Change | Requires |
|--------|----------|
| Assign **`fără`** to a side | Operator ADR |
| Change **INV-LOGICAL-OPS-6** set | ADR + migration |
| Merge Ψ with TFP softmax areas | ADR — keep planes separate in v0.1 |
| LLM-only next hex (no GTPA argmax) | Forbidden in v0.1 |

---

## 15. Traceability

| Operator / brain | Hesperia formal |
|------------------|-----------------|
| Hex rotates | `HexOrientation` / `hex_rotation` |
| 6 programming operators | `LogicalOperator` `L_0..L_5` |
| cu, din, la, … | `SemanticOperator` `Σ_0..Σ_5` |
| fără | `FARA` stateless reserved |
| Point zero delta to all families/areas | `δ_powv`, broadcast `δ_k`, **Ψ** |
| Precalculate next hex | **GTPA** `Score`, `h*` |
| As above so below | **Π**, **GTPA** map Ω → ∂Ω |
| Future general thought propagation | **GTPA** / `gtp.v0_1` |

---

## 16. Phased backlog (triaged → active.md 2026-05-24, implemented 2026-07-19)

| ID | Summary | Owner | Depends |
|----|---------|-------|---------|
| **GTP-01** | Freeze hex side operator tables (logical + RO/EN; FARA reserved) | Gena → Felix (implemented) | — |
| **GTP-02** | `gtp_v0_1` schema + fixture | Felix | GTP-01 |
| **GTP-03** | `hex_rotation` + side match `m_s` | Gena → Felix (implemented) | GTP-01 |
| **GTP-04** | PointZeroDelta broadcast + coherence Ψ | Gena → Felix (implemented) | IPoV-03, GTP-01 |
| **GTP-05** | GTPA next-hex `Score` / argmax | Gena → Felix (implemented) | GTP-03, GTP-04 |
| **GTP-06** | ThoughtImprint + ImprintDifference | Gena → Felix (implemented) | GTP-03 |
| **GTP-07** | Bundle / `coherence_hints` wire | Felix | GTP-02, GTP-05 |
| **GTP-08** | Gold tests deterministic GTPA | Felix | GTP-05 |

## 17. Promotion checklist (dev repo)

1. ~~Copy to `docs/specs/23_SPEC__General_Thought_Propagation_and_Hex_Orientation_v0_1.md`.~~ **Done 2026-07-19 — this file.**
2. Cross-link `22_SPEC__`, `20_GEOMETRY`, `40_POLICY`. — `22_SPEC__` cross-linked above; `20_GEOMETRY` and `40_POLICY` do not exist yet (see §0.1 item 1).
3. Add operator table to `VARIABLES.md` §GTP (future). — not yet done.
4. ~~Implement when **GTP-*** rows marked DONE on active.md.~~ **Done 2026-07-19.**

---

**SIGNED: Ethan (governance) | GTP hex orientation + coherence formalization v0.1 | 2026-05-24 | brain draft — no tasks**

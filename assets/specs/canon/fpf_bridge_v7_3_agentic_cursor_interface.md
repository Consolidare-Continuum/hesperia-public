# SPEC: fpf_bridge v7.3 — Agentic Cursor Interface (COBALT + TFP scope)

**Version:** v7.3 (extension)
**Status:** RATIFIED (Ethan) — 2026-07-19
**Date:** 2026-07-04 (draft) · **Ratified:** 2026-07-19
**Author:** Felix (Developer, Claude Code)
**Parent:** `specs/canon/fpf_bridge_v7_2_evidence_expansion.md`
**Depends on:** v7.2 Phase 1 (contradiction pilot) proven in practice — this spec exposes v7.2's evidence
surface to an external agent; there is nothing worth exposing until that evidence is real and gated.
**Scope:** COBALT + TFP only, same as v7.2. **Primary named consumer: Olga**, via **Cursor**, TFP branch
first. **Explicitly out of scope:** MRT (same reasoning as v7.2 §0 — closed MVP, different grid).
**Explicitly not a replacement for:** the existing `mode="llm"` internal narration path
(`runtime/services/product_interpret_service.py` → `llm_integration.py`) that IRC Teacher's production
line depends on. That path stays exactly as-is; this spec adds a second, parallel consumer for
exploratory research use, not a replacement for the production clinical envelope.

---

## 0. What this spec closes

Reviewing whether v7.2 "flies for agentic use" surfaced a real gap: `bridge_to_llm_prompt()`'s output
is real, and v7.2 makes its evidence richer and better-gated — but nothing today lets an external
agentic LLM (Cursor, driven by Olga) actually receive that state and reason over it. The only existing
"LLM" consumer is Hesperia's own internal, single-shot, server-side call to OpenAI/Anthropic
(`interpret_prompt_state`) — a closed loop that never hands control to an outside agent. This spec adds
the missing piece: an MCP interface that hands `bridge_to_llm_prompt()`'s state to Cursor directly, so
Cursor's own model becomes the reasoner, using the same FPF-anchored vocabulary v7.2 built (evidence,
gates, `context_scope`, `contradicts`, the `DEGRADE`/`BLOCK` lattice) — not a second, parallel
interpretation of it.

---

## 1. Two tools, two risk tiers — do not build both at once

### 1.1 Phase A (build first): `get_hesperia_bridge_state` — read-only

| Arg | Type | Description |
|---|---|---|
| `text` | string | Olga's research query or session excerpt |
| `branch` | `"tfp"` \| `"cobalt"` | Which `context_scope` this call is for — required, no default, so Cursor never silently mixes scopes |
| `include_cobalt` | bool, default `false` | If true and `HESPERIA_COBALT_ENABLED=1`, also runs `compose_and_retrieve` (S1) and folds `cobalt_retrieval` into the response |

**Returns:** exactly `bridge_to_llm_prompt(result, context_id=...)`'s dict — current structural state,
FGR-scored evidence (v7.2-expanded: contradiction pressure with `contradicts[]`, `trust_tier`,
`system_confidence`, `decision_status`, KME primitives when `branch="tfp"`), legal next transitions with
their gate requirements, the pre-evaluated `initial_outcome`. **No internal LLM call happens in this
path** — this is the literal difference from `mode="llm"`: the JSON that would otherwise go to OpenAI
goes to Cursor instead, and Cursor's own model does the reasoning, out loud, in the IDE, where Olga sees
it.

This tool cannot change anything. It is exactly as safe as `get_cobalt_packet` — same risk class, same
justification for shipping first.

### 1.2 Phase B (build only after A is proven): `attempt_hesperia_transition` — validation, not mutation

| Arg | Type | Description |
|---|---|---|
| `text` | string | Same input text as the `get_hesperia_bridge_state` call this follows — **must match**, see §2 |
| `branch` | `"tfp"` \| `"cobalt"` | Same as above |
| `transition_id` | string | One of the `possible_transitions` ids Cursor received from Phase A |

**Returns:** `GateDecision` (`ABSTAIN`/`PASS`/`DEGRADE`/`BLOCK`, the real 4-value lattice from
`fpf_thinking_map`, not collapsed to boolean), `missing_evidence` (from `GatePrimitive.missing_evidence`),
and the gate's own `description`. **Still does not mutate anything** — `sphere/` stays untouched, this
only re-runs the deterministic pipeline on the same text and evaluates one named transition against its
gate, same computation `bridge_pipeline_result` already does internally, just exposed one call at a time
instead of only as a single internal `initial_outcome`. The reason this is a separate, higher-tier phase
even though it's read-only in effect: it's the one place a `BLOCK` result must actually be honored by
Cursor's narration (per v7.2 §4.2.2's design intent) — worth its own gold test and its own explicit
sign-off before it ships, same as COBALT treated its adapter and its prod flag as separate gates.

---

## 2. Statelessness — no server-side session, ever

Neither tool keeps session state between calls. Every call re-derives everything from the `text` argument
alone, using the exact same deterministic guarantee the sealed engine already provides: same input →
same `engine_trace_hash`. Practically:

- Cursor calls `get_hesperia_bridge_state(text, branch)` once per research turn.
- If Cursor/Olga wants to test a specific transition, `attempt_hesperia_transition` is called with the
  **same `text`** — the tool re-runs `/analyze` on it internally and checks the `engine_trace_hash`
  matches what a caller would get from a fresh `get_hesperia_bridge_state` call on that same text. If the
  text changed even slightly (Olga edited her query), the hash won't match — that is not an error to
  hide, it means this is now genuinely a different structural read, and the transition being asked about
  may not even be in the new legal set.
- No hidden mutable state means no risk of one Cursor session's contradiction evidence leaking into
  another session, or stale evidence surviving past the input that produced it — same guarantee v7.2 §4.2.3
  gives via `SemanticFloor` decay, enforced here at the interface level too, for free, because there is
  nothing to decay when nothing persists.

---

## 3. The new risk surface this spec introduces — and what has to be checked before it ships

This is the part that did not exist in v7.2 and needs its own explicit sign-off, not an inherited one:

**Today**, the only LLM path is `product_interpret_service.py` calling OpenAI/Anthropic directly,
server-side, per-request, with no persistent log beyond whatever Hesperia's own audit trail keeps
(`router_output_audit`). **After this spec**, the same evidence — including anything derived from real
TFP clinical sessions via KME primitives (§1.10 of v7.2, `context_scope="tfp"`) — flows into Cursor's own
conversation context: a different logging/telemetry boundary, a different retention policy, potentially
a different backing model than whatever Hesperia's internal call uses.

**Before Phase A ships with real (not synthetic) TFP input:**

- Confirm no evidence primitive ever carries raw session text or a directly quoted clinical excerpt —
  the "menu, not dump" discipline `corners/fpf_bridge.md` already established must hold for this new
  consumer exactly as strictly as it holds for the internal one. This needs to be checked explicitly for
  the new v7.2 evidence types (KME primitives, contradiction `contracts[]` labels) — a `contradicts`
  list naming *which evidence_id* is contradicted is fine; a `contradicts` entry that embeds a snippet of
  session text would not be.
- **A security review scoped specifically to this exposure path** — not a reuse of COBALT-20
  (Sophia's review covered CHROMA-2 query content, a different data path entirely). Same reviewer,
  same rigor, new scope: does anything Cursor receives, combined with Cursor's own logging, create a
  PII/session-content exposure that didn't exist when the only consumer was Hesperia's own ephemeral
  OpenAI/Anthropic call?
- Confirm which Cursor account/session this runs under (Olga's, per her own MCP deployment convention,
  §5) and that no cross-account leakage is possible between her TFP-scoped calls and any other user's.

**None of this blocks Phase A's *design or code* — it blocks Phase A's *prod flag going on with real
clinical input*.** Same two-speed discipline COBALT used: build and gold-test against synthetic input
first, flip on for real data only after the review passes.

---

## 4. Reasoning loop — the actual shape of "agentic run in Cursor"

This is what Olga's session looks like once Phase A and B are both live:

1. Olga asks a TFP research question in Cursor.
2. Cursor (the calling agent — me, or whichever model backs her Cursor session) calls
   `get_hesperia_bridge_state(text, branch="tfp")`.
3. Cursor receives: current structural state, the v7.2-expanded evidence set (contradiction pressure with
   named contradictions, trust tier, system confidence, KME primitives), the legal next transitions and
   their gates, and `initial_outcome`.
4. Cursor reasons **out loud, in its own turn**, using the same FPF-anchored vocabulary the evidence is
   already expressed in — it does not need to re-derive what "contradiction pressure" or "bounded
   context" mean, because `ContextPrimitive.glossary` (v7.2 §4.2.4) already carries those definitions in
   the object it just received.
5. If Cursor's reasoning wants to commit to a specific structural conclusion tied to a transition, it
   calls `attempt_hesperia_transition(text, branch, transition_id)` before narrating that conclusion as
   settled. A `BLOCK` result means Cursor must not narrate that conclusion — it says so, and reasons about
   why (using `missing_evidence`), rather than working around it.
6. Optionally, Cursor also calls `get_cobalt_packet` (v7.2/COBALT, unchanged) for library grounding,
   consistently scoped via the same `context_scope` value.
7. Olga sees all of this in her IDE, as ordinary agent reasoning — not a black-box narrative object
   handed back from a single opaque call, which is what `mode="llm"` gives the production Teacher path
   today.

This is the concrete payoff of v7.2's §4 ("FPF library as the shared stage"): the vocabulary Cursor
reasons in and the vocabulary Hesperia computed in are the same objects, not a translation layer between
two independently-designed schemas.

---

## 5. Deployment — reuse Olga's existing MCP pattern, don't invent a new one

Olga's repo (`github.com/igareosh/olga`) already has the exact convention this needs, built for
`colombo-library`:

- `governance/mcp-config.json` — the MCP server registry, deployed via `scripts/deploy-olga-mcp.sh` to
  both `~/.cursor/mcp.json` and the project `.cursor/mcp.json`.
- `scripts/agent-mcp-colombo-library-olga.sh` — a launcher script exporting env vars and invoking the
  brain-repo's Python MCP module directly (`agent_mcp_colombo_library`), with a venv/site-packages
  fallback pattern for her account specifically.

This spec's tools follow the identical shape:

| Item | Value |
|---|---|
| New launcher | `scripts/agent-mcp-hesperia-bridge-olga.sh` (Olga's repo, same directory as the existing colombo launcher) |
| Module | New `agent_mcp_hesperia_bridge` package (dev repo, `igareosh/hesperia`), exposing `get_hesperia_bridge_state` and (Phase B) `attempt_hesperia_transition` |
| Registry entry | Add to `governance/mcp-config.json` alongside the existing `colombo-library` entry |
| Env vars | `HESPERIA_ENGINE_URL` (points at the sealed `/analyze` or in-process pipeline), `HESPERIA_MCP_BRIDGE_ENABLED`, `HESPERIA_MCP_BRIDGE_BRANCH_DEFAULT=tfp` |
| No duplicate client | Reuse `sphere/fpf_bridge/bridge.py::bridge_to_llm_prompt` directly — the MCP tool is a thin wrapper, not a second implementation, same "no duplicate client" rule COBALT-10 already established for its own CHROMA-2 access |

---

## 6. Env flags

| Flag | Default | Effect |
|---|---|---|
| `HESPERIA_MCP_BRIDGE_ENABLED` | `0` | Phase A tool (`get_hesperia_bridge_state`) available at all |
| `HESPERIA_MCP_BRIDGE_ACT_ENABLED` | `0` | Phase B tool (`attempt_hesperia_transition`) available — separate flag, higher tier |
| `HESPERIA_MCP_BRIDGE_REAL_DATA` | `0` | Gates whether real (non-synthetic) TFP input may flow through either tool — flips on only after §3's security review passes, independent of the two flags above being on for synthetic/dev testing |

Same discipline as every prior flag in this bridge lineage: everything defaults off, nothing here changes
production behavior until explicitly enabled, and "code exists" and "real clinical data allowed through
it" are two separate, separately-gated decisions (`HESPERIA_MCP_BRIDGE_ACT_ENABLED` vs
`HESPERIA_MCP_BRIDGE_REAL_DATA`), same split COBALT used between "adapter built" and "prod flag on."

---

## 7. Phase plan

| Phase | Scope | Flag state |
|---|---|---|
| **0** | Ethan ratify this spec; confirm v7.2 Phase 1 has actually landed first | — |
| **1** | `get_hesperia_bridge_state` built + gold-tested against synthetic TFP input | `BRIDGE_ENABLED=1` (dev), `REAL_DATA=0` |
| **2** | Olga's MCP launcher + registry entry deployed (§5); Olga runs Phase 1 tool against synthetic input in her own Cursor session | same |
| **3** | Security review (§3) scoped to this exposure path specifically | — |
| **4** | `REAL_DATA=1` — Olga's real TFP research questions may flow through Phase A | after §3 passes **and** `fpf_bridge_v7_4_cobalt_corpus_scaleup.md` exit criteria pass for any COBALT-branch retrieval — `REAL_DATA=1` against a 25-document pilot-scale corpus is not real-data readiness, it's the pilot number wearing a different flag |
| **5** | `attempt_hesperia_transition` (Phase B) built + gold-tested — a case where a `BLOCK` result is returned and Cursor correctly declines to narrate the blocked conclusion | `ACT_ENABLED=1` (dev) |
| **6** | `ACT_ENABLED` + real-data flip for Phase B, after its own review pass | after Phase 5 gold test + review |

---

## 8. Exit criteria

- [x] `get_hesperia_bridge_state` returns same evidence/state shape as `bridge_to_llm_prompt()` — FBV73-01 DONE (synthetic path)
- [ ] No raw session text or clinical excerpt in tool responses under real-data — **blocked on FBV73-03 security + FBV74 exit** before `REAL_DATA=1`
- [x] Statelessness proven in gold tests — FBV73-01 / FBV73-04
- [ ] Security review (§3) complete — **FBV73-03 OPEN (Sophia)** — hard gate before `REAL_DATA=1`
- [x] Phase B `attempt_hesperia_transition` built — FBV73-04 DONE; amendment: installed `fpf-thinking-map` `GatePrimitive.evaluate()` does not currently emit `GateDecision.BLOCK` (only ABSTAIN/DEGRADE/PASS) — gold tests assert real library outcomes, not a fictional BLOCK case
- [x] No change to sealed `/analyze` or production `mode="llm"` path — additive only
- [x] Register rows on `active.md` (FBV73-00..04)

**Still open (not blocking design ratification):** FBV73-02 Olga+Gena MCP deploy; FBV73-03 Sophia security; FBV74 exit before any `REAL_DATA=1`.

---

## 9. Ratification

| Role | Action | Date | Status |
|---|---|---|---|
| Felix | Draft spec (MCP interface, statelessness, risk-tier split) | 2026-07-04 | DONE |
| Ethan | Ratify / amend; confirm v7.2 Phase 1 dependency satisfied | 2026-07-19 | **RATIFIED** |
| Sophia (or equivalent) | Security review scoped to Cursor/MCP exposure of TFP-scoped evidence (§3) | — | PENDING (FBV73-03) |
| Olga | Confirm Phase 2 deployment against her own MCP convention; first real-use sign-off before Phase 4 | — | PENDING (FBV73-02) |
| Grace | Triage Phase 1–2 execution rows | 2026-07 | DONE (rows live) |

### Ethan ratification notes (2026-07-19)

1. **Two-tool / two-risk-tier split** (read-only first, then attempt_transition) — **accepted**.
2. **v7.2 Phase 1 dependency** — **satisfied** (FBV72-01 DONE; FBV72-00 ratified same day).
3. **Statelessness / no server session** — **accepted** (hard invariant).
4. **Does not replace** production `mode="llm"` IRC Teacher path — **accepted**.
5. **REAL_DATA=1** remains gated on FBV73-03 + FBV74 exit — ratification does **not** unlock real clinical/library input.
6. **Library BLOCK gap** (FBV73-04) is documented architecture reality, not a silent fail — do not invent BLOCK tests the package cannot produce.

`SIGNED: Developer (Felix) | Claude Code context | 2026-07-04 | fpf_bridge v7.3 agentic Cursor interface spec draft`

`SIGNED: Architecture (Ethan) | Hesperia day run | 2026-07-19 | FBV73-00 RATIFIED — design + Phase A/B code path; security/Olga deploy/REAL_DATA still open`

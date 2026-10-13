# Operator guide (ISO/IEC/IEEE 26511/26512 form)

For whoever calls Hesperia over HTTP — not for whoever maintains its internals. Everything here is
drawn from the frozen contract and the current governed service; nothing here changes either.

## 1. Which endpoint to use

Two contracts exist. Use the one matching your integration's age and needs
(`docs/iso/ARCHITECTURE_DESCRIPTION.md` §6):

| If you... | Use | Because |
|---|---|---|
| Already integrated against the legacy shape | `/analyze` | Frozen (HSPR-01/02); `docs/ENGINE-ANALYZE-CONTRACT.md` guarantees the 9 top-level fields never change shape |
| Are integrating new, or need governance verdicts | `/product/interpret` | Current governed V7 router surface; returns richer envelope + optional LLM narration with audit. This is the surface closest to Hesperia's productization wording of "deterministic validation" plus audit trace, not the legacy `/analyze` contract |

## 2. Calling `/analyze`

Request: `{"text": "...", "mode": "reflection"|"standard"}`. Full field reference:
`docs/ENGINE-ANALYZE-CONTRACT.md`. Mandatory response fields: `trace[]`, `dominant_area_id`,
`dominant_family_id`, `dominant_concept_id`, `governance`, `loopability`, `tension_energy`,
`obstacle_score`, `contradiction_flags[]`, `weak_signals[]`. The Python client
(`HesperiaPublicSnapshot.from_engine_result`) raises `ValueError` if any mandatory field is missing
— if you write your own client, replicate this strictness rather than defensively guessing at field
presence.

## 3. Calling `/product/interpret`

Call `run_product_interpret(text, mode="deterministic"|"llm")`
(`runtime/services/product_interpret_service.py`).

- **`mode="deterministic"`** (default, no LLM call): returns `schema`, `mode`, `router_envelope`
  (full L1–L9 + fpf_bridge state), `interpretation` (small structural summary), `engine_trace_hash`,
  `router_fingerprint`, `evidence_ids`, `decision` (always `"ALLOW"` in this mode), `router_mode`.
- **`mode="llm"`**: additionally invokes an LLM narration and audits it, adding `llm`,
  `prompt_envelope`, `router_output_audit`, `router_decision`, `governed_decision`, and
  `evidence_ids.output_hash`.

If you are building the buyer-facing artifact the repo's productization docs call a deterministic
validation report or evidence-grade audit trace, this is the endpoint family to build on.

**Set `HESPERIA_ROUTER_MODE`** to control what a non-`ALLOW` verdict does to your response:

| Mode | Behavior on `WARN`/`REVIEW_REQUIRED`/`BLOCK` |
|---|---|
| `observe` (default) | No effect on response — verdict is computed but not enforced |
| `warn` | Adds `governance_warning` string to response; content still served |
| `strict` | On `REVIEW_REQUIRED`/`BLOCK`: drops `llm` entirely, collapses `interpretation` to a `"blocked"` stub, sets `governance_block: true` |

If your integration cannot tolerate a suppressed response, use `strict` and handle
`governance_block` explicitly — do not use `observe` and assume the verdict is being enforced.

## 4. Reading the response — what to actually look at

You do not need every field in `docs/foundations/output_catalog.md`'s ~190-variable inventory. For
most integrations:

- **Trust at a glance:** `router_envelope`'s L9 output — `BRAND_WORD_TRUST`
  (`BLOCKED`/`TRUSTED`/`USABLE`/`TENTATIVE`/`FRAGILE`) and the six `BAND_*` confidence bands.
- **Should this be shown to an end user at all:** `ACTION_ALLOW_HUMAN_SUMMARY` — if `false`, the
  system itself is saying this read isn't ready to be narrated to a human.
- **Why something was flagged:** `ACTION_REQUIRE_MORE_INPUT`, `ACTION_REQUIRE_EVIDENCE_REBUILD`,
  `ACTION_REQUIRE_GOVERNANCE_REVIEW` are the three "what to do next" triggers.
- **In `mode="llm"`:** check `decision` before trusting `llm`'s content — `router_decision.decision`
  is the governed verdict `llm`'s narration was actually checked against.

## 5. What NOT to build against

- **Do not** build against `hesperia/extensions/dynamics/`'s output shape
  (`run_output_e2e_field_dynamics.json`) as an operator — it has no path into either endpoint above
  (`docs/foundations/corners/field_dynamics.md`).
- **Do not** assume field names from `/analyze` and `/product/interpret` are interchangeable — they
  are independently versioned contracts (`docs/foundations/output_catalog.md` §0).
- **Do not** treat `observe` mode's silence on a `BLOCK` verdict as the system being permissive by
  design — it means your integration opted not to enforce, not that nothing was flagged.

## Maintenance note

Registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. If either endpoint's response shape
changes, update this guide in the same commit as `docs/ENGINE-ANALYZE-CONTRACT.md` or
`runtime/services/product_interpret_service.py` — this guide has no independent authority over the
contract, only over how to read it.

## Navigation

← [`docs/README.md`](../README.md) (start here) · [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`ARCHITECTURE_DESCRIPTION.md`](ARCHITECTURE_DESCRIPTION.md) §6 (Product Surface Viewpoint, the architectural form of this guide) · [`../foundations/output_catalog.md`](../foundations/output_catalog.md) §0 (full field-by-field response contract detail) · [`../ENGINE-ANALYZE-CONTRACT.md`](../ENGINE-ANALYZE-CONTRACT.md) (the frozen `/analyze` contract this guide summarizes)

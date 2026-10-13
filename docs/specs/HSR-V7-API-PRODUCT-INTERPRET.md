# HSR-V7 — `/product/interpret` API (Gate E-03)

**Endpoint:** `POST /product/interpret`  
**Schema:** `hesperia.product_interpret.v0_1`

## Description (operator-facing)

Governed **routed endpoint**: compiles operator text → `RouterInputEnvelope` → structural interpretation and/or LLM path with **post-LLM audit** → `RouterDecision`. Not an "intelligent answer" API.

## Request

```json
{ "text": "<operator input>", "mode": "deterministic" | "llm" }
```

## Response (always)

| Field | Meaning |
|-------|---------|
| `router_envelope` | Sealed pre-LLM packet (`hesperia.router_input_envelope.v0_1`) |
| `interpretation` | Deterministic structural summary (all modes) |
| `llm` | Present when `mode=llm` — **generated narrative** |
| `router_decision` | ALLOW / WARN / REVIEW_REQUIRED / BLOCK |
| `router_output_audit` | Alignment, corpus check, policy check |
| `router_mode` | observe / warn / strict (`HESPERIA_ROUTER_MODE`) |

## Governance modes

- **observe** — decision recorded; output served
- **warn** — flag on WARN/BLOCK/REVIEW
- **strict** — BLOCK strips LLM payload

Ref: `runtime/services/product_interpret_service.py` · Olivia contract (brain) `OLIVIA-HSR-V7-10-PRODUCT-INTERPRET-API-CONTRACT-2026-06-29.md`

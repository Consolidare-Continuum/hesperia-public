# HSR-V7 — Operator surface labels (Gate E-04..E-06)

Apply to Inspector, API JSON viewers, and shipping UI when showing v7 router fields.

## E-04 — Provenance (always visible when envelope present)

| Field | Label |
|-------|-------|
| `router_fingerprint` | Router fingerprint |
| `corpus_snapshot_id` | Corpus snapshot |
| `policy_snapshot_id` | Policy snapshot |
| `input_hash` | Input hash |
| `output_hash` | Output hash |

## E-05 — LLM output

| Context | Label |
|---------|-------|
| LLM narrative block | **Generated text** (not "Hesperia answer") |
| `confidence` | Model confidence (generated) |
| Provider field | LLM provider |

## E-06 — Unsupported / audit

When `corpus_check.status` is `unsupported` or `missing_evidence`, or decision is REVIEW_REQUIRED/BLOCK for corpus reasons:

> **Unsupported by corpus** — narrative exceeds attached evidence.

When `UNSUPPORTED_CLAIM` in `decision_reasons`:

> High-certainty language without corpus backing — review required.

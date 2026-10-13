# HSR-V7 RouterPromptEnvelope v0.1 (C-14)

**Schema:** `schemas/router/router_prompt_envelope_v0_1.schema.json`  
**Builder:** `sphere/router/prompt_envelope.py` → `build_prompt_envelope()`  
**Policy:** `enforce_prompt_policy()` — no `input_text`, no hidden reasoning keys

## Required fields

`schema`, `router_version`, `input_hash`, `router_fingerprint`, `engine_trace`, `logic_mapping`, `retrieval_context`, `relation_context`, `policy_block`, `corpus_snapshot_id`, `policy_snapshot_id`, `allowed_tasks`, `forbidden_actions`, `answer_instructions`

## Optional

`evidence_references`, `calculable`, `coherence_hints`

## Bounded by policy

`allowed_tasks` / `forbidden_actions` from `policy_block` or defaults; prompt substrate excludes raw operator `input_text`.

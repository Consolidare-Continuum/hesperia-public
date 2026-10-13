# HSR-V7 — RouterInputEnvelope + fingerprint v0.1

**Tasks:** HSR-V7-03, HSR-V7-04 · **Owner:** Gena · **Ratified by:** Ethan HSR-V7-01

**Brain spec:** `governance/SPEC-ETHAN-HESPERIA-V7-SEMANTICS-ROUTER-COMPLIANCE.md` (brain repo)

---

## Artifacts (this repo)

| Path | Purpose |
|------|---------|
| `schemas/router/router_input_envelope_v0_1.schema.json` | JSON Schema |
| `sphere/router/envelope_v0_1.py` | `RouterInputEnvelope` dataclass + `envelope_to_dict` |
| `sphere/router/fingerprint.py` | `compute_router_fingerprint`, `fingerprint_contract_v0_1` |
| `sphere/router/thinking_map_bridge.py` | `logic_mapping` / `policy_block` from **fpf-thinking-map** MCP JSON |
| `tests/router/test_router_fingerprint_v0_1.py` | Determinism + bridge smoke |

---

## fpf-thinking-map (we are this library)

Pin: **fpf-thinking-map==1.9.2** (ATM2-43; `requirements/router.txt` + `calibration.txt`; add to product `pyproject.toml` when Felix wires runtime).

```python
from sphere.router.thinking_map_bridge import logic_mapping_from_thinking_map, policy_block_from_thinking_map

outcome = ...  # thinking_map_step JSON
logic_mapping = logic_mapping_from_thinking_map(outcome)
policy_block = policy_block_from_thinking_map(outcome)
```

---

## Fingerprint contract (v0.1)

`sha256(canonical_json(parts))` where `parts` = `input_hash`, `engine_trace_hash`, `retrieval_snapshot_hash`, `policy_snapshot_id`, `router_version`, `enabled_modules` (sorted).

See `fingerprint_contract_v0_1()` for machine-readable contract.

---

SIGNED: Developer (Gena) | HSR-V7 router envelope v0.1 | 2026-06-28 | hesperia dev

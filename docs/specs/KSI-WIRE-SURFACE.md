# KSI-Inspector wire surface (sealed /analyze)

**Package:** `core.domain.ksi` (`core/domain/ksi/`) — Class A pure-function derived measurement  
**Ratify:** brain `governance/HES-MATH-BEHAV-RATIFY-2026-08-05.md`  
**Status:** wired 2026-08-05 (HES-MATH-BEHAV-25..33) — additive, **default-off**

---

## Hook points

| Surface | Path | Behaviour |
|---------|------|-----------|
| Sealed engine envelope | `sphere/router/engine_analyze_bridge.py` → `build_engine_analyze_from_raw` | After trace envelope built, calls `attach_ksi_to_engine_result` |
| Hybrid retrieve | `runtime/irc_teacher/analyze_adapter.py` → `retrieve` | Re-attaches via same entry if engine omitted `ksi` |
| Wire entry | `core/domain/ksi/pipeline.py` | `run_ksi_inspect` / `run_ksi_inspect_from_engine` / `attach_ksi_to_engine_result` |
| Flags | `core/domain/ksi/flags.py` | `HESPERIA_KSI_*` readers |
| Env allowlist | `runtime/shipping/env_guard.py` | All live KSI flags |

**Not recreated:** Φ_e / Expected_j / bridge / teacher modules already in package (drain `7056953c`).

---

## Flags (default-off unless noted)

| Env | Default | Role |
|-----|---------|------|
| `HESPERIA_KSI_ENABLED` | `0` | Master gate — unset/0 → **no** `ksi` key on envelope |
| `HESPERIA_KSI_PHI_TRACE` | `0` | Include `phi_trace` edge map |
| `HESPERIA_KSI_CONFIG` | asset default | Path override for `ksi_config_v01.json` |
| `HESPERIA_KSI_TAU` / `_TAU_BRIDGE` / `_TAU_TEACHER` | config | Threshold overrides |
| `HESPERIA_KSI_TEACHER_PACKET` | `1` when enabled | Attach inspect-only `teacher_packet` under `ksi` |
| `HESPERIA_KSI_TEACHER_INSPECT_ONLY` | `1` | Packet marked inspect-only |
| `HESPERIA_KSI_LLM_TEACHER` | `0` | Live LLM (IRC teacher path; not sealed apply) |
| `HESPERIA_KSI_TEACHER_MODEL` | `gpt-4o-mini` | Model name when LLM teacher on |
| `HESPERIA_KSI_SANDBOX_FIXTURES` | — | Sandbox fixtures path |

**Apply gate:** `teacher_packet.apply_allowed` is always `false` with `apply_gate=blocked_until_0.7.0`. No graph apply on this wire.

---

## Envelope shape (when enabled)

```json
{
  "contract_version": "v1.0",
  "trace": [ ... ],
  "ksi": {
    "version": "0.1",
    "concepts": { "SHAME": { "expected": 0.0, "observed": 0.3, "residual": -0.3, "incident": null } },
    "areas": {},
    "incidents": [],
    "missing_bridges": [],
    "phi_trace": null,
    "teacher_packet": {
      "mode": "inspect_only",
      "apply_allowed": false,
      "apply_gate": "blocked_until_0.7.0"
    }
  }
}
```

Inputs for Expected_j: `trace` activations + optional `ksi_edges` / `temp_relation_overlay` / `invariant_activation.concepts`.

---

## Module pointer

- Package: `core/domain/ksi/`
- Tests: `tests/domain/ksi/` (unit + `test_ksi_analyze_wire.py`)
- Assets: `assets/data/ksi/`

SIGNED: Developer (Felix) | Claude Code context | 2026-08-05 | KSI wire surface

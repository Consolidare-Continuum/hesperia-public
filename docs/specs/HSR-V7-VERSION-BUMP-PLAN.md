# VERSION.yaml bump plan — V7 campaign (HSR-V7-A-08)

**Current source/system version:** `0.6.5`  
**Brain owner:** Gena · **Architect:** Ethan

---

## Version ladder

| Version | Stage | Meaning |
|---------|-------|---------|
| **0.6.3** | `irc_teacher_application_run` | Historical sealed baseline — physics + assets frozen; prod gate |
| **0.6.5** | `v7_router_fusion` | Current source/system identity — router envelope, post-LLM audit, `/product/interpret`, fpf-thinking-map calibration |
| **0.7.0** | `modular_branches` | Apply/sandbox direction; Class A drain complete; TFP/MRT/COBALT modules registered |

---

## Bump rules

1. **Patch (0.6.x):** router/governance/API-only — no `sealed_multiscale_stack` or asset hash change.
2. **0.6.5:** current router-fusion line, no sealed physics change.
3. **0.7.0:** apply/sandbox line; requires Gate B drain resolution (B-21) + Gate C exit + COBALT gates G1–G4 if COBALT prod flag considered.

---

## Fields to update at 0.6.5

- `system_version`, `components.*` aligned to `0.6.5`
- `release_stage: v7_router_fusion`
- `build.git_commit` from promote SHA
- `runtime/shipping/version_info.py` aligned to `0.6.5`

---

## Promote path

Dev: `igareosh/hesperia` branch `hsr-v7-router-implementation` → prod: `Atomic-Commits-Team/hesperia` after Abelard A-12 clean + tag. **Historical** — Atomic abandoned 2026-07-26 (copyright assigned to Consolidare Continuum S.R.L.); prod promotion is now the same repo, `igareosh/hesperia`.

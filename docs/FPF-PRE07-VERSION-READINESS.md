# FPF pre-0.7 version readiness (no seal tag bump)

**Date:** 2026-07-19  
**Owner:** Gena (Main developer)  
**Rows:** FPF-PRE07-08  
**Repo:** `igareosh/hesperia` · path `/data/workspaces/hesperia`  
**Brain hold:** `HSR-V7-SEAL-OPERATOR-HOLD.md` — X-01..14 PAUSED

---

## Verdict

**pre-0.7 wire readiness** = HAND faces + pin + gold loops documented and executable on **altitudine**.  
**Not** a product seal. **Do not** bump seal / release tags for PRE07-08.

| Field | Value |
|-------|--------|
| Current system identity | `0.6.5` · `v7_router_fusion` (see `VERSION.yaml` / tag registry) |
| Apply sandbox | may show `0.7.0` apply.version — **not** prod seal |
| Seal / prod tag | **HELD** — operator explicit allow only |
| This note | Readiness **documentation** only |

---

## Pin (mandatory)

```
fpf-thinking-map==1.9.2
```

| Location | Status |
|----------|--------|
| `requirements/router.txt` | `==1.9.2` |
| `requirements/calibration.txt` | `==1.9.2` |
| `sphere/fpf_inspect/constants.py` `FPF_PIN_EXPECTED` | `fpf-thinking-map==1.9.2` |
| Brain `requirements-thinking-map.txt` | `==1.9.2` (soak) |

**Converge with brain.** See [FPF-PIN-HESPERIA-VS-BRAIN.md](FPF-PIN-HESPERIA-VS-BRAIN.md). No silent upgrade path — bump is an explicit PR + CI (Felix PRE07-01 / MWI-05).

---

## PRE07-08 do / do-not

**Do**

- Record pin `1.9.2` and readiness criteria here  
- Point operators to HAND runbook (brain) and dig CLI  
- Keep `VERSION.yaml` honest about `0.6.5` system stage  

**Do not**

- Create / push seal tag for 0.7  
- Unpause HSR-V7-X-*  
- Claim prod READY from this note alone (Emma PRE07-18 + Grace PRE07-19)  

---

## Readiness criteria (wire, not seal)

```
[ ] Pin 1.9.2 installable in Hesperia venv on altitudine
[ ] sphere/fpf_inspect climb + GapReport runnable
[ ] Both MCP faces deployable (brain Liam PRE07-16) — not this repo's seal
[ ] ground_truth three blocks enforced at inquire/interpret seams
[ ] No VERSION seal tag change in this task
```

---

`SIGNED: Main developer (Gena) | pre-0.7 readiness note | 2026-07-19 | PRE07-08 no seal tag bump`

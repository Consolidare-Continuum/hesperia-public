# Hesperia — core, modules, and scoped branches

**Canonical on dev repo:** `igareosh/hesperia` (this tree)  
**Updated:** 2026-06-20  
**Author:** Colombo (research) · operator-confirmed  
**Prod push:** `igareosh/hesperia` (same repo as dev; was `Atomic-Commits-Team/hesperia`, abandoned 2026-07-26 — copyright assigned to Consolidare Continuum S.R.L.) — **docs only on dev** until Ethan release wave

---

## 1. Sealed core

The **runtime semantic engine** is **sealed**: `/analyze` + dict calculus + deterministic trace on the 12×24×250×6 grid.

- Code: `hesperia/engine/`, sealed assets under `assets/data/engine_dynamics_v060/`
- Deterministic structural computation is canonical under `core/`, with `core.domain` owning shared
  KME/domain measurement logic and `core.engine`/`core.math`/etc. owning the pure engine internals.
- **KSI-Inspector** (Class A, not module-registry-shaped): `core/domain/ksi/` — wire surface + flags
  → [KSI-WIRE-SURFACE.md](KSI-WIRE-SURFACE.md). Additive neighbour lens on sealed `/analyze`; default-off.
- **2026-08-04:** the pluggable Class A modules (dict_a, dict_b, topology, metrics — see §2) moved out
  of `core/runtime/` into `hesperia/modules/default/`, sibling to `hesperia/modules/{nlp,tfp}/`. Reasoning:
  `core/` should hold engine-internal compute with no module-registry shape (no `provides`/`requires`/
  `capabilities`/`create()`); anything with that pluggable-module shape belongs under `hesperia/modules/`
  regardless of whether it's Class A (universal/default) or Class B (branch-specific) — the class
  distinction is about *scope*, not about living inside `core/` vs not. `core/runtime/__init__.py`'s
  back-compat re-export was removed the same day — `tools/check_core_module_boundary.py` flagged it as
  a forbidden `core` → `hesperia.modules.*` import (zero real importers existed anyway); resolve these
  modules via `core.engine.module_loader.load_module()`/`module_aliases.py` instead.
- `hesperia.engine.kme` remains only as a narrowed compatibility package surface where explicitly
  protected legacy behavior still matters.
- Former `hesperia.modules.core` / `metrics.base` / `topology.core` shim files were removed once
  live code and tests converged to canonical `core.runtime.*` (2026-07) — since re-homed again to
  `hesperia.modules.default.*` per the note above.
- **No branch reopens core physics.** MRT, TFP, COBALT, and future work **branch understanding and outputs**, not measurement truth.

---

## 2. Module classes — default (universal) vs branch (domain-specific)

### Class A — Default modules (universal, domain-agnostic)

Universal plumbing lives under `hesperia/modules/default/` (moved from `core/runtime/` 2026-08-04 —
see §1). Branch work that proves **domain-agnostic** value merges back here.

| Alias | Module | Universal because |
|-------|--------|--------------------|
| `dict_a` / `dict_b` | `hesperia.modules.default.dict_*_module` | Lexical → grid calculus — all domains |
| `topology` | `hesperia.modules.default.topology_module` | Shared geometry phase |
| `nlp` | `hesperia.modules.nlp.basic` | Baseline tokenization |
| `metrics` | `hesperia.modules.default.metrics_module` | Shared measurement hooks |

### Class B — Branch modules (domain-specific)

**Not universal** — semantic attribution, theme, or domain specificity (IT, psy, clinical, library, …). Already live under `hesperia/modules/` (sibling to `default/`), never inside `core/`.

| Module / branch | Location | Why branch-scoped |
|-----------------|----------|--------------------|
| **TFP** | `hesperia.modules.tfp` | **Psy / clinical** — sessions, RU specialized outputs |
| **MRT** | `igareosh/hesperia_mrt` | **IT / tech** — FPF, 96-fam, `sphere_rag` |
| **COBALT** | spec → `runtime/cobalt/` | **Semantic attribution** — CHROMA-2 bounding, themes |

**Class B modules register** with core (alias, envelope slot, flag) but **do not** enter sealed `/analyze` assets.

**Decision test:** *Universal engine plumbing?* → Class A, `hesperia/modules/default/`. *Domain / theme / attribution?* → Class B, own `hesperia/modules/<branch>/`.

### Calibration / propose domain seal (2026-09-14)

| Lane | Module folder | Corpus | Catalog | Propose `--domain` |
|------|---------------|--------|---------|-------------------|
| **DEFAULT / CORE** | `hesperia/modules/default/` | `…/default/corpus/syzif` | `assets/calibration/dicts/v0_core_syzif_001/` | **`core` (default)** |
| **TFP** | `hesperia/modules/tfp/` | `…/tfp/data/tfp_v1/corpus/…` | `engine_dynamics_v060/dict_b/dict_b_tfp*` | **`tfp` (opt-in only)** |

**Hard rule:** no TFP prompt, catalog, or concept ids on DEFAULT/CORE/syzif runs. CORE scope is wider; TFP is a narrow Class B field module. Gate: `tools/check_core_default_tfp_boundary.py`. Spec: `docs/specs/HESPERIA-CORE-DEFAULT-VS-TFP-CALIBRATION-SEAL.md`.

---

## 3. Modules in this repo (registry)

Registered aliases: `core/engine/module_aliases.py`

| Alias | Class | Scoped result-oriented output |
|-------|-------|------------------------------|
| `dict_a` / `dict_b` | **A** | Token → sparse activations; surface math |
| `topology`, `nlp`, `metrics` | **A** | Shared engine plumbing |
| `tfp` | **B** | Clinical TFP: roadmaps, iterations, corpus compose |

Future: `cobalt` → Class **B** (attribution / library).

**Pattern:** core measures → enabled modules produce **scoped artifacts** → envelope/MCP/LLM composes.

---

## 4. Sibling branches (separate repos / trees)

| Branch | Repo | Why separate |
|--------|------|--------------|
| **MRT** | `igareosh/hesperia_mrt` | 96-family tech/FPF grid; `sphere_rag`; not prod 288-fam |
| **COBALT** | spec → this dev repo | CHROMA-2 library RAG; corpus gate first |

Dev workspace on **altitudine:** `/data/workspaces/hesperia` (this repo) · `/data/workspaces/hesperia_mrt` (MRT).

---

## 5. Whole-world aim → mandatory separation

We can realistically cover **many domains** only by separating:

1. One **sealed core** (Class A modules).
2. Many **non-cored branch modules** (Class B — IT, psy, attribution, …).
3. **Independent MVP** per branch.
4. **Consolidation** for Class A only; Class B **registers**, does not merge into sealed stack.

---

## 6. Read next

| Doc | Path |
|-----|------|
| **Mandatory read policy (dev agents)** | cursor brain `governance/HESPERIA-MODULAR-ARCHITECTURE-MANDATORY-READ.md` |
| Full architecture | [docs/brain-export/colombo/HESPERIA-MODULAR-BRANCH-ARCHITECTURE.md](../brain-export/colombo/HESPERIA-MODULAR-BRANCH-ARCHITECTURE.md) |
| Branch inventory | [docs/brain-export/colombo/HESPERIA-BRANCH-MODEL-TFP-COBALT-MRT.md](../brain-export/colombo/HESPERIA-BRANCH-MODEL-TFP-COBALT-MRT.md) |
| COBALT formalization | [docs/brain-export/colombo/COBALT_research_FORMALIZATION-v0_1.md](../brain-export/colombo/COBALT_research_FORMALIZATION-v0_1.md) |
| Brain pointers | cursor repo `CLIENTS/hesperia/README.md` |

---

`SIGNED: Researcher (Colombo) | dev repo core+modules+branches | 2026-06-20 | igareosh/hesperia`

---

`SIGNED: Developer (Felix) | Claude Code context | 2026-08-04 | Class A modules re-homed core/runtime/ -> hesperia/modules/default/, per operator directive to keep core/ free of module-registry shapes`

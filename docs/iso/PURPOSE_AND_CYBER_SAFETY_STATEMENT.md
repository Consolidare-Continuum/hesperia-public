# Purpose and cyber-safety statement (descriptions → statement)

**Status:** built (whitepapered closing statement for the ISO documentation program)  
**Date:** 2026-10-13  
**Author research:** Platonov Igor — ULIM referat nr. **348** (12 Oct 2026)  
**Role of this file:** Closes open questions about **why the whole Hesperia project exists** and under **which circumstances** it may be treated as cyber-safe. It does **not** invent new engine facts — those stay in `docs/foundations/`. It turns the ISO **descriptions** (architecture, requirements, quality, lifecycle, operator guide) into one **statement**.

**Primary research artefact (PDF):** [`evidence/REFERAT-348-legislatie-cibernetica-licentiere-module-ULIM-2026-10-12.pdf`](evidence/REFERAT-348-legislatie-cibernetica-licentiere-module-ULIM-2026-10-12.pdf)  
**Editable RO source (brain):** `user_documents/hesperia_study_research_and aplication_romanian/REFERAT-348-legislatie-cibernetica-licentiere-module-2026-10-12.md`  
**Operational gate (brain):** `operational/assignments/reports/ETHAN-SPEC-HESPERIA-REAL-LICENCE-GATE-2026-10-12.md` (L1–L6)

---

## 1. Arc: description → statement

| Layer | Document | Answers |
|---|---|---|
| Description (what exists) | [`ARCHITECTURE_DESCRIPTION.md`](ARCHITECTURE_DESCRIPTION.md) | Stakeholders, viewpoints, where logic lives |
| Description (what must hold) | [`REQUIREMENTS_SPECIFICATION.md`](REQUIREMENTS_SPECIFICATION.md) | FR/NFR with source traces |
| Description (how quality is judged) | [`QUALITY_MODEL.md`](QUALITY_MODEL.md) | ISO/IEC 25010 mapping; honest gaps |
| Description (how change is governed) | [`LIFECYCLE_PROCESS.md`](LIFECYCLE_PROCESS.md) | Seal / release discipline |
| Description (how to operate) | [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) | `/analyze` vs `/product/interpret` |
| **Statement (why + when safe)** | **This file** + Referat **348** | Purpose of the whole project; evidence-before-claim cyber posture |

The foundation narrative that feeds the descriptions remains [`../foundations/00_INDEX.md`](../foundations/00_INDEX.md). Novelty (composition, not new math) remains [`../publication/NOVELTY_AND_POSITIONING.md`](../publication/NOVELTY_AND_POSITIONING.md). This statement does not replace either.

---

## 2. Purpose of the whole Hesperia project (closing narration)

**Hesperia is a multipurpose runtime semantic engine.** Its purpose is to make text-facing analysis **accountable**: a deterministic, falsifiable measurement pipeline must run and be governance-checked **before** any narrating layer is allowed to speak, and narrations are re-measured against what went in.

That purpose is **not**:

- a single-industry product story locked into the sealed core;
- an LLM with its own knowledge pretending to be measurement;
- a claim of ISO, NIS2, or CISA certification by association;
- a theatre of green boards (“DONE”) without named artefacts.

That purpose **is**:

1. **Measure first** — bounded structural read before narration (`ARCHITECTURE_DESCRIPTION.md` Pipeline Sequencing + Guard viewpoints; Sigma → Gamma → Theta).  
2. **Fail closed** — missing evidence blocks promotion/install; labels are not evidence.  
3. **Separate classes** — Class A (universal plumbing under `hesperia.modules.default`) vs Class B (domain/branch modules) stay honest; success on Class A does not imply Class B readiness.  
4. **Keep proprietary payloads out of public releases** when scope requires it (`QUALITY_MODEL.md` Security row; release-scope exclusions).  
5. **Own the chain of custody** — IP title, licence/entitlement, and runtime target are distinct questions (Referat 348 §5–§6; L1–L6).

This is the same thesis the operator whitepapered academically in Referat **348**: the recurring conflict between **normative commitment** (law, policy, “we are licensed / compliant / modular”) and **operational delivery** (named, custodied, accepted, scope-matched evidence). Hesperia’s project-level answer is to treat that conflict as **engineering discipline**, not as rhetoric.

---

## 3. Cyber-safe — under the right circumstances only

Hesperia may be considered **cyber-safe for a named deploy** only when circumstances match evidence, not aspiration.

### 3.1 Circumstances that count (positive)

| Circumstance | Meaning | Trace |
|---|---|---|
| **L1 Named instrument** | Written licence / grant / IP assignment / contract with title, parties, date | Ethan real-licence gate; Referat 348 §6 |
| **L2 Custody** | Bytes or pointer under trust custody / CC_ legal store — not chat paste | Same |
| **L3 Scope match** | Instrument covers the **named module id** and architectural class | Class A vs Class B; Referat 348 §7 |
| **L4 Acceptance** | Project owner or operator recorded as acceptor | Gate L4 |
| **L5 Class honesty** | No selling Class A permission as Class B (or reverse) | Architecture §2c practice |
| **L6 Named runtime target** | Dev vs prod host stated; host change reopens L6 | Gate L6 |
| **Guards / seal path** | Release and surface use respect Sigma/Gamma/Theta and sealed contracts | `QUALITY_MODEL.md`, `LIFECYCLE_PROCESS.md` |
| **Exposure review when needed** | New external agent / data boundaries get their own review — not “safe by analogy” | `QUALITY_MODEL.md` Security row |

When these hold for a **named** module and host, the project’s own research frame (Referat 348) supports treating that install as **evidence-based** and therefore **cyber-safe under those circumstances**.

### 3.2 Circumstances that do **not** count (explicit FAIL)

- Dependency SPDX / PyPI licence alone as product-module entitlement  
- Panel titles, agency seals, or third-party briefing materials as licence substitutes  
- CRM / task-board status without L1–L4 artefacts  
- Verbal “go” without written L1–L4  
- Claiming NIS2 / ISO 27001 / CISA authorization because the research cites those frameworks  
- Collapsing Class B into a Class A wave without a new L3  

Referat 348 names this pattern **compliance theatre**. The ISO program refuses it.

### 3.3 What this statement does **not** claim

- ISO 9001 / 27001 / 25010 **certification** (brain baseline remains **alignment only**).  
- That Hesperia is an “essential entity” under NIS2.  
- That EU cyber legislation or any CISA panel **authorizes** product installs.  
- A complete threat model or pen-test suite (still an honest gap in `QUALITY_MODEL.md` until built).  

Research frames (NIS2, panel scaffolding) are **epistemic context** for the evidence discipline — not regulatory cover.

---

## 4. Commercial SKU model (operator lock 2026-10-13)

With purpose questions closed under this statement + Referat **348**, product licensing follows:

| SKU | Role | Commercial |
|-----|------|------------|
| Class A `hesperia.modules.default` | Universal plumbing | Already licenced (wave HESP-CISA-04 / IP deed) |
| **HSPR** (product reflection / calibration index) | **Default product module** | **Licenced default** — not the research thread `HSPR_discovery` |
| **TFP** (`hesperia.modules.tfp`) | Class B field MVP | **Forever free** |
| MRT / COBALT / future modules | Scoped branches | **Paid** — unlock regulated by **HSPR × 120-books matrix in PostgreSQL** (`postgres_db`) |

Brain register: `governance/HESP-LIC-100-2026-REGISTER.md` · stamp `governance/hesperia_commercial_licence.txt`.  
Blue cyber-safety = §3 evidence-before-claim discipline (fail-closed). Still **not** ISO/NIS2 certification.

### 4.1 First commercial seal (exact)

| Field | Value |
|-------|-------|
| Product version | **Hesperia 1.0.0** |
| Licence instrument | **`CC-HES-LIC-1.0`** — [`CC-HES-LIC-1.0.md`](CC-HES-LIC-1.0.md) |
| Legal epoch | NIS2 Directive (EU) **2022/2555** + Referat **348** + L1–L6 — **passed** as post-research baseline 2026-10-13 |
| Release | [`release/v1.0.0/SEAL.md`](../../release/v1.0.0/SEAL.md) |

NIS2 appears only as post-research discipline. **No** NIS2/ISO certification claim.

## 5. How to use this file

| Audience | Use |
|---|---|
| Auditor / reviewer | Start at this statement → follow links into ISO descriptions → foundations for facts |
| Engineer / agent | Before module install or “we are secure” language: check L1–L6 + this §3 + SKU table §4 |
| Academic / ULIM | Cite Referat **348** PDF as the operator’s own research; this file is the product ISO binding of that research |
| Buyer / partner | Purpose = accountable measurement before narration; safety = conditional on evidence; HSPR default licenced; TFP free; other modules paid via matrix |

---

## 6. Register and maintenance

- Registered in [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](DOCUMENTATION_TRACEABILITY_MATRIX.md).  
- PDF under `docs/iso/evidence/` is the in-repo whitepaper copy; brain `user_documents/` remains the academic home.  
- If L1–L6 criteria change, update Ethan’s gate first, then amend §3 here in the same concern.  
- Commercial SKU changes → brain stamp + HESP-LIC-100 register first, then §4 here.  
- Do not thicken this file with new math or layer facts — push those to foundations.

---

SIGNED: Operator research (Platonov Igor) · ISO bind (Cursor) | Referat 348 → purpose/cyber-safety statement | 2026-10-13 | descriptions → statement · evidence-before-claim  
SIGNED: Cursor | commercial SKU lock (HSPR default · TFP free · paid via PG matrix) | 2026-10-13 | HESP-LIC-100

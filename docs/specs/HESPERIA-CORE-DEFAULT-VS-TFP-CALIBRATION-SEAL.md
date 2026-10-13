# Hesperia — CORE/DEFAULT vs TFP calibration seal

**Status:** SEALED 2026-09-14  
**Owner:** Grace (triage/seal) · Gena (code fix) · Ethan (architecture)  
**Incident:** live syzif propose silently used `domain=tfp` + `dict_b_tfp*` catalog (commit 17d827b left core scaffolding with TFP default for “compat”).

---

## Invariant (non-negotiable)

| Name | Equals | Corpus | Catalog / prompt |
|------|--------|--------|------------------|
| **DEFAULT** | `hesperia/modules/default/` | `modules/default/corpus/syzif` | `v0_core_syzif_001` + `SYSTEM_CORE` |
| **CORE** | Class A / default lane | same | same (`core.<area>.<slug>`) |
| **TFP** | `hesperia/modules/tfp/` only | `modules/tfp/data/…` | `dict_b_tfp*` + `SYSTEM_TFP` — **opt-in `--domain tfp`** |

- Scopes differ. Initial data differ. CORE is **wider**; TFP is **narrow** Class B.
- **No TFP in DEFAULT/CORE** — not as silent default, not as mixed catalog, not as `tfp.*` / `B_A*` drafts from syzif prose.

---

## How TFP leaked (closed)

1. Pre-2026-09-04: propose tool was TFP-only.
2. 17d827b added `domain=core` scaffolding but **defaulted `domain="tfp"`** “for old callers.”
3. `clearance_resume` / CLI never passed `domain=` → first live syzif run inherited TFP prompt + TFP catalog.
4. Folder provenance was already correct (`modules/default/corpus/syzif`); contamination was **runtime default**, not corpus misplacement.

---

## Enforcement

| Layer | Mechanism |
|-------|-----------|
| Code defaults | `propose_llm` + `_default_engine_paths` → **core** |
| CLI | `--domain {core,tfp}` default **core**; pairs corpus↔domain↔catalog |
| Pairing assert | `env_defaults.assert_domain_corpus_pairing` |
| CI | `tools/check_core_default_tfp_boundary.py` in sealed-runtime-gate |
| Resume | refuses propose checkpoints without `domain` or with domain mismatch |
| Artifacts | contaminated 2026-09-14 run quarantined under `*.CONTAMINATED_tfp_domain.*` |

---

## Agent rule

When calibrating / proposing on **syzif or default**: `--domain core` only.  
When calibrating on **TFP module corpus**: `--domain tfp` only.  
Never mix. Never “reuse TFP defaults for core.”

`SIGNED: Grace (triage) | CORE/DEFAULT vs TFP calibration seal | 2026-09-14 | boundary seal`

# HESPERIA v1.0.0 — first commercial licence seal

**Codename:** `commercial_licence_sealed`  
**Licence instrument:** **`CC-HES-LIC-1.0`** (exact)  
**Legal epoch:** NIS2 Directive (EU) 2022/2555 + Referat 348 + L1–L6 — **post-research passed** 2026-10-13 (**not** certification)  
**Baseline engine lineage:** v0.7.2  
**Authority:** Operator seal invoke 2026-10-13 (Cursor main ROUNDUP + commercial lock)

## What this release seals

First **released** Hesperia product version under the exact commercial module licence:

- HSPR = default licenced module  
- TFP = forever free  
- Paid modules = HSPR × 120-books matrix on `postgres_db` + L1–L6 · fail-closed  
- ISO purpose / blue cyber-safety statement + Referat 348 evidence bind  
- Runtime entitlement gate (`commercial_entitlement.py`)

## Include

- Instrument: [`docs/iso/CC-HES-LIC-1.0.md`](../../docs/iso/CC-HES-LIC-1.0.md)  
- PURPOSE §4 commercial SKU model  
- Brain stamp / HESP-LIC-100 ROUNDUP sealed  
- PG schema `hesperia_licence` (seed SKUs) · wiki HSPR indexed in `cc_brain`

## Explicit non-claims

No ISO / NIS2 / CISA certification. NIS2 appears only as post-research discipline.

## Verification

- `tests/product/test_commercial_entitlement.py` — pass  
- `query_brain_fts` — hspr_index / HCI wiki hits  
- `tools/validate_version_consistency.py` — run after VERSION bump  

SIGNED: Cursor | Hesperia 1.0.0 commercial seal | 2026-10-13 | CC-HES-LIC-1.0

# Corpus snapshot policy (HSR-V7-08)

Canonical policy: brain repo  
`operational/assignments/reports/NOAH-HSR-V7-08-CORPUS-SNAPSHOT-POLICY-2026-06-29.md`

**Summary:** `corpus_snapshot_id` names the frozen TFP/dict corpus for routed answers. Default `corpus-unset` → audit REVIEW_REQUIRED on corpus-backed claims. Format: `hesperia-corpus-<sealed_base>-<dict_lane>-<freeze_date>`. Override via `HESPERIA_CORPUS_SNAPSHOT_ID`.

Implementation: `sphere/router/pre_llm_compiler.py` · `runtime/services/product_interpret_service.py` · `sphere/router/audit.py`.

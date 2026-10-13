# Archive manifest

This manifest records archive moves made during the HSR-V7 ISO-grade rename and archive consolidation pass.

## Entries

### 1

- Old path: `docs/brain-export/README.md`
- New path: `docs/archive/brain-export/README.md`
- Reason: Archive guidance for the brain-export tree belongs in the archive area, not in the active docs root.
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `docs/archive/README.md`, `docs/archive/HSR-V7-CONSOLIDATION-INVENTORY.md`
- Date: 2026-07-06

### 2

- Old path: `core/attribution/lexical_loader.py`
- New path: `core/attribution/_deprecated/lexical_loader.py`
- Reason: Zero production importers confirmed (canon-matrix/attribution-layer consolidation pass). Oldest generation (Spec-20 v0.3) attribution module, superseded by attribution.py/attribution_shared.py/structural.py.
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `core/attribution/_deprecated/README.md`, `docs/foundations/attribution_layer.md`
- Date: 2026-07-30

### 3

- Old path: `core/attribution/attribution_compat.py`
- New path: `core/attribution/_deprecated/attribution_compat.py`
- Reason: Zero importers anywhere; a deprecation shim pointing at `structural.py`, itself never canonical (one of three live attribution modules, not the sole one).
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `core/attribution/_deprecated/README.md`, `docs/foundations/attribution_layer.md`
- Date: 2026-07-30

### 4

- Old path: `assets/lexicon/curated/A_CORE_STAR_MAP_v0_4_1_1.json`
- New path: `assets/lexicon/curated/_deprecated/A_CORE_STAR_MAP_v0_4_1_1.json`
- Reason: Only referenced by the now-archived `lexical_loader.py`. A checksum-pinned copy remains at `assets/lexicon/frozen/A_CORE_STAR_MAP_v0_4_1_1.json` and was intentionally left in place (immutable release ledger).
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `assets/lexicon/curated/_deprecated/README.md`
- Date: 2026-07-30

### 5

- Old path: `assets/lexicon/curated/A_CORE_STAR_MAP_v0_4_1_2.json`
- New path: `assets/lexicon/curated/_deprecated/A_CORE_STAR_MAP_v0_4_1_2.json`
- Reason: Zero references anywhere in the repo. Superseded by `A_CORE_STAR_MAP_v0_4_1_3.json`, the live asset used by `structural.py`/`attribution_shared.py`.
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `assets/lexicon/curated/_deprecated/README.md`
- Date: 2026-07-30

### 6

- Old path: `assets/lexicon/curated/A_CORE_STAR_MAP_v1.json`
- New path: `assets/lexicon/curated/_deprecated/A_CORE_STAR_MAP_v1.json`
- Reason: Referenced only by the now-archived `lexical_loader.py` and the standalone, non-runtime `lexicon/validation/validate_lexical.py`.
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `assets/lexicon/curated/_deprecated/README.md`
- Date: 2026-07-30

### 7

- Old path: `assets/lexicon/curated/B_SURFACE_LEX_FIELD_v1.json`
- New path: `assets/lexicon/curated/_deprecated/B_SURFACE_LEX_FIELD_v1.json`
- Reason: Referenced only by the now-archived `lexical_loader.py` and the standalone, non-runtime `lexicon/validation/validate_lexical.py`.
- Status: moved
- Authority level: `HISTORICAL-REFERENCE`
- Referenced by: `assets/lexicon/curated/_deprecated/README.md`
- Date: 2026-07-30


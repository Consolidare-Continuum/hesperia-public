# Anchor map reconcile — IPoV-01 ↔ METRIC `anchor_map_id`

**Task:** METRIC-19 (Gena)  
**Status:** DONE 2026-06-23  
**Operator freeze:** METRIC-17 option **A** — `ANCHOR_MAP_V1: FROZEN option=A — 2026-06-23 — igareosh`

## Single canonical id

| Layer | Location | `anchor_map_id` |
|-------|----------|-----------------|
| METRIC / 24_SPEC | `schemas/anchor_map_v1.json` | `anchor_map_v1` |
| Runtime emit | `runtime/services/hesperia_metric_emit.py` | `anchor_map_v1` |
| IPoV-01 code | `tersagor_agent/hesperia/geometry/anchor_map.py` | `ANCHOR_MAP_ID = "anchor_map_v1"` |
| JSON schema | `schemas/hesperia_metric_v01.json` | `anchor_map_id` string field |

## Rule alignment (option A)

IPoV-01 `geodesic_hex_count_for_family(family_index_in_area)`:

- `family_index_in_area % 6 == 0` → **250** slots (48 families per area ring)
- else → **251** slots (240 families)

Matches frozen JSON `family_slot_rule: family_index_in_area_mod_6_eq_0` and counts  
`240×251 + 48×250 = 72_240` geodesic hex.

## No duplicate maps

PoWV direction geometry lives in **tersagor** `ANCHOR_MAP` singleton. Product **does not** ship a second direction table — only the frozen registry JSON + `anchor_map_id` pointer for GCS/IPoW emit tiers.

**SIGNED: Developer (Gena) | Hesperia METRIC-19 | 2026-06-23 | anchor_map reconcile**

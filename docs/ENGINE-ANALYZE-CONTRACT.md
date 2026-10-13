# Hesperia Engine `/analyze` Response Contract

**SPEC ID**: HSPR-01 / HSPR-02  
**Version**: `v1.0` (Hesperia Vigil baseline)  
**Owner**: Developer (Felix replacing Gena)  
**Date**: 2026-06-11  
**Status**: Frozen — Python side (`HesperiaPublicSnapshot`, `HesperiaEngineBridge`) parses against this contract.

Product-surface note: `/analyze` is the frozen engine contract, not the main productization-facing
surface. In the repo's later buyer-language framing (`UPCELERATOR_PRODUCTIZATION_QA.md`), the
governed `/product/interpret` path is the closer match to a deterministic validation report with
audit trace.

---

## 1. Endpoint

```
POST /analyze
Content-Type: application/json
```

### 1.1 Request body (mandatory fields)

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Input text to analyze |
| `mode` | string | `"reflection"` when called from Vigil loop; `"standard"` otherwise |
| `overlay_hint` | object (optional) | Advisory bias overlay — see §3 |
| `temp_relation_overlay` | array (optional) | Transient edge boosts — see §4 |

---

## 2. Response body — mandatory fields

The engine **must** return all fields listed below. Python side raises `ValueError` if any mandatory field is absent.

### 2.1 Trace array

```json
{
  "trace": [
    {
      "area_id": "GOOD",
      "family_id": "Altruism",
      "concept_id": "concept_12",
      "label": "Human readable concept label",
      "activation": 0.82,
      "confidence": 0.75
    }
  ]
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `area_id` | string | Must match one of 12 canonical area IDs |
| `family_id` | string | Must match family name within the area |
| `concept_id` | string | Internal concept identifier |
| `label` | string | Public-safe human readable label |
| `activation` | float | `[0.0, 1.0]` |
| `confidence` | float | `[0.0, 1.0]` |

### 2.2 Dominant activation

```json
{
  "dominant_area_id": "GOOD",
  "dominant_family_id": "Altruism",
  "dominant_concept_id": "concept_12"
}
```

All three fields are **mandatory**. Must correspond to the highest-activation step in `trace[]`.

### 2.3 Scalar health metrics

```json
{
  "governance": 0.78,
  "loopability": 0.65,
  "tension_energy": 0.21,
  "obstacle_score": 0.10
}
```

| Field | Type | Constraints | Meaning |
|-------|------|-------------|---------|
| `governance` | float | `[0.0, 1.0]` | Alignment with policy/governance path |
| `loopability` | float | `[0.0, 1.0]` | Capacity for closed-loop coherent propagation |
| `tension_energy` | float | `[0.0, 1.0]` | Semantic tension / unresolved contradictions |
| `obstacle_score` | float | `[0.0, 1.0]` | Guard/obstacle density on traversal |

### 2.4 Flag arrays

```json
{
  "contradiction_flags": ["flag_id_1", "flag_id_2"],
  "weak_signals": ["signal_id_1"]
}
```

Both arrays **must** be present (may be empty `[]`). Contents are string identifiers; Python side treats them as opaque labels.

### 2.5 Complete minimal response example

```json
{
  "trace": [
    {
      "area_id": "GOOD",
      "family_id": "Altruism",
      "concept_id": "concept_001",
      "label": "Helping others",
      "activation": 0.85,
      "confidence": 0.80
    }
  ],
  "dominant_area_id": "GOOD",
  "dominant_family_id": "Altruism",
  "dominant_concept_id": "concept_001",
  "governance": 0.75,
  "loopability": 0.60,
  "tension_energy": 0.15,
  "obstacle_score": 0.05,
  "contradiction_flags": [],
  "weak_signals": []
}
```

---

## 3. `overlay_hint` — advisory activation modifiers (HSPR-02)

When `overlay_hint` is present in the request, the engine **should** apply these as additive biases to the activation scoring for this call only. The hint is **advisory**: if the engine does not support it, it must silently ignore it and return a normal response.

```json
{
  "overlay_hint": {
    "family_biases": {
      "GOOD:Altruism": {
        "prior_boost": 0.08,
        "contradiction_penalty": -0.02,
        "governance_modifier": 0.01
      }
    },
    "edge_biases": {
      "Altruism->Protection": {
        "weight_modifier": 0.05
      }
    }
  }
}
```

| Key format | Meaning |
|-----------|---------|
| `family_biases` key | `"{area_id}:{family_id}"` |
| `edge_biases` key | `"{from_family_id}->{to_family_id}"` |
| All values | Additive floats; engine must clamp final activation to `[0.0, 1.0]` |

**Engine fallback:** If `overlay_hint` is not supported, engine returns a standard response without the overlay applied. Python side uses `_engine_with_temp_overlay()` fallback to re-call without overlay.

---

## 4. `temp_relation_overlay` — transient edge boosts (HSPR-02 / HSPR-19)

When `temp_relation_overlay` is present, the engine applies these as transient edge weight boosts for **this call only**. Used by `RelationTeacherLoop` ping-pong.

```json
{
  "temp_relation_overlay": [
    {
      "from_area_id": "GOOD",
      "from_family_id": "Altruism",
      "to_area_id": "CARE",
      "to_family_id": "Compassion",
      "relation_type": "BRIDGES",
      "proposed_strength": 0.70
    }
  ]
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `from_area_id`, `to_area_id` | string | Canonical area IDs |
| `from_family_id`, `to_family_id` | string | Family names |
| `relation_type` | string | One of `RelationType` enum values |
| `proposed_strength` | float | `[0.0, 1.0]` — advisory edge weight boost |

**Engine fallback:** Same as `overlay_hint` — silently ignore if unsupported.

---

## 5. Python parsing — `HesperiaPublicSnapshot.from_engine_result()`

Located at `hesperia/reflection/reflection_models.py`.

```python
@classmethod
def from_engine_result(cls, result: dict, input_text: str) -> "HesperiaPublicSnapshot":
    ...
```

This method:
1. Reads `trace[]` → `SemanticTraceStep` list
2. Reads `dominant_area_id`, `dominant_family_id`, `dominant_concept_id`
3. Reads scalar metrics: `governance`, `loopability`, `tension_energy`, `obstacle_score`
4. Reads `contradiction_flags[]`, `weak_signals[]`
5. Raises `ValueError` if any mandatory field is absent or out of range

---

## 6. Acceptance criteria (HSPR-03)

The smoke test at `tests/test_hesperia_engine_bridge.py` (HSPR-03, blocked on live engine) asserts:

1. `trace` is non-empty list with all required fields present and in range
2. `dominant_area_id` matches an entry in `trace[].area_id`
3. `governance`, `loopability`, `tension_energy`, `obstacle_score` all in `[0.0, 1.0]`
4. `contradiction_flags` and `weak_signals` are lists (may be empty)

---

## 7. Versioning

Engine responses should optionally include `"contract_version": "v1.0"`. Python side ignores unknown fields for forward compatibility.

### 7.1 Flag-gated metric metadata (METRIC-22/23)

The frozen default response remains unchanged when both flags are absent or false.

- `HESPERIA_L6_PERTURBATION=1` adds `engine_result.meta.layer_6` (producer; default off).
- `HESPERIA_METRIC_EMIT=1` adds `engine_result.meta.hesperia_metric` and
  `engine_result.meta.interior_point_of_world_view`.
- `HESPERIA_GCS_EMIT=1`, when metric emit is enabled, adds the static
  `engine_result.meta.hesperia_metric.geodesic_sphere` descriptor.
- `meta.interior_point_of_world_view` is the METRIC-23 public read-only PointZero snapshot;
  the nested copy in `meta.hesperia_metric` remains part of the metric registry schema.

---

SIGNED: Developer (Felix) | Claude Code context | 2026-06-11 | ENGINE-ANALYZE-CONTRACT.md HSPR-01/HSPR-02

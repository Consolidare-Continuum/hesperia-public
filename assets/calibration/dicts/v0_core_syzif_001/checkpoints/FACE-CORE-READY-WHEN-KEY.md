# face=core readiness (no live call — key absent)

## When key available

1. Capture baseline: `face=core` inquire on fixed prompt pack (before bundle pin).
2. Pin `v0_core_syzif_001` in config / sealed version string.
3. Capture after: same prompt pack; diff scores / top concepts.
4. Do **not** enable `coherence_empirical_weight` until D-live gate (separate).

## Now (no key)

- Bundle paths ready under `assets/calibration/dicts/v0_core_syzif_001/`.
- Mock propose evidence in `checkpoints/`.
- Skipped marker: `face_core_skipped_no_openai_key.json`.

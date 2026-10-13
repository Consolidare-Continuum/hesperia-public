# Live propose gate (when OpenAI key returns)

**Do not** run full-corpus propose at extract `min_freq=2` (~3.6M rows → ~90k batches @40).

## Domain hard rule (2026-09-14)

- **DEFAULT = `core`** (Class A / `modules/default` / syzif / `v0_core_syzif_001`).
- **TFP is Class B** — pass `--domain tfp` only for TFP corpus work. Never the silent default.
- Catalog default: `assets/calibration/dicts/v0_core_syzif_001/dict_b.jsonl` (not `engine_dynamics_v060/dict_b/dict_b_tfp*.jsonl`).
- Prompt: `SYSTEM_CORE` (`core.<area>.<slug>`). Reject any live output that invents `tfp.*` / `B_A*` / RU TFP framing on book prose.

## Required before first live call

1. Export `OPENAI_API_KEY` from trustmaster custody only (never commit).
2. Unset or ignore `HESPERIA_CALIB_MOCK_OPENAI` for the live pass.
3. Raise extract floor — recommended start: **`min_freq >= 20`** (re-measure batches; target << 5k calls unless budget approved).
4. Cap phrases: area/family waves; checkpoint every batch (`raw_checkpoint_path`).
5. Dry fixture propose (051) with key once before full pass — **`--domain core`**.
6. After propose → anchor → merge → Stage8 evidence → **then** face=core before/after.
7. Dict D weight flip only after Stage8 + inert D load verified.

**Offline seal (current):** mock propose + D artifact; `coherence_empirical_weight=0`.

**Incident 2026-09-14:** live propose without `--domain` silently used TFP prompt+catalog → full redo required. Fix: defaults flipped to core; CLI exposes `--domain`.

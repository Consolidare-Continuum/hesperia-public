# HESPERIA v0.6.0 baseline sealed release

Ship the existing engine as-is.
Do not ship calibration dict payloads.
Do not ship corpus payloads.
Do not ship Chroma state.

Treat this folder as the baseline release contract.
Use it before Docker packaging.

## Include

- Ship runtime, core, hesperia, lexicon, schemas, matrices, P_CH, calibration profiles, public schema, capability flags.
- Ship current public routes only: `GET /health`, `POST /analyze`, `POST /compare`, `POST /batch`, `POST /batch-analyze`.
- Ship reference output and output inventory from working examples.

## Exclude

- Exclude `assets/calibration/dicts/`.
- Exclude corpus session payload trees.
- Exclude Chroma persist directories and snapshots.
- Exclude ad-hoc outputs and local run state.

## Pin

- Pin system version to `0.6.0`.
- Pin active calibration profile to `default_v1`.
- Pin expected dict pack name to `v0_6_0_clr_v052_2`.
- Keep dicts external. Prebuild them before sealed validation.

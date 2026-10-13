# HESPERIA v0.6.3 — IRC Teacher application run (GitHub archive)

**Sealed:** application-level 0.6.3 pre-release. **Engine math unchanged** from 0.6.2.

## Include

- Runtime, core, hesperia, lexicon, schemas, matrices, calibration **profiles** (not dict payloads).
- Shipping API: `GET /health`, `POST /analyze`, compare/batch routes.
- `docs/specs/0.6.3-IRC-TEACHER-RUN.md` — integration contract (tersagor `0149120`).
- `assets/calibration/dicts/archive_063_minimal/` — placeholder only.

## Exclude (GitHub archive)

- `assets/calibration/dicts/v0_*` prod sealed packs.
- `hesperia/modules/tfp/data/corpus/**` and `tfp_v1/corpus/**`.
- Chroma state, `outputs/`, secrets, brain team docs.

## Integration (out of tree)

- **tersagor** `igareosh/tersagor@0149120` — envelope, Teacher v063, IRC emitter, MySQL persist.
- **MySQL** ledger DDL: brain `cluster/hesperia/mysql/001_h063_schema.sql`.

## E2E

`HESPERIA_DICT_CALIB_OFFLINE=1 ./tools/run_063_archive_e2e_gate.sh` → **PASS** required before tag `hesperia-0.6.3`.

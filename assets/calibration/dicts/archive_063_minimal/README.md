# archive_063_minimal — GitHub release dict placeholder

**Not** the production sealed pack (`v0_6_0_clr_v052_*`). This directory exists so `VERSION.yaml` pins a named pack for the **0.6.3 public archive** without shipping prod dict JSONL or corpus trees.

## Run E2E on the archive

```bash
export HESPERIA_DICT_CALIB_OFFLINE=1
./tools/run_063_archive_e2e_gate.sh
```

For full calibration runs, prebuild dicts separately (out of band). Prod corpus remains on `Atomic-Commits-Team/hesperia` prod disk only.

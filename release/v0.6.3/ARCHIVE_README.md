# Hesperia 0.6.3 complete archive (GitHub)

**Git SHA:** `6df2695` (`6df2695e06829bab8db84f623721e8d687abd7e8`)  
**Sealed UTC:** 2026-06-14T13:00:24Z  
**Policy:** No production dict packs or corpus sessions in this archive.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export HESPERIA_DICT_CALIB_OFFLINE=1
./tools/run_063_archive_e2e_gate.sh
```

## Build zip for GitHub release

```bash
./tools/build_063_github_archive.sh
# -> dist/hesperia-0.6.3-archive.zip + SHA256SUMS
```

## What 0.6.3 adds

Application-level IRC-visible Teacher run (tersagor). This repo ships the **engine + shipping API** contract; live Teacher path runs on **tersagor VM** against prod `/analyze` on prichindel.

See `docs/specs/0.6.3-IRC-TEACHER-RUN.md`.

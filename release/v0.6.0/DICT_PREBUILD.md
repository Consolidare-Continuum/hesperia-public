# Dict prebuild

Do not bundle dict payloads in release.
Prebuild them outside the release zip.
Stage them under `assets/calibration/dicts/v0_6_0_clr_v052_2/` before full product seal.

## Required files

- `dict_a.jsonl`
- `dict_b.jsonl`
- `dict_c.jsonl`
- `links.jsonl`
- `weights.jsonl`
- `metrics.json`

## Do

- Build the pinned pack name exactly.
- Keep filenames exact.
- Keep JSONL schema stable.
- Keep `metrics.json` present for gate checks.
- Run `python3 tools/validate_version_consistency.py`.
- Run the calibration gates after dict placement.

## Do not

- Do not rename the pack dir.
- Do not commit private source corpora into the release bundle.
- Do not ship draft dict waves as product baseline.

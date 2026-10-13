# Release contents

Use this folder as the `0.6.0` release contract.
Read the files in this order.

## Read first

- `manifest.json` — release identity, routes, payload policy, doc list.
- `final_gate_status.json` — sealed gate result for this baseline.
- `system_seal.json` — latest full system seal result.

## Prepare externals

- `DICT_PREBUILD.md` — required dict pack name, filenames, and prebuild rules.
- `CORPUS_AND_CHROMA.md` — required corpus and Chroma preparation rules.

## Ship runtime

- `DOCKER_BUNDLE.md` — Docker bundle build and smoke contract.
- `docker_bundle_manifest.json` — Docker image tag and tar hash.
- `docker_bundle_verification.json` — Docker check result.
- `docker_requirements_used.txt` — runtime dependency lock used in shipping image.

## Validate behavior

- `OUTPUT_SURFACE.md` — output catalog and public envelope requirements.
- `output_inventory.json` — output examples and hashes.
- `e2e_reference_output.json` — checked reference behavior.
- `schema.json` — public output schema.
- `capabilities.yaml` — capability flags shipped with the engine.

## Trace build

- `BUILD_PROVENANCE.json` — generator and source trace.
- `checksums.txt` — file integrity list for this folder.
